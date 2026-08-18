# Sprint 16 — Phase D Task D2 (synthetic orchestrator — concept-loop driver + condition matrix; Stage-A catalog populator)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 16                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | D2 (the Stage-A half — see [`../RESEARCH_PROTOCOL.md §5 Phase D`](../RESEARCH_PROTOCOL.md)) |
| **Predecessor** | Sprint 15 — `slot_extractor.py` + `rule_emitter.py` + `variant_catalog.py` (see [`SPRINT_15.md`](SPRINT_15.md)) |
| **Successor**   | Sprint 17 — Phase D Task D1 (stage hooks) + the D2 pipeline-rerun half (consume the catalog, materialise mutated stage JSONs, rerun s03→s07, emit raw synthetic items) |

---

## Context

Sprints 12–15 built the full **Stage-A primitive set**:

- **C1** (Sprint 12) — `prompts/`, the 12 Spanish prompt templates +
  `load_prompt`.
- **C2** (Sprint 13) — `llm_proposer.py`, the `LLMClient` protocol +
  `propose()` with retry/fallback.
- **C3** (Sprint 14) — `variant_proposer.py`, `propose_variant` +
  per-type schema validation + `EXPECTED_SLOTS`.
- **C4-prep + C4** (Sprint 15) — `slot_extractor.py`
  (`enumerate_targets` / `extract_slots`), `rule_emitter.py`
  (`emit_rules` → `EmissionResult`), `variant_catalog.py`
  (`write_catalog_entry` / `read_catalog_entry` + the three frozen
  dataclasses).

Every primitive is independently tested and pure. **Nothing wires them
together yet.** Sprint 16 ships the driver that does: a concept-loop
orchestrator that, for each `(concept, condition)`, enumerates targets,
renders prompts, proposes variants (stubbed LLM), emits and composes
rules, and writes one `VariantCatalogEntry` per concept to
`data/synthetic/variants/`.

### The Stage-A / Stage-B boundary is the load-bearing scope decision

The protocol's [§5 Phase D D2](../RESEARCH_PROTOCOL.md) reads:

> **D2. Synthetic orchestrator.** `src/synthetic/run_synthetic.py`
> (or notebook) — given a variant catalog, materialises mutated stage
> JSONs, reruns s03→s07, emits raw synthetic items into
> `data/synthetic/intermediate/`.

That sentence spans two genuinely separable halves:

1. **Stage-A close — produce the variant catalog.** Loop concepts ×
   conditions, propose variants, emit + compose rules, persist
   per-concept catalog files. This is the durable Stage-A artifact the
   design table calls out as *"decoupled from pipeline reruns"*
   ([`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) Design
   Decisions). It needs only the Sprint-12–15 primitives + a stub LLM.
   **Fully testable now, zero notebook execution, zero real IO.**
2. **Stage-B — consume the catalog, rerun the pipeline.** Read the
   catalog, **apply** the rules to stage JSONs (`mutator.apply_*`),
   rerun s03→s07, emit raw items. This needs **D1 stage hooks**
   (unbuilt — s03/s04/s05 are notebooks, not importable functions) and
   it must **interleave application with re-execution across the four
   injection points** (PD/L1 inject at s02→s03, L2 at s03→s04, L3 at
   s04→s05). You cannot apply a stacked cross-layer variant to a single
   in-memory JSON — the layers target different stage representations.

Sprint 16 ships **half 1 only**. Half 2 (D1 + the rerun) is Sprint 17.
This split is forced by the architecture, not chosen for convenience:
the catalog is explicitly the decoupling seam (C4's "pipeline reruns
*consume* this catalog"), and rule application is inseparable from the
stage rerun it's interleaved with.

Consequence: **Sprint 16 does not call `mutator.apply_*`.** It calls
`composition.compose_rules` (to validate stackability, fix apply order,
and log unstackable skips — all state-blind, rule-vs-rule only) and
stores the composed admissible rules in the catalog. The rerun
(Sprint 17) is what applies them, stage by stage.

### Three design tensions to resolve up front

1. **Condition matrix: data or code?** The seven condition families
   (`single_L1_*` ×6, `single_L2_*` ×3, `single_L3_*` ×2,
   `new_param_only`, `stacked_2..5+`, `full_random_mix`) are a fixed
   recipe table ([`../RESEARCH_PROTOCOL.md §6`](../RESEARCH_PROTOCOL.md)).
   A YAML file (`configs/synthetic/variant_budgets.yaml`) is the
   eventual home for *per-concept budgets* (Phase F), but the
   condition→modification-type *mapping* is structural and stable.
   Sprint 16 ships it as a **Python module-level constant**
   (`CONDITION_SPECS`), same call Sprint 11 made for
   `COMPATIBILITY_MATRIX`. YAML externalisation is deferred to Phase F
   when budgets need an editable surface without a code change.
2. **Determinism under sampling.** `single_*` and `new_param_only`
   are exhaustive (one attempt per enumerated target — deterministic by
   construction). `stacked_*` and `full_random_mix` *sample* a depth-N
   subset of `(mtype, target)` pairs from the eligible pool. Sampling
   must be **reproducible**: the orchestrator threads a seeded
   `random.Random(seed)` and never touches the global `random` module
   or set iteration order. Pinned by a "run-twice-same-catalog" test.
   Same determinism discipline Sprint 6.5 enforced for
   `s07_Filter_duplicates.ipynb` and Sprint 15 enforced for
   `enumerate_targets`.
3. **Apply-or-not, and the role of `compose_rules`.** Because Sprint 16
   doesn't apply rules, one might ask why it composes them at all. The
   answer: composition is **state-blind rule-vs-rule** validation
   (Sprint 11) — it catches same-target collisions, layer-dependency
   conflicts (a `new_param` axis can't also carry an L1 mutation in the
   same batch), and fixes the PD→L1→L2→L3 apply order. That validation
   belongs in Stage A so the catalog records *admissible, ordered*
   rules; the Stage-B rerun then applies them without re-deciding
   compatibility. Skips from composition land in the catalog's
   `skipped` log with their reasons, exactly as the `Modification`
   schema intends. **Rule-vs-data** validation (does this `value` label
   exist on this axis? does this `original` substring appear in this
   template?) stays at apply-time in Sprint 17's rerun — that's the
   per-layer worker's job, and it needs the live stage JSON.

Sprint 15's verification baseline: **526 passed + 1 skipped.**
Sprint 16 adds one new module + one new test file. Net pytest delta
target: **≥30 new functions** = **≥556 passed** total. Zero failures,
zero new skips, zero changes to surviving tests. No changes to any
`layer_*.py`, `mutator.py`, `composition.py`, `taxonomy.py`,
`slot_extractor.py`, `rule_emitter.py`, `variant_catalog.py`,
`variant_proposer.py`, `llm_proposer.py`, or `src/synthetic/prompts/`.

---

## Scope

### In scope

- **D2 (Stage-A half): the orchestrator** — new module
  `src/synthetic/run_synthetic.py`. Public surface:

  - `CONDITION_SPECS: dict[str, ConditionSpec]` — module-level
    constant, one entry per condition label. `ConditionSpec` is a
    frozen dataclass `{pool: frozenset[ModificationType],
    stack_depth: int, sampled: bool}`:
    - `single_L1_synonym_label` … `single_L1_code_expansion` (6) —
      `pool={one L1 type}`, `stack_depth=1`, `sampled=False`.
    - `single_L2_paraphrase` / `single_L2_expansion` /
      `single_L2_compression` (3) — `pool={one L2 type}`,
      `stack_depth=1`, `sampled=False`.
    - `single_L3_omission` / `single_L3_reorder` (2) —
      `pool={one L3 type}`, `stack_depth=1`, `sampled=False`.
    - `new_param_only` — `pool={NEW_PARAM}`, `stack_depth=1`,
      `sampled=False`.
    - `stacked_2` / `stacked_3` / `stacked_4` / `stacked_5plus` —
      `pool=ALL_TYPES`, `stack_depth=2/3/4/5`, `sampled=True`.
    - `full_random_mix` — `pool=ALL_TYPES`, `stack_depth=0`
      (interpreted as "sample a random depth in `[2, MAX_MIX_DEPTH]`"),
      `sampled=True`.
    The label naming follows the `single_{layer}_{type.value}` /
    `stacked_{n}` / `full_random_mix` convention the downstream
    `bc3cat-retrieval` slices key on
    ([`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) Generation
    Conditions).

  - `@dataclass(frozen=True) class ConditionSpec` — as above.

  - `@dataclass(frozen=True) class Attempt` — one
    `(modification_type, target_id)` pair the orchestrator will ship
    through `propose_variant`. Fields:
    `modification_type: ModificationType`, `target_id: Any`.

  - `@dataclass(frozen=True) class VariantPlan` — one variant to
    attempt for a concept. Fields: `variant_id: str` (the
    `{concept_key}_syn_v{n}` id), `condition: str`,
    `attempts: tuple[Attempt, ...]`. A `single_*` plan has exactly one
    attempt; a `stacked_n` plan has `n`.

  - `def plan_concept_variants(stage_json, concept_key, conditions, *,
    rng) -> list[VariantPlan]` — pure planner. For each condition in
    `conditions` (a sequence of condition labels), builds the
    `VariantPlan`s:
    - `single_*` / `new_param_only`: one plan per enumerated target
      (`slot_extractor.enumerate_targets(stage_json, concept_key,
      mtype)`), each with a single `Attempt`. A condition whose single
      type yields no targets (e.g., `single_L2_paraphrase` on a concept
      with no `text_variables`) contributes zero plans — graceful skip.
    - `stacked_n`: sample `n` distinct `(mtype, target)` attempts from
      the union of every type's enumerated targets across the pool,
      drawn with `rng`. If fewer than `n` distinct attempts exist for
      the concept, the plan lands with as many as exist (and is dropped
      entirely if zero). One plan per `stacked_n` condition per concept
      (budgets — multiple plans per condition — are Phase F).
    - `full_random_mix`: sample a depth `d = rng.randint(2,
      min(MAX_MIX_DEPTH, n_available))`, then sample `d` attempts as
      above. One plan per concept.
    `variant_id` counter is per-concept monotonic across all
    conditions, assigned in `conditions` order then per-target order
    (deterministic).

  - `def run_variant(stage_json, concept_key, plan, client, *,
    prompt_loader=load_prompt) -> _VariantOutcome` — drives one
    `VariantPlan` end-to-end:
    1. For each `Attempt`: render the prompt
       (`prompt_loader(mtype)` → `propose_variant(template, slots,
       client, mtype)` where `slots = extract_slots(...)`), capture a
       `ProvenanceRecord` regardless of outcome.
    2. On a successful proposal: `emit_rules(payload, mtype,
       target_id=..., stage_json=..., concept_key=...)`; accumulate
       `result.rules`; route `result.unmatched` entries into the skip
       log as `Modification(status="skipped",
       reason="unmatched_payload_entry: ...")`.
    3. On a skipped proposal (C2 fallback / C3 schema fail):
       accumulate `proposal.skipped` into the skip log.
    4. After all attempts: `compose_rules(accumulated_rules)` →
       `(admissible_in_order, composition_skips)`; extend the skip log
       with `composition_skips`.
    5. Build a `VariantRecord(condition=plan.condition,
       modification_type=<the plan's lead type — see below>,
       target_id_repr=repr(<the attempts' target_ids>),
       rules=tuple(admissible_in_order))` **iff** `admissible_in_order`
       is non-empty; otherwise no `VariantRecord` (the variant landed
       nothing — all attempts skipped — and only contributes skip +
       provenance records).
    Returns `_VariantOutcome(record: Optional[VariantRecord],
    skipped: list[Modification], provenance: list[ProvenanceRecord])`.

  - `def run_concept(stage_json, concept_key, conditions, client, *,
    out_dir, seed, prompt_loader=load_prompt) -> tuple[VariantCatalogEntry, Path]`
    — top per-concept driver: seeds `rng = random.Random(seed)`, plans,
    runs each plan, aggregates all `VariantRecord`s / skips /
    provenance into one `VariantCatalogEntry`, calls
    `write_catalog_entry(entry, out_dir)`, returns the entry + the
    written path.

  - `def run_catalog(stage_json, concept_keys, conditions, client, *,
    out_dir, seed, prompt_loader=load_prompt) -> list[Path]` — the
    outer loop over `concept_keys`. Each concept gets a **derived
    per-concept seed** (`seed_for(concept_key, seed)` — a stable hash
    so the same concept always samples the same way regardless of the
    iteration order or which other concepts are in the batch). Returns
    the list of written catalog paths in `concept_keys` order.

  - Module-level constants: `ALL_TYPES` (frozenset of all 12
    `ModificationType`), `MAX_MIX_DEPTH` (an int — start at 5,
    matching `stacked_5plus`), and the `_L1_TYPES` / `_L2_TYPES` /
    `_L3_TYPES` partitioning (re-encoded sibling constants, same as
    Sprint 15's modules).

- **Tests** — new test file `tests/synthetic/test_run_synthetic.py`;
  ≥30 functions. Coverage outlined in §Tasks.

- **Housekeeping**:
  - Sprint 16 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - One new ✅ row in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files in
    This Branch" section (`run_synthetic.py`) — flip ❌ → ✅ with the
    Stage-A-half annotation.
  - Prepend an "After Sprint 16 — …" entry to the Sprint History
    section.

### Out of scope (explicit)

- **Rule application (`mutator.apply_*`).** Sprint 16 composes and
  catalogs rules; it does **not** apply them. Application is
  interleaved with the stage rerun across the four injection points
  (PD/L1 → s03 → L2 → s04 → L3 → s05) and needs the live stage JSON for
  rule-vs-data validation — Sprint 17's job. The catalog stores the
  composed admissible rules; the rerun applies them.
- **D1 stage hooks.** s03/s04/s05 are notebooks, not importable
  functions. Wrapping them to accept mutated stage JSONs transparently
  is D1 — Sprint 17. Sprint 16 reads stage JSON as an in-memory dict
  fixture; it does not execute any notebook.
- **The pipeline rerun (s03→s07) and raw-item emission.** The Stage-B
  half of D2. Sprint 17, gated on D1.
- **A concrete LLM transport.** Same Sprint 13/14/15 rationale — A3
  (proposer-model choice) still TBD. Tests use the `_StubLLMClient`
  pattern (a queued-response client, same as `test_llm_proposer.py`).
- **Live LLM calls in pytest.** Identical rationale. The orchestrator
  takes an `LLMClient`; tests inject a stub.
- **Real stage-JSON IO in pytest.** All fixtures are inline literal
  dicts. Reading real `data/intermediate/{CHAPTER}/*.json` off disk is
  Sprint 17's concern (it needs the path-config plumbing
  `config.stage_path` already provides, plus D1).
