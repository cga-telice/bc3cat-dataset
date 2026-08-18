# Sprint 08 — Phase B Task B2: L2 `text_variable` mutator bodies (`layer_l2.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 08                                                                                          |
| **Date**        | 2026-05-19 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | B2 — see [`../RESEARCH_PROTOCOL.md §5 Phase B`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 07 — `layer_l1.py` + 6 L1 mutator bodies (see [`SPRINT_07.md`](SPRINT_07.md))         |
| **Successor**   | Sprint 09 — Phase B Task B3 (`layer_l3.py` — template mutators) — TBD                       |

---

## Context

Sprint 07 closed Task B1 by promoting the six L1 `param_value` stubs to real
bodies in [`src/synthetic/layer_l1.py`](../../src/synthetic/layer_l1.py),
landing at 63/63 pytest pass on a verified-clean main pipeline. The mechanical
contract — *one shared private worker, N thin public wrappers, one `Modification`
record per wrapper call, semantic-blind applier layer* — generalises directly to
L2. Sprint 08 fans the same pattern across the three **text_variable** types:
`paraphrase`, `expansion`, `compression`.

L2 differs from L1 in three places:

1. **Mutation target.** Stage-3 JSON's `text_variables[var_key]`, not stage-2's
   `parameters[axis_key]["values"]`. Where L1 overwrote a `value_entry["value"]`
   string, L2 rewrites one *quoted fragment* inside a BC3 formula like
   `'"normal" * (%B=="a") + "bajo vías" * (%B=="b") + ...'`.
2. **Addressing scheme.** Rule schema swaps `(param, value)` for
   `(var, condition)`. The condition is the literal BC3 selector that paired
   with the fragment (`%B=="a"`), and the mutator finds the fragment by
   matching `"FRAG" * (CONDITION)` against the formula text.
3. **Container polymorphism.** A `text_variables` entry can be either a `str`
   (single formula like `'K'` / `'I'` / `'N'`) or a `list[str]` where each
   element is itself a `"FRAG" * (CONDITION)` expression (like `'P'`). Pure
   lookup-table list entries — `['"Diurno"', '"Nocturno"', ...]` with no
   `* (condition)` segment, e.g. `'G'`, `'H'`, `'J'`, `'E'` — are **out of
   scope** for B2; they have no condition-keyed handle and require an
   `index`-addressed rule shape that B2 deliberately does not introduce.

The mechanics — find-by-condition, capture-the-fragment, write-the-new — are
identical across the three types; the semantic intent (paraphrase / expand /
compress) lives in the emitted `Modification.type`, exactly as in Sprint 07's
"three wrappers, one worker" model.

Sprint 07's pytest baseline: 63 passed (48 surviving Sprints 01–05 baseline +
15 new L1 contract cases). Sprint 08 narrows the `_STUB_TYPES` parametrisation
in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py)
from 6 cases to 3 (the surviving L3 + PD types), and adds the new L2 contract
suite in [`tests/synthetic/test_layer_l2.py`](../../tests/synthetic/test_layer_l2.py).

---

## Scope

### In scope
- **B2** — `src/synthetic/layer_l2.py` (new): three public mutator functions
  `apply_paraphrase`, `apply_expansion`, `apply_compression`, plus a shared
  private worker `_replace_fragment`.
- **Wire-in** to [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):
  import the three new mutators, replace the three `_stub_*` entries in
  `_DISPATCH` for `PARAPHRASE` / `EXPANSION` / `COMPRESSION`, and delete the
  three obsolete `_stub_paraphrase`, `_stub_expansion`, `_stub_compression`
  function definitions. The dispatcher surface
  (`apply_l1`/`l2`/`l3`/`apply_new_param`) does not change. Update the module
  docstring from "6 L1 live, 6 still stubs" to "6 L1 + 3 L2 live, 3 still
  stubs".
- **Test narrowing** in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):
  `_STUB_TYPES` shrinks from "non-PARAM_VALUE" (6 cases) to "TEMPLATE or
  PARAM_DEFINITION" (3 cases: `omission`, `reorder`, `new_param`). The
  `test_deep_copy_purity_on_notimplemented` example rule — currently
  `paraphrase` (Sprint 07 swap) — must switch to a surviving stub
  (e.g., `omission` against `apply_l3`).
