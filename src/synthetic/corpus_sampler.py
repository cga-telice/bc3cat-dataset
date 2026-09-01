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


def _allocate(n: int, leaf_counts: Mapping[str, int]) -> dict[str, int]:
    """Split ``n`` across concepts proportional to leaf counts.

    Largest-remainder rounding, minimum 1 per applicable concept (funded by
    the largest allocations), capped at each concept's leaf count (surplus
    redistributed to concepts with spare leaves). Deterministic.
    """
    keys = sorted(k for k, c in leaf_counts.items() if c > 0)
    if not keys or n <= 0:
        return {}
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

    # cap at leaf count; redistribute surplus to spare capacity
    surplus = 0
    for k in keys:
        if alloc[k] > leaf_counts[k]:
            surplus += alloc[k] - leaf_counts[k]
            alloc[k] = leaf_counts[k]
    while surplus > 0:
        spare = sorted((k for k in keys if alloc[k] < leaf_counts[k]),
                       key=lambda k: (-(leaf_counts[k] - alloc[k]), k))
        if not spare:
            break  # inventory exhausted — the condition falls short
        alloc[spare[0]] += 1
        surplus -= 1

    return {k: a for k, a in alloc.items() if a > 0}


def _condition_type(condition: str) -> ModificationType:
    return ModificationType(condition[len(_SINGLE_PREFIX):])


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
    the inventory). The reuse counter is global across the whole plan, so
    ``all_combined`` draws also honour the thin-type caps.
    """
    concept_keys = tuple(sorted(set(concepts) & set(inventory.concepts())))
    applicable = {c: pantry.for_concept(c) for c in concept_keys}
    usage: dict[str, int] = {}
    plan: list[PlannedVariant] = []

    for condition in CONDITIONS:
        target = budgets.targets[condition]
        if condition == _ALL_COMBINED:
            eligible = [c for c in concept_keys
                        if any(t in applicable[c] for t in NINE_TYPES)]
        else:
            mtype = _condition_type(condition)
            eligible = [c for c in concept_keys if mtype in applicable[c]]
        leaf_counts = {c: len(inventory.leaves(c)) for c in eligible}
        alloc = _allocate(target, leaf_counts)
        rng = random.Random(budgets.seed ^ zlib.crc32(condition.encode("utf-8")))

        for concept_key in sorted(alloc):
            chosen_leaves = rng.sample(
                list(inventory.leaves(concept_key)), alloc[concept_key]
            )
            for leaf in chosen_leaves:
                if condition == _ALL_COMBINED:
                    rewrites: list[ApprovedRewrite] = []
                    used_dedup: set = set()
                    for t in NINE_TYPES:
                        cands = applicable[concept_key].get(t)
                        if not cands:
                            continue  # type not applicable here — skip
                        pick = _pick_rewrite(cands, t, budgets.reuse_cap,
                                             usage, frozenset(used_dedup))
                        if pick is None:
                            continue  # capped out / dedup-blocked — skip type
                        rewrites.append(pick)
                        used_dedup.add(pick.dedup_key)
                else:
                    pick = _pick_rewrite(applicable[concept_key][mtype], mtype,
                                         budgets.reuse_cap, usage)
                    rewrites = [pick] if pick is not None else []
                if not rewrites:
                    continue  # deficit — never refilled from other types
                for r in rewrites:
                    usage[r.uid] = usage.get(r.uid, 0) + 1
                plan.append(PlannedVariant(
                    condition=condition,
                    concept_key=concept_key,
                    leaf_item_key=leaf,
                    rewrites=tuple(rewrites),
                ))

    return tuple(plan)


def plan_report(
    plan: tuple[PlannedVariant, ...], budgets: Budgets
) -> dict[str, dict[str, int]]:
    """Per condition: achieved n, unique rewrites, max reuse, deficit."""
    out: dict[str, dict[str, int]] = {}
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
    return out
