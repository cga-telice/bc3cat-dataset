# Sprint 20 — Phase E Tasks E3 (validation sampler) + E4 (domain-reviewer harness)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 20                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | E3, E4 (see [`../RESEARCH_PROTOCOL.md §5 Phase E`](../RESEARCH_PROTOCOL.md))                |
| **Predecessor** | Sprint 19 — `metadata.py` (E1: variant-grained → item-grained join + E2: schema validator) (see [`SPRINT_19.md`](SPRINT_19.md)) |
| **Successor**   | Sprint 21 — Phase F (F1–F2: single-concept pilot generation + pilot retro) and/or Phase G (G1: Parquet + JSONL packaging) |

---

## Context

Sprint 19 closed E1/E2: [`metadata.py`](../../src/synthetic/metadata.py) turns the
variant-grained Stage-B payloads into a flat list of `SyntheticItem` release
records (one per leaf), each carrying the traceability triple
`(item_key, original_key, variante_id)`, a recomputed
`modification_types`/`modification_count`, and the full `modifications` log;
`validate_items` fail-loud-asserts they are well-formed.

What is **still missing** before any benchmark can ship is the *quality gate*.
Full manual review of every synthetic item is unrealistic at scale (Phase F3
runs across all 25 concept groups). The protocol's answer is **stratified
sampling** (proposal Stage D / [`../RESEARCH_PROTOCOL.md §5 E3–E4`](../RESEARCH_PROTOCOL.md)):

- **E3 — validation sampler.** Stratify the `SyntheticItem`s over
  `(concept_key × modification_type)` cells; surface a deterministic review
  queue hitting a per-cell coverage target, with **100 % coverage for
  `new_param`** (the proposal §4 / risk-table decision — `new_param` carries the
  highest semantic-collision risk and is reviewed in full).
- **E4 — domain-reviewer harness.** [`src/synthetic/review.py`](../../src/synthetic/review.py)
  captures, per sampled item, four verdicts (proposal Stage D):
  (i) grammatical Spanish, (ii) parametric-meaning preservation,
  (iii) `new_param` axis distinguishability (no semantic collision),
  (iv) metadata accuracy. When ≥2 reviewers score the same item it records
  inter-annotator agreement.

This sprint builds **both** as one module (`review.py`): a pure sampling +
agreement library plus a thin CLI. It does **not** run a real review pass — that
is **F4** (the validation pass that produces `docs/synthetic/QUALITY_REPORT.md`).
E3/E4 build the *machinery*; F4 *uses* it.

### The load-bearing design decisions (decide up front)

1. **The unit of review is the `SyntheticItem`; the stratum is
   `(concept_key, ModificationType)`.** A single-type variant's items land in
   exactly one cell. A *stacked* variant's item (multiple `modification_types`)
   is a member of **each** of its types' cells — it can be drawn to satisfy any
   of them. The final queue is **de-duplicated by `item_key`** (an item reviewed
   once covers every cell it was drawn for), so coverage is computed *per cell*
   but the reviewer never sees the same item twice.

2. **`new_param` is sampled at 100 %; every other type at a coverage fraction
   with a per-cell floor.** Defaults: `coverage = 0.10`, `floor = 5` (capped at
   the cell size — a 3-item cell yields 3, not an error). `full_coverage_types =
   {NEW_PARAM}`. These are *arguments*, not constants baked into the logic
   (open question §10.3 — the concrete thresholds are tunable; F2 retro may
   revise them). The floor-vs-fraction rule: `n_sampled = min(cell_size,
   max(floor, ceil(coverage * cell_size)))`; full-coverage cells take the whole
   cell.

3. **Sampling is deterministic and seeded.** Candidate `item_key`s are sorted,
   then a seeded selection (`random.Random(seed)` over the sorted keys, or a
   stable hash) picks the cell's sample. Run-twice-equal is a pinned invariant —
   a review queue must be reproducible so a re-run does not reshuffle reviewer
   assignments.

