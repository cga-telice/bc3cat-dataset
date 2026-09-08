"""Synthetic orchestrator (Phase D Task D2, Stage-A half).

Concept-loop driver that ties the Sprint-12-15 Stage-A primitives
together and populates the variant catalog under
`data/synthetic/variants/`:

    enumerate_targets / extract_slots   (slot_extractor, Sprint 15)
        -> load_prompt                  (prompts, Sprint 12)
        -> propose_variant              (variant_proposer, Sprint 14)
        -> emit_rules                   (rule_emitter, Sprint 15)
        -> compose_rules                (composition, Sprint 11)
        -> VariantCatalogEntry          (variant_catalog, Sprint 15)
        -> write_catalog_entry          (variant_catalog, Sprint 15)

Owns:

  * the condition matrix (`CONDITION_SPECS`) — condition label ->
    (modification-type pool, stack depth, sampled?);
  * deterministic per-concept variant planning (seeded RNG);
  * the per-variant proposal/emission/composition loop;
  * per-concept catalog assembly + write.

Does NOT own:

  * applying rules (`mutator.apply_*`) — interleaved with the stage
    rerun (Sprint 17, gated on D1);
  * the pipeline rerun (s03->s07) + raw-item emission (Sprint 17);
  * a concrete LLM transport (A3) — takes an `LLMClient`;
  * variant budgets (Phase F) — one plan per single-target / per
    stacked-condition for now.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from .composition import compose_rules
from .llm_proposer import LLMClient
from .prompts import load_prompt
from .rule_emitter import emit_rules
from .slot_extractor import concept_resumen, enumerate_targets, extract_slots
from .taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER
from .variant_catalog import (
    ProvenanceRecord,
    VariantCatalogEntry,
    VariantRecord,
    write_catalog_entry,
)
from .variant_proposer import propose_variant


_L1_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL, ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION, ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION, ModificationType.CODE_EXPANSION,
})
_L2_TYPES = frozenset({
    ModificationType.PARAPHRASE, ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})
_L3_TYPES = frozenset({ModificationType.OMISSION, ModificationType.REORDER})
ALL_TYPES = frozenset(ModificationType)
MAX_MIX_DEPTH = 5

PromptLoader = Callable[[ModificationType], str]


@dataclass(frozen=True)
class ConditionSpec:
    pool: frozenset[ModificationType]
    stack_depth: int          # 1 for singles; n for stacked_n; 0 = sampled depth
    sampled: bool


def _layer_tag(mtype: ModificationType) -> str:
    layer = TYPE_TO_LAYER[mtype]
    return {
        Layer.PARAM_VALUE: "L1",
        Layer.TEXT_VARIABLE: "L2",
        Layer.TEMPLATE: "L3",
        Layer.PARAM_DEFINITION: "PD",
    }[layer]


def _build_condition_specs() -> dict[str, ConditionSpec]:
    specs: dict[str, ConditionSpec] = {}
    for mtype in sorted(ALL_TYPES, key=lambda m: m.value):
        if mtype is ModificationType.NEW_PARAM:
            continue  # new_param_only is the PD single, named separately
        tag = _layer_tag(mtype)
        specs[f"single_{tag}_{mtype.value}"] = ConditionSpec(
            pool=frozenset({mtype}), stack_depth=1, sampled=False,
        )
    specs["new_param_only"] = ConditionSpec(
        pool=frozenset({ModificationType.NEW_PARAM}),
        stack_depth=1, sampled=False,
    )
    for n in (2, 3, 4):
        specs[f"stacked_{n}"] = ConditionSpec(
            pool=ALL_TYPES, stack_depth=n, sampled=True,
        )
    specs["stacked_5plus"] = ConditionSpec(
        pool=ALL_TYPES, stack_depth=5, sampled=True,
    )
    specs["full_random_mix"] = ConditionSpec(
        pool=ALL_TYPES, stack_depth=0, sampled=True,
    )
    return specs


CONDITION_SPECS: dict[str, ConditionSpec] = _build_condition_specs()


@dataclass(frozen=True)
class Attempt:
    modification_type: ModificationType
    target_id: Any


@dataclass(frozen=True)
class VariantPlan:
    variant_id: str
    condition: str
    attempts: tuple[Attempt, ...]


@dataclass(frozen=True)
class _VariantOutcome:
    record: Optional[VariantRecord]
    skipped: tuple[Modification, ...]
    provenance: tuple[ProvenanceRecord, ...]


def _all_attempts(
    stage_json: dict, concept_key: str, pool: frozenset[ModificationType],
) -> list[Attempt]:
    """Flatten every (mtype, target_id) over `pool`, in a deterministic
    order (pool sorted by `.value`, targets in `enumerate_targets`
    order)."""
    out: list[Attempt] = []
    for mtype in sorted(pool, key=lambda m: m.value):
        for target_id in enumerate_targets(stage_json, concept_key, mtype):
            out.append(Attempt(mtype, target_id))
    return out


def plan_concept_variants(
    stage_json: dict,
    concept_key: str,
    conditions: Sequence[str],
    *,
    rng: random.Random,
) -> list[VariantPlan]:
    plans: list[VariantPlan] = []
    counter = 0
    for condition in conditions:
        spec = CONDITION_SPECS[condition]
        if not spec.sampled:
            # exhaustive: one plan per enumerated target of the single type
            (mtype,) = tuple(spec.pool)
            for target_id in enumerate_targets(stage_json, concept_key, mtype):
                plans.append(VariantPlan(
                    variant_id=f"{concept_key}_syn_v{counter}",
                    condition=condition,
                    attempts=(Attempt(mtype, target_id),),
                ))
                counter += 1
        else:
            available = _all_attempts(stage_json, concept_key, spec.pool)
            if not available:
                continue
            if spec.stack_depth == 0:  # full_random_mix
                depth = rng.randint(2, min(MAX_MIX_DEPTH, len(available)))
            else:
                depth = min(spec.stack_depth, len(available))
            chosen = tuple(rng.sample(available, depth))
            plans.append(VariantPlan(
                variant_id=f"{concept_key}_syn_v{counter}",
                condition=condition,
                attempts=chosen,
            ))
            counter += 1
    return plans


def run_variant(
    stage_json: dict,
    concept_key: str,
    plan: VariantPlan,
    client: LLMClient,
    *,
    prompt_loader: PromptLoader = load_prompt,
) -> _VariantOutcome:
    accumulated_rules: list[dict] = []
    skipped: list[Modification] = []
    provenance: list[ProvenanceRecord] = []
    for attempt in plan.attempts:
        mtype = attempt.modification_type
        template = prompt_loader(mtype)
        slots = extract_slots(stage_json, concept_key, mtype, attempt.target_id)
        proposal = propose_variant(template, slots, client, mtype)
        provenance.append(ProvenanceRecord(
            modification_type=mtype,
            rendered_prompt=_render_for_provenance(template, slots, mtype),
            raw_responses=proposal.raw_responses,
            validated_payload=proposal.payload,
            skipped=proposal.skipped,
        ))
        if proposal.skipped is not None:
            skipped.append(proposal.skipped)
            continue
        result = emit_rules(
            proposal.payload, mtype, target_id=attempt.target_id,
            stage_json=stage_json, concept_key=concept_key,
        )
        accumulated_rules.extend(result.rules)
        for entry in result.unmatched:
            skipped.append(Modification(
                type=mtype, layer=TYPE_TO_LAYER[mtype], status="skipped",
                reason=f"unmatched_payload_entry: {entry!r}",
            ))
    admissible, comp_skips = compose_rules(accumulated_rules)
    skipped.extend(comp_skips)
    record = None
    if admissible:
        record = VariantRecord(
            condition=plan.condition,
            modification_type=plan.attempts[0].modification_type,
            target_id_repr=repr(tuple(a.target_id for a in plan.attempts)),
            rules=tuple(admissible),
        )
    return _VariantOutcome(record, tuple(skipped), tuple(provenance))


def run_concept(
    stage_json: dict,
    concept_key: str,
    conditions: Sequence[str],
    client: LLMClient,
    *,
    out_dir: Path,
    seed: int,
    prompt_loader: PromptLoader = load_prompt,
) -> tuple[VariantCatalogEntry, Path]:
    rng = random.Random(seed)
    plans = plan_concept_variants(stage_json, concept_key, conditions, rng=rng)
    records: list[VariantRecord] = []
    skipped: list[Modification] = []
    provenance: list[ProvenanceRecord] = []
    for plan in plans:
        outcome = run_variant(
            stage_json, concept_key, plan, client, prompt_loader=prompt_loader,
        )
        if outcome.record is not None:
            records.append(outcome.record)
        skipped.extend(outcome.skipped)
        provenance.extend(outcome.provenance)
    entry = VariantCatalogEntry(
        concept_key=concept_key,
        concept_resumen=concept_resumen(stage_json, concept_key),
        parent_key=stage_json[concept_key].get("parent_key", ""),
        variants=tuple(records),
        skipped=tuple(skipped),
        provenance=tuple(provenance),
    )
    path = write_catalog_entry(entry, out_dir)
    return entry, path


def run_catalog(
    stage_json: dict,
    concept_keys: Sequence[str],
    conditions: Sequence[str],
    client: LLMClient,
    *,
    out_dir: Path,
    seed: int,
    prompt_loader: PromptLoader = load_prompt,
) -> list[Path]:
    paths: list[Path] = []
    for concept_key in concept_keys:
        _, path = run_concept(
            stage_json, concept_key, conditions, client,
            out_dir=out_dir, seed=_seed_for(concept_key, seed),
            prompt_loader=prompt_loader,
        )
        paths.append(path)
    return paths


# ----- helpers ----------------------------------------------------------

def _seed_for(concept_key: str, base_seed: int) -> int:
    """Stable per-concept seed: same concept samples the same way
    regardless of batch composition or iteration order."""
    h = hashlib.sha256(f"{base_seed}:{concept_key}".encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _render_for_provenance(
    template: str, slots: dict, mtype: ModificationType,
) -> str:
    """Reuse the proposer's renderer so provenance stores the exact
    prompt that was sent. `propose_variant` renders internally; we
    re-render here for the record. (Sprint 17 may thread the rendered
    string out of `propose_variant` to avoid the double render; the
    cost is one cheap string format, so it's not worth widening the
    C3 surface for now.)"""
    from .variant_proposer import _render_prompt
    return _render_prompt(template, slots, mtype)