- **New contract suite** `tests/synthetic/test_layer_l2.py` covering all 3
  types on a small inline stage-3 fixture for `OEB020$` (using the real
  observed shape of `text_variables['K']` / `['I']` / `['P']`): happy-path
  fragment replacement on both str-typed and list-typed entries, Modification
  emission with `var` + `condition` + `original` + `new`, deep-copy purity,
  and unknown-target errors. Plus the explicit "lookup-table list raises"
  case for pure non-conditional list entries.
- **Housekeeping**: append Sprint 08 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md);
  flip ❌ → ✅ for `src/synthetic/layer_l2.py` in
  [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); prepend "After Sprint
  08 — …" history entry.

### Out of scope (explicit)
- **B3 / B4 / B5** — `layer_l3.py`, `layer_pd.py`, `composition.py`. The
  3 surviving stubs continue to raise `NotImplementedError`.
- **C1–C4** — no prompts, no LLM client, no variant proposer, no variant
  catalog. Rules carry their `new` fragment as a literal string; nothing in
  this sprint *generates* proposed paraphrases / expansions / compressions.
- **D1 / D2** — no stage-hook wiring into s04, no orchestrator. The
  mutator is exercised via direct unit calls only.
- **No Spanish reference data inside `layer_l2.py`.** No paraphrase
  dictionaries, no expansion templates, no compression rules. Each rule is
  authoritative — it carries the precise `new` fragment string.
- **Pure lookup-table list entries** (e.g., `text_variables['G']` =
  `['"Diurno"', '"Nocturno"', ...]`). These have no `* (CONDITION)` segment
  to address by condition. A rule that targets such a var must
  `raise ValueError` with a message that names the var and explains the
  shape mismatch. An `index`-addressed rule shape (`{"var": "G",
  "index": 0, "new": "..."}`) is **explicitly deferred** — neither
  implemented nor accepted — to keep B2's rule schema uniform with
  `(var, condition)`.
- **Cross-variable side effects.** A rule's `var` field is authoritative;
  the mutator must not touch any other entry in `text_variables`, nor
  `parameters`, `resumen`, `texto`, or any other key in the concept block.
- **Cross-fragment side effects within the same var.** Even if the formula
  contains the same literal fragment text under two different conditions
  (`"normal" * (%B=="a") + "normal" * (%B=="x")`), the mutator must rewrite
  **only** the fragment whose condition matches `rule["condition"]`. Other
  fragments are bytewise-preserved.
- **Composition / stacking constraints.** As in Sprint 07, the worker
  overwrites; conflict detection across multiple rules in a batch is B5's
  job. A second rule that targets the same `(var, condition)` after a
  previous rule already rewrote it will succeed and overwrite — and the
  log's `original` will be the *intermediate* value from the previous rule's
  write, not the pre-batch fragment. This is the intentional semantic-blind
  worker contract.
- **Anything under `data/`, `configs/`, `src/utils/`, or any notebook.**
  Tests run against an inline fixture; no disk I/O. No path-refactor work,
  no Generate_OEB changes, no s04 changes.

---

## L2 stage-3 JSON shape (verified against real data)

The L2 worker operates on the concept's `text_variables` block. Two shapes
appear in `data/intermediate/OBRA CIVIL/OBRA CIVIL.json` for `OEB020$`:

```python
"text_variables": {
    # str-typed formula (the common case — see 'K', 'I', 'N' in OEB020$)
    "K": '"normal" * (%B=="a") + "bajo vías" * (%B=="b") + '
         '"rocoso" * (%B=="c") + "en cruce de carretera" * (%B=="d") + ...',
    "I": '"en cualquier clase de terreno, excepto roca" * (%B=="a") + '
         '"en cruce bajo vías" * (%B=="b") + ...',
    "N": '"el descerne y la entibación..." * (%B=="b"  or  %B=="g") + '
         '"la demolición de roca dura," * (%B=="c") + ...',

    # list-typed with conditional fragments (the rarer case — see 'P' in OEB020$)
    "P": ['"la preparación y nivelación de la solera, ..." * (%B=="f")'],

    # list-typed pure lookup table — OUT OF SCOPE for B2
    "G": ['"Diurno"', '"Nocturno"', '"Diurno Excepcional"',
          '"Nocturno Excepcional"', '"Cualquier franja horaria"',
          '"Cualquier franja horaria excepcional"'],
}
```

Notes that affect the implementation:

- **Keys carry no `$` prefix.** The `$` appears only as the reference syntax
  in formulas (`$K`, `$I`). Dict keys are bare (`'K'`, `'I'`, `'N'`). The
  rule's `var` field MUST accept either form; the mutator strips a leading
  `'$'` if present before looking the key up.
