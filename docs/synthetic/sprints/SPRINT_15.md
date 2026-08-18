# Sprint 15 — Phase C Task C4 (variant catalog writer) + slot-extraction shim + payload-to-rule lift

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 15                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | C4 + two Sprint-14-deferred concerns — see [`../RESEARCH_PROTOCOL.md §5 Phase C`](../RESEARCH_PROTOCOL.md) |
| **Predecessor** | Sprint 14 — `variant_proposer.py` (`propose_variant` + `EXPECTED_SLOTS` + per-type schema validation) (see [`SPRINT_14.md`](SPRINT_14.md)) |
| **Successor**   | Sprint 16 — Phase D Task D2 (orchestrator `run_synthetic.py` — concept-loop driver that ties prompts → proposer → catalog → mutator together) |

---

## Context

Sprint 14 closed C3 (variant proposer) with a deliberately narrow surface:
`propose_variant` takes an **already-rendered prompt** and an
**already-built slots dict** and returns a `VariantProposal` whose
`payload` is the validated LLM dict — *not* a Phase-B rule. Two
explicit deferrals fell out of that boundary call:

1. **Slot extraction.** The caller is responsible for going from
   `(stage_json, concept_key, modification_type)` to a per-type slots
   dict matching `EXPECTED_SLOTS[modification_type]`. Sprint 14's
   tests passed inline literal dicts; production code needs a real
   walker.
2. **Payload → Phase-B rule emission.** A `synonym_label` payload
   `{"synonyms": [{"original": "Normal", "new": "Estándar"}, …]}` is
   not a Phase-B rule yet — `layer_l1.apply_synonym_label` consumes
   `{"type": "synonym_label", "param": "B", "value": "a",
   "original": "Normal", "new": "Estándar"}`, and the `param` /
   `value` fields aren't in the LLM payload (they need to be lifted
   from the per-concept stage-JSON context that the slot extractor
   already has at hand).

The protocol's [§5 Phase C C4](../RESEARCH_PROTOCOL.md) names the
third concern:

> **C4. Variant catalog.** JSON-per-concept files under
> `data/synthetic/variants/` storing every accepted variant with its
> full `modifications` log. Durable artifact of Stage A; pipeline
> reruns consume this catalog.

All three concerns share the same per-concept context (the stage JSON
walk, the slots dict, the validated payload, the emitted rules, the
final `Modification` records). Bundling them into one sprint keeps the
context-passing boundaries sharp; splitting would force a temporary
inter-module shim that lasts a single sprint cycle.

Three design tensions to resolve up front:

1. **Single-target vs. multi-target slot extraction.** A `synonym_label`
   slot dict pins one axis (`{"axis_label": "TIPO DE TERRENO",
   "value_list": "Normal, Rocoso"}`) but a concept has multiple axes
   (`B`, `C`, `D`, …). The natural call shape is therefore
   `extract_slots(stage_json, concept_key, mtype, target_id)` —
   single-target — paired with an enumerator
   `enumerate_targets(stage_json, concept_key, mtype) -> Iterator[Any]`
   that yields every viable `target_id` for the concept. The
   orchestrator (D2, next sprint) loops over `enumerate_targets`,
   builds one slots dict per target via `extract_slots`, and ships
   each through `propose_variant`. Same pattern as the Sprint-14
   `_StubLLMClient`'s queue — one call per target.
2. **Per-type `target_id` shape.** L1's six types target one axis key
   (a single letter like `"B"`). L2's three types target a
   `(var_key, condition)` pair (e.g., `("K", "%B=a")`). L3 omission
   targets a `(field, var_to_omit)` pair (e.g.,
   `("TEXTO", "N")`). L3 reorder targets a field
   (`"TEXTO"`). PD `new_param` has no target — yields one `None`.
   Sprint 15 codifies these as the canonical `target_id` shapes;
   `enumerate_targets` and `extract_slots` agree on them. A
   per-type-tagged tuple (e.g.,
   `L1Target(axis="B")`, `L2Target(var="K", condition="%B=a")`,
   `OmissionTarget(field="TEXTO", var="N")`) is cleaner than raw
   tuples — wraps the type signature so a caller mixing two types
   gets a static-typing tell. But Phase B's rule schemas use bare
   strings, so the wrapping adds boilerplate without saving anything.
   Sprint 15 ships **plain Python primitives** (strings and
   tuples) as `target_id`; readability wins.
3. **Rule emission: structural vs. semantic.** The L1/L2/L3 lifts are
   structural: take the payload, take the slot/target context, fill
   in the rule schema. The PD `new_param` lift wants more —
   `var_definition` is a raw string `'$X = "..." * (%G=a) + ...'` that
   the L1 / L2 mutators can't consume as-is (they need a parsed
   `text_variable: {"var": "X", "formula": '...'}` block); the
   `template_patch` string needs anchoring against the existing
   resumen / texto templates. **Sprint 15 ships the structural
   lift for L1/L2/L3 in full and a partial lift for PD** — the
   PD rule emitter emits `{type, param, label, values}` (the
   required fields per `layer_pd.apply_new_param`) and stores the
   raw `var_definition` and `template_patch` strings as
   pass-through metadata. Parsing those strings into the optional
   `text_variable` / `template_patches` rule fields is a follow-up
   sprint (Sprint 16+); the structural shape ships now so the
   orchestrator can wire the catalog end-to-end without blocking.

Sprint 14's verification baseline: **448 passed + 1 skipped.**
Sprint 15 adds three new modules + three new test files. Net pytest
delta target: **≥+40 new cases** = **≥488 passed** total. Zero
failures, zero new skips, zero changes to surviving tests. No
changes to any `layer_*.py`, `mutator.py`, `composition.py`,
`taxonomy.py`, `src/synthetic/prompts/`, `src/synthetic/llm_proposer.py`,
or `src/synthetic/variant_proposer.py`.

---

## Scope

### In scope

