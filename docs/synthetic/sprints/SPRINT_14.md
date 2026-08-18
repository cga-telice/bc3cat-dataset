# Sprint 14 — Phase C Task C3: variant proposer (`variant_proposer.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 14                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | C3 — see [`../RESEARCH_PROTOCOL.md §5 Phase C`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 13 — `llm_proposer.py` (`LLMClient` Protocol + `propose` + retry/fallback) (see [`SPRINT_13.md`](SPRINT_13.md)) |
| **Successor**   | Sprint 15 — Phase C Task C4 (variant catalog writer — JSON-per-concept artefacts under `data/synthetic/variants/`); plus a slot-extraction shim that builds per-`ModificationType` slots dicts from stage-2/3/4 JSON (TBD) |

---

## Context

Sprint 13 froze the LLM round-trip: `propose(prompt, client, modification_type)`
takes an *already-rendered* prompt, parses the response as a JSON object,
retries once on malformed output, and emits a
`Modification(status="skipped", reason="malformed_llm_response_after_retry: …")`
fallback on double failure. **What it cannot do**: render a prompt
template (the 12 `.txt` files Sprint 12 froze contain Python-style
`{slot}` placeholders **plus** literal `{` `}` inside the
`Responde SOLO con un JSON: {...}` contract block); check that the LLM's
parsed dict matches the per-`ModificationType` schema (does a
`synonym_label` response actually carry
`{"synonyms": [{"original", "new"}, …]}`? does a `paraphrase` response
carry `{"original", "new", "preserves_meaning"}`?). Sprint 13's
`_parse_json_object` only verifies JSON-validity + dict-root; the
per-type schema is C3's responsibility, as spelled out by the protocol's
[§5 Phase C C3](../RESEARCH_PROTOCOL.md):

> **C3. Variant proposer.** `src/synthetic/variant_proposer.py` — calls
> the LLM, validates output shape against the `Modification` schema,
> returns a candidate.

Three design tensions to resolve up front:

1. **Brace-classification inside the prompt templates.** The 12 prompts
   intermix Python placeholders (`{concept}`, `{axis_label}`, …) with
   literal JSON braces (`{ "synonyms": [...] }`). Python's stdlib
   `str.format_map` treats every `{` as a placeholder opener — a
   straight `.format_map(slots)` call against any of the prompts
   raises `KeyError` (on JSON-literal-keys) or `IndexError` (on the
   `[...]` arrays). Sprint 14 resolves this by **escaping every brace
   pair first, then selectively un-escaping the per-type declared
   placeholder set**. The declared set is sourced from Sprint 12's
   placeholder audit (`tests/synthetic/test_prompts.py`'s
   `_EXPECTED_PLACEHOLDERS`); we re-encode it as a module-level
   constant in `variant_proposer.py` to keep the two contracts
   in lockstep without a test-file dependency.
2. **C3 vs. C4 boundary — what is a "candidate"?** The protocol says
   "returns a candidate". A *candidate* could mean:
   - **(a)** the validated LLM payload — the parsed dict that survived
     C2's JSON check and C3's per-type schema check;
   - **(b)** one or more Phase-B *rule dicts* — the JSON shape the
     `layer_*.py` mutators consume (e.g.,
     `{"type": "synonym_label", "param": "B", "value": "a", "original": "Normal", "new": "Estándar"}`).

   Option (b) requires *cross-referencing* the LLM payload with the
   per-concept stage-JSON context: a `synonym_label` LLM payload like
   `{"synonyms": [{"original": "Normal", "new": "Estándar"}]}` needs
   the axis key (`"B"`) and the value-label (`"a"`) which only the
   stage-2 `concept["parameters"]["B"]["values"]` block carries.
   That's *stage-JSON-aware* logic and pulls a lot of per-type rule
   shape into Sprint 14. **Sprint 14 ships option (a) only:** the
   validated payload, not the rule. The payload → rule mapping is
   deferred to a follow-up sprint (Sprint 15 — slot-extraction +
   rule-emission, alongside the C4 variant-catalog writer). Reason:
   payload validation is a small, schema-pure concern (≈12 schemas,
   each a few dict-shape checks); rule emission needs to know axis
   keys, value labels, var keys, condition strings, template fields
   — which is the same context the *slot-extraction* sprint will
   build. Bundling slot-extraction + rule-emission into one sprint
   (and out of Sprint 14) keeps the boundaries clean and the test
   surface small.
3. **Slot population — where does `slots: dict[str, Any]` come from?**
   Sprint 12 froze the prompts and their placeholder signatures
   (L1 prompts have `{concept, axis_label, value_list}`; L2 prompts
   have `{concept, var_key, fragment, condition}`; L3 and PD diverge
   per type). The slot values themselves come from per-concept stage
   JSON: `{concept}` from a concept-name lookup, `{axis_label}` from
   `concept["parameters"][param]["label"]`, `{value_list}` from a
   join over the `values` block, etc. **Sprint 14 does not extract
   slots from stage JSON.** Symmetrically with C2's "take an
   already-rendered prompt" contract, C3 takes an *already-built
   slots dict* — caller is responsible for populating it. The
   slot-extraction shim is deferred (Sprint 15 territory). Tests
   pass deterministic slots dicts inline; no stage-JSON fixtures
   needed in this sprint's test file.

