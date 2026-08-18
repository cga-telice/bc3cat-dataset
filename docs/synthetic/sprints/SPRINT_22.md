# Sprint 22 — Phase G Task G2 (loader utilities: `loaders.py` — read API + 1:1 join + long/short projection)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 22                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | G2 (see [`../RESEARCH_PROTOCOL.md §5 Phase G`](../RESEARCH_PROTOCOL.md))                     |
| **Predecessor** | Sprint 21 — `packaging.py` (G1: items Parquet + modifications sidecar JSONL) (see [`SPRINT_21.md`](SPRINT_21.md)) |
| **Successor**   | Sprint 23 — Phase G (G3: `DATA_CARD.md` + `README.md` "Synthetic Variant" section; G4: `HANDOFF.md`) and/or **A3** (concrete `LLMClient` transport) to unblock the Phase F real pilot |

---

## Context

Sprint 21 (G1) shipped the durable release: [`packaging.py`](../../src/synthetic/packaging.py)
writes `BC3CAT_Syn_items.parquet` (flat columnar, frozen `ITEM_COLUMNS`) and
`BC3CAT_Syn_modifications.jsonl` (ragged per-`item_key` log), joining 1:1 on
`item_key`. G1 deliberately shipped only the **minimal read side**
(`read_items_parquet` / `read_modifications_jsonl`) needed to pin its own
round-trip, and explicitly deferred three things to G2:

1. the **consumer-facing loader API** (`RESEARCH_PROTOCOL.md §5 G2`:
   `load_items()`, `load_modifications()`, `join()`);
2. the **1:1 join** that re-attaches the ragged `modifications` log to the flat
   items frame as an in-memory convenience column (the column packaging keeps
   *out* of the flat Parquet on purpose);
3. the **long/short projection** — the OEB-style two-view layout
   (`texto` → long/target view, `resumen` → short/query view) that
   `bc3cat-retrieval` indexes, plus the re-derivable `text_norm` lexical column
   (G1 decision 2: the `_norm`/`_feats` columns are a downstream derivation, not
   part of the §2.3 release record).

G2 is the thin, **read-only** consumer layer that turns the two on-disk release
files into the frames a downstream retrieval harness wants. It builds *on*
`packaging`'s read functions; it does not re-implement Parquet/JSONL parsing, and
it writes **no new on-disk artifacts** — every projection is in-memory and
re-derivable, so G1's "two files are the canonical release" invariant is
preserved.

### Why G2 and not G3 or A3

Sprint 21's successor note offered "G2/G3 **and/or** A3". G2 is the natural
next single-module sprint: it directly continues G1, is **fully unblocked**
(consumes the two release files as-is, the same `OBRA CIVIL` baseline used by
Sprints 19–21), and matches the one-module-per-sprint cadence (Sprint 19
`metadata.py`, Sprint 20 `review.py`, Sprint 21 `packaging.py`). **G3** is
documentation (`DATA_CARD.md` + README) — better written *after* the loader API
it must document exists. **A3** (the concrete `LLMClient` transport that unblocks
the Phase F real pilot) is a different track entirely and remains its own
dedicated sprint (network transport, retry/timeout, API-key handling, live-vs-
recorded test fixtures — none of which G2 touches). G2 first; A3 next or after.

### The load-bearing design decisions (decide up front)

1. **`loaders.py` is read-only and builds on `packaging`.** It imports
   `packaging` and calls `read_items_parquet` / `read_modifications_jsonl` rather
   than re-parsing. The default input paths are
   `config.SYNTHETIC_PROCESSED_DIR / packaging.ITEMS_FILENAME` and
   `… / packaging.MODIFICATIONS_FILENAME` — resolved at call time, not import
   time (the Sprint 19–21 discipline). No `write_*` in this module; G2 never
   produces a release file.

2. **`join()` re-attaches `modifications` as an in-memory column — it does not
   resurrect the flat-Parquet shape.** G1 kept the ragged log *out* of the flat
   table on purpose; G2's `join()` adds a `modifications` column back to a copy
   of the items frame (as `list[dict]`, the `Modification.to_dict` shape) for
   consumers that want per-row provenance. The join is **1:1 on `item_key`** and
   **fail-loud** (`LoaderError`) on either side carrying a key the other lacks —
   a partial release must not silently drop or duplicate rows.