- **Conditions use `==`, not `=`.** The proposal's worked example shows
  `(%B=a)` schematically; real BC3 stage-2/stage-3 data has `(%B=="a")`. The
  rule's `condition` field MUST be supplied in the **exact form that appears
  in the formula**, with the surrounding parentheses **NOT** included
  (those are part of the formula's syntactic frame).
- **Compound conditions exist.** Variable `'N'` shows
  `(%B=="b"  or  %B=="g")` — two equality clauses joined by `or` with
  irregular whitespace. The rule's `condition` field carries the **literal
  inner string** between the parentheses, preserving the catalog's
  whitespace. The mutator collapses runs of whitespace before regex
  comparison to be robust against single-space-vs-double-space drift.
- **Fragments are quoted with `"`.** No escaped quotes inside any fragment
  in the OEB020 sample. B2 may assume fragments do not contain literal `"`
  characters; a future sprint adds escape-aware handling if a catalog item
  ever requires it.

---

## Tasks

### Task 1 — `src/synthetic/layer_l2.py`: shared worker + three public mutators

Create `src/synthetic/layer_l2.py`. Module surface:

```python
"""L2 `text_variable` mutators — three pure fragment-replacement transformers.

Each public function receives a stage-3 JSON dict (already deep-copied by the
upstream `apply_l2` orchestrator in `mutator.py`), the target `concept_key`,
and a single rule dict naming `(var, condition)` and carrying the proposed
`new` fragment string. The mutator finds the matching `"FRAG" * (CONDITION)`
segment inside `stage_json[concept_key]["text_variables"][var]`, overwrites
the quoted fragment, and returns the dict together with a one-element
`[Modification]` log.
"""

from __future__ import annotations
import re
from typing import Any
from .taxonomy import Layer, Modification, ModificationType


def apply_paraphrase(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_expansion(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
def apply_compression(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]: ...
```

#### Rule schema (all three types)

| Key         | Required | Type | Description                                                                                          |
|-------------|:--------:|------|------------------------------------------------------------------------------------------------------|
| `type`      | yes      | str  | One of `"paraphrase"`, `"expansion"`, `"compression"`. The dispatcher validates this.                |
| `var`       | yes      | str  | Key inside `stage_json[concept_key]["text_variables"]`. Leading `$` is stripped: `"$I"` → `"I"`.     |
| `condition` | yes      | str  | The BC3 condition between the parentheses, e.g. `'%B=="a"'`. Whitespace-normalized at match time.    |
| `new`       | yes      | str  | The replacement fragment string. Supplied **without** surrounding `"` quotes; the worker adds them.  |

The worker never reads `original` from the rule. As in L1 it captures
`Modification.original` from the live fragment it overwrites. This pins the
"rule's `original` is informational; log's `original` is authoritative"
contract — verified by an explicit test (Task 3 #4).

#### Internal worker

```python
def _replace_fragment(
    stage_json: dict,
    concept_key: str,
    rule: dict,
    mod_type: ModificationType,
) -> tuple[dict, list[Modification]]:
    """Locate (concept, var, condition) and rewrite the matching fragment."""
```

Behavioural requirements:

1. **Concept lookup.** `concept = stage_json[concept_key]`. If missing, raise
   `KeyError(f"concept_key {concept_key!r} not found in stage_json")`.
2. **`text_variables` lookup.** Require `concept["text_variables"]` to be a
   `dict`; if missing, raise
   `KeyError(f"concept {concept_key!r} has no text_variables block")`.
3. **Var normalization.** Strip a single leading `'$'` from `rule["var"]` if
   present: `var_key = rule["var"][1:] if rule["var"].startswith("$") else rule["var"]`.
   Look up `entry = concept["text_variables"][var_key]`. Missing → raise
   `KeyError(f"var {var_key!r} not found on concept {concept_key!r}")`.
4. **Entry shape gate.** `entry` must be either:
   - `str` — the single-formula case. Treat as a length-1 list internally for
     uniform handling.
   - `list[str]` where **at least one element** contains a `* (...)` segment
     (a regex sanity-check: `re.search(r"\*\s*\(", element)` matches on at
     least one element). If `entry` is a list and **no** element contains
     `* (`, raise
     `ValueError(f"var {var_key!r} on concept {concept_key!r} is a lookup-table list (no conditional fragments); L2 condition-addressed mutation does not apply")`.
   Any other shape (`dict`, `int`, `None`, etc.) → raise
   `TypeError(f"var {var_key!r} on concept {concept_key!r} has unsupported shape {type(entry).__name__}")`.
5. **Rule field validation.** `rule["condition"]` and `rule["new"]` must both
   be non-empty strings; otherwise raise
   `ValueError(f"rule for {mod_type.value} requires non-empty 'condition' and 'new' fields")`.
6. **Whitespace-normalised condition.** Define
   `def _norm(s): return re.sub(r"\s+", " ", s).strip()`. Match the rule's
   condition against the formula using its normalized form, but capture the
   **as-written** condition from the formula for the Modification record's
   `condition` field.
7. **Fragment-finder regex.**
   ```python
   pat = re.compile(
       r'"(?P<frag>[^"]*)"\s*\*\s*\(\s*(?P<cond>[^)]*)\s*\)'
   )
   ```
   Iterate `pat.finditer(formula_text)` and pick the first match where
   `_norm(m.group("cond")) == _norm(rule["condition"])`. If no such match
   exists in any list element, raise
   `KeyError(f"condition {rule['condition']!r} not found on var {var_key!r} of concept {concept_key!r}")`.
   If **multiple** matches across all list elements satisfy the condition,
   raise `ValueError` with a message listing the duplicate occurrences (catalog
   corruption — same condition must not appear twice for the same var).
8. **In-place rewrite.** Capture `original = m.group("frag")` (unquoted
   inner). Build `replacement = f'"{rule["new"]}" * ({m.group("cond")})'`
   — note the as-written `cond` group is preserved verbatim so any
   compound `or` expression and the original whitespace inside the parens
   survive. Replace the single matched span via
   `new_element = element[:m.start()] + replacement + element[m.end():]`.
   Write `new_element` back into the list (or back into the str slot if
   `entry` was a single str).
9. **Other list elements untouched.** When `entry` is a list and only one
   element contains the match, every other element must be bytewise-identical
   pre and post.
10. **Modification record.** Emit exactly one:
    ```python
    Modification(
        type=mod_type,
        layer=Layer.TEXT_VARIABLE,
        var=var_key,
        condition=m.group("cond"),    # as-written, not the rule's normalized form
        original=original,             # captured inner fragment, unquoted
        new=rule["new"],
        status="applied",
    )
    ```
    `param`, `value`, `field`, `reason` stay `None`.

#### Three thin public wrappers

```python
def apply_paraphrase(stage_json, concept_key, rule):
    return _replace_fragment(stage_json, concept_key, rule, ModificationType.PARAPHRASE)

def apply_expansion(stage_json, concept_key, rule):
    return _replace_fragment(stage_json, concept_key, rule, ModificationType.EXPANSION)

def apply_compression(stage_json, concept_key, rule):
    return _replace_fragment(stage_json, concept_key, rule, ModificationType.COMPRESSION)
```

As in Sprint 07, mechanics are uniform; the per-type semantics ride on the
`Modification.type` enum.

**Acceptance**

- `from synthetic.layer_l2 import (apply_paraphrase, apply_expansion,
  apply_compression, _replace_fragment)` succeeds.
- Each public wrapper's signature is exactly
  `(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]`.
- For a str-typed formula `'"normal" * (%B=="a") + "bajo vías" * (%B=="b")'`
  and rule `{"type":"paraphrase","var":"K","condition":'%B=="a"',"new":"estándar"}`:
  - Returned formula is `'"estándar" * (%B=="a") + "bajo vías" * (%B=="b")'`.
  - Emitted `Modification.original == "normal"`, `.new == "estándar"`,
    `.condition == '%B=="a"'`, `.var == "K"`, `.status == "applied"`,
    `.layer is Layer.TEXT_VARIABLE`.
- For a list-typed entry `['"x" * (%A=="a")', '"y" * (%A=="b")']` and a rule
  targeting condition `%A=="b"`, only index `1` is rewritten; index `0` is
  bytewise-identical pre/post.
- For an entry that is a pure lookup-table list
  (`['"Diurno"', '"Nocturno"']`, no `* (`) the worker raises `ValueError`
  with a message that names the var and explains the shape mismatch.
- Rule with `var="$I"` resolves to dict key `"I"` exactly as `var="I"`
  would.

---

### Task 2 — Wire the three L2 functions into the dispatcher

Edit [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):

1. Add the import block under the existing `from .layer_l1 import (...)`:
   ```python
   from .layer_l2 import (
       apply_compression,
       apply_expansion,
       apply_paraphrase,
   )
   ```
2. **Delete** the three `_stub_paraphrase`, `_stub_expansion`,
   `_stub_compression` function definitions.
3. **Replace** the three matching entries in `_DISPATCH`:
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
       ModificationType.OMISSION: _stub_omission,
       ModificationType.REORDER: _stub_reorder,
       ModificationType.NEW_PARAM: _stub_new_param,
   }
   ```
4. **Update the module docstring** from "6 L1 live, 6 still stubs" to "6 L1
   + 3 L2 live, 3 still stubs". One-line swap; the boundary-stability claim
   is unchanged.
5. **Do not touch** `_apply_rules`, `_resolve_type`, `_gate_layer`,
   `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`, or the
   surviving 3 stub definitions.

**Acceptance**

- `python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER; live = [t for t in ModificationType if TYPE_TO_LAYER[t] in (Layer.PARAM_VALUE, Layer.TEXT_VARIABLE)]; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in live); stubs = [t for t in ModificationType if t not in live]; assert all(_DISPATCH[t].__name__.startswith('_stub_') for t in stubs); assert len(live) == 9 and len(stubs) == 3; print('dispatch audit ok')"` succeeds.
- `python -c "from synthetic.mutator import _stub_paraphrase"` raises
  `ImportError` (the three L2 stubs are physically gone).
