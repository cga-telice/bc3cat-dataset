"""Three-layer injection harness — pure dispatchers over stage JSONs.

Public API matches `CLAUDE_SYNTHETIC.md` "Stage-Hook Integration Note":
`apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`. Each function
deep-copies its input stage JSON, validates the rule(s)' declared layer,
and routes through `_DISPATCH` to the matching per-type stub.

All 12 stubs currently raise `NotImplementedError`. Real bodies arrive in
Phase B (B1–B4) and will be physically relocated to `layer_l1.py` /
`_l2.py` / `_l3.py` / `_pd.py`; the dispatcher's surface is the stable
boundary.
"""

from __future__ import annotations

import copy
from typing import Any, Callable

from .taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER


_StubResult = tuple[dict, list[Modification]]


def _stub_synonym_label(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.SYNONYM_LABEL.value} mutator not yet implemented"
    )


def _stub_num_to_text(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.NUM_TO_TEXT.value} mutator not yet implemented"
    )


def _stub_unit_conversion(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.UNIT_CONVERSION.value} mutator not yet implemented"
    )


def _stub_unit_expansion(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.UNIT_EXPANSION.value} mutator not yet implemented"
    )


def _stub_abbrev_expansion(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.ABBREV_EXPANSION.value} mutator not yet implemented"
    )


def _stub_code_expansion(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.CODE_EXPANSION.value} mutator not yet implemented"
    )


def _stub_paraphrase(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.PARAPHRASE.value} mutator not yet implemented"
    )


def _stub_expansion(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.EXPANSION.value} mutator not yet implemented"
    )


def _stub_compression(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.COMPRESSION.value} mutator not yet implemented"
    )


def _stub_omission(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.OMISSION.value} mutator not yet implemented"
    )


def _stub_reorder(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.REORDER.value} mutator not yet implemented"
    )


def _stub_new_param(stage_json: dict, concept_key: str, rule: dict) -> _StubResult:
    raise NotImplementedError(
        f"Phase B: {ModificationType.NEW_PARAM.value} mutator not yet implemented"
    )


_DISPATCH: dict[ModificationType, Callable[[dict, str, dict], _StubResult]] = {
    ModificationType.SYNONYM_LABEL: _stub_synonym_label,
    ModificationType.NUM_TO_TEXT: _stub_num_to_text,
    ModificationType.UNIT_CONVERSION: _stub_unit_conversion,
    ModificationType.UNIT_EXPANSION: _stub_unit_expansion,
    ModificationType.ABBREV_EXPANSION: _stub_abbrev_expansion,
    ModificationType.CODE_EXPANSION: _stub_code_expansion,
    ModificationType.PARAPHRASE: _stub_paraphrase,
    ModificationType.EXPANSION: _stub_expansion,
    ModificationType.COMPRESSION: _stub_compression,
    ModificationType.OMISSION: _stub_omission,
    ModificationType.REORDER: _stub_reorder,
    ModificationType.NEW_PARAM: _stub_new_param,
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
