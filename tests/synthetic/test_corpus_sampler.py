"""Sprint 39 — hermetic tests for :mod:`synthetic.corpus_sampler`.

Tiny hand-built fixtures: 2 concepts (``C1$`` with 4 leaves, ``C2$`` with 2
leaves) and a toy pantry of 3 modification types. No real parquet, no LLM.
"""
from __future__ import annotations

import pytest

from synthetic.corpus_sampler import (
    CONDITIONS,
    Budgets,
    LeafInventory,
    build_plan,
    load_budgets,
    plan_report,
)
from synthetic.pantry import ApprovedRewrite, Pantry, Usage
from synthetic.taxonomy import ModificationType


# ----- fixtures -----------------------------------------------------------

C1, C2 = "C1$", "C2$"
# every toy leaf's original text contains every toy rewrite's `original`
# surface form, so compatibility never interferes with the generic tests
TOY_TEXT = "obra con p-alpha p-beta n-alpha n-beta n-solo n-a de base"
LEAVES = {
    C1: [("C1aa", TOY_TEXT), ("C1ab", TOY_TEXT),
         ("C1ba", TOY_TEXT), ("C1bb", TOY_TEXT)],
    C2: [("C2aa", TOY_TEXT), ("C2ab", TOY_TEXT)],
}


def _rewrite(mtype, canonical, ci=0, concepts=(C1, C2), dedup=None):
    return ApprovedRewrite(
        mtype=mtype,
        dedup_key=tuple(dedup) if dedup else (canonical,),
        canonical=canonical,
        candidate_index=ci,
        payload={"original": canonical, "new": f"{canonical}-v{ci}"},
        usages=tuple(Usage(c, None) for c in concepts),
    )


def _toy_pantry():
    """3 types applicable to both concepts, 2 rewrites each, distinct targets."""
    return Pantry(by_type={
        ModificationType.PARAPHRASE: (
            _rewrite(ModificationType.PARAPHRASE, "p-alpha"),
            _rewrite(ModificationType.PARAPHRASE, "p-beta"),
        ),
        ModificationType.REORDER: (
            _rewrite(ModificationType.REORDER, "r-alpha"),
            _rewrite(ModificationType.REORDER, "r-beta"),
        ),
        ModificationType.NUM_TO_TEXT: (
            _rewrite(ModificationType.NUM_TO_TEXT, "n-alpha"),
            _rewrite(ModificationType.NUM_TO_TEXT, "n-beta"),
        ),
    })


def _budgets(seed=39, reuse_cap=None, **overrides):
    targets = {c: 1 for c in CONDITIONS}
    targets.update(overrides)
    return Budgets(seed=seed, targets=targets, reuse_cap=dict(reuse_cap or {}))


def _inventory():
    return LeafInventory(LEAVES)


# ----- tests --------------------------------------------------------------