Sprint 13's verification baseline: **362 passed + 1 skipped.** Sprint 14
adds the new `src/synthetic/variant_proposer.py` module + its contract
test suite (`tests/synthetic/test_variant_proposer.py`). Net pytest
delta target: **≥+30 new cases** = **≥392 passed** total. Zero
failures, zero new skips, zero changes to surviving tests. No
changes to any `layer_*.py`, `mutator.py`, `composition.py`,
`taxonomy.py`, `src/synthetic/prompts/`, or to
`src/synthetic/llm_proposer.py`.

---

## Scope

### In scope

- **C3** — `src/synthetic/variant_proposer.py` (new). Public surface:
  - `@dataclass(frozen=True) class VariantProposal` — fields
    `payload: Optional[dict]`, `raw_responses: tuple[str, ...]`,
    `skipped: Optional[Modification]`. Carries either the validated
    LLM payload + empty `skipped`, or `payload=None` + a populated
    `skipped` record (C2-fallback or C3-validation-failure flavours,
    distinguishable by the `reason` prefix).
  - `def propose_variant(prompt_template, slots, client,
    modification_type, *, retry_once=True) -> VariantProposal` —
    the single entry point. Renders the prompt template by escaping
    literal braces and substituting the per-type declared placeholder
    set from `slots`; calls `llm_proposer.propose(...)` with the
    rendered prompt; if `propose` returned a fallback, propagates it
    unchanged into `skipped`; otherwise validates the payload against
    the per-type schema and either passes the validated payload through
    or emits a new
    `Modification(status="skipped", reason="schema_validation_failed: ...")`
    skip record. Never raises; all failures encoded in
    `VariantProposal.skipped`.
  - Module-level constants:
    - `EXPECTED_SLOTS: dict[ModificationType, frozenset[str]]` — the
      declared placeholder set per `ModificationType`, re-encoded
      from Sprint 12's `test_prompts.py` audit. Used by the renderer
      to drive the selective un-escape and by the renderer's
      slot-key gate.
