"""Axis ↔ text-variable twin discovery (Sprint 31).

Some BC3 concepts render a parameter axis through *two* independent
variables at the same time: the raw parameter value (`$B` in the `texto`)
and an indexed text-variable (`$L(%B)` in the `resumen`). The text-variable's
fragments carry a duplicated copy of the parameter labels. In the original
catalog the two copies coincide; any single-layer L1 or L2 modification
breaks the coincidence and desynchronises the query (`resumen`) from the
document (`texto`).

The mutator refactor pairs L1 + L2 edits automatically so both surfaces
move together. To do that, it needs a per-concept map of which
text-variable is the twin of which parameter axis. This module is that
map.

Delegates axis discovery to `l2_repr.derive_var_axis_map` — the same
regex-based scan of `resumen`/`texto` for indexed references (`$VAR(%AXIS)`).
Ambiguous cases (two indexed vars on the same axis) yield no twin from the
axis side; the caller falls back to single-layer mutation.
"""

from __future__ import annotations

import re
from typing import Optional

from .l2_repr import derive_var_axis_map


__all__ = [
    "axis_twin_map",
    "var_twin_map",
    "axis_twin",
    "var_twin",
    "pair_l1_into_text_var",
    "pair_l2_into_param",
    "axis_value_collides",
    "fragment_collides",
]


# `"FRAGMENT" * (CONDITION)` term — mirrors layer_l2._FRAGMENT_PAT.
_FRAGMENT_PAT = re.compile(r'"(?P<frag>[^"]*)"\s*\*\s*\(\s*(?P<cond>[^)]*)\s*\)')
# `%B=a`, `%B="a"`, `%B == a`, etc. — extract axis letter and value label.
_CONDITION_PAT = re.compile(r"%([A-Z])\s*=+\s*\"?(?P<label>[A-Za-z0-9]+)\"?")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def var_twin_map(concept_item: dict) -> dict[str, str]:
    """Return {text_var_key: axis_key} for every indexed-referenced text-var.

    A text-var referenced only via `$K` (bare) is not a twin candidate.
    A text-var indexed against multiple axes is ambiguous and excluded
    upstream by `derive_var_axis_map`.
    """
    return derive_var_axis_map(concept_item)


def axis_twin_map(concept_item: dict) -> dict[str, str]:
    """Return {axis_key: text_var_key} — the inverse of `var_twin_map`.

    Axes that no indexed text-var covers are absent. Axes with two or more
    indexed vars pointing at them are ambiguous and also absent, so the
    caller can fall back to single-layer mutation without risk of picking
    the wrong twin.
    """
    counts: dict[str, list[str]] = {}
    for var, axis in var_twin_map(concept_item).items():
        counts.setdefault(axis, []).append(var)
    return {axis: vars_[0] for axis, vars_ in counts.items() if len(vars_) == 1}


def axis_twin(concept_item: dict, axis_key: str) -> Optional[str]:
    """Return the twin text-var for `axis_key`, or `None` if none / ambiguous."""
    return axis_twin_map(concept_item).get(axis_key)


def var_twin(concept_item: dict, var_key: str) -> Optional[str]:
    """Return the twin axis for `var_key`, or `None` if the var is not
    indexed-referenced in any template field."""
    return var_twin_map(concept_item).get(var_key)


# ---- paired-edit primitives -------------------------------------------

def _find_fragment_hit(formula: str, axis_key: str, value_label: str
                       ) -> Optional[re.Match]:
    """Locate the `"…" * (%<axis>=<label>)` term in a formula string.

    Tolerates the same condition-format variations `layer_l2._replace_fragment`
    tolerates (e.g. `%B=a`, `%B="a"`, `%B == "a"`). Returns the first match
    or `None` if the condition isn't present.
    """
    for m in _FRAGMENT_PAT.finditer(formula):
        cond_m = _CONDITION_PAT.search(m.group("cond"))
        if cond_m and cond_m.group(1) == axis_key and cond_m.group("label") == value_label:
            return m
    return None


