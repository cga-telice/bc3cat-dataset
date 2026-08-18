"""Contract suite for the L1 `param_value` mutators (Sprint 07)."""

import copy
import json

import pytest

from synthetic.layer_l1 import (
    _replace_value,
    apply_abbrev_expansion,
    apply_code_expansion,
    apply_num_to_text,
    apply_synonym_label,
    apply_unit_conversion,
    apply_unit_expansion,
)
from synthetic.mutator import apply_l1
from synthetic.taxonomy import Layer, Modification, ModificationType


@pytest.fixture
def oeb020_stage2():
    return {
        "OEB020$": {
            "concept": "CANALIZACIÓN HORMIGONADA",
            "parameters": {
                "A": {
                    "label": "Nº TUBOS",
                    "values": [
                        {"label": "a", "value": "1"},
                        {"label": "b", "value": "2"},
                        {"label": "c", "value": "3"},
                    ],
                },
                "B": {
                    "label": "TIPO DE TERRENO",
                    "values": [
                        {"label": "a", "value": "Normal"},
                        {"label": "b", "value": "Bajo vías"},
                        {"label": "c", "value": "Rocoso"},
                    ],
                },
                "C": {
                    "label": "DIÁMETRO",
                    "values": [
                        {"label": "a", "value": "110 mm"},
                        {"label": "b", "value": "160 mm"},
                    ],
                },
                "D": {
                    "label": "MATERIAL",
                    "values": [
                        {"label": "a", "value": "PVC"},
                        {"label": "b", "value": "PEAD"},
                    ],
                },
                "E": {
                    "label": "CALIDAD HORMIGÓN",
                    "values": [
                        {"label": "a", "value": "HE-20"},
                        {"label": "b", "value": "HE-25"},
                    ],
                },
            },
            "text_variables": {},
            "resumen": "PLACEHOLDER",
            "texto": "PLACEHOLDER",
        }
    }


_HAPPY_PATH_CASES = [
    pytest.param(
        apply_synonym_label,
        ModificationType.SYNONYM_LABEL,
        "B", "a", "Normal", "Estándar",
        id="synonym_label",
    ),
    pytest.param(
        apply_num_to_text,
        ModificationType.NUM_TO_TEXT,
        "A", "b", "2", "dos",
        id="num_to_text",
    ),
    pytest.param(
        apply_unit_conversion,
        ModificationType.UNIT_CONVERSION,
        "C", "a", "110 mm", "11 cm",
        id="unit_conversion",
    ),
    pytest.param(
        apply_unit_expansion,
        ModificationType.UNIT_EXPANSION,
        "C", "b", "160 mm", "160 milímetros",
        id="unit_expansion",
    ),
    pytest.param(
        apply_abbrev_expansion,
        ModificationType.ABBREV_EXPANSION,
        "D", "a", "PVC", "policloruro de vinilo",
        id="abbrev_expansion",
    ),
    pytest.param(
        apply_code_expansion,
        ModificationType.CODE_EXPANSION,
        "E", "a", "HE-20", "hormigón estructural tipo 20",
        id="code_expansion",
    ),
]


@pytest.mark.parametrize(
    "wrapper, mtype, param, value_label, expected_original, new_value",
    _HAPPY_PATH_CASES,
)
def test_happy_path_per_type(
    oeb020_stage2, wrapper, mtype, param, value_label, expected_original, new_value
):
    pre_axis_len = len(oeb020_stage2["OEB020$"]["parameters"][param]["values"])
    siblings_before = [
        copy.deepcopy(entry)
        for entry in oeb020_stage2["OEB020$"]["parameters"][param]["values"]
        if entry["label"] != value_label
    ]

    rule = {"type": mtype.value, "param": param, "value": value_label, "new": new_value}
    out, log = wrapper(oeb020_stage2, "OEB020$", rule)

    axis_values = out["OEB020$"]["parameters"][param]["values"]
    assert len(axis_values) == pre_axis_len

    target = next(e for e in axis_values if e["label"] == value_label)
    assert target["value"] == new_value

    siblings_after = [e for e in axis_values if e["label"] != value_label]
    assert siblings_after == siblings_before

    assert len(log) == 1
    mod = log[0]
    assert isinstance(mod, Modification)
    assert mod.type is mtype
    assert mod.layer is Layer.PARAM_VALUE
    assert mod.param == param
    assert mod.value == value_label
    assert mod.original == expected_original
    assert mod.new == new_value
    assert mod.status == "applied"


