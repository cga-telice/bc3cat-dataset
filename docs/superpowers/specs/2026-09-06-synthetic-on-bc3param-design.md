# Running BC3CAT-Syn on the bc3param engine — design (Phase 1: OEB equivalence)

Date: 2026-09-06
Branch: `synthetic-on-bc3param` (based on `synthetic`; never merges to `main`)
Status: approved

## Goal

Run the synthetic-corpus generation algorithm on the new `bc3param` engine instead of the
legacy notebook pipeline (`stage_runners` = s03/s04/s05/s07 verbatim + `z_formula_processing`),
without rewriting the algorithm. Phase 1 proves **equivalence on the OEB pilot**: regenerate
the pilot corpus with bc3param as the render backend and show that every difference from the
frozen `synthetic` release (`6b52053`) is either whitespace or a documented v2 correction of
v1's literal corruption (`>==`, `<==`, spurious quotes). Phase 2 (separate spec) expands to
the OE chapter on the BPA 2026 base.

Non-goals for Phase 1: expanding scope beyond OEB; changing the mutation model, the menu/LLM
layer, the frozen pantry of approved rewrites, the sampler, the driver, or the packaging;
re-running any LLM or re-doing human review.

## Context and constraints

- The synthetic branch reached an accepted result: a reproducible algorithm that mutates the
  BC3 grammar (rule, not text) and re-runs expansion to emit a corpus. The bulk of the branch
  is scaffolding (docs/sprints, recorded LLM transcripts, César's verdicts, pilots) that is
  kept as history and not touched.
- The dependency on the legacy pipeline is a narrow **seam**: `stage_runners` (verbatim
  s03-s07), `slot_extractor` (uses `z_formula_processing`), `l2_repr` / `stage_b` (reason about
  s04/s05 semantics). Everything above the seam (`corpus_sampler`, `corpus_driver`,
  `packaging`, `loaders`, `pantry`, `metadata`, `digest`, menu layer) only imports
  `utils.config` / `utils.text_processing` and is engine-agnostic.
- `stage_b` already takes the s03→s07 runner as an **injectable** parameter (default identity),
  so the backend can be swapped at that boundary without editing callers.
- The corpus is byte-defined against the legacy engine, and `stage_runners` deliberately
  preserves v1's buggy s04 formula translation to reproduce the golden output byte-for-byte.
  bc3param fixes exactly that, so Phase 1 equivalence is defined **up to documented v2
  corrections**, verified by a reconciliation report (mirroring the dataset v1↔v2 report).
- bc3param currently lives on `main`, not on `synthetic`. Task 1 of the plan merges `main`
  into this branch (direction `main → synthetic`, which is allowed; `synthetic → main` remains
  forbidden).
- Phase 1 uses the **same source file the pilot used** (the 2024 `_mod` catalogue) so the
  reconciliation isolates engine differences, not source differences.

## The contract to preserve (stage JSON)

The legacy `stage_runners.run_stages_3_to_7(concept_slice) -> stage_json` returns a dict keyed
by leaf `item_key`, each value carrying at least: `item_key`, `parent_key`, `ud`, `concept`,
`parameters` (nested dict `{VAR: {label, values:[{label,value}]}}`), `resumen`, `texto`.
`slot_extractor` walks this shape and `corpus_driver` filters/materializes from it. The adapter
must emit the same shape and key set so nothing above the seam changes.

## Architecture

Replace the render seam with a bc3param-backed adapter, keeping the stage-JSON contract.

```
pantry (approved rules, frozen)          bc3param (from main, Task 1)
        │                                     │
        ▼                                     ▼
corpus_driver ─▶ stage_b.apply_variant_rules ─▶ bc3param_backend.run_stages_3_to_7
   (unchanged)     (rules → Family edits)          (Family → per-leaf render → stage_json)
        │                                     │
        └────────────── stage_json (same shape) ◀┘
        ▼
filters / materialize / packaging (unchanged) ─▶ BC3CAT_Syn_items.parquet + modifications.jsonl
```

## Components

### 1. `bc3param` mutation + render capability (new, small)

bc3param already parses `~P` into a typed `Family` (parameters, `Assign` text-variables with
`Str`/formula values, `Text` RESUMEN/TEXTO templates) and renders one leaf via `Evaluator`.
Add a thin, well-bounded ability to produce a mutated `Family` by string edits and re-render:

- `bc3param.mutate` (new module):
  - `replace_option_value(family, var, letter, new_value) -> Family` — edit a `ParamDef` option.
  - `replace_text_fragment(family, name, old, new) -> Family` — edit a `Str` value inside an
    `Assign` (text variable), matched by exact fragment.
  - `replace_template(family, label, new_template) -> Family` — replace a RESUMEN/TEXTO `Text`.
  - `add_param_axis(family, ...) -> Family` — for `new_param` (not needed in Phase 1; pantry
    excludes `new_param`/`omission`, so this is deferred to Phase 2 if ever).
  Each returns a new `Family` (dataclasses copied), leaving the original untouched.
- `bc3param.render_chapter_leaves(family) -> dict` — expand the cartesian product with
  `Evaluator` and return the stage-JSON dict for that family (helper used by the adapter).

These are additive to bc3param and covered by their own unit tests; they do not change the
evaluator semantics.

### 2. `src/synthetic/bc3param_backend.py` (adapter, new)

- `run_stages_3_to_7(concept_input) -> stage_json`: same signature/return shape as
  `stage_runners.run_stages_3_to_7`. Internally: obtain the concept's `Family` (parsed by
  bc3param from the catalogue, cached per concept), apply the variant's rule edits to the
  `Family` via `bc3param.mutate`, then `render_chapter_leaves` and map bc3param's per-leaf
  output to the legacy stage-JSON keys.
