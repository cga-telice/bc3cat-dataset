# Sprint 37 — Phase F Task F3-prep-1 (menu builder: dedup-first target scan + N-candidate proposer + human-review artefact)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 37                                                                                          |
| **Date**        | 2026-07-08 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | F3-prep-1 (new split of F3). This sprint builds the *menu-first* generation flow — the humanreview gate César asked for before running live at chapter scale. Hermetic. |
| **Predecessor** | Sprint 36 — 13th modification type `template_paraphrase` (see [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md)); Sprint 35 multi-concept sanity check; F1-review decision on menu-first review (this conversation, 2026-07-08). |
| **Successor**   | Sprint 38 — **F3-prep-2** (live phi4 pass to populate the menu; manual review by César) → Sprint 39 F3-prep-3 (variant budgets + sampler + chapter driver) → F3 full generation. |

---

## Context

Sprints 30–36 closed all F1_FINDINGS items and validated the pipeline across three concepts (OEB020$, OEB050$, OEB070$) at ≥90 % clean. F3 (full-catalog generation) was the natural next step. Before launching it, **César raised a stronger quality gate**: don't accept phi4's single rewrite per target and later review a sample of rendered items — instead ask phi4 for a **menu of 10 candidates per target**, review the whole menu once by hand, and sample the final corpus from the approved candidates only.

The measurement that motivated the shift (dedup scan on the OEB subset, 2026-07-08 in the scratchpad):

| Rewrite family | Total targets | Unique after dedup | Savings |
|---|---:|---:|---:|
| L1 (per axis-value)   | 459 each type | **67 each** | **85 %** |
| L2 (per fragment)     | 306 each type | **33 each** | **89 %** |
| L3 (per template)     | 50 each type  | 49 each     | 2 %     |
| new_param             | 25            | 25          | 0 %     |
| **All families**      | **3 847**     | **673**     | **83 %** |

