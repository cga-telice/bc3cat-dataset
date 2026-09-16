"""E3 — balanced dose-ladder planner (spec: E3_DOSE_DESIGN.md).

Decides WHAT gets generated; it does not render and does not write. Produces
:class:`~synthetic.corpus_sampler.PlannedVariant`\\ s that
:func:`~synthetic.corpus_driver.run_corpus` materialises.

Two condition families:

* ``probe_<type>`` — one variant per (leaf, admitted type) with a SINGLE
  modification, TEXTO field. Measures which types actually change each
  leaf's TEXTO, and, restricted to the leaf POOL, is the isolated-effects
  deliverable (D6). (The pool is the common set of leaves the ladder runs
  on — not the pantry, which is the stock of approved rewrites.)
* ``dose_1..dose_5`` — the nested ladder: ``types(dose_k)`` is the
  length-``k`` prefix of the leaf's type order, so exactly one modification
  is added between consecutive rungs (D4).

Two notions of per-leaf applicability, both free of reuse caps (D1):

* :func:`structural_types` — the grammar admits the type. Comes from the
  chapter's *targets* (:func:`~synthetic.target_scanner.scan_chapter`), i.e.
  what exists before any LLM proposal.
* :func:`available_types` — an approved AND compatible rewrite also exists.

Determinism: same inputs -> same plan, byte for byte. Every seed derivation
uses ``zlib.crc32`` (never ``hash()``, salted per process).
"""

from __future__ import annotations

import random
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

import yaml

from .corpus_sampler import (
    NINE_TYPES,
    Budgets,
    L1_VALUE_TYPES,
    LeafInventory,
    PlannedVariant,
    is_compatible,
)
from .pantry import ApprovedRewrite, Pantry
from .target_scanner import ChapterInventory
from .taxonomy import ModificationType

__all__ = [
    "LADDER_MAX",
    "DoseLadderError",
    "structural_types",
    "compatible_rewrites",
    "available_types",
]

#: Rungs of the ladder: dose_1 .. dose_5 (their §1).
LADDER_MAX = 5


class DoseLadderError(RuntimeError):
    """A guarantee this module promises has been violated."""


def _surface(mtype: ModificationType, dedup_key: Sequence) -> str:
    """The reviewed surface form carried by a ``dedup_key``.

    L1: ``(axis, value)`` -> the value. L2: ``(fragment,)`` -> the fragment.
    L3: the template body, which `is_compatible` ignores anyway (L3 rewrites
    touch the shared template, so they surface in every leaf).
    """
    if mtype in L1_VALUE_TYPES and len(dedup_key) >= 2:
        return str(dedup_key[1])
    return str(dedup_key[0]) if dedup_key else ""


def _as_rewrite(mtype: ModificationType, dedup_key: Sequence) -> ApprovedRewrite:
    """Wrap a scanned target as a synthetic rewrite, so the ONE compatibility
    rule (`corpus_sampler.is_compatible`) judges structure too — no second
    implementation to drift out of sync."""
    return ApprovedRewrite(
        mtype=mtype,
        dedup_key=tuple(dedup_key),
        canonical="",
        candidate_index=-1,
        payload={"original": _surface(mtype, dedup_key)},
        usages=(),
    )


def structural_types(
    chapter_inventory: ChapterInventory,
    concept_key: str,
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> frozenset[ModificationType]:
    """The types the GRAMMAR admits for this leaf (D1, structural half).

    Independent of the pantry: a type counts as structurally applicable when
    the chapter scan found a target of that type in this leaf's concept whose
    surface the leaf selects. Only the nine admitted types are considered.
    """
    out: set[ModificationType] = set()
    for mtype in NINE_TYPES:
        for target in chapter_inventory.by_type.get(mtype, ()):
            if not any(u.concept_key == concept_key for u in target.usages):
                continue
            if is_compatible(
                _as_rewrite(mtype, target.dedup_key), leaf_text, leaf_axis_values
            ):
                out.add(mtype)
                break
    return frozenset(out)


def compatible_rewrites(
    pantry: Pantry,
    concept_key: str,
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> dict[ModificationType, tuple[ApprovedRewrite, ...]]:
    """Per type, this leaf's approved AND compatible rewrites (cap-free).

    Sorted by ``uid`` so downstream picking is deterministic.
    """
    applicable = pantry.for_concept(concept_key)
    out: dict[ModificationType, tuple[ApprovedRewrite, ...]] = {}
    for mtype in NINE_TYPES:
        hits = tuple(sorted(
            (r for r in applicable.get(mtype, ())
             if is_compatible(r, leaf_text, leaf_axis_values)),
            key=lambda r: r.uid,
        ))
        if hits:
            out[mtype] = hits
    return out


def available_types(
    pantry: Pantry,
    concept_key: str,
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> frozenset[ModificationType]:
    """The types this leaf can REALLY take (D1, realizable half): an approved,
    compatible rewrite exists. Cap-free by design — see D1's rationale."""
    return frozenset(compatible_rewrites(
        pantry, concept_key, leaf_text, leaf_axis_values,
    ))
