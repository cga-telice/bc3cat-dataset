"""Contract suite for the L2 `text_variable` mutators (Sprint 08)."""

import copy
import json
import re

import pytest

from synthetic.layer_l2 import (
    _replace_fragment,
    apply_compression,
    apply_expansion,
    apply_paraphrase,
)
from synthetic.mutator import apply_l2
from synthetic.taxonomy import Layer, Modification, ModificationType


@pytest.fixture
def oeb020_stage3():
    return {
        "OEB020$": {
            "concept": "CANALIZACIÓN HORMIGONADA",
            "parameters": {
                "A": {
                    "label": "Nº TUBOS",
                    "values": [{"label": "a", "value": "1"}],
                },
                "B": {
                    "label": "TIPO DE TERRENO",
                    "values": [
                        {"label": "a", "value": "Normal"},
                        {"label": "b", "value": "Bajo vías"},
                        {"label": "c", "value": "Rocoso"},
                        {"label": "f", "value": "Solera"},
                        {"label": "g", "value": "Roca dura"},
                    ],
                },
            },
            "text_variables": {
                "K": (
                    '"normal" * (%B=="a") + '
                    '"bajo vías" * (%B=="b") + '
                    '"rocoso" * (%B=="c")'
                ),
                "I": (
                    '"en cualquier clase de terreno, excepto roca" * (%B=="a") + '
                    '"en cruce bajo vías" * (%B=="b")'
                ),
                "N": '"el descerne y la entibación," * (%B=="b"  or  %B=="g")',
                "P": ['"la preparación y nivelación..." * (%B=="f")'],
                "G": ['"Diurno"', '"Nocturno"'],
            },
            "resumen": "PLACEHOLDER",
            "texto": "PLACEHOLDER",
        }
    }


_HAPPY_PATH_CASES = [
    pytest.param(
        apply_paraphrase,
        ModificationType.PARAPHRASE,
        "K", '%B=="a"', "normal", "estándar",
        id="paraphrase",
    ),
    pytest.param(
        apply_expansion,
        ModificationType.EXPANSION,
        "I", '%B=="a"',
        "en cualquier clase de terreno, excepto roca",
        "en cualquier tipo de terreno, salvo formaciones rocosas duras",
        id="expansion",
    ),
    pytest.param(
        apply_compression,
        ModificationType.COMPRESSION,
        "K", '%B=="b"', "bajo vías", "bajo vía",
        id="compression",
    ),
]


@pytest.mark.parametrize(
    "wrapper, mtype, var_key, condition, expected_original, new_fragment",
    _HAPPY_PATH_CASES,
)
def test_happy_path_per_type(
    oeb020_stage3, wrapper, mtype, var_key, condition, expected_original, new_fragment
):
    rule = {
        "type": mtype.value,
        "var": var_key,
        "condition": condition,
        "new": new_fragment,
    }
    out, log = wrapper(oeb020_stage3, "OEB020$", rule)

    formula = out["OEB020$"]["text_variables"][var_key]
    if isinstance(formula, list):
        formula_str = " | ".join(formula)
    else:
        formula_str = formula

    assert f'"{new_fragment}" * ({condition})' in formula_str
    assert f'"{expected_original}" * ({condition})' not in formula_str

    assert len(log) == 1
    mod = log[0]
    assert isinstance(mod, Modification)
    assert mod.type is mtype
    assert mod.layer is Layer.TEXT_VARIABLE
    assert mod.var == var_key
    assert mod.condition == condition
    assert mod.original == expected_original
    assert mod.new == new_fragment
    assert mod.status == "applied"


def test_list_typed_conditional_fragment(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "P",
        "condition": '%B=="f"',
        "new": "la nivelación previa de la solera",
    }
    pre_len = len(oeb020_stage3["OEB020$"]["text_variables"]["P"])
    out, log = apply_paraphrase(oeb020_stage3, "OEB020$", rule)

    entry = out["OEB020$"]["text_variables"]["P"]
    assert isinstance(entry, list)
    assert len(entry) == pre_len
    assert entry[0] == '"la nivelación previa de la solera" * (%B=="f")'

    assert len(log) == 1
    assert log[0].var == "P"
    assert log[0].original == "la preparación y nivelación..."
    assert log[0].new == "la nivelación previa de la solera"


def test_var_prefix_stripped(oeb020_stage3):
    rule_bare = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="a"',
        "new": "estándar",
    }
    rule_prefixed = {
        "type": "paraphrase",
        "var": "$K",
        "condition": '%B=="a"',
        "new": "estándar",
    }

    fixture_bare = copy.deepcopy(oeb020_stage3)
    fixture_prefixed = copy.deepcopy(oeb020_stage3)

    out_bare, log_bare = apply_paraphrase(fixture_bare, "OEB020$", rule_bare)
    out_prefixed, log_prefixed = apply_paraphrase(
        fixture_prefixed, "OEB020$", rule_prefixed
    )

    assert json.dumps(out_bare, sort_keys=True, ensure_ascii=False) == json.dumps(
        out_prefixed, sort_keys=True, ensure_ascii=False
    )
    assert log_bare[0].var == "K"
    assert log_prefixed[0].var == "K"
    assert log_bare[0].to_dict() == log_prefixed[0].to_dict()


def test_modification_original_sourced_from_stage_json(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="a"',
        "original": "WRONG",
        "new": "estándar",
    }
    _, log = apply_paraphrase(oeb020_stage3, "OEB020$", rule)
    assert log[0].original == "normal"