- **Per-concept variant budgets** (`configs/synthetic/variant_budgets.yaml`).
  Phase F. Sprint 16 generates one plan per `single_*` target and one
  plan per `stacked_*` / `mix` condition. Capping variant counts per
  type per concept is F2's tuning.
- **`new_param_allowlist.yaml`.** Still deferred (Sprint 15) — the
  `allowlist` slot stays `"[]"`. The orchestrator passes whatever
  `extract_slots` produces.
- **PD `var_definition` / `template_patch` parsing.** Sprint 15's
  partial PD lift stands — the orchestrator catalogs the
  `metadata.{var_definition, template_patch}` raw strings as emitted.
  Parsing them into `text_variable` / `template_patches` rule fields is
  still a follow-up (it lands when the Stage-B rerun needs the full PD
  effect, Sprint 17+).
- **Cache hygiene (D3).** Clearing pickled BM25 / embedding /
  LlamaIndex caches between runs is D3 — a Stage-B concern (the caches
  only matter once real items are emitted). Sprint 17+.
- **Metadata join / schema validator (E1–E2).** The catalog stores the
  `modifications` log per variant; binding synthetic *items* to their
  `modifications` via `(original_key, variante_id)` is E1, and it needs
  the raw items the Stage-B rerun produces. Sprint 18+.