3. **The long/short projection mirrors the OEB *record subset*, not the exact
   OEB column list.** `long_view(items)` and `short_view(items)` each return a
   frame whose retrieval text lives in a single `text` column (`texto` for long,
   `resumen` for short), carrying the keys + slice metadata
   (`item_key, original_key, concept_key, params, variante_id,
   modification_types, modification_count`) and a derived `text_norm` lexical
   column. They intentionally do **not** fabricate OEB-only columns
   (`id`, `ud`, `concept`) that the synthetic record never carried — those are an
   OEB-LlamaIndex-document concern, not a §2.3-record concern.

4. **`text_norm` is derived, never stored.** The lexical column is
   `utils.text_processing.normalize_text(text)` (the *exact* existing
   normalizer — accent-strip + lowercase + `\w+` tokenize, returning
   `list[str]`), computed in-memory by the loader. This is the "feats pass" G1
   deferred (decision 2); it adds **no** new dependency and **no** new on-disk
   file. Reusing the existing `normalize_text` (not a re-implementation) keeps the
   synthetic lexical column byte-for-byte consistent with the OEB `_norm` columns
   downstream tooling already expects.

5. **`LoaderError(ValueError)`** — a distinct, catchable failure type for the
   join-mismatch / malformed-input cases, mirroring `packaging.PackagingError`
   and `review.ReviewError`.

6. **`loaders.py` imports `packaging`, `metadata`, `taxonomy`, `utils.config`,
   `utils.text_processing`, `pandas` (lazily), and stdlib only — never
   `stage_b` / `run_synthetic` / `stage_runners` / `review` / `mutator` / any
   `layer_*`.** The release/consume path is `packaging.read_* → join/project`;
   the generation and review stacks are not in it. `pandas`/`pyarrow` are imported
   lazily (inside the frame functions) so the module + the stdlib
   `load_modifications` path stay importable in a tree without them — the Sprint
   21 gating discipline.

7. **`pandas`/`pyarrow` gating, exactly as Sprint 21.** `load_modifications`
   (JSONL → `dict[str, list[Modification]]`) is **always-on stdlib**; everything
   that returns or consumes a frame (`load_items`, `join`, `long_view`,
   `short_view`) is gated with `pytest.importorskip("pyarrow")` (the on-disk read
   needs the Parquet engine). The import-hygiene / no-side-effects / CLI tests are
   always-on. "Zero failures in any tree" holds.

8. **The CLI is a thin wrapper; the library is the contract.** `python -m
   synthetic.loaders info` loads both release files (default paths), prints row
   counts + the items column list + a join-consistency check, and exits 0;
   `main([])` (no subcommand) returns non-zero without raising. All logic is
   tested through the library functions.

---

## Scope

### In scope

- **G2 — new module `src/synthetic/loaders.py`.** Public surface:

  - `class LoaderError(ValueError)` — distinct, catchable failure type
    (join key mismatch, malformed input).
  - `DEFAULT_ITEMS_PATH` / `DEFAULT_MODIFICATIONS_PATH` — module-level helpers
    (or a `default_*_path()` callable) resolving
    `config.SYNTHETIC_PROCESSED_DIR / packaging.{ITEMS,MODIFICATIONS}_FILENAME`
    **at call time**.
  - `load_items(path: Path | None = None) -> pandas.DataFrame` — thin wrapper
    over `packaging.read_items_parquet`; default path; returns the frame with
    `ITEM_COLUMNS`.
  - `load_modifications(path: Path | None = None) -> dict[str, list[Modification]]`
    — thin wrapper over `packaging.read_modifications_jsonl`; default path;
    always-on stdlib.
  - `join(items=None, modifications=None, *, items_path=None, mods_path=None) ->
    pandas.DataFrame` — load (or accept) both, assert a **1:1** `item_key` join
    (fail-loud `LoaderError` on any unmatched key on either side), return a copy
    of the items frame with an added `modifications` column (`list[dict]` per
    row, sorted-by-`item_key` stable). No mutation of the input frame.
  - `long_view(items) -> pandas.DataFrame` / `short_view(items) -> pandas.DataFrame`
    — project to the OEB-style target/query views: rename `texto`/`resumen` →
    `text`, keep the key+metadata columns (decision 3), add `text_norm`
    (`normalize_text(text)`, `list[str]`). Pure; in-memory; no I/O.
  - `main(argv: Sequence[str] | None = None) -> int` — `info` subcommand
    (argparse): load both default files, print counts + columns + a 1:1
    join-consistency line; thin wrapper. `main([])` (no subcommand) returns
    non-zero without raising.