- A round-trip through `apply_l2` with one well-formed `paraphrase` rule on
  the stage-3 fixture mutates only the targeted fragment; the caller's
  input dict is byte-identical pre/post via `json.dumps(..., sort_keys=True)`.

---

### Task 3 — `tests/synthetic/test_layer_l2.py`: contract suite for the 3 L2 types

Create `tests/synthetic/test_layer_l2.py`. Add a stage-3 fixture mirroring
the real `OEB020$` shape (str-typed `K`/`I`/`N`, list-typed conditional `P`,
and a lookup-table list `G` for the out-of-scope error path):

```python
import copy
import json
import pytest

from synthetic.layer_l2 import (
    _replace_fragment,
    apply_compression,
    apply_expansion,
    apply_paraphrase,
)
from synthetic.mutator import apply_l2
from synthetic.taxonomy import Layer, Modification, ModificationType


@pytest.fixture
def oeb020_stage3():
    return {
        "OEB020$": {
            "concept": "CANALIZACIÓN HORMIGONADA",
            "parameters": { ... },   # carried for realism; not read by L2
            "text_variables": {
                "K": (
                    '"normal" * (%B=="a") + '
                    '"bajo vías" * (%B=="b") + '
                    '"rocoso" * (%B=="c")'
                ),
                "I": (
                    '"en cualquier clase de terreno, excepto roca" * (%B=="a") + '
                    '"en cruce bajo vías" * (%B=="b")'
                ),
                "N": '"el descerne y la entibación," * (%B=="b"  or  %B=="g")',
                "P": ['"la preparación y nivelación..." * (%B=="f")'],
                "G": ['"Diurno"', '"Nocturno"'],   # lookup table — out of scope
            },
            "resumen": "PLACEHOLDER",
            "texto": "PLACEHOLDER",
        }
    }
```