4. **Zero-modification baselines are excluded from the review queue.** A
   `SyntheticItem` with `modification_count == 0` has nothing to review; it is
   reported in a separate `baselines` count in the coverage report, never queued.
   (Mirrors Sprint 19 decision 4: keep baselines, flag them — here, flag-and-skip.)

5. **E4 does not load the baseline catalog text.** Semantic-preservation review
   works off the per-`Modification` `original`/`new` fragments already in the
   item's `modifications` log (the reviewer sees *what changed*), plus the
   synthetic `resumen`/`texto`. A full original-vs-synthetic side-by-side that
   re-expands the unmutated catalog row is **baseline-dependent and deferred to
   F4** (the same deferral Sprint 19 made for the `original_key`-existence
   cross-check). `review.py` stays decoupled: it imports `metadata` + `taxonomy`
   + `utils.config` + stdlib only — **no** `stage_b` / `run_synthetic` /
   `stage_runners`, **no** baseline re-expansion.

6. **Verdicts persist as JSONL keyed by `(item_key, reviewer)`; agreement is
   computed only over items with ≥2 reviewers.** Inter-annotator agreement is
   **percent agreement + Cohen's κ** per verdict dimension, hand-rolled in
   stdlib (no `sklearn`/`pandas`). `axis_distinguishable` is `Optional[bool]` —
   `None` for non-`new_param` items — and is scored/agreed only over the
   `new_param` subset.

7. **The CLI is a thin wrapper; the library is the contract.** `python -m
   synthetic.review build` reads `SYNTHETIC_INTERMEDIATE_DIR` via
   `metadata.join_intermediate`, samples, and writes the queue;
   `python -m synthetic.review agree` reads recorded verdicts and prints the
   agreement table. All logic is tested through the library functions; the CLI
   `main(argv)` is smoke-tested for argument wiring only.

---

## Scope

### In scope

- **E3 — stratified sampler, new module `src/synthetic/review.py`.** Public
  surface:

  - `@dataclass(frozen=True) ReviewTask` — `item_key, concept_key,
    modification_types (tuple[ModificationType,...]), modification_count,
    resumen, texto, modifications (tuple[Modification,...]),
    strata (tuple[tuple[str, ModificationType], ...])` + `to_dict()`.
  - `stratify(items: Iterable[SyntheticItem]) -> dict[tuple[str,
    ModificationType], list[SyntheticItem]]` — pure; one entry per
    `(concept_key, type)` cell; baselines excluded; stacked items appear in each
    of their types' cells.
  - `@dataclass(frozen=True) CoverageReport` — per-cell `size`/`sampled`/
    `target`/`fraction`, total `queued`, total `baselines`, plus `to_dict()`.
  - `sample_review_queue(items, *, coverage=0.10, floor=5,
    full_coverage_types=frozenset({ModificationType.NEW_PARAM}), seed=0) ->
    tuple[list[ReviewTask], CoverageReport]` — the deterministic core (decision
    2 floor/fraction rule, decision 3 seeded selection, decision 1 de-dup by
    `item_key`). Tasks returned in a stable order (sorted by `item_key`).
  - `write_queue(tasks, path)` / `read_queue(path) -> list[ReviewTask]` — JSONL,
    atomic write (`.tmp` rename, the `variant_catalog`/`stage_b` discipline).

- **E4 — reviewer harness, in `review.py`.**
  - `@dataclass(frozen=True) Verdict` — `item_key, reviewer, grammatical (bool),
    semantic_preserved (bool), axis_distinguishable (Optional[bool]),
    metadata_accurate (bool), notes (str = "")` + `to_dict`/`from_dict`.
  - `write_verdicts(verdicts, path)` / `read_verdicts(path) -> list[Verdict]` —
    JSONL keyed by `(item_key, reviewer)`; dedup-on-write (last wins) is
    out of scope — a duplicate `(item_key, reviewer)` is a fail-loud
    `ReviewError`.
  - `class AgreementStat` (frozen) — `dimension, n_items, percent_agreement,
    cohen_kappa (Optional[float])`; `agreement(verdicts) -> dict[str,
    AgreementStat]` over the four dimensions, computed only across items with
    ≥2 reviewers (`axis_distinguishable` only over the `new_param` subset where
    it is non-`None`). κ is `None` when undefined (single annotator, or zero
    expected-disagreement degenerate case).
  - `class ReviewError(ValueError)` — distinct, catchable failure type
    (duplicate verdict key, malformed queue/verdict record).
  - `main(argv: Sequence[str] | None = None) -> int` — `build` / `agree`
    subcommands (argparse); thin wrapper over the library.

