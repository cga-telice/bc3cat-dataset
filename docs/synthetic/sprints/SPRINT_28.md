# Sprint 28 — Phase F Task F1-run (single-concept pilot: live local generation + 100 % manual review)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 28                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | F1-run (see [`../RESEARCH_PROTOCOL.md §5 Phase F`](../RESEARCH_PROTOCOL.md)) — split **F1-run-generate** (runnable: local + free) / **F1-review** (manual close-out by César). |
| **Predecessor** | Sprint 27 — **F1 pilot harness** (`f1_pilot.py` + `stage_b` pre-rerun hook) (see [`SPRINT_27.md`](SPRINT_27.md)); Sprint 25 model decision (`llama3.1:8b`); Sprint 26 L2 adapter |
| **Successor**   | Sprint 29 — **F2** pilot retro (tune prompts / conditions / model from F1 findings) → F3 full generation → F4 validation (`QUALITY_REPORT.md`) → post-F3 `DATA_CARD.md` stats |

---

## Context

Everything is built and the harness is runnable: Sprint 25 chose the model
(**local `llama3.1:8b`** via Ollama), Sprint 26 fixed the silent L2 no-op
(`l2_repr`), and Sprint 27 shipped the pilot driver (`f1_pilot.run_pilot`) + its
hermetic tests. **No code is needed this sprint.** F1-run is the first *real*
generation pass: actually invoking the harness against the pinned pilot concept
with the live model, then reviewing what `llama3.1:8b` produced.

Because we deliberately skipped the pre-generation fluency spike (A3b-run was a
strategic commitment, not a measured comparison), **F1's 100 %-manual review is
the real Spanish-quality gate for `llama3.1:8b`.** This is the cheapest place — one
concept — to discover that the model, a prompt, or a condition is wrong before
paying the time to generate at 47k scale (F3).

### The split: F1-run-generate (runnable, local, free) vs F1-review (manual)

* **F1-run-generate — local, free, reproducible; Claude- or César-runnable.**
  Invoke `python -m synthetic.f1_pilot run` on `OEB070$` against Ollama-served
  `llama3.1:8b`. It produces durable artefacts (recorded LLM store, variant
  catalog, materialized items, the 100 %-coverage review queue) and prints the
  **mechanical scorecard** (variants generated/skipped, the C2/C3 malformed/schema
  split, `l2_targets`, materialized/reviewable items, queue size, coverage). This
  half is *mechanical*: it tells us the plumbing worked end-to-end on real data and
  how reliably the model emits valid JSON — but it does **not** judge the Spanish.
  `temperature 0.0` + the `RecordingClient` make it deterministic and replayable
  offline forever after the one live pass.
* **F1-review — manual, human judgement, out-of-suite; César's.** Read what the
  model wrote and judge: is it fluent, technically-correct construction Spanish?
  Did the modification preserve meaning where it should (synonym / paraphrase /
  expansion / compression) and change it where intended (omission / new_param)?
  Are placeholders and discriminative parameter values intact (retrieval safety)?
  Any hallucinated units, invented codes, broken `$VAR`/template? Verdicts go
  through `review.write_verdicts`; the output is an **F1 findings note** + the
  **`llama3.1:8b` verdict** that feeds F2.

**Claude runs F1-run-generate and captures the mechanical scorecard + a generation
report; César runs F1-review.** Build the runnable pilot, never fabricate the
review verdicts — the same discipline as A3a/A3b/B6.

### Prerequisites (satisfied)

- Ollama running at `http://localhost:11434`; **`llama3.1:8b` pulled and verified**
  live through `HttpLLMClient` (Sprint 25/26). `utils.config LLM_MODEL =
  "llama3.1:8b"` (exact tag).
- Pilot concept **pinned: `OEB070$`** ("HINCA TUBO DE POLIETILENO 110 MM", 144
  leaves, 4 axes incl. the numeric `N° TUBOS`). All 12 modification types fire
  (L2 via the Sprint-26 adapter: `$L`+`$N` → 9 L2 targets each; `$M` is malformed
  source — `embedded_quote` — left native, recorded, not L2-targetable).
- Harness: `synthetic.f1_pilot` (Sprint 27).

### Decisions to make up front

1. **Condition scope.** The harness `default_conditions()` runs **all 17**
   (12 single-type + 4 stacked + full_random_mix) **exhaustively** — on `OEB070$`
   the single-type conditions alone yield dozens of variants (one per enumerated
   target: ~24 L1 + 27 L2 + L3 + new_param), and each materializes up to 144
   leaves. **Recommendation:** run the full set (it is free), but expect a large
   item-level queue — see decision 2. *(Note: the protocol's wording "one variant
   per modification type" predates the exhaustive enumerator; running exhaustively
   is strictly more informative for a one-concept pilot. If a lighter first pass is
   wanted, pass `--conditions` limited to the 12 single-type conditions.)*