- `catalog()` / `family(concept_key)`: load the catalogue once (the 2024 `_mod` file in
  Phase 1, path from `utils.config`) and cache parsed families.
- A translation layer `rules_to_family_edits(rules) -> list[edit]` mapping the existing variant
  rule representation (PD/L1/L2/L3 records the pantry/`stage_b` produce) to the
  `bc3param.mutate` calls. This is where the "apply approved rules on the Family" decision
  lives (approved in brainstorming).

### 3. `stage_b` re-point (one-line change)

`stage_b.materialize_variant` / `materialize_catalog_entry` receive the runner via the existing
injectable parameter; wire it to `bc3param_backend.run_stages_3_to_7`. Callers in
`corpus_driver` pass the new runner. No other change to `stage_b`.

### 4. `slot_extractor` reliance

`slot_extractor` walks the emitted stage JSON (unchanged) for enumeration; its only coupling to
the legacy engine is formula parsing via `z_formula_processing`. In Phase 1 the corpus is
regenerated from the **frozen pantry**, so target enumeration is not re-run through the LLM;
`slot_extractor` is exercised only where `corpus_driver`/`target_scanner` need per-leaf slot
reads on the stage JSON, which the adapter supplies in the same shape. No rewrite of
`slot_extractor` in Phase 1; if a specific call still needs `z_formula`, cover it by reading
the value from the stage JSON the adapter emits.

### 5. Reconciliation report (new)

`scripts/reconcile_syn_v1_v2.py` + `docs/synthetic/reconciliation-syn-v1-v2.md`: compare the
bc3param-regenerated OEB corpus against the frozen release `6b52053`, classifying every
difference as exact / whitespace-only / v2-correction / unexplained (mirrors the dataset
report). Success = zero unexplained.

## Data flow (Phase 1)

`bc3param` loads the 2024 `_mod` catalogue → per OEB concept: `Family` → `corpus_driver`
drives `stage_b` with the bc3param runner, applying frozen pantry rules → per-leaf render →
stage JSON → existing filters/materialize/packaging → regenerated
`BC3CAT_Syn_items.parquet` + `modifications.jsonl` → reconciliation vs `6b52053`.

## Error handling

- The adapter raises loudly on any concept bc3param cannot parse or any rule edit whose target
  fragment is not found in the `Family` (no silent no-op — consistent with the branch's
  "fail loud" discipline). `corpus_driver`'s existing no-op counter remains as a backstop.
- Leaf render errors (bad index, etc.) surface per concept with the concept key, not silently
  dropped.

## Testing

- bc3param `mutate`: unit tests for each edit function (option value, text fragment, template)
  and that the original `Family` is untouched.
- Adapter round-trip: for a set of OEB concepts with no rules applied, the adapter's stage JSON
  equals the legacy `stage_runners` output **up to documented v2 corrections** (whitespace +
  `>==`/`<==`/quotes), asserted by the same normalization used in the dataset reconciliation.
- Adapter with rules: a handful of approved pantry rules produce the expected mutated leaves.
- `stage_b` with the injected runner yields the same `MaterializedVariant` set as legacy up to
  v2 corrections on a sample concept.
- Full OEB corpus regeneration + reconciliation: zero unexplained differences vs `6b52053`.
- The branch's existing synthetic test suite (1,092 tests) still passes for everything above
  the seam; seam tests that assert legacy byte-output are updated to the "up to v2 corrections"
  criterion, with the old golden kept as the v1 reference in the reconciliation.

## Out of scope (Phase 2, separate spec)

OE-chapter expansion; switch to the BPA 2026 base; any re-freeze/release of a v2 synthetic
corpus for the retrieval phase; optional clean re-targeting of `slot_extractor`/`l2_repr` onto
the bc3param AST if the legacy shape proves to get in the way.
