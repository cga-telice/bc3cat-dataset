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
    "build_dose_plan",
    "nested_order",
    "placeable_depth",
    "leaf_slots",
    "leaf_rewrites",
    "select_pool",
    "depth_histogram",
    "leaf_concept_map",
]

#: Rungs of the ladder: dose_1 .. dose_5 (their §1).
LADDER_MAX = 5

#: Diagnostic bucket in ``pool_exhausted`` for ladders blocked by span clashes.
SPAN_CONFLICT = "<span_conflict>"

#: Diagnostic bucket for pool leaves ``nested_order`` left out: under the reuse
#: caps no ``LADDER_MAX`` types still fit on them.
NOT_ORDERED = "<not_ordered>"


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


#: Public alias — the build script needs this mapping to feed `select_pool`,
#: and rebuilding it at the call site would duplicate a two-line invariant.
leaf_concept_map = _concept_of


def _spread_across_concepts(
    n: int,
    grouped: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    """Draw ``n`` leaves from ``grouped`` ({concept: leaves, each list already
    sorted}), spread across concepts by
    :func:`~synthetic.corpus_sampler.allocate` — proportional, floor of one per
    concept, capped at each concept's supply.

    Never a prefix of the sorted leaf keys: those begin with the concept code,
    so truncating them spends the whole budget on the alphabetically-first
    concepts. Both the probe candidate set and the ladder pool need this, and
    the consumer partitions the delivered set by concept, so concept coverage
    is load-bearing in both.

    Keep ``n`` comfortably above the number of concepts in ``grouped``: below
    it there is no budget left to give every concept its floor of one, and
    which concepts survive falls to ``allocate``'s tie-break (leaf count, then
    concept key), so the alphabetical bias this exists to remove creeps back
    in at the level of WHICH concepts appear at all.
    """
    alloc = allocate(n, {c: len(v) for c, v in grouped.items()})
    return tuple(sorted(
        leaf
        for concept in sorted(alloc)
        for leaf in grouped[concept][: alloc[concept]]
    ))


def candidate_leaves(
    chapter_inventory: ChapterInventory,
    inventory: LeafInventory,
    *,
    threshold: int,
    cap: int,
) -> tuple[str, ...]:
    """Leaves worth probing: at least ``threshold`` STRUCTURALLY applicable
    types, at most ``cap`` in total, spread ACROSS concepts (see
    :func:`_spread_across_concepts` — including the note on keeping ``cap``
    comfortably above the number of qualifying concepts).

    The threshold is structural on purpose (D5): it costs no renders and
    cannot bias the pool by anything that depends on the pantry or the seed.
    """
    qualifying: dict[str, list[str]] = {}
    for leaf, concept in sorted(_concept_of(inventory).items()):
        types = structural_types(
            chapter_inventory, concept, inventory.text(leaf),
            inventory.axis_values(leaf),
        )
        if len(types) >= threshold:
            qualifying.setdefault(concept, []).append(leaf)

    return _spread_across_concepts(cap, qualifying)


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


def placeable_depth(slots: Mapping[ModificationType, frozenset]) -> int:
    """How many of these types fit on pairwise-distinct spans at once.

    ``slots`` maps each type to the spans (``dedup_key``\\ s) it can rewrite on
    one leaf. Types of a family share spans — L2 by fragment, L1 by
    ``(axis, value)``, L3 by template — so this is a maximum bipartite
    matching, not ``len(slots)``.
    """
    owner: dict = {}

    def augment(mtype: ModificationType, seen: set) -> bool:
        for key in sorted(slots[mtype], key=repr):
            if key in seen:
                continue
            seen.add(key)
            if key not in owner or augment(owner[key], seen):
                owner[key] = mtype
                return True
        return False

    return sum(augment(t, set()) for t in sorted(slots, key=lambda t: t.value))


def leaf_rewrites(
    pantry: Pantry,
    inventory: LeafInventory,
    available: Mapping[str, frozenset],
) -> dict[str, dict[ModificationType, tuple[ApprovedRewrite, ...]]]:
    """Per leaf, each AVAILABLE type -> its compatible rewrites (cap-free, D1).

    Exactly what :func:`build_dose_plan` computes per leaf, restricted to the
    available types — ``nested_order(rewrites=...)`` must see the same
    candidates the builder will, or its decisions do not replay.
    """
    concept_of = _concept_of(inventory)
    applicable: dict[str, dict] = {}
    out: dict[str, dict[ModificationType, tuple[ApprovedRewrite, ...]]] = {}
    for leaf in sorted(available):
        concept = concept_of[leaf]
        if concept not in applicable:
            applicable[concept] = pantry.for_concept(concept)
        by_type = compatible_rewrites(
            applicable[concept], inventory.text(leaf), inventory.axis_values(leaf),
        )
        out[leaf] = {t: rws for t, rws in by_type.items() if t in available[leaf]}
    return out


def leaf_slots(
    pantry: Pantry,
    inventory: LeafInventory,
    available: Mapping[str, frozenset],
) -> dict[str, dict[ModificationType, frozenset]]:
    """The span view of :func:`leaf_rewrites`: each available type -> the spans
    its compatible rewrites touch. Feeds :func:`placeable_depth`."""
    return {
        leaf: {t: frozenset(r.dedup_key for r in rws) for t, rws in by_type.items()}
        for leaf, by_type in leaf_rewrites(pantry, inventory, available).items()
    }


def _assign_spans(
    types: Sequence[ModificationType],
    by_type: Mapping[ModificationType, Sequence[ApprovedRewrite]],
    reuse_cap: Mapping[str, int],
    usage: Mapping[str, int],
) -> Optional[tuple[ApprovedRewrite, ...]]:
    """One uncapped rewrite per type, on pairwise-distinct spans, or ``None``.

    Depth-first over least-used-first candidates, so whenever the plain greedy
    pick succeeds it is exactly what this returns; the search only differs when
    an early pick takes the one span a later type needs. Per level only the
    least-used rewrite of each span is tried: what stays feasible downstream
    depends on the spans taken, not on which rewrite took them.
    """
    picks: list[ApprovedRewrite] = []

    def search(i: int, taken: frozenset) -> bool:
        if i == len(types):
            return True
        cap = reuse_cap.get(types[i].value)
        tried: set = set()
        for rewrite in sorted(by_type.get(types[i], ()),
                              key=lambda r: (usage.get(r.uid, 0), r.uid)):
            if cap is not None and usage.get(rewrite.uid, 0) >= cap:
                continue
            if rewrite.dedup_key in taken or rewrite.dedup_key in tried:
                continue
            tried.add(rewrite.dedup_key)
            picks.append(rewrite)
            if search(i + 1, taken | {rewrite.dedup_key}):
                return True
            picks.pop()
        return False

    return tuple(picks) if search(0, frozenset()) else None


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


def build_dose_plan(
    pantry: Pantry,
    inventory: LeafInventory,
    order: Mapping[str, tuple[ModificationType, ...]],
    pool: Sequence[str],
    *,
    reuse_cap: Mapping[str, int],
    per_count: int,
) -> tuple[PlannedVariant, ...]:
    """The five rungs, built leaf-atomically over a common pool (D4 + D5).

    For each candidate leaf in ``pool`` order, all ``LADDER_MAX`` rungs are
    built together from the leaf's nested type order. If any rung cannot be
    filled — every compatible rewrite of the type it needs is capped out — the
    leaf's whole ladder is reverted and the next candidate is tried, so the
    accepted leaves always carry a COMPLETE ladder and the five count cells
    share one population. Stops at ``per_count`` accepted leaves.

    Each leaf's rewrites sit on pairwise-distinct spans; when an early type's
    least-used pick would take the only span a later type can use, another
    assignment is searched before the leaf is given up (:func:`_assign_spans`).

    Reuse caps count per RUN here, not per condition: the five rungs of a leaf
    are built together, so a single counter is the only coherent accounting.

    Either delivers exactly ``per_count`` complete ladders or raises
    :class:`DoseLadderError` — it never returns a short plan. A partial
    delivery would be silent (every rung short by the same amount, with
    nothing in the return value to say so), and this repo's pattern for that
    class of degradation (see the emitter's ``applied_count_mismatch``) is to
    stop rather than let it ship unnoticed.
    """
    concept_of = _concept_of(inventory)
    # resolved once per concept, not once per leaf (see `compatible_rewrites`)
    applicable: dict[str, dict] = {}
    usage: dict[str, int] = {}
    blocked: Counter = Counter()
    plan: list[PlannedVariant] = []
    accepted = 0

    for leaf in pool:
        # `pool_min > per_count` by config, so the tail is reserve: leaves whose
        # ladder cannot be built are skipped and later candidates take their
        # place. See `DoseBudgets.effective_pool_min`.
        if accepted >= per_count:
            break
        if leaf not in order:
            blocked[NOT_ORDERED] += 1
            continue
        concept = concept_of[leaf]
        if concept not in applicable:
            applicable[concept] = pantry.for_concept(concept)
        by_type = compatible_rewrites(
            applicable[concept], inventory.text(leaf), inventory.axis_values(leaf),
        )
        types = order[leaf]
        picks = _assign_spans(types, by_type, reuse_cap, usage)
        if picks is None:
            exhausted = [
                t.value for t in types
                if _least_used(by_type.get(t, ()), reuse_cap.get(t.value), usage) is None
            ]
            blocked.update(exhausted or [SPAN_CONFLICT])
            continue
        for pick in picks:
            usage[pick.uid] = usage.get(pick.uid, 0) + 1
        for k in range(1, LADDER_MAX + 1):
            plan.append(PlannedVariant(
                condition=f"dose_{k}", concept_key=concept,
                leaf_item_key=leaf, rewrites=tuple(picks[:k]),
            ))
        accepted += 1

    if accepted < per_count:
        raise DoseLadderError(
            f"pool_exhausted: only {accepted} of {per_count} requested ladders "
            f"could be built from a pool of {len(pool)} leaves. Every rung is "
            f"short by the same amount, so the delivered set would miss the "
            f"per-count floor. Ladders were blocked by these types running out "
            f"of uncapped rewrites: {dict(blocked.most_common())} "
            f"({NOT_ORDERED!r} counts pool leaves `nested_order` left out "
            f"because the caps left no {LADDER_MAX} types that fit; "
            f"{SPAN_CONFLICT!r} counts ladders whose types all had uncapped "
            f"rewrites but no assignment to distinct spans: the order was "
            f"built without `slots`, or caps left only colliding spans). "
            f"If one type "
            f"dominates that list its `reuse_cap` is the binding constraint and "
            f"raising `pool_min` will NOT help; if the list is empty or thinly "
            f"spread, the pool is simply too short — raise `pool_min` above "
            f"`per_count`, or lower `per_count`"
        )

    return tuple(plan)


def nested_order(
    admitted: Mapping[str, frozenset],
    seed: int,
    *,
    rewrites: Optional[Mapping[str, Mapping[ModificationType, Sequence[ApprovedRewrite]]]] = None,
    reuse_cap: Optional[Mapping[str, int]] = None,
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

    ``rewrites`` (from :func:`leaf_rewrites`) makes stage 1 skip a type that no
    longer has an assignment next to the ones already chosen: a rewrite on a
    span of its own, under ``reuse_cap``. Without it every type is taken to
    have a span of its own and no cap. Ignoring caps, the sets of types that
    fit form a transversal matroid, so the greedy still returns the least-used
    feasible choice, and a leaf where ``LADDER_MAX`` types fit and six or more
    are available has at least two feasible top-rung compositions — D5's
    reason for ``d >= 6`` carries over unchanged.

    With caps, a thin type (few distinct rewrites) is included only while it
    has capacity left, and the other types fill in: the top cell's balance
    becomes capacity-limited, which the corpus report shows. Capacity is spent
    in ``admitted``'s own order and committed with the very call
    :func:`build_dose_plan` makes, so pass the pool in pool order and the
    builder replays every decision without reverting a leaf. A leaf left with
    fewer than ``LADDER_MAX`` feasible types is omitted — it is reserve, and
    the builder skips it.

    On balance (their §3), stated honestly: stage 1 makes the top cell even.
    Cells below it cannot be made exactly even by a greedy, because the
    positions are NOT independent — which type a leaf places at position ``p``
    constrains what remains for ``p+1`` — so a small residual spread survives.
    It is a residual of a few leaves per cell against cells of order a
    hundred, and it is noise rather than bias: it does not favour particular
    types across seeds (measured — see the corpus report). On real data the
    binding constraint is admission anyway (types are admitted by very
    different numbers of leaves), which no ordering policy can undo.

    Raises :class:`DoseLadderError` for a leaf where fewer than ``LADDER_MAX``
    types fit even without caps — the pool selection must have excluded it.
    """
    caps = reuse_cap or {}
    usage: dict[str, int] = {}
    inclusion: Counter = Counter()
    per_position: list[Counter] = [Counter() for _ in range(LADDER_MAX)]
    order: dict[str, tuple[ModificationType, ...]] = {}
    for leaf in admitted:
        types = admitted[leaf]
        by_type = rewrites[leaf] if rewrites is not None else None
        spans = (
            {t: frozenset(r.dedup_key for r in by_type.get(t, ())) for t in types}
            if by_type is not None else {t: frozenset({t}) for t in types}
        )
        fits = placeable_depth(spans)
        if fits < LADDER_MAX:
            raise DoseLadderError(
                f"ladder_too_deep: leaf {leaf!r} admits {len(types)} types on "
                f"{fits} distinct spans, needs {LADDER_MAX} — it should not be "
                f"in the pool"
            )
        rng = random.Random(seed ^ zlib.crc32(leaf.encode("utf-8")))
        shuffled = rng.sample(sorted(types, key=lambda t: t.value), len(types))
        rank = {t: i for i, t in enumerate(shuffled)}

        # stage 1: which types ride this leaf's ladder at all
        used: list[ModificationType] = []
        for mtype in sorted(shuffled, key=lambda t: (inclusion[t], rank[t])):
            if by_type is None or _assign_spans((*used, mtype), by_type, caps, usage):
                used.append(mtype)
                if len(used) == LADDER_MAX:
                    break
        if len(used) < LADDER_MAX:
            continue
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
        if by_type is not None:
            for pick in _assign_spans(order[leaf], by_type, caps, usage):
                usage[pick.uid] = usage.get(pick.uid, 0) + 1
    return order


def depth_histogram(available: Mapping[str, frozenset]) -> dict[int, int]:
    """``{number of available types: number of leaves}`` — the measurement D5
    defers to, and a row of the corpus report."""
    return dict(sorted(Counter(len(v) for v in available.values()).items()))


def select_pool(
    available: Mapping[str, frozenset],
    concept_of: Mapping[str, str],
    *,
    pool_min: int,
    min_depth: int,
) -> tuple[int, tuple[str, ...]]:
    """The common leaf pool (D5): ``(depth, leaves)``.

    Picks the DEEPEST ``d >= min_depth`` for which at least ``pool_min`` leaves
    admit ``d`` types, then draws ``pool_min`` of them SPREAD ACROSS CONCEPTS
    via :func:`_spread_across_concepts` — including the note there on keeping
    ``pool_min`` comfortably above the number of concepts, since under-
    provisioning it drops whole concepts silently rather than erroring.

    All five rungs run on these same leaves, so the count cells share one
    population and the dose effect carries no leaf-difficulty selection. That
    is D5's guarantee, and it is unaffected by how the pool is spread: which
    leaves are chosen is orthogonal to every rung using the identical set.

    ``concept_of`` must cover every key of ``available``; use
    :func:`leaf_concept_map` on the inventory the probe ran on. A gap raises
    :class:`DoseLadderError` — see below — rather than a bare ``KeyError``,
    since both this function and ``leaf_concept_map`` are public and an
    external caller can trip it.

    Raises :class:`DoseLadderError` when ``concept_of`` is missing a leaf, or
    when no depth fills the pool — silently dropping to a shallower ladder
    would void D5's guarantee.
    """
    if min_depth <= LADDER_MAX:
        raise DoseLadderError(
            f"min_depth_too_shallow: {min_depth} <= LADDER_MAX={LADDER_MAX} "
            f"would leave rung {LADDER_MAX} with no choice of composition (D5)"
        )
    missing = sorted(set(available) - set(concept_of))
    if missing:
        raise DoseLadderError(
            f"concept_of_incomplete: {len(missing)} leaf/leaves in `available` "
            f"have no concept, e.g. {missing[:3]} — pass "
            f"`leaf_concept_map(inventory)` for the inventory the probe ran on"
        )
    histogram = depth_histogram(available)
    deepest = max(histogram, default=0)
    for depth in range(deepest, min_depth - 1, -1):
        eligible = tuple(sorted(k for k, v in available.items() if len(v) >= depth))
        if len(eligible) >= pool_min:
            qualifying: dict[str, list[str]] = {}
            for leaf in eligible:
                qualifying.setdefault(concept_of[leaf], []).append(leaf)
            return depth, _spread_across_concepts(pool_min, qualifying)
    raise DoseLadderError(
        f"pool_too_small: no depth >= {min_depth} yields {pool_min}+ leaves; "
        f"depth histogram = {histogram}"
    )


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
        per rung item (the ladder uses the SAME leaves at every rung).

        Leaving ``pool_min`` unset is a trap: the fallback to ``per_count``
        gives :func:`build_dose_plan` NO reserve, so any leaf whose ladder
        fails to build (a capped-out type) reduces the delivered count below
        ``per_count`` and the run raises rather than silently shipping short
        (D-shortfall). A config that wants the ``per_count`` floor honoured
        must set ``pool_min`` above it. That reserve is not free, though: a
        larger ``pool_min`` demands more leaves at the chosen depth, which
        can force :func:`select_pool` to settle for a shallower ``d``.
        """
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
