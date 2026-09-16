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
* per-leaf AVAILABILITY is decided empirically, not statically: the probe
  pass renders one single-modification variant per (leaf, compatible type)
  and keeps those whose TEXTO actually changed. This module supplies the
  static half — :func:`compatible_rewrites` — and the build script turns
  probe survival into the delivered ``available_types`` (D1).

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
from .pantry import ApprovedRewrite
from .target_scanner import ChapterInventory
from .taxonomy import ModificationType

__all__ = [
    "LADDER_MAX",
    "DoseLadderError",
    "structural_types",
    "compatible_rewrites",
    "DoseBudgets",
    "load_dose_budgets",
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
    applicable: Mapping[ModificationType, Sequence[ApprovedRewrite]],
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> dict[ModificationType, tuple[ApprovedRewrite, ...]]:
    """Per type, the rewrites among ``applicable`` that are compatible with
    this leaf (cap-free), sorted by ``uid`` so downstream picking is
    deterministic.

    ``applicable`` is one concept's rewrites — ``Pantry.for_concept(key)``.
    It is taken already resolved because it depends only on the concept,
    while this function is called once per LEAF: resolving it here would
    re-walk the whole pantry for every leaf of the same concept.

    A type with no compatible rewrite is absent from the result — callers
    read the key set as "the types this leaf can take", so mapping it to an
    empty tuple would report it as available when it is not.
    """
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


@dataclass(frozen=True)
class DoseBudgets:
    """Validated E3 budgets.

    ``per_count`` items per rung (their §3 asks for >= 600);
    ``structural_threshold`` is the minimum number of STRUCTURALLY applicable
    types a leaf needs to enter the probe candidate set (D5 wants room to
    choose at rung 5, so it must exceed ``LADDER_MAX``); ``candidate_cap``
    bounds the probe's render cost.
    """

    seed: int
    per_count: int
    structural_threshold: int
    candidate_cap: int
    reuse_cap: Mapping[str, int]
    pool_min: Optional[int] = None

    @property
    def effective_pool_min(self) -> int:
        """Leaves the pool must reach: ``pool_min`` when given, else one leaf
        per rung item (the ladder uses the SAME leaves at every rung)."""
        return self.per_count if self.pool_min is None else self.pool_min

    def to_driver_budgets(self) -> Budgets:
        """Adapter for `run_corpus(budgets=...)`, which only reads
        ``targets``/``seed``/``reuse_cap`` to render the QA report."""
        return Budgets(
            seed=self.seed,
            targets={f"dose_{k}": self.per_count for k in range(1, LADDER_MAX + 1)},
            reuse_cap=dict(self.reuse_cap),
        )


def _positive_int(value: object, what: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(
            f"dose_budgets_invalid: {what} must be a positive int, got {value!r}"
        )
    return value


def load_dose_budgets(path: Path) -> DoseBudgets:
    """Read + validate the E3 budgets YAML. Fails loud
    (``ValueError("dose_budgets_invalid: ...")``)."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"dose_budgets_invalid: {Path(path).name} is not a mapping")

    seed = _positive_int(raw.get("seed"), "seed")
    per_count = _positive_int(raw.get("per_count"), "per_count")
    threshold = _positive_int(raw.get("structural_threshold"), "structural_threshold")
    candidate_cap = _positive_int(raw.get("candidate_cap"), "candidate_cap")
    if threshold <= LADDER_MAX:
        raise ValueError(
            f"dose_budgets_invalid: structural_threshold must exceed "
            f"LADDER_MAX={LADDER_MAX} so rung {LADDER_MAX} still has a choice "
            f"(D5), got {threshold}"
        )
    pool_min = raw.get("pool_min")
    if pool_min is not None:
        pool_min = _positive_int(pool_min, "pool_min")

    reuse_cap = raw.get("reuse_cap") or {}
    if not isinstance(reuse_cap, dict):
        raise ValueError("dose_budgets_invalid: reuse_cap is not a mapping")
    valid = {t.value for t in NINE_TYPES}
    for mtype, cap in reuse_cap.items():
        if mtype not in valid:
            raise ValueError(
                f"dose_budgets_invalid: reuse_cap type {mtype!r} is not one of "
                f"the nine admitted types"
            )
        _positive_int(cap, f"reuse_cap[{mtype}]")

    return DoseBudgets(
        seed=seed, per_count=per_count, structural_threshold=threshold,
        candidate_cap=candidate_cap, reuse_cap=dict(reuse_cap), pool_min=pool_min,
    )
