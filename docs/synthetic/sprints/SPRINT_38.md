# Sprint 38 — Phase F Task F3-prep-2 (menu builder: live phi4 run + review parser + manual review)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 38                                                                                          |
| **Date**        | 2026-07-09 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | F3-prep-2, split **F3-prep-2-code** (Claude: driver CLI + review parser, hermetic), **F3-prep-2-generate** (Claude, live: point the driver at phi4 → produce the menu artefacts on disk), **F3-prep-2-review** (César, manual: tick approvals in the Markdown files). |
| **Predecessor** | Sprint 37 — **F3-prep-1** menu builder (`target_scanner.py` + `menu_proposer.py` + `menu_artefacts.py`) (see [`SPRINT_37.md`](SPRINT_37.md)); Sprint 30 model decision (`phi4:latest`). |
| **Successor**   | Sprint 39 — **F3-prep-3** (variant budgets YAML + deterministic sampler + chapter driver) → Sprint 40 F3-run → F4 validation → post-F3 `DATA_CARD.md` stats. |

---

## Context

Everything the menu-first Stage-A flow needs to *propose and write* is built and green (Sprint 37, 990 passed, 2 skipped). What is missing is the runnable driver that composes those modules against a live LLM client, the reader that translates the reviewer's Markdown ticks back into structured verdicts, and — critically — the manual review pass itself.

This is the **first real quality gate** for the whole menu-first pivot. If phi4 emits menus with the wrong shape (list-of-single-dicts instead of list-of-N), if the multi-candidate wrapper doesn't push the model hard enough, if the review artefact turns out to be tedious in practice, or if entire rewrite types produce garbage across the board, we discover it here — on one chapter subset, with recorded transcripts, before Sprint 40's chapter-driver spends hours of local GPU time on the full catalog.

### The split: code (F3-prep-2-code) → live (generate) → manual (review) → parser (Claude, post-review)

* **F3-prep-2-code (Claude, hermetic).** Two new modules, both above the frozen seam. `menu_runner.py` is the CLI driver — a consumer of `target_scanner` + `menu_proposer` + `menu_artefacts` + `llm_client` that mirrors `spike.py` / `f1_pilot.py`. `menu_review_parser.py` reads the ticked Markdown and emits structured `MenuVerdict` records. Both have hermetic tests (canned client / golden Markdown fixture). No live LLM call from `pytest`.
* **F3-prep-2-generate (Claude, live).** Serve `phi4:latest` on Ollama; run `python -m synthetic.menu_runner run --concept-filter OEB --n 10 --seed 7`. Produces the recorded transcript store `data/synthetic/llm_cache/menu_OEB/`, machine JSONL under `data/synthetic/menus/`, and human Markdown under `docs/synthetic/menus/`. Prints a mechanical scorecard (total unique targets, LLM calls, generated / skipped per rewrite type, mean latency, mean surviving candidates per target). This half is *mechanical* — plumbing worked, phi4's JSON reliability at list-shape N=10 is measured — but it does not judge Spanish quality.
* **F3-prep-2-review (César, manual, out-of-suite).** Read the 13 Markdown files. Tick candidates you accept. Save. This is the Spanish-quality gate for the whole benchmark. **Claude does not produce verdicts.**
* **F3-prep-2-parse (Claude, post-review).** Run `python -m synthetic.menu_review_parser parse` to translate the ticked Markdown into `data/synthetic/menus/verdicts/{mtype}.jsonl` — one line per unique target with per-candidate `approved: true/false`. Print a coverage summary (per rewrite type: total targets / targets with ≥1 approval / total approvals). This closes F3-prep-2 and hands F3-prep-3's sampler a clean approved-menu contract.

### Why a separate `menu_runner.py` and not a `main` in `menu_proposer.py`

