import inspect
import json

import pytest

from synthetic.mutator import (
    _DISPATCH,
    apply_l1,
    apply_l2,
    apply_l3,
    apply_new_param,
)
from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER


_LAYER_TO_APPLY = {
    Layer.PARAM_VALUE: apply_l1,
    Layer.TEXT_VARIABLE: apply_l2,
    Layer.TEMPLATE: apply_l3,
}


def test_apply_l1_signature():
    assert list(inspect.signature(apply_l1).parameters) == [
        "stage2_json",
        "concept_key",
        "rules",
    ]


def test_apply_l2_signature():
    assert list(inspect.signature(apply_l2).parameters) == [
        "stage3_json",
        "concept_key",
        "rules",
    ]


def test_apply_l3_signature():
    assert list(inspect.signature(apply_l3).parameters) == [
        "stage4_json",
        "concept_key",
        "rules",
    ]


def test_apply_new_param_signature():
    assert list(inspect.signature(apply_new_param).parameters) == [
        "stage2_json",
        "concept_key",
        "rule",
    ]


def test_dispatch_table_has_exactly_12_entries():
    assert len(_DISPATCH) == 12
    assert set(_DISPATCH) == set(ModificationType)


@pytest.mark.parametrize("mtype", list(ModificationType))
def test_each_stub_raises_notimplemented_with_type_code(mtype):
    rule = {"type": mtype.value}
    layer = TYPE_TO_LAYER[mtype]
    if mtype is ModificationType.NEW_PARAM:
        with pytest.raises(NotImplementedError, match=mtype.value):
            apply_new_param({}, "OEB020$", rule)
    else:
        fn = _LAYER_TO_APPLY[layer]
        with pytest.raises(NotImplementedError, match=mtype.value):
            fn({}, "OEB020$", [rule])


def test_wrong_layer_rule_raises_valueerror():
    paraphrase_rule = {"type": "paraphrase"}
    with pytest.raises(ValueError):
        apply_l1({}, "OEB020$", [paraphrase_rule])


def test_wrong_layer_rule_on_new_param_raises_valueerror():
    paraphrase_rule = {"type": "paraphrase"}
    with pytest.raises(ValueError):
        apply_new_param({}, "OEB020$", paraphrase_rule)


def test_unknown_type_code_raises_valueerror():
    with pytest.raises(ValueError, match="unknown modification type"):
        apply_l1({}, "OEB020$", [{"type": "not_a_real_type"}])


def test_deep_copy_purity_on_notimplemented():
    stage = {
        "OEB020$": {
            "parameters": {
                "A": {
                    "label": "TRABAJO",
                    "values": [{"label": "a", "value": "Diurno"}],
                }
            },
            "resumen": "Canalización ...",
        }
    }
    snapshot = json.dumps(stage, sort_keys=True)
    with pytest.raises(NotImplementedError):
        apply_l1(stage, "OEB020$", [{"type": "synonym_label"}])
    assert json.dumps(stage, sort_keys=True) == snapshot
