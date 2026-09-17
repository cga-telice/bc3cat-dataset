"""E3 — hermetic tests for :mod:`synthetic.dose_ladder`.

Tiny fixtures: 2 concepts, leaves with known (axis, value) pairs, and a toy
pantry. No real parquet, no LLM, no bc3param.
"""
from __future__ import annotations

from collections import Counter

import pytest

from synthetic.corpus_sampler import LeafInventory
from synthetic.pantry import ApprovedRewrite, Pantry, Usage
from synthetic.target_scanner import ChapterInventory, TargetUsage, UniqueTarget
from synthetic.taxonomy import ModificationType

MT = ModificationType
C1, C2 = "C1$", "C2$"
NINE_SUBSET = (
    MT.PARAPHRASE, MT.EXPANSION, MT.TEMPLATE_PARAPHRASE, MT.SYNONYM_LABEL,
    MT.COMPRESSION, MT.REORDER,
)


def _target(dedup, concepts=(C1,)):
    return UniqueTarget(
        dedup_key=tuple(dedup),
        canonical=" / ".join(str(x) for x in dedup),
        usages=tuple(TargetUsage(c, None, "") for c in concepts),
    )


def _chapter_inventory(by_type):
    return ChapterInventory(concept_keys=(C1, C2), by_type=dict(by_type))


def test_structural_types_l1_requires_the_leaf_to_select_the_pair():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({
        MT.NUM_TO_TEXT: (_target(("N TUBOS", "5")),),
        MT.UNIT_CONVERSION: (_target(("SECCION", "150 mm2")),),
    })
    # the leaf selects N TUBOS=5 but not SECCION=150 mm2. The axis label must
    # match the dedup_key's case: both normalisers (corpus_sampler._norm_ws,
    # target_scanner._norm) fold whitespace only, never case, and in real data
    # both sides read the same catalogue label.
    got = structural_types(
        inv, C1, leaf_text="canalizacion de 5 tubos", leaf_axis_values=(("N TUBOS", "5"),),
    )
    assert got == frozenset({MT.NUM_TO_TEXT})
    assert isinstance(got, frozenset)  # pin the return type, not just its contents


def test_structural_types_l3_applies_to_every_leaf():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({MT.REORDER: (_target(("TEXTO", "plantilla")),)})
    got = structural_types(inv, C1, leaf_text="cualquier cosa", leaf_axis_values=())
    assert got == frozenset({MT.REORDER})


def test_structural_types_ignores_other_concepts():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({
        MT.REORDER: (_target(("TEXTO", "plantilla"), concepts=(C2,)),),
    })
    assert structural_types(inv, C1, leaf_text="x", leaf_axis_values=()) == frozenset()


def test_structural_types_ignores_excluded_types():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({
        MT.OMISSION: (_target(("TEXTO", "plantilla", "$L"), concepts=(C1,)),),
    })
    assert structural_types(inv, C1, leaf_text="x", leaf_axis_values=()) == frozenset()


def test_compatibility_ignores_the_fields_as_rewrite_leaves_empty():
    """`structural_types` fabricates an ApprovedRewrite whose `canonical`,
    `candidate_index` and `usages` are empty sentinels, so the compatibility
    rule must not read them. If this fails, `_as_rewrite`'s shortcut is no
    longer safe and the module needs a real surface-matching entry point."""
    from synthetic.corpus_sampler import is_compatible

    kwargs = dict(mtype=MT.NUM_TO_TEXT, dedup_key=("N TUBOS", "5"),
                  payload={"original": "5"})
    bare = ApprovedRewrite(canonical="", candidate_index=-1, usages=(), **kwargs)
    rich = ApprovedRewrite(canonical="N TUBOS / 5", candidate_index=7,
                           usages=(Usage(C1, None),), **kwargs)
    leaf = ("canalizacion de 5 tubos", (("N TUBOS", "5"),))
    assert is_compatible(bare, *leaf) == is_compatible(rich, *leaf) is True


def _rewrite(mtype, original, ci=0, concepts=(C1,), dedup=None):
    return ApprovedRewrite(
        mtype=mtype,
        dedup_key=tuple(dedup) if dedup else (original,),
        canonical=original,
        candidate_index=ci,
        payload={"original": original, "new": f"{original}-v{ci}"},
        usages=tuple(Usage(c, None) for c in concepts),
    )


def test_compatible_rewrites_keeps_only_the_compatible_ones():
    from synthetic.dose_ladder import compatible_rewrites

    pantry = Pantry(by_type={
        MT.PARAPHRASE: (_rewrite(MT.PARAPHRASE, "fragmento-a"),),
        MT.COMPRESSION: (_rewrite(MT.COMPRESSION, "ausente-del-texto"),),
    })
    applicable = pantry.for_concept(C1)
    got = compatible_rewrites(
        applicable, leaf_text="obra con fragmento-a de base", leaf_axis_values=(),
    )
    assert set(got) == {MT.PARAPHRASE}
    assert got[MT.PARAPHRASE] == (pantry.by_type[MT.PARAPHRASE][0],)


def test_compatible_rewrites_signature_is_cap_free():
    """A reuse cap must not enter this function: availability is a population
    descriptor, caps are per-run accounting. Assert the parameter set EXACTLY,
    so a future cap parameter under any name is caught."""
    from synthetic.dose_ladder import compatible_rewrites
    import inspect

    assert set(inspect.signature(compatible_rewrites).parameters) == {
        "applicable", "leaf_text", "leaf_axis_values",
    }


def test_load_dose_budgets_reads_and_validates(tmp_path):
    from synthetic.dose_ladder import load_dose_budgets

    p = tmp_path / "dose.yaml"
    p.write_text(
        "seed: 42\n"
        "per_count: 600\n"
        "structural_threshold: 6\n"
        "candidate_cap: 1500\n"
        "reuse_cap:\n"
        "  num_to_text: 20\n",
        encoding="utf-8",
    )
    b = load_dose_budgets(p)
    assert (b.seed, b.per_count, b.structural_threshold, b.candidate_cap) == (42, 600, 6, 1500)
    assert b.reuse_cap == {"num_to_text": 20}


