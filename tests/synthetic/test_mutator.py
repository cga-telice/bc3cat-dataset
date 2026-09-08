import inspect

import pytest

from synthetic.composition import compose_rules
from synthetic.mutator import (
    _DISPATCH,
    apply_l1,
    apply_l2,
    apply_l3,
    apply_new_param,
)
from synthetic.taxonomy import ModificationType


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


def test_dispatch_table_has_exactly_13_entries():
    # Sprint 36: TEMPLATE_PARAPHRASE joined the taxonomy.
    assert len(_DISPATCH) == 13
    assert set(_DISPATCH) == set(ModificationType)


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


def test_no_stubs_remain_in_dispatch():
    """After Sprint 10 every _DISPATCH entry is a real mutator."""
    assert all(fn.__name__.startswith("apply_") for fn in _DISPATCH.values())
    assert not any(fn.__name__.startswith("_stub_") for fn in _DISPATCH.values())


def test_composition_module_exposes_compose_rules():
    """B5 — composer is importable with the expected signature."""
    sig = inspect.signature(compose_rules)
    assert list(sig.parameters) == ["rules"]