Required test cases (≥13):

1. **`test_happy_path_per_type` (parametrised, 3 cases).** For each of the
   three wrappers and a credible (var, condition, new) triple on `K` / `I` /
   `N`, assert:
   - Returned formula contains the new fragment with original quoting and
     the as-written condition preserved.
   - Adjacent fragments in the formula are bytewise-identical (string slice
     comparison around the rewritten span).
   - Exactly one `Modification` is emitted with the right
     `type`/`layer`/`var`/`condition`/`original`/`new`/`status`.

2. **`test_list_typed_conditional_fragment`.** Rule targets `var="P"`,
   `condition='%B=="f"'`. List has one element which is rewritten; the list
   length and order are preserved.

3. **`test_var_prefix_stripped`.** Two equivalent rules — `var="K"` and
   `var="$K"` — produce byte-identical `out` dicts and `Modification`
   records when applied to a fresh fixture each time.

4. **`test_modification_original_sourced_from_stage_json`.** Rule's
   `original` field is `"WRONG"`; assert the log carries the actual
   captured fragment, not the rule's stale value. Pins the same asymmetry
   as Sprint 07's L1 contract.

5. **`test_apply_l2_orchestrator_threads_rules`.** Pass a 3-element batch
   (one paraphrase, one expansion, one compression — each targeting a
   different `(var, condition)`). Assert log is `[Modification, Modification,
   Modification]` in submission order, all `status="applied"`, and the
   input dict's pre-call `json.dumps(..., sort_keys=True)` matches the
   post-call snapshot (outer `_apply_rules` deep-copy guarantee).

