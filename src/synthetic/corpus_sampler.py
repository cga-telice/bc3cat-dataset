"""Deterministic sampling plan for the Sprint 39 pilot synthetic corpus.

Consumes the approved-rewrite :class:`~synthetic.pantry.Pantry`, the leaf
inventory of the original OEB corpus, and the budgets YAML
(``configs/synthetic/variant_budgets.yaml``) and produces a fully
deterministic plan: one :class:`PlannedVariant` per synthetic item to
materialise — ``(condition, concept_key, leaf_item_key, rewrites)``.

Design (SPRINT_39_DESIGN.md, binding):

* 10 conditions — ``single_{type}`` for the nine information-preserving
  types plus ``all_combined``.
* Per condition, the target n is split across the concepts where the
  condition applies, proportional to each concept's leaf count
  (largest-remainder rounding, minimum 1 where applicable).
* Leaves are unique within a condition (a leaf may recur across
  conditions). Leaf choice uses ``random.Random(seed ^ zlib.crc32(cond))``
  — a stable hash, never builtin ``hash()`` (per-process salting would
  break determinism).
* Singles carry exactly one rewrite of their type, chosen by weighted
  round-robin (least-used first) honouring ``reuse_cap`` for the thin
  types; when the cap exhausts the applicable pantry the slice falls
  short and the deficit is reported — never refilled from other types.
  Reuse counters are **per condition** (reset at each condition's start),
  so a thin-type rewrite capped out in its single condition is still
  drawable in ``all_combined`` — where the same per-condition caps apply.
* Allocation is capacity-aware: a concept never receives more variants
  than its applicable rewrites can serve under the caps; the surplus is
  redistributed within the condition to concepts with spare capacity.
* ``all_combined`` carries one rewrite of each applicable type (types
  with nothing available are skipped) with no two rewrites sharing a
  ``dedup_key``; composition validation is the driver's job.

Pure CPU, no I/O beyond :func:`load_budgets`. Same inputs → identical plan.
"""

from __future__ import annotations

import math
import random
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

import yaml

from utils import config
from .pantry import ApprovedRewrite, Pantry
from .taxonomy import ModificationType

__all__ = [
    "NINE_TYPES",
    "CONDITIONS",
    "DEFAULT_BUDGETS_PATH",
    "Budgets",
    "LeafInventory",
    "PlannedVariant",
    "load_budgets",
    "leaf_inventory_from_frame",
    "build_plan",
    "plan_report",
]

#: The nine information-preserving modification types of the pilot
#: (spec order — the order ``all_combined`` picks rewrites in).
NINE_TYPES: tuple[ModificationType, ...] = (
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.TEMPLATE_PARAPHRASE,
    ModificationType.SYNONYM_LABEL,
    ModificationType.COMPRESSION,
    ModificationType.REORDER,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_EXPANSION,
    ModificationType.UNIT_CONVERSION,
)

_ALL_COMBINED = "all_combined"
_SINGLE_PREFIX = "single_"

#: The 10 pilot conditions, in processing order.
CONDITIONS: tuple[str, ...] = tuple(
    f"{_SINGLE_PREFIX}{t.value}" for t in NINE_TYPES
) + (_ALL_COMBINED,)

DEFAULT_BUDGETS_PATH = (
    config.REPO_ROOT / "configs" / "synthetic" / "variant_budgets.yaml"
)


# ----- budgets ------------------------------------------------------------

@dataclass(frozen=True)
class Budgets:
    """Validated corpus budgets: per-condition targets + thin-type caps."""

    seed: int
    targets: Mapping[str, int]
    reuse_cap: Mapping[str, int]


def _require_positive_int(value: object, what: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"budgets_invalid: {what} must be a positive int, "
                         f"got {value!r}")
    return value


