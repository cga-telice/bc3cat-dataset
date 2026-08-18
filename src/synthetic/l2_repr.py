"""L2 text-variable representation adapter (Sprint 26, Task B6).

The synthetic L2 layer (paraphrase / expansion / compression) addresses
text-variable phrases by a `"FRAGMENT" * (%AXIS=label)` **formula string** — that
is what `slot_extractor.enumerate_targets` parses (`_L2_FORMULA_RE`). But the real
catalog stores text-variables in **three** shapes, and `enumerate_targets`
silently skips two of them (`if not isinstance(formula, str): continue`):

  * **`LIST_plain`** — a positional value list `['"Diurno"', '"Nocturno"', …]`,
    referenced in the template *indexed* as `$L(%B)` (s05 indexes it positionally
    by the leaf's axis-value). Skipped by enumerate.
  * **`STR_formula`** — already a formula string `'"normal" * (%B=="a") + …'`,
    referenced *bare* as `$K` (s04 evaluates it per leaf). Enumerate handles it.
  * **`LIST_conditional`** — a list whose elements are themselves conditional
    fragments `['"…prose…" * (%B=="f")', …]`, referenced *bare* as `$P`. Skipped
    by enumerate, **but** `layer_l2._replace_fragment` mutates it natively.

This module makes all three enumerable for Stage A and restores each to the form
the s03→s07 rerun needs — **without editing the frozen seam** (`slot_extractor` /
`layer_l2` / `rule_emitter`). It imports `slot_extractor` / `taxonomy` + stdlib and
is never imported by any seam module.

The reference style decides the rerun form (empirically verified):

  | shape            | template ref     | rerun needs                         |
  |------------------|------------------|-------------------------------------|
  | `LIST_plain`     | indexed `$L(%B)` | positional **list**                 |
  | `STR_formula`    | bare `$K`        | **formula string** (s04 evaluates)  |
  | `LIST_conditional`| bare `$P`       | **list** of conditional fragments   |

Feeding the wrong form to the rerun corrupts output: a `LIST_plain` as a formula
mangles s05's positional index; a `STR_formula` as a list collapses every leaf to
the first value; and a `LIST_conditional` joined into one formula changes which
leaves render (baseline faithfulness is lost). BC3CAT-Syn must reproduce the
original byte-for-byte, so each shape is restored exactly.

The flow the F1 driver composes (no seam edits):

    enum  = list_to_formula(concept)                      # all L2 vars → strings
    entry = run_concept(enum, …)                          # enumerate/propose/emit rules
    appl  = list_to_formula(concept, include_conditional=False)  # only LIST_plain → formula
    mut, _ = stage_b.apply_variant_rules(appl, key, entry…rules) # LIST_conditional/STR mutate natively
    rerun = formula_to_list(mut)                          # indexed-ref strings → positional lists
    items = run_stages_3_to_7(rerun)

`list_to_formula(include_conditional=True)` is for *enumeration only* (its output
is read, never rerun). The mutation is applied to the `include_conditional=False`
concept so `LIST_conditional`/`STR_formula` vars keep their native shape and stay
byte-faithful; `formula_to_list` then restores only the indexed-referenced
`LIST_plain` vars. Condition format emitted for `LIST_plain` is `%AXIS=label`;
`LIST_conditional` conditions are joined **verbatim** (e.g. `%B=="f"`), so the
rules round-trip against the native list unchanged.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Optional

from .slot_extractor import enumerate_targets
from .taxonomy import ModificationType

__all__ = [
    "derive_var_axis_map",
    "list_to_formula",
    "formula_to_list",
    "assert_l2_targets_or_warn",
]

logger = logging.getLogger(__name__)

# `$VAR(%AXIS)` indexed reference in a template — e.g. `$L(%B)`.
_VAR_AXIS_RE = re.compile(r"\$([A-Za-z0-9]+)\(%([A-Z])\)")

# A `"FRAGMENT" * (CONDITION)` term — mirrors slot_extractor._L2_FORMULA_RE.
_FORMULA_TERM_RE = re.compile(r'"([^"]*)"\s*\*\s*\(([^)]+)\)')

# A conditional term anywhere in a string (the `layer_l2` list-acceptance test).
_HAS_CONDITIONAL = re.compile(r'"[^"]*"\s*\*\s*\(')

# A reconstructed `%AXIS=label` condition (what we emit for LIST_plain).
_CONDITION_RE = re.compile(r"^\s*%([A-Z])\s*=\s*(.+?)\s*$")

_TEMPLATE_FIELDS = ("resumen", "RESUMEN", "texto", "TEXTO")


# ---------------------------------------------------------------------------
# Reference-style derivation
# ---------------------------------------------------------------------------

def derive_var_axis_map(concept_item: dict) -> dict[str, str]:
    """Map each *indexed-referenced* text-variable (`$VAR(%AXIS)` in the
    `resumen`/`texto`) to its axis. A var referenced against more than one axis is
    ambiguous and excluded. Bare-referenced vars (`$K` with no `(%…)`) are not in
    the map. Operates on a single concept *entry*."""
    return {var: next(iter(axes)) for var, axes in _scan_var_axes(concept_item).items()
            if len(axes) == 1}


def _scan_var_axes(concept_item: dict) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for field in _TEMPLATE_FIELDS:
        text = concept_item.get(field)
        if not isinstance(text, str):
            continue
        for var, axis in _VAR_AXIS_RE.findall(text):
            found.setdefault(var, set()).add(axis)
    return found


# ---------------------------------------------------------------------------
# list -> formula (Stage A: makes every L2 var enumerable)
# ---------------------------------------------------------------------------

def list_to_formula(
    stage_json: dict, *, include_conditional: bool = True,
) -> tuple[dict, list[dict]]:
    """Rewrite text-variables into the formula-string form the L2 path enumerates.

    `include_conditional=True` (default, for **enumeration**): also folds
    `LIST_conditional` vars into a joined formula string so they enumerate.
    `include_conditional=False` (for **application**): leaves `LIST_conditional`
    (and `STR_formula`) in their native shape so `layer_l2` mutates them in place
    and they stay byte-faithful through the rerun; only `LIST_plain` indexed vars
    are converted.

    Pure: deep-copies. Returns `(converted, report)` — one dict per
    (concept_key, var) with a `reason`; nothing is dropped silently.
    """
    out = copy.deepcopy(stage_json)
    report: list[dict] = []
    for concept_key, item in out.items():
        if not isinstance(item, dict):
            continue
        tvs = item.get("text_variables")
        if not isinstance(tvs, dict):
            continue
        var_axes = _scan_var_axes(item)
        params = item.get("parameters", {}) or {}
        for var_key, entry in list(tvs.items()):
            reason, new_value = _convert_one(
                var_key, entry, var_axes, params, include_conditional,
            )
            if new_value is not None:
                tvs[var_key] = new_value
            report.append({"concept_key": concept_key, "var": var_key, "reason": reason})
    return out, report


def _convert_one(var_key, entry, var_axes, params, include_conditional):
    """Return `(reason, new_value_or_None)` for one text-variable."""
    if isinstance(entry, str):
        return "already_formula", None  # STR_formula (or other str) — leave it
    if not isinstance(entry, list):
        return "unsupported_shape", None

    # LIST_conditional: elements already carry `"frag" * (cond)`.
    if any(isinstance(el, str) and _HAS_CONDITIONAL.search(el) for el in entry):
        if not include_conditional:
            return "native_conditional", None  # mutate/rerun in native list form
        if any(isinstance(el, str) and _embedded_quote_in_terms(el) for el in entry):
            return "embedded_quote", None
        if not all(isinstance(el, str) for el in entry):
            return "unsupported_shape", None
        return "joined_conditional", " + ".join(entry)

    # LIST_plain: positional value list keyed on an indexed axis reference.
    axes = var_axes.get(var_key, set())
    if not axes:
        return "unreferenced", None
    if len(axes) > 1:
        return "multi_axis_conflict", None
    axis = next(iter(axes))
    values = params.get(axis, {}).get("values", []) or []
    if len(entry) != len(values):
        return "length_mismatch", None
    frags: list[str] = []
    for el in entry:
        if not isinstance(el, str):
            return "embedded_quote", None
        frag = _strip_one_quote_pair(el)
        if '"' in frag:
            return "embedded_quote", None
        frags.append(frag)
    terms = [f'"{frag}" * (%{axis}={values[i]["label"]})' for i, frag in enumerate(frags)]
    return "converted", " + ".join(terms)


# ---------------------------------------------------------------------------
# formula -> list (Stage B: restore the rerun-faithful shape)
# ---------------------------------------------------------------------------

def formula_to_list(stage_json: dict) -> dict:
    """Restore **indexed-referenced** `LIST_plain` vars (now formula strings) to
    positional value lists, so the s03→s07 rerun (which indexes them positionally)
    renders correctly.

    Bare-referenced vars (`STR_formula`, mutated as strings) and native lists
    (`LIST_conditional`, mutated in place) are left untouched — the rerun needs
    them exactly as they are. Self-contained (reference style read from the
    template); pure (deep-copies).
    """
    out = copy.deepcopy(stage_json)
    for item in out.values():
        if not isinstance(item, dict):
            continue
        tvs = item.get("text_variables")
        if not isinstance(tvs, dict):
            continue
        indexed = derive_var_axis_map(item)
        params = item.get("parameters", {}) or {}
        for var_key in list(tvs.keys()):
            if var_key not in indexed:
                continue  # bare-referenced or unreferenced — leave it
            entry = tvs[var_key]
            rebuilt = _formula_to_list_one(entry, params)
            if rebuilt is not None:
                tvs[var_key] = rebuilt
    return out


def _formula_to_list_one(entry, params) -> Optional[list]:
    """Positional list for an indexed var's formula string, or None to leave it."""
    if not isinstance(entry, str):
        return None
    terms = _FORMULA_TERM_RE.findall(entry)
    if not terms:
        return None
    label_to_frag: dict[str, str] = {}
    axis: Optional[str] = None
    for frag, cond in terms:
        m = _CONDITION_RE.match(cond)
        if m is None:
            return None
        cond_axis, label = m.group(1), m.group(2)
        if axis is None:
            axis = cond_axis
        elif axis != cond_axis:
            return None
        label_to_frag[label] = frag
    values = params.get(axis, {}).get("values", []) or []
    if not values:
        return None
    rebuilt: list[str] = []
    for v in values:
        label = v.get("label")
        if label not in label_to_frag:
            return None
        rebuilt.append(f'"{label_to_frag[label]}"')
    return rebuilt