- **Minimal config addition.** Add `SYNTHETIC_REVIEW_DIR = SYNTHETIC_DATA_ROOT /
  "review"` to [`../../src/utils/config.py`](../../src/utils/config.py) (the
  default home for the queue + verdict JSONL). One constant, no behavioural
  change to existing paths.

- **Tests** — `tests/synthetic/test_review.py`. Always-on inline-fixture tier
  (hand-built `SyntheticItem`s — single-type, stacked, `new_param`, baseline) +
  a data-gated tier that joins one real `OBRA CIVIL` concept (Sprint 19's
  `stage_b → join`) and samples + reports over it.

- **Doc + housekeeping**:
  - Add a ✅ `review.py` row to the "New Files in This Branch" map in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); add the
    `SYNTHETIC_REVIEW_DIR` path; prepend an "After Sprint 20" Sprint History
    entry; record the stratum key `(concept_key, modification_type)`, the
    100 %-`new_param` rule, and the coverage/floor defaults.
  - Sprint 20 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip the `E3–E4` row in [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md)
    §3 status table ❌ → ✅ (this is a status flip, not a design change — allowed).

### Out of scope (explicit)

- **Running a real validation pass / writing `QUALITY_REPORT.md` (`F4`).** E3/E4
  build the sampler + harness; *using* them on real reviewers' verdicts to
  produce the quality report is Phase F. No `QUALITY_REPORT.md` this sprint.
- **Parquet / sidecar JSONL release packaging (`G1`).** The queue + verdicts are
  reviewer-workflow JSONL, not the release artifact. No `pandas`/`pyarrow`.
- **Baseline-text re-expansion for original-vs-synthetic side-by-side.** Decision
  5 — deferred to F4 (baseline-dependent). E4 reviews off the `modifications`
  log + synthetic text.
- **A GUI / notebook reviewer UI.** The harness is a library + a minimal argparse
  CLI; a notebook front-end (if wanted) is downstream and not gated on this.
- **Changes to `metadata.py`, `stage_b.py`, `run_synthetic.py`, `stage_runners.py`,
  any `layer_*` / `mutator` module.** E3 *consumes* `SyntheticItem`s as-is. If a
  record is malformed, that is an E1/E2 bug — `validate_items` (Sprint 19)
  catches it upstream; the sampler assumes validated input.
- **Statistical power analysis / optimal-coverage derivation.** The coverage
  fraction + floor are tunable arguments seeded with the proposal's defaults
  (§10.3); deriving optimal thresholds is an F2-retro analysis, not a Sprint-20
  library concern.
- **Multi-chapter generality of the data-gated test.** Pinned to `OBRA CIVIL`,
  as in Sprints 17–19.

---

## Behavioural requirements

1. **Stratify keys on `(concept_key, modification_type)`; baselines excluded.**
   A 2-concept, mixed-type fixture yields the expected cell set; a
   `modification_count == 0` item appears in **no** cell and increments
   `CoverageReport.baselines`. Pinned.
2. **Stacked items are members of every type's cell but queued once.** A
   2-type item appears in both cells' candidate lists; the returned queue has
   exactly one `ReviewTask` for it, whose `strata` lists both cells. Pinned.
3. **`new_param` cells are sampled at 100 %.** Every `new_param` item in a cell
   is queued regardless of `coverage`. Pinned on a `new_param` fixture larger
   than `ceil(coverage * size)`.