- **C4-prep: slot extractor** — new module
  `src/synthetic/slot_extractor.py`. Public surface:
  - `def enumerate_targets(stage_json, concept_key, modification_type)
    -> Iterator[Any]` — yields one `target_id` per viable
    application site within the concept, per-type semantics:
    - L1 (six types): each axis key in `parameters` (e.g.,
      `"B"`, `"C"`).
    - L2 (three types): each `(var_key, condition)` tuple parsed
      from the formula in `text_variables[var_key]` (one
      condition per `* (%X=y)` clause).
    - L3 omission: each `(field, var_token)` pair where `field ∈
      {"RESUMEN", "TEXTO"}` and `var_token` is each unique
      `$<letter>` substring in the field's text.
    - L3 reorder: each `field ∈ {"RESUMEN", "TEXTO"}` —
      reorder is a whole-field operation; the LLM picks the
      constituents internally.
    - PD `new_param`: yields exactly one `None` — only one new
      param per concept-attempt; the LLM picks the new axis.
  - `def extract_slots(stage_json, concept_key, modification_type,
    target_id) -> dict[str, Any]` — returns a slots dict that
    matches `EXPECTED_SLOTS[modification_type]` exactly (i.e.,
    Sprint 14's `propose_variant` accepts it without raising).
    Per-type field derivation:
    - L1 `{concept, axis_label, value_list}` —
      `concept = concept_resumen(stage_json, concept_key)`;
      `axis_label = parameters[target_id]["label"]`;
      `value_list = "; ".join(f"{v['label']}: {v['value']}" for v
      in parameters[target_id]["values"])`.
    - L2 `{concept, var_key, fragment, condition}` — `target_id`
      is `(var_key, condition)`; `var_key`, `condition` pass
      through; `fragment` is the literal-string operand bound to
      the condition in the formula (e.g., for
      `$K = "normal" * (%B=a) + "bajo vías" * (%B=b)` and
      condition `"%B=a"`, fragment is `"normal"`).
    - L3 omission `{concept, template, var_to_omit, axis_label}` —
      `target_id` is `(field, var_token)`;
      `template = stage_json[concept_key][field]` (the resolved
      RESUMEN/TEXTO);
      `var_to_omit = var_token.lstrip("$")` (so `"$N"` →
      `"N"`); `axis_label` is the parameter label whose values
      bind the var (best-effort via the text_variables formula
      walk; empty string if not derivable).
    - L3 reorder `{concept, template, constituents}` — `target_id`
      is the field; `template = stage_json[concept_key][field]`;
      `constituents` is a `"; "`-joined enumeration of the
      `$<letter>` tokens in `template` (e.g., `"$A; $N"`).
    - PD `new_param` `{concept, existing_axes_with_labels,
      allowlist}` — `existing_axes_with_labels = "; ".join(
      f"{key}: {block['label']}" for key, block in
      parameters.items())`; `allowlist = "[]"` (the
      `new_param_allowlist.yaml` loader is still deferred per
      Sprint 14).
  - `def concept_resumen(stage_json, concept_key) -> str` — small
    helper. Returns `stage_json[concept_key]["resumen"]` if present;
    falls back to `stage_json[concept_key]["RESUMEN"]` (uppercase —
    same field, depending on stage); raises `KeyError` if neither.
  - Module-level constants:
    - `_L1_TYPES`, `_L2_TYPES`, `_L3_TYPES`, `_PD_TYPE` — the same
      partitioning Sprint 11 uses; re-imported from
      `synthetic.composition` if available to avoid drift, or
      re-encoded as a sibling constant.

- **C4-prep: rule emitter** — new module
  `src/synthetic/rule_emitter.py`. Public surface:
  - `def emit_rules(payload, modification_type, *, target_id,
    stage_json, concept_key) -> list[dict]` — single dispatch
    entry-point. Returns a list of Phase-B-consumable rule
    dicts (one per `synonyms` / `numerals` entry for L1; one
    per call for L2 / L3 / PD).
  - Per-type private emitters: `_emit_l1` (six types, dispatches
    on `mtype.value` for the rule's `"type"` field),
    `_emit_l2` (three types), `_emit_l3_omission`,
    `_emit_l3_reorder`, `_emit_new_param`. Each emitter knows
    the per-type rule schema and the per-type payload shape;
    the dispatch table is a small `dict[ModificationType,
    Callable]` constant. Returns one rule dict per call for
    L2 / L3 / PD; for L1, returns one per
    `{original, new}` entry in `payload["synonyms"]` (or
    `payload["numerals"]` for `num_to_text`) — each entry
    cross-referenced against the target axis's `values` block
    to derive the per-rule `value` (the value label, e.g.,
    `"a"`).
  - Behaviour on `cross-reference failure` (e.g., the LLM
    returned `{"original": "Stándard"}` with a typo and no
    matching value exists in `parameters[target_id]["values"]`):
    the rule is dropped, and the dropped entry is recorded in a
    sibling `unmatched_payload_entries` list. The list rides
    alongside the returned `rules` via a single
    `EmissionResult` frozen-dataclass return type:
    `EmissionResult(rules: list[dict],
    unmatched: list[dict])`. Drift-handling is intentional —
    no raise, no silent drop. Pinned by a test.
  - For PD `new_param`: emits exactly one rule. The rule's
    `param` key is allocated by `_allocate_axis_key(stage_json,
    concept_key)` — picks the first uppercase letter not in
    the existing `parameters` block (alphabetical scan A-Z;
    raises `ValueError("no_free_axis_letter")` if all 26 are
    taken — a defensive case the BPA catalog can't hit but the
    test pins). The rule's `values` field passes through
    `payload["values"]` verbatim; `var_definition` and
    `template_patch` ride as `metadata.var_definition` /
    `metadata.template_patch` keys (a nested `metadata` dict in
    the rule). The L2/L3 *parsed* shapes (`text_variable`,
    `template_patches`) are **not** emitted — Sprint 16's
    follow-up adds the parser.

- **C4: variant catalog writer** — new module
  `src/synthetic/variant_catalog.py`. Public surface:
  - `@dataclass(frozen=True) class VariantCatalogEntry` — the
    JSON-per-concept payload. Fields:
    - `concept_key: str`
    - `concept_resumen: str`
    - `parent_key: str`
    - `variants: tuple[VariantRecord, ...]` — one record per
      successfully landed variant.
    - `skipped: tuple[Modification, ...]` — per-attempt skip
      records (C2 fallback / C3 schema-validation / unmatched
      payload entries / composition rejections).
    - `provenance: tuple[ProvenanceRecord, ...]` — one entry
      per LLM round-trip (parallel to `variants + skipped` in
      attempt order).
  - `@dataclass(frozen=True) class VariantRecord` —
    `{condition: str, modification_type: ModificationType,
    target_id_repr: str, rules: tuple[dict, ...]}`.
    `condition` is the Phase-D condition label
    (`"single_L1_synonym_label"`, `"stacked_2"`, …); the
    orchestrator pins it. `target_id_repr` is
    `repr(target_id)` for human-readable trace.
  - `@dataclass(frozen=True) class ProvenanceRecord` —
    `{modification_type: ModificationType,
    rendered_prompt: str, raw_responses: tuple[str, ...],
    validated_payload: Optional[dict],
    skipped: Optional[Modification]}`. One per LLM round-trip;
    captures everything Sprint 14's `VariantProposal` returned
    plus the rendered prompt (for diagnostics).
  - `def write_catalog_entry(entry, out_dir) -> Path` — writes
    `out_dir / f"{entry.concept_key}.json"` as UTF-8 JSON
    (indent=2, `ensure_ascii=False`, trailing newline). Atomic
    write: write to `out_dir / f".{concept_key}.json.tmp"`,
    then `os.replace` to the final path. Creates `out_dir`
    if absent (`out_dir.mkdir(parents=True, exist_ok=True)`).
    Returns the final `Path`. Raises `OSError` on disk
    failures (no swallow).
  - `def read_catalog_entry(path) -> VariantCatalogEntry` —
    inverse for tests + downstream consumers. Strict
    `json.load`; rebuilds the frozen dataclasses via the
    `ModificationType` enum coercion + `Modification.from_dict`
    Sprint 01 already exposes.

- **Tests** — three new test files (`tests/synthetic/
  test_slot_extractor.py`, `tests/synthetic/test_rule_emitter.py`,
  `tests/synthetic/test_variant_catalog.py`); ≥40 cases total
  across them. Coverage outlined per-module in §Tasks below.

- **Housekeeping**:
  - Sprint 15 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Three new ✅ rows in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files
    in This Branch" section (`slot_extractor.py`,
    `rule_emitter.py`, `variant_catalog.py`).
  - Flip ❌ → ✅ for the `data/synthetic/variants/` row (now
    `write_catalog_entry` writes there). The directory itself is
    created on-demand; the row's annotation describes the writer.
  - Prepend an "After Sprint 15 — …" entry to the Sprint History
    section.

### Out of scope (explicit)

- **A concrete LLM transport.** Same Sprint 13/14 rationale — A3
  (proposer-model choice) still TBD. Tests use the same
  `_StubLLMClient` pattern.
- **The orchestrator (`src/synthetic/run_synthetic.py`, D2).** Sprint
  15 ships the data-flow primitives the orchestrator will compose;
  the concept-loop driver (and the per-concept condition matrix —
  `single_L1_*`, `stacked_2`, `full_random_mix`, …) is the next
  sprint's work.
- **`new_param` `text_variable` / `template_patches` rule parsing.**
  The PD lift ships the structural fields (`param`, `label`,
  `values`) only; `var_definition` and `template_patch` ride as
  metadata strings, not as parsed-and-anchored rule blocks. Reason:
  the parser needs to handle FIEBDC formula grammar (the same
  grammar `src/utils/z_formula_processing.py` already implements)
  plus a template-anchoring heuristic; both are non-trivial and
  deserve their own sprint. The PD rule the catalog ships is still
  **applicable** by `layer_pd.apply_new_param` (param/label/values
  are the required keys; text_variable/template_patches are
  optional) — Sprint 16 will widen it.
- **`new_param_allowlist.yaml` parsing.** Sprint 15 keeps the
  `allowlist` slot at the placeholder string `"[]"`. The YAML
  reader lands when configs/synthetic/new_param_allowlist.yaml is
  authored (Phase B4 follow-up). The C3 prompt template still
  references the slot; the LLM is asked to use best judgement until
  the allowlist exists.
- **Live LLM calls in pytest.** Identical Sprint 13/14 rationale —
  `_StubLLMClient` and inline payload fixtures only.
- **Composition / stacking the rules.** Sprint 11's
  `composition.compose_rules` is the composer; Sprint 15 does not
  invoke it. The orchestrator (D2, next sprint) calls it on the
  emitted rule batches.
- **Applying the rules to stage JSON.** `layer_*.apply_*` is Phase
  B, already shipped. Sprint 15 only writes the catalog; rule
  application is what the downstream orchestrator does with the
  catalog.
- **`text_variables` formula parser refactor.** The slot extractor
  reads `text_variables[var_key]` and partitions it into
  `(condition, fragment)` pairs via a small ad-hoc regex helper
  (`_parse_l2_formula`). It does **not** import from or modify
  `src/utils/z_formula_processing.py`. The full FIEBDC operator
  grammar is overkill for the L2 slot-extraction case (we only
  need the literal-string-by-condition table). If a Phase-B-style
  parser is needed later, the formula parsing module is the right
  place — not the slot extractor.
- **Updates to `RESEARCH_PROPOSAL.md` or `RESEARCH_PROTOCOL.md`.**
  §3.3, §5 Phase C C4 already cover the deliverable at the framing
  layer; nothing changes there.
- **Changes to existing source modules.** Sprint 15 is additive in
  three new module files + three test files. No edits to
  `variant_proposer.py`, `llm_proposer.py`, `composition.py`, any
  `layer_*.py`, `mutator.py`, `taxonomy.py`, or
  `src/synthetic/prompts/`. Only the two doc files change.

---

## Module surfaces

### 1. `src/synthetic/slot_extractor.py`

```python
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
from .variant_proposer import EXPECTED_SLOTS  # for the round-trip audit


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
        yield from sorted(item.get("parameters", {}).keys())
    elif modification_type in _L2_TYPES:
        for var_key, formula in sorted(item.get("text_variables", {}).items()):
            for condition, _fragment in _parse_l2_formula(formula):
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
        fragment = dict(_parse_l2_formula(formula))[condition]
        return {
            "concept": concept,
            "var_key": var_key,
            "fragment": fragment,
            "condition": condition,
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
    pairs = [(cond.strip(), frag) for frag, cond in _L2_FORMULA_RE.findall(formula)]
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
    the `%<axis>=...` conditions, and returns the first
    axis-label match. Returns `""` if no derivation is possible —
    the omission prompt's `axis_label` slot is informational, not
    load-bearing.
    """
    formula = item.get("text_variables", {}).get(var_to_omit, "")
    match = re.search(r"%([A-Z])\s*=", formula)
    if match is None:
        return ""
    axis = match.group(1)
    return item.get("parameters", {}).get(axis, {}).get("label", "")
```

### 2. `src/synthetic/rule_emitter.py`

```python
"""Payload -> Phase-B rule lift. Bridges Sprint 14's
`VariantProposal.payload` (the validated LLM dict) and the Phase-B
mutators' rule schemas (the dicts `layer_*.apply_*` consume).

Per-type dispatch returns one or more rule dicts plus a sibling
`unmatched` list for LLM payload entries that don't cross-reference
to a known parameter value / variable / field.

Does NOT own:

  * applying the rules — `mutator.apply_*` is Phase B (already shipped);
  * `new_param` `text_variable` / `template_patches` parsing — those
    optional fields stay as raw strings under `metadata.*` in the
    emitted rule; Sprint 16 widens.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Any

from .taxonomy import ModificationType


@dataclass(frozen=True)
class EmissionResult:
    rules: tuple[dict, ...]
    unmatched: tuple[dict, ...]


def emit_rules(
    payload: dict,
    modification_type: ModificationType,
    *,
    target_id: Any,
    stage_json: dict,
    concept_key: str,
) -> EmissionResult:
    if modification_type in _L1_TYPES:
        return _emit_l1(payload, modification_type, target_id, stage_json, concept_key)
    if modification_type in _L2_TYPES:
        return _emit_l2(payload, modification_type, target_id)
    if modification_type is ModificationType.OMISSION:
        return _emit_l3_omission(payload, target_id)
    if modification_type is ModificationType.REORDER:
        return _emit_l3_reorder(payload, target_id)
    if modification_type is ModificationType.NEW_PARAM:
        return _emit_new_param(payload, stage_json, concept_key)
    raise ValueError(f"no_emitter_for_type: {modification_type.value!r}")


# ---- L1 ----------------------------------------------------------------

_L1_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})
_L1_LIST_KEY = {
    ModificationType.SYNONYM_LABEL:    "synonyms",
    ModificationType.NUM_TO_TEXT:      "numerals",
    ModificationType.UNIT_CONVERSION:  "synonyms",
    ModificationType.UNIT_EXPANSION:   "synonyms",
    ModificationType.ABBREV_EXPANSION: "synonyms",
    ModificationType.CODE_EXPANSION:   "synonyms",
}


def _emit_l1(payload, mtype, target_id, stage_json, concept_key):
    param = target_id
    values = stage_json[concept_key]["parameters"][param]["values"]
    by_value = {v["value"]: v["label"] for v in values}
    entries = payload[_L1_LIST_KEY[mtype]]
    rules: list[dict] = []
    unmatched: list[dict] = []
    for entry in entries:
        original = entry["original"]
        if original not in by_value:
            unmatched.append(entry)
            continue
        rules.append({
            "type": mtype.value,
            "param": param,
            "value": by_value[original],
            "original": original,
            "new": entry["new"],
        })
    return EmissionResult(tuple(rules), tuple(unmatched))


# ---- L2 ----------------------------------------------------------------

_L2_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})


def _emit_l2(payload, mtype, target_id):
    var_key, condition = target_id
    rule = {
        "type": mtype.value,
        "var": var_key,
        "condition": condition,
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


# ---- L3 ----------------------------------------------------------------

def _emit_l3_omission(payload, target_id):
    field, _var_token = target_id
    rule = {
        "type": ModificationType.OMISSION.value,
        "field": field,
        "original": payload["original"],
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


def _emit_l3_reorder(payload, target_id):
    field = target_id
    rule = {
        "type": ModificationType.REORDER.value,
        "field": field,
        "original": payload["original"],
        "new": payload["new"],
    }
    return EmissionResult((rule,), ())


# ---- PD ----------------------------------------------------------------

def _emit_new_param(payload, stage_json, concept_key):
    new_letter = _allocate_axis_key(stage_json, concept_key)
    rule = {
        "type": ModificationType.NEW_PARAM.value,
        "param": new_letter,
        "label": payload["new_axis_label"],
        "values": [dict(v) for v in payload["values"]],
        "metadata": {
            "var_definition": payload["var_definition"],
            "template_patch": payload["template_patch"],
        },
    }
    return EmissionResult((rule,), ())


def _allocate_axis_key(stage_json: dict, concept_key: str) -> str:
    used = set(stage_json[concept_key].get("parameters", {}).keys())
    for letter in string.ascii_uppercase:
        if letter not in used:
            return letter
    raise ValueError("no_free_axis_letter")
```

### 3. `src/synthetic/variant_catalog.py`

```python
"""Variant catalog writer (Phase C Task C4).

JSON-per-concept artefacts under `data/synthetic/variants/`. Every
emitted variant carries its full audit trail: the rule(s) that landed,
the `Modification`s that skipped, the LLM provenance per attempt.

Atomic write: `.tmp` rename. Round-trip-safe: `read_catalog_entry`
reverses `write_catalog_entry` exactly (modulo the unordered-dict
caveats `json` already imposes).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional

from .taxonomy import Modification, ModificationType


@dataclass(frozen=True)
class ProvenanceRecord:
    modification_type: ModificationType
    rendered_prompt: str
    raw_responses: tuple[str, ...]
    validated_payload: Optional[dict]
    skipped: Optional[Modification]


@dataclass(frozen=True)
class VariantRecord:
    condition: str
    modification_type: ModificationType
    target_id_repr: str
    rules: tuple[dict, ...]


@dataclass(frozen=True)
class VariantCatalogEntry:
    concept_key: str
    concept_resumen: str
    parent_key: str
    variants: tuple[VariantRecord, ...]
    skipped: tuple[Modification, ...]
    provenance: tuple[ProvenanceRecord, ...]


def write_catalog_entry(entry: VariantCatalogEntry, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{entry.concept_key}.json"
    tmp = out_dir / f".{entry.concept_key}.json.tmp"
    payload = _entry_to_dict(entry)
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, final)
    return final


def read_catalog_entry(path: Path) -> VariantCatalogEntry:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return _entry_from_dict(raw)


# ----- helpers ----------------------------------------------------------

def _entry_to_dict(entry: VariantCatalogEntry) -> dict:
    return {
        "concept_key": entry.concept_key,
        "concept_resumen": entry.concept_resumen,
        "parent_key": entry.parent_key,
        "variants": [_variant_to_dict(v) for v in entry.variants],
        "skipped": [m.to_dict() for m in entry.skipped],
        "provenance": [_provenance_to_dict(p) for p in entry.provenance],
    }


def _variant_to_dict(v: VariantRecord) -> dict:
    return {
        "condition": v.condition,
        "modification_type": v.modification_type.value,
        "target_id_repr": v.target_id_repr,
        "rules": list(v.rules),
    }


def _provenance_to_dict(p: ProvenanceRecord) -> dict:
    return {
        "modification_type": p.modification_type.value,
        "rendered_prompt": p.rendered_prompt,
        "raw_responses": list(p.raw_responses),
        "validated_payload": p.validated_payload,
        "skipped": p.skipped.to_dict() if p.skipped is not None else None,
    }


def _entry_from_dict(d: dict) -> VariantCatalogEntry:
    return VariantCatalogEntry(
        concept_key=d["concept_key"],
        concept_resumen=d["concept_resumen"],
        parent_key=d["parent_key"],
        variants=tuple(_variant_from_dict(v) for v in d["variants"]),
        skipped=tuple(Modification.from_dict(m) for m in d["skipped"]),
        provenance=tuple(_provenance_from_dict(p) for p in d["provenance"]),
    )


def _variant_from_dict(d: dict) -> VariantRecord:
    return VariantRecord(
        condition=d["condition"],
        modification_type=ModificationType(d["modification_type"]),
        target_id_repr=d["target_id_repr"],
        rules=tuple(d["rules"]),
    )


def _provenance_from_dict(d: dict) -> ProvenanceRecord:
    return ProvenanceRecord(
        modification_type=ModificationType(d["modification_type"]),
        rendered_prompt=d["rendered_prompt"],
        raw_responses=tuple(d["raw_responses"]),
        validated_payload=d.get("validated_payload"),
        skipped=Modification.from_dict(d["skipped"]) if d.get("skipped") else None,
    )
```

### Behavioural requirements

1. **`enumerate_targets` is sorted-deterministic.** L1 axes by axis
   key; L2 by `(var_key, condition)` lexicographic; L3 omission by
   `(field, var_token)`; L3 reorder by field. Pinned by tests —
   PYTHONHASHSEED safe.
2. **`extract_slots` returns a dict that `propose_variant` accepts.**
   For every `(stage_json, concept_key, mtype, target_id)` tuple from
   `enumerate_targets`, `set(extract_slots(...).keys()) ==
   EXPECTED_SLOTS[mtype]`. Pinned by a per-type round-trip test that
   builds a slots dict and asserts the key match.
3. **`emit_rules` returns an `EmissionResult` even on empty inputs.**
   Never raises on per-entry cross-reference failure; the unmatched
   entry rides in `EmissionResult.unmatched`. Empty `payload["synonyms"]`
   (which the C3 validator already rejects — but defensive layering
   is cheap) yields `EmissionResult((), ())`.
4. **L1 rule emission cross-references payload `original` against
   the target axis's `value` field.** A `synonym_label` payload
   `{"synonyms": [{"original": "Normal", "new": "Estándar"}]}` against
   a parameters block `{"B": {"values": [{"label": "a", "value":
   "Normal"}]}}` emits rule `{"type": "synonym_label", "param": "B",
   "value": "a", "original": "Normal", "new": "Estándar"}`. An
   `{"original": "Stándard"}` (LLM typo) entry with no match
   appends to `unmatched`. Pinned by a happy + sad test pair.
5. **PD `new_param` rule allocates a free axis letter A-Z.** Skips
   letters already in `parameters`. Raises `ValueError(
   "no_free_axis_letter")` if all 26 are taken — defensive case
   pinned by a 26-axis stress test.
6. **`write_catalog_entry` is atomic.** Writes to a hidden `.tmp`
   sibling, then `os.replace`. If the write or rename fails, the
   final path is either absent or unchanged (no half-written file).
   Pinned by an "interrupted-write" test that mocks `os.replace` to
   raise and asserts the `.tmp` file is the only artifact left.
7. **`write_catalog_entry` + `read_catalog_entry` round-trip
   losslessly.** `read(write(entry)) == entry` for every field
   except dict-key ordering inside `rules` (which `json` doesn't
   preserve — irrelevant for content equality). Pinned by a
   per-type round-trip test.
8. **No module-level side effects.** No env-var reads, no on-import
   I/O, no `out_dir` resolution at import time. Same Sprint 13/14
   convention; pinned by `importlib.reload` tests for all three
   modules.
9. **No new runtime dependencies.** Stdlib + in-repo only. Same
   Sprint 13/14 rationale.
10. **No `text_variables` formula parser drift.** The
    `_parse_l2_formula` regex is intentionally narrow: matches
    `"<literal>" * (<condition>)` clauses and nothing else. If a
    Phase-B mutator's L2 input ever requires richer parsing, the
    work belongs in `src/utils/z_formula_processing.py`, not here.

### Acceptance

- `from synthetic.slot_extractor import enumerate_targets,
  extract_slots, concept_resumen` succeeds.
- `from synthetic.rule_emitter import emit_rules, EmissionResult`
  succeeds.
- `from synthetic.variant_catalog import (VariantCatalogEntry,
  VariantRecord, ProvenanceRecord, write_catalog_entry,
  read_catalog_entry)` succeeds.
- For a fixture concept with one L1-eligible axis: round-trip
  `enumerate_targets -> extract_slots -> propose_variant (stubbed)
  -> emit_rules -> VariantCatalogEntry -> write_catalog_entry ->
  read_catalog_entry` yields an equal entry, and the rule dict
  matches `layer_l1`'s expected schema (i.e., calling
  `apply_synonym_label([rule], stage_json)` does not raise on
  the schema check).
