# Sprint 27 — Phase F Task F1-build (pilot harness: the `f1_pilot.py` driver + a `stage_b` pre-rerun hook)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 27                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | F1-build (new split of F1) — the runnable harness. Code, hermetic. The live run + manual review are **F1-run** (Sprint 28). |
| **Predecessor** | Sprint 26 — B6 L2 representation adapter (`l2_repr.py`) (see [`SPRINT_26.md`](SPRINT_26.md)); Sprint 25 A3b-run decision (local **`llama3.1:8b`** via Ollama) |
| **Successor**   | Sprint 28 — **F1-run** (live local generation on `OEB070$` + 100 % manual review) (see [`SPRINT_28.md`](SPRINT_28.md)) → Sprint 29 F2 retro → F3 → F4 |

---

## Context

Everything the pilot needs **exists** except the orchestration that ties it
together for one concept with the L2 adapter bracketed in:

- `run_concept` (Stage A: enumerate → propose → emit → catalog), `stage_b`
  (apply rules + s03→s07 rerun → materialized items), `metadata.join_intermediate`
  (materialized variants → `SyntheticItem`s), `review.sample_review_queue`
  (stratified queue) — all built, frozen, test-pinned.
- `llm_client` (`HttpLLMClient`/`RecordingClient`/`ReplayClient`) and the
  `llama3.1:8b` config — A3a + the A3b-run decision.
- `l2_repr` (Sprint 26) — makes all three text-variable shapes enumerable for
  Stage A and restores them for the rerun.

What does **not** exist is the driver that composes these for the pilot, and there
is exactly **one structural blocker**: the two-mode `l2_repr` flow requires
`l2_repr.formula_to_list` to run **between** `apply_variant_rules` and
`run_stages_3_to_7`, but `stage_b.materialize_variant` / `materialize_catalog_entry`
**hard-wire apply→rerun with no insertion point** (verified: their signatures take
no hook). So before any live pilot run, two code changes must land — and they are
**hermetically testable with no live LLM call** (the live run is Sprint 28). That
build-vs-run split is the same discipline as A3a/A3b and the L2 work.

### The two changes (this sprint)

1. **A `pre_rerun` hook in `stage_b`** — the single, minimal, backward-compatible
   seam edit that lets the driver insert `formula_to_list` before the rerun.
2. **`src/synthetic/f1_pilot.py`** — the pilot driver: a *consumer above the
   orchestrator* (like `spike.py`) that brackets the mutation with the two-mode
   adapter, drives one concept across all §6 conditions through a
   `RecordingClient`, materializes, joins metadata, and builds a 100 %-coverage
   review queue, returning an automatable scorecard.

### Why a `stage_b` hook (and not just driver-side orchestration)

The alternative is to have the driver re-implement `materialize_variant`'s
per-variant loop (slice → apply → rerun → wrap `MaterializedVariant` → atomic
JSON write) so it can slot `formula_to_list` in the middle — duplicating tested
`stage_b` logic. A `pre_rerun: Callable[[dict], dict] = <identity>` parameter
(default identity) is strictly smaller, leaves **every existing caller and test
byte-identical**, and keeps the driver thin by reusing `materialize_catalog_entry`'s
write loop. It is the one deliberate seam touch this sprint makes; everything else
composes the frozen public surface. (If the no-seam-edit route is preferred, the
driver-orchestrates fallback is the explicit alternative — decide at Task 1.)

---

## Scope

### In scope

- **F1-build-1 — `stage_b` pre-rerun hook.** Add `pre_rerun: Callable[[dict],
  dict] = _identity` to `materialize_variant` and `materialize_catalog_entry`,
  applied to the mutated concept immediately before `run_stages_3_to_7`. Default
  is identity → no behavior change for existing callers (`run_stage_b`, all
  `test_stage_b` cases stay green). Documented as the single intentional seam edit.

- **F1-build-2 — `src/synthetic/f1_pilot.py` driver.**
  - `load_pilot_concept(stage_json, concept_key) -> dict` — slice one concept into
    a single-concept stage_json.
  - `PilotScore` (dataclass) — automatable scorecard: variants generated, skipped
    (split on the C2/C3 reason-prefixes, reusing the `spike`/catalog tally),
    materialized item count, review-queue size, coverage fraction, and the
    `assert_l2_targets_or_warn` count (proves L2 fired).
  - `run_pilot(concept, concept_key, *, conditions=ALL §6, client, store_root,
    variants_dir, intermediate_dir, review_dir, seed) -> PilotScore` — the
    composition:
    1. `enum = l2_repr.list_to_formula(concept, include_conditional=True)`;
       `assert_l2_targets_or_warn(concept)`.
    2. `entry, _ = run_concept(enum, key, conditions, RecordingClient(client, store),
       out_dir=variants_dir, seed=…)`.
    3. `appl = l2_repr.list_to_formula(concept, include_conditional=False)`.
    4. `materialize_catalog_entry(appl, entry, out_dir=intermediate_dir,
       pre_rerun=l2_repr.formula_to_list)`.
    5. `items = metadata.join_intermediate(intermediate_dir)`;
       `metadata.validate_items(items)`.
    6. `tasks, coverage = review.sample_review_queue(items, coverage=1.0)`;
       `review.write_queue(tasks, review_dir/…)`.
    7. tally + return `PilotScore`.
  - `default_conditions()` → all 17 `run_synthetic.CONDITION_SPECS` keys (full §6
    coverage).
  - Client injection: default = `HttpLLMClient(LLMConfig.from_env())` (model
    `llama3.1:8b`); a `replay=True` path uses `ReplayClient` over the per-concept
    store for an offline, free re-run (no live call).
  - `format_scorecard(score) -> str` + a thin `main(argv)` `run`/`replay` CLI
    (`--stage-json`, `--concept`, `--seed`, `--store-root`).
  - Imports `l2_repr` / `run_synthetic` / `stage_b` / `stage_runners` / `metadata`
    / `review` / `llm_client` / `taxonomy` / `utils.config` + stdlib. Like
    `spike.py`, it sits **above** the orchestrator and is never imported by any
    seam module.

