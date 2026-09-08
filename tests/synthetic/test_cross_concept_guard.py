"""Guard #1 — cross-concept collision guard (corpus-level, pure)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from synthetic import cross_concept_guard as g


def _base():
    # Two genuinely-duplicate concepts (OED020 == OED170) share a leaf — this is a
    # BASELINE property of the source catalogue, not a synthesis defect.
    long_df = pd.DataFrame([
        {"item_key": "OEB010aa", "parent_key": "OEB010$", "text": "Texto canaleta A"},
        {"item_key": "OED020aa", "parent_key": "OED020$", "text": "Texto cim rect"},
        {"item_key": "OED170aa", "parent_key": "OED170$", "text": "Texto cim rect"},
    ])
    short_df = pd.DataFrame([
        {"item_key": "OEB010aa", "text": "Canaleta A"},
        {"item_key": "OED020aa", "text": "Cim rect"},
        {"item_key": "OED170aa", "text": "Cim rect"},
    ])
    return g.build_base_index(long_df, short_df)


def test_baseline_index_maps_shared_text_to_multiple_concepts():
    idx = _base()
    assert idx.owners("resumen", "Cim rect") == frozenset({"OED020$", "OED170$"})
    assert idx.owners("resumen", "Canaleta A") == frozenset({"OEB010$"})
    assert idx.self_text("OED020aa", "texto") == "Texto cim rect"


def test_audit_flags_introduced_and_inherited_separately():
    idx = _base()
    items = pd.DataFrame([
        # A) INTRODUCED: an OEB010 item whose resumen was rewritten to a string that
        #    is actually OED020/OED170's base leaf -> newly matches a different concept.
        {"item_key": "OEB010aa_syn_1", "original_key": "OEB010aa",
         "concept_key": "OEB010$", "resumen": "Cim rect", "texto": "Texto canaleta A"},
        # B) INHERITED: an OED020 item whose resumen is unchanged from its own base;
        #    it collides with OED170 only because the source catalogue already does.
        {"item_key": "OED020aa_syn_1", "original_key": "OED020aa",
         "concept_key": "OED020$", "resumen": "Cim rect", "texto": "Texto cim rect"},
        # C) CLEAN: reworded to something no other concept owns.
        {"item_key": "OEB010aa_syn_2", "original_key": "OEB010aa",
         "concept_key": "OEB010$", "resumen": "Conducto A reworded", "texto": "Texto canaleta A"},
    ])
    cols = g.audit_corpus(items, idx)
    introduced = g.introduced(cols)
    assert {c.kind for c in cols} == {"introduced", "inherited"}
    assert len(introduced) == 1
    only = introduced[0]
    assert only.item_key == "OEB010aa_syn_1"
    assert only.field == "resumen"
    assert only.concept == "OEB010$"
    assert only.other_concepts == ("OED020$", "OED170$")


def test_classify_unchanged_field_on_twin_is_inherited_not_introduced():
    # The template-level bug: a RESUMEN rewrite leaves texto untouched; that
    # untouched texto still equals the genuine twin OED170's base texto. It must
    # be classified `inherited` (value == own base), never `introduced`.
    idx = _base()
    c = g.classify(idx, item_key="OED020aa", base_key="OED020aa",
                   concept="OED020$", field="texto", val="Texto cim rect")
    assert c is not None and c.kind == "inherited"
    assert c.other_concepts == ("OED170$",)
    # A genuinely paraphrased texto that now matches a foreign concept IS introduced.
    c2 = g.classify(idx, item_key="OEB010aa", base_key="OEB010aa",
                    concept="OEB010$", field="texto", val="Texto cim rect")
    assert c2 is not None and c2.kind == "introduced"
    # No foreign owner -> no collision.
    assert g.classify(idx, "k", "OEB010aa", "OEB010$", "resumen", "Canaleta A") is None


def test_clean_corpus_has_zero_introduced():
    idx = _base()
    items = pd.DataFrame([
        {"item_key": "x", "original_key": "OEB010aa", "concept_key": "OEB010$",
         "resumen": "Something entirely new", "texto": "Also new"},
    ])
    assert g.introduced(g.audit_corpus(items, idx)) == []
