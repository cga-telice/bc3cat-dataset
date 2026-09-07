"""Option A — leaf-proportional budget allocation."""
from __future__ import annotations

import pytest

from synthetic import corpus_sampler as cs


def test_concept_budgets_proportional_floor_cap():
    # A: proportional; B: proportional; C: below floor -> floored (and capped).
    b = cs._concept_budgets({"A": 100, "B": 10, "C": 1},
                            total=100, floor=5, cap_per_leaf=2.0)
    assert b == {"A": 90, "B": 9, "C": 5}


def test_concept_budgets_ignores_zero_leaf_concepts():
    assert cs._concept_budgets({"A": 0, "B": 4}, total=10, floor=2, cap_per_leaf=3.0) == {"B": 10}


def test_split_by_type_sums_to_budget_and_renormalises_over_eligible():
    mix = {c: 0.0 for c in cs.CONDITIONS}
    mix["single_paraphrase"] = 0.3
    mix["all_combined"] = 0.6  # only these two are eligible below
    out = cs._split_by_type(10, ["single_paraphrase", "all_combined"], mix)
    assert sum(out.values()) == 10
    assert out == {"single_paraphrase": 3, "all_combined": 7}


def test_split_by_type_zero_budget_is_empty():
    assert cs._split_by_type(0, ["all_combined"], {"all_combined": 1.0}) == {}


def test_load_budgets_leaf_proportional(tmp_path):
    mix = "\n".join(f"  {c}: 0.1" for c in cs.CONDITIONS)
    (tmp_path / "b.yaml").write_text(
        "seed: 42\nmode: leaf_proportional\ntotal: 5000\nfloor: 5\n"
        "cap_per_leaf: 3.0\ntype_mix:\n" + mix + "\nreuse_cap:\n  num_to_text: 20\n",
        encoding="utf-8")
    b = cs.load_budgets(tmp_path / "b.yaml")
    assert b.mode == "leaf_proportional"
    assert (b.total, b.floor) == (5000, 5)
    assert b.cap_per_leaf == pytest.approx(3.0)
    assert set(b.type_mix) == set(cs.CONDITIONS)
    assert b.targets == {}


def test_load_budgets_leaf_proportional_rejects_bad_type_mix(tmp_path):
    (tmp_path / "b.yaml").write_text(
        "seed: 42\nmode: leaf_proportional\ntotal: 100\nfloor: 5\n"
        "cap_per_leaf: 3.0\ntype_mix:\n  single_paraphrase: 1.0\n",
        encoding="utf-8")
    with pytest.raises(ValueError):
        cs.load_budgets(tmp_path / "b.yaml")
