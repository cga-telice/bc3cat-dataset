"""Variant proposer for Stage-A LLM-assisted catalog mutation.

Sits between the prompt library (`synthetic.prompts.load_prompt`) and
the LLM round-trip (`synthetic.llm_proposer.propose`). Owns:

  * JSON-aware prompt rendering — escapes literal JSON braces in the
    template so `str.format_map` only substitutes the per-type
    declared placeholder set;
  * per-`ModificationType` schema validation of the LLM payload;
  * a `Modification(status="skipped", reason="schema_validation_failed: ...")`
    skip record on validation failure (distinct from C2's
    `malformed_llm_response_after_retry: ...` prefix).

Does NOT own:

  * slot extraction (per-concept context -> slots dict) — caller's
    responsibility; the Sprint 15 slot-extraction shim is the
    intended provider;
  * payload -> Phase-B rule mapping (the `layer_*.py` mutators
    consume `{"type": ..., "param": ..., ...}` dicts; that lift is
    Sprint 15's territory);
  * variant catalog persistence (Sprint 15+ — C4);
  * a concrete LLM transport (still A3 — `LLMClient` Protocol).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Optional

from .llm_proposer import LLMClient, propose
from .slot_extractor import _UNIT_TOKENS
from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER


EXPECTED_SLOTS: dict[ModificationType, frozenset[str]] = {
    ModificationType.SYNONYM_LABEL:    frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.NUM_TO_TEXT:      frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.UNIT_CONVERSION:  frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.UNIT_EXPANSION:   frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.ABBREV_EXPANSION: frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.CODE_EXPANSION:   frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.PARAPHRASE:       frozenset({"concept", "var_key", "fragment", "condition", "sibling_fragments"}),
    ModificationType.EXPANSION:        frozenset({"concept", "var_key", "fragment", "condition", "sibling_fragments"}),
    ModificationType.COMPRESSION:      frozenset({"concept", "var_key", "fragment", "condition", "sibling_fragments"}),
    ModificationType.OMISSION:         frozenset({"concept", "template", "var_to_omit", "axis_label"}),
    ModificationType.REORDER:          frozenset({"concept", "template", "constituents"}),
    ModificationType.TEMPLATE_PARAPHRASE: frozenset({"concept", "field", "template", "placeholders"}),
    ModificationType.NEW_PARAM:        frozenset({"concept", "existing_axes_with_labels", "allowlist"}),
}


@dataclass(frozen=True)
class VariantProposal:
    """Outcome of one `propose_variant()` call.

    Three terminal shapes:

      success:
        payload       = validated LLM payload (dict matching the per-type schema)
        raw_responses = whatever C2 captured (1 or 2 entries)
        skipped       = None

      C2 fallback (LLM round-trip itself failed):
        payload       = None
        raw_responses = the captured malformed responses
        skipped       = Modification(..., reason="malformed_llm_response_after_retry: ...")

      C3 validation failure (LLM produced valid JSON but wrong shape):
        payload       = None
        raw_responses = the captured (valid-JSON-but-wrong-shape) responses
        skipped       = Modification(..., reason="schema_validation_failed: ...")
    """

    payload: Optional[dict]
    raw_responses: tuple[str, ...]
    skipped: Optional[Modification]


def propose_variant(
    prompt_template: str,
    slots: dict[str, Any],
    client: LLMClient,
    modification_type: ModificationType,
    *,
    retry_once: bool = True,
) -> VariantProposal:
    """Render `prompt_template` with `slots`, ship it through
    `llm_proposer.propose`, and validate the parsed payload against
    the per-`modification_type` schema.

    Never raises on LLM failure modes (C2 fallback propagates) or
    schema-shape failures (C3 emits its own skip). DOES raise on
    catalog-authoring errors:

      KeyError   — slots is missing a declared placeholder
      ValueError — slots has an undeclared key

    These are catalog-build-time programming errors, not run-time LLM
    failure modes; letting them propagate is the right forcing
    function for the caller to fix the slot dict / prompt file.
    """
    rendered = _render_prompt(prompt_template, slots, modification_type)
    result = propose(rendered, client, modification_type, retry_once=retry_once)
    if result.fallback is not None:
        return VariantProposal(
            payload=None,
            raw_responses=result.raw_responses,
            skipped=result.fallback,
        )
    try:
        validated = _validate_payload(result.payload, modification_type)
    except ValueError as err:
        skip = Modification(
            type=modification_type,
            layer=TYPE_TO_LAYER[modification_type],
            status="skipped",
            reason=f"schema_validation_failed: {err}",
        )
        return VariantProposal(
            payload=None,
            raw_responses=result.raw_responses,
            skipped=skip,
        )
    return VariantProposal(
        payload=validated,
        raw_responses=result.raw_responses,
        skipped=None,
    )


# ----- helpers ----------------------------------------------------------

def _render_prompt(
    template: str,
    slots: dict[str, Any],
    modification_type: ModificationType,
) -> str:
    """Render `template` by escaping literal JSON braces, then
    selectively un-escaping the per-type declared placeholders, then
    calling `str.format_map(slots)`. Validates the slots dict matches
    `EXPECTED_SLOTS[modification_type]` exactly.

    Missing slots -> KeyError (sorted names in the message for
    deterministic output across PYTHONHASHSEED values).
    Extra slots -> ValueError (same sorted convention).
    """
    expected = EXPECTED_SLOTS[modification_type]
    have = set(slots.keys())
    missing = expected - have
    extra = have - expected
    if missing:
        raise KeyError(
            f"missing slots for {modification_type.value!r}: "
            f"{sorted(missing)} (expected {sorted(expected)})"
        )
    if extra:
        raise ValueError(
            f"unexpected slots for {modification_type.value!r}: "
            f"{sorted(extra)} (allowed {sorted(expected)})"
        )
    escaped = template.replace("{", "{{").replace("}", "}}")
    for key in expected:
        escaped = escaped.replace("{{" + key + "}}", "{" + key + "}")
    return escaped.format_map(slots)


def _validate_payload(
    payload: Optional[dict],
    modification_type: ModificationType,
) -> dict:
    """Per-type structural validator. Returns `payload` unchanged on
    success; raises `ValueError("<detail>")` on shape mismatch."""
    if payload is None:
        raise ValueError("payload_is_none")
    if not isinstance(payload, dict):
        raise ValueError(f"payload_not_dict: type={type(payload).__name__}")
    if modification_type in _LIST_PAIR_TYPES:
        list_key = _LIST_KEY[modification_type]
        _validate_pair_list(payload, list_key)
    elif modification_type in _ORIGINAL_NEW_PRESERVES_TYPES:
        _validate_original_new_preserves(payload)
        if modification_type is ModificationType.REORDER:
            # reorder rewrites a template: every `$VAR` / `$VAR(%AXIS)`
            # placeholder must survive (a small LLM corrupts them — e.g.
            # `$L(%B)` -> `$/($B)` — and the string-only checks miss it).
            _require_placeholders_preserved(payload["original"], payload["new"])
            _require_quantities_conserved(payload["original"], payload["new"])
        elif modification_type in _L2_CONTENT_TYPES:
            # L2 fragments are placeholder-free by construction. F1-review
            # found paraphrase/expansion/compression payloads whose `new`
            # re-embedded template placeholders like `($L(%B)/$M(%C)/$N(%D))`,
            # which then leaked verbatim into the rendered surfaces. Reject.
            _require_no_placeholders_in_new_fragment(payload["new"])
    elif modification_type is ModificationType.OMISSION:
        _validate_omission(payload)
        _require_placeholders_omitted(payload)
    elif modification_type is ModificationType.TEMPLATE_PARAPHRASE:
        # Same shape as REORDER (original/new/preserves_meaning), same
        # placeholder-preservation invariant: the full-surface paraphrase
        # keeps every $VAR / $VAR(%AXIS) token intact.
        _validate_original_new_preserves(payload)
        _require_placeholders_preserved(payload["original"], payload["new"])
        _require_quantities_conserved(payload["original"], payload["new"])
    elif modification_type is ModificationType.NEW_PARAM:
        _validate_new_param(payload)
    else:  # defensive: every enum member must be covered
        raise ValueError(
            f"no_schema_for_type: {modification_type.value!r}"
        )
    return payload


_LIST_PAIR_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})
_LIST_KEY: dict[ModificationType, str] = {
    ModificationType.SYNONYM_LABEL:    "synonyms",
    ModificationType.NUM_TO_TEXT:      "numerals",
    ModificationType.UNIT_CONVERSION:  "synonyms",
    ModificationType.UNIT_EXPANSION:   "synonyms",
    ModificationType.ABBREV_EXPANSION: "synonyms",
    ModificationType.CODE_EXPANSION:   "synonyms",
}
_ORIGINAL_NEW_PRESERVES_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
    ModificationType.REORDER,
})
# L2 content types: the `new` fragment goes back into a text_variable,
# which is a placeholder-free string by construction. Any $VAR / $VAR(%X)
# token in the fragment leaks into the rendered surface at stage-5.
_L2_CONTENT_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})


def _validate_pair_list(payload: dict, list_key: str) -> None:
    if list_key not in payload:
        raise ValueError(f"missing_key: {list_key!r}")
    items = payload[list_key]
    if not isinstance(items, list):
        raise ValueError(f"{list_key}_not_list: type={type(items).__name__}")
    if not items:
        raise ValueError(f"{list_key}_is_empty")
    for i, entry in enumerate(items):
        if not isinstance(entry, dict):
            raise ValueError(f"{list_key}[{i}]_not_dict")
        for k in ("original", "new"):
            if k not in entry:
                raise ValueError(f"{list_key}[{i}]_missing_key: {k!r}")
            if not isinstance(entry[k], str):
                raise ValueError(
                    f"{list_key}[{i}].{k}_not_str: type="
                    f"{type(entry[k]).__name__}"
                )


def _validate_original_new_preserves(payload: dict) -> None:
    for k in ("original", "new"):
        if k not in payload:
            raise ValueError(f"missing_key: {k!r}")
        if not isinstance(payload[k], str):
            raise ValueError(
                f"{k}_not_str: type={type(payload[k]).__name__}"
            )
    if "preserves_meaning" not in payload:
        raise ValueError("missing_key: 'preserves_meaning'")
    # `bool` is a subclass of `int`, so check `bool` directly (not via
    # `isinstance(x, int)`) to reject `0` / `1` int payloads.
    if not isinstance(payload["preserves_meaning"], bool):
        raise ValueError(
            f"preserves_meaning_not_bool: type="
            f"{type(payload['preserves_meaning']).__name__}"
        )


def _validate_omission(payload: dict) -> None:
    for k in ("original", "new", "omitted_var"):
        if k not in payload:
            raise ValueError(f"missing_key: {k!r}")
        if not isinstance(payload[k], str):
            raise ValueError(
                f"{k}_not_str: type={type(payload[k]).__name__}"
            )


# A template placeholder: `$A` or `$L(%B)`. The set of these must survive a
# template-rewriting modification (reorder keeps all; omission drops only the
# omitted variable's tokens) — otherwise the rerun renders broken templates and
# retrieval degrades. The string-only checks above do not catch corruption.
_PLACEHOLDER_RE = re.compile(r"\$[A-Za-z0-9]+(?:\(%[A-Z]\))?")
_PLACEHOLDER_VAR_RE = re.compile(r"\$([A-Za-z0-9]+)")


def _placeholders(text: str) -> set[str]:
    return set(_PLACEHOLDER_RE.findall(text))


def _placeholder_var(token: str) -> str:
    m = _PLACEHOLDER_VAR_RE.match(token)
    return m.group(1) if m else ""


def _require_placeholders_preserved(original: str, new: str) -> None:
    """Reorder: `new` must carry exactly `original`'s placeholder set."""
    o, n = _placeholders(original), _placeholders(new)
    if o != n:
        raise ValueError(
            f"placeholders_not_preserved: original={sorted(o)} new={sorted(n)}"
        )


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_ATTACHED_UNIT_RE = re.compile(r"\d(?:[.,]\d+)?\s*([a-záéíóúñü°²³%]+)\.?", re.IGNORECASE)


