# Sprint 17 — Phase D Task D1 (stage hooks — extract s03/s04/s05/s07 core transforms as importable in-memory pure functions + equivalence harness)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 17                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | D1 (see [`../RESEARCH_PROTOCOL.md §5 Phase D`](../RESEARCH_PROTOCOL.md))                     |
| **Predecessor** | Sprint 16 — `run_synthetic.py` (Stage-A orchestrator: populates the variant catalog) (see [`SPRINT_16.md`](SPRINT_16.md)) |
| **Successor**   | Sprint 18 — Phase D Task D2 (Stage-B half): consume the catalog, apply rules across the four injection points, rerun the pipeline via these D1 hooks, emit raw synthetic items into `data/synthetic/intermediate/`; + D3 cache hygiene |

---

## Context

Sprint 16 closed **Stage A**: the orchestrator (`run_synthetic.py`) loops
`(concept, condition)`, proposes variants through a stubbed LLM, emits +
composes rules, and writes one `VariantCatalogEntry` per concept to
`data/synthetic/variants/`. The catalog now records *admissible, ordered*
rules per variant — but **nothing applies them or reruns the pipeline**.
Sprint 16 deliberately did not call `mutator.apply_*`; a test even audits
that `run_synthetic` never imports `mutator`.

Stage B — apply the catalog's rules and regenerate the mutated items —
is blocked on one missing primitive: **the pipeline stages are
notebooks, not importable functions.** You cannot rerun s03→s07 in
process on a mutated in-memory stage JSON because s03/s04/s05/s07 only
exist as `.ipynb` cells with file-IO drivers. Sprint 17 builds that
primitive: **D1, the stage hooks.**

### What the pipeline actually looks like (verified, not assumed)

The stage chain is a deterministic JSON→JSON cascade. Each stage's core
transform is *already factored into functions* — but those functions
live inside notebook cells, wrapped in file-IO + (for s04/s05)
`ijson`-chunked streaming drivers. Verified contract:

| Stage | Notebook | Reads | Writes | Core in-memory transform (the part to extract) |
|:-----:|----------|-------|--------|-----------------------------------------------|
| s03 | `s03_generate_parametric_combinations.ipynb` | `config.chapter_path(ch)` (s02 `{CH}.json`) | `{CH}_stage3.json` | `transform_data(data)` — Cartesian expansion over parameter axes via `itertools.product`; one leaf item per combination, key = `parent_key[:-1] + "".join(param_labels)` |
| s04 | `s04_evaluate_text_variables.ipynb` | `{CH}_stage3.json` | `{CH}_stage4.json` | `process_unresolved_variables(process_text_variables(data))` — resolves `$VAR` formulas; uses `translate_formula_to_python` / `quote_second_term` |
| s05 | `s05_evaluate_resumen_texto.ipynb` | `{CH}_stage4.json` | `{CH}_stage5.json` | `filter_fields(process_json(data))` — instantiates `\RESUMEN\`/`\TEXTO\` templates (`$L(...)`, `$A`), then keeps only `[parent_key, ud, concept, resumen, texto, parameters]` *(composition order to confirm at extraction — `process_chunk` shows `process_json`; `filter_fields` is applied at merge)* |
| s06 | `s06_data_analysis.ipynb` | `{CH}_stage5.json` | *(none — stats only)* | **skipped in the rerun** — pure read-only analysis, no file output |
| s07 | `s07_Filter_duplicates.ipynb` | `{CH}_stage5.json` → marks → `{CH}_stage6.json` → filters → `{CH}_stage7.json` | `{CH}_stage6.json` then `{CH}_stage7.json` | two file-based steps: `marcar_duplicados(path_in, path_out)` (adds `validation: bool`) then `filter_json(json_data)` (drops dup `(resumen, texto)` pairs, keeps first) |

Three facts that matter for extraction:

1. **s06 produces no file.** The "stage6" file is written *by s07* (its
   `marcar_duplicados` marking step), not by s06. The rerun skips s06
   entirely — it is analysis, not a data transform.
2. **s07's `marcar_duplicados` is file-path-based** (`path_entrada`,
   `path_salida`); `filter_json` is already in-memory. The extracted
   `run_stage7` must do marking + filtering **in memory**, no disk.
3. **s04 redefines `translate_formula_to_python` / `quote_second_term`
   inline**, even though `src/utils/z_formula_processing.py` already
   exports both. The extracted `run_stage4` must import the canonical
   util — and Sprint 17 must verify the inline notebook copies are
   byte-equivalent to the util before deleting them (or reconcile if
   they have drifted).

### The load-bearing scope decision: Sprint 17 is D1 only

Sprint 16's successor line named Sprint 17 as "D1 + the D2 Stage-B
rerun half." Splitting that — D1 here, the Stage-B rerun in Sprint 18 —
is the right call, for the same architecture-forced reason Sprint 16
split D2 itself:

- **D1 is a faithful-extraction problem.** Pull the core transforms out
  of the notebooks into importable pure functions and prove —
  byte-for-byte against the committed `{CH}_stage{3,4,5,7}.json` golden
  files — that the extracted functions reproduce the notebook outputs.
  This is self-contained, fully testable, and touches no synthetic
  logic. It is also where the *risk* lives (notebook cells with
  chunked-IO drivers, an inline-vs-util duplication to reconcile, a
  file-based dedup to make in-memory).
- **The Stage-B rerun is a wiring problem** that *depends on* D1 being
  proven correct. It applies the catalog's rules across the four
  injection points (PD/L1 before s03, L2 before s04, L3 before s05),
  chains the D1 hooks, loops over every variant in every catalog entry,
  and emits raw items. Bundling it with D1 would mean debugging the
  orchestration on top of an unproven extraction — exactly the
  "untested rerun path" Sprint 16 refused to ship.

So Sprint 17 ships the **four pure stage runners + the equivalence
harness that proves they match the notebooks**. Sprint 18 wires them
into the orchestrator's apply-and-rerun loop.

Consequence: **Sprint 17 does not import `run_synthetic`, the variant
catalog, `mutator`, or any `layer_*` / `taxonomy` synthetic module.**
The stage runners are pure pipeline transforms — they know nothing about
mutations. (A test asserts `stage_runners` imports nothing from the
synthetic mutation stack.)

### Two design tensions to resolve up front

1. **Extract-and-reimport, or re-implement?** Two ways to get importable
   stage functions: (A) physically move the notebook function bodies
   into a new module and refactor the notebooks to `from
   synthetic.stage_runners import …` (single source of truth, zero drift
   by construction); (B) re-implement the transforms fresh and pin them
   with golden tests (cleaner module, but two copies that can drift).
   **Sprint 17 takes (A)** — move the logic verbatim, leave each
   notebook's own IO/driver/logging cells in place but calling the
   extracted core. This honours the protocol's D1 wording exactly
   ("*No changes to the stages' internal logic*"): the logic is
   relocated, not rewritten. The golden equivalence harness is the
   safety net that proves the relocation was faithful.
2. **Chunking.** s04/s05 stream the full chapter through `ijson` in
   chunks for memory. The *core transform* (`process_text_variables` /
   `process_json`) already operates on a plain dict per chunk — the
   chunking is a driver concern, not a transform concern. The extracted
   `run_stage4` / `run_stage5` operate on a whole in-memory dict (a
   single concept's mutated subtree is tiny; no streaming needed). The
   notebooks keep their chunked file drivers, now calling the same
   extracted core. **No chunking logic moves into `stage_runners.py`.**

Sprint 16's verification baseline: **557 passed + 1 skipped.** Sprint 17
adds one new module + one new test file. Net pytest delta target:
**≥20 new always-on functions** = **≥577 passed**. The golden
equivalence tests are **data-gated** (`skipif` the committed
`data/intermediate/OBRA CIVIL/*.json` are absent) so a data-less
checkout stays green; when the data is present they must pass. The lone
pre-existing skip (Sprint 12's `new_param` brace audit) stays; data-gated
skips are expected to be 0 in César's working tree (the intermediate
JSONs are present) and up to 4 in a bare checkout.

---

## Scope

### In scope

- **D1: the stage runners** — new module
  `src/synthetic/stage_runners.py`. Public surface:

  - `def run_stage3(stage2_json: dict) -> dict` — Cartesian parametric
    expansion. Body relocated verbatim from s03's `transform_data`
    (+ its helper `generate_combinations`). Pure: deep-copies input,
    never touches disk.
  - `def run_stage4(stage3_json: dict) -> dict` — text-variable
    evaluation. Body = `process_unresolved_variables(
    process_text_variables(stage3_json))` relocated from s04. Imports
    `translate_formula_to_python` / `quote_second_term` from
    `src/utils/z_formula_processing.py` (canonical) rather than the
    inline notebook copies.
  - `def run_stage5(stage4_json: dict) -> dict` — template
    instantiation + field filter. Body = `filter_fields(process_json(
    stage4_json))` relocated from s05 (confirm composition order during
    extraction).
  - `def run_stage7(stage5_json: dict) -> dict` — in-memory dedup.
    Combines s07's `marcar_duplicados` (marking) + `filter_json`
    (filtering) into one pure dict→dict function, **no file IO**.
    Deterministic: iteration follows insertion order (Python 3.7+);
    first occurrence of each `(resumen, texto)` pair wins. (Same
    sorted/stable-iteration discipline Sprint 6.5 pinned for the
    notebook version.)
  - `def run_stages_3_to_7(stage2_json: dict) -> dict` — convenience
    that chains `run_stage3 → run_stage4 → run_stage5 → run_stage7`
    (s06 skipped). No rule injection — that's Sprint 18's orchestrator.
    This is the function Sprint 18 will interleave `apply_*` calls
    between.

- **Notebook refactor** — s03/s04/s05/s07 each lose their inline core
  transform cell, replaced by `from synthetic.stage_runners import …`
  (or `from utils`-style import consistent with the notebooks' existing
  `from utils import config`). The notebooks keep their own
  file-IO/driver/logging/chunking cells, now delegating the transform
  to the imported function. **Each notebook must still execute top to
  bottom and produce a byte-identical `{CH}_stage{N}.json`** — proven by
  the equivalence harness, not by re-running the notebook in pytest.

- **Equivalence harness (golden tests)** — new test file
  `tests/synthetic/test_stage_runners.py`. Two tiers:
  - **Always-on unit tests** (no real IO; tiny inline fixtures): one per
    stage runner exercising the core transform on a hand-built concept,
    plus purity (input-not-mutated), determinism (run-twice-equal), and
    the `run_stages_3_to_7` chain.
  - **Data-gated golden tests** (`@pytest.mark.skipif` on
    `config.INTERMEDIATE_DIR / "OBRA CIVIL"` absence): assert
    `run_stage3(load(stage2)) == load(stage3_golden)`, and likewise
    stage4-from-stage3, stage5-from-stage4, stage7-from-stage5, against
    the committed `OBRA_CIVIL_stage{3,4,5,7}.json`. These are the
    faithfulness gate for the extraction.

- **Reconciliation check** — a test (or a documented manual diff in the
  log) confirming s04's inline `translate_formula_to_python` /
  `quote_second_term` were byte-equivalent to the
  `z_formula_processing.py` exports before removal. If they differ,
  **stop and surface it** — do not silently pick one.

- **Housekeeping**:
  - Sprint 17 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - New ✅ row for `stage_runners.py` in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files in
    This Branch" map; note the s03/s04/s05/s07 notebooks now import
    their core from it.
  - Prepend an "After Sprint 17 — …" entry to the Sprint History
    section.

### Out of scope (explicit)

- **Rule application + the Stage-B rerun (D2 Stage-B half).** Applying
  the catalog's rules across the four injection points, looping
  variants, emitting raw items into `data/synthetic/intermediate/` —
  Sprint 18, gated on these hooks. Sprint 17's `run_stages_3_to_7` does
  *no* injection.
- **`run_synthetic.py` changes.** The orchestrator is not touched. It
  will *gain* a Stage-B path in Sprint 18; Sprint 17 only provides the
  hooks it will call.
- **`mutator` / `layer_*` / `taxonomy` / variant-catalog imports.** The
  stage runners are pure pipeline transforms, ignorant of mutations. A
  test pins that `stage_runners` imports nothing from the synthetic
  mutation stack.
- **D3 cache hygiene.** Clearing pickled BM25 / embedding / LlamaIndex
  caches between runs — Sprint 18 (it only matters once real mutated
  items are emitted).
- **s06 extraction.** s06 is read-only analysis with no file output and
  no role in the rerun. Not extracted.
- **`Generate_OEB_dataset.ipynb`.** Reads pickles, not the stage chain;
  produces the final OEB Parquet/Pickle. Orthogonal to the s03→s07
  rerun. Not extracted (the synthetic export path is a later phase).
- **Multi-chapter generality.** The golden tests pin `OBRA CIVIL` (the
  chapter with committed intermediate files). The runners are
  chapter-agnostic pure functions, but the equivalence proof is for the
  one chapter whose golden files exist.
- **Performance / chunking.** The runners take a whole dict. Streaming
  large chapters stays in the notebooks' file drivers. The synthetic
  rerun operates per-concept (tiny), so in-memory is fine.

---

## Behavioural requirements

1. **Each `run_stageN` is pure.** Deep-copies (or otherwise does not
   mutate) its input; same input → same output. Pinned by an
   input-unchanged test and a run-twice-equal test per stage.
2. **`run_stage3` reproduces s03's expansion.** A 2-axis concept (axes
   with 2 and 3 values) yields 6 leaf items with keys derived as
   `parent_key[:-1] + param_labels`. Pinned on a fixture; the real
   expansion pinned by the golden test.
3. **`run_stage4` resolves text-variable formulas via the canonical
   util.** Imports `translate_formula_to_python` from
   `z_formula_processing.py`; a fixture with a `$K = "a"*(%B=a)+...`
   formula resolves to the expected literal. No inline formula-translate
   copy in `stage_runners.py`.
4. **`run_stage5` instantiates templates and filters fields.** Output
   items carry only `[parent_key, ud, concept, resumen, texto,
   parameters]` (whatever the notebook's `filter_fields` keeps —
   confirm and pin the exact field set during extraction).
5. **`run_stage7` dedups in memory, deterministically.** Duplicate
   `(resumen, texto)` pairs collapse to the first occurrence; no disk
   IO; iteration order stable. Pinned by a fixture with a planted
   duplicate and a run-twice-equal test.
6. **`run_stages_3_to_7` chains the four, skipping s06.** A stage-2
   fixture run through the chain equals
   `run_stage7(run_stage5(run_stage4(run_stage3(fixture))))`. Pinned.
7. **Golden equivalence (data-gated).** For `OBRA CIVIL`:
   `run_stage3(stage2) == stage3_golden`, and the same for 4/5/7 from
   their predecessors. Skipped (not failed) when the intermediate data
   is absent.
8. **No synthetic-stack imports.** `stage_runners` imports only stdlib +
   `src/utils/*`. Pinned by a source/`__dict__` audit (no `mutator`,
   `taxonomy`, `run_synthetic`, `layer_*`, `composition`,
   `variant_*`, `rule_emitter`, `slot_extractor`).
9. **Notebooks still produce identical outputs.** After the refactor,
   each notebook's core cell is an import; the byte-identity of the
   regenerated `{CH}_stage{N}.json` is what the golden tests assert.
   (Re-running the notebooks themselves is a manual verification step in
   the runbook, not a pytest case.)
10. **No module-level side effects.** No env reads, no on-import IO, no
    path resolution at import. Pinned by `importlib.reload`.
11. **No new runtime dependencies.** Stdlib + in-repo (`src/utils`) only.
    (`ijson` stays in the notebook drivers; it does not enter
    `stage_runners.py`.)

---

## Acceptance

- `from synthetic.stage_runners import (run_stage3, run_stage4,
  run_stage5, run_stage7, run_stages_3_to_7)` succeeds.
- The four notebooks (s03/s04/s05/s07) import their core transform from
  `stage_runners` and contain no inline duplicate of it.
- For `OBRA CIVIL` with the committed intermediate JSONs present:
  `run_stage3 / 4 / 5 / 7` each reproduce the committed golden stage
  file byte-for-byte (modulo JSON key-order/whitespace already imposed
  by `json`).
- s04's removed inline `translate_formula_to_python` /
  `quote_second_term` are confirmed byte-equivalent to the
  `z_formula_processing.py` exports (or any divergence is surfaced in
  the log, not silently resolved).
- `pytest tests -q` exits 0 with **≥577 passed**, **1 skipped** (the
  brace audit) in César's tree where intermediate data is present;
  **zero failures** in any tree (data-gated tests skip, never fail,
  when data is absent).

---

## Tasks

### Task 1 — `src/synthetic/stage_runners.py`

1. Extract s03's `transform_data` (+ `generate_combinations`) verbatim
   into `run_stage3`. Confirm the leaf-key derivation matches the
   notebook exactly.
2. Extract s04's `process_text_variables` + `process_unresolved_variables`
   (+ their private helpers: `process_single_item`, `evaluate_formula`,
   `replace_parameter_placeholder`, `find_text_variable_references`,
   `resolve_text_variable_reference`, `is_formula`, `safe_quote`,
   etc.) into `run_stage4`. **Reconcile the formula-translate
   duplication**: import `translate_formula_to_python` /
   `quote_second_term` from `utils.z_formula_processing`; before
   deleting the inline copies, diff them against the util and record the
   result. Stop and surface any divergence.
3. Extract s05's `process_json` + `filter_fields` (+ `get_variable_value`,
   `evaluate_string`) into `run_stage5`. Confirm the
   `process_json`→`filter_fields` composition order and the exact kept
   field set.
4. Build `run_stage7` from s07's `marcar_duplicados` marking logic +
   `filter_json` filtering logic, fused into one pure in-memory
   dict→dict (no `open`, no path args). Preserve deterministic
   first-wins dedup.
5. Add `run_stages_3_to_7` chaining the four (s06 skipped).
6. Pure-function discipline: deep-copy inputs; no module-level IO; no
   synthetic-stack imports.

### Task 2 — Notebook refactor

For each of s03/s04/s05/s07: replace the inline core-transform
function definitions with an import from `stage_runners`, leaving the
file-IO / driver / logging / chunking cells in place but delegating the
transform. Each notebook must still run top-to-bottom and regenerate its
`{CH}_stage{N}.json`. (Verify by executing once — see runbook — not in
pytest.)

### Task 3 — `tests/synthetic/test_stage_runners.py`

≥20 always-on functions + the data-gated golden tier. Suggested cases:

- `test_module_exposes_public_surface`
- `test_stage_runners_imports_no_synthetic_stack` — `__dict__`/source audit
- `test_run_stage3_expands_cartesian` — 2×3 axes → 6 leaf items, key derivation
- `test_run_stage3_is_pure` / `test_run_stage3_deterministic`
- `test_run_stage4_resolves_formula_via_util` — asserts canonical-util usage
- `test_run_stage4_is_pure` / `test_run_stage4_deterministic`
- `test_run_stage5_instantiates_template`
- `test_run_stage5_filters_to_expected_fields`
- `test_run_stage5_is_pure` / `test_run_stage5_deterministic`
- `test_run_stage7_dedups_first_wins`
- `test_run_stage7_in_memory_no_io` (monkeypatch `open` to raise → must not be called)
- `test_run_stage7_is_pure` / `test_run_stage7_deterministic`
- `test_run_stages_3_to_7_equals_manual_chain`
- `test_module_has_no_side_effects_at_import` (`importlib.reload`)
- **Golden tier** (`skipif` data absent): `test_golden_stage3`,
  `test_golden_stage4`, `test_golden_stage5`, `test_golden_stage7`.

### Task 4 — Housekeeping

After Tasks 1–3 pass:
1. Append a Sprint 17 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the new module + its four
   pure runners, the extract-and-reimport decision, the
   formula-translate reconciliation result, the s06-skip and
   in-memory-dedup findings, the equivalence-harness design (always-on
   unit tier + data-gated golden tier), the test-count delta, and a
   one-line next-step (Sprint 18 — D2 Stage-B rerun + D3).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): add a ✅
   `stage_runners.py` row to the "New Files in This Branch" map with the
   annotation "Sprint 17 — Task D1 — in-memory pure stage runners
   (`run_stage3/4/5/7` + `run_stages_3_to_7`) extracted from the
   s03/s04/s05/s07 notebooks; the notebooks now import their core from
   here. Rule injection + the Stage-B rerun are Sprint 18."; prepend an
   "After Sprint 17" Sprint History entry.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md)
   or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). (If a
   reviewer wants D1 marked done in §5, that's a one-cell annotation —
   defer unless asked.)

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥577 passed, 1 skipped** with intermediate data present
(0 data-gated skips); **zero failures** in any tree.

Notebook-faithfulness check (manual, once — confirms the refactored
notebooks still regenerate identical stage files):

```powershell
# back up the committed golden stage files, re-run each refactored
# notebook (jupyter nbconvert --execute or run in Jupyter), then diff
# the regenerated {CH}_stage{3,4,5,7}.json against the backups.
# They must be byte-identical (modulo json whitespace).
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/stage_runners.py
new file:   tests/synthetic/test_stage_runners.py
modified:   src/s03_generate_parametric_combinations.ipynb
modified:   src/s04_evaluate_text_variables.ipynb
modified:   src/s05_evaluate_resumen_texto.ipynb
modified:   src/s07_Filter_duplicates.ipynb
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_17.md (this file)
```

No edits to `run_synthetic.py` or any `src/synthetic/*` mutation module;
no new dependencies; no `data/synthetic/` writes at sprint-build time.

---

## Design notes worth committing to memory

- **D1 is faithful extraction, not reinvention.** The protocol's "*No
  changes to the stages' internal logic*" is honoured by *relocating*
  the notebook transform functions verbatim into an importable module
  and proving byte-equivalence against the committed golden stage files
  — not by rewriting them. The golden harness is the contract.
- **s06 is not a transform.** It writes no file; the "stage6" file is
  s07's own marking output. The rerun chains s03→s04→s05→s07 and skips
  s06.
- **s07's dedup goes in-memory.** The notebook's `marcar_duplicados` is
  file-path-based; the extracted `run_stage7` fuses marking + filtering
  into a pure dict→dict with deterministic first-wins iteration. No disk.
- **One formula-translate, not two.** s04 duplicated
  `translate_formula_to_python` / `quote_second_term` inline; the
  canonical home is `src/utils/z_formula_processing.py`. The extraction
  reconciles to the util and the log records the diff result.
- **Stage runners are mutation-blind.** They are pure pipeline
  transforms with no synthetic-stack imports. The injection of L1/L2/L3/
  PD rules *between* stages is the orchestrator's job (Sprint 18) — the
  runners just transform whatever dict they're handed, mutated or not.
  This is the seam that lets Sprint 18 interleave `apply_*` across the
  four injection points without the runners knowing.
- **The four injection points (for Sprint 18, recorded here):** PD/L1
  rules mutate the **stage-2** dict *before* `run_stage3`; L2 rules
  mutate the **stage-3** dict *before* `run_stage4`; L3 rules mutate the
  **stage-4** dict *before* `run_stage5`. `mutator.apply_l1/apply_new_param`
  take stage-2, `apply_l2` takes stage-3, `apply_l3` takes stage-4 —
  exactly matching where each runner consumes them.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase D`](../RESEARCH_PROTOCOL.md) — D1
  (stage hooks, this sprint), D2 (orchestrator — Stage-A done Sprint 16,
  Stage-B Sprint 18), D3 (cache hygiene, Sprint 18).
- [`SPRINT_16.md`](SPRINT_16.md) — the Stage-A orchestrator that will
  call these hooks; its "compose-not-apply" decision and the
  Stage-A/Stage-B seam.
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — Mutation
  Architecture (the four injection points), the Stage-Hook Integration
  Note, and the file map to add the `stage_runners.py` row to.
- [`../../src/utils/config.py`](../../src/utils/config.py) —
  `chapter_path`, `stage_path`, `INTERMEDIATE_DIR`,
  `SYNTHETIC_INTERMEDIATE_DIR` (Sprint 18's emit target).
- [`../../src/utils/z_formula_processing.py`](../../src/utils/z_formula_processing.py)
  — `translate_formula_to_python`, `quote_second_term` (the canonical
  formula util `run_stage4` imports).
- [`../../src/synthetic/mutator.py`](../../src/synthetic/mutator.py) —
  `apply_l1` (stage-2), `apply_new_param` (stage-2), `apply_l2`
  (stage-3), `apply_l3` (stage-4). The injection functions Sprint 18
  interleaves between these runners.

---

## Non-goals reminder

If you find yourself importing `mutator`, `run_synthetic`, `taxonomy`,
`layer_*`, `composition`, or any `variant_*` / `rule_emitter` /
`slot_extractor` module into `stage_runners.py` — **stop**. The stage
runners are pure pipeline transforms. Rule injection is Sprint 18.

If you find yourself *re-implementing* a transform from scratch instead
of relocating the notebook's existing function body — **stop**. D1 is
faithful extraction; the golden tests must pass byte-for-byte.

If you find yourself adding `ijson` / chunking / file-streaming into
`stage_runners.py` — **stop**. The runners take a whole dict; streaming
stays in the notebooks' file drivers.

If you find yourself silently picking one copy of
`translate_formula_to_python` over the other without diffing them —
**stop**. Reconcile to the `z_formula_processing.py` util and record the
diff result in the log.

If you find yourself applying rules, looping variants, or writing into
`data/synthetic/intermediate/` — **stop**. That's the Stage-B rerun
(Sprint 18), gated on these hooks.