- `pytest tests -q` exits 0 with **≥488 passed, exactly 1 skipped**,
  zero failures.

---

## Tasks

### Task 1 — `src/synthetic/slot_extractor.py`

Create the module per the surface above. Implementation notes:

1. Stage-shape tolerance: read both `"resumen"` (lowercase, the
   pipeline's canonical key) and `"RESUMEN"` (uppercase, the
   BC3 grammar key — present at earlier stages or in fixtures).
   Same for `"texto"` / `"TEXTO"`. The `_field_text` helper
   centralises the case-fold lookup.
2. The L2 formula regex is intentionally narrow. The real
   BC3 grammar permits more (conditional chains, nested
   parens), but the L2 prompt's `{fragment}` and `{condition}`
   slots only need the literal-by-condition partition. If
   `_parse_l2_formula` returns zero pairs, raise — that's a
   catalog-shape error, not a runtime data shape.
3. `_var_axis_label` is best-effort. The omission prompt uses
   the slot informationally; an empty string is acceptable and
   tested.
4. No imports from `src/utils/z_formula_processing.py`.

### Task 2 — `src/synthetic/rule_emitter.py`

Create the module per the surface above. Implementation notes:

1. The L1 cross-reference uses `entry["value"]` (the human-readable
   value, e.g., `"Normal"`) as the lookup key, not
   `entry["label"]` (the per-axis code letter `"a"`). The C3
   payload schema speaks `original`/`new` in human-readable terms;
   the lookup goes through the parameters block's `value` field.
   Pinned by a test.