- **Changes to existing source modules.** Sprint 16 is additive in one
  new module file + one test file. No edits to any prior
  `src/synthetic/*.py` (besides the two doc files).

---

## Module surface

### `src/synthetic/run_synthetic.py`

```python
"""Synthetic orchestrator (Phase D Task D2, Stage-A half).

Concept-loop driver that ties the Sprint-12–15 Stage-A primitives
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

from .llm_proposer import LLMClient
from .composition import compose_rules
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


def _all_attempts(stage_json, concept_key, pool) -> list[Attempt]:
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


def _render_for_provenance(template, slots, mtype) -> str:
    """Reuse the proposer's renderer so provenance stores the exact
    prompt that was sent. `propose_variant` renders internally; we
    re-render here for the record. (Sprint 17 may thread the rendered
    string out of `propose_variant` to avoid the double render; the
    cost is one cheap string format, so it's not worth widening the
    C3 surface for now.)"""
    from .variant_proposer import _render_prompt
    return _render_prompt(template, slots, mtype)
```

### Behavioural requirements

1. **`CONDITION_SPECS` covers exactly the protocol's condition table —
   17 fixed labels:** 6 `single_L1_*` + 3 `single_L2_*` + 2
   `single_L3_*` + `new_param_only` + `stacked_2` + `stacked_3` +
   `stacked_4` + `stacked_5plus` + `full_random_mix` = 17. Pinned by a
   test that asserts the key set and that every `single_*` pool is a
   singleton whose layer tag matches the label.
2. **`plan_concept_variants` is deterministic given an `rng`.** Same
   `(stage_json, concept_key, conditions, seed)` → identical
   `list[VariantPlan]` (including `variant_id`s and sampled attempts).
   Pinned by a run-twice-equal test.
3. **`single_*` conditions are exhaustive over targets.** A concept
   with two L1 axes yields two `single_L1_synonym_label` plans (one per
   axis), each a single-attempt plan. Pinned.
4. **A condition with no eligible targets contributes zero plans.**
   `single_L2_paraphrase` on a concept with no `text_variables` →
   no plan, no crash. Pinned.
5. **`stacked_n` samples `n` distinct attempts; degrades gracefully.**
   If only `k < n` distinct attempts exist, the plan has `k` attempts;
   if `k == 0`, no plan. Pinned for both the full and degraded cases.
6. **`full_random_mix` samples a depth in `[2, min(MAX_MIX_DEPTH,
   available)]`.** Reproducible under the seed. Pinned.
