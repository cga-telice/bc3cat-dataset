# Sprint 07 — Phase B Task B1: L1 `param_value` mutator bodies (`layer_l1.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 07                                                                                          |
| **Date**        | 2026-05-19 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | B1 — see [`../RESEARCH_PROTOCOL.md §5 Phase B`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 6.5 — s07 sorted iter + Generate_OEB resumen writer (see [`SPRINT_065_REPORT.md`](SPRINT_065_REPORT.md)) |
| **Successor**   | Sprint 08 — Phase B Task B2 (`layer_l2.py` — text-variable mutators) — TBD                 |

---

## Context

Sprint 06 closed Phase A with a 24/24 PASS end-to-end byte-and-content equivalence
gate, and Sprint 6.5 cleaned up the two pre-existing findings (s07 set-iteration
nondeterminism, missing `OEB_resumen.pkl` writer cell). The synthetic foundation —
`taxonomy.py` + the `mutator.py` dispatcher with 12 `NotImplementedError`-raising
stubs — is now demonstrably running on top of a verified-clean main pipeline.

Sprint 07 opens Phase B by promoting the six **L1 `param_value`** stubs in
[`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) to real bodies. All six
share a single mechanical contract — *given a rule that names a target
`(concept_key, param, value_label)` and a proposed replacement string, swap the
`"value"` field of the matching entry in
`stage_json[concept_key]["parameters"][param]["values"]` and emit one
`Modification` record* — and differ only in the semantic intent encoded by the
`type` field. They are explicitly *not* responsible for proposing the new value;
that is the LLM proposer's job in Phase C. Sprint 07 implements the deterministic
applier layer.

The 30 + 12 + 7 + 2 + 3 = 54 pytest baseline (Sprints 01 → 05) survives. New
contract tests for the 6 L1 types extend that baseline; the existing parameterised
"all-12 stubs raise" test in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py)
narrows from 12 types to 6 (L2 + L3 + PD only).

---

## Scope

### In scope
- **B1** — `src/synthetic/layer_l1.py` (new): six public mutator functions
  `apply_synonym_label`, `apply_num_to_text`, `apply_unit_conversion`,
  `apply_unit_expansion`, `apply_abbrev_expansion`, `apply_code_expansion`, plus a
  shared private worker `_replace_value`.
- **Wire-in** to [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py): import the
  six new mutators, replace the six `_stub_*` entries in `_DISPATCH`, and delete the
  six obsolete `_stub_*` function definitions for the L1 layer. The dispatcher
  surface (`apply_l1`/`l2`/`l3`/`apply_new_param`) does not change.
- **Test promotion** in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):
  narrow `test_each_stub_raises_notimplemented_with_type_code` from all 12 types to
  the 6 still-stubbed types (L2 + L3 + PD); switch
  `test_deep_copy_purity_on_notimplemented`'s example rule from `synonym_label`
  (now implemented) to `paraphrase` (still a stub).
- **New contract suite** `tests/synthetic/test_layer_l1.py` covering all 6 types
  on a small inline `OEB020$` fixture: happy-path replacement + Modification
  emission + deep-copy purity + unknown-target errors.
- Housekeeping: append Sprint 07 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md);
  flip ❌ → ✅ for `src/synthetic/layer_l1.py` in
  [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md).

### Out of scope (explicit)
- **B2 / B3 / B4 / B5** — `layer_l2.py`, `layer_l3.py`, `layer_pd.py`,
  `composition.py`. Their stubs continue to raise `NotImplementedError`.
- **C1–C3** — no prompts, no LLM client, no variant proposer. Rules in Sprint 07
  carry their `new` value as a literal string; nothing in this sprint *generates*
  proposed replacements.
- **C4 / D1 / D2** — no variant-catalog reader, no orchestrator, no stage-hook
  wiring into s03. The mutator is exercised via direct unit calls only.
- **Real LLM-proposer dictionaries.** Do **not** ship Spanish number-word tables,
  unit-conversion tables, acronym dictionaries, or any other static reference
  data inside `layer_l1.py`. Each rule is authoritative: it carries the precise
  `new` string the mutator must apply.
- **Bulk per-axis rules.** A rule mutates **one** `(param, value_label)` pair.
  Mutating every value on an axis at once is represented as a *list* of atomic
  rules at the `apply_l1` boundary, not as a single multi-target rule.
- **Cross-concept or cross-axis side effects.** A rule's `param` field is
  authoritative; the mutator must not touch any other axis. The mutator must not
  touch `text_variables`, `resumen`, `texto`, or any other key in the concept
  block. Downstream consumers (s03 expansion + s04 var resolution) consume the
  modified `parameters` block transparently.
- **Anything under `data/synthetic/`, `configs/synthetic/`, or `data/intermediate/`.**
  Tests run against an inline fixture; no disk I/O.
- **Notebooks.** No notebook is touched in this sprint.

---

## Tasks

### Task 1 — `src/synthetic/layer_l1.py`: shared worker + six public mutators

Create `src/synthetic/layer_l1.py`. Module surface:

```python
"""L1 `param_value` mutators — six pure value-replacement transformers.

Each public function receives a stage-2 JSON dict (already deep-copied by the
upstream `apply_l1` orchestrator in `mutator.py`), the target `concept_key`, and
a single rule dict naming `(param, value_label)` and carrying the proposed `new`
string. The mutator overwrites the matching value entry in place and returns
the dict together with a one-element `[Modification]` log.
"""

from __future__ import annotations
from typing import Any
from .taxonomy import Layer, Modification, ModificationType


def apply_synonym_label(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_num_to_text(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_unit_conversion(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_unit_expansion(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_abbrev_expansion(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_code_expansion(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
```

#### Rule schema (all six types)

Every L1 rule is a dict with the following keys. Unknown keys are ignored.

| Key      | Required | Type | Description                                                                  |
|----------|:--------:|------|------------------------------------------------------------------------------|
| `type`   | yes      | str  | One of the six L1 type codes. The dispatcher in `mutator.py` validates this. |
| `param`  | yes      | str  | Axis key inside `stage_json[concept_key]["parameters"]` (e.g., `"B"`).        |
| `value`  | yes      | str  | `label` of the target value entry within that axis (e.g., `"a"`).             |
| `new`    | yes      | str  | The replacement string to write into the value entry's `"value"` field.       |

The mutator never reads `original` from the rule — it reads the current
`"value"` field off the stage JSON itself and writes that into the
`Modification.original` field. This guarantees the log records what actually
got replaced, regardless of whether the caller supplied a stale `original`.

#### Internal worker

```python
def _replace_value(
    stage_json: dict,
    concept_key: str,
    rule: dict,
    mod_type: ModificationType,
) -> tuple[dict, list[Modification]]:
    """Locate (concept, param, value_label) and rewrite its `value` string."""
```

Behavioural requirements:

1. **Concept lookup.** `concept = stage_json[concept_key]`. If the key is missing
   raise `KeyError(f"concept_key {concept_key!r} not found in stage_json")`.
2. **Axis lookup.** `axis = concept["parameters"][rule["param"]]`. If `"parameters"`
   is missing or the axis key is absent raise
   `KeyError(f"param {rule['param']!r} not found on concept {concept_key!r}")`.
3. **Value lookup.** Scan `axis["values"]` for the entry whose `"label"` equals
   `rule["value"]`. If no entry matches raise
   `KeyError(f"value label {rule['value']!r} not found on param {rule['param']!r}")`.
   If multiple entries match (catalog corruption) raise `ValueError` with a
   message naming the duplicates.
4. **Rule field validation.** `rule["new"]` must be present and a non-empty
   string; otherwise raise `ValueError(f"rule for {mod_type.value} requires a non-empty 'new' field")`.
   No coercion (no `str(rule["new"])`, no `.strip()`).
5. **In-place mutation.** Capture the current `value_entry["value"]` into
   `original`, then assign `value_entry["value"] = rule["new"]`. Do not touch any
   other field of `value_entry`, the axis, the concept, or the stage JSON.
6. **Modification record.** Emit exactly one record:
   ```python
   Modification(
       type=mod_type,
       layer=Layer.PARAM_VALUE,
       param=rule["param"],
       value=rule["value"],
       original=original,
       new=rule["new"],
       status="applied",
   )
   ```
   `condition`, `var`, `field`, and `reason` stay `None`.

#### Six thin public wrappers

Each public function calls the worker with the matching `ModificationType` enum
value. Example:

```python
def apply_synonym_label(stage_json, concept_key, rule):
    return _replace_value(stage_json, concept_key, rule, ModificationType.SYNONYM_LABEL)
```

The six wrappers exist purely so that semantics are recorded in the
`Modification.type` field. They are deliberately uniform — the *mechanics* of
all six L1 types are identical at this layer; the *meaning* lives in the
type code, which is what downstream slice analysis reads.

**Acceptance**

- `from synthetic.layer_l1 import (apply_synonym_label, apply_num_to_text,
  apply_unit_conversion, apply_unit_expansion, apply_abbrev_expansion,
  apply_code_expansion, _replace_value)` succeeds.
- Each public wrapper's signature is exactly
  `(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]`.
- Calling any wrapper with a well-formed rule on the `OEB020$` fixture (Task 3)
  returns `(out_dict, [Modification(type=<matching code>, layer=PARAM_VALUE,
  param=..., value=..., original=..., new=..., status="applied")])` and the
  matching `value_entry["value"]` inside `out_dict` is the new string.
- The `Modification.original` field is sourced from the *stage JSON*, never from
  `rule.get("original")` — verified by passing a rule whose `original` field is
  intentionally stale and asserting the log carries the actual original.

---

### Task 2 — Wire the six L1 functions into the dispatcher

Edit [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):

1. Add the import block near the top (under the existing `from .taxonomy import ...`):
   ```python
   from .layer_l1 import (
       apply_synonym_label,
       apply_num_to_text,
       apply_unit_conversion,
       apply_unit_expansion,
       apply_abbrev_expansion,
       apply_code_expansion,
   )
   ```
2. **Delete** the six `_stub_synonym_label`, `_stub_num_to_text`,
   `_stub_unit_conversion`, `_stub_unit_expansion`, `_stub_abbrev_expansion`,
   `_stub_code_expansion` function definitions.
3. **Replace** the six matching entries in `_DISPATCH`:
   ```python
   _DISPATCH: dict[ModificationType, Callable[[dict, str, dict], _StubResult]] = {
       ModificationType.SYNONYM_LABEL: apply_synonym_label,
       ModificationType.NUM_TO_TEXT: apply_num_to_text,
       ModificationType.UNIT_CONVERSION: apply_unit_conversion,
       ModificationType.UNIT_EXPANSION: apply_unit_expansion,
       ModificationType.ABBREV_EXPANSION: apply_abbrev_expansion,
       ModificationType.CODE_EXPANSION: apply_code_expansion,
       ModificationType.PARAPHRASE: _stub_paraphrase,
       ModificationType.EXPANSION: _stub_expansion,
       ModificationType.COMPRESSION: _stub_compression,
       ModificationType.OMISSION: _stub_omission,
       ModificationType.REORDER: _stub_reorder,
       ModificationType.NEW_PARAM: _stub_new_param,
   }
   ```
4. **Do not touch** `_apply_rules`, `_resolve_type`, `_gate_layer`, `apply_l1`,
   `apply_l2`, `apply_l3`, `apply_new_param`, or the surviving 6 stub
   definitions. The outer-level `copy.deepcopy(stage_json)` in `_apply_rules`
   keeps the input-purity guarantee for the caller; the L1 mutators mutate
   their received `out` dict in place, which is legitimate because that dict
   is already a deep copy.

**Acceptance**

- `python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER; assert len(_DISPATCH) == 12 and all(_DISPATCH[t].__name__.startswith('apply_') for t in ModificationType if TYPE_TO_LAYER[t] is Layer.PARAM_VALUE)"`
  succeeds (`apply_*` for L1 entries, `_stub_*` for the other 6).
- `python -c "from synthetic.mutator import _stub_synonym_label"` raises
  `ImportError` (the six L1 stubs are gone).
- A round-trip through `apply_l1` with one well-formed `synonym_label` rule on
  the OEB020 fixture mutates only that single value entry; the caller's
  `stage2_json` dict (the *original*, not the returned `out`) is byte-identical
  pre- and post-call — verified by `json.dumps(..., sort_keys=True)` snapshot.

---

### Task 3 — `tests/synthetic/test_layer_l1.py`: contract suite for the 6 L1 types

Create `tests/synthetic/test_layer_l1.py`. Add to `tests/synthetic/conftest.py`
(or inline at the top of the new test file — implementer's choice) a small
fixture for `OEB020$` covering at least three distinct axes so all 6 mutator
flavours have a credible target:

```python
import pytest

@pytest.fixture
def oeb020_stage2():
    return {
        "OEB020$": {
            "concept": "CANALIZACIÓN HORMIGONADA",
            "parameters": {
                "A": {  # Nº TUBOS — num_to_text targets
                    "label": "Nº TUBOS",
                    "values": [
                        {"label": "a", "value": "1"},
                        {"label": "b", "value": "2"},
                        {"label": "c", "value": "3"},
                    ],
                },
                "B": {  # TIPO DE TERRENO — synonym_label targets
                    "label": "TIPO DE TERRENO",
                    "values": [
                        {"label": "a", "value": "Normal"},
                        {"label": "b", "value": "Bajo vías"},
                        {"label": "c", "value": "Rocoso"},
                    ],
                },
                "C": {  # DIÁMETRO — unit_conversion / unit_expansion targets
                    "label": "DIÁMETRO",
                    "values": [
                        {"label": "a", "value": "110 mm"},
                        {"label": "b", "value": "160 mm"},
                    ],
                },
                "D": {  # MATERIAL — abbrev_expansion targets
                    "label": "MATERIAL",
                    "values": [
                        {"label": "a", "value": "PVC"},
                        {"label": "b", "value": "PEAD"},
                    ],
                },
                "E": {  # CALIDAD HORMIGÓN — code_expansion targets
                    "label": "CALIDAD HORMIGÓN",
                    "values": [
                        {"label": "a", "value": "HE-20"},
                        {"label": "b", "value": "HE-25"},
                    ],
                },
            },
            "text_variables": {},
            "resumen": "PLACEHOLDER",
            "texto": "PLACEHOLDER",
        }
    }
```

Required test cases (one parametrised module covering all 6 types is encouraged,
plus per-type focused cases):

1. **`test_happy_path_per_type` (parametrised, 6 cases).** For each of the 6
   types, call its public wrapper directly with a credible rule:
   - `synonym_label` on `(B, a)` → `"Estándar"`
   - `num_to_text` on `(A, b)` → `"dos"`
   - `unit_conversion` on `(C, a)` → `"11 cm"`
   - `unit_expansion` on `(C, b)` → `"160 milímetros"`
   - `abbrev_expansion` on `(D, a)` → `"policloruro de vinilo"`
   - `code_expansion` on `(E, a)` → `"hormigón estructural tipo 20"`

   Assert: returned `out["OEB020$"]["parameters"][param]["values"]` has exactly
   the same length as the fixture; the targeted value entry's `"value"` field
   is the new string; all sibling value entries are unchanged; exactly one
   `Modification` is returned with the right `type`, `layer=PARAM_VALUE`,
   `param`, `value`, `original`, `new`, and `status="applied"`.

2. **`test_apply_l1_orchestrator_threads_rules`.** Pass the fixture, the
   concept key `"OEB020$"`, and a 3-element rules list mixing types (e.g.,
   one `synonym_label`, one `num_to_text`, one `unit_conversion`). Assert
   that the returned log is `[Modification, Modification, Modification]` in
   submission order, and that the input dict is byte-identical to its
   pre-call state (the outer `_apply_rules` deep-copy guarantee).

3. **`test_modification_original_sourced_from_stage_json`.** Build a rule
   whose `original` field is `"WRONG"` (stale) and call the mutator. Assert
   `Modification.original == "Normal"` (the actual stage value), not
   `"WRONG"`. The rule's `original` is informational only; the log
   authoritatively comes from what was actually replaced.

4. **`test_missing_concept_key_raises`.** Rule names a `concept_key` not in
   `stage_json`. Assert `KeyError` whose message names the missing key.

5. **`test_missing_param_raises`.** Rule names a `param` not in
   `concept["parameters"]`. Assert `KeyError` whose message names the missing
   param.

6. **`test_missing_value_label_raises`.** Rule names a `value` label not present
   on the target axis. Assert `KeyError` whose message names the missing label.

7. **`test_empty_new_raises`.** Rule's `"new"` is `""` (or missing). Assert
   `ValueError` whose message mentions the `mod_type` and `"new"`.

8. **`test_caller_dict_unchanged_after_apply`.** Take a snapshot via
   `json.dumps(stage_json, sort_keys=True)`, call `apply_l1` with one
   well-formed `synonym_label` rule, take a fresh snapshot. The two strings
   are identical. The mutation lives entirely on the returned `out` dict.

**Acceptance**

- The new file contributes at least 13 test cases (6 parametrised happy-path +
  1 orchestrator + 1 stale-original + 3 missing-target + 1 empty-new + 1
  caller-purity). More is fine; less is not.
- `pytest tests/synthetic/test_layer_l1.py -q` exits 0 with no skips.

---

### Task 4 — Adjust the existing stub tests in `tests/synthetic/test_mutator.py`

Two surgical edits:

1. **`test_each_stub_raises_notimplemented_with_type_code`.** Narrow the
   parametrisation from `list(ModificationType)` to the surviving 6
   still-stubbed types. Cleanest expression:
   ```python
   from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER

   _STUB_TYPES = [
       t for t in ModificationType
       if TYPE_TO_LAYER[t] is not Layer.PARAM_VALUE
   ]

   @pytest.mark.parametrize("mtype", _STUB_TYPES)
   def test_each_stub_raises_notimplemented_with_type_code(mtype):
       ...
   ```
   The 6 promoted L1 types are now covered by Task 3's happy-path suite. After
   B2 and B3 land, the next sprint(s) narrow this list further; after B4 it
   becomes empty and the test gets deleted entirely.

2. **`test_deep_copy_purity_on_notimplemented`.** Switch the example rule's
   `type` from `"synonym_label"` (now a successful L1 mutator) to
   `"paraphrase"` (still a stub). Stage JSON unchanged otherwise. The test's
   intent — "input dict is unchanged even when the dispatched mutator
   raises" — still holds against the surviving stubs.

**Acceptance**

- `pytest tests/synthetic/test_mutator.py -q` exits 0. Test count for that
  file: 12 baseline → 12 (`test_each_stub_raises_notimplemented_with_type_code`
  shrinks from 12 parametrised cases to 6; the other tests are unchanged
  except for the single-line rule-type swap in `test_deep_copy_purity_*`).
- No new external dependencies introduced.

---

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 07 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: files created/edited, the
   test-count delta (54 → expected ~67), the dispatcher-table audit result,
   any deviations from this sprint file, and a one-line next-step
   recommendation.
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for `src/synthetic/layer_l1.py` in the "New Files in This
     Branch" block, with a one-line annotation matching the existing entries
     (e.g., "✅ Sprint 07 — Task B1 — apply_synonym_label / num_to_text /
     unit_conversion / unit_expansion / abbrev_expansion / code_expansion
     bodies; `_replace_value` shared worker; 6 stubs removed from
     `mutator.py`").
   - Prepend a new "After Sprint 07 — …" entry to the Sprint History section
     following the existing template.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Their content
   stands; the protocol's B1 entry simply becomes "done".

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: at least **67 passed** (54 baseline + 13 new L1 contract cases),
zero failures, zero skips. The 6 NotImplementedError cases that previously
covered L1 types are subsumed by the new happy-path suite, so the net delta
is exactly the count of new tests added in Task 3.

Smoke checks (PowerShell-friendly one-liners):

```powershell
python -c "from synthetic.layer_l1 import apply_synonym_label, apply_num_to_text, apply_unit_conversion, apply_unit_expansion, apply_abbrev_expansion, apply_code_expansion, _replace_value; print('imports ok')"

python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER; l1 = [t for t in ModificationType if TYPE_TO_LAYER[t] is Layer.PARAM_VALUE]; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in l1); other = [t for t in ModificationType if t not in l1]; assert all(_DISPATCH[t].__name__.startswith('_stub_') for t in other); print('dispatch audit ok:', len(l1), 'L1 live,', len(other), 'still stubs')"

python -c "import json; from synthetic.mutator import apply_l1; s = {'OEB020$': {'parameters': {'B': {'label': 'TIPO DE TERRENO', 'values': [{'label':'a','value':'Normal'},{'label':'b','value':'Bajo vías'}]}}}}; snap = json.dumps(s, sort_keys=True); out, log = apply_l1(s, 'OEB020$', [{'type':'synonym_label','param':'B','value':'a','new':'Estándar'}]); assert json.dumps(s, sort_keys=True) == snap; assert out['OEB020$']['parameters']['B']['values'][0]['value'] == 'Estándar'; assert len(log) == 1 and log[0].original == 'Normal' and log[0].new == 'Estándar' and log[0].status == 'applied'; print('end-to-end ok')"
```

End-of-sprint expected `git status --short`:
```
new file:   src/synthetic/layer_l1.py
modified:   src/synthetic/mutator.py
new file:   tests/synthetic/test_layer_l1.py
modified:   tests/synthetic/test_mutator.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_07.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks under `src/`, nothing under `data/`,
`configs/`, or `docs/synthetic/*.md` (except the two log files) should appear.

---

## Design notes worth committing to memory

- **Six wrappers, one worker.** Identical mechanics across the six L1 types is
  not a code smell — it is a deliberate design statement that the *mechanism*
  is value-replacement and the *meaning* lives in the type code. Per-type
  semantic enforcement belongs upstream (in the LLM-proposer's prompt library,
  Phase C) and downstream (in the validation reviewer harness, Phase E). The
  applier is intentionally semantic-blind.
- **Rule's `original` is informational, log's `original` is authoritative.**
  Stage 07 enforces this asymmetry via `test_modification_original_sourced_from_stage_json`.
  Reason: the variant catalog (Phase C) may be reused across pipeline reruns
  where the underlying stage-2 JSON has shifted, and we want the log to record
  what *actually* changed at apply-time, not what the catalog *expected* to
  change. If a catalog entry's `original` no longer matches the live stage
  value, the right escalation is in Phase E (reviewer harness flags drift),
  not silent agreement.
- **Outer-level deep-copy stays at `_apply_rules`, not inside the worker.**
  The current architecture deep-copies once at the `apply_l1` entry point and
  threads the same `out` dict through every rule in the list. Worker-level
  deep-copy would balloon costs on stacked rules (Phase B5 composition) and
  is unnecessary for caller-side purity (already guaranteed by the outer
  copy). Sprint 07 does not change this contract.
- **Unstackable-combo handling deferred to B5.** This sprint's mutators do
  not check whether a target value has *already* been rewritten by an earlier
  rule in the same batch — they just overwrite. The composition layer (B5)
  will enforce stacking constraints by either reordering rules, skipping
  conflicts (with a `status="skipped"` Modification + `reason`), or rejecting
  the batch up-front. Per-mutator pre-checks would couple unrelated layers.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file map,
  stage-hook integration note.
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.2 (12-type taxonomy
  table — L1 types are the first 6 rows), §2.3 (`Modification` schema +
  worked example).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.3 (three-layer
  mutation interface), §5 Phase B (B1 task definition), §8.1 (representative
  `synonym_label` prompt — informs Phase C, *not* this sprint).
- [`SPRINT_01.md`](SPRINT_01.md) — taxonomy + harness skeleton, contains the
  shape this sprint is promoting from stub to real.
- [`SPRINT_06_REPORT.md`](SPRINT_06_REPORT.md) and [`SPRINT_065_REPORT.md`](SPRINT_065_REPORT.md)
  — verification baseline for the foundation Sprint 07 builds on.

---

## Non-goals reminder

If you find yourself opening any `.ipynb` file, anything under `data/`,
`configs/`, or `src/utils/`, anything in `src/synthetic/layer_l2.py` /
`layer_l3.py` / `layer_pd.py` / `composition.py` / `llm_proposer.py` /
`prompts/`, or writing Spanish unit-conversion tables / number-word
dictionaries / acronym lookups inside `layer_l1.py` — **stop**. That's
outside Sprint 07. Either the work belongs to a future sprint (B2+, C1+,
D1+) or it should be raised as a clarifying question in `RESEARCH_LOG.md`
before being addressed.
