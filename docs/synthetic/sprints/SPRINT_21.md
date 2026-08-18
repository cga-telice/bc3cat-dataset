# Sprint 21 — Phase G Task G1 (release packaging: items Parquet + modifications sidecar JSONL)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 21                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | G1 (see [`../RESEARCH_PROTOCOL.md §5 Phase G`](../RESEARCH_PROTOCOL.md))                     |
| **Predecessor** | Sprint 20 — `review.py` (E3: stratified validation sampler + E4: domain-reviewer harness) (see [`SPRINT_20.md`](SPRINT_20.md)) |
| **Successor**   | Sprint 22 — Phase G (G2: loader utilities `loaders.py`; G3: `DATA_CARD.md`) and/or **A3** (concrete `LLMClient` transport) to unblock the Phase F real pilot |

---

## Context

Phase E is closed. [`metadata.py`](../../src/synthetic/metadata.py) (Sprint 19)
turns the variant-grained Stage-B payloads into flat `SyntheticItem` release
records — one per leaf, each carrying the traceability triple
`(item_key, original_key, variante_id)`, a recomputed
`modification_types`/`modification_count`, and the full `modifications` log;
`validate_items` fail-loud-asserts they are well-formed.
[`review.py`](../../src/synthetic/review.py) (Sprint 20) is the quality-gate
machinery (sampler + reviewer harness).

What is **still missing** is the *release artifact itself*. Everything built so
far is in-memory dataclasses + workflow JSONL; nothing on disk is the shape a
downstream consumer (`bc3cat-retrieval`) loads. G1 (proposal Stage E /
[`../RESEARCH_PROTOCOL.md §5 G1`](../RESEARCH_PROTOCOL.md)) packages the
`SyntheticItem` records into the durable BC3CAT-Syn release:

- **A columnar items Parquet** carrying the per-item release record (proposal
  §2.3 / `SyntheticItem.to_dict`) plus the four traceability metadata columns.
- **A sidecar JSONL** keyed by `item_key` carrying the full `modifications`
  array (the nested, ragged log that does not belong in a flat Parquet column).

### Why G1 and not the Phase F pilot

Sprint 20's successor note offered "F1–F2 (single-concept pilot) **and/or** G1".
**F1–F2 is blocked**: the concrete LLM transport (**A3**) is still unwired —
[`llm_proposer.py`](../../src/synthetic/llm_proposer.py) defines only the
`LLMClient` *Protocol*, [`variant_proposer.py`](../../src/synthetic/variant_proposer.py)
and [`run_synthetic.py`](../../src/synthetic/run_synthetic.py) both note "a
concrete LLM transport (A3)" as not-owned, and there is no transport
implementation in the tree. A *real* pilot — whose entire deliverable is F2's
per-type acceptance rate, generation throughput, and `new_param`
semantic-collision rate — cannot run on a stub. G1, by contrast, is **fully
unblocked**: it consumes `SyntheticItem`s as-is and is testable against the same
real `OBRA CIVIL` baseline join used by Sprints 19–20. G1 is therefore the
correct next sprint; A3 (to unblock the F-phase) is its own dedicated sprint.

### The load-bearing design decisions (decide up front)

1. **The release is two files, exactly as protocol §7 names them:**
   `BC3CAT_Syn_items.parquet` (one row per `SyntheticItem`) and
   `BC3CAT_Syn_modifications.jsonl` (one line per `item_key`). The Parquet is the
   flat, columnar, retrieval-facing table; the sidecar carries the ragged
   `modifications` arrays. They join on `item_key`.

2. **The items Parquet carries the proposal §2.3 record columns + the four
   metadata columns — *not* the OEB `_feats` lexical columns.** Columns:
   `item_key, original_key, parent_key, concept_key, params, resumen, texto,
   variante_id, modification_types, modification_count`. The OEB release
   (`OEB_long_norm.parquet`) additionally carries derived
   `text_norm`/`tokens_word`/`param_tokens`/… columns produced by the *feature
   stage* — those are **mechanically re-derivable** from `texto`/`resumen` by the
   existing normalization (`utils.text_processing.normalize_text`) and are **not**
   part of the per-item release record (§2.3). They are **deferred** (a feats
   pass / G2 loader concern), keeping G1 the canonical record table. `params` is
   stored as the nested dict, mirroring how OEB stores `parameters`;
   `modification_types` is a `list<str>` column (enum `.value`s).

