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
  ``dedup_key``; for ``template_paraphrase`` it carries one rewrite per
  FIELD — one RESUMEN-template and one TEXTO-template rewrite — so both
  output surfaces move (César, 2026-09-02). Composition validation is
  the driver's job.
* Leaf↔rewrite compatibility: an L1 value rewrite or L2 fragment rewrite
  only surfaces in leaves whose parameters select that value/fragment, so
  the sampler pairs a rewrite with a leaf only when it is compatible —
  value-precise where the leaf's selected ``(axis, value)`` pairs are
  known (L1 = exact pair membership; L2 = selected-value equality, with
  matches swallowed by a longer sibling value rejected), else a
  boundary-aware match of the normalized ``payload["original"]`` in the
  leaf's original combined text (resumen + texto); L3 template types are
  always compatible. Incompatible picks would render as no-ops — and, in
  ``all_combined``, mislabel the item's ``modification_types``.

Pure CPU, no I/O beyond :func:`load_budgets`. Same inputs → identical plan.
"""

from __future__ import annotations

import math
import random
import re
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
    "leaf_inventory_from_frames",
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
    """Validated corpus budgets.

    Two modes:

    * ``legacy`` (default) — flat per-condition ``targets`` distributed across
      concepts proportional to leaves, with a cross-concept recovery pass.
    * ``leaf_proportional`` (Option A) — each concept gets a total budget
      proportional to its leaf share, clamped to ``[floor, cap_per_leaf*leaves]``;
      that budget is split across conditions by ``type_mix`` and any single-type
      shortfall is absorbed by the concept's own ``all_combined`` (no
      cross-concept leakage). Keeps the item count per concept ∝ leaves while
      guaranteeing a coverage floor.
    """

    seed: int
    targets: Mapping[str, int]
    reuse_cap: Mapping[str, int]
    mode: str = "legacy"
    total: Optional[int] = None
    floor: Optional[int] = None
    cap_per_leaf: Optional[float] = None
    type_mix: Optional[Mapping[str, float]] = None


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

    reuse_cap = raw.get("reuse_cap") or {}
    if not isinstance(reuse_cap, dict):
        raise ValueError("budgets_invalid: reuse_cap is not a mapping")
    valid_types = {t.value for t in NINE_TYPES}
    for mtype, cap in reuse_cap.items():
        if mtype not in valid_types:
            raise ValueError(f"budgets_invalid: reuse_cap type {mtype!r} is "
                             f"not one of the nine pilot types")
        _require_positive_int(cap, f"reuse_cap[{mtype}]")

    mode = raw.get("mode", "legacy")
    if mode == "leaf_proportional":
        total = _require_positive_int(raw.get("total"), "total")
        floor = _require_positive_int(raw.get("floor"), "floor")
        cap = raw.get("cap_per_leaf")
        if not isinstance(cap, (int, float)) or cap <= 0:
            raise ValueError("budgets_invalid: cap_per_leaf must be a positive number")
        mix = raw.get("type_mix")
        if not isinstance(mix, dict) or set(mix) != set(CONDITIONS):
            raise ValueError("budgets_invalid: type_mix must cover exactly the "
                             "10 conditions")
        for c, w in mix.items():
            if not isinstance(w, (int, float)) or w < 0:
                raise ValueError(f"budgets_invalid: type_mix[{c}] must be >= 0")
        if sum(mix.values()) <= 0:
            raise ValueError("budgets_invalid: type_mix sums to 0")
        return Budgets(seed=seed, targets={}, reuse_cap=dict(reuse_cap),
                       mode="leaf_proportional", total=total, floor=floor,
                       cap_per_leaf=float(cap), type_mix=dict(mix))

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
        if type(n) is not int or n < 0:
            raise ValueError(f"budgets_invalid: targets[{condition}] must be a "
                             f"non-negative int, got {n!r}")
    if sum(targets.values()) <= 0:
        raise ValueError("budgets_invalid: at least one target must be positive")

    return Budgets(seed=seed, targets=dict(targets), reuse_cap=dict(reuse_cap))


# ----- leaf inventory -----------------------------------------------------

def _norm_ws(s: str) -> str:
    """Whitespace-normalize — the single normalization used on BOTH sides
    of every leaf↔rewrite compatibility check."""
    return " ".join(s.split())


class LeafInventory:
    """Leaves of the original corpus grouped by concept key.

    Each leaf carries its whitespace-normalized ORIGINAL combined text
    (``resumen + " " + texto``) and, when available, its selected
    ``(axis_label, value)`` pairs — the sampler only pairs a leaf with
    rewrites whose surface form actually appears in it (value-precise
    where the pairs are known). Built directly from
    ``{concept_key: [(item_key, combined_text[, axis_values]), ...]}``
    (tests; bare ``item_key`` strings are accepted with an empty text) or
    from the original OEB parquets via :func:`leaf_inventory_from_frames`.
    Concepts and leaves are kept sorted so iteration order is stable.
    """

    def __init__(self, leaves_by_concept: Mapping[str, Iterable]):
        self._by_concept: dict[str, tuple[str, ...]] = {}
        self._texts: dict[str, str] = {}
        self._axis_values: dict[str, tuple[tuple[str, str], ...]] = {}
        for concept, entries in sorted(leaves_by_concept.items()):
            keys: list[str] = []
            for entry in entries:
                values: tuple = ()
                if isinstance(entry, str):
                    key, text = entry, ""
                elif len(entry) == 2:
                    key, text = entry
                else:
                    key, text, values = entry
                keys.append(key)
                self._texts[key] = _norm_ws(text)
                self._axis_values[key] = tuple(sorted(
                    (_norm_ws(str(axis)), _norm_ws(str(value)))
                    for axis, value in values
                ))
            self._by_concept[concept] = tuple(sorted(keys))

    def concepts(self) -> tuple[str, ...]:
        return tuple(self._by_concept)

    def leaves(self, concept_key: str) -> tuple[str, ...]:
        return self._by_concept.get(concept_key, ())

    def text(self, item_key: str) -> str:
        """The leaf's normalized original combined text ("" if unknown)."""
        return self._texts.get(item_key, "")

    def axis_values(self, item_key: str) -> tuple[tuple[str, str], ...]:
        """The leaf's normalized selected `(axis_label, value)` pairs
        (empty when unknown — compatibility then falls back to the text)."""
        return self._axis_values.get(item_key, ())


