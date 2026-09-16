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
    allocate,
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
    "DoseBudgets",
    "load_dose_budgets",
    "candidate_leaves",
    "build_probe_plan",
    "nested_order",
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


def _concept_of(inventory: LeafInventory) -> dict[str, str]:
    """``{leaf_item_key: concept_key}`` for the whole inventory."""
    return {
        leaf: concept
        for concept in inventory.concepts()
        for leaf in inventory.leaves(concept)
    }


def candidate_leaves(
    chapter_inventory: ChapterInventory,
    inventory: LeafInventory,
    *,
    threshold: int,
    cap: int,
) -> tuple[str, ...]:
    """Leaves worth probing: at least ``threshold`` STRUCTURALLY applicable
    types, at most ``cap`` in total, spread ACROSS concepts.

    The threshold is structural on purpose (D5): it costs no renders and
    cannot bias the pool by anything that depends on the pantry or the seed.

    The cap is applied by :func:`~synthetic.corpus_sampler.allocate` — the
    same proportional, floor-1, supply-capped split the ablation inventory
    was built with — and NOT by truncating the sorted leaf keys. Leaf keys
    begin with their concept code, so a plain truncation would spend the
    whole budget on the alphabetically-first concepts and leave most of the
    chapter out of the pool; the consumer partitions the delivered set by
    concept against its own dev/test split, so concept coverage is
    load-bearing.

    Keep ``cap`` comfortably above the number of qualifying concepts. Below
    it, no budget remains to give every concept its floor of one, and which
    concepts survive is then decided by ``allocate``'s tie-break — leaf count,
    then concept key — so the alphabetical bias this split exists to remove
    creeps back in at the level of WHICH concepts appear at all. The committed
    config (1500 against ~83 concepts) is far from that regime.
    """
    qualifying: dict[str, list[str]] = {}
    for leaf, concept in sorted(_concept_of(inventory).items()):
        types = structural_types(
            chapter_inventory, concept, inventory.text(leaf),
            inventory.axis_values(leaf),
        )
        if len(types) >= threshold:
            qualifying.setdefault(concept, []).append(leaf)

    alloc = allocate(cap, {c: len(v) for c, v in qualifying.items()})
    picked = [
        leaf
        for concept in sorted(alloc)
        for leaf in qualifying[concept][: alloc[concept]]
    ]
    return tuple(sorted(picked))


def _least_used(
    candidates: Sequence[ApprovedRewrite],
    cap: Optional[int],
    usage: Mapping[str, int],
    used_dedup: frozenset = frozenset(),
) -> Optional[ApprovedRewrite]:
    """Least-used-first pick honouring ``cap`` and the per-variant dedup set.

    ``None`` when every candidate is capped out or dedup-blocked. Ties break on
    ``uid`` so the pick is reproducible. ``cap=0`` blocks every candidate —
    this is a public function and callers other than
    :func:`load_dose_budgets` (whose positive-int validation forbids it) may
    pass it directly.
    """
    for rewrite in sorted(candidates, key=lambda r: (usage.get(r.uid, 0), r.uid)):
        if cap is not None and usage.get(rewrite.uid, 0) >= cap:
            continue
        if rewrite.dedup_key in used_dedup:
            continue
        return rewrite
    return None


def build_probe_plan(
    pantry: Pantry,
    inventory: LeafInventory,
    leaves: Sequence[str],
) -> tuple[PlannedVariant, ...]:
    """One single-modification variant per (leaf, available type).

    Condition ``probe_<type>``, so leaves stay unique within a condition and
    the driver's report breaks the probe down per type.

    No reuse cap applies here. This pass's survivors define per-leaf
    availability, which D1 requires to be cap-free: a cap would make a type
    look unavailable for one leaf and available for another purely because of
    processing order, and — since a capped-out pair never becomes a variant —
    it would do so with no trace in the driver's report. Least-used-first
    still spreads reuse across the pool. Caps belong to the ladder (task 9),
    where an exhausted leaf is reverted whole and therefore visible.
    """
    concept_of = _concept_of(inventory)
    # `Pantry.for_concept` walks the whole pantry but its result depends only
    # on the concept, so resolve it once per concept rather than once per leaf.
    applicable: dict[str, dict] = {}
    usage: dict[str, int] = {}
    plan: list[PlannedVariant] = []
    for leaf in sorted(leaves):
        concept = concept_of[leaf]
        if concept not in applicable:
            applicable[concept] = pantry.for_concept(concept)
        by_type = compatible_rewrites(
            applicable[concept], inventory.text(leaf), inventory.axis_values(leaf),
        )
        for mtype in NINE_TYPES:
            cands = by_type.get(mtype)
            if not cands:
                continue
            pick = _least_used(cands, None, usage)
            usage[pick.uid] = usage.get(pick.uid, 0) + 1
            # `corpus_driver._expected_applied_count` relies on every probe_*
            # variant carrying exactly ONE rewrite (-> expects 1 applied
            # modification). Keep this a single-rewrite tuple, always.
            plan.append(PlannedVariant(
                condition=f"probe_{mtype.value}", concept_key=concept,
                leaf_item_key=leaf, rewrites=(pick,),
            ))
    return tuple(plan)


