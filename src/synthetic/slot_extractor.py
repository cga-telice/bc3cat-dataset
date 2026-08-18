"""Slot extractor: stage-JSON walk -> per-type slots dict for
`variant_proposer.propose_variant`.

Owns the per-concept context derivation that Sprint 14 deliberately
left to the caller. Three public functions:

  * `enumerate_targets(stage_json, concept_key, mtype)` — yields one
    `target_id` per viable application site within the concept;
    per-type semantics (axis key / (var, condition) / (field, var) /
    field / None);
  * `extract_slots(stage_json, concept_key, mtype, target_id)` —
    builds the per-type slots dict matching
    `variant_proposer.EXPECTED_SLOTS[mtype]`;
  * `concept_resumen(stage_json, concept_key)` — small helper for
    the `{concept}` slot.

Does NOT own:

  * `text_variables` formula parsing beyond the L2 partition helper
    (`_parse_l2_formula`) — FIEBDC operator grammar lives in
    `src/utils/z_formula_processing.py`;
  * `new_param_allowlist.yaml` loading — slot stays "[]" until a
    later sprint authors the YAML;
  * per-concept condition labelling (e.g., "single_L1_synonym_label",
    "stacked_2") — that's the orchestrator's job.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

from .taxonomy import ModificationType


_L1_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})
_L2_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})


# ---- Sprint 31: per-axis applicability gate for L1 types ---------------
#
# F1-review found that enumerating every L1 type against every axis on
# `OEB070$` produced ungrammatical duplications (unit_expansion on the
# numeric count axis A: "de Un tubo tubo(s)") and legitimate no-op skips
# (abbrev/code_expansion on time-band axes with nothing to expand).
# `_axis_applies` gates axis enumeration by content-driven applicability:
#
#   * SYNONYM_LABEL     — needs any textual value (letters present).
#   * NUM_TO_TEXT       — needs any purely-numeric value.
#   * UNIT_CONVERSION   — needs any value carrying a unit token.
#   * UNIT_EXPANSION    — same as UNIT_CONVERSION.
#   * ABBREV_EXPANSION  — needs any value with an uppercase 2–6-letter
#                         abbreviation (PVC, HE-20, IPN, …).
#   * CODE_EXPANSION    — same as ABBREV_EXPANSION.
#
# Heuristics err on the side of being permissive — a value need only match
# the predicate once for the axis to be considered applicable.

_NUMERIC_RE = re.compile(r"^\s*-?\d+(?:[.,]\d+)?\s*$")
_HAS_LETTER_RE = re.compile(r"[A-Za-zÁÉÍÓÚÑáéíóúñÜü]")
_WORD_RE = re.compile(r"[A-Za-zÁÉÍÓÚÑáéíóúñÜü°²³]+\.?|%")
_ABBREV_RE = re.compile(r"\b[A-Z]{2,6}(?:-\d+[A-Z]?)?\b")

_UNIT_TOKENS: frozenset[str] = frozenset({
    # length
    "mm", "cm", "m", "km", "μm", "um", "mm²", "cm²", "m²", "km²",
    "mm³", "cm³", "m³",
    # mass
    "g", "kg", "t", "mg", "tn",
    # volume
    "l", "ml", "cl",
    # time
    "s", "seg", "min", "h", "hr", "hora", "horas", "día", "dia", "días", "dias",
    "semana", "semanas", "mes", "meses", "año", "ano", "años", "anos",
    # pressure
    "at", "at.", "atm", "bar", "pa", "kpa", "mpa",
    # temperature
    "°c", "°f", "k",
    # power
    "w", "kw", "mw", "hp", "cv",
    # electricity
    "v", "kv", "a", "ka", "kva", "hz",
    # misc
    "%",
})


def _values(block: dict) -> list[str]:
    return [
        v.get("value", "")
        for v in block.get("values", [])
        if isinstance(v, dict)
    ]


def _is_numeric(value: str) -> bool:
    return bool(_NUMERIC_RE.match(value))


def _has_letters(value: str) -> bool:
    return bool(_HAS_LETTER_RE.search(value))


def _has_unit(value: str) -> bool:
    lower = value.lower()
    for tok in _WORD_RE.findall(lower):
        norm = tok.rstrip(".")
        if norm in _UNIT_TOKENS:
            return True
    return False


def _has_abbrev(value: str) -> bool:
    return bool(_ABBREV_RE.search(value))


def _axis_applies(block: dict, mtype: ModificationType) -> bool:
    """Return True if `block`'s values make `mtype` a semantically sensible
    modification. Sprint 31 gate — see module docstring above."""
    values = _values(block)
    if not values:
        return False
    if mtype is ModificationType.SYNONYM_LABEL:
        return any(_has_letters(v) for v in values)
    if mtype is ModificationType.NUM_TO_TEXT:
        return any(_is_numeric(v) for v in values)
    if mtype in (ModificationType.UNIT_CONVERSION, ModificationType.UNIT_EXPANSION):
        return any(_has_unit(v) for v in values)
    if mtype in (ModificationType.ABBREV_EXPANSION, ModificationType.CODE_EXPANSION):
        return any(_has_abbrev(v) for v in values)
    return True


def concept_resumen(stage_json: dict, concept_key: str) -> str:
    item = stage_json[concept_key]
    if "resumen" in item:
        return item["resumen"]
    if "RESUMEN" in item:
        return item["RESUMEN"]
    raise KeyError(
        f"concept_key {concept_key!r} has neither 'resumen' nor 'RESUMEN' field"
    )


def enumerate_targets(
    stage_json: dict, concept_key: str, modification_type: ModificationType,
) -> Iterator[Any]:
    item = stage_json[concept_key]
    if modification_type in _L1_TYPES:
        params = item.get("parameters", {}) or {}
        for axis_key in sorted(params.keys()):
            if _axis_applies(params[axis_key], modification_type):
                yield axis_key
    elif modification_type in _L2_TYPES:
        for var_key, formula in sorted(item.get("text_variables", {}).items()):
            if not isinstance(formula, str):
                continue
            try:
                pairs = _parse_l2_formula(formula)
            except ValueError:
                continue
            for condition, _fragment in pairs:
                yield (var_key, condition)
    elif modification_type is ModificationType.OMISSION:
        for field in ("RESUMEN", "TEXTO"):
            text = _field_text(item, field)
            for var_token in sorted(set(re.findall(r"\$[A-Z]", text))):
                yield (field, var_token)
    elif modification_type is ModificationType.REORDER:
        for field in ("RESUMEN", "TEXTO"):
            if _field_text(item, field):
                yield field
    elif modification_type is ModificationType.TEMPLATE_PARAPHRASE:
        # Same targeting as reorder — one target per non-empty template field.
        for field in ("RESUMEN", "TEXTO"):
            if _field_text(item, field):
                yield field
    elif modification_type is ModificationType.NEW_PARAM:
        yield None
    else:  # defensive: every enum member must be covered
        raise ValueError(f"no_enumerator_for_type: {modification_type.value!r}")


def extract_slots(
    stage_json: dict,
    concept_key: str,
    modification_type: ModificationType,
    target_id: Any,
) -> dict[str, Any]:
    item = stage_json[concept_key]
    concept = concept_resumen(stage_json, concept_key)
    if modification_type in _L1_TYPES:
        param = target_id
        block = item["parameters"][param]
        return {
            "concept": concept,
            "axis_label": block["label"],
            "value_list": "; ".join(
                f"{v['label']}: {v['value']}" for v in block["values"]
            ),
        }
    if modification_type in _L2_TYPES:
        var_key, condition = target_id
        formula = item["text_variables"][var_key]
        pairs = _parse_l2_formula(formula)
        fragment_lookup = dict(pairs)
        if condition not in fragment_lookup:
            raise KeyError(
                f"condition {condition!r} not found in formula for var "
                f"{var_key!r} on concept {concept_key!r}"
            )
        # Sprint 34: the prompt now gets the other clauses of the same
        # text-variable so it can avoid collapsing this fragment onto a
        # sibling's text. Formatted like the L1 `value_list`, in formula
        # order, excluding the target.
        siblings = "; ".join(
            f"{cond}: {frag}" for cond, frag in pairs if cond != condition
        )
        return {
            "concept": concept,
            "var_key": var_key,
            "fragment": fragment_lookup[condition],
            "condition": condition,
            "sibling_fragments": siblings or "(ninguno)",
        }
    if modification_type is ModificationType.OMISSION:
        field, var_token = target_id
        template = _field_text(item, field)
        var_to_omit = var_token.lstrip("$")
        axis_label = _var_axis_label(item, var_to_omit)
        return {
            "concept": concept,
            "template": template,
            "var_to_omit": var_to_omit,
            "axis_label": axis_label,
        }
    if modification_type is ModificationType.REORDER:
        field = target_id
        template = _field_text(item, field)
        constituents = "; ".join(sorted(set(re.findall(r"\$[A-Z]", template))))
        return {
            "concept": concept,
            "template": template,
            "constituents": constituents,
        }
    if modification_type is ModificationType.TEMPLATE_PARAPHRASE:
        # Sprint 36. Emit the field name, the template, and the exhaustive
        # set of placeholders (including axis-indexed forms like `$L(%B)`)
        # so the prompt can enforce preservation explicitly.
        field = target_id
        template = _field_text(item, field)
        placeholder_tokens = sorted(set(
            re.findall(r"\$[A-Za-z0-9]+(?:\(%[A-Z]\))?", template)
        ))
        placeholders = ", ".join(placeholder_tokens) if placeholder_tokens else "(ninguna)"
        return {
            "concept": concept,
            "field": field,
            "template": template,
            "placeholders": placeholders,
        }
    if modification_type is ModificationType.NEW_PARAM:
        params = item.get("parameters", {})
        axes_str = "; ".join(
            f"{key}: {block['label']}" for key, block in sorted(params.items())
        )
        return {
            "concept": concept,
            "existing_axes_with_labels": axes_str,
            "allowlist": "[]",
        }
    raise ValueError(f"no_extractor_for_type: {modification_type.value!r}")


# ----- helpers ----------------------------------------------------------

_L2_FORMULA_RE = re.compile(r'"([^"]*)"\s*\*\s*\(([^)]+)\)')


def _parse_l2_formula(formula: str) -> list[tuple[str, str]]:
    """Partition `'"a" * (%B=a) + "b" * (%B=b)'` into
    `[("%B=a", "a"), ("%B=b", "b")]`.

    Returns a list (not an iterator) so callers can index it. Raises
    `ValueError` only if the formula has zero matches — that's a
    catalog-authoring error, not a runtime data shape.
    """
    pairs = [
        (cond.strip(), frag) for frag, cond in _L2_FORMULA_RE.findall(formula)
    ]
    if not pairs:
        raise ValueError(f"l2_formula_unparseable: {formula!r}")
    return pairs


def _field_text(item: dict, field: str) -> str:
    if field in item:
        return item[field]
    if field.lower() in item:
        return item[field.lower()]
    return ""


def _var_axis_label(item: dict, var_to_omit: str) -> str:
    """Best-effort lookup of the parameter label whose values bind
    the named variable. Walks the text_variables formula, extracts
    the first `%<axis>=...` condition, and returns the matching
    parameter label. Returns `""` if no derivation is possible —
    the omission prompt's `axis_label` slot is informational, not
    load-bearing.
    """
    formula = item.get("text_variables", {}).get(var_to_omit, "")
    if not isinstance(formula, str):
        return ""
    match = re.search(r"%([A-Z])\s*=", formula)
    if match is None:
        return ""
    axis = match.group(1)
    return item.get("parameters", {}).get(axis, {}).get("label", "")