def _check_parent_rule(item_key, parent_key) -> None:
    """The repo's own concept↔item rule (stage_runners.transform_data,
    validated by metadata.validate_item): the concept key IS the parquet's
    ``parent_key``. Parametric concepts end in ``$`` and expand to
    ``item_key = parent_key[:-1] + <axis labels>``; non-parametric concepts
    keep ``item_key == parent_key`` (their single leaf is themselves).
    Fails loud on any row violating the rule instead of guessing a prefix.
    """
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


def _axis_value_pairs(parameters: object) -> tuple[tuple[str, str], ...]:
    """`(axis_label, value)` pairs from one parquet `parameters` cell
    (`{axis_id: {"label": ..., "values": [{"label", "value"}]} | None}`).
    Unrecognised shapes yield `()` — compatibility then falls back to text."""
    if not isinstance(parameters, dict):
        return ()
    pairs: list[tuple[str, str]] = []
    for block in parameters.values():
        if not isinstance(block, dict):
            continue
        axis_label = block.get("label", "")
        for entry in block.get("values") if block.get("values") is not None else ():
            if isinstance(entry, dict) and entry.get("value") is not None:
                pairs.append((str(axis_label), str(entry["value"])))
    return tuple(pairs)


def leaf_inventory_from_frames(long_df, short_df) -> LeafInventory:
    """The real-data loader: join the long (texto) and short (resumen)
    parquets on ``item_key`` and build the inventory with each leaf's
    combined original text plus its selected `(axis_label, value)` pairs
    (from the long frame's ``parameters`` column, when present). Fails loud
    on a leaf missing from the short frame or on any concept-rule violation
    (see :func:`_check_parent_rule`).
    """
    resumen_by_key = dict(zip(short_df["item_key"], short_df["text"]))
    params_by_key = (
        dict(zip(long_df["item_key"], long_df["parameters"]))
        if "parameters" in long_df.columns
        else {}
    )
    grouped: dict[str, list[tuple[str, str, tuple]]] = {}
    for item_key, parent_key, texto in zip(
        long_df["item_key"], long_df["parent_key"], long_df["text"]
    ):
        _check_parent_rule(item_key, parent_key)
        resumen = resumen_by_key.get(item_key)
        if resumen is None:
            raise ValueError(
                f"inventory_invalid: item {item_key!r} missing from the "
                f"short (resumen) frame"
            )
        grouped.setdefault(parent_key, []).append(
            (
                item_key,
                f"{resumen} {texto}",
                _axis_value_pairs(params_by_key.get(item_key)),
            )
        )
    return LeafInventory(grouped)


