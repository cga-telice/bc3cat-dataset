"""Sprint 31 — digest generator with condition-binding leaf selector.

F1-review §4.3 finding: the hand-built F1_PILOT_REVIEW_DIGEST.md always
picked the minimal leaf (`OEB070aaaa`), which for many variants does NOT
carry the parameter value the modification touched. Result: the reviewer
literally cannot see what changed in ~half the entries.

The new selector picks a leaf whose parameter labels bind to the modified
conditions. E.g., for a mod on `%C=c`, the leaf's third-position label is
`c`; for a mod on `param B value "b"`, the leaf's second-position label is
`b`.
"""

from __future__ import annotations

import pytest

from synthetic import digest


# ---- bindings extraction ------------------------------------------------


def test_bindings_from_l1_rule():
    rule = {"type": "synonym_label", "param": "B", "value": "b", "new": "Noche"}
    assert digest.bindings_from_rule(rule) == {"B": "b"}


def test_bindings_from_l2_rule_bare_condition():
    rule = {"type": "paraphrase", "var": "L", "condition": "%B=a", "new": "Día"}
    assert digest.bindings_from_rule(rule) == {"B": "a"}


def test_bindings_from_l2_rule_quoted_condition():
    rule = {"type": "expansion", "var": "L", "condition": '%B="c"', "new": "..."}
    assert digest.bindings_from_rule(rule) == {"B": "c"}


def test_bindings_from_l3_rule_returns_empty():
    # omission / reorder don't bind to a specific parameter value.
    assert digest.bindings_from_rule({"type": "omission", "field": "RESUMEN"}) == {}
    assert digest.bindings_from_rule({"type": "reorder", "field": "TEXTO"}) == {}


def test_bindings_merged_over_multiple_rules():
    rules = [
        {"type": "synonym_label", "param": "B", "value": "b"},
        {"type": "paraphrase", "var": "M", "condition": "%C=c"},
    ]
    assert digest.merged_bindings(rules) == {"B": "b", "C": "c"}


# ---- leaf selection ----------------------------------------------------


_SORTED_AXES = ["A", "B", "C", "D"]
_PREFIX = "OEB070"
# 24 concrete leaves is enough to exercise the selector; ordering aabb…
_LEAVES = [
    "OEB070aaaa", "OEB070aaab", "OEB070aaba", "OEB070aabb",
    "OEB070abaa", "OEB070abab", "OEB070abba", "OEB070abbb",
    "OEB070baaa", "OEB070baab", "OEB070baba", "OEB070babb",
    "OEB070bbaa", "OEB070bbab", "OEB070bbba", "OEB070bbbb",
    # positions %B=c, %C=c leaves for tests below
    "OEB070acba", "OEB070acbb", "OEB070acca", "OEB070accb",
    "OEB070aabc",
]


def test_select_leaf_binds_to_axis_b_value_b():
    got = digest.select_representative_leaf(
        _LEAVES, concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
        bindings={"B": "b"},
    )
    # position 1 (axis B) must be 'b'; alphabetically first match.
    assert got == "OEB070abaa"


def test_select_leaf_binds_multiple_axes():
    got = digest.select_representative_leaf(
        _LEAVES, concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
        bindings={"B": "b", "C": "b"},
    )
    # positions 1 = 'b', 2 = 'b' → OEB070abba (first match).
    assert got == "OEB070abba"


def test_select_leaf_binds_axis_c_value_c():
    got = digest.select_representative_leaf(
        _LEAVES, concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
        bindings={"C": "c"},
    )
    # position 2 = 'c' → first is OEB070aaca... but that's not in _LEAVES.
    # The first match in _LEAVES is OEB070acba (a,c,b,a) — nope, position 2 is 'b'.
    # Actually OEB070aabc has position 2 = 'b', not 'c'.
    # Let me re-scan: which leaves have position 2 == 'c'?
    # OEB070acca (a,c,c,a), OEB070accb (a,c,c,b) — those match. First alphabetically:
    assert got == "OEB070acca"


def test_select_leaf_falls_back_to_minimal_when_no_binding():
    got = digest.select_representative_leaf(
        _LEAVES, concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
        bindings={},
    )
    # No bindings → alphabetically smallest.
    assert got == "OEB070aaaa"


def test_select_leaf_falls_back_when_no_match_available():
    got = digest.select_representative_leaf(
        _LEAVES, concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
        bindings={"A": "z"},   # no leaf has 'z' anywhere
    )
    # Fall back to alphabetically smallest — do not raise.
    assert got == "OEB070aaaa"


def test_select_leaf_stem_ignores_syn_suffix():
    """Item keys carry a `_syn_<variant_id>` suffix; the selector matches on
    the stem alone."""
    keys = [
        "OEB070aaaa_syn_variant_x",
        "OEB070abaa_syn_variant_x",
    ]
    got = digest.select_representative_leaf(
        keys, concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
        bindings={"B": "b"},
    )
    assert got == "OEB070abaa_syn_variant_x"


# ---- end-to-end variant rendering --------------------------------------


def test_render_variant_entry_picks_binding_leaf_and_formats_markdown():
    variant = {
        "variant_id": "single_L1_synonym_label_abc",
        "rules": [
            {"type": "synonym_label", "param": "B", "value": "b",
             "new": "Horario de luz solar", "original": "Nocturno"},
        ],
    }
    materialized = {
        "OEB070aaaa_syn_single_L1_synonym_label_abc": {
            "resumen": "Canal ($L(%B)/...)", "texto": "Trabajo: Diurno",
        },
        "OEB070abaa_syn_single_L1_synonym_label_abc": {
            "resumen": "Canal (Horario de luz solar/...)",
            "texto": "Trabajo: Horario de luz solar",
        },
    }
    out = digest.render_variant_entry(
        n=1, variant=variant, materialized=materialized,
        concept_prefix=_PREFIX, sorted_axes=_SORTED_AXES,
    )
    # Uses the axis-B=b leaf, not the minimal one.
    assert "OEB070abaa_syn_single_L1_synonym_label_abc" in out
    assert "OEB070aaaa" not in out.split("**item_key:**")[1].split("\n")[0]
    # Records the modification
    assert "synonym_label" in out
    assert "Nocturno" in out and "Horario de luz solar" in out
    # Renders both fields
    assert "resumen" in out.lower() and "texto" in out.lower()