# ---------------------------------------------------------------------------
# Silent-no-op guard
# ---------------------------------------------------------------------------

def assert_l2_targets_or_warn(
    stage_json: dict, *, log: Optional[logging.Logger] = None,
) -> int:
    """Guard against the silent L2 no-op recurring on a future shape drift.

    Converts `stage_json` for enumeration and, if any var was made enumerable,
    counts the L2 (paraphrase) targets that now enumerate. If convertible vars
    exist but the count is zero, emits a warning. Returns the target count."""
    log = log if log is not None else logger
    converted, report = list_to_formula(stage_json, include_conditional=True)
    made_enumerable = [r for r in report if r["reason"] in ("converted", "joined_conditional")]
    if not made_enumerable:
        return 0
    count = 0
    for concept_key, item in converted.items():
        if isinstance(item, dict):
            count += len(list(enumerate_targets(converted, concept_key,
                                                 ModificationType.PARAPHRASE)))
    if count == 0:
        log.warning(
            "L2 silent-no-op guard: %d text-variable(s) were made enumerable but "
            "zero L2 targets enumerated — the L2 path may have drifted out of "
            "shape (vars: %s)",
            len(made_enumerable),
            [(r["concept_key"], r["var"]) for r in made_enumerable],
        )
    return count


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _embedded_quote_in_terms(element: str) -> bool:
    """True if any `"frag" * (cond)` term in `element` has an embedded quote in
    its fragment (which would break the `"([^"]*)"` round-trip for enumeration)."""
    stripped = _FORMULA_TERM_RE.sub("", element)
    # If removing well-formed terms still leaves a stray quote, a fragment had an
    # embedded one (or the element is malformed) — don't risk a partial parse.
    return '"' in stripped


def _strip_one_quote_pair(s: str) -> str:
    """Strip exactly one surrounding `"` pair: `'"Diurno"'` -> `'Diurno'`."""
    if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s