def test_load_budgets_validates_conditions(tmp_path):
    # the committed default YAML loads and carries the spec constants
    budgets = load_budgets()
    assert budgets.seed == 39
    assert budgets.targets["all_combined"] == 1500
    assert budgets.targets["single_unit_conversion"] == 350
    assert budgets.reuse_cap == {"num_to_text": 20, "unit_expansion": 20,
                                 "unit_conversion": 20}
    # a YAML missing one condition fails loud
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "seed: 39\ntargets:\n"
        + "".join(f"  {c}: 10\n" for c in CONDITIONS if c != "all_combined")
        + "reuse_cap: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="budgets_invalid"):
        load_budgets(bad)
    # a non-positive target fails loud too
    worse = tmp_path / "worse.yaml"
    worse.write_text(
        "seed: 39\ntargets:\n"
        + "".join(f"  {c}: {0 if c == 'all_combined' else 10}\n" for c in CONDITIONS)
        + "reuse_cap: {}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="budgets_invalid"):
        load_budgets(worse)


def test_plan_is_deterministic():
    pantry = _toy_pantry()
    budgets = _budgets(single_paraphrase=4, single_reorder=3,
                       single_num_to_text=2, all_combined=3)
    a = build_plan(pantry, _inventory(), budgets, [C1, C2])
    b = build_plan(pantry, _inventory(), budgets, [C1, C2])
    assert a == b
    assert a  # non-empty


def test_single_condition_uses_one_rewrite_of_its_type():
    pantry = _toy_pantry()
    budgets = _budgets(single_paraphrase=4, single_reorder=3, single_num_to_text=2)
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    singles = [p for p in plan if p.condition.startswith("single_")]
    assert singles
    for pv in singles:
        assert len(pv.rewrites) == 1
        assert pv.rewrites[0].mtype.value == pv.condition[len("single_"):]


def test_all_combined_uses_one_per_applicable_type():
    pantry = _toy_pantry()
    budgets = _budgets(all_combined=4)
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    combined = [p for p in plan if p.condition == "all_combined"]
    assert len(combined) == 4
    for pv in combined:
        assert len(pv.rewrites) == 3  # one per applicable type
        types = [r.mtype for r in pv.rewrites]
        assert len(set(types)) == 3
        dedups = [r.dedup_key for r in pv.rewrites]
        assert len(set(dedups)) == len(dedups)


def test_leaves_unique_within_condition():
    pantry = _toy_pantry()
    budgets = _budgets(single_paraphrase=6, single_reorder=5, all_combined=6)
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    by_condition: dict[str, list[str]] = {}
    for pv in plan:
        by_condition.setdefault(pv.condition, []).append(pv.leaf_item_key)
    for condition, leaves in by_condition.items():
        assert len(leaves) == len(set(leaves)), condition
    # single_paraphrase asked for all 6 leaves — got each exactly once
    assert sorted(by_condition["single_paraphrase"]) == sorted(
        [k for k, _ in LEAVES[C1]] + [k for k, _ in LEAVES[C2]])


def test_reuse_cap_shortfall_reported():
    # one num_to_text rewrite, applicable to C1 only, cap 2, target 5:
    # the slice stops at 2 uses — deficit 3, no cross-type refill.
    pantry = Pantry(by_type={
        ModificationType.NUM_TO_TEXT: (
            _rewrite(ModificationType.NUM_TO_TEXT, "n-solo", concepts=(C1,)),
        ),
    })
    budgets = _budgets(single_num_to_text=5, reuse_cap={"num_to_text": 2})
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    slice_ = [p for p in plan if p.condition == "single_num_to_text"]
    assert len(slice_) == 2
    assert all(p.rewrites[0].mtype is ModificationType.NUM_TO_TEXT for p in slice_)
    report = plan_report(plan, budgets)
    row = report["single_num_to_text"]
    assert row["n"] == 2
    assert row["deficit"] == 3
    assert row["unique_rewrites"] == 1
    assert row["max_reuse"] == 2


def test_reuse_caps_are_per_condition():
    # a thin-type rewrite capped out in its single condition must still be
    # drawable in all_combined (counters reset per condition)
    pantry = Pantry(by_type={
        ModificationType.NUM_TO_TEXT: (
            _rewrite(ModificationType.NUM_TO_TEXT, "n-solo", concepts=(C1,)),
        ),
        ModificationType.PARAPHRASE: (
            _rewrite(ModificationType.PARAPHRASE, "p-alpha", concepts=(C1,)),
        ),
    })
    budgets = _budgets(single_num_to_text=1, all_combined=1,
                       reuse_cap={"num_to_text": 1})
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    single = [p for p in plan if p.condition == "single_num_to_text"]
    combined = [p for p in plan if p.condition == "all_combined"]
    assert len(single) == 1
    assert single[0].rewrites[0].canonical == "n-solo"  # cap 1 fully used
    assert len(combined) == 1
    assert {r.mtype for r in combined[0].rewrites} == {
        ModificationType.PARAPHRASE, ModificationType.NUM_TO_TEXT}


def test_allocation_respects_rewrite_capacity():
    # concept A: 100 leaves but only 1 applicable rewrite (cap 2) -> gets <=2;
    # concept B: 10 leaves, 5 distinct rewrites (cap 2) -> receives the surplus
    a, b = "A1$", "B1$"
    inventory = LeafInventory({
        a: [(f"A1x{i:03d}", "obra n-a") for i in range(100)],
        b: [(f"B1x{i:02d}", "obra n-b0 n-b1 n-b2 n-b3 n-b4") for i in range(10)],
    })
    pantry = Pantry(by_type={
        ModificationType.NUM_TO_TEXT: (
            _rewrite(ModificationType.NUM_TO_TEXT, "n-a", concepts=(a,)),
        ) + tuple(
            _rewrite(ModificationType.NUM_TO_TEXT, f"n-b{i}", concepts=(b,))
            for i in range(5)
        ),
    })
    budgets = _budgets(single_num_to_text=12, reuse_cap={"num_to_text": 2})
    plan = build_plan(pantry, inventory, budgets, [a, b])
    slice_ = [p for p in plan if p.condition == "single_num_to_text"]
    n_a = sum(1 for p in slice_ if p.concept_key == a)
    n_b = sum(1 for p in slice_ if p.concept_key == b)
    assert n_a <= 2
    assert n_b == 10  # surplus redistributed within the condition
    assert n_a + n_b == 12
    assert plan_report(plan, budgets)["single_num_to_text"]["deficit"] == 0


def test_plan_report_counts_type_presence_in_all_combined():
    pantry = _toy_pantry()
    budgets = _budgets(all_combined=4)
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    report = plan_report(plan, budgets)
    presence = report["all_combined"]["type_presence"]
    assert presence == {"num_to_text": 4, "paraphrase": 4, "reorder": 4}
    assert "type_presence" not in report["single_paraphrase"]


def test_l1_rewrite_only_paired_with_matching_leaf():
    # a value rewrite of "Diurno" must never land on a leaf whose original
    # text lacks "Diurno" (it would render as a no-op there)
    inv = LeafInventory({C1: [
        ("C1aa", "trabajo en turno Diurno con medios"),
        ("C1ab", "trabajo en  turno   Diurno con medios"),  # ws-normalized hit
        ("C1ba", "trabajo en turno nocturno con medios"),
        ("C1bb", "trabajo en turno nocturno con medios"),
    ]})
    pantry = Pantry(by_type={
        ModificationType.SYNONYM_LABEL: (
            _rewrite(ModificationType.SYNONYM_LABEL, "turno Diurno",
                     concepts=(C1,)),
        ),
    })
    budgets = _budgets(single_synonym_label=4)
    stats: dict = {}
    plan = build_plan(pantry, inv, budgets, [C1], stats_out=stats)
    slice_ = [p for p in plan if p.condition == "single_synonym_label"]
    assert {p.leaf_item_key for p in slice_} == {"C1aa", "C1ab"}
    report = plan_report(plan, budgets, stats=stats)
    assert report["single_synonym_label"]["n"] == 2
    assert report["single_synonym_label"]["deficit"] == 2
    assert report["single_synonym_label"]["incompatible_skips"] == 2


def test_l2_fragment_compatibility():
    inv = LeafInventory({C1: [
        ("C1aa", "incluso fragmento largo de texto"),
        ("C1ab", "sin nada relevante aqui"),
    ]})
    pantry = Pantry(by_type={
        ModificationType.PARAPHRASE: (
            _rewrite(ModificationType.PARAPHRASE, "fragmento largo",
                     concepts=(C1,)),
        ),
    })
    budgets = _budgets(single_paraphrase=2)
    plan = build_plan(pantry, inv, budgets, [C1])
    slice_ = [p for p in plan if p.condition == "single_paraphrase"]
    assert [p.leaf_item_key for p in slice_] == ["C1aa"]


def test_l3_always_compatible():
    # template-level rewrites (reorder, template_paraphrase) cover every
    # leaf regardless of surface text
    inv = LeafInventory({C1: [("C1aa", "texto cualquiera")]})
    pantry = Pantry(by_type={
        ModificationType.REORDER: (
            _rewrite(ModificationType.REORDER, "no aparece en el texto",
                     concepts=(C1,)),
        ),
        ModificationType.TEMPLATE_PARAPHRASE: (
            _rewrite(ModificationType.TEMPLATE_PARAPHRASE, "tampoco aparece",
                     concepts=(C1,)),
        ),
    })
    budgets = _budgets(single_reorder=1, single_template_paraphrase=1)
    plan = build_plan(pantry, inv, budgets, [C1])
    assert sum(1 for p in plan if p.condition == "single_reorder") == 1
    assert sum(1 for p in plan
               if p.condition == "single_template_paraphrase") == 1


def test_all_combined_skips_incompatible_types_for_leaf():
    inv = LeafInventory({C1: [("C1aa", "contiene p-alpha pero sin numeros")]})
    pantry = Pantry(by_type={
        ModificationType.PARAPHRASE: (
            _rewrite(ModificationType.PARAPHRASE, "p-alpha", concepts=(C1,)),
        ),
        ModificationType.NUM_TO_TEXT: (
            _rewrite(ModificationType.NUM_TO_TEXT, "n-alpha", concepts=(C1,)),
        ),
    })
    budgets = _budgets(all_combined=1)
    stats: dict = {}
    plan = build_plan(pantry, inv, budgets, [C1], stats_out=stats)
    combined = [p for p in plan if p.condition == "all_combined"]
    assert len(combined) == 1
    assert {r.mtype for r in combined[0].rewrites} == {
        ModificationType.PARAPHRASE}  # num_to_text skipped for this leaf
    report = plan_report(plan, budgets, stats=stats)
    assert report["all_combined"]["type_presence"] == {"paraphrase": 1}
    assert report["all_combined"]["incompatible_skips"] == 1


def test_proportional_allocation():
    # C1 has 4 leaves, C2 has 2: a target of 6 splits 4 / 2 (largest
    # remainder; ±1 tolerance for rounding).
    pantry = _toy_pantry()
    budgets = _budgets(single_paraphrase=6)
    plan = build_plan(pantry, _inventory(), budgets, [C1, C2])
    slice_ = [p for p in plan if p.condition == "single_paraphrase"]
    n1 = sum(1 for p in slice_ if p.concept_key == C1)
    n2 = sum(1 for p in slice_ if p.concept_key == C2)
    assert n1 + n2 == 6
    assert abs(n1 - 4) <= 1
    assert abs(n2 - 2) <= 1