def nested_order(
    admitted: Mapping[str, frozenset],
    seed: int,
) -> dict[str, tuple[ModificationType, ...]]:
    """Per-leaf type order whose prefixes ARE the ladder rungs (D4).

    Two greedy stages, both least-used-first with the leaf's own deterministic
    shuffle as tie-break:

    1. WHICH types the leaf uses — the ``LADDER_MAX`` types used fewest times
       across leaves so far. A leaf admitting more types than there are rungs
       must leave some out, and leaving that unbalanced skews the top cell
       directly: ``presence(t, LADDER_MAX) = n_leaves - n_leaves_excluding_t``.
    2. In WHICH ORDER — the type placed at this position across the fewest
       leaves so far, among the ones stage 1 chose.

    ``types(dose_k)`` is the length-``k`` prefix, so consecutive rungs differ
    by exactly one added modification (D4).

    On balance (their §3), stated honestly: stage 1 makes the top cell even.
    Cells below it cannot be made exactly even by a greedy, because the
    positions are NOT independent — which type a leaf places at position ``p``
    constrains what remains for ``p+1`` — so a small residual spread survives.
    It is a residual of a few leaves per cell against cells of order a
    hundred, and it is noise rather than bias: it does not favour particular
    types across seeds (measured — see the corpus report). On real data the
    binding constraint is admission anyway (types are admitted by very
    different numbers of leaves), which no ordering policy can undo.

    Raises :class:`DoseLadderError` for a leaf admitting fewer than
    ``LADDER_MAX`` types — the pool selection must have excluded it already.
    """
    inclusion: Counter = Counter()
    per_position: list[Counter] = [Counter() for _ in range(LADDER_MAX)]
    order: dict[str, tuple[ModificationType, ...]] = {}
    for leaf in sorted(admitted):
        types = admitted[leaf]
        if len(types) < LADDER_MAX:
            raise DoseLadderError(
                f"ladder_too_deep: leaf {leaf!r} admits {len(types)} types, "
                f"needs {LADDER_MAX} — it should not be in the pool"
            )
        rng = random.Random(seed ^ zlib.crc32(leaf.encode("utf-8")))
        shuffled = rng.sample(sorted(types, key=lambda t: t.value), len(types))
        rank = {t: i for i, t in enumerate(shuffled)}

        # stage 1: which types ride this leaf's ladder at all
        used = sorted(shuffled, key=lambda t: (inclusion[t], rank[t]))[:LADDER_MAX]
        for mtype in used:
            inclusion[mtype] += 1

        # stage 2: their order, so each position stays even too.
        # `rank[t]` is load-bearing here, not decorative: only for the first
        # leaf does `used` come out in shuffle order (all `inclusion` counters
        # are 0, so stage 1's key degenerates to `rank`). From the second leaf
        # on, `inclusion` dominates stage 1's sort, so `remaining`'s order says
        # nothing about the leaf's shuffle — without this key the tie-break
        # would be an artifact of stage 1 rather than the documented policy.
        chosen: list[ModificationType] = []
        for position in range(LADDER_MAX):
            remaining = [t for t in used if t not in chosen]
            pick = min(remaining, key=lambda t: (per_position[position][t], rank[t]))
            chosen.append(pick)
            per_position[position][pick] += 1
        order[leaf] = tuple(chosen)
    return order


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