def leaf_inventory_from_frame(df) -> LeafInventory:
    """Single-frame variant: texts come from ``df["text"]`` alone.

    Prefer :func:`leaf_inventory_from_frames` (resumen + texto) for real
    runs — with only one surface, rewrites whose original appears solely
    in the other surface would be judged incompatible.
    """
    grouped: dict[str, list[tuple[str, str]]] = {}
    for item_key, parent_key, text in zip(
        df["item_key"], df["parent_key"], df["text"]
    ):
        _check_parent_rule(item_key, parent_key)
        grouped.setdefault(parent_key, []).append((item_key, text))
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


#: Template-level types: the rewrite touches the shared L3 template, so it
#: surfaces in EVERY leaf of the concept — always compatible.
_L3_ALWAYS_COMPATIBLE = frozenset({
    ModificationType.REORDER,
    ModificationType.TEMPLATE_PARAPHRASE,
})


#: Characters that extend a word: a match glued to one of these on either
#: side is a substring hit, not the value/fragment itself (numeral "2" must
#: not match inside "220 kV"). Accented Spanish letters are word characters.
_WORD_CHARS = "0-9A-Za-zÁÉÍÓÚÑáéíóúñÜü"

#: L1 per-value types: their ``dedup_key`` is ``(axis_label, value)``, so
#: with known leaf axis-values compatibility is an exact pair membership.
_L1_VALUE_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})


def _boundary_search(needle_norm: str, haystack: str) -> bool:
    """Boundary-aware search: no word character glued to either side."""
    pattern = (
        rf"(?<![{_WORD_CHARS}]){re.escape(needle_norm)}(?![{_WORD_CHARS}])"
    )
    return re.search(pattern, haystack) is not None