- **Tests** — `tests/synthetic/test_loaders.py`. Always-on stdlib tier
  (`load_modifications` round-trip via a hand-written JSONL fixture, the
  fail-loud `LoaderError` join-mismatch construction where it can be exercised
  without a frame, import-hygiene + no-side-effects audits, `main([])` exit) +
  a `pyarrow`-gated tier (`load_items` reads a `write_release`-produced Parquet;
  `join` 1:1 + `modifications`-column shape + mismatch fail-loud; `long_view` /
  `short_view` column set + `text`/`text_norm` correctness against
  `normalize_text`) + a data-gated + `pyarrow`-gated tier (join one real
  `OBRA CIVIL` concept end-to-end: `stage_b → join_intermediate → write_release →
  load_items + load_modifications → join` is 1:1; `long_view`/`short_view`
  preserve the `item_key` set). The data-gated tier is also `pyarrow`-gated.

- **Doc + housekeeping**:
  - Flip the ✅ `loaders.py` row in the "New Files in This Branch" map in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) (currently ❌); record the
    read-only / build-on-`packaging` / join-1:1 / long-short-projection /
    `text_norm`-derived decisions near the `packaging.py` row. Prepend an
    "After Sprint 22" Sprint History entry.
  - Sprint 22 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip the `G2` portion of the "Dataset packager + loader utilities" §3 status
    row in [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — that row is now
    🟡 (G1 ✅ / G2 ❌); on G2 ship, flip it ✅ (G1–G2 both done). Status flip only —
    no design edit. Do not otherwise edit the protocol.

### Out of scope (explicit)

- **The Phase F pilot (F1–F4) and the LLM transport (A3).** F1–F2 are blocked on
  A3; G2 needs neither. No generation happens this sprint — G2 reads whatever
  `write_release` already produced.
- **`DATA_CARD.md` (G3), `README.md` "Synthetic Variant" section (G3),
  `HANDOFF.md` (G4).** Documentation/handoff is the next Phase-G sprint — better
  written once the loader API it documents exists.
- **Any new on-disk artifact.** G2 is read-only. It writes no `_long_norm` /
  `_short_norm` / `_feats` Parquet; the projections are in-memory frames. (If a
  later sprint decides the long/short views must be materialised on disk, that is
  a separate packaging-side task, not G2.)
- **`bc3cat-retrieval` wiring.** G2 ships the loader API on *this* side of the
  cross-repo boundary; the downstream `import`/index integration is G4 + a
  `bc3cat-retrieval` change, not this sprint.
- **Changes to `packaging.py`, `metadata.py`, `review.py`, `stage_b.py`,
  `run_synthetic.py`, `stage_runners.py`, any `layer_*` / `mutator` module.** G2
  *consumes* the G1 artifacts. A malformed release is a G1/E2 bug already caught
  on the write path.
- **Multi-chapter generality of the data-gated test.** Pinned to `OBRA CIVIL`,
  as in Sprints 17–21.

---

## Behavioural requirements

1. **`load_items` returns the `ITEM_COLUMNS` frame from a `write_release`
   Parquet.** Round-trips the Sprint 21 artifact; `list(df.columns) ==
   list(packaging.ITEM_COLUMNS)`. Pinned (`pyarrow`-gated).
2. **`load_modifications` returns `{item_key: [Modification, ...]}` from the
   sidecar JSONL.** Reconstructs `Modification`s (`from_dict`); baseline →
   `[]`. Pinned (always-on stdlib).
3. **`join` is 1:1 on `item_key` and fail-loud on mismatch.** A clean release
   joins every items row to exactly one sidecar entry; the result carries a
   `modifications` column (`list[dict]`) and no dropped/duplicated rows. A
   sidecar missing an items key (or vice-versa) raises `LoaderError` before
   returning. Pinned (`pyarrow`-gated for the frame path; the mismatch raise also
   exercised on a hand-built frame).
4. **`long_view` / `short_view` carry a single `text` column + derived
   `text_norm`.** `long_view` `text == texto`, `short_view` `text == resumen`;
   `text_norm == normalize_text(text)` cell-for-cell; the key+metadata columns
   are preserved; no OEB-only `id`/`ud`/`concept` columns are fabricated;
   `modifications` is absent from both views. Pinned (`pyarrow`-gated).
5. **`join` does not mutate its input frame.** The returned frame is a copy; the
   caller's `items` is unchanged (no in-place `modifications` column). Pinned.
6. **`loaders.py` imports neither `stage_b`, `run_synthetic`, `stage_runners`,
   `review`, `mutator`, nor any `layer_*`.** It imports `packaging`, `metadata`,
   `taxonomy`, `utils.config`, `utils.text_processing`, `pandas`, stdlib only.
   Pinned by source + `__dict__` audits (the Sprint 17–21 hygiene shape).
7. **No module-level side effects; no *new repo* dependency.** Stdlib + in-repo +
   the already-required `pandas`/`pyarrow`. Pinned by `importlib.reload`. Default
   paths resolve at call time, not import time. The CLI `main([])` (no
   subcommand) returns non-zero without raising.

---

## Acceptance

- `from synthetic.loaders import (LoaderError, load_items, load_modifications,
  join, long_view, short_view, main)` succeeds.
- On a `write_release`-produced release (inline mixed fixture: single-mod +
  stacked + baseline): `load_items` returns the `ITEM_COLUMNS` frame;
  `load_modifications` returns one entry per `item_key` (baseline → `[]`);
  `join` returns a frame with a `modifications` column, 1:1 on `item_key`, input
  frame unmutated; `long_view`/`short_view` carry `text` + `text_norm ==
  normalize_text(text)` and the key/metadata columns, no `modifications`.
- A deliberately mismatched (`item_key` present in items, absent in sidecar)
  join raises `LoaderError` and returns nothing.
- **Data-gated + `pyarrow`-gated (OBRA CIVIL):** materialise one real concept
  (Sprint 19 `stage_b → join_intermediate`), `write_release` it, then
  `load_items` + `load_modifications` + `join` round-trip to a 1:1 frame whose
  `item_key` set equals the joined set; `long_view`/`short_view` preserve that
  set. Skipped when intermediate data **or** `pyarrow` is absent.
- `pytest tests -q` exits 0 with **≥ (Sprint 21 baseline 703) + (new always-on
  count) passed**, the Sprint 12 brace audit still **1 skipped**, plus the new
  `pyarrow`-gated / data-gated tests passing in César's tree and **skipping
  (never failing) in any tree** without `pyarrow` or the intermediate data.

---

## Tasks

### Task 1 — `src/synthetic/loaders.py`
1. `LoaderError(ValueError)` + the default-path helpers (resolve at call time).
2. `load_items` / `load_modifications` (thin wrappers over `packaging.read_*`;
   `load_modifications` always-on stdlib).
3. `join` (load-or-accept both; 1:1 `item_key` assertion, fail-loud `LoaderError`
   on mismatch; add `modifications` `list[dict]` column to a **copy**).
4. `long_view` / `short_view` (rename text col → `text`, keep key+metadata
   columns, add derived `text_norm` via `utils.text_processing.normalize_text`;
   pure, in-memory).
5. `main(argv)` — `info` subcommand (thin argparse wrapper); `main([])` → non-zero.
6. Import-hygiene + no-side-effects discipline; lazy `pandas` import.

### Task 2 — `tests/synthetic/test_loaders.py`
Always-on stdlib tier (`load_modifications` round-trip from a hand-written JSONL
fixture, `LoaderError` mismatch where exercisable without a frame, import-hygiene,
no-side-effects, `main([])` exit) + `pyarrow`-gated tier (`load_items` round-trip,
`join` 1:1 + `modifications`-column shape + no-mutation + mismatch fail-loud,
`long_view`/`short_view` columns + `text`/`text_norm`) + 1 data-gated (`OBRA
CIVIL` `write_release → load → join` 1:1). Suggested cases:
- `test_module_exposes_public_surface`
- `test_loaders_imports_no_generation_or_review_stack`
- `test_module_has_no_side_effects_at_import`
- `test_default_paths_resolve_under_processed_dir`
- `test_load_modifications_round_trip` *(always-on)*
- `test_load_modifications_baseline_empty_list` *(always-on)*
- `test_join_mismatch_is_fail_loud` *(always-on where frame-free; else pyarrow-gated)*
- `test_main_no_subcommand_returns_nonzero`
- `test_load_items_round_trip` *(pyarrow-gated)*
- `test_join_one_to_one_adds_modifications_column` *(pyarrow-gated)*
- `test_join_does_not_mutate_input` *(pyarrow-gated)*
- `test_long_view_text_is_texto_and_norm_matches` *(pyarrow-gated)*
- `test_short_view_text_is_resumen_and_norm_matches` *(pyarrow-gated)*
- `test_views_have_no_modifications_column` *(pyarrow-gated)*
- **Data-gated + pyarrow-gated:** `test_real_concept_round_trip_load_join_views`

### Task 3 — Housekeeping
1. Prepend a Sprint 22 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the G2-over-G3/A3 sequencing
   decision, the read-only / build-on-`packaging` decision, the join-1:1
   fail-loud decision, the long/short + derived-`text_norm` decision (and the
   "no new on-disk artifact" invariant), the `pyarrow`-gating decision, the
   test-count delta, and the next step (Sprint 23 — G3/G4 and/or A3).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): flip the ✅ `loaders.py`
   row; record the loader decisions near the `packaging.py` note; prepend the
   "After Sprint 22" history entry.