def test_load_dose_budgets_rejects_a_threshold_below_the_ladder(tmp_path):
    from synthetic.dose_ladder import LADDER_MAX, load_dose_budgets

    p = tmp_path / "dose.yaml"
    p.write_text(
        f"seed: 42\nper_count: 10\nstructural_threshold: {LADDER_MAX - 1}\n"
        "candidate_cap: 100\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dose_budgets_invalid"):
        load_dose_budgets(p)


def test_load_dose_budgets_rejects_unknown_reuse_cap_type(tmp_path):
    from synthetic.dose_ladder import load_dose_budgets

    p = tmp_path / "dose.yaml"
    p.write_text(
        "seed: 42\nper_count: 10\nstructural_threshold: 6\ncandidate_cap: 100\n"
        "reuse_cap:\n  no_such_type: 5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dose_budgets_invalid"):
        load_dose_budgets(p)


def test_dose_budgets_to_driver_budgets_has_one_target_per_rung():
    from synthetic.dose_ladder import LADDER_MAX, DoseBudgets

    b = DoseBudgets(seed=1, per_count=7, structural_threshold=6, candidate_cap=10,
                    reuse_cap={})
    drv = b.to_driver_budgets()
    assert drv.targets == {f"dose_{k}": 7 for k in range(1, LADDER_MAX + 1)}
    assert drv.seed == 1


def test_effective_pool_min_falls_back_to_per_count():
    """Both committed configs omit `pool_min`, so the fallback is the branch
    that actually runs; and Task 11 feeds this to `select_pool`, where a wrong
    value would look like "not enough leaves" rather than an obvious error."""
    import dataclasses
    from synthetic.dose_ladder import DoseBudgets

    b = DoseBudgets(seed=1, per_count=7, structural_threshold=6,
                    candidate_cap=10, reuse_cap={})
    assert b.effective_pool_min == 7
    assert dataclasses.replace(b, pool_min=3).effective_pool_min == 3


def _toy_setup():
    """2 conceptos; C1 con 3 hojas que admiten 3 tipos, C2 con 1 hoja que admite 1."""
    text = "obra frag-a frag-b tpl"
    inventory = LeafInventory({
        C1: [(f"C1a{i}", text, (("eje", "v"),)) for i in "abc"],
        C2: [("C2aa", "otra obra", ())],
    })
    pantry = Pantry(by_type={
        MT.PARAPHRASE: (_rewrite(MT.PARAPHRASE, "frag-a", concepts=(C1,)),),
        MT.COMPRESSION: (_rewrite(MT.COMPRESSION, "frag-b", concepts=(C1,)),),
        MT.REORDER: (
            _rewrite(MT.REORDER, "tpl", concepts=(C1,), dedup=("TEXTO", "tpl")),
            _rewrite(MT.REORDER, "tpl2", concepts=(C2,), dedup=("TEXTO", "tpl2")),
        ),
    })
    return inventory, pantry


def test_candidate_leaves_applies_the_structural_threshold_and_cap():
    from synthetic.dose_ladder import candidate_leaves

    inventory, _ = _toy_setup()
    inv = _chapter_inventory({
        MT.PARAPHRASE: (_target(("frag-a",)),),
        MT.COMPRESSION: (_target(("frag-b",)),),
        MT.REORDER: (_target(("TEXTO", "tpl")),),
    })
    # C1 is the only qualifying concept here (C2's single leaf admits just 1
    # type, below the threshold), so the per-concept allocation collapses to
    # the same prefix a plain truncation would have picked.
    got = candidate_leaves(inv, inventory, threshold=3, cap=2)
    assert got == ("C1aa", "C1ab")          # sorted, capped, C2 excluded (1 type)
    assert candidate_leaves(inv, inventory, threshold=4, cap=10) == ()


def test_candidate_leaves_spreads_the_cap_across_concepts():
    """The cap must not be a prefix of the sorted leaf keys: those start with
    the concept code, so truncation would spend the whole budget on the
    alphabetically-first concepts and leave the rest of the chapter out of
    the pool the consumer partitions by concept."""
    from synthetic.dose_ladder import candidate_leaves

    text = "obra frag-a frag-b tpl"
    inventory = LeafInventory({
        C1: [(f"C1a{i:02d}", text, ()) for i in range(10)],
        C2: [(f"C2a{i:02d}", text, ()) for i in range(10)],
    })
    inv = _chapter_inventory({
        MT.PARAPHRASE: (_target(("frag-a",), concepts=(C1, C2)),),
        MT.COMPRESSION: (_target(("frag-b",), concepts=(C1, C2)),),
        MT.REORDER: (_target(("TEXTO", "tpl"), concepts=(C1, C2)),),
    })
    got = candidate_leaves(inv, inventory, threshold=3, cap=6)
    assert len(got) == 6
    # both concepts represented, not six leaves of C1 and none of C2
    assert len({k[:2] for k in got}) == 2


def test_build_probe_plan_is_one_single_modification_per_leaf_and_type():
    from synthetic.dose_ladder import build_probe_plan

    inventory, pantry = _toy_setup()
    plan = build_probe_plan(pantry, inventory, ("C1aa", "C1ab"))
    assert {p.condition for p in plan} == {
        "probe_paraphrase", "probe_compression", "probe_reorder",
    }
    assert all(len(p.rewrites) == 1 for p in plan)
    assert len(plan) == 6                    # 2 leaves x 3 types
    # a leaf never repeats within a condition
    for cond in {p.condition for p in plan}:
        leaves = [p.leaf_item_key for p in plan if p.condition == cond]
        assert len(leaves) == len(set(leaves))


def test_build_probe_plan_is_deterministic():
    from synthetic.dose_ladder import build_probe_plan

    inventory, pantry = _toy_setup()
    a = build_probe_plan(pantry, inventory, ("C1aa", "C1ab"))
    b = build_probe_plan(pantry, inventory, ("C1aa", "C1ab"))
    key = lambda pl: [(p.condition, p.leaf_item_key, tuple(r.uid for r in p.rewrites)) for p in pl]
    assert key(a) == key(b)


