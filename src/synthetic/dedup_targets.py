"""Cross-concept twin de-duplication for the OE retrieval benchmark.

Some BPA concepts render byte-identical leaf descriptions (e.g. ``OED020`` and
``OED170``, which differ only by a header phrase — "CON ESPERAS ROSCADAS" — that
is absent from the RESUMEN/TEXTO templates). For a retrieval benchmark whose label
is the concept, identical descriptions under two concepts are an ambiguous target.

Policy (see :func:`plan_dedup`): keep one canonical concept per identical
``(resumen, texto)`` description — the lexicographically-first ``parent_key`` —
and **drop** the non-canonical twin's leaves from the target corpus, and drop the
synthetic items derived from those dropped leaves. Dropping (rather than
relabelling the twin's items onto the survivor) keeps the surviving concept from
being over-represented.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DedupPlan:
    #: target leaf item_keys to drop (the non-canonical twin's leaves)
    drop_leaf_keys: frozenset
    #: dropped concept -> the canonical concept it duplicates (provenance)
    canonical: dict


def plan_dedup(long_df, short_df) -> DedupPlan:
    """Find identical ``(resumen, texto)`` descriptions shared across >1 concept
    and mark every leaf not belonging to the canonical (first) concept for drop.
    """
    parent = dict(zip(long_df["item_key"], long_df["parent_key"]))
    texto = dict(zip(long_df["item_key"], long_df["text"]))
    resumen = dict(zip(short_df["item_key"], short_df["text"]))

    groups: dict = {}
    for key in long_df["item_key"]:
        groups.setdefault((resumen.get(key, ""), texto.get(key, "")), []).append(key)

    drop: set = set()
    canonical: dict = {}
    for keys in groups.values():
        concepts = {parent[k] for k in keys}
        if len(concepts) <= 1:
            continue
        keep = min(concepts)
        for k in keys:
            if parent[k] != keep:
                drop.add(k)
                canonical[parent[k]] = keep
    return DedupPlan(drop_leaf_keys=frozenset(drop), canonical=dict(canonical))


def dedup_target(long_df, short_df, plan: DedupPlan):
    """Drop the plan's twin leaves from the target corpus (both long and short)."""
    keep_keys = set(long_df["item_key"]) - plan.drop_leaf_keys
    lo = long_df[long_df["item_key"].isin(keep_keys)].reset_index(drop=True)
    sh = short_df[short_df["item_key"].isin(keep_keys)].reset_index(drop=True)
    return lo, sh


def dedup_synthetic(syn_df, plan: DedupPlan):
    """Drop synthetic items derived from a dropped twin leaf.

    Returns ``(kept_df, dropped_item_keys)``.
    """
    mask = ~syn_df["original_key"].isin(plan.drop_leaf_keys)
    dropped = set(syn_df.loc[~mask, "item_key"])
    return syn_df[mask].reset_index(drop=True), dropped
