# Sprint 09 — Phase B Task B3: L3 `template` mutator bodies (`layer_l3.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 09                                                                                          |
| **Date**        | 2026-05-19 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | B3 — see [`../RESEARCH_PROTOCOL.md §5 Phase B`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 08 — `layer_l2.py` + 3 L2 mutator bodies (see [`SPRINT_08.md`](SPRINT_08.md))         |
| **Successor**   | Sprint 10 — Phase B Task B4 (`layer_pd.py` — `new_param` mutator) — TBD                     |

---

## Context

Sprint 08 closed Task B2 by promoting the three L2 `text_variable` stubs to
real bodies in [`src/synthetic/layer_l2.py`](../../src/synthetic/layer_l2.py),
landing at 78/78 pytest pass with a `_replace_fragment` shared worker that
addresses formula fragments by `(var, condition)`. The "one shared private
worker, N thin public wrappers, one `Modification` record per wrapper call,
semantic-blind applier layer" pattern is now fanned across two layers (L1
×6, L2 ×3). Sprint 09 fans it across the final stage-template layer: **L3
`template`** with two types — `omission` and `reorder`.

L3 differs from L1/L2 in three places:

1. **Mutation target.** Stage-4 JSON's `concept["resumen"]` and `concept["texto"]`
   template strings — *not* parameter axes (L1) and *not* text-variable formulas
   (L2). At stage 4 these are still **templates** carrying `$A` / `$B` /
   `$I` / `$L(%A)` placeholders that s05 will resolve to concrete strings
   per item. The L3 worker mutates the template **before** s05 expansion,
   so all `$var` references that survive the mutation continue to render
   downstream.
2. **Addressing scheme.** Rule schema swaps L1's `(param, value)` and L2's
   `(var, condition)` for `(field, original)`. `field` names the template
   (`"RESUMEN"` or `"TEXTO"`, uppercase per the worked example in
   [`../RESEARCH_PROPOSAL.md §2.3`](../RESEARCH_PROPOSAL.md)); `original`
   is the **literal substring** the worker must find and rewrite. The
   string-substring match must be uniquely satisfiable — multiple
   occurrences raise.
3. **Rule's `original` is now load-bearing, not informational.** In L1 the
   rule's `original` was ignored at apply-time (the live `value_entry["value"]`
   was captured); in L2 the rule had no `original` field (the live
   `m.group("frag")` was captured). In L3 the rule's `original` *is* the
   addressing key, so the worker explicitly verifies it occurs once in the
   named template and emits `Modification.original` equal to the matched
   substring (bytewise the same string the rule supplied). The
   "log-`original`-is-authoritative" contract is preserved — if the
   catalog drifts and the substring no longer occurs, the worker raises
   `KeyError`, never silently emits a stale `original`.

The mechanics — find-the-substring, splice-the-replacement — are uniform
across `omission` and `reorder`; the semantic intent (delete a `$var`
reference vs. swap two template constituents) lives in the emitted
`Modification.type`, exactly as in Sprints 07–08's "two wrappers, one
worker" model. For `omission`, the canonical `new` is `""` (empty
deletion); for `reorder`, `new` is the reordered substring. The wrappers
do **not** enforce this divergence — they're identical except for the
type enum. Per-type semantic policing belongs in Phase C (prompts) and
Phase E (reviewer harness).

