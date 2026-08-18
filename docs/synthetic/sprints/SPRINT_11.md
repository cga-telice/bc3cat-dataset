# Sprint 11 — Phase B Task B5: composition rules (`composition.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 11                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | B5 — see [`../RESEARCH_PROTOCOL.md §5 Phase B`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 10 — `layer_pd.py` + B4 closes; all 12 mutators live (see [`SPRINT_10.md`](SPRINT_10.md))     |
| **Successor**   | Sprint 12 — Phase C Task C1 (`prompts/` — per-type Spanish prompt library) — TBD            |

---

## Context

Sprint 10 closed Task B4 by promoting the last surviving stub
(`_stub_new_param`) to a real body in
[`src/synthetic/layer_pd.py`](../../src/synthetic/layer_pd.py), landing at
**124/124 pytest pass** with `_DISPATCH` reporting **12 live, 0 stubs**
and the `_stub_*` prefix eliminated from `mutator.py`. Phase B's
*per-type mutator-body* work is complete. The remaining Phase-B task
is **B5 — composition rules**, which shifts the codebase from
per-type fan-out (six L1 wrappers, three L2 wrappers, two L3 wrappers,
one PD wrapper) to **cross-rule reasoning**: given a batch of rules to
apply to a single concept, decide *which can co-exist*, *in what order
they apply*, and *which must be skipped with a logged reason*.

The protocol's [`§5 Phase B B5`](../RESEARCH_PROTOCOL.md) row reads:

> **B5. Composition rules.** Encode which atomic mutations may stack on
> the same target (e.g., `unit_conversion` ∘ `num_to_text` requires an
> explicit ordering). Conflicts: skip + log via the `Modification` record.

and [`§3.3`](../RESEARCH_PROTOCOL.md) adds the ordering hint:

> Mutations from different layers compose by stacking: L1 mutations run
> first, then L2, then L3, then PD (or PD-first if the new axis affects
> L2/L3 — see §B5 composition rules).

The two layer-order statements are reconciled by Sprint 11: **PD runs
first, then L1 within the same stage-2 dict, then L2 at stage-3, then
L3 at stage-4** — because PD's job is to *add an axis* that subsequent
L1/L2/L3 rules in the same batch may reference. The protocol's "L1
first" framing in §3.3 was written before PD's cross-block edits were
specified in Sprints 04/10; reconciling it here pins the canonical
order for D1/D2 to consume.

Sprint 10's verification baseline: **124 passed**. Sprint 11 adds the
new `composition.py` module + its contract test suite (`test_composition.py`),
and a small wiring delta in `test_mutator.py` (one new import-audit
test). No changes to `mutator.py`'s `_DISPATCH`, the four orchestrator
functions, or any `layer_*.py` module. The composer is a **pure,
pre-apply validator** — the orchestrator decides when to consult it
(out of scope for B5; lives in D1/D2).

Net pytest delta target: **≥+20** new test cases from
`test_composition.py` + 1 new audit in `test_mutator.py` = **≥145
passed** total. Zero failures, zero skips, zero changes to surviving
tests.

---

## Scope

### In scope
- **B5** — `src/synthetic/composition.py` (new): one public function
  `compose_rules(rules)` that returns
  `(admissible_rules_in_apply_order, skipped_modifications)`; one
  module-level constant `COMPATIBILITY_MATRIX: dict[tuple[ModificationType, ModificationType], CompatibilityVerdict]`
  expressing the pair-wise stacking table; one enum
  `CompatibilityVerdict(str, Enum)` with values `COMPATIBLE`,
  `SAME_TARGET`, `LAYER_DEPENDENCY`, `UNSTACKABLE`; one private helper
  `_canonical_key(rule)` computing the per-rule addressing tuple used
  for same-target dedup.
- **Tests** — `tests/synthetic/test_composition.py` (new, ≥20 cases)
  covering layer-ordering, same-target dedup per layer (L1/L2/L3/PD),
  cross-layer compatibility, PD-vs-L1 same-axis interaction,
  empty-input edge case, single-rule pass-through, skipped-record
  shape, and idempotence under re-composition.
- **Wire-in audit** — one new test in
  [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):
  `test_composition_module_exposes_compose_rules` asserts that
  `synthetic.composition.compose_rules` exists and has signature
  `(rules: list[dict]) -> tuple[list[dict], list[Modification]]`. This
  is the *only* edit to `test_mutator.py`; no changes to the surviving
  9 tests from Sprint 10.
