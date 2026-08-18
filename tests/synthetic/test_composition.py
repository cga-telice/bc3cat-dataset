"""Contract tests for `synthetic.composition.compose_rules`.

Pre-apply validator over rule batches. Three passes:
1. Canonical-key dedup (same target → later rule skipped).
2. PD-vs-L1 same-axis pass (L1 rule on a param a PD rule introduces
   → L1 skipped).
3. Matrix pass (currently no-effect for the starter content because
   the only entries are `LAYER_DEPENDENCY` and step 2 handles them).

Tests are state-blind by construction; the composer never reads
stage JSON.
"""

from __future__ import annotations

import copy
import inspect

import pytest

from synthetic.composition import (
    COMPATIBILITY_MATRIX,
    CompatibilityVerdict,
    compose_rules,
)
from synthetic.taxonomy import Layer, Modification, ModificationType


def _r(mtype: ModificationType, **kwargs):
    return {"type": mtype.value, **kwargs}


# ---------------------------------------------------------------------------
# Signature + edge-case shape
# ---------------------------------------------------------------------------


def test_compose_rules_signature():
    sig = inspect.signature(compose_rules)
    assert list(sig.parameters) == ["rules"]


def test_empty_input_returns_empty_tuple():
    admissible, skipped = compose_rules([])
    assert admissible == []
    assert skipped == []


@pytest.mark.parametrize(
    "rule",
    [
        _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno"),
        _r(ModificationType.PARAPHRASE, var="K", condition='%B=="a"', new="estandar"),
        _r(ModificationType.OMISSION, field="TEXTO", original=" $I,", new=""),
        _r(
            ModificationType.NEW_PARAM,
            param="K",
            label="CALIDAD",
            values=[{"label": "a", "value": "Std"}],
        ),
    ],
)
def test_single_rule_passes_through_per_layer(rule):
    admissible, skipped = compose_rules([rule])
    assert admissible == [rule]
    assert skipped == []


# ---------------------------------------------------------------------------
# Layer apply-order
# ---------------------------------------------------------------------------


def test_layer_order_pd_l1_l2_l3():
    l3 = _r(ModificationType.OMISSION, field="TEXTO", original=" $I,", new="")
    l2 = _r(ModificationType.PARAPHRASE, var="K", condition='%B=="a"', new="estandar")
    l1 = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")
    pd = _r(
        ModificationType.NEW_PARAM,
        param="F",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )

    admissible, skipped = compose_rules([l3, l2, l1, pd])

    assert [r["type"] for r in admissible] == [
        "new_param",
        "synonym_label",
        "paraphrase",
        "omission",
    ]
    assert skipped == []


def test_stable_order_within_layer():
    a = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")
    b = _r(ModificationType.NUM_TO_TEXT, param="B", value="b", new="dos")
    c = _r(ModificationType.UNIT_CONVERSION, param="C", value="c", new="2 km")

    admissible, skipped = compose_rules([a, b, c])

    assert admissible == [a, b, c]
    assert skipped == []


# ---------------------------------------------------------------------------
# Same-target dedup — per layer
# ---------------------------------------------------------------------------


def test_same_target_dedup_l1():
    first = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")
    second = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="One")

    admissible, skipped = compose_rules([first, second])

    assert admissible == [first]
    assert len(skipped) == 1
    assert skipped[0].type is ModificationType.SYNONYM_LABEL
    assert skipped[0].layer is Layer.PARAM_VALUE
    assert skipped[0].status == "skipped"
    assert skipped[0].reason.startswith("same_target_conflict")


def test_same_target_dedup_l1_across_types():
    first = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")
    second = _r(ModificationType.NUM_TO_TEXT, param="A", value="a", new="uno")

    admissible, skipped = compose_rules([first, second])

    assert admissible == [first]
    assert len(skipped) == 1
    assert skipped[0].type is ModificationType.NUM_TO_TEXT
    assert skipped[0].reason.startswith("same_target_conflict")


def test_distinct_targets_no_conflict_l1():
    a = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")
    b = _r(ModificationType.SYNONYM_LABEL, param="A", value="b", new="Dos")

    admissible, skipped = compose_rules([a, b])

    assert admissible == [a, b]
    assert skipped == []


def test_same_target_dedup_l2():
    # Pins both normalisations: $-strip (var "K" == "$K") and
    # whitespace-collapse (single-space '==' matches double-space).
    first = _r(
        ModificationType.PARAPHRASE,
        var="K",
        condition='%B == "a"',
        new="primero",
    )
    second = _r(
        ModificationType.PARAPHRASE,
        var="$K",
        condition='%B  ==  "a"',
        new="segundo",
    )

    admissible, skipped = compose_rules([first, second])

    assert admissible == [first]
    assert len(skipped) == 1
    assert skipped[0].type is ModificationType.PARAPHRASE
    assert skipped[0].layer is Layer.TEXT_VARIABLE
    assert skipped[0].reason.startswith("same_target_conflict")