def test_nested_order_prefixes_are_the_rungs():
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(20)}
    order = nested_order(admitted, seed=42)
    for leaf, types in order.items():
        assert len(types) == LADDER_MAX
        assert len(set(types)) == LADDER_MAX            # no repeats
        assert set(types) <= admitted[leaf]
        for k in range(1, LADDER_MAX):
            assert set(types[:k]) < set(types[:k + 1])  # strictly nested


def test_nested_order_is_deterministic():
    from synthetic.dose_ladder import nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(20)}
    assert nested_order(admitted, seed=42) == nested_order(admitted, seed=42)
    assert nested_order(admitted, seed=43) != nested_order(admitted, seed=42)


def test_nested_order_balances_the_top_cell_exactly():
    """Stage 1 balances WHICH types ride each ladder, and the top cell is
    exactly that: presence(t, LADDER_MAX) = n_leaves - n_leaves_excluding_t.
    With a uniform admitted set and n divisible by the type count, the optimum
    is reachable, so anything but an exact split means stage 1 is not working.
    """
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(180)}
    order = nested_order(admitted, seed=42)
    presence = Counter(t for types in order.values() for t in types)
    assert set(presence) == set(NINE_SUBSET)
    assert max(presence.values()) == min(presence.values())


def test_nested_order_keeps_every_cell_near_even():
    """Their §3, achievable half. Cells below the top cannot be exactly even —
    the positions are correlated, since what a leaf places early constrains
    what remains — so this pins that the residual spread stays small relative
    to the cell, not that it is zero. The tolerance is a few leaves against
    cells of order a hundred; its purpose is to catch a mechanism that has
    stopped balancing, not to certify optimality. Whether a type is
    systematically favoured is a separate question, measured across seeds by
    `test_nested_order_has_no_systematic_per_type_bias`.
    """
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(180)}
    order = nested_order(admitted, seed=42)
    for k in range(1, LADDER_MAX + 1):
        presence = Counter(t for types in order.values() for t in types[:k])
        assert set(presence) == set(NINE_SUBSET)
        mean = sum(presence.values()) / len(presence)
        assert max(presence.values()) - min(presence.values()) <= max(2, 0.05 * mean)


def test_nested_order_has_no_systematic_per_type_bias():
    """Their §3, stated so it can actually be measured.

    Averaged over many seeds, every type's presence at a rung must sit close
    to the cell mean. Spread under a single seed is noise — averaging shrinks
    it by roughly sqrt(n_seeds) — while a type that is systematically favoured
    survives the average. That is the failure their §3 names (in the existing
    stacked set `template_paraphrase` rides 100 % of items), and it is what
    this pins.

    Deliberately NOT phrased as "which type is most present": with inclusion
    balanced exactly, cells tie outright under most seeds, and on a tie the
    "most present" type is decided by sort order rather than by anything this
    function did.
    """
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(180)}
    seeds = tuple(range(1, 13))
    for k in range(1, LADDER_MAX + 1):
        totals: Counter = Counter()
        for seed in seeds:
            for types in nested_order(admitted, seed).values():
                totals.update(types[:k])
        assert set(totals) == set(NINE_SUBSET)
        means = {t: totals[t] / len(seeds) for t in NINE_SUBSET}
        cell_mean = sum(means.values()) / len(means)
        worst = max(abs(m - cell_mean) for m in means.values())
        assert worst <= 0.05 * cell_mean, (
            f"rung {k}: per-type mean presence {means} deviates by {worst:.2f} "
            f"from the cell mean {cell_mean:.2f}"
        )


def test_nested_order_rejects_a_leaf_that_cannot_fill_the_ladder():
    from synthetic.dose_ladder import DoseLadderError, nested_order

    with pytest.raises(DoseLadderError, match="ladder_too_deep"):
        nested_order({"L1": frozenset(list(NINE_SUBSET)[:2])}, seed=42)


def test_nested_order_handles_a_leaf_admitting_exactly_the_ladder_depth():
    """No exclusion is possible at exactly LADDER_MAX admitted types: the
    ladder must be those types, in some order, with no error."""
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    exact = frozenset(NINE_SUBSET[:LADDER_MAX])
    order = nested_order({"L000": exact}, seed=42)
    assert set(order["L000"]) == set(exact)
    assert len(order["L000"]) == LADDER_MAX


def test_nested_order_handles_non_uniform_admitted_sets():
    """Real data: leaves admit different numbers of types. Every leaf must
    still get a full ladder drawn only from what IT admits."""
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {}
    for i in range(30):
        size = LADDER_MAX + (i % 2)          # alternate 5 and 6 admitted types
        admitted[f"L{i:03d}"] = frozenset(NINE_SUBSET[:size])
    order = nested_order(admitted, seed=42)
    assert set(order) == set(admitted)
    for leaf, types in order.items():
        assert len(types) == LADDER_MAX
        assert len(set(types)) == LADDER_MAX
        assert set(types) <= admitted[leaf]


def test_select_pool_takes_the_deepest_level_that_still_fills():
    """Single concept here: this test pins the DEPTH-selection policy, not
    the concept spread (that is `test_select_pool_spreads_the_pool_across_
    concepts`), so every leaf maps to the same concept and `allocate`
    collapses to a plain sorted take — depth and pool size are unaffected
    by spreading."""
    from synthetic.dose_ladder import select_pool

    avail = {}
    for i in range(10):                      # 10 leaves admit 8 types
        avail[f"D8_{i:02d}"] = frozenset(list(NINE_SUBSET)[:6]) | {MT.NUM_TO_TEXT, MT.UNIT_EXPANSION}
    for i in range(50):                      # 50 more admit 6
        avail[f"D6_{i:02d}"] = frozenset(NINE_SUBSET)
    concept_of = {leaf: C1 for leaf in avail}
    depth, pool = select_pool(avail, concept_of, pool_min=40, min_depth=6)
    assert depth == 6                        # 8 would only give 10 leaves
    assert len(pool) == 40
    assert pool == tuple(sorted(pool))       # deterministic, sorted


