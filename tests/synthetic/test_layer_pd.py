import copy
import json

import pytest

from synthetic.layer_pd import apply_new_param
from synthetic.mutator import apply_new_param as orchestrator_apply_new_param
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
                    ],
                },
                "B": {
                    "label": "TIPO DE TERRENO",
                    "values": [
                        {"label": "a", "value": "Normal"},
                        {"label": "b", "value": "Bajo vías"},
                    ],
                },
            },
            "text_variables": {
                "K": '"normal" * (%B=="a") + "bajo vías" * (%B=="b")',
            },
            "resumen": "Canalización hormigonada de $A T, PVC 110 mm, $K.\\",
            "texto":  "\\Canalización hormigonada de $A tubos, $K. Final.",
        }
    }


def _axis_only_rule():
    return {
        "type": "new_param",
        "param": "F",
        "label": "CALIDAD ACABADO",
        "values": [
            {"label": "a", "value": "Estándar"},
            {"label": "b", "value": "Premium"},
        ],
    }


def _axis_plus_var_rule():
    rule = _axis_only_rule()
    rule["text_variable"] = {
        "var": "F",
        "formula": '"estándar" * (%F=="a") + "premium" * (%F=="b")',
    }
    return rule


def _full_combo_rule():
    rule = _axis_plus_var_rule()
    rule["template_patches"] = [
        {
            "field": "RESUMEN",
            "original": "PVC 110 mm, $K.",
            "new": "PVC 110 mm, $K, calidad $F.",
        },
        {
            "field": "TEXTO",
            "original": "tubos, $K. Final.",
            "new": "tubos, $K, calidad $F. Final.",
        },
    ]
    return rule


def test_happy_path_axis_only(oeb020_stage2):
    pre_params_a = copy.deepcopy(oeb020_stage2["OEB020$"]["parameters"]["A"])
    pre_params_b = copy.deepcopy(oeb020_stage2["OEB020$"]["parameters"]["B"])
    pre_text_vars = copy.deepcopy(oeb020_stage2["OEB020$"]["text_variables"])
    pre_resumen = oeb020_stage2["OEB020$"]["resumen"]
    pre_texto = oeb020_stage2["OEB020$"]["texto"]

    out, log = apply_new_param(oeb020_stage2, "OEB020$", _axis_only_rule())

    assert out["OEB020$"]["parameters"]["F"] == {
        "label": "CALIDAD ACABADO",
        "values": [
            {"label": "a", "value": "Estándar"},
            {"label": "b", "value": "Premium"},
        ],
    }
    assert out["OEB020$"]["parameters"]["A"] == pre_params_a
    assert out["OEB020$"]["parameters"]["B"] == pre_params_b
    assert out["OEB020$"]["text_variables"] == pre_text_vars
    assert out["OEB020$"]["resumen"] == pre_resumen
    assert out["OEB020$"]["texto"] == pre_texto

    assert len(log) == 1
    mod = log[0]
    assert mod.type is ModificationType.NEW_PARAM
    assert mod.layer is Layer.PARAM_DEFINITION
    assert mod.param == "F"
    assert mod.new == "CALIDAD ACABADO"
    assert mod.var is None
    assert mod.status == "applied"


def test_happy_path_axis_plus_text_variable(oeb020_stage2):
    pre_k = oeb020_stage2["OEB020$"]["text_variables"]["K"]
    pre_resumen = oeb020_stage2["OEB020$"]["resumen"]
    pre_texto = oeb020_stage2["OEB020$"]["texto"]

    out, log = apply_new_param(oeb020_stage2, "OEB020$", _axis_plus_var_rule())

    formula = '"estándar" * (%F=="a") + "premium" * (%F=="b")'
    assert out["OEB020$"]["text_variables"]["F"] == formula
    assert out["OEB020$"]["text_variables"]["K"] == pre_k
    assert out["OEB020$"]["resumen"] == pre_resumen
    assert out["OEB020$"]["texto"] == pre_texto

    assert len(log) == 1
    assert log[0].var == "F"
    assert log[0].param == "F"
    assert log[0].new == "CALIDAD ACABADO"


def test_happy_path_axis_plus_one_template_patch(oeb020_stage2):
    pre_resumen = oeb020_stage2["OEB020$"]["resumen"]

    rule = _axis_only_rule()
    rule["template_patches"] = [
        {
            "field": "TEXTO",
            "original": "$K. Final.",
            "new": "$K, calidad $F. Final.",
        }
    ]

    out, log = apply_new_param(oeb020_stage2, "OEB020$", rule)

    assert out["OEB020$"]["texto"] == (
        "\\Canalización hormigonada de $A tubos, $K, calidad $F. Final."
    )
    assert out["OEB020$"]["resumen"] == pre_resumen
    assert len(log) == 1


def test_happy_path_full_combo(oeb020_stage2):
    out, log = apply_new_param(oeb020_stage2, "OEB020$", _full_combo_rule())

    assert out["OEB020$"]["parameters"]["F"]["label"] == "CALIDAD ACABADO"
    assert "calidad $F" in out["OEB020$"]["resumen"]
    assert "calidad $F" in out["OEB020$"]["texto"]
    assert out["OEB020$"]["text_variables"]["F"].startswith('"estándar"')

    assert len(log) == 1
    mod = log[0]
    assert mod.param == "F"
    assert mod.new == "CALIDAD ACABADO"
    assert mod.var == "F"
    assert mod.status == "applied"


