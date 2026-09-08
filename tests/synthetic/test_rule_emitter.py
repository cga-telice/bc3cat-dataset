"""Contract tests for `synthetic.rule_emitter`.

Pins per-type rule shapes against the Phase-B `layer_*.apply_*` rule
schemas, plus the L1 cross-reference + unmatched-payload diagnostic
contract.
"""

from __future__ import annotations

import copy
import importlib

import pytest

from synthetic import rule_emitter
from synthetic.rule_emitter import EmissionResult, emit_rules
from synthetic.taxonomy import ModificationType


_L1_TYPES = (
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
)
_L1_LIST_KEY = {
    ModificationType.SYNONYM_LABEL:    "synonyms",
    ModificationType.NUM_TO_TEXT:      "numerals",
    ModificationType.UNIT_CONVERSION:  "synonyms",
    ModificationType.UNIT_EXPANSION:   "synonyms",
    ModificationType.ABBREV_EXPANSION: "synonyms",
    ModificationType.CODE_EXPANSION:   "synonyms",
}
_L2_TYPES = (
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
)


def _stage_with_axis(values=None):
    if values is None:
        values = [
            {"label": "a", "value": "Normal"},
            {"label": "b", "value": "Rocoso"},
        ]
    return {
        "OEB020aa": {
            "parent_key": "OEB020$",
            "parameters": {
                "B": {"label": "TIPO DE TERRENO", "values": values},
            },
            "text_variables": {},
            "resumen": "Canalización",
            "texto": "Canalización $K incluso $N",
        },
    }


# ---- public surface ----------------------------------------------------

def test_module_exposes_public_surface():
    assert callable(rule_emitter.emit_rules)
    assert rule_emitter.EmissionResult is EmissionResult


# ---- L1 ----------------------------------------------------------------

@pytest.mark.parametrize("mtype", _L1_TYPES)
def test_emit_l1_happy_path_per_type(mtype):
    stage = _stage_with_axis()
    list_key = _L1_LIST_KEY[mtype]
    payload = {list_key: [{"original": "Normal", "new": "Estándar"}]}
    result = emit_rules(
        payload, mtype, target_id="B", stage_json=stage,
        concept_key="OEB020aa",
    )
    assert isinstance(result, EmissionResult)
    assert result.unmatched == ()
    assert len(result.rules) == 1
    rule = result.rules[0]
    assert rule == {
        "type": mtype.value,
        "param": "B",
        "value": "a",
        "original": "Normal",
        "new": "Estándar",
    }


def test_emit_l1_emits_one_rule_per_synonyms_entry():
    stage = _stage_with_axis([
        {"label": "a", "value": "Normal"},
        {"label": "b", "value": "Rocoso"},
        {"label": "c", "value": "Bajo vías"},
    ])
    payload = {"synonyms": [
        {"original": "Normal",    "new": "Estándar"},
        {"original": "Rocoso",    "new": "Pétreo"},
        {"original": "Bajo vías", "new": "Bajo ferrocarril"},
    ]}
    result = emit_rules(
        payload, ModificationType.SYNONYM_LABEL,
        target_id="B", stage_json=stage, concept_key="OEB020aa",
    )
    assert len(result.rules) == 3
    assert {r["value"] for r in result.rules} == {"a", "b", "c"}


def test_emit_l1_unmatched_original_rides_in_unmatched_list():
    stage = _stage_with_axis()
    payload = {"synonyms": [
        {"original": "Normal",    "new": "Estándar"},
        {"original": "Stándard",  "new": "Estándar"},  # typo, no match
    ]}
    result = emit_rules(
        payload, ModificationType.SYNONYM_LABEL,
        target_id="B", stage_json=stage, concept_key="OEB020aa",
    )
    assert len(result.rules) == 1
    assert result.rules[0]["original"] == "Normal"
    assert result.unmatched == (
        {"original": "Stándard", "new": "Estándar"},
    )


def test_emit_l1_rule_carries_value_label_not_value_string():
    stage = _stage_with_axis()
    payload = {"synonyms": [{"original": "Normal", "new": "X"}]}
    result = emit_rules(
        payload, ModificationType.SYNONYM_LABEL,
        target_id="B", stage_json=stage, concept_key="OEB020aa",
    )
    assert result.rules[0]["value"] == "a"
    assert result.rules[0]["value"] != "Normal"


