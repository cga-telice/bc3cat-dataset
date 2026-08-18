# Sprint 10 — Phase B Task B4: PD `new_param` mutator body (`layer_pd.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 10                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | B4 — see [`../RESEARCH_PROTOCOL.md §5 Phase B`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 09 — `layer_l3.py` + 2 L3 mutator bodies (see [`SPRINT_09.md`](SPRINT_09.md))         |
| **Successor**   | Sprint 11 — Phase B Task B5 (`composition.py` — stacking rules) — TBD                       |

---

## Context

Sprint 09 closed Task B3 by promoting the two L3 `template` stubs to real
bodies in [`src/synthetic/layer_l3.py`](../../src/synthetic/layer_l3.py),
landing at 99/99 pytest pass with a `_replace_substring` shared worker that
addresses template prose by `(field, original)`. The "one shared private
worker, N thin public wrappers, one `Modification` record per wrapper call,
semantic-blind applier layer" pattern is now fanned across three layers
(L1 ×6, L2 ×3, L3 ×2). Sprint 10 lands the **last surviving stub**: the
PD-layer **`new_param`** mutator. After B4 closes, `_DISPATCH` reaches
**12 live, 0 stubs**.

PD differs from L1/L2/L3 in **four** places — enough that the
"wrappers, one worker" pattern that's served Sprints 07–09 must be set
aside in favour of a single-function design:

1. **Mutation target.** Stage-2 JSON's `concept["parameters"]` axis dict —
   *adding* a new axis rather than rewriting an existing one. Optionally
   also `concept["text_variables"]` (a new `$VAR` formula) and
   `concept["resumen"]` / `concept["texto"]` (template patches that inject
   the new variable's reference). One PD rule may touch **three** blocks
   of the same concept; L1/L2/L3 rules touch exactly one.
2. **Mutation kind: `add`, not `replace`.** L1/L2/L3 are all
   find-the-target → rewrite-the-target operations. PD is
   find-no-target → install-a-new-target. Collision detection (param key
   already present, var key already present) replaces L1/L2/L3's
   not-found / multiple-match check.
3. **Single rule, not a list.** `apply_new_param` in `mutator.py` accepts
   one rule (not `rules: list[dict]`) and does not thread through
   `_apply_rules`. The dispatch contract was set at Sprint 01 and is
   already wired correctly — this sprint does not change it; it only
   replaces `_stub_new_param` with the real body and confirms the
   single-rule shape.
4. **One type, one wrapper.** PD has exactly one `ModificationType`
   (`NEW_PARAM`). There is no "N wrappers, one worker" fan-out to
   express — only **one** function whose job is the entire PD edit. The
   sprint surface is therefore one public function (named
   `apply_new_param` for symmetry with L1's `apply_synonym_label`,
   L2's `apply_paraphrase`, L3's `apply_omission`), called via the
   `_DISPATCH` table. The orchestrator entry-point `apply_new_param` in
   `mutator.py` keeps its existing name; the layer-module worker is
   imported with a local alias to avoid the name clash.

The dispatcher surface (`apply_l1`/`l2`/`l3`/`apply_new_param`) does not
change. After this sprint, **every** entry in `_DISPATCH` resolves to a
function whose `__name__` starts with `apply_`; the `_stub_*` prefix
disappears from `mutator.py` entirely; the parametrised stub test in
[`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py)
goes away (its `_STUB_TYPES` source list is now empty); and
`test_deep_copy_purity_on_notimplemented` retires (it depended on a
still-stubbed type code being available to raise `NotImplementedError`;
caller-purity on a *successful* PD application is covered by the new
contract suite in `test_layer_pd.py`).

Sprint 09's pytest baseline: 99 passed. Sprint 10 removes 1 case (the
parametrised stub test's last surviving NEW_PARAM case) plus 1 case
(`test_deep_copy_purity_on_notimplemented`), and adds the new PD
contract suite in
[`tests/synthetic/test_layer_pd.py`](../../tests/synthetic/test_layer_pd.py)
(≥18 cases). Net delta: at least +16 → **≥115 passed**.

---

## Scope

### In scope
- **B4** — `src/synthetic/layer_pd.py` (new): one public function
  `apply_new_param(stage_json, concept_key, rule)` that adds a new axis
  to `concept["parameters"]`, optionally registers a new `$VAR` in
  `concept["text_variables"]`, and optionally applies one or more
  substring patches to `concept["resumen"]` / `concept["texto"]` to
  inject the new variable's reference. Returns
  `tuple[dict, list[Modification]]` with exactly one `Modification` in
  the log.
- **Wire-in** to [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):
  import the new function with a local alias (`apply_new_param as _layer_pd_apply_new_param`)
  to avoid clashing with the existing `apply_new_param` orchestrator
  defined in `mutator.py` itself; replace the `_stub_new_param` entry in
  `_DISPATCH`; delete the `_stub_new_param` function definition. The
  dispatcher surface and the orchestrator `apply_new_param` are
  byte-preserved. Update the module docstring from "6 L1 + 3 L2 + 2 L3
  live, 1 still stub (PD — `new_param`)" to "all 12 (6 L1 + 3 L2 + 2 L3
  + 1 PD) mutators live; dispatcher is fully promoted from stubs".
- **Test cleanup** in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):
  delete `_STUB_TYPES`, `_LAYER_TO_APPLY`, the parametrised
  `test_each_stub_raises_notimplemented_with_type_code` function, and
  `test_deep_copy_purity_on_notimplemented` (they all depended on at
  least one stub remaining). Drop the now-unused imports `Layer` and
  `TYPE_TO_LAYER`. Add a new audit test
  `test_no_stubs_remain_in_dispatch` that asserts every value in
  `_DISPATCH` is a function whose `__name__` starts with `apply_`.
  Retained tests: the four signature tests,
  `test_dispatch_table_has_exactly_12_entries`, the three layer-gate
  tests (`test_wrong_layer_rule_raises_valueerror`,
  `test_wrong_layer_rule_on_new_param_raises_valueerror`,
  `test_unknown_type_code_raises_valueerror`). Eight tests survive in
  `test_mutator.py` + the one new audit test = nine.
- **New contract suite** `tests/synthetic/test_layer_pd.py` covering the
  PD mutator on a small inline stage-2 fixture mirroring the real
  `OEB020$` shape: happy-path with axis-only, axis+text_variable,
  axis+template-patch, axis+text_variable+template-patches (full combo);
  collision errors (param-key clash, var-key clash); template-patch
  errors (substring not found, multiple matches); rule-shape errors
  (empty `param`, empty `label`, empty `values`, duplicate value labels,
  text_variable without formula); field-case normalisation;
  caller-purity snapshot through the orchestrator;
  text_variables-block-auto-creation when the rule supplies a variable
  but the concept lacks the block; direct-worker call. ≥18 cases.
- **Housekeeping**: append Sprint 10 entry to
  [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md); flip ❌ → ✅ for
  `src/synthetic/layer_pd.py` in
  [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); prepend "After
  Sprint 10 — …" history entry.

### Out of scope (explicit)
- **B5** — `composition.py` (stacking rules). PD rules are still applied
  in isolation; no stacking constraints with L1/L2/L3 are validated at
  apply-time. The B5 sprint will add those.
- **`new_param_allowlist.yaml`** (Phase B configs). The applier does
  **not** validate the rule's `param` / `label` / `values` against any
  controlled list of admissible new axes. The variant proposer (Phase C)
  is responsible for constraining itself to the allowlist; the reviewer
  harness (Phase E) is responsible for enforcing it. The applier is
  semantic-blind, exactly like L1/L2/L3.
- **C1–C4** — prompts, LLM client, variant proposer, variant catalog. The
  rule schema below is what the variant proposer will emit in Phase C;
  nothing in this sprint *generates* a `new_param` proposal.
- **D1 / D2** — no stage-hook wiring into s03, no orchestrator. The
  mutator is exercised via direct unit calls only.
- **Cross-axis semantic collision detection.** A rule that adds a new
  axis labelled "GRADE" when the concept already has an axis labelled
  "QUALITY" — even though semantically these clash — succeeds at
  apply-time. Collisions are by axis **key** (`param`) and var **key**
  (`var`), not by label or value semantics. Per-axis semantic vetting
  lives in Phase E (reviewer harness).
- **Cross-template insertion consistency.** A rule may patch
  `texto` but not `resumen` (or vice-versa), or both, or neither — the
  applier does not require symmetry. A "well-formed" PD rule typically
  injects the new variable into at least one template, but the applier
  does not enforce this. A rule that adds a new axis without referencing
  it anywhere succeeds (the new axis becomes a parameter that nothing
  reads — that's a Phase C proposer bug to detect, not a Phase B
  applier bug).
- **Stage-3 Cartesian expansion.** PD operates on stage-2 JSON (parent
  concept dict like `OEB020$`), **before** s03's Cartesian product over
  axes. The new axis will participate in the expansion at the next
  pipeline stage. Sprint 10 verifies the stage-2 edit only; the
  downstream "does s03 successfully expand the new axis?" check is a
  Phase D (stage-hook) concern.
- **Splitting one PD rule into multiple `Modification` records.** The
  applier emits **one** `Modification` per rule, even when the rule
  touches three blocks (parameters + text_variables + templates). The
  `Modification` dataclass fields populated capture the high-level audit
  (`param=<new key>`, `new=<new label>`, `var=<new var key if any>`);
  full mutation detail lives in the variant catalog's rule payload,
  which the Phase E1 metadata-join uses to reconstruct the per-item
  metadata. This pins Sprints 07–09's "one rule → one `Modification`"
  contract uniformly across all 12 types.
- **`Modification` dataclass changes.** No new fields, no new optionals.
  The existing schema (`param`, `var`, `condition`, `field`, `value`,
  `original`, `new`, `status`, `reason`) is sufficient; PD overloads
  `param=<new axis key>`, `new=<new axis label>`, `var=<new var key if
  any>`. Variant catalog reconstruction is the source-of-truth for the
  rest.
- **Anything under `data/`, `configs/`, `src/utils/`, or any notebook.**
  Tests run against an inline fixture; no disk I/O. No path-refactor
  work, no Generate_OEB changes, no s03 changes.

---

## Stage-2 JSON shape (verified against test fixtures and real catalog)

The PD worker operates on the concept's `parameters`, `text_variables`,
`resumen`, and `texto` blocks at stage 2. The shape verified by
[`tests/synthetic/test_layer_l1.py`](../../tests/synthetic/test_layer_l1.py)
(`oeb020_stage2` fixture) and by
`data/intermediate/OBRA CIVIL/OBRA_CIVIL.json` for `OEB020$`:

```python
{
    "OEB020$": {
        "concept": "CANALIZACIÓN HORMIGONADA",
        "parameters": {
            "A": {"label": "Nº TUBOS",        "values": [{"label": "a", "value": "1"}, ...]},
            "B": {"label": "TIPO DE TERRENO", "values": [...]},
            "C": {"label": "DIÁMETRO",        "values": [...]},
            "D": {"label": "MATERIAL",        "values": [...]},
            "E": {"label": "CALIDAD HORMIGÓN","values": [...]},
        },
        "text_variables": {
            "K": '"normal" * (%B=="a") + ...',     # str or list[str] per L2 shape
            # may be {} if no text variables are defined
        },
        "resumen": "Canalización hormigonada de $A T, PVC 110 mm, $K. ...\\",
        "texto":   "\\Canalización hormigonada de $A tubos ... $K ...",
    }
}
```

Notes that affect the implementation:

- **`parameters` is always present** on a parametric concept. A concept
  without `parameters` is not parametric (and PD has nothing to do).
  The worker raises `KeyError` if the block is absent.
- **`text_variables` may be `{}` or absent entirely.** Some concepts
  have no `$VAR` formulas (every template-token is a direct parameter
  reference like `$A`). When the rule supplies a `text_variable` block,
  the worker creates `concept["text_variables"] = {}` if missing, then
  inserts the new var. This is the *only* "create missing block" path
  in the worker — it exists because a stage-2 concept legitimately may
  lack the block, and the rule is the explicit authorisation to install
  one.
- **`resumen` and `texto` are templates** at stage 2 — they contain
  `$VAR` references that s05 will resolve later. PD template patches
  are bytewise substring rewrites, exactly like L3 — same uniqueness
  contract, same case-insensitive `field` lookup.
- **Param keys are single uppercase letters in practice** (`A`, `B`, …),
  but the worker treats them as opaque strings. A rule with
  `param="QC"` is accepted; a rule with `param="A"` on a concept that
  already has axis `A` raises `ValueError`.

---

## Tasks

### Task 1 — `src/synthetic/layer_pd.py`: the `apply_new_param` worker

Create `src/synthetic/layer_pd.py`. Module surface:

```python
"""PD `new_param` mutator — adds a parameter axis plus optional
text-variable and template-patch side effects.

Receives a stage-2 JSON dict (already deep-copied by the upstream
`apply_new_param` orchestrator in `mutator.py`), the target
`concept_key`, and a single rule dict. The worker installs the new
axis under `concept["parameters"][rule["param"]]`, optionally registers
a new `$VAR` formula under `concept["text_variables"][rule["text_variable"]["var"]]`,
and optionally applies one or more substring patches to
`concept["resumen"]` / `concept["texto"]`. Returns the dict together
with a one-element `[Modification]` log.

Diverges from L1/L2/L3 in three ways: it `add`s rather than `replace`s
(collisions raise); it may touch multiple blocks of the same concept
within one rule; and there is only one wrapper (no per-type fan-out)
because PD has exactly one `ModificationType`.
"""

from __future__ import annotations

from .taxonomy import Layer, Modification, ModificationType


def apply_new_param(
    stage_json: dict,
    concept_key: str,
    rule: dict,
) -> tuple[dict, list[Modification]]: ...
```

#### Rule schema

| Key                | Required | Type                              | Description                                                                                                                       |
|--------------------|:--------:|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `type`             | yes      | str                               | Must be `"new_param"`. The orchestrator validates this via `_resolve_type` + `_gate_layer`.                                       |
| `param`            | yes      | str                               | New axis key (e.g., `"K"`). Must be a non-empty string. Must NOT already exist in `concept["parameters"]`.                       |
| `label`            | yes      | str                               | New axis display label (e.g., `"CALIDAD ACABADO"`). Non-empty string.                                                              |
| `values`           | yes      | list[dict]                        | Non-empty list of axis value entries. Each entry is `{"label": str, "value": str}`. Labels must be unique within the list.       |
| `text_variable`    | no       | dict                              | If present: `{"var": str, "formula": str}`. Registers a new `$VAR` formula on `concept["text_variables"]`. `var` must NOT clash. |
| `template_patches` | no       | list[dict]                        | Each patch: `{"field": "RESUMEN" or "TEXTO", "original": str, "new": str}`. Same L3 semantics — `original` occurs exactly once.   |

Per-field validation:

- `param`: type-check as `str`, raise `ValueError(f"rule for new_param requires a non-empty 'param' (string) field")` on missing/empty.
- `label`: type-check + non-empty.
- `values`: type-check as `list`, non-empty; each element a dict with `label` and `value` as non-empty `str`; pairwise-unique `label`s within the list.
- `text_variable`: optional. If present, must be a dict with `var` (non-empty str) and `formula` (non-empty str). Missing keys / empty values raise `ValueError`.
- `template_patches`: optional. If present, must be a list (may be empty — treated as no-op). Each element validated against the L3 patch contract below.

#### Worker behavioural requirements

1. **Concept lookup.** `concept = stage_json[concept_key]`. If missing, raise
   `KeyError(f"concept_key {concept_key!r} not found in stage_json")`.
2. **`parameters` block lookup.** `parameters = concept.get("parameters")`. If
   not a dict, raise
   `KeyError(f"concept {concept_key!r} has no parameters block")`.
3. **Validate `param`, `label`, `values`** per the table. Surface
   `ValueError` with messages naming `"new_param"` and the offending field
   ("param", "label", "values", "value labels duplicated").
4. **Collision check on `param`.** If `rule["param"] in parameters`, raise
   `ValueError(f"param key {rule['param']!r} already exists on concept "
   f"{concept_key!r}; new_param cannot replace an existing axis")`.
5. **Install the new axis.** `parameters[rule["param"]] = {"label": rule["label"], "values": list(rule["values"])}`.
   The `list(...)` is belt-and-braces (the outer `apply_new_param`
   orchestrator already deep-copied the whole stage_json — the rule
   itself is the caller's, so a shallow copy of `values` keeps the
   rule's `values` list immune to later in-place edits the variant
   catalog might do).
6. **Optional text_variable block.** If `"text_variable"` is in `rule`:
   a. Validate `text_variable` is a dict; `var` and `formula` are
      non-empty strings. Raise `ValueError` on missing / wrong-shape.
   b. `text_variables = concept.get("text_variables")`. If absent or
      not a dict, **create** `concept["text_variables"] = {}` and bind
      `text_variables` to the new empty dict. This is the only
      block-creation path in the worker; it exists because a stage-2
      concept legitimately may lack the block.
   c. Collision check on `var`. If
      `rule["text_variable"]["var"] in text_variables`, raise
      `ValueError(f"var key {var!r} already exists on concept "
      f"{concept_key!r}; new_param cannot overwrite an existing text variable")`.
   d. Install: `text_variables[var] = formula`.
7. **Optional template_patches.** If `"template_patches"` is in `rule`:
   a. Validate `template_patches` is a list. Raise `ValueError` otherwise.
   b. For each patch (in submission order):
      i.   Validate patch is a dict with `field`, `original`, `new` keys;
           same constraints as the L3 worker
           ([`src/synthetic/layer_l3.py`](../../src/synthetic/layer_l3.py)):
           `field` case-insensitive resolves to `"resumen"` or `"texto"`;
           `original` non-empty str; `new` str (may be empty).
      ii.  `template = concept[field_lower]`. Missing or non-string →
           `KeyError(f"concept {concept_key!r} has no {field_lower!r} template")`.
      iii. Count occurrences of `patch["original"]` in `template`. Zero
           → `KeyError`. Multiple → `ValueError`. Both messages name
           the substring and the field.
      iv.  Apply `concept[field_lower] = template.replace(original, new, 1)`.
   c. Patches apply in submission order; if a later patch's `original`
      no longer matches because an earlier patch rewrote that region,
      the worker raises `KeyError` (same as L3's stacked-rule contract).
      This is the intentional semantic-blind contract — patch ordering
      is the rule author's responsibility.
8. **Emit one `Modification`.** Exactly one record per rule:
   ```python
   Modification(
       type=ModificationType.NEW_PARAM,
       layer=Layer.PARAM_DEFINITION,
       param=rule["param"],                              # new axis key
       new=rule["label"],                                # new axis label
       var=rule["text_variable"]["var"] if "text_variable" in rule else None,
       status="applied",
   )
   ```
   `field`, `value`, `original`, `condition`, `reason` stay `None`. The
   full mutation delta (`values`, `formula`, every `template_patch`)
   lives in the rule payload — the variant catalog (Phase C4) stores
   the rule alongside the `Modification`, and the metadata-join (Phase
   E1) reconstructs the per-item metadata from both. This is the
   conscious "one rule → one `Modification`" contract maintained from
   Sprints 07–09; deviating here would couple the audit schema to
   per-type structure and break the symmetry with L1/L2/L3.

#### Acceptance

- `from synthetic.layer_pd import apply_new_param` succeeds.
- The function signature is exactly
  `(stage_json: dict, concept_key: str, rule: dict) -> tuple[dict, list[Modification]]`.
- **Axis-only happy path.** For the `oeb020_stage2` fixture (5 axes
  `A`–`E`, empty `text_variables`, placeholder `resumen` / `texto`), a
  rule `{"type":"new_param","param":"F","label":"CALIDAD ACABADO","values":[{"label":"a","value":"Estándar"},{"label":"b","value":"Premium"}]}`:
  - `concept["parameters"]["F"] == {"label": "CALIDAD ACABADO", "values": [...]}` after the call.
  - `concept["parameters"]["A"]…["E"]` are bytewise-preserved.
  - `concept["text_variables"]`, `concept["resumen"]`, `concept["texto"]`
    are bytewise-preserved.
  - Emitted `Modification` carries `type=NEW_PARAM, layer=PARAM_DEFINITION, param="F", new="CALIDAD ACABADO", var=None, status="applied"`.
- **Axis + text_variable happy path.** Rule with a
  `text_variable={"var":"F","formula":'"estándar" * (%F=="a") + "premium" * (%F=="b")'}`
  block:
  - `concept["text_variables"]["F"] == '"estándar" * (%F=="a") + "premium" * (%F=="b")'`.
  - Other text variables (if any) are bytewise-preserved.
  - Emitted `Modification.var == "F"`.
- **Axis + template_patches happy path.** Rule with
  `template_patches=[{"field":"TEXTO","original":"…unique substring…","new":"…rewritten…"}]`:
  - `concept["texto"]` is rewritten exactly as L3 would handle it.
  - `concept["resumen"]` is bytewise-preserved.
- **Param collision.** Rule with `param="A"` (already in the fixture)
  raises `ValueError` whose message names the colliding key.
- **Var collision.** Fixture extended with
  `text_variables = {"K": '"normal" * (%B=="a")'}`; rule with
  `text_variable={"var":"K","formula":"…"}` raises `ValueError` whose
  message names the colliding key.
- **Template patch substring not found.** Patch's `original` doesn't
  occur in the named template — `KeyError`.
- **Template patch substring multiple matches.** Patch's `original`
  occurs twice — `ValueError`.
- **Missing concept_key.** `KeyError` whose message names the key.
- **Concept has no `parameters` block.** Concept exists but the dict
  lacks `parameters` — `KeyError`.
- **Empty `param` / `label` / `values` / value-label duplicate.** All
  raise `ValueError` whose message identifies the field.
- **`text_variable` block without `formula`.** `ValueError`.
- **`template_patches` patch with unknown `field`.** `ValueError`
  whose message lists the accepted values (`"RESUMEN"`, `"TEXTO"`).
- **Field-case normalisation on template patches.** `TEXTO` / `texto` /
  `Texto` / `tExTo` all reach the same `concept["texto"]` lookup.
- **`text_variables` block auto-created.** Concept's
  `text_variables` is absent; rule supplies a `text_variable` block;
  worker creates `text_variables = {}` then inserts the new var. The
  fixture for this case may legitimately omit the `text_variables` key
  entirely.

---

### Task 2 — Wire `apply_new_param` into the dispatcher

Edit [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py):

1. Add an import with a local alias, under the existing
   `from .layer_l3 import (...)`:
   ```python
   from .layer_pd import apply_new_param as _layer_pd_apply_new_param
   ```
   The alias is **load-bearing**: `apply_new_param` is the existing name
   of the orchestrator function defined later in the same module, and
   importing the worker under the same identifier would shadow it. The
   alias keeps the orchestrator surface intact while making the worker
   addressable from `_DISPATCH`.
2. **Delete** the `_stub_new_param` function definition.
3. **Replace** the matching entry in `_DISPATCH`:
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
       ModificationType.NEW_PARAM: _layer_pd_apply_new_param,
   }
   ```
4. **Update the module docstring** from "6 L1 + 3 L2 + 2 L3 live, 1
   still stub (PD — `new_param`)" to "all 12 (6 L1 + 3 L2 + 2 L3 + 1
   PD) mutators live; dispatcher fully promoted from stubs". One-liner
   swap; the boundary-stability claim is unchanged.
5. **Optional rename of `_StubResult`.** It used to mean "the return
   type of a stub". After this sprint there are no stubs; the alias
   still works as "the return type of a dispatched mutator". Either
   leave it alone (zero-risk) or rename to `_MutatorResult` in a single
   replace-all. **Recommend leaving it alone** — purely cosmetic, and a
   rename touches the orchestrator type annotations needlessly. Note the
   leftover-naming in the Sprint 10 RESEARCH_LOG entry so a future
   reader knows it's vestigial.
6. **Do not touch** `_resolve_type`, `_gate_layer`, `_apply_rules`, or
   `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`. The
   orchestrator's `apply_new_param` (line ~133 in current file) is the
   single-rule entry-point that **calls** `_layer_pd_apply_new_param`
   via `_DISPATCH[mtype]`; its body is already correct.

**Acceptance**

- `python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import ModificationType; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in ModificationType); assert len(_DISPATCH) == 12; print('dispatcher fully promoted:', len(_DISPATCH), 'live, 0 stubs')"` succeeds.
- `python -c "from synthetic.mutator import _stub_new_param"` raises
  `ImportError` (the last stub is physically gone).
- The orchestrator `apply_new_param` in `mutator.py` retains its
  signature `(stage2_json, concept_key, rule)`, deep-copies its input,
  validates the rule's layer via `_gate_layer`, and dispatches through
  `_DISPATCH[ModificationType.NEW_PARAM]` to
  `_layer_pd_apply_new_param`. The orchestrator's body is byte-identical
  pre/post-sprint.
- A round-trip through `apply_new_param` with an axis-only rule on the
  stage-2 fixture installs the new axis and emits one `Modification`;
  the caller's input dict is byte-identical pre/post via
  `json.dumps(..., sort_keys=True, ensure_ascii=False)`.

---

### Task 3 — `tests/synthetic/test_layer_pd.py`: contract suite for the PD type

Create `tests/synthetic/test_layer_pd.py`. Inline stage-2 fixture
mirroring the real `OEB020$` shape (verified against the L1 fixture and
`data/intermediate/OBRA CIVIL/OBRA_CIVIL.json`):

```python
import copy
import json
import pytest

from synthetic.layer_pd import apply_new_param
from synthetic.mutator import apply_new_param as orchestrator_apply_new_param
from synthetic.taxonomy import Layer, Modification, ModificationType


@pytest.fixture
def oeb020_stage2():
    return {
        "OEB020$": {
            "concept": "CANALIZACIÓN HORMIGONADA",
            "parameters": {
                "A": {"label": "Nº TUBOS",        "values": [{"label": "a", "value": "1"}, {"label": "b", "value": "2"}]},
                "B": {"label": "TIPO DE TERRENO", "values": [{"label": "a", "value": "Normal"}, {"label": "b", "value": "Bajo vías"}]},
            },
            "text_variables": {
                "K": '"normal" * (%B=="a") + "bajo vías" * (%B=="b")',
            },
            "resumen": "Canalización hormigonada de $A T, PVC 110 mm, $K.\\",
            "texto":  "\\Canalización hormigonada de $A tubos, $K. Final.",
        }
    }
```

Required test cases (≥18):

1. **`test_happy_path_axis_only`.** Rule
   `{"type":"new_param","param":"F","label":"CALIDAD ACABADO","values":[{"label":"a","value":"Estándar"},{"label":"b","value":"Premium"}]}`.
   Assert:
   - `out["OEB020$"]["parameters"]["F"] == {"label": "CALIDAD ACABADO", "values": [...]}`.
   - `out["OEB020$"]["parameters"]["A"]` and `["B"]` are bytewise-identical pre and post.
   - `text_variables`, `resumen`, `texto` are bytewise-preserved.
   - One `Modification` emitted with `type=NEW_PARAM, layer=PARAM_DEFINITION, param="F", new="CALIDAD ACABADO", var=None, status="applied"`.

2. **`test_happy_path_axis_plus_text_variable`.** Rule adds axis `F` and
   `text_variable={"var":"F","formula":'"estándar" * (%F=="a") + "premium" * (%F=="b")'}`.
   Assert:
   - `out[...]["text_variables"]["F"]` is the new formula.
   - Pre-existing `text_variables["K"]` is bytewise-preserved.
   - Templates are bytewise-preserved.
   - `Modification.var == "F"`.

3. **`test_happy_path_axis_plus_one_template_patch`.** Rule with one
   `TEXTO` patch that injects `$F` (e.g.,
   `original="$K. Final."`, `new="$K, calidad $F. Final."`). Assert:
   - `out[...]["texto"]` is rewritten exactly as `str.replace(original, new, 1)`.
   - `resumen` is bytewise-preserved.

4. **`test_happy_path_full_combo`.** Rule combines all three blocks:
   axis + text_variable + 2 template_patches (one `RESUMEN`, one `TEXTO`).
   Assert all four edits land and the `Modification` carries `param`, `new`, `var` correctly.

5. **`test_param_collision_raises`.** Rule with `param="A"` (already
   exists). `ValueError` whose message names the key and the concept.

6. **`test_var_collision_raises`.** Rule with
   `text_variable={"var":"K", ...}` (the fixture already defines `K`).
   `ValueError` whose message names the var key and the concept.

7. **`test_template_patch_substring_not_found_raises`.** Patch's
   `original` is `"NO_SUCH_SUBSTRING"`. `KeyError`.

8. **`test_template_patch_substring_multiple_matches_raises`.**
   Patch's `original` is a string that appears twice in the named
   template (use `"hormigonada"` which is in `resumen` once and `texto`
   once — pick a fixture-specific double-match string, or extend the
   fixture to ensure one). `ValueError` whose message names the
   substring, count, and field.

9. **`test_missing_concept_key_raises`.** `concept_key="NOPE$"` → `KeyError`.

10. **`test_concept_has_no_parameters_block_raises`.** One-off fixture
    where the concept dict lacks `parameters`. `KeyError`.

11. **`test_empty_param_raises`.** `rule["param"] = ""` → `ValueError`
    matching `new_param.*param`.

12. **`test_missing_param_field_raises`.** Rule omits `"param"` entirely. `ValueError`.

13. **`test_empty_label_raises`.** `rule["label"] = ""` → `ValueError`
    matching `new_param.*label`.

14. **`test_empty_values_raises`.** `rule["values"] = []` → `ValueError`
    matching `new_param.*values`.

15. **`test_duplicate_value_labels_raise`.** `rule["values"]` contains
    two `{"label": "a", ...}` entries. `ValueError` whose message
    mentions duplicated value labels.

16. **`test_text_variable_without_formula_raises`.** `rule["text_variable"] = {"var": "F"}` (no `formula`). `ValueError`.

17. **`test_text_variables_block_auto_created`.** One-off fixture with
    a concept that has NO `text_variables` key at all. Rule supplies an
    axis + a `text_variable` block. After the call,
    `concept["text_variables"]` exists as a dict containing exactly the
    new var. (Pins the "auto-create missing block" semantic.)

18. **`test_template_patch_unknown_field_raises`.** Patch's `field` is
    `"DESCRIPCION"`. `ValueError` whose message names the field and the
    accepted values.

19. **`test_field_case_normalization_for_template_patches`**
    (parametrised over `TEXTO`, `texto`, `Texto`, `tExTo`). All four
    produce byte-identical `out` dicts and yield exactly one
    `Modification` whose `Modification.var` and `Modification.param`
    are correctly populated. (Note: `Modification.field` is `None` for
    PD — the patch's field doesn't propagate to the audit record; full
    detail is in the rule payload.)

20. **`test_orchestrator_routes_through_dispatch`.** Call
    `mutator.apply_new_param` (the orchestrator, imported as
    `orchestrator_apply_new_param`) with an axis-only rule. Assert:
    - The new axis lands on the returned `out`.
    - The caller's input dict is byte-identical via
      `json.dumps(..., sort_keys=True, ensure_ascii=False)` pre/post.
    - The emitted `Modification` carries the expected fields.

21. **`test_wrong_layer_rule_raises_valueerror`.** Pass a non-PD rule
    (e.g., `{"type": "paraphrase", ...}`) through the orchestrator.
    `ValueError` from `_gate_layer`. (Note: this also lives in
    `test_mutator.py` as `test_wrong_layer_rule_on_new_param_raises_valueerror`;
    re-asserting here keeps `test_layer_pd.py` self-contained as a
    contract suite.)

22. **`test_modification_has_exactly_one_entry`.** Even when the rule
    touches all four blocks (axis + text_variable + 2 template_patches),
    the log contains exactly one `Modification`. Pins the
    "one rule → one Modification" contract.

23. **`test_caller_dict_unchanged_after_apply`.** Snapshot via
    `json.dumps(stage_json, sort_keys=True, ensure_ascii=False)`, call
    `orchestrator_apply_new_param` with a well-formed full-combo rule,
    take a fresh snapshot. The two strings are identical (the outer
    `apply_new_param` orchestrator deep-copies its input).

**Acceptance**

- The new file contributes at least 18 test cases. More is fine; less is
  not. (The list above totals 23 — covers parametrisations.)
- `pytest tests/synthetic/test_layer_pd.py -q` exits 0 with no skips.

---

### Task 4 — Delete obsolete stub-test scaffolding from `test_mutator.py`

Surgical edits to [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):

1. **Delete** the `_LAYER_TO_APPLY` mapping, `_STUB_TYPES` list, and the
   `@pytest.mark.parametrize("mtype", _STUB_TYPES)`-decorated
   `test_each_stub_raises_notimplemented_with_type_code` function. These
   all assumed at least one stub remained; after B4 the parametrised
   list is empty and pytest would emit a `PytestCollectionWarning` ("no
   tests collected for this parameter list").
2. **Delete** `test_deep_copy_purity_on_notimplemented`. Its assertion
   (`apply_new_param` raises `NotImplementedError` while leaving the
   input dict unchanged) is now meaningless — `apply_new_param` no
   longer raises `NotImplementedError`. Caller-purity on the *successful*
   PD path is covered by `test_layer_pd.py::test_caller_dict_unchanged_after_apply`.
3. **Drop the now-unused imports** `Layer` and `TYPE_TO_LAYER` from the
   `from synthetic.taxonomy import …` line. Keep `ModificationType` (still
   used by `test_wrong_layer_rule_on_new_param_raises_valueerror`'s
   assertion isn't `Mtype`-typed; double-check: actually
   `ModificationType` is unused too if the parametrised stub test goes
   — verify on edit and prune accordingly).
4. **Add a new audit test** at the bottom of the file:
   ```python
   def test_no_stubs_remain_in_dispatch():
       """After Sprint 10 every _DISPATCH entry is a real mutator."""
       assert all(fn.__name__.startswith("apply_") for fn in _DISPATCH.values())
       assert not any(fn.__name__.startswith("_stub_") for fn in _DISPATCH.values())
   ```

**Acceptance**

- `pytest tests/synthetic/test_mutator.py -q` exits 0. Test count
  shrinks from 10 (Sprint 09 baseline: 4 signature tests + dispatch
  table + 1 parametrised stub case + wrong-layer ×2 + unknown-type +
  deep-copy-purity) to **9** (4 signature + dispatch table size +
  wrong-layer ×2 + unknown-type + new audit). Net delta for this file:
  −2 (parametrised stub + deep-copy-purity removed) + 1 (audit added) = −1.
- No new external dependencies introduced.
- `Layer` / `TYPE_TO_LAYER` / `ModificationType` imports are pruned if
  unused after the deletions.

---

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 10 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: files
   created/edited, the test-count delta (99 → expected ~115+), the
   dispatcher audit result (`12 live, 0 stubs`), the rule schema
   decisions (`param`-collision check, optional `text_variable` with
   block-auto-create, optional `template_patches` reusing L3
   semantics, single `Modification` per rule overloading `param` /
   `new` / `var`), the structural divergence from L1/L2/L3 (no
   "wrappers, one worker" fan-out — single function per layer, one
   type), the import-alias workaround for the orchestrator name clash,
   any deviations from this sprint file, and a one-line next-step
   recommendation (B5 → `composition.py` for stacking-rule encoding).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for `src/synthetic/layer_pd.py` in the "New Files in
     This Branch" block, with a one-line annotation matching the Sprint
     07–09 entries' shape (e.g., "✅ Sprint 10 — Task B4 —
     apply_new_param body; cross-block edits (parameters +
     text_variables + template_patches) in one rule; param/var
     collision raises `ValueError`; template patches reuse L3
     uniqueness-by-substring contract; last stub removed from
     `mutator.py`").
   - Prepend a new "After Sprint 10 — …" entry to the Sprint History
     section following the Sprint 07–09 template.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md)
   or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Their content
   stands; the protocol's B4 entry simply becomes "done".

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥115 passed** (99 from Sprint 09 − 2 retired
`test_mutator.py` cases + 18 minimum new PD contract cases + 1 new audit
test = 116 minimum). Zero failures, zero skips. If Task 3 lands the
recommended 23 cases (counting parametrisations), the total is 99 − 2 +
23 + 1 = **121**.

> ⚠ **Plan-self-consistency cross-check** (carried over from Sprints
> 07–09): the verification arithmetic uses the **minimum** new-test
> count (18 for Task 3 + 1 for Task 4's audit), not the recommended
> list count (23 cases including parametrisations). The binding gate
> is "≥18 new PD contract cases, all green, no skips, no regressions
> in the surviving baseline"; the headline pytest number depends on
> how many `test_layer_pd.py` cases the implementer chooses to write.
> Update the RESEARCH_LOG entry with the actual count.

Smoke checks (PowerShell-friendly one-liners — large quoted strings
should be written to a temp `.py` and run via `python file.py` to avoid
PowerShell single-quote escaping pain, per Sprints 08–09's lesson):

```powershell
python -c "from synthetic.layer_pd import apply_new_param; print('imports ok')"

python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import ModificationType; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in ModificationType); assert len(_DISPATCH) == 12; print('dispatcher fully promoted:', len(_DISPATCH), 'live, 0 stubs')"

python -c "from synthetic.mutator import _stub_new_param" 2>&1 | findstr ImportError
```

End-to-end smoke (write to `_smoke_pd.py` then run, then delete):

```python
import json
from synthetic.mutator import apply_new_param

s = {
    "OEB020$": {
        "parameters": {
            "A": {"label": "Nº TUBOS", "values": [{"label": "a", "value": "1"}]},
        },
        "text_variables": {},
        "resumen": "Canalización hormigonada de $A T, PVC 110 mm.\\",
        "texto":   "\\Canalización hormigonada de $A tubos. Final.",
    }
}
snap = json.dumps(s, sort_keys=True, ensure_ascii=False)

rule = {
    "type": "new_param",
    "param": "F",
    "label": "CALIDAD ACABADO",
    "values": [
        {"label": "a", "value": "Estándar"},
        {"label": "b", "value": "Premium"},
    ],
    "text_variable": {
        "var": "F",
        "formula": '"estándar" * (%F=="a") + "premium" * (%F=="b")',
    },
    "template_patches": [
        {"field": "TEXTO", "original": "tubos. Final.", "new": "tubos, calidad $F. Final."},
    ],
}

out, log = apply_new_param(s, "OEB020$", rule)

assert json.dumps(s, sort_keys=True, ensure_ascii=False) == snap, "caller dict mutated"

assert out["OEB020$"]["parameters"]["F"]["label"] == "CALIDAD ACABADO"
assert out["OEB020$"]["text_variables"]["F"].startswith('"estándar"')
assert "calidad $F" in out["OEB020$"]["texto"]
assert out["OEB020$"]["resumen"] == "Canalización hormigonada de $A T, PVC 110 mm.\\"

assert len(log) == 1
assert log[0].param == "F"
assert log[0].new == "CALIDAD ACABADO"
assert log[0].var == "F"
assert log[0].status == "applied"

print("end-to-end ok")
```

End-of-sprint expected `git status --short` (sprint-scoped subset only):
```
new file:   src/synthetic/layer_pd.py
modified:   src/synthetic/mutator.py
new file:   tests/synthetic/test_layer_pd.py
modified:   tests/synthetic/test_mutator.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_10.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`,
`configs/`, or `docs/synthetic/*.md` (except the two log files) should
appear.

---

## Design notes worth committing to memory

- **PD breaks the "wrappers, one worker" pattern — deliberately.** L1
  has six wrappers + one worker; L2 has three + one; L3 has two + one.
  PD has **one** type, so it has one function. Forcing a private
  `_install_new_param` worker + a thin `apply_new_param` wrapper would
  add zero structural benefit (no fan-out to compress) and would
  obscure that PD is genuinely different. Keep the single-function
  surface and document the divergence.
- **The orchestrator/worker name clash is real and the alias is the
  fix.** `apply_new_param` is simultaneously the orchestrator's name
  (top-level in `mutator.py`) and the natural name for the layer
  worker (matching `apply_omission` / `apply_paraphrase` / etc.).
  Renaming the worker (`apply_new_param_axis`, `install_new_param`)
  would break naming symmetry with L1/L2/L3; renaming the orchestrator
  would break the public dispatcher surface. The
  `from .layer_pd import apply_new_param as _layer_pd_apply_new_param`
  alias resolves the clash with a one-line import — preferred over both
  renames.
- **PD `add` semantics replace L1/L2/L3 `replace` semantics — collisions
  raise.** A `new_param` rule that targets a `param` key already present
  on the concept is a catalog-authoring error (the variant proposer in
  Phase C should never emit it). The applier raises `ValueError`
  loudly, exactly like L2's "lookup-table-list" raise. The cost of
  silent overwrite (a Phase D run silently destroys an existing axis)
  vastly outweighs the cost of a loud failure that the variant catalog
  reviewer must investigate.
- **`text_variables` block auto-creation is the only "create-on-write"
  path in PD.** A stage-2 concept legitimately may have no
  `text_variables` (every template token is a direct `$A`/`$B` axis
  reference). When the rule supplies a `text_variable` block, the
  worker creates `concept["text_variables"] = {}` and inserts the new
  var. This is asymmetric with `parameters` (which MUST already exist —
  the worker raises if missing): the rationale is "a concept without
  parameters isn't parametric, so PD has nothing to mutate; a concept
  without text_variables is fine, PD can install the first one".
- **Template patches reuse the L3 substring-uniqueness contract.** The
  patch list is a thin wrapper around N L3-style `(field, original,
  new)` rewrites. The worker MAY refactor to call
  `layer_l3._replace_substring` directly per patch (modulo the
  `Modification` log — L3's worker emits a per-patch Modification, but
  PD wants one Modification total). To keep "one rule → one
  Modification" clean and avoid coupling layer_pd to layer_l3's
  private worker, **reimplement** the patch loop inline in
  `apply_new_param` rather than reusing `_replace_substring`. The patch
  validation logic (string-non-empty, field-resolve, count, replace) is
  ~10 lines duplicated; the duplication is preferable to importing a
  private symbol or restructuring L3's emit-Modification contract.
- **`template_patches` apply in submission order; later patches may
  fail if earlier patches rewrote their region.** This is the
  intentional semantic-blind contract — patch ordering is the rule
  author's responsibility, exactly like the L3 stacked-rule contract.
  No reordering, no "skip + log"; if a patch's `original` no longer
  matches because an earlier patch in the same rule rewrote that
  region, raise `KeyError`. Phase C's variant proposer is responsible
  for ordering patches such that each match site survives.
- **One `Modification` per rule, even when 3+ blocks were edited.** The
  `Modification` dataclass overloads its fields for PD: `param`=new
  axis key, `new`=new axis label, `var`=new var key if any.
  `values`/`formula`/per-patch detail does NOT fit in the dataclass —
  it lives in the rule payload, which the variant catalog (Phase C4)
  stores alongside the `Modification`, and which the metadata-join
  (Phase E1) reconstructs the per-item metadata from. Maintaining
  "one rule → one Modification" uniformly across all 12 types is more
  valuable than capturing every PD edit in the dataclass — the
  alternative (Modification ranges or sub-records) would couple the
  audit schema to per-type structure and ripple through Phase E.
- **`new_param_allowlist.yaml` is a Phase C/E concern, not Phase B.**
  The applier doesn't know which axes are "admissible" for which
  concept group. The variant proposer (Phase C) consults the allowlist
  before emitting a `new_param` rule; the reviewer harness (Phase E)
  enforces the allowlist as part of the 100% manual-review pass that
  the protocol (`§5 Phase B`, risk register) requires for `new_param`.
  Phase B's applier remains semantic-blind.
- **Sprints 07–09's plan-arithmetic note carries over.** The
  verification runbook's expected pytest count uses the minimum
  new-test count (18 + 1) as the binding gate; the recommended list
  count (23 + 1 cases counting parametrisations) is the headline. The
  RESEARCH_LOG entry should record the actual count, not the planned
  count.
- **After this sprint, `_STUB_TYPES = []` and the parametrised stub
  test is gone.** Plus `test_deep_copy_purity_on_notimplemented`. Both
  scaffolds existed only because Sprints 01 → 06 set up stubs that
  Sprints 07–10 promoted one layer at a time. With B4 closing, Phase
  B's mutator-body work is **done**; Phase B5 (composition rules)
  switches to a different kind of code (stacking-rule encoder, no new
  per-type mutators).

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context,
  file map, stage-hook integration note (the PD entry now becomes live).
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.2 (12-type
  taxonomy table — `new_param` is row 12), §2.3 (`Modification` schema —
  the worked example covers only L1/L2/L3 fields; PD overloads as
  described above), §6 Open Questions Q4 (`new_param` design
  constraints — controlled allowlist deferred to Phase C/E).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.3
  (three-layer mutation interface + PD row), §3.5 (PD task row), §5
  Phase B (B4 task definition), §6 risk register (`new_param`
  collisions → manual review + allowlist).
- [`SPRINT_07.md`](SPRINT_07.md) — the L1 template this sprint
  diverges from. The "N wrappers, one worker" pattern that does NOT
  apply here, and the dispatcher-wiring recipe (import block +
  `_DISPATCH` swap + stub deletion) that DOES apply.
- [`SPRINT_08.md`](SPRINT_08.md) — the L2 template adapted for
  formula-fragment addressing. The PowerShell escaping lesson (write
  end-to-end smoke checks to a temp `.py` file) carries forward.
- [`SPRINT_09.md`](SPRINT_09.md) — the L3 template adapted for
  template-substring addressing. The `(field, original)`-uniqueness
  contract is reused inside PD's `template_patches` loop. The
  field-case-normalisation pattern is reused for PD's patch fields.
- [`src/synthetic/layer_l3.py`](../../src/synthetic/layer_l3.py) — the
  closest semantic neighbour for the template-patch sub-component. PD
  intentionally re-implements (not re-imports) the patch validation +
  apply loop to avoid coupling to L3's private worker and to preserve
  the "one rule → one Modification" contract.
- [`src/s03_generate_parametric_combinations.ipynb`](../../src/s03_generate_parametric_combinations.ipynb)
  — the downstream consumer of the mutated stage-2 JSON. Important for
  understanding why the new axis must follow the existing
  `{label, values: [{label, value}]}` shape: s03's Cartesian-product
  expander walks `concept["parameters"][axis_key]["values"]` and
  composes leaf keys from `axis_key + value_label`. A PD rule that
  emits a malformed `values` list (missing `label` or `value` on an
  entry) will silently corrupt the leaf-key derivation; the worker's
  per-entry validation is what catches this at apply-time.

---

## Non-goals reminder

If you find yourself opening any `.ipynb` file, anything under `data/`,
`configs/`, or `src/utils/`, anything in `src/synthetic/composition.py`
/ `llm_proposer.py` / `prompts/`, `configs/synthetic/new_param_allowlist.yaml`,
or writing Spanish new-axis heuristics / value-list generators /
collision-by-semantics detectors inside `layer_pd.py` — **stop**.
That's outside Sprint 10. Either the work belongs to a future sprint
(B5+, C1+, D1+) or it should be raised as a clarifying question in
`RESEARCH_LOG.md` before being addressed.

If you find yourself splitting the PD `Modification` into one record
per edited block (one for the axis, one for the text variable, one per
template patch) — also **stop**. That's a deliberate B4 non-goal; the
"one rule → one Modification" contract is uniform across all 12 types
and the variant catalog's rule payload carries the full delta. Bring
up audit-schema redesign as a future-sprint candidate (likely a
Phase E1 metadata-join discussion, not Phase B) before changing the
emit shape.

If you find yourself reusing L3's `_replace_substring` private worker
inside PD's `template_patches` loop — also **stop**. That couples
`layer_pd.py` to `layer_l3.py`'s private surface and forces a choice
between L3's per-patch `Modification` emission and PD's
one-Modification-per-rule contract. The ~10 lines of patch-validation
duplication is the deliberate price of contract isolation;
re-implement inline.

If you find yourself adding a `new_param_allowlist` lookup, an
existing-axes-semantic-similarity check, or any kind of "is this new
axis sensible for this concept" gate inside `layer_pd.py` — also
**stop**. That's a Phase C (variant proposer) and Phase E (reviewer
harness) concern. Sprint 10's applier is semantic-blind, exactly like
Sprints 07–09's L1/L2/L3 appliers.

If you find yourself renaming the orchestrator `apply_new_param` in
`mutator.py` to avoid the import clash with the layer-pd worker —
also **stop**. The orchestrator's name is part of the public
dispatcher surface (`apply_l1`/`l2`/`l3`/`apply_new_param`); renaming
it ripples through `tests/synthetic/test_mutator.py`, `CLAUDE_SYNTHETIC.md`'s
stage-hook integration note, and any future Phase D orchestrator
that depends on the four-function entry surface. The import alias
(`from .layer_pd import apply_new_param as _layer_pd_apply_new_param`)
is the strictly-smaller change.