- Private helpers:
  - `_render_prompt(template, slots, modification_type) -> str` —
    escapes every `{` → `{{` and `}` → `}}` in the template, then
    un-escapes the declared placeholders in
    `EXPECTED_SLOTS[modification_type]`, then calls
    `escaped.format_map(slots)`. Validates that `slots.keys()` matches
    the expected set exactly: missing keys raise `KeyError`; extra
    keys raise `ValueError`. Raises on placeholder/slot mismatch —
    these are programming errors at the catalog-authoring boundary,
    not LLM-failure modes, and the orchestrator can be expected to
    let them propagate.
  - `_validate_payload(payload, modification_type) -> dict` — checks
    the parsed dict against the per-type schema:
    | ModificationType | Required top-level shape |
    |---|---|
    | `synonym_label`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion` | `{"synonyms": [{"original": str, "new": str}, …]}` |
    | `num_to_text` | `{"numerals": [{"original": str, "new": str}, …]}` |
    | `paraphrase`, `reorder` | `{"original": str, "new": str, "preserves_meaning": bool}` |
    | `expansion`, `compression` | `{"original": str, "new": str, "preserves_meaning": bool}` |
    | `omission` | `{"original": str, "new": str, "omitted_var": str}` |
    | `new_param` | `{"new_axis_label": str, "values": [{"label": str, "value": str}, …], "var_definition": str, "template_patch": str}` |

    Returns the payload unchanged on success; raises `ValueError` with
    a descriptive message on shape mismatch (missing key, wrong
    value type, empty list where ≥1 entry required, etc.). The
    schema enforcement is *structural*: it does not check Spanish
    fluency, paraphrase preservation, value distinctness, or
    template syntactic validity — those are Phase E review
    concerns, not C3 schema gates.
- **Tests** — `tests/synthetic/test_variant_proposer.py` (new,
  ≥25 cases). Coverage: public surface; per-`ModificationType` happy
  path (parametrised ×12); per-`ModificationType` schema-violation
  path (one missing-key case each, parametrised ×12); C2-fallback
  propagation; C3-validation-failure skip emission with the
  `"schema_validation_failed: "` prefix; brace-escape correctness
  (JSON literal in template survives intact); slot substitution
  correctness; missing-slot `KeyError`; extra-slot `ValueError`;
  `raw_responses` propagation from C2; `retry_once=False`
  short-circuit; `VariantProposal` immutability and equality;
  module re-import without side effects; the two skip-reason prefixes
  (`malformed_llm_response_after_retry: ` vs.
  `schema_validation_failed: `) are distinguishable by substring
  match — pinning the Phase E1 grep-handle convention.
- **Housekeeping**:
  - Sprint 14 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip ❌ → ✅ for a new `variant_proposer.py` row in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files
    in This Branch" section: "✅ Sprint 14 — Task C3 —
    `propose_variant` + per-type schema validation + JSON-aware
    template renderer; slot-extraction (stage-JSON → slots dict) and
    payload-to-Phase-B-rule emission deferred to Sprint 15". Prepend
    an "After Sprint 14 — …" entry to the Sprint History.

### Out of scope (explicit)

- **Slot extraction from stage JSON.** `propose_variant` takes an
  *already-built* `slots: dict[str, Any]`. The caller is responsible
  for going from `(stage_json, concept_key, modification_type)` to a
  per-type slots dict. Building that extractor needs deep familiarity
  with stage-2/3/4 JSON layouts (axis-key allocation, value-label
  lookup, var-key resolution, reorderable-constituent identification
  in templates) — enough to deserve its own sprint. Reason for
  deferral: keeps Sprint 14's surface ≤120 LOC; the slot-extraction
  surface is genuinely orthogonal (a function of stage-JSON shape,
  not LLM-response shape).
- **Payload → Phase-B rule emission.** A `synonym_label` LLM payload
  `{"synonyms": [{"original": "Normal", "new": "Estándar"}, …]}` is
  not a Phase-B rule yet — Phase B's L1 mutator consumes one rule per
  `(param, value, original, new)` tuple, and the `param` / `value`
  fields aren't in the LLM payload. The mapping payload → list-of-rule
  is per-type and pulls in slots data (the axis key, the value label).
  Bundled with slot-extraction in Sprint 15. Sprint 14's
  `VariantProposal.payload` is the validated dict; downstream code
  (Sprint 15) lifts it to rule shape.
- **A concrete LLM transport implementation.** No `OllamaClient`,
  no `AnthropicClient`, etc. The C2 `propose` Protocol surface is
  the transport contract; tests instantiate the same `_StubLLMClient`
  pattern from Sprint 13's test file. A3's "LLM proposer choice
  spike" is still TBD; the concrete client lands in a follow-up
  sprint, not here.
- **Per-type Spanish fluency / semantic-preservation checks.** The
  schema validator checks dict-shape only. "Does this paraphrase
  preserve meaning?" / "Is the new synonym idiomatic technical
  Spanish?" / "Does the omission produce grammatical text?" are
  reviewer concerns (Phase E reviewer harness). C3 does not enforce
  semantics — only structure.
- **`pydantic` / `jsonschema` as runtime dependencies.** Sprint 14
  keeps the dependency surface tight. The 12 schemas are simple
  enough that hand-coded `isinstance` checks + key-presence checks
  are cleaner than declaring a `pydantic.BaseModel` per type (the
  declarative form would still need a per-type `model_validate`
  call, and the error messages would be `pydantic.ValidationError`
  noise instead of the tight `schema_validation_failed: …` reason
  string Phase E1's grep wants). Reversible: a future sprint can
  swap `_validate_payload` to delegate to `pydantic` without
  changing the public surface.
- **Compositionality enforcement.** `compose_rules` (Sprint 11) is
  the pre-apply validator the orchestrator (D2) will consult when
  fanning multi-rule batches through `_DISPATCH`. C3 ships a
  single-`Modification`-candidate-per-call shape; multi-rule
  composition is a downstream concern.
- **Variant catalog persistence (C4).** No
  `data/synthetic/variants/{concept_key}.json` writes; no
  `data/synthetic/variants/__init__.py`; no IO at all besides
  whatever `client.complete(prompt)` does. C3 is pure in-memory —
  the catalog writer is the next sprint.
- **`{allowlist}` slot population for `new_param`.** Phase B4's
  `configs/synthetic/new_param_allowlist.yaml` is still not
  authored. The slot remains the caller's responsibility; tests
  pass an empty list `"[]"` or a stub string. Phase F prompt-tuning
  revisits.
- **Live LLM calls in pytest CI.** All tests use the
  `_StubLLMClient` pattern. Real-model smoke tests live in
  `scripts/spike_a3_*.py` or a manually-run notebook.
- **Streaming, chat-format, function-calling, tool-use APIs.** Same
  Sprint 13 rationale — the Protocol surface is
  `complete(prompt) -> str`; A3's concrete client adapts whatever
  native shape the chosen vendor exposes into that single method.
- **Anything under `src/synthetic/prompts/`, `data/`, notebooks,
  `configs/`, or `src/utils/`.** C3 is additive in exactly one new
  module file + one new test file. No edits to existing files
  besides the two doc files.
- **Changes to `src/synthetic/llm_proposer.py`.** Sprint 13's
  `propose` is consumed as-is. If Sprint 14 discovers a needed
  refinement in C2 (e.g., expose `_parse_json_object` publicly,
  add a `payload_only` shortcut), it should land in a separate
  PR, not bundled into the C3 sprint.

---

## Module surface

```python
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

  * slot extraction (per-concept context → slots dict) — caller's
    responsibility; the Sprint 15 slot-extraction shim is the
    intended provider;
  * payload → Phase-B rule mapping (the `layer_*.py` mutators
    consume `{"type": ..., "param": ..., ...}` dicts; that lift is
    Sprint 15's territory);
  * variant catalog persistence (Sprint 15+ — C4);
  * a concrete LLM transport (still A3 — `LLMClient` Protocol).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from .llm_proposer import LLMClient, propose
from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER


EXPECTED_SLOTS: dict[ModificationType, frozenset[str]] = {
    ModificationType.SYNONYM_LABEL:    frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.NUM_TO_TEXT:      frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.UNIT_CONVERSION:  frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.UNIT_EXPANSION:   frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.ABBREV_EXPANSION: frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.CODE_EXPANSION:   frozenset({"concept", "axis_label", "value_list"}),
    ModificationType.PARAPHRASE:       frozenset({"concept", "var_key", "fragment", "condition"}),
    ModificationType.EXPANSION:        frozenset({"concept", "var_key", "fragment", "condition"}),
    ModificationType.COMPRESSION:      frozenset({"concept", "var_key", "fragment", "condition"}),
    ModificationType.OMISSION:         frozenset({"concept", "template", "var_to_omit", "axis_label"}),
    ModificationType.REORDER:          frozenset({"concept", "template", "constituents"}),
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

      KeyError  — slots is missing a declared placeholder
      ValueError — slots has an undeclared key, OR the template's
                   placeholder set doesn't match EXPECTED_SLOTS[mtype]

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
    `EXPECTED_SLOTS[modification_type]` exactly."""
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
    elif modification_type is ModificationType.OMISSION:
        _validate_omission(payload)
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
```

### Behavioural requirements

1. **`propose_variant` never raises on LLM-failure or schema-failure
   paths.** Both modes encode into `VariantProposal.skipped`. The
   caller (eventually D2 orchestrator) walks a uniform return-value
   path. Symmetric with Sprint 13's `propose` contract.
2. **Two distinguishable skip-reason prefixes.**
   `"malformed_llm_response_after_retry: "` — C2-fallback, the LLM
   never produced parseable JSON. `"schema_validation_failed: "` —
   C2 succeeded but the payload didn't match the per-type schema.
   Phase E1's metadata pipeline grep on the prefix to distinguish
   the two error families. Pinned by a test.
3. **`_render_prompt` raises (not skips) on slot/placeholder
   mismatch.** Missing slots → `KeyError`; extra slots →
   `ValueError`. These are catalog-authoring programming errors at
   build time, not LLM-runtime failures, and silent skipping would
   hide them. Reasonable for the orchestrator to catch-and-log if
   it wants graceful behaviour across an entire concept batch, but
   the default is propagate.
4. **`EXPECTED_SLOTS` is a frozen dict-of-frozensets, in lockstep
   with `tests/synthetic/test_prompts.py`'s `_EXPECTED_PLACEHOLDERS`.**
   Drift between the two is a regression: Sprint 14 adds an
   audit-style test (`test_expected_slots_matches_prompt_audit`)
   that re-checks every prompt against the C3 constant. If a future
   sprint adds a new `ModificationType`, both constants must update
   together.
5. **`_validate_payload` is shape-only; no semantic checks.** It
   verifies dict shape, key presence, value types, and (for
   `new_param`'s `values`) bounded length. It does not check
   Spanish fluency, paraphrase preservation, value distinctness,
   template syntactic validity, or anything else that requires
   linguistic / catalog-semantic knowledge. Those are Phase E
   reviewer concerns.
6. **`new_param.values` length is gated at 2 ≤ N ≤ 5.** Matches the
   prompt's "entre 2 y 5 valores discretos" wording. The validator
   raises `values_out_of_range` outside that interval. Verified by
   `test_validate_new_param_rejects_out_of_range_lengths`.
7. **`new_param.values[i].label` is not yet uniqueness-checked.**
   The Phase E reviewer harness will check label uniqueness +
   admissibility against the allowlist. C3's structural schema is
   intentionally narrower. (A future tightening can add the unique-
   labels check in `_validate_new_param` without breaking the
   public surface.)
8. **Brace escaping is two-pass and order-independent.** First pass:
   double every `{` and every `}` in the template. Second pass:
   for each declared placeholder, replace `{{key}}` (the doubled
   form) with `{key}` (the format-string form). The order of
   `replace` calls across placeholders doesn't matter because no
   placeholder name is a substring of another. The
   `.format_map(slots)` call then substitutes the un-escaped
   placeholders and leaves the JSON-literal `{{` / `}}` as
   single-brace `{` / `}` in the output. Verified by a
   round-trip test that checks the rendered output contains the
   *literal* JSON contract (single braces) and the *substituted*
   slot values.

### Acceptance

- `from synthetic.variant_proposer import VariantProposal,
  propose_variant, EXPECTED_SLOTS` succeeds.
- `len(EXPECTED_SLOTS) == 12` and
  `set(EXPECTED_SLOTS) == set(ModificationType)`.
- For each `mtype in ModificationType`: a happy-path `propose_variant`
  with a one-shot stub returning a schema-valid JSON payload yields
  `VariantProposal(payload=<the_payload>, raw_responses=(<text>,),
  skipped=None)`.
- For each `mtype in ModificationType`: a stub returning
  `{"unrelated": "data"}` yields a `VariantProposal` with `payload=None`
  and `skipped.reason.startswith("schema_validation_failed: ")`.
- C2-fallback propagation: stub returning `["junk1", "junk2"]`
  yields `skipped.reason.startswith("malformed_llm_response_after_retry: ")`.
- `pytest tests -q` exits 0 with **≥392 passed, exactly 1 skipped**,
  zero failures.

---

## Tasks

### Task 1 — `src/synthetic/variant_proposer.py`

Create the module as specified in §"Module surface" above.
Implementation notes:

1. **Single-pass brace-escape, single-pass un-escape.** Use plain
   `str.replace` — no regex. The naive approach is correct because
   placeholder names are alphanumeric+underscore and none is a
   substring of another (audit: `concept`, `axis_label`, `value_list`,
   `var_key`, `fragment`, `condition`, `template`, `constituents`,
   `var_to_omit`, `existing_axes_with_labels`, `allowlist`,
   `template_patch`, `new_axis_label`, `var_definition`).
   `template_patch` is *not* a slot key (it's a `new_param` payload
   field), so no slot-key/value-key collision.
2. **`EXPECTED_SLOTS` is a module-level constant**, not a function
   call. Sprint 12's `test_prompts.py` already pinned the
   placeholder set per type; we re-encode the *same* sets here.
   The lockstep audit (Task 2's
   `test_expected_slots_matches_prompt_audit`) is the binding
   contract — if the two ever drift, a test fails.
3. **`_validate_payload` uses `isinstance(value, bool)` *before*
   `isinstance(value, int)`** if any check needs a bool — Python's
   `bool` is a subclass of `int`, so the order matters. The current
   `_validate_original_new_preserves` checks bool directly, so we
   don't trip this trap, but the comment is worth adding to the
   helper.
4. **`_validate_new_param.values` uses 2 ≤ len ≤ 5.** From the
   `new_param.txt` prompt's "entre 2 y 5 valores discretos" wording.
   Outside this range → `values_out_of_range: len=<n> (expected 2..5)`.
5. **No `logger` import.** Sprint 13's pure-data-flow convention
   continues. The orchestrator logs `VariantProposal.skipped` if
   desired.
6. **No module-level side effects.** No env reads, no on-import
   I/O. Symbols only.
7. **Stdlib-only imports** plus the in-repo `llm_proposer` and
   `taxonomy` modules. No `pydantic`, no `jsonschema`.

### Task 2 — `tests/synthetic/test_variant_proposer.py`

Create the test file. ≥25 cases. Skeleton:

```python
from __future__ import annotations

import importlib
from dataclasses import FrozenInstanceError

import pytest

from synthetic.variant_proposer import (
    EXPECTED_SLOTS,
    VariantProposal,
    propose_variant,
)
from synthetic.taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER


_ALL_TYPES = tuple(ModificationType)


class _StubLLMClient:
    """In-test transport, identical to Sprint 13's pattern."""
    def __init__(self, responses: list[str]):
        self._queue = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._queue:
            raise AssertionError("_StubLLMClient: no more queued responses")
        return self._queue.pop(0)


# Per-type happy-path templates and slot dicts. Each template includes
# every declared slot once + a literal `Responde SOLO con un JSON: {...}`
# block so the renderer's brace-escape is exercised on every type.
_TEMPLATES: dict[ModificationType, str] = {
    ModificationType.SYNONYM_LABEL: (
        "Concepto: {concept}\nEje: {axis_label}\nValores: {value_list}\n"
        'Responde SOLO con un JSON: {"synonyms": [...]}'
    ),
    # ... one per ModificationType
}

_SLOTS: dict[ModificationType, dict[str, str]] = {
    ModificationType.SYNONYM_LABEL: {
        "concept": "Canalización",
        "axis_label": "TIPO DE TERRENO",
        "value_list": "Normal, Rocoso",
    },
    # ... one per ModificationType
}

_PAYLOADS: dict[ModificationType, dict] = {
    ModificationType.SYNONYM_LABEL: {
        "synonyms": [{"original": "Normal", "new": "Estándar"}]
    },
    ModificationType.NUM_TO_TEXT: {
        "numerals": [{"original": "2", "new": "dos"}]
    },
    ModificationType.PARAPHRASE: {
        "original": "Hormigón HM-20",
        "new": "Hormigón en masa HM-20",
        "preserves_meaning": True,
    },
    # ... etc.
}
```

Required test cases (≥25 functions, expanding to ≥60 cases with
parametrisations):

1. **`test_module_exposes_public_surface`** — `VariantProposal`,
   `propose_variant`, `EXPECTED_SLOTS` import correctly.
2. **`test_expected_slots_covers_all_modification_types`** —
   `set(EXPECTED_SLOTS) == set(ModificationType)`;
   `len(EXPECTED_SLOTS) == 12`.
3. **`test_expected_slots_matches_prompt_audit`** — for each
   `ModificationType`, load the actual prompt file via
   `synthetic.prompts.load_prompt(mtype)` and check that every
   declared placeholder in `EXPECTED_SLOTS[mtype]` appears as
   `{<name>}` in the prompt body (before the
   `"Responde SOLO con un JSON"` literal). Pins the lockstep
   between Sprint 12's prompts and Sprint 14's slot constant.
4. **`test_happy_path_per_type`** (parametrised ×12) — for each
   `mtype`, build a stub returning `json.dumps(_PAYLOADS[mtype])`,
   call `propose_variant(_TEMPLATES[mtype], _SLOTS[mtype], stub,
   mtype)`, assert `result.payload == _PAYLOADS[mtype]`,
   `result.skipped is None`,
   `len(result.raw_responses) == 1`.
5. **`test_schema_violation_per_type`** (parametrised ×12) — for
   each `mtype`, stub returns `'{"unrelated": "data"}'`, assert
   `result.payload is None`, `result.skipped is not None`,
   `result.skipped.type == mtype`,
   `result.skipped.layer == TYPE_TO_LAYER[mtype]`,
   `result.skipped.status == "skipped"`,
   `result.skipped.reason.startswith("schema_validation_failed: ")`.
6. **`test_c2_fallback_propagates`** — stub queue `["junk1", "junk2"]`
   (both malformed JSON); result has `payload=None`,
   `skipped is not None`,
   `skipped.reason.startswith("malformed_llm_response_after_retry: ")`,
   `len(raw_responses) == 2`.
7. **`test_two_skip_prefixes_are_distinguishable`** — pin that
   `"malformed_llm_response_after_retry: "` and
   `"schema_validation_failed: "` are non-overlapping substrings.
8. **`test_render_substitutes_slots`** — for a fixed type, build
   a template with three placeholders + a JSON literal; assert the
   rendered string contains all three slot values and the literal
   `"Responde SOLO con un JSON: {"` (single brace, not doubled).
9. **`test_render_preserves_json_literal_braces`** — template
   `'... {"k": [1, 2]} ...'`; assert the rendered output contains
   `'{"k": [1, 2]}'` exactly (single braces).
10. **`test_render_missing_slot_raises_keyerror`** —
    `propose_variant(template, {}, stub, ModificationType.SYNONYM_LABEL)`
    → `KeyError` mentioning the missing slot.
11. **`test_render_extra_slot_raises_valueerror`** —
    `propose_variant(template, {**valid_slots, "extra": "x"}, ...)`
    → `ValueError` mentioning the extra slot.
12. **`test_render_rejects_partial_slots`** — provide 2 of 3
    expected slots → `KeyError` listing both missing names.
13. **`test_validate_pair_list_missing_key`** —
    `_validate_payload({"unrelated": []}, SYNONYM_LABEL)` →
    `ValueError("missing_key: 'synonyms'")`.
14. **`test_validate_pair_list_wrong_inner_shape`** —
    `_validate_payload({"synonyms": [{"original": "x"}]}, SYNONYM_LABEL)`
    → `ValueError("synonyms[0]_missing_key: 'new'")`.
15. **`test_validate_pair_list_empty`** —
    `_validate_payload({"synonyms": []}, SYNONYM_LABEL)` →
    `ValueError("synonyms_is_empty")`.
16. **`test_validate_pair_list_non_str_value`** —
    `_validate_payload({"synonyms": [{"original": 1, "new": "x"}]}, ...)`
    → `ValueError` mentioning `original_not_str` and `type=int`.
17. **`test_validate_original_new_preserves_happy`** — three
    L2 + reorder types accept the right shape.
18. **`test_validate_original_new_preserves_rejects_int_bool`** —
    `preserves_meaning=1` rejected with
    `preserves_meaning_not_bool` (pins the `bool`-not-`int`
    isinstance order).
19. **`test_validate_omission_happy_and_sad`** — accepts
    `{"original", "new", "omitted_var"}` (all strs); rejects each
    missing-key flavour individually.
20. **`test_validate_new_param_happy`** — full payload with
    2-element `values` list accepted.
21. **`test_validate_new_param_rejects_out_of_range_lengths`** —
    parametrise over `len=0`, `len=1`, `len=6`; all rejected with
    `values_out_of_range`.
22. **`test_validate_new_param_rejects_wrong_inner_shape`** —
    `values=[{"label": "a"}]` (missing `value`); rejected.
23. **`test_raw_responses_propagate_from_c2`** — single-success
    path → `len(raw_responses) == 1`; retry-then-success path
    (stub queue `["bad", "<valid_json>"]`) → `len == 2`; assert
    both elements match the queued strings.
24. **`test_retry_once_false_short_circuits`** — single malformed
    response queued + `retry_once=False` → `skipped` is the
    `malformed_llm_response_after_retry` flavour;
    `len(raw_responses) == 1`; stub received exactly 1 call.
25. **`test_propose_variant_does_not_raise_on_any_llm_failure`** —
    parametrise across malformed/wrong-shape/empty stub
    responses; assert every path returns a `VariantProposal`
    (no `pytest.raises`).
26. **`test_variant_proposal_is_frozen`** —
    `result.payload = {}` → `FrozenInstanceError` /
    `AttributeError`.
27. **`test_variant_proposal_equality`** — two structurally
    identical results compare equal.
28. **`test_module_has_no_side_effects_at_import`** —
    `importlib.reload(synthetic.variant_proposer)` → no exceptions;
    `EXPECTED_SLOTS` and `propose_variant` identity preserved.
29. **`test_rendered_prompt_passed_to_client_verbatim`** — stub
    captures `prompt` in `stub.calls`; assert the captured prompt
    contains every slot value and the JSON literal exactly once.
30. **`test_skip_record_other_fields_are_none`** — on
    schema-validation skip: `param`, `var`, `condition`, `field`,
    `value`, `original`, `new` are all `None`. (Same convention as
    Sprint 13's `_build_fallback`.)

Test count: 30 functions; parametrisation expansion (×12 happy
+ ×12 schema-violation + ×3 new_param-length + ×6 malformed-input)
brings the headline to **≥70 cases**. Binding gate is "≥25 listed
functions, all green".

### Task 3 — Housekeeping

After Tasks 1–2 pass:

1. Append a Sprint 14 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: the new
   `variant_proposer.py` module, its public surface
   (`VariantProposal`, `propose_variant`, `EXPECTED_SLOTS`), the
   three terminal shapes (success / C2 fallback / C3 schema
   failure) and their distinguishable reason prefixes, the
   brace-escape strategy, the per-type schema table, the
   test-count delta, the C3/C4 boundary (Sprint 14 owns
   render + validate; Sprint 15 owns slot-extraction + payload →
   rule emission + C4 catalog writer), and a one-line next-step
   recommendation (Sprint 15 — slot extraction + rule emission +
   variant catalog writer).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Add a new `variant_proposer.py` row under the existing
     `llm_proposer.py` row in the "New Files in This Branch" file
     map; flip it ✅ with the annotation "Sprint 14 — Task C3 —
     `propose_variant` + per-type schema validation + JSON-aware
     template renderer; slot-extraction and payload-to-rule lift
     deferred to Sprint 15".
   - Update the `llm_proposer.py` row's "C3 still ❌" trailing
     note: drop the "; C3 still ❌" suffix now that C3 lands in
     its own row.
   - Prepend a new "After Sprint 14 — …" entry to the Sprint
     History section.
3. Do **not** modify
   [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md). §3.3 and
   §8 already cover Stage A's LLM-assisted variant proposal model
   at the framing layer; nothing changes there.
4. Do **not** modify
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §5 Phase C
   C3. The protocol entry already names
   `src/synthetic/variant_proposer.py`, the LLM call, the schema
   validation, and the candidate return — Sprint 14 ships exactly
   that.
5. Do **not** create
   `data/synthetic/variants/__init__.py` or any
   `data/synthetic/variants/*.json`. The catalog persistence layer
   is C4 (Sprint 15+).

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥392 passed, 1 skipped** (Sprint 12's `new_param`
brace-audit skip is still the only skip in the suite). Zero failures.
The skip count must stay at exactly 1 — any new skip is a regression.

> ⚠ **Plan-self-consistency cross-check** (continuing the
> Sprint 07–13 convention): the binding gate is "≥25 new test
> functions, all green, no skips, no regressions in the 362-pass +
> 1-skip baseline". The headline pytest number depends on how many
> parametrisations the implementer keeps. Update the RESEARCH_LOG
> entry with the actual count.

Smoke checks (PowerShell-friendly one-liners):

```powershell
python -c "from synthetic.variant_proposer import VariantProposal, propose_variant, EXPECTED_SLOTS; from synthetic.taxonomy import ModificationType; print('imports ok'); print('expected slots types:', len(EXPECTED_SLOTS), '==', len(ModificationType))"

python -c "
import json
from synthetic.variant_proposer import propose_variant
from synthetic.taxonomy import ModificationType

class _S:
    def __init__(self, q): self._q = list(q)
    def complete(self, p): return self._q.pop(0)

# Happy path
tmpl = 'Concepto: {concept}\nEje: {axis_label}\nValores: {value_list}\nResponde SOLO con un JSON: {\"synonyms\": [...]}'
slots = {'concept': 'Canalización', 'axis_label': 'TIPO DE TERRENO', 'value_list': 'Normal, Rocoso'}
payload = {'synonyms': [{'original': 'Normal', 'new': 'Estándar'}]}
r = propose_variant(tmpl, slots, _S([json.dumps(payload)]), ModificationType.SYNONYM_LABEL)
assert r.payload == payload and r.skipped is None
print('happy path ok')

# C3 schema-violation path
r2 = propose_variant(tmpl, slots, _S(['{\"unrelated\": []}']), ModificationType.SYNONYM_LABEL)
assert r2.payload is None and r2.skipped.reason.startswith('schema_validation_failed: ')
print('schema-violation ok -', r2.skipped.reason[:60], '...')

# C2 fallback path propagates
r3 = propose_variant(tmpl, slots, _S(['junk1', 'junk2']), ModificationType.SYNONYM_LABEL)
assert r3.skipped.reason.startswith('malformed_llm_response_after_retry: ')
print('C2 fallback propagation ok')
"
```

End-of-sprint expected `git status --short` (sprint-scoped subset
only):

```
new file:   src/synthetic/variant_proposer.py
new file:   tests/synthetic/test_variant_proposer.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_14.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`,
nothing under `configs/`. **No changes to any `layer_*.py`, to
`mutator.py`, to `composition.py`, to `taxonomy.py`, to
`src/synthetic/prompts/`, or to `src/synthetic/llm_proposer.py`**
— C3 is additive in one new module plus its test file.

---

## Design notes worth committing to memory

- **Render → propose → validate is the right pipeline.** Three
  pure functions, composed by `propose_variant`. Each helper has
  a narrow contract and a tight test surface; the orchestrator
  function is just glue.
- **Brace-escape uses pre-escape + selective un-escape, not
  split-at-marker.** The split-at-`"Responde SOLO con un JSON"`
  alternative would couple the renderer to that exact marker
  phrase — if a future prompt drops or rewords it, the splitter
  silently mis-classifies. Pre-escape is marker-agnostic.
- **`EXPECTED_SLOTS` is a module-level constant; the
  cross-file audit test is the binding contract.** The two
  declarations (Sprint 12's `_EXPECTED_PLACEHOLDERS` in
  `test_prompts.py` and Sprint 14's `EXPECTED_SLOTS` in
  `variant_proposer.py`) live in different files for a reason —
  one is a *test fixture* that drives prompt audits; the other is
  a *production constant* that drives runtime rendering. Drift
  between them is caught by
  `test_expected_slots_matches_prompt_audit`, which loads the
  actual prompts off disk and re-verifies the production constant.
- **`_validate_payload` is shape-only, by intent.** Reviewer-grade
  validation (does this paraphrase actually preserve meaning?
  is this synonym idiomatic technical Spanish?) belongs to Phase E.
  The schema check is the contractually-pinned shape, nothing
  more.
- **Two distinct skip-reason prefixes** — Phase E1's metadata
  pipeline grep on `"malformed_llm_response_after_retry: "` to
  count C2 failures per type, and on `"schema_validation_failed: "`
  to count C3 failures. Together they answer "of the proposals
  that didn't land, where did they break?".
- **`propose_variant` never raises on LLM- or schema-failure
  paths.** Same uniform-return-value contract Sprint 13 established.
  But `_render_prompt` *does* raise on slot/placeholder mismatch
  — those are build-time programming errors, not runtime data
  shapes.
- **The payload, not a rule, is the candidate.** Sprint 15 lifts
  the validated payload to Phase-B rule shape using the
  per-concept context (axis keys, value labels, var keys) that
  the slot-extraction shim will already have at hand. Keeping the
  payload→rule mapping out of C3 keeps the schemas (12 of them)
  free from per-concept context noise.
- **`new_param.values` length-gate is the only numeric bound the
  schema enforces.** Every other constraint (label uniqueness,
  admissibility against `new_param_allowlist.yaml`,
  axis-distinctness from existing axes) is structural-blind here
  and falls to Phase E. The 2..5 bound is in the prompt itself
  ("entre 2 y 5 valores discretos") and so is the natural place
  to enforce it.
- **No `pydantic` / `jsonschema` runtime dep.** The 12 schemas are
  too simple to justify the import, the declarative model file,
  and the noisier error messages. Reversible if Phase E grows a
  schema-introspection need; the public surface doesn't change.
- **No live LLM calls in pytest.** Identical Sprint 13 rationale —
  `_StubLLMClient` only; real-model smoke tests live in
  `scripts/spike_a3_*.py` or a manually-run notebook.
- **`VariantProposal.raw_responses` mirrors
  `ProposalResult.raw_responses` exactly.** No filtering, no
  reformatting — Sprint 14 just passes the C2 capture through.
  Phase E1's metadata pipeline can compare the raw payload against
  the validated payload for diagnostic purposes (e.g., "the LLM
  returned `{"synonimos": ...}` instead of `{"synonyms": ...}` —
  consider a prompt polish").
- **`EXPECTED_SLOTS` keys are sorted in the error messages.**
  Cosmetic but pinned by test: missing-slot / extra-slot errors
  report slot names in `sorted()` order so the error string is
  byte-deterministic run-to-run (set iteration was
  PYTHONHASHSEED-randomized — see Sprint 6.5's analogous fix
  inside `s07_Filter_duplicates.ipynb`).

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch
  context, file map (`variant_proposer.py` row to be added;
  `llm_proposer.py` row's "C3 still ❌" suffix to be removed).
- [`../RESEARCH_PROPOSAL.md §3.3`](../RESEARCH_PROPOSAL.md) — Stage
  A pipeline framing (LLM-assisted variant proposal + human
  review). §8 lists the four representative prompts (their JSON
  contracts are the source of the C3 schemas for
  `synonym_label` / `paraphrase` / `omission` / `new_param`).
- [`../RESEARCH_PROTOCOL.md §5 Phase C`](../RESEARCH_PROTOCOL.md) —
  C3 task definition ("variant proposer … calls the LLM,
  validates output shape against the `Modification` schema,
  returns a candidate"). §2 risk-table row "LLM proposer model:
  TBD" stays open (still A3's deferred sprint).
- [`SPRINT_12.md`](SPRINT_12.md) — the prompt library + the
  `_EXPECTED_PLACEHOLDERS` audit Sprint 14 mirrors in
  `EXPECTED_SLOTS`.
- [`SPRINT_13.md`](SPRINT_13.md) — the LLM client Sprint 14
  consumes. C2's `propose` is the inner round-trip;
  `ProposalResult.raw_responses` propagates into
  `VariantProposal.raw_responses` unchanged; the C2 fallback's
  `Modification` becomes `VariantProposal.skipped` unchanged.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py)
  — `Modification`, `ModificationType`, `Layer`, `TYPE_TO_LAYER`.
  Sprint 14 imports the first three for the skip record's shape
  and the fourth for `type → layer` lookup.
- [`../../src/synthetic/prompts/__init__.py`](../../src/synthetic/prompts/__init__.py)
  — `load_prompt`. Sprint 14 imports it from
  `tests/synthetic/test_variant_proposer.py` (for the
  cross-file audit test only); the production module
  `variant_proposer.py` does **not** import it directly — the
  caller passes a pre-loaded template string.

---

## Non-goals reminder

If you find yourself opening `data/synthetic/` to read or write a
variant catalog file, `src/synthetic/composition.py` to wire the
composer in, or any `layer_*.py` to consume the proposer's output
— **stop**. Sprint 14 is additive in exactly one new module
(`variant_proposer.py`) plus its test file. Catalog persistence is
C4 (next sprint).

If you find yourself building a function that takes a
`(stage_json, concept_key, modification_type)` triple and returns a
per-type slots dict — **stop**. That's the Sprint 15 slot-extraction
shim. Sprint 14's `propose_variant` takes an *already-built* slots
dict.

If you find yourself lifting a validated LLM payload to a
Phase-B rule dict (e.g.,
`{"type": "synonym_label", "param": "B", "value": "a", "original": "Normal", "new": "Estándar"}`)
— **stop**. That's also Sprint 15. Sprint 14's
`VariantProposal.payload` is the validated dict, not a rule.

If you find yourself importing or shimming
`pydantic` / `jsonschema` / `cerberus` / any external schema lib —
**stop**. Stdlib + Sprint 13's `llm_proposer` + Sprint 01's
`taxonomy` are the only allowed runtime imports. The hand-coded
validators are intentional.

If you find yourself running a real LLM endpoint inside the
pytest suite — **stop**. All tests use `_StubLLMClient` with
queued responses. Real-model smoke tests live in `scripts/` (A3's
problem) or in a manually-run notebook (Phase F1 pilot).

If you find yourself adding logging, telemetry, or metric
emission inside `variant_proposer.py` — **stop**. The module is
pure data-flow; instrumentation is the orchestrator's (D2's)
call. Same Sprint 13 rationale.

If you find yourself extending the `Modification` dataclass to
carry an `original_llm_payload` field — **stop**.
`VariantProposal.raw_responses` already exposes that. Embedding
it in `Modification` would change the taxonomy schema for a
diagnostic concern.

If you find yourself splitting the template at the literal
`"Responde SOLO con un JSON"` string to bypass the brace-escape
— **stop**. The escape strategy is marker-agnostic and survives
prompt polish; the split-at-marker alternative couples C3 to a
specific phrase. Pre-escape + selective un-escape is the design.

If you find yourself widening `_validate_payload` to check
semantics (paraphrase preservation, synonym idiomaticity, value
distinctness, template grammaticality) — **stop**. That's Phase
E. C3's validator is structural only.
