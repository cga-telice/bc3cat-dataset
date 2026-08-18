# Sprint 25 — Phase A Task A3b (live model-choice spike harness + recorded decision)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 25                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | A3b (see [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md)) — split A3b-build (this sprint, code) / A3b-run (this sprint, manual close-out by César) |
| **Predecessor** | Sprint 24 — A3a concrete `LLMClient` transport + record/replay harness (`llm_client.py`) (see [`SPRINT_24.md`](SPRINT_24.md)) |
| **Successor**   | Sprint 26 — **F1** single-concept pilot (replays the A3b recorded store; one variant per §6 condition; 100 % manual review) → **F2** pilot retro → **F3** full generation → **F4** validation (`QUALITY_REPORT.md`) → post-F3 `DATA_CARD.md` statistics refresh |

---

## Context

Sprint 24 shipped A3a: the concrete `HttpLLMClient` (OpenAI-compatible
`/chat/completions` over stdlib `urllib`), `ReplayClient`, and `RecordingClient`,
all behind the already-frozen `llm_proposer.LLMClient` Protocol. The transport
exists; what does **not** exist is the **answer to the one research question A3
was always about**: *which model do we generate BC3CAT-Syn with?*
[`RESEARCH_PROTOCOL.md §4`](../RESEARCH_PROTOCOL.md) still reads
`LLM proposer model = TBD`, and §5 A3b is the gate.

The whole Stage-A→Stage-B machinery is built and frozen:

* [`variant_proposer.propose_variant`](../../src/synthetic/variant_proposer.py)
  renders a per-type Spanish prompt, ships it through `llm_proposer.propose`, and
  validates the payload against the per-`ModificationType` schema — emitting a
  distinguishable `malformed_llm_response_after_retry:` (C2) or
  `schema_validation_failed:` (C3) skip on failure.
* [`run_synthetic.run_concept`](../../src/synthetic/run_synthetic.py) takes a
  `client: LLMClient` and a `stage_json`, plans one variant per §6 condition
  (`CONDITION_SPECS` covers all 12 single-type conditions + the stacked ones),
  proposes each, and writes a `VariantCatalogEntry` whose `variants` /
  `skipped` / `provenance` tuples are exactly the per-cell outcome record.
* [`llm_client`](../../src/synthetic/llm_client.py) (A3a) gives us a real
  `complete()` plus the `RecordingClient` that captures every transcript.

So the spike is now a *composition*, not new proposing logic: wrap each candidate
`HttpLLMClient` in a `RecordingClient`, call `run_concept` over **one pilot
concept group across the 12 single-type conditions**, and read the per-candidate
scorecard straight off the returned catalog entry. That composition — plus the
manual judgement it feeds — is A3b.

### Why A3b now

A3b is the **last open Phase-A item and the gate on all of Phase F**. F1 (the
single-concept pilot) replays a recorded store; that store does not exist until
the spike runs. Picking the model is also the single highest-leverage research
decision left: §4 calls Spanish technical-writing quality "the gating factor",
and every variant in the eventual corpus is shaped by it. With A3a's transport in
hand, the spike is finally runnable.

### The honest split: A3b-build (this sprint, code) vs A3b-run (this sprint, manual)

`RESEARCH_PROTOCOL.md §5 A3b` bundles two things with opposite testability — the
same fault line Sprint 24 drew through A3, and Sprint 23 through G3:

* **A3b-build — the spike harness — is code with hermetic tests.** A thin
  module that drives `run_concept` over one pilot concept for each candidate
  config, wraps every client in a `RecordingClient`, and tallies an
  **automatable scorecard** (JSON-parse success, schema-pass rate, per-type skip
  counts split by reason-prefix, latency, response length) off the catalog
  entry. Every test is network-free: a `ReplayClient` over canned per-prompt
  transcripts drives the whole harness, the scorecard is asserted, and **no test
  opens a socket.** This is the Sprint 25 *code* deliverable.
* **A3b-run — the live ≥2-model comparison and the §4 decision — is manual,
  paid, and out-of-suite.** It needs real API keys, network, and cost; it
  produces a *judgement* — Spanish-technical fluency read off the recorded
  transcripts, weighed against the harness's JSON-reliability/latency/cost
  numbers — that **cannot** live in `pytest`. César runs `python -m
  synthetic.spike` against each candidate, eyeballs the recorded Spanish,
  decides, records the decision in `RESEARCH_LOG.md`, and **flips §4's
  `LLM proposer model` row from `TBD` to the chosen model.**