3. **A `SyntheticItem` carries both `resumen` and `texto`, so the items table is
   ONE row per item with both text columns** — *not* a two-file
   long/short split. OEB split `*_long_norm` / `*_short_norm` because they were
   separate LlamaIndex document sets (targets vs. queries); a synthetic item
   inherently has both, and a single keyed table makes the sidecar join trivial.
   If `bc3cat-retrieval` needs the exact two-view layout, that projection is a
   one-liner in the G2 loader, not a G1 packaging concern.

4. **`modifications` lives only in the sidecar, never in the Parquet.** The
   Parquet keeps `modification_types` (list) + `modification_count` (int) for
   slice-aware filtering; the full per-`Modification` log (ragged, optional
   per-type fields) is the sidecar JSONL, reusing `Modification.to_dict`. This is
   the protocol §7 split verbatim.

5. **Determinism + atomic writes.** Rows are emitted sorted by `item_key`; both
   files are written atomically (`.tmp` rename, the
   `variant_catalog`/`stage_b`/`review` discipline). Run-twice-equal bytes is a
   pinned invariant (a release artifact must be reproducible).

6. **`packaging.py` validates before it writes.** It calls
   `metadata.validate_items` (Sprint 19, E2) on its input and fails loud
   (`PackagingError`) on a malformed record rather than emitting a corrupt
   release. It imports `metadata` + `taxonomy` + `utils.config` + `pandas`/
   `pyarrow` + stdlib only — **no** `stage_b` / `run_synthetic` / `stage_runners`
   / `review`. The join `metadata.join_intermediate` is the input source; the
   sampler `review.py` is *not* in the release path.

7. **`pandas`/`pyarrow` are an existing pipeline dependency, but a first for the
   synthetic test suite.** The main pipeline already requires them
   (`CLAUDE.md` setup; `Generate_OEB_dataset.ipynb` writes the OEB Parquet), so
   using them in `packaging.py` introduces no *new repo* dependency. But the
   `synthetic` test tier has been stdlib-only (Sprints 11–20). Decision: the
   **Parquet** tests are gated with `pytest.importorskip("pyarrow")` (skip — never
   fail — where the dep is absent); the **sidecar JSONL** tests stay always-on
   stdlib. This preserves "zero failures in any tree".

8. **The CLI is a thin wrapper; the library is the contract.** `python -m
   synthetic.packaging build` reads `SYNTHETIC_INTERMEDIATE_DIR` via
   `metadata.join_intermediate`, validates, and writes both files under
   `SYNTHETIC_PROCESSED_DIR`. All logic is tested through the library functions;
   `main(argv)` is smoke-tested for argument wiring + the no-subcommand exit.

---

## Scope

### In scope

- **G1 — new module `src/synthetic/packaging.py`.** Public surface:

  - `class PackagingError(ValueError)` — distinct, catchable failure type
    (malformed record on the write path, sidecar key collision).
  - `ITEM_COLUMNS: tuple[str, ...]` — the frozen column order for the items
    frame (decision 2), exported so tests and downstream pin against it.
  - `items_to_frame(items: Iterable[SyntheticItem]) -> pandas.DataFrame` — pure;
    one row per item, columns = `ITEM_COLUMNS`, rows sorted by `item_key`,
    `modification_types` as `list<str>`, `params` as nested dict. Validates via
    `metadata.validate_items` first.
  - `modifications_sidecar(items) -> list[dict]` — pure; one
    `{"item_key": ..., "modifications": [m.to_dict(), ...]}` per item, sorted by
    `item_key`. (Items with an empty log still get a line, `modifications: []`.)
  - `write_items_parquet(items, path)` — atomic Parquet write (`.tmp` rename).
  - `write_modifications_jsonl(items, path)` — atomic JSONL write; fail-loud
    `PackagingError` on a duplicate `item_key`.
  - `write_release(items, *, out_dir=None) -> dict[str, Path]` — validates, then
    writes both files under `out_dir` (default `config.SYNTHETIC_PROCESSED_DIR`);
    returns the two written paths.
  - `read_items_parquet(path) -> pandas.DataFrame` /
    `read_modifications_jsonl(path) -> dict[str, list[Modification]]` — the
    minimal read side needed to pin the round-trip (full loader API is G2).
  - `main(argv: Sequence[str] | None = None) -> int` — `build` subcommand
    (argparse); thin wrapper. `main([])` (no subcommand) returns non-zero without
    raising.

