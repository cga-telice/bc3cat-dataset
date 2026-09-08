"""Sprint 31 — L1 ↔ L2 paired mutation through the layer wrappers.

F1-review verdict: on OEB070, axis B/C/D each have a *twin* text-variable
($L/$M/$N) whose fragments duplicate the parameter's value labels. A
single-layer L1 or L2 mutation touches only one representation and
desynchronises resumen (query) from texto (document). The mutator layers
now apply the paired edit atomically: when a twin exists AND the twin's
current text still coincides with the pre-mod value, both sides move
together and a second Modification carrying `status="paired"` is logged.
"""

from __future__ import annotations

import copy

import pytest

from synthetic.layer_l1 import apply_synonym_label
from synthetic.layer_l2 import apply_paraphrase
from synthetic.taxonomy import Layer, ModificationType


def _oeb070_stage2():
    """Fresh mutable OEB070-shaped stage-2 with duplicated encoding on B/C/D."""
    return {
        "OEB070$": {
            "concept": "CANALIZACIÓN OEB070",
            "parameters": {
                "A": {"label": "Nº TUBOS", "values": [
                    {"label": "a", "value": "1"},
                    {"label": "b", "value": "2"},
                ]},
                "B": {"label": "TRABAJO", "values": [
                    {"label": "a", "value": "Diurno"},
                    {"label": "b", "value": "Nocturno"},
                ]},
                "C": {"label": "BANDA", "values": [
                    {"label": "a", "value": "i >= 5 horas"},
                ]},
                "D": {"label": "CONDICIONES", "values": [
                    {"label": "a", "value": "Volumen relevante"},
                ]},
            },
            "text_variables": {
                "L": '"Diurno" * (%B=a) + "Nocturno" * (%B=b)',
                "M": '"i >= 5 horas" * (%C=a)',
                "N": '"Volumen relevante" * (%D=a)',
            },
            "resumen": "de $A tubo(s) ($L(%B)/$M(%C)/$N(%D))",
            "texto": "de $A tubo(s). Trabajo: $B Banda: $C Condiciones: $D",
        }
    }


# ---- L1 → paired L2 -----------------------------------------------------

def test_l1_on_twin_axis_carries_into_text_variable():
    stage = _oeb070_stage2()
    # Synonym on param B value "a": Diurno → Día. Twin is $L via $L(%B).
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "a", "new": "Día"},
    )
    # 1) Param B value updated (single-layer semantics preserved).
    b_a = stage_out["OEB070$"]["parameters"]["B"]["values"][0]["value"]
    assert b_a == "Día"
    # 2) Text-variable L's fragment updated (paired edit).
    l_formula = stage_out["OEB070$"]["text_variables"]["L"]
    assert '"Día" * (%B=a)' in l_formula
    assert '"Nocturno" * (%B=b)' in l_formula
    # 3) Log carries two entries: primary L1 + paired L2.
    assert len(log) == 2
    assert log[0].layer is Layer.PARAM_VALUE
    assert log[0].type is ModificationType.SYNONYM_LABEL
    assert log[0].original == "Diurno" and log[0].new == "Día"
    assert log[1].layer is Layer.TEXT_VARIABLE
    assert log[1].status == "paired"
    assert log[1].var == "L"
    assert log[1].condition == "%B=a"
    assert log[1].original == "Diurno" and log[1].new == "Día"


def test_l1_on_axis_without_twin_leaves_log_at_one():
    stage = _oeb070_stage2()
    # Axis A ($A bare) has no twin text-variable.
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "A", "value": "a", "new": "uno"},
    )
    assert stage_out["OEB070$"]["parameters"]["A"]["values"][0]["value"] == "uno"
    assert len(log) == 1
    assert log[0].layer is Layer.PARAM_VALUE


def test_l1_when_twin_fragment_diverges_pair_is_skipped():
    stage = _oeb070_stage2()
    # Author diverged the text-var from the param value already.
    stage["OEB070$"]["text_variables"]["L"] = (
        '"Trabajo diurno" * (%B=a) + "Nocturno" * (%B=b)'
    )
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "a", "new": "Día"},
    )
    # Param B still gets rewritten...
    assert stage_out["OEB070$"]["parameters"]["B"]["values"][0]["value"] == "Día"
    # ...but the text-var is left as-authored (fragment != original literal).
    assert '"Trabajo diurno" * (%B=a)' in stage_out["OEB070$"]["text_variables"]["L"]
    # Log carries only the primary L1 write.
    assert len(log) == 1
    assert log[0].layer is Layer.PARAM_VALUE