- **F1-build-3 — tests `tests/synthetic/test_f1_pilot.py`** (all hermetic):
  - `run_pilot` over a tiny in-memory mixed-shape concept (LIST_plain + STR_formula
    + LIST_conditional, mirroring the `l2_repr` fixtures) + a canned/`ReplayClient`
    → `PilotScore` whose counts tally; **L2 fired** (≥1 paraphrase variant); the
    review queue is **100 %-coverage**; materialized items pass
    `metadata.validate_items`. Zero sockets.
  - `stage_b` hook: `materialize_variant`/`materialize_catalog_entry` with the
    default `pre_rerun` reproduce the pre-sprint output **byte-identically**
    (guards backward-compat); with `pre_rerun=formula_to_list` the rerun receives
    the list-restored shape.
  - `format_scorecard` columns; no-reverse-import (`run_synthetic`/`stage_b`/etc.
    do not import `f1_pilot`); no new dependency.
  - **No live `pytest` case** — the live run is the Sprint-28 CLI invocation.

- **Doc + housekeeping:** this file; `RESEARCH_LOG.md` Sprint 27 entry;
  `CLAUDE_SYNTHETIC.md` `f1_pilot.py` row + the `stage_b` hook note + history;
  `RESEARCH_PROTOCOL.md` §3.5/§5 (F1-build ✅, F1-run ⏳).

### Out of scope (explicit)

- **The live generation run + the manual review** — F1-run (Sprint 28); paid only
  in time (local + free), and the fluency/semantic judgement is César's.
- **Editing any seam module other than the minimal `stage_b` `pre_rerun` hook.**
  No change to `run_synthetic` / `slot_extractor` / `layer_*` / `mutator` /
  `composition` / `variant_*` / `metadata` / `review` / `l2_repr` / `llm_client`.
- **Multi-concept, variant budgets, Phase-F sampling policy** — F3.
- **A retrieval-safety *code* guard.** The safety semantics already live in the
  prompts (paraphrase: "no alteres cantidades/unidades/referente"; omission/reorder:
  "conserva TODAS las variables `$A`,`$B` intactas"); F1-run's manual review is
  where `llama3.1:8b`'s actual compliance is judged. A code-level compliance check
  is deferred unless that review shows the model disobeys.
- **Merging `synthetic` to `main`.** Permanently forbidden.

---

## Content requirements

1. A `pre_rerun` hook in `stage_b` (default identity) lets `formula_to_list` run
   between apply and the rerun **without changing existing behavior** (existing
   `test_stage_b` stays byte-identical green).
2. `f1_pilot.run_pilot` composes the **unedited** frozen stack + the two-mode
   `l2_repr` adapter over one concept across **all 12 + stacked** conditions,
   producing the recorded store, catalog, materialized items, a **100 %-coverage**
   review queue, and an automatable `PilotScore`.
3. The deterministic suite makes **zero network calls**; the live run is the
   Sprint-28 CLI. `replay=True` re-runs offline from the store.
4. `f1_pilot` is a consumer above the orchestrator — never imported by a seam
   module (asserted); no new third-party dependency.

## Acceptance

- `src/synthetic/f1_pilot.py` + `tests/synthetic/test_f1_pilot.py` exist; the only
  seam change is the backward-compatible `stage_b` `pre_rerun` hook (a `git diff`
  shows `run_synthetic`/`slot_extractor`/`layer_*`/`metadata`/`review`/`l2_repr`
  untouched).
- `run_pilot` (driven by a canned/`ReplayClient`) returns a `PilotScore` with a
  100 %-coverage queue, L2 fired, and items that validate — over a tiny in-memory
  concept, **no sockets**.
- `pytest tests -q` → the Sprint-26 baseline **794 passed, 2 skipped** still green
  **plus** the new hermetic `test_f1_pilot` (+ the `stage_b` hook tests) →
  **794+N passed, 2 skipped**, zero failures, zero network.
- Housekeeping docs updated; F1-build flipped ✅, F1-run annotated ⏳.