Sprint 08's pytest baseline: 78 passed (63 surviving Sprint 07 baseline −
3 narrowed-out L2 stub cases + 18 new L2 contract cases). Sprint 09 narrows
the `_STUB_TYPES` parametrisation in
[`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py)
from 3 cases to 1 (only `new_param` survives), and adds the new L3 contract
suite in [`tests/synthetic/test_layer_l3.py`](../../tests/synthetic/test_layer_l3.py).

---

## Scope

### In scope
- **B3** — `src/synthetic/layer_l3.py` (new): two public mutator functions
  `apply_omission`, `apply_reorder`, plus a shared private worker
  `_replace_substring`.
- **Wire-in** to [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):
  import the two new mutators, replace the two `_stub_*` entries in
  `_DISPATCH` for `OMISSION` / `REORDER`, and delete the two obsolete
  `_stub_omission`, `_stub_reorder` function definitions. The dispatcher
  surface (`apply_l1`/`l2`/`l3`/`apply_new_param`) does not change. Update
  the module docstring from "6 L1 + 3 L2 live, 3 still stubs (L3 / PD)" to
  "6 L1 + 3 L2 + 2 L3 live, 1 still stub (PD)".
- **Test narrowing** in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):
  `_STUB_TYPES` shrinks from "TEMPLATE or PARAM_DEFINITION" (3 cases) to
  "PARAM_DEFINITION only" (1 case: `new_param`). The
  `test_deep_copy_purity_on_notimplemented` example rule — currently
  `omission` against `apply_l3` (Sprint 08 swap) — must switch to
  `new_param` against `apply_new_param`.
- **New contract suite** `tests/synthetic/test_layer_l3.py` covering both
  types on a small inline stage-4 fixture mirroring the real `OEB020$`
  shape: happy-path omission and reorder on both `resumen` and `texto`,
  Modification emission with `field` + `original` + `new`, deep-copy
  purity, unique-substring enforcement, and unknown-target errors.
- **Housekeeping**: append Sprint 09 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md);
  flip ❌ → ✅ for `src/synthetic/layer_l3.py` in
  [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); prepend "After Sprint
  09 — …" history entry.

### Out of scope (explicit)
- **B4 / B5** — `layer_pd.py`, `composition.py`. The 1 surviving PD stub
  continues to raise `NotImplementedError`.
- **C1–C4** — no prompts, no LLM client, no variant proposer, no variant
  catalog. Rules carry their `new` substring as a literal string; nothing
  in this sprint *generates* proposed omissions / reorderings.
- **D1 / D2** — no stage-hook wiring into s04/s05, no orchestrator. The
  mutator is exercised via direct unit calls only.
- **`$var`-reference parsing.** The worker treats `$A` / `$I` / `$L(%A)`
  as opaque substring characters. It does **not** parse them, validate
  them, or reason about whether the resulting template still references
  every parameter. A rule that omits `$A` from the template without also
  pruning the `parameters["A"]` axis will produce a template that no
  longer mentions axis A — that's intentional (the proposer's signal that
  axis A is now suppressed in the human-facing description). The
  reviewer harness (Phase E) enforces semantic constraints.
- **Per-type semantic enforcement.** `omission` does not require
  `new == ""`; `reorder` does not require `new != ""` or any structural
  invariant. The wrappers set the `Modification.type` enum and that's the
  only behavioural difference. A rule with `type="omission"` and
  `new="something"` succeeds at apply-time and emits an `omission`
  Modification — semantic policing lives in Phase C prompts (where the
  generator is constrained to emit empty `new` for omission) and Phase E
  review.
- **Cross-template side effects.** A rule's `field` is authoritative; the
  worker touches only the named template (`resumen` or `texto`), never
  the other. A rule that wants to mutate both must be issued as two
  separate rules.
- **Cross-substring side effects within the same template.** If `original`
  occurs twice in the named template, the worker raises `ValueError`
  rather than picking one occurrence. The rule author must supply a
  sufficiently-disambiguating substring (e.g., adding surrounding context
  like `" $I, incluso"` instead of just `"$I"`).
- **Whitespace / punctuation cleanup around omitted `$var`.** The rule
  author is responsible for picking a precise enough `original` that the
  resulting template doesn't have dangling commas, double spaces, or
  orphaned conjunctions. A rule `{"original": "$I", "new": ""}` removes
  just the `$I` token and leaves any surrounding whitespace in place
  bytewise; a rule `{"original": " $I,", "new": ""}` removes the leading
  space and trailing comma too. The worker is a bytewise substring
  replacement engine — it has no opinions about prose hygiene.
- **Composition / stacking constraints.** As in Sprints 07–08, the worker
  overwrites; conflict detection across multiple rules in a batch is
  B5's job. A second rule that targets the same substring after a
  previous rule already rewrote it will raise `KeyError` (the substring
  no longer exists). This is the intentional semantic-blind worker
  contract.
- **Anything under `data/`, `configs/`, `src/utils/`, or any notebook.**
  Tests run against an inline fixture; no disk I/O. No path-refactor
  work, no Generate_OEB changes, no s05 changes.

---

## L3 stage-4 JSON shape (verified against real data)

The L3 worker operates on the concept's `resumen` and `texto` template
strings. The shapes verified in
`data/intermediate/OBRA CIVIL/OBRA CIVIL_stage4.json` for `OEB020aaaaa`
(one leaf of the `OEB020$` group):

```python
{
    "OEB020aaaaa": {
        "parent_key": "OEB020$",
        "ud": "m",
        "concept": "CANALIZACIÓN HORMIGONADA DE TUBO DE PVC 110 mm",
        "text_variables": { ... },   # carried for realism; not read by L3
        "resumen": "Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))\\",
        "texto": "\\Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno y el compactado de la zanja, $P el suministro y el montaje de los tubos y hormigón tipo HE-20 sin vibrar, la prueba de los conductos, el transporte y la retirada de los productos al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: $D Condiciones de ejecución: $F",
        "parameters": { ... },       # carried for realism; not read by L3
    }
}
```

Notes that affect the implementation:

- **Templates are still un-rendered at stage 4.** They contain literal `$A`
  / `$I` / `$L(%A)` references that s05 will substitute. The L3 worker
  treats these as opaque characters — a `$` followed by alphanumerics is
  not parsed; only the literal substring match matters.
- **Field casing.** Stage-4 JSON dict keys are lowercase
  (`concept["resumen"]`, `concept["texto"]`). The proposal's worked
  example (`§2.3`) emits `Modification.field` in **uppercase**
  (`"field": "RESUMEN"`). The rule's `field` field is accepted in either
  case; the worker normalises it to lowercase for the lookup and emits
  `Modification.field` in uppercase, matching the worked-example contract.
- **Templates can have leading/trailing `\\` sentinels.** `resumen` ends
  with `\\`; `texto` starts with `\\`. These are FIEBDC-3 record
  delimiters and must be preserved bytewise. A rule that targets a
  substring near a sentinel must include or exclude it explicitly via
  the `original` substring boundaries.
- **The same substring can appear in both `resumen` and `texto`.** For
  example, `"$A"` appears in both templates above. The `field` field
  disambiguates which template the rule targets; the other template is
  byte-preserved.
- **Free-form prose around `$var` references.** Spanish text, commas,
  spaces, parens, slashes (`/`), and BC3 sentinels (`\\`) all coexist in
  one template. The worker does **not** tokenise or otherwise interpret
  the template — it's bytes in, bytes out.

---

## Tasks

### Task 1 — `src/synthetic/layer_l3.py`: shared worker + two public mutators

Create `src/synthetic/layer_l3.py`. Module surface:

```python
"""L3 `template` mutators — two pure substring-rewrite transformers.

Each public function receives a stage-4 JSON dict (already deep-copied by the
upstream `apply_l3` orchestrator in `mutator.py`), the target `concept_key`,
and a single rule dict naming `(field, original)` and carrying the proposed
`new` substring. The mutator finds the unique occurrence of `original`
inside `stage_json[concept_key][field.lower()]`, overwrites the matched span
with `new`, and returns the dict together with a one-element
`[Modification]` log.
"""

from __future__ import annotations
from .taxonomy import Layer, Modification, ModificationType


def apply_omission(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_reorder(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
```

#### Rule schema (both types)

| Key        | Required | Type | Description                                                                                                                  |
|------------|:--------:|------|------------------------------------------------------------------------------------------------------------------------------|
| `type`     | yes      | str  | One of `"omission"`, `"reorder"`. The dispatcher validates this.                                                              |
| `field`    | yes      | str  | One of `"RESUMEN"` / `"TEXTO"` (canonical, per `RESEARCH_PROPOSAL.md §2.3`). Lowercase variants `"resumen"` / `"texto"` accepted; normalised at the rule boundary. |
| `original` | yes      | str  | Exact substring to find in the named template. Must occur exactly once.                                                       |
| `new`      | yes      | str  | Replacement substring. May be empty `""` for omission. May equal `original` (no-op) — the worker still applies and logs.      |

Unlike L1/L2 the rule's `original` field is **load-bearing** at apply-time:
it is the addressing key. If `original` does not occur in the named template,
the worker raises `KeyError`. If it occurs multiple times, the worker raises
`ValueError`. `Modification.original` is bytewise equal to `rule["original"]`
(by construction — the substring matched verbatim).

#### Internal worker

```python
def _replace_substring(
    stage_json: dict,
    concept_key: str,
    rule: dict,
    mod_type: ModificationType,
) -> tuple[dict, list[Modification]]:
    """Locate (concept, field, original) and rewrite the matching substring."""
```

Behavioural requirements:

1. **Concept lookup.** `concept = stage_json[concept_key]`. If missing, raise
   `KeyError(f"concept_key {concept_key!r} not found in stage_json")`.
2. **Field normalisation.** Accept `rule["field"]` in any case; coerce via
   `field_lower = rule["field"].lower()`. The lookup key must be one of
   `"resumen"` or `"texto"`. If not, raise
   `ValueError(f"field {rule['field']!r} is not 'RESUMEN' or 'TEXTO'")`.
3. **Template lookup.** Require `concept[field_lower]` to be a `str`. If
   missing or not a string, raise
   `KeyError(f"concept {concept_key!r} has no {field_lower!r} template")`.
   Empty-string templates are allowed at the type-check layer but will
   fail the substring lookup with `KeyError` in step 5.
4. **Rule field validation.** `rule["original"]` must be a non-empty string;
   `rule["new"]` must be a string (possibly empty). If either fails, raise
   `ValueError(f"rule for {mod_type.value} requires non-empty 'original' "
   f"and 'new' (string) fields")`. The `new` key being missing entirely
   raises a `ValueError` (not `KeyError`) for symmetry with L1/L2's
   missing-`new` test.
5. **Uniqueness check.** Count occurrences of `rule["original"]` in
   `concept[field_lower]`:
   ```python
   template = concept[field_lower]
   count = template.count(rule["original"])
   ```
   If `count == 0`, raise
   `KeyError(f"original {rule['original']!r} not found in {field_lower!r} "
   f"of concept {concept_key!r}")`.
   If `count > 1`, raise
   `ValueError(f"original {rule['original']!r} matches {count} substrings "
   f"in {field_lower!r} of concept {concept_key!r}; rule author must "
   f"supply a sufficiently-disambiguating substring")`.
6. **In-place rewrite.** With exactly one occurrence, use
   `str.replace(rule["original"], rule["new"], 1)` (the explicit `count=1`
   argument is belt-and-braces — uniqueness was already checked):
   ```python
   new_template = template.replace(rule["original"], rule["new"], 1)
   concept[field_lower] = new_template
   ```
7. **Other template untouched.** Whichever of `resumen` / `texto` was
   **not** named by `field` is bytewise-identical pre and post. Verified by
   a dedicated test (Task 3 #5).
8. **Modification record.** Emit exactly one:
   ```python
   Modification(
       type=mod_type,
       layer=Layer.TEMPLATE,
       field=rule["field"].upper(),    # canonical uppercase, regardless of input case
       original=rule["original"],       # bytewise equal to the matched substring
       new=rule["new"],
       status="applied",
   )
   ```
   `param`, `value`, `var`, `condition`, `reason` stay `None`.

#### Two thin public wrappers

```python
def apply_omission(stage_json, concept_key, rule):
    return _replace_substring(stage_json, concept_key, rule, ModificationType.OMISSION)


def apply_reorder(stage_json, concept_key, rule):
    return _replace_substring(stage_json, concept_key, rule, ModificationType.REORDER)
```

As in Sprints 07–08, mechanics are uniform; the per-type semantics ride on
the `Modification.type` enum.

**Acceptance**

- `from synthetic.layer_l3 import (apply_omission, apply_reorder, _replace_substring)`
  succeeds.
- Each public wrapper's signature is exactly
  `(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]`.
- For a `texto` template containing `" $I, incluso"` and rule
  `{"type":"omission","field":"TEXTO","original":" $I,","new":""}`:
  - Returned `texto` is byte-identical to the original except the matched
    `" $I,"` is removed.
  - Emitted `Modification.field == "TEXTO"`, `.original == " $I,"`,
    `.new == ""`, `.type is ModificationType.OMISSION`,
    `.status == "applied"`, `.layer is Layer.TEMPLATE`.
- For a `texto` template containing `"$A tubos de PVC de 110 mm de diámetro $I"`
  and rule `{"type":"reorder","field":"texto","original":"$A tubos de PVC de 110 mm de diámetro $I","new":"$I, en tubos de PVC de 110 mm de diámetro, $A unidades"}`:
  - The matched span is rewritten verbatim.
  - Emitted `Modification.field == "TEXTO"` (uppercased even though rule
    input was lowercase).
- Rule with `field="resumen"` looks up `concept["resumen"]` (lowercase)
  and emits `Modification.field == "RESUMEN"`.
- A rule whose `original` doesn't occur in the named template raises
  `KeyError` whose message names both the missing substring and the field.
- A rule whose `original` occurs **twice** in the named template raises
  `ValueError` with a message naming the substring, the occurrence count,
  and the field.

---

### Task 2 — Wire the two L3 functions into the dispatcher

Edit [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):

1. Add the import block under the existing `from .layer_l2 import (...)`:
   ```python
   from .layer_l3 import (
       apply_omission,
       apply_reorder,
   )
   ```
2. **Delete** the two `_stub_omission`, `_stub_reorder` function
   definitions.
3. **Replace** the two matching entries in `_DISPATCH`:
   ```python
   _DISPATCH: dict[ModificationType, Callable[[dict, str, dict], _StubResult]] = {
       ModificationType.SYNONYM_LABEL: apply_synonym_label,
       ModificationType.NUM_TO_TEXT: apply_num_to_text,
       ModificationType.UNIT_CONVERSION: apply_unit_conversion,
       ModificationType.UNIT_EXPANSION: apply_unit_expansion,
       ModificationType.ABBREV_EXPANSION: apply_abbrev_expansion,
       ModificationType.CODE_EXPANSION: apply_code_expansion,
       ModificationType.PARAPHRASE: apply_paraphrase,
       ModificationType.EXPANSION: apply_expansion,
       ModificationType.COMPRESSION: apply_compression,
       ModificationType.OMISSION: apply_omission,
       ModificationType.REORDER: apply_reorder,
       ModificationType.NEW_PARAM: _stub_new_param,
   }
   ```
4. **Update the module docstring** from "6 L1 + 3 L2 live, 3 still stubs
   (L3 / PD)" to "6 L1 + 3 L2 + 2 L3 live, 1 still stub (PD —
   `new_param`)". One-line swap; the boundary-stability claim is
   unchanged.
5. **Do not touch** `_apply_rules`, `_resolve_type`, `_gate_layer`,
   `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`, or the
   surviving `_stub_new_param` definition.

**Acceptance**

- `python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER; live = [t for t in ModificationType if TYPE_TO_LAYER[t] is not Layer.PARAM_DEFINITION]; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in live); stubs = [t for t in ModificationType if t not in live]; assert all(_DISPATCH[t].__name__.startswith('_stub_') for t in stubs); assert len(live) == 11 and len(stubs) == 1; print('dispatch audit ok')"` succeeds.
- `python -c "from synthetic.mutator import _stub_omission"` raises
  `ImportError` (the two L3 stubs are physically gone).
- A round-trip through `apply_l3` with one well-formed `omission` rule on
  the stage-4 fixture mutates only the named template; the caller's input
  dict is byte-identical pre/post via `json.dumps(..., sort_keys=True)`.

---

### Task 3 — `tests/synthetic/test_layer_l3.py`: contract suite for the 2 L3 types

Create `tests/synthetic/test_layer_l3.py`. Inline stage-4 fixture mirroring
the real `OEB020aaaaa` shape (verified against
`data/intermediate/OBRA CIVIL/OBRA CIVIL_stage4.json`):

```python
import copy
import json
import pytest

from synthetic.layer_l3 import (
    _replace_substring,
    apply_omission,
    apply_reorder,
)
from synthetic.mutator import apply_l3
from synthetic.taxonomy import Layer, Modification, ModificationType


@pytest.fixture
def oeb020_stage4():
    return {
        "OEB020aaaaa": {
            "parent_key": "OEB020$",
            "ud": "m",
            "concept": "CANALIZACIÓN HORMIGONADA DE TUBO DE PVC 110 mm",
            "text_variables": { ... },   # carried for realism; not read by L3
            "resumen": "Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D)/$J(%F))\\",
            "texto": (
                "\\Canalización hormigonada de $A tubos de PVC de 110 mm "
                "de diámetro $I, incluso $N el relleno y el compactado de "
                "la zanja, $P el suministro y el montaje de los tubos y "
                "hormigón tipo HE-20 sin vibrar, la prueba de los "
                "conductos, el transporte y la retirada de los productos "
                "al lugar de empleo. $M Trabajo: $C Banda de mantenimiento: "
                "$D Condiciones de ejecución: $F"
            ),
            "parameters": { ... },        # carried for realism; not read by L3
        }
    }
```

Required test cases (≥15):

1. **`test_happy_path_omission_on_texto`.** Rule
   `{"type":"omission","field":"TEXTO","original":" $I,","new":""}`. Assert:
   - The returned `texto` no longer contains `" $I,"`.
   - The pre-/post-substitution diff is exactly the deletion of that
     4-character substring (use a direct `pre.replace(" $I,", "", 1) == post` assertion).
   - The `resumen` is bytewise-identical pre and post.
   - Exactly one `Modification` emitted with `type=OMISSION`,
     `layer=TEMPLATE`, `field="TEXTO"`, `original=" $I,"`, `new=""`,
     `status="applied"`.

2. **`test_happy_path_omission_on_resumen`.** Rule
   `{"type":"omission","field":"RESUMEN","original":", $K","new":""}` (or
   another credible target). Symmetric assertions: `resumen` rewritten,
   `texto` bytewise-preserved.

3. **`test_happy_path_reorder_on_texto`.** Rule
   `{"type":"reorder","field":"TEXTO","original":"$A tubos de PVC de 110 mm de diámetro $I","new":"$I, en tubos de PVC de 110 mm de diámetro $A"}`.
   Assert:
   - The original substring is replaced by the reordered one.
   - Adjacent template prose (`"\\Canalización hormigonada de "` before,
     `", incluso $N "` after) is bytewise-preserved — slice-comparison
     check around the rewritten span.
   - Exactly one `Modification` emitted with `type=REORDER`.

4. **`test_happy_path_reorder_on_resumen`.** Symmetric to #3 but on
   `resumen`. The `texto` is bytewise-preserved.

5. **`test_other_template_untouched` (parametrised, 2 cases).** Apply an
   omission or reorder to `RESUMEN`; assert `concept["texto"]` is
   bytewise-identical pre and post (and vice-versa). Drives home the
   cross-template-isolation guarantee.

6. **`test_field_case_normalization` (parametrised, 4 cases).** Apply
   `apply_omission` with `field="TEXTO"`, `"texto"`, `"Texto"`, `"tExTo"`.
   All four produce byte-identical `out` dicts. The emitted
   `Modification.field` is `"TEXTO"` in every case (canonical uppercase).

7. **`test_apply_l3_orchestrator_threads_rules`.** Pass a 2-element batch
   (one `omission`, one `reorder`, each targeting a different substring,
   each on a different template). Assert log is
   `[Modification, Modification]` in submission order, all
   `status="applied"`, and the input dict's pre-call
   `json.dumps(..., sort_keys=True)` matches the post-call snapshot
   (outer `_apply_rules` deep-copy guarantee).

8. **`test_omission_with_empty_new`.** Rule has `new=""`. The matched
   substring is deleted (no replacement), the `Modification.new` is `""`.
   Pins the "omission with empty `new` is allowed" semantic. Verifies the
   `new`-non-empty check applies only at the *key-missing* level, not the
   *empty-string* level.

9. **`test_reorder_with_no_op_new_succeeds`.** Rule has `new == original`.
   The template is unchanged (no-op), but the worker still emits one
   `Modification(status="applied")` with `original == new`. This pins the
   semantic-blind contract — applier does not second-guess the rule.

10. **`test_missing_concept_key_raises`.** Concept key not in
    `stage_json`. Assert `KeyError` whose message names the missing key.

11. **`test_missing_field_template_raises`.** Concept exists but has no
    `"resumen"` key (or value is not a string). Assert `KeyError` whose
    message names the missing field.

12. **`test_unknown_field_raises`.** Rule's `field` is `"DESCRIPCION"` or
    similar bogus value. Assert `ValueError` whose message names the
    invalid field and lists the accepted values (`"RESUMEN"` and
    `"TEXTO"`).

13. **`test_original_not_found_raises`.** Rule's `original` doesn't occur
    in the named template. Assert `KeyError` whose message names both the
    missing substring and the field.

14. **`test_original_matches_multiple_times_raises`.** Use a fixture
    where the rule's `original` substring occurs twice (e.g., `"$A"`
    appears in both early and late positions of the same `texto`).
    Assert `ValueError` whose message names the substring, the
    occurrence count, and the field. The rule author is expected to
    pick a more disambiguating substring.

15. **`test_empty_original_raises`.** Rule's `original` is `""`. Assert
    `ValueError` whose message mentions the `mod_type` and `"original"`.

16. **`test_missing_new_field_raises`.** Rule omits the `"new"` field
    entirely. Assert `ValueError` whose message mentions the `mod_type`
    and `"new"`. Symmetric with L1/L2's missing-`new` test.

17. **`test_modification_original_byte_equals_rule_original`.** The
    `Modification.original` field is **bytewise equal** to `rule["original"]`
    (no normalisation, no trimming). Diverges from L1/L2's
    "rule's `original` is informational; log captures the live value"
    pattern — for L3 the rule's `original` IS the addressing key and the
    matched substring is bytewise the rule's input. Document this in the
    docstring of the test so future readers don't expect L1/L2 semantics.

18. **`test_caller_dict_unchanged_after_apply`.** Snapshot via
    `json.dumps(stage_json, sort_keys=True, ensure_ascii=False)`, call
    `apply_l3` with one well-formed `omission` rule, take a fresh
    snapshot. The two strings are identical.

19. **`test_replace_substring_directly`.** Call `_replace_substring`
    directly (bypassing the wrappers) to verify the worker's correctness
    without going through the dispatcher. Pin the private-worker contract
    in the same way Sprint 07/08 do.

**Acceptance**

- The new file contributes at least 15 test cases. More is fine; less is
  not. (The list above totals 19 — covers parametrisations).
- `pytest tests/synthetic/test_layer_l3.py -q` exits 0 with no skips.

---

### Task 4 — Adjust the existing stub tests in `tests/synthetic/test_mutator.py`

Two surgical edits:

1. **`_STUB_TYPES` shrinks from "TEMPLATE or PARAM_DEFINITION" to
   "PARAM_DEFINITION only".** Replace:
   ```python
   _STUB_TYPES = [
       t for t in ModificationType
       if TYPE_TO_LAYER[t] in (Layer.TEMPLATE, Layer.PARAM_DEFINITION)
   ]
   ```
   with:
   ```python
   _STUB_TYPES = [
       t for t in ModificationType
       if TYPE_TO_LAYER[t] is Layer.PARAM_DEFINITION
   ]
   ```
   This narrows the parametrised stub test from 3 cases to 1
   (`new_param`). After B4 lands, this list becomes empty and the entire
   parametrised test gets deleted.

2. **`test_deep_copy_purity_on_notimplemented` swaps `omission` →
   `new_param`.** Sprint 08 set this to `omission` against `apply_l3`;
   `omission` is now a live mutator. Change the rule's `type` to
   `"new_param"` and the entry-point to `apply_new_param`:
   ```python
   with pytest.raises(NotImplementedError):
       apply_new_param(stage, "OEB020$", {"type": "new_param"})
   ```
   The test's intent — "input dict unchanged even when the dispatched
   mutator raises" — is preserved against the last surviving stub.

**Acceptance**

- `pytest tests/synthetic/test_mutator.py -q` exits 0. The parametrised
  case count for `test_each_stub_raises_notimplemented_with_type_code`
  shrinks from 3 to 1.
- No new external dependencies introduced.

---

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 09 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: files
   created/edited, the test-count delta (78 → expected ~91), the
   dispatcher-table audit result (`11 live + 1 stub`), the L3 rule schema
   decisions (`field`-uppercasing, uniqueness-by-substring, empty-`new`
   allowed for omission, no-op `new == original` allowed for reorder),
   the contract divergence from L1/L2 (rule's `original` is now
   load-bearing, not informational), any deviations from this sprint
   file, and a one-line next-step recommendation (B4 → `layer_pd.py`).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for `src/synthetic/layer_l3.py` in the "New Files in
     This Branch" block, with a one-line annotation matching the Sprint
     07–08 entries' shape (e.g., "✅ Sprint 09 — Task B3 — apply_omission
     / apply_reorder bodies; `_replace_substring` shared worker; 2 stubs
     removed from `mutator.py`; substring-addressed rule schema with
     `field`-case-normalisation and uniqueness-by-substring enforcement").
   - Prepend a new "After Sprint 09 — …" entry to the Sprint History
     section following the Sprint 07–08 template.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md)
   or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Their content
   stands; the protocol's B3 entry simply becomes "done".

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **91 passed** (78 from Sprint 08 − 2 narrowed-out L3 stub cases
+ 15 new L3 contract cases — at minimum). Zero failures, zero skips. The
arithmetic: Sprint 08 ended at 78 with `_STUB_TYPES` parametrising the
stub test over 3 cases; B3 narrows that to 1 (−2 cases), and Task 3 adds
≥15 new tests. Net delta: +13 → 91 minimum. If Task 3 adds the
recommended 19 cases (counting parametrisations), the total is 78 − 2 +
19 = **95**.