def _quantity_signature(text: str) -> tuple[Counter, Counter]:
    """Multisets of (numeric tokens, number-attached unit tokens) in `text`.

    Sprint 38.6 (per SPRINT_386_DESIGN.md D4.3: "attached unit/code
    tokens"). Numbers include those embedded in codes (`HM-20` → `20`,
    `4x40` → `4`,`40`). Unit tokens count only when they immediately
    follow a numeric token (optional whitespace, optional trailing
    dot) and appear in :data:`slot_extractor._UNIT_TOKENS` (`mm`, `m`,
    `%`, `horas`, …) — e.g. `"2 m"`, `"5 At."`, `"95%"`. Standalone
    letters/words elsewhere in the prose (a lone `"t"` or `"a"`, or a
    placeholder's variable letter) never count; that's what keeps this
    safe for prose that merely contains unit-like single letters.
    """
    numbers = Counter(_NUMBER_RE.findall(text))
    units = Counter(
        m.lower() for m in _ATTACHED_UNIT_RE.findall(text) if m.lower() in _UNIT_TOKENS
    )
    return numbers, units


def _require_quantities_conserved(original: str, new: str) -> None:
    """Full-surface rewrites must keep every quantity and unit token:
    a changed dimension (`760 mm` → `780 mm`), a dropped count, a
    duplicated diameter, or a re-spelled unit (`mm` → `milímetros`) all
    change catalog meaning. Unit re-spelling is `unit_expansion`'s job.
    Known leak (multiset design, false-negative direction only): a unit
    swap between numbers (`"2 tubos de 250 mm"` → `"250 tubos de 2 mm"`)
    passes, since both multisets still hold {2, 250} and {mm}; human
    review catches this rare case."""
    o_num, o_unit = _quantity_signature(original)
    n_num, n_unit = _quantity_signature(new)
    if o_num != n_num or o_unit != n_unit:
        raise ValueError(
            "quantities_not_conserved: "
            f"numbers {sorted(o_num.items())}→{sorted(n_num.items())}, "
            f"units {sorted(o_unit.items())}→{sorted(n_unit.items())}"
        )