def test_select_pool_prefers_depth_when_supply_allows():
    """Single concept — see the note on the previous test."""
    from synthetic.dose_ladder import select_pool

    avail = {
        f"D8_{i:02d}": frozenset(list(NINE_SUBSET)[:6]) | {MT.NUM_TO_TEXT, MT.UNIT_EXPANSION}
        for i in range(50)
    }
    concept_of = {leaf: C1 for leaf in avail}
    depth, pool = select_pool(avail, concept_of, pool_min=40, min_depth=6)
    assert depth == 8


def test_select_pool_fails_loud_when_no_depth_fills():
    from synthetic.dose_ladder import DoseLadderError, select_pool

    avail = {f"L{i}": frozenset(NINE_SUBSET) for i in range(5)}
    concept_of = {leaf: C1 for leaf in avail}
    with pytest.raises(DoseLadderError, match="pool_too_small"):
        select_pool(avail, concept_of, pool_min=600, min_depth=6)


def test_select_pool_rejects_an_incomplete_concept_map():
    """`concept_of` must cover every leaf in `available`; a bare KeyError would
    name no contract, and both this function and `leaf_concept_map` are public."""
    from synthetic.dose_ladder import DoseLadderError, select_pool

    avail = {f"L{i:02d}": frozenset(NINE_SUBSET) for i in range(3)}
    with pytest.raises(DoseLadderError, match="concept_of_incomplete"):
        select_pool(avail, {"L00": C1}, pool_min=2, min_depth=6)


def test_select_pool_spreads_the_pool_across_concepts():
    """The pool must not be a prefix of the sorted leaf keys: those start with
    the concept code, so truncation would shut whole concepts out of a set the
    consumer partitions by concept. D5 is unaffected — it requires every rung
    to use the SAME leaves, not any particular leaves."""
    from synthetic.dose_ladder import select_pool

    deep = frozenset(list(NINE_SUBSET)[:6]) | {MT.NUM_TO_TEXT}
    available, concept_of = {}, {}
    for prefix, concept in (("C1", C1), ("C2", C2)):
        for i in range(20):
            leaf = f"{prefix}x{i:02d}"
            available[leaf] = deep
            concept_of[leaf] = concept
    depth, pool = select_pool(available, concept_of, pool_min=10, min_depth=6)
    assert depth == 7
    assert len(pool) == 10
    assert len({concept_of[k] for k in pool}) == 2   # both concepts represented


def test_depth_histogram_reports_the_distribution():
    from synthetic.dose_ladder import depth_histogram

    avail = {"a": frozenset(NINE_SUBSET), "b": frozenset(list(NINE_SUBSET)[:3])}
    assert depth_histogram(avail) == {3: 1, 6: 1}


def test_nested_order_does_not_starve_a_thinly_admitted_type():
    """Stage 1 picks the globally LEAST-included types, so a type only a few
    leaves admit should ride all of them rather than being crowded out by the
    abundant ones. On real data the thin types (`unit_conversion`,
    `unit_expansion`) depend on this: a mechanism that dropped them would
    hollow out the very cells the study measures.

    The rare leaves are named to sort LAST, so by the time they are processed
    the abundant types already carry high inclusion counts — which is the
    situation where starvation would show up.
    """
    from synthetic.dose_ladder import nested_order

    common = frozenset(NINE_SUBSET)
    rare_type = MT.NUM_TO_TEXT               # not in NINE_SUBSET
    admitted = {f"L{i:03d}": common for i in range(100)}
    for i in range(5):
        admitted[f"Z{i:03d}"] = frozenset(list(NINE_SUBSET)[:5]) | {rare_type}
    order = nested_order(admitted, seed=42)
    carried = [k for k in admitted if rare_type in order[k]]
    assert sorted(carried) == [f"Z{i:03d}" for i in range(5)]


def _ladder_setup(n_leaves=12):
    """n hojas de un concepto, cada una compatible con 6 tipos (2 reescrituras/tipo)."""
    surfaces = {t: f"s-{t.value}" for t in NINE_SUBSET}
    text = "obra " + " ".join(surfaces.values())
    inventory = LeafInventory({C1: [(f"C1{i:03d}", text, ()) for i in range(n_leaves)]})
    pantry = Pantry(by_type={
        t: tuple(
            _rewrite(t, surfaces[t], ci=ci, concepts=(C1,), dedup=(f"{t.value}-{ci}",))
            for ci in range(2)
        )
        for t in NINE_SUBSET
    })
    return inventory, pantry


def test_build_dose_plan_has_exact_counts_and_nesting():
    from synthetic.dose_ladder import (
        LADDER_MAX, build_dose_plan, nested_order,
    )

    inventory, pantry = _ladder_setup()
    pool = tuple(f"C1{i:03d}" for i in range(10))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    plan = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)

    assert len(plan) == 10 * LADDER_MAX
    by_leaf = {}
    for p in plan:
        k = int(p.condition[len("dose_"):])
        assert len(p.rewrites) == k                      # exact count
        by_leaf.setdefault(p.leaf_item_key, {})[k] = {r.mtype for r in p.rewrites}
    for leaf, rungs in by_leaf.items():
        assert set(rungs) == set(range(1, LADDER_MAX + 1))   # complete ladder
        for k in range(1, LADDER_MAX):
            assert rungs[k] < rungs[k + 1]                   # strictly nested


def test_build_dose_plan_uses_the_same_leaves_at_every_rung():
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup()
    pool = tuple(f"C1{i:03d}" for i in range(10))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    plan = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)
    per_rung = {}
    for p in plan:
        per_rung.setdefault(p.condition, set()).add(p.leaf_item_key)
    assert len(per_rung) == LADDER_MAX
    assert len(set(map(frozenset, per_rung.values()))) == 1   # one population