- **Tests** — `tests/synthetic/test_packaging.py`. Always-on stdlib tier
  (sidecar JSONL shape/round-trip/dedup, `ITEM_COLUMNS` pin, import-hygiene +
  no-side-effects audits, CLI no-subcommand) + a `pyarrow`-gated tier
  (`items_to_frame` schema, Parquet atomic round-trip, determinism) + a
  data-gated tier (join one real `OBRA CIVIL` concept, `write_release`, reread,
  assert join-on-`item_key` consistency). The data-gated tier is *also*
  `pyarrow`-gated.

- **Doc + housekeeping**:
  - Flip the ✅ `packaging.py` row into the "New Files in This Branch" map in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) (it is currently absent —
    add it near the `metadata.py`/`review.py` rows); flip the
    `data/synthetic/processed/BC3CAT_Syn_items.parquet` +
    `BC3CAT_Syn_modifications.jsonl` rows ❌ → ✅; record the two-file split, the
    §2.3-record-columns (not `_feats`) decision, and the one-row-with-both-texts
    decision. Prepend an "After Sprint 21" Sprint History entry.
  - Sprint 21 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip the `G1` portion of the "Dataset packager + loader utilities" row in
    [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §3 status table — but
    that row is `G1–G2` combined; **leave it ❌ until G2 ships**, or split a note
    that G1 is done and G2 pending. (Status flip only — no design change. Do not
    otherwise edit the protocol.)

### Out of scope (explicit)

- **The Phase F pilot (F1–F4) and the LLM transport (A3).** F1–F2 are blocked on
  A3 (see Context); G1 needs neither. No generation happens this sprint — G1
  packages whatever `join_intermediate` already produced.
- **Loader utilities `loaders.py` (G2).** `packaging.py` ships the *minimal* read
  side needed to pin the round-trip; the consumer-facing
  `load_items()`/`load_modifications()`/`join()` API + the long/short projection
  is G2. No downstream `bc3cat-retrieval` wiring.
- **The derived `_norm` / `_feats` lexical columns** (`text_norm`,
  `tokens_word`, `param_tokens`, `text_word_params`, …). Re-derivable from
  `texto`/`resumen` by the existing feature stage; not part of the §2.3 record.
  Deferred (decision 2).
- **`DATA_CARD.md` (G3), `README.md` "Synthetic Variant" section (G3),
  `HANDOFF.md` (G4).** Documentation/handoff is a later Phase-G sprint.
- **Changes to `metadata.py`, `review.py`, `stage_b.py`, `run_synthetic.py`,
  `stage_runners.py`, any `layer_*` / `mutator` module.** G1 *consumes*
  validated `SyntheticItem`s. A malformed record is an E1/E2 bug
  `validate_items` already catches.
- **Multi-chapter generality of the data-gated test.** Pinned to `OBRA CIVIL`,
  as in Sprints 17–20.

---

## Behavioural requirements

1. **`items_to_frame` produces exactly `ITEM_COLUMNS`, one row per item, sorted
   by `item_key`.** A mixed inline fixture yields the expected column set/order;
   `modification_types` cells are `list[str]` of enum values; `params` cells are
   the nested dict. Pinned (`pyarrow`-gated only insofar as it builds a frame —
   the column/row assertions need pandas).
2. **The modifications sidecar is one line per item, keyed by `item_key`,
   carrying the full log.** A baseline item (empty log) still gets a line with
   `modifications: []`; a multi-mod item carries every `Modification.to_dict`.
   Pinned (always-on stdlib).
3. **`modifications` never appears in the items frame; `modification_types` +
   `modification_count` do.** Pinned.
4. **Both writes are atomic and deterministic.** `write_*` leaves no `.tmp`;
   writing the same items twice yields byte-identical files (Parquet write pinned
   with a fixed pandas/pyarrow path; JSONL pinned always-on). Pinned on
   `tmp_path`.
5. **Round-trip consistency.** `read_modifications_jsonl(write…)` reconstructs
   the per-item `Modification` tuples (`Modification.from_dict`);
   `read_items_parquet(write…)` returns a frame whose `item_key` set + scalar
   columns match the input. The two files join 1:1 on `item_key`. Pinned.
6. **Duplicate `item_key` on the sidecar write is fail-loud `PackagingError`.**
   Pinned (always-on).
7. **`write_release` validates first.** A deliberately malformed `SyntheticItem`
   (e.g., count/types mismatch) raises before any file is written — no partial
   release on disk. Pinned.
8. **`packaging.py` imports neither `stage_b`, `run_synthetic`, `stage_runners`,
   nor `review`.** Pinned by source + `__dict__` audits (the Sprint 17–20 hygiene
   shape). It imports `metadata`, `taxonomy`, `utils.config`, `pandas`/`pyarrow`,
   stdlib only.
9. **No module-level side effects; no *new repo* dependency.** Stdlib + in-repo +
   the already-required `pandas`/`pyarrow`. Pinned by `importlib.reload`. The CLI
   `main([])` (no subcommand) returns non-zero without raising.

---

## Acceptance

- `from synthetic.packaging import (PackagingError, ITEM_COLUMNS, items_to_frame,
  modifications_sidecar, write_items_parquet, write_modifications_jsonl,
  write_release, read_items_parquet, read_modifications_jsonl, main)` succeeds.
- On an inline mixed fixture (single-mod + stacked + baseline `SyntheticItem`s):
  `items_to_frame` returns a frame with `list(df.columns) == list(ITEM_COLUMNS)`,
  rows sorted by `item_key`, no `modifications` column; `modifications_sidecar`
  returns one dict per item keyed by `item_key` (baseline → `[]`).
- `write_release(items, out_dir=tmp)` writes both files, leaves no `.tmp`, and a
  re-run is byte-identical; the two files join 1:1 on `item_key`.
- A duplicate-`item_key` sidecar write and a malformed-record `write_release`
  each raise `PackagingError`; no file is left behind for the malformed case.
- **Data-gated + `pyarrow`-gated (OBRA CIVIL):** join one real concept (Sprint 19
  `stage_b → join_intermediate`), `write_release` it, reread both files, and
  assert the Parquet `item_key` set equals the sidecar key set equals the joined
  `item_key` set. Skipped when intermediate data **or** `pyarrow` is absent.
- `pytest tests -q` exits 0 with **≥ (Sprint 20 baseline 683) + (new always-on
  count) passed**, the Sprint 12 brace audit still **1 skipped**, plus the new
  `pyarrow`-gated/data-gated tests passing in César's tree and **skipping (never
  failing) in any tree** without `pyarrow` or the intermediate data.

