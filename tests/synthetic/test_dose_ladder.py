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


def test_build_dose_plan_skips_a_leaf_whose_ladder_cannot_be_built():
    """A cap that exhausts mid-ladder must drop the WHOLE leaf and move to the
    reserve — a partial ladder would break the common population (D5)."""
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup(n_leaves=12)
    pool = tuple(f"C1{i:03d}" for i in range(12))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    # 2 rewrites x cap 1 = 2 uses of paraphrase in the whole run: at most 2
    # leaves can carry it, so fewer than 12 ladders are buildable
    plan = build_dose_plan(
        pantry, inventory, order, pool, reuse_cap={"paraphrase": 1}, per_count=12,
    )
    leaves = {p.leaf_item_key for p in plan}
    assert len(plan) == len(leaves) * LADDER_MAX     # every kept leaf is complete
    assert len(leaves) < 12                          # some were skipped


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