The four workhorse axes (TRABAJO, BANDA DE MANTENIMIENTO, CONDICIONES DE EJECUCIÓN, TIPO DE TERRENO) repeat in 18–24 of the 25 OEB concepts. The candidate-review budget collapses from ~38 000 lines (no dedup) to ~6 700 lines (~7–9 h manual review, likely less once Sprint 34's per-axis applicability gate trims L1). That is the effort budget this sprint enables.

### The split: F3-prep-1 (this sprint, hermetic) vs F3-prep-2 (live) vs F3-prep-3 (sampler)

* **F3-prep-1 — the menu builder.** Code only, no live LLM call. Ships the chapter-level target scanner + dedup, the multi-candidate proposer, and the review-friendly artefact writer, plus hermetic tests over a canned client. The single design intent: make it *possible* for phi4 to populate the menu and *easy* for César to review it.
* **F3-prep-2 — the live run + manual review** (Sprint 38, live, local, free). Point the menu builder at phi4 + the OEB subset in OBRA CIVIL; produce the actual menu on disk; César reviews the Markdown artefact and marks candidates ✅/❌ in place; a parser reads the approvals back into structured verdicts.
* **F3-prep-3 — variant budgets + sampler + chapter driver** (Sprint 39). `configs/synthetic/variant_budgets.yaml` (flat 50 per concept), the deterministic sampler that draws N variants per concept from the approved menu, and the chapter driver that iterates concept keys. That closes F3-prep and unblocks F3-run.

### Why the menu-first approach is a real change

Today's pipeline (Sprints 27–36) does: enumerate targets per concept → propose one variant per target → apply → materialize → review a sample of rendered items. Failures caught at the review stage are already replicated across hundreds of leaves. The menu-first flow catches every bad rewrite **before** it multiplies: the LLM proposes many, the human filters at the source, the sampler only draws from surviving candidates. It also uses phi4's capacity to hedge with alternatives (10 attempts per prompt) rather than trusting a single greedy pick.

---

## Scope

### In scope

- **F3-prep-1-A — `target_scanner.py`** (chapter-level target enumeration + dedup).
  - `scan_chapter(stage_json: dict, *, concept_filter: Callable[[str], bool] | None = None) -> ChapterInventory`.
  - `ChapterInventory` (frozen dataclass): per-`ModificationType` list of `UniqueTarget(dedup_key, canonical: str, usages: tuple[TargetUsage, ...])`, where each `TargetUsage` records `(concept_key, axis_or_var, siblings, condition)` — everything the proposer and the review artefact need.
  - Dedup keys per family (documented in-module):
    - **L1** = `(axis_label_normalised, value_text_normalised)` — the value is what's rewritten; the axis label is the semantic anchor (guards against accidental cross-axis collisions of identical strings). One `UniqueTarget` fans out to all six L1 types via `TYPE_TO_LAYER`.
    - **L2** = `fragment_text_normalised` alone. Aggressive dedup by textual identity; sibling context per usage is carried in `TargetUsage.siblings`, so the collision guard from Sprint 34 still gets the right per-concept siblings at sampling time. Applies to the three L2 types.
    - **L3** = `(field, template_normalised)`. Templates rarely repeat; this line is here for completeness. Applies to the three L3 types.
    - **new_param** = `concept_key`. No dedup — always concept-specific.
  - Whitespace-normalised, case-preserving (Spanish accents matter). Imports `taxonomy`/`slot_extractor` + stdlib only.
- **F3-prep-1-B — `menu_proposer.py`** (the N-candidate driver).
  - `propose_candidates(target: UniqueTarget, mtype: ModificationType, *, n: int, client: LLMClient) -> CandidateSet`.
  - Wraps the existing `variant_proposer.propose_variant` shape but requests a **JSON list of `n` alternatives** by appending a shared multi-candidate instruction to the loaded prompt (no edits to the 13 prompt files — the extension is a single f-string in this module): *"Devuelve una lista JSON de `n` alternativas distintas, ordenadas de mejor a peor. Cada alternativa debe seguir el esquema JSON descrito arriba; no repitas alternativas."*
  - Parse: list-of-`n` JSON; on a single retry after malformed output the whole target skips (same failure semantics as C2). Individual candidates that fail per-item schema validation (`variant_proposer._validate_payload`) are dropped and logged; the surviving list becomes the `CandidateSet`. **Inter-candidate dedup** at parse time (normalised-string set) — phi4 sometimes returns near-duplicates.
  - Return: `CandidateSet(target, mtype, candidates: tuple[CandidateProposal, ...], malformed: bool, dropped: tuple[dict, ...])`. Each `CandidateProposal` mirrors `VariantProposal`'s shape (payload + skipped-or-not + rejection reason) so downstream code that already speaks that vocabulary needs no re-education.
  - Uses `RecordingClient` transparently — one prompt → one recorded response → `n` candidates → deterministic replay.
- **F3-prep-1-C — `menu_artefacts.py`** (the writer: both formats, from one call).
  - `write_menu(inventory: ChapterInventory, sets: Iterable[CandidateSet], *, machine_dir: Path, review_dir: Path) -> None`.
  - **Machine-readable — `data/synthetic/menus/{mtype}.jsonl`** (one file per rewrite type, one JSON line per `UniqueTarget`, carries `dedup_key` + `canonical` + `usages` + `candidates: list[{new, approved: null, ...}]`). Atomic `.tmp` + `os.replace`. This is what F3-prep-3's sampler consumes.
  - **Human-review — `docs/synthetic/menus/{mtype}.md`** (one file per rewrite type). Format (fixed by test):
    ```markdown
    # L1 synonym_label — OEB subset menu

    _One section per unique (axis, value). Tick candidates you approve; delete or leave unticked to reject. Save the file. The parser (Sprint 38) reads ticks back._

    ## TRABAJO / Diurno
    _Used in 20 concepts: OEB010$, OEB020$, OEB030$, …_
    _Sibling values on this axis: Nocturno, Cualquier franja horaria, Diurno Excepcional, Nocturno Excepcional_

    - [ ] 1. Turno diurno
    - [ ] 2. Horario de día
    - [ ] 3. Jornada diurna
    …
    - [ ] 10. En horario diurno

    ## TRABAJO / Nocturno
    _Used in 20 concepts: OEB010$, OEB020$, …_
    _Sibling values on this axis: Diurno, Cualquier franja horaria, Diurno Excepcional, Nocturno Excepcional_

    - [ ] 1. Turno de noche
    - [ ] 2. Horario nocturno
    …
    ```
  - Design intent: skimmable in GitHub's Markdown viewer, editable in VS Code / any text editor, diffable in git, single-checkbox action per candidate. Sibling values are shown so the reviewer sees the collision context that shaped phi4's prompt. **Deterministic ordering** (dedup-key sort inside each file, candidate index preserved) so re-runs produce byte-identical diffs.
- **F3-prep-1-D — tests `tests/synthetic/test_menu_builder.py`** (all hermetic).
  - `scan_chapter` on a tiny 3-concept stage-2 fixture → the expected dedup counts + `TargetUsage` sibling capture; L1/L2/L3/new_param each covered.
  - `propose_candidates` against a canned client returning valid-list / malformed-then-valid / all-schema-fail / near-duplicates → correct `CandidateSet` shape, inter-candidate dedup fires, malformed-after-retry skips whole target, per-item schema failures drop only the offender.
  - `write_menu` byte-identical output round-trip against a golden Markdown fixture + a golden JSONL fixture; atomic write; deterministic ordering.
  - No-reverse-import: no seam module imports the three new modules. Zero sockets. Zero new third-party dependency.
- **Doc + housekeeping:** this file; `RESEARCH_LOG.md` Sprint 37 entry; `CLAUDE_SYNTHETIC.md` file map (new `target_scanner.py` / `menu_proposer.py` / `menu_artefacts.py` rows; `configs/synthetic/variant_budgets.yaml` still ❌ — Sprint 39; `menu_review_parser.py` still ❌ — Sprint 38); `RESEARCH_PROTOCOL.md` §5 F3-prep sub-tasks landed.

### Out of scope (explicit)

- **The live phi4 run + populated menus + the review markdown César will fill in** — F3-prep-2 (Sprint 38). This sprint's tests use a canned client only.
- **The review parser** that reads ticked boxes back into `Verdict` records — F3-prep-2 (Sprint 38). Sprint 37 defines the on-disk shape; Sprint 38 writes the reader.
- **`configs/synthetic/variant_budgets.yaml` + the sampler + the chapter driver** — F3-prep-3 (Sprint 39). Menu → approved menu → variant catalog → materialized items is a strict pipeline; this sprint owns only the first arrow.
- **Any edit to the 13 prompt files.** The multi-candidate instruction is appended by `menu_proposer` at runtime; the frozen prompt bodies stay byte-identical (their test pins hold).
- **Any change to `variant_proposer.propose_variant`, `run_synthetic.run_concept`, `stage_b`, `metadata`, `review`, `packaging`, `loaders`.** The menu builder is a *parallel* generation front-end above the seam; the single-variant path stays intact for anyone (or any old test) that still calls it.
- **Merging `synthetic` to `main`.** Permanently forbidden.

---

## Content requirements

1. `scan_chapter` on the real OBRA CIVIL stage-2 JSON, filtered to OEB-prefixed concepts, reproduces the scratchpad measurement (673 unique targets across 25 concepts, per-family breakdown above). This is asserted by a slow-marked integration test (`@pytest.mark.integration`) that reads the real file; the fast suite covers a tiny fixture only.
2. `propose_candidates` requests `n = 10` by default (constant `DEFAULT_N_CANDIDATES = 10` in `menu_proposer`, overridable in the CLI arg for the live sprint). Inter-candidate dedup runs before schema validation so near-duplicates don't waste a schema-fail slot.
3. The Markdown artefact is trivially skimmable: **one target = one heading = up to 10 checkboxes.** A future rerun that only changes the candidate ordering produces a minimal diff (deterministic ordering guarantees this).
4. The machine-readable JSONL carries `approved: null` for every candidate; Sprint 38's parser flips those to `true` / `false` from the Markdown ticks and re-emits.

## Acceptance

- `src/synthetic/target_scanner.py`, `src/synthetic/menu_proposer.py`, `src/synthetic/menu_artefacts.py`, `tests/synthetic/test_menu_builder.py` exist.
- `git diff` shows **zero edits** to `variant_proposer.py`, `run_synthetic.py`, `slot_extractor.py`, `layer_*.py`, `mutator.py`, `stage_b.py`, `metadata.py`, `review.py`, `packaging.py`, `loaders.py`, `l2_repr.py`, `llm_client.py`, `f1_pilot.py`, `spike.py`, and the 13 `prompts/*.txt` files.
- `pytest tests -q` → **951 + N passed, 2 skipped** (Sprint 36 baseline 951, N ≥ 20 from the new hermetic cases). Zero failures, zero network, zero new third-party dependency.
- The integration test (`pytest tests -q -m integration`) reads OBRA CIVIL stage-2 and asserts the 673 unique-target count + the per-family breakdown from the scratchpad measurement.
- Housekeeping docs updated; F3-prep-1 flipped ✅, F3-prep-2 annotated ⏳, F3-prep-3 annotated ⏳.

---

## Tasks

### Task 1 — `target_scanner.py` (F3-prep-1-A)
`ChapterInventory` + `UniqueTarget` + `TargetUsage` dataclasses + `scan_chapter(stage_json, *, concept_filter=None)`. Dedup keys as specified above. Reuse `slot_extractor.enumerate_targets` per concept, canonicalise, group by dedup key, record usages. Whitespace normalisation via a small local helper (do not import Spanish-accent stripping — accents are semantically load-bearing here).

### Task 2 — `menu_proposer.py` (F3-prep-1-B)
`DEFAULT_N_CANDIDATES = 10`; `propose_candidates(target, mtype, *, n, client)` composes the loaded prompt + the shared multi-candidate instruction, parses a JSON list, dedupes inter-candidate near-duplicates, validates each candidate via the existing `variant_proposer._validate_payload`, returns a `CandidateSet`. Malformed-list-after-retry → whole-target skip with `Modification(status="skipped", reason="malformed_list_after_retry: …")` reason. Per-item failures drop only the offender.

### Task 3 — `menu_artefacts.py` (F3-prep-1-C)
`write_menu(inventory, sets, *, machine_dir, review_dir)` — writes both formats atomically. Fixed Markdown template (see Scope-C). Deterministic ordering by dedup key inside each file; candidates numbered by their `CandidateProposal` order (which mirrors phi4's own quality ranking).

### Task 4 — Hermetic tests (F3-prep-1-D)
Per Scope-D. Golden fixtures live under `tests/synthetic/fixtures/menu_builder/` (tiny 3-concept stage-2 JSON, canned client responses, golden `.md` + `.jsonl`). Add the slow `integration` marker to the OBRA CIVIL-scale test and configure `pytest.ini`/`conftest` if the marker isn't already declared.

### Task 5 — Housekeeping
`RESEARCH_LOG.md` Sprint 37 entry (mechanical scorecard: unique-target counts, files added, test delta); `CLAUDE_SYNTHETIC.md` file-map rows for the three new modules; `RESEARCH_PROTOCOL.md` §5 F3-prep-1 ✅ / F3-prep-2 ⏳ / F3-prep-3 ⏳.

---

## Verification runbook

```powershell
$env:PYTHONPATH = "src"

# fast suite (default): 951 + N passed, 2 skipped, no network
pytest tests -q --basetemp="$env:TEMP\pt_s37"

# slow integration test: reproduces the 673 unique-target count on OEB subset
pytest tests -q -m integration --basetemp="$env:TEMP\pt_s37_int"

# no-seam-edit audit
git diff -- src/synthetic/variant_proposer.py src/synthetic/run_synthetic.py `
            src/synthetic/slot_extractor.py src/synthetic/layer_l1.py `
            src/synthetic/layer_l2.py src/synthetic/layer_l3.py `
            src/synthetic/layer_pd.py src/synthetic/mutator.py `
            src/synthetic/stage_b.py src/synthetic/metadata.py `
            src/synthetic/review.py src/synthetic/packaging.py `
            src/synthetic/loaders.py src/synthetic/l2_repr.py `
            src/synthetic/llm_client.py src/synthetic/f1_pilot.py `
            src/synthetic/spike.py src/synthetic/prompts    # empty

git status --short   # new: target_scanner.py, menu_proposer.py, menu_artefacts.py,
                     #      test_menu_builder.py, fixtures/menu_builder/*;
                     # modified: docs only
```

The **live** F3-prep-2 (Sprint 38) is NOT part of this suite:

```powershell
# (Sprint 38, live, local, free — Ollama serving phi4:latest)
python -m synthetic.menu_proposer run `
  --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" `
  --concept-filter "OEB" --n 10 --seed 7
```

---

## Risks / things most likely to surface here (which is the point)

- **phi4's list-vs-dict compliance.** Every existing prompt asks for a single dict; the multi-candidate wrapper asks for a list. If phi4 collapses under the change, we'll see it in Sprint 38's malformed rate — Sprint 37's canned tests only pin the *parser*, not the model behaviour. If real malformed rate is high we tighten the wrapper instruction; if it's very high we accept single-dict responses as a degraded fallback (deferred).
- **L2 dedup by fragment-text alone is aggressive.** Two concepts using the same Spanish phrase for semantically different roles could get the same approved rewrite. The scratchpad top-15 shows the workhorse fragments really are the same phrase; if a specific case blows up in Sprint 38, we add a per-usage override — but only when it actually happens.
- **`{sibling_fragments}` and `{value_list}` slots in the existing L1/L2 prompts still fire per-usage** (they're populated by `slot_extractor.extract_slots`, not by the target-scanner dedup). The menu builder passes the *first* usage's slot values to phi4 (deterministic); if downstream sampling picks a usage with different siblings, the collision guard from Sprint 34 catches any late-arriving conflict.
- **Markdown ticks are the review contract.** GitHub renders `- [ ]` / `- [x]` universally, VS Code supports click-to-toggle, `grep '\[x\]'` works. If the review parser (Sprint 38) has trouble with edge-case syntax, we constrain the acceptable tick set in that sprint.

---

## Design notes worth committing to memory

- **Dedup-first is the real efficiency win.** The 83 % target reduction (measured, not estimated) is what makes 10 candidates × human review affordable. Every code path in this sprint is designed around a `UniqueTarget` being the unit of proposal and review, not a `(concept, target)` pair.
- **The Markdown artefact is the human contract; the JSONL artefact is the machine contract.** Both are emitted from one call. The reviewer never touches JSONL; the sampler never touches Markdown. Sprint 38 bridges them.
- **The multi-candidate instruction is appended at runtime, not baked into prompt files.** Prompt tests from Sprints 32–36 stay green; the 13 files stay byte-identical; if we ever revert to single-candidate mode, we delete one f-string.
- **`propose_candidates` is a peer of `propose_variant`, not a replacement.** The single-candidate path (used by `run_concept` → Sprint 27's `f1_pilot`) stays live. If the menu-first flow turns out to have a fatal flaw at Sprint 38, we haven't broken anything.
- **Deterministic ordering everywhere.** Same stage-2 + same seed + same canned responses → byte-identical Markdown + byte-identical JSONL. This is what makes re-runs and reviewer diffs sane.

---

## References

- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 36 (13-type taxonomy) as the closing entry before this pivot.
- [`../F1_FINDINGS.md`](../F1_FINDINGS.md) — the earlier review model, superseded by the menu-first flow.
- [`../../src/synthetic/slot_extractor.py`](../../src/synthetic/slot_extractor.py) — the per-concept target enumerator this sprint dedupes across concepts.
- [`../../src/synthetic/variant_proposer.py`](../../src/synthetic/variant_proposer.py) — `_validate_payload` reused per candidate; `propose_variant` untouched.
- [`../../src/synthetic/llm_client.py`](../../src/synthetic/llm_client.py) / [`../../src/synthetic/f1_pilot.py`](../../src/synthetic/f1_pilot.py) — the transport + consumer-above-orchestrator pattern this sprint mirrors.
- [`../../CLAUDE.md`](../../CLAUDE.md) — never-merge-`synthetic`-to-`main`.

---

## Non-goals reminder

If you find yourself editing `variant_proposer` / `run_synthetic` / any seam module — **stop**. The menu builder sits *above* the seam like `spike.py` and `f1_pilot.py`.

If you find yourself editing one of the 13 prompt files to add "return a list" instructions — **stop**. The instruction is a runtime f-string append in `menu_proposer.py`; the frozen prompt bodies stay byte-identical.

If you find yourself making a live LLM call from a `pytest` case — **stop**. The suite is hermetic (canned client); the live run is Sprint 38's CLI.

If you find yourself writing the review parser or the sampler — **stop**. That is F3-prep-2 / F3-prep-3.