4. **Non-`new_param` cells obey `min(size, max(floor, ceil(coverage·size)))`.**
   Pinned: a 3-item cell with `floor=5` yields 3; a 100-item cell with
   `coverage=0.10, floor=5` yields 10; a 20-item cell with `coverage=0.10,
   floor=5` yields 5.
5. **Sampling is deterministic + seeded.** Same `(items, coverage, floor, seed)`
   → identical queue (`item_key` order + membership); a different `seed` may
   change *which* items (not how many). Run-twice-equal pinned.
6. **Queue round-trips through JSONL.** `read_queue(write_queue(q)) == q`
   (`ReviewTask` equality); atomic write leaves no `.tmp`. Pinned on `tmp_path`.
7. **Verdict round-trips; duplicate `(item_key, reviewer)` is fail-loud.**
   `read_verdicts(write_verdicts(v)) == v`; a second verdict for the same
   `(item_key, reviewer)` raises `ReviewError`. `axis_distinguishable` survives
   the `None` round-trip. Pinned.
8. **Agreement is percent + κ over ≥2-reviewer items only.** Two reviewers
   agreeing on every dimension → `percent_agreement == 1.0`; a planted
   disagreement drops it; single-reviewer items contribute nothing.
   `axis_distinguishable` agreement is computed only over the `new_param`
   subset. κ is `None` when undefined. Pinned (hand-checked κ on a tiny table).
9. **`review.py` imports neither `stage_b`, `run_synthetic`, nor `stage_runners`.**
   Pinned by source + `__dict__` audits (same shape as the Sprint 17–19 hygiene
   audits). It imports `metadata`, `taxonomy`, `utils.config`, stdlib only.
10. **No new runtime dependencies; no module-level side effects.** Stdlib +
    in-repo. Pinned by `importlib.reload`. The CLI `main([])` (no subcommand)
    returns non-zero without raising.

---

## Acceptance

- `from synthetic.review import (ReviewTask, CoverageReport, Verdict,
  AgreementStat, ReviewError, stratify, sample_review_queue, write_queue,
  read_queue, write_verdicts, read_verdicts, agreement, main)` succeeds.
- On an inline mixed-type fixture (single-type + stacked + `new_param` +
  baseline): `stratify` produces the expected cells (baseline absent);
  `sample_review_queue` returns a deduped queue with every `new_param` item, the
  floor/fraction count per other cell, and a `CoverageReport` whose `baselines`
  counts the excluded baseline.
- `sample_review_queue(...) == sample_review_queue(...)` for equal args (seeded
  determinism).
- `read_queue(write_queue(q, p)) == q` and `read_verdicts(write_verdicts(v, p))
  == v`; a duplicate-keyed verdict raises `ReviewError`.
- `agreement` on a 2-reviewer table returns `percent_agreement == 1.0` on full
  agreement and `< 1.0` with a planted disagreement; κ matches a hand-computed
  value on a pinned 2×2 table.
- **Data-gated (OBRA CIVIL):** join one real concept (Sprint 19
  `stage_b → join_intermediate`), `sample_review_queue` it, assert the queue ⊆
  the joined items, every queued task passes a shape check, and the
  `CoverageReport` cell counts sum consistently. Skipped when intermediate data
  is absent.
- `pytest tests -q` exits 0 with **≥679 passed** (Sprint 19 baseline 655 with
  data — 654 always-on + 1 data-gated — plus ≥24 new always-on functions),
  **1 skipped** (the Sprint 12 brace audit) in César's tree; **zero failures**
  in any tree (data-gated tests skip, never fail).

---

## Tasks

### Task 1 — `src/synthetic/review.py`
1. `ReviewTask` + `CoverageReport` frozen dataclasses + `to_dict()`.
2. `stratify` (pure cell builder; baselines excluded; stacked → multi-cell).
3. `sample_review_queue` (floor/fraction rule, 100 %-`new_param`, seeded
   deterministic selection, de-dup by `item_key`, coverage report).