6. **`test_compound_or_condition_preserved`.** Rule targets `var="N"`,
   `condition='%B=="b"  or  %B=="g"'` (matching the as-written form with
   the double space). The rewritten formula MUST preserve the as-written
   condition verbatim (double space included). The Modification record's
   `condition` field MUST also be the as-written form.

7. **`test_whitespace_normalized_condition_match`.** Rule's `condition` is
   `'%B=="b" or %B=="g"'` (single space). It still matches the fixture's
   `'%B=="b"  or  %B=="g"'` (double space) because the matcher normalizes
   runs of whitespace. The emitted `Modification.condition` still carries
   the **as-written** double-space form.

8. **`test_lookup_table_list_raises`.** Rule targets `var="G"`,
   `condition='%C=="a"'`. `G` is `['"Diurno"', '"Nocturno"']` — no
   `* (` segment in any element. Assert `ValueError` with a message that
   mentions `"G"` and the words "lookup-table" or "no conditional fragments".

9. **`test_missing_concept_key_raises`.** Concept key not in stage_json.
   Assert `KeyError` whose message names the missing key.

10. **`test_missing_var_raises`.** Rule names a var not in
    `concept["text_variables"]`. Assert `KeyError` whose message names the
    missing var (after `$`-strip).

11. **`test_missing_condition_raises`.** Rule's condition doesn't match any
    fragment on the named var. Assert `KeyError` whose message names the
    missing condition and the var.

12. **`test_empty_new_raises`.** Rule's `"new"` is `""`. Assert `ValueError`
    whose message mentions the `mod_type` and `"new"`.

13. **`test_missing_condition_field_raises`.** Rule omits the `"condition"`
    field entirely (KeyError on access from `rule["condition"]`, or the
    pre-check raises `ValueError` if you do `rule.get("condition")` first
    — implementer's choice, but pin one of the two behaviours via this
    test).

14. **`test_caller_dict_unchanged_after_apply`.** Snapshot via
    `json.dumps(stage_json, sort_keys=True, ensure_ascii=False)`, call
    `apply_l2` with one well-formed `paraphrase` rule, take a fresh
    snapshot. The two strings are identical.

15. **`test_only_targeted_fragment_changes`.** Pre-call, capture every
    fragment in the formula by running `re.findall(r'"[^"]*"', formula)`.
    Post-call, capture again. Exactly one element of the resulting list
    must differ (the rewritten fragment); every other element must be
    bytewise-identical.

**Acceptance**

- The new file contributes at least 15 test cases. More is fine; less is
  not.
- `pytest tests/synthetic/test_layer_l2.py -q` exits 0 with no skips.

---

### Task 4 — Adjust the existing stub tests in `tests/synthetic/test_mutator.py`

Two surgical edits:

1. **`_STUB_TYPES` shrinks from "non-PARAM_VALUE" to "TEMPLATE or
   PARAM_DEFINITION".** Replace:
   ```python
   _STUB_TYPES = [
       t for t in ModificationType
       if TYPE_TO_LAYER[t] is not Layer.PARAM_VALUE
   ]
   ```
   with:
   ```python
   _STUB_TYPES = [
       t for t in ModificationType
       if TYPE_TO_LAYER[t] in (Layer.TEMPLATE, Layer.PARAM_DEFINITION)
   ]
   ```
   This narrows the parametrised stub test from 6 cases to 3
   (`omission`, `reorder`, `new_param`). After B3 lands, this becomes
   `(Layer.PARAM_DEFINITION,)`; after B4 the list becomes empty and the
   entire parametrised test gets deleted.

2. **`test_deep_copy_purity_on_notimplemented` swaps `paraphrase` →
   `omission`.** Sprint 07 set this to `paraphrase` against `apply_l2`;
   `paraphrase` is now a live mutator. Change the rule's `type` to
   `"omission"` and the entry-point to `apply_l3`:
   ```python
   with pytest.raises(NotImplementedError):
       apply_l3(stage, "OEB020$", [{"type": "omission"}])
   ```
   The test's intent — "input dict unchanged even when the dispatched
   mutator raises" — is preserved against the surviving L3 stubs.

**Acceptance**

- `pytest tests/synthetic/test_mutator.py -q` exits 0. The parametrised
  case count for `test_each_stub_raises_notimplemented_with_type_code`
  shrinks from 6 to 3.
- No new external dependencies introduced.

