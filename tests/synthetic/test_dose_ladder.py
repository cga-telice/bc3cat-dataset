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