This is the same discipline as Sprints 23–24: **build the runnable contract,
never fabricate the measured result.** Sprint 25-as-executed-by-Claude ships the
harness + hermetic tests + the run-it runbook; the *automatable* metrics are
real code, the *fluency judgement and the model pick* are César's manual
close-out. The harness's `RecordingClient` makes that close-out reproducible: run
the spike once, replay every candidate's transcripts forever, and F1 inherits the
chosen model's store offline and free.

> **Scope note (one-task-per-sprint cadence).** Sprint 24's successor line listed
> `A3b → F1 → F2 → …` as the *remaining roadmap*, not a Sprint-25 bundle. A3b is a
> substantial sprint on its own — the harness plus the gating §4 decision — so
> **F1 is Sprint 26**, consistent with the project's tight sprint boundaries
> (A2=S1 … G3+G4=S23, A3a=S24, A3b=S25). If a bundled A3b+F1 sprint is wanted
> instead, that is a deliberate redirection of this draft.

### The load-bearing design decisions (decide up front)

1. **The harness composes `run_concept`; it does not reimplement proposing.**
   `src/synthetic/spike.py` wraps each candidate `HttpLLMClient` in a
   `RecordingClient` and calls the **unedited** `run_synthetic.run_concept` over
   one pilot concept across the 12 single-type conditions. The scorecard is
   tallied from the returned `VariantCatalogEntry` (`len(variants)`,
   `skipped` partitioned on the `malformed_llm_response_after_retry:` vs
   `schema_validation_failed:` reason-prefix). No new prompt rendering, no new
   parsing, no new schema logic — those are the frozen C2/C3 seam.

2. **The harness is a *consumer* of the orchestrator, never imported by it.**
   `spike.py` may import `run_synthetic` / `llm_client` / `loaders` / stdlib;
   nothing in the Stage-A/Stage-B seam imports `spike`. The Sprint-24 "A3 slots
   in *under* the Protocol" invariant is preserved — A3b sits *above* the
   orchestrator, calling in.

3. **Automatable metrics are code; Spanish fluency is human.** The harness scores
   what code can verify — JSON-parse success, schema-pass rate, per-type skip
   reasons, latency, response length. It **does not** score Spanish-technical
   fluency; it surfaces the recorded transcripts (and the rendered synthetic
   `resumen`/`texto`) for César to read. Honest split: measure the measurable,
   defer the judgement.

4. **`RecordingClient` is mandatory — the spike must be reproducible.** Each
   candidate runs through `RecordingClient(HttpLLMClient(cfg), store_dir)` into a
   **per-candidate** store under `config.LLM_CACHE_DIR` (e.g.
   `llm_cache/<candidate_slug>/`). The chosen candidate's store becomes F1's
   replay source — generation is reproducible offline and free thereafter.

5. **Hermetic tests drive the harness with `ReplayClient` + canned transcripts.**
   `tests/synthetic/test_spike.py` builds a tiny in-memory `stage_json` fixture
   (mirroring `test_run_synthetic.py`), seeds a `ReplayClient` with canned
   per-prompt responses (well-formed for some types, malformed/schema-violating
   for others), runs the harness, and asserts the scorecard tallies (counts,
   skip-reason split, that a recording store round-trips). **Zero sockets.** The
   one live execution is the manual CLI run, not a `pytest` case.

6. **`§4` stays `TBD` until César runs A3b-run.** Sprint 25-by-Claude ships the
   harness and leaves §4 `LLM proposer model = TBD` with a note that the *harness
   exists and the run is the gate*. The TBD→model flip and the `RESEARCH_LOG.md`
   decision prose are A3b-run — César's manual close-out, exactly as A3a left
   A3b. **Claude does not pick the model, run the paid spike, or flip §4.**

7. **No secrets, no new dependency.** A3a's rules carry over verbatim: the key is
   read from the `config`-named env var at request time, never written to a
   store/log/exception; the harness is stdlib + existing `synthetic` modules
   only — no `requests`/`httpx`/vendor SDK.

