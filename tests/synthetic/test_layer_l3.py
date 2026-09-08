"""Contract suite for the L3 `template` mutators (Sprint 09)."""

import copy
import json

import pytest

from synthetic.layer_l3 import (
    _replace_substring,
    apply_omission,
    apply_reorder,
)
from synthetic.mutator import apply_l3
from synthetic.taxonomy import Layer, Modification, ModificationType


_RESUMEN = "Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))\\"
_TEXTO = (
    "\\Canalización hormigonada de $A tubos de PVC de 110 mm "
    "de diámetro $I, incluso $N el relleno y el compactado de "
    "la zanja, $P el suministro y el montaje de los tubos y "
    "hormigón tipo HE-20 sin vibrar, la prueba de los "
    "conductos, el transporte y la retirada de los productos "
    "al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: "
    "$D Condiciones de ejecución: $F"
)


@pytest.fixture
def oeb020_stage4():
    return {
        "OEB020aaaaa": {
            "parent_key": "OEB020$",
            "ud": "m",
            "concept": "CANALIZACIÓN HORMIGONADA DE TUBO DE PVC 110 mm",
            "text_variables": {
                "K": '"normal" * (%B=="a")',
            },
            "resumen": _RESUMEN,
            "texto": _TEXTO,
            "parameters": {
                "A": {
                    "label": "Nº TUBOS",
                    "values": [{"label": "a", "value": "1"}],
                },
            },
        }
    }