2. `_allocate_axis_key` scans `string.ascii_uppercase`. The 26-axis
   stress test is defensive only; real BC3 catalogs cap well below.
3. PD rule's `metadata` block carries the raw `var_definition` and
   `template_patch` strings. The rule is still consumable by
   `layer_pd.apply_new_param` because `text_variable` and
   `template_patches` are optional in the PD rule schema. Sprint 16
   will widen the emitter to parse the strings.

### Task 3 — `src/synthetic/variant_catalog.py`

Create the module per the surface above. Implementation notes:

1. `write_catalog_entry` uses `tmp.write_text` + `os.replace` for
   atomicity. `tmp.write_text` overwrites any existing tmp file;
   `os.replace` is atomic on POSIX and best-effort-atomic on Windows
   (`MoveFileExW(MOVEFILE_REPLACE_EXISTING)`).
2. `_entry_to_dict` / `_entry_from_dict` use `Modification.to_dict` /
   `Modification.from_dict` (already shipped by Sprint 01). No
   re-encoding of the `Modification` schema here.
3. `read_catalog_entry` is strict — it raises on malformed JSON
   or missing keys. No best-effort patching. Catalog files are
   produced by our writer; they're trusted.
4. The catalog file name is `{concept_key}.json` — no
   prefix, no `.gz`. The orchestrator picks the directory.