7. **`run_variant` records one `ProvenanceRecord` per attempt.** A
   3-attempt plan yields 3 provenance records regardless of how many
   attempts succeed. Pinned.
8. **A fully-skipped variant lands no `VariantRecord` but does record
   skips + provenance.** If every attempt's proposal is skipped (stub
   returns malformed JSON), `outcome.record is None`,
   `outcome.skipped` is non-empty, `outcome.provenance` has one entry
   per attempt. Pinned.
9. **`run_variant` calls `compose_rules`, never `mutator.apply_*`.**
   Composition skips land in `outcome.skipped`; the
   admissible-in-order rules land in the `VariantRecord`. Pinned by a
   stacked test whose two attempts collide on the same target →
   one rule lands, one composition skip recorded. (Importing
   `mutator` inside `run_synthetic` is a static tell of scope creep;
   a test asserts `run_synthetic` has no `mutator` import.)
10. **Unmatched payload entries become skip records.** An L1 attempt
    whose LLM payload carries an `original` with no matching axis value
    → the entry rides in `EmissionResult.unmatched` and the
    orchestrator converts it to a
    `Modification(reason="unmatched_payload_entry: ...")` skip. Pinned.
11. **`run_concept` writes exactly one catalog file per concept.**
    `{concept_key}.json` under `out_dir`; the returned `VariantCatalogEntry`
    round-trips via `read_catalog_entry`. Pinned.
12. **`run_catalog` is order-stable and per-concept-seed-stable.** The
    same concept produces the same catalog regardless of which other
    concepts are in the batch or their order (because `_seed_for`
    derives the per-concept seed from `concept_key`). Pinned by a
    "concept in batch-of-1 == concept in batch-of-3" test.
13. **No module-level side effects.** No env reads, no on-import IO, no
    `out_dir` resolution at import time. Pinned by `importlib.reload`.
14. **No new runtime dependencies.** Stdlib (`hashlib`, `random`,
    `dataclasses`, `pathlib`, `typing`) + in-repo only.

### Acceptance

- `from synthetic.run_synthetic import (CONDITION_SPECS, ConditionSpec,
  Attempt, VariantPlan, plan_concept_variants, run_variant,
  run_concept, run_catalog)` succeeds.
- `set(CONDITION_SPECS) == {17 fixed labels}`; every `single_*` pool is
  a singleton.
- For a fixture concept with one L1-eligible axis and a stub LLM
  returning a valid `synonym_label` payload: `run_concept` writes a
  catalog file whose single `VariantRecord` carries a
  `synonym_label` rule that `layer_l1.apply_synonym_label` accepts
  without raising (the same end-to-end gate Sprint 15's acceptance
  pinned, now driven by the orchestrator).
- `plan_concept_variants(...)` called twice with fresh
  `random.Random(seed)` returns equal plan lists.
- `pytest tests -q` exits 0 with **≥556 passed, exactly 1 skipped**,
  zero failures.

---

## Tasks

### Task 1 — `src/synthetic/run_synthetic.py`

Create the module per the surface above. Implementation notes:

1. `CONDITION_SPECS` is built once at import (`_build_condition_specs()`),
   not recomputed per call. The builder derives the `single_*` labels
   from the enum so a future 13th `ModificationType` surfaces a new
   condition automatically (same forcing-function rationale as Sprint
   12's `PROMPT_FILENAMES`).
2. All sampling goes through the passed `rng` (`rng.sample`,
   `rng.randint`). Never call the module-level `random` functions and
   never iterate a `set` for ordering — sort by `.value` first. Same
   PYTHONHASHSEED determinism trap Sprint 6.5 / Sprint 15 pinned.
3. `run_variant` accumulates rules across attempts *before* composing —
   composition is a batch operation (it needs to see all rules to
   detect same-target / layer-dependency conflicts).
4. `_seed_for` uses `hashlib.sha256` (stable across processes and
   Python versions, unlike `hash()` which is salted per-process). The
   per-concept seed must be reproducible run-to-run.
5. Do **not** import `mutator`. If you reach for `apply_l1` etc., stop
   — application is Sprint 17.

### Task 2 — Tests

New test file `tests/synthetic/test_run_synthetic.py`. ≥30 functions.
Reuse the `_StubLLMClient` queued-response pattern from
`test_llm_proposer.py` / `test_variant_proposer.py`. Skeleton:

```python
# tests/synthetic/test_run_synthetic.py
import copy, importlib, json, random
import pytest
from synthetic import run_synthetic
from synthetic.run_synthetic import (
    CONDITION_SPECS, ConditionSpec, Attempt, VariantPlan,
    plan_concept_variants, run_variant, run_concept, run_catalog,
)
from synthetic.taxonomy import ModificationType
from synthetic.variant_catalog import read_catalog_entry


class _StubLLMClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._responses.pop(0)


_STAGE = {
    "OEB020aa": {
        "parent_key": "OEB020$",
        "parameters": {
            "B": {"label": "TIPO DE TERRENO",
                  "values": [{"label": "a", "value": "Normal"},
                             {"label": "b", "value": "Rocoso"}]},
        },
        "text_variables": {"K": '"normal" * (%B=a) + "rocoso" * (%B=b)'},
        "resumen": "Canalización para terreno normal",
        "texto": "Canalización para terreno $K, incluso $N",
    },
}
```

Required test cases (≥30 functions):

1. **`test_module_exposes_public_surface`**
2. **`test_condition_specs_key_set`** — exactly the 17 labels
3. **`test_condition_specs_singles_are_singletons_with_matching_layer_tag`**
4. **`test_condition_specs_stacked_depths`** — `stacked_2/3/4` depths
   2/3/4, `stacked_5plus` depth 5, `full_random_mix` depth 0
5. **`test_plan_single_l1_is_exhaustive_over_axes`** — 2 axes → 2 plans
6. **`test_plan_single_assigns_one_attempt_each`**
7. **`test_plan_condition_with_no_targets_yields_no_plan`** —
   `single_L2_*` on a concept with no `text_variables`
8. **`test_plan_variant_ids_are_monotonic_per_concept`**
9. **`test_plan_is_deterministic_under_same_seed`** — run twice, equal
10. **`test_plan_stacked_samples_n_distinct_attempts`**
11. **`test_plan_stacked_degrades_when_fewer_than_n_available`**
12. **`test_plan_full_random_mix_depth_in_bounds`**
13. **`test_run_variant_records_one_provenance_per_attempt`**
14. **`test_run_variant_success_lands_record_with_rules`** — stub
    returns a valid `synonym_label` payload
15. **`test_run_variant_all_skipped_lands_no_record`** — stub returns
    malformed JSON for every attempt
16. **`test_run_variant_unmatched_payload_becomes_skip`** — LLM typo
    `original`
17. **`test_run_variant_calls_compose_not_apply`** — stacked
    same-target collision → 1 rule + 1 composition skip
18. **`test_run_synthetic_does_not_import_mutator`** — `assert
    "mutator" not in run_synthetic.__dict__`-style source audit
19. **`test_run_variant_provenance_carries_payload_on_success`**
20. **`test_run_variant_provenance_carries_skip_on_failure`**
21. **`test_run_concept_writes_one_catalog_file`**
22. **`test_run_concept_entry_round_trips_via_read`**
23. **`test_run_concept_entry_carries_concept_resumen_and_parent_key`**
24. **`test_run_concept_emitted_rule_applies_via_layer_l1`** — the
    end-to-end gate: pull the landed rule, call
    `layer_l1.apply_synonym_label([rule], stage)`, assert no raise
25. **`test_run_catalog_writes_one_file_per_concept`**
26. **`test_run_catalog_order_stable`**
27. **`test_run_catalog_per_concept_seed_stable_across_batch_size`** —
    concept in batch-of-1 == concept in batch-of-3
28. **`test_seed_for_is_stable_across_process`** — known input → known
    output (pin the sha256-derived int)
29. **`test_run_concept_is_deterministic_under_same_seed`** — two runs
    to two dirs → equal entries
30. **`test_condition_specs_pool_membership`** — `stacked_*` /
    `full_random_mix` pools == `ALL_TYPES`
31. **`test_module_has_no_side_effects_at_import`** —
    `importlib.reload`

Test count: ~31 functions. With the stub-LLM queue feeding multiple
attempts, several exercise multi-attempt flows. Binding gate: "≥30
listed functions, all green".

### Task 3 — Housekeeping

After Tasks 1–2 pass:

1. Append a Sprint 16 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: the new module,
   its public surface, the condition matrix, the deterministic planner,
   the Stage-A-close framing (catalog populated; application + rerun
   deferred to Sprint 17), the `compose-not-apply` decision and its
   rationale (cross-layer injection points + rule-vs-data validation
   needs live stage JSON), the test-count delta, and a one-line
   next-step recommendation (Sprint 17 — D1 stage hooks + the D2
   pipeline-rerun half).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for the `run_synthetic.py` row in the "New Files in
     This Branch" file map, with the annotation "Sprint 16 — Task D2
     (Stage-A half) — concept-loop driver + `CONDITION_SPECS` condition
     matrix + deterministic seeded planner; populates the variant
     catalog. Rule application (`mutator.apply_*`) + pipeline rerun
     (s03→s07) deferred to Sprint 17 (gated on D1 stage hooks)."
   - Prepend a new "After Sprint 16 — …" entry to the Sprint History
     section.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md)
   or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). §5 Phase D
   and §6 Generation Conditions already cover the deliverable at the
   framing layer. (If a reviewer wants the D2 row split into "Stage-A
   half done / Stage-B half pending" in the §5 status table, that's a
   one-cell annotation — but defer it to keep the framing docs stable
   unless explicitly asked.)

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥556 passed, 1 skipped** (Sprint 12's `new_param`
brace-audit skip is still the only skip). Zero failures. The skip count
must stay at exactly 1 — any new skip is a regression.