3. In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §3: flip the
   `Dataset packager + loader utilities` row 🟡 → ✅ (G1–G2 both done) — status
   only, no design edit.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
# A stale %TEMP%\pytest-of-cesar\pytest-current symlink can raise WinError 5
# during pytest's tmp-cleanup; route to a fresh basetemp to sidestep it.
pytest tests -q --basetemp="$env:TEMP\pt_s22"
```

Expected: the Sprint 21 count **plus** the new always-on tests passed, **1
skipped** (Sprint 12 brace audit) with `pyarrow` + intermediate data present;
**zero failures** in any tree (the `pyarrow`/data-gated tests skip, never fail).

Optional end-to-end smoke (manual, with a real release on disk — run the Sprint
21 smoke first to produce it):

```powershell
# python -c "from synthetic.loaders import load_items, load_modifications, join, long_view; \
#   df=join(); print(len(df),'rows', list(df.columns)); \
#   lv=long_view(load_items()); print('long_view cols', list(lv.columns))"
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/loaders.py
new file:   tests/synthetic/test_loaders.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_22.md (this file)
```

No edits to `packaging.py`, `metadata.py`, `review.py`, `stage_b.py`,
`run_synthetic.py`, `stage_runners.py`, `mutator.py`, any `layer_*` module, or
`cache_hygiene.py`; no new *repo* dependency (`pandas`/`pyarrow` are already
required by the main pipeline).

---

## Design notes worth committing to memory

- **G2 consumes; it neither generates nor packages.** The loader is a read-only
  function of the two G1 files. No LLM, no pipeline rerun, no new on-disk
  artifact — every projection is an in-memory, re-derivable frame.
- **Build on `packaging`, don't re-parse.** `loaders` calls
  `packaging.read_items_parquet` / `read_modifications_jsonl`; the file format
  contract lives in one place (G1), the consumer ergonomics in another (G2).
- **`join()` re-attaches what the Parquet deliberately dropped.** G1 keeps the
  ragged `modifications` log in the sidecar to keep the columnar table flat; G2's
  `join()` is the in-memory reunion for consumers that want per-row provenance —
  1:1 and fail-loud, never a silent partial.
- **The long/short views mirror the OEB *record*, not its LlamaIndex columns.**
  `text` + `text_norm` + keys + slice metadata; no fabricated `id`/`ud`/`concept`.
  `text_norm` is `utils.text_processing.normalize_text` reused verbatim, so the
  synthetic lexical column matches the OEB `_norm` columns byte-for-byte.
- **`pyarrow` stays gated; the stdlib JSONL path stays always-on.** Same rule as
  Sprint 21 — any tree stays green.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase G`](../RESEARCH_PROTOCOL.md) — G2 (loaders,
  this sprint: `load_items`/`load_modifications`/`join`), G3 (docs, next), G4
  (handoff); §3 status row; §7 file map.