### Task 4 — Tests

Three new test files. Total ≥40 functions across them. Skeletons:

```python
# tests/synthetic/test_slot_extractor.py
from synthetic.slot_extractor import (
    concept_resumen, enumerate_targets, extract_slots,
)
from synthetic.variant_proposer import EXPECTED_SLOTS
from synthetic.taxonomy import ModificationType


_STAGE_JSON_FIXTURE = {
    "OEB020aa": {
        "parent_key": "OEB020$",
        "parameters": {
            "B": {"label": "TIPO DE TERRENO",
                  "values": [{"label": "a", "value": "Normal"},
                             {"label": "b", "value": "Rocoso"}]},
            "D": {"label": "PROFUNDIDAD",
                  "values": [{"label": "a", "value": "Hasta 1 m"},
                             {"label": "b", "value": "Más de 1 m"}]},
        },
        "text_variables": {
            "K": '"normal" * (%B=a) + "rocoso" * (%B=b)',
            "L": '"hasta 1 m" * (%D=a) + "más de 1 m" * (%D=b)',
        },
        "resumen": "Canalización para terreno normal hasta 1 m",
        "texto": "Canalización para terreno $K de profundidad $L, incluso $N por metro",
    },
}
```

Required test cases (≥15 functions in `test_slot_extractor.py`):

