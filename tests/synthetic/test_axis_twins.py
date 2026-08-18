"""Sprint 31 — axis↔text-variable twin discovery.

F1-review found that `OEB070$` renders each parameter axis through *two
independent variables*: the raw parameter value ($B, $C, $D in `texto`) and
an indexed text-variable ($L(%B), $M(%C), $N(%D) in `resumen`). Modifying
only one desyncs the query and the document. The mutator refactor pairs
L1 + L2 edits automatically, and needs a per-concept map of which
text-variable is the twin of which parameter axis.

`axis_twins` derives that map from the concept's `resumen`/`texto`
templates via `l2_repr.derive_var_axis_map` (single source of truth for
indexed references). Ambiguous cases (two text-vars indexed on the same
axis) yield no twin — pairing falls back to single-layer.
"""

from __future__ import annotations

import pytest

from synthetic import axis_twins


# OEB070-shaped: `$L(%B)`, `$M(%C)`, `$N(%D)` in resumen; raw `$B $C $D` in texto.
_OEB070 = {
    "resumen": (
        "Suministro y ejecución de canalización de $A tubo(s) "
        "($L(%B)/$M(%C)/$N(%D))"
    ),
    "texto": (
        "Suministro y ejecución de canalización de $A tubo(s). "
        "Trabajo: $B  Banda: $C  Condiciones: $D"
    ),
}


def test_axis_twin_map_oeb070_shape():
    m = axis_twins.axis_twin_map(_OEB070)
    assert m == {"B": "L", "C": "M", "D": "N"}


def test_var_twin_map_oeb070_shape():
    m = axis_twins.var_twin_map(_OEB070)
    assert m == {"L": "B", "M": "C", "N": "D"}


def test_axis_with_no_indexed_ref_has_no_twin():
    m = axis_twins.axis_twin_map(_OEB070)
    # Axis A appears as bare $A in both templates — not a twin candidate.
    assert "A" not in m


def test_bare_referenced_var_absent_from_var_twin_map():
    concept = {"resumen": "$K here", "texto": "$K there"}
    assert axis_twins.var_twin_map(concept) == {}
    assert axis_twins.axis_twin_map(concept) == {}


def test_ambiguous_axis_two_vars_indexed_on_same_axis_yields_no_twin():
    # Contrived: two text-vars both indexed on axis B → no unique twin.
    concept = {"resumen": "$L(%B) and $P(%B)", "texto": "..."}
    m = axis_twins.axis_twin_map(concept)
    assert "B" not in m


def test_var_map_still_records_unambiguous_var_axis_direction():
    # Same contrived case — from the var side, each var maps unambiguously
    # to axis B (each var appears only against %B).
    concept = {"resumen": "$L(%B) and $P(%B)", "texto": "..."}
    m = axis_twins.var_twin_map(concept)
    assert m == {"L": "B", "P": "B"}


def test_axis_twin_functions():
    """Convenience lookups return None on missing / ambiguous, string on hit."""
    assert axis_twins.axis_twin(_OEB070, "B") == "L"
    assert axis_twins.axis_twin(_OEB070, "C") == "M"
    assert axis_twins.axis_twin(_OEB070, "A") is None      # no indexed ref
    assert axis_twins.var_twin(_OEB070, "L") == "B"
    assert axis_twins.var_twin(_OEB070, "M") == "C"
    assert axis_twins.var_twin(_OEB070, "Z") is None       # unknown var


def test_empty_concept_yields_empty_maps():
    assert axis_twins.axis_twin_map({}) == {}
    assert axis_twins.var_twin_map({}) == {}


# ========================================================================
# Paired-edit primitives — carry an L1 rewrite into its twin text-var, and
# an L2 rewrite into its twin parameter value.
# ========================================================================