---

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 08 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: files created/edited,
   the test-count delta (63 → expected ~75), the dispatcher-table audit
   result (`9 live + 3 stubs`), the L2 rule schema decisions (`$`-stripping,
   whitespace-normalized condition match, lookup-table-list error path),
   any deviations from this sprint file, and a one-line next-step
   recommendation (B3 → `layer_l3.py`).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for `src/synthetic/layer_l2.py` in the "New Files in This
     Branch" block, with a one-line annotation matching the Sprint 07
     entry's shape (e.g., "✅ Sprint 08 — Task B2 — apply_paraphrase /
     apply_expansion / apply_compression bodies; `_replace_fragment`
     shared worker; 3 stubs removed from `mutator.py`; condition-addressed
     rule schema with `$`-strip and whitespace-normalized matching").
   - Prepend a new "After Sprint 08 — …" entry to the Sprint History
     section following the Sprint 07 template.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Their content
   stands; the protocol's B2 entry simply becomes "done".

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **75 passed** (63 from Sprint 07 − 3 narrowed-out L2 stub cases +
15 new L2 contract cases), zero failures, zero skips. The arithmetic:
Sprint 07 ended at 63 with `_STUB_TYPES` parametrising the stub test over
6 cases; B2 narrows that to 3 (−3 cases), and Task 3 adds ≥15 new tests.
Net delta: +12 → 75.