- [`SPRINT_21.md`](SPRINT_21.md) / [`../../src/synthetic/packaging.py`](../../src/synthetic/packaging.py)
  — the G1 release (the loader input): `ITEM_COLUMNS`, `read_items_parquet`,
  `read_modifications_jsonl`, `ITEMS_FILENAME`/`MODIFICATIONS_FILENAME`, the
  atomic-write + import-hygiene + `pyarrow`-gating + data-gating patterns reused
  here.
- [`SPRINT_19.md`](SPRINT_19.md) / [`../../src/synthetic/metadata.py`](../../src/synthetic/metadata.py)
  — `SyntheticItem` / `join_intermediate` (the data-gated source), `validate_items`.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) —
  `Modification.to_dict` / `from_dict` (the sidecar payload, the `join` column).
- [`../../src/utils/text_processing.py`](../../src/utils/text_processing.py) —
  `normalize_text` (the exact `text_norm` derivation; reuse, do not re-implement).
- [`../../src/utils/config.py`](../../src/utils/config.py) —
  `SYNTHETIC_PROCESSED_DIR` (release home / default loader input;
  already present — **no config change this sprint**).
- [`../../src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb)
  — the OEB long/short layout precedent (`OEB_long_norm`/`OEB_short_norm`:
  `text` + `text_norm`); G2 mirrors the *record subset* + `text_norm`, not the
  OEB-only LlamaIndex columns.
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.3 per-item record
  (the items-frame columns); §5 release-format note (Parquet items + sidecar
  JSONL of `modifications`).

---

## Non-goals reminder

If you find yourself wiring an `LLMClient`, calling a model, or running
`run_synthetic` / `stage_b` to *generate* items — **stop**. That is Stage A/B and
(for a real pilot) A3. G2 reads `write_release()` output only.

If you find yourself writing a `write_*` / emitting a new `_long_norm` /
`_short_norm` / `_feats` Parquet on disk — **stop**. G2 is read-only; the
projections are in-memory frames. Materialising a new release file is a separate
packaging-side task, not G2.

If you find yourself re-parsing Parquet/JSONL by hand instead of calling
`packaging.read_items_parquet` / `read_modifications_jsonl` — **stop**. The file
format contract lives in `packaging` (G1); `loaders` builds on it.

If you find yourself fabricating OEB-only columns (`id`, `ud`, `concept`) the
synthetic §2.3 record never carried, or re-implementing `normalize_text` instead
of importing it — **stop**. The long/short views mirror the record subset +
`text_norm`; the normalizer is reused verbatim (decisions 3–4).

If you find yourself importing `stage_b` / `run_synthetic` / `stage_runners` /
`review` / `mutator` / a `layer_*` module into `loaders.py` — **stop**. The
consume path is `packaging.read_* → join/project`; the generation and review
stacks are not in it (requirement 6).

If you find yourself letting a missing `pyarrow` *fail* the suite — **stop**.
Gate the frame/Parquet tests with `pytest.importorskip("pyarrow")`; the stdlib
`load_modifications` path stays always-on (requirement 7 / "zero failures in any
tree").

If you find yourself writing `DATA_CARD.md`, the README "Synthetic Variant"
section, or `HANDOFF.md` — **stop**. That is G3/G4 (Sprint 23+). G2 ships the
loader API only.