End-to-end smoke (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -c @"
import json, tempfile, pathlib
from synthetic.run_synthetic import run_concept
from synthetic.variant_catalog import read_catalog_entry
from synthetic.layer_l1 import apply_synonym_label

class Stub:
    def __init__(self, responses): self._r = list(responses)
    def complete(self, prompt): return self._r.pop(0)

stage = {
    'OEB020aa': {
        'parent_key': 'OEB020\$',
        'parameters': {'B': {'label': 'TIPO DE TERRENO',
            'values': [{'label': 'a', 'value': 'Normal'},
                       {'label': 'b', 'value': 'Rocoso'}]}},
        'text_variables': {'K': '\"normal\" * (%B=a) + \"rocoso\" * (%B=b)'},
        'resumen': 'Canalizacion para terreno normal',
        'texto':   'Canalizacion para terreno \$K, incluso \$N',
    },
}
# one synonym_label payload per axis (single_L1 is exhaustive over B)
client = Stub([
    json.dumps({'synonyms': [{'original': 'Normal', 'new': 'Estandar'}]}),
])
with tempfile.TemporaryDirectory() as d:
    entry, path = run_concept(
        stage, 'OEB020aa', ['single_L1_synonym_label'], client,
        out_dir=pathlib.Path(d), seed=7,
    )
    print('wrote:', path.name)
    print('variants:', len(entry.variants))
    print('round-trip ok:', read_catalog_entry(path) == entry)
    rule = entry.variants[0].rules[0]
    print('rule:', rule)
    apply_synonym_label(stage, 'OEB020aa', rule)  # must not raise
    print('apply_synonym_label accepted the emitted rule')
"@
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/run_synthetic.py
new file:   tests/synthetic/test_run_synthetic.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_16.md (this file)
```

Nothing under `data/synthetic/variants/` is committed (populated at run
time, not at sprint-build time). Nothing under `configs/`, no notebooks,
no edits to existing `src/synthetic/` modules besides the two doc files.

---

## Design notes worth committing to memory

- **Sprint 16 closes Stage A, not Stage B.** The variant catalog is the
  decoupling seam (C4: "pipeline reruns *consume* this catalog"). The
  orchestrator's Sprint-16 job is to *populate* the catalog: propose,
  emit, compose, persist. *Applying* the rules and *rerunning* the
  pipeline is Stage B — it's interleaved across the four injection
  points (PD/L1 → s03 → L2 → s04 → L3 → s05), needs live stage JSON for
  rule-vs-data validation, and depends on D1 stage hooks (s03/s04/s05
  are notebooks, not functions). Forcing both halves into one sprint
  would either pull notebook execution into pytest (breaking the
  no-live-IO discipline) or ship an untested rerun path.
- **`compose_rules` yes, `mutator.apply_*` no.** Composition is
  state-blind rule-vs-rule validation (same-target dedup,
  layer-dependency conflict, PD→L1→L2→L3 ordering). It belongs in
  Stage A so the catalog records *admissible, ordered* rules and the
  rerun applies them without re-deciding compatibility. Application is
  rule-vs-data — it needs the live JSON and is inseparable from the
  stage it injects into.
- **Condition matrix is a Python constant, derived from the enum.**
  `CONDITION_SPECS` is built by `_build_condition_specs()` off
  `ModificationType`, so a future type surfaces its `single_*`
  condition automatically. YAML (`variant_budgets.yaml`) is for Phase F
  *budgets*, not the structural condition→type mapping. Same call
  Sprint 11 made for `COMPATIBILITY_MATRIX` and Sprint 12 for
  `PROMPT_FILENAMES`.
- **Determinism is threaded, not global.** Every sample goes through a
  passed `random.Random(seed)`; `_seed_for` derives a stable
  per-concept seed via `sha256` (not the per-process-salted `hash()`).
  The same concept samples the same variants regardless of batch
  composition — critical for reproducible regeneration and for the
  Data-in-Brief methodology section. Same PYTHONHASHSEED trap Sprint
  6.5 and Sprint 15 pinned.
- **`single_*` exhaustive, `stacked_*` / `mix` sampled, one plan each.**
  Exhaustive singles give clean per-type isolation slices (one variant
  per eligible target). Stacked/mix sample one depth-N variant per
  condition per concept; *how many* variants per condition (budgets) is
  Phase F tuning, not a Stage-A structural decision.
- **A fully-skipped variant still leaves a trace.** No `VariantRecord`,
  but the `skipped` log and per-attempt `provenance` records land in
  the catalog. Phase E1's metadata pipeline reads these to compute
  per-type acceptance rates without re-querying the LLM.
- **Provenance is per-attempt, parallel to the catalog's `skipped` +
  `variants` in attempt order.** One `ProvenanceRecord` per LLM
  round-trip captures the rendered prompt, raw responses, and either
  the validated payload (success) or the skip (failure) — the full
  diagnostic trail Sprint 15's `VariantCatalogEntry` was shaped to hold.
- **The orchestrator takes an `LLMClient`, never constructs one.** A3
  (model choice) is still open; the concrete transport is injected.
  Tests use the `_StubLLMClient` queue. Same Sprint 13/14 contract.
- **No `mutator` import is a scope tripwire.** A test audits that
  `run_synthetic` doesn't import `mutator`. The day someone wires
  application into the orchestrator, that test fails and forces the
  D1/Stage-B conversation rather than silently coupling Stage A to the
  rerun.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase D`](../RESEARCH_PROTOCOL.md) — D1
  (stage hooks), D2 (orchestrator), D3 (cache hygiene). Sprint 16 is
  the Stage-A half of D2; D1 + the Stage-B half are Sprint 17.