> ⚠ **Plan-self-consistency cross-check** (per Sprint 07's known issue): If
> the implementer's Task 3 adds exactly 15 tests and the narrowing in Task 4
> drops exactly 3 stub cases, total = 63 − 3 + 15 = **75**. Verify this
> arithmetic before sealing the sprint and update the RESEARCH_LOG entry
> with the actual count.

Smoke checks (PowerShell-friendly one-liners):

```powershell
python -c "from synthetic.layer_l2 import apply_paraphrase, apply_expansion, apply_compression, _replace_fragment; print('imports ok')"

python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER; live = [t for t in ModificationType if TYPE_TO_LAYER[t] in (Layer.PARAM_VALUE, Layer.TEXT_VARIABLE)]; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in live); stubs = [t for t in ModificationType if t not in live]; assert all(_DISPATCH[t].__name__.startswith('_stub_') for t in stubs); assert len(live) == 9 and len(stubs) == 3; print('dispatch audit ok:', len(live), 'live,', len(stubs), 'still stubs')"

python -c "import json; from synthetic.mutator import apply_l2; s = {'OEB020$': {'text_variables': {'K': '\"normal\" * (%B==\"a\") + \"bajo vias\" * (%B==\"b\")'}}}; snap = json.dumps(s, sort_keys=True, ensure_ascii=False); out, log = apply_l2(s, 'OEB020$', [{'type':'paraphrase','var':'K','condition':'%B==\"a\"','new':'estandar'}]); assert json.dumps(s, sort_keys=True, ensure_ascii=False) == snap; assert out['OEB020$']['text_variables']['K'] == '\"estandar\" * (%B==\"a\") + \"bajo vias\" * (%B==\"b\")', out['OEB020$']['text_variables']['K']; assert len(log) == 1 and log[0].var == 'K' and log[0].original == 'normal' and log[0].new == 'estandar' and log[0].status == 'applied'; print('end-to-end ok')"
```

End-of-sprint expected `git status --short` (sprint-scoped subset only):
```
new file:   src/synthetic/layer_l2.py
modified:   src/synthetic/mutator.py
new file:   tests/synthetic/test_layer_l2.py
modified:   tests/synthetic/test_mutator.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_08.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`, `configs/`,
or `docs/synthetic/*.md` (except the two log files) should appear.

---

## Design notes worth committing to memory

- **Three wrappers, one worker — Sprint 07's pattern generalises cleanly.**
  L2's `_replace_fragment` is the L1 `_replace_value` pattern adapted for
  condition-addressed fragments inside formulas. The wrappers exist purely
  to set the `Modification.type` enum on the emitted record. Per-type
  semantic enforcement (does this "paraphrase" actually preserve meaning?
  is this "compression" shorter than the original?) lives upstream in
  Phase C prompts and downstream in Phase E review, never inside the
  applier.
- **Whitespace normalization is matcher-only, never writer.** The matcher
  normalises runs of whitespace to single spaces to find the condition
  robustly; the writer preserves the as-written condition verbatim
  (including any double-space irregularities in compound `or` expressions).
  This means the rewritten formula stays byte-equivalent to the original in
  every region the rule didn't target. The `Modification.condition` field
  records the as-written form so downstream consumers see what's actually
  in the formula, not the rule-supplied alias.
- **Pure lookup-table lists fail loudly, not silently.** A rule targeting
  `var="G"` with a condition has no fragment to address. Raising
  `ValueError` (rather than emitting `status="skipped"`) is the right
  call: the variant catalog (Phase C) is human-curated and a condition-
  on-lookup-table mismatch is a catalog authoring error, not a runtime
  edge case to absorb. Phase B5 composition rules will gate this at
  catalog-validation time before any apply call.
- **`$`-prefix tolerance lives at the L2 rule boundary, not in the data.**
  Stage-3 JSON dict keys are bare (`'K'`, `'I'`, `'N'`). The rule schema
  accepts both `var="K"` and `var="$K"` because the Modification record's
  worked example in
  [`RESEARCH_PROPOSAL.md §2.3`](../RESEARCH_PROPOSAL.md) shows `"var": "$I"`
  and the catalog's authors think in reference-syntax terms. The mutator
  strips the prefix at the rule boundary; everywhere inside the worker
  the key is bare. `Modification.var` is emitted in the **bare** form for
  consistency with the stage JSON's internal naming.
- **Compound conditions are opaque to the worker.** The condition is
  treated as a literal string handle for matching; the worker does not
  parse `%B=="b" or %B=="g"` into clauses. If a variant catalog wants to
  mutate only one half of the disjunction, that's a different rule shape
  (and arguably a different L2 type) — explicitly deferred. B2's worker
  treats the entire parenthesized expression as the addressing key.
- **No deep-copy at the worker, same as L1.** The outer `_apply_rules`
  `copy.deepcopy` handles caller purity; the worker mutates its received
  `out` in place. Worker-level deep-copy would balloon costs on stacked
  rules in Phase B5 composition. Caller purity is pinned by
  `test_caller_dict_unchanged_after_apply`.
- **Sprint 07 plan-arithmetic gotcha is repeated above intentionally.**
  Sprint 07's headline pytest count was internally inconsistent because
  the stub-test narrowing wasn't subtracted from the plan's "54 + N = ?"
  math. This sprint draft's verification runbook does the arithmetic
  explicitly (63 − 3 + 15 = 75) so the next sprint's plan review catches
  any drift earlier.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file
  map, stage-hook integration note (the L2 entry now becomes live).
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.2 (12-type
  taxonomy table — L2 types are rows 7–9), §2.3 (`Modification` schema with
  the `paraphrase` worked example).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.3 (three-layer
  mutation interface, L2 row), §5 Phase B (B2 task definition), §8.2
  (representative `paraphrase` prompt — informs Phase C, *not* this sprint).
- [`SPRINT_07.md`](SPRINT_07.md) — the L1 template this sprint is fanning
  out. The "three wrappers, one worker" pattern and the rule-`original`-
  vs-log-`original` asymmetry transfer directly.
- [`src/s04_evaluate_text_variables.ipynb`](../../src/s04_evaluate_text_variables.ipynb)
  — the downstream consumer of the mutated stage-3 JSON. Important for
  understanding why the worker must preserve the formula's syntactic frame
  byte-for-byte outside the targeted fragment: s04's `evaluate_formula`
  Python-evals the formula after parameter substitution, so any disturbance
  to operators, quotes, or parens breaks downstream resolution.
- [`src/utils/z_formula_processing.py`](../../src/utils/z_formula_processing.py)
  — `translate_formula_to_python()` is the function s04 hands the mutated
  formula to. Confirms that the `"FRAG" * (COND) + "FRAG" * (COND)` shape
  is the canonical BC3 formula form and must be preserved.

---

## Non-goals reminder

If you find yourself opening any `.ipynb` file, anything under `data/`,
`configs/`, or `src/utils/`, anything in `src/synthetic/layer_l3.py` /
`layer_pd.py` / `composition.py` / `llm_proposer.py` / `prompts/`, or
writing Spanish paraphrase dictionaries / expansion tables / compression
heuristics inside `layer_l2.py` — **stop**. That's outside Sprint 08.
Either the work belongs to a future sprint (B3+, C1+, D1+) or it should be
raised as a clarifying question in `RESEARCH_LOG.md` before being
addressed.

If you find yourself implementing an `index`-addressed rule shape so the
lookup-table list `'G'` can be mutated — also **stop**. That's a
deliberate B2 non-goal; bring it up for a future sprint (B2.5 candidate)
before adding it here. Sprint 08's rule schema is exclusively
`(var, condition)`-addressed.