8. **Pick the pilot concept deterministically and reuse it for F1.** One moderate
   OEB concept group (per F1's 50–200-item guidance) named in the runbook, so the
   recorded store seeds F1 directly. The default is config/CLI-overridable; the
   harness does not hard-code a concept.

---

## Scope

### In scope

- **A3b-build-1 — new module `src/synthetic/spike.py`.** The model-choice spike
  harness:
  - `CandidateSpec` (dataclass) — a human-readable `name`/slug + an `LLMConfig`
    (so ≥2 candidates differ by `base_url` + `model` alone, per A3a decision 2).
  - `CandidateScore` (dataclass) — the automatable per-candidate scorecard:
    proposed/skipped counts, per-`ModificationType` outcome, skip counts split by
    `malformed_llm_response_after_retry:` vs `schema_validation_failed:`,
    total/mean latency, mean response length. **No fluency field** (decision 3).
  - `run_candidate(stage_json, concept_key, candidate, *, store_root, seed,
    conditions=<12 single-type>) -> CandidateScore` — wraps the candidate's
    `HttpLLMClient` in a `RecordingClient` under
    `store_root / candidate.name`, calls `run_concept`, tallies the score off
    the returned `VariantCatalogEntry`. Latency measured around `complete` via an
    injectable clock (default `time.perf_counter`) so tests stay deterministic.
  - `run_spike(stage_json, concept_key, candidates, *, store_root, seed) ->
    list[CandidateScore]` — runs each candidate, returns the scorecards.
  - `format_scorecard(scores) -> str` — a plain-text/Markdown comparison table
    for the runbook and `RESEARCH_LOG.md` (the automatable columns only).
  - A thin `main(argv)` CLI (mirroring `packaging`/`loaders`/`llm_client`) — a
    `run` subcommand reading the pilot concept's stage JSON + candidate configs,
    executing the spike (live), and printing the scorecard; a `replay` flag to
    re-tally from an existing store without a live call.
  - Imports `run_synthetic` / `llm_client` / `taxonomy` / `utils.config` +
    stdlib only; **never imported by** any seam module (decision 2).

- **A3b-build-2 — tests `tests/synthetic/test_spike.py`.** All hermetic:
  - `run_candidate` over a tiny in-memory `stage_json` + a `ReplayClient` of
    canned transcripts → a `CandidateScore` whose proposed/skipped counts and
    per-type outcomes match the canned mix; the recording store round-trips
    (a fresh `ReplayClient` reads it).
  - Skip-reason split: a malformed canned response lands in the
    `malformed_llm_response_after_retry:` bucket, a schema-violating one in the
    `schema_validation_failed:` bucket (proving the harness reads the C2/C3 seam,
    not its own logic).
  - `run_spike` over ≥2 candidates → one `CandidateScore` each, written to
    distinct per-candidate stores.
  - `format_scorecard` emits a table with a row per candidate and the automatable
    columns; **no fluency column** (guards decision 3).
  - Latency is deterministic under an injected fake clock (no wall-clock flake).
  - No-secret-leak: a candidate key value appears in neither the recording store
    nor the scorecard output (carried over from A3a's assertion).
  - **No live `pytest` case** — the live run is the manual CLI invocation
    (decision 5); the suite opens zero sockets.

- **A3b-run — manual close-out by César (out-of-suite, paid).** *Not a Claude
  deliverable; specified here as the runbook the sprint hands off:*
  1. Choose ≥2 candidates (per §10/§4: a GPT-4-class API for the fluency
     ceiling, a local Llama 3.1 for reproducibility, optionally a Spanish-tuned
     model). Set each candidate's `base_url`/`model`/key env var.
  2. Run `python -m synthetic.spike run …` against the named pilot concept;
     inspect the scorecard (JSON reliability, latency, cost) **and** read the
     recorded Spanish transcripts for technical fluency.
  3. Decide. Record the decision + the scorecard table + the fluency rationale in
     a new `RESEARCH_LOG.md` entry, and **flip `RESEARCH_PROTOCOL.md §4`
     `LLM proposer model` from `TBD` to the chosen model** (with the chosen
     `base_url`/`model` + the recorded-store path F1 will replay).

- **Doc + housekeeping** (the Claude-executed part):
  - Add a `spike.py` row (✅, A3b-build) to the file map / "New Files in This
    Branch" in [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); record the
    composes-`run_concept` / consumer-not-imported / automatable-vs-fluency /
    mandatory-`RecordingClient` / hermetic-tests / §4-stays-TBD-until-run /
    no-secrets-no-dep decisions and the A3b-build-vs-A3b-run split. Prepend an
    "After Sprint 25" Sprint History entry.
  - Sprint 25 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (the harness
    landed; the model decision is the pending manual close-out).
  - In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md): §5 A3b — annotate
    **A3b-build ✅ (spike harness `spike.py`)**, **A3b-run ⏳ (live spike +
    decision, pending César)**; §3.5 — add/annotate a "Model-choice spike
    harness" row ✅; §4 `LLM proposer model` row **stays `TBD`** with a note that
    the harness now exists and the run (A3b-run) is the remaining gate.
    Status/annotation only — no design rewrite, no fabricated model pick.

### Out of scope (explicit)

- **A3b-run itself — picking the model, paying for the calls, flipping §4.**
  Manual, paid, out-of-suite (the A3b-build/A3b-run split). César's close-out.
- **F1–F4 (pilot, retro, full generation, validation).** A3b unblocks F1; it is
  not F1. No real corpus is generated, no `QUALITY_REPORT.md`. F1 is Sprint 26.
- **Editing the seam.** No changes to `llm_proposer.py`, `variant_proposer.py`,
  `run_synthetic.py`, `llm_client.py`, `prompts/`, `slot_extractor.py`,
  `rule_emitter.py`, `composition.py`, `variant_catalog.py`, the `layer_*`
  mutators, `mutator.py`, `stage_runners.py`, `stage_b.py`, `metadata.py`,
  `review.py`, `packaging.py`, `loaders.py`. A3b sits *above* the orchestrator
  and calls in.
- **A second provider client / multi-provider abstraction.** A3a's
  OpenAI-compatible `HttpLLMClient` covers the API and local-Llama candidates by
  config alone; a native Anthropic client is added only if A3b-run picks a model
  that needs it (A3a decision 2).
- **Any live network call in the deterministic suite.** The `ReplayClient` and
  canned transcripts keep `pytest` hermetic; the live run is the manual CLI.
- **Scoring or ranking Spanish fluency in code.** The harness surfaces
  transcripts; the fluency judgement is human (decision 3).
- **Variant budgets / Phase-F sampling policy.** The spike runs one variant per
  single-type condition for one concept; budgets are F2/F3.
- **Merging `synthetic` to `main`.** Permanently forbidden
  ([`CLAUDE.md`](../../CLAUDE.md)).

---

## Content requirements

1. **`src/synthetic/spike.py` exists and runs a ≥2-candidate, 12-type,
   one-concept spike by composing the unedited `run_concept`**, wrapping each
   candidate in a `RecordingClient`, and returning a per-candidate
   `CandidateScore`.
2. **No new third-party dependency**; the harness imports `run_synthetic` /
   `llm_client` / `taxonomy` / `utils.config` + stdlib only, and is **never
   imported by** any seam module (a test asserts the no-reverse-import).
3. **The scorecard is automatable-only** (parse/schema/skip/latency/length); it
   carries **no fluency field** — fluency is the human read of the recorded
   transcripts (decision 3).
4. **The deterministic suite makes zero network calls**: every test drives the
   harness via `ReplayClient` over canned transcripts; the live run is the manual
   CLI invocation, not a `pytest` case.
5. **No secret leaks** (A3a carry-over): a candidate key value never enters the
   recording store, the scorecard output, a log, or an exception.
6. **`§4` is left `TBD`** with a "harness exists; A3b-run is the gate" note — the
   model pick and the §4 flip are César's manual close-out, never fabricated.

## Acceptance

- `src/synthetic/spike.py` and `tests/synthetic/test_spike.py` exist; **no
  `src/synthetic/*.py` other than `spike.py` is added or modified**, and no seam
  file changes (a `git diff` shows `llm_proposer`/`variant_proposer`/
  `run_synthetic`/`llm_client` untouched).
- `run_candidate` / `run_spike` compose `run_concept`, tally a `CandidateScore`
  off the catalog entry, write a per-candidate `RecordingClient` store a fresh
  `ReplayClient` can read, and split skips on the C2/C3 reason-prefix.
- `format_scorecard` emits a per-candidate comparison table with the automatable
  columns and **no fluency column**.
- No candidate key value appears in any store or scorecard string (asserted).
- `pytest tests -q` makes **no network call** and reports the Sprint 24 baseline
  **749 passed, 2 skipped** still green, **plus** the new hermetic `test_spike`
  tests all passing (→ **749+N passed, 2 skipped** — the skip count is unchanged;
  the spike's live path is the manual CLI, not a new `pytest` gate). Zero
  failures in any tree.
- Housekeeping: `CLAUDE_SYNTHETIC.md` gains the `spike.py` ✅ row + decisions +
  "After Sprint 25" history entry; `RESEARCH_LOG.md` Sprint 25 entry prepended;
  `RESEARCH_PROTOCOL.md` §3.5/§5 A3b-build flipped ✅, A3b-run annotated pending,
  §4 model row left `TBD` with the harness-now-exists note.

---

## Tasks

### Task 1 — `src/synthetic/spike.py` (A3b-build-1)
Implement `CandidateSpec`, `CandidateScore`, `run_candidate` (wraps
`RecordingClient(HttpLLMClient(cfg))`, calls the unedited `run_concept`, tallies
the automatable scorecard off the `VariantCatalogEntry`, injectable clock for
latency), `run_spike`, `format_scorecard`, and a thin `main(argv)` `run`/`replay`
CLI. Imports `run_synthetic`/`llm_client`/`taxonomy`/`utils.config` + stdlib
only; not imported by any seam module.

### Task 2 — `tests/synthetic/test_spike.py` (A3b-build-2)
Write the hermetic tier per Scope §A3b-build-2 (scorecard tallies over a tiny
`stage_json` + `ReplayClient` of canned transcripts; C2/C3 skip-reason split;
≥2-candidate `run_spike` with distinct per-candidate stores; `format_scorecard`
columns + no-fluency guard; deterministic latency via injected clock; recording
round-trip; no-secret-leak; no-reverse-import assertion). No live `pytest` case.

### Task 3 — Housekeeping
1. Prepend a Sprint 25 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the A3b-build-vs-A3b-run split, the
   composes-`run_concept` / consumer-not-imported / automatable-vs-fluency /
   mandatory-`RecordingClient` / hermetic-tests / §4-stays-TBD / no-secrets-no-dep
   decisions, the suite math (749 + new hermetic passing, 2 skipped unchanged),
   and the next step (César runs A3b-run, then Sprint 26 — F1).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): add the `spike.py` ✅
   file-map row; record the decisions; prepend the "After Sprint 25" history
   entry.
3. In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md): §3.5 add/flip the
   model-choice-spike-harness row ✅ (A3b-build); §5 annotate A3b-build ✅ /
   A3b-run ⏳; §4 leave the model row `TBD` with the "harness exists; the run
   (A3b-run) is the gate" note. Status only.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