`menu_proposer` is a pure library (used by tests, could be used programmatically). Adding a `main` would require it to import `menu_artefacts` and `llm_client`, which would (a) reverse the current one-way import from `menu_artefacts` → `menu_proposer` (creating a cycle) and (b) blur the library-vs-driver boundary. `menu_runner.py` mirrors `f1_pilot.py`'s consumer-above-orchestrator shape: one module, one `run` / `replay` CLI, composes the frozen public surfaces.

### Review contract (fixed by this sprint)

Every candidate lives on a Markdown line of the form:

```
- [ ] 1. Turno diurno
```

The reviewer flips `[ ]` to `[x]` to **approve**. Everything else — untouched `[ ]`, deleted line, comment above — is **reject**. Rationale: unambiguous, GitHub-native (`- [x]` renders as a filled checkbox), VS Code toggles on click, `grep '\[x\]'` gives an exact count. A per-file summary line at the top *"N of M candidates approved"* is added by the parser after review, but is not part of the input contract.

**No third state.** Not-yet-reviewed is indistinguishable from rejected on the parser side. To flag partial reviews the parser's coverage summary highlights any rewrite type where the approval count is exactly zero (the "I never opened this file" signal). If a partial-review workflow becomes necessary later, we add a `- [~]` skip marker — but only when it actually happens, not preemptively.

### Prerequisites

- Ollama running at `http://localhost:11434`; `phi4:latest` pulled and live through `HttpLLMClient` (Sprint 25/30). `utils.config.LLM_MODEL` unchanged; the runner overrides via `LLMConfig.from_env` if the user prefers env-var override, or `--model` argument.
- Menu builder trio (Sprint 37) frozen and green.
- OBRA CIVIL stage-2 JSON at `data/intermediate/OBRA CIVIL/OBRA CIVIL.json` (committed).

### Decisions to make up front

1. **Concept scope.** OEB subset (25 concepts) — same as the pilot; produces ~562 unique targets and ~5 600 candidate lines at `n=10`; ~2–3 h of live generation, ~7–9 h of manual review. **Recommendation:** start with OEB. Full OBRA CIVIL (451 concepts) is F3-run's scope.
2. **N per target.** Committed to 10 (2026-07-08).
3. **Determinism.** Seed 7; `temperature 0.0`; `RecordingClient` wraps `HttpLLMClient` so every subsequent invocation is offline and free — matches Sprint 27–28's discipline.

---

## Scope

### In scope

- **F3-prep-2-code-A — `src/synthetic/menu_runner.py`.** CLI driver above the orchestrator. Public surface: `MenuRun` (dataclass — the automatable scorecard), `run_menu(stage_json, *, concept_filter, n, client, out_dir_machine, out_dir_review, chapter_label) -> MenuRun`, a thin `main(argv)` with `run` / `replay` subcommands. Default client: `RecordingClient(HttpLLMClient(LLMConfig.from_env()))` with a per-concept-set cache path under `SYNTHETIC_DATA_ROOT / "llm_cache" / f"menu_{chapter_label}"`; `replay` uses `ReplayClient` over the same store (no live call). Composition: `target_scanner.scan_chapter` → loop `ModificationType`: `menu_proposer.propose_type(..., n=n)` → aggregate → `menu_artefacts.write_menu(...)`. Imports `target_scanner`/`menu_proposer`/`menu_artefacts`/`llm_client`/`taxonomy`/`utils.config` + stdlib only. Never imported by any seam module (asserted).

- **F3-prep-2-code-B — `src/synthetic/menu_review_parser.py`.** Reads the ticked Markdown files under `docs/synthetic/menus/` and emits verdict JSONL. Public surface: `MenuVerdict` (frozen dataclass with `dedup_key`, `canonical`, `candidates: tuple[CandidateVerdict, ...]`, `mtype`), `CandidateVerdict` (`payload`, `approved: bool`), `parse_review_file(md_path, jsonl_path) -> tuple[MenuVerdict, ...]` (joins Markdown ticks against the machine JSONL by target order — the JSONL is the schema authority; the Markdown is the human input), `write_verdicts(verdicts, out_path)` (atomic JSONL), `parse_all(machine_dir, review_dir, out_dir) -> ParseReport`, thin `main(argv)` with a `parse` subcommand. Fail-loud on target-count mismatch between JSONL and Markdown (the human deleted a heading — a real error, not a review verdict). Imports `menu_proposer` (for `CandidateProposal` shape reference) + `taxonomy` + stdlib only. **Reads Markdown line-by-line with a fixed regex — no Markdown-parser dependency.**