- [`../RESEARCH_PROTOCOL.md §6 Generation Conditions`](../RESEARCH_PROTOCOL.md)
  — the condition recipe table `CONDITION_SPECS` encodes.
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — Mutation
  Architecture (the four injection points), Design Decisions (variant
  catalog decoupling, variant ID format `{original_key}_syn_v{n}`,
  deterministic temperature), Generation Conditions, Stage-Hook
  Integration Note (the `run_synthetic.py` D2 description), and the
  `run_synthetic.py` ❌ → ✅ row to flip.
- [`SPRINT_15.md`](SPRINT_15.md) — `slot_extractor.{enumerate_targets,
  extract_slots, concept_resumen}`, `rule_emitter.{emit_rules,
  EmissionResult}`, `variant_catalog.{VariantCatalogEntry,
  VariantRecord, ProvenanceRecord, write_catalog_entry,
  read_catalog_entry}` — the primitives the orchestrator composes.
- [`SPRINT_14.md`](SPRINT_14.md) — `variant_proposer.{propose_variant,
  VariantProposal, EXPECTED_SLOTS, _render_prompt}`. The orchestrator
  ships slots through `propose_variant` and re-uses `_render_prompt`
  for provenance.
- [`SPRINT_13.md`](SPRINT_13.md) — `llm_proposer.LLMClient`. Injected,
  not constructed.
- [`SPRINT_12.md`](SPRINT_12.md) — `prompts.load_prompt`. The default
  `prompt_loader`.
- [`SPRINT_11.md`](SPRINT_11.md) — `composition.compose_rules`. Called
  per variant to validate stackability + fix apply order + log skips.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py)
  — `Modification`, `ModificationType`, `Layer`, `TYPE_TO_LAYER`.

---

## Non-goals reminder

If you find yourself importing `mutator` or calling `apply_l1` /
`apply_l2` / `apply_l3` / `apply_new_param` — **stop**. Sprint 16
populates the catalog; rule application is interleaved with the stage
rerun (Sprint 17, gated on D1).

If you find yourself executing a notebook (`papermill`, `nbconvert`,
`jupyter`) or reading real `data/intermediate/*.json` off disk —
**stop**. That's the Stage-B rerun (Sprint 17). Sprint 16 takes an
in-memory stage-JSON dict and a stub `LLMClient`.

If you find yourself authoring or loading
`configs/synthetic/variant_budgets.yaml` — **stop**. Per-concept
budgets are Phase F. Sprint 16 generates one plan per single-target /
per stacked-condition.

If you find yourself wiring a concrete LLM transport (Ollama,
Anthropic, OpenAI) into the orchestrator — **stop**. A3's model choice
is still open; the client is injected.

If you find yourself parsing the PD `var_definition` / `template_patch`
strings into rule fields — **stop**. Sprint 15's partial PD lift
stands; the orchestrator catalogs the raw `metadata.*` strings as
emitted. The full parse lands when the Stage-B rerun needs it.

If you find yourself building the metadata join (binding items to their
`modifications` via `(original_key, variante_id)`) — **stop**. That's
E1, and it needs the raw items the Stage-B rerun produces (Sprint 18+).

If you find yourself reaching for the global `random` module or
iterating a `set` for ordering — **stop**. Thread the passed
`random.Random` and sort by `.value`. PYTHONHASHSEED determinism is a
pinned contract.