def test_build_dose_plan_revert_frees_capacity_for_later_leaves():
    """The revert must restore `usage`, not just drop the leaf.

    With `paraphrase` capped at 1 (2 rewrites x cap 1 = total capacity 2,
    exhausted by leaves C1000/C1001) and `compression` capped at 2, leaves
    C1004 and C1007 each successfully pick a `compression` rewrite before
    blocking on the now-exhausted `paraphrase` later in their own order, and
    get reverted whole. If those `compression` picks were not given back, both
    `compression` rewrites would sit at their cap by the time leaf C1008 is
    tried — and C1008 needs `compression` FIRST in its order, so it would
    block immediately instead of completing a ladder: a leaked increment from
    a leaf that was never emitted would silently starve a later, unrelated
    leaf. Traced by hand at seed=42 and cross-checked against the real
    algorithm outside pytest: with the revert, the 4 accepted leaves are
    exactly C1000, C1001, C1002, C1008; breaking the revert (commenting out
    `usage[pick.uid] -= 1`) drops C1008 and the run raises `pool_exhausted`
    instead of returning 4 ladders.
    """
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup(n_leaves=12)
    pool = tuple(f"C1{i:03d}" for i in range(12))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    plan = build_dose_plan(
        pantry, inventory, order, pool,
        reuse_cap={"paraphrase": 1, "compression": 2}, per_count=4,
    )
    leaves = {p.leaf_item_key for p in plan}
    assert leaves == {"C1000", "C1001", "C1002", "C1008"}
    assert len(plan) == 4 * LADDER_MAX
    # no rewrite is used more times than its cap allows across the whole run
    used = Counter(
        r.uid for p in plan if p.condition == f"dose_{LADDER_MAX}"
        for r in p.rewrites
    )
    caps = {"paraphrase": 1, "compression": 2}
    for uid, n in used.items():
        mtype = uid.split(":", 1)[0]
        if mtype in caps:
            assert n <= caps[mtype], f"{uid} used {n} times over its cap"


def test_build_dose_plan_raises_when_the_pool_cannot_fill_the_request():
    """A shortfall is loud, not silent: every rung would be short by the same
    amount, so the delivered set would miss the per-count floor. The cap here
    allows only 2 uses of `paraphrase` in the whole run, so most leaves that
    need it cannot build a ladder."""
    from synthetic.dose_ladder import DoseLadderError, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup(n_leaves=12)
    pool = tuple(f"C1{i:03d}" for i in range(12))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    with pytest.raises(DoseLadderError, match="pool_exhausted"):
        build_dose_plan(
            pantry, inventory, order, pool,
            reuse_cap={"paraphrase": 1}, per_count=12,
        )


def test_build_dose_plan_draws_on_the_reserve_when_a_ladder_fails():
    """A pool longer than `per_count` IS the reserve: leaves whose ladder
    cannot be built are skipped whole (D5 — a partial ladder would break the
    common population) and later candidates take their place, so the request
    is still met in full."""
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup(n_leaves=12)
    pool = tuple(f"C1{i:03d}" for i in range(12))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    plan = build_dose_plan(
        pantry, inventory, order, pool,
        reuse_cap={"paraphrase": 1}, per_count=4,
    )
    leaves = {p.leaf_item_key for p in plan}
    assert len(leaves) == 4                      # request met exactly
    assert len(plan) == 4 * LADDER_MAX           # every accepted leaf complete
    assert leaves <= set(pool)


def test_build_dose_plan_is_deterministic():
    from synthetic.dose_ladder import build_dose_plan, nested_order

    inventory, pantry = _ladder_setup()
    pool = tuple(f"C1{i:03d}" for i in range(10))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    key = lambda pl: [
        (p.condition, p.leaf_item_key, tuple(r.uid for r in p.rewrites)) for p in pl
    ]
    a = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)
    b = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)
    assert key(a) == key(b)


def test_committed_dose_configs_load():
    from pathlib import Path
    from synthetic.dose_ladder import LADDER_MAX, load_dose_budgets

    root = Path(__file__).resolve().parents[2] / "configs" / "synthetic"
    dose = load_dose_budgets(root / "variant_budgets_OE_dose.yaml")
    assert dose.per_count >= 600                 # their §3
    assert dose.structural_threshold > LADDER_MAX
    # 40: the lowest cap that reaches per_count on the real pool (see the YAML)
    assert dose.reuse_cap == {
        "num_to_text": 40, "unit_expansion": 40, "unit_conversion": 40,
    }
    # a reserve exists: select_pool returns exactly pool_min leaves and
    # build_dose_plan raises rather than deliver fewer than per_count ladders
    assert dose.effective_pool_min > dose.per_count

    probe = load_dose_budgets(root / "variant_budgets_OE_probe.yaml")
    assert probe.candidate_cap >= dose.effective_pool_min
    # the probe measures availability, which D1 requires to be cap-free
    assert probe.reuse_cap == {}


# ---------------------------------------------------------------------------
# Tramos compartidos. Los tipos de una familia compiten por el mismo tramo de
# texto: los L2 por fragmento, los L1 por (eje, valor), los L3 por plantilla.
# Los fixtures de arriba dan a cada tipo un tramo exclusivo, así que no podían
# verlo; la prueba de humo sobre el stage de 2024 lo encontró (0 de 5 escaleras).

FRAG = ("en cualquier clase de terreno, excepto roca",)


def _shared_slots():
    """Siete tipos disponibles, los tres L2 sobre un único fragmento: caben 5."""
    return {
        MT.PARAPHRASE: frozenset({FRAG}),
        MT.EXPANSION: frozenset({FRAG}),
        MT.COMPRESSION: frozenset({FRAG}),
        MT.SYNONYM_LABEL: frozenset({("TIPO", "Normal")}),
        MT.NUM_TO_TEXT: frozenset({("Nº TUBOS", "2")}),
        MT.UNIT_CONVERSION: frozenset({("DIAMETRO", "110 mm")}),
        MT.REORDER: frozenset({("TEXTO", "tpl")}),
    }


def _as_rewrites(slots_by_leaf):
    """One rewrite per (type, span): the rewrites view of a slots fixture."""
    return {
        leaf: {
            t: tuple(_rewrite(t, f"{t.value}|{key}", dedup=key)
                     for key in sorted(keys, key=repr))
            for t, keys in slots.items()
        }
        for leaf, slots in slots_by_leaf.items()
    }


def test_placeable_depth_counts_distinct_spans_not_types():
    from synthetic.dose_ladder import placeable_depth

    assert placeable_depth(_shared_slots()) == 5
    assert placeable_depth({}) == 0