def test_apply_l2_orchestrator_threads_rules(oeb020_stage3):
    snapshot = json.dumps(oeb020_stage3, sort_keys=True, ensure_ascii=False)
    rules = [
        {
            "type": "paraphrase",
            "var": "K",
            "condition": '%B=="a"',
            "new": "estándar",
        },
        {
            "type": "expansion",
            "var": "I",
            "condition": '%B=="a"',
            "new": "en cualquier tipo de terreno, salvo formaciones rocosas duras",
        },
        {
            "type": "compression",
            "var": "K",
            "condition": '%B=="b"',
            "new": "bajo vía",
        },
    ]

    out, log = apply_l2(oeb020_stage3, "OEB020$", rules)

    assert (
        json.dumps(oeb020_stage3, sort_keys=True, ensure_ascii=False) == snapshot
    )

    assert len(log) == 3
    assert [mod.type for mod in log] == [
        ModificationType.PARAPHRASE,
        ModificationType.EXPANSION,
        ModificationType.COMPRESSION,
    ]
    assert all(mod.status == "applied" for mod in log)

    text_vars = out["OEB020$"]["text_variables"]
    assert '"estándar" * (%B=="a")' in text_vars["K"]
    assert '"bajo vía" * (%B=="b")' in text_vars["K"]
    assert (
        '"en cualquier tipo de terreno, salvo formaciones rocosas duras" '
        '* (%B=="a")'
    ) in text_vars["I"]


def test_compound_or_condition_preserved(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "N",
        "condition": '%B=="b"  or  %B=="g"',
        "new": "el descerne y la entibación auxiliar",
    }
    out, log = apply_paraphrase(oeb020_stage3, "OEB020$", rule)

    formula = out["OEB020$"]["text_variables"]["N"]
    assert (
        '"el descerne y la entibación auxiliar" '
        '* (%B=="b"  or  %B=="g")'
    ) == formula
    assert log[0].condition == '%B=="b"  or  %B=="g"'


def test_whitespace_normalized_condition_match(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "N",
        "condition": '%B=="b" or %B=="g"',
        "new": "el descerne y la entibación auxiliar",
    }
    out, log = apply_paraphrase(oeb020_stage3, "OEB020$", rule)

    formula = out["OEB020$"]["text_variables"]["N"]
    assert "%B==\"b\"  or  %B==\"g\"" in formula
    assert log[0].condition == '%B=="b"  or  %B=="g"'


def test_lookup_table_list_raises(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "G",
        "condition": '%C=="a"',
        "new": "Día",
    }
    with pytest.raises(ValueError) as excinfo:
        apply_paraphrase(oeb020_stage3, "OEB020$", rule)
    msg = str(excinfo.value)
    assert "'G'" in msg
    assert "lookup-table" in msg or "no conditional fragments" in msg


def test_missing_concept_key_raises(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="a"',
        "new": "X",
    }
    with pytest.raises(KeyError, match="NOPE"):
        apply_paraphrase(oeb020_stage3, "NOPE$", rule)


def test_missing_var_raises(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "$Z",
        "condition": '%B=="a"',
        "new": "X",
    }
    with pytest.raises(KeyError, match="'Z'"):
        apply_paraphrase(oeb020_stage3, "OEB020$", rule)


def test_missing_condition_raises(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="zz"',
        "new": "X",
    }
    with pytest.raises(KeyError) as excinfo:
        apply_paraphrase(oeb020_stage3, "OEB020$", rule)
    msg = excinfo.value.args[0]
    assert "'K'" in msg
    assert '%B=="zz"' in msg


def test_empty_new_raises(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="a"',
        "new": "",
    }
    with pytest.raises(ValueError, match="paraphrase.*new"):
        apply_paraphrase(oeb020_stage3, "OEB020$", rule)


def test_missing_condition_field_raises(oeb020_stage3):
    rule = {"type": "paraphrase", "var": "K", "new": "X"}
    with pytest.raises(ValueError, match="paraphrase.*condition"):
        apply_paraphrase(oeb020_stage3, "OEB020$", rule)


def test_caller_dict_unchanged_after_apply(oeb020_stage3):
    snapshot = json.dumps(oeb020_stage3, sort_keys=True, ensure_ascii=False)
    apply_l2(
        oeb020_stage3,
        "OEB020$",
        [
            {
                "type": "paraphrase",
                "var": "K",
                "condition": '%B=="a"',
                "new": "estándar",
            }
        ],
    )
    assert (
        json.dumps(oeb020_stage3, sort_keys=True, ensure_ascii=False) == snapshot
    )


def test_only_targeted_fragment_changes(oeb020_stage3):
    pre_formula = oeb020_stage3["OEB020$"]["text_variables"]["K"]
    pre_fragments = re.findall(r'"[^"]*"', pre_formula)

    rule = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="b"',
        "new": "bajo vía",
    }
    out, _ = apply_paraphrase(oeb020_stage3, "OEB020$", rule)

    post_formula = out["OEB020$"]["text_variables"]["K"]
    post_fragments = re.findall(r'"[^"]*"', post_formula)

    assert len(pre_fragments) == len(post_fragments)
    diffs = [
        i for i, (a, b) in enumerate(zip(pre_fragments, post_fragments)) if a != b
    ]
    assert len(diffs) == 1
    assert pre_fragments[diffs[0]] == '"bajo vías"'
    assert post_fragments[diffs[0]] == '"bajo vía"'


def test_replace_fragment_directly(oeb020_stage3):
    rule = {
        "type": "paraphrase",
        "var": "K",
        "condition": '%B=="a"',
        "new": "estándar",
    }
    out, log = _replace_fragment(
        oeb020_stage3, "OEB020$", rule, ModificationType.PARAPHRASE
    )
    assert out is oeb020_stage3
    assert '"estándar" * (%B=="a")' in out["OEB020$"]["text_variables"]["K"]
    assert log[0].type is ModificationType.PARAPHRASE
    assert log[0].layer is Layer.TEXT_VARIABLE
