"""E3 — hermetic tests for :mod:`synthetic.dose_ladder`.

Tiny fixtures: 2 concepts, leaves with known (axis, value) pairs, and a toy
pantry. No real parquet, no LLM, no bc3param.
"""
from __future__ import annotations

import pytest

from synthetic.corpus_sampler import LeafInventory
from synthetic.pantry import ApprovedRewrite, Pantry, Usage
from synthetic.target_scanner import ChapterInventory, TargetUsage, UniqueTarget
from synthetic.taxonomy import ModificationType

MT = ModificationType
C1, C2 = "C1$", "C2$"


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