def test_placeable_depth_finds_the_assignment_a_greedy_would_miss():
    """A admite dos tramos y B solo el primero: caben los dos si A cede."""
    from synthetic.dose_ladder import placeable_depth

    k1, k2 = ("EJE", "1"), ("EJE", "2")
    assert placeable_depth({
        MT.NUM_TO_TEXT: frozenset({k1, k2}),
        MT.UNIT_CONVERSION: frozenset({k1}),
    }) == 2


def test_leaf_slots_maps_available_types_to_their_compatible_spans():
    from synthetic.dose_ladder import leaf_slots

    frag = "excepto roca"
    inventory = LeafInventory({C1: [("C1000", f"zanja {frag} normal", ())]})
    pantry = Pantry(by_type={
        MT.PARAPHRASE: (_rewrite(MT.PARAPHRASE, frag, ci=0),
                        _rewrite(MT.PARAPHRASE, frag, ci=1)),
        MT.EXPANSION: (_rewrite(MT.EXPANSION, frag),),
        MT.COMPRESSION: (_rewrite(MT.COMPRESSION, "no aparece"),),
    })
    slots = leaf_slots(
        pantry, inventory,
        {"C1000": frozenset({MT.PARAPHRASE, MT.COMPRESSION})},
    )
    # EXPANSION no está disponible; COMPRESSION no tiene reescritura compatible
    assert slots == {"C1000": {MT.PARAPHRASE: frozenset({(frag,)})}}


def test_nested_order_with_slots_never_puts_two_types_on_one_span():
    from synthetic.dose_ladder import LADDER_MAX, nested_order, placeable_depth

    slots = {f"L{i:03d}": _shared_slots() for i in range(30)}
    admitted = {k: frozenset(v) for k, v in slots.items()}
    # sin tramos, el equilibrio mete dos L2 en alguna hoja: el test tiene dientes
    plain = nested_order(admitted, seed=42)
    assert any(
        placeable_depth({t: slots[leaf][t] for t in types}) < LADDER_MAX
        for leaf, types in plain.items()
    )
    order = nested_order(admitted, seed=42, rewrites=_as_rewrites(slots))
    for leaf, types in order.items():
        assert placeable_depth({t: slots[leaf][t] for t in types}) == LADDER_MAX
        for k in range(1, LADDER_MAX):
            assert set(types[:k]) < set(types[:k + 1])


def test_nested_order_with_slots_keeps_the_top_cell_balanced():
    """Un L2 por hoja, repartido a partes iguales entre los tres."""
    from synthetic.dose_ladder import nested_order

    slots = {f"L{i:03d}": _shared_slots() for i in range(30)}
    order = nested_order({k: frozenset(v) for k, v in slots.items()}, seed=42,
                         rewrites=_as_rewrites(slots))
    inclusion = Counter(t for types in order.values() for t in types)
    for t in (MT.PARAPHRASE, MT.EXPANSION, MT.COMPRESSION):
        assert inclusion[t] == 10
    for t in (MT.SYNONYM_LABEL, MT.NUM_TO_TEXT, MT.UNIT_CONVERSION, MT.REORDER):
        assert inclusion[t] == 30


def test_nested_order_with_disjoint_slots_is_the_plain_order():
    from synthetic.dose_ladder import nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(20)}
    slots = {k: {t: frozenset({(t.value,)}) for t in v} for k, v in admitted.items()}
    assert (nested_order(admitted, seed=42, rewrites=_as_rewrites(slots))
            == nested_order(admitted, seed=42))


def test_nested_order_rejects_a_leaf_whose_spans_cannot_fill_the_ladder():
    from synthetic.dose_ladder import DoseLadderError, nested_order

    slots = _shared_slots()
    del slots[MT.REORDER]                    # 6 tipos, pero solo 4 tramos
    with pytest.raises(DoseLadderError, match="ladder_too_deep"):
        nested_order({"L000": frozenset(slots)}, seed=42,
                     rewrites=_as_rewrites({"L000": slots}))


def _shared_span_setup(n_leaves=6):
    """Los tres L2 comparten fragmento; dos reescrituras por tipo."""
    frag = "en cualquier clase de terreno"
    own = {MT.SYNONYM_LABEL: "s-syn", MT.NUM_TO_TEXT: "s-num",
           MT.UNIT_CONVERSION: "s-unit", MT.REORDER: "s-reo"}
    text = f"zanja {frag} " + " ".join(own.values())
    inventory = LeafInventory({C1: [(f"C1{i:03d}", text, ()) for i in range(n_leaves)]})
    by_type = {
        t: tuple(_rewrite(t, frag, ci=ci, dedup=(frag,)) for ci in range(2))
        for t in (MT.PARAPHRASE, MT.EXPANSION, MT.COMPRESSION)
    }
    by_type.update({
        t: tuple(_rewrite(t, s, ci=ci, dedup=(s,)) for ci in range(2))
        for t, s in own.items()
    })
    return inventory, Pantry(by_type=by_type)


def test_build_dose_plan_fills_ladders_when_types_share_a_span():
    from synthetic.dose_ladder import (
        LADDER_MAX, build_dose_plan, leaf_rewrites, nested_order,
    )

    inventory, pantry = _shared_span_setup()
    pool = tuple(f"C1{i:03d}" for i in range(6))
    available = {leaf: frozenset(pantry.by_type) for leaf in pool}
    order = nested_order(available, seed=42,
                         rewrites=leaf_rewrites(pantry, inventory, available))
    plan = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=6)

    assert len(plan) == 6 * LADDER_MAX
    for p in plan:
        keys = [r.dedup_key for r in p.rewrites]
        assert len(keys) == len(set(keys))           # un tramo por modificación