2. **Review depth.** A modification is defined at the concept level (e.g.
   "paraphrase `$L` under `%B=a`: Diurno→…"), so **one representative leaf per
   variant** is enough to judge that modification; the 100 %-coverage queue repeats
   each modification across the other axes' values. **Recommendation:** review at
   the **distinct-modification (per-variant) level**, spot-checking item-level
   rendering — far more tractable than reading every item, and it is the
   modification quality that matters. `review.sample_review_queue`'s `coverage`
   knob controls item volume if a sampled queue is preferred.
3. **Determinism / cost.** Seed pinned; `temperature 0.0`; one live pass recorded
   → all re-runs (`replay`) are offline and free. No reason to call the model twice
   unless a prompt/condition changes.

---

## Scope

### In scope

- **F1-run-generate (Claude- or César-runnable).** Run `f1_pilot run` on `OEB070$`
  with live `llama3.1:8b`; capture the artefacts + the mechanical scorecard.
  **Mechanical sanity checks** (code/observation, *not* fluency): the
  `assert_l2_targets_or_warn` guard did **not** warn (L2 fired); `l2_targets > 0`;
  the malformed/schema skip counts are low (a high malformed rate is itself a
  finding about 8B's JSON reliability); `coverage_fraction == 1.0` on reviewable
  items; `metadata.validate_items` passed (the harness asserts it). Prepend a short
  **generation report** (the mechanical numbers only) to `RESEARCH_LOG.md`.
- **F1-review (manual close-out by César).** *Not a Claude deliverable; the runbook
  the sprint hands off — see "Review protocol" below.*
- **Doc + housekeeping** (Claude): the generation report (RESEARCH_LOG Sprint 28
  entry — mechanical half landed, F1-review pending); `RESEARCH_PROTOCOL.md §5`
  F1-run annotated (generate ✅ / review ⏳).

### Out of scope (explicit)

- **F1-review itself** — reading the Spanish, judging fluency, writing verdicts and
  the model decision. Manual, César's.
- **Any code change.** The harness is frozen (Sprint 27); F1-run only *invokes* it.
  No new modules, no edits to the seam, no `f1_pilot` changes (if a real bug
  surfaces, that is a new bugfix sprint, not silent in-place patching).
- **F2–F4.** F1 unblocks F2 (tuning); it is not F2. No prompt/model re-tuning, no
  full generation (F3), no `QUALITY_REPORT.md` (F4).
- **The corpus / budgets / multi-concept.** One concept; budgets are F3.
- **Re-running the model-choice spike.** `spike.py` is the *contingency* F1-review
  may recommend (compare 8B vs `llama3.1:70b` vs a Spanish-tuned model on the
  recorded transcripts), not an F1 deliverable.
- **Merging `synthetic` to `main`.** Permanently forbidden.

---

## Tasks

### Task 1 — Run the live generation (F1-run-generate)
From repo root, with Ollama serving `llama3.1:8b`:

```powershell
$env:PYTHONPATH = "src"
python -m synthetic.f1_pilot run `
  --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" `
  --concept "OEB070$" --seed 7
```

Produces (under `data/synthetic/`): the recorded store `llm_cache/OEB070$/`, the
variant catalog `variants/OEB070$.json`, materialized items
`intermediate/OEB070$/*.json`, the review queue `review/OEB070$_review_queue.jsonl`,
and the scorecard on stdout. (A lighter first pass: append
`--conditions single_L2_paraphrase …` once the CLI grows the flag, or run the
default 17.)

### Task 2 — Mechanical sanity check + generation report (F1-run-generate)
Confirm: guard silent (L2 fired), `l2_targets > 0`, low malformed/schema rate,
`coverage_fraction == 1.0`, items validated. Prepend the scorecard numbers to
`RESEARCH_LOG.md` as the Sprint-28 generation report. **No fluency claims.**

### Task 3 (hand-off, not Claude) — F1-review
César executes the review protocol below: verdicts, findings note, model verdict.

### Task 4 — Housekeeping
`RESEARCH_PROTOCOL.md §5` F1-run-generate ✅ / F1-review ⏳; `CLAUDE_SYNTHETIC.md`
"After Sprint 28" history (generation ran; review pending). Status only.

---

## Review protocol (F1-review — César, out-of-suite)

1. **Open the queue:** `review.read_queue(Path("data/synthetic/review/OEB070$_review_queue.jsonl"))`.
   Review at the **distinct-modification level** (one representative per variant);
   the recorded transcripts under `llm_cache/OEB070$/` show the raw model output
   per prompt.
2. **Per modification type, judge:**
   - **synonym_label / paraphrase / expansion / compression** — meaning *preserved*?
     Fluent technical Spanish? **Discriminative content intact** (the param value /
     distinguishing tokens survive, so retrieval isn't degraded)? No altered
     quantities/units/physical referent (the prompt forbids it).
   - **num_to_text / unit_* / abbrev_/code_expansion** — correct, unambiguous
     rendering (e.g. `N° TUBOS` 1→"uno") that a retriever can still match.
   - **omission** — the targeted parameter mention is gone, **all other `$VAR`
     placeholders intact**, text still grammatical.
   - **reorder** — same parametric information, all placeholders intact, grammatical.
   - **new_param** — the added axis/value/template is semantically valid and does
     not collide with an existing axis (100 %-review mandated).
3. **Record verdicts** via `review.write_verdicts`; if ≥2 reviewers, compute
   `review.agreement` (percent + Cohen's κ; `axis_distinguishable` for new_param).
4. **Write the F1 findings note** (`docs/synthetic/F1_PILOT_FINDINGS.md` or a
   `RESEARCH_LOG.md` entry): per-condition accept/reject counts, the failure modes
   seen, the model's JSON reliability (from the scorecard's malformed rate), and
   the **verdict on `llama3.1:8b`** — good-enough-for-F3, or **escalate** (run
   `spike.py` to compare `llama3.1:70b` / a Spanish-tuned model on the recorded
   transcripts). This is the input to F2.

### What "good enough" means (César sets the thresholds)

A combination of: acceptance rate per type (e.g. is paraphrase usable?), JSON
reliability (the scorecard's malformed/schema skip rate), and retrieval-safety
(discriminative content preserved). If 8B falls short on fluency or reliability,
the escalation is one `spike.py` run away — the recorded transcripts replay free.

---

## Acceptance

- **F1-run-generate (this sprint, Claude):** the run completes against live
  `llama3.1:8b`; the artefacts exist; the scorecard is captured; the mechanical
  checks pass (guard silent, L2 fired, items validated); the generation report is
  in `RESEARCH_LOG.md`. The recorded store makes the run replayable.
- **F1-review (manual, César):** verdicts recorded + the F1 findings note + the
  `llama3.1:8b` verdict — explicitly *not* fabricated by Claude.
- `pytest tests -q` → **808 passed, 2 skipped**, unchanged (F1-run adds **no
  code**). The generated artefacts under `data/synthetic/` are derived data, not
  source.

---

## Risks / what to watch

- **8B JSON reliability.** A small local model may emit malformed JSON; the C2
  retry absorbs some, the rest land in the `malformed_skips` bucket. A high rate is
  a real finding (and an escalation trigger), not a failure of the harness.
- **Review volume.** Exhaustive conditions × 144 leaves → a large item-level queue;
  reviewing per-distinct-modification keeps it tractable (decision 2).
- **L2 value-paraphrase retrieval-safety.** Paraphrasing a value-var (e.g. Diurno)
  is allowed but must preserve the distinguishing meaning; the prompt instructs it,
  the review verifies it (the concern raised pre-sprint).
- **Embedded-quote vars.** `$M` on `OEB070$` is malformed source (`embedded_quote`)
  → left native, not L2-targetable. Expected; recorded; not a harness bug.

---

## Design notes worth committing to memory

- **F1-run is execute + review, no code.** Sprint 27 built the harness; this sprint
  runs it live and reviews. The mechanical scorecard is code/observation; the
  Spanish quality is the human read.
- **The skipped spike moved the quality gate into F1-review.** This review is the
  first real test of `llama3.1:8b`'s Spanish; `spike.py` is the one-run escalation.
- **`RecordingClient` makes the pilot reproducible and F2 free.** One live pass;
  every re-run and re-review replays offline.
- **Next is F2 (Sprint 29).** F1 findings (per-condition accept/reject + the model
  verdict + JSON reliability) drive F2's prompt/condition/model tuning.

---

## References

- [`SPRINT_27.md`](SPRINT_27.md) — the harness this sprint runs.
- [`../RESEARCH_PROTOCOL.md §5 Phase F`](../RESEARCH_PROTOCOL.md) — F1; §4 model row
  (`llama3.1:8b`); §6 conditions.
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — the A3b-run decision making F1 the gate.
- [`../../src/synthetic/f1_pilot.py`](../../src/synthetic/f1_pilot.py) /
  [`review.py`](../../src/synthetic/review.py) /
  [`spike.py`](../../src/synthetic/spike.py) — the harness, the review API, the
  escalation path.
- [`../../CLAUDE.md`](../../CLAUDE.md) — never-merge-`synthetic`-to-`main`.

---

## Non-goals reminder

If you find yourself editing `f1_pilot` or any seam module — **stop**. F1-run only
*invokes* the frozen harness; a real bug is a new bugfix sprint, not a silent patch.

If you find yourself scoring Spanish fluency in code or writing the review verdicts
— **stop**. The scorecard is mechanical; the fluency/semantic judgement is César's
F1-review.

If you find yourself generating other concepts, building `QUALITY_REPORT.md`, or
refreshing `DATA_CARD.md` — **stop**. That is F3/F4. F1 is one concept.

If you find yourself re-running the model-choice spike as an F1 deliverable —
**stop**. The model is committed; the spike is the contingency F1-review may
recommend.