---

## Tasks

### Task 1 — `src/synthetic/packaging.py`
1. `PackagingError(ValueError)` + `ITEM_COLUMNS`.
2. `items_to_frame` (validate → sorted rows → frozen column order; `params`
   nested, `modification_types` list, no `modifications`).
3. `modifications_sidecar` (one dict per item, sorted; baseline → `[]`).
4. `write_items_parquet` / `write_modifications_jsonl` (atomic `.tmp` rename;
   fail-loud duplicate key on the sidecar).
5. `write_release` (validate-first; both files under `SYNTHETIC_PROCESSED_DIR`;
   returns paths).
6. `read_items_parquet` / `read_modifications_jsonl` (minimal round-trip read).
7. `main(argv)` — `build` subcommand (thin argparse wrapper).
8. Import-hygiene + no-side-effects discipline.

### Task 2 — `tests/synthetic/test_packaging.py`
Always-on stdlib tier (sidecar shape/round-trip/dedup, `ITEM_COLUMNS` pin,
`main([])` exit, import-hygiene, no-side-effects) + `pyarrow`-gated tier
(`items_to_frame` schema, Parquet atomic round-trip + determinism, validate-first
no-partial-release) + 1 data-gated (`OBRA CIVIL` join → `write_release` → reread →
1:1 join). Suggested cases:
- `test_module_exposes_public_surface`
- `test_packaging_imports_no_stage_b_run_synthetic_stage_runners_or_review`
- `test_module_has_no_side_effects_at_import`
- `test_item_columns_frozen_order`
- `test_modifications_sidecar_one_line_per_item`
- `test_baseline_item_sidecar_has_empty_list`
- `test_sidecar_jsonl_round_trip` (tmp_path)
- `test_sidecar_atomic_no_tmp_left` (tmp_path)
- `test_sidecar_duplicate_item_key_fail_loud`
- `test_write_release_validates_first_no_partial` (tmp_path)
- `test_main_no_subcommand_returns_nonzero`
- `test_items_frame_columns_and_sort` *(pyarrow-gated)*
- `test_items_frame_has_no_modifications_column` *(pyarrow-gated)*
- `test_items_parquet_round_trip` *(pyarrow-gated, tmp_path)*
- `test_release_deterministic_byte_identical` *(pyarrow-gated, tmp_path)*
- **Data-gated + pyarrow-gated:** `test_write_release_real_concept_joins_one_to_one`