def test_build_dose_plan_backtracks_over_the_span_assignment():
    """NUM_TO_TEXT puede ir a span1 o span2; UNIT_CONVERSION solo a span1.
    Elegir primero el uid menor (span1) bloquearía la escalera: el constructor
    tiene que ceder span1 en vez de descartar la hoja."""
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan

    text = "a-uno b-dos u-uno s-syn s-reo s-comp"
    inventory = LeafInventory({C1: [("C1000", text, ())]})
    pantry = Pantry(by_type={
        MT.NUM_TO_TEXT: (_rewrite(MT.NUM_TO_TEXT, "a-uno", dedup=("span1",)),
                         _rewrite(MT.NUM_TO_TEXT, "b-dos", dedup=("span2",))),
        MT.UNIT_CONVERSION: (_rewrite(MT.UNIT_CONVERSION, "u-uno", dedup=("span1",)),),
        MT.SYNONYM_LABEL: (_rewrite(MT.SYNONYM_LABEL, "s-syn"),),
        MT.REORDER: (_rewrite(MT.REORDER, "s-reo"),),
        MT.COMPRESSION: (_rewrite(MT.COMPRESSION, "s-comp"),),
    })
    order = {"C1000": (MT.NUM_TO_TEXT, MT.UNIT_CONVERSION, MT.SYNONYM_LABEL,
                       MT.REORDER, MT.COMPRESSION)}
    plan = build_dose_plan(pantry, inventory, order, ("C1000",),
                           reuse_cap={}, per_count=1)

    top = next(p for p in plan if p.condition == f"dose_{LADDER_MAX}")
    by_type = {r.mtype: r.dedup_key for r in top.rewrites}
    assert by_type[MT.NUM_TO_TEXT] == ("span2",)
    assert by_type[MT.UNIT_CONVERSION] == ("span1",)
    # el anidamiento se conserva: el peldaño k es el prefijo de longitud k
    assert [p.rewrites for p in plan] == [top.rewrites[:k] for k in range(1, LADDER_MAX + 1)]


# ---------------------------------------------------------------------------
# Topes de reuso en el orden anidado. Con el catálogo real, unit_conversion tenía
# 4 reescrituras distintas en el fondo (capacidad 4 x 20 = 80) y el reparto
# equilibrado le pedía 375 escaleras: 260 de 600. El orden reparte ahora según
# la capacidad que queda, y el constructor reproduce sus decisiones.


def test_nested_order_leaves_a_capped_out_type_out_instead_of_the_leaf():
    """Mismo escenario que el test de `pool_exhausted` de arriba (paraphrase con
    capacidad 2), pero con el orden informado: sale entero."""
    from synthetic.dose_ladder import (
        LADDER_MAX, build_dose_plan, leaf_rewrites, nested_order,
    )

    inventory, pantry = _ladder_setup(n_leaves=12)
    pool = tuple(f"C1{i:03d}" for i in range(12))
    available = {leaf: frozenset(NINE_SUBSET) for leaf in pool}
    caps = {"paraphrase": 1}
    order = nested_order(available, seed=42,
                         rewrites=leaf_rewrites(pantry, inventory, available),
                         reuse_cap=caps)

    assert set(order) == set(pool)          # quedan 5 tipos: ninguna hoja se pierde
    assert sum(MT.PARAPHRASE in types for types in order.values()) == 2
    plan = build_dose_plan(pantry, inventory, order, pool, reuse_cap=caps, per_count=12)
    assert len(plan) == 12 * LADDER_MAX


def test_nested_order_omits_a_leaf_it_cannot_fill_under_caps():
    """Hojas con exactamente 5 tipos: agotado uno, no queda escalera posible.
    La hoja pasa a la reserva en vez de romper la corrida."""
    from synthetic.dose_ladder import (
        DoseLadderError, build_dose_plan, leaf_rewrites, nested_order,
    )

    inventory, pantry = _ladder_setup(n_leaves=6)
    pool = tuple(f"C1{i:03d}" for i in range(6))
    available = {leaf: frozenset(NINE_SUBSET[:5]) for leaf in pool}
    caps = {"paraphrase": 1}
    order = nested_order(available, seed=42,
                         rewrites=leaf_rewrites(pantry, inventory, available),
                         reuse_cap=caps)

    assert list(order) == ["C1000", "C1001"]
    build_dose_plan(pantry, inventory, order, pool, reuse_cap=caps, per_count=2)
    with pytest.raises(DoseLadderError, match="pool_exhausted"):
        build_dose_plan(pantry, inventory, order, pool, reuse_cap=caps, per_count=3)


def test_nested_order_spends_capacity_in_the_given_leaf_order():
    """El constructor recorre el fondo en su orden; el orden anidado tiene que
    gastar la capacidad en ese mismo orden o sus decisiones no se reproducen."""
    from synthetic.dose_ladder import leaf_rewrites, nested_order

    inventory, pantry = _ladder_setup(n_leaves=6)
    pool = tuple(f"C1{i:03d}" for i in reversed(range(6)))
    available = {leaf: frozenset(NINE_SUBSET[:5]) for leaf in pool}
    order = nested_order(available, seed=42,
                         rewrites=leaf_rewrites(pantry, inventory, available),
                         reuse_cap={"paraphrase": 1})
    assert list(order) == ["C1005", "C1004"]


def test_leaf_slots_is_the_span_view_of_leaf_rewrites():
    from synthetic.dose_ladder import leaf_rewrites, leaf_slots

    inventory, pantry = _shared_span_setup(n_leaves=2)
    available = {"C1000": frozenset(pantry.by_type), "C1001": frozenset({MT.REORDER})}
    rewrites = leaf_rewrites(pantry, inventory, available)
    assert set(rewrites["C1001"]) == {MT.REORDER}
    assert leaf_slots(pantry, inventory, available) == {
        leaf: {t: frozenset(r.dedup_key for r in rws) for t, rws in by_type.items()}
        for leaf, by_type in rewrites.items()
    }


# ---------------------------------------------------------------------------
# Visibilidad en el TEXTO. La compatibilidad compara cadenas: una reescritura de
# $K ("bajo vías", solo en el RESUMEN) pasaba por compatible porque "bajo vías"
# aparece en el TEXTO dentro de $I ("en cruce bajo vías"). Se aplicaba, se
# contaba y no se veía: en la corrida real ~28 % de dose_5 decía 5 cambios con 4
# visibles, y 21 hojas se quedaron sin dose_1.