def test_happy_path_omission_on_texto(oeb020_stage4):
    pre_texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    pre_resumen = oeb020_stage4["OEB020aaaaa"]["resumen"]
    rule = {"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}

    out, log = apply_omission(oeb020_stage4, "OEB020aaaaa", rule)

    post_texto = out["OEB020aaaaa"]["texto"]
    assert " $I," not in post_texto
    assert pre_texto.replace(" $I,", "", 1) == post_texto
    assert out["OEB020aaaaa"]["resumen"] == pre_resumen

    assert len(log) == 1
    mod = log[0]
    assert isinstance(mod, Modification)
    assert mod.type is ModificationType.OMISSION
    assert mod.layer is Layer.TEMPLATE
    assert mod.field == "TEXTO"
    assert mod.original == " $I,"
    assert mod.new == ""
    assert mod.status == "applied"


def test_happy_path_omission_on_resumen(oeb020_stage4):
    pre_resumen = oeb020_stage4["OEB020aaaaa"]["resumen"]
    pre_texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    rule = {"type": "omission", "field": "RESUMEN", "original": ", $K", "new": ""}

    out, log = apply_omission(oeb020_stage4, "OEB020aaaaa", rule)

    post_resumen = out["OEB020aaaaa"]["resumen"]
    assert ", $K" not in post_resumen
    assert pre_resumen.replace(", $K", "", 1) == post_resumen
    assert out["OEB020aaaaa"]["texto"] == pre_texto

    assert len(log) == 1
    mod = log[0]
    assert mod.type is ModificationType.OMISSION
    assert mod.layer is Layer.TEMPLATE
    assert mod.field == "RESUMEN"
    assert mod.original == ", $K"
    assert mod.new == ""
    assert mod.status == "applied"


def test_happy_path_reorder_on_texto(oeb020_stage4):
    pre_texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    pre_resumen = oeb020_stage4["OEB020aaaaa"]["resumen"]
    original = "$A tubos de PVC de 110 mm de diámetro $I"
    new = "$I, en tubos de PVC de 110 mm de diámetro $A"
    rule = {"type": "reorder", "field": "TEXTO", "original": original, "new": new}

    out, log = apply_reorder(oeb020_stage4, "OEB020aaaaa", rule)

    post_texto = out["OEB020aaaaa"]["texto"]
    assert original not in post_texto
    assert new in post_texto

    start = pre_texto.index(original)
    end = start + len(original)
    assert post_texto[:start] == pre_texto[:start]
    assert post_texto[start + len(new):] == pre_texto[end:]
    assert out["OEB020aaaaa"]["resumen"] == pre_resumen

    assert len(log) == 1
    mod = log[0]
    assert mod.type is ModificationType.REORDER
    assert mod.layer is Layer.TEMPLATE
    assert mod.field == "TEXTO"
    assert mod.original == original
    assert mod.new == new
    assert mod.status == "applied"


def test_happy_path_reorder_on_resumen(oeb020_stage4):
    pre_resumen = oeb020_stage4["OEB020aaaaa"]["resumen"]
    pre_texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    original = "Canalización hormigonada de $A T, PVC 110 mm"
    new = "PVC 110 mm, canalización hormigonada de $A T"
    rule = {"type": "reorder", "field": "RESUMEN", "original": original, "new": new}

    out, log = apply_reorder(oeb020_stage4, "OEB020aaaaa", rule)

    post_resumen = out["OEB020aaaaa"]["resumen"]
    assert original not in post_resumen
    assert new in post_resumen
    assert pre_resumen.replace(original, new, 1) == post_resumen
    assert out["OEB020aaaaa"]["texto"] == pre_texto

    assert log[0].type is ModificationType.REORDER
    assert log[0].field == "RESUMEN"
    assert log[0].original == original
    assert log[0].new == new


@pytest.mark.parametrize(
    "wrapper, mtype, field, original, new",
    [
        pytest.param(
            apply_omission,
            ModificationType.OMISSION,
            "TEXTO",
            " $I,",
            "",
            id="omission-on-texto-leaves-resumen",
        ),
        pytest.param(
            apply_omission,
            ModificationType.OMISSION,
            "RESUMEN",
            ", $K",
            "",
            id="omission-on-resumen-leaves-texto",
        ),
    ],
)
def test_other_template_untouched(oeb020_stage4, wrapper, mtype, field, original, new):
    pre_resumen = oeb020_stage4["OEB020aaaaa"]["resumen"]
    pre_texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    rule = {"type": mtype.value, "field": field, "original": original, "new": new}

    out, _ = wrapper(oeb020_stage4, "OEB020aaaaa", rule)

    if field == "TEXTO":
        assert out["OEB020aaaaa"]["resumen"] == pre_resumen
        assert out["OEB020aaaaa"]["texto"] != pre_texto
    else:
        assert out["OEB020aaaaa"]["texto"] == pre_texto
        assert out["OEB020aaaaa"]["resumen"] != pre_resumen


@pytest.mark.parametrize("field_in", ["TEXTO", "texto", "Texto", "tExTo"])
def test_field_case_normalization(oeb020_stage4, field_in):
    rule = {"type": "omission", "field": field_in, "original": " $I,", "new": ""}
    fixture = copy.deepcopy(oeb020_stage4)
    out, log = apply_omission(fixture, "OEB020aaaaa", rule)

    canonical_fixture = copy.deepcopy(oeb020_stage4)
    canonical_rule = {"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}
    canonical_out, _ = apply_omission(canonical_fixture, "OEB020aaaaa", canonical_rule)

    assert json.dumps(out, sort_keys=True, ensure_ascii=False) == json.dumps(
        canonical_out, sort_keys=True, ensure_ascii=False
    )
    assert log[0].field == "TEXTO"


def test_apply_l3_orchestrator_threads_rules(oeb020_stage4):
    snapshot = json.dumps(oeb020_stage4, sort_keys=True, ensure_ascii=False)
    rules = [
        {"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""},
        {
            "type": "reorder",
            "field": "RESUMEN",
            "original": "Canalización hormigonada de $A T, PVC 110 mm",
            "new": "PVC 110 mm, canalización hormigonada de $A T",
        },
    ]

    out, log = apply_l3(oeb020_stage4, "OEB020aaaaa", rules)

    assert json.dumps(oeb020_stage4, sort_keys=True, ensure_ascii=False) == snapshot

    assert len(log) == 2
    assert [mod.type for mod in log] == [
        ModificationType.OMISSION,
        ModificationType.REORDER,
    ]
    assert all(mod.status == "applied" for mod in log)
    assert " $I," not in out["OEB020aaaaa"]["texto"]
    assert "PVC 110 mm, canalización hormigonada de $A T" in out["OEB020aaaaa"]["resumen"]


def test_omission_with_empty_new(oeb020_stage4):
    """Omission with `new=""` deletes the matched span and logs `new=""`."""
    rule = {"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}
    out, log = apply_omission(oeb020_stage4, "OEB020aaaaa", rule)

    assert " $I," not in out["OEB020aaaaa"]["texto"]
    assert log[0].new == ""


def test_reorder_with_no_op_new_succeeds(oeb020_stage4):
    """A no-op rule (`new == original`) is semantic-blind: still applies, still logs."""
    pre_texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    original = "$A tubos de PVC de 110 mm de diámetro $I"
    rule = {
        "type": "reorder",
        "field": "TEXTO",
        "original": original,
        "new": original,
    }
    out, log = apply_reorder(oeb020_stage4, "OEB020aaaaa", rule)

    assert out["OEB020aaaaa"]["texto"] == pre_texto
    assert len(log) == 1
    assert log[0].status == "applied"
    assert log[0].original == log[0].new == original


def test_missing_concept_key_raises(oeb020_stage4):
    rule = {"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}
    with pytest.raises(KeyError, match="NOPE"):
        apply_omission(oeb020_stage4, "NOPE$", rule)


def test_missing_field_template_raises():
    stage = {
        "OEB020aaaaa": {
            "texto": "\\Canalización ..."
            # no 'resumen' key
        }
    }
    rule = {"type": "omission", "field": "RESUMEN", "original": "Canalización", "new": ""}
    with pytest.raises(KeyError) as excinfo:
        apply_omission(stage, "OEB020aaaaa", rule)
    msg = excinfo.value.args[0]
    assert "'resumen'" in msg
    assert "OEB020aaaaa" in msg


def test_unknown_field_raises(oeb020_stage4):
    rule = {"type": "omission", "field": "DESCRIPCION", "original": "x", "new": ""}
    with pytest.raises(ValueError) as excinfo:
        apply_omission(oeb020_stage4, "OEB020aaaaa", rule)
    msg = str(excinfo.value)
    assert "DESCRIPCION" in msg
    assert "RESUMEN" in msg
    assert "TEXTO" in msg


def test_original_not_found_raises(oeb020_stage4):
    rule = {
        "type": "omission",
        "field": "TEXTO",
        "original": "NO_SUCH_FRAGMENT_IN_TEMPLATE",
        "new": "",
    }
    with pytest.raises(KeyError) as excinfo:
        apply_omission(oeb020_stage4, "OEB020aaaaa", rule)
    msg = excinfo.value.args[0]
    assert "NO_SUCH_FRAGMENT_IN_TEMPLATE" in msg
    assert "'texto'" in msg


def test_original_matches_multiple_times_raises(oeb020_stage4):
    """`'de '` occurs many times in the texto template; uniqueness is required."""
    rule = {"type": "omission", "field": "TEXTO", "original": "de ", "new": ""}
    with pytest.raises(ValueError) as excinfo:
        apply_omission(oeb020_stage4, "OEB020aaaaa", rule)
    msg = str(excinfo.value)
    assert "'de '" in msg
    assert "'texto'" in msg
    # Count is reported.
    texto = oeb020_stage4["OEB020aaaaa"]["texto"]
    assert str(texto.count("de ")) in msg


def test_empty_original_raises(oeb020_stage4):
    rule = {"type": "omission", "field": "TEXTO", "original": "", "new": ""}
    with pytest.raises(ValueError, match="omission.*original"):
        apply_omission(oeb020_stage4, "OEB020aaaaa", rule)


def test_missing_new_field_raises(oeb020_stage4):
    rule = {"type": "omission", "field": "TEXTO", "original": " $I,"}
    with pytest.raises(ValueError, match="omission.*new"):
        apply_omission(oeb020_stage4, "OEB020aaaaa", rule)


def test_modification_original_byte_equals_rule_original(oeb020_stage4):
    """For L3 the rule's `original` IS the addressing key (load-bearing).

    Diverges from L1/L2: there the rule's `original` was either ignored
    (L1) or absent (L2), and the log captured the live value. For L3 the
    matched substring is bytewise the rule's input — `str.count` + bytewise
    `str.replace` is the entire matching primitive.
    """
    original = " $I,"
    rule = {"type": "omission", "field": "TEXTO", "original": original, "new": ""}
    _, log = apply_omission(oeb020_stage4, "OEB020aaaaa", rule)
    assert log[0].original == original
    assert log[0].original is not original or log[0].original == original


def test_caller_dict_unchanged_after_apply(oeb020_stage4):
    snapshot = json.dumps(oeb020_stage4, sort_keys=True, ensure_ascii=False)
    apply_l3(
        oeb020_stage4,
        "OEB020aaaaa",
        [{"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}],
    )
    assert (
        json.dumps(oeb020_stage4, sort_keys=True, ensure_ascii=False) == snapshot
    )


def test_replace_substring_directly(oeb020_stage4):
    rule = {"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}
    out, log = _replace_substring(
        oeb020_stage4, "OEB020aaaaa", rule, ModificationType.OMISSION
    )
    assert out is oeb020_stage4
    assert " $I," not in out["OEB020aaaaa"]["texto"]
    assert log[0].type is ModificationType.OMISSION
    assert log[0].layer is Layer.TEMPLATE
    assert log[0].field == "TEXTO"