### Task 3 — Housekeeping
1. Prepend a Sprint 21 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the G1-over-F1 sequencing decision
   (F1 blocked on A3), the two-file split, the §2.3-columns-not-`_feats`
   decision, the one-row-with-both-texts decision, the `pyarrow`-gating decision,
   the validate-first invariant, the test-count delta, and the next step
   (Sprint 22 — G2/G3 and/or A3).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): add the ✅
   `packaging.py` row; flip the two `data/synthetic/processed/` artifact rows
   ❌ → ✅; record the packaging decisions near the metadata/review notes; prepend
   the "After Sprint 21" history entry.
3. In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §3: annotate the
   `G1–G2` status row (G1 ✅ / G2 pending) — status only, no design edit.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
# A stale %TEMP%\pytest-of-cesar\pytest-current symlink can raise WinError 5
# during pytest's tmp-cleanup; route to a fresh basetemp to sidestep it.
pytest tests -q --basetemp="$env:TEMP\pt_s21"
```

Expected: the Sprint 20 count **plus** the new always-on tests passed, **1
skipped** (Sprint 12 brace audit) with `pyarrow` + intermediate data present;
**zero failures** in any tree (the `pyarrow`/data-gated tests skip, never fail).

Optional end-to-end smoke (manual, with real per-variant JSON under
`data/synthetic/intermediate/`):

```powershell
# python -c "from synthetic.metadata import join_intermediate; from synthetic.packaging import write_release; \
#   items=join_intermediate(); paths=write_release(items); print({k:str(v) for k,v in paths.items()}, len(items),'items')"
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/packaging.py
new file:   tests/synthetic/test_packaging.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_21.md (this file)
data/synthetic/processed/BC3CAT_Syn_items.parquet         # only if the smoke test is run; gitignored/LFS per .gitattributes
data/synthetic/processed/BC3CAT_Syn_modifications.jsonl   # likewise
```

No edits to `metadata.py`, `review.py`, `stage_b.py`, `run_synthetic.py`,
`stage_runners.py`, `mutator.py`, any `layer_*` module, or `cache_hygiene.py`; no
new *repo* dependency (`pandas`/`pyarrow` are already required by the main
pipeline).

---

## Design notes worth committing to memory

- **G1 packages; it does not generate.** The release is a deterministic function
  of `join_intermediate()` output. No LLM, no pipeline rerun — that is upstream
  (Stage A/B) and, for a real pilot, blocked on A3.
- **Two files, one key.** Flat columnar items (`item_key` + record + 4 metadata)
  for retrieval/slicing; ragged `modifications` sidecar for provenance. They join
  on `item_key`. This is the protocol §7 split, not an invention.
- **The §2.3 record is the contract, not the OEB feats schema.** G1 mirrors the
  *record*; the `_norm`/`_feats` lexical columns are a downstream derivation, not
  part of the per-item release. Don't smuggle the feature stage into the packager.
- **Validate before you write.** A release artifact must never be corrupt;
  `write_release` runs E2's `validate_items` first and fails loud rather than
  emitting a half-bad Parquet.
- **`pyarrow` is the suite's first non-stdlib dep — gate it, don't fail on it.**
  Always-on stdlib for the JSONL side; `importorskip("pyarrow")` for Parquet, so
  any tree stays green.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase G`](../RESEARCH_PROTOCOL.md) — G1
  (packaging, this sprint), G2 (loaders, next), G3/G4 (docs/handoff); §7 file map
  (`BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl`); §3 status row.
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.3 per-item release
  record (the columns G1 mirrors); §6.1 final record shape.