def pair_l1_into_text_var(
    concept_item: dict,
    *,
    param: str,
    value_label: str,
    original: str,
    new: str,
) -> Optional[dict]:
    """Carry an L1 param-value rewrite into the twin text-variable's fragment.

    Only pairs when:
      1. `param` has a unique twin text-var (indexed as `$VAR(%param)` in a
         template).
      2. The twin text-var carries a fragment for `%{param}={value_label}` in
         formula form.
      3. That fragment's literal text (stripped) equals `original`.

    If all three hold, the fragment is rewritten in place to `new` and a
    metadata dict is returned. Otherwise returns `None` and the concept is
    left untouched.
    """
    twin_var = axis_twin(concept_item, param)
    if twin_var is None:
        return None
    text_vars = concept_item.get("text_variables") or {}
    formula = text_vars.get(twin_var)
    if not isinstance(formula, str):
        return None
    hit = _find_fragment_hit(formula, param, value_label)
    if hit is None:
        return None
    if _norm(hit.group("frag")) != _norm(original):
        return None
    replacement = f'"{new}" * ({hit.group("cond")})'
    new_formula = formula[: hit.start()] + replacement + formula[hit.end():]
    text_vars[twin_var] = new_formula
    return {
        "var": twin_var,
        "condition": f"%{param}={value_label}",
        "original": original,
        "new": new,
    }


def axis_value_collides(
    concept_item: dict,
    *,
    param: str,
    exclude_value_label: str,
    candidate: str,
) -> bool:
    """Return True if `candidate` (normalised) equals another value on the
    same parameter axis. Used by the L1 pre-flight collision guard to
    prevent two axis values from rendering identically."""
    params = concept_item.get("parameters") or {}
    axis = params.get(param) or {}
    target = _norm(candidate)
    for entry in axis.get("values", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("label") == exclude_value_label:
            continue
        if _norm(entry.get("value", "")) == target:
            return True
    return False


def fragment_collides(
    concept_item: dict,
    *,
    var: str,
    exclude_condition: str,
    candidate: str,
) -> bool:
    """Return True if `candidate` (normalised) equals another fragment on
    the same text-variable's formula. Used by the L2 pre-flight collision
    guard. `exclude_condition` matches by condition-text normalisation, so
    `%B=a` and ` %B = a ` are treated as the same slot."""
    text_vars = concept_item.get("text_variables") or {}
    formula = text_vars.get(var)
    if not isinstance(formula, str):
        return False
    target = _norm(candidate)
    exclude = _norm(exclude_condition)
    for m in _FRAGMENT_PAT.finditer(formula):
        if _norm(m.group("cond")) == exclude:
            continue
        if _norm(m.group("frag")) == target:
            return True
    return False


def pair_l2_into_param(
    concept_item: dict,
    *,
    var: str,
    condition: str,
    original: str,
    new: str,
) -> Optional[dict]:
    """Carry an L2 text-var-fragment rewrite into the twin parameter's value.

    Only pairs when:
      1. `var` has a twin axis (i.e. it is indexed-referenced in a template).
      2. `condition` names that axis with a resolvable value label (`%B=a`,
         `%B="a"`, `%B == "a"` — all accepted).
      3. The param's value entry for that label carries a `value` string that
         (stripped) equals `original`.

    If all three hold, the value is rewritten in place to `new` and a
    metadata dict is returned. Otherwise returns `None` and the concept is
    left untouched.
    """
    twin_axis = var_twin(concept_item, var)
    if twin_axis is None:
        return None
    cond_m = _CONDITION_PAT.search(condition)
    if cond_m is None or cond_m.group(1) != twin_axis:
        return None
    value_label = cond_m.group("label")
    params = concept_item.get("parameters") or {}
    axis_block = params.get(twin_axis) or {}
    for entry in axis_block.get("values", []):
        if not isinstance(entry, dict):
            continue
        if entry.get("label") == value_label:
            if _norm(entry.get("value", "")) != _norm(original):
                return None
            entry["value"] = new
            return {
                "param": twin_axis,
                "value_label": value_label,
                "original": original,
                "new": new,
            }
    return None