def _surface_stage():
    return {"C1$": {
        "ud": "m", "concept": "zanja",
        "parameters": {
            "A": {"label": "TIPO DE TERRENO ", "values": [
                {"label": "a", "value": "Normal"}, {"label": "b", "value": "Bajo vías"}]},
            "B": {"label": "BANDA", "values": [
                {"label": "a", "value": "5 horas"}, {"label": "b", "value": "3 horas"}]},
        },
        "texto": "Zanja $I, banda $B",
        "resumen": "Zanja $K ($A)",
        "text_variables": {},
    }}


def _l2(mtype, fragment, var, condition, ci=0):
    from synthetic.pantry import Usage

    return ApprovedRewrite(
        mtype=mtype, dedup_key=(fragment,), canonical=f"${var} / {condition}: {fragment}",
        candidate_index=ci, payload={"original": fragment, "new": f"{fragment}-v{ci}"},
        usages=(Usage(C1, None, f"${var} / {condition}: {fragment}"),),
    )


def test_texto_surface_rejects_a_fragment_whose_variable_only_feeds_the_resumen():
    from synthetic.dose_ladder import TextoSurface

    surface = TextoSurface.from_stage(_surface_stage())
    in_resumen = _l2(MT.PARAPHRASE, "bajo vías", "K", '%A=="b"')
    in_texto = _l2(MT.COMPRESSION, "en cruce bajo vías", "I", '%A=="b"')
    assert surface.shows(in_resumen, C1, "C1ba") is False
    assert surface.shows(in_texto, C1, "C1ba") is True


def test_texto_surface_requires_the_condition_to_bind_the_leaf():
    from synthetic.dose_ladder import TextoSurface

    surface = TextoSurface.from_stage(_surface_stage())
    assert surface.shows(_l2(MT.EXPANSION, "roca", "I", '%A=="b"'), C1, "C1ab") is False
    assert surface.shows(_l2(MT.EXPANSION, "roca", "I", "%A=b"), C1, "C1ba") is True
    either = _l2(MT.EXPANSION, "roca", "I", '%A=="a"  or  %A=="b"')
    assert surface.shows(either, C1, "C1ab") is True


def test_texto_surface_rejects_what_it_cannot_parse():
    """No confirmar la visibilidad es no ofrecerla: el conteo exacto (D2) pesa
    más que una reescritura de menos."""
    from synthetic.dose_ladder import TextoSurface

    surface = TextoSurface.from_stage(_surface_stage())
    assert surface.shows(_l2(MT.PARAPHRASE, "roca", "I", "%A>1"), C1, "C1ab") is False


def test_texto_surface_checks_value_types_by_their_axis_placeholder():
    from synthetic.dose_ladder import TextoSurface

    surface = TextoSurface.from_stage(_surface_stage())
    only_resumen = _rewrite(MT.SYNONYM_LABEL, "Normal", dedup=("TIPO DE TERRENO", "Normal"))
    in_texto = _rewrite(MT.UNIT_EXPANSION, "5 horas", dedup=("BANDA", "5 horas"))
    assert surface.shows(only_resumen, C1, "C1aa") is False
    assert surface.shows(in_texto, C1, "C1aa") is True


def test_texto_surface_passes_template_types_through():
    from synthetic.dose_ladder import TextoSurface

    surface = TextoSurface.from_stage(_surface_stage())
    assert surface.shows(_rewrite(MT.REORDER, "tpl", dedup=("TEXTO", "tpl")), C1, "C1aa")


def test_texto_surface_rejects_a_leaf_key_that_does_not_match_the_axes():
    from synthetic.dose_ladder import DoseLadderError, TextoSurface

    surface = TextoSurface.from_stage(_surface_stage())
    with pytest.raises(DoseLadderError, match="leaf_key_axes"):
        surface.shows(_l2(MT.PARAPHRASE, "roca", "I", "%A=a"), C1, "C1abc")


def test_planners_drop_rewrites_the_texto_does_not_show():
    """Sondeo, orden y constructor ven las mismas candidatas filtradas."""
    from synthetic.dose_ladder import (
        TextoSurface, build_dose_plan, build_probe_plan, leaf_rewrites,
    )

    from synthetic.dose_ladder import DoseLadderError

    text = "Zanja en cruce bajo vías, banda 5 horas"
    inventory = LeafInventory({C1: [("C1ba", text, (("BANDA", "5 horas"),))]})
    pantry = Pantry(by_type={
        MT.COMPRESSION: (_l2(MT.COMPRESSION, "en cruce bajo vías", "I", '%A=="b"'),),
        MT.PARAPHRASE: (_l2(MT.PARAPHRASE, "bajo vías", "K", '%A=="b"'),),
        MT.UNIT_EXPANSION: (_rewrite(MT.UNIT_EXPANSION, "5 horas", dedup=("BANDA", "5 horas")),),
        MT.REORDER: (_rewrite(MT.REORDER, "t1", dedup=("TEXTO", "t1")),),
        MT.TEMPLATE_PARAPHRASE: (_rewrite(MT.TEMPLATE_PARAPHRASE, "t2", dedup=("TEXTO", "t2")),),
    })
    surface = TextoSurface.from_stage(_surface_stage())
    every = frozenset(pantry.by_type)

    probe = build_probe_plan(pantry, inventory, ["C1ba"], surface=surface)
    assert "probe_paraphrase" in {p.condition for p in build_probe_plan(pantry, inventory, ["C1ba"])}
    assert {p.condition for p in probe} == {
        "probe_compression", "probe_unit_expansion", "probe_reorder",
        "probe_template_paraphrase"}

    rewrites = leaf_rewrites(pantry, inventory, {"C1ba": every}, surface=surface)
    assert MT.PARAPHRASE not in rewrites["C1ba"]

    order = {"C1ba": (MT.PARAPHRASE, MT.COMPRESSION, MT.UNIT_EXPANSION,
                      MT.REORDER, MT.TEMPLATE_PARAPHRASE)}
    build_dose_plan(pantry, inventory, order, ("C1ba",), reuse_cap={}, per_count=1)
    with pytest.raises(DoseLadderError, match="pool_exhausted"):
        build_dose_plan(pantry, inventory, order, ("C1ba",), reuse_cap={},
                        per_count=1, surface=surface)