- [`SPRINT_19.md`](SPRINT_19.md) / [`../../src/synthetic/metadata.py`](../../src/synthetic/metadata.py)
  — `SyntheticItem` (the packager input), `to_dict` (the §2.3 column source),
  `join_intermediate` (the data-gated source), `validate_items` (the
  write-path gate).
- [`SPRINT_20.md`](SPRINT_20.md) — the immediately-preceding sprint; the
  atomic-write + import-hygiene + data-gating test patterns reused here.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) —
  `Modification.to_dict` / `from_dict` (the sidecar payload).
- [`../../src/utils/config.py`](../../src/utils/config.py) —
  `SYNTHETIC_INTERMEDIATE_DIR` (input), `SYNTHETIC_PROCESSED_DIR` (release home;
  already present — **no config change this sprint**).
- [`../../src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb)
  — the OEB Parquet packaging precedent (`OEB_long_norm.parquet` columns: `id,
  item_key, parent_key, ud, concept, parameters, text, text_norm, …` — G1 mirrors
  the *record* subset, not the `_feats` columns).

---

## Non-goals reminder

If you find yourself wiring an `LLMClient`, calling a model, or running
`run_synthetic` / `stage_b` to *generate* items — **stop**. That is Stage A/B and
(for a real pilot) A3. G1 packages `join_intermediate()` output only.

If you find yourself computing `text_norm` / `tokens_word` / `param_tokens` /
`text_word_params` — **stop**. The lexical `_feats` columns are a downstream
derivation, not the §2.3 release record (decision 2).

If you find yourself writing `loaders.py`, `load_items()` / `join()`, the
long/short two-view projection, `DATA_CARD.md`, or `README.md` edits — **stop**.
That is G2/G3. G1 ships the two artifacts + the *minimal* read needed to pin the
round-trip.

If you find yourself importing `stage_b` / `run_synthetic` / `stage_runners` /
`review` into `packaging.py` — **stop**. The release path is
`metadata.join_intermediate → validate → write`; the sampler and the generation
stack are not in it (requirement 8).

If you find yourself editing `metadata.py` / a `layer_*` mutator to make
packaging work — **stop**. The packager consumes *validated* `SyntheticItem`s; a
malformed record is an E1/E2 bug `validate_items` already catches.

If you find yourself letting a missing `pyarrow` *fail* the suite — **stop**.
Gate Parquet tests with `pytest.importorskip("pyarrow")`; any tree stays green
(requirement 9 / the "zero failures in any tree" rule).
