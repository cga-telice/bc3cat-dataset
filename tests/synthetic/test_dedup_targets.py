"""Cross-concept twin de-duplication (drop policy)."""
from __future__ import annotations

import pandas as pd

from synthetic import dedup_targets as d


def _frames():
    # OED020 / OED170 are genuine twins: identical resumen+texto under two concepts.
    long_df = pd.DataFrame([
        {"item_key": "OEB010aa", "parent_key": "OEB010$", "text": "Texto A"},
        {"item_key": "OED020aa", "parent_key": "OED020$", "text": "Texto cim"},
        {"item_key": "OED170aa", "parent_key": "OED170$", "text": "Texto cim"},
        {"item_key": "OED020ab", "parent_key": "OED020$", "text": "Texto cim2"},
        {"item_key": "OED170ab", "parent_key": "OED170$", "text": "Texto cim2"},
    ])
    short_df = pd.DataFrame([
        {"item_key": "OEB010aa", "text": "Res A"},
        {"item_key": "OED020aa", "text": "Res cim"},
        {"item_key": "OED170aa", "text": "Res cim"},
        {"item_key": "OED020ab", "text": "Res cim2"},
        {"item_key": "OED170ab", "text": "Res cim2"},
    ])
    return long_df, short_df


def test_plan_keeps_canonical_first_concept_and_drops_twin():
    plan = d.plan_dedup(*_frames())
    assert plan.drop_leaf_keys == frozenset({"OED170aa", "OED170ab"})
    assert plan.canonical == {"OED170$": "OED020$"}


def test_dedup_target_removes_twin_leaves_from_both_frames():
    long_df, short_df = _frames()
    plan = d.plan_dedup(long_df, short_df)
    lo, sh = d.dedup_target(long_df, short_df, plan)
    assert set(lo["item_key"]) == {"OEB010aa", "OED020aa", "OED020ab"}
    assert set(sh["item_key"]) == {"OEB010aa", "OED020aa", "OED020ab"}
    # every surviving (resumen, texto) now maps to exactly one concept
    ik2p = dict(zip(lo["item_key"], lo["parent_key"]))
    res = dict(zip(sh["item_key"], sh["text"]))
    tex = dict(zip(lo["item_key"], lo["text"]))
    owners: dict = {}
    for k in lo["item_key"]:
        owners.setdefault((res[k], tex[k]), set()).add(ik2p[k])
    assert all(len(v) == 1 for v in owners.values())


def test_dedup_synthetic_drops_items_from_dropped_leaves():
    long_df, short_df = _frames()
    plan = d.plan_dedup(long_df, short_df)
    syn = pd.DataFrame([
        {"item_key": "OEB010aa_syn_1", "original_key": "OEB010aa", "concept_key": "OEB010$"},
        {"item_key": "OED020aa_syn_1", "original_key": "OED020aa", "concept_key": "OED020$"},
        {"item_key": "OED170aa_syn_1", "original_key": "OED170aa", "concept_key": "OED170$"},
        {"item_key": "OED170ab_syn_1", "original_key": "OED170ab", "concept_key": "OED170$"},
    ])
    out, dropped = d.dedup_synthetic(syn, plan)
    assert set(out["item_key"]) == {"OEB010aa_syn_1", "OED020aa_syn_1"}
    assert dropped == {"OED170aa_syn_1", "OED170ab_syn_1"}


def _intra_frames():
    # Same concept OEG010 renders identical text under two leaves (a param axis
    # absent from its templates); OEB010 is unique.
    long_df = pd.DataFrame([
        {"item_key": "OEB010aa", "parent_key": "OEB010$", "text": "Texto A"},
        {"item_key": "OEG010aa", "parent_key": "OEG010$", "text": "Texto cim"},
        {"item_key": "OEG010ab", "parent_key": "OEG010$", "text": "Texto cim"},
    ])
    short_df = pd.DataFrame([
        {"item_key": "OEB010aa", "text": "Res A"},
        {"item_key": "OEG010aa", "text": "Res cim"},
        {"item_key": "OEG010ab", "text": "Res cim"},
    ])
    return long_df, short_df


def test_plan_collapse_keeps_first_leaf_and_maps_the_rest():
    drop, remap = d.plan_collapse(*_intra_frames())
    assert drop == frozenset({"OEG010ab"})
    assert remap == {"OEG010ab": "OEG010aa"}


def test_plan_collapse_rejects_cross_concept_duplicate():
    import pytest
    with pytest.raises(ValueError):
        d.plan_collapse(*_frames())  # OED020/OED170 still cross-concept dup


def test_remap_synthetic_repoints_original_key_without_dropping():
    _, remap = d.plan_collapse(*_intra_frames())
    syn = pd.DataFrame([
        {"item_key": "OEG010ab_syn_1", "original_key": "OEG010ab", "concept_key": "OEG010$"},
        {"item_key": "OEG010aa_syn_1", "original_key": "OEG010aa", "concept_key": "OEG010$"},
    ])
    out, n = d.remap_synthetic(syn, remap)
    assert n == 1 and len(out) == 2
    assert set(out["original_key"]) == {"OEG010aa"}  # ab repointed to aa