4. `write_queue` / `read_queue` (atomic JSONL).
5. `Verdict` + `write_verdicts` / `read_verdicts` (JSONL, fail-loud duplicate
   key) + `ReviewError`.
6. `AgreementStat` + `agreement` (percent + Cohen's κ, ≥2-reviewer subset,
   `axis_distinguishable` over `new_param` only).
7. `main(argv)` — `build` / `agree` subcommands (thin argparse wrapper).
8. Import-hygiene + no-side-effects discipline.

### Task 2 — `src/utils/config.py`
1. Add `SYNTHETIC_REVIEW_DIR = SYNTHETIC_DATA_ROOT / "review"` (one line, beside
   the other `SYNTHETIC_*` paths).

### Task 3 — `tests/synthetic/test_review.py`
≥24 always-on functions + 1 data-gated. Suggested cases:
- `test_module_exposes_public_surface`
- `test_review_does_not_import_stage_b_run_synthetic_or_stage_runners`
- `test_module_has_no_side_effects_at_import`
- `test_stratify_keys_on_concept_and_type`
- `test_stratify_excludes_baselines`
- `test_stratify_stacked_item_in_every_type_cell`
- `test_sample_new_param_full_coverage`
- `test_sample_floor_caps_at_cell_size`
- `test_sample_fraction_above_floor`
- `test_sample_floor_dominates_small_cell`
- `test_sample_dedups_stacked_item_to_one_task`
- `test_sample_task_strata_lists_all_cells`
- `test_sample_deterministic_same_seed`
- `test_sample_seed_changes_selection_not_count`
- `test_coverage_report_counts_baselines`
- `test_coverage_report_cell_sums_consistent`
- `test_review_task_to_dict_shape`
- `test_queue_jsonl_round_trip` (tmp_path)
- `test_queue_atomic_no_tmp_left` (tmp_path)
- `test_verdict_round_trip_including_none_axis` (tmp_path)
- `test_verdict_duplicate_key_is_fail_loud`
- `test_agreement_full_agreement_is_one`
- `test_agreement_disagreement_below_one`
- `test_agreement_kappa_matches_hand_value`
- `test_agreement_axis_only_over_new_param`
- `test_agreement_ignores_single_reviewer_items`
- `test_main_no_subcommand_returns_nonzero`
- **Data-gated:** `test_sample_real_concept_queue_subset_of_items`

### Task 4 — Housekeeping
1. Prepend a Sprint 20 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the stratum-key decision, the
   100 %-`new_param` + floor/fraction rule (with the defaults and §10.3 tie-in),
   the baseline-exclusion decision, the agreement-metric choice (percent + κ,
   ≥2-reviewer subset), the F4 baseline-text deferral, the test-count delta, and
   the next step (Sprint 21 — Phase F pilot and/or G1 packaging).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): add the ✅ `review.py`
   row + the `SYNTHETIC_REVIEW_DIR` path; record the stratum key + coverage
   defaults near the validation/quality notes; prepend the "After Sprint 20"
   history entry.