def test_same_target_dedup_l3():
    first = _r(
        ModificationType.OMISSION,
        field="TEXTO",
        original="$I,",
        new="",
    )
    second = _r(
        ModificationType.OMISSION,
        field="texto",
        original="$I,",
        new="!",
    )

    admissible, skipped = compose_rules([first, second])

    assert admissible == [first]
    assert len(skipped) == 1
    assert skipped[0].type is ModificationType.OMISSION
    assert skipped[0].layer is Layer.TEMPLATE
    assert skipped[0].reason.startswith("same_target_conflict")


def test_same_target_dedup_pd():
    first = _r(
        ModificationType.NEW_PARAM,
        param="K",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )
    second = _r(
        ModificationType.NEW_PARAM,
        param="K",
        label="GRADO",
        values=[{"label": "a", "value": "Bajo"}],
    )

    admissible, skipped = compose_rules([first, second])

    assert admissible == [first]
    assert len(skipped) == 1
    assert skipped[0].type is ModificationType.NEW_PARAM
    assert skipped[0].layer is Layer.PARAM_DEFINITION
    assert "PARAM_DEFINITION" in skipped[0].reason or "param_definition" in skipped[0].reason
    assert "K" in skipped[0].reason


# ---------------------------------------------------------------------------
# PD-vs-L1 same-axis layer-dependency pass
# ---------------------------------------------------------------------------


def test_pd_introduces_axis_l1_on_same_axis_skipped():
    pd = _r(
        ModificationType.NEW_PARAM,
        param="K",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )
    l1 = _r(ModificationType.SYNONYM_LABEL, param="K", value="a", new="X")

    admissible, skipped = compose_rules([pd, l1])

    assert admissible == [pd]
    assert len(skipped) == 1
    assert skipped[0].type is ModificationType.SYNONYM_LABEL
    assert skipped[0].layer is Layer.PARAM_VALUE
    assert "layer_dependency_conflict" in skipped[0].reason
    assert "'K'" in skipped[0].reason


def test_pd_introduces_axis_l1_on_different_axis_no_conflict():
    pd = _r(
        ModificationType.NEW_PARAM,
        param="K",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )
    l1 = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")

    admissible, skipped = compose_rules([pd, l1])

    assert admissible == [pd, l1]
    assert skipped == []


_ALL_L1_TYPES = [
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
]


@pytest.mark.parametrize("l1_type", _ALL_L1_TYPES)
def test_pd_introduces_axis_all_six_l1_types_each_skipped(l1_type):
    pd = _r(
        ModificationType.NEW_PARAM,
        param="K",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )
    l1 = _r(l1_type, param="K", value="a", new="X")

    admissible, skipped = compose_rules([pd, l1])

    assert admissible == [pd]
    assert len(skipped) == 1
    assert skipped[0].type is l1_type
    assert "layer_dependency_conflict" in skipped[0].reason
    assert "'K'" in skipped[0].reason


def test_l2_on_var_pd_does_not_introduce_no_conflict():
    pd = _r(
        ModificationType.NEW_PARAM,
        param="K",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
        text_variable={"var": "K", "formula": '"x" * (%K=="a")'},
    )
    l2 = _r(
        ModificationType.PARAPHRASE,
        var="OTHER",
        condition='%B=="a"',
        new="paraphrased",
    )

    admissible, skipped = compose_rules([pd, l2])

    assert admissible == [pd, l2]
    assert skipped == []


# ---------------------------------------------------------------------------
# Mixed-batch happy path
# ---------------------------------------------------------------------------


def test_mixed_layer_batch_no_conflicts():
    pd = _r(
        ModificationType.NEW_PARAM,
        param="F",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )
    l1 = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")
    l2 = _r(
        ModificationType.PARAPHRASE,
        var="K",
        condition='%B=="a"',
        new="estandar",
    )
    l3 = _r(ModificationType.OMISSION, field="TEXTO", original=" $I,", new="")

    admissible, skipped = compose_rules([l3, l2, l1, pd])

    assert admissible == [pd, l1, l2, l3]
    assert skipped == []


# ---------------------------------------------------------------------------
# Purity / identity contract
# ---------------------------------------------------------------------------


