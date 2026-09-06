"""Stage B (Phase D Task D2): apply a variant's rules, then re-run the pipeline.

Stage A (`run_synthetic.py`) proposes, composes, and *catalogs* admissible,
ordered rule sets per variant — it applies nothing. Stage B is the join: read a
`VariantCatalogEntry`, apply each variant's rules to the single concept, and
regenerate the mutated raw items through the D1 stage hooks.

**One parent-level injection, not four.** Every mutator (`layer_l1` / `layer_l2`
/ `layer_l3` / `layer_pd`) indexes the same concept-keyed *stage-2* record
(`stage_json[concept_key][...]`); none can consume a leaf-keyed `run_stage3+`
output (no `concept_key`, no raw formulas/templates left to match). So Stage B
applies PD -> L1 -> L2 -> L3 to that one record (in the composed order Stage A
already pinned), then calls `run_stages_3_to_7` once. No interleaving.

This module imports `mutator`, `stage_runners`, `variant_catalog`, `taxonomy`,
and `utils.config` — and deliberately **not** `run_synthetic` (the Stage-A
half stays mutator-free; this is the Stage-A/Stage-B seam guard).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from . import mutator
from .stage_runners import run_stages_3_to_7
from .taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER
from .variant_catalog import VariantCatalogEntry, VariantRecord, read_catalog_entry
from utils import config

__all__ = [
    "MaterializedVariant",
    "apply_variant_rules",
    "materialize_variant",
    "materialize_catalog_entry",
    "run_stage_b",
]

logger = logging.getLogger(__name__)


def _identity(stage_json: dict) -> dict:
    """Default `pre_rerun` adapter: pass the mutated concept through unchanged."""
    return stage_json

# PD before L1 before L2 before L3 — every rule is a syntactic edit to the
# concept's pre-expansion definition; this is the composed order Stage A pinned.
_LAYER_ORDER = (
    Layer.PARAM_DEFINITION,
    Layer.PARAM_VALUE,
    Layer.TEXT_VARIABLE,
    Layer.TEMPLATE,
)


@dataclass(frozen=True)
class MaterializedVariant:
    """One materialised variant: its applied modifications + regenerated items."""

    variant_id: str
    condition: str
    concept_key: str
    modification_types: tuple[ModificationType, ...]
    modifications: tuple[Modification, ...]
    items: dict


def apply_variant_rules(
    stage2_concept: dict,
    concept_key: str,
    rules: Sequence[dict],
) -> tuple[dict, list[Modification]]:
    """Apply a variant's pre-composed rules to a single-concept stage-2 dict.

    Partitions `rules` by layer (`TYPE_TO_LAYER`), then threads the concept dict
    through PD -> L1 -> L2 -> L3, preserving the catalog's intra-layer order.
    Pure: the `mutator.apply_*` calls deep-copy, so `stage2_concept` is never
    mutated. A rule that fails to apply is skipped-and-logged (Stage B consumes
    the mutators as-is; it does not patch them).
    """
    buckets: dict[Layer, list[dict]] = {layer: [] for layer in _LAYER_ORDER}
    for rule in rules:
        layer = TYPE_TO_LAYER[ModificationType(rule["type"])]
        buckets[layer].append(rule)

    out = stage2_concept
    log: list[Modification] = []
    for layer in _LAYER_ORDER:
        for rule in buckets[layer]:
            try:
                out, sub_log = _apply_one(out, concept_key, layer, rule)
            except (KeyError, ValueError, TypeError) as exc:
                logger.warning(
                    "stage_b: skipping %s rule on concept %s: %s",
                    rule.get("type"), concept_key, exc,
                )
                continue
            log.extend(sub_log)
    return out, log


def _apply_one(
    stage_json: dict, concept_key: str, layer: Layer, rule: dict,
) -> tuple[dict, list[Modification]]:
    if layer is Layer.PARAM_DEFINITION:
        return mutator.apply_new_param(stage_json, concept_key, rule)
    if layer is Layer.PARAM_VALUE:
        return mutator.apply_l1(stage_json, concept_key, [rule])
    if layer is Layer.TEXT_VARIABLE:
        return mutator.apply_l2(stage_json, concept_key, [rule])
    return mutator.apply_l3(stage_json, concept_key, [rule])


def materialize_variant(
    stage2_json: dict,
    concept_key: str,
    variant: VariantRecord,
    *,
    pre_rerun: Callable[[dict], dict] = _identity,
) -> MaterializedVariant:
    """Slice the concept, apply its rules, re-run s03->s07, wrap the result.

    `stage2_json` is left unchanged (the slice shares references but every
    mutator + every stage runner deep-copies before writing).

    `pre_rerun` is applied to the mutated concept dict immediately before the
    s03->s07 rerun (default: identity, so existing callers are unaffected). The
    L2 representation adapter (`l2_repr.formula_to_list`) plugs in here so that
    `LIST_plain` text-variables, which are mutated in formula form, are restored
    to the positional-list shape the rerun's s05 indexer needs.
    """
    concept_slice = {concept_key: stage2_json[concept_key]}
    mutated, mods = apply_variant_rules(concept_slice, concept_key, variant.rules)
    items = run_stages_3_to_7(pre_rerun(mutated))
    return MaterializedVariant(
        variant_id=_variant_id(variant),
        condition=variant.condition,
        concept_key=concept_key,
        modification_types=tuple(m.type for m in mods),
        modifications=tuple(mods),
        items=items,
    )


def materialize_variant_bc3param(stage2_json, concept_key, variant):
    """Materialise a variant via the bc3param backend (Phase 1 seam swap).

    Ignores the stage2_json concept body: bc3param re-parses the concept from the
    raw ~P (clean) and applies the variant's rules as Family edits. Rules whose
    target cannot be edited are skipped-and-logged (as the legacy path does), so
    the modification log — and thus the sidecar — is built only from the rules
    that actually applied.
    """
    from .bc3param_backend import modifications_from_rules, run_variant_logged

    items, applied = run_variant_logged(concept_key, variant.rules)
    mods = tuple(modifications_from_rules(applied))
    types = tuple(m.type for m in mods)
    return MaterializedVariant(
        variant_id=_variant_id(variant),
        condition=variant.condition,
        concept_key=concept_key,
        modification_types=types,
        modifications=mods,
        items=items,
    )


def materialize_catalog_entry(
    stage2_json: dict,
    entry: VariantCatalogEntry,
    *,
    out_dir: Path,
    pre_rerun: Callable[[dict], dict] = _identity,
) -> list[Path]:
    """Materialise every variant of one catalog entry; one JSON per variant.

    Writes `out_dir/{concept_key}/{variant_id}.json` atomically (`.tmp` rename,
    same discipline as `variant_catalog.write_catalog_entry`). The payload
    carries the variant metadata, the modification log, and the regenerated
    items. `pre_rerun` is forwarded to `materialize_variant` (see there).
    """
    concept_dir = Path(out_dir) / entry.concept_key
    concept_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for variant in entry.variants:
        mv = materialize_variant(
            stage2_json, entry.concept_key, variant, pre_rerun=pre_rerun,
        )
        final = concept_dir / f"{mv.variant_id}.json"
        tmp = concept_dir / f".{mv.variant_id}.json.tmp"
        tmp.write_text(
            json.dumps(_materialized_to_dict(mv), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp, final)
        paths.append(final)
    return paths


def run_stage_b(
    stage2_json: dict,
    variants_dir: Path,
    *,
    out_dir: Optional[Path] = None,
) -> list[Path]:
    """Read every catalog entry under `variants_dir` and materialise each.

    Default `out_dir` is `config.SYNTHETIC_INTERMEDIATE_DIR`.
    """
    target = config.SYNTHETIC_INTERMEDIATE_DIR if out_dir is None else Path(out_dir)
    paths: list[Path] = []
    for entry_path in sorted(Path(variants_dir).glob("*.json")):
        entry = read_catalog_entry(entry_path)
        paths.extend(materialize_catalog_entry(stage2_json, entry, out_dir=target))
    return paths


# ----- helpers ----------------------------------------------------------

def _variant_id(variant: VariantRecord) -> str:
    """Deterministic filesystem-safe id from the variant's identity.

    `VariantRecord` carries no id (the catalog round-trip drops `VariantPlan`'s),
    so derive one: condition tag + a short hash of (condition, targets, rules).
    Distinct variants -> distinct ids.
    """
    digest = hashlib.sha1(
        repr((variant.condition, variant.target_id_repr, variant.rules)).encode("utf-8")
    ).hexdigest()[:10]
    return f"{variant.condition}_{digest}"


def _materialized_to_dict(mv: MaterializedVariant) -> dict:
    return {
        "variant_id": mv.variant_id,
        "condition": mv.condition,
        "concept_key": mv.concept_key,
        "modification_types": [t.value for t in mv.modification_types],
        "modifications": [m.to_dict() for m in mv.modifications],
        "items": mv.items,
    }
