"""Three-layer injection harness — pure dispatchers over stage JSONs.

Public API matches `CLAUDE_SYNTHETIC.md` "Stage-Hook Integration Note":
`apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`. Each function
deep-copies its input stage JSON, validates the rule(s)' declared layer,
and routes through `_DISPATCH` to the matching per-type mutator.

All 12 (6 L1 + 3 L2 + 2 L3 + 1 PD) mutators live; dispatcher fully
promoted from stubs.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from .layer_l1 import (
    apply_abbrev_expansion,
    apply_code_expansion,
    apply_num_to_text,
    apply_synonym_label,
    apply_unit_conversion,
    apply_unit_expansion,
)
from .layer_l2 import (
    apply_compression,
    apply_expansion,
    apply_paraphrase,
)
from .layer_l3 import (
    apply_omission,
    apply_reorder,
    apply_template_paraphrase,
)
from .layer_pd import apply_new_param as _layer_pd_apply_new_param
from .taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER


_StubResult = tuple[dict, list[Modification]]


_DISPATCH: dict[ModificationType, Callable[[dict, str, dict], _StubResult]] = {
    ModificationType.SYNONYM_LABEL: apply_synonym_label,
    ModificationType.NUM_TO_TEXT: apply_num_to_text,
    ModificationType.UNIT_CONVERSION: apply_unit_conversion,
    ModificationType.UNIT_EXPANSION: apply_unit_expansion,
    ModificationType.ABBREV_EXPANSION: apply_abbrev_expansion,
    ModificationType.CODE_EXPANSION: apply_code_expansion,
    ModificationType.PARAPHRASE: apply_paraphrase,
    ModificationType.EXPANSION: apply_expansion,
    ModificationType.COMPRESSION: apply_compression,
    ModificationType.OMISSION: apply_omission,
    ModificationType.REORDER: apply_reorder,
    ModificationType.TEMPLATE_PARAPHRASE: apply_template_paraphrase,
    ModificationType.NEW_PARAM: _layer_pd_apply_new_param,
}


def _resolve_type(rule: dict[str, Any]) -> ModificationType:
    raw = rule["type"]
    try:
        return ModificationType(raw)
    except ValueError as exc:
        raise ValueError(f"unknown modification type: {raw!r}") from exc


def _gate_layer(mtype: ModificationType, expected: Layer) -> None:
    actual = TYPE_TO_LAYER[mtype]
    if actual is not expected:
        raise ValueError(
            f"rule type {mtype.value!r} is a {actual.value!r} mutation, "
            f"not {expected.value!r}"
        )


def _apply_rules(
    stage_json: dict,
    concept_key: str,
    rules: list[dict],
    expected_layer: Layer,
) -> _StubResult:
    out = copy.deepcopy(stage_json)
    log: list[Modification] = []
    for rule in rules:
        mtype = _resolve_type(rule)
        _gate_layer(mtype, expected_layer)
        out, sub_log = _DISPATCH[mtype](out, concept_key, rule)
        log.extend(sub_log)
    return out, log


def apply_l1(
    stage2_json: dict,
    concept_key: str,
    rules: list[dict],
) -> _StubResult:
    """Apply L1 (`param_value`) mutations to a stage-2 JSON dict."""
    return _apply_rules(stage2_json, concept_key, rules, Layer.PARAM_VALUE)


def apply_l2(
    stage3_json: dict,
    concept_key: str,
    rules: list[dict],
) -> _StubResult:
    """Apply L2 (`text_variable`) mutations to a stage-3 JSON dict."""
    return _apply_rules(stage3_json, concept_key, rules, Layer.TEXT_VARIABLE)


def apply_l3(
    stage4_json: dict,
    concept_key: str,
    rules: list[dict],
) -> _StubResult:
    """Apply L3 (`template`) mutations to a stage-4 JSON dict."""
    return _apply_rules(stage4_json, concept_key, rules, Layer.TEMPLATE)


def apply_new_param(
    stage2_json: dict,
    concept_key: str,
    rule: dict,
) -> _StubResult:
    """Apply a single `new_param` (PD) mutation to a stage-2 JSON dict."""
    out = copy.deepcopy(stage2_json)
    mtype = _resolve_type(rule)
    _gate_layer(mtype, Layer.PARAM_DEFINITION)
    return _DISPATCH[mtype](out, concept_key, rule)