def load_budgets(path: Optional[Path] = None) -> Budgets:
    """Read + validate the budgets YAML (default: the committed spec file).

    Fails loud (``ValueError("budgets_invalid: ...")``) unless ``targets``
    covers exactly the 10 conditions with positive-int values.
    """
    path = Path(path) if path else DEFAULT_BUDGETS_PATH
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"budgets_invalid: {path.name} is not a mapping")

    seed = _require_positive_int(raw.get("seed"), "seed")

    targets = raw.get("targets")
    if not isinstance(targets, dict):
        raise ValueError("budgets_invalid: targets missing or not a mapping")
    expected = set(CONDITIONS)
    got = set(targets)
    if got != expected:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise ValueError(
            f"budgets_invalid: targets must cover exactly the 10 conditions "
            f"(missing={missing}, extra={extra})"
        )
    for condition, n in targets.items():
        _require_positive_int(n, f"targets[{condition}]")

    reuse_cap = raw.get("reuse_cap") or {}
    if not isinstance(reuse_cap, dict):
        raise ValueError("budgets_invalid: reuse_cap is not a mapping")
    valid_types = {t.value for t in NINE_TYPES}
    for mtype, cap in reuse_cap.items():
        if mtype not in valid_types:
            raise ValueError(f"budgets_invalid: reuse_cap type {mtype!r} is "
                             f"not one of the nine pilot types")
        _require_positive_int(cap, f"reuse_cap[{mtype}]")

    return Budgets(seed=seed, targets=dict(targets), reuse_cap=dict(reuse_cap))


# ----- leaf inventory -----------------------------------------------------

class LeafInventory:
    """Leaves of the original corpus grouped by concept key.

    Built directly from ``{concept_key: [item_key, ...]}`` (tests) or from
    the original OEB parquet via :func:`leaf_inventory_from_frame`.
    Concepts and leaves are kept sorted so iteration order is stable.
    """

    def __init__(self, leaves_by_concept: Mapping[str, Iterable[str]]):
        self._by_concept: dict[str, tuple[str, ...]] = {
            concept: tuple(sorted(leaves))
            for concept, leaves in sorted(leaves_by_concept.items())
        }

    def concepts(self) -> tuple[str, ...]:
        return tuple(self._by_concept)

    def leaves(self, concept_key: str) -> tuple[str, ...]:
        return self._by_concept.get(concept_key, ())


def leaf_inventory_from_frame(df) -> LeafInventory:
    """Group parquet rows (``item_key``, ``parent_key``) into an inventory.

    Reuses the repo's own concept↔item rule (stage_runners.transform_data,
    validated by metadata.validate_item): the concept key IS the parquet's
    ``parent_key``. Parametric concepts end in ``$`` and expand to
    ``item_key = parent_key[:-1] + <axis labels>``; non-parametric concepts
    keep ``item_key == parent_key`` (their single leaf is themselves).
    Fails loud on any row violating the rule instead of guessing a prefix.
    """
    grouped: dict[str, list[str]] = {}
    for item_key, parent_key in zip(df["item_key"], df["parent_key"]):
        if not (isinstance(parent_key, str) and isinstance(item_key, str)):
            raise ValueError(
                f"inventory_invalid: non-string keys ({item_key!r}, {parent_key!r})"
            )
        if parent_key.endswith("$"):
            ok = item_key.startswith(parent_key[:-1])
        else:
            ok = item_key == parent_key
        if not ok:
            raise ValueError(
                f"inventory_invalid: item_key {item_key!r} does not follow "
                f"its parent {parent_key!r}"
            )
        grouped.setdefault(parent_key, []).append(item_key)
    return LeafInventory(grouped)


# ----- the plan -----------------------------------------------------------

@dataclass(frozen=True)
class PlannedVariant:
    """One synthetic item to materialise."""

    condition: str
    concept_key: str
    leaf_item_key: str
    rewrites: tuple[ApprovedRewrite, ...]