- **F3-prep-2-code-C — tests `tests/synthetic/test_menu_runner.py` + `test_menu_review_parser.py`** (all hermetic):
  - `run_menu` against a canned client → `MenuRun` scorecard with expected counts on the tiny fixture; the two artefact files exist and validate; `replay=True` re-runs offline against the recorded store with zero live calls.
  - `menu_review_parser.parse_review_file` against a golden Markdown fixture (some checkboxes ticked, some not) + its matching golden JSONL → the expected `MenuVerdict` tuple (per-candidate `approved` flags match).
  - Fail-loud paths: deleted heading (target count mismatch); tick on a line the JSONL doesn't know about (extra checkbox — reject as `parse_error`).
  - Boundary: neither module is imported by any seam module (AST-based check same shape as Sprint 37's `TestBoundaries`).
  - Zero sockets. Zero new third-party dependency (no `markdown` / `mistune` / etc.).

- **F3-prep-2-generate (Claude, live).** Once code is green, invoke `python -m synthetic.menu_runner run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7 --chapter-label OEB`. Produces:
  - `data/synthetic/llm_cache/menu_OEB/` — recorded transcript store (content-addressed).
  - `data/synthetic/menus/{mtype}.jsonl` — 13 machine-readable files.
  - `docs/synthetic/menus/{mtype}.md` — 13 human-review files.
  - Stdout scorecard captured into `RESEARCH_LOG.md` Sprint 38 generation report (mechanical only — no fluency claims).

- **F3-prep-2-review (César, out-of-suite).** Read the 13 Markdown files. Flip `[ ]` → `[x]` on candidates you accept. Save. **Claude does not do this step and does not fabricate verdicts.**

- **F3-prep-2-parse (Claude, post-review).** `python -m synthetic.menu_review_parser parse --machine-dir data/synthetic/menus --review-dir docs/synthetic/menus --out-dir data/synthetic/menus/verdicts`. Writes 13 verdict JSONL files under `data/synthetic/menus/verdicts/` + prints a coverage summary. Records the summary in `RESEARCH_LOG.md` alongside the generation report.

- **Doc + housekeeping** (Claude, after each landmark): sprint-plan file (this); `RESEARCH_LOG.md` entries at code-landed / generation-ran / review-closed; `CLAUDE_SYNTHETIC.md` file-map rows (`menu_runner.py` ✅, `menu_review_parser.py` ✅, `data/synthetic/menus/` ✅); `RESEARCH_PROTOCOL.md §5` F3-prep-2 status flip. Commit the generated Markdown menus into the branch (diffable review history).

### Out of scope (explicit)

- **Editing any seam module** (`variant_proposer` / `run_synthetic` / `slot_extractor` / `layer_*` / `mutator` / `stage_b` / `metadata` / `review` / `packaging` / `loaders` / `l2_repr` / `llm_client` / `f1_pilot` / `spike`) **or Sprint 37's `target_scanner` / `menu_proposer` / `menu_artefacts`** or the 13 `prompts/*.txt` files. If a real bug surfaces during F3-prep-2-generate, it is a new bugfix sprint, not silent in-place patching.
- **`configs/synthetic/variant_budgets.yaml`, the sampler, the chapter driver** — F3-prep-3 (Sprint 39). This sprint's output is the *approved menu*; the sampler is what turns it into a variant catalog.
- **F3-run (full-catalog generation).** One chapter subset only (OEB). Full OBRA CIVIL + other chapters is F3-run.
- **F4 quality report / DATA_CARD refresh.**
- **Merging `synthetic` to `main`.** Permanently forbidden.

---

## Content requirements

1. `menu_runner.run_menu` composes the frozen `menu_proposer` + `menu_artefacts` surfaces without touching them and produces the two artefacts + a `MenuRun` scorecard.
2. `menu_review_parser.parse_review_file` reads a Markdown file line-by-line, matches `- [x] N. …` / `- [ ] N. …` against the machine JSONL by target heading + candidate index, and produces one `MenuVerdict` per unique target with per-candidate `approved` flags.
3. Every code path is hermetic. The live generation is the CLI invocation, not a `pytest` case.
4. The Markdown format written by Sprint 37 is the *input contract* to the parser. Changing either side without changing the other is an acceptance failure — a round-trip test pins the pairing.

## Acceptance

- **F3-prep-2-code (this sprint, Claude):**
  - `src/synthetic/menu_runner.py`, `src/synthetic/menu_review_parser.py`, `tests/synthetic/test_menu_runner.py`, `tests/synthetic/test_menu_review_parser.py` exist.
  - `git diff` shows **zero edits** to Sprint 37's three modules, to any seam module, or to the 13 prompt files.
  - `pytest tests -q` → **990 + N passed, 2 skipped** (N ≥ 15 from the new hermetic cases). Zero sockets, zero new third-party dep.
- **F3-prep-2-generate (this sprint, Claude, live):**
  - The 13 machine JSONL + 13 human Markdown files exist on disk (or a subset if a rewrite type has zero targets).
  - The recorded transcript store exists and `replay` reproduces the scorecard byte-identically.
  - The generation report (mechanical numbers only) is prepended to `RESEARCH_LOG.md`.
- **F3-prep-2-review (César, manual):** the 13 Markdown files show César's approvals; commit lands on the branch.
- **F3-prep-2-parse (Claude, post-review):**
  - `data/synthetic/menus/verdicts/{mtype}.jsonl` exists for every mtype with targets.
  - Coverage summary in `RESEARCH_LOG.md`: per-mtype total targets / targets with ≥1 approval / total approvals.
- Housekeeping docs updated at each landmark; F3-prep-2 flipped ✅ once the parse pass lands.

---

## Tasks

### Task 1 — `menu_runner.py` (F3-prep-2-code-A)
`MenuRun` dataclass (n_unique_targets, n_llm_calls, per-mtype {generated, skipped, mean_candidates}, total_wall_clock_s). `run_menu(stage_json, *, concept_filter, n, client, out_dir_machine, out_dir_review, chapter_label, seed)` composes Sprint 37 modules. `default_client(chapter_label)` returns `RecordingClient(HttpLLMClient(LLMConfig.from_env()), store_path)`. `format_scorecard(run)` (Markdown table). `main(argv)` with `run` (live) / `replay` (offline) subcommands; args: `--stage-json`, `--concept-filter`, `--n`, `--seed`, `--chapter-label`, `--model`, `--out-machine`, `--out-review`, `--llm-cache`.

### Task 2 — `menu_review_parser.py` (F3-prep-2-code-B)
`MenuVerdict` + `CandidateVerdict` frozen dataclasses. `_TICK_RE = re.compile(r"^- \[( |x)\] (\d+)\. ")`. `_HEADING_RE = re.compile(r"^## (.+)$")`. `parse_review_file(md_path, jsonl_path) -> tuple[MenuVerdict, ...]`: iterate JSONL as the source of truth for target order and candidate count; walk Markdown headings in order; assert canonical strings match; assert candidate count matches; per-candidate `approved = (tick == "x")`. `write_verdicts(verdicts, out_path)` (atomic JSONL). `parse_all(machine_dir, review_dir, out_dir) -> ParseReport` (per-mtype counts). `main(argv)` with `parse` subcommand.

### Task 3 — Hermetic tests (F3-prep-2-code-C)
As detailed in Scope. Golden fixtures under `tests/synthetic/fixtures/menu_review/` — a tiny sample menu (~2 targets × 3 candidates) with matching golden Markdown and JSONL. Positive and negative cases (all-ticked, none-ticked, mixed, heading-count mismatch, candidate-count mismatch).

### Task 4 — Housekeeping (Claude, post-code)
`RESEARCH_LOG.md` Sprint 38 entry with the code delta; `CLAUDE_SYNTHETIC.md` file-map rows for the two new modules + Sprint History entry; `RESEARCH_PROTOCOL.md §5` F3-prep-2-code ✅ / F3-prep-2-generate ⏳.

### Task 5 (Claude, live) — Run the live generation (F3-prep-2-generate)
```powershell
$env:PYTHONPATH = "src"
$env:BC3CAT_LLM_MODEL = "phi4:latest"
python -m synthetic.menu_runner run `
  --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" `
  --concept-filter OEB `
  --n 10 `
  --seed 7 `
  --chapter-label OEB
```
Capture the scorecard, prepend to `RESEARCH_LOG.md` as the Sprint 38 generation report. Commit the 13 Markdown files into the branch so César can review via git diff.

### Task 6 (César, manual) — F3-prep-2-review
Read the 13 Markdown files under `docs/synthetic/menus/`. Flip `- [ ]` → `- [x]` on candidates you accept. Save. Commit.

### Task 7 (Claude, post-review) — F3-prep-2-parse
```powershell
$env:PYTHONPATH = "src"
python -m synthetic.menu_review_parser parse `
  --machine-dir data/synthetic/menus `
  --review-dir docs/synthetic/menus `
  --out-dir data/synthetic/menus/verdicts
```
Prepend the coverage summary to `RESEARCH_LOG.md`. Flip F3-prep-2 ✅ in `RESEARCH_PROTOCOL.md §5`.

---

## Verification runbook

```powershell
$env:PYTHONPATH = "src"

# code (fast, hermetic): 990 + N passed, 2 skipped, no network
pytest tests -q --basetemp="$env:TEMP\pt_s38"

# no-seam-edit audit
git diff -- src/synthetic/variant_proposer.py src/synthetic/run_synthetic.py `
            src/synthetic/slot_extractor.py src/synthetic/layer_l1.py `
            src/synthetic/layer_l2.py src/synthetic/layer_l3.py `
            src/synthetic/layer_pd.py src/synthetic/mutator.py `
            src/synthetic/stage_b.py src/synthetic/metadata.py `
            src/synthetic/review.py src/synthetic/packaging.py `
            src/synthetic/loaders.py src/synthetic/l2_repr.py `
            src/synthetic/llm_client.py src/synthetic/f1_pilot.py `
            src/synthetic/spike.py src/synthetic/prompts `
            src/synthetic/target_scanner.py src/synthetic/menu_proposer.py `
            src/synthetic/menu_artefacts.py   # empty

git status --short   # new: menu_runner.py, menu_review_parser.py, test_menu_runner.py,
                     #      test_menu_review_parser.py, fixtures/menu_review/*;
                     # later: data/synthetic/menus/*, docs/synthetic/menus/*
```

The **live** F3-prep-2-generate (Task 5) is NOT part of the fast suite — it is the manual CLI invocation captured above.

---

## Risks / things most likely to surface here (which is the point)

- **phi4's list-shape reliability at N=10.** Sprint 37 pinned the parser; Sprint 38 is the first time we see how often phi4 returns a valid JSON list of 10 vs single-dict / N=1 / prose-wrapped-mess. High malformed-after-retry rate is a real finding — the fix is either a tighter wrapper instruction (single f-string edit in `menu_proposer.py`, cheap) or dropping `n` to 5 (config-only). Both are follow-up bugfixes if needed; not this sprint.
- **Multi-candidate quality degradation.** phi4 might produce 3 good + 7 near-identical candidates ("Turno diurno" / "En turno diurno" / "Durante el turno diurno" / …) — inter-candidate dedup catches the trivial ones, but if the diversity is genuinely low it means N=10 is over-budget. Measurable from the mean-candidates-per-target after dedup (in `MenuRun.mean_candidates`).
- **Review artefact tedium.** ~5 600 checkbox lines is a lot to skim, even at 3-5 s/line. If some rewrite types (e.g. `omission` at 212 targets) turn out to be uniformly good, we could add a "batch approve" shortcut in the Markdown template — but only if the review actually demands it. Sprint 37's format is our starting point.
- **Heading-string drift between Markdown and JSONL.** If the reviewer accidentally edits a `## TRABAJO / Diurno` heading, the parser's canonical-match assertion fails loud. Documented as expected; the reviewer is asked not to touch headings.
- **Wall-clock on the live run.** ~350-400 LLM calls × ~20-30 s/call on `phi4:latest` (local Ollama) ≈ 2-3 h. Acceptable for a one-off; recorded so subsequent replays are instant.

---

## Design notes worth committing to memory

- **F3-prep-2 splits code / generate / review / parse, like F1-run before it.** Sprint 37 built the writer; this sprint builds the driver + reader and runs both live-then-review. The manual review is the *only* fluency judgement in the whole flow.
- **Reject-by-default is the review contract.** Anything not `- [x]` is rejected. This trades a small chance of accidental all-reject for a much simpler parser and no ambiguous "not reviewed" state.
- **The parser reads the JSONL as truth and Markdown as input.** Machine JSONL fixes target order, canonical text, and candidate count; Markdown provides only the tick state. This prevents silent drift and gives the parser a clear failure mode.
- **`menu_runner.py` is `f1_pilot.py`'s sibling.** Consumer above the orchestrator, one `run` / `replay` CLI, `RecordingClient` bracketing the live call.
- **Deterministic + recorded end-to-end.** Same stage-2 + same seed + same recorded store → byte-identical outputs on replay. This is what makes the review process safe to iterate on.

---

## References

- [`SPRINT_37.md`](SPRINT_37.md) — the menu builder this sprint drives + reads back.
- [`../../src/synthetic/menu_proposer.py`](../../src/synthetic/menu_proposer.py) / [`menu_artefacts.py`](../../src/synthetic/menu_artefacts.py) / [`target_scanner.py`](../../src/synthetic/target_scanner.py) — the frozen public surfaces.
- [`../../src/synthetic/f1_pilot.py`](../../src/synthetic/f1_pilot.py) / [`spike.py`](../../src/synthetic/spike.py) — the consumer-above-orchestrator pattern the new driver mirrors.
- [`../../src/synthetic/llm_client.py`](../../src/synthetic/llm_client.py) — `HttpLLMClient` / `RecordingClient` / `ReplayClient`.
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 37 entry (dedup measurement) → Sprint 38 landmarks.
- [`../../CLAUDE.md`](../../CLAUDE.md) — never-merge-`synthetic`-to-`main`.

---

## Non-goals reminder

If you find yourself editing the seam or Sprint 37's three modules — **stop**. The driver + parser compose the frozen public surfaces; a real bug is a new bugfix sprint.

If you find yourself making a live LLM call from a `pytest` case — **stop**. The suite is hermetic (canned client); the live run is the CLI invocation.

If you find yourself ticking `[x]` on candidates from Claude — **stop**. The manual review is César's; Claude produces the artefacts and reads the state back, never authors the verdicts.

If you find yourself running the full-catalog generation, building `configs/synthetic/variant_budgets.yaml`, writing the sampler, or drafting the chapter driver — **stop**. That is F3-prep-3 (Sprint 39) and F3-run (Sprint 40).