3. Flip the `E3–E4` status row in
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §3 ❌ → ✅. Do **not**
   otherwise edit the protocol or [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md).

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
# Note: a stale %TEMP%\pytest-of-cesar\pytest-current symlink can raise WinError 5
# during pytest's tmp-cleanup; route to a fresh basetemp to sidestep it.
pytest tests -q --basetemp="$env:TEMP\pt_s20"
```

Expected: **≥679 passed, 1 skipped** with intermediate data present (0
data-gated skips); **zero failures** in any tree.

Optional end-to-end smoke (manual, with real per-variant JSON under
`data/synthetic/intermediate/`):

```powershell
# python -c "from synthetic.metadata import join_intermediate; from synthetic.review import sample_review_queue, write_queue; \
#   items=join_intermediate(); q,rep=sample_review_queue(items); \
#   from utils import config; config.SYNTHETIC_REVIEW_DIR.mkdir(parents=True, exist_ok=True); \
#   write_queue(q, config.SYNTHETIC_REVIEW_DIR/'queue.jsonl'); print(len(q),'queued;', rep.to_dict())"
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/review.py
new file:   tests/synthetic/test_review.py
modified:   src/utils/config.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_20.md (this file)
```

No edits to `metadata.py`, `stage_b.py`, `run_synthetic.py`, `stage_runners.py`,
`mutator.py`, any `layer_*` module, or `cache_hygiene.py`; no new dependencies.

---

## Design notes worth committing to memory

- **Sampler builds the queue; F4 burns it down.** E3/E4 are the *machinery*
  (stratify → sample → capture verdicts → measure agreement). The actual review
  pass + `QUALITY_REPORT.md` is F4. Keeping them apart means the sampler is a
  pure, re-runnable library and the review is a one-time human process layered
  on top.
- **`new_param` is the 100 %-review type.** Highest semantic-collision risk
  (proposal §4); the sampler hard-codes nothing but takes `full_coverage_types`
  defaulting to `{NEW_PARAM}` so the policy is visible and tunable.
- **Stratify by `(concept, type)`, queue by `item_key`.** Coverage is a per-cell
  property; reviewer effort is a per-item property. The two are reconciled by
  de-duplicating the drawn candidates into one task per item.
- **Agreement only where there is agreement to measure.** Percent + κ over the
  ≥2-reviewer subset; `axis_distinguishable` over `new_param` only. Single-
  reviewer items carry no agreement signal and are excluded, not defaulted.
- **E4 reviews the diff, not the baseline.** The `modifications` log already
  carries `original`/`new`; full baseline re-expansion is F4's job. `review.py`
  stays decoupled from the generation stack.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase E`](../RESEARCH_PROTOCOL.md) — E3 (sampler,
  this sprint), E4 (reviewer harness, this sprint); §10.3 (coverage thresholds);
  §3 status table (the E3–E4 row to flip).
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — Stage D validation
  (§ "Stage D — Validation": the four verdict checks); §4 risk table
  (100 %-`new_param` review, target inter-annotator agreement).
- [`SPRINT_19.md`](SPRINT_19.md) — E1/E2; the `SyntheticItem` record + `to_dict`
  + `join_intermediate` this sprint consumes; the baseline-text deferral pattern
  reused for decision 5.
- [`../../src/synthetic/metadata.py`](../../src/synthetic/metadata.py) —
  `SyntheticItem` (the sampler input), `join_intermediate` (the data-gated
  source), `validate_items` (the upstream gate the sampler trusts).
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) —
  `ModificationType` (`NEW_PARAM` is the full-coverage type), `Modification`.
- [`../../src/utils/config.py`](../../src/utils/config.py) —
  `SYNTHETIC_INTERMEDIATE_DIR` (sampler input dir), `SYNTHETIC_REVIEW_DIR` (new
  this sprint — queue + verdict home).

---

## Non-goals reminder

If you find yourself adding `pandas` / `pyarrow` / `sklearn` — **stop**. The
queue + verdicts are workflow JSONL; agreement is hand-rolled stdlib κ; Parquet
packaging is G1.

If you find yourself writing `docs/synthetic/QUALITY_REPORT.md` or running a real
review pass — **stop**. That is F4. This sprint builds the sampler + harness, not
the report.

If you find yourself importing `stage_b` / `run_synthetic` / `stage_runners` into
`review.py`, or re-expanding the baseline catalog for an original-vs-synthetic
view — **stop**. E4 reviews off the `modifications` log + synthetic text;
baseline join is F4 (decision 5). The `metadata.SyntheticItem` record is the
contract.

If you find yourself editing `metadata.py` / a `layer_*` mutator / `stage_b` to
make the sampler work — **stop**. The sampler consumes *validated*
`SyntheticItem`s; a malformed record is an E1/E2 bug `validate_items` already
catches.

If you find yourself making `sample_review_queue` non-deterministic (unseeded
`random`, set-iteration order, dict-insertion reliance) — **stop**. A review
queue must be reproducible (requirement 5).