def _allocate(
    n: int,
    leaf_counts: Mapping[str, int],
    capacities: Optional[Mapping[str, float]] = None,
) -> dict[str, int]:
    """Split ``n`` across concepts proportional to leaf counts.

    Largest-remainder rounding, minimum 1 per applicable concept (funded by
    the largest allocations), capped at each concept's effective limit —
    ``min(leaf count, rewrite capacity)`` — with the surplus redistributed
    within the condition to concepts with spare capacity. Deterministic.
    """
    keys = sorted(k for k, c in leaf_counts.items() if c > 0)
    if not keys or n <= 0:
        return {}
    capacities = capacities or {}
    limits = {
        k: min(leaf_counts[k], int(min(capacities.get(k, math.inf), n)))
        for k in keys
    }
    total = sum(leaf_counts[k] for k in keys)
    quotas = {k: n * leaf_counts[k] / total for k in keys}
    alloc = {k: math.floor(quotas[k]) for k in keys}
    remainder = n - sum(alloc.values())
    by_fraction = sorted(
        keys, key=lambda k: (-(quotas[k] - alloc[k]), -leaf_counts[k], k)
    )
    for k in by_fraction[:remainder]:
        alloc[k] += 1

    # minimum 1 where applicable (funded by the largest allocations)
    for k in keys:
        if alloc[k] == 0:
            donors = sorted((d for d in keys if alloc[d] >= 2),
                            key=lambda d: (-alloc[d], d))
            if donors:
                alloc[donors[0]] -= 1
                alloc[k] = 1

    # cap at the effective limit; redistribute surplus to spare capacity
    surplus = 0
    for k in keys:
        if alloc[k] > limits[k]:
            surplus += alloc[k] - limits[k]
            alloc[k] = limits[k]
    while surplus > 0:
        spare = sorted((k for k in keys if alloc[k] < limits[k]),
                       key=lambda k: (-(limits[k] - alloc[k]), k))
        if not spare:
            break  # capacity exhausted — the condition falls short
        alloc[spare[0]] += 1
        surplus -= 1

    return {k: a for k, a in alloc.items() if a > 0}


def _rewrite_capacity(
    condition: str,
    applicable: Mapping[ModificationType, tuple[ApprovedRewrite, ...]],
    reuse_cap: Mapping[str, int],
) -> float:
    """Max variants this concept's applicable rewrites can serve here.

    Per-condition usage starts at zero, so capacity per capped type is
    ``n_applicable_rewrites × cap``; an uncapped type is unbounded. For
    ``all_combined`` a variant exists while any applicable type still has
    capacity, so per-type capacities add up (infinite dominates).
    """
    def type_capacity(t: ModificationType) -> float:
        cap = reuse_cap.get(t.value)
        if cap is None:
            return math.inf
        return len(applicable.get(t, ())) * cap

    if condition == _ALL_COMBINED:
        return sum(type_capacity(t) for t in NINE_TYPES if t in applicable)
    return type_capacity(_condition_type(condition))


def _condition_type(condition: str) -> ModificationType:
    return ModificationType(condition[len(_SINGLE_PREFIX):])


def _draw_rewrites(
    condition: str,
    applicable: Mapping[ModificationType, tuple[ApprovedRewrite, ...]],
    reuse_cap: Mapping[str, int],
    usage: dict[str, int],
) -> tuple[ApprovedRewrite, ...]:
    """The rewrites for one variant — empty when the concept is capped out.

    Within one condition the result is monotone: once empty for a concept,
    it stays empty (usage only grows), so callers may stop trying it.
    """
    if condition == _ALL_COMBINED:
        rewrites: list[ApprovedRewrite] = []
        used_dedup: set = set()
        for t in NINE_TYPES:
            cands = applicable.get(t)
            if not cands:
                continue  # type not applicable here — skip
            pick = _pick_rewrite(cands, t, reuse_cap, usage,
                                 frozenset(used_dedup))
            if pick is None:
                continue  # capped out / dedup-blocked — skip type
            rewrites.append(pick)
            used_dedup.add(pick.dedup_key)
        return tuple(rewrites)
    mtype = _condition_type(condition)
    pick = _pick_rewrite(applicable[mtype], mtype, reuse_cap, usage)
    return (pick,) if pick is not None else ()


def _pick_rewrite(
    candidates: tuple[ApprovedRewrite, ...],
    mtype: ModificationType,
    reuse_cap: Mapping[str, int],
    usage: dict[str, int],
    used_dedup: frozenset = frozenset(),
) -> Optional[ApprovedRewrite]:
    """Least-used-first (weighted round-robin), honouring the type's cap.

    Returns ``None`` when every applicable rewrite is capped out (or its
    ``dedup_key`` is already taken within an ``all_combined`` variant).
    """
    cap = reuse_cap.get(mtype.value)
    ordered = sorted(candidates, key=lambda r: (usage.get(r.uid, 0), r.uid))
    for rewrite in ordered:
        if cap is not None and usage.get(rewrite.uid, 0) >= cap:
            continue
        if rewrite.dedup_key in used_dedup:
            continue
        return rewrite
    return None