def test_emit_l1_empty_list_yields_empty_result():
    stage = _stage_with_axis()
    payload = {"synonyms": []}
    result = emit_rules(
        payload, ModificationType.SYNONYM_LABEL,
        target_id="B", stage_json=stage, concept_key="OEB020aa",
    )
    assert result == EmissionResult((), ())


# ---- L2 ----------------------------------------------------------------

@pytest.mark.parametrize("mtype", _L2_TYPES)
def test_emit_l2_happy_path_per_type(mtype):
    payload = {
        "original": "normal",
        "new": "estándar",
        "preserves_meaning": True,
    }
    result = emit_rules(
        payload, mtype, target_id=("K", "%B=a"),
        stage_json={}, concept_key="OEB020aa",
    )
    assert result.unmatched == ()
    assert result.rules == ({
        "type": mtype.value,
        "var": "K",
        "condition": "%B=a",
        "new": "estándar",
    },)


def test_emit_l2_rule_carries_var_and_condition():
    payload = {"original": "x", "new": "y", "preserves_meaning": True}
    result = emit_rules(
        payload, ModificationType.PARAPHRASE,
        target_id=("Z", "%D=b"), stage_json={}, concept_key="X",
    )
    assert result.rules[0]["var"] == "Z"
    assert result.rules[0]["condition"] == "%D=b"


# ---- L3 ----------------------------------------------------------------

def test_emit_l3_omission_rule_shape():
    payload = {
        "original": "incluso $N por metro",
        "new": "incluso por metro",
        "omitted_var": "$N",
    }
    result = emit_rules(
        payload, ModificationType.OMISSION,
        target_id=("TEXTO", "$N"),
        stage_json={}, concept_key="X",
    )
    assert result.rules == ({
        "type": "omission",
        "field": "TEXTO",
        "original": "incluso $N por metro",
        "new": "incluso por metro",
    },)
    assert result.unmatched == ()


def test_emit_l3_reorder_rule_shape():
    payload = {
        "original": "$A; $N",
        "new": "$N; $A",
        "preserves_meaning": True,
    }
    result = emit_rules(
        payload, ModificationType.REORDER, target_id="TEXTO",
        stage_json={}, concept_key="X",
    )
    assert result.rules == ({
        "type": "reorder",
        "field": "TEXTO",
        "original": "$A; $N",
        "new": "$N; $A",
    },)


# ---- PD new_param ------------------------------------------------------

def _new_param_payload():
    return {
        "new_axis_label": "ACABADO",
        "var_definition": '$P = "pulido" * (%G=a) + "rugoso" * (%G=b)',
        "template_patch": "incluso acabado $P",
        "values": [
            {"label": "a", "value": "pulido"},
            {"label": "b", "value": "rugoso"},
        ],
    }


def test_emit_new_param_allocates_free_axis_letter():
    stage = {
        "X": {
            "parameters": {"A": {}, "B": {}, "C": {}},
            "resumen": "x",
        },
    }
    result = emit_rules(
        _new_param_payload(), ModificationType.NEW_PARAM,
        target_id=None, stage_json=stage, concept_key="X",
    )
    assert result.rules[0]["param"] == "D"


def test_emit_new_param_skips_used_letters_in_order():
    stage = {
        "X": {
            "parameters": {"A": {}, "C": {}, "E": {}},
            "resumen": "x",
        },
    }
    result = emit_rules(
        _new_param_payload(), ModificationType.NEW_PARAM,
        target_id=None, stage_json=stage, concept_key="X",
    )
    assert result.rules[0]["param"] == "B"