def test_param_collision_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["param"] = "A"
    with pytest.raises(ValueError, match=r"'A'.*OEB020\$"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_var_collision_raises(oeb020_stage2):
    rule = _axis_plus_var_rule()
    rule["text_variable"] = {"var": "K", "formula": '"x" * (%F=="a")'}
    with pytest.raises(ValueError, match=r"'K'.*OEB020\$"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_template_patch_substring_not_found_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["template_patches"] = [
        {
            "field": "TEXTO",
            "original": "NO_SUCH_SUBSTRING",
            "new": "irrelevant",
        }
    ]
    with pytest.raises(KeyError, match="NO_SUCH_SUBSTRING"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_template_patch_substring_multiple_matches_raises(oeb020_stage2):
    oeb020_stage2["OEB020$"]["texto"] = (
        "\\Canalización hormigonada de $A tubos, $K tubos. Final."
    )
    rule = _axis_only_rule()
    rule["template_patches"] = [
        {"field": "TEXTO", "original": "tubos", "new": "conductos"}
    ]
    with pytest.raises(ValueError, match=r"tubos.*2.*'texto'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_missing_concept_key_raises(oeb020_stage2):
    with pytest.raises(KeyError, match="NOPE\\$"):
        apply_new_param(oeb020_stage2, "NOPE$", _axis_only_rule())


def test_concept_has_no_parameters_block_raises():
    stage = {"OEB020$": {"concept": "FOO", "resumen": "x", "texto": "y"}}
    with pytest.raises(KeyError, match="parameters"):
        apply_new_param(stage, "OEB020$", _axis_only_rule())


def test_empty_param_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["param"] = ""
    with pytest.raises(ValueError, match=r"new_param.*'param'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_missing_param_field_raises(oeb020_stage2):
    rule = _axis_only_rule()
    del rule["param"]
    with pytest.raises(ValueError, match=r"new_param.*'param'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_empty_label_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["label"] = ""
    with pytest.raises(ValueError, match=r"new_param.*'label'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_empty_values_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["values"] = []
    with pytest.raises(ValueError, match=r"new_param.*'values'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_duplicate_value_labels_raise(oeb020_stage2):
    rule = _axis_only_rule()
    rule["values"] = [
        {"label": "a", "value": "Estándar"},
        {"label": "a", "value": "Premium"},
    ]
    with pytest.raises(ValueError, match="duplicated value labels"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_text_variable_without_formula_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["text_variable"] = {"var": "F"}
    with pytest.raises(ValueError, match=r"text_variable.*'formula'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


def test_text_variables_block_auto_created():
    stage = {
        "OEB020$": {
            "concept": "BARE",
            "parameters": {
                "A": {
                    "label": "Nº TUBOS",
                    "values": [{"label": "a", "value": "1"}],
                },
            },
            "resumen": "Canal $A.\\",
            "texto": "\\Canal $A. Final.",
        }
    }
    assert "text_variables" not in stage["OEB020$"]
    rule = _axis_plus_var_rule()
    out, log = apply_new_param(stage, "OEB020$", rule)
    assert isinstance(out["OEB020$"]["text_variables"], dict)
    assert out["OEB020$"]["text_variables"] == {
        "F": '"estándar" * (%F=="a") + "premium" * (%F=="b")'
    }
    assert log[0].var == "F"


def test_template_patch_unknown_field_raises(oeb020_stage2):
    rule = _axis_only_rule()
    rule["template_patches"] = [
        {"field": "DESCRIPCION", "original": "x", "new": "y"}
    ]
    with pytest.raises(ValueError, match=r"DESCRIPCION.*'RESUMEN'.*'TEXTO'"):
        apply_new_param(oeb020_stage2, "OEB020$", rule)


@pytest.mark.parametrize("field_case", ["TEXTO", "texto", "Texto", "tExTo"])
def test_field_case_normalization_for_template_patches(oeb020_stage2, field_case):
    rule = _axis_only_rule()
    rule["template_patches"] = [
        {
            "field": field_case,
            "original": "$K. Final.",
            "new": "$K, calidad $F. Final.",
        }
    ]
    out, log = apply_new_param(oeb020_stage2, "OEB020$", rule)
    assert out["OEB020$"]["texto"] == (
        "\\Canalización hormigonada de $A tubos, $K, calidad $F. Final."
    )
    assert len(log) == 1
    assert log[0].param == "F"
    assert log[0].field is None


def test_orchestrator_routes_through_dispatch(oeb020_stage2):
    snap = json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False)
    out, log = orchestrator_apply_new_param(
        oeb020_stage2, "OEB020$", _axis_only_rule()
    )
    assert out["OEB020$"]["parameters"]["F"]["label"] == "CALIDAD ACABADO"
    assert json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False) == snap
    assert len(log) == 1
    assert log[0].type is ModificationType.NEW_PARAM


def test_wrong_layer_rule_raises_valueerror(oeb020_stage2):
    paraphrase_rule = {"type": "paraphrase"}
    with pytest.raises(ValueError):
        orchestrator_apply_new_param(oeb020_stage2, "OEB020$", paraphrase_rule)


def test_modification_has_exactly_one_entry(oeb020_stage2):
    out, log = apply_new_param(oeb020_stage2, "OEB020$", _full_combo_rule())
    assert len(log) == 1


def test_caller_dict_unchanged_after_apply(oeb020_stage2):
    snap = json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False)
    orchestrator_apply_new_param(oeb020_stage2, "OEB020$", _full_combo_rule())
    assert json.dumps(oeb020_stage2, sort_keys=True, ensure_ascii=False) == snap