# ---- L2 → paired L1 -----------------------------------------------------

def test_l2_on_twin_var_carries_into_parameter_value():
    stage = _oeb070_stage2()
    # Paraphrase $L fragment for %B=b: Nocturno → Noche. Twin is axis B.
    stage_out, log = apply_paraphrase(
        stage, "OEB070$",
        {"var": "L", "condition": "%B=b", "new": "Noche"},
    )
    # 1) Text-var L updated (single-layer L2 semantics preserved).
    l_formula = stage_out["OEB070$"]["text_variables"]["L"]
    assert '"Diurno" * (%B=a)' in l_formula
    assert '"Noche" * (%B=b)' in l_formula
    # 2) Param B value for label "b" updated to "Noche" (paired edit).
    b_values = {v["label"]: v["value"]
                for v in stage_out["OEB070$"]["parameters"]["B"]["values"]}
    assert b_values == {"a": "Diurno", "b": "Noche"}
    # 3) Log: primary L2 + paired L1.
    assert len(log) == 2
    assert log[0].layer is Layer.TEXT_VARIABLE
    assert log[0].type is ModificationType.PARAPHRASE
    assert log[0].original == "Nocturno" and log[0].new == "Noche"
    assert log[1].layer is Layer.PARAM_VALUE
    assert log[1].status == "paired"
    assert log[1].param == "B"
    assert log[1].value == "b"
    assert log[1].original == "Nocturno" and log[1].new == "Noche"


def test_l2_on_bare_referenced_var_no_pair():
    stage = _oeb070_stage2()
    stage["OEB070$"]["text_variables"]["K"] = '"foo" * (%B=a) + "bar" * (%B=b)'
    # $K is not indexed-referenced in resumen/texto → no twin axis.
    stage_out, log = apply_paraphrase(
        stage, "OEB070$",
        {"var": "K", "condition": "%B=a", "new": "baz"},
    )
    # L2 write happened...
    assert '"baz" * (%B=a)' in stage_out["OEB070$"]["text_variables"]["K"]
    # ...but no paired edit; param B untouched.
    assert stage_out["OEB070$"]["parameters"]["B"]["values"][0]["value"] == "Diurno"
    assert len(log) == 1
    assert log[0].layer is Layer.TEXT_VARIABLE


def test_l2_when_param_value_diverges_pair_is_skipped():
    stage = _oeb070_stage2()
    stage["OEB070$"]["parameters"]["B"]["values"][0]["value"] = "Trabajo diurno"
    stage_out, log = apply_paraphrase(
        stage, "OEB070$",
        {"var": "L", "condition": "%B=a", "new": "Día"},
    )
    # L2 write happened...
    assert '"Día" * (%B=a)' in stage_out["OEB070$"]["text_variables"]["L"]
    # ...but param B untouched because current value != original.
    assert stage_out["OEB070$"]["parameters"]["B"]["values"][0]["value"] == "Trabajo diurno"
    assert len(log) == 1


# ---- both directions are additive over the existing dispatcher ---------

def test_paired_edits_do_not_break_multi_rule_apply_l1():
    """The mutator dispatcher runs multiple rules; each should trigger its own
    (optional) paired edit and accumulate the log honestly."""
    from synthetic.mutator import apply_l1
    stage = _oeb070_stage2()
    rules = [
        {"type": "synonym_label", "param": "B", "value": "a", "new": "Día"},
        {"type": "synonym_label", "param": "B", "value": "b", "new": "Noche"},
    ]
    stage_out, log = apply_l1(stage, "OEB070$", rules)
    # 2 primary + 2 paired = 4 entries.
    assert len(log) == 4
    layers = [m.layer for m in log]
    assert layers.count(Layer.PARAM_VALUE) == 2
    assert layers.count(Layer.TEXT_VARIABLE) == 2
