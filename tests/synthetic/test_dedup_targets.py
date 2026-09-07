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