> ⚠ **Plan-self-consistency cross-check** (per Sprints 07–08's known
> issue): the verification arithmetic uses the **minimum** new-test count
> (15), not the recommended list count (19 cases including
> parametrisations). The binding gate is "≥15 new L3 contract cases, all
> green, no skips, no regressions in the surviving baseline"; the
> headline pytest number depends on how many test_layer_l3.py cases the
> implementer chooses to write. Update the RESEARCH_LOG entry with the
> actual count.

Smoke checks (PowerShell-friendly one-liners — large quoted strings
should be written to a temp `.py` and run via `python file.py` to avoid
PowerShell single-quote escaping pain, per Sprint 08's lesson):

```powershell
python -c "from synthetic.layer_l3 import apply_omission, apply_reorder, _replace_substring; print('imports ok')"

python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER; live = [t for t in ModificationType if TYPE_TO_LAYER[t] is not Layer.PARAM_DEFINITION]; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in live); stubs = [t for t in ModificationType if t not in live]; assert all(_DISPATCH[t].__name__.startswith('_stub_') for t in stubs); assert len(live) == 11 and len(stubs) == 1; print('dispatch audit ok:', len(live), 'live,', len(stubs), 'still stubs')"
```

End-to-end smoke (write to `_smoke_l3.py` then run):

```python
import json
from synthetic.mutator import apply_l3

s = {
    "OEB020aaaaa": {
        "resumen": "Canalización hormigonada de $A T.",
        "texto": "\\Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro $I, incluso $N el relleno.",
    }
}
snap = json.dumps(s, sort_keys=True, ensure_ascii=False)

out, log = apply_l3(
    s,
    "OEB020aaaaa",
    [{"type": "omission", "field": "TEXTO", "original": " $I,", "new": ""}],
)

assert json.dumps(s, sort_keys=True, ensure_ascii=False) == snap, "caller dict mutated"

expected = "\\Canalización hormigonada de $A tubos de PVC de 110 mm de diámetro incluso $N el relleno."
got = out["OEB020aaaaa"]["texto"]
assert got == expected, got

assert len(log) == 1
assert log[0].field == "TEXTO"
assert log[0].original == " $I,"
assert log[0].new == ""
assert log[0].status == "applied"

print("end-to-end ok")
```

End-of-sprint expected `git status --short` (sprint-scoped subset only):
```
new file:   src/synthetic/layer_l3.py
modified:   src/synthetic/mutator.py
new file:   tests/synthetic/test_layer_l3.py
modified:   tests/synthetic/test_mutator.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_09.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`,
`configs/`, or `docs/synthetic/*.md` (except the two log files) should
appear.

---

## Design notes worth committing to memory

- **Two wrappers, one worker — Sprints 07–08's pattern lands cleanly on
  L3.** `_replace_substring` is the L1 `_replace_value` and L2
  `_replace_fragment` patterns adapted for arbitrary template
  substrings. The wrappers exist purely to set the `Modification.type`
  enum on the emitted record. Per-type semantic enforcement (does this
  "omission" really remove a `$var` and only a `$var`? does this
  "reorder" really change constituent order rather than just modify
  the prose?) lives upstream in Phase C prompts and downstream in
  Phase E review, never inside the applier.
- **Rule's `original` is load-bearing for L3 — and that's a deliberate
  divergence from L1/L2.** In L1 the rule's `original` was ignored
  (informational); in L2 the rule had no `original` field. In L3 the
  rule's `original` IS the addressing key — there is no other
  structural handle to identify which substring to mutate. The
  "log-`original`-is-authoritative" contract is preserved by a
  different mechanism: the worker raises `KeyError` if the substring
  doesn't occur, so a stale rule cannot silently emit an out-of-date
  `original`. The variant catalog drift detection at Phase E review
  remains the safety net.
- **Field-case normalisation lives at the rule boundary, not in the
  data.** Stage-4 JSON dict keys are lowercase (`resumen`, `texto`);
  the proposal's worked example uses uppercase (`"field": "RESUMEN"`).
  The worker accepts either and normalises to lowercase for the
  lookup, then emits `Modification.field` in uppercase. The reasoning:
  the catalog's authors think in screaming-snake-case (matching the
  BC3 `\RESUMEN\` / `\TEXTO\` record-type sentinels), but the JSON
  parser landed on lowercase. The rule schema accommodates the human
  convention; the data lookup uses the machine convention; the log
  pins the canonical proposal form.
- **Uniqueness is by substring, not by regex.** `str.count` and
  `str.replace(original, new, 1)` are the entire matching primitive.
  The worker does **not** interpret `$var` references, does not parse
  the template grammar, and does not normalise whitespace. The rule
  author is responsible for picking an `original` that:
  (a) occurs exactly once, and (b) starts/ends at the right boundary
  (e.g., picking `" $I,"` rather than `"$I"` if the goal is to remove
  the leading space and trailing comma together). This pushes the
  "what should the precise mutation be?" complexity to Phase C
  prompts, where it belongs.
- **Empty-`new` is allowed; no-op `new == original` is allowed.** The
  worker is semantic-blind. An omission rule with `new = ""` deletes
  the matched span; a reorder rule with `new == original` is a no-op
  but still emits a `Modification(status="applied")`. Phase C will
  constrain its proposer to emit empty `new` for `omission` and
  non-trivial reorderings for `reorder` — that's a generation-time
  invariant, not an applier-time invariant.
- **No deep-copy at the worker, same as L1/L2.** The outer
  `_apply_rules` `copy.deepcopy` handles caller purity; the worker
  mutates its received `out` in place. Worker-level deep-copy would
  balloon costs on stacked rules in Phase B5 composition. Caller
  purity is pinned by `test_caller_dict_unchanged_after_apply`.
- **`$var`-reference preservation is the rule author's responsibility,
  not the worker's.** A reorder rule whose `new` accidentally drops a
  `$var` reference will produce a template that no longer renders
  that parameter at s05 time — that's a Phase E review failure, not
  a Phase B applier failure. The applier emits the rewrite as
  specified; the reviewer catches semantic drift.
- **Sprints 07–08's plan-arithmetic note carries over.** The
  verification runbook's expected pytest count uses the minimum
  new-test count (15) as the binding gate; the recommended list count
  (19 cases counting parametrisations) is the headline. The
  RESEARCH_LOG entry should record the actual count, not the planned
  count.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context,
  file map, stage-hook integration note (the L3 entry now becomes live).
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.2 (12-type
  taxonomy table — L3 types are rows 10–11), §2.3 (`Modification` schema
  with the `compression`/`template`/`field=RESUMEN` worked example —
  pins the uppercase convention adopted here).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.3
  (three-layer mutation interface, L3 row), §5 Phase B (B3 task
  definition).
- [`SPRINT_07.md`](SPRINT_07.md) — the L1 template this sprint generalises
  from. The "N wrappers, one worker" pattern, the dispatcher-wiring
  recipe, and the test-narrowing pattern all transfer directly.
- [`SPRINT_08.md`](SPRINT_08.md) — the L2 template adapted for
  formula-fragment addressing. The PowerShell escaping lesson (write
  end-to-end smoke checks to a temp `.py` file) carries forward.
- [`src/s05_evaluate_resumen_texto.ipynb`](../../src/s05_evaluate_resumen_texto.ipynb)
  — the downstream consumer of the mutated stage-4 JSON. Important for
  understanding why the worker must preserve every `$var` reference the
  rule didn't explicitly target: s05's renderer substitutes those
  `$var` references with concrete parameter/text-variable values, and
  any disturbance to a non-targeted `$X` will silently break the
  per-item render.

---

## Non-goals reminder

If you find yourself opening any `.ipynb` file, anything under `data/`,
`configs/`, or `src/utils/`, anything in `src/synthetic/layer_pd.py` /
`composition.py` / `llm_proposer.py` / `prompts/`, or writing Spanish
omission heuristics / reorder rules / `$var`-dependency analysis inside
`layer_l3.py` — **stop**. That's outside Sprint 09. Either the work
belongs to a future sprint (B4+, C1+, D1+) or it should be raised as a
clarifying question in `RESEARCH_LOG.md` before being addressed.

If you find yourself parsing the template into a constituent tree so
that a "reorder" can be expressed structurally (e.g., "swap the third
and fifth `$var` references") — also **stop**. That's a deliberate B3
non-goal; bring it up for a future sprint (B3.5 candidate) before
adding it here. Sprint 09's rule schema is exclusively
`(field, original)`-addressed, with `original` as a literal substring.

If you find yourself implementing per-wrapper validation divergence
(e.g., enforcing `new == ""` inside `apply_omission` but
`new != ""` inside `apply_reorder`) — also **stop**. That's a
deliberate B3 non-goal; the wrappers exist purely to set the
`Modification.type` enum. Per-type semantic enforcement lives
upstream (Phase C generator) and downstream (Phase E reviewer), never
inside the applier.