def test_emit_new_param_raises_when_all_letters_taken():
    stage = {"X": {
        "parameters": {ch: {} for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
        "resumen": "x",
    }}
    with pytest.raises(ValueError, match="no_free_axis_letter"):
        emit_rules(
            _new_param_payload(), ModificationType.NEW_PARAM,
            target_id=None, stage_json=stage, concept_key="X",
        )


def test_emit_new_param_metadata_carries_raw_strings():
    stage = {"X": {"parameters": {}, "resumen": "x"}}
    payload = _new_param_payload()
    result = emit_rules(
        payload, ModificationType.NEW_PARAM,
        target_id=None, stage_json=stage, concept_key="X",
    )
    rule = result.rules[0]
    assert rule["metadata"]["var_definition"] == payload["var_definition"]
    assert rule["metadata"]["template_patch"] == payload["template_patch"]


def test_emit_new_param_values_passes_through():
    stage = {"X": {"parameters": {}, "resumen": "x"}}
    payload = _new_param_payload()
    result = emit_rules(
        payload, ModificationType.NEW_PARAM,
        target_id=None, stage_json=stage, concept_key="X",
    )
    rule = result.rules[0]
    assert rule["label"] == "ACABADO"
    assert rule["values"] == payload["values"]
    # Ensure it's a copy — mutating the rule must not bleed into payload.
    rule["values"][0]["label"] = "X"
    assert payload["values"][0]["label"] == "a"


# ---- contract invariants ----------------------------------------------

def test_emission_result_is_frozen():
    er = EmissionResult((), ())
    with pytest.raises(Exception):  # FrozenInstanceError
        er.rules = ()  # type: ignore[misc]


def test_emit_rules_dispatches_per_type_no_raise_on_payload_shape():
    """Smoke-test the dispatcher across every `ModificationType`. Uses
    minimally-conformant payloads per type — the rule emitter does not
    re-validate the payload shape (that's C3's job); it only consumes
    the fields it lifts.
    """
    stage = copy.deepcopy(_stage_with_axis())
    # add a second axis with explicit values so PD can allocate "C"
    stage["OEB020aa"]["parameters"]["D"] = {
        "label": "PROFUNDIDAD",
        "values": [{"label": "a", "value": "Hasta 1 m"}],
    }
    payloads_and_targets = {
        ModificationType.SYNONYM_LABEL: (
            {"synonyms": [{"original": "Normal", "new": "X"}]}, "B",
        ),
        ModificationType.NUM_TO_TEXT: (
            {"numerals": [{"original": "Normal", "new": "X"}]}, "B",
        ),
        ModificationType.UNIT_CONVERSION: (
            {"synonyms": [{"original": "Normal", "new": "X"}]}, "B",
        ),
        ModificationType.UNIT_EXPANSION: (
            {"synonyms": [{"original": "Normal", "new": "X"}]}, "B",
        ),
        ModificationType.ABBREV_EXPANSION: (
            {"synonyms": [{"original": "Normal", "new": "X"}]}, "B",
        ),
        ModificationType.CODE_EXPANSION: (
            {"synonyms": [{"original": "Normal", "new": "X"}]}, "B",
        ),
        ModificationType.PARAPHRASE: (
            {"original": "x", "new": "y", "preserves_meaning": True},
            ("K", "%B=a"),
        ),
        ModificationType.EXPANSION: (
            {"original": "x", "new": "y", "preserves_meaning": True},
            ("K", "%B=a"),
        ),
        ModificationType.COMPRESSION: (
            {"original": "x", "new": "y", "preserves_meaning": True},
            ("K", "%B=a"),
        ),
        ModificationType.OMISSION: (
            {"original": "x", "new": "y", "omitted_var": "$N"},
            ("TEXTO", "$N"),
        ),
        ModificationType.REORDER: (
            {"original": "x", "new": "y", "preserves_meaning": True},
            "TEXTO",
        ),
        ModificationType.NEW_PARAM: (
            _new_param_payload(), None,
        ),
    }
    for mtype, (payload, target_id) in payloads_and_targets.items():
        result = emit_rules(
            payload, mtype, target_id=target_id,
            stage_json=stage, concept_key="OEB020aa",
        )
        assert isinstance(result, EmissionResult), f"failed: {mtype!r}"
        # Every dispatch should produce at least one rule for these
        # minimally-conformant payloads (L1 because the `original` cross-
        # references; L2/L3/PD because emission is unconditional).
        assert result.rules, f"empty rules for {mtype!r}"


# ---- import-time safety ------------------------------------------------

def test_module_has_no_side_effects_at_import():
    importlib.reload(rule_emitter)
    assert callable(rule_emitter.emit_rules)