def test_no_mutation_of_input_rules():
    rules = [
        _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno"),
        _r(
            ModificationType.NEW_PARAM,
            param="K",
            label="CALIDAD",
            values=[{"label": "a", "value": "Std"}],
        ),
        _r(
            ModificationType.PARAPHRASE,
            var="K",
            condition='%B=="a"',
            new="estandar",
        ),
    ]
    snapshot = copy.deepcopy(rules)

    compose_rules(rules)

    assert rules == snapshot


def test_admissible_output_aliases_input_rules():
    pd = _r(
        ModificationType.NEW_PARAM,
        param="F",
        label="CALIDAD",
        values=[{"label": "a", "value": "Std"}],
    )
    l1 = _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno")

    admissible, _ = compose_rules([l1, pd])

    assert admissible[0] is pd
    assert admissible[1] is l1


# ---------------------------------------------------------------------------
# Malformed input → exceptions
# ---------------------------------------------------------------------------


def test_unknown_type_raises_valueerror():
    rule = {"type": "not_a_real_type"}
    with pytest.raises(ValueError, match="not_a_real_type"):
        compose_rules([rule])


def test_l1_rule_missing_value_raises_keyerror():
    rule = _r(ModificationType.SYNONYM_LABEL, param="A", new="Uno")
    with pytest.raises(KeyError) as excinfo:
        compose_rules([rule])
    assert excinfo.value.args[0] == "value"


def test_l2_rule_missing_condition_raises_keyerror():
    rule = _r(ModificationType.PARAPHRASE, var="K", new="estandar")
    with pytest.raises(KeyError) as excinfo:
        compose_rules([rule])
    assert excinfo.value.args[0] == "condition"


def test_l3_rule_missing_original_raises_keyerror():
    rule = _r(ModificationType.OMISSION, field="TEXTO", new="")
    with pytest.raises(KeyError) as excinfo:
        compose_rules([rule])
    assert excinfo.value.args[0] == "original"


def test_pd_rule_missing_param_raises_keyerror():
    rule = {
        "type": ModificationType.NEW_PARAM.value,
        "label": "X",
        "values": [{"label": "a", "value": "1"}],
    }
    with pytest.raises(KeyError) as excinfo:
        compose_rules([rule])
    assert excinfo.value.args[0] == "param"


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------


def test_idempotent_under_recomposition():
    rules = [
        _r(ModificationType.OMISSION, field="TEXTO", original=" $I,", new=""),
        _r(
            ModificationType.PARAPHRASE,
            var="K",
            condition='%B=="a"',
            new="estandar",
        ),
        _r(ModificationType.SYNONYM_LABEL, param="A", value="a", new="Uno"),
        _r(ModificationType.NUM_TO_TEXT, param="B", value="b", new="dos"),
        _r(
            ModificationType.NEW_PARAM,
            param="F",
            label="CALIDAD",
            values=[{"label": "a", "value": "Std"}],
        ),
        _r(
            ModificationType.REORDER,
            field="RESUMEN",
            original="$A T",
            new="T $A",
        ),
    ]

    admissible_a, skipped_a = compose_rules(rules)
    admissible_b, skipped_b = compose_rules(admissible_a)

    assert admissible_a == admissible_b
    assert skipped_b == []


# ---------------------------------------------------------------------------
# Matrix audit
# ---------------------------------------------------------------------------


def test_compatibility_matrix_only_contains_known_pairs():
    for key, value in COMPATIBILITY_MATRIX.items():
        assert isinstance(key, tuple) and len(key) == 2
        earlier, later = key
        assert isinstance(earlier, ModificationType)
        assert isinstance(later, ModificationType)
        assert isinstance(value, CompatibilityVerdict)


def test_compatibility_matrix_starter_pd_l1_pairs():
    expected = {
        (ModificationType.NEW_PARAM, ModificationType.SYNONYM_LABEL): CompatibilityVerdict.LAYER_DEPENDENCY,
        (ModificationType.NEW_PARAM, ModificationType.NUM_TO_TEXT): CompatibilityVerdict.LAYER_DEPENDENCY,
        (ModificationType.NEW_PARAM, ModificationType.UNIT_CONVERSION): CompatibilityVerdict.LAYER_DEPENDENCY,
        (ModificationType.NEW_PARAM, ModificationType.UNIT_EXPANSION): CompatibilityVerdict.LAYER_DEPENDENCY,
        (ModificationType.NEW_PARAM, ModificationType.ABBREV_EXPANSION): CompatibilityVerdict.LAYER_DEPENDENCY,
        (ModificationType.NEW_PARAM, ModificationType.CODE_EXPANSION): CompatibilityVerdict.LAYER_DEPENDENCY,
    }
    assert COMPATIBILITY_MATRIX == expected
