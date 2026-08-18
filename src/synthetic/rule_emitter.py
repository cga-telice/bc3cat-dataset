"""Payload -> Phase-B rule lift. Bridges Sprint 14's
`VariantProposal.payload` (the validated LLM dict) and the Phase-B
mutators' rule schemas (the dicts `layer_*.apply_*` consume).

Per-type dispatch returns one or more rule dicts plus a sibling
`unmatched` list for LLM payload entries that don't cross-reference
to a known parameter value / variable / field.

Does NOT own:

  * applying the rules — `mutator.apply_*` is Phase B (already shipped);
  * `new_param` `text_variable` / `template_patches` parsing — those
    optional fields stay as raw strings under `metadata.*` in the
    emitted rule; Sprint 16 widens.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Any

from .taxonomy import ModificationType


@dataclass(frozen=True)
class EmissionResult:
    rules: tuple[dict, ...]
    unmatched: tuple[dict, ...]


def emit_rules(
    payload: dict,
    modification_type: ModificationType,
    *,
    target_id: Any,
    stage_json: dict,
    concept_key: str,
) -> EmissionResult:
    if modification_type in _L1_TYPES:
        return _emit_l1(
            payload, modification_type, target_id, stage_json, concept_key,
        )
    if modification_type in _L2_TYPES:
        return _emit_l2(payload, modification_type, target_id)
    if modification_type is ModificationType.OMISSION:
        return _emit_l3_omission(payload, target_id)
    if modification_type is ModificationType.REORDER:
        return _emit_l3_reorder(payload, target_id)
    if modification_type is ModificationType.TEMPLATE_PARAPHRASE:
        return _emit_l3_template_paraphrase(payload, target_id)
    if modification_type is ModificationType.NEW_PARAM:
        return _emit_new_param(payload, stage_json, concept_key)
    raise ValueError(f"no_emitter_for_type: {modification_type.value!r}")


# ---- L1 ----------------------------------------------------------------

_L1_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})
_L1_LIST_KEY: dict[ModificationType, str] = {
    ModificationType.SYNONYM_LABEL:    "synonyms",
    ModificationType.NUM_TO_TEXT:      "numerals",
    ModificationType.UNIT_CONVERSION:  "synonyms",
    ModificationType.UNIT_EXPANSION:   "synonyms",
    ModificationType.ABBREV_EXPANSION: "synonyms",
    ModificationType.CODE_EXPANSION:   "synonyms",
}


def _emit_l1(
    payload: dict,
    mtype: ModificationType,
    target_id: Any,
    stage_json: dict,
    concept_key: str,
) -> EmissionResult:
    param = target_id
    values = stage_json[concept_key]["parameters"][param]["values"]
    by_value = {v["value"]: v["label"] for v in values}
    entries = payload.get(_L1_LIST_KEY[mtype], [])
    rules: list[dict] = []
    unmatched: list[dict] = []
    for entry in entries:
        original = entry.get("original")
        if original not in by_value:
            unmatched.append(entry)
            continue
        rules.append({
            "type": mtype.value,
            "param": param,
            "value": by_value[original],
            "original": original,
            "new": entry["new"],
        })
    return EmissionResult(tuple(rules), tuple(unmatched))


# ---- L2 ----------------------------------------------------------------

_L2_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})


def _emit_l2(
    payload: dict, mtype: ModificationType, target_id: Any,
) -> EmissionResult:
    var_key, condition = target_id
    rule = {
        "type": mtype.value,
        "var": var_key,
        "condition": condition,
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


# ---- L3 ----------------------------------------------------------------

def _emit_l3_omission(payload: dict, target_id: Any) -> EmissionResult:
    field, _var_token = target_id
    rule = {
        "type": ModificationType.OMISSION.value,
        "field": field,
        "original": payload["original"],
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


def _emit_l3_reorder(payload: dict, target_id: Any) -> EmissionResult:
    field = target_id
    rule = {
        "type": ModificationType.REORDER.value,
        "field": field,
        "original": payload["original"],
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


def _emit_l3_template_paraphrase(payload: dict, target_id: Any) -> EmissionResult:
    """Sprint 36 emitter. Same rule shape as reorder — the mutator's
    `_replace_substring` finds `original` in `field` and swaps in `new`.
    Placeholder-preservation was already enforced by the variant proposer's
    validator; nothing more to check here."""
    field = target_id
    rule = {
        "type": ModificationType.TEMPLATE_PARAPHRASE.value,
        "field": field,
        "original": payload["original"],
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


# ---- PD ----------------------------------------------------------------

def _emit_new_param(
    payload: dict, stage_json: dict, concept_key: str,
) -> EmissionResult:
    new_letter = _allocate_axis_key(stage_json, concept_key)
    rule = {
        "type": ModificationType.NEW_PARAM.value,
        "param": new_letter,
        "label": payload["new_axis_label"],
        "values": [dict(v) for v in payload["values"]],
        "metadata": {
            "var_definition": payload["var_definition"],
            "template_patch": payload["template_patch"],
        },
    }
    return EmissionResult((rule,), ())


def _allocate_axis_key(stage_json: dict, concept_key: str) -> str:
    used = set(stage_json[concept_key].get("parameters", {}).keys())
    for letter in string.ascii_uppercase:
        if letter not in used:
            return letter
    raise ValueError("no_free_axis_letter")