1. **`test_module_exposes_public_surface`**
2. **`test_concept_resumen_lowercase_key`** / **uppercase_key** /
   **missing_raises_keyerror**
3. **`test_enumerate_targets_l1_yields_sorted_axis_keys`** —
   parametrised over the six L1 types
4. **`test_enumerate_targets_l2_yields_sorted_var_condition_pairs`**
5. **`test_enumerate_targets_l3_omission_yields_field_var_pairs`**
6. **`test_enumerate_targets_l3_reorder_yields_fields_with_text`**
7. **`test_enumerate_targets_new_param_yields_single_none`**
8. **`test_extract_slots_matches_expected_slots_per_type`** —
   parametrised ×12: build slots, assert
   `set(extract_slots(...).keys()) == EXPECTED_SLOTS[mtype]`. The
   binding round-trip with Sprint 14.
9. **`test_extract_slots_l1_value_list_format`** — value_list is
   `"a: Normal; b: Rocoso"` exactly
10. **`test_extract_slots_l2_fragment_picks_correct_clause`**
11. **`test_extract_slots_omission_axis_label_best_effort`** —
    returns the parameter label for `$N` if the formula binds it;
    returns `""` otherwise
12. **`test_extract_slots_reorder_constituents_format`** — `"$A; $N"`
    style
13. **`test_extract_slots_new_param_allowlist_is_placeholder_for_now`**
14. **`test_parse_l2_formula_unparseable_raises`**
15. **`test_module_has_no_side_effects_at_import`**

Required test cases (≥15 functions in `test_rule_emitter.py`):

1. **`test_module_exposes_public_surface`** (incl. `EmissionResult`)
2. **`test_emit_l1_happy_path_per_type`** — parametrised ×6
3. **`test_emit_l1_emits_one_rule_per_synonyms_entry`** — payload
   with 3 entries yields 3 rules
4. **`test_emit_l1_unmatched_original_rides_in_unmatched_list`** —
   LLM typo case
5. **`test_emit_l1_rule_carries_value_label_not_value_string`** —
   `rule["value"] == "a"` (the label), not `"Normal"`
6. **`test_emit_l2_happy_path_per_type`** — parametrised ×3
7. **`test_emit_l2_rule_carries_var_and_condition`**
8. **`test_emit_l3_omission_rule_shape`**
9. **`test_emit_l3_reorder_rule_shape`**
10. **`test_emit_new_param_allocates_free_axis_letter`** — given
    `parameters={A, B, C}`, yields `"D"`
11. **`test_emit_new_param_raises_when_all_letters_taken`** — 26-axis
    fixture
12. **`test_emit_new_param_metadata_carries_raw_strings`** —
    `var_definition` / `template_patch` ride under `metadata.*`
13. **`test_emit_new_param_values_passes_through`**
14. **`test_emission_result_is_frozen`**
15. **`test_emit_rules_dispatches_per_type_no_raise_on_payload_shape`** —
    ×12 over `ModificationType` with the Sprint-14 fixture payload
16. **`test_module_has_no_side_effects_at_import`**

Required test cases (≥10 functions in `test_variant_catalog.py`):

1. **`test_module_exposes_public_surface`**
2. **`test_write_catalog_entry_creates_file_at_expected_path`**
3. **`test_write_catalog_entry_creates_out_dir_if_missing`**
4. **`test_write_catalog_entry_round_trips_via_read`** — write +
   read returns the same dataclass-equal entry
5. **`test_write_catalog_entry_is_atomic_on_replace_failure`** —
   `monkeypatch.setattr(os, "replace", raise OSError); write
   raises; final path absent; tmp present`
6. **`test_write_catalog_entry_overwrites_existing_file`** — second
   write to the same key replaces the file