# Default (hermetic) run — must make NO network call:
pytest tests -q --basetemp="$env:TEMP\pt_s25"
```

Expected: the Sprint 24 baseline **749 passed, 2 skipped** still green, the new
hermetic `test_spike` tests all passing → **749+N passed, 2 skipped**, zero
failures, **zero network calls**.

```powershell
# Confirm the seam is untouched (only spike.py added):
git status --short
git diff -- src/synthetic/llm_proposer.py src/synthetic/variant_proposer.py `
            src/synthetic/run_synthetic.py src/synthetic/llm_client.py   # empty
```

**A3b-run (manual, paid — César, NOT part of the deterministic suite):**

```powershell
# Two candidates differing by base_url + model alone (A3a decision 2):
$env:BC3CAT_LLM_API_KEY = "<api-key>"        # never committed
python -m synthetic.spike run `
  --stage-json "<pilot concept stage5 JSON>" --concept "<OEB pilot concept_key>" `
  --candidate "gpt4api:https://api.openai.com/v1:gpt-4o" `
  --candidate "llama-local:http://localhost:11434/v1:llama3.1"
# Inspect the scorecard AND read the recorded Spanish transcripts under
# data/synthetic/llm_cache/<candidate>/, then decide, record in RESEARCH_LOG.md,
# and flip RESEARCH_PROTOCOL.md §4 LLM proposer model from TBD to the choice.
```

End-of-sprint expected `git status --short` (Claude-executed subset):

```
new file:   src/synthetic/spike.py
new file:   tests/synthetic/test_spike.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_25.md (this file)
```

No edits to the Stage-A/Stage-B seam (`llm_proposer` / `variant_proposer` /
`run_synthetic` / `llm_client` / `prompts` / `slot_extractor` / `rule_emitter` /
`composition` / `variant_catalog` / `layer_*` / `mutator` / `stage_runners` /
`stage_b`) nor to `metadata` / `review` / `packaging` / `loaders`. No new
dependency. No secret committed. §4 model row not flipped by Claude.

---

## Design notes worth committing to memory

- **A3b splits like A3a did: build the harness (code, hermetic) vs. run the spike
  (manual, paid, prose).** Sprint 25 ships A3b-build — the `spike.py` harness that
  composes `run_concept` and produces an automatable scorecard — and leaves
  A3b-run (the live ≥2-model fluency read and the §4 model flip) to César's
  manual close-out. Build the runnable contract; never fabricate the measured
  result.
- **The spike is a composition, not new logic.** It wraps each candidate in a
  `RecordingClient` and calls the unedited `run_concept`; the scorecard is tallied
  off the `VariantCatalogEntry`. The harness sits *above* the orchestrator and is
  never imported by it.
- **Code measures the measurable; humans judge fluency.** Parse/schema/skip/
  latency/length are scored automatically; Spanish technical fluency is read off
  the recorded transcripts by César.
- **`RecordingClient` is what makes the decision reproducible and F1 free.** Run
  the spike once; the chosen model's store replays offline forever, and F1
  inherits it.
- **§4 stays `TBD` until the run.** Sprint 25-by-Claude ships the harness; the
  model pick and the §4 flip are the manual gate — exactly as A3a deferred A3b.
- **Next is A3b-run then F1 (Sprint 26).** With the model chosen and its store
  recorded, F1 drives the single-concept pilot offline.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md) — A3b (this
  sprint, split A3b-build/A3b-run); §4 design table (`LLM proposer model` = TBD);
  §6 generation conditions (the 12 single-type conditions the spike runs); §10
  candidate models for the spike.
- [`SPRINT_24.md`](SPRINT_24.md) — the predecessor (A3a transport + record/replay)
  and the build-vs-measure split this sprint mirrors.
- [`../../src/synthetic/llm_client.py`](../../src/synthetic/llm_client.py) —
  `HttpLLMClient` / `ReplayClient` / `RecordingClient` (A3a) the harness composes.
- [`../../src/synthetic/run_synthetic.py`](../../src/synthetic/run_synthetic.py) —
  `run_concept` / `CONDITION_SPECS` the harness drives (unedited).
- [`../../src/synthetic/variant_proposer.py`](../../src/synthetic/variant_proposer.py)
  — the C3 schema validation whose `malformed_…` / `schema_validation_failed:`
  skip-reason prefixes the scorecard partitions on.
- [`../../CLAUDE.md`](../../CLAUDE.md) — the never-merge-`synthetic`-to-`main`
  invariant.

---

## Non-goals reminder

If you find yourself editing `llm_proposer.py`, `variant_proposer.py`,
`run_synthetic.py`, or `llm_client.py` — **stop**. A3b composes the orchestrator
in a *new* module (`spike.py`); the seam is frozen. The harness calls `run_concept`;
it does not re-implement proposing, parsing, or schema validation.

If you find yourself scoring Spanish fluency in code, or adding a `fluency` column
to the scorecard — **stop**. The harness measures the automatable
(parse/schema/skip/latency/length); fluency is the human read of the recorded
transcripts.

If you find yourself running the live spike, picking a model, paying for calls, or
flipping the §4 `LLM proposer model` row from `TBD` — **stop**. That is A3b-run,
César's manual close-out. Sprint 25 *enables* it via the harness and
`RecordingClient`; it does not run it.

If you find yourself making a real network call from a `pytest` case — **stop**.
The deterministic suite is hermetic (driven by `ReplayClient` over canned
transcripts); the live run is the manual `python -m synthetic.spike` invocation.

If you find yourself adding `requests`, `httpx`, `openai`, or `anthropic`, or
making the orchestrator import `spike` — **stop**. The harness is stdlib + the
existing `synthetic` modules, and it is a *consumer* of the orchestrator, never
imported by it.

If you find yourself generating a real corpus, calling `run_catalog` for output,
or writing `QUALITY_REPORT.md` — **stop**. That is Phase F (F1 = Sprint 26). A3b
chooses the model that *unblocks* the pilot; it does not run it.