- **Housekeeping** — Sprint 11 entry in
  [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md); flip ❌ → ✅ for
  `src/synthetic/composition.py` in
  [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files in
  This Branch" block; prepend "After Sprint 11 — …" history entry.

### Out of scope (explicit)
- **`configs/synthetic/composition_rules.yaml`** — the protocol's
  file-tree listing reserves this path for a YAML mirror of the
  matrix. Sprint 11 keeps the matrix as a **Python module-level
  constant** in `composition.py` (source of truth). YAML
  externalization is deferred to a future sprint *if and when* Phase C
  / Phase E tooling needs an editable surface without touching code.
  This is a deliberate deviation from the protocol's file-tree
  listing — document it in the RESEARCH_LOG entry and update the
  protocol's `§5 Phase B B5` row at the end of the sprint to reflect
  "matrix lives in `composition.py` for B5; YAML extraction is a
  follow-up Phase E concern".
- **Wire-in to `mutator.py`'s `_DISPATCH` / `_apply_rules`** —
  composition.py is a **pre-apply** validator, not a runtime
  dispatcher. The orchestrator's `_apply_rules` continues to iterate
  rules in submission order without consulting the composer. The
  decision of *where* to invoke `compose_rules` (in D1's stage hooks
  before each layer runs? in D2's batch orchestrator? in C3's variant
  proposer?) is a Phase C/D concern — Sprint 11 lands the composer as
  an importable function with a verified contract, no behavioural
  change to existing orchestrator semantics.
- **Stage-2/3/4 JSON inspection** — the composer is **state-blind**.
  It validates a list of rules against the matrix without ever
  looking at the concept's stage JSON. A rule's `param` clash with an
  *existing* axis on the concept (not introduced by a PD rule in the
  same batch) is caught at apply-time by the per-layer worker, not by
  the composer. The composer's job is **rule-vs-rule** consistency,
  not rule-vs-data consistency.
- **Dynamic substring-collision detection on L3 patches.** Two L3
  rules with non-overlapping `original` substrings may still
  interfere if one's rewrite consumes the other's match site. The
  composer does **not** simulate the patches; the L3 worker's
  `template.count(original) == 1` check at apply-time is the
  authoritative guard. Sprint 11 ships only the static, by-key
  uniqueness check.
- **Composition with the variant-catalog's nested `modifications`
  field.** Phase E1's metadata-join consumes both the catalog payload
  *and* the per-rule `Modification` log emitted by the layer workers
  — that integration is E1's responsibility. The composer's
  `skipped_modifications` list carries enough audit detail
  (`type`, `layer`, `status="skipped"`, `reason`) to feed into E1's
  join, but Sprint 11 does not change the `Modification` dataclass.
- **Per-concept group rules.** The composer treats every rule as
  applying to *one* concept (the orchestrator's `concept_key`
  argument). Cross-concept stacking rules (e.g., "no two synthetic
  variants of the same concept may share the identical mutation
  set") are a Phase C4 variant-catalog concern, not a B5 concern.
- **LLM-output validation.** Phase C3's variant proposer is
  responsible for emitting well-formed `Modification`-shaped rules;
  the composer assumes the rules already have `type`, `layer` (via
  `TYPE_TO_LAYER[ModificationType(rule["type"])]`), and any
  addressing fields required by their type. Malformed rules surface
  via the existing per-layer worker's `ValueError` / `KeyError`,
  not via the composer. The composer raises `ValueError` for
  *unknown type codes* only — same loose contract as
  `mutator._resolve_type`.
- **Anything under `data/`, `configs/`, `src/utils/`, or any
  notebook.** Tests run inline; no disk I/O. No path-refactor work,
  no Generate_OEB changes, no s03/s04/s05 changes.

---

## Compatibility matrix — design

### Canonical addressing key

Each rule has a **canonical key** capturing what it addresses. Two
rules with the same canonical key conflict by *same-target*
(later one skipped, reason names the duplication).

| Layer | Canonical key                                                                                  |
|:-----:|------------------------------------------------------------------------------------------------|
| **L1** | `(Layer.PARAM_VALUE, rule["param"], rule["value"])`                                          |
| **L2** | `(Layer.TEXT_VARIABLE, rule["var"].lstrip("$"), _norm_cond(rule["condition"]))`              |
| **L3** | `(Layer.TEMPLATE, rule["field"].lower(), rule["original"])`                                  |
| **PD** | `(Layer.PARAM_DEFINITION, rule["param"])`                                                    |

Where `_norm_cond(s)` is the same whitespace-collapsing helper
[`src/synthetic/layer_l2.py`](../../src/synthetic/layer_l2.py)
uses (`re.sub(r"\s+", " ", s).strip()`). The composer reuses this
helper rather than re-implementing it — small, semantic-stable,
and the symmetry with L2's addressing keeps a single source of
truth for "what counts as the same condition string". Import via
`from .layer_l2 import _norm as _norm_cond`.

### Pair-wise verdict enum

```python
class CompatibilityVerdict(str, Enum):
    COMPATIBLE = "compatible"
    SAME_TARGET = "same_target_conflict"
    LAYER_DEPENDENCY = "layer_dependency_conflict"
    UNSTACKABLE = "unstackable"
```

- **`COMPATIBLE`** — Default. Two rules of different layers, or two
  rules of the same layer with distinct canonical keys.
- **`SAME_TARGET`** — Two rules with identical canonical keys. *Always*
  the later rule skipped — independent of type pair. (Two
  `synonym_label` rules on the same `(A, "a")`: second clobbers first.
  Two `omission`s on the same `(TEXTO, " $I,")`: second's `original`
  no longer matches because first's `new` overwrote it. Two `new_param`
  rules introducing axis `F`: second collides with first's install.)
- **`LAYER_DEPENDENCY`** — A pair where applying rule A *creates the
  surface* that rule B addresses, or *destroys* it. For Sprint 11 the
  only encoded case is **`new_param` introducing axis K + any L1 rule
  on `param=K`**: the L1 rule's `(param, value)` addressing key
  presumes the axis already exists, but the PD rule installs it in
  the same batch. Variant proposers should issue one or the other,
  never both. Skip the L1 rule (PD's installation is the more
  interesting variant); reason names both rule type codes.
- **`UNSTACKABLE`** — A pair that is *structurally* incompatible
  regardless of addressing. Reserved for future use (none in the
  Sprint 11 starter matrix). Sprint 11 ships the enum value for
  schema completeness so future sprints don't need to extend the
  enum to add categories.

### Starter matrix

The Sprint 11 starter matrix encodes only the **structural**
constraints — same-target dedup falls out of canonical-key
comparison, so the matrix itself stays sparse. Entries below are
the *non-COMPATIBLE* pairs; all unlisted pairs default to
`COMPATIBLE` (looked up via `dict.get(pair, CompatibilityVerdict.COMPATIBLE)`).

```python
COMPATIBILITY_MATRIX: dict[
    tuple[ModificationType, ModificationType],
    CompatibilityVerdict,
] = {
    # PD introducing an axis vs L1 rule on the same axis — only the
    # PD survives. Detected dynamically (the L1 rule's `param`
    # matches the PD rule's `param`), so the matrix is consulted
    # AFTER the canonical-key dedup pass and AFTER the
    # PD-axis-vs-L1-param same-axis pass.
    (ModificationType.NEW_PARAM, ModificationType.SYNONYM_LABEL):    CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.NUM_TO_TEXT):       CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.UNIT_CONVERSION):   CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.UNIT_EXPANSION):    CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.ABBREV_EXPANSION):  CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.CODE_EXPANSION):    CompatibilityVerdict.LAYER_DEPENDENCY,
}
```

The matrix is **directional** (the tuple `(NEW_PARAM, SYNONYM_LABEL)`
means "NEW_PARAM-first; SYNONYM_LABEL-second is the conflict"). The
composer normalises lookup by *sorting rules into canonical layer
order first*, then iterating pairs in that order — so the matrix
key is always `(earlier_layer_type, later_layer_type)`. This avoids
the combinatorial doubling of a symmetric matrix.

The matrix is intentionally **minimal** for Sprint 11. Most
real-world conflicts surface through canonical-key dedup
(SAME_TARGET) without needing matrix entries. The `LAYER_DEPENDENCY`
entries above are the only cases where two rules with *different*
canonical keys still conflict (the PD rule's key is
`(PARAM_DEFINITION, "K")`, the L1 rule's is `(PARAM_VALUE, "K", "a")`
— different keys but the L1 rule presumes the axis the PD rule is
installing).

### Apply-order

The composer returns rules in this canonical order:

1. All **PD** rules (in submission order).
2. All **L1** rules (in submission order).
3. All **L2** rules (in submission order).
4. All **L3** rules (in submission order).

Within each layer, rules apply in the order the variant proposer
emitted them. Stable; deterministic; reproducible. The orchestrator's
existing `_apply_rules` iterates the composer's output in this
order, so the rule batch lands deterministically regardless of how
the proposer emitted them.

---

## Tasks

### Task 1 — `src/synthetic/composition.py`

Create [`src/synthetic/composition.py`](../../src/synthetic/composition.py).
Module surface:

```python
"""Composition rules — pre-apply validator for rule batches.

Given a list of rules destined for the same concept, decides which
are mutually compatible, what order they apply in, and which must
be skipped with a logged reason. State-blind: never inspects the
concept's stage JSON. Rule-vs-rule consistency only; rule-vs-data
consistency is enforced at apply-time by the per-layer worker.

The composer is a pure function: same input → same output. It does
not mutate either input or output rule dicts; the returned
`admissible_rules_in_apply_order` is a fresh `list` aliasing the
input rule dicts (shallow copy of the list, the dict elements are
the same objects).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from .layer_l2 import _norm as _norm_cond
from .taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER


class CompatibilityVerdict(str, Enum):
    COMPATIBLE = "compatible"
    SAME_TARGET = "same_target_conflict"
    LAYER_DEPENDENCY = "layer_dependency_conflict"
    UNSTACKABLE = "unstackable"


_LAYER_APPLY_ORDER: tuple[Layer, ...] = (
    Layer.PARAM_DEFINITION,
    Layer.PARAM_VALUE,
    Layer.TEXT_VARIABLE,
    Layer.TEMPLATE,
)


COMPATIBILITY_MATRIX: dict[
    tuple[ModificationType, ModificationType],
    CompatibilityVerdict,
] = {
    (ModificationType.NEW_PARAM, ModificationType.SYNONYM_LABEL):    CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.NUM_TO_TEXT):       CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.UNIT_CONVERSION):   CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.UNIT_EXPANSION):    CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.ABBREV_EXPANSION):  CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.CODE_EXPANSION):    CompatibilityVerdict.LAYER_DEPENDENCY,
}


def _canonical_key(rule: dict[str, Any]) -> tuple:
    """Per-rule addressing tuple used for same-target dedup."""
    ...


def compose_rules(
    rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Modification]]:
    """Sort `rules` into PD→L1→L2→L3 order, deduplicate by canonical
    key, then check pairs against COMPATIBILITY_MATRIX. Returns the
    admissible rules in apply order plus a `Modification` log of
    skipped rules.
    """
    ...
```

#### Behavioural requirements

1. **Type resolution.** For each rule, resolve `mtype =
   ModificationType(rule["type"])` and `layer = TYPE_TO_LAYER[mtype]`.
   An unknown `rule["type"]` raises `ValueError(f"unknown modification
   type: {rule['type']!r}")` — same contract as
   `mutator._resolve_type`. A rule missing the `"type"` key raises
   `KeyError` (no `rule.get("type")` softness; the composer treats
   "no type" as malformed input, not as a skip candidate).
2. **Layer sort.** Stable-sort the rules by `_LAYER_APPLY_ORDER.index(layer)`.
   Within each layer the submission order is preserved. The result
   is a `list[(mtype, layer, rule)]` triple list used by the
   downstream passes; the public return value strips the metadata
   and yields the bare rule dicts.
3. **Canonical-key dedup pass.** Walk the sorted list. For each rule,
   compute `_canonical_key(rule)`. If the key has been seen in any
   earlier rule, emit
   `Modification(type=<rule's mtype>, layer=<rule's layer>,
   status="skipped",
   reason=f"same_target_conflict with earlier rule at canonical key {key!r}")`
   to the skipped log and drop the rule from the admissible list.
   First-write-wins.
4. **`_canonical_key` per-layer logic.**
   - `Layer.PARAM_VALUE`: `(Layer.PARAM_VALUE, rule["param"], rule["value"])`.
   - `Layer.TEXT_VARIABLE`: `(Layer.TEXT_VARIABLE, rule["var"].lstrip("$"), _norm_cond(rule["condition"]))`.
   - `Layer.TEMPLATE`: `(Layer.TEMPLATE, rule["field"].lower(), rule["original"])`.
   - `Layer.PARAM_DEFINITION`: `(Layer.PARAM_DEFINITION, rule["param"])`.
   Missing addressing fields raise `KeyError` with a message naming
   the field — same loose contract as type resolution.
5. **PD-axis-vs-L1-param same-axis pass.** After dedup, walk the
   surviving rules. For each L1 rule (`layer == Layer.PARAM_VALUE`),
   check whether any earlier-admissible PD rule
   (`layer == Layer.PARAM_DEFINITION`) has `pd_rule["param"] ==
   l1_rule["param"]`. If yes, skip the L1 rule with
   `reason=f"layer_dependency_conflict: param {l1_rule['param']!r} "
   f"introduced by new_param rule in same batch"`. This pass is
   independent of the matrix — it is a *runtime* property of the
   rule pair, not a static type-pair property. (The matrix entry
   for `(NEW_PARAM, SYNONYM_LABEL)` etc. expresses the **policy**;
   this pass implements the **detection**.)
6. **Matrix pass.** For each pair `(earlier_rule, later_rule)` in
   surviving-admissible order (later_rule must come strictly later
   in the apply-ordered list), look up
   `COMPATIBILITY_MATRIX.get((earlier_mtype, later_mtype),
   CompatibilityVerdict.COMPATIBLE)`. If the verdict is not
   `COMPATIBLE`, skip the later rule with
   `reason=f"{verdict.value}: {earlier_mtype.value} stacked with "
   f"{later_mtype.value}"`. **But:** if the verdict is
   `LAYER_DEPENDENCY` and step 5 already handled the pair, the
   matrix pass is a no-op for that pair (avoid double-skipping the
   same rule). Sprint 11's starter matrix puts all
   `LAYER_DEPENDENCY` entries on `(NEW_PARAM, L1-type)` pairs that
   the same-axis pass also catches — so in practice the matrix
   pass is empty-effect for the starter content. The matrix exists
   for *future extension* (e.g., adding `UNSTACKABLE` entries for
   `OMISSION` + `REORDER` if research uncovers structural
   incompatibilities).
7. **Return shape.** `(admissible_rules, skipped_modifications)` —
   the first list is in PD→L1→L2→L3 apply order with the original
   rule dicts (not copies); the second list is in skip-detection
   order (which is also the apply-order traversal order). Empty
   input → `([], [])`.
8. **No mutation of input.** The composer is pure: neither the
   input `rules` list nor any rule dict is modified. The output
   list is a fresh `list`. Verified by an inline assert at the end
   of `compose_rules` is **out of scope** — the contract is verified
   by tests, not by runtime guards.

#### Acceptance

- `from synthetic.composition import compose_rules, COMPATIBILITY_MATRIX, CompatibilityVerdict` succeeds.
- `inspect.signature(compose_rules).parameters` is exactly `["rules"]`
  and the return-type annotation is
  `tuple[list[dict[str, Any]], list[Modification]]`.
- `compose_rules([])` returns `([], [])`.
- `compose_rules([r])` for any well-formed `r` returns `([r], [])`.
- A 4-rule batch with one rule per layer in **reverse** submission
  order (L3 first, L2, L1, PD last) returns the rules in
  PD→L1→L2→L3 order with empty skipped log.
- A 2-rule batch with two `synonym_label` rules on the same
  `(param, value)` returns the first rule + one skipped
  `Modification` for the second.
- A 2-rule batch with one PD rule introducing axis `K` and one L1
  `synonym_label` rule on `param="K"` returns the PD rule + one
  skipped `Modification` for the L1 rule with `reason` naming
  `layer_dependency_conflict`.
- A rule with `type="not_a_real_type"` raises `ValueError` whose
  message names the bad type code.
- A rule missing addressing fields (e.g., L1 rule without `value`)
  raises `KeyError`.

---

### Task 2 — `tests/synthetic/test_composition.py`: contract suite

Create [`tests/synthetic/test_composition.py`](../../tests/synthetic/test_composition.py).
≥20 cases covering ordering, dedup, cross-layer compatibility,
PD-vs-L1 detection, matrix-pass detection, and edge cases.

```python
import inspect

import pytest

from synthetic.composition import (
    COMPATIBILITY_MATRIX,
    CompatibilityVerdict,
    compose_rules,
)
from synthetic.taxonomy import Layer, Modification, ModificationType


def _r(mtype, **kwargs):
    return {"type": mtype.value, **kwargs}
```

Required test cases (≥20):

1. **`test_compose_rules_signature`** — exactly `["rules"]` parameter list.
2. **`test_empty_input_returns_empty_tuple`** — `compose_rules([])` → `([], [])`.
3. **`test_single_rule_passes_through_per_layer`** parametrised over
   one rule per layer (L1 `synonym_label`, L2 `paraphrase`, L3
   `omission`, PD `new_param`). Each returns `([rule], [])`.
4. **`test_layer_order_pd_l1_l2_l3`** — submit four rules in
   L3→L2→L1→PD order; assert returned order is PD→L1→L2→L3 by
   inspecting each rule's `type`.
5. **`test_stable_order_within_layer`** — submit three L1 rules
   (`synonym_label`, `num_to_text`, `unit_conversion`) on three
   different `(param, value)` pairs; assert returned order is the
   submission order.
6. **`test_same_target_dedup_l1`** — two `synonym_label` rules on
   the same `(A, "a")`; first survives, second skipped with
   `status="skipped"` and `reason` starting with `"same_target_conflict"`.
7. **`test_same_target_dedup_l1_across_types`** — `synonym_label`
   then `num_to_text` on the same `(A, "a")`. Both are L1, same
   canonical key → second skipped (different type, same target).
8. **`test_distinct_targets_no_conflict_l1`** — two `synonym_label`
   rules on `(A, "a")` and `(A, "b")` — distinct canonical keys,
   both admissible.
9. **`test_same_target_dedup_l2`** — two `paraphrase` rules on
   `(var="K", condition='%B=="a"')`; second skipped. Pin the
   `$`-strip + whitespace-collapse symmetry: rule 1 has
   `var="K"`, condition `'%B=="a"'`; rule 2 has `var="$K"`,
   condition `'%B  ==  "a"'` — both produce the same canonical
   key.
10. **`test_same_target_dedup_l3`** — two `omission` rules on
    `(field="TEXTO", original="$I,")`; second skipped. Test
    field-case symmetry: rule 1 has `field="TEXTO"`, rule 2 has
    `field="texto"`.
11. **`test_same_target_dedup_pd`** — two `new_param` rules with
    `param="K"`; second skipped with reason naming the
    `(PARAM_DEFINITION, "K")` canonical key.
12. **`test_pd_introduces_axis_l1_on_same_axis_skipped`** — PD rule
    `param="K"` + L1 `synonym_label` rule `param="K", value="a"`.
    PD admissible, L1 skipped with `reason` containing
    `"layer_dependency_conflict"` and naming the `"K"` axis.
13. **`test_pd_introduces_axis_l1_on_different_axis_no_conflict`** —
    PD rule `param="K"` + L1 rule `param="A", value="a"`. Both
    admissible.
14. **`test_pd_introduces_axis_all_six_l1_types_each_skipped`**
    parametrised over the six L1 `ModificationType`s. PD rule
    `param="K"` paired with each L1 type targeting `param="K"`.
    Asserts all six L1 rules skipped; PD survives in every case.
15. **`test_l2_on_var_pd_does_not_introduce_no_conflict`** — PD rule
    `param="K"` (with `text_variable={"var":"K","formula":"..."}`)
    + L2 `paraphrase` rule on `var="OTHER"`. Both admissible.
    (Note: B5's matrix does NOT encode PD-vs-L2 conflicts even when
    PD installs a new `text_variable` — L2 rules referencing the new
    var would only matter if L2's `condition` referenced it, and the
    canonical-key dedup catches *L2 vs L2 same-var* but not *PD's
    new-var vs L2's existing-var*. Document this as a Sprint 11
    boundary: PD-side `text_variable` block additions are
    `COMPATIBLE` with any L2 rule on a different var.)
16. **`test_mixed_layer_batch_no_conflicts`** — one rule per layer,
    all on different addressing keys. Returns 4 admissible, 0
    skipped, in PD→L1→L2→L3 order.
17. **`test_no_mutation_of_input_rules`** — submit a list and a deep
    copy snapshot. Call `compose_rules`. Assert the original input
    list and every rule dict in it are byte-identical to the
    snapshot. The composer must not mutate its input.
18. **`test_admissible_output_aliases_input_rules`** — the returned
    admissible rules are *the same dict objects* as the input
    rules (identity check via `is`), not deep copies. This pins
    the "no copying for performance; orchestrator's deep-copy is
    elsewhere" decision.
19. **`test_unknown_type_raises_valueerror`** — rule with
    `type="not_a_real_type"` → `ValueError` whose message names the
    bad code.
20. **`test_l1_rule_missing_value_raises_keyerror`** — rule with
    `type="synonym_label", param="A"` (no `value`) → `KeyError`
    naming `"value"`.
21. **`test_l2_rule_missing_condition_raises_keyerror`** — rule
    with `type="paraphrase", var="K"` (no `condition`) →
    `KeyError`.
22. **`test_l3_rule_missing_original_raises_keyerror`** — rule
    with `type="omission", field="TEXTO"` (no `original`) →
    `KeyError`.
23. **`test_pd_rule_missing_param_raises_keyerror`** — rule with
    `type="new_param"` only → `KeyError` naming `"param"`.
24. **`test_idempotent_under_recomposition`** — call
    `compose_rules` on a 6-rule mixed batch. Take the
    admissible-rules result and pass it back into
    `compose_rules`. Assert the second call returns the same
    admissible list with empty skipped log. Pins the
    "composition is a fixed-point operation" property.
25. **`test_compatibility_matrix_only_contains_known_pairs`** —
    audit: every key in `COMPATIBILITY_MATRIX` is a `(ModificationType,
    ModificationType)` tuple of valid enum members; every value is
    a `CompatibilityVerdict` member.
26. **`test_compatibility_matrix_starter_pd_l1_pairs`** — audit:
    the matrix contains exactly the six
    `(NEW_PARAM, L1-type)` entries listed in the sprint plan, all
    valued `LAYER_DEPENDENCY`. The audit pins the matrix's
    *starter content* — a future sprint that extends the matrix
    must explicitly update this test.

**Acceptance**
- The new file contributes ≥20 test cases (parametrisations count
  as one case each in test-count terms; the spec list above totals
  26 with parametrisations expanding to ~33 individual cases).
- `pytest tests/synthetic/test_composition.py -q` exits 0 with no
  skips.

---

### Task 3 — Add module-exposure audit to `test_mutator.py`

Surgical edit to
[`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py):

1. Add `from synthetic.composition import compose_rules` under the
   existing import block.
2. Add one new test at the bottom of the file (after
   `test_no_stubs_remain_in_dispatch`):
   ```python
   def test_composition_module_exposes_compose_rules():
       """B5 — composer is importable with the expected signature."""
       import inspect
       sig = inspect.signature(compose_rules)
       assert list(sig.parameters) == ["rules"]
   ```

The nine surviving Sprint-10 tests in `test_mutator.py` are unchanged.

**Acceptance**
- `pytest tests/synthetic/test_mutator.py -q` exits 0; test count
  grows from 9 (post-Sprint-10) to 10.

---

### Task 4 — Housekeeping

After Tasks 1–3 pass:

1. Append a Sprint 11 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: files
   created/edited, the test-count delta (124 → ≥145), the
   composer's surface (`compose_rules` + `COMPATIBILITY_MATRIX` +
   `CompatibilityVerdict` + `_canonical_key`), the
   PD→L1→L2→L3 apply order with the explicit reconciliation of
   protocol §3.3's ambiguous phrasing, the same-target dedup +
   layer-dependency pass + matrix pass three-pass design, the
   decision to keep the matrix as a Python constant rather than a
   YAML file (with rationale), any deviations from this sprint
   plan, and a one-line next-step recommendation (likely Phase C
   — C1 prompt library).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for `src/synthetic/composition.py` in the "New
     Files in This Branch" block. Annotation example: "✅ Sprint 11
     — Task B5 — `compose_rules` pre-apply validator;
     `COMPATIBILITY_MATRIX` Python constant (starter matrix: six
     `(NEW_PARAM, L1-type)` `LAYER_DEPENDENCY` entries);
     PD→L1→L2→L3 apply order; canonical-key dedup with
     L2-`$`-strip / whitespace-norm and L3-field-case symmetry;
     no `configs/synthetic/composition_rules.yaml` (matrix is the
     Python constant; YAML deferred)".
   - Prepend a new "After Sprint 11 — …" entry to the Sprint
     History section.
3. **Update the protocol's B5 row** at
   [`../RESEARCH_PROTOCOL.md §5 Phase B B5`](../RESEARCH_PROTOCOL.md)
   to reflect the YAML deferral. One-line edit: replace
   "Encode which atomic mutations may stack on the same target …"
   with the same sentence plus a postscript: "Matrix lives in
   `src/synthetic/composition.py` as a Python module-level
   constant for B5; YAML externalisation
   (`configs/synthetic/composition_rules.yaml`) deferred to a
   later phase if Phase C / E tooling needs an editable surface
   without code changes." Also: remove the
   `composition_rules.yaml                          # B5 stacking
   constraints` line from the file-tree listing at line 302, or
   change it to read "(deferred — matrix is in
   `src/synthetic/composition.py`)".
4. Do **not** modify
   [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md). The
   proposal's content stands; B5's protocol entry is the only doc
   that referenced the YAML.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥145 passed** (124 from Sprint 10 + 20 minimum new
composition cases + 1 new audit test = 145 minimum). Zero
failures, zero skips. If Task 2 lands all 26 listed cases (with
parametrisation expansion to ~33 individual cases), the total is
124 + 33 + 1 = **≥158**.

> ⚠ **Plan-self-consistency cross-check** (continuing the
> Sprint 07–10 convention): the binding gate is "≥20 new
> composition cases, all green, no skips, no regressions in the
> 124-pass baseline". The headline pytest number depends on how
> many `test_composition.py` cases the implementer chooses to
> write. Update the RESEARCH_LOG entry with the actual count.

Smoke checks (PowerShell-friendly one-liners; write multi-line
asserts to a temp `_smoke_compose.py` per the
Sprints 08–10 lesson):

```powershell
python -c "from synthetic.composition import compose_rules, COMPATIBILITY_MATRIX, CompatibilityVerdict; print('imports ok'); print('matrix size:', len(COMPATIBILITY_MATRIX))"

python -c "from synthetic.composition import compose_rules; out, log = compose_rules([]); assert out == [] and log == []; print('empty-input ok')"
```

End-to-end smoke (write to `_smoke_compose.py` then run, then
delete):

```python
from synthetic.composition import compose_rules
from synthetic.taxonomy import ModificationType

# 5 rules, intentionally out-of-order, with one same-target dup
# and one PD-vs-L1 same-axis dependency.
rules = [
    {"type": "omission",      "field": "TEXTO",  "original": "$I,",      "new": ""},                  # L3
    {"type": "paraphrase",    "var":   "K",      "condition": '%B=="a"', "new": "estandar"},          # L2
    {"type": "synonym_label", "param": "A",      "value": "a",            "new": "Uno"},               # L1
    {"type": "synonym_label", "param": "K",      "value": "a",            "new": "X"},                 # L1 — same axis as PD below
    {"type": "new_param",     "param": "K",      "label": "CALIDAD",      "values": [{"label": "a", "value": "Std"}]},  # PD
]
admissible, skipped = compose_rules(rules)

types_in_order = [r["type"] for r in admissible]
assert types_in_order == ["new_param", "synonym_label", "paraphrase", "omission"], types_in_order

assert len(skipped) == 1
assert skipped[0].type is ModificationType.SYNONYM_LABEL
assert "layer_dependency_conflict" in skipped[0].reason
assert "K" in skipped[0].reason

print("compose smoke ok — 4 admissible in PD→L1→L2→L3 order, 1 skipped (L1 on PD's axis)")
```

End-of-sprint expected `git status --short` (sprint-scoped subset
only):
```
new file:   src/synthetic/composition.py
new file:   tests/synthetic/test_composition.py
modified:   tests/synthetic/test_mutator.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_11.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`,
`configs/`. **No changes to `src/synthetic/mutator.py`**, **no
changes to any `layer_*.py`**, **no changes to `taxonomy.py`** —
B5 is additive in `src/synthetic/`.

---

## Design notes worth committing to memory

- **B5 is a *static* validator, not a runtime dispatcher.** The
  composer reads a rule list and returns a sorted-and-filtered rule
  list; it never reads stage JSON, never imports `_DISPATCH`, never
  invokes a layer worker. The orchestrator (D1/D2) is the consumer.
  This separation makes the composer trivially unit-testable
  without fixtures and makes the contract narrow enough that a
  Phase E reviewer can sanity-check skip decisions against the
  variant catalog without running the pipeline.
- **Layer apply-order reconciliation.** Protocol §3.3 says "L1
  first, then L2, L3, PD"; §B5 hints at "PD-first if the new axis
  affects L2/L3". Sprint 11 pins the canonical order as
  **PD → L1 → L2 → L3** and updates the protocol's §3.3 phrasing
  in the Sprint 11 housekeeping pass (see Task 4 step 3). The
  rationale: PD's job is to *add an axis*; L1's job is to *mutate
  values on an axis*. If a batch contains both, PD must run first
  to install the axis, otherwise L1's `(param, value)` addressing
  fails. The 4-layer order is one consistent rule; the
  conditional "PD-first only if the new axis affects L2/L3" framing
  is unnecessarily nuanced.
- **Canonical-key dedup is the workhorse; the matrix is the
  exception list.** Most real-world conflicts (two `synonym_label`s
  on the same value, two `paraphrase`s on the same condition, two
  `omission`s on the same span) are caught by canonical-key
  equality without consulting the matrix. The matrix exists for
  the rare case where two rules with *different* canonical keys
  still conflict (PD installing axis K + L1 mutating values on K).
  Sprint 11's starter matrix has six entries — all of them
  redundant with the dedicated PD-vs-L1 same-axis pass. The
  matrix's purpose is **future extension** without code changes:
  the next sprint that uncovers, e.g., `omission` + `reorder` on
  overlapping spans as a structural problem can add one
  `UNSTACKABLE` entry without touching the composer's pass logic.
- **The composer never copies rule dicts.** The returned
  admissible-rules list aliases the input rule dicts. The
  orchestrator's `_apply_rules` already deep-copies stage JSON at
  entry; rule dicts are the *caller's* (variant catalog's)
  property and should not be cloned by an intermediate validator.
  The "no-mutation" contract is pinned by
  `test_no_mutation_of_input_rules`; the "no-copy" contract is
  pinned by `test_admissible_output_aliases_input_rules`. These
  two tests express the same property from opposite directions
  and together they form a strong contract.
- **Skip decisions emit `Modification(status="skipped", reason=...)`,
  not exceptions.** Matches the protocol's "skip + log via the
  `Modification` record" decision from §4. A composer that raised
  on conflict would force the orchestrator to wrap every batch in
  try/except, and the conflict signal would never reach the
  per-item metadata where Phase E's slice analysis needs it.
  Skipping + logging keeps the variant catalog's audit trail
  uniform: every rule the variant proposer emitted has a
  corresponding `Modification` record, even if its `status` is
  `"skipped"` rather than `"applied"`.
- **YAML deferral is deliberate.** The protocol's file-tree listing
  reserves `configs/synthetic/composition_rules.yaml` but doesn't
  specify its schema or its loading semantics. Externalising the
  matrix to YAML introduces a parse step at module load, a schema
  validation surface, and an asymmetric edit path (humans edit
  YAML; tests read YAML; the composer reads YAML). For Sprint 11's
  starter content (six near-identical entries), the cost of
  externalisation exceeds the benefit. When Phase C tooling needs
  to add ten-plus entries without touching code, the YAML
  externalisation can be a single follow-up sprint that wraps
  `COMPATIBILITY_MATRIX = _load_matrix(Path(__file__).parent.parent
  / "configs" / "synthetic" / "composition_rules.yaml")` around the
  current inline definition. The composer's public surface stays
  unchanged.
- **The PD-vs-L1 same-axis pass is separate from the matrix.** Two
  reasons. (1) The matrix encodes *type-pair* policy; the pass
  encodes *value-pair* detection (PD's `param` field matches L1's
  `param` field). The matrix doesn't have a place for "and the
  rules share an addressing value" — that's a runtime check, not a
  type-pair constant. (2) The pass is unconditional (PD-vs-L1
  same-axis is always a conflict) and doesn't need a matrix
  lookup. Keeping it as a dedicated pass makes the conflict
  detection logic explicit rather than buried in a lookup table.
- **Re-composition is idempotent.** Passing the composer's
  admissible output back through `compose_rules` returns the same
  admissible list with empty skipped log. This is a fixed-point
  property: once a batch has been composed, it's *stable* under
  re-composition. Variant catalog's audit pipeline (Phase E1)
  can re-run the composer on an already-composed batch as part of
  metadata reconstruction without inflating the skipped log.
  Pinned by `test_idempotent_under_recomposition`.
- **Phase C / D / E hooks the composer at one of three points,
  user's choice.** (a) Inside `mutator._apply_rules` before the
  loop, transparently filtering rules per layer. (b) Inside the
  Phase D2 orchestrator's variant-materialisation step, before
  the orchestrator hands a per-layer rule list to the
  corresponding `apply_l*`. (c) Inside the Phase C3 variant
  proposer's post-processing, to drop conflicting rules before
  they reach the variant catalog. Sprint 11 lands the composer as
  a standalone module; the wiring decision is Phase C/D's. The
  three options correspond to **applier-side**, **orchestrator-side**,
  and **proposer-side** filtering — Phase B5 makes all three
  viable by keeping the composer state-blind and idempotent.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch
  context, file map, stage-hook integration note. The
  `composition.py` entry now becomes live.
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §3
  (Generation Pipeline — stacking framing), §6 (`modifications`
  array schema that B5's `Modification(status="skipped")` records
  populate).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.3
  (three-layer mutation interface + stacking order — to be updated
  by this sprint), §4 (Unstackable-combo handling: "Skip + log"),
  §5 Phase B B5 (task definition — to be updated by this sprint to
  reflect the YAML deferral), §6 risk register (composition rules
  declare admissible stacks; conflicts are skipped and logged).
- [`SPRINT_07.md`](SPRINT_07.md) — Sprint 11 differs structurally:
  no per-type fan-out, no shared worker, no `_DISPATCH` change.
- [`SPRINT_08.md`](SPRINT_08.md) — the `_norm` whitespace-collapse
  helper that L2 introduced is reused by the composer's
  `_canonical_key` for `Layer.TEXT_VARIABLE` rules. Imported via
  `from .layer_l2 import _norm as _norm_cond`.
- [`SPRINT_09.md`](SPRINT_09.md) — the field-case normalisation
  pattern for L3 is reused by the composer's `_canonical_key` for
  `Layer.TEMPLATE` rules (`rule["field"].lower()` is the
  addressing component).
- [`SPRINT_10.md`](SPRINT_10.md) — the immediate predecessor;
  closed B4 and made `_DISPATCH` fully promoted. Sprint 11
  consumes the now-stable per-layer worker contracts (all 12
  mutators emit `Modification(status="applied", ...)` records;
  the composer emits the complementary `Modification(status="skipped", ...)`
  records).
- [`../../src/synthetic/layer_l2.py`](../../src/synthetic/layer_l2.py)
  — `_norm` private helper imported by the composer.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py)
  — `Layer`, `ModificationType`, `TYPE_TO_LAYER`, `Modification`.
  The composer adds no new types; it consumes the existing
  taxonomy.

---

## Non-goals reminder

If you find yourself opening any `.ipynb` file, anything under
`data/`, `configs/`, or `src/utils/`, anything in
`src/synthetic/llm_proposer.py` / `prompts/` / `metadata.py` /
`review.py`, or writing
`configs/synthetic/composition_rules.yaml` — **stop**. That's
outside Sprint 11. Either the work belongs to a future sprint
(C1+, D1+, E1+) or it should be raised as a clarifying question
in `RESEARCH_LOG.md` before being addressed.

If you find yourself adding a third pass beyond the
canonical-key dedup pass and the PD-vs-L1 same-axis pass and the
matrix pass — **stop**. Three passes are sufficient for Sprint
11's starter content. A fourth pass (e.g., simulating L3
patches' substring-after-rewrite availability) would re-implement
applier logic in the composer; the L3 worker's apply-time
`template.count(original) == 1` check is the authoritative guard
for that. Phase B5 stays static.

If you find yourself making `compose_rules` mutate its input or
deep-copy rule dicts — **stop**. The "no-mutation, no-copy"
contract is pinned by two complementary tests
(`test_no_mutation_of_input_rules` and
`test_admissible_output_aliases_input_rules`); both must pass.

If you find yourself wiring `compose_rules` into
`mutator._apply_rules` or `mutator.apply_l*` / `apply_new_param`
— **stop**. The composer is additive in `src/synthetic/`;
Sprint 11 does not change the orchestrator's behaviour. Wiring
decision (applier-side vs orchestrator-side vs proposer-side
filtering) is Phase C/D's call, not B5's.

If you find yourself extending the `Modification` dataclass to
add new fields for skipped-record context — **stop**. The
existing `(type, layer, status, reason)` quartet is sufficient
for Sprint 11's skipped records (matching the protocol's
"skip + log" design). Extra fields belong to Phase E1's
metadata-join discussion, not Phase B5's pre-apply validator.

If you find yourself externalising the matrix to YAML in
`configs/synthetic/composition_rules.yaml` — **stop**. The
sprint's deliberate deferral is documented in the design notes
and in Task 4 step 3's protocol update. Externalisation is a
single follow-up sprint when Phase C / E tooling needs it; doing
it now adds parse/schema/test surface for no current consumer.