def test_apply_l1_orchestrator_threads_rules(oeb020_stage2):
    snapshot = json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False)
    rules = [
        {"type": "synonym_label", "param": "B", "value": "a", "new": "Estándar"},
        {"type": "num_to_text", "param": "A", "value": "b", "new": "dos"},
        {"type": "unit_conversion", "param": "C", "value": "a", "new": "11 cm"},
    ]

    out, log = apply_l1(oeb020_stage2, "OEB020$", rules)

    assert json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False) == snapshot

    assert len(log) == 3
    assert [mod.type for mod in log] == [
        ModificationType.SYNONYM_LABEL,
        ModificationType.NUM_TO_TEXT,
        ModificationType.UNIT_CONVERSION,
    ]
    assert all(mod.status == "applied" for mod in log)

    params = out["OEB020$"]["parameters"]
    assert params["B"]["values"][0]["value"] == "Estándar"
    assert params["A"]["values"][1]["value"] == "dos"
    assert params["C"]["values"][0]["value"] == "11 cm"


def test_modification_original_sourced_from_stage_json(oeb020_stage2):
    rule = {
        "type": "synonym_label",
        "param": "B",
        "value": "a",
        "original": "WRONG",
        "new": "Estándar",
    }
    _, log = apply_synonym_label(oeb020_stage2, "OEB020$", rule)
    assert log[0].original == "Normal"


def test_missing_concept_key_raises(oeb020_stage2):
    rule = {"type": "synonym_label", "param": "B", "value": "a", "new": "X"}
    with pytest.raises(KeyError, match="NOPE"):
        apply_synonym_label(oeb020_stage2, "NOPE$", rule)


def test_missing_param_raises(oeb020_stage2):
    rule = {"type": "synonym_label", "param": "Z", "value": "a", "new": "X"}
    with pytest.raises(KeyError, match="'Z'"):
        apply_synonym_label(oeb020_stage2, "OEB020$", rule)


def test_missing_value_label_raises(oeb020_stage2):
    rule = {"type": "synonym_label", "param": "B", "value": "zz", "new": "X"}
    with pytest.raises(KeyError, match="'zz'"):
        apply_synonym_label(oeb020_stage2, "OEB020$", rule)


def test_empty_new_raises(oeb020_stage2):
    rule = {"type": "synonym_label", "param": "B", "value": "a", "new": ""}
    with pytest.raises(ValueError, match="synonym_label.*new"):
        apply_synonym_label(oeb020_stage2, "OEB020$", rule)


def test_missing_new_raises(oeb020_stage2):
    rule = {"type": "synonym_label", "param": "B", "value": "a"}
    with pytest.raises(ValueError, match="synonym_label.*new"):
        apply_synonym_label(oeb020_stage2, "OEB020$", rule)


def test_caller_dict_unchanged_after_apply(oeb020_stage2):
    snapshot = json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False)
    apply_l1(
        oeb020_stage2,
        "OEB020$",
        [{"type": "synonym_label", "param": "B", "value": "a", "new": "Estándar"}],
    )
    assert json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False) == snapshot


def test_replace_value_directly(oeb020_stage2):
    rule = {"type": "synonym_label", "param": "B", "value": "a", "new": "Estándar"}
    out, log = _replace_value(
        oeb020_stage2, "OEB020$", rule, ModificationType.SYNONYM_LABEL
    )
    assert out is oeb020_stage2
    assert out["OEB020$"]["parameters"]["B"]["values"][0]["value"] == "Estándar"
    assert log[0].type is ModificationType.SYNONYM_LABEL
    assert log[0].layer is Layer.PARAM_VALUE