7. **`test_catalog_entry_records_modification_type_as_value_string`** —
   on-disk JSON has `"modification_type": "synonym_label"`, not the
   enum repr
8. **`test_provenance_record_carries_skipped_or_payload_not_both`** —
   structural invariant pin
9. **`test_variant_record_carries_rules_as_tuple_in_memory_list_on_disk`** —
   in-memory immutability, on-disk JSON-friendly
10. **`test_dataclasses_are_frozen`** — all three (Entry, Variant,
    Provenance) reject reassignment
11. **`test_read_catalog_entry_strict_on_malformed_json`**
12. **`test_module_has_no_side_effects_at_import`**

Test count: 42 functions, 60–70 cases after parametrisation. Binding
gate: "≥40 listed functions, all green".

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 15 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: the three new
   modules, their public surfaces, the slot-extraction + rule-emission
   + catalog persistence triple, the test-count delta, the explicit
   PD-rule-emission partial-credit (var_definition / template_patch
   ride as metadata; full parse is Sprint 16), and a one-line next-step
   recommendation (Sprint 16 — D2 orchestrator).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Add three new `slot_extractor.py`, `rule_emitter.py`,
     `variant_catalog.py` rows under the `variant_proposer.py` row
     in the "New Files in This Branch" file map; flip each ✅ with
     the appropriate per-module annotation.
   - Flip ❌ → ✅ for the `data/synthetic/variants/` row with the
     annotation "Sprint 15 — Task C4 — `write_catalog_entry` writes
     here; orchestrator (Sprint 16) populates per-concept files".
   - Prepend a new "After Sprint 15 — …" entry to the Sprint History
     section.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md)
   or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). The
   framing already covers Stage A's full pipeline; nothing changes
   at the framing layer.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥488 passed, 1 skipped** (Sprint 12's `new_param`
brace-audit skip is still the only skip). Zero failures. The skip
count must stay at exactly 1 — any new skip is a regression.

End-to-end smoke (PowerShell):

```powershell
$env:PYTHONPATH = "src"
python -c @"
import json, tempfile, pathlib
from synthetic.slot_extractor import enumerate_targets, extract_slots
from synthetic.rule_emitter import emit_rules
from synthetic.variant_catalog import (
    VariantCatalogEntry, VariantRecord, ProvenanceRecord,
    write_catalog_entry, read_catalog_entry,
)
from synthetic.taxonomy import ModificationType

stage = {
    'OEB020aa': {
        'parent_key': 'OEB020$',
        'parameters': {
            'B': {'label': 'TIPO DE TERRENO',
                  'values': [{'label': 'a', 'value': 'Normal'},
                             {'label': 'b', 'value': 'Rocoso'}]},
        },
        'text_variables': {'K': '"normal" * (%B=a) + "rocoso" * (%B=b)'},
        'resumen': 'Canalización para terreno normal',
        'texto':   'Canalización para terreno $K, incluso $N',
    },
}
targets = list(enumerate_targets(stage, 'OEB020aa', ModificationType.SYNONYM_LABEL))
print('targets:', targets)
slots = extract_slots(stage, 'OEB020aa', ModificationType.SYNONYM_LABEL, 'B')
print('slots:', slots)
payload = {'synonyms': [{'original': 'Normal', 'new': 'Estándar'}]}
result = emit_rules(payload, ModificationType.SYNONYM_LABEL,
                    target_id='B', stage_json=stage, concept_key='OEB020aa')
print('rules:', result.rules)
print('unmatched:', result.unmatched)

entry = VariantCatalogEntry(
    concept_key='OEB020aa', concept_resumen=stage['OEB020aa']['resumen'],
    parent_key='OEB020$',
    variants=(VariantRecord(
        condition='single_L1_synonym_label',
        modification_type=ModificationType.SYNONYM_LABEL,
        target_id_repr=repr('B'),
        rules=result.rules,
    ),),
    skipped=(), provenance=(),
)
with tempfile.TemporaryDirectory() as d:
    p = write_catalog_entry(entry, pathlib.Path(d))
    print('wrote:', p)
    back = read_catalog_entry(p)
    print('round-trip ok:', back == entry)
"@
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/slot_extractor.py
new file:   src/synthetic/rule_emitter.py
new file:   src/synthetic/variant_catalog.py
new file:   tests/synthetic/test_slot_extractor.py
new file:   tests/synthetic/test_rule_emitter.py
new file:   tests/synthetic/test_variant_catalog.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_15.md (this file)
```

Nothing under `data/synthetic/variants/` is committed (the directory
gets populated at run time by the orchestrator, not at sprint-build
time). Nothing under `configs/`, no notebooks, no edits to existing
`src/synthetic/` modules besides the two doc files.

---

## Design notes worth committing to memory

- **Three modules, one sprint — they share the per-concept context.**
  Splitting would force a temporary intra-sprint shim. The
  slot extractor produces the dict the rule emitter consumes; the
  rule emitter produces the rules the catalog persists. The boundaries
  are sharp (each module is independently testable) but the
  *information flow* is one-way and tight.
- **`enumerate_targets` + `extract_slots` is the L0/L1 pattern of
  parametrisable rule generation.** Same shape every retrieval-grade
  pipeline ends up with: an enumerator of "what to try" and a
  per-attempt context builder. The orchestrator (D2) just nests
  `for target in enumerate_targets: slots = extract_slots(target);
  proposal = propose_variant(prompt, slots, client, mtype); ...`.
- **`EmissionResult` is the right return type.** A bare `list[dict]`
  would hide the unmatched-payload diagnostic; a raise-on-mismatch
  contract would couple the per-entry-failure handling into the
  caller. The frozen dataclass keeps the caller's path uniform.
- **PD rule emission ships partial credit — `metadata.var_definition`
  and `metadata.template_patch` ride as raw strings.** The full parse
  (FIEBDC formula grammar + template anchor heuristic) is Sprint 16's
  scope. The minimal rule (param/label/values) is still applicable by
  `layer_pd.apply_new_param` — text_variable and template_patches are
  optional in the PD rule schema. The catalog file still records the
  raw LLM strings, so a future re-parse can hydrate the optional
  fields without re-querying the LLM.
- **L1 rule cross-reference uses `value`, not `label`.** The C3 prompt
  speaks in human-readable terms (`Normal`, `Rocoso`); the parameters
  block's `value` field is the matching key, `label` is the per-axis
  code letter (`a`, `b`). The rule emitter does the indirection.
  Test pins this — drift would silently drop every synonym that
  reached the LLM.