def _oeb070_concept():
    """Fresh mutable OEB070-shaped concept with parameters + text_variables
    in the formula-string form the L1/L2 layers consume."""
    return {
        "resumen": "de $A tubo(s) ($L(%B)/$M(%C)/$N(%D))",
        "texto": "de $A tubo(s). Trabajo: $B  Banda: $C  Condiciones: $D",
        "parameters": {
            "A": {"label": "N", "values": [{"label": "a", "value": "1"}]},
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
    }


def test_pair_l1_into_text_var_updates_twin_fragment_when_it_matches():
    concept = _oeb070_concept()
    # L1: rename axis B value "a" from "Diurno" → "Día"
    pair = axis_twins.pair_l1_into_text_var(
        concept, param="B", value_label="a", original="Diurno", new="Día",
    )
    assert pair == {"var": "L", "condition": "%B=a", "original": "Diurno", "new": "Día"}
    # And the concept's text_variable L now carries the change.
    assert '"Día" * (%B=a)' in concept["text_variables"]["L"]
    assert '"Nocturno" * (%B=b)' in concept["text_variables"]["L"]


def test_pair_l1_no_twin_axis_returns_none():
    concept = _oeb070_concept()
    # Axis A is not indexed-referenced ($A bare) → no twin.
    assert axis_twins.pair_l1_into_text_var(
        concept, param="A", value_label="a", original="1", new="uno",
    ) is None
    # And nothing in text_variables changed.
    assert concept["text_variables"]["L"].startswith('"Diurno"')


def test_pair_l1_fragment_diverges_from_original_returns_none():
    concept = _oeb070_concept()
    # Manually diverge $L's fragment from param B value.
    concept["text_variables"]["L"] = '"Trabajo diurno" * (%B=a) + "Nocturno" * (%B=b)'
    # L1 rewrite of param B value "Diurno" → "Día"; $L fragment != "Diurno".
    assert axis_twins.pair_l1_into_text_var(
        concept, param="B", value_label="a", original="Diurno", new="Día",
    ) is None
    # $L untouched.
    assert '"Trabajo diurno" * (%B=a)' in concept["text_variables"]["L"]


def test_pair_l2_into_param_updates_twin_value_when_it_matches():
    concept = _oeb070_concept()
    # L2: rewrite $L fragment for %B=b from "Nocturno" → "Noche"
    pair = axis_twins.pair_l2_into_param(
        concept, var="L", condition="%B=b", original="Nocturno", new="Noche",
    )
    assert pair == {"param": "B", "value_label": "b", "original": "Nocturno", "new": "Noche"}
    # Param B value for label "b" now says "Noche".
    b_values = {v["label"]: v["value"] for v in concept["parameters"]["B"]["values"]}
    assert b_values == {"a": "Diurno", "b": "Noche"}


def test_pair_l2_no_twin_var_returns_none():
    concept = _oeb070_concept()
    # $K would be a bare-referenced var — no axis pairing.
    concept["text_variables"]["K"] = '"foo" * (%B=a)'
    # Bare $K → no twin axis.
    assert axis_twins.pair_l2_into_param(
        concept, var="K", condition="%B=a", original="foo", new="bar",
    ) is None


def test_pair_l2_value_diverges_from_original_returns_none():
    concept = _oeb070_concept()
    # Manually diverge param B a's value from $L's fragment.
    concept["parameters"]["B"]["values"][0]["value"] = "Trabajo diurno"
    # L2 says the fragment was "Diurno"; the param value is now "Trabajo diurno" — no pair.
    assert axis_twins.pair_l2_into_param(
        concept, var="L", condition="%B=a", original="Diurno", new="Día",
    ) is None
    # Param B value untouched.
    assert concept["parameters"]["B"]["values"][0]["value"] == "Trabajo diurno"


def test_pair_l2_condition_with_quoted_form_still_parses():
    concept = _oeb070_concept()
    # Some formulas use %B="a" (quoted). The pair helper should still identify axis B.
    concept["text_variables"]["L"] = '"Diurno" * (%B="a") + "Nocturno" * (%B="b")'
    # Also update the axis_twin lookup: template still uses $L(%B), so twin_map is unchanged.
    pair = axis_twins.pair_l2_into_param(
        concept, var="L", condition='%B="a"', original="Diurno", new="Día",
    )
    assert pair == {"param": "B", "value_label": "a", "original": "Diurno", "new": "Día"}


def test_pair_l1_ambiguous_condition_not_found_returns_none():
    concept = _oeb070_concept()
    # value_label "z" doesn't exist in $L's formula.
    assert axis_twins.pair_l1_into_text_var(
        concept, param="B", value_label="z", original="Diurno", new="Día",
    ) is None