def _require_placeholders_omitted(payload: dict) -> None:
    """Omission: `new` must carry `original`'s placeholders minus exactly the
    tokens that reference the omitted variable."""
    original, new, omitted = payload["original"], payload["new"], payload["omitted_var"]
    omitted_var = omitted.lstrip("$")
    o = _placeholders(original)
    dropped = {t for t in o if _placeholder_var(t) == omitted_var}
    expected = o - dropped
    got = _placeholders(new)
    if got != expected:
        raise ValueError(
            f"placeholders_not_preserved_after_omission: "
            f"expected={sorted(expected)} new={sorted(got)} (omitted {omitted_var!r})"
        )


def _require_no_placeholders_in_new_fragment(new: str) -> None:
    """L2 content guard: paraphrase/expansion/compression fragments must not
    embed `$VAR` / `$VAR(%AXIS)` template tokens. If they do, stage-5 renders
    them verbatim (F1-review digest #23, #31, #42)."""
    found = _placeholders(new)
    if found:
        raise ValueError(
            f"fragment_contains_template_placeholders: found={sorted(found)} "
            f"(L2 fragments must be placeholder-free)"
        )


def _validate_new_param(payload: dict) -> None:
    for k, expected_type in (
        ("new_axis_label", str),
        ("var_definition", str),
        ("template_patch", str),
    ):
        if k not in payload:
            raise ValueError(f"missing_key: {k!r}")
        if not isinstance(payload[k], expected_type):
            raise ValueError(
                f"{k}_not_{expected_type.__name__}: type="
                f"{type(payload[k]).__name__}"
            )
    if "values" not in payload:
        raise ValueError("missing_key: 'values'")
    values = payload["values"]
    if not isinstance(values, list):
        raise ValueError(f"values_not_list: type={type(values).__name__}")
    if not (2 <= len(values) <= 5):
        raise ValueError(f"values_out_of_range: len={len(values)} (expected 2..5)")
    for i, v in enumerate(values):
        if not isinstance(v, dict):
            raise ValueError(f"values[{i}]_not_dict")
        for k in ("label", "value"):
            if k not in v:
                raise ValueError(f"values[{i}]_missing_key: {k!r}")
            if not isinstance(v[k], str):
                raise ValueError(
                    f"values[{i}].{k}_not_str: type={type(v[k]).__name__}"
                )