- **Atomic catalog writes via tmp + replace.** Defensive against
  interrupted writes (Ctrl-C, OOM, machine reboot mid-write). The
  cost is one extra inode per write; the benefit is "no half-written
  JSON in the catalog directory" — important because the orchestrator
  may run for hours, and a corrupt catalog file would force a re-run.
- **`_parse_l2_formula` regex is narrow by design.** The L2 prompts'
  `{fragment}` and `{condition}` slots only need the
  literal-string-by-condition table. The richer FIEBDC operator
  grammar lives in `src/utils/z_formula_processing.py`, where it
  belongs.
- **`_allocate_axis_key` is alphabetical, not "next-free-after-Z".**
  Picks the first uppercase letter not in the existing axes. Skips
  `parameters` keys only — doesn't inspect text_variables. The 26-axis
  cap is defensive; BC3 catalogs cap well below.
- **No live LLM, no real stage-JSON IO in tests.** All fixtures are
  inline literal dicts. Real-stage-JSON smoke is the orchestrator's
  problem (Sprint 16+) or a Phase F pilot concern.
- **Same Sprint 13/14 no-side-effects-at-import convention.**
  `importlib.reload` pins it per module.
- **The catalog file format is JSON, not Parquet.** Per-concept files
  are small (one concept × handful of variants × per-attempt
  provenance = a few KB); the read side is mostly human-eyeball
  diagnostic, not bulk-analysis. Parquet would optimise the wrong
  axis. If a future sprint needs bulk querying across concepts, the
  natural extension is a `materialize_catalog_to_parquet` aggregator
  function — not a change to the per-concept file format.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch
  context, file map (`slot_extractor.py` / `rule_emitter.py` /
  `variant_catalog.py` rows to be added; `data/synthetic/variants/`
  row to flip ✅).
- [`../RESEARCH_PROPOSAL.md §3.3`](../RESEARCH_PROPOSAL.md) — Stage
  A pipeline framing. §8 lists the four representative LLM prompts;
  the rule emitter's per-type lift is exactly the §8-payload →
  §2.3-rule mapping.
- [`../RESEARCH_PROTOCOL.md §5 Phase C C4`](../RESEARCH_PROTOCOL.md) —
  variant catalog task definition (verbatim quoted in §Context).
- [`SPRINT_14.md`](SPRINT_14.md) — the variant proposer Sprint 15
  consumes. `EXPECTED_SLOTS` is the binding contract the slot
  extractor satisfies; `VariantProposal.payload` is the validated
  dict the rule emitter lifts. Sprint 14's "Out of scope" rationale
  for slot-extraction + payload-to-rule is the predecessor's
  successor commitment.
- [`SPRINT_13.md`](SPRINT_13.md) — the LLM client. Sprint 15 does
  not import from it directly (the catalog stores LLM provenance
  Sprint 14 already captured into `VariantProposal.raw_responses`).
- [`SPRINT_11.md`](SPRINT_11.md) — `composition.compose_rules`. The
  rule emitter's output is the compose input; Sprint 15 emits, the
  orchestrator (Sprint 16) composes.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py)
  — `Modification`, `ModificationType`, `Layer`, `TYPE_TO_LAYER`.
  The catalog writer uses `Modification.to_dict` / `from_dict` for
  on-disk encoding.
- [`../../src/synthetic/variant_proposer.py`](../../src/synthetic/variant_proposer.py)
  — `EXPECTED_SLOTS` (re-imported by slot extractor for round-trip
  audit); `VariantProposal` (consumed by the orchestrator, which
  feeds it into the catalog's provenance records).
- [`../../src/synthetic/layer_l1.py`](../../src/synthetic/layer_l1.py),
  [`layer_l2.py`](../../src/synthetic/layer_l2.py),
  [`layer_l3.py`](../../src/synthetic/layer_l3.py),
  [`layer_pd.py`](../../src/synthetic/layer_pd.py) — the rule
  schemas the emitter targets. Sprint 15 does **not** modify them;
  the emitter is a one-way producer.

---

## Non-goals reminder

If you find yourself opening `src/synthetic/run_synthetic.py` to wire
the concept loop — **stop**. That's Sprint 16 (D2 orchestrator).
Sprint 15 ships the three primitives the orchestrator composes;
composing them is the next sprint's job.

If you find yourself parsing the `var_definition` FIEBDC formula
string into a `text_variable: {var, formula}` rule block — **stop**.
That's Sprint 16+. Sprint 15's PD lift carries the raw string under
`metadata.var_definition`; the minimal rule (`param`, `label`,
`values`) is already applicable by `layer_pd.apply_new_param`.

If you find yourself anchoring the `template_patch` string into the
existing RESUMEN / TEXTO templates — **stop**. Same Sprint 16+
deferral. The raw string rides under `metadata.template_patch`.

If you find yourself authoring or loading
`configs/synthetic/new_param_allowlist.yaml` — **stop**. The slot
stays the placeholder `"[]"` until Phase B4's allowlist YAML is
authored (a separate sprint).

If you find yourself importing
`src/utils/z_formula_processing.py` from the slot extractor —
**stop**. The L2 slot extractor's `_parse_l2_formula` is
intentionally narrow; FIEBDC operator grammar belongs in
`z_formula_processing.py`, not here.

If you find yourself calling `compose_rules` from the rule emitter
— **stop**. Emission and composition are separate concerns; the
orchestrator (D2, Sprint 16) is where they meet.

If you find yourself calling `layer_*.apply_*` from any of the three
new modules — **stop**. Sprint 15 emits rules and writes the
catalog; rule application is the orchestrator's job.

If you find yourself writing a Parquet aggregator for the catalog —
**stop**. The per-concept JSON format is the deliverable. A bulk
aggregator may land later if Phase F bulk analysis needs it; it
doesn't here.

If you find yourself adding logging, telemetry, or metric emission
inside any of the three new modules — **stop**. Same Sprint 13/14
rationale; the modules are pure data-flow.

If you find yourself running a real LLM endpoint inside pytest —
**stop**. Same Sprint 13/14 rationale; all tests use inline payload
fixtures (no `_StubLLMClient` in Sprint 15's tests — the LLM
round-trip is Sprint 14's concern, and Sprint 15 consumes the
already-validated payload directly).

If you find yourself reading real stage JSON off disk inside pytest —
**stop**. All fixtures are inline literal dicts in the test files.
Stage-JSON IO is the orchestrator's problem.
