# Sprint 38.6 — template_paraphrase diversity — Design Spec

| Field | Value |
|---|---|
| **Date** | 2026-08-30 (approved by César in session) |
| **Branch** | `synthetic` (never merged to `main`) |
| **Problem** | `template_paraphrase` candidates are dull: mean token distance to the original is 0.33 and mutual similarity between a target's candidates is 0.77 (measured 2026-08-18) — near-synonym swaps, no structural variation. |
| **Goal** | More lexical *and structural* variation per template, without losing meaning, losing parameters, or mixing templates — so the `single_L3_template_paraphrase` evaluation slice genuinely tests structural robustness on its own (César's explicit decision: structure lives *inside* the type, not only in stacked conditions). |
| **Predecessor** | Sprint 38.5 (parser repair, caps, gates) + addendum (`prompt_scaffold_echo` guard). |
| **Successor** | Implementation plan `SPRINT_386.md`; the manual review (F3-prep-2-review) then runs on the improved menus. |

## Why the current output is dull (diagnosis)

1. **Temperature 0** — deterministic decoding takes the safest path: synonym substitution.
2. **One call for 10 alternatives "ordered best to worst"** — candidates 2–10 anchor on candidate 1; the menu holds ten variations of one paraphrase.
3. **The prompt is all brakes** ("conservando exactamente el significado…") **and no accelerator** — it never asks for structural change.
4. **phi4-14B is small** — restructuring a 150-word dimension-dense sentence while preserving 8 placeholders is hard; small models retreat to word swaps.

## Design

### D1. Transformation-slotted rounds (prompt)

Per target, **3 rounds** of ~3 candidates, each round's instructions appended by the runtime wrapper (Sprint-37 pattern — the on-disk prompt file stays byte-identical):

- **R1 — voice & frame:** active ↔ passive/impersonal *se*; nominal ↔ verbal frame (*"Ejecución de canalización…" → "Se ejecutará la canalización…" / "Canalización ejecutada mediante…"*).
- **R2 — architecture:** clause reordering (e.g. the *"incluso…"* tail moved forward), split one long sentence into two or merge two, relocate the parenthetical placeholder block.
- **R3 — free restructuring:** "rewrite as a different technical writer would, changing both wording and sentence structure"; the wrapper lists the openings of R1/R2's outputs as forbidden starts.

Each wrapper carries its round tag (also what makes the cache key unique per round) and restates the placeholder-preservation contract.

**Slot sanitization (mini-F1):** the `template` and `concept` slot values are stripped of the FIEBDC `\` delimiters before rendering, **for `template_paraphrase` only** — its cache is invalidated by this sprint anyway, and the trailing `\` is the proven root cause of the OEB010$ prompt echo. The other 10 types keep byte-identical prompts and valid caches; full F1 remains a Sprint-40 pre-task.

### D2. Sampling temperature

The `template_paraphrase` calls run at **temperature 0.8** via the existing `BC3CAT_LLM_TEMPERATURE` env knob (no code change in `llm_client`); the driver invocation for this type sets it, everything else stays at the protocol-pinned 0.0. Replays read recorded transcripts and remain deterministic.

### D3. Two models

The same 3 rounds run against **`phi4:latest`** and **`qwen2.5:14b`** (via `BC3CAT_LLM_MODEL`), each with its own transcript store: `data/synthetic/llm_cache/menu_OEB_tpar_<model>/`. Candidates gain a `proposer_model` payload field, shown in the review Markdown so provenance is visible.

> **Prerequisite (blocking, needs César's go-ahead to download):** `ollama list` is empty as of 2026-08-30 — `phi4:latest` was lost, presumably to an Ollama update. Both models must be pulled from ollama.com before the live run: `ollama pull phi4:latest` (~9.1 GB) and `ollama pull qwen2.5:14b` (~9.0 GB).

### D4. Pooling, gates, ordering

All rounds × models pool into one `CandidateSet` per target, then in order:

1. **Schema + placeholder-set validation** (existing, unchanged): the candidate's `$VAR` / `$VAR(%AXIS)` set must equal the original's exactly.
2. **`prompt_scaffold_echo` guard** (existing, from the 38.5 addendum).
3. **Quantity-conservation check (new):** the *multiset* of numeric tokens (`760`, `1,60`, `95`) and attached unit/code tokens (`mm`, `m`, `%`, `HM-20`, `4x40`) in `new` must equal `original`'s. Catches changed dimensions, dropped quantities, duplicated diameters — the highest-risk drift class in these templates. Applied to `template_paraphrase` **and `reorder`** (same full-surface shape). Drop reason: `quantities_not_conserved`.
4. **Similarity gate (new, all types, cache-neutral):** a candidate with token-Jaccard > 0.8 against an already-kept candidate of the same target is dropped (`near_duplicate_of_kept`). Existing exact-normalised dedup stays as the first line.
5. No `MENU_CAP` for `template_paraphrase` (unchanged — it is not in the cap table).

### D5. Measurement

`menu_profile` gains two columns: **`dist_orig`** (mean token-level distance of candidates to their original) and **`pair_sim`** (mean pairwise token-Jaccard among a target's candidates). Success criterion for this sprint: `template_paraphrase` `pair_sim` drops well below the current 0.77 (target ≤ 0.55) while `dist_orig` rises from 0.33 (target ≥ 0.45), with the quantity and placeholder gates reporting only legitimate drops.

### D6. Rollout

1. Hermetic build + tests (no live calls from pytest — canned clients, as always).
2. **Pilot:** 5 concepts × 3 rounds × 2 models ≈ 60 calls. Profile + eyeball with César.
3. **Full run:** all 49 `template_paraphrase` targets ≈ 300 calls, estimated **45–90 min GPU total** across both models.
4. Regenerate `template_paraphrase` menu artefacts; all other types replay from their existing caches untouched.

## Guarantee model (what protects what)

| Property | Strength | Mechanism |
|---|---|---|
| Parameters preserved | **Proven** | `_require_placeholders_preserved` (exact set equality) + `layer_l3` exact-substring application fails loud |
| No template mixing | **Structural** | one template per prompt (no siblings in context); placeholder fingerprint mismatch kills blends; application anchored to the concept's own field |
| Quantities/dimensions preserved | **Proven (new)** | quantity-conservation multiset check (D4.3) |
| Qualitative meaning | **Human-gated** | prompt constraint + César's reject-by-default tick (the menu-first workflow's semantic gate, by design) |

## Out of scope

- Round-trip translation (held in reserve; most code, most drift risk).
- Diversity work on the other 10 types (L2 `paraphrase`/`expansion` measured healthy; low-entropy types are capped by design).
- Full F1 (prompt-side `\` strip for all types) — Sprint 40 pre-task.
- Replacing `unit_conversion`/`num_to_text` with arithmetic (follow-up F2).

## Risks

| Risk | Mitigation |
|---|---|
| qwen2.5:14b ignores the JSON-list contract | The 38.5 tolerant parser + per-element validation already absorb format noise; pilot measures the failure rate before the full run |
| Temp 0.8 raises placeholder-corruption rate | Placeholder check drops them; pilot quantifies; if >50% of a round dies, lower to 0.5 |
| R3 "forbidden openings" makes prompts order-dependent | Only R3 depends on R1/R2 outputs; recorded per-round transcripts keep replays deterministic |
| ~18 GB of model downloads | Explicitly gated on César's go-ahead (see D3) |