---

## Tasks

### Task 1 — `stage_b` pre-rerun hook (F1-build-1)
Add `pre_rerun: Callable[[dict], dict] = _identity` to `materialize_variant` and
`materialize_catalog_entry`; apply it to the mutated concept before
`run_stages_3_to_7`. Default identity. (Decision point: hook vs. driver-orchestrates
— recommend the hook; if rejected, the driver re-implements the materialize loop
and `stage_b` stays untouched.)

### Task 2 — `f1_pilot.py` driver (F1-build-2)
Implement `load_pilot_concept`, `PilotScore`, `run_pilot` (the 7-step composition
above), `default_conditions`, `format_scorecard`, and a thin `run`/`replay`
`main(argv)`. Consumer above the orchestrator; stdlib + existing `synthetic`
modules only.

### Task 3 — Hermetic tests (F1-build-3)
Per Scope F1-build-3: `run_pilot` over a tiny mixed-shape concept + canned/Replay
client (counts tally, L2 fired, 100 %-coverage queue, items validate, zero
sockets); the `stage_b` hook backward-compat + insertion tests; no-reverse-import;
no live `pytest` case.

### Task 4 — Housekeeping
`RESEARCH_LOG.md` Sprint 27 entry; `CLAUDE_SYNTHETIC.md` `f1_pilot.py` row + the
`stage_b` hook note + "After Sprint 27" history; `RESEARCH_PROTOCOL.md` §3.5/§5
F1-build ✅ / F1-run ⏳.

---

## Verification runbook

```powershell
$env:PYTHONPATH = "src"
pytest tests -q --basetemp="$env:TEMP\pt_s27"
# → 794 + N passed, 2 skipped, zero failures, zero network.

# Confirm the only seam touch is the stage_b hook:
git diff -- src/synthetic/run_synthetic.py src/synthetic/slot_extractor.py `
            src/synthetic/layer_l2.py src/synthetic/metadata.py `
            src/synthetic/review.py src/synthetic/l2_repr.py     # empty
git status --short   # new: f1_pilot.py, test_f1_pilot.py; modified: stage_b.py + docs
```

The **live** F1-run (Sprint 28) is NOT part of this suite:

```powershell
# (Sprint 28, live, local, free — Ollama serving llama3.1:8b)
python -m synthetic.f1_pilot run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept "OEB070$" --seed 7
```

---

## Risks / things most likely to surface here (which is the point)

- **`metadata` schema friction.** `metadata.join_intermediate` → `validate_items`
  may reject the materialized items if a required `SyntheticItem` field isn't
  populated by the pilot path. Better to hit this in a hermetic build than mid-run.
- **`review.sample_review_queue(coverage=1.0)`** must yield true 100 % coverage
  (`min(size, max(floor, ceil(1.0·size))) == size`); pin it in a test.
- **The `pre_rerun` ordering** must be *after* all rules apply and *before* the
  rerun, once per variant; the byte-identical-default test guards regressions.

---

## Design notes worth committing to memory

- **F1 splits build vs run, like everything before it.** Sprint 27 ships the
  runnable harness (hermetic); Sprint 28 runs it live and reviews. Build the
  contract; never fabricate the run.
- **One deliberate seam touch: a default-identity `pre_rerun` hook.** The two-mode
  L2 adapter forces a `formula_to_list` step between apply and rerun;
  `materialize_*` had no insertion point. A backward-compatible hook is smaller
  than duplicating the materialize loop.
- **The driver is `spike.py`'s sibling** — a consumer above the orchestrator,
  never imported by the seam, composing the frozen public surface + `l2_repr`.
- **Safety is already in the prompts.** No retrieval-safety code guard this sprint;
  the F1-run review judges whether `llama3.1:8b` honors it.

---

## References

- [`SPRINT_28.md`](SPRINT_28.md) — F1-run, which executes this harness live.
- [`SPRINT_26.md`](SPRINT_26.md) — the `l2_repr` adapter the driver brackets with.
- [`../../src/synthetic/spike.py`](../../src/synthetic/spike.py) — the
  consumer-above-the-orchestrator pattern this driver mirrors.
- [`../../src/synthetic/stage_b.py`](../../src/synthetic/stage_b.py) /
  [`run_synthetic.py`](../../src/synthetic/run_synthetic.py) /
  [`metadata.py`](../../src/synthetic/metadata.py) /
  [`review.py`](../../src/synthetic/review.py) — the stack the driver composes.
- [`../../CLAUDE.md`](../../CLAUDE.md) — never-merge-`synthetic`-to-`main`.

---

## Non-goals reminder

If you find yourself editing the seam beyond the one `stage_b` `pre_rerun` hook —
**stop**. The driver composes the frozen public surface.

If you find yourself making a live LLM call from a `pytest` case — **stop**. The
suite is hermetic (canned/`ReplayClient`); the live run is Sprint 28's CLI.

If you find yourself running the live pilot, picking review verdicts, or judging
Spanish fluency — **stop**. That is F1-run (Sprint 28), César's manual close-out.