def build_plan(
    pantry: Pantry,
    inventory: LeafInventory,
    budgets: Budgets,
    concepts: Iterable[str],
) -> tuple[PlannedVariant, ...]:
    """Produce the full deterministic sampling plan.

    ``concepts`` restricts the plan to those concept keys (intersected with
    the inventory). Reuse counters are per condition — reset at each
    condition's start — so caps bound reuse within a condition; the caps
    themselves apply in every condition, ``all_combined`` included.
    """
    concept_keys = tuple(sorted(set(concepts) & set(inventory.concepts())))
    applicable = {c: pantry.for_concept(c) for c in concept_keys}
    plan: list[PlannedVariant] = []

    for condition in CONDITIONS:
        usage: dict[str, int] = {}
        target = budgets.targets[condition]
        if condition == _ALL_COMBINED:
            eligible = [c for c in concept_keys
                        if any(t in applicable[c] for t in NINE_TYPES)]
        else:
            mtype = _condition_type(condition)
            eligible = [c for c in concept_keys if mtype in applicable[c]]
        leaf_counts = {c: len(inventory.leaves(c)) for c in eligible}
        capacities = {
            c: _rewrite_capacity(condition, applicable[c], budgets.reuse_cap)
            for c in eligible
        }
        alloc = _allocate(target, leaf_counts, capacities)
        rng = random.Random(budgets.seed ^ zlib.crc32(condition.encode("utf-8")))

        # Per-concept shuffled leaf order, consumed left to right; a leaf is
        # only consumed when a variant is actually produced, so leaves stay
        # unique within the condition.
        orders = {
            c: rng.sample(list(inventory.leaves(c)), leaf_counts[c])
            for c in sorted(eligible)
        }
        pos = {c: 0 for c in eligible}
        dead: set[str] = set()  # concepts capped out for this condition
        cond_plan: list[PlannedVariant] = []

        def _produce(concept_key: str) -> bool:
            if concept_key in dead or pos[concept_key] >= len(orders[concept_key]):
                return False
            rewrites = _draw_rewrites(condition, applicable[concept_key],
                                      budgets.reuse_cap, usage)
            if not rewrites:
                dead.add(concept_key)  # deficit — never refilled cross-type
                return False
            leaf = orders[concept_key][pos[concept_key]]
            pos[concept_key] += 1
            for r in rewrites:
                usage[r.uid] = usage.get(r.uid, 0) + 1
            cond_plan.append(PlannedVariant(
                condition=condition,
                concept_key=concept_key,
                leaf_item_key=leaf,
                rewrites=rewrites,
            ))
            return True

        # main pass: the proportional allocation
        for concept_key in sorted(alloc):
            for _ in range(alloc[concept_key]):
                if not _produce(concept_key):
                    break

        # recovery pass: shared rewrites make per-concept capacities
        # overestimates, so refill any remaining deficit from concepts that
        # still have spare leaves and live rewrites (deterministic sweeps,
        # most-spare-leaves first; stop when a full sweep adds nothing).
        while len(cond_plan) < target:
            candidates = sorted(
                (c for c in eligible
                 if c not in dead and pos[c] < len(orders[c])),
                key=lambda c: (-(len(orders[c]) - pos[c]), c),
            )
            progressed = False
            for concept_key in candidates:
                if len(cond_plan) >= target:
                    break
                progressed = _produce(concept_key) or progressed
            if not progressed:
                break  # condition-wide capacity exhausted — deficit reported

        plan.extend(cond_plan)

    return tuple(plan)


def plan_report(
    plan: tuple[PlannedVariant, ...], budgets: Budgets
) -> dict[str, dict]:
    """Per condition: achieved n, unique rewrites, max reuse, deficit.

    The ``all_combined`` row additionally carries ``type_presence`` —
    ``{type: number of all_combined variants carrying a rewrite of it}``
    (at most one rewrite per type per variant, so this counts variants).
    """
    out: dict[str, dict] = {}
    for condition in CONDITIONS:
        variants = [p for p in plan if p.condition == condition]
        uses = Counter(r.uid for p in variants for r in p.rewrites)
        target = budgets.targets[condition]
        out[condition] = {
            "n": len(variants),
            "target": target,
            "unique_rewrites": len(uses),
            "max_reuse": max(uses.values()) if uses else 0,
            "deficit": target - len(variants),
        }
        if condition == _ALL_COMBINED:
            presence = Counter(
                r.mtype.value for p in variants for r in p.rewrites
            )
            out[condition]["type_presence"] = dict(sorted(presence.items()))
    return out