def _compatible(
    rewrite: ApprovedRewrite,
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> bool:
    """Leaf↔rewrite compatibility.

    An L1 value rewrite or L2 fragment rewrite only surfaces in leaves
    whose parameters select that value/fragment. With the leaf's selected
    ``(axis_label, value)`` pairs known (the real-data loader supplies
    them), the check is value-precise:

    * L1 per-value types: compatible iff the leaf selects exactly
      ``(dedup axis label, original)`` — "5" on Nº TUBOS never rides a
      boundary hit inside BANDA's "i >= 5 horas".
    * L2 fragments: an original that exactly equals a selected value is
      compatible (the axis-twin surface); one that appears only INSIDE a
      longer selected value ("Diurno" in "Diurno Excepcional") is not.
    * otherwise fall back to the boundary-aware text match: the original
      appears in the leaf's normalized combined text with no word
      character glued to either side ("2" matches in "de 2 m", not in
      "220 kV").

    L3 types are always compatible (the template covers every leaf). A
    payload without an ``original`` surface cannot be checked and passes
    (fail-open — the driver's no-op filter is the backstop).
    """
    if rewrite.mtype in _L3_ALWAYS_COMPATIBLE:
        return True
    original = rewrite.payload.get("original")
    if not isinstance(original, str) or not original.strip():
        return True
    original_norm = _norm_ws(original)

    if leaf_axis_values:
        if rewrite.mtype in _L1_VALUE_TYPES and len(rewrite.dedup_key) == 2:
            # exact pair AND rendered surface: a selected value whose text
            # never surfaces (its twin fragment diverged) cannot change the
            # rendered item, so pair membership alone is not enough.
            axis_norm = _norm_ws(str(rewrite.dedup_key[0]))
            return (
                (axis_norm, original_norm) in leaf_axis_values
                and _boundary_search(original_norm, leaf_text)
            )
        selected = {value for _axis, value in leaf_axis_values}
        if original_norm in selected:
            return True
        if any(
            value != original_norm and _boundary_search(original_norm, value)
            for value in selected
        ):
            return False  # only surfaces inside a longer selected value

    return _boundary_search(original_norm, leaf_text)


def _draw_rewrites(
    condition: str,
    applicable: Mapping[ModificationType, tuple[ApprovedRewrite, ...]],
    reuse_cap: Mapping[str, int],
    usage: dict[str, int],
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> tuple[tuple[ApprovedRewrite, ...], int, bool]:
    """The rewrites for one variant on one leaf.

    Returns ``(rewrites, incompatible_type_skips, capacity_left)``:
    ``incompatible_type_skips`` counts types that still had uncapped
    rewrites but none compatible with THIS leaf; ``capacity_left`` says
    whether any applicable type still has an uncapped rewrite at all
    (leaf-independent — when False the concept is done for this
    condition, since usage only grows).
    """
    def _uncapped(t: ModificationType, cands):
        cap = reuse_cap.get(t.value)
        if cap is None:
            return list(cands)
        return [r for r in cands if usage.get(r.uid, 0) < cap]

    if condition != _ALL_COMBINED:
        mtype = _condition_type(condition)
        avail = _uncapped(mtype, applicable[mtype])
        if not avail:
            return (), 0, False
        compat = [
            r for r in avail if _compatible(r, leaf_text, leaf_axis_values)
        ]
        if not compat:
            return (), 1, True
        pick = _pick_rewrite(compat, mtype, reuse_cap, usage)
        return (pick,), 0, True

    rewrites: list[ApprovedRewrite] = []
    used_dedup: set = set()
    incompatible = 0
    capacity_left = False
    for t in NINE_TYPES:
        cands = applicable.get(t)
        if not cands:
            continue  # type not applicable to this concept — skip
        avail = _uncapped(t, cands)
        if not avail:
            continue  # capped out — skip type
        capacity_left = True
        compat = [
            r for r in avail if _compatible(r, leaf_text, leaf_axis_values)
        ]
        if not compat:
            incompatible += 1  # nothing of this type surfaces in this leaf
            continue
        if t is ModificationType.TEMPLATE_PARAPHRASE:
            # both output surfaces must move: one RESUMEN-template AND one
            # TEXTO-template rewrite per all_combined variant (a field with
            # an empty pool is skipped — real OEB coverage has both).
            for field in ("RESUMEN", "TEXTO"):
                pool = tuple(r for r in compat if r.dedup_key[0] == field)
                if not pool:
                    continue
                pick = _pick_rewrite(pool, t, reuse_cap, usage,
                                     frozenset(used_dedup))
                if pick is None:
                    continue  # dedup-blocked — skip field
                rewrites.append(pick)
                used_dedup.add(pick.dedup_key)
            continue
        pick = _pick_rewrite(compat, t, reuse_cap, usage,
                             frozenset(used_dedup))
        if pick is None:
            continue  # dedup-blocked — skip type
        rewrites.append(pick)
        used_dedup.add(pick.dedup_key)
    return tuple(rewrites), incompatible, capacity_left


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


# ----- Option A: leaf-proportional allocation -----------------------------

def _concept_budgets(
    leaf_counts: Mapping[str, int], total: int, floor: int, cap_per_leaf: float,
) -> dict[str, int]:
    """Per-concept item budget ∝ leaf share, clamped to ``[floor, cap]`` where
    ``cap = max(floor, round(cap_per_leaf*leaves))``. Deterministic."""
    keys = sorted(k for k, c in leaf_counts.items() if c > 0)
    supply = sum(leaf_counts[k] for k in keys)
    if supply == 0:
        return {}
    out: dict[str, int] = {}
    for k in keys:
        prop = round(total * leaf_counts[k] / supply)
        cap = max(floor, round(cap_per_leaf * leaf_counts[k]))
        out[k] = min(max(prop, floor), cap)
    return out


def _split_by_type(
    b_c: int, eligible: list[str], type_mix: Mapping[str, float],
) -> dict[str, int]:
    """Split a concept's budget across its eligible conditions by ``type_mix``
    (renormalised over the eligible set), largest-remainder to sum exactly ``b_c``."""
    if b_c <= 0:
        return {}
    weights = {c: type_mix.get(c, 0.0) for c in eligible if type_mix.get(c, 0.0) > 0}
    total_w = sum(weights.values())
    if total_w <= 0:
        return {}
    quotas = {c: b_c * weights[c] / total_w for c in weights}
    alloc = {c: math.floor(q) for c, q in quotas.items()}
    remainder = b_c - sum(alloc.values())
    order = sorted(quotas, key=lambda c: (-(quotas[c] - alloc[c]), c))
    for c in order[:remainder]:
        alloc[c] += 1
    return {c: a for c, a in alloc.items() if a > 0}


def _eligible(condition: str, applicable: Mapping[ModificationType, tuple]) -> bool:
    if condition == _ALL_COMBINED:
        return any(t in applicable for t in NINE_TYPES)
    return _condition_type(condition) in applicable


def _produce_condition(
    condition: str, alloc: Mapping[str, int], applicable: Mapping[str, dict],
    inventory: "LeafInventory", budgets: Budgets,
) -> tuple[list[PlannedVariant], dict]:
    """Main production pass for a condition against a fixed per-concept ``alloc``
    (no cross-concept recovery — Option A recovers within each concept via
    ``all_combined``). Same leaf-order/compatibility/reuse-cap semantics as the
    legacy pass."""
    eligible = list(alloc)
    usage: dict[str, int] = {}
    rng = random.Random(budgets.seed ^ zlib.crc32(condition.encode("utf-8")))
    orders = {c: rng.sample(list(inventory.leaves(c)), len(inventory.leaves(c)))
              for c in sorted(eligible)}
    pos = {c: 0 for c in eligible}
    dead: set[str] = set()
    cond_plan: list[PlannedVariant] = []
    cond_stats = {"incompatible_skips": 0}

    def _produce(c: str) -> bool:
        while c not in dead and pos[c] < len(orders[c]):
            leaf = orders[c][pos[c]]
            rewrites, n_incompatible, capacity_left = _draw_rewrites(
                condition, applicable[c], budgets.reuse_cap, usage,
                inventory.text(leaf), inventory.axis_values(leaf),
            )
            if rewrites:
                cond_stats["incompatible_skips"] += n_incompatible
                pos[c] += 1
                for r in rewrites:
                    usage[r.uid] = usage.get(r.uid, 0) + 1
                cond_plan.append(PlannedVariant(
                    condition=condition, concept_key=c,
                    leaf_item_key=leaf, rewrites=rewrites))
                return True
            if not capacity_left:
                dead.add(c)
                return False
            cond_stats["incompatible_skips"] += max(n_incompatible, 1)
            pos[c] += 1
        return False

    for c in sorted(alloc):
        for _ in range(alloc[c]):
            if not _produce(c):
                break
    return cond_plan, cond_stats


def _build_plan_leaf_proportional(
    pantry: Pantry, inventory: "LeafInventory", budgets: Budgets,
    concepts: Iterable[str], *, stats_out: Optional[dict] = None,
) -> tuple[PlannedVariant, ...]:
    """Option A: each concept gets a total budget ∝ leaves (floor/cap), split
    across conditions by ``type_mix``; any single-type shortfall is absorbed by
    that concept's own ``all_combined`` (no cross-concept leakage)."""
    concept_keys = tuple(sorted(set(concepts) & set(inventory.concepts())))
    applicable = {c: pantry.for_concept(c) for c in concept_keys}
    leaf_counts = {c: len(inventory.leaves(c)) for c in concept_keys}
    budget = _concept_budgets(leaf_counts, budgets.total, budgets.floor,
                              budgets.cap_per_leaf)

    split = {
        c: _split_by_type(
            budget.get(c, 0),
            [cond for cond in CONDITIONS if _eligible(cond, applicable[c])],
            budgets.type_mix)
        for c in concept_keys
    }

    plan: list[PlannedVariant] = []
    produced = {c: 0 for c in concept_keys}
    ordered = [c for c in CONDITIONS if c != _ALL_COMBINED]
    if _ALL_COMBINED in CONDITIONS:
        ordered.append(_ALL_COMBINED)  # last: absorbs each concept's shortfall

    for condition in ordered:
        if condition == _ALL_COMBINED:
            alloc = {c: budget.get(c, 0) - produced[c] for c in concept_keys
                     if _eligible(_ALL_COMBINED, applicable[c])
                     and budget.get(c, 0) - produced[c] > 0}
        else:
            alloc = {c: split[c].get(condition, 0) for c in concept_keys
                     if split[c].get(condition, 0) > 0}
        cond_plan, cond_stats = _produce_condition(
            condition, alloc, applicable, inventory, budgets)
        for p in cond_plan:
            produced[p.concept_key] += 1
        plan.extend(cond_plan)
        if stats_out is not None:
            stats_out[condition] = cond_stats
    return tuple(plan)


def build_plan(
    pantry: Pantry,
    inventory: LeafInventory,
    budgets: Budgets,
    concepts: Iterable[str],
    *,
    stats_out: Optional[dict] = None,
) -> tuple[PlannedVariant, ...]:
    """Produce the full deterministic sampling plan.

    Dispatches to the leaf-proportional builder (Option A) when
    ``budgets.mode == "leaf_proportional"``, else the legacy per-condition path.

    ``concepts`` restricts the plan to those concept keys (intersected with
    the inventory). Reuse counters are per condition — reset at each
    condition's start — so caps bound reuse within a condition; the caps
    themselves apply in every condition, ``all_combined`` included. A leaf
    is only paired with rewrites compatible with its original text (see
    :func:`_compatible`); incompatible leaves are skipped within the leaf
    order, and pairing-level skips are tallied per condition into
    ``stats_out`` (when given) for :func:`plan_report`.
    """
    if budgets.mode == "leaf_proportional":
        return _build_plan_leaf_proportional(
            pantry, inventory, budgets, concepts, stats_out=stats_out)

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
        cond_stats = {"incompatible_skips": 0}

        def _produce(concept_key: str) -> bool:
            """Try leaves in order until one yields a variant.

            A leaf incompatible with everything drawable is consumed and
            skipped (it cannot serve this condition); the concept goes
            dead only when no uncapped rewrite remains at all.
            """
            while concept_key not in dead and pos[concept_key] < len(orders[concept_key]):
                leaf = orders[concept_key][pos[concept_key]]
                rewrites, n_incompatible, capacity_left = _draw_rewrites(
                    condition, applicable[concept_key], budgets.reuse_cap,
                    usage, inventory.text(leaf), inventory.axis_values(leaf),
                )
                if rewrites:
                    # (all_combined: types skipped for THIS leaf still count)
                    cond_stats["incompatible_skips"] += n_incompatible
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
                if not capacity_left:
                    dead.add(concept_key)  # deficit — never refilled cross-type
                    return False
                cond_stats["incompatible_skips"] += max(n_incompatible, 1)
                pos[concept_key] += 1  # leaf can't serve this condition
            return False

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
        if stats_out is not None:
            stats_out[condition] = dict(cond_stats)

    return tuple(plan)


def plan_report(
    plan: tuple[PlannedVariant, ...],
    budgets: Budgets,
    stats: Optional[dict] = None,
) -> dict[str, dict]:
    """Per condition: achieved n, unique rewrites, max reuse, deficit.

    ``stats`` is the ``stats_out`` dict filled by :func:`build_plan`; it
    feeds each row's ``incompatible_skips`` diagnostic (0 when absent).
    The ``all_combined`` row additionally carries ``type_presence`` —
    ``{type: number of all_combined variants carrying a rewrite of it}``
    (at most one rewrite per type per variant, so this counts variants).
    """
    out: dict[str, dict] = {}
    for condition in CONDITIONS:
        variants = [p for p in plan if p.condition == condition]
        uses = Counter(r.uid for p in variants for r in p.rewrites)
        target = budgets.targets.get(condition, len(variants))
        out[condition] = {
            "n": len(variants),
            "target": target,
            "unique_rewrites": len(uses),
            "max_reuse": max(uses.values()) if uses else 0,
            "deficit": target - len(variants),
            "incompatible_skips": (
                (stats or {}).get(condition, {}).get("incompatible_skips", 0)
            ),
        }
        if condition == _ALL_COMBINED:
            presence = Counter(
                r.mtype.value for p in variants for r in p.rewrites
            )
            out[condition]["type_presence"] = dict(sorted(presence.items()))
    return out
