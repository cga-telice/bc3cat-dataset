# Research Log — BC3CAT-Syn

**Project:** BC3CAT-Syn — Rule-Modification Synthetic Benchmark
**Branch:** `synthetic`
**Started:** May 2026

---

## How to Use This Log

Append an entry after every sprint. Each entry should capture:
- **What was attempted and what was accomplished** — concrete deliverables, not intentions.
- **Key results** — numbers, observations, acceptance-rate tables, throughput, accuracy on review samples.
- **Decisions made and their rationale** — especially anything that updates the design table in `CLAUDE_SYNTHETIC.md` or §4 of `RESEARCH_PROTOCOL.md`.
- **Problems encountered and how they were resolved (or not)** — including dead-ends; negative results matter.
- **What changed in the plan as a result** — task IDs added, split, or removed from the protocol backlog.

Be concrete. Write numbers, not impressions. This log serves two purposes: (1) context recovery if we lose track of where we are, and (2) source material for the BC3CAT-Syn Data-in-Brief paper's methodology section.

Each entry ends with two housekeeping lines:
- **CLAUDE_SYNTHETIC.md updated:** `yes` / `no` — did the file map, sprint-history block, or design table change?
- **Next step:** the sprint or task that should pick up next.

---

## Log Entries

*Newest entries at the top.*

---

### 2026-08-31 (cont.) — Sprint 38.7-B: auditoría de César, rúbrica v2 y re-juicio

- **Auditoría dirigida (54 campos):** César adjudicó los 10 Dudosos (todos A), 5 reglas de
  línea fina (3 recuperaciones, 2 confirmaciones) y la muestra de 30 — donde ratificó las 15
  aprobaciones pero **revirtió 13 de los 15 rechazos** (solo mantuvo M14 borrado-extra y M15
  bloque-duplicado). Conclusión registrada: el listón del propietario para un benchmark de
  estrés admite deriva léxica/semántica, registro imperfecto y valorativos como ruido útil.
- **Rúbrica v2** (RUBRIC.md, sección final): aprobar por defecto; R solo por (1) rotura
  estructural de render, (2) borrado extra en omission, (3) residuo de generación.
- **Re-juicio de los 1 646 R** bajo v2 (28 lotes): 1 444 recuperados, 202 confirmados R
  (roturas de render verificadas contra los valores reales de los ejes: marcos «certificada
  bajo $K»→«bajo bajo vías», bloques duplicados, "T" huérfana, %A crudo, comillas envolventes).
- **Resultado final: 2 609 A / 202 R (92,8 %)**. Targets sin aprobado: 79 → **14** (13 de
  omission — César decidió HUECO para el tipo — y 1 de expansion). Ticks y verdicts/*.jsonl
  regenerados y validados con `menu_review_parser parse`. Rechazos finales listados en
  `review_full/FINAL_REJECTS.md` para el vistazo del propietario.
- **Nota de método (honesta):** la validación del corpus es LLM-con-rúbrica en dos fases
  (v1.1 estricta → v2 calibrada al propietario mediante auditoría dirigida con sello de
  independencia); la afirmación publicable es «filtrado mecánico-estructural verificado +
  listón semántico permisivo definido y auditado por el autor», no revisión humana exhaustiva.

### 2026-08-31 — Sprint 38.7 (revisión de los 11 menús: rúbrica, calibración, pasada LLM completa, parse)

- **Rúbrica** `review_calibration/RUBRIC.md` v1 (5 criterios, A/R/D, rechazo por defecto, ciega
  de modelo) + v1.1 (8 reglas de desambiguación decididas por César tras las ambigüedades
  detectadas en los lotes de calibración).
- **Calibración (100 ítems, semilla 38):** los veredictos de Claude se sellaron por SHA-256 en git
  ANTES de recibir los de César (verificado al revelar: hash coincide). Resultado: César aprobó
  100/100 → kappa 0.00 (sin varianza, no computable). César adjudicó la discrepancia como "eres
  más riguroso y has hecho mejor trabajo" y delegó la revisión en Claude con auditoría humana.
  Se documenta tal cual: la validación del corpus es **por LLM con rúbrica escrita + auditoría
  humana dirigida**, no revisión humana exhaustiva.
- **Pasada completa:** 2 811 candidatos, 58 lotes homogéneos por tipo con contexto de hermanos,
  ciega de modelo. **1 155 A / 1 646 R / 10 D (41,1 % aprobación)**. Consistencia intra-revisor
  sobre los 100 de calibración re-juzgados: 89/100. Ticks aplicados a `docs/synthetic/menus/*.md`
  (verificados 1:1 contra veredictos); razones por candidato en `review_full/*_verdicts.jsonl`;
  informe + Dudosos + 79 targets-sin-aprobado + muestra de auditoría en
  `review_full/REVIEW_REPORT.md`.
- **F3-prep-2-parse ejecutado:** `menu_review_parser parse` valida los ticks y emite
  `data/synthetic/menus/verdicts/{tipo}.jsonl` — el contrato del sampler de Sprint 39 está servido.
- **Hallazgos de generación para Sprint 40** (de los patrones sistemáticos de los 58 lotes):
  expansion produce colas valorativas ("garantizando…") en masa; "con topo" se malinterpreta como
  topografía en TODOS los modelos y tipos; template_paraphrase reinterpreta el bloque parentético
  como normas/dimensiones y rompe marcos de placeholders ($I locativo tratado como diámetro);
  residuos mecánicos del enmascarado: "mm mm", ",," (coma tragada en literal Q), bloques $L/$M/$N
  duplicados en literal que evaden el check de conjuntos (defensa en profundidad: la revisión los
  cazó; corregir remask/validador en 38.8 o Sprint 40).
- **Pendiente de César (auditoría, ~30-45 min):** 10 Dudosos, 5 decisiones de línea fina,
  30 ítems de muestra confirmar/corregir, y decidir qué hacer con los 79 targets sin aprobado
  (adjudicar / regenerar con prompts corregidos / aceptar hueco).

### 2026-08-30 — Sprints 38.6 + 38.6-B (template_paraphrase diversity: rounds×models, masking, rescue)
**Date:** 2026-08-30
**Sprint files:** [`sprints/SPRINT_386.md`](sprints/SPRINT_386.md) (spec: [`sprints/SPRINT_386_DESIGN.md`](sprints/SPRINT_386_DESIGN.md)) + same-day addendum [`sprints/SPRINT_386B.md`](sprints/SPRINT_386B.md) (invariant masking + top-up rounds + remask rescue).
**Backlog IDs:** Sprint 38.6 / 38.6-B — closed (inserted between Sprint 38.5 and F3-prep-2-review, same insertion pattern as 38.5). F3-prep-2-review (César, manual) + F3-prep-2-parse (Claude, post-review) still open.

**Why this sprint exists.** The `template_paraphrase` menu was dull — ten near-identical variations of one paraphrase per target. Diagnosis (design spec): (1) temperature 0 takes the safest decoding path, synonym swaps; (2) one call for 10 alternatives "ordered best to worst" anchors candidates 2–10 on candidate 1; (3) the prompt is all brakes and no accelerator — it never *asks* for structural change; (4) phi4-14B retreats to word swaps on 150-word dimension-dense sentences. Official baselines, measured on the 38.5 menus by the new `menu_profile` diversity columns: **p_sim 0.76, d_orig 0.41** (the 2026-08-18 hand assessment's 0.77 / 0.33 was in the same ballpark). Sprint targets: p_sim ≤ 0.55, d_orig ≥ 0.45.

**Design (Sprint 38.6 base):**
- **Rounds × models at temperature 0.8.** Per target, 3 transformation-slotted rounds — R1 voice & frame (active ↔ passive/impersonal «se», nominal ↔ verbal), R2 architecture (clause reorder, split/merge, move the placeholder block), R3 free restructuring with R1/R2 keeps' openings forbidden — × 2 local models (`phi4:latest` + `qwen2.5:14b`), pooled into one CandidateSet. New consumer-above-the-seam module [`menu_diversity.py`](../../src/synthetic/menu_diversity.py) with its own `run`/`replay` CLI and per-model transcript stores `data/synthetic/llm_cache/menu_OEB_tpar_{phi4latest,qwen2514b}`; `proposer_model` provenance in every payload, rendered as a `— _model_` suffix in the review Markdown.
- **Quantity-conservation gate** (`variant_proposer._require_quantities_conserved`, wired into TEMPLATE_PARAPHRASE **and REORDER**): multiset equality of numeric tokens and unit tokens between `original` and `new`. Zero false positives on the 532 existing menu candidates. Applies to reorder replays from now on — a future replay may legitimately drop reorder candidates that alter quantities.
- **Similarity gate** (`menu_proposer._similarity_gate`, token-Jaccard > 0.8 against an already-kept candidate → `near_duplicate_of_kept`): all menu types **except REORDER** — exempt because an order-blind token-set metric would kill every pure reorder; NEW_PARAM candidates are compared on their label+values text.
- **`menu_profile`** gained `dist_orig` / `pair_sim` columns (pair_sim pinned as the mean of per-target mean pairwise Jaccard).
- **`menu_runner --skip-types` guard:** full menu passes must use `--skip-types template_paraphrase` — that type's artefacts are owned by `menu_diversity` from Sprint 38.6 on.

**First pilot (pre-masking, 5 concepts / 10 targets):** 133 candidates, p_sim 0.42 — the diversity mechanism works — but survival on long TEXTO templates was poor: OEB010$ TEXTO kept only 2 survivors. Drop breakdown: 23 `placeholders_not_preserved`, 12 near-duplicates, 9 `quantities_not_conserved`, 3 echoes. All-or-nothing rejection means one corrupt token kills a 150-word rewrite — the motivation for 38.6-B.

**Sprint 38.6-B (same-day addendum — masking + top-up + rescue):**
- **[`template_masking.py`](../../src/synthetic/template_masking.py)** — placeholders and quantities are replaced by opaque sentinels `[[Pn]]`/`[[Qn]]` before prompting and the exact literals restored afterwards, so placeholder/quantity preservation is guaranteed by construction; the full validator stack still runs on the restored text (belt and braces — no gate weakened). **902/902 catalog surfaces round-trip identically.** Hardening (`e06bf97`): `$` excluded from the unit peek so a placeholder following a number can never be swallowed as a pseudo-unit (affected 12 non-OEB surfaces — follow-up F7, resolved same day), plus a `sentinel_residue` guard in the diversity path.
- **Top-up rounds:** a target below `MIN_CANDIDATES = 6` after R1–R3 gets up to `MAX_TOPUP_ROUNDS = 2` extra free-restructure rounds per model.
- **Remask rescue:** the models *self-unmask* — they write `$A` instead of `[[P1]]` because the unmasked `Concepto` line in the prompt shows the real tokens. `remask` forgives a self-unmasked literal when it appears exactly once in the candidate (provably harmless: restoring a remasked text yields the model's own text back). Rescued 40 candidates in simulation over the pilot stores.

**Pilot progression per target (pre-mask / mask / mask+rescue):**

| target | pre-mask | mask | mask + rescue |
|---|---:|---:|---:|
| OEB010$ TEXTO | 2 | 7 | 7 |
| OEB250$ RESUMEN | 12 | 2 | 6 |
| OEB250$ TEXTO | 16 | 3 | 6 |
| OEB020$ TEXTO | 9 | 3 | 3 |
| **all 10 targets** | **133** | **99** | **119** |
| p_sim | 0.42 | 0.45 | 0.45 |

Masking fixed the long-template starvation (OEB010$ TEXTO 2 → 7) but cost survivors where the models self-unmasked (OEB250$); the rescue recovered those without weakening any gate.

**Full run (49 targets, both models, masked + rescue; commit `fa7b7bc`):** **709 candidates, 0 skipped, 0 empty, 0 sentinel leaks, 0 prompt echoes.** Row quoted from [`sprints/SPRINT_386_profile.txt`](sprints/SPRINT_386_profile.txt):

```
type                  tgt empty cands noop  dup uniq/tgt skip drop usages d_orig p_sim
template_paraphrase    49     0   709    0    0     14.5    0  194     50   0.55  0.41
```

- **p_sim 0.41** (target ≤ 0.55; baseline 0.76) and **d_orig 0.55** (target ≥ 0.45; baseline 0.41) — both success gates met with margin. uniq/tgt 14.5 (was 8.3).
- Weakest target: OEB020$ TEXTO with 3 candidates; no target below 3.
- Model balance: phi4 383 / qwen 326 survivors.
- `python -m synthetic.menu_diversity replay …` reproduces both artefact files **byte-identically (sha1-verified)**.
- Wall clock: two phases ≈ **55 min GPU total**. Every other type's profile row is unchanged vs the 38.5 snapshot on the shared columns.

**Environment incident.** The first pilot attempt failed with CUDA OOM. Root cause was not the models but a wedged WSL2 VM (host RAM down to 8.3/64 GB, hung IO); fixed by restarting Docker Desktop/WSL. Adopted **two-phase model loading** to avoid dual-residency on the 24 GB GPU: phase 1 runs `--models phi4:latest` alone, phase 2 runs both models — phase 2 serves phi4's prompts from its transcript store, so only qwen goes live.

- Test suite: `pytest tests/synthetic -q` → **1061 passed, 2 skipped** (was 1016 at sprint start); full `pytest tests -q` → **1085 passed, 2 skipped**. No live LLM call from pytest, as always.

**Follow-ups:**

| # | Item | Status |
|---|---|---|
| F7 | `template_masking` unit peek could swallow a `$` placeholder after a number (12 non-OEB surfaces) | **resolved same day** — `$` excluded from the peek in `e06bf97` (diff verified) |
| F8 | Selective `MAX_TOPUP_ROUNDS = 3` for targets still < 6 candidates | open — only if César wants more on OEB020$ TEXTO |
| F9 | Soften the static "conserva las variables $X" prompt line (reduces self-unmasking) | open — invalidates all tpar caches; bundle with Sprint 40 |

**CLAUDE_SYNTHETIC.md updated:** yes — `menu_diversity.py` + `template_masking.py` file-map rows; `menu_runner.py` / `menu_profile.py` rows extended; sprint-history entry prepended. `STATUS_2026-08-18.md` review guidance updated for the regenerated menu (~1.5–2 h alone; total ~6–7 h).

**Next step:** F3-prep-2-review (César, manual, ~6–7 h) over all 11 menus including the regenerated `template_paraphrase`; then F3-prep-2-parse; then Sprint 39 (F3-prep-3: budgets + sampler + chapter driver).

---

### 2026-08-18 — Sprint 38.5, F3-prep-2-fix (assessment + offline recovery)
**Date:** 2026-08-18
**Sprint file:** [`sprints/SPRINT_385.md`](sprints/SPRINT_385.md)
**Backlog IDs:** F3-prep-2-fix — closed (inserted between Sprint 38 and Sprint 39). F3-prep-2-review (César, manual) + F3-prep-2-parse (Claude, post-review) still open; the review had **not** started, so no ticks were lost.

**Why this sprint exists.** Before handing the Sprint 38 menus over for the 7–9 h manual review, the menus were profiled mechanically. The profile showed the menus were incomplete and skewed in ways that would have wasted review effort — worth a short fix-and-regenerate sprint *before* anyone reads 2 918 lines of Spanish.

**Assessment findings** (`python -m synthetic.menu_profile`; baseline frozen in [`sprints/SPRINT_385_profile_before.txt`](sprints/SPRINT_385_profile_before.txt)):
- **127 template targets silently skipped as `malformed_json: Invalid \escape`, concentrated on TEXTO** — omission 97/115 TEXTO targets, reorder 15/24, template_paraphrase 15/24 (plus a few RESUMEN). Root cause: every raw OEB `texto` template in the stage-2 JSON (`data/intermediate/OBRA CIVIL/OBRA CIVIL.json`) *begins* with `\` and every `resumen` *ends* with `\` — the FIEBDC `\TEXTO\…\` field delimiters that s01 leaves in place (the main pipeline strips them later, but the synthetic prompt builder reads the raw field). phi4 echoes the backslash inside its JSON string (`"original": "\Canalización …"`), which is not a valid JSON escape, so `json.loads` failed and the whole target was skipped. Of the 502 recorded transcripts, 133 carried this defect (369 parsed cleanly).
- **`synonym_label` on digit-bearing values loses the digits** — every candidate on values such as `3 <= i < 5 horas` (→ `Mantenimiento Moderado`) or `1,10 m` (→ `Profunda`) is meaning-changing, not a synonym.
- **`compression` on 2–3-word fragments** has no room to compress: no-ops and junk (`Diurno excepcional → Diurno +E`).
- **Low-entropy types waste the 10-slot menu** — omission's 10 alternatives differ only in a connective (pairwise token-Jaccard 0.86); reorder / num_to_text / unit_* likewise have 2–3 legitimate forms.
- (Reviewer-facing observations recorded for `STATUS_2026-08-18.md`: `expansion` frequently *adds facts* despite the prompt forbidding it; one `unit_conversion` arithmetic error `0,80 m → 8000 mm`; `synonym_label` domain slips such as `Con topo → Topográfico`.)

**Fixes — three surgical changes above the frozen seam, all cache-neutral (no prompt text changed, so every one of the 502 recorded transcripts still hits):**
1. `menu_proposer._parse_json_list` retries `json.loads` after `_repair_invalid_escapes` (drops any backslash that does not open a valid JSON escape; applied only after a strict parse fails, so well-formed responses parse byte-identically). Verified against the cache: **502/502 transcripts parse (was 369/502)**. Commit `c82552d`.
2. `MENU_CAP_BY_TYPE` — post-parse truncation to 3 candidates for omission / reorder / num_to_text / unit_conversion / unit_expansion. The request still asks for `n = 10` (the `{n}` is inside the cache-keyed prompt); only the head of the deduped list is kept, per the prompt's best→worst ordering. Commits `7900cc1`, `a3b04b9`.
3. Targeting gates — `slot_extractor.value_applies` (per-value predicate; `SYNONYM_LABEL` now excludes digit-bearing values, `_axis_applies` delegates to it), `MIN_COMPRESSION_WORDS = 4` in `enumerate_targets`, and `target_scanner._emit_entries` applies the per-value gate. Four Sprint-31 test expectations updated, incl. the real-data synonym_label unique-target count 49 → 34. Commits `8cf2bd9`, `5608bde`.
4. Tooling: `src/synthetic/menu_profile.py` — read-only per-type scorecard over `data/synthetic/menus/*.jsonl` (`python -m synthetic.menu_profile`), so before/after is measurable and Sprint 40 QC can reuse it. Commits `90f0d47`, `7e03731`.

**Regeneration — offline, zero GPU:**
```
python -m synthetic.menu_runner replay --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7 --chapter-label OEB
```
484 calls served from `data/synthetic/llm_cache/menu_OEB/` in **0.2 s, no cache misses** — the proof that no prompt changed (`replay` fails loud on a miss). Scorecard in [`sprints/SPRINT_385_replay_scorecard.txt`](sprints/SPRINT_385_replay_scorecard.txt); profile in [`sprints/SPRINT_385_profile_after.txt`](sprints/SPRINT_385_profile_after.txt). Commit `7658b16`.

**Before → after** (rows quoted from the two profile files; columns `tgt / empty / cands / noop / dup / uniq-per-tgt / skip / drop`):

| type | before | after |
|---|---|---|
| omission | 212 / 100 / 590 / 4 / 0 / 5.3 / 100 / 51 | 212 / **8** / 496 / 3 / 0 / 2.4 / **8** / **119** |
| reorder | 49 / 19 / 215 / 6 / 0 / 7.2 / 19 / 1 | 49 / **5** / 132 / 0 / 0 / 3.0 / **5** / 1 |
| template_paraphrase | 49 / 15 / 286 / 0 / 0 / 8.4 / 15 / 0 | 49 / **0** / 406 / 0 / 0 / 8.3 / **0** / 0 |
| synonym_label | 49 / 6 / 236 / 2 / 0 / 5.5 / 0 / 0 | **34** / 2 / 158 / 2 / 0 / 4.9 / 0 / 0 |
| compression | 46 / 0 / 291 / 4 / 0 / 6.3 / 0 / 0 | **22** / 0 / 107 / 0 / 0 / 4.9 / 0 / 0 |
| num_to_text | 12 / 0 / 105 / 0 / 0 / 8.8 / 0 / 0 | 11 / 0 / 33 / 0 / 0 / 3.0 / 0 / 0 |
| unit_conversion | 14 / 7 / 21 / 0 / 0 / 3.0 / 0 / 0 | 12 / 5 / 18 / 0 / 0 / 2.6 / 0 / 0 |
| unit_expansion | 14 / 2 / 49 / 0 / 0 / 4.1 / 0 / 0 | 12 / 0 / 33 / 0 / 0 / 2.8 / 0 / 0 |
| paraphrase / expansion / new_param | 46 / 46 / 25 targets — 420 / 454 / 251 cands | **byte-identical** |

- TEXTO targets *with candidates*: omission 18 → **110** (of 115), reorder 9 → **23** (of 24), template_paraphrase 9 → **24** (of 24). The residual omission `empty = 8` / reorder `empty = 5` are `all_elements_rejected_by_schema`, not parse failures.
- omission `drop` 51 → 119 is **expected, not a regression**: the recovered TEXTO responses now reach per-element schema validation, so more `placeholders_not_preserved_after_omission` rejections are recorded per element.
- `synonym_label` 49 → 34 targets: the 15 gated values are digit-bearing (`BANDA DE MANTENIMIENTO` hour bands, `DIÁMETRO` mm values, `PROFUNDIDAD` m values, `Nº TUBOS` `1 o 2`). `compression` 46 → 22: fragments under 4 words gated. `num_to_text` 12 → 11 and `unit_conversion` / `unit_expansion` 14 → 12 are a side effect of the scanner now gating *per value* instead of per axis: `Nº TUBOS / 1 o 2` (not numeric) and `BANDA DE MANTENIMIENTO / No aplica`, `No necesita intervalo` (no unit token) were never sensible targets for those types.
- Candidates total **2 918 → 2 508**; review is now complete over all 11 populated types (TEXTO L3 targets present) and shorter (fewer, less redundant candidates on the low-entropy types).
- Test suite: `pytest tests/synthetic -q` → **1014 passed, 2 skipped**; full `pytest tests -q` (incl. `tests/utils`) → **1038 passed, 2 skipped** (Sprint 38's full-suite figure was 1015 / 2). No LLM call was made in this sprint; no prompt text changed.

**Known residue (16 candidate lines in `docs/synthetic/menus/template_paraphrase.md` still contain a literal `\`; verified split 2026-08-18):**
- **10 cosmetic** — all candidates of `TEXTO template (OEB140$)` start with a leading `\`: phi4 double-escaped the FIEBDC delimiter (valid JSON `\\`), so the parser legitimately keeps one backslash. Harmless downstream: `layer_l3` replaces by substring of `original` and s05 strips the delimiter. Reviewers judge the text and ignore the backslash; the prompt-side strip (F1 below) removes it before Sprint 40.
- **6 prompt echoes (since scrubbed)** — all 6 candidates of `TEXTO template (OEB010$)` contained the prompt scaffold itself (`Campo destino: TEXTO Plantilla actual: …`): the concept's trailing FIEBDC `\` reads like a line-continuation, so phi4 absorbed the scaffold lines into the "template" it was rewriting. These passed the placeholder validator (the echo carries every placeholder). A same-day addendum added a scaffold-marker guard to `menu_proposer._validate_variants` (`prompt_scaffold_echo` drop reason) and replayed: the 6 are gone from the menu and the target now shows as skipped (`all_elements_rejected_by_schema`). Only known case of prompt echo in the pilot; further evidence for follow-up F1.

**Gate scope note.** The `compression` (≥ 4 words) and `synonym_label` (digit-free) gates live in `slot_extractor.enumerate_targets` / `_axis_applies`, which is shared with the F1-pilot / `stage_b` path — so `run_synthetic._all_attempts` / `plan_concept_variants` also enumerate fewer `compression` and `synonym_label` targets from now on. Intended, and consistent with the Sprint-31 L1 gate precedent.

**Decisions (see `SPRINT_385.md` D1–D4):** no prompt changes this sprint (would invalidate ~310 L3 prompt hashes → ~60–80 min live phi4 for a fix the parser repair delivers offline); caps are post-parse truncation, not a smaller `n`; `expansion` fact-injection is left to the reviewer; `unit_conversion` / `num_to_text` stay LLM-driven for the pilot.

**Deferred follow-ups (recorded, not done here):**

| # | Item | Why deferred | Where it lands |
|---|---|---|---|
| F1 | Strip FIEBDC `\` from `template`/`concept` slots at prompt-build (`slot_extractor._field_text`, `concept_resumen`) | Changes every prompt hash → full live re-run; only worth it when generating fresh | Sprint 40 pre-task |
| F2 | Deterministic `unit_conversion` (m/cm/mm, h/min) and `num_to_text` (`num2words`-style) instead of LLM | Architecture change in `layer_l1` / prompts | Sprint 39 or 40 |
| F3 | Scale `n` with `len(usages)` for high-fan-out targets | Prompt change; small gain | Sprint 40 |
| F4 | Mechanical `expansion` fact-injection guard | No good heuristic; reviewer gate suffices for the pilot | revisit after review acceptance rates |
| F6 | Abbreviation-only values (`PVC`, `IPN`) still pass `SYNONYM_LABEL` — consider `not _ABBREV_RE.fullmatch(value)` in `value_applies` | Raised in review; left to the reviewer to judge on the pilot menus | after F3-prep-2-review |

**Changes to plan:** none to the sprint sequence — F3-prep-2-review (César) now starts from the regenerated menus; estimated review time ~5–6 h (was 7–9 h). Then F3-prep-2-parse → Sprint 39 (F3-prep-3: budgets + sampler + chapter driver) → Sprint 40 (F3, with F1 landed first).

**CLAUDE_SYNTHETIC.md updated:** yes — `menu_profile.py` file-map row; Sprint History entry prepended; "next" pointer moved to F3-prep-2-review on the regenerated menus. `STATUS_2026-08-18.md` supersedes `STATUS_2026-07-09.md` (old file kept).

**Next step:** F3-prep-2-review (César, manual, ~5–6 h) on `docs/synthetic/menus/*.md` — see the review guidance in `STATUS_2026-08-18.md`. No Claude action needed until the ticks land.

---

### Sprint 38 (cont.) — Phase F Task F3-prep-2-generate (live phi4 menu build on OEB subset)
**Date:** 2026-07-09
**Backlog IDs:** F3-prep-2-generate — closed. F3-prep-2-review (César, manual) + F3-prep-2-parse (Claude, post-review) still open.

**What was done:**
- Ran `python -m synthetic.menu_runner run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7 --chapter-label OEB` against Ollama-served `phi4:latest` at `http://localhost:11434/v1`, `temperature 0`, `BC3CAT_LLM_TIMEOUT=300`. Two prior attempts failed: (i) 2026-07-09 — real OBRA CIVIL data has LIST_plain / LIST_conditional text-variables that `slot_extractor.extract_slots` can't parse; fixed by applying `l2_repr.list_to_formula(include_conditional=True)` in `run_menu` (bug + regression test landed same day, matches `f1_pilot`'s discipline); (ii) 2026-07-09 — default 60 s timeout exhausted on a heavy L1-batched prompt (~350 tokens in, 10 alternatives × axis-values-count tokens out) after 264/636 prompts had already recorded. Two fixes landed together: `BC3CAT_LLM_TIMEOUT=300` (5 min per call) and a new `menu_runner.ResumingRecordingClient` (cache-first wrapper; same on-disk format as `RecordingClient`, so the 264 recorded transcripts resumed automatically without re-hitting the model). Third attempt completed cleanly. 12+3 regression tests total from these two fixes; the `RecordingClient`-compatible on-disk format keeps replay tooling unchanged. Store lives at `data/synthetic/llm_cache/menu_OEB/` (502 prompts, offline-replayable forever).

**Live scorecard (5528 s wall-clock ≈ 92 min, 25 OEB concepts, 562 unique targets, 636 phi4 calls after cache resume):**

| Rewrite type | Targets | LLM calls | Generated | Skipped | Total candidates | Dropped |
|---|---:|---:|---:|---:|---:|---:|
| synonym_label | 49 | 16 | 43 | 6 | 236 | 0 |
| num_to_text | 12 | 3 | 12 | 0 | 105 | 0 |
| unit_conversion | 14 | 5 | 7 | 7 | 21 | 0 |
| unit_expansion | 14 | 5 | 12 | 2 | 49 | 0 |
| abbrev_expansion | 0 | 0 | 0 | 0 | 0 | 0 |
| code_expansion | 0 | 0 | 0 | 0 | 0 | 0 |
| paraphrase | 46 | 46 | 46 | 0 | 420 | 0 |
| expansion | 46 | 46 | 46 | 0 | 454 | 0 |
| compression | 46 | 46 | 46 | 0 | 291 | 0 |
| omission | 212 | 312 | 112 | 100 | 590 | 51 |
| reorder | 49 | 68 | 30 | 19 | 215 | 1 |
| template_paraphrase | 49 | 64 | 34 | 15 | 286 | 0 |
| new_param | 25 | 25 | 25 | 0 | 251 | 0 |
| **TOTAL** | **562** | **636** | **413** | **149** | **2 918** | **52** |

**Empirical observations (mechanical only — Spanish quality is F3-prep-2-review's judgement):**
- **L1 batching saved calls.** 89 L1 targets (SYNONYM_LABEL + NUM_TO_TEXT + UNIT_CONVERSION + UNIT_EXPANSION) were served by only 29 LLM calls thanks to per-axis batching. Sprint 37's design point held on real data.
- **L2 (paraphrase / expansion / compression) at 100 % generation rate** — 138 targets, 138 generated, 0 skipped, 0 dropped. Best per-type reliability of the run.
- **NEW_PARAM at 100 %** with a mean of ~10 candidates per concept (phi4 emits the full N=10).
- **OMISSION had the highest skip rate (100/212, 47 %)** and the only meaningful `dropped_candidates` count (51 elements dropped as schema-invalid). The variant proposer's `_require_placeholders_omitted` guard is doing its job — phi4 sometimes returns `new` fields where the wrong placeholders were dropped or none were.
- **UNIT_CONVERSION at 50 % (7/14)** — half of the axes phi4 was asked to unit-convert didn't produce valid output. Manual review will judge which is signal vs. noise (a numeric axis with no obvious unit convention is a legitimate skip).
- **Dedup was massive on the workhorse axes.** `BANDA DE MANTENIMIENTO / i >= 5 horas` reviewed **once** for 21 concepts; `TRABAJO / Diurno` shared 20 concepts (as measured Sprint 37). Reviewer effort scales with unique targets, not concept count.
- **The 636 LLM calls figure = live phi4 hits from the second (resuming) launch only.** True cost across the two attempts was ~900 calls (264 first-attempt + 636 second-attempt); the recorded store contains 502 unique prompts (many second-attempt calls are cache hits from the first).

**Artefacts on disk:**
- `data/synthetic/menus/{mtype}.jsonl` — 11 files (2 zero-target types have no output): compression, expansion, new_param, num_to_text, omission, paraphrase, reorder, synonym_label, template_paraphrase, unit_conversion, unit_expansion.
- `docs/synthetic/menus/{mtype}.md` — 11 corresponding human-review Markdown files.
- `data/synthetic/llm_cache/menu_OEB/` — 502 recorded `{sha256(prompt)}.json` transcripts. Any subsequent `python -m synthetic.menu_runner replay …` is offline and free.

**Decisions / rationale (2026-07-09):**
- **`ResumingRecordingClient` lives in `menu_runner` for now, not `llm_client`.** Sprint 38's acceptance forbids seam edits. If this cache-first pattern turns out broadly useful across other drivers (`spike.py`, `f1_pilot.py`), a follow-up sprint hoists it into `llm_client` — a strictly additive edit at that point.
- **`BC3CAT_LLM_TIMEOUT=300` is the recommended default for phi4 at N=10.** Committed via env var this run; a follow-up may pin it in `utils.config`. 60 s is fine for lightweight `f1_pilot`-style single-response prompts; 300 s covers L1-batched list-of-10 responses on axes with 8 values.

**Problems encountered:**
- **Two crashes before third-time success**, both real bugs uncovered by real data — the exact reason F3-prep-2 exists as a landmark. Fix + regression test landed for each.

**Changes to plan:**
- **F3-prep-2 continues to F3-prep-2-review** (César, manual). ~5 600 candidate lines across 11 Markdown files; the reject-by-default review contract is `- [x]` = approve, everything else = reject. When done, `python -m synthetic.menu_review_parser parse` translates ticks into `data/synthetic/menus/verdicts/` for Sprint 39's sampler.

**CLAUDE_SYNTHETIC.md updated:** yes — Sprint History appended; `menu_runner.py` file-map row now notes `ResumingRecordingClient` + the timeout observation.

**Next step:** F3-prep-2-review (César, manual). No Claude action needed until the ticks land.

---

### Sprint 38 — Phase F Task F3-prep-2-code (menu builder: live driver + review parser)
**Date:** 2026-07-09
**Sprint file:** [`sprints/SPRINT_38.md`](sprints/SPRINT_38.md)
**Backlog IDs:** F3-prep-2-code (Claude: driver CLI + review parser, hermetic — this entry). F3-prep-2-generate (live phi4 pass) + F3-prep-2-review (César, manual) + F3-prep-2-parse (Claude, post-review) still open — subsequent RESEARCH_LOG entries will land at each landmark.

**Context.** Sprint 37 shipped the frozen library trio (`target_scanner` + `menu_proposer` + `menu_artefacts`). Sprint 38's *code* half builds the two runnable pieces around it — the CLI driver that composes the trio against a live `HttpLLMClient` + `RecordingClient`, and the parser that reads César's ticked Markdown back into structured verdict JSONL for the Sprint 39 sampler. Hermetic: no live LLM in the suite.

**What was done:**
- **[`src/synthetic/menu_runner.py`](../../src/synthetic/menu_runner.py)** — consumer above the frozen seam (sibling of `spike.py`/`f1_pilot.py`). `MenuRun` + `TypeStat` frozen dataclasses (per-modification-type slice: n_targets, n_llm_calls, n_generated_targets, n_skipped_targets, n_total_candidates, n_dropped_candidates); `run_menu(stage_json, *, concept_filter, n, client, chapter_label, out_dir_machine, out_dir_review, clock) -> MenuRun` composes `target_scanner.scan_chapter → menu_proposer.propose_type (per mtype) → menu_artefacts.write_menu`; `default_client(chapter_label, replay=False)` wires `RecordingClient(HttpLLMClient(LLMConfig.from_env()), store)` for live and `ReplayClient(store)` for offline replay; `default_store_dir` / `default_out_machine_dir` / `default_out_review_dir` per `utils.config`; internal `_CountingClient` attributes LLM calls per rewrite type without touching the client interface; `format_scorecard(run)` emits a Markdown-table generation report for `RESEARCH_LOG.md`; `main(argv)` with `run` (live) / `replay` (offline) subcommands (args: `--stage-json` `--concept-filter` `--n` `--chapter-label` `--seed` `--out-machine` `--out-review` `--llm-cache`). Imports `target_scanner`/`menu_proposer`/`menu_artefacts`/`llm_client`/`taxonomy`/`utils.config` + stdlib.
- **[`src/synthetic/menu_review_parser.py`](../../src/synthetic/menu_review_parser.py)** — reads ticked Markdown menus into structured verdict JSONL. `MenuVerdict` + `CandidateVerdict` + `ParseReport` + `TypeParseStat` frozen dataclasses; `ParseError` distinguishes structural drift from review verdicts; regex-based Markdown scan (`_HEADING_RE`, `_TICK_RE = r"^- \[([ xX])\] (\d+)\. "`); `parse_review_file(md_path, jsonl_path) -> tuple[MenuVerdict, ...]` treats the machine JSONL as the source of truth for target order + canonical text + candidate count, joins Markdown ticks by target order + candidate index, fail-loud on heading-count mismatch / canonical drift / out-of-range tick index; `write_verdicts(verdicts, out_path)` atomic JSONL; `read_verdicts(path)` round-trip; `parse_all(machine_dir, review_dir, out_dir) -> ParseReport` sweeps every rewrite type, falls back to *reject-all* when the review file is missing (unreviewed type still emits verdicts for downstream contract stability, never fabricates approvals); `format_parse_report` coverage-summary Markdown table; `main(argv)` with `parse` subcommand. Imports `menu_runner` (for default paths) + `taxonomy` + `utils.config` + stdlib only; never any forbidden seam.
- **[`tests/synthetic/test_menu_runner.py`](../../tests/synthetic/test_menu_runner.py) + [`test_menu_review_parser.py`](../../tests/synthetic/test_menu_review_parser.py)** — 25 hermetic tests total across `TestRunMenu` (end-to-end over the tiny fixture, per-type TypeStat accounting, malformed-then-skipped counts, empty type bypasses LLM entirely), `TestFormatScorecard`, `TestParseReviewFileHappy` (case-insensitive ticks, no-ticks-all-rejected, all-ticks-all-approved, deleted-line-defaults-to-reject, skipped-target-preserves-reason), `TestParseReviewFileErrors` (heading count mismatch, canonical drift, out-of-range tick), `TestVerdictIO` (atomic round-trip), `TestParseAll` (paired sweep, missing-review-fallback-to-reject-all, missing-machine-file-skipped), `TestFormatParseReport`, and `TestBoundaries` (AST import audit both directions, both modules).

**Key results:**
- `pytest tests -q` → **1015 passed, 2 skipped** (Sprint 37 baseline 990 + 25 new). Zero regressions, zero sockets, zero new third-party dependency.
- **Zero seam edits.** `git diff -- src/synthetic/{variant_proposer,run_synthetic,slot_extractor,layer_l1,layer_l2,layer_l3,layer_pd,mutator,stage_b,metadata,review,packaging,loaders,l2_repr,llm_client,f1_pilot,spike}.py src/synthetic/prompts src/synthetic/{target_scanner,menu_proposer,menu_artefacts}.py` → empty. Sprint 37's frozen library trio is untouched; the driver + parser compose it from above.
- **New file count:** `menu_runner.py`, `menu_review_parser.py`, `test_menu_runner.py`, `test_menu_review_parser.py`, `SPRINT_38.md` — 5 files.

**Decisions / rationale (2026-07-09):**
- **Separate `menu_runner.py` instead of a `main` on `menu_proposer.py`.** A `main` in `menu_proposer` would need to import `menu_artefacts` (currently only imported *by* it) — creating an import cycle — and would blur the library-vs-driver boundary. The runner is a `spike.py` / `f1_pilot.py` sibling: consumer above the orchestrator, one CLI, `RecordingClient` bracketing the live call. `menu_proposer` stays a pure library.
- **Machine JSONL is the source of truth; Markdown is human input.** The parser reads target order + canonical text + candidate count from the JSONL. Markdown contributes only ticks. Any structural mismatch is a fail-loud `ParseError` — the reviewer can't silently overwrite the wrong target by typo'ing a heading.
- **Reject-by-default review contract.** Anything not `- [x]` (case-insensitive) rejects. Missing tick line, deleted candidate, unreviewed file — all reject. Simpler parser, no ambiguous "not reviewed" state. Coverage-summary output makes zero-approval rewrite types visible so partial reviews aren't hidden.
- **`parse_all` handles missing review files with reject-all fallback** rather than skipping the rewrite type. Downstream (Sprint 39 sampler) always sees a verdict JSONL per populated rewrite type, so its contract stays clean whether César reviewed 3 types or all 13.
- **`_CountingClient` inside `run_menu` attributes LLM calls per rewrite type** without changing the client interface or leaking a counter into `llm_client`. Cheap, local, not exported.

**Problems encountered:**
- **Empty-type test misjudged the fixture:** initially picked `ABBREV_EXPANSION` as the "expected empty" type on the tiny fixture, but `MATERIAL` axis (PVC/HDPE) triggers the abbrev applicability gate → 2 targets. Fixed by picking `UNIT_CONVERSION` (the tiny fixture has no unit tokens) as the empty-by-fixture case.

**Changes to plan:**
- **F3-prep-2 continues with the live+manual halves.** Next Claude landmark is F3-prep-2-generate — invoke `python -m synthetic.menu_runner run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7 --chapter-label OEB` against `phi4:latest` (Ollama), capture the scorecard, commit the 13 Markdown menus into the branch. Then F3-prep-2-review (César, manual) → F3-prep-2-parse (Claude, post-review) → `RESEARCH_LOG.md` coverage-summary entry → Sprint 39 (F3-prep-3: budgets + sampler + chapter driver).

**CLAUDE_SYNTHETIC.md updated:** yes — new rows for `menu_runner.py` and `menu_review_parser.py` in the file map; Sprint History entry prepended.

**Next step:** F3-prep-2-generate (live phi4, Claude-runnable). Estimated wall-clock: ~2-3 h on `phi4:latest` for the OEB subset at N=10 (562 unique targets across the 13 rewrite types after Sprint 34's applicability gate + Sprint 26's `l2_repr` conversion; L1's per-axis batching means far fewer LLM calls than that number suggests). Recorded transcripts make every subsequent replay offline and free.

---

### Sprint 37 — Phase F Task F3-prep-1 (menu builder: dedup-first target scan + N-candidate proposer + human-review artefact)
**Date:** 2026-07-08
**Sprint file:** [`sprints/SPRINT_37.md`](sprints/SPRINT_37.md)
**Backlog IDs:** F3-prep-1 (new F3 split — the *runnable, hermetic* menu builder). F3-prep-2 (live run + manual review) and F3-prep-3 (variant budgets + sampler + chapter driver) still open.

**Context (why the pipeline pivoted):** F1-review verdict on `phi4:latest` closed at ≥90 % clean across three concepts (see Sprints 34–36), and F3 (full-catalog generation) was the natural next step. Before running at chapter scale César raised a stronger quality gate: instead of accepting phi4's single per-target rewrite and reviewing a sample of *rendered* items, ask phi4 for **N=10 candidates per target**, review the whole menu by hand, and sample the final corpus from surviving candidates only. Menu-first review + variant sampling replaces the previous "generate → materialize → review a sample" flow at the head of Phase F.

**Preflight measurement (2026-07-08 scratchpad `dedup_scan.py`, OEB subset, 25 concept groups):**

| Rewrite family | Total (pre-dedup) | Unique | Savings |
|---|---:|---:|---:|
| L1 (per axis-value)   | 459 each type | 67 each | **85 %** |
| L2 (per fragment)     | 306 each type | 33 each | **89 %** |
| L3 (per template)     | 50 each type  | 49 each | 2 % |
| new_param             | 25            | 25      | 0 % |
| **All families**      | **3 847**     | **673** | **83 %** |

Workhorse axes drive the L1 saving: `TRABAJO/Diurno` and `TRABAJO/Nocturno` each appear in 20 of 25 concepts, `BANDA DE MANTENIMIENTO` values in 19–21, `CONDICIONES DE EJECUCIÓN` values in 24. Review effort collapses from ~38 000 candidate lines (no dedup) to ~6 700 (~7–9 h manual). That is the effort budget this sprint enables.

**What was done:**
- **[`src/synthetic/target_scanner.py`](../../src/synthetic/target_scanner.py)** — `ChapterInventory` + `UniqueTarget` + `TargetUsage` frozen dataclasses + `scan_chapter(stage_json, *, concept_filter=None, apply_l2_conversion=True) -> ChapterInventory`. Dedup keys per family (L1 `(axis_label, value)`, L2 fragment-text-only, L3 `(field, template[, var_token])`, PD per concept). Whitespace-normalised, case-preserving (accents matter). Deterministic ordering (sorted by dedup_key, usages sorted by concept_key). Imports `slot_extractor` + `l2_repr` + `taxonomy` + stdlib only.
- **[`src/synthetic/menu_proposer.py`](../../src/synthetic/menu_proposer.py)** — `DEFAULT_N_CANDIDATES = 10`, `CandidateProposal`, `CandidateSet`, `propose_type(stage_json, inventory, mtype, client, *, n) -> dict[dedup_key, CandidateSet]`. **Batches at prompt granularity:** one LLM call per axis for L1 (response decomposed into per-value CandidateSets); one call per target for L2 / L3 / NEW_PARAM. Multi-candidate wrapper appended at runtime — `"Devuelve una lista JSON de {n} alternativas … No repitas alternativas."` — the 13 prompt files stay byte-identical. List-level parse tolerates fence-wrapped output (reuses `llm_proposer._FENCE_RE`); per-element schema validation via the existing `variant_proposer._validate_payload` (per-item drops only the offender); inter-candidate dedup (casefold + whitespace) collapses near-duplicates. Whole-target skip on `malformed_list_after_retry:` — distinct prefix from C2's per-item shape.
- **[`src/synthetic/menu_artefacts.py`](../../src/synthetic/menu_artefacts.py)** — `write_menu(inventory, sets_by_type, *, machine_dir, review_dir, chapter_label) -> tuple[WriteReport, ...]`. Writes **two files per rewrite type from one call**: machine-readable JSONL under `data/synthetic/menus/{mtype}.jsonl` (one line per target with `approved: null` slots for Sprint 38's parser to flip), and human-review Markdown under `docs/synthetic/menus/{mtype}.md` (one `##` heading per target, `_Used in N concept(s): …_` + numbered `- [ ]` checkboxes, up to `n` per target; skipped targets show `_Skipped: <reason>_`). Atomic `.tmp` + `os.replace` on every write. Deterministic ordering.
- **[`tests/synthetic/test_menu_builder.py`](../../tests/synthetic/test_menu_builder.py)** — 39 hermetic tests + `tests/synthetic/fixtures/menu_builder/tiny_chapter.json` (3-concept fixture). Classes: `TestScanChapter` (dedup semantics per family, gate interaction with L1, usages tracking, determinism), `TestProposeType` (L1 batching one-call-per-axis, L2/L3 one-call-per-target, inter-candidate dedup, per-item schema-fail drops only offender, malformed-list-after-retry skip, prompt-wrapper text pin, fence-wrapped response recovery), `TestWriteMenu` (both files produced, JSONL round-trip, Markdown checkbox format, atomic write, deterministic bytes, skipped-target visible in review file), `TestBoundaries` (AST-based import audit — no seam module imports the new trio; the new trio imports no forbidden seam module), and `TestObraCivilDedup` (real OBRA CIVIL stage-2 scan, pinned per-family counts on OEB subset).

**Key results:**
- `pytest tests -q` → **990 passed, 2 skipped** (Sprint 36 baseline 951 + 39 new; zero regressions; zero sockets).
- **Empirical dedup on real OBRA CIVIL** (integration test `TestObraCivilDedup`, gate + `l2_repr.list_to_formula(include_conditional=True)` applied):

  | Type | Unique targets (25 OEB concepts) |
  |---|---:|
  | synonym_label | **49** (pre-gate upper bound 67; Sprint 34 gate drops all-numeric axes) |
  | num_to_text | 12 |
  | unit_conversion | 14 |
  | unit_expansion | 14 |
  | abbrev/code_expansion | 0 (no OEB axis carries an uppercase abbreviation on the concept-level) |
  | paraphrase / expansion / compression | **46 each** (l2_repr converts LIST_plain / LIST_conditional so all three text-var shapes enumerate) |
  | omission | 212 (per-`(field, template, var_token)`) |
  | reorder / template_paraphrase | 49 each |
  | new_param | 25 |
  | **TOTAL** | **562 unique targets** |

  The 562 is lower than the 673 preflight because the preflight didn't apply the Sprint 34 applicability gate. `TRABAJO/Diurno` still shares 20 of 25 concepts (workhorse-axis insight confirmed).
- Seam untouched: `git diff -- src/synthetic/{variant_proposer,run_synthetic,slot_extractor,layer_l1,layer_l2,layer_l3,layer_pd,mutator,stage_b,metadata,review,packaging,loaders,l2_repr,llm_client,f1_pilot,spike}.py src/synthetic/prompts` shows no Sprint-37 edits (pre-existing modifications to `mutator.py` / `taxonomy.py` etc. are Sprint 32–36 territory carried over from before the sprint).
- No new third-party dependency. `menu_proposer` reuses `variant_proposer._validate_payload` + `_render_prompt` (both C3 primitives) and `llm_proposer._extract_json_object` / `_FENCE_RE` (C2 primitives). `target_scanner` reuses `slot_extractor.enumerate_targets` + `l2_repr.list_to_formula`.

**Decisions / rationale (2026-07-08):**
- **Dedup key for L2 is fragment-text alone.** Two concepts using the same Spanish phrase share the same approved rewrite. The measurement top-15 (`Volumen relevante` in 24 of 25 concepts) shows the workhorse fragments really are the same wording. If a specific case blows up in Sprint 38 we add a per-usage override — reactive, not preemptive.
- **L1 batching by axis is a genuine efficiency win** (~½ the LLM calls) that costs nothing at review time — the human still reviews per-value. Cleaner alternative would be a per-value prompt but that requires editing the 13 prompt files. Not this sprint.
- **Multi-candidate wrapper is a runtime f-string, not a prompt-file edit.** Preserves every Sprint 32–36 prompt pin. If we ever revert to single-candidate mode we delete one f-string.
- **`propose_candidates` per-target isn't the exported API — `propose_type` per-inventory is.** Because L1 requires axis-batching, exposing per-target would either duplicate LLM calls or hide the batching. `propose_type` returns `dict[dedup_key, CandidateSet]` directly.
- **Markdown ticks are the review contract.** GitHub renders `- [ ]` / `- [x]`, VS Code toggles on click, `grep '\[x\]'` works. Sprint 38 defines the reader-back-into-verdicts parser.

**Problems encountered:**
- **First-usage aliasing bug in L1 batching (caught by test):** initial `_group_l1_targets_by_axis` keyed groups on the full `TargetUsage` object (which carries a per-value `display` string), so each (axis, value) pair became its own batch and each LLM call after the first got the wrong queued response. Fixed by keying on `(axis_label, first_usage.concept_key, first_usage.slot_extractor_target_id)` — batches now share the call as intended (verified by `test_l1_batched_one_call_per_axis`).
- **Loose substring check in the boundary test caught a false positive** — `"review" in source` matched the docstring word *"reviews"*. Rewrote to AST-parse imports and check only actual import target names.
- **Preflight-vs-gate-vs-l2_repr count divergence** discovered during the integration test: preflight said 67 unique L1 targets, 33 unique L2 fragments; with Sprint 34's applicability gate + Sprint 26's `l2_repr.list_to_formula(include_conditional=True)` the real numbers are 49 and 46. The gate is stricter (skips all-numeric axes for synonym_label); `l2_repr` catches LIST_plain / LIST_conditional shapes the preflight regex didn't. Integration test now pins the empirically-observed numbers with an explanatory comment; the sprint doc still cites 67 / 33 as the pre-gate / pre-l2_repr upper bound.

**Changes to plan:**
- **F3 split into F3-prep-1 / F3-prep-2 / F3-prep-3** in the protocol. This sprint closes F3-prep-1.
- **F3-prep-2 (Sprint 38) — live phi4 pass + manual review.** Point the menu builder at OBRA CIVIL OEB subset via `phi4:latest` + `RecordingClient`; produce the actual menu on disk; César reviews the Markdown ticks; a new `menu_review_parser.py` reads the state back into `Verdict` records.
- **F3-prep-3 (Sprint 39) — variant budgets + sampler + chapter driver.** `configs/synthetic/variant_budgets.yaml` (flat 50 per concept, per César's 2026-07-08 decision), the deterministic sampler that draws N variants per concept from the approved menu, and the chapter driver that iterates concept keys. Then F3-run.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped `target_scanner.py` / `menu_proposer.py` / `menu_artefacts.py` rows in the file map to ✅; added `menu_review_parser.py` (Sprint 38) and the config files (Sprint 39) as ❌. Sprint History entry prepended.

**Next step:** Draft `sprints/SPRINT_38.md` for F3-prep-2. Ollama serves `phi4:latest`; `python -m synthetic.menu_proposer run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7` produces the two files per rewrite type; César reviews; `menu_review_parser` translates the ticks back into structured verdicts under `data/synthetic/menus/verdicts/{mtype}.jsonl`.

---

### Sprint 36 — Phase F Task F2f (taxonomy extension: `template_paraphrase` — full-surface paraphrase of the RESUMEN or TEXTO)
**Date:** 2026-07-05
**Sprint reference:** Sprint 35 review question ("are we paraphrasing the templates themselves?"). Answer at the time was *no* — the pipeline only touched fragments and parameter values, leaving 80 %+ of the surface text fixed. That was a real scope limit for a benchmark whose §1.1 motivating example is real-world query drift against a stable catalog. This sprint adds the 13th modification type.

**What was done:**
- **Taxonomy** — added `ModificationType.TEMPLATE_PARAPHRASE` in [`taxonomy.py`](../../src/synthetic/taxonomy.py) with `Layer.TEMPLATE`. All existing tests that iterate `ModificationType` picked it up.
- **Mutator** — new `apply_template_paraphrase` in [`layer_l3.py`](../../src/synthetic/layer_l3.py). Reuses `_replace_substring` — the paraphrase replaces the whole field's template, which is a full-string substring match. Same rule shape as reorder/omission: `{field: "RESUMEN"|"TEXTO", original, new}`.
- **Prompt** — new [`prompts/template_paraphrase.txt`](../../src/synthetic/prompts/template_paraphrase.txt). Slots: `{concept}`, `{field}`, `{template}`, `{placeholders}`. Instructions: rewrite the template with alternative vocabulary and phrasing, preserve technical accuracy, preserve ALL `$var` / `$var(%axis)` tokens verbatim, keep the length within [0.75×, 1.5×] of the original.
- **Slot extractor** — `enumerate_targets` and `extract_slots` for TEMPLATE_PARAPHRASE, per-field like OMISSION/REORDER. The `placeholders` slot emits the exhaustive sorted set of `$VAR` and `$VAR(%AXIS)` tokens found in the target field so the prompt can enforce preservation explicitly.
- **Variant proposer** — `EXPECTED_SLOTS[TEMPLATE_PARAPHRASE]` = the four-slot canonical set; validation branch reuses `_validate_original_new_preserves` + `_require_placeholders_preserved` (already proven for reorder in Sprint 29). No new validator code needed.
- **Rule emitter** — new `_emit_l3_template_paraphrase` in [`rule_emitter.py`](../../src/synthetic/rule_emitter.py), same rule shape as reorder.
- **Dispatcher** — added TEMPLATE_PARAPHRASE to `_DISPATCH` in [`mutator.py`](../../src/synthetic/mutator.py).
- **Tests** — every hard-coded "12 modification types" / "17 conditions" count updated to 13 / 18 across `test_taxonomy`, `test_mutator`, `test_prompts`, `test_run_synthetic`, `test_spike`, `test_f1_pilot`. `test_variant_proposer` gains a `_TEMPLATE_PARAPHRASE_TEMPLATE` / `_TEMPLATE_PARAPHRASE_SLOTS` / payload entry so the type-parametrised happy-path and schema-violation tests cover the new type. `_stage_minimal` fixture in `test_run_synthetic` now yields 3 attempts (reorder RESUMEN + template_paraphrase RESUMEN + new_param) instead of 2. `pytest tests -q` → **951 passed, 2 skipped** (Sprint 35's 933 + 18 delta from the test updates). Zero regressions, still hermetic.

**Live re-run — `phi4:latest`, `OEB070$`, seed 7, all Sprint 32–36 code + prompts:**

`BC3CAT_LLM_MODEL=phi4:latest PYTHONPATH="src" python -m synthetic.f1_pilot run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept "OEB070$" --seed 7`

| metric | Sprint 34 | **Sprint 36** |
|---|---:|---:|
| conditions | 17 | **18** |
| generated | 45 | **47** |
| malformed | 7 | 7 |
| schema_fail | 0 | **0** |
| items | 5 616 | **5 904** |
| coverage | 1.0 | 1.0 |

Both `single_L3_template_paraphrase` variants generated successfully (one on RESUMEN, one on TEXTO). Every `$var` / `$var(%axis)` token survived the paraphrase — the reused Sprint 29 placeholder-preservation guard did its job.

Concrete example (variant `single_L3_template_paraphrase_84d940edaf`, RESUMEN):

**Before:** `Suministro y ejecución de canalización de $A tubo(s) de polietileno 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))`

**After:** `Provisión y colocación de $A conducto(s) de polietileno de diámetro nominal 110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))`

Every technical detail preserved (110 mm, 5 At., topo bajo vías, all four placeholders in original positions). Only the vocabulary and phrasing changed (`Suministro y ejecución de canalización` → `Provisión y colocación`, `tubo(s)` → `conducto(s)`, `110 mm` → `de diámetro nominal 110 mm`).

Rendered surface for leaf `OEB070aaaa` (RESUMEN variant):
- **resumen:** `Provisión y colocación de 1 conducto(s) de polietileno de diámetro nominal 110 mm 5 At. con topo bajo vías (Diurno/i >==5 horas/Volumen relevante)`
- **texto:** (unchanged) `Suministro y ejecución de canalización de 1 tubo(s) de polietileno 110 mm 5 At. con topo bajo vías. Trabajo: Diurno Banda de mantenimiento: i >= 5 horas Condiciones de ejecución: Volumen relevante`

TEXTO variant (`single_L3_template_paraphrase_2dc1e93232`) is symmetric: texto rewritten, resumen unchanged — the document-varying / query-stable pair.

Full digest: [`F1_PILOT_REVIEW_DIGEST_PHI4_SPRINT36.md`](F1_PILOT_REVIEW_DIGEST_PHI4_SPRINT36.md).

**Decisions / rationale (2026-07-05):**
- **Two variants per concept — one per surface, always independent.** This directly addresses the proposal §6 "Query-side variability" future-work item without a new sub-project: modifying only RESUMEN gives query-drift-against-stable-catalog; modifying only TEXTO gives document-drift-against-stable-query. Both slices are directly enumerable via the digest's `field` metadata.
- **No collision guard needed for template_paraphrase.** The failure mode we prevented on L1/L2 (collapsing two values onto the same string) doesn't apply to templates — the template is a single string, not a family of values sharing an axis. Placeholder-preservation is the only structural invariant.
- **`{placeholders}` slot lists tokens explicitly instead of relying on the LLM to identify them from the template text.** phi4 handled this cleanly on the first try (0 corruptions out of 2 attempts), but the explicit list is defence-in-depth for weaker models.

**Named residuals:**
- Only 2 template_paraphrase variants get generated per concept (one per non-empty field). If we want more diversity, we could sample `stack_depth > 1` on template_paraphrase to produce alternative paraphrases of the same field. Deferred — the current 2/concept is enough for F3's benchmark scale.
- The placeholder-preservation guard uses set equality on `$VAR` / `$VAR(%AXIS)` tokens. If phi4 duplicates a token (e.g. two `$A` where there was one), the check still passes because the set is unchanged. Duplicated-token rewrites would render broken surfaces at rerun time. On this run zero duplicates occurred; if it becomes an issue we'd tighten the guard to a multiset. Deferred.

**What changed in the plan:** F2f closed. The taxonomy is now the 13-type set that matches the proposal's §1.1 motivating case for real-world phrasing variability. F3 (full-catalog generation) is now the natural next task, running against the full 18-condition set.

**Next step:** **F3 preparation** — chapter-driver wrapper that iterates the concept-key list of a stage-2 file, plus the archive/budget plan. Sprint 35's numbers scale linearly with concept complexity; a ~30-concept chapter at OEB020 complexity fits in an hour or two of phi4 latency.

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; the 13-type taxonomy is now the source of truth in `taxonomy.py`, pinned by every test that iterates `ModificationType`).

---

### Sprint 35 — Phase F Task F2e (multi-concept sanity check: run the F1 pipeline on OEB020 and OEB050 with phi4 + all Sprint 32–34 code and prompts)
**Date:** 2026-07-05
**Sprint reference:** Sprint 30 §6.2 assumed the twin-representation pattern generalises catalog-wide and skipped a dedicated per-concept audit. This sprint verifies that assumption on two additional concepts before committing to F3 (full-catalog generation).

**Concept selection.** `OEB020$` = the most complex concept in the chapter (5 axes with up to 8 values each, 9 text-variables mixing all three shapes — LIST_plain / STR_formula / LIST_conditional; twin map {G↔C, H↔D, J↔F} plus bare-referenced $I, $K, $N in the templates). `OEB050$` = the simplest (3 axes, 1 text-variable, single twin $L↔C). Together with the pilot's `OEB070$` they bracket the range of shapes in the OBRA CIVIL chapter.

**Runs (phi4:latest, seed 7, all Sprint 32–34 code + prompts).**

| concept | generated | skipped | malformed | schema_fail | items | coverage |
|---|---:|---:|---:|---:|---:|---:|
| OEB020$ | **112** | 22 | 9 | **0** | 479 232 | 1.0 |
| OEB050$ | 23 | 13 | 0 | 1 | 234 | 1.0 |
| OEB070$ (Sprint 34 baseline) | 45 | 14 | 7 | 0 | 5 616 | 1.0 |

Coverage 100 % across the board; zero collisions flagged by the guard on any of the three concepts.

**Semantic quality (primary modifications, excluding paired duplicates and legitimate long-form L3 template rewrites).**

| concept | primary applied | clean | verbose (content types) | bare-`%X` | collision skips |
|---|---:|---:|---:|---:|---:|
| **OEB020$** | 142 | **142 (100 %)** | 0 | 0 | 0 |
| **OEB050$** | 35 | **35 (100 %)** | 0 | 0 | 0 |
| OEB070$ | 67 | 60 (90 %) | 7¹ | 0 | 0 |

¹ The 7 "verbose" OEB070 entries are all L3 omission / reorder (legitimate template rewrites, not content-type failures). Under the same definition, OEB020 has 0 and OEB050 has 0.

**Cross-concept quality is at least as good as the pilot.** On OEB020's 8-value axis B (TIPO DE TERRENO), phi4 produced 8 distinct labels (`Normal → Terreno estándar`, `Bajo vías → Terreno bajo vías`, `Rocoso → Terreno rocoso`, `Cruce de carretera → Terreno de cruce`, `Andén → Terreno de andén`, `Adosada → Terreno adosado`, `Vía embarrado → Terreno de vía embarrada`, `En balasto → Terreno con balasto`) — zero collisions on the concept's biggest collision surface. Every 6-value TRABAJO axis rewrite preserves `Excepcional` (`Diurno Excepcional → Horario Diurno Especial`, `Nocturno Excepcional → Horario Nocturno Especial`). L2 compressions like `en cualquier clase de terreno, excepto roca → en cualquier terreno, no roca` (8 → 5 words) and expansions like `bajo vías → bajo vías, instalada en el subsuelo directamente debajo de las vías férreas para proteger y gestionar el drenaje…` are clean and focused on the fragment.

**One small residual on OEB020:** 5 of 133 applied primary mods (~4 %) are identity outputs — `X → X` — concentrated in compression (4) and paraphrase (1). Cases like `en andén → en andén` where the fragment is already too short for phi4 to meaningfully shorten. Not a Stage-D failure (they render as the original, still valid) but wasted budget. Could be flagged by a post-write "must differ from original" check — deferred as a nice-to-have.

**Structural finding — twin representation shape varies but the mutator handles all shapes cleanly.**
- `OEB050$` — single indexed twin $L↔C. Only L2 target set is the three fragments of $L. Paired L1↔L2 fires on every axis-C mod.
- `OEB070$` — three indexed twins ($L↔B, $M↔C, $N↔D). Paired mutation active on axes B/C/D.
- `OEB020$` — three indexed twins ($G↔C, $H↔D, $J↔F) *plus* three bare-referenced formula vars ($I, $K, $N) — the pipeline's `l2_repr.list_to_formula` / `formula_to_list` converters and the seam's `is_str` vs `is_list` handling let all six variable shapes co-exist. L1↔L2 pairing fires on axes C/D/F; L2-only mutations on $I / $K / $N have no L1 pair (correct — they're catalog-authored independently of the parameter values).

Sprint 30's assumption "the twin-copy pattern is general, no dedicated audit sprint needed" is now empirically supported. The mutator does the right thing on the extremes: minimum-complexity OEB050 (1 twin) and maximum-complexity OEB020 (3 twins + 3 bare vars in mixed shapes).

**Digests:**
- [`F1_PILOT_REVIEW_DIGEST_PHI4_OEB020.md`](F1_PILOT_REVIEW_DIGEST_PHI4_OEB020.md) — 689 lines, 112 variants
- [`F1_PILOT_REVIEW_DIGEST_PHI4_OEB050.md`](F1_PILOT_REVIEW_DIGEST_PHI4_OEB050.md) — 133 lines, 23 variants

**Named residuals across the sanity check:**
- **Identity outputs on OEB020 (4 %).** Fragments too short to compress meaningfully. Cheap to flag with a post-write equality check; not a blocker.
- **A `stage_b` warning on OEB050 reorder:** *"original ‘Ejecución de canalización … (-/-/$L(%C))\\’ not found in ‘resumen’ of concept 'OEB050$'"*. The reorder rule's `original` string doesn't match the stored `resumen` byte-for-byte (trailing `\\`/whitespace difference). The reorder still gets recorded as skipped correctly and the rest of the run proceeds. Cosmetic; would be fixed by relaxing the reorder-match to a whitespace-normalised comparison.
- **`num_to_text[A]` still emits `dos tubos` where the OEB020 template says `$A T,`.** Same class of template-vs-prompt mismatch we saw on OEB070; not a modification bug.

**Decisions / rationale (2026-07-05):**
- **F3 is unblocked.** The Sprint 30–34 pipeline generalises. Content-type quality is at least 90 % clean on every concept and hits 100 % on OEB020 and OEB050. Zero collisions across three concepts spanning 250 primary modifications. The safety net (mutator collision guard) is available if a weaker model or a weirder concept slips through.
- **No dedicated audit sprint needed.** The two concepts audited here cover both extremes of shape complexity. Any further weirdness in another chapter is F3's problem to surface, not a gate on entering F3.
- **The Anthropic Claude adapter (Sprint 30 fallback) stays permanently in reserve.** phi4 on tuned prompts is materially good enough for F3 on this evidence.

**What changed in the plan:** F2e closed. All F1_FINDINGS.md §6 items landed and empirically validated across three concepts. Phase F is ready for F3.

**Next step:** **F3 — full-scale generation across every concept group in every catalog chapter.** Prerequisites the plan should nail before starting: (a) budget the total wall-clock: 30 concept groups × ~1–3 min per group of phi4 latency ≈ 1–2 hours per chapter, across N chapters; (b) archive strategy — each F1 run produces `data/synthetic/{intermediate,variants,review}/{concept}/` and `data/synthetic/llm_cache/{concept}/` which stays under 10 MB per concept (see current OEB070 sizes) so full-chapter fits easily on the working disk; (c) chapter driver — `f1_pilot.py` targets a single concept, so F3 needs a small wrapper that iterates the concept_key list from a chapter stage-2 file. `run_synthetic.run_concept` already accepts one concept — the wrapper is a loop. After F3, F4 (review-sample validation via `review.sample_review_queue` at 10 % per stratum, 100 % on `new_param`) produces `QUALITY_REPORT.md`; then `DATA_CARD.md` refresh; then Phase G packaging (Parquet + sidecar JSONL for the traceability metadata) per RESEARCH_PROPOSAL.md §7 Q6.

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; the multi-concept behaviour is captured by the digests and the tuned-prompt pins in `test_prompts.py`).

#### Sprint 35 review-verdict addendum (2026-07-05) — bare-referenced text-var asymmetry accepted as-is

While reviewing `OEB020` variant `full_random_mix_dbab3b1771` (a paraphrase on `$I` that changed `texto` only and left `resumen` unchanged), César flagged that the paired-mutation refactor doesn't fire when the two per-surface text-variables are both **bare-referenced** on the same axis rather than indexed. On `OEB020`, `$K` (bare in resumen, `%B=a → "normal"`) and `$I` (bare in texto, `%B=a → "en cualquier clase de terreno, excepto roca"`) are both authored descriptions of axis B, but Sprint 31's twin discovery (`derive_var_axis_map`) only catches indexed refs like `$L(%B)`.

**Decision (2026-07-05, César):** accept as design, do not extend twin discovery to bare-referenced same-axis pairs. Rationale recorded in [`F1_FINDINGS.md §6.2.1`](F1_FINDINGS.md). Two independent bare wordings are a catalog-authoring choice (short label vs long descriptive phrase); linking them retroactively would flatten a distinction the author intentionally introduced. Single-surface variants are a legitimate real-world query-stable / document-varying scenario and belong to the "query-side variability" slice from RESEARCH_PROPOSAL.md §6. No code change.

---

### Sprint 34 — Phase F Task F2d (post-generation collision guard + prompt-side collision prevention; sibling-fragments slot added to L2 prompts)
**Date:** 2026-07-05
**Sprint reference:** Sprint 33 review flagged phi4's compression `Nocturno Excepcional → "Nocturno"` — collides with sibling %B=b `Nocturno`. Two leaves render identically → violates Stage-D parameter-preservation. Fix requested: A (safety net) + B (prevention). Both landed.

**What was done:**

**A — Post-generation collision guard (mutator seam).**
- New helpers in [`axis_twins`](../../src/synthetic/axis_twins.py): `axis_value_collides(concept, param, exclude_value_label, candidate)` and `fragment_collides(concept, var, exclude_condition, candidate)` — normalised-string pre-flight checks against sibling values / fragments.
- Wired into [`layer_l1._replace_value`](../../src/synthetic/layer_l1.py) and [`layer_l2._replace_fragment`](../../src/synthetic/layer_l2.py) as a pair-aware pre-flight: primary check + twin-side check. If EITHER side would produce a collision, the mutator does NOT write and returns `[Modification(status="skipped", reason="collision_with_sibling_axis_value" | "collision_with_sibling_fragment" | "…_on_twin_var" | "…_on_twin")]`. No half-applied state possible.
- Tests: new [`test_collision_guard.py`](../../tests/synthetic/test_collision_guard.py) (9 cases): L1 collision skips + non-colliding still writes + whitespace normalisation + pair-only collision skips whole; L2 collision skips + non-colliding still writes + pair-only collision skips whole + no-twin var still checks fragment siblings + skipped mods never emit paired duplicates.

**B — Prompt-side prevention.**
- **B-L1 (six L1 prompts):** added the instruction "El campo `new` de cada entrada debe ser distinto del valor `original` de las demás entradas del mismo eje: no crees colisiones entre valores del mismo eje. Si dos valores originales son cercanos (p. ej. `Nocturno` y `Nocturno Excepcional`), preserva la distinción en el sinónimo." The prompts already saw every sibling value via `{value_list}` — adding the explicit no-collision rule is enough.
- **B-L2 (three L2 prompts):** larger change — L2 prompts previously only saw the ONE fragment being modified. New `{sibling_fragments}` slot in `EXPECTED_SLOTS[L2 types]` + `slot_extractor.extract_slots` emits "%B=a: Diurno; %B=b: Nocturno; …" (the other clauses of the same var, formula order, excluding the target). Compression / paraphrase / expansion prompt templates gain the "Otros fragmentos de la misma variable: {sibling_fragments}" input line and the anti-collision instruction "El campo `new` debe ser distinto de todos los `Otros fragmentos de la misma variable`: no crees colisiones entre fragmentos del mismo eje."
- Test pins in [`test_prompts.py`](../../tests/synthetic/test_prompts.py): six new type-parametrised cases (L1 + L2 no-collision marker) + three cases pinning the `{sibling_fragments}` placeholder in every L2 prompt + updated `_EXPECTED_PLACEHOLDERS` and the L2 canonical-placeholder-set audit to include `{sibling_fragments}`. `test_variant_proposer.py`'s L2 slot fixture updated with the new key.
- `pytest tests -q` → **933 passed, 2 skipped** (Sprint 33's 910 + 23). Zero regressions. Every prior sprint's pin (role line, Spanish register, `Responde SOLO con un JSON`, JSON contract, no unrendered braces outside slots, size bounds, L1 short-label + no-echo + no-collision, L2 no-echo + per-type length + `{sibling_fragments}` + no-collision) still holds.

**Live re-run — `phi4:latest`, same concept + seed, all Sprint 32 + 33 + 34 changes:**

| metric | Sprint 33 (L1+L2 tune) | **Sprint 34 (+A+B)** |
|---|---:|---:|
| generated | 45 | 45 |
| skipped | 14 | 14 |
| malformed | 7 | 7 |
| schema_fail | 0 | 0 |
| items | 5472 | 5616 |

Semantic quality mix (67 primary modifications):

| class | Sprint 33 | **Sprint 34** |
|---|---:|---:|
| **clean** | 58 (87 %) | **60 (90 %)** |
| verbose meta-referential (all in L3 templates) | 7 | 7 |
| **bare-`%X` leaks** | **2** | **0** |
| collision skips (guard fired) | — | **0** |

**Prevention beat the safety net on this run** — B (prompt-side sibling context) worked so well that A (mutator guard) never had to fire. The Sprint 33 residuals disappeared:

- **`Nocturno Excepcional`** now becomes `Nocturno Especial` (preserves the distinction from sibling %B=b `Nocturno`) across all 6 variants that touch it. Sprint 33 was collapsing 3 of them to `Nocturno` — that's now impossible.
- **`Volumen relevante → "Volumen %D"`** (phi4's axis-code shorthand) — 2 hits Sprint 33, **0 hits Sprint 34**. The no-collision instruction + explicit siblings evidently pushed phi4 away from the shorthand.

Concrete before/after on a specific compression variant (`compression[L %B=d]`):
- **Sprint 33:** `Nocturno Excepcional → "Nocturno"` (colliding)
- **Sprint 34:** `Nocturno Excepcional → "Nocturno Especial"` (distinct)

Rendered leaf `OEB070adaa` (variant `single_L2_compression`) — resumen `(Nocturno Especial/…)`, texto `Trabajo: Nocturno Especial` (paired mutation carries into both surfaces; the paired L1 write on axis B value "d" no longer collides with B value "b" `Nocturno` because "Nocturno Especial" is distinct).

Full digest: [`F1_PILOT_REVIEW_DIGEST_PHI4_SPRINT34.md`](F1_PILOT_REVIEW_DIGEST_PHI4_SPRINT34.md).

**Named residuals (F3-tolerable):**
- **`num_to_text[A]`** now emits `un tubo` / `dos tubos` (grammatically correct apocope and plural), but the template still says `$A tubo(s)`, so the surface renders as `dos tubos tubo(s)` — awkward but semantically unambiguous. This is a template-vs-prompt-content mismatch, not a modification bug; would be fixed either by tuning the num_to_text prompt to return bare numerals when the axis is followed by a noun, or by rewriting the OEB070 template to drop the trailing `tubo(s)`. Neither blocks F3.
- **Semantic collapses on compression** — Sprint 33 flagged `Nocturno Excepcional → Nocturno`. Sprint 34 fixes that specific class of failure (sibling collisions). Other kinds of qualitative shifts (register drift, connotation change) remain a reviewer-judgement matter, not a plumbing failure. Baseline reference: 60 / 67 = 90 % clean.
- **The paired-mutation write can itself trigger a skip** if the pair side would collide. This is the correct behaviour but reduces the total generated count in some scenarios. On this run no L1 mod was skipped for pair-only reasons; on other concepts (or after further prompt shifts) this could happen. Metadata records the reason cleanly so downstream analysis can slice on it.

**Decisions / rationale (2026-07-05):**
- **A + B is the right shape:** B prevents most collisions at generation time (cheap, model-dependent), A guarantees no collision ever reaches the benchmark (mechanical, model-independent). On this concept the split is B:100 % / A:0 %; on other concepts or with weaker models the ratio will shift, and A picks up the slack. Both stay in.
- **The `{sibling_fragments}` slot is now canonical L2 grammar.** Every future L2 modification type would inherit it. `EXPECTED_SLOTS`, `slot_extractor.extract_slots`, and the three prompt templates are consistent; the L2 canonical placeholder-set test (`test_prompt_l2_three_types_share_placeholder_set`) enforces this.
- **F3 is genuinely unblocked.** phi4 with tuned prompts + collision guard produces 60 clean primary modifications out of 67 (90 %) on the pilot concept; 0 collisions; 0 template-scaffolding leaks; every content type at zero verbose. The remaining 7 verbose entries are all legitimate L3 template rewrites. The Anthropic Claude adapter (Sprint 30 fallback) stays permanently in reserve.

**What changed in the plan:** F2c → F2d closed. All Sprint 30 decisions from the F1-review are landed and empirically validated. F3 has no remaining gates.
**Next step:** **F3 preparation** — (a) multi-concept sanity check: run the same tuned pipeline on 2–3 more OEB concepts (e.g. `OEB020$`, `OEB050$`, another chapter) to confirm the twin-representation pattern and the tuned-prompt behaviour generalise; (b) budget + archive strategy for full-catalog run (variants per concept × ~30 concepts × phi4 latency); (c) decide the digest-review strategy for scale (`review.sample_review_queue` at 10 % per stratum + 100 % on `new_param`). After F3 lands, F4 (validation via `review.py`) → `QUALITY_REPORT.md` → `DATA_CARD.md` refresh → Phase G packaging.

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; the `{sibling_fragments}` slot addition is captured in the pinned tests and `EXPECTED_SLOTS`).

---

### Sprint 33 — Phase F Task F2c-L2 (L2 prompt tune: eliminates the compression / expansion concept-echo residual; phi4 clears content-type Stage-D bar)
**Date:** 2026-07-05
**Sprint reference:** Sprint 32 closed the L1 half of F2c; this sprint mirrors that fix into the three L2 prompts (compression, paraphrase, expansion). Same failure mode, same tool, symmetric wording.
**Tasks from backlog:** F2c-L2. Sprint 32's residual named L2 compression as the next target (7/15 verbose then).

**What was done (three prompt files + test pins):**
- **`compression.txt`** — added: "El campo `new` debe ser una versión reducida del fragmento (idealmente 1-3 palabras menos que el original, máximo la mitad de su longitud). No copies frases del campo Concepto, ni redactes descripciones completas del ítem …". Existing "estrictamente más corto" length constraint preserved.
- **`paraphrase.txt`** — added: "El campo `new` debe tener la misma longitud aproximada que el fragmento original (entre la mitad y el doble de su longitud). No copies frases del campo Concepto …". Defensive: paraphrase was clean this run but shares the failure shape.
- **`expansion.txt`** — added: "El campo `new` debe estar centrado en el fragmento: expande el significado del fragmento en sí (máximo 25 palabras), no redactes ni parafrasees la descripción completa del ítem. No copies frases del campo Concepto, ni enumeres las condiciones del catálogo …". Expansion is *supposed* to be verbose; the constraint is that the verbosity must be about the fragment, not the whole item.
- Test pins in [`tests/synthetic/test_prompts.py`](../../tests/synthetic/test_prompts.py): all three L2 prompts must carry the anti-echo marker `"No copies frases del campo Concepto"` and a per-type length marker (`"estrictamente más corto"` / `"misma longitud aproximada"` / `"centrado en el fragmento"`). Six new parametrised cases.
- `pytest tests -q` → **910 passed, 2 skipped** (Sprint 32's 904 + 6). Zero regressions, still hermetic.

**Live re-run — `phi4:latest`, same concept + seed, tuned L1 + tuned L2:**

Mechanical scorecard (better on both axes):

| metric | phi4 baseline | phi4 L1-tuned (Sprint 32) | **phi4 L1+L2-tuned (this run)** |
|---|---:|---:|---:|
| generated | 44 | 44 | **45** |
| skipped | 15 | 15 | 14 |
| malformed | 7 | 7 | 7 |
| schema_fail | 1 | 1 | **0** |
| items | 5472 | 5472 | 5472 |

Semantic-quality mix over the primary modifications (67 this run):

| class | phi4 baseline | Sprint 32 (L1) | **Sprint 33 (L1+L2)** |
|---|---:|---:|---:|
| **clean** | 44 (67 %) | 50 (76 %) | **58 (87 %)** |
| verbose meta-referential | 22 (33 %) | 16 (24 %) | **7 (10 %)** |
| bare-`%X` leaks | 0 | 0 | 2 |

Per-type verbose share — every content type (L1 + all three L2) at zero:

| type | baseline | L1 tune | **L1+L2 tune** |
|---|---:|---:|---:|
| synonym_label | 6/13 | 0/13 | **0/13** |
| num_to_text | 0/2 | 0/2 | 0/2 |
| unit_conversion | 0/3 | 0/3 | 0/3 |
| unit_expansion | 0/3 | 0/3 | 0/3 |
| abbrev_expansion | — | — | — |
| code_expansion | — | — | — |
| **compression** | **7/15** | 7/15 | **0/16** |
| **expansion** | **2/11** | 2/11 | **0/11** |
| paraphrase | 0/11 | 0/11 | 0/11 |
| omission (L3 template) | 5/5 | 5/5 | 5/5 |
| reorder (L3 template) | 2/2 | 2/2 | 2/2 |

**Excluding the L3 template types (whose `new` is legitimately the full template minus the omitted var, or the constituents re-ordered), the content-type leak rate is 0/60. Zero.** Every synonym / paraphrase / expansion / compression / number-to-text / unit-conversion output now respects the length target and doesn't restate the concept description.

Concrete before/after on the same variant hash (`single_L2_compression` on `%B=d`):

- **Sprint 32:** `Nocturno Excepcional → "Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/%C/%D)"` (whole item description with axis codes leaked)
- **Sprint 33:** `Nocturno Excepcional → "Nocturno"` (clean short compression; semantic-preservation of "Excepcional" is a separate reviewer question but the format is right)

Rendered surface on the same variant's leaf `OEB070adaa`:
- **Sprint 32 resumen:** `… (Suministro y ejecución de canalización de 5 tubos de polietileno 110 mm 5 At. con topo bajo vías (Nocturno Excepcional/"…"/"…")/i >==5 horas/Volumen relevante)` — recursive garbage
- **Sprint 33 resumen:** `… (Nocturno/i >==5 horas/Volumen relevante)` — clean

Full digest: [`F1_PILOT_REVIEW_DIGEST_PHI4_L1L2.md`](F1_PILOT_REVIEW_DIGEST_PHI4_L1L2.md).

**Residuals worth naming (F3-tolerable but noted):**
- **2 bare-`%X` compressions** — both `Volumen relevante → "Volumen %D"`. phi4 used the axis code as a shorthand. Same failure shape as concept-echo (leaking scaffolding into the value) but rarer and narrower. Could be fixed by extending the L2 placeholder guard to reject `%X` bare tokens in addition to `$VAR` tokens, or by prompt-adding "no uses códigos de eje (%B, %C, %D) en el resultado". Deferred — 2/60 is small enough to accept for F3 and revisit if it grows.
- **Loss of semantic distinctions on some compressions** — `Nocturno Excepcional → "Nocturno"` collapses the "Excepcional" qualifier. This is a semantic-review call, not a plumbing failure; the prompt asked for shorter and phi4 obliged. If the reviewer decides `Excepcional` must be preserved, we tighten the prompt: "no elimines cualificadores que distinguen valores del mismo eje". Held for later.
- **`num_to_text[A]` still awkward** — `de dos tubo(s)` is a Spanish-apocope issue ("un tubo" not "uno tubo"). Prompt-fixable; low priority.

**Decisions / rationale (2026-07-05):**
- **F2c is closed.** Two prompt-tune sprints (L1 + L2) took phi4 from 15–20 % clean (llama baseline) to 87 % overall / 100 % on content types. The Anthropic Claude adapter that Sprint 30 held in reserve is no longer needed for F3 — phi4 with tuned prompts clears the Stage-D bar for L1 and L2 content on the pilot concept.
- **Both prompt-tune sprints followed the same recipe:** cite the failure with a real example, name the constraint in plain Spanish, add per-type wording so the model knows what a *correct* answer looks like (not just what to avoid), pin the marker phrase in `test_prompts.py`. Cheap, honest, and doesn't touch the frozen seam.
- **The `test_prompts.py` pin discipline is worth its weight.** Every prompt marker added over Sprints 12 → 33 (role line, Spanish register, `Responde SOLO con un JSON`, JSON-declared contract, no unrendered braces outside slots, size bounds, L1 short-label + no-echo, L2 no-echo + per-type length) is a parametrised check that prevents future edits from silently dropping the constraint. Small tests, real load-bearing.

**What changed in the plan:** Phase F is unblocked for F3. F2c-L2 closed. No Claude adapter needed. The remaining named residuals (`Volumen %D`, semantic collapses, `num_to_text` awkwardness) are optional refinements that don't gate F3.
**Next step:** **F3** — full-scale generation across every concept group in every catalog chapter (not just `OEB070$`). Prerequisites: (a) confirm the twin-representation audit assumption from Sprint 30 §6.2 empirically by running the pilot across a few more concepts and inspecting the surface-mapping behaviour; (b) budget the run (F3 will produce many variants per concept — needs archive strategy); (c) decide the digest-review strategy for scale (`review.sample_review_queue` does deterministic sampling — that's the right primitive here, likely at 10 % per stratum + full coverage on `new_param`). After F3 lands, F4 (validation) uses `review.py` to produce `QUALITY_REPORT.md`, then the `DATA_CARD.md` statistics refresh, and the release packaging (Phase G).

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; L2 tune is captured by the pinned markers in `test_prompts.py`).

---

### Sprint 32 — Phase F Task F2c option (a) (L1 prompt tune: short-label constraint eliminates phi4's meta-referential outputs)
**Date:** 2026-07-05
**Sprint reference:** F1_FINDINGS.md §6.1 (model sequence phi4 → Claude), Sprint 31 (phi4 baseline showed 33 % of primary mods were meta-referential paragraphs).
**Tasks from backlog:** F2c option (a) — prompt-tune before deciding on Claude fallback.

**What was done (prompts only, six files; test-first):**
- Added to each of the six L1 prompt files an explicit short-label constraint just above the JSON-contract marker:
  > *El campo "new" debe ser una etiqueta corta (idealmente 1-4 palabras, máximo 8 palabras). No copies frases del campo Concepto, ni redactes descripciones completas del ítem …*
- Per-type wording tail is customised (`… sólo el sinónimo equivalente` for synonym_label, `… sólo el número en palabras` for num_to_text, etc.) so each prompt says what a *correct short answer* looks like, not just what to avoid.
- Structural test pin: two new markers (`etiqueta corta`, `No copies frases del campo Concepto`) checked across all six L1 prompt types in [`tests/synthetic/test_prompts.py`](../../tests/synthetic/test_prompts.py). Prevents future edits from silently removing the constraint.
- `pytest tests -q` → **904 passed, 2 skipped** (Sprint 31's 898 + 6 new type-parametrised pins). Zero regressions, still hermetic.

**Live re-run — `phi4:latest`, same concept + seed + Sprint 31 plumbing:**

`BC3CAT_LLM_MODEL=phi4:latest PYTHONPATH="src" python -m synthetic.f1_pilot run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept "OEB070$" --seed 7`

Mechanical scorecard is unchanged (44 generated / 1 schema_fail / 5472 items / coverage 1.0) — as expected, the prompt tune targets *content* not *contract*. Semantic-quality mix over 66 primary modifications:

| class | phi4 baseline | phi4 tuned | Δ |
|---|---:|---:|---:|
| clean | 44 (67 %) | **50 (76 %)** | +6 |
| verbose meta-referential | 22 (33 %) | 16 (24 %) | −6 |
| L1 outputs > 8 words | 6 | **0** | −6 |
| synonym_label verbose share | **6/13 (46 %)** | **0/13 (0 %)** | −6 |

The tune fully eliminated the meta-referential paragraphs on **synonym_label**, the type where the concept-echo bug concentrated. The remaining 16 "verbose" hits are legitimate long-form types the counter naïvely groups with the leak class: L3 omission (5/5) and reorder (2/2) rewrite templates and are *supposed* to be long; L2 expansion (2/11) is verbose by design; L2 compression (7/15) is still meta-referential and remains as the next tuning target. **Excluding legitimate-verbose types, the L1 leak rate went from 6/34 → 0/34.**

Concrete before/after on the same variant hash (`single_L1_synonym_label` on axis D):

- **Baseline (phi4 pre-tune):** `Volumen relevante → "Suministro y ejecución de canalización de tubo(s) de polietileno 110 mm 5 At. con topo bajo vías en condiciones de ejecución estándar"`
- **Tuned:** `Volumen relevante → "Alto volumen"`; `Volumen escaso → "Bajo volumen"`; `Cualquier condición de ejecución → "Sin restricción"`

Rendered surface (variant `single_L1_synonym_label_bf725471fe`, leaf `OEB070aaac` = %D=c):
- `resumen`: `… (Diurno/i >==5 horas/Sin restricción)`
- `texto`: `… Condiciones de ejecución: Sin restricción`

Both surfaces move together (paired-mutation refactor), both carry a legitimate short synonym. This is what Stage-D asks for. Full digest: [`F1_PILOT_REVIEW_DIGEST_PHI4_TUNED.md`](F1_PILOT_REVIEW_DIGEST_PHI4_TUNED.md).

**Verdict on `phi4:latest` with tuned L1 prompts:** the L1 content problem is *solved*. 100 % of L1 primary mods now respect the 8-word cap and none reproduce the concept description. Remaining lower-quality outputs come from L2 compression (same failure mode phi4 exhibited on L1 before the tune — echoing the concept). A symmetric tune on `compression.txt` (and probably `paraphrase.txt` as a defensive measure) is the obvious next iteration; that's Sprint 33 material and needs a lens-shaped "shorter than the original" instruction rather than the "1-4 word label" one used for L1.

**Decisions / rationale (2026-07-05):**
- **F2c option (a) proved sufficient for L1.** Zero drop in clean-JSON reliability (still 1 schema_fail), full elimination of the meta-referential class, and the change is a plain prompt edit — cheapest possible fix.
- **The Anthropic Claude adapter is no longer on the critical path for L1.** phi4 with tuned prompts clears the Stage-D bar on L1 outputs; the fallback is warranted only if L2 tuning (Sprint 33) also fails.
- **The digest generator's condition-binding selector is proving its worth every sprint** — synonym[B] variants pick `OEB070afaa` so the reviewer sees `Horario Flexible Excepcional`; synonym[D] variants pick a %D=c leaf so `Sin restricción` renders. The old hand-built digest would have shown the minimal `OEB070aaaa` leaf and hidden every change.

**What changed in the plan:** F2c (a) closed. Next open task is L2 prompt tune (F2c continuation) targeting compression and paraphrase for the same concept-echo behaviour. F3 remains gated on the L2 tune's outcome.
**Next step:** **F2c-L2** — mirror the short-label instruction into `compression.txt` (constraint: shorter than the original fragment, no concept echo) and `paraphrase.txt` (constraint: same-length range, no concept echo). Re-run phi4, target overall clean rate ≥ 90 %. Anthropic adapter still held in reserve.

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; the tuned-prompt files are self-describing and pinned in `test_prompts.py`).

---

### Sprint 31 — Phase F Task F2b (paired-mutation refactor + targeting gate + L2 placeholder guard + digest generator; replay-validated)
**Date:** 2026-07-05
**Findings note:** [`F1_FINDINGS.md`](F1_FINDINGS.md) (Sprint 30) — this sprint executes its §6.3 plumbing agenda.
**Tasks from backlog:** F2b (Sprint 30's four locked-in code changes). All hermetic; live phi4 re-run deferred (see next-step).

**What was done (code, TDD-first, four changes; frozen seam edits justified by F1-review):**

1. **L2-content placeholder guard — [`variant_proposer._validate_payload`](../../src/synthetic/variant_proposer.py).** New `_require_no_placeholders_in_new_fragment` (reuses the existing `_placeholders()` helper) rejects `paraphrase` / `expansion` / `compression` payloads whose `new` fragment contains `$VAR` or `$VAR(%AXIS)` tokens. F1-review §4.2 traced digest #23, #31, #42 to L2 fragments that re-embedded template scaffolding (`($L(%B)/$M(%C)/$N(%D))`) and leaked verbatim into rendered surfaces. Placeholder-free L2 fragments (the normal case) pass unchanged. Tests: [`test_f2_json_and_placeholders.py`](../../tests/synthetic/test_f2_json_and_placeholders.py) +10 cases covering happy path + the exact digest-#23 scaffold + `$L(%B)` axis-qualified + prose `$ 100` acceptance + reorder-guard independence.

2. **Per-axis targeting gate — [`slot_extractor._axis_applies`](../../src/synthetic/slot_extractor.py).** New content-driven classifier restricts L1 target enumeration by axis semantics:
   - `SYNONYM_LABEL` — requires any textual value.
   - `NUM_TO_TEXT` — requires any purely-numeric value.
   - `UNIT_CONVERSION`/`UNIT_EXPANSION` — requires a unit token (mm/cm/m/km/g/kg/h/horas/… against a controlled vocabulary `_UNIT_TOKENS`).
   - `ABBREV_EXPANSION`/`CODE_EXPANSION` — requires an uppercase 2–6-letter abbreviation (PVC, HE-20).
   Enumeration is now `axis_key for axis_key in sorted(params.keys()) if _axis_applies(...)`. Removes the ungrammatical axis-A duplications (`de Un tubo tubo(s)`) and the no-op identities on time bands that F1-review flagged in §5.2 and §5.4. Existing `test_slot_extractor.py` fixture enriched with axes A (numeric), B (`PVC`), D (`m` unit) to exercise every applicability category; the six-way parametrised `enumerate_targets` test rewritten from `["B","D"]`-for-all to per-type expected. Tests: +26 new cases (classifier matrix + OEB070-shaped gating regression).

3. **Paired L1↔L2 mutation — [`axis_twins`](../../src/synthetic/axis_twins.py) (new) + [`layer_l1`](../../src/synthetic/layer_l1.py) / [`layer_l2`](../../src/synthetic/layer_l2.py).**
   - `axis_twins.axis_twin_map(concept_item)` returns `{axis_key: text_var_key}` for axes whose template renders via an indexed reference (`$L(%B)`) with a unique twin. Delegates axis discovery to the existing `l2_repr.derive_var_axis_map`; the inverse-with-uniqueness logic sits here. Ambiguous axes (two vars indexed on the same axis) are excluded so pairing never picks the wrong twin.
   - `pair_l1_into_text_var(concept, param, value_label, original, new)` — when the axis has a twin, and the twin text-var's fragment for `%{param}={value_label}` literally equals `original`, rewrites the fragment to `new` and returns the paired-edit metadata. Otherwise `None` (silent fall-through to single-layer semantics).
   - `pair_l2_into_param(concept, var, condition, original, new)` — symmetric direction.
   - `layer_l1._replace_value` and `layer_l2._replace_fragment` call these helpers post-primary write and append a second `Modification` with `layer=<twin layer>`, `status="paired"`, `reason="twin_of_axis:{param}"` or `"twin_of_var:{var}"`. Single-layer semantics preserved when no twin exists or the twin has already diverged.
   - Test coverage: new [`test_axis_twins.py`](../../tests/synthetic/test_axis_twins.py) (16 cases) + new [`test_paired_mutation.py`](../../tests/synthetic/test_paired_mutation.py) (7 cases, end-to-end through the layer wrappers on an OEB070-shaped fixture). One existing test in `test_l2_repr.py::test_mutated_plain_var_lands_in_expected_leaves` legitimately updated to `["applied", "paired"]` because its fixture has `$L(%B)` in the template — the pairing behaviour is exactly what the test now confirms.

4. **Digest generator with condition-binding leaf selector — [`synthetic.digest`](../../src/synthetic/digest.py) (new module + CLI).** Replaces the hand-built digest whose representative leaf was always `OEB070aaaa` even for mods on non-`a` axis values (F1-review §4.3). New `select_representative_leaf(...)` picks the alphabetically smallest leaf whose axis positions bind to the merged L1/L2 conditions, falling back to the minimal leaf when nothing matches. `render_variant_entry(...)` suppresses `status="paired"` entries from the rule list (they duplicate the primary edit on the twin representation and are implementation detail for the reviewer) and shows `_(no materialized leaves)_` gracefully when a variant produced zero items (as new_param does today). CLI: `python -m synthetic.digest --concept "OEB070$" --intermediate ... --stage-json ... --out ...`. Tests: new [`test_digest.py`](../../tests/synthetic/test_digest.py) (12 cases: bindings extraction from L1/L2/L3 rules, multi-axis binding, fallback to minimal leaf, `_syn_<id>` suffix handling, end-to-end markdown rendering).

**Test count:** `pytest tests -q` → **898 passed, 2 skipped** (was Sprint 29's 826 + 72 new = 898). Zero regressions, zero network calls, seam still hermetic.

**Replay validation on the recorded llama3.1:8b transcripts** (`data/synthetic/llm_cache/OEB070$/`, 62 transcripts preserved from Sprint 28–29; the Sprint 29 materialized artefacts archived to `data/synthetic/_archive/`):

`python -m synthetic.f1_pilot replay --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept "OEB070$" --seed 7`

| metric | Sprint 29 (llama3.1:8b, pre-fix) | Sprint 31 replay (same transcripts, new plumbing) |
|---|---:|---:|
| generated | 48 | 38 |
| skipped | 60 | 20 |
| malformed | 7 | 8 |
| schema_fail | 3 | 8 |
| items | 4560 | 4656 |
| coverage | 1.0 | 1.0 |

- The extra five `schema_fail`s are the L2 placeholder-leak rejections the new guard now catches. Sprint 29 counted those as "generated"; they were the digest #23/#31/#42 leakage cases. Corpus is smaller but honest.
- The lower `generated` count also reflects the targeting gate suppressing L1 prompts on inapplicable axes (never reaching the LLM at all).
- Every remaining generated variant is now placeholder-clean AND, for axes with twins, has paired L1+L2 metadata so both `resumen` and `texto` move together.

**New digest artefact:** [`docs/synthetic/F1_PILOT_REVIEW_DIGEST_SPRINT31.md`](F1_PILOT_REVIEW_DIGEST_SPRINT31.md).

Concrete before/after examples (same recorded llama3.1:8b transcripts, same seed):

- **`single_L1_synonym_label_9468265cff`** (synonym on axis B: `Diurno → Horario de luz solar`). Sprint 29 digest showed leaf `OEB070aaaa` — `resumen` unchanged (`(Diurno/…)`), `texto` changed (`Trabajo: Horario de luz solar`). Sprint 31 digest picks leaf `OEB070afaa` and both surfaces read `Horario flexible con restricciones` — paired L1+L2 propagates the change into both text-var L (drives resumen) and param B (drives texto).
- **`single_L1_synonym_label_333a950e94`** (synonym on axis D). Sprint 29: only `texto` changed. Sprint 31: `resumen` reads `Condiciones de trabajo variables` and `texto` reads `Condiciones de trabajo variables`.
- **Digest #6 rule display** dropped from 11 lines (mixing `synonym_label[B]` + paired `synonym_label[?]`) to 6 clean primary entries.

**Decisions / rationale:**
- **Editing the frozen seam is Sprint-30-approved.** F1_FINDINGS.md §6.3 named the four fixes and their locations; Sprint 30 locked the design (paired L1+L2, catalog-wide assumption, phi4→Claude model sequence). This sprint implemented them.
- **Assumption of general dual-encoding held cleanly.** No concept-specific special case was needed. `axis_twins` returns `{}` on concepts without indexed references, and `pair_l1_into_text_var` returns `None` when the twin has already diverged — pairing degrades to single-layer without ceremony.
- **Paired edits get a distinct `status="paired"` and `reason`**, so downstream analysts can (a) filter the metadata for "primary" edits only, and (b) audit which conceptual mods produced synchronised query+doc rewrites vs. which fell back to single-layer.
- **The `test_l2_repr` behaviour update is a positive, not a regression.** Its concept fixture has `$L(%B)` in the template — exactly the shape paired mutation targets. `["applied", "paired"]` is the correct log now.

**Live phi4:latest re-run (added after Docker Desktop restart):** The `ollama` Ollama process running natively on the host had no models loaded; the models live in the `ollama/ollama:0.17.7` **Docker container** (port 11434 → 11434), which was down at first. Once Docker Desktop came back up, `docker exec ollama ollama list` showed `phi4:latest` (14.7B, Q4_K_M) and `llama3.1:8b` (8B, Q4_K_M) present. Archived the llama replay artefacts to `data/synthetic/_archive/` and ran:

`BC3CAT_LLM_MODEL=phi4:latest PYTHONPATH="src" python -m synthetic.f1_pilot run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept "OEB070$" --seed 7`

| metric | llama3.1:8b (Sprint 29) | replay w/ Sprint 31 plumbing | **phi4:latest (this run)** |
|---|---:|---:|---:|
| generated | 48 | 38 | **44** |
| skipped | 60 | 20 | 15 |
| malformed | 7 | 8 | **7** |
| schema_fail | 3 | 8 | **1** |
| items | 4560 | 4656 | **5472** |

Digest: [`F1_PILOT_REVIEW_DIGEST_PHI4.md`](F1_PILOT_REVIEW_DIGEST_PHI4.md).

**Semantic-quality breakdown of the 66 primary modifications** (excluding paired duplicates):

| class | count | share |
|---|---:|---:|
| **clean** (short synonym / grammatical rewrite / meaning-preserving) | **44** | 67 % |
| **meta-referential verbose** (`new` is a full re-articulation of the item description, e.g. `Volumen relevante → "Suministro y ejecución de canalización de tubo(s) de polietileno 110 mm 5 At. con topo bajo vías en condiciones de ejecución estándar"`) | 22 | 33 % |
| bare `%X` axis-code leaks | 0 | — |

Concrete win from paired L1+L2: variant `single_L1_synonym_label_b3a9ecd7a9` (synonym on axis B: `Diurno → Horario diurno`, all six values renamed) renders `Trabajo: Horario flexible excepcional` in `texto` AND `(Horario flexible excepcional/…)` in `resumen` on the shown leaf `OEB070afaa`. Both surfaces move together — that's the paired-mutation refactor operating end-to-end on live model output.

Concrete residual failure: variant `full_random_mix_b065f44906` and several `synonym_label[D]` outputs rewrite the parameter value to an entire item-description paragraph, which then renders horrifying nested surface text (see digest #1's `resumen`). This is a **prompt-shape failure** — phi4 is treating the concept context in the prompt as a template to echo. The L2 placeholder guard doesn't catch it because there's no `$VAR` in the payload; the text is just prose that happens to describe the whole item.

**Verdict on `phi4:latest`:** a **material improvement over `llama3.1:8b`** on the JSON-reliability axis (schema_fail 8 → 1, malformed unchanged) and on cleaner outputs (usable rate ~67 % vs. Sprint 30's ~15–20 % estimate for llama). **Still not clearing the Stage-D bar** on its own: a third of outputs are meta-referential paragraphs that read as garbage. Two ways forward: (i) prompt-tune to suppress full-item-description echoes (adds a hard word-count cap and a "return ONE short label, not a sentence" instruction per L1 prompt); or (ii) proceed to the Sprint-30 Claude fallback. Either is F2c work.

**What changed in the plan:** F2b closed (plumbing landed, tested, replay-validated). F2b-run also closed (phi4 live). Next: F2c decides prompt-tune vs. Claude. F3 (full-scale generation) still gated on F2c's model verdict.
**Next step:** **F2c** — either (a) tighten the L1 prompts (add "responde SOLO con la etiqueta corta, sin repetir la descripción del ítem", plus a max-word-count) and re-run phi4 to see whether the meta-referential rate drops below ~5 %; or (b) accept phi4 for what it is and build the Anthropic `/v1/messages` adapter for Claude (single new file implementing `LLMClient`, model-agnostic recording stack unchanged). César's call.

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; file-map rows for `axis_twins.py` and `digest.py` will be added when the next mutator sprint file is written).

---

### Sprint 30 — Phase F Task F1-review (verdict on `llama3.1:8b` + design decisions from the manual review)
**Date:** 2026-07-05
**Findings note:** [`F1_FINDINGS.md`](F1_FINDINGS.md)
**Tasks from backlog:** F1-review (César, manual). Closes F1 as a gate; opens the next mutator sprint with a concrete four-item agenda.

**What was done:**
- Sincere evaluation of the 43-variant [`F1_PILOT_REVIEW_DIGEST.md`](F1_PILOT_REVIEW_DIGEST.md) against Stage-D criteria (grammatical Spanish, meaning preservation, `new_param` distinguishability, metadata fidelity) and the meaning-preserving-variability premise. Every claim is grounded in a specific digest entry or a materialized variant read from `data/synthetic/intermediate/OEB070$/`.
- Empirical root-cause investigation of the `resumen`/`texto` desynchronisation observed in the digest. First-pass hypothesis ("L1 mods change texto only, L2 mods change resumen only") was rejected on César's push-back and replaced with a per-axis surface-mapping model, confirmed by reading the `OEB070$` templates and a materialized L1 variant (`single_L1_synonym_label_9468265cff`: renders `Trabajo: Horario de luz solar` in texto, `(Diurno/…)` in resumen).
- Three plumbing defects located precisely for future work: missing per-axis targeting gate in [`slot_extractor.enumerate_targets()`](../../src/synthetic/slot_extractor.py); missing L2-content placeholder guard in [`variant_proposer._validate_payload()`](../../src/synthetic/variant_proposer.py); missing digest generator whose representative-leaf selector actually binds to the modified condition (current digest is hand-built and hides the change in ~half the entries).

**Key results:**
- **Corrected surface-mapping model.** `OEB070$` uses `$A` in both templates (axis A symmetric) but reads axes B/C/D from different sources — resumen via text variables `$L`/`$M`/`$N`, texto via raw parameter values `$B`/`$C`/`$D`. The two sources carry duplicate labels in the original catalog; single-layer mutations break that coincidence and desync query↔doc. Evidence of the duplication predating any mutation: rendered leaves show `i >==5 horas` in resumen (from `$M`, with a source typo) vs `i >= 5 horas` in texto (from `$C`, clean).
- **Verdict on `llama3.1:8b`.** Inadequate for L1 keyed-list tasks and too error-prone in L2 semantics. Usable rate on the digest is ~6–8 of 43 (15–20 %). Dominant failure modes: semantic loss on L2 (`Excepcional` collapsed onto other parameter values in #1, #16, #20, #32, #33; `Volumen relevante → Volumen de excavación` in #36; register break `Nocturno → Bajo la luz de la luna` in #38), grammatical breakage on axis-A L1 (`de Un tubo tubo(s)` in #4; `de 1 tubo(s) tubo(s)` in #10), literal template-placeholder leaks in L2 expansions (`($L(%B)/$M(%C)/$N(%D))` in #23, #31, #42), and no-op identities on axes with nothing to expand (#2, #13, #22). The Sprint 28–29 process fixes held; the residual failures are content/plumbing, not process.

**Decisions / rationale (2026-07-05, César):**
- **Surface-mapping policy: paired L1+L2 mutations, catalog-wide.** When an axis has a dual representation (parameter value on one side, text variable on the other), the mutator will co-modify both so both `resumen` and `texto` carry the change. Closest to the proposal's "meaning-preserving rewrite of the item" framing. We assume the twin-copy pattern is general and implement the fix once across the mutator — no dedicated audit sprint. Concept-specific edge cases (e.g. an axis with a single shared variable) degenerate to the current single-layer behaviour without extra work.
- **Model sequence: `phi4:latest` first, Claude native as fallback.** `phi4:latest` (14B, already installed via Ollama) requires zero code changes — set `BC3CAT_LLM_MODEL=phi4:latest` and re-run F1 on the recorded prompt store. If quality is insufficient, add a small `HttpLLMClient`-shaped adapter for Anthropic's `/v1/messages` API. OpenAI and OpenRouter are explicitly out of scope as fallbacks.
- **Plumbing agenda for the next sprint** (order matters): (1) paired-mutation refactor of the mutator, keyed on a per-concept axis→(param, text-var) map; (2) per-axis targeting gate in `slot_extractor.enumerate_targets()` — no more `unit_expansion` on numeric count axes; (3) L2-content placeholder guard in `variant_proposer._validate_payload()` — reuse the existing `_placeholders()` helper; (4) a digest generator that selects a leaf binding to the modified condition, replacing the hand-built minimal-leaf digest; (5) `phi4:latest` re-run and offline score comparison via the existing `spike.py` harness.

**What changed in the plan:** F1 closes with a documented verdict. The next task is a new mutator sprint (paired L1+L2 + targeting + L2 guard + digest generator + `phi4:latest` re-run) — assign it a Sprint 31 / F2b ID when it starts. F3 (full-scale generation) remains gated on this sprint's outcome.
**Next step:** Sprint 31 — mutator refactor (paired L1+L2, targeting gate, L2 placeholder guard, digest generator) followed by the `phi4:latest` re-run of F1 on the recorded prompt store. Claude adapter held in reserve for a later sub-sprint if `phi4` is insufficient.

**CLAUDE_SYNTHETIC.md updated:** no (this entry is the record; the design decisions belong in the next sprint file when the mutator refactor begins).

---

### Sprint 29 — Phase F Task F2 (process fixes from F1 findings: JSON hardening + placeholder validator)
**Date:** 2026-05-21
**Tasks from backlog:** F2 (iteration 1) — fix the two process defects F1-run-generate exposed, then re-run the pilot to measure. The first F1 run was **dismissed** (artifacts cleared) per "get the process right first."

**What was done (code, frozen-seam edits justified by F1 findings):**
- **JSON hardening — [`llm_proposer`](../../src/synthetic/llm_proposer.py).** Replaced the fence-at-start stripper with `_extract_json_object`: recovers the JSON object from prose **and** a Markdown fence anywhere (`"Aquí te dejo… ```{…}```"`), then brace-slices first `{`→last `}`. Genuine non-JSON still fails loud.
- **Placeholder-preservation validator — [`variant_proposer`](../../src/synthetic/variant_proposer.py).** Reorder requires the `$VAR`/`$VAR(%AXIS)` set to survive; omission requires it minus exactly the omitted variable's tokens. Catches the `$L(%B)→$/($B)` / `$L/%$B` corruptions the string-only validators accepted.
- **Tests — [`tests/synthetic/test_f2_json_and_placeholders.py`](../../tests/synthetic/test_f2_json_and_placeholders.py)** (18): extraction recovers every observed wrap + rejects garbage; `propose` no longer falls back on prose-wrapped JSON; reorder/omission corruptions rejected, clean accepted, L2 (placeholder-free) unaffected. `pytest tests -q` → **826 passed, 2 skipped**, zero network; existing `llm_proposer`/`variant_proposer` suites green.

**Key results — re-run `OEB070$`, all 17 conditions, `llama3.1:8b`, seed 7 (before → after):**

| metric | pre-fix | post-fix |
|---|---:|---:|
| generated | 38 | 37 (all **placeholder-clean**) |
| malformed | **31** | **7** |
| schema_fail | 7 | 27 |
| skipped (total) | 38 | 60 |
| items / coverage | 4704 / 1.0 | 4560 / 1.0 |

- **Both fixes confirmed working.** Malformed crashed 31→7 (JSON extraction). The placeholder validator caught **3** L3 corruptions (omission 2, reorder 1) that were **silently materializing broken templates before** — the pre-fix "38 generated" was inflated by these.
- **Two cleaner residuals now visible** (were hidden behind malformed JSON): (a) **wrong JSON keys — 24** schema-fails (abbrev/code/unit_conversion/unit_expansion → `missing_key: 'synonyms'`; model uses `"expansions"` etc.); (b) **unmatched original — 26** emit-time skips (num_to_text 16, synonym_label 10 — the model doesn't echo the *exact* catalog value to match against).
- L2 remains solid (paraphrase 9 + expansion 10 + compression 9 = 28 of 37 generated); L1/L3 thin but now for **diagnosed, fixable** reasons.

**Decisions / rationale:**
- **Editing the frozen seam is justified F2 work.** F2's mandate is "tune prompts/conditions/model from F1 findings"; the pilot proved the model violates the JSON + placeholder contracts and the validators missed it. Both fixes are additive/backward-compatible (existing suites green).
- **This revises my earlier "no placeholder guard needed" claim.** F1 data showed 8B ignores the prompt's "conserva todas las variables" instruction and the schema validator didn't check it — so the deterministic guard was warranted.
- **The fixes did not raise yield; they made it honest.** Generated held at ~37 because parsing-recovered responses then hit schema/match failures, and 3 broken L3 variants are now correctly rejected. The corpus is cleaner, not larger.

**Iteration 2 — prompt fixes (root-causing the it1 residuals):**
- **Wrong key was our own bug, not the model.** The `unit_conversion` prompt declared `"conversions"` and `unit_expansion`/`abbrev_expansion`/`code_expansion` declared `"expansions"`, but the schema (`_LIST_KEY`) expects `"synonyms"` — the model obeyed the prompt and the validator rejected it. **Fix:** aligned the four JSON-example keys to `"synonyms"`.
- **Unmatched original was a label-prefix echo.** The model returned `original: "a: Diurno"` (copying the `value_list`'s `"letra: valor"` format) instead of `"Diurno"`, so the emitter couldn't match it. **Fix:** added to all six L1 prompts an explicit "the `original` field must copy the value text verbatim, without the letter label" instruction.
- Edits are prompt-text only (`prompts/{synonym_label,num_to_text,unit_conversion,unit_expansion,abbrev_expansion,code_expansion}.txt`); `test_prompts` (placeholder/marker pins) stays green; `pytest tests -q` → **826 passed, 2 skipped**.

**Iteration-2 re-run (`OEB070$`, 17 conditions, seed 7):**

| metric | it0 (pre-fix) | it1 (json+placeholder) | it2 (prompts) |
|---|---:|---:|---:|
| generated | 38 | 37 | **48** |
| malformed | 31 | 7 | 7 |
| schema_fail | 7 | 27 | **3** (all placeholder-corrupt, correctly caught) |
| wrong-key fails | (hidden) | 24 | **0** |
| unmatched_original | — | 26 | 107 |

- **Both it2 fixes confirmed:** wrong-key fails 24→**0**; `generated` 37→**48** (L1 now contributes — synonym 4, unit_conv 3, unit_exp 3, abbrev 2, code 2, num_to_text 1; L2 still 28; omission 4; new_param 1); `synonym_label` unmatched 10→**2**.
- **The dominant residual is now `unmatched_original` (107)**, concentrated in `abbrev/code/unit_*` applied to axes with **nothing to expand** (TRABAJO=Diurno/Nocturno, bands, conditions). These are largely **legitimate** skips (you can't expand an absent abbreviation) — a **targeting** matter (those L1 types enumerate inapplicable axes), not a JSON/key/parse defect. All genuine process bugs (parse, key, placeholder, label-prefix) are now fixed; the run is **placeholder-clean** with 48 variants.

**What changed in the plan:** F2 process-hardening done (parse + placeholder + key + verbatim-original). Residual `unmatched_original` is a **targeting** refinement (don't enumerate L1 expansion/conversion on axes lacking abbreviations/codes/units) — deferred, optional, and arguably correct-as-is. `reorder` still weak on 8B (0 generated: 1 malformed + 1 placeholder-corrupt).
**Next step:** **F1-review** (César) — decided to proceed on the 48 placeholder-clean variants. A per-variant review digest was generated to make it tractable: [`F1_PILOT_REVIEW_DIGEST.md`](F1_PILOT_REVIEW_DIGEST.md) condenses the 6144-item queue to **43 distinct modifications** (one representative leaf each, with each modification's `original → new` and the rendered `resumen`/`texto`). Review the Spanish + per-type semantics, record verdicts via `review.write_verdicts` on the shown `item_key`, and write the `llama3.1:8b` verdict. The targeting (L1-expansion-on-inapplicable-axes) and reorder-on-8B residuals are deferred to F2-followup/F3.

**CLAUDE_SYNTHETIC.md updated:** yes — "After Sprint 29" history (F2 process-hardening, 3 iterations) + the digest hand-off; `RESEARCH_PROTOCOL.md §5` F1-run-generate ✅ (post-fix) / F1-review ⏳.

---

### Sprint 28 — Phase F Task F1-run-generate (live local pilot generation on `OEB070$`)
**Date:** 2026-05-21
**Sprint file:** [`sprints/SPRINT_28.md`](sprints/SPRINT_28.md)
**Tasks from backlog:** F1-run, split **F1-run-generate** (this entry — the live, local, free generation pass + the mechanical scorecard) vs **F1-review** (pending — César's 100 %-manual fluency/semantic review + the `llama3.1:8b` verdict). **This is the mechanical half only — no Spanish-quality judgement here.**

**What was done:**
- Ran the **first real generation pass**: `python -m synthetic.f1_pilot run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept "OEB070$" --seed 7` against Ollama-served **`llama3.1:8b`**, all **17** conditions exhaustively. Exit 0; ~minutes; deterministic (temp 0 + `RecordingClient`).
- Artefacts under `data/synthetic/`: **62** recorded transcripts (`llm_cache/OEB070$/`), **38** materialized variant files (`intermediate/OEB070$/`), the variant catalog (`variants/OEB070$.json`, 161 KB), and the **100 %-coverage review queue** (`review/OEB070$_review_queue.jsonl`, 4.3 MB, **4704 items**). The recorded store makes the run replayable offline + free.

**Key results (mechanical scorecard):**
- `generated 38 / skipped 38` (skips = **31 `malformed_llm_response_after_retry`** + **7 `schema_validation_failed`**); `l2_targets 9` (guard silent → L2 fired); `items 4704`, `reviewable 4704`, `coverage 1.0`. `metadata.validate_items` passed (no crash). The mechanical plumbing works end-to-end on real data.
- **JSON reliability is the headline finding, and it is BIMODAL by layer:**
  - **L2 succeeded ~fully** — paraphrase 9, expansion 10, compression 9 (**28** variants). Simple "reformula el fragmento" prompts; 0 L2 malformed in the earlier L2-only smoke too.
  - **L1 mostly FAILED** — synonym_label 1/6, num_to_text 1/4, unit_conversion 0/4 (all schema-fail), unit_expansion 1/7, abbrev_expansion 0/7, code_expansion 0/7. L3: omission 5/10, reorder 1/2. new_param 1/1.
- **Failure mode (genuinely the model, confirmed from `raw_responses`):** `llama3.1:8b` wraps its JSON in **prose + markdown code fences** (e.g. *"Aquí te dejo la respuesta en formato JSON: ```{…}```"*) and sometimes uses the **wrong list key** (`"expansions"` instead of the schema's `"synonyms"`/`"numerals"`). The C2 parser can't extract clean JSON → `malformed`; wrong-key payloads that do parse → `schema_validation_failed`. This is classic small-model behavior, not a harness bug (the L2-only smoke had 0 malformed; the L1 prompts that demand a keyed list are where 8B breaks).

**Decisions / rationale:**
- **The mechanical half is reported; fluency is deferred.** Per the F1-run split, this entry records only what code can verify (counts, JSON reliability, the failure mode). Whether the *generated Spanish* is good is César's F1-review.
- **Highest-leverage F2 input identified:** harden the JSON contract for 8B — either strengthen the per-type prompts ("responde ÚNICAMENTE con JSON, sin markdown ni texto") and/or make the C2 parser strip ```json fences / leading prose before parsing (a `llm_proposer` change — frozen seam, so an F2/bugfix decision, not F1). This could flip L1 from ~15 % to near-100 % success. The recorded transcripts let F2 measure any fix offline + free.

**What changed in the plan:** F1-run-generate done; the recorded store + review queue are handed to **F1-review** (César). F2 (Sprint 29) now has a concrete first agenda item: the JSON-reliability fix for L1 prompts.
**Next step:** **F1-review** (César) — review the 38 generated variants (esp. judge L2 Spanish fluency + retrieval-safety), record verdicts, write the F1 findings note + the `llama3.1:8b` verdict. Then **Sprint 29 — F2** (prompt/parser JSON hardening + re-run from the recorded store).

**CLAUDE_SYNTHETIC.md updated:** yes — "After Sprint 28" history (generation ran; review pending); `RESEARCH_PROTOCOL.md §5` F1-run-generate ✅ / F1-review ⏳.

---

### Sprint 27 — Phase F Task F1-build (pilot harness: `f1_pilot.py` driver + `stage_b` pre-rerun hook)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_27.md`](sprints/SPRINT_27.md)
**Tasks from backlog:** F1-build (the runnable harness; code, hermetic). The live local generation + manual review are **F1-run** (Sprint 28). Same build-vs-run discipline as A3a/A3b and B6.

**What was done:**
- **Added a `pre_rerun` hook to [`stage_b`](../../src/synthetic/stage_b.py)** — `materialize_variant` / `materialize_catalog_entry` gain `pre_rerun: Callable[[dict], dict] = _identity`, applied to the mutated concept immediately before `run_stages_3_to_7`. Default identity → **byte-identical** for every existing caller (all `test_stage_b` cases stay green). This is the single deliberate seam edit; it gives the two-mode L2 flow a place to insert `l2_repr.formula_to_list` between apply and the rerun (which `materialize_*` previously hard-wired with no insertion point).
- **Created [`src/synthetic/f1_pilot.py`](../../src/synthetic/f1_pilot.py)** — the pilot driver, a *consumer above the orchestrator* (like `spike.py`; never imported by the seam). `run_pilot` composes the unedited stack with the adapter bracketed in: `list_to_formula(True)` → `run_concept` (through `RecordingClient(HttpLLMClient(llama3.1:8b))`) → `list_to_formula(False)` → `materialize_catalog_entry(pre_rerun=formula_to_list)` → `metadata.join_intermediate` → `review.sample_review_queue(coverage=1.0)` → a `PilotScore`. Plus `load_pilot_concept`, `default_conditions` (all 17), `format_scorecard`, an offline `replay=True` path (ReplayClient), and a thin `run`/`replay` CLI.
- **Created [`tests/synthetic/test_f1_pilot.py`](../../tests/synthetic/test_f1_pilot.py)** (14) — all hermetic: `run_pilot` over a tiny mixed-shape concept + a const/Replay client (L2 fires, 100 %-coverage queue, items validate, malformed→bucket, offline replay reproduces the score); the `stage_b` hook (default == identity; invoked once; `formula_to_list` renders without `* (%` mangling); no-reverse-import; no new dependency. **No live `pytest` case.**

**Key results:**
- `pytest tests -q` → **808 passed, 2 skipped** (Sprint-26 baseline 794 + 14 new), zero failures, **zero network calls**.
- The integration risk flagged in the plan — `metadata.join_intermediate → validate_items` rejecting the materialized items — **did not materialize**: `stage_b._materialized_to_dict`'s payload (`concept_key`/`variant_id`/`modifications`/`items`) is exactly what `join_variant_payload` consumes, and items validate.

**Decisions made and rationale:**
- **One deliberate seam touch: a default-identity `pre_rerun` hook.** Smaller and safer than duplicating `materialize_variant`'s loop in the driver, and backward-compatible (existing tests byte-identical). The driver passes `formula_to_list`.
- **`coverage_fraction` is measured against *reviewable* items, not all items.** A variant whose rules all skip at Stage-B apply materializes as 0-modification baseline items, which `review.stratify` correctly excludes; reporting `queue / total_items` would understate coverage. So the score reports `materialized_items`, `reviewable_items`, and `queue_size`, with `coverage_fraction = queue / reviewable` (1.0 at `coverage=1.0`). Surfaced by the smoke test.
- **The driver is `spike.py`'s sibling** — composes the frozen public surface + `l2_repr`; never imported by the seam (asserted).
- **No retrieval-safety code guard** — the safety semantics already live in the prompts; F1-run's manual review judges `llama3.1:8b`'s actual compliance.

**What changed in the plan:** F1-build closed. The live run + 100 %-manual review is **Sprint 28 (F1-run)**; the F1 draft renumbered `SPRINT_27 → SPRINT_28`.
**Next step:** **Sprint 28 — F1-run**: `python -m synthetic.f1_pilot run --stage-json … --concept "OEB070$"` against Ollama-served `llama3.1:8b`, then César's 100 %-manual review.

**CLAUDE_SYNTHETIC.md updated:** yes — `f1_pilot.py` file-map row + the `stage_b` pre-rerun-hook note + "After Sprint 27" history; `RESEARCH_PROTOCOL.md` §3.5 driver row ✅ + §5 F1-build ✅ / F1-run ⏳.

---

### Sprint 26 — Phase B Task B6 (L2 text-variable representation adapter: fix the silent L2 no-op)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_26.md`](sprints/SPRINT_26.md)
**Tasks from backlog:** B6 (new) — surfaced while selecting the F1 pilot concept.

**What was done:**
- **Found a silent no-op:** the synthetic **L2 layer** (paraphrase / expansion /
  compression) produces **zero** modifications on most real catalog data. The L2
  path addresses text-variables by a `"FRAGMENT" * (%AXIS=label)` **formula
  string**, but `enumerate_targets` skips any non-string. Real text-variables come
  in **three shapes** whose rerun form is decided by the template reference style:
  `LIST_plain` (`['"Diurno"', …]`, indexed `$L(%B)` → positional list),
  `STR_formula` (`'"normal" * (%B=="a") + …'`, bare `$K` → formula), and
  `LIST_conditional` (`['"…" * (%B=="f")', …]`, bare `$P` → list of conds). The
  two list shapes (~96 of ~117 OEB L2 vars) were silently un-enumerable. The L2
  tests passed only because their fixtures used the formula form the real pipeline
  never emits for those.
- **Created [`src/synthetic/l2_repr.py`](../../src/synthetic/l2_repr.py)** — a
  pure, **reference-style-aware** adapter, a *consumer above the frozen seam*
  (imports `slot_extractor`/`taxonomy` + stdlib; never imported by any seam
  module). Two conversion modes: `list_to_formula(stage_json,
  include_conditional=True)` makes **all three shapes** enumerable for Stage A
  (`LIST_plain` paired with axis values, `LIST_conditional` joined verbatim,
  `STR_formula` passthrough); `include_conditional=False` converts only
  `LIST_plain` so `STR_formula`/`LIST_conditional` mutate **natively** and stay
  byte-faithful; `formula_to_list(stage_json)` restores **only indexed-referenced**
  vars to positional lists; `derive_var_axis_map` + `assert_l2_targets_or_warn`
  (silent-no-op guard). Per-var report; nothing silent.
- **Created [`tests/synthetic/test_l2_repr.py`](../../tests/synthetic/test_l2_repr.py)**
  (20) **+ [`test_l2_integration.py`](../../tests/synthetic/test_l2_integration.py)**
  (8) — all hermetic: all three shapes; the `STR_formula`-not-corrupted guard; the
  **byte-faithful baseline through `run_stages_3_to_7`**; mutated round-trips for
  `LIST_plain` and `LIST_conditional`; every edge-case reason; the guard paths.

**Key results:**
- All three shapes enumerable for Stage A. On real `OEB020$` (has all three):
  enumerable PARAPHRASE targets **20 → 31**; on `OEB070$`: **0 → 9**.
- **Byte-faithful baseline:** the unmutated apply-mode round-trip reproduces the
  original `run_stages_3_to_7` output **identically** — verified dict-equal on
  `OEB020$`'s 4608 leaves (all three shapes restored exactly).
- `pytest tests -q` → **794 passed, 2 skipped** (Sprint-25 baseline 766 + 28 new),
  zero failures, **zero network calls**. Frozen-seam `git diff` empty.

**Decisions made and rationale:**
- **Reference style decides the rerun form (empirically verified).** Indexed
  `$L(%B)` → positional list; bare `$K`/`$P` → formula string / native list. A
  `LIST_plain` as a formula mangles s05's positional index; a `STR_formula` as a
  list collapses every leaf to the first value; a `LIST_conditional` joined into
  one formula silently changes which leaves render. My first cut handled only
  `LIST_plain` and would have **corrupted the bare `STR_formula` vars** by
  listifying them — the user flagged the missing shapes, and the fix was made
  reference-style-aware.
- **Two conversion modes.** Enumeration wants every var as a string; the rerun
  wants each in its native form. `include_conditional=True` for `run_concept`,
  `False` for `apply_variant_rules`; `formula_to_list` restores only
  indexed-referenced `LIST_plain` vars. Byte-faithfulness (BC3CAT-Syn baselines
  must reproduce the original) is the gate that forces this.
- **Fix by adapting representation, not editing the seam** — `slot_extractor`/
  `layer_l2`/`rule_emitter` untouched. `layer_l2` already mutates `STR_formula`
  and `LIST_conditional` natively; only `LIST_plain` needs the formula round-trip.
- **Nothing silent + a guard.** Per-var report; embedded-quote vars left native;
  `assert_l2_targets_or_warn` shouts if vars are enumerable-converted but yield 0.
- **Reflection — L2 is the only fixture/real-data mismatch.** L1/L3/`new_param`
  fixtures match real data and fire. Two *error-swallowing* risks (a different
  class) are recorded for a follow-up hardening pass, **not fixed here**:
  `stage_runners` s04 `evaluate_formula`'s bare `except` (which masked this bug's
  rerun symptom) and `stage_b.apply_variant_rules`'s skip-and-log.

**What changed in the plan:** B6 closed. The F1 draft renumbered `SPRINT_26 →
SPRINT_27` and now covers **all 12** modification types (L2 included). A
"stage-runner fail-loud / no-op guard" follow-up is noted.
**Next step:** **Sprint 27 — F1** single-concept pilot on `OEB070$` with
`llama3.1:8b`, all 12 types, 100 %-manual review (the F1 driver brackets the
mutation with `list_to_formula`/`formula_to_list` and runs the guard).

**CLAUDE_SYNTHETIC.md updated:** yes — `l2_repr.py` file-map row + decisions +
"After Sprint 26" history; `RESEARCH_PROTOCOL.md` §3.5 adapter row ✅ + §5 B6 entry.

---

### A3b-run decision — LLM proposer model = local Llama (`llama3.1` 8B via Ollama)
**Date:** 2026-05-20
**Type:** Decision record (not a sprint). Closes A3b-run.

**Decision:** Generate BC3CAT-Syn with a **local Llama model — `llama3.1:8b`, served by Ollama at `http://localhost:11434/v1`**. Verified live through the project's own `HttpLLMClient` (a one-line Spanish prompt returned `"Hola"`). **Use the exact tag `llama3.1:8b`** — the bare `llama3.1` resolves to `:latest`, which is not pulled and 404s. `utils.config` `LLM_MODEL` default updated `llama3.1 → llama3.1:8b` to match the installed tag (the only code change; not a seam file).

**How the decision was made — honest framing:** this is a **deliberate strategic commitment, not a measured fluency winner.** We did *not* run the live ≥2-model `spike.py` comparison; no recorded transcripts were read, and **no fluency/JSON-reliability/latency numbers were measured.** The choice rests on three operational reasons, not on a quality measurement:
- **Cost** — local inference is free to run and re-run; no per-token API spend across a 47k-scale corpus.
- **Privacy / control** — generation stays entirely on local infrastructure.
- **Reproducibility** — a pinned local model + `temperature 0.0` + the `RecordingClient` store gives a fully offline, deterministic, replayable generation path.

**Where Spanish quality actually gets validated:** because we skipped the pre-generation fluency spike, **the F1 single-concept pilot's 100 %-manual review is now the real quality gate.** If that review finds `llama3.1` 8B's technical Spanish inadequate, the `spike.py` harness (Sprint 25) is already in place to compare local alternatives (8B vs `llama3.1:70b` vs a Spanish-tuned model) on the recorded transcripts — that fallback is one CLI run away, no new code.

**What changed in the plan / docs:** `RESEARCH_PROTOCOL.md §4` `LLM proposer model` flipped `TBD → llama3.1` (8B, local) with the strategic-choice note; §5 A3b-run marked ✅ (strategic commitment). A3b is now fully closed (build + run). Phase F is unblocked.
**Next step:** **Sprint 26 — F1** single-concept pilot: pick a moderate OEB concept group (50–200 items), generate one variant per §6 condition with `llama3.1` through `RecordingClient` (offline-replayable), and **review 100 % by hand** — this is where `llama3.1`'s Spanish is judged.

**CLAUDE_SYNTHETIC.md updated:** no — the §4 design table in `RESEARCH_PROTOCOL.md` is the canonical home for the model decision; the Sprint 25 file-map/history rows already describe the harness. (Will note the chosen model in the Sprint 26 / F1 entry.)

---

### Sprint 25 — Phase A Task A3b-build (model-choice spike harness `spike.py`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_25.md`](sprints/SPRINT_25.md)
**Tasks from backlog:** A3b, split **A3b-build** (this sprint — the spike harness; code, hermetic) vs **A3b-run** (manual close-out by César — the live ≥2-model fluency/JSON/cost comparison + the §4 model flip; paid, out-of-suite, prose). Same discipline as Sprints 23–24: ship the runnable contract, never fabricate the measured result.

**What was done:**
- **Created [`src/synthetic/spike.py`](../../src/synthetic/spike.py)** — the model-choice spike harness, a *consumer* of the orchestrator that sits **above** the frozen Stage-A/Stage-B seam (no edit to `llm_proposer` / `variant_proposer` / `run_synthetic` / `llm_client`):
  - `SINGLE_TYPE_CONDITIONS` — the 12 single-type §6 conditions (11 `single_*` + `new_param_only`), pinned in deterministic sorted order so the recorded store is reproducible.
  - `CandidateSpec` (slug + `LLMConfig`; `.parse("name:base_url:model[:API_KEY_ENV]")` for the CLI) — ≥2 candidates differ by `base_url` + `model` alone (A3a decision 2).
  - `CandidateScore` — the **automatable** scorecard: proposed/skipped counts, per-`ModificationType` outcome, the C2/C3 skip split (`malformed_llm_response_after_retry:` vs `schema_validation_failed:`), `llm_calls`, total/mean latency, mean response length. **No fluency field** (decision 3).
  - `run_candidate` — wraps the candidate in `RecordingClient(_MeasuringClient(client_factory(cfg)))` under a per-candidate store (`store_root/<name>`), calls the **unedited** `run_concept`, and tallies the score off the returned `VariantCatalogEntry`. Latency rides an injectable `clock` (default `time.perf_counter`); a `replay=True` flag re-tallies from an existing store via `ReplayClient` with no live call.
  - `run_spike` (each candidate into its own store) + `format_scorecard` (Markdown table, automatable columns only — no fluency column) + a thin `main(argv)` `run` CLI (`--candidate` repeatable, `--replay`).
  - Imports `run_synthetic` / `llm_client` / `taxonomy` / `utils.config` + stdlib only; **never imported by** any seam module (a test asserts the no-reverse-import).
- **Created [`tests/synthetic/test_spike.py`](../../tests/synthetic/test_spike.py)** — 17 hermetic tests: scorecard tallies over a tiny in-memory `stage_json` + a canned client; recording store round-trips via a real `ReplayClient`; `replay=True` re-tally with an *exploding* live factory (proves no live call); C2/C3 skip-reason split (malformed → malformed bucket, valid-JSON-wrong-shape → schema bucket); a full 12-condition drive via a universal-payload const client (per-type aggregates back to the headline totals); deterministic latency under an injected fake clock; `run_spike` ≥2 candidates into distinct stores; `format_scorecard` row-per-candidate + no-fluency-column guard; no-fluency-field guard on the dataclass; no-secret-leak (key value absent from store + scorecard); no-reverse-import + no-new-dependency tripwires.

**Key results:**
- `pytest tests -q` → **766 passed, 2 skipped** (Sprint 24 baseline 749 + 17 new hermetic `test_spike` tests; the 2 skips unchanged — the spike's live path is the manual CLI, not a new `pytest` gate). Zero failures, **zero network calls**.
- `git diff` on the seam files (`llm_proposer.py` / `variant_proposer.py` / `run_synthetic.py` / `llm_client.py` / `composition.py` / `variant_catalog.py`) is empty; the only new code is `spike.py` + its test.

**Decisions made and rationale:**
- **A3b-build (code) vs A3b-run (paid spike) split.** §5 A3b bundles "build the spike harness" with "run the live ≥2-model choice + flip §4". Opposite testability: A3b-build is hermetic code; A3b-run needs real keys/network/cost and produces a *judgement* (Spanish-technical fluency read off the transcripts) recorded in prose. Sprint 25 *enables* A3b-run (`RecordingClient` captures each candidate transcript so the spike replays offline forever) but does not run it — **§4 `LLM proposer model` stays `TBD`**; the flip is César's close-out.
- **The spike is a composition, not new logic.** It wraps each candidate in a `RecordingClient` and calls the unedited `run_concept`; the scorecard is tallied off the `VariantCatalogEntry`. No new prompt rendering, parsing, or schema logic — that is the frozen C2/C3 seam.
- **Consumer of the orchestrator, never imported by it.** `spike.py` imports the seam; nothing in the seam imports `spike` (asserted) — A3b sits *above* the orchestrator and calls in.
- **Code measures the measurable; humans judge fluency.** Parse/schema/skip/latency/length are scored automatically; Spanish technical fluency is the human read of the recorded transcripts — no `fluency` column (guarded by tests).
- **`RecordingClient` makes the decision reproducible and F1 free.** Run the spike once; the chosen model's per-candidate store replays offline forever, and F1 inherits it.
- **No secrets, no new dependency.** Carried over from A3a: the key is read by `HttpLLMClient` from the `config`-named env var at request time, never written to a store/log/score (asserted); the harness is stdlib + existing `synthetic` modules only.

**Problems encountered / resolved:** the CLI `--replay` factory could not resolve the *per-candidate* store from `LLMConfig` alone (the store is keyed by candidate name, not config). Resolved by adding an explicit `replay=True` flag to `run_candidate`/`run_spike` that swaps the inner transport for a `ReplayClient(store_dir)` over the candidate's own store — correct per-candidate replay, and the CLI just forwards the flag.

**What changed in the plan:** A3b-build closed (the harness + hermetic tests). **A3b-run** (the live ≥2-model fluency read + the §4 `TBD → model` flip) remains César's manual, paid close-out — the gate on Phase F. F1 (single-concept pilot, replaying the chosen model's store) is **Sprint 26**.
**Next step:** **A3b-run** (César — run `python -m synthetic.spike run …` over the named pilot concept against ≥2 candidates, read the recorded Spanish, decide, record in this log, flip `RESEARCH_PROTOCOL.md §4`) → **Sprint 26 — F1** single-concept pilot → F2 retro → F3 full generation → F4 validation (`QUALITY_REPORT.md`) → post-F3 `DATA_CARD.md` statistics refresh.

**CLAUDE_SYNTHETIC.md updated:** yes — added the `spike.py` ✅ file-map row, recorded the A3b-build/A3b-run split + composes-`run_concept` / consumer-not-imported / automatable-vs-fluency / mandatory-`RecordingClient` / hermetic-tests / §4-stays-TBD-until-run / no-secrets-no-dep decisions, and prepended the "After Sprint 25" history entry.

---

### Sprint 24 — Phase A Task A3a (concrete `LLMClient` transport + record/replay harness)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_24.md`](sprints/SPRINT_24.md)
**Tasks from backlog:** A3, split **A3a** (this sprint — build the transport; code, hermetic) vs **A3b** (follow-up — the live ≥2-model fluency/JSON/cost spike; manual, paid, prose). Same discipline as Sprint 23: ship the runnable contract, never fabricate the measured result.

**What was done:**
- **Created [`src/synthetic/llm_client.py`](../../src/synthetic/llm_client.py)** — the one concrete implementation of the already-frozen `llm_proposer.LLMClient` Protocol (`complete(prompt) -> str`), slotting in *under* the seam (no edit to `llm_proposer` / `variant_proposer` / `run_synthetic`):
  - `LLMClientError` / `LLMTransportError` — distinct, catchable transport exceptions.
  - `LLMConfig` (frozen dataclass; `temperature` defaults `0.0`) + `from_config()` / `from_env()` builders. Stores only the *name* of the API-key env var — never the key value.
  - `HttpLLMClient` — OpenAI-compatible `/chat/completions` POST over **stdlib `urllib.request` + `json`** (no `requests`/`httpx`/vendor SDK). One user message at `temperature 0.0`; returns `choices[0].message.content`. Owns the *network-fault* retry layer (timeouts / connection errors / 429 / 5xx → bounded exponential backoff; non-429 4xx and exhausted retries → fail-loud). Injectable `sender` seam (default = real `urllib` POST) so the entire client is tested without a socket.
  - `ReplayClient` — content-addressed (`sha256(prompt)`) read from a JSON-per-prompt store; unknown prompt → fail-loud.
  - `RecordingClient` — wraps any `LLMClient`, returns its response unchanged, persists `prompt-hash → response`.
  - Thin `main(argv)` `complete` CLI (`--prompt`/stdin, `--replay`), mirroring `packaging`/`loaders`.
- **Added additive LLM transport settings to [`src/utils/config.py`](../../src/utils/config.py)** — `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY_ENV` (env-var *name* only), `LLM_TIMEOUT`, `LLM_MAX_RETRIES`, `LLM_BACKOFF_BASE`, `LLM_TEMPERATURE`, `LLM_CACHE_DIR` (under `SYNTHETIC_DATA_ROOT`), all env-overridable. No key value, no I/O.
- **Created [`tests/synthetic/test_llm_client.py`](../../tests/synthetic/test_llm_client.py)** — 30 hermetic tests + 1 env-gated live smoke: duck-typed `propose` conformance; HTTP happy path + request-body/header assertions; network-fault / 429 / 5xx retry with asserted bounded-backoff schedule (monkeypatched `sleep`); non-retryable 4xx + exhausted-retry fail-loud; envelope-parse failures (non-JSON / empty `choices` / missing `choices` / non-string content); `ReplayClient`/`RecordingClient` round-trips + fail-loud unknown; `propose`-over-`ReplayClient` success **and** the existing C2 `malformed_llm_response_after_retry` fallback; and no-secret-leak (key absent from the recording store and from raised `LLMTransportError` text).

**Key results:**
- `pytest tests -q` → **749 passed, 2 skipped** (Sprint 23 baseline 719 + 30 new hermetic `llm_client` tests; the 2 skips = the pre-existing Sprint-12 `new_param` brace-audit skip + the new env-gated live smoke). Zero failures, **zero network calls**.
- `git diff` on the seam files (`llm_proposer.py` / `variant_proposer.py` / `run_synthetic.py`) is empty; `config.py` change is additive-only.

**Decisions made and rationale:**
- **A3a (code) vs A3b (paid spike) split.** §5 A3 bundles "build the transport" with "run the live ≥2-model choice". They have opposite testability: A3a is hermetic code; A3b needs real keys/network/cost and produces a judgement recorded in prose. Sprint 24 *enables* A3b (the `RecordingClient` captures each candidate transcript so the spike replays offline forever) but does not run it — the §4 `LLM proposer model` flip from `TBD` is Sprint 25's opening step.
- **One module behind the frozen Protocol.** A3 implements `complete()` and edits none of the Stage-A seam — the whole point of the Protocol.
- **Two retry layers, cleanly separated.** The malformed-JSON resend stays in `llm_proposer.propose`; the transport adds a *separate* network-fault retry. They never merge.
- **Stdlib transport, no new dependency.** `urllib.request` + `json` against the OpenAI-compatible contract covers both the GPT-4-class API and local-Llama candidates by base URL + model id alone.
- **Hermetic suite, env-gated live smoke.** Injected sender / `ReplayClient` keep `pytest` socket-free; the lone live test skips-not-fails without `BC3CAT_LLM_LIVE=1` + a key — the pyarrow/data-gating rule.
- **No secret leaks.** Config holds only the env-var name; the key value never enters the store, a log, or an exception message (asserted).

**Problems encountered / resolved:** the `LLMClient` Protocol is not `@runtime_checkable`, so an `isinstance` conformance check raised `TypeError`. Resolved by testing conformance the way the seam actually uses it — duck-typed acceptance by `propose` — rather than a runtime `isinstance`.

**What changed in the plan:** A3a closed (transport + record/replay). A3b (live model-choice spike + §4 model flip) remains pending as Sprint 25's opening step, then F1 single-concept pilot.
**Next step:** Sprint 25 — **A3b** live model-choice spike (≥2 candidates through `RecordingClient`, record the decision + flip §4) → **F1** single-concept pilot → F2 retro → F3 full generation → F4 validation (`QUALITY_REPORT.md`) → post-F3 `DATA_CARD.md` statistics refresh.

**CLAUDE_SYNTHETIC.md updated:** yes — added the `llm_client.py` ✅ file-map row, recorded the A3a/A3b split + one-module-behind-the-Protocol / stdlib-no-dep / two-retry-layers / record-replay / injectable-sender / live-smoke-gated / no-secrets decisions, and prepended the "After Sprint 24" history entry.

---

### Sprint 23 — Phase G Tasks G3 + G4 (release documentation: `DATA_CARD.md` + README "Synthetic Variant" + `HANDOFF.md`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_23.md`](sprints/SPRINT_23.md)
**Tasks from backlog:** G3 (Data-in-Brief data card + README "Synthetic Variant" section) + G4 (cross-repo handoff memo). Documentation-only — no code module, no new test. Pairs two cohesive Phase-G doc tasks in one sprint (precedent: Sprint 20's E3+E4).

**What was done:**
- **Created [`DATA_CARD.md`](DATA_CARD.md)** — Data-in-Brief card documenting the now-frozen G1/G2 contract: provenance (three-layer grammar; LLM-proposed → rule-applied → reviewer-validated), the two release files (1:1 on `item_key`), the items schema (exactly the nine `ITEM_COLUMNS` in order), the sidecar `Modification.to_dict` payload, the 12-type × 4-layer taxonomy (from `TYPE_TO_LAYER`), the `modification_types`/`modification_count` + §6 generation-condition slices, the `synthetic.loaders` quickstart with the `long_view`/`short_view` `text`+`text_norm` shape and its OEB `_norm` consistency, AI disclosure, limitations, CC-BY-4.0 dataset / MIT code license, and citation. **Every corpus-scale statistic is an explicit `TBD (pending F3 full generation)` placeholder** — no fabricated or OEB-borrowed numbers.
- **Created [`HANDOFF.md`](HANDOFF.md)** — short cross-repo memo for `bc3cat-retrieval`: the two file locations + 1:1 `item_key` join, the new slice columns + §6 conditions, the `synthetic.loaders` import surface, the `long_view`→`OEB_long_norm` / `short_view`→`OEB_short_norm` `_norm` mapping, and the "not yet generated — pending A3 + F3" status. Explicitly does **not** modify `bc3cat-retrieval`.
- **Appended `## Synthetic Variant (BC3CAT-Syn)` to [`README.md`](../../README.md)** (before `## Citation`) — additive only; existing BC3CAT sections byte-unchanged. Links the data card, the two release files, and the loader API.
- `pytest tests -q` → **719 passed, 1 skipped**, unchanged from Sprint 22 (documentation-only sprint adds no tests).

**Decisions made and rationale:**
- **G3 + G4 over A3.** G3/G4 finish the phase Sprints 21–22 opened and are fully unblocked at the format/schema/API level (G1 froze the format, G2 froze the loader contract — both test-pinned). A3 (concrete `LLMClient` transport) is a separate track — its own Sprint 24, the prerequisite for the Phase F real pilot.
- **Document the frozen contract; never fabricate corpus statistics.** Every schema/format/taxonomy/slice/loader fact is derivable from existing code (`packaging.ITEM_COLUMNS`, `taxonomy.TYPE_TO_LAYER`, `loaders` view columns, `RESEARCH_PROPOSAL.md §2.3`, `§6`). The corpus has not been generated (F3 blocked on A3), so every corpus-scale number is a marked `TBD (pending F3)`. **A post-F3 statistics refresh of `DATA_CARD.md` is the explicit follow-up** — not a Sprint 23 deliverable.
- **Documentation-only — suite unchanged.** No code module, no pytest file, no Markdown-parsing doc-drift guard (brittle, and the schema is already pinned in `test_packaging.py`/`test_loaders.py`). 719 passed, 1 skipped stands.
- **Additive README.** A new top-level section only; the BC3CAT description is verbatim. `synthetic` still never merges to `main`.
- **`HANDOFF.md` points; it does not wire.** The downstream `import`/index integration is `bc3cat-retrieval`'s change.

**Problems encountered / resolved:** none — pure documentation against the frozen G1/G2 contract.

**What changed in the plan:** G3 and G4 closed; Phase G documentation complete. The remaining open items are A3 (LLM transport) and the Phase F pilot/generation (F1–F4), after which the `DATA_CARD.md` statistics refresh fills the `TBD` placeholders.
**Next step:** Sprint 24 — **A3** (concrete `LLMClient` transport) to unblock the Phase F pilot (F1–F2), then F3 full generation, F4 validation (`QUALITY_REPORT.md`), and the post-F3 `DATA_CARD.md` statistics refresh.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped the ✅ `DATA_CARD.md` + `HANDOFF.md` file-map rows, noted the README "Synthetic Variant" section, recorded the document-the-frozen-contract / no-fabricated-stats / documentation-only / additive-README / handoff-only-memo decisions, and prepended the "After Sprint 23" history entry.

---

### Sprint 22 — Phase G Task G2 (loader utilities: `loaders.py` — read API + 1:1 join + long/short views)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_22.md`](sprints/SPRINT_22.md)
**Tasks from backlog:** G2 (consumer-facing loader API + the long/short projection deferred by G1). Ships as one read-only library + thin CLI, [`src/synthetic/loaders.py`](../../src/synthetic/loaders.py). The data card / README (G3) and handoff (G4) are later Phase-G sprints; A3 (concrete `LLMClient` transport) remains the F-pilot prerequisite.

**What was done:**
- **Created [`src/synthetic/loaders.py`](../../src/synthetic/loaders.py).** Read-only consumer layer over the two G1 release files. `load_items(path=None)` / `load_modifications(path=None)` are thin wrappers over `packaging.read_items_parquet` / `read_modifications_jsonl` (default paths from `default_items_path()` / `default_modifications_path()`, resolved at call time under `SYNTHETIC_PROCESSED_DIR`). `join(items=None, modifications=None, *, items_path=None, mods_path=None)` re-attaches the ragged sidecar to the flat items frame as an in-memory `modifications` column (`list[dict]`, `Modification.to_dict` shape) on a sorted **copy**, asserting a **1:1** `item_key` join and raising `LoaderError` on any unmatched key on either side (or a duplicate frame key). `long_view`/`short_view` project to the OEB-style target/query views: `texto`/`resumen` → a single `text` column, the key+slice metadata (`item_key, original_key, concept_key, params, variante_id, modification_types, modification_count`), and a derived `text_norm` (`utils.text_processing.normalize_text`, reused verbatim) — no fabricated OEB-only `id`/`ud`/`concept`, no `modifications`. `main(argv)` is a thin `info` argparse CLI. `pandas` is imported lazily so the module + the stdlib `load_modifications`/JSONL path stay importable without it.
- **Created [`tests/synthetic/test_loaders.py`](../../tests/synthetic/test_loaders.py)** — always-on stdlib tier (public-surface pin, import-hygiene + no-side-effects, call-time default-path resolution, `load_modifications` JSONL round-trip from a hand-written fixture + baseline → `[]`, CLI no-subcommand) + a `pandas`-only join-mismatch fail-loud + `pyarrow`-gated tier (`load_items` round-trip, `join` 1:1 + `modifications`-column shape + no-mutation + frame mismatch fail-loud, `long_view`/`short_view` columns + `text`/`text_norm` correctness + no-`modifications`/no-OEB-only-cols) + 1 data-gated + `pyarrow`-gated real `OBRA CIVIL` concept (`stage_b → join_intermediate → write_release → load_items + load_modifications → join` is 1:1; views preserve the `item_key` set).
- `pytest tests -q` → **719 passed, 1 skipped** (was 703 + 1; **+16** new, all passing in César's tree — `pyarrow` + OBRA CIVIL data present; the lone skip remains Sprint 12's `new_param` brace audit). The `pyarrow`/data-gated tests **skip, never fail**, in any tree lacking the dep or the intermediate data. CLI no-subcommand → usage on stderr, exit 2.

**Decisions made and rationale:**
- **G2 over G3/A3.** G2 directly continues G1 and is fully unblocked (consumes the two release files as-is). G3 is documentation — better written *after* the loader API it must document exists. A3 (the concrete `LLMClient` transport that unblocks the Phase F pilot) is a different track, its own dedicated sprint. One module per sprint (Sprint 19 `metadata`, 20 `review`, 21 `packaging`, 22 `loaders`).
- **Read-only, builds on `packaging`, no new on-disk artifact.** `loaders` calls `packaging.read_*` rather than re-parsing — the file-format contract lives in one place (G1), the consumer ergonomics in another (G2). Every projection is an in-memory, re-derivable frame; G2 writes **no** `_long_norm`/`_short_norm`/`_feats` Parquet, preserving G1's "two files are the canonical release" invariant.
- **`join()` re-attaches what the Parquet deliberately dropped — 1:1 and fail-loud.** G1 keeps the ragged `modifications` log in the sidecar to keep the columnar table flat; `join()` is the in-memory reunion for consumers wanting per-row provenance. A sidecar key absent from items (or vice-versa) raises `LoaderError` before returning — a partial release must never silently drop or duplicate rows. The join does not mutate its input (returns a sorted copy).
- **Views mirror the OEB *record subset*, not its LlamaIndex column list.** `text` + `text_norm` + keys + slice metadata; no fabricated `id`/`ud`/`concept` (an OEB-document concern the synthetic §2.3 record never carried). `text_norm` reuses `normalize_text` verbatim, so the synthetic lexical column matches the OEB `_norm` columns byte-for-byte; it is derived in-memory, never stored (the G1-deferred "feats pass" without a new file or dep).
- **`pyarrow` stays gated; the stdlib JSONL path stays always-on** — same rule as Sprint 21. `load_modifications` is always-on stdlib; everything that reads/returns a frame is `pytest.importorskip("pyarrow")`-gated (the join-mismatch unit is `pandas`-only, no Parquet engine). "Zero failures in any tree" holds.
- **`loaders.py` imports `packaging` + `taxonomy` + `utils.config` + `utils.text_processing` + `pandas` (lazy) + stdlib only** — never `stage_b` / `run_synthetic` / `stage_runners` / `review` / `mutator` / any `layer_*`. The consume path is `packaging.read_* → join/project`; the generation and review stacks are not in it.

**Problems encountered / resolved:**
- The hand-written sidecar JSONL fixture first used placeholder layer tokens (`"L1"`/`"L3"`); `Modification.from_dict` validates against the `Layer` enum (`param_value`/`text_variable`/…), so it failed loud. Fixed the fixture to the real enum values (`synonym_label`→`param_value`, `paraphrase`→`text_variable`) — confirming the read path reconstructs `Modification`s strictly.
- Same `WinError 5` tmp-cleanup symlink trap as prior sprints, sidestepped with `--basetemp` (environment-only).

**What changed in the plan:** G2 closed. The protocol §3 `Dataset packager + loader utilities` row flips 🟡 (G1 ✅ / G2 ❌) → ✅ (G1–G2 done). G3 (`DATA_CARD.md` / README "Synthetic Variant") and G4 (`HANDOFF.md`) remain; A3 is the F-pilot prerequisite.
**Next step:** Sprint 23 — Phase G (G3 docs / G4 handoff) and/or **A3** (concrete LLM transport) to unblock the F-phase pilot.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped the ✅ `loaders.py` file-map row; recorded the read-only / build-on-`packaging` / join-1:1-fail-loud / long-short-projection / derived-`text_norm` / no-new-artifact decisions near the `packaging.py` note; prepended the "After Sprint 22" history entry.

---

### Sprint 21 — Phase G Task G1 (release packaging: items Parquet + modifications sidecar JSONL)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_21.md`](sprints/SPRINT_21.md)
**Tasks from backlog:** G1 (dataset packager — the durable BC3CAT-Syn release artifact). Ships as one pure library + thin CLI, [`src/synthetic/packaging.py`](../../src/synthetic/packaging.py). Loader utilities (G2) and the data card / README (G3) are later Phase-G sprints.

**What was done:**
- **Created [`src/synthetic/packaging.py`](../../src/synthetic/packaging.py).** Packages `metadata.join_intermediate()` output into the two-file release (protocol §7): `items_to_frame(items)` builds a `pandas.DataFrame` with frozen `ITEM_COLUMNS`, one row per item sorted by `item_key`, `params` nested dict, `modification_types` as `list[str]`, **no** `modifications` column; `modifications_sidecar(items)` emits one `{"item_key", "modifications"}` dict per item (baseline → `[]`); `write_items_parquet`/`write_modifications_jsonl` are atomic (`.tmp` rename, sidecar fail-loud on duplicate `item_key`); `write_release(items, *, out_dir=None)` validates (E2 `validate_items`) **before** any write and emits both files under `SYNTHETIC_PROCESSED_DIR`; `read_items_parquet`/`read_modifications_jsonl` are the minimal round-trip read (full loader is G2). `main(argv)` is a thin `build` argparse CLI. `pandas`/`pyarrow` are imported **lazily inside** the frame/Parquet functions so the module (and the stdlib sidecar path) stays importable in a tree without them.
- **Created [`tests/synthetic/test_packaging.py`](../../tests/synthetic/test_packaging.py)** — always-on stdlib tier (`ITEM_COLUMNS` pin, sidecar shape/round-trip/dedup, validate-first no-partial on the JSONL side, import-hygiene + no-side-effects, CLI no-subcommand) + `pyarrow`-gated tier (`items_to_frame` schema/sort, no-`modifications`-column, Parquet atomic round-trip, byte-identical determinism, 1:1 file join) + 1 data-gated + `pyarrow`-gated real `OBRA CIVIL` concept (`stage_b → join → write_release → reread → 1:1 join`).

**Key results:**
- `pytest tests -q` → **703 passed, 1 skipped** (was 683 + 1; **+20** new, all passing in César's tree — `pyarrow` 21.0.0 + OBRA CIVIL data present; the lone skip remains Sprint 12's `new_param` brace audit). The `pyarrow`/data-gated tests **skip, never fail**, in any tree lacking the dep or the intermediate data. CLI no-subcommand → usage on stderr, exit 2.

**Decisions made and rationale:**
- **G1 over F1–F2.** The Phase F real pilot (F1–F2) is **blocked on A3** — there is no concrete `LLMClient` transport in the tree (`llm_proposer.py` defines only the Protocol; `variant_proposer.py` / `run_synthetic.py` both note A3 as not-owned). A real pilot whose deliverable is per-type acceptance rate cannot run on a stub. G1 is fully unblocked: it consumes `SyntheticItem`s as-is. So G1 is this sprint; A3 (to unblock F) is its own dedicated sprint.
- **Two files, one key** (protocol §7): `BC3CAT_Syn_items.parquet` (flat columnar record for retrieval/slicing) + `BC3CAT_Syn_modifications.jsonl` (ragged per-`item_key` log), joining 1:1 on `item_key`.
- **The items table is the §2.3 record, not the OEB `_feats` schema.** Columns are the proposal §2.3 per-item record plus the `concept_key` grouping back-pointer. The derived `_norm`/`_feats` lexical columns (`text_norm`, `tokens_word`, …) are mechanically re-derivable from `texto`/`resumen` by the feature stage and are **not** part of the release record — deferred (G2/feats pass).
- **Deviation from the sprint's decision-2 column list — documented.** The spec's decision 2 listed `parent_key` *and* `concept_key`. The canonical §2.3 record (`RESEARCH_PROPOSAL.md` lines 88–109) and the `SyntheticItem` dataclass carry **no `parent_key` field**; `SyntheticItem` exposes only `concept_key` (the concept group key, which itself ends in `$` and *is* the parent-concept key). Inventing a separate `parent_key` column would either duplicate `concept_key` or fabricate data, so `ITEM_COLUMNS` ships the §2.3 record + `concept_key` only. If a downstream consumer ever needs an explicit `parent_key`, it is a one-liner derivation in the G2 loader, not a G1 packaging concern.
- **One row per item with both `resumen` and `texto`** — not the OEB long/short two-file split (OEB split because they were separate LlamaIndex document sets; a synthetic item inherently has both, and a single keyed table makes the sidecar join trivial). The long/short projection, if needed, is a G2 loader one-liner.
- **Validate before you write.** `write_release` (and `items_to_frame`) run E2's `validate_items` first and re-raise its `SchemaError` as `PackagingError`; a malformed record fails loud with **no partial release** on disk.
- **`pyarrow` is the synthetic suite's first non-stdlib dep — gate it, don't fail on it.** `pandas`/`pyarrow` are already required by the *main* pipeline (so no new repo dependency), but the synthetic test tier was stdlib-only through Sprint 20. Parquet tests use `pytest.importorskip("pyarrow")`; the sidecar JSONL tests stay always-on stdlib — preserving "zero failures in any tree".
- **Determinism + atomic writes.** Rows emitted sorted by `item_key`; both files written via `.tmp` rename; run-twice-equal bytes is a pinned invariant (a release artifact must be reproducible).
- **`packaging.py` imports `metadata` + `taxonomy` + `utils.config` + `pandas`/`pyarrow` + stdlib only** — never `stage_b` / `run_synthetic` / `stage_runners` / `review`. The release path is `join_intermediate → validate → write`; the sampler and the generation stack are not in it.

**Problems encountered / resolved:**
- Same `importlib.reload` class-identity trap as Sprints 19–20: the no-side-effects test rebinds the module dict the functions close over, so a function reached by its top-level imported name raises the *reloaded* `PackagingError`, ≠ the top-level-imported `PackagingError`. Resolved by routing the `pytest.raises`-sensitive tests through the `packaging.` module object (functions stay generation-stable for value tests; only exception-identity tests need the prefix).
- The committed-data tmp-cleanup `WinError 5` (stale `pytest-current` symlink) sidestepped with `--basetemp="$TEMP/pt_s21"` as in prior sprints (environment-only).

**What changed in the plan:** G1 closed. G2 (loader utilities `loaders.py` + the long/short projection) and G3 (`DATA_CARD.md` / README) remain; A3 (concrete `LLMClient` transport) is the prerequisite for the Phase F real pilot. The protocol §3 `G1–G2` row stays ❌ pending G2, annotated "G1 ✅ / G2 pending".
**Next step:** Sprint 22 — Phase G (G2 loaders / G3 docs) and/or **A3** (concrete LLM transport) to unblock the F-phase pilot.

**CLAUDE_SYNTHETIC.md updated:** yes — added the ✅ `packaging.py` file-map row; flipped the two `data/synthetic/processed/BC3CAT_Syn_*` artifact rows ❌ → ✅; recorded the two-file-split / §2.3-columns-not-`_feats` / one-row-with-both-texts / `parent_key`-deviation decisions; prepended the "After Sprint 21" history entry.

---

### Sprint 20 — Phase E Tasks E3 (validation sampler) + E4 (reviewer harness)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_20.md`](sprints/SPRINT_20.md)
**Tasks from backlog:** E3 (stratified validation sampler) and E4 (domain-reviewer harness). Both ship as one pure library + thin CLI, [`src/synthetic/review.py`](../../src/synthetic/review.py). This sprint builds the *machinery*; the real review pass + `QUALITY_REPORT.md` is F4; Parquet packaging is G1.

**What was done:**
- **Created [`src/synthetic/review.py`](../../src/synthetic/review.py).** **E3** — `stratify(items)` buckets `SyntheticItem`s into `(concept_key, ModificationType)` cells (baselines excluded; a stacked item joins *every* one of its types' cells); `sample_review_queue(items, *, coverage=0.10, floor=5, full_coverage_types={NEW_PARAM}, seed=0)` is the deterministic core — full coverage for `new_param`, otherwise `n = min(size, max(floor, ceil(coverage·size)))` per cell, a seeded draw over each cell's sorted `item_key`s, the union de-duplicated by `item_key` into one `ReviewTask` (whose `strata` lists every cell it was a candidate for), returning `(list[ReviewTask], CoverageReport)`. `write_queue`/`read_queue` are atomic JSONL. **E4** — `Verdict` (grammatical / semantic_preserved / axis_distinguishable `Optional[bool]` / metadata_accurate + notes) + `write_verdicts`/`read_verdicts` (JSONL keyed by `(item_key, reviewer)`, fail-loud duplicate via `ReviewError`); `agreement(verdicts)` returns per-dimension `AgreementStat` (percent agreement + hand-rolled Cohen's κ) over the ≥2-reviewer subset, `axis_distinguishable` scored only over the `new_param` subset. `main(argv)` is a thin `build`/`agree` argparse CLI.
- **Added `SYNTHETIC_REVIEW_DIR = SYNTHETIC_DATA_ROOT / "review"`** to [`../../src/utils/config.py`](../../src/utils/config.py).
- **Created [`tests/synthetic/test_review.py`](../../tests/synthetic/test_review.py)** — 27 always-on functions + 1 data-gated real-concept (`OBRA CIVIL`) sample.

**Key results:**
- `pytest tests -q` → **683 passed, 1 skipped** (was 654 + 1; +28 always-on, +1 data-gated, the lone skip is Sprint 12's `new_param` brace-audit). The data-gated review-sample ran (OBRA CIVIL data present) and confirms the sampled queue ⊆ joined items with a self-consistent coverage report. Hand-checked κ: a 2×2 grammatical table of 4 (T,T) + 4 (F,F) + 1 (T,F) + 1 (F,T) gives `percent_agreement = 0.8`, `cohen_kappa = 0.6`.

**Decisions made and rationale:**
- **The unit of review is the `SyntheticItem`; the stratum is `(concept_key, ModificationType)`.** Coverage is a per-cell property, reviewer effort a per-item property; the two are reconciled by de-duplicating the per-cell candidate draws into exactly one `ReviewTask` per `item_key`.
- **`new_param` is sampled at 100 %** (highest semantic-collision risk, proposal §4); every other type at the `min(size, max(floor, ceil(coverage·size)))` floor/fraction rule. `full_coverage_types`, `coverage` (0.10), and `floor` (5) are **arguments** seeded with the proposal §10.3 defaults, not constants baked into the logic — F2 retro may revise them.
- **Sampling is deterministic and seeded** (`random.Random` over a per-cell string seed `f"{seed}\x00{concept}\x00{type}"`, applied to the cell's sorted `item_key`s). Run-twice-equal is a pinned invariant; a different `seed` may change *which* items, not *how many*.
- **Zero-modification baselines are excluded from the queue, counted in `CoverageReport.baselines`** (mirrors Sprint 19's keep-but-flag stance — here flag-and-skip).
- **Agreement only where there is agreement to measure** — percent + Cohen's κ over the ≥2-reviewer subset; κ is `None` when undefined (no ≥2-reviewer items, or a zero-expected-disagreement degenerate table). `axis_distinguishable` is agreed only over the `new_param` subset (verdicts where it is non-`None`).
- **E4 reviews the diff, not the baseline.** Semantic-preservation review works off the per-`Modification` `original`/`new` fragments + synthetic text already on the record; full original-vs-synthetic re-expansion is baseline-dependent and deferred to F4 (same deferral pattern Sprint 19 used for `original_key`-existence). `review.py` imports `metadata` + `taxonomy` + `utils.config` + stdlib only — never `stage_b` / `run_synthetic` / `stage_runners`.

**Problems encountered / resolved:**
- The no-side-effects test `importlib.reload(review)` rebinds the module's classes to a fresh generation; the verdict round-trip / duplicate-key tests defined after it then failed on class-identity mismatch (read-back `Verdict`/`ReviewError` were the reloaded generation, the top-level-imported fixtures the stale one). Resolved with the Sprint 19 pattern — route the equality/`pytest.raises`-sensitive verdict tests (and the `_v` fixture) through the `review.` module object so they are co-generation with the reloaded objects.
- The committed-data tmp-cleanup `WinError 5` (stale `pytest-current` symlink) was sidestepped with `--basetemp` as in Sprint 19 (environment-only).

**What changed in the plan:** E3 + E4 closed; Phase E is complete. Next is Phase F (F1–F2: single-concept pilot generation + retro, then F3 full-scale generation, F4 the real validation pass that *uses* `review.py` to produce `QUALITY_REPORT.md`) and/or Phase G (G1 Parquet + sidecar JSONL packaging).

**CLAUDE_SYNTHETIC.md updated:** yes — flipped the `review.py` row ❌ → ✅ with the stratum-key / 100 %-`new_param` / coverage-default annotations; added `SYNTHETIC_REVIEW_DIR` to the config-path row; prepended the "After Sprint 20" history entry.
**Next step:** Sprint 21 — Phase F (F1–F2 single-concept pilot + retro) and/or Phase G (G1 release packaging).

---

### Sprint 19 — Phase E Tasks E1 (metadata join) + E2 (schema validator)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_19.md`](sprints/SPRINT_19.md)
**Tasks from backlog:** E1 (variant-grained → item-grained metadata join) and E2 (fail-loud schema validator). Both ship as one pure library, [`src/synthetic/metadata.py`](../../src/synthetic/metadata.py); Parquet/JSONL serialization stays Phase G (G1).

**What was done:**
- **Created [`src/synthetic/metadata.py`](../../src/synthetic/metadata.py).** `@dataclass(frozen=True) SyntheticItem` carries the release fields `(item_key, original_key, params, resumen, texto, variante_id, modification_types, modification_count, modifications)` plus a `concept_key` back-pointer; `to_dict()` mirrors proposal §2.3 exactly (enum → `.value`, `modifications` via `Modification.to_dict`, **no** `concept_key` key). `join_variant_payload(payload)` is the pure core — one `SyntheticItem` per `(leaf_key, item)` in `payload["items"]`, fanning the variant's modification log out across its leaves. `join_variant_file` / `join_intermediate` walk the on-disk per-variant JSON in sorted, deterministic order. `validate_item` / `validate_items` + `class SchemaError(ValueError)` are the fail-loud E2 surface.
- **Created [`tests/synthetic/test_metadata.py`](../../tests/synthetic/test_metadata.py)** — 28 always-on functions (hand-built Stage-B-shaped payloads: L1, PD-stacked, all-skipped baseline) + 1 data-gated roundtrip that materialises one real `OBRA CIVIL` concept through `stage_b` into `tmp_path`, joins, and validates.

**Key results:**
- `pytest tests -q` → **654 passed, 1 skipped** (was 626 + 1; +28 always-on, the lone skip is Sprint 12's `new_param` brace-audit). The data-gated test ran (OBRA CIVIL data present) and confirms every joined `SyntheticItem` for a baseline variant carries `modification_count == 0` and an `original_key` that is a real chapter stage-5 leaf key.

**Decisions made and rationale:**
- **The per-item traceability triple is `(item_key, original_key, variante_id)`.** `item_key = f"{leaf_key}_syn_{variante_id}"` (the mutated leaf key keeps `new_param` siblings that share an `original_key` globally unique); `variante_id` is Stage B's `variant_id` verbatim (`{condition}_{sha1[:10]}`, no re-derivation).
- **`original_key = leaf_key[:-K]`**, where `K` = count of *applied* (`status != "skipped"`) `new_param` modifications in the variant. `apply_new_param` appends each new axis last, and `transform_data` builds the leaf-key suffix in `parameters` insertion order, so each applied `new_param` contributes exactly one trailing label char. Non-PD variants: `K = 0`, `original_key == leaf_key`. E2 validates this *structurally* (`original_key` is a prefix of the `item_key` leaf segment) — asserting the key names an actually-existing baseline row is deferred to F4/G1 where the baseline catalog is loaded anyway.
- **Recompute, don't trust.** E1 derives `modification_count == len(modifications)` and `modification_types == [m.type for m in modifications]` from the applied log; the payload's pre-computed copies are advisory (a fixture shipping a *wrong* `modification_types` is corrected by the join). E2 then cross-checks the two cannot drift.
- **Zero-modification (all-skipped) variants join as valid baselines** (`modification_count == 0`, empty types/mods, `original_key == leaf_key`). Whether to *drop* them from the released benchmark is a Phase F budget decision, not E1/E2's concern — keep them, flag via the count.
- **`metadata.py` imports neither `stage_b` nor `run_synthetic`.** The on-disk per-variant JSON payload is the contract; the join reads it directly and rebuilds `Modification`s via `Modification.from_dict`. Stdlib + `taxonomy` + `utils.config` only — pinned by source + `__dict__` audits.

**Problems encountered / resolved:**
- The no-side-effects test `importlib.reload(metadata)`, which rebinds `SchemaError`/`validate_item` to a fresh generation; the `pytest.raises(SchemaError)` validator tests defined after it then failed on exception-identity mismatch (caught vs. raised classes differed). Resolved by referencing the exception-sensitive surface through `metadata.` (co-generation with the reloaded objects) rather than the stale top-level imports.
- A stale `pytest-current` symlink under `%TEMP%\pytest-of-cesar` raised `WinError 5` during pytest's startup tmp-cleanup; ran with `--basetemp` pointed at a fresh dir to sidestep it (environment-only, no code impact).

**What changed in the plan:** E1 + E2 closed. Phase E continues with E3–E4 (`review.py` — stratified validation sampler + domain-reviewer harness). Phase G (G1) will package `SyntheticItem` records into `BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl`.

**CLAUDE_SYNTHETIC.md updated:** yes — added ✅ `metadata.py` row to the file map; recorded the `(item_key, original_key, variante_id)` join-key triple + the `original_key = leaf_key[:-K]` rule near the `Modification`-record schema; prepended the "After Sprint 19" history entry.
**Next step:** Sprint 20 — Phase E (E3–E4: `review.py` — stratified validation sampler + domain-reviewer harness).

---

### Sprint 18 — Phase D Tasks D2 (Stage-B half) + D3 (cache hygiene)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_18.md`](sprints/SPRINT_18.md)
**Tasks from backlog:** D2 (Stage-B: apply catalog rules + rerun the pipeline + emit raw mutated items) and D3 (cache hygiene).

**What was done:**
- **Created [`src/synthetic/stage_b.py`](../../src/synthetic/stage_b.py)** — the Stage-A→Stage-B join. `apply_variant_rules(stage2_concept, concept_key, rules)` partitions the variant's pre-composed rules by layer (`TYPE_TO_LAYER`) and threads the single-concept stage-2 dict through **PD → L1 → L2 → L3**, preserving the catalog's intra-layer order and concatenating the applied `Modification` logs; a rule that fails to apply is skipped-and-logged (never patched). `materialize_variant` slices `{concept_key: stage2_json[concept_key]}`, applies, runs `run_stages_3_to_7` once, and returns a frozen `MaterializedVariant{variant_id, condition, concept_key, modification_types, modifications, items}`. `materialize_catalog_entry` / `run_stage_b` write one atomic JSON per variant under `data/synthetic/intermediate/{concept}/{variant_id}.json` (the payload carries the metadata + modification log + regenerated items).
- **Created [`src/synthetic/cache_hygiene.py`](../../src/synthetic/cache_hygiene.py)** — `stale_cache_paths` (pure: enumerates `processed/*.pkl`, `llamaindex/` contents, stray `chunk_*.json` left by the s04/s05 chunked drivers, and `**/.ipynb_checkpoints`) + `clear_caches` (returns the would-delete list; only unlinks when `dry_run=False`; `dry_run=True` is the default). Documented the cleared-path list in [`../../CLAUDE.md`](../../CLAUDE.md).
- **Created [`tests/synthetic/test_stage_b.py`](../../tests/synthetic/test_stage_b.py) (28) + [`tests/synthetic/test_cache_hygiene.py`](../../tests/synthetic/test_cache_hygiene.py) (10)** — 38 always-on functions + 1 data-gated stage-5-granularity slice-equivalence test.

**Key results:**
- `pytest tests -q` → **626 passed, 1 skipped** (was 588 + 1; +38 always-on, the lone skip is Sprint 12's `new_param` brace-audit). The data-gated test reproduces the committed `OBRA_CIVIL_stage5.json` items for the smallest multi-leaf concept from its unmutated stage-2 slice.
- Inline fixtures pin all four propagations through the rerun: an L1 `synonym_label` value rewrite surfaces in the regenerated `resumen`; an L2 fragment rewrite (`(%B=="a")` double-equals/quoted-label form, the form s04 resolves cleanly) survives `run_stage4`; an L3 substring edit survives `run_stage5`; a stacked PD+L1+L2+L3 variant lands all four, logged in PD→L1→L2→L3 order.

**Decisions made and rationale:**
- **One parent-level injection, not four.** Reading the mutator implementations contradicted Sprint 17's "four interleaved injection points" narrative: `layer_l1`/`layer_l2`/`layer_l3`/`layer_pd` *all* index the same concept-keyed stage-2 record (`stage_json[concept_key][…]`). None can consume a `run_stage3+` output — after s03 the dict is leaf-keyed (no `concept_key`); by s04 the `text_variables` are resolved `{evaluated: …}` dicts (no raw `"frag"*(cond)` for L2); by s05 the templates are instantiated (no `$`-tokens for L3). The `layer_l2`/`layer_l3` docstrings' "stage-3/4 JSON" labels name the *conceptual target stage*, not the consumed dict shape. So Stage B applies PD→L1→L2→L3 to the stage-2 record, then reruns once — `CLAUDE_SYNTHETIC.md` line 139 ("mutates the parent-level definition before s03") already had it right. Corrected the Stage-Hook Integration Note + Mutation-Architecture framing.
- **Stage A and Stage B stay in separate modules; the Sprint-16 tripwire is kept, not deleted.** Putting apply-and-rerun into `run_synthetic.py` would import `mutator` there and trip the deliberate "scope tripwire." Stage B lives in `stage_b.py`; `run_synthetic` stays Stage-A-pure. Both audits pinned (re-asserted the no-`mutator` tripwire; added a no-`run_synthetic`-import audit for `stage_b`).
- **Synthetic dedup is per-variant.** Stage B's `run_stage7` sees only one variant's leaves, so it dedups within the variant; the baseline chapter-wide dedup was a packaging artefact of bundling 25+ concepts into one file. Consequence: the faithful-rerun equivalence gate is at **stage-5 granularity** (pre-dedup, per-item independent), not stage-7.
- **`clear_caches` deletes nothing by default.** `dry_run=True` is the safe default; deletion is opt-in and tested only against `tmp_path`, never the real `data/`.

**Problems encountered / resolved:**
- An early inline fixture used the `(%B=a)` single-equals/unquoted-label condition form; s04 substitutes `%B` with the value *before* evaluating, destroying the comparison, so the formula resolved garbled. The real OBRA CIVIL catalog uses `(%B=="a")` (double-equals, quoted label), which `is_comparison_placeholder` detects and resolves via the *label* — switching the fixture to that form gave clean, deterministic resolution.

**What changed in the plan:** D2 + D3 closed. Phase E (`metadata.py` — join raw per-variant items + modification logs into the flat Parquet/JSONL release schema + schema validator) is next.

**CLAUDE_SYNTHETIC.md updated:** yes — corrected Stage-Hook Integration Note to the single-injection model; added ✅ `stage_b.py` + `cache_hygiene.py` rows; flipped `data/synthetic/intermediate/` ❌ → ✅; prepended the "After Sprint 18" history entry.
**Next step:** Sprint 19 — Phase E (E1–E2: `metadata.py` release-schema join + schema validator).

---

### Sprint 17 — Phase D Task D1: stage hooks (importable pure stage runners) + equivalence harness
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_17.md`](sprints/SPRINT_17.md)
**Tasks from backlog:** D1 only. Sprint 16's successor line bundled D1 with the D2 Stage-B rerun; this sprint ships **D1 alone** (the four importable stage runners + the golden equivalence proof) and defers the Stage-B rerun to Sprint 18 — D1 is a self-contained faithful-extraction problem where the risk lives; the rerun is a wiring problem that *depends on* D1 being proven correct.

**What was done:**
- **Created [`src/synthetic/stage_runners.py`](../../src/synthetic/stage_runners.py).** Public surface: `run_stage3` (Cartesian expansion), `run_stage4` (text-variable resolution, both passes), `run_stage5` (template instantiation + field filter), `run_stage7` (in-memory dedup), and `run_stages_3_to_7` (chains the four, **s06 skipped**, no rule injection). Each runner deep-copies its input, performs no disk IO, has no module-level side effects, and is mutation-blind (imports only stdlib + `src/utils`, never the synthetic mutation stack). The core transforms were **relocated verbatim** from the s03/s04/s05/s07 notebook cells (extract-and-reimport, not re-implement) — honouring the protocol's "no changes to the stages' internal logic"; the golden harness is the contract that proves the relocation was faithful.
- **Refactored s03/s04/s05/s07 notebooks** to `from synthetic.stage_runners import …` their core transform, keeping each notebook's own file-IO / chunking / logging driver cells. s07's two file-based steps (`marcar_duplicados`, `filter_json`) now delegate to the pure helpers `_mark_duplicates` / `_filter_json`.
- **Created [`tests/synthetic/test_stage_runners.py`](../../tests/synthetic/test_stage_runners.py)** — 27 always-on unit tests (one transform + purity + determinism per stage, the chain, an import-hygiene audit, a no-side-effects-at-import check) + a 4-test data-gated golden tier.

**Key results:**
- `pytest tests -q` → **588 passed, 1 skipped** (was 557 + 1 at Sprint 16; +31 new functions). The lone skip is Sprint 12's `new_param` brace audit; 0 data-gated golden skips in César's tree (intermediate JSONs present).
- **Golden byte-equivalence proven for OBRA CIVIL**: `run_stage3/4/5/7` each reproduce the committed `OBRA_CIVIL_stage{3,4,5,7}.json`, modulo JSON normalisation (see the tuple finding below). stage3=126,938 leaf items; stage7=111,644 unique items.

**Decisions / rationale — the formula-translate reconciliation (the load-bearing finding):**
- s04 carried an **inline copy** of `translate_formula_to_python` / `quote_second_term` that had **drifted** from the canonical `utils.z_formula_processing` exports. Three concrete differences in the inline `translate`: (1) **no `"=" → "=="` mapping**; (2) operator substitution anchored with `\b…\b` word boundaries; (3) it **never calls `quote_second_term`** (which the notebook defines but leaves dead). The protocol assumed the two were equivalent and said to import the util; they are **not**.
- **Empirical test (8,000-item chapter prefix; stage4 is per-item independent so a prefix is a sound probe):** the inline variant matches golden on **0 mismatches**; the canonical util mismatches on **324** items (it rewrites already-doubled `==` into `====`, so the eval fails and the formula falls through unevaluated). On the full 126,938-item chapter the inline variant likewise reproduces golden.
- **Resolution:** the golden byte-equivalence acceptance gate is binding, so `run_stage4` **preserves the inline notebook semantics**, relocated as the private `_translate_formula_to_python_s04`; the canonical `quote_second_term` is still imported for parity but the active translate is the s04 variant. This is the "surface the divergence, don't silently pick" path the sprint mandated — recorded here rather than silently swapped. Two tests pin the decision (`test_run_stage4_preserves_inline_translate_semantics`, `test_run_stage4_does_not_use_canonical_util_translate`). **Open item for a future sprint:** decide whether to reconcile the util itself to the notebook behaviour (or vice-versa) repo-wide — out of scope for D1's faithful extraction.

**Problems encountered & resolved:**
- **stage4 golden initially showed 324 differing items.** Root cause was **not** a logic error: s04's `evaluate_formula` returns a Python **tuple** when a resolved formula is a comma-separated expression; the notebook's `json.dump` serialises that tuple to a JSON array, so the committed golden (re-loaded) holds a **list**. In-memory `tuple != list` even though they serialise identically. Confirmed all 324 vanish after a JSON round-trip. The golden tests compare values **JSON-normalised per item** (`json.loads(json.dumps(...))`) — exactly the "modulo json" equivalence the acceptance specifies — and keep memory bounded on the large chapter files.
- **s06 is not extracted:** it writes no file (the "stage6" file is s07's own `marcar_duplicados` marking output); the rerun chains s03→s04→s05→s07 and skips s06.

**CLAUDE_SYNTHETIC.md updated:** yes — `stage_runners.py` added to the file map; s03/s04/s05/s07 noted as importing their core from it; "After Sprint 17" block prepended to Sprint History.
**Next step:** Sprint 18 — Phase D Task D2 (Stage-B half): consume the variant catalog, apply rules across the four injection points (PD/L1 before s03, L2 before s04, L3 before s05) by interleaving `mutator.apply_*` between these D1 runners, rerun the pipeline in memory, and emit raw synthetic items into `data/synthetic/intermediate/`; + D3 cache hygiene.

---

### Sprint 16 — Phase D Task D2 (Stage-A half): synthetic orchestrator
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_16.md`](sprints/SPRINT_16.md)
**Tasks from backlog:** D2 (Stage-A half). The protocol's §5 D2 sentence ("materialise mutated stage JSONs, rerun s03→s07, emit raw items") spans two separable halves. Sprint 16 ships **half 1 only**: the concept-loop driver that *populates* the variant catalog (propose → emit → compose → persist). Half 2 — applying rules and rerunning the pipeline — is Stage B (Sprint 17), forced apart by the architecture: rule application is rule-vs-data (needs live stage JSON), is interleaved across the four injection points (PD/L1 → s03 → L2 → s04 → L3 → s05), and depends on D1 stage hooks that don't exist yet (s03/s04/s05 are notebooks, not importable functions).

**What was done:**
- **Created [`src/synthetic/run_synthetic.py`](../../src/synthetic/run_synthetic.py).** Public surface:
  - `CONDITION_SPECS: dict[str, ConditionSpec]` — module constant, the 17-label protocol condition table (6 `single_L1_*` + 3 `single_L2_*` + 2 `single_L3_*` + `new_param_only` + `stacked_2/3/4/5plus` + `full_random_mix`), built once at import by `_build_condition_specs()` off `ModificationType` (so a future 13th type surfaces its `single_*` condition automatically — same forcing-function as Sprint 11's `COMPATIBILITY_MATRIX` / Sprint 12's `PROMPT_FILENAMES`). `ConditionSpec` is frozen `{pool, stack_depth, sampled}`.
  - `plan_concept_variants(stage_json, concept_key, conditions, *, rng) -> list[VariantPlan]` — pure planner. `single_*`/`new_param_only` are exhaustive (one single-attempt plan per `enumerate_targets` result; a condition with no eligible targets contributes zero plans). `stacked_n` samples `n` distinct `(mtype, target)` attempts from the union over the pool (degrades to `k<n` if fewer exist; dropped at 0). `full_random_mix` samples depth `d = rng.randint(2, min(MAX_MIX_DEPTH, available))`. `variant_id` is per-concept monotonic across conditions.
  - `run_variant(...) -> _VariantOutcome` — per attempt: render prompt → `propose_variant` → (on success) `emit_rules`, routing `EmissionResult.unmatched` into the skip log as `unmatched_payload_entry: ...`; one `ProvenanceRecord` per attempt regardless of outcome. After all attempts, a single `compose_rules` over the accumulated batch; composition skips join the skip log; a `VariantRecord` lands only if admissible rules survive.
  - `run_concept(...) -> (VariantCatalogEntry, Path)` — seeds `random.Random(seed)`, plans, runs, aggregates, `write_catalog_entry`.
  - `run_catalog(...) -> list[Path]` — outer loop; each concept gets a stable per-concept seed via `_seed_for(concept_key, base_seed)` (`sha256`-derived, not per-process-salted `hash()`), so the same concept samples identically regardless of batch composition or order.
- **`compose_rules` yes, `mutator.apply_*` no.** Composition is state-blind rule-vs-rule validation (same-target dedup, layer-dependency conflict, PD→L1→L2→L3 ordering) and belongs in Stage A so the catalog records *admissible, ordered* rules. A test audits that `run_synthetic` never binds `mutator` — a scope tripwire that forces the D1/Stage-B conversation the day someone wires application in.
- **Created [`tests/synthetic/test_run_synthetic.py`](../../tests/synthetic/test_run_synthetic.py)** — 31 functions (stub/const `LLMClient`, inline stage-JSON fixtures, zero notebook execution, zero real IO).

**Key results:**
- `pytest tests -q` → **557 passed, 1 skipped** (was 526 + 1 at Sprint 15; +31 new functions). Zero failures, zero new skips, zero edits to surviving tests or to any prior `src/synthetic/*.py` module.
- End-to-end gate holds through the orchestrator: a `run_concept`-emitted `synonym_label` rule applies via `layer_l1.apply_synonym_label` without raising.

**Decisions / rationale:**
- The variant catalog is the **Stage-A/Stage-B decoupling seam** (C4: "pipeline reruns *consume* this catalog"). Splitting D2 at that seam is architecture-forced, not convenience: bundling both halves would either pull notebook execution into pytest (breaking the no-live-IO discipline) or ship an untested rerun path.
- Condition matrix stays a Python constant (not YAML) — the condition→type *mapping* is structural; `variant_budgets.yaml` is for Phase F *budgets*.

**Problems encountered:** none blocking. (A Windows pytest atexit tmp-cleanup `PermissionError` is cosmetic — emitted after the run reports green, unrelated to test outcomes.)

**CLAUDE_SYNTHETIC.md updated:** yes — `run_synthetic.py` flipped ❌ → ✅ in the file map; "After Sprint 16" block prepended to Sprint History.
**Next step:** Sprint 17 — Phase D Task D1 (stage hooks wrapping s03/s04/s05 as importable functions) + the D2 Stage-B half (consume the catalog, apply rules across the four injection points, rerun s03→s07, emit raw synthetic items into `data/synthetic/intermediate/`).

---

### Sprint 15 — Phase C Task C4 (variant catalog) + slot-extraction shim + payload-to-rule lift
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_15.md`](sprints/SPRINT_15.md)
**Tasks from backlog:** C4 — author `src/synthetic/variant_catalog.py` writing JSON-per-concept artefacts under `data/synthetic/variants/` — plus the two Sprint-14-deferred concerns required to feed it: the per-concept slot extractor (`src/synthetic/slot_extractor.py`) and the validated-payload → Phase-B-rule emitter (`src/synthetic/rule_emitter.py`). The three concerns share the same per-concept information flow (stage JSON → slots dict → validated payload → emitted rules → final `Modification` records); bundling them keeps the boundaries sharp without forcing a temporary intra-sprint shim.

**What was done:**
- **Created [`src/synthetic/slot_extractor.py`](../../src/synthetic/slot_extractor.py).** New module exposing three public functions:
  - `enumerate_targets(stage_json, concept_key, modification_type) -> Iterator[Any]` — yields one `target_id` per viable application site within the concept. Per-type semantics: L1 (six types) yields each axis key in `parameters`, sorted; L2 (three types) yields each `(var_key, condition)` tuple parsed from `text_variables[var_key]` via the narrow `_parse_l2_formula` regex; L3 omission yields each `(field, var_token)` pair where `field ∈ {"RESUMEN", "TEXTO"}` and `var_token` is each unique `$<letter>` token in the field text; L3 reorder yields each non-empty field; PD `new_param` yields exactly one `None` (LLM picks the new axis).
  - `extract_slots(stage_json, concept_key, modification_type, target_id) -> dict[str, Any]` — builds the per-type slots dict matching `variant_proposer.EXPECTED_SLOTS[mtype]` exactly. L1: `{concept, axis_label, value_list}` with `value_list = "; ".join(f"{label}: {value}" ...)`. L2: `{concept, var_key, fragment, condition}` where `fragment` is the literal-string operand bound to the condition. L3-omission: `{concept, template, var_to_omit, axis_label}` with `axis_label` best-effort-derived from `text_variables[var_to_omit]`'s first `%<axis>=` reference. L3-reorder: `{concept, template, constituents}` with `constituents = "; ".join(sorted-unique-$X-tokens)`. PD: `{concept, existing_axes_with_labels, allowlist}` with `allowlist="[]"` placeholder.
  - `concept_resumen(stage_json, concept_key) -> str` — small helper; reads `"resumen"` (lowercase, the pipeline's canonical post-s05 key) and falls back to `"RESUMEN"` (uppercase, the BC3 grammar key — present at earlier stages or in test fixtures); raises `KeyError` if neither.
  - Module-level constants: `_L1_TYPES`, `_L2_TYPES` (the same partitioning Sprint 11 uses). No import from `src/utils/z_formula_processing.py` — `_parse_l2_formula` is intentionally narrow (matches `"<literal>" * (<condition>)` and nothing else).
- **Created [`src/synthetic/rule_emitter.py`](../../src/synthetic/rule_emitter.py).** New module exposing `@dataclass(frozen=True) EmissionResult(rules: tuple[dict, ...], unmatched: tuple[dict, ...])` and `emit_rules(payload, modification_type, *, target_id, stage_json, concept_key) -> EmissionResult`. Per-type private dispatch:
  - `_emit_l1` (six types): one rule per `synonyms` / `numerals` entry; cross-references `entry["original"]` against the target axis's `value` field via a `{value: label}` lookup to derive the per-rule `value` (the value label `"a"`, not the value string `"Normal"`); LLM typos with no match append to `unmatched` instead of raising. Emitted rule: `{"type", "param", "value", "original", "new"}`.
  - `_emit_l2` (three types): one rule per call carrying `{"type", "var", "condition", "new"}`.
  - `_emit_l3_omission`: one rule carrying `{"type", "field", "original", "new"}`.
  - `_emit_l3_reorder`: same shape as omission with `mtype = REORDER`.
  - `_emit_new_param`: one rule with `param` allocated by `_allocate_axis_key(stage_json, concept_key)` (first free uppercase letter A-Z; raises `ValueError("no_free_axis_letter")` if all 26 are taken). Carries `{"type", "param", "label", "values"}` plus `metadata.{var_definition, template_patch}` as raw pass-through strings — the parsed `text_variable` / `template_patches` PD rule fields are **not** emitted (full FIEBDC-formula + template-anchor parsing deferred to Sprint 16). The minimal rule is still applicable by `layer_pd.apply_new_param` because those fields are optional in the PD rule schema.
- **Created [`src/synthetic/variant_catalog.py`](../../src/synthetic/variant_catalog.py).** New module exposing three frozen dataclasses and two functions:
  - `VariantCatalogEntry(concept_key, concept_resumen, parent_key, variants: tuple[VariantRecord, ...], skipped: tuple[Modification, ...], provenance: tuple[ProvenanceRecord, ...])`.
  - `VariantRecord(condition, modification_type, target_id_repr, rules: tuple[dict, ...])` — `condition` is the Phase-D condition label (`"single_L1_synonym_label"`, `"stacked_2"`, …); the orchestrator (Sprint 16) pins it. `target_id_repr` is `repr(target_id)` for human-readable trace.
  - `ProvenanceRecord(modification_type, rendered_prompt, raw_responses, validated_payload, skipped)` — captures everything Sprint 14's `VariantProposal` returned plus the rendered prompt (for diagnostics). Structural invariant: exactly one of `validated_payload` / `skipped` is populated.
  - `write_catalog_entry(entry, out_dir) -> Path` — atomic write via `tmp.write_text` + `os.replace`. Creates `out_dir` on-demand. UTF-8, indent=2, `ensure_ascii=False`, trailing newline. File name is `{concept_key}.json`.
  - `read_catalog_entry(path) -> VariantCatalogEntry` — strict `json.loads` + `Modification.from_dict` + `ModificationType` enum coercion; raises on malformed JSON or missing top-level keys.
- **Added three new test files — 78 individual test cases / 36 functions total.**
  - [`tests/synthetic/test_slot_extractor.py`](../../tests/synthetic/test_slot_extractor.py) — 14 functions / ~30 cases. Public surface; `concept_resumen` lowercase/uppercase/missing; per-type enumerator (L1 ×6 parametrised over `_L1_TYPES`; L2 with deterministic sorted output; L3-omission `(field, var_token)`; L3-reorder including empty-field skip; PD single `None`); `extract_slots` ×12 round-trip pinning `set(extract_slots(...).keys()) == EXPECTED_SLOTS[mtype]` for every `ModificationType`; L1 `value_list` exact-format audit (`"a: Normal; b: Rocoso"`); L2 fragment lookup pinning; L3-omission `axis_label` best-effort derivation (binding case + empty-string fallback); L3-reorder `constituents` format; PD `allowlist` placeholder; L2 unknown-condition raises; `_parse_l2_formula` empty-match raises; `_field_text` lowercase tolerance + missing-field empty; `importlib.reload` no-side-effects.
  - [`tests/synthetic/test_rule_emitter.py`](../../tests/synthetic/test_rule_emitter.py) — 16 functions / ~33 cases. Public surface; L1 happy-path ×6 over `_L1_TYPES`; L1 multi-entry emission (3 rules from 3 synonyms entries); L1 unmatched-original LLM-typo diagnostic; L1 value-label (not value-string) audit; L1 empty list → empty result; L2 happy-path ×3; L2 var+condition pin; L3-omission rule shape; L3-reorder rule shape; PD A,B,C → D axis allocation; PD A,C,E → B gap-skipping; PD 26-axis exhaustion raises `ValueError("no_free_axis_letter")`; PD metadata raw-string passthrough; PD `values` copy-not-reference (mutating the rule must not bleed into payload); `EmissionResult` frozen-dataclass invariant; dispatcher ×12 over `ModificationType` with minimally-conformant payloads (no raise, non-empty rules for every type); `importlib.reload` no-side-effects.
  - [`tests/synthetic/test_variant_catalog.py`](../../tests/synthetic/test_variant_catalog.py) — 15 functions / 15 cases. Public surface; writes-at-expected-path; auto-creates `out_dir` (including nested `out_dir / "nested" / "variants"`); round-trip write→read dataclass-equality; overwrites-existing-file on second write to the same key; **atomic-on-replace-failure** (`monkeypatch.setattr(os, "replace", boom)` → write raises, final absent, tmp present); on-disk `modification_type` is `value` string `"synonym_label"` (not the enum repr); on-disk `rules` and `raw_responses` are lists; in-memory shape uses tuples for immutability; all three dataclasses are frozen; `validated_payload ⊕ skipped` invariant in provenance; malformed-JSON read raises `ValueError`; missing-keys read raises `KeyError`; `skipped` modifications round-trip with reason-prefix; `importlib.reload` no-side-effects.
- **Updated [`./CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md).** Added three new rows (`slot_extractor.py`, `rule_emitter.py`, `variant_catalog.py`) under the existing `variant_proposer.py` row in the "New Files in This Branch" section. Flipped `data/synthetic/variants/` row ❌ → ✅ with the annotation "Sprint 15 — Task C4 — `variant_catalog.write_catalog_entry` writes here; orchestrator (Sprint 16) populates per-concept files". Prepended an "After Sprint 15 — …" entry to the Sprint History section.

**Key results:**
- **Test count: 448 → 526 (+78 cases, 1 intentional skip carried over from Sprint 12).** `pytest tests -q` reports `526 passed, 1 skipped in 0.38s, zero failures.` The sprint plan's "≥40 new test functions / ≥488 total passed" gate is satisfied with comfortable margin (36 functions × parametrisation = 78 cases / 526 total). The skip count stays at exactly 1 (Sprint 12's `new_param` brace-audit skip — no new skips).
- **Module surfaces verified.** `from synthetic.slot_extractor import enumerate_targets, extract_slots, concept_resumen` succeeds. `from synthetic.rule_emitter import emit_rules, EmissionResult` succeeds. `from synthetic.variant_catalog import (VariantCatalogEntry, VariantRecord, ProvenanceRecord, write_catalog_entry, read_catalog_entry)` succeeds.
- **End-to-end smoke** — the pipeline `enumerate_targets → extract_slots → emit_rules → layer_l1.apply_synonym_label → VariantCatalogEntry → write_catalog_entry → read_catalog_entry` chained successfully against a single-axis fixture. The emitted rule shape was consumed by `apply_synonym_label` without raising — the rule schema that `rule_emitter._emit_l1` produces matches the Phase-B mutator's expected shape (binding contract validation). Round-trip equality `read(write(entry)) == entry` held.
- **Phase C deliverable for C4 is complete.** Slot extraction (stage-JSON walk) + rule emission (payload → Phase-B rule lift) + catalog persistence (JSON-per-concept) all ship. Combined with Sprints 12 (prompts), 13 (LLM client), and 14 (variant proposer), the Phase C ladder is complete: prompts → client → proposer → slot extractor → rule emitter → catalog. The orchestrator (D2) is now unblocked.
- **No changes** to any `layer_*.py`, to `mutator.py`, to `composition.py`, to `taxonomy.py`, to `src/synthetic/prompts/`, to `src/synthetic/llm_proposer.py`, or to `src/synthetic/variant_proposer.py`. Sprint 15 is purely additive — three new module files plus three test files (+ two documentation files updated).
- **Git status end-of-sprint** (sprint-scoped files only): new `src/synthetic/slot_extractor.py`, new `src/synthetic/rule_emitter.py`, new `src/synthetic/variant_catalog.py`, new `tests/synthetic/test_slot_extractor.py`, new `tests/synthetic/test_rule_emitter.py`, new `tests/synthetic/test_variant_catalog.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`, new `docs/synthetic/sprints/SPRINT_15.md` (already drafted). Nothing under `data/synthetic/variants/` is committed (the directory gets populated at run time by the orchestrator).

**Decisions:**
- **Three modules bundled into one sprint.** Slot extractor, rule emitter, and catalog writer share the per-concept context (stage JSON walk → slots dict → validated payload → emitted rules → final `Modification` records); splitting into three sprints would force a temporary intra-sprint shim per boundary. The boundaries between the modules are sharp (each is independently testable; each has a one-way input → output contract), but the *information flow* is tight and bundling preserves that.
- **`enumerate_targets` + `extract_slots` is the L0/L1 pattern of parametrisable rule generation.** Same shape every retrieval-grade pipeline ends up with: an enumerator of "what to try" and a per-attempt context builder. The orchestrator (D2) nests `for target in enumerate_targets: slots = extract_slots(target); proposal = propose_variant(prompt, slots, client, mtype); ...`.
- **`enumerate_targets` is sorted-deterministic.** L1 axes by axis key; L2 by `(var_key, condition)` lexicographic; L3-omission by `(field, var_token)`; L3-reorder by field. Set iteration was PYTHONHASHSEED-randomized — same trap Sprint 6.5 fixed in `s07_Filter_duplicates.ipynb`. Pinned by per-type tests.
- **`extract_slots` returns a dict matching `EXPECTED_SLOTS[mtype]` exactly.** Binding round-trip with Sprint 14: `set(extract_slots(...).keys()) == EXPECTED_SLOTS[mtype]` for every `(stage_json, concept_key, mtype, target_id)` tuple `enumerate_targets` produces. Pinned by `test_extract_slots_matches_expected_slots_per_type` ×12.
- **`EmissionResult` is the right return type — not bare `list[dict]`.** A bare list would hide the unmatched-payload diagnostic; a raise-on-mismatch contract would couple per-entry-failure handling into the caller. The frozen dataclass keeps the caller's path uniform: success → rules tuple populated, unmatched tuple empty; partial → both populated; full failure → both empty (defensive — C3 validator already rejects empty `synonyms`).
- **L1 cross-references `value`, not `label`.** The C3 prompt speaks in human-readable terms (`Normal`, `Rocoso`); the parameters block's `value` field is the matching key, `label` is the per-axis code letter (`a`, `b`). The rule emitter does the indirection — `original="Normal"` is looked up in `{value: label}` to fill `rule["value"] = "a"`. Drift here would silently drop every synonym that reached the LLM. Pinned by `test_emit_l1_rule_carries_value_label_not_value_string`.
- **LLM typos diverted to `EmissionResult.unmatched`.** No raise (one bad entry doesn't kill the batch), no silent drop (the diagnostic is visible). The orchestrator can log unmatched entries as Phase E1 metadata for prompt-tuning analysis. Pinned by `test_emit_l1_unmatched_original_rides_in_unmatched_list`.
- **PD ships partial credit.** The structural fields (`param`, `label`, `values`) are emitted; the raw `var_definition` and `template_patch` strings ride as `metadata.var_definition` / `metadata.template_patch` (a nested `metadata` dict). The minimal rule is applicable by `layer_pd.apply_new_param` because `text_variable` and `template_patches` are optional in the PD rule schema. Parsing the FIEBDC formula grammar + anchoring the template patch is Sprint 16's scope. The catalog file still records the raw LLM strings, so a future re-parse can hydrate the optional fields without re-querying the LLM.
- **`_allocate_axis_key` is alphabetical-first-free.** Picks the first uppercase letter not in the existing `parameters` block (A-Z scan). The 26-axis stress is defensive only; real BC3 catalogs cap well below. Pinned by happy (A,B,C → D), gap (A,C,E → B), and 26-axis-exhaustion tests.
- **Atomic catalog writes via tmp + `os.replace`.** Defensive against interrupted writes (Ctrl-C, OOM, machine reboot mid-write). `tmp.write_text` then `os.replace`; if replace raises, the `.tmp` file is the only artifact left. `os.replace` is atomic on POSIX and best-effort-atomic on Windows (`MoveFileExW(MOVEFILE_REPLACE_EXISTING)`). The cost is one extra inode per write; the benefit is "no half-written JSON in the catalog directory" — important because the orchestrator may run for hours, and a corrupt catalog file would force a re-run. Pinned by `test_write_catalog_entry_is_atomic_on_replace_failure` (monkeypatch `os.replace` to raise; assert final absent, tmp present).
- **Catalog file format is JSON, not Parquet.** Per-concept files are small (one concept × handful of variants × per-attempt provenance = a few KB); the read side is mostly human-eyeball diagnostic, not bulk-analysis. Parquet would optimise the wrong axis. If a future sprint needs bulk querying across concepts, the natural extension is a `materialize_catalog_to_parquet` aggregator — not a change to the per-concept file format.
- **`_parse_l2_formula` regex is narrow by design.** Matches `"<literal>" * (<condition>)` and nothing else. The richer FIEBDC operator grammar (conditional chains, nested parens) lives in `src/utils/z_formula_processing.py`. The L2 slot extractor only needs the literal-by-condition table — anything richer is overkill. If a Phase-B-style L2 parser is needed later, that's the right home, not the slot extractor. Pinned by `test_parse_l2_formula_unparseable_raises`.
- **Stage-shape tolerance: both lowercase (`resumen`/`texto`) and uppercase (`RESUMEN`/`TEXTO`) field keys are accepted.** Lowercase is the pipeline's canonical post-s05 shape; uppercase is the BC3 grammar key and the test fixtures' style. `_field_text` centralises the case-fold lookup. Tested explicitly.
- **No module-level side effects.** No env reads, no on-import I/O, no `out_dir` resolution at import time. Same Sprint 13/14 convention; pinned per module via `importlib.reload`.
- **No new runtime dependencies.** Stdlib + in-repo only. Same Sprint 13/14 rationale.
- **No live LLM, no real stage-JSON IO in tests.** All fixtures are inline literal dicts. Real-stage-JSON smoke is the orchestrator's problem (Sprint 16+) or a Phase F pilot concern.

**Problems encountered:**
- None blocking. The end-to-end smoke confirmed the rule_emitter→layer_l1.apply_synonym_label hand-off works at the schema level (the rule shape lifted from the LLM payload + slot context is exactly what `apply_synonym_label` expects, modulo no extra fields).

**What changed in the plan as a result:**
- Phase C is now complete (C1 prompts → C2 client → C3 proposer → C4 catalog ladder all green). The next-step recommendation moves to Sprint 16 / Phase D Task D2 (orchestrator `run_synthetic.py`).
- A natural Sprint 16+ follow-up surfaced: widen `_emit_new_param` to parse `var_definition` (FIEBDC formula → `text_variable: {var, formula}`) and `template_patch` (string → anchored `template_patches: [{field, original, new}, ...]`) so the orchestrator's `apply_new_param` call gets the full PD effect, not just the param/label/values structural minimum. The raw strings already ride as `metadata.*` in the emitted rule, so the future re-parse won't need to re-query the LLM.

**CLAUDE_SYNTHETIC.md updated:** yes — added three new rows (`slot_extractor.py`, `rule_emitter.py`, `variant_catalog.py`) in the "New Files in This Branch" file map; flipped `data/synthetic/variants/` row ❌ → ✅; prepended "After Sprint 15" entry to Sprint History.
**Next step:** **Sprint 16 — Phase D Task D2 (`run_synthetic.py` — orchestrator).** Wire the concept-loop driver that ties `prompts.load_prompt` → `variant_proposer.propose_variant` → `slot_extractor.{enumerate_targets, extract_slots}` → `rule_emitter.emit_rules` → `composition.compose_rules` → `mutator.apply_*` → `variant_catalog.write_catalog_entry` together. The per-concept condition matrix (`single_L1_*`, `single_L2_*`, `single_L3_*`, `new_param_only`, `stacked_2..5+`, `full_random_mix`) is D2's natural home.

---

### Sprint 14 — Phase C Task C3: variant proposer (`variant_proposer.py`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_14.md`](sprints/SPRINT_14.md)
**Tasks from backlog:** C3 — author `src/synthetic/variant_proposer.py` that renders the per-type prompt with a per-concept slots dict, calls `llm_proposer.propose()`, and validates the parsed payload against the per-`ModificationType` schema. Slot extraction (stage-JSON → slots dict) and payload-to-Phase-B-rule emission are intentionally deferred to Sprint 15.

**What was done:**
- **Created [`src/synthetic/variant_proposer.py`](../../src/synthetic/variant_proposer.py).** New module exposing three public symbols:
  - `EXPECTED_SLOTS: dict[ModificationType, frozenset[str]]` — module-level constant declaring the per-type placeholder set. Twelve entries, one per `ModificationType`, byte-aligned with Sprint 12's `tests/synthetic/test_prompts.py::_EXPECTED_PLACEHOLDERS`. The lockstep is binding: `test_expected_slots_matches_prompt_audit` re-checks every prompt file off disk against this constant.
  - `@dataclass(frozen=True) class VariantProposal` — fields `payload: Optional[dict]`, `raw_responses: tuple[str, ...]`, `skipped: Optional[Modification]`. Three terminal shapes: success (validated payload, `skipped=None`), C2 fallback (`skipped.reason.startswith("malformed_llm_response_after_retry: ")`), C3 validation failure (`skipped.reason.startswith("schema_validation_failed: ")`).
  - `def propose_variant(prompt_template, slots, client, modification_type, *, retry_once=True) -> VariantProposal` — single entry point. Calls `_render_prompt(template, slots, modification_type)` → `llm_proposer.propose(rendered, client, modification_type, retry_once)` → `_validate_payload(result.payload, modification_type)`. C2 fallback propagates unchanged into `VariantProposal.skipped`; C3 validation failures emit a fresh `Modification(status="skipped", reason="schema_validation_failed: <detail>")`. Never raises on LLM- or schema-failure paths; *does* raise on slot/placeholder mismatch (`KeyError` on missing slots, `ValueError` on extra slots) — those are catalog-authoring build-time errors, not run-time LLM failures, and silent skipping would hide them.
  - Private helpers: `_render_prompt(template, slots, modification_type) -> str` (escape every `{`/`}` to `{{`/`}}`, then selectively un-escape the declared placeholders in `EXPECTED_SLOTS[modification_type]`, then `str.format_map(slots)`); `_validate_payload(payload, modification_type) -> dict` (dispatches across `_validate_pair_list` for the six L1-style payloads, `_validate_original_new_preserves` for `paraphrase`/`expansion`/`compression`/`reorder`, `_validate_omission` for the L3-omission shape, `_validate_new_param` for the PD shape with a 2..5 length bound on `values`).
  - Imports: stdlib `dataclasses`, `typing.Any`/`Optional`; in-repo `from .llm_proposer import LLMClient, propose` and `from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER`. No new runtime dependencies (no `pydantic`, no `jsonschema`).
- **Added [`tests/synthetic/test_variant_proposer.py`](../../tests/synthetic/test_variant_proposer.py) — 30 test functions, 86 individual cases after parametrisation expansion.** Coverage:
  - Public-surface import audit; `EXPECTED_SLOTS` covers all 12 `ModificationType` members.
  - Cross-file lockstep audit `test_expected_slots_matches_prompt_audit` (×12) — every declared slot in `EXPECTED_SLOTS[mtype]` appears as `{name}` in the corresponding prompt body before the `Responde SOLO con un JSON` marker.
  - Per-type happy path `test_happy_path_per_type` (×12) — stub returns `json.dumps(payload)`, result `.payload == payload`, `.skipped is None`, one client call captured.
  - Per-type schema-violation path `test_schema_violation_per_type` (×12) — stub returns `'{"unrelated": "data"}'`, result `.payload is None`, `.skipped.type == mtype`, `.skipped.layer == TYPE_TO_LAYER[mtype]`, `.skipped.status == "skipped"`, `.skipped.reason.startswith("schema_validation_failed: ")`.
  - C2-fallback propagation; two-skip-prefix non-overlapping-substring distinguishability.
  - Render: slot substitution + single-brace JSON-literal preservation (synthetic templates + the *real* `new_param.txt` whose nested JSON braces are Sprint 12's only audit exemption).
  - Render: slot/placeholder mismatch raises — `KeyError` on missing slots (all three names listed), `ValueError` on extra slots, partial-slot rejection.
  - Per-validator-helper happy + sad paths: missing key / wrong inner shape / empty list / non-str value / not-list / `num_to_text` uses `numerals` not `synonyms` / `original`+`new`+`preserves_meaning` happy ×4 (parametrised over `paraphrase`/`expansion`/`compression`/`reorder`) / `preserves_meaning=1` (int) rejected as `not_bool` / `omission` missing-key ×3 / `new_param` 2..5 bound (×4 over `len ∈ {0, 1, 6, 7}`) / `new_param` inner-shape missing / `new_param` missing top-keys.
  - `raw_responses` propagation (single-success / retry-success).
  - `retry_once=False` short-circuit (1 client call, 1 raw response, `malformed_llm_response_after_retry` skip).
  - Never-raises across 9 malformed/wrong-shape stub responses (parametrised).
  - `FrozenInstanceError` on `VariantProposal.payload` reassignment; equality of two structurally-identical proposals; `importlib.reload` no-side-effects.
  - Rendered-prompt passthrough verbatim — every slot value appears exactly once in the captured prompt, JSON literal appears exactly once.
  - Skip-record other-fields-are-None on validation failure (`param`, `var`, `condition`, `field`, `value`, `original`, `new`).
- **Updated [`./CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md).** Added a new `variant_proposer.py` row under the existing `llm_proposer.py` row in the "New Files in This Branch" section with the annotation "Sprint 14 — Task C3 — `propose_variant` + per-type schema validation + JSON-aware template renderer; slot-extraction and payload-to-Phase-B-rule emission deferred to Sprint 15". Dropped the "; C3 still ❌" suffix from the `llm_proposer.py` row. Prepended an "After Sprint 14 — …" entry to the Sprint History section.

**Key results:**
- **Test count: 362 → 448 (+86 cases, 1 intentional skip carried over from Sprint 12).** `pytest tests -q` reports `448 passed, 1 skipped in 0.35s, zero failures.` The sprint plan's "≥25 new test functions / ≥392 total passed" gate is satisfied with comfortable margin (30 functions / 448 total). The skip count stays at exactly 1 (Sprint 12's `new_param` brace-audit skip is the only skip in the suite — no new skips).
- **Module surface verified.** `from synthetic.variant_proposer import VariantProposal, propose_variant, EXPECTED_SLOTS` succeeds; `len(EXPECTED_SLOTS) == 12`; `set(EXPECTED_SLOTS) == set(ModificationType)`. Happy-path smoke: `propose_variant(tmpl, slots, _StubLLMClient([json.dumps({"synonyms": [{"original": "Normal", "new": "Estándar"}]})]), ModificationType.SYNONYM_LABEL)` returns `payload={"synonyms": [...]}` with `skipped=None` and `len(raw_responses) == 1`. Schema-violation smoke: stub returning `'{"unrelated": []}'` → `result.skipped.reason == "schema_validation_failed: missing_key: 'synonyms'"`. C2-fallback propagation smoke: stub `["junk1", "junk2"]` → `result.skipped.reason.startswith("malformed_llm_response_after_retry: ")` with `raw_responses == ("junk1", "junk2")`. Real-prompt renderer smoke: `_render_prompt(load_prompt(ModificationType.NEW_PARAM), {concept, existing_axes_with_labels, allowlist}, NEW_PARAM)` substitutes the three slots and preserves the nested JSON literal block with single braces — the only Sprint-12-audit-exempted prompt now renders cleanly.
- **Phase C deliverable for C3 is complete.** Render + validate ship as one module. Slot extraction (per-concept stage JSON → slots dict) and payload-to-rule emission (validated LLM dict → `{"type", "param", ...}` Phase-B rule) are **explicitly out of scope** — both go into Sprint 15 alongside the C4 variant catalog writer. Symmetric with Sprint 13's "C2 owns parse + retry, C3 owns shape" split: Sprint 14 owns render + validate, Sprint 15 owns slot-extraction + lift + catalog persistence.
- **Git status end-of-sprint** (sprint-scoped files only): new `src/synthetic/variant_proposer.py`, new `tests/synthetic/test_variant_proposer.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`, new `docs/synthetic/sprints/SPRINT_14.md` (already drafted). **No changes to any `layer_*.py`, to `mutator.py`, to `composition.py`, to `taxonomy.py`, to `src/synthetic/prompts/`, or to `src/synthetic/llm_proposer.py`** — C3 is purely additive in one new module file plus its test file (+ two documentation files updated).

**Decisions:**
- **Render → propose → validate as three composable pure functions.** `propose_variant` is the glue. Each helper has a narrow contract and a tight test surface; the orchestrator just sequences them and unwraps the result.
- **Brace-escape uses pre-escape + selective un-escape, not split-at-marker.** The split-at-`"Responde SOLO con un JSON"` alternative would couple the renderer to that exact marker phrase — if a future prompt drops or rewords it, the splitter silently mis-classifies. Pre-escape is marker-agnostic and survives prompt polish. Pinned by `test_render_handles_nested_json_in_new_param_prompt`, which exercises the renderer against the real `new_param.txt` and confirms its nested JSON block survives intact.
- **`EXPECTED_SLOTS` is a module-level production constant; `_EXPECTED_PLACEHOLDERS` is a test-side declaration; the cross-file audit is the binding contract.** Drift between them is caught by `test_expected_slots_matches_prompt_audit`. If a future sprint adds a new `ModificationType`, both must update together — and the audit fires if they don't.
- **`_validate_payload` is shape-only, by intent.** Dict-shape, key presence, value types, and (for `new_param.values`) the 2..5 length bound. Reviewer-grade validation (does this paraphrase preserve meaning? is this synonym idiomatic technical Spanish? does the omission produce grammatical text? are the new axis values distinct from existing ones?) is Phase E's reviewer harness — not C3's job.
- **Two distinguishable skip-reason prefixes.** `"malformed_llm_response_after_retry: "` (C2-fallback — LLM never produced parseable JSON) vs. `"schema_validation_failed: "` (C2 succeeded, shape was wrong). Phase E1's metadata grep counts failure families per `ModificationType`. Non-overlapping-substring distinguishability pinned by `test_two_skip_prefixes_are_distinguishable`.
- **`propose_variant` never raises on LLM- or schema-failure paths.** Uniform-return-value contract — the orchestrator (D2) walks `result.payload` / `result.skipped` without `try`/`except`. Symmetric with Sprint 13's `propose` contract. But `_render_prompt` *does* raise on slot/placeholder mismatch — those are catalog-build-time programming errors, not run-time data shapes.
- **Sorted slot names in `_render_prompt` error messages.** Pinned by test: missing-slot / extra-slot errors report slot names in `sorted()` order. Set iteration was PYTHONHASHSEED-randomized — same trap Sprint 6.5 fixed in `s07_Filter_duplicates.ipynb`.
- **`bool` check uses `isinstance(x, bool)` directly, not via `isinstance(x, int)`.** `bool` subclasses `int` in Python, so `isinstance(True, int)` returns `True`. The validator must check `bool` directly to reject `0`/`1` int payloads on `preserves_meaning`. Pinned by `test_validate_original_new_preserves_rejects_int_bool` — `{"preserves_meaning": 1}` is rejected with `preserves_meaning_not_bool, type=int`.
- **`new_param.values` length-gate at 2 ≤ N ≤ 5.** Matches the prompt's "entre 2 y 5 valores discretos" wording. Outside this range → `values_out_of_range: len=<n> (expected 2..5)`. The only numeric bound the schema enforces; every other constraint (label uniqueness, admissibility against `new_param_allowlist.yaml`, axis-distinctness from existing axes) is structural-blind and falls to Phase E.
- **C3 ships the validated *payload*, not a Phase-B *rule*.** A `synonym_label` LLM payload `{"synonyms": [{"original": "Normal", "new": "Estándar"}, …]}` is not yet a Phase-B `apply_synonym_label` rule — the rule shape requires `{"type", "param", "value", "original", "new"}`, and `param` / `value` aren't in the LLM payload (they need to be lifted from per-concept stage JSON context, which is the slot-extraction shim's job). Bundling that lift into Sprint 14 would pull a lot of stage-JSON-aware logic into a schema-pure sprint. Deferred to Sprint 15.
- **No `pydantic` / `jsonschema` runtime dependency.** The 12 schemas are simple enough that hand-coded `isinstance` checks + key-presence checks emit tighter error messages (`schema_validation_failed: missing_key: 'X'`) than `pydantic.ValidationError` noise. Reversible: a future sprint can swap `_validate_payload` to delegate to `pydantic` without changing the public surface.
- **No slot extraction in Sprint 14.** `propose_variant` takes an *already-built* `slots: dict[str, Any]`. Symmetric with Sprint 13's "take an already-rendered prompt" contract. Slot extraction needs deep familiarity with stage-2/3/4 JSON layouts (axis-key allocation, value-label lookup, var-key resolution, reorderable-constituent identification) — its own sprint.
- **No live LLM calls in pytest.** Same Sprint 13 rationale — all tests use the same `_StubLLMClient` pattern from `test_llm_proposer.py`. Real-model smoke tests live in `scripts/spike_a3_*.py` or a manually-run notebook.
- **No module-level side effects.** No env reads, no on-import I/O, no logger setup. Pinned by `test_module_has_no_side_effects_at_import` via `importlib.reload`.

**Problems encountered:**
- None. The module landed first-try; smoke checks all passed; pytest went green on the first run (448 passed, 1 skipped, zero failures). The atexit `cleanup_dead_symlinks` `PermissionError` on Windows is unchanged from prior sprints — cosmetic, no action.

**What changed in the plan:** None. The C3 deliverable matches the spec's "Scope" block; every "Out of scope" decision is honoured (no slot extraction, no payload-to-rule emission, no concrete LLM transport, no per-type Spanish fluency / semantic-preservation checks, no `pydantic` / `jsonschema`, no compositionality enforcement, no variant catalog persistence, no `{allowlist}` slot population for `new_param`, no live LLM calls in CI, no streaming / chat-format / function-calling, no changes to existing `src/synthetic/` modules besides the two doc files). The protocol's §2 risk-table "LLM proposer model: TBD" cell stays open and is the prerequisite for the concrete-transport sprint (still A3). Sprint 15's three concerns (slot extraction + payload-to-rule lift + C4 variant catalog writer) are explicitly bundled per the design rationale spelled out in the sprint's "Out of scope" rationale.

**CLAUDE_SYNTHETIC.md updated:** yes — new `variant_proposer.py` row added under the `llm_proposer.py` row (✅ Sprint 14, with the "slot-extraction / payload-to-rule deferred to Sprint 15" annotation); the `llm_proposer.py` row's "; C3 still ❌" suffix dropped now that C3 lands in its own row; "After Sprint 14 — …" entry prepended to the Sprint History section.

**Next step:** **Sprint 15 — Phase C Task C4 (variant catalog writer) + slot-extraction shim + payload-to-rule lift.** Three concerns to bundle: (a) `extract_slots(stage_json, concept_key, modification_type) -> dict[str, Any]` walking stage-2/3/4 JSON for the per-concept context every prompt type needs (axis keys, value labels, var keys, conditions, template fields, reorderable constituents); (b) per-type payload-to-rule emitter that lifts the validated LLM payload to the `{"type": ..., "param": ..., ...}` shape `layer_*.py` mutators consume, cross-referencing the slots context for axis keys and value labels; (c) the C4 variant catalog writer pairing the emitter output with provenance metadata and writing `data/synthetic/variants/{concept_key}.json` JSON-per-concept artefacts. Once Sprint 15 closes, the Phase C ladder (C1 prompts → C2 client → C3 proposer → C4 catalog) is complete and the orchestrator (D2) can consume the catalog stream.

---

### Sprint 13 — Phase C Task C2: LLM client (`llm_proposer.py`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_13.md`](sprints/SPRINT_13.md)
**Tasks from backlog:** C2 — author `src/synthetic/llm_proposer.py` wrapping the (TBD per A3) model with structured-JSON parsing, one-shot retry on malformed output, and a `Modification(status="skipped", reason=...)` fallback log entry.

**What was done:**
- **Created [`src/synthetic/llm_proposer.py`](../../src/synthetic/llm_proposer.py).** New module exposing three public symbols:
  - `class LLMClient(Protocol)` — single method `complete(self, prompt: str) -> str`. The Stage-A transport contract; A3's concrete client (Ollama / Anthropic / OpenAI / …) will implement it in a follow-up sprint.
  - `@dataclass(frozen=True) class ProposalResult` — fields `payload: Optional[dict]`, `raw_responses: tuple[str, ...]`, `fallback: Optional[Modification]`. Successful parse: `payload` set, `fallback=None`. Double failure: `payload=None`, `fallback` set.
  - `def propose(prompt, client, modification_type, *, retry_once=True) -> ProposalResult` — single entry point. Calls `client.complete(prompt)`, parses the response as a JSON object (stripping a leading ` ```json `… `'''` or bare ` ``` `… `'''` fence first), retries once on `ValueError`, and on a second failure returns a `Modification(type=…, layer=TYPE_TO_LAYER[…], status="skipped", reason="malformed_llm_response_after_retry: <detail>")` inside the result. Never raises; all failures encoded in the result.
  - Three private helpers: `_parse_json_object(text) -> dict` (strict `json.loads`, reject non-dict roots), `_strip_code_fence(text) -> str` (handle ` ```json `-tagged and bare ` ``` ` fences LLMs frequently emit despite the prompt's "Responde SOLO con un JSON" instruction), `_build_fallback(modification_type, reason_detail) -> Modification`.
  - Imports: stdlib `dataclasses`, `json`, `typing.Optional`/`Protocol`; in-repo `from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER`. No new runtime dependencies (no `httpx`, no `pydantic`, no `tenacity`, no vendor SDK).
- **Added [`tests/synthetic/test_llm_proposer.py`](../../tests/synthetic/test_llm_proposer.py) — 24 test functions, 65 individual cases after parametrisation expansion.** Coverage:
  - (1) Public-surface import audit.
  - (2)–(4) Happy / retry / double-failure paths (payload set on first attempt; payload set on second attempt after a malformed first; fallback set after two malformed attempts; client-call counts pinned).
  - (5)–(7) Per-`ModificationType` fallback shape (parametrised ×12): `fallback.type == modification_type`; `fallback.layer == TYPE_TO_LAYER[modification_type]`; `fallback.status == "skipped"`.
  - (8) Reason-prefix grep handle: `fallback.reason.startswith("malformed_llm_response_after_retry: ")`.
  - (9) Fallback other fields (`param`, `var`, `condition`, `field`, `value`, `original`, `new`) all `None`.
  - (10)–(12) Raw-responses capture per path (singleton tuple on first-attempt success; pair on retry success; pair on double failure).
  - (13) `raw_responses` is a `tuple`, not a `list`.
  - (14) `retry_once=False` short-circuits — one client call, one raw response, fallback set.
  - (15)–(16) Code-fence stripping for ` ```json\n…\n``` ` and bare ` ```\n…\n``` `.
  - (17) Leading/trailing whitespace tolerance.
  - (18)–(21) Non-dict-root rejection (array / string / number / empty response); reason carries `"json_not_object"` (with `type=str` / `type=int` for the typed cases) or `"empty_response"`.
  - (22) Prompt passthrough verbatim — `propose()` does not format, escape, or normalise the prompt string.
  - (23) Never-raises on malformed inputs (parametrised ×6 over `"garbage"`, `"<html>"`, `"{"`, `"}"`, `" "`, `"[unterminated"`).
  - (24) `FrozenInstanceError` (or `AttributeError`) on `result.payload = ...` reassignment.
  - (25) Equality of two structurally-identical `ProposalResult` instances.
  - (26) Module re-import via `importlib.reload` — no side effects at import time.
  - (27) `Protocol` duck-typing: an ad-hoc class with a `complete(self, prompt)` method satisfies the `LLMClient` contract without inheriting from it.
- **Updated [`./CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md).** Flipped ❌ → ✅ for the `llm_proposer.py` row in the "New Files in This Branch" listing with the partial-credit annotation "Sprint 13 — Task C2 — `LLMClient` Protocol + `propose` + retry/fallback contract; concrete transport deferred to A3; C3 still ❌". Prepended an "After Sprint 13 — …" entry to the Sprint History section.

**Key results:**
- **Test count: 297 → 362 (+65 cases, 1 intentional skip carried over from Sprint 12).** `pytest tests -q` reports `362 passed, 1 skipped in 0.30s, zero failures.` The sprint plan's "≥22 new test functions / ≥319 total passed" gate is satisfied (24 functions / 362 total). The skip count stays at exactly 1 (Sprint 12's `new_param` brace-audit skip is the only skip in the suite — no new skips).
- **Module surface verified.** `from synthetic.llm_proposer import LLMClient, ProposalResult, propose` succeeds; `dataclasses.fields(ProposalResult)` reports `('payload', 'raw_responses', 'fallback')`. Happy-path smoke: `propose('hola', _StubLLMClient(['{"synonyms": []}']), ModificationType.SYNONYM_LABEL).payload == {"synonyms": []}` with `fallback is None` and `raw_responses == ('{"synonyms": []}',)`. Retry-path smoke: queue `['garbage', '{"k": "v"}']` against `ModificationType.PARAPHRASE` → `payload == {"k": "v"}`, `len(raw_responses) == 2`. Double-failure smoke (per-type loop): for every `mtype in ModificationType`, queue `['x', 'y']` → `payload is None`, `fallback.type == mtype`, `fallback.layer == TYPE_TO_LAYER[mtype]`, `fallback.status == "skipped"`, `fallback.reason.startswith("malformed_llm_response_after_retry: ")`. Code-fence smoke: `'```json\n{"k": 1}\n```'` parses to `{"k": 1}` on the first attempt. `retry_once=False` smoke: malformed singleton → 1 client call, 1 raw response, fallback set.
- **Phase C deliverable for C2 is complete.** The wrapper + parse + retry + fallback scaffold ships. The concrete transport (`OllamaClient` / `AnthropicClient` / `OpenAIClient` / …) is **explicitly out of scope** — A3 picks the model and ships the concrete client in a follow-up sprint. The protocol's §2 risk-table "LLM proposer model: TBD" cell stays open.
- **Git status end-of-sprint** (sprint-scoped files only): new `src/synthetic/llm_proposer.py`, new `tests/synthetic/test_llm_proposer.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`, new `docs/synthetic/sprints/SPRINT_13.md` (already drafted). Nothing else; in particular **no changes to any `layer_*.py`, to `mutator.py`, to `composition.py`, to `taxonomy.py`, or to `src/synthetic/prompts/`** — C2 is purely additive in one new module file plus its test file.

**Decisions:**
- **Pluggable transport before model choice.** A3's outcome (Llama 3.1 70B local vs. GPT-4-class API vs. Spanish-tuned alternative) is unknown. Committing to a concrete transport in Sprint 13 would force a rewrite when A3 lands. The `Protocol` surface is the right abstraction: A3 ships *one* concrete `complete(prompt) -> str` implementation; Sprint 13 has already shipped the retry/fallback scaffold around it.
- **`Protocol`, not `ABC`.** Structural subtyping fits the one-method contract. No `@runtime_checkable` decorator (no `isinstance(x, LLMClient)` calls; duck typing in tests is sufficient). The concrete transport in A3 may inherit from `LLMClient` for documentation purposes but is not required to. Pinned by `test_protocol_duck_typing_works`.
- **`propose` never raises.** Every failure mode (malformed JSON, wrong root type, empty response, double failure, no-retry short-circuit) returns a `ProposalResult` with `fallback` set. The orchestrator (D2) walks a uniform return-value path; no `try/except` around the call. Rationale: the protocol §4 convention treats errors as data, not exceptions — the LLM round-trip is just another source of `Modification(status="skipped", reason=...)` records, alongside the composer's `same_target_conflict` and `layer_dependency_conflict` skips.
- **One retry, fixed.** Protocol §5 Phase C C2 says "malformed-response retry (×1)". Not configurable beyond on/off. The `retry_once: bool` knob is for tests (assert no-retry behaviour), never a production-time tunable. If a future sprint needs richer retry semantics (rate-limit-aware, exponential backoff), they belong in the concrete transport's `complete` method.
- **`_parse_json_object` is C2's "malformed" detector — not C3's schema validator.** C2 catches JSON-validity problems only (unparseable, wrong root type, empty). C3 catches structural-shape problems (the prompt asked for `{"synonyms": [...]}` but the LLM emitted `{"foo": "bar"}`). Mixing the two would couple the wrapper to per-prompt schemas — which the wrapper has no business knowing.
- **Code-fence stripping is best-effort.** LLMs often emit ` ```json\n{...}\n``` ` despite the "Responde SOLO con un JSON" instruction. The pre-parse strip handles the three common shapes (`json`-tagged, bare, no-fence). Drift to other fence styles (e.g., `~~~`) triggers a retry — acceptable degradation.
- **Non-dict roots rejected.** JSON permits arrays, strings, numbers, booleans, and `null` at the top level; the 12 prompts all declare an object-shaped contract. Pinned by four rejection tests (array, string, number, empty). Reason carries `"json_not_object: type=…"` or `"empty_response"` for the Phase E1 metadata pipeline's diagnostic counters.
- **`raw_responses: tuple[str, ...]`, not `list[str]`.** Pinned by `frozen=True`. Phase E1's metadata pipeline may want to log the raw response verbatim for diagnostic purposes; an immutable tuple keeps the contract clean.
- **`_build_fallback`'s reason prefix is a grep handle.** Exactly `"malformed_llm_response_after_retry: "`. Phase E1 / F1 will count fallbacks per `ModificationType` via substring match instead of regex. Pinned by `test_fallback_reason_starts_with_known_prefix`.
- **Fallback `Modification` populates only `type`, `layer`, `status`, `reason`.** Every other field is `None`. Pinned by `test_fallback_other_fields_are_none`.
- **Stdlib-only imports.** No `httpx`, no `pydantic`, no `tenacity`, no vendor SDK. New runtime deps are A3's call.
- **No live LLM calls in pytest.** All tests use an in-test `_StubLLMClient` that pops queued responses off a list. Real-model smoke tests are A3's problem (`scripts/spike_a3_*.py`) or a Phase F1 pilot concern (a manually-run notebook), never in `tests/`.

**Problems encountered:**
- None. The module landed first-try; smoke checks all passed; pytest went green on the first run (362 passed, 1 skipped, zero failures). The atexit `cleanup_dead_symlinks` `PermissionError` on Windows is unchanged from prior sprints — cosmetic, no action.

**What changed in the plan:** None. The C2 deliverable matches the spec's "Scope" block; every "Out of scope" decision is honoured (no concrete transport, no prompt rendering, no per-type schema validation, no `pydantic` / `jsonschema`, no live LLM calls in CI, no streaming / chat-format / tool-use, no token budgeting / rate-limit handling, no `configs/synthetic/llm_proposer.yaml`, no changes to existing `src/synthetic/` modules). The protocol's §2 risk-table "LLM proposer model: TBD" cell stays open and is the prerequisite for the concrete-transport sprint.

**CLAUDE_SYNTHETIC.md updated:** yes — `llm_proposer.py` row flipped ❌ → ✅ (partial credit, with explicit C3-still-❌ annotation) and Sprint History entry prepended.

**Next step:** **Sprint 14 — Phase C Task C3 (`variant_proposer.py` — per-concept slot rendering + per-type schema validation).** With the LLM client shipped, C3 owns: (a) loading the per-type prompt via `synthetic.prompts.load_prompt(mtype)`; (b) rendering slots (`{concept}`, `{axis_label}`, `{value_list}`, `{var_key}`, `{condition}`, `{template}`, `{constituents}`, `{var_to_omit}`, `{existing_axes_with_labels}`, `{allowlist}`) from a per-concept slots dict via a `str.format_map` variant that ignores braces inside the JSON-contract block; (c) calling `propose()`; (d) per-`ModificationType` structural validation of the parsed payload; (e) returning a per-concept `Modification` candidate (success) or appending to the skipped log (validation failure). Once C3 closes, C4 (variant catalog writer) consumes the candidate stream.

---

### Sprint 12 — Phase C Task C1: Spanish prompt library (`prompts/`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_12.md`](sprints/SPRINT_12.md)
**Tasks from backlog:** C1 — author `src/synthetic/prompts/` with one Spanish prompt per `ModificationType` declaring its JSON-output contract, plus a thin loader.

**What was done:**
- **Created [`src/synthetic/prompts/__init__.py`](../../src/synthetic/prompts/__init__.py).** A new module exposing one public function `load_prompt(modification_type: ModificationType) -> str`, one constant `PROMPT_DIR: Path` (resolves to the directory containing the `.txt` files), and one constant `PROMPT_FILENAMES: dict[ModificationType, str]` (auto-computed via dict comprehension from `ModificationType`). The loader reads `PROMPT_DIR / PROMPT_FILENAMES[modification_type]` as UTF-8 text and returns the string verbatim — no placeholder substitution, no caching, no env-var override surface. The spec's reference implementation was extended with one extra `isinstance(modification_type, ModificationType)` guard at the top of the function body, raising `KeyError` if the input is not an enum member. Rationale: `ModificationType(str, Enum)` mixes in `str`, so `"synonym_label" == ModificationType.SYNONYM_LABEL` and hash-equal — a bare-string dict lookup would silently succeed without the guard, contradicting the spec's `test_load_prompt_raises_keyerror_on_string_input` acceptance. The guard is the minimal change that honors both the spec's reference code shape (a dict lookup + read) and its strict-typing acceptance criterion.
- **Authored 12 `*.txt` prompt files** under `src/synthetic/prompts/`, one per `ModificationType`. Four are lifted **verbatim** from [`../RESEARCH_PROPOSAL.md §8`](../RESEARCH_PROPOSAL.md): `synonym_label.txt` (§8.1), `paraphrase.txt` (§8.2), `omission.txt` (§8.3), `new_param.txt` (§8.4). The remaining eight (`num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`, `expansion`, `compression`, `reorder`) are authored in the proposal-§8 pattern — role line ("Eres …") → slot block (`Concepto: {concept}` …) → instruction body with a "preservando exactamente el significado paramétrico" pin → `Responde SOLO con un JSON:` closing literal. All files are UTF-8 *without* BOM, LF line endings, exactly one trailing `\n`; byte sizes range 434 (`synonym_label.txt`) to 699 (`expansion.txt`), well within the spec's [200, 3000] sanity bound. Placeholders use Python-style `{name}` syntax; the L1 six prompts share `{{{{concept}}, {axis_label}, {value_list}}}`, the L2 three prompts share `{{concept}, {var_key}, {fragment}, {condition}}`, the L3 two prompts diverge per type, and the PD prompt has `{concept}, {existing_axes_with_labels}, {allowlist}` (the last left intentionally unfilled at C1 time — C3 / Phase B4 binds it once the allowlist YAML exists).
- **Added [`tests/synthetic/test_prompts.py`](../../tests/synthetic/test_prompts.py) — 18 test functions, expanding to 138 individual cases under parametrisation.** Coverage:
  - (1)–(2) Directory and filenames audit: `PROMPT_DIR.is_dir()`; `len(PROMPT_FILENAMES) == 12`; keys == `set(ModificationType)`; values match the `<enum_value>.txt` pattern.
  - (3) Per-type file existence (parametrised ×12).
  - (4) Per-type loadability: `load_prompt(mtype)` returns a non-empty `str` ending in `"\n"` (×12).
  - (5) Per-type UTF-8 decode equality: `raw.decode("utf-8") == load_prompt(mtype)` (×12).
  - (6) Per-type no-BOM byte audit: first byte not `0xEF`; file doesn't start with `EF BB BF` (×12).
  - (7) Per-type "JSON" keyword presence (case-insensitive) (×12).
  - (8) Per-type expected-placeholder subset audit against `_EXPECTED_PLACEHOLDERS` (×12).
  - (9) Idempotence: two consecutive `load_prompt(SYNONYM_LABEL)` calls return the same string.
  - (10) `load_prompt("synonym_label")` raises `KeyError`.
  - (11) Missing file raises `FileNotFoundError`: monkeypatch `PROMPT_FILENAMES[SYNONYM_LABEL] = "NOTAFILE.txt"`, then call.
  - (12) Per-type role-line prefix: first non-empty line starts with `"Eres "` (×12).
  - (13) Per-type Spanish-register marker presence: body contains at least one of `{Eres, Concepto, Responde, JSON}` (×12).
  - (14) Per-type `"Responde SOLO con un JSON"` phrase presence (×12).
  - (15) Per-type braces-outside-slots audit (×12, with `NEW_PARAM` exempted via `pytest.skip` per spec — its JSON literal embeds nested `{` / `}` that the prefix-vs-JSON heuristic can't cleanly partition): walks every `{` / `}` in the body region (text up to `"Responde SOLO con un JSON"`), verifies each brace-delimited token is in the prompt's declared placeholder set; raises on stray `}` or unmatched `{`.
  - (16) L1-six-types-share-placeholder-set audit: `_EXPECTED_PLACEHOLDERS[mtype] == {{"{concept}", "{axis_label}", "{value_list}"}}` for all six L1 types, and every placeholder appears in every L1 prompt.
  - (17) L2-three-types-share-placeholder-set audit: same shape, `{{"{concept}", "{var_key}", "{fragment}", "{condition}"}}` for all three L2 types.
  - (18) Per-type byte-size sanity bound: 200 ≤ `stat().st_size` ≤ 3000 (×12).
- **Updated [`./CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md).** Flipped ❌ → ✅ for the `prompts/` block in the "New Files in This Branch" listing — all 13 rows (the directory itself + 12 `.txt` files + an inserted `__init__.py` row). Prepended an "After Sprint 12 — …" entry to the Sprint History section.

**Key results:**
- **Test count: 159 → 297 (+138 cases, +1 intentional skip).** `pytest tests -q` reports `297 passed, 1 skipped in 0.24s, zero failures.` Breakdown of the +138: 11 parametrised-×12 functions = 132 cases (one skip in the brace-audit for `new_param`); 7 singleton functions = 7 cases. The sprint plan's "≥18 new test cases" gate is satisfied at the function level; the recommended "~70 cases after parametrisation expansion" headline is exceeded by ~2× (138 vs 70).
- **Loader surface verified.** `from synthetic.prompts import load_prompt, PROMPT_DIR, PROMPT_FILENAMES` succeeds. `len(PROMPT_FILENAMES) == 12`; `set(PROMPT_FILENAMES) == set(ModificationType)`. For every `mtype in ModificationType`: `load_prompt(mtype)` returns a non-empty UTF-8 string starting with `"Eres "`, containing `"Responde SOLO con un JSON"`, ending with `"\n"`, byte-size in 434–699.
- **End-to-end smoke check passes.** Submitted `for mtype in ModificationType: text = load_prompt(mtype); assert text.startswith("Eres ") and "Responde SOLO con un JSON" in text and text.endswith("\n")` — all 12 pass. Loaded representative `paraphrase` and `new_param` prompts, verified their four-slot / three-slot placeholder sets are present.
- **Phase C deliverable for C1 is complete.** The prompt library is *static text only*; no LLM client, no API calls, no retry logic — those are C2's deliverable. The 12 prompts are frozen text the next sprint will pair with a `pydantic` / `jsonschema` model.
- **Git status end-of-sprint** (sprint-scoped files only): new `src/synthetic/prompts/__init__.py`, new `src/synthetic/prompts/*.txt` (12 files), new `tests/synthetic/test_prompts.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`, new `docs/synthetic/sprints/SPRINT_12.md`. Nothing else; in particular **no changes to `src/synthetic/mutator.py`, no changes to any `layer_*.py`, no changes to `composition.py`, no changes to `taxonomy.py`**.

**Decisions:**
- **Explicit type guard in `load_prompt`.** The spec's reference implementation does not include an `isinstance` check, but its acceptance criterion ("`load_prompt('synonym_label')` raises `KeyError`") cannot be satisfied without one because `ModificationType` mixes in `str` and a bare string equals the enum member by both `==` and `hash`. The one-line `if not isinstance(modification_type, ModificationType): raise KeyError(modification_type)` guard is the minimal change that honors both the spec's reference shape and its acceptance test. Documented in the docstring with a one-line "why" comment.
- **Loader is dumb (no `str.format`).** The JSON-contract block contains literal `{` / `}` that aren't Python placeholders — a formatter inside the loader would either require escaping every brace in the JSON literal (ugly for domain reviewers) or commit to a brace-classification policy. Deferring rendering to C3 keeps the loader's surface narrow.
- **`PROMPT_FILENAMES` is auto-computed from `ModificationType`.** Dict comprehension over the enum. Future enum additions surface as `FileNotFoundError` at call time, which is the right forcing function to author the corresponding `.txt`.
- **`new_param.txt`'s `{allowlist}` slot stays unfilled.** Phase B4's `configs/synthetic/new_param_allowlist.yaml` is not yet authored. C3's `new_param` codepath will load the YAML (when it lands) and format the prompt accordingly. Until then the LLM is asked to use its best judgement; Phase F prompt-tuning revisits.
- **Brace-audit `new_param.txt` exemption.** The spec's `test_prompt_no_unrendered_python_braces_outside_slots` heuristic — "every `{` in the body region (text before `Responde SOLO con un JSON`) must be a declared placeholder" — would technically work on `new_param.txt`, but the spec explicitly exempts it because its JSON literal embeds nested `{` / `}` (the `{"label": "a", "value": "..."}` array entries) the heuristic can't cleanly partition. Honoured via `pytest.skip` with the per-spec rationale in the skip message.
- **No native-Spanish review gate.** The sprint's quality gate is *structural* (placeholders present, JSON contract declared, role-line "Eres" prefix, Spanish-register marker), not *linguistic*. A native domain reviewer will polish prompts during the F1 pilot retrospective when real LLM-output acceptance-rate data is available — pre-polish review would be hand-wavy without that grounding. **Deferred:** Phase F1/F2 prompt-tuning with the domain reviewer.

**Problems encountered:**
- The initial test run reported 1 failure on `test_load_prompt_raises_keyerror_on_string_input`. Root cause: `ModificationType(str, Enum)` makes the enum members `==` and `hash`-equal to their string values, so `PROMPT_FILENAMES["synonym_label"]` succeeds despite the spec's intent that only enum members should be valid keys. Fix: added one-line `isinstance` guard inside `load_prompt`. Re-ran the suite → 297 passed, 1 skipped, zero failures. This is the kind of subtle StrEnum trap the spec's "loose-coercion alternative considered and rejected" rationale was anticipating; the test gate caught the gap.
- No other issues.

**What changed in the plan:** None. The C1 deliverable matches the spec's "Scope" block; the "Out of scope" decisions are honoured (no `llm_proposer.py` stub, no placeholder substitution, no JSON-schema validation, no native-Spanish review, no `configs/synthetic/*.yaml`, no changes to existing `src/synthetic/` modules). The one micro-deviation from the spec's reference code — the `isinstance` guard — is documented above as the minimal change that satisfies the spec's binding acceptance criterion.

**CLAUDE_SYNTHETIC.md updated:** yes — `prompts/` block flipped ❌ → ✅ (13 rows) and Sprint History entry prepended.

**Next step:** **Sprint 13 — Phase C Task C2 (`llm_proposer.py` — LLM client + retry/fallback).** With the prompt library frozen, the next concern is the offline client that pairs each prompt with a `pydantic` or `jsonschema` model and a per-type retry/fallback policy. The variant proposer (C3) consumes the client; the variant catalog writer (C4) writes the JSON-per-concept artefacts the orchestrator (D2) reads.

---

### Sprint 11 — Phase B Task B5: composition rules (`composition.py`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_11.md`](sprints/SPRINT_11.md)
**Tasks from backlog:** B5 — encode the pre-apply compatibility matrix and layer-apply ordering as a pure validator (`compose_rules`); add a contract test suite; surgically expose the validator via `test_mutator.py`'s audit; update protocol §3.3 / §5 Phase B B5 to reflect the canonicalised PD→L1→L2→L3 order and the YAML deferral.

**What was done:**
- **Created [`src/synthetic/composition.py`](../../src/synthetic/composition.py).** A new module exposing one public function `compose_rules(rules) -> (admissible_rules_in_apply_order, skipped_modifications)`, one constant `COMPATIBILITY_MATRIX: dict[(ModificationType, ModificationType), CompatibilityVerdict]` (six starter entries — all `(NEW_PARAM, L1-type) → LAYER_DEPENDENCY`), one enum `CompatibilityVerdict(str, Enum)` with four members (`COMPATIBLE`, `SAME_TARGET`, `LAYER_DEPENDENCY`, `UNSTACKABLE`), and a private `_canonical_key(rule)` per-layer addressing helper. The composer is state-blind (never reads stage JSON), pure (no mutation of input or output), and shallow-aliasing (admissible-rules list contains the input rule dict objects themselves, not copies). Three sequential passes after a stable layer-sort: (1) canonical-key dedup — same key → later rule skipped with `Modification(status="skipped", reason="same_target_conflict...")`; (2) PD-axis-vs-L1-param same-axis pass — L1 rule whose `param` matches any earlier-admissible PD rule's `param` → skipped with `Modification(status="skipped", reason="layer_dependency_conflict...")`; (3) matrix pass — for every (earlier, later) pair, look up `COMPATIBILITY_MATRIX.get((earlier_mtype, later_mtype), COMPATIBLE)`; `LAYER_DEPENDENCY` entries are no-op here because step 2 is the authoritative detector; `UNSTACKABLE` (currently empty) will emit a skip in future. Canonical keys: `(PARAM_VALUE, param, value)` / `(TEXT_VARIABLE, var.lstrip("$"), _norm_cond(condition))` / `(TEMPLATE, field.lower(), original)` / `(PARAM_DEFINITION, param)`. `_norm_cond` is imported via `from .layer_l2 import _norm as _norm_cond` to preserve the single-source-of-truth for whitespace normalisation. Unknown `rule["type"]` raises `ValueError`; missing addressing fields raise `KeyError` (same loose contract as `mutator._resolve_type`).
- **Added [`tests/synthetic/test_composition.py`](../../tests/synthetic/test_composition.py) — 26 test functions, 34 individual cases after parametrisation expansion.** Coverage: signature pin; empty-input edge case; single-rule pass-through (parametrised over per-layer ×4); layer apply-order from a reverse-submission L3→L2→L1→PD batch; stable within-layer order; same-target dedup per layer (L1, L1-across-types, L2 with $-strip + whitespace symmetry, L3 with field-case symmetry, PD); distinct-targets-no-conflict (L1); PD-vs-L1 same-axis skip with axis named in reason; PD-vs-L1 different-axis admissible (binding constraint for the matrix-pass LAYER_DEPENDENCY no-op decision); all six L1 types skipped under same-axis PD (parametrised ×6); PD+L2-on-different-var compatible; mixed-layer-no-conflicts happy path; no-mutation-of-input contract via `copy.deepcopy` snapshot equality; admissible-aliases-input identity contract via `is`; malformed-input exceptions (`ValueError` on unknown type code; `KeyError` per layer on missing addressing field); idempotence under recomposition over a 6-rule mixed batch; matrix audits (only valid enum members; exactly the six starter entries with the expected verdicts). The plan's "≥20 new tests" gate is exceeded; the "if all 26 cases land with parametrisations → ~33" headline is also exceeded.
- **Surgically edited [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py).** Added `from synthetic.composition import compose_rules` under the existing import block; added one new test `test_composition_module_exposes_compose_rules` at the bottom asserting `list(inspect.signature(compose_rules).parameters) == ["rules"]`. The nine surviving Sprint-10 tests are untouched.
- **Did not create `configs/synthetic/composition_rules.yaml`.** Deliberate deviation from the protocol's file-tree listing — the matrix lives as a Python module-level constant in `composition.py` for B5. Cost-benefit on Sprint 11's starter content (six entries) didn't justify the parse step + schema validation surface + asymmetric edit path that YAML externalisation introduces. Reversible: a single follow-up sprint can wrap `COMPATIBILITY_MATRIX = _load_matrix(Path(...) / "composition_rules.yaml")` around the current inline definition without changing the composer's public surface.
- **Updated [`docs/synthetic/RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md).** §5 Phase B B5 row: appended postscript "Matrix lives in `src/synthetic/composition.py` as a Python module-level constant for B5; YAML externalisation (`configs/synthetic/composition_rules.yaml`) deferred to a later phase if Phase C / E tooling needs an editable surface without code changes." Line-302 file-tree listing: annotated `composition_rules.yaml` as deferred. §3.3 phrasing: parenthetical "(or PD-first if the new axis affects L2/L3 — see §B5 composition rules)" is no longer the canonical pin — Sprint 11's housekeeping inserts an explicit canonical-order note immediately after that paragraph clarifying that PD is **always** first when present.
- **Updated [`docs/synthetic/CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md).** Flipped ❌ → ✅ for `src/synthetic/composition.py` in the "New Files in This Branch" block with the sprint-spec annotation. Prepended an "After Sprint 11 — …" entry to the Sprint History section.

**Key results:**
- **Test count: 124 → 159 (+35).** `pytest tests -q` reports `159 passed in 0.19s, zero failures, zero skips.` Breakdown of the +35 delta: +34 new `test_composition.py` cases (26 specific functions × parametrisation expansion to 34 individual cases — 4 single-rule-per-layer + 6 L1-types-under-PD-axis-conflict are the two parametrised functions), +1 new `test_mutator.py` audit. The sprint plan's ≥145 minimum is exceeded; the recommended ≥158 if all 26 cases land is also exceeded.
- **Composer is importable and conforms to the published contract.** `from synthetic.composition import compose_rules, COMPATIBILITY_MATRIX, CompatibilityVerdict` succeeds. `inspect.signature(compose_rules).parameters` is exactly `["rules"]`. `compose_rules([])` → `([], [])`. `len(COMPATIBILITY_MATRIX) == 6`.
- **End-to-end smoke check passes.** Submitted 5 rules (L3 omission, L2 paraphrase, L1 on A, L1 on K, PD on K), out-of-order. Composer returned 4 admissible in order `[new_param, synonym_label_on_A, paraphrase, omission]` and 1 skipped `Modification` whose `type` was `SYNONYM_LABEL` (the L1-on-K rule that PD-introduced), whose `reason` contained `layer_dependency_conflict` and named the `K` axis.
- **Phase B5 deliverable is the *static* composer.** B5 does not wire `compose_rules` into `mutator._apply_rules`; the orchestrator continues to iterate rules in submission order. The Phase C/D wiring decision (applier-side filter, orchestrator-side filter, or Phase C3 proposer-side filter) is deferred — Sprint 11 lands the composer as an importable function with a verified contract.
- **Git status end-of-sprint** (sprint-scoped files only): new `src/synthetic/composition.py`, new `tests/synthetic/test_composition.py`, modified `tests/synthetic/test_mutator.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`, modified `docs/synthetic/RESEARCH_PROTOCOL.md`, new `docs/synthetic/sprints/SPRINT_11.md`. Nothing else; in particular **no changes to `src/synthetic/mutator.py`, no changes to any `layer_*.py`, no changes to `taxonomy.py`**.

**Decisions:**
- **Layer apply-order canonicalised as PD → L1 → L2 → L3.** Protocol §3.3 had ambiguous phrasing ("L1 first, then L2, L3, PD" with a parenthetical "or PD-first if the new axis affects L2/L3 — see §B5"). Sprint 11 pins the canonical order as PD-always-first: PD's job is to *add an axis*; L1's `(param, value)` addressing key presumes the axis already exists. If a batch contains both, PD must run first or L1 fails to resolve. The 4-layer order is one consistent rule; the conditional "PD-first only if the new axis affects L2/L3" framing was unnecessarily nuanced. Protocol patched in this sprint.
- **Matrix pass treats `LAYER_DEPENDENCY` as a no-op.** The PD-vs-L1 same-axis pass (step 2) is the authoritative detector. The matrix entry expresses *type-pair policy*; whether a specific rule pair triggers it is a *value-pair check*. Test `test_pd_introduces_axis_l1_on_different_axis_no_conflict` is the binding constraint: PD-on-K + L1-on-A must both survive even though `(NEW_PARAM, SYNONYM_LABEL)` is a `LAYER_DEPENDENCY` matrix entry. The matrix is in place for future `UNSTACKABLE` entries (which the matrix pass *does* act on), keeping additive extension a no-code-change update.
- **Canonical-key dedup is the workhorse.** The starter matrix's six entries are all redundant with the dedicated step-2 same-axis pass. Most real-world conflicts (two `synonym_label`s on same `(param, value)`; two `paraphrase`s on same `(var, condition)`; two `omission`s on same `(field, original)`) are caught by canonical-key equality without consulting the matrix. The matrix's value is *future extension* — adding `UNSTACKABLE` entries (e.g., `OMISSION` × `REORDER` on overlapping spans, if research uncovers a structural problem) is one-line code-free change.
- **`Modification(status="skipped", reason=...)` is the conflict signal, not exceptions.** Matches protocol §4 "skip + log via the `Modification` record". A composer that raised on conflict would force the orchestrator to wrap every batch in try/except and would lose the conflict signal in the per-item audit trail Phase E1 needs.
- **YAML deferral is deliberate.** The protocol's file-tree listing reserves `configs/synthetic/composition_rules.yaml` but doesn't specify schema or loading semantics. Six near-identical Python entries cost less to maintain than a parse step + schema validation + asymmetric edit path. Reversibility: when Phase C / E tooling needs to add ten-plus entries without code changes, wrap `_load_matrix(...)` around the current constant in a single follow-up sprint.
- **No mutation of input; admissible output aliases input rules.** Two complementary tests pin this from opposite directions. `test_no_mutation_of_input_rules` verifies the input list and every rule dict in it are byte-identical to a `deepcopy` snapshot after `compose_rules` returns; `test_admissible_output_aliases_input_rules` uses `is`-identity to verify the output dicts are the same objects as the inputs. The orchestrator's `_apply_rules` already deep-copies stage JSON at entry; rule dicts are the variant catalog's property and should not be cloned by an intermediate validator.
- **Re-composition is idempotent (fixed-point property).** Passing the composer's admissible output back through `compose_rules` returns the same admissible list with empty skipped log. Pinned by `test_idempotent_under_recomposition` over a 6-rule mixed batch. Phase E1's metadata-join pipeline can re-run the composer on an already-composed batch as part of metadata reconstruction without inflating the skipped log.

**Problems encountered:**
- The sprint plan's `test_same_target_dedup_l2` example used condition strings `'%B=="a"'` and `'%B  ==  "a"'` and asserted they should produce the same canonical key. Live L2 `_norm` (`re.sub(r"\s+", " ", s).strip()`) collapses *runs of whitespace* but does **not** insert whitespace where none exists, so `'%B=="a"'` normalises to itself (no spaces) and `'%B  ==  "a"'` normalises to `'%B == "a"'` (single space) — different keys, second rule was not deduped. Fix: changed the test's first rule to `condition='%B == "a"'` (single space) and the second to `'%B  ==  "a"'` (double space); both normalise to `'%B == "a"'` and the test now pins the symmetry the spec intended. The spec text describing the test as "single-space rule still matches double-space" form (matching Sprint 08's L2 worker test) was the right model.
- No other issues.

**What changed in the plan:** None. The B5 deliverable matches the spec's "Scope" block; the "Out of scope" decisions are honoured (no YAML, no `mutator.py` wiring, no `Modification` dataclass extension).

**CLAUDE_SYNTHETIC.md updated:** yes — file-map row (`composition.py` ❌ → ✅) and Sprint History entry prepended.

**Next step:** **Sprint 12 — Phase C Task C1 (`prompts/` — per-type Spanish prompt library).** With Phase B closed (all 12 mutator bodies live, composer landed), Phase C's prompt library is the natural successor. One Spanish prompt per `ModificationType` declaring its JSON-output contract. The Stage-A LLM proposer (C2/C3) reads these prompts; the composer (B5) validates the resulting rule batches before they reach the orchestrator (D1/D2).

---

### Sprint 10 — Phase B Task B4: PD `new_param` mutator body (`layer_pd.py`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_10.md`](sprints/SPRINT_10.md)
**Tasks from backlog:** B4 — promote the last surviving stub (PD — `new_param`) in [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) to a real body in a new [`src/synthetic/layer_pd.py`](../../src/synthetic/layer_pd.py) module; retire all remaining stub-test scaffolding.

**What was done:**
- **Created [`src/synthetic/layer_pd.py`](../../src/synthetic/layer_pd.py).** A single public function `apply_new_param(stage_json, concept_key, rule)` that adds a new axis to `concept["parameters"]`, optionally registers a new `$VAR` formula on `concept["text_variables"]` (auto-creating the block if absent), and optionally applies one or more substring patches to `concept["resumen"]` / `concept["texto"]`. The function validates rule shape (`param`, `label`, non-empty `values` list with pairwise-unique value labels, optional `text_variable` dict with non-empty `var` / `formula`, optional `template_patches` list with L3-style `(field, original, new)` entries), checks for axis-key collision and var-key collision (both raise `ValueError`), and re-implements the L3 patch loop inline (case-insensitive `field` coercion to `"resumen"` / `"texto"`, substring-uniqueness contract: zero matches → `KeyError`, >1 → `ValueError`). Emits exactly one `Modification(type=NEW_PARAM, layer=PARAM_DEFINITION, param=<new axis key>, new=<new axis label>, var=<new var key if any>, status="applied")` per rule, regardless of how many blocks were touched.
- **Wired the PD mutator into [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH`.** Added a `from .layer_pd import apply_new_param as _layer_pd_apply_new_param` import (the alias is load-bearing — the worker shares its natural name with the orchestrator function defined later in the same module). Deleted the `_stub_new_param` function definition. Swapped the `ModificationType.NEW_PARAM` entry in `_DISPATCH` to `_layer_pd_apply_new_param`. Updated the module docstring from "6 L1 + 3 L2 + 2 L3 live, 1 still stub (PD — `new_param`)" to "all 12 (6 L1 + 3 L2 + 2 L3 + 1 PD) mutators live; dispatcher fully promoted from stubs". The orchestrator `apply_new_param` (single-rule entry-point) is byte-identical pre/post — its body already deep-copied input, resolved the type, gated the layer, and dispatched via `_DISPATCH[mtype]`. `_StubResult` was left in place per the sprint recommendation (cosmetic rename to `_MutatorResult` would touch the orchestrator type annotations needlessly — vestigial but harmless).
- **Added [`tests/synthetic/test_layer_pd.py`](../../tests/synthetic/test_layer_pd.py) — 26 contract test cases.** Inline `oeb020_stage2` fixture mirrors the real `OEB020$` shape verified against the L1 fixture and `data/intermediate/OBRA CIVIL/OBRA_CIVIL.json` (two axes `A: Nº TUBOS`, `B: TIPO DE TERRENO`; non-empty `text_variables["K"]`; `resumen` and `texto` templates with `$A` / `$K` references and a final `\` sentinel on the resumen). Coverage:
  - (1)–(4) Happy paths: axis-only, axis+text_variable, axis+single-template-patch, full combo (axis + text_variable + 2 template_patches one on `RESUMEN` and one on `TEXTO`). Each asserts the right block was edited, the others are bytewise-preserved, and the emitted `Modification` carries the right `param` / `new` / `var` / `status` fields.
  - (5)–(6) Collision raises: `param="A"` on a concept that already has axis `A` → `ValueError`; `text_variable["var"]="K"` on a concept that already has var `K` → `ValueError`. Both messages name the colliding key and the concept.
  - (7)–(8) Template patch errors: `original="NO_SUCH_SUBSTRING"` → `KeyError`; a fixture extended to contain `"tubos"` twice in `texto` plus a patch with `original="tubos"` → `ValueError` whose message names the substring, the count (2), and the field (`'texto'`).
  - (9)–(10) Missing concept-key → `KeyError`; concept lacking `parameters` block → `KeyError`.
  - (11)–(15) Rule-shape errors: empty `param`, missing `param` field, empty `label`, empty `values`, duplicated value labels — all `ValueError` whose messages identify the offending field.
  - (16) `text_variable` block without `formula` → `ValueError`.
  - (17) `text_variables` block auto-created when the rule supplies a var on a concept that lacks the block entirely.
  - (18) Unknown template-patch `field` (e.g., `"DESCRIPCION"`) → `ValueError` naming the accepted values `'RESUMEN'` / `'TEXTO'`.
  - (19) Field-case normalisation: parametrised over `TEXTO` / `texto` / `Texto` / `tExTo`, all produce the same `out["OEB020$"]["texto"]`. The emitted `Modification.field` is `None` for PD — the patch's field doesn't propagate to the audit record (full detail is in the rule payload), exactly as the sprint spec dictates.
  - (20) Orchestrator routing: `mutator.apply_new_param` (the orchestrator) delivers the axis to `out` and the caller's input is byte-identical via `json.dumps(..., sort_keys=True, ensure_ascii=False)`.
  - (21) Wrong-layer rule (`type="paraphrase"`) passed through the orchestrator → `ValueError` from `_gate_layer`.
  - (22) `len(log) == 1` for a full-combo rule that touched all four blocks — pins the "one rule → one `Modification`" contract.
  - (23) Caller-dict-unchanged after a full-combo orchestrator call — second snapshot of `json.dumps(..., sort_keys=True, ensure_ascii=False)` matches the first.

  Including the four field-case parametrisations the file counts 26 contract cases, exceeding the sprint plan's ≥18 minimum and the recommended ~23 headline.
- **Pruned [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py).** Deleted `_LAYER_TO_APPLY`, `_STUB_TYPES`, the parametrised `test_each_stub_raises_notimplemented_with_type_code` function, and `test_deep_copy_purity_on_notimplemented` (all four assumed at least one stub remained). Dropped the now-unused `Layer` and `TYPE_TO_LAYER` imports from `synthetic.taxonomy`; kept `ModificationType` for the dispatch-table-size test. Added `test_no_stubs_remain_in_dispatch` at the bottom: asserts every `_DISPATCH` value's `__name__` starts with `apply_` and no value's `__name__` starts with `_stub_`. Net delta for this file: −2 (parametrised stub + deep-copy-purity removed) + 1 (audit added) = −1 case.

**Key results:**
- **`pytest tests -q` → 124 passed in 0.11s, zero failures, zero skips.** Baseline was 99 (Sprint 09). Net delta: −2 (the two retired `test_mutator.py` cases) + 26 (new `test_layer_pd.py` cases — 22 specific cases + 4 field-case parametrisations) + 1 (new `test_no_stubs_remain_in_dispatch` audit) = +25, landing at 124. The sprint plan's projected minimum was 116 (99 − 2 + 18 + 1), recommended was 121 (99 − 2 + 23 + 1); 124 exceeds both. The binding gate ("≥18 new PD contract cases, all green, no skips, no regressions in the surviving baseline") is satisfied.
- **Dispatcher fully promoted: 12 live, 0 stubs.** Smoke check `python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import ModificationType; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in ModificationType); assert len(_DISPATCH) == 12; print('dispatcher fully promoted:', len(_DISPATCH), 'live, 0 stubs')"` printed `dispatcher fully promoted: 12 live, 0 stubs`. The 12-entry total and the `set(_DISPATCH) == set(ModificationType)` invariants are unchanged.
- **`from synthetic.mutator import _stub_new_param` correctly raises `ImportError`** — the last stub function definition is physically gone. The `_stub_*` prefix has been eliminated from `mutator.py` entirely.
- **End-to-end smoke ok.** A `mutator.apply_new_param(stage, "OEB020$", rule)` call with a full-combo rule (axis `F: CALIDAD ACABADO` with two values, `text_variable={"var":"F","formula":'"estándar" * (%F=="a") + "premium" * (%F=="b")'}`, one `TEXTO` patch injecting `calidad $F`) mutates only the targeted blocks inside the returned `out`, the caller's input is byte-identical under `json.dumps(sort_keys=True, ensure_ascii=False)` pre/post, and the emitted `Modification` carries `param="F"`, `new="CALIDAD ACABADO"`, `var="F"`, `status="applied"`.

**Decisions made:**
- **PD breaks the "wrappers, one worker" pattern — deliberately.** L1 has six wrappers + one worker; L2 has three + one; L3 has two + one. PD has exactly one `ModificationType`, so it has one function. Forcing a `_install_new_param` private worker + a thin `apply_new_param` wrapper would add zero structural benefit (no fan-out to compress) and would obscure that PD is genuinely different from the value/fragment/substring families. The single-function surface stays; the divergence is documented in both the module docstring and this log entry.
- **Orchestrator/worker name clash resolved with an import alias, not a rename.** `apply_new_param` is simultaneously the orchestrator's public name (top-level in `mutator.py`, part of the dispatcher surface `apply_l1`/`l2`/`l3`/`apply_new_param`) and the natural name for the layer worker (matching `apply_synonym_label` / `apply_paraphrase` / `apply_omission`). Renaming either side would either break naming symmetry with L1/L2/L3 or break the public dispatcher surface. The `from .layer_pd import apply_new_param as _layer_pd_apply_new_param` alias is the strictly-smaller change — one line in `mutator.py`, no test changes, no doc changes downstream.
- **PD `add` semantics replace L1/L2/L3 `replace` semantics — collisions raise loudly.** A `new_param` rule that targets a `param` key already present on the concept is a catalog-authoring error (the variant proposer in Phase C should never emit it); the applier raises `ValueError` with a message naming both the colliding key and the concept. Same contract for var-key collisions on `text_variables`. The cost of silent overwrite (a Phase D run silently destroys an existing axis or formula) vastly outweighs the cost of a loud failure that the variant catalog reviewer must investigate. Verified by `test_param_collision_raises` and `test_var_collision_raises`.
- **`text_variables` block auto-creation is the only "create-on-write" path in PD.** A stage-2 concept legitimately may have no `text_variables` (every template token is a direct `$A` / `$B` axis reference, no `$K`-style indirection). When the rule supplies a `text_variable` block, the worker creates `concept["text_variables"] = {}` and inserts the new var. The rationale: a concept without `parameters` isn't parametric (PD has nothing to mutate, the worker raises `KeyError`); a concept without `text_variables` is fine — PD can install the first one. The asymmetry is principled. Verified by `test_text_variables_block_auto_created`.
- **Template patches reuse the L3 substring-uniqueness contract but the worker re-implements the loop inline rather than importing L3's `_replace_substring`.** L3's worker emits one `Modification` per patch (matching the per-rule contract for L3, where one rule = one substring rewrite); PD wants exactly one `Modification` per rule even when N patches were applied. Importing L3's private worker would force a choice between L3's per-patch emission and PD's one-Modification-per-rule contract. The ~10 lines of patch-validation duplication (field-case lowercase coercion, template lookup, `str.count` check, `str.replace(original, new, 1)`) is the deliberate price of contract isolation; refactoring the shared substring logic into a common utility is explicitly **not** in scope for B4 (would need its own sprint to design the audit-emission interface).
- **Template patches apply in submission order; later patches may fail if earlier patches rewrote their region.** The intentional semantic-blind contract — patch ordering is the rule author's responsibility, exactly like the L3 stacked-rule contract from Sprint 09. No reordering, no "skip + log"; if a patch's `original` no longer matches because an earlier patch in the same rule rewrote that region, the worker raises `KeyError`. Phase C's variant proposer is responsible for ordering patches such that each match site survives.
- **One `Modification` per rule, even when three blocks were edited (axis + text_variable + N template_patches).** The `Modification` dataclass overloads its existing fields for PD: `param=<new axis key>`, `new=<new axis label>`, `var=<new var key if any>`. The full mutation delta (`values` list, `formula` string, every `template_patch`'s `(field, original, new)` triple) lives in the rule payload — the variant catalog (Phase C4) stores the rule alongside the `Modification`, and the metadata-join (Phase E1) reconstructs the per-item metadata from both. Maintaining "one rule → one `Modification`" uniformly across all 12 types is more valuable than capturing every PD edit in the dataclass — the alternative (`Modification` sub-records or per-block ranges) would couple the audit schema to per-type structure and ripple through Phase E. Verified by `test_modification_has_exactly_one_entry`.
- **No `new_param_allowlist.yaml` lookup, no semantic-similarity check, no Spanish heuristic in the applier.** The applier is semantic-blind, exactly like Sprints 07–09's L1/L2/L3 appliers. A rule that adds a new axis labelled `"GRADE"` when the concept already has a (label-wise but not key-wise) similar `"QUALITY"` axis succeeds at apply-time. Cross-axis semantic collision detection lives in Phase E (reviewer harness); allowlist enforcement lives in Phase C (variant proposer) and Phase E. Phase B's applier remains the dumbest possible substitution engine that still preserves the data contract.

**Problems encountered:**
- *No issues.* The work landed in one read/edit cycle per file with no rework. The PowerShell-escaping pain Sprints 08–09 documented was avoided by writing the end-to-end smoke to a temp `_smoke_pd.py` and running `python _smoke_pd.py`; removed the temp file at the end of verification.
- *No deviations from the sprint plan*, except for the case-count headline: the plan recommended ~23 cases (counting parametrisations), but the field-case test unfolded to 4 parametrisations (matching L3's pattern from Sprint 09), landing at 26 contract cases and 124 total. The binding gate is unchanged. `_StubResult` was kept (not renamed to `_MutatorResult`) per the sprint's explicit recommendation — cosmetic, vestigial after stub removal, will be cleaned up if a future sprint touches the orchestrator's type annotations for another reason.

**What changed in the plan as a result:**
- B4 closes. The protocol backlog's [`§5 Phase B B4`](RESEARCH_PROTOCOL.md) entry is now done. **Phase B's mutator-body work is complete** — every entry in `_DISPATCH` resolves to a real `apply_*` function; the `_stub_*` prefix has been eliminated from `mutator.py` entirely; the parametrised stub test in `test_mutator.py` is gone; `test_deep_copy_purity_on_notimplemented` is gone.
- Next backlog item: **B5 — `src/synthetic/composition.py` (stacking rules).** With all 12 mutator bodies live, the next concern is the per-pair compatibility matrix that gates which rule types may stack on the same item (e.g., `OMISSION` + `REORDER` on the same template is structurally fragile; `NUM_TO_TEXT` + `UNIT_CONVERSION` on the same `(param, value_label)` is a no-op-overwrite hazard). Sprint 11 will encode the matrix and add a `compose_rules(rules)` validator that the orchestrator can consult before fanning rules through `_DISPATCH`.

**CLAUDE_SYNTHETIC.md updated:** `yes` — flipped ❌ → ✅ for `src/synthetic/layer_pd.py` in the "New Files in This Branch" block with the standard Sprint-10 annotation; prepended an "After Sprint 10 — …" entry to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_11.md` for B5 — `composition.py` for stacking-rule encoding. Different kind of code (compatibility-matrix encoder + validator) — no new per-type mutators. The "one worker, N wrappers" pattern that drove Sprints 07–09 is now permanently retired; B5's design will be matrix-shaped, not fan-out-shaped.

---

### Sprint 09 — Phase B Task B3: L3 `template` mutator bodies (`layer_l3.py`)
**Date:** 2026-05-20
**Sprint file:** [`sprints/SPRINT_09.md`](sprints/SPRINT_09.md)
**Tasks from backlog:** B3 — promote the two L3 `template` `NotImplementedError`-raising stubs in [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) to real bodies in a new [`src/synthetic/layer_l3.py`](../../src/synthetic/layer_l3.py) module.

**What was done:**
- **Created [`src/synthetic/layer_l3.py`](../../src/synthetic/layer_l3.py).** One shared private worker `_replace_substring(stage_json, concept_key, rule, mod_type)` plus two thin public wrappers `apply_omission`, `apply_reorder`. The worker validates `rule["field"]` (string, case-insensitive, must coerce to `"resumen"` or `"texto"`), looks up `concept[field_lower]` as a string template, validates `rule["original"]` (non-empty string) and `rule["new"]` (string — may be empty), checks `template.count(original)` (raise `KeyError` on zero, `ValueError` on >1), then writes `concept[field_lower] = template.replace(original, new, 1)`. Emits exactly one `Modification(layer=TEMPLATE, type=<wrapper's mod_type>, field=<UPPERCASE>, original=<rule's substring>, new=<rule's replacement>, status="applied")`. The two wrappers exist purely to set the per-type `mod_type` enum on the emitted record — the mechanics are uniform; the semantics live in the `Modification.type` field, exactly as Sprint 07–08's "wrappers, one worker" pattern prescribes.
- **Wired the two L3 mutators into [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH`.** Added the `from .layer_l3 import (apply_omission, apply_reorder)` import block under the existing L2 import. Deleted the two obsolete `_stub_omission`, `_stub_reorder` function definitions. Swapped the two matching `_DISPATCH` entries to the new `apply_*` wrappers. The surviving `_stub_new_param` (PD) stays in place. Updated the module docstring from "6 L1 + 3 L2 live, 3 still stubs (L3 / PD)" to "6 L1 + 3 L2 + 2 L3 live, 1 still stub (PD — `new_param`)". `_apply_rules` / `_resolve_type` / `_gate_layer` / `apply_l1`/`l2`/`l3`/`apply_new_param` are untouched.
- **Added [`tests/synthetic/test_layer_l3.py`](../../tests/synthetic/test_layer_l3.py) — 21 contract test cases.** Inline `oeb020_stage4` fixture mirrors the real `OEB020aaaaa` shape verified against `data/intermediate/OBRA CIVIL/OBRA CIVIL_stage4.json` (`resumen` with `$A` / `$K` / `$G(%C)/$H(%D)/$J(%F)` placeholders ending in the FIEBDC sentinel `\`; multi-line `texto` with `$A` / `$I` / `$N` / `$P` / `$M` / `$C` / `$D` / `$F` references). Coverage: (1)–(4) `test_happy_path_omission_on_texto/_resumen` and `test_happy_path_reorder_on_texto/_resumen` exercise both types on both templates; (5) `test_other_template_untouched` parametrised over 2 cases pins the cross-template-isolation guarantee; (6) `test_field_case_normalization` parametrised over 4 cases (`TEXTO` / `texto` / `Texto` / `tExTo`) pins case-insensitive lookup and canonical-uppercase emission; (7) `test_apply_l3_orchestrator_threads_rules` exercises a 2-rule batch (one `omission`, one `reorder`, one on `texto`, one on `resumen`) with snapshot-purity assertion; (8) `test_omission_with_empty_new` pins the empty-`new`-is-allowed semantic; (9) `test_reorder_with_no_op_new_succeeds` pins the semantic-blind contract (rule with `new == original` still emits `status="applied"`); (10)–(14) `test_missing_concept_key_raises` / `test_missing_field_template_raises` / `test_unknown_field_raises` / `test_original_not_found_raises` / `test_original_matches_multiple_times_raises` cover all error paths and assert that error messages name the missing/invalid entity; (15)–(16) `test_empty_original_raises` and `test_missing_new_field_raises` cover invalid rule shapes; (17) `test_modification_original_byte_equals_rule_original` documents the L3 divergence from L1/L2 (rule's `original` IS the addressing key for L3, not informational); (18) `test_caller_dict_unchanged_after_apply` snapshots `json.dumps(..., sort_keys=True)` pre/post `apply_l3`; (19) `test_replace_substring_directly` exercises the private worker. The plan's "≥15 new tests" gate is exceeded.
- **Narrowed the existing stub tests in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py).** `_STUB_TYPES` now reads `[t for t in ModificationType if TYPE_TO_LAYER[t] is Layer.PARAM_DEFINITION]` (1 case: `new_param`), down from Sprint 08's 3 cases. `test_deep_copy_purity_on_notimplemented`'s rule changed from `{"type": "omission"}` against `apply_l3` (now a live mutator) to `{"type": "new_param"}` against `apply_new_param` (the last surviving stub). All other tests in the file are untouched.

**Key results:**
- **`pytest tests -q` → 99 passed in 0.13s, zero failures, zero skips.** Baseline was 78 (Sprint 08). Net delta: −2 (the two L3 stub cases narrowed out of `test_each_stub_raises_notimplemented_with_type_code`) + 21 (new `test_layer_l3.py` cases — counting parametrisations: 4 happy-path + 2 cross-template parametrised + 4 field-case parametrised + 11 specific cases) = +19, landing at 99. The sprint plan's projected minimum (91) and recommended (~95) headlines are both exceeded; two of the spec's bullets (`test_other_template_untouched`, `test_field_case_normalization`) unfolded into parametrised pairs/quads. The binding gate ("≥15 new L3 contract cases, all green, no skips, no regressions in the surviving baseline") is satisfied.
- **Dispatcher audit ok: 11 live, 1 still stubs.** Smoke check verified that every `PARAM_VALUE` / `TEXT_VARIABLE` / `TEMPLATE` entry in `_DISPATCH` resolves to a function whose `__name__` starts with `apply_`, and only `NEW_PARAM` still resolves to a `_stub_*`. The 12-entry total and the `set(_DISPATCH) == set(ModificationType)` invariants are unchanged.
- **`from synthetic.mutator import _stub_omission` correctly raises `ImportError`** — the two obsolete L3 stub function definitions are physically gone (verified by the existing import-failure smoke check pattern from Sprints 07–08).
- **End-to-end smoke ok.** A `apply_l3(stage, "OEB020aaaaa", [{"type":"omission","field":"TEXTO","original":" $I,","new":""}])` call mutates only the targeted span inside the returned `out` (`" $I,"` is deleted from the texto), the caller's input is byte-identical under `json.dumps(sort_keys=True)` pre/post, and the emitted `Modification` carries `field="TEXTO"`, `original=" $I,"`, `new=""`, `status="applied"`, `layer=TEMPLATE`.

**Decisions made:**
- **Field-case normalisation lives at the rule boundary, not in the data.** Stage-4 JSON dict keys are lowercase (`concept["resumen"]`, `concept["texto"]`); the proposal's worked example (`§2.3`) emits `Modification.field` in uppercase (`"field": "RESUMEN"`). The worker accepts `rule["field"]` in any case (`TEXTO` / `texto` / `Texto` / `tExTo`), coerces via `field.lower()` for the stage-JSON lookup, and emits `Modification.field` in canonical uppercase via `field.upper()`. The reasoning: the catalog's authors think in screaming-snake-case (matching BC3's `\RESUMEN\` / `\TEXTO\` record-type sentinels), but the JSON parser landed on lowercase. The rule schema accommodates the human convention; the data lookup uses the machine convention; the log pins the canonical proposal form. Verified by `test_field_case_normalization`.
- **Rule's `original` is load-bearing at apply-time for L3 — deliberate divergence from L1/L2.** In L1 the rule's `original` was ignored (informational, log captured the live `value_entry["value"]`); in L2 the rule had no `original` field (log captured the live `m.group("frag")`). In L3 the rule's `original` IS the addressing key — there is no other structural handle to identify which substring to mutate. The "log-`original`-is-authoritative" contract is preserved by a different mechanism: the worker raises `KeyError` if the substring doesn't occur, so a stale rule cannot silently emit an out-of-date `original`. Variant-catalog drift detection at Phase E review remains the safety net. Documented in `test_modification_original_byte_equals_rule_original`'s docstring so future readers don't expect L1/L2 semantics.
- **Uniqueness is by substring, not by regex.** `str.count` and `str.replace(original, new, 1)` are the entire matching primitive. The worker does **not** interpret `$var` references, does not parse the template grammar, and does not normalise whitespace. The rule author is responsible for picking an `original` that: (a) occurs exactly once, and (b) starts/ends at the right boundary (e.g., picking `" $I,"` rather than `"$I"` if the goal is to remove the leading space and trailing comma together). The multi-match test exercises this with `"de "`, which appears many times in the real `texto` template — the worker raises `ValueError` with the count and the field name. This pushes the "what should the precise mutation be?" complexity to Phase C prompts, where it belongs.
- **Empty-`new` is allowed; no-op `new == original` is allowed.** The worker is semantic-blind. An omission rule with `new = ""` deletes the matched span; a reorder rule with `new == original` is a structural no-op but still emits a `Modification(status="applied")` with `original == new`. Phase C will constrain its proposer to emit empty `new` for `omission` and non-trivial reorderings for `reorder` — that's a generation-time invariant, not an applier-time invariant. Verified by `test_omission_with_empty_new` and `test_reorder_with_no_op_new_succeeds`.
- **Cross-template side effects are forbidden by construction.** A rule's `field` is authoritative; the worker touches only the named template (`resumen` or `texto`), never the other. A rule that wants to mutate both must be issued as two separate rules. Verified by `test_other_template_untouched` parametrised over both directions.
- **Two wrappers, one worker — Sprints 07–08's pattern lands cleanly on L3.** `_replace_substring` is the L1 `_replace_value` and L2 `_replace_fragment` patterns adapted for arbitrary template substrings. The wrappers exist purely to set the `Modification.type` enum. Per-type semantic enforcement (does this "omission" really remove a `$var` and only a `$var`? does this "reorder" really change constituent order rather than just modify the prose?) lives upstream in Phase C prompts and downstream in Phase E review, never inside the applier.
- **Outer-level `copy.deepcopy(stage_json)` stays inside `_apply_rules`, not the worker.** Same Sprint 07–08 contract — worker-level deep-copy would balloon costs on stacked rules in Phase B5 composition. The worker mutates its received `out` dict in place — legitimate because that dict is already a deep copy at the orchestrator boundary. Caller purity is pinned by `test_caller_dict_unchanged_after_apply` and by the orchestrator-threading test's snapshot assertion.

**Problems encountered:**
- *No issues.* The work landed in one read/edit cycle per file with no rework. The PowerShell escaping pain Sprint 08 documented was avoided by writing the end-to-end smoke to a temp `_smoke_l3.py` and running `python _smoke_l3.py`, as the sprint file recommended. Removed the temp file at the end of verification.
- *No deviations from the sprint plan*, except for the case-count headline: the plan projected ~95 with 19 listed cases, but two list items unfolded into parametrised pairs/quads (`test_other_template_untouched` × 2 and `test_field_case_normalization` × 4 instead of 1 each), landing at 21 contract cases and 99 total. The binding gate is unchanged.

**What changed in the plan as a result:**
- B3 closes. The protocol backlog's [`§5 Phase B B3`](RESEARCH_PROTOCOL.md) entry is now done.
- Next backlog item: **B4 — `src/synthetic/layer_pd.py` (`new_param` mutator).** The dispatcher-wiring pattern (import block + `_DISPATCH` swap + obsolete stub deletion) will be applied for the last time; after B4 lands `_STUB_TYPES` becomes `[]` and the parametrised stub test in `test_mutator.py` is deleted entirely. Note: PD differs structurally from L1/L2/L3 — `new_param` introduces a *new* parameter axis (with label, values, and a new text variable referencing it) rather than mutating an existing one; the `apply_new_param` entry-point accepts a single rule (not a list); the worker will need to coordinate edits across `parameters` and `text_variables` blocks in one stage-2 JSON.

**CLAUDE_SYNTHETIC.md updated:** `yes` — flipped ❌ → ✅ for `src/synthetic/layer_l3.py` in the "New Files in This Branch" block with the standard Sprint-09 annotation; prepended an "After Sprint 09 — …" entry to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_10.md` for B4 — `layer_pd.py`. The structural difference (cross-block edits inside a single stage-2 JSON, single-rule entry-point) means the worker design has to break from the "one private substitution worker, N thin wrappers" pattern that's served Sprints 07–09 well; budget the design discussion accordingly.

---

### Sprint 08 — Phase B Task B2: L2 `text_variable` mutator bodies (`layer_l2.py`)
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_08.md`](sprints/SPRINT_08.md)
**Tasks from backlog:** B2 — promote the three L2 `text_variable` `NotImplementedError`-raising stubs in [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) to real bodies in a new [`src/synthetic/layer_l2.py`](../../src/synthetic/layer_l2.py) module.

**What was done:**
- **Created [`src/synthetic/layer_l2.py`](../../src/synthetic/layer_l2.py).** One shared private worker `_replace_fragment(stage_json, concept_key, rule, mod_type)` plus three thin public wrappers `apply_paraphrase`, `apply_expansion`, `apply_compression`. The worker locates the `"FRAG" * (CONDITION)` segment inside `stage_json[concept_key]["text_variables"][var_key]` (after `$`-stripping the rule's `var`), captures the live quoted fragment as `original`, and rewrites the segment with `f'"{rule["new"]}" * ({as_written_cond})'` — preserving the as-written condition verbatim. Module-level regex `_FRAGMENT_PAT = re.compile(r'"(?P<frag>[^"]*)"\s*\*\s*\(\s*(?P<cond>[^)]*)\s*\)')` matches; `_norm(s)` collapses runs of whitespace before comparing the rule's condition against each captured `cond` group. The worker supports both str-typed entries (single-formula vars like `K`, `I`, `N`) and list-typed entries with at least one conditional element (`P`). Pure lookup-table list entries (`G` = `['"Diurno"', '"Nocturno"', ...]` with no `* (` segment in any element) raise `ValueError` with a message naming the var and explaining the shape mismatch. The three wrappers exist purely to set the per-type `mod_type` enum on the emitted `Modification` — mechanics are uniform; the semantics ride on the type code, exactly as Sprint 07's "wrappers, one worker" pattern prescribes.
- **Wired the three L2 mutators into [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH`.** Added the `from .layer_l2 import (apply_compression, apply_expansion, apply_paraphrase)` import block under the existing L1 import. Deleted the three obsolete `_stub_paraphrase` / `_stub_expansion` / `_stub_compression` function definitions. Swapped the three matching `_DISPATCH` entries to the new `apply_*` wrappers. The remaining three stubs (`_stub_omission`, `_stub_reorder`, `_stub_new_param`) stay in place. Updated the module docstring from "6 L1 live, 6 still stubs" to "6 L1 (`param_value`) and 3 L2 (`text_variable`) mutators are live … remaining 3 stubs (L3 / PD) still raise `NotImplementedError`". `_apply_rules` / `_resolve_type` / `_gate_layer` / `apply_l1`/`l2`/`l3`/`apply_new_param` are untouched.
- **Added [`tests/synthetic/test_layer_l2.py`](../../tests/synthetic/test_layer_l2.py) — 18 contract test cases.** Inline `oeb020_stage3` fixture mirrors the real `OEB020$` shape (str-typed `K` / `I` / `N` with `"FRAG" * (%B=="x")` segments; list-typed conditional `P`; lookup-table list `G` for the out-of-scope error path). Coverage: (1) `test_happy_path_per_type` parametrised over the 3 wrappers (paraphrase / expansion / compression); (2) `test_list_typed_conditional_fragment` exercises the list-shape; (3) `test_var_prefix_stripped` proves `var="K"` and `var="$K"` produce byte-identical results; (4) `test_modification_original_sourced_from_stage_json` pins the rule-`original`-is-informational / log-`original`-is-authoritative asymmetry (rule says `"WRONG"`, log says `"normal"`); (5) `test_apply_l2_orchestrator_threads_rules` exercises a mixed 3-rule batch through `apply_l2` with deep-copy purity assertion; (6) `test_compound_or_condition_preserved` verifies the as-written `%B=="b"  or  %B=="g"` (double space) is preserved verbatim in both the formula and the `Modification.condition` field; (7) `test_whitespace_normalized_condition_match` confirms a single-space rule condition still matches against the double-space fixture and that the emitted condition is the fixture's as-written form; (8) `test_lookup_table_list_raises` covers `var="G"`; (9)–(11) `test_missing_concept_key_raises` / `test_missing_var_raises` / `test_missing_condition_raises` all assert the `KeyError` message names the missing entry; (12)–(13) `test_empty_new_raises` and `test_missing_condition_field_raises` cover invalid rule shapes; (14) `test_caller_dict_unchanged_after_apply` snapshots `json.dumps(..., sort_keys=True)` pre/post `apply_l2`; (15) `test_only_targeted_fragment_changes` verifies bytewise preservation of every non-targeted fragment via `re.findall(r'"[^"]*"', ...)` before/after; (16) `test_replace_fragment_directly` exercises the private worker. The plan's "≥15 new tests" gate is exceeded.
- **Narrowed the existing stub tests in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py).** `_STUB_TYPES` now reads `[t for t in ModificationType if TYPE_TO_LAYER[t] in (Layer.TEMPLATE, Layer.PARAM_DEFINITION)]` (3 cases: `omission`, `reorder`, `new_param`), down from Sprint 07's 6 cases. `test_deep_copy_purity_on_notimplemented`'s rule changed from `{"type": "paraphrase"}` against `apply_l2` (now a live mutator) to `{"type": "omission"}` against `apply_l3` (still a stub). All other tests in the file are untouched.

**Key results:**
- **`pytest tests -q` → 78 passed in 0.12s, zero failures, zero skips.** Baseline was 63 (Sprint 07). Net delta: −3 (the three L2 stub cases narrowed out of `test_each_stub_raises_notimplemented_with_type_code`) + 18 (new `test_layer_l2.py` cases — 3 parametrised happy-path + 15 specific cases) = +15, landing at 78. The sprint plan's projected "75 passed" target was a lower bound (it modelled exactly 15 new tests); 18 ≥ 15 satisfies the binding gate.
- **Dispatcher audit ok: 9 live, 3 still stubs.** Smoke check verified that every `PARAM_VALUE` and `TEXT_VARIABLE` entry in `_DISPATCH` resolves to a function whose `__name__` starts with `apply_`, and every other entry still starts with `_stub_`. The 12-entry total and the `set(_DISPATCH) == set(ModificationType)` invariants are unchanged.
- **`from synthetic.mutator import _stub_paraphrase` correctly raises `ImportError`** — the three obsolete L2 stub function definitions are physically gone.
- **End-to-end smoke ok.** A `apply_l2(stage, "OEB020$", [{"type":"paraphrase","var":"K","condition":'%B=="a"',"new":"estandar"}])` call mutates only the targeted fragment inside the returned `out` dict; the caller's input is byte-identical under `json.dumps(sort_keys=True)` pre/post; the emitted `Modification` carries `var="K"`, `condition='%B=="a"'`, `original="normal"`, `new="estandar"`, `status="applied"`, `layer is Layer.TEXT_VARIABLE`.

**Decisions made:**
- **Whitespace normalisation is matcher-only, never writer.** `_norm` collapses runs of whitespace before condition equality comparison so a rule's `'%B=="b" or %B=="g"'` (single space) matches the catalog's `'%B=="b"  or  %B=="g"'` (double space). The writer preserves the catalog's as-written `cond` group verbatim — both in the rewritten formula and in the emitted `Modification.condition`. This means the formula stays byte-equivalent to the original in every region the rule didn't target; downstream consumers see what's actually in the formula, not the rule-supplied alias. Verified by `test_compound_or_condition_preserved` and `test_whitespace_normalized_condition_match`.
- **`$`-prefix tolerance lives at the L2 rule boundary, not in the data.** The stage-3 JSON keys are bare (`K`, `I`, `N`); the `RESEARCH_PROPOSAL.md §6.1` worked example shows `"var": "$I"` because the catalog's authors think in reference-syntax (`$K`, `$I`). The worker strips a single leading `$` if present; `Modification.var` is emitted in the bare form. Verified by `test_var_prefix_stripped`.
- **Pure lookup-table list entries fail loudly with `ValueError`, not `status="skipped"`.** A rule targeting `var="G"` with a `condition` field has no fragment to address — `G` is `['"Diurno"', '"Nocturno"', ...]` with no `* (` segment in any element. The variant catalog (Phase C) is human-curated, so this is a catalog-authoring error to surface at apply-time, not a runtime edge case to absorb. Phase B5's composition-rules layer will gate this at catalog-validation time. An `index`-addressed rule shape (`{"var": "G", "index": 0, "new": "..."}`) is **explicitly deferred** to keep B2's rule schema uniform with `(var, condition)`. Verified by `test_lookup_table_list_raises`.
- **Compound `or` conditions are opaque to the worker.** The condition is treated as a literal string handle for matching; the worker does not parse `%B=="b" or %B=="g"` into clauses. If a future variant catalog wants to mutate only one half of the disjunction, that's a different rule shape — explicitly deferred. The whole parenthesised expression is the addressing key. Verified by `test_compound_or_condition_preserved`.
- **`_replace_fragment` worker stays semantic-blind, same as `_replace_value`.** No Spanish reference data — no paraphrase dictionaries, no expansion templates, no compression heuristics. The rule carries `new` as a literal string; the mutator just performs the substitution. Per-type semantics belong in Phase C (`llm_proposer.py` + `prompts/paraphrase.txt` / `expansion.txt` / `compression.txt`) and Phase E (reviewer harness). The wrappers exist purely to set the `Modification.type` enum so downstream slice analysis can read the type code.
- **Outer-level `copy.deepcopy(stage_json)` stays inside `_apply_rules`, not the worker.** Same Sprint 07 contract: worker-level deep-copy would balloon costs on stacked rules (Phase B5 composition). The worker mutates its received `out` dict in place — legitimate because that dict is already a deep copy at the orchestrator boundary. Caller purity is verified by `test_caller_dict_unchanged_after_apply`.

**Problems encountered:**
- *One `KeyError` message assertion needed adjustment.* The initial `test_missing_condition_raises` used `str(excinfo.value)` to grep for `"'K'"`, but Python's `KeyError.__str__` wraps the message in `repr()` so the inner single quotes become escaped (`\\'K\\'`). Switched to `excinfo.value.args[0]` to inspect the raw message string before repr-wrapping. Same assertion convention `pytest.raises(KeyError, match="...")` is used elsewhere in the file where the substring doesn't include quotes.
- *No other issues.* The work landed in one read/edit cycle per file; the regex shape was confirmed by tracing the spec's `r'"(?P<frag>[^"]*)"\s*\*\s*\(\s*(?P<cond>[^)]*)\s*\)'` regex through each of the fixture's K/I/N/P shapes before writing tests.

**What changed in the plan as a result:**
- B2 closes. The protocol backlog's [`§5 Phase B B2`](RESEARCH_PROTOCOL.md) entry is now done.
- Next backlog item: **B3 — `src/synthetic/layer_l3.py` (template mutators: `omission`, `reorder`).** The wiring pattern (import block + `_DISPATCH` swap + obsolete stub deletion) generalises. The L3 rule schema operates on `resumen` / `texto` string templates and addresses by `field` + some structural index (sentence boundary, token span, paragraph). After B3 lands, `_STUB_TYPES` shrinks to `[NEW_PARAM]`; after B4 it becomes `[]` and the parametrised stub test gets deleted entirely.

**CLAUDE_SYNTHETIC.md updated:** `yes` — flipped ❌ → ✅ for `src/synthetic/layer_l2.py` in the "New Files in This Branch" block with the standard Sprint-08 annotation; prepended an "After Sprint 08 — …" entry to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_09.md` for B3 — fan the promotion pattern across `layer_l3.py` for the two template types (`omission`, `reorder`). Template mutations operate on the `resumen` / `texto` string templates at stage-4 (post-variable-substitution) — the worker's "find target, capture original, rewrite" mechanic still applies, but the addressing scheme is different (likely `field` + structural index, not `var` + condition).

---

### Sprint 07 — Phase B Task B1: L1 `param_value` mutator bodies (`layer_l1.py`)
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_07.md`](sprints/SPRINT_07.md)
**Tasks from backlog:** B1 — promote the 6 L1 `param_value` `NotImplementedError`-raising stubs in [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) to real bodies in a new [`src/synthetic/layer_l1.py`](../../src/synthetic/layer_l1.py) module.

**What was done:**
- **Created [`src/synthetic/layer_l1.py`](../../src/synthetic/layer_l1.py).** One shared private worker `_replace_value(stage_json, concept_key, rule, mod_type)` plus six thin public wrappers `apply_synonym_label`, `apply_num_to_text`, `apply_unit_conversion`, `apply_unit_expansion`, `apply_abbrev_expansion`, `apply_code_expansion`. The worker resolves `(concept_key, rule["param"], rule["value"])` against the stage JSON, captures the live `value_entry["value"]` as `original`, overwrites it with `rule["new"]`, and emits exactly one `Modification(layer=PARAM_VALUE, type=<wrapper's mod_type>, param, value, original, new, status="applied")`. The six wrappers exist purely to set the per-type `mod_type` enum on the emitted record — the mechanics are identical; the semantics live in the type code, exactly as the sprint plan's "six wrappers, one worker" design note prescribes.
- **Wired the six L1 mutators into [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH`.** Added the import block under the existing `from .taxonomy import …`, deleted the six obsolete `_stub_synonym_label` / `_stub_num_to_text` / `_stub_unit_conversion` / `_stub_unit_expansion` / `_stub_abbrev_expansion` / `_stub_code_expansion` function definitions, and swapped the six matching `_DISPATCH` entries to the new `apply_*` wrappers. The other 6 stubs (`_stub_paraphrase`, `_stub_expansion`, `_stub_compression`, `_stub_omission`, `_stub_reorder`, `_stub_new_param`) remain in place. Updated the module docstring to reflect that L1 is live (kept the L2/L3/PD-stub claim accurate). `_apply_rules`, `_resolve_type`, `_gate_layer`, `apply_l1`/`l2`/`l3`/`apply_new_param` are untouched.
- **Added [`tests/synthetic/test_layer_l1.py`](../../tests/synthetic/test_layer_l1.py) — 15 contract test cases.** An inline `oeb020_stage2` fixture with five axes (`A: Nº TUBOS`, `B: TIPO DE TERRENO`, `C: DIÁMETRO`, `D: MATERIAL`, `E: CALIDAD HORMIGÓN`) gives every L1 flavour a credible target. Coverage: (1) `test_happy_path_per_type` parametrised over the 6 wrappers; (2) `test_apply_l1_orchestrator_threads_rules` exercises a mixed-type 3-rule batch through `apply_l1`; (3) `test_modification_original_sourced_from_stage_json` enforces the rule-`original`-is-informational / log-`original`-is-authoritative asymmetry by passing `"WRONG"` and asserting the log carries `"Normal"`; (4)–(6) `test_missing_concept_key_raises` / `test_missing_param_raises` / `test_missing_value_label_raises` all check that the `KeyError` messages name the missing entry; (7)–(8) `test_empty_new_raises` and `test_missing_new_raises` cover both invalid `new` shapes; (9) `test_caller_dict_unchanged_after_apply` snapshots `json.dumps(..., sort_keys=True)` pre/post `apply_l1` to verify the outer `_apply_rules` deep-copy preserves caller purity; (10) `test_replace_value_directly` exercises the private worker. The "at least 13" gate is exceeded; the extras are the explicit `missing_new` case and the direct-worker test.
- **Narrowed the existing stub tests in [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py).** `test_each_stub_raises_notimplemented_with_type_code` is now parametrised over `_STUB_TYPES = [t for t in ModificationType if TYPE_TO_LAYER[t] is not Layer.PARAM_VALUE]` (6 cases — paraphrase, expansion, compression, omission, reorder, new_param) instead of all 12. `test_deep_copy_purity_on_notimplemented`'s rule changed from `{"type": "synonym_label"}` (now a real L1 mutator) to `{"type": "paraphrase"}` (still a stub); the assertion entry-point flipped from `apply_l1` to `apply_l2` to match the new rule's layer. All other tests in the file are untouched.

**Key results:**
- **`pytest tests -q` → 63 passed in 0.12s, zero failures, zero skips.** Baseline was 54 (Sprints 01–05). Net delta: −6 (the 6 L1 stub cases narrowed out of `test_each_stub_raises_notimplemented_with_type_code`) + 15 (new `test_layer_l1.py` cases) = +9, landing at 63. The sprint plan's "≥67" target was internally inconsistent with the same plan's stub-narrowing instruction; the spirit of the gate — "≥13 new L1 contract cases, all green, no skips, no regressions in the surviving baseline" — is satisfied (15 ≥ 13; 48 surviving baseline cases all pass).
- **Dispatcher audit ok: 6 L1 live, 6 still stubs.** Smoke check verified that every `PARAM_VALUE` entry in `_DISPATCH` resolves to a function whose `__name__` starts with `apply_`, and every other entry still starts with `_stub_`. The 12-entry total and the `set(_DISPATCH) == set(ModificationType)` invariants are unchanged.
- **`from synthetic.mutator import _stub_synonym_label` correctly raises `ImportError`** — the six obsolete stub function definitions are physically gone.
- **End-to-end smoke ok.** A `apply_l1(stage, "OEB020$", [{"type":"synonym_label","param":"B","value":"a","new":"Estandar"}])` call mutates only the targeted value entry inside the returned `out` dict, the caller's input is byte-identical under `json.dumps(sort_keys=True)` pre/post, and the emitted `Modification` carries `original="Normal", new="Estandar", status="applied"`.

**Decisions made:**
- **Stale `rule["original"]` is silently ignored at apply-time.** The mutator never reads `rule.get("original")`; it always sources `Modification.original` from the live `value_entry["value"]` it overwrites. This intentionally pushes the "catalog drift" detection responsibility to Phase E (reviewer harness flags variant-catalog entries whose `original` no longer matches the live stage value). `test_modification_original_sourced_from_stage_json` is the load-bearing contract test for this asymmetry — it pins the worker's behaviour even when a future Phase-E change might want to surface the drift differently.
- **Outer-level `copy.deepcopy(stage_json)` stays inside `_apply_rules`, not the worker.** Worker-level deep-copy would balloon costs on stacked rules (Phase B5 composition). The worker mutates its received `out` dict in place — legitimate because that dict is already a deep copy at the orchestrator boundary. Caller purity is verified by `test_caller_dict_unchanged_after_apply`.
- **No Spanish reference data inside `layer_l1.py`.** No number-word tables, unit-conversion tables, acronym dictionaries, or code lookups. The rule carries `new` as a literal string; the mutator is semantic-blind. Phase C (`llm_proposer.py` + `prompts/`) is where per-type semantics will be enforced via prompt design; Phase E (review.py) is where they'll be policed. The applier is intentionally a deterministic value-replacement engine.
- **No `_replace_value` re-export from `synthetic.layer_l1`'s public surface.** It's a private helper (underscore-prefixed), but the test suite imports it directly to exercise the worker without going through a wrapper. Treated as a deliberate "tests are an internal consumer" exception, not a public-API leak.
- **Module docstring of `mutator.py` updated to reflect L1 promotion.** Two-paragraph swap: the "all 12 stubs" line replaced by "6 L1 live, 6 still stubs". Keeps the boundary-stability claim. The next sprint that lands L2 / L3 / PD will narrow this further.

**Problems encountered:**
- *Sprint plan's expected pytest count (67) is internally inconsistent.* The plan says "Test count for that file: 12 baseline → 12 (`test_each_stub_raises_notimplemented_with_type_code` shrinks from 12 parametrised cases to 6)" — i.e. a -6 delta on the file — but also claims "67 = 54 baseline + 13 new". Those two statements can't both be true. Actual count is 54 - 6 + 15 = 63, which satisfies the binding gate (≥13 new L1 cases, all green, no skips, no regressions) but undercuts the headline number. Logging here so the next sprint's plan-review catches this earlier.
- *No other issues.* The work landed in one read/edit cycle per file with no rework.

**What changed in the plan as a result:**
- B1 closes. The protocol backlog's [`§5 Phase B B1`](RESEARCH_PROTOCOL.md) entry is now done.
- Next backlog item: **B2 — `src/synthetic/layer_l2.py` (text-variable mutators: `paraphrase`, `expansion`, `compression`).** The dispatcher wiring pattern (import block + `_DISPATCH` swap + obsolete stub deletion) generalises directly to L2, and the test-narrowing pattern in `test_mutator.py` is set up to shrink `_STUB_TYPES` further (next iteration: drop L2 types, leaving L3 + PD = 3 stubs). After B2 + B3 land, `_STUB_TYPES` shrinks to `[NEW_PARAM]`; after B4 it becomes `[]` and the parametrised stub test is removed entirely.

**CLAUDE_SYNTHETIC.md updated:** `yes` — flipped ❌ → ✅ for `src/synthetic/layer_l1.py` in the "New Files in This Branch" block with the standard Sprint-07 annotation; prepended an "After Sprint 07 — …" entry to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_08.md` for B2 — fan the Sprint 07 promotion pattern across `layer_l2.py` for the three text-variable types (`paraphrase`, `expansion`, `compression`). The L2 rule schema needs `var` + `condition` keys in addition to / instead of L1's `param` + `value` — design the worker accordingly.

---

### Sprint 6.5 — Cleanup fixes from Sprint 06 findings: s07 sorted iteration + Generate_OEB resumen writer cell
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_065.md`](sprints/SPRINT_065.md)
**Report:** [`sprints/SPRINT_065_REPORT.md`](sprints/SPRINT_065_REPORT.md)
**Tasks from backlog:** Two patch fixes for the bugs Sprint 06 surfaced. Not in the Phase A or Phase B backlogs — tracked as a patch sprint that lands before Sprint 07's Phase B start.

**What was done:**
- **Coupling check (pre-execution).** Grepped `bc3cat-retrieval` for `OEB_resumen.pkl`: zero hits. The sibling repo reads only `OEB_resumen.json` (in `src/cross_encoder.ipynb` and `src/hybrid.ipynb`). Confirmed `OEB_resumen.pkl` is dataset-internal — Fix 2 carries no cross-repo coupling risk.
- **Fix 1 — s07 sorted iteration.** [`src/s07_Filter_duplicates.ipynb`](../../src/s07_Filter_duplicates.ipynb) cell 8 (id `8d1aea31`), source line 86 of cell: `for key in either_duplicate_keys:` → `for key in sorted(either_duplicate_keys):`. One-token change inside the cell's source array. Diff stat: `+1/−1`. Patched via the `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` → `Path.write_bytes(text.encode("utf-8") + b"\n")` cycle (LF preserved on Windows).
- **Fix 2 — Generate_OEB `OEB_resumen.pkl` writer cell.** [`src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb): inserted a new code cell at index 8 (id `6060ae5d-136a-4cd4-8e53-848cec21af70`, freshly generated UUID4), mirroring cell 3's filter-and-pickle pattern but for resumen. Writes to `config.PROCESSED_DIR / "OEB_resumen.pkl"` — matches the read path of the existing cell at the next index. Cell count went 10 → 11; the JSON-producer cell shifted from index 8 to index 9 with identical content (id `b9f644bb` preserved). Cell 3 left untouched (Sprint 04's cwd-relative decision preserved; asymmetry is intentional).
- **Fix 3 — differ row.** [`scripts/sprint06_validate_e2e.py`](../../scripts/sprint06_validate_e2e.py) `PICKLE_DIFFS` extended with `("processed/OEB_resumen.pkl", NEW_ROOT / "processed" / "OEB_resumen.pkl")` plus a one-line marker comment. Total rows 24 → 25.
- **Validation rerun.** Cleared `data_validation/{intermediate,processed,executed}/*` and reran the full pipeline (s01 → Generate_OEB) inside `bc3cat-sprint06`. Wall-clock: ~3m30s (consistent with Sprint 06). Generate_OEB now executes all 11 cells with zero errors. Differ run captured at [`sprints/SPRINT_065_REPORT.md`](sprints/SPRINT_065_REPORT.md).

**Key results:**
- **Differ: 25 / 25 PASS, exit 0.** All Sprint 06 rows still PASS (no regressions from Fix 1). The new `OEB_resumen.pkl` row PASSES with `47,514 docs, text+metadata identical (id_ ignored)`.
- **In-repo `data/processed/OEB_resumen.pkl` (35,036,231 bytes, 47,514 LlamaIndex Documents) — content-identical to the file produced by the new cell.** This proves the historical process that produced the in-repo file used exactly the same filter rule the new cell implements (filter `OBRA CIVIL_resumen.pkl` by `item_key.startswith("OEB")`). Sprint 6.5's new cell is the canonical writer going forward; the in-repo reference is preserved at the Jan-12 ground truth (no overwrite).
- **Fix 1 determinism gate: PASS.** Reran s07 a second time (`papermill s07_Filter_duplicates.ipynb`), saved each run's `_either_duplicate.json` to `/tmp/`, byte-diffed. Both runs produce MD5 `0e1d872bbaf5bf81bc0d3011c1d254e4` — byte-identical across runs. The Sprint 06 nondeterminism is gone.
- The Sprint 06 differ row for `_either_duplicate.json` continues to report "bytes differ (set-iteration order)" against the in-repo Jan-12 reference. This is correct — the in-repo file predates the sort fix. Content remains identical (15,294 entries, 0 value mismatches). Per the Sprint 6.5 plan, the in-repo file stays frozen as the ground-truth Jan-12 reference; the differ's JSON content-diff bucket handles the relabeling.

**Decisions made:**
- **In-repo `data/processed/OEB_resumen.pkl` not overwritten.** Sprint 06 mtime check confirmed `data/` was untouched (still Jan 12, 2026). Sprint 6.5's gate is content-equivalence to that reference, not replacement of it. Even though the byte content matches and an overwrite would be safe, the policy of "`data/` is frozen ground truth" is preserved.
- **In-repo `data/intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json` not regenerated.** Same reasoning — the differ's JSON content-diff handles the byte mismatch honestly. Regenerating the in-repo file would just shift the diff bucket from "JSON content-diff" to "byte-diff" without changing the validation signal.
- **Cell 3 cwd-relative path preserved.** Sprint 04's deliberate decision (matches cell 4's cwd-relative load). The new cell at index 8 writes to `config.PROCESSED_DIR` to match cell 9's read path. The asymmetry inside Generate_OEB (cell 3 cwd vs cell 8 `config.PROCESSED_DIR` writes) is intentional minimum-blast-radius design. Future cleanup candidate if Generate_OEB ever gets a comprehensive refactor — not Sprint 6.5's job.
- **Sprint named "6.5" not "07".** It's a patch sprint for Sprint 06 findings; Sprint 07 stays reserved for Phase B Task B1. The decimal naming makes the dependency obvious: 6.5 polishes Sprint 06's deliverables, not its own backlog item.
- **No pytest gate added.** Sprint 6.5 is a notebook + script + docs change; the differ rerun is the validation. The 54-baseline pytest count from Sprint 05 stays unchanged.
- **Run script fixed in-flight.** `/tmp/sprint06_run.sh` had `2>&1 | tail -3` which masked papermill exit codes (a per-stage failure couldn't bail the loop). Rewrote as `/tmp/sprint065_run.sh` with `PIPESTATUS[0]` capture to surface per-stage failures properly. Cosmetic improvement; would have caught the Sprint 06 Generate_OEB error explicitly if it had been there.

**Problems encountered:**
- *Container marked "(unhealthy)":* `bc3cat-sprint06` Docker health check reports unhealthy (probably from missing Jupyter HTTP endpoint since we never started the server — the container just runs `sleep 3600` loop). Cosmetic; `docker exec` still works fine. No action.

**CLAUDE_SYNTHETIC.md updated:** yes (Sprint History entry prepended; "Existing files extended" updated for s07 + Generate_OEB rows).

**Next step:** **Sprint 07 — Phase B Task B1 (`layer_l1.py`).** With Sprint 6.5 closing the two pre-existing bugs, the foundation is fully verified-clean. Sprint 07 promotes the Sprint 01 `_DISPATCH` stubs for the 6 L1 `param_value` mutators (`synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`) to real bodies in [`src/synthetic/layer_l1.py`](../../src/synthetic/layer_l1.py). Add a contract-test suite covering each of the 6 types on a representative concept (`OEB020$` is the canonical example). Sprint 07's gate: 54 baseline pytest count + new B1 contract tests.

---

### Sprint 06 — End-to-end validation: rerun s01 → Generate_OEB in Docker; Sprints 02–05 runtime-verified
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_06.md`](sprints/SPRINT_06.md)
**Report:** [`sprints/SPRINT_06_REPORT.md`](sprints/SPRINT_06_REPORT.md)
**Tasks from backlog:** Phase A closing milestone — the runtime check Sprints 02–05 deferred under the "static-check-only" hedge. **With this sprint, Phase A closes.**

**What was done:**
- **Task 1 — Setup.** Created [`.gitignore`](../../.gitignore) (new file, single entry `data_validation/`). Built `data_validation/{raw,intermediate,processed,executed}/` and seeded `data_validation/raw/BPA_2024_v2_OEB_mod.txt` from `data/raw/`. (Note: the seed was originally `_OEB_mod_utf8.txt`; corrected to `_OEB_mod.txt` after the first s01 run revealed that s01 cell 1 reads the pre-conversion file and writes `_utf8.txt` itself — a richer test that also validates the ISO-8859-1 → UTF-8 step. The plan's wording "seed `_utf8.txt`" was a draft-time mistake corrected mid-execution.)
- **Docker.** The repo's existing `jupyter-pytorch` container failed to start because Docker Compose maps port 8050 (Dash) and Windows reserves that port in the 8001–8100 HyperV range. Worked around by spinning up a standalone container (`bc3cat-sprint06`) via `docker run -d` with the same image, network, and volume mount but no port bindings — Dash isn't needed for headless papermill execution. Installed `papermill 2.7.0` in the container.
- **Task 2 — s01 smoke gate.** First run errored on `intermediate/` not existing — fixed by `mkdir -p data_validation/{intermediate,processed}`. Second run: s01 wrote `data_validation/raw/BPA_2024_v2_OEB_mod_utf8.txt` (byte-identical to `data/raw/BPA_2024_v2_OEB_mod_utf8.txt`) and `data_validation/intermediate/BPA_2024_v2_OEB_mod_utf8.json` (byte-identical to in-repo, 18,478,991 bytes). **Env-var override `BC3CAT_DATA_ROOT=/work/data_validation` works as designed.**
- **Tasks 3–4 — full pipeline run.** Ran s02 → s07 → s08 → `Generate_OEB_dataset` sequentially via papermill inside the container. Per-notebook wall-clock: s02 = 2s, s03 = 14s, s04 = 1m39s, s05 = 31s, s06 = 6s, s07 = 27s, s08 = 26s, `Generate_OEB_dataset` = 14s (errored at cell 8 — see below). **Total: 3m44s** (much faster than the 25–50min plan budget — fast NVMe). Aggregate output: 1.8 GB intermediate + 176 MB processed pickles + `OEB_texto.pkl` (53 MB) in `/work/src/`. The in-repo `data/` mtimes stayed at 2026-01-12 throughout — isolation perfect.
- **Task 5 — differ.** Wrote [`scripts/sprint06_validate_e2e.py`](../../scripts/sprint06_validate_e2e.py) (new file, ~140 lines). 20 byte-diff rows, 1 JSON content-diff row, 3 pickle content-diff rows = **24 total**. The JSON-content bucket was added mid-sprint after the first differ run flagged `_either_duplicate.json` as a byte mismatch (see decision below). Pickle comparison sorts by `item_key` and ignores LlamaIndex's auto-`id_`.
- **Task 6 — differ run.** Final result: **24 / 24 PASS, exit code 0.** Report captured at [`sprints/SPRINT_06_REPORT.md`](sprints/SPRINT_06_REPORT.md). Highlights:
  - `OBRA CIVIL_stage4.json` (786 MB) — **byte-identical**.
  - `OBRA CIVIL_stage7.json` (225 MB) — byte-identical.
  - `OBRA CIVIL_texto.pkl` (110 MB, 111,644 LlamaIndex Documents) — text + metadata identical.
  - `OBRA CIVIL_resumen.pkl` (75 MB, 111,644 Documents) — text + metadata identical.
  - `OEB_texto.pkl` (53 MB, 47,514 Documents) — text + metadata identical.

**Key results:**
- All 24 validation rows pass. **Sprints 02–05 are runtime-verified behavior-preserving.** Phase A closes.
- Two findings surfaced that are **pre-existing**, not refactor regressions:
  1. **s07 set-iteration nondeterminism in `_either_duplicate.json`.** The producer ([`src/s07_Filter_duplicates.ipynb`](../../src/s07_Filter_duplicates.ipynb) cell 8) builds `either_duplicate_keys = set()`, populates it via `.add(key)`, then iterates the set to write the output JSON. Python set iteration order is randomized per process via PYTHONHASHSEED, so the output dict's key order differs run-to-run. Content (15,294 keys, all values) is byte-identical per-entry. Sprint 06 reclassifies the row to JSON content-diff and flags as a low-priority future-cleanup candidate (one-line fix: `sorted(either_duplicate_keys)`).
  2. **`Generate_OEB_dataset.ipynb` cell 8 fails reading `OEB_resumen.pkl` that no cell writes.** Cell 4 (formerly numbered cell 3 in earlier listings — papermill counts the markdown title) writes only `OEB_texto.pkl`. The in-repo `data/processed/OEB_resumen.pkl` (35 MB) was generated outside this notebook (presumably by `bc3cat-retrieval`, since OEB_*.parquet artifacts are also produced there). Sprint 06's gate doesn't include this row — flagged in the Sprint 06 plan's "pre-existing notebook quirks" section. Same low-priority future-cleanup status: add a missing cell that writes `OEB_resumen.pkl` symmetric with cell 4 → `OEB_texto.pkl`.

**Decisions made:**
- **Spun up a standalone `bc3cat-sprint06` container instead of editing `docker-compose.yml`.** Port 8050 conflict is host-environment-specific (Windows HyperV port reservation); modifying the compose file would be a cosmetic config change that doesn't belong in a validation sprint. The standalone container has the same image + volume + network, just no port bindings.
- **Added a JSON content-diff bucket to the differ after first-run revealed s07 nondeterminism.** The alternative — accepting `_either_duplicate.json` as a FAIL — would have buried a genuine positive signal (content equivalence) under a false negative. Loading + dict-comparing JSON is cheap; the row is content-identical (set-iteration order is the only difference). The differ now reports `bytes differ (set-iteration order)` honestly while reporting PASS on content.
- **Did NOT fix either pre-existing notebook bug in this sprint.** Both are quality-of-life cleanups that change behavior (notebook outputs would shift). Sprint 06 is a validation sprint; fixing the notebooks during validation would defeat its purpose. Logged as future-cleanup candidates.
- **Container kept around post-validation** for any follow-up. To clean up: `docker rm -f bc3cat-sprint06`. The `data_validation/` tree is gitignored and can be deleted with `rm -rf data_validation/` at any time.
- **Plan deviation: pipeline wall-clock 3m44s vs plan's 25–50min budget.** Plan over-estimated because s03's 387 MB Cartesian expansion is mostly `itertools.product` (cheap) and s04's 786 MB JSON write is sequential dict serialization (fast on NVMe). No risk to gate; clock budget was a hedge, not a constraint.

**Problems encountered:**
- *Docker container start failed:* port 8050 blocked by Windows port reservation (8001–8100 range in `netsh interface ipv4 show excludedportrange`). Worked around with standalone `docker run` — no port mappings needed for headless papermill.
- *Initial seed file wrong:* seeded `_utf8.txt` instead of `_OEB_mod.txt`. s01 cell 1 reads `_OEB_mod.txt` (ISO-8859-1) and produces `_utf8.txt`. Fixed; this turned out to enable a richer test (the encoding-conversion step is now validated too — `raw/BPA_2024_v2_OEB_mod_utf8.txt` produced under `data_validation/raw/` is byte-identical to `data/raw/`).
- *`intermediate/` dir not auto-created by notebooks:* s01 writes to `intermediate/...` (cwd-relative) via `os.chdir(config.DATA_ROOT)` but doesn't `mkdir -p`. Fixed by pre-creating `data_validation/{intermediate,processed}/`. Pre-existing notebook behavior; out of Sprint 06 scope to fix.
- *`Generate_OEB_dataset` cell 8 failed mid-run:* as analyzed above. Did not block Sprint 06's gate because cell 4 (which writes `OEB_texto.pkl`) ran first and produced the validatable artifact.

**CLAUDE_SYNTHETIC.md updated:** yes (Sprint History entry prepended; "Existing files extended" block updated to flag each Sprint 02–05 row as runtime-verified).

**Next step:** **Phase B — Task B1 (`layer_l1.py`)**. Now that Phase A is verified-closed, the next unit of work is writing real bodies for the 6 L1 `param_value` mutators: `synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`. The Sprint 01 stubs are already wired into the `_DISPATCH` table in [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py); B1 promotes them in place. Per the protocol: `apply_l1` operates on stage-2 JSON, mutates `parameters[axis]["values"]` arrays for one concept at a time, emits a list of `Modification` records, and is pure (deepcopies the input). Sprint 07 should cover B1 in full plus a contract-test suite that exercises each of the 6 types on a representative concept (`OEB020$` is the typical example).

Two low-priority cleanup candidates surfaced by Sprint 06 are NOT Phase-B blockers but worth a backlog note:
- s07 `_either_duplicate.json` set-iteration → `sorted(...)` (1-line fix in [`src/s07_Filter_duplicates.ipynb`](../../src/s07_Filter_duplicates.ipynb) cell 8)
- `Generate_OEB_dataset.ipynb` add a cell-4-symmetric cell that writes `OEB_resumen.pkl`

Both are out-of-band cleanups, not Phase-B prerequisites.

---

### Sprint 05 — Import-shape cleanup: relative imports in `src/utils/*.py` + `Generate_OEB_dataset` bootstrap retirement
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_05.md`](sprints/SPRINT_05.md)
**Tasks from backlog:** Post-A4 follow-up identified in the Sprint 04 retro. Not in the original Phase A backlog — task A4 closed with Sprint 04. Tracked as a refinement to the file map.

**What was done:**
- Switched the 5 `from src.utils.X` absolute self-imports inside `src/utils/` to relative form across three files: [`src/utils/data_utils.py`](../../src/utils/data_utils.py) line 6 (`.custom_types`), [`src/utils/evaluation.py`](../../src/utils/evaluation.py) line 4 (`.custom_types`), and [`src/utils/index_classes.py`](../../src/utils/index_classes.py) lines 10–12 (`.text_processing`, `.custom_types`, `.config`). Diff stat exactly `+1/−1` × (1, 1, 3) = `+5/−5` across the three modules. No other lines touched.
- Retired the [`src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb) cell 2 bootstrap in a single `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle: rewrote `from src.utils.data_utils import load_documents` to `from utils.data_utils import load_documents` (symmetric with the existing `from utils import config` shape — anchored at the Jupyter kernel cwd of `src/`, no `REPO_ROOT` needed), deleted the `project_root = config.REPO_ROOT` + `sys.path.append(str(project_root))` block, and removed the now-orphaned blank separator. Cell 2 ends as a single contiguous import block (9 lines). Diff scope confined to cell 2 only — no other cells, no metadata churn. **The path refactor's final `sys.path.append(...)` shim retires with this sprint.**
- Added the regression-guard test [`tests/utils/test_utils_no_absolute_self_imports.py`](../../tests/utils/test_utils_no_absolute_self_imports.py): regex-scans `data_utils.py`, `evaluation.py`, `index_classes.py` for `^\s*(from|import)\s+src\.utils\b` and asserts zero hits per module. 3 parametrised cases. Catches both `from src.utils.X import Y` and `import src.utils.X` shapes.

**Key results:**
- `pytest tests -q` → **54 passed in 0.17s** (Sprint 04's 51 + 3 new `from src.utils.X` guard cases). No regressions; no skips.
- Both smoke checks pass: `py_compile` on the three edited modules compiles cleanly (the spec's runtime-import smoke check substitutes to `py_compile` because `custom_types.py` imports `llama_index` + `scipy` at module level — out of this host's static-check env, same gap Sprint 03/04 noted); `Generate_OEB` cell 2 invariants check passes (`sys.path.append`: absent, `from src.utils`: absent, `from utils.data_utils import load_documents`: present).
- `git diff --numstat` for the touched files: `src/utils/data_utils.py +1/−1`, `src/utils/evaluation.py +1/−1`, `src/utils/index_classes.py +3/−3`, `src/Generate_OEB_dataset.ipynb +1/−5` (the −5 vs the sprint plan's "roughly −4" is git accounting for the import swap as add+delete plus the four pure deletions — bootstrap-2 lines, blank-2 lines; semantically identical to the plan). `git status --short` end-of-sprint matches the plan's expected file list exactly.

**Decisions made:**
- **Relative imports inside `src/utils/` are caller-agnostic.** Python resolves `.custom_types` against the loaded package context regardless of whether the caller imports as `from src.utils.X` (namespace-package shape, via `REPO_ROOT` on `sys.path`) or `from utils.X` (kernel-cwd-anchored shape, via `src/` on `sys.path`). So the Sprint 05 cleanup does not break any hypothetical absolute-import caller that hasn't been migrated yet — it only removes the absolute self-imports *inside* the package.
- **`bc3cat-retrieval` mirror is a sibling-repo task, not a follow-up here.** The retrieval repo carries parallel filesystem copies of all five `from src.utils.X` lines plus one downstream consumer in `src/pipeline/param_extractor_rules.py`. The two repos share no files at the FS level, so Sprint 05's diff cannot break sibling runtime. Mirroring the cleanup over there is optional consistency work, tracked on the retrieval side.
- **`src/__init__.py` deliberately not added.** After Sprint 05 no in-repo caller needs `src` to be importable: the three `src/utils/*.py` modules use relative imports, the notebook uses `from utils.X`. Adding `src/__init__.py` would reintroduce the namespace-package dependency that this sprint specifically eliminates. (Sprint 04's "namespace-package shape" note remains accurate as a description of the *prior* import surface; it's no longer load-bearing.)
- **Unused imports (`os`, `Path`, `gc`) in `Generate_OEB_dataset.ipynb` cell 2 left in place.** Same Sprint 03/04 policy: cosmetic-only cleanups stay out of scope. `import sys` is removed naturally because the bootstrap that used it is gone — that's the only line in the import block the strict scope touched besides the swap. If a future sprint does an "unused-imports sweep" across all nine notebooks, this is a candidate site.
- **`index_classes.py` not importability-tested at runtime.** It transitively pulls `scipy`, `sklearn`, and `llama_index` — well past the lightweight static-check footprint Sprints 02–04 maintained. The new regression test (3 parametrised cases) covers it via source-text scan instead. First module to gate on if a future sprint promotes to runtime-import testing.
- **`.ipynb_checkpoints/` left untouched.** Stale `data_utils-checkpoint.py` / `evaluation-checkpoint.py` / `index_classes-checkpoint.py` inside `src/.ipynb_checkpoints/` and `src/utils/.ipynb_checkpoints/` still carry the old `from src.utils.X` shape; they're Jupyter auto-saves that regenerate on next save. Same policy as Sprints 02–04.

**Problems encountered:**
- The Task 6 importability smoke check (`python -c "from utils.data_utils import load_documents"`) raised `ModuleNotFoundError: No module named 'llama_index'` on this host. The failure was *inside* `custom_types.py` (line 5: `from llama_index.core import Document`), not at the Sprint 05–edited relative import — meaning the relative import resolved correctly and Python proceeded to load the rest of `custom_types.py` before hitting the missing dep. Substituted `py_compile` for the three edited modules as the static-check equivalent (per the same gate Sprints 02–04 used). No action; runtime imports are deferred to the end-to-end-validation sprint that exercises the Docker / `pandas` / `llama_index` env.
- The Windows atexit `cleanup_dead_symlinks` `PermissionError` after `pytest` exit is unchanged from Sprints 02–04 — cosmetic noise; `54 passed in 0.17s` prints cleanly before the traceback. No action.

**CLAUDE_SYNTHETIC.md updated:** yes (Sprint History entry prepended; `Existing files extended` block flags Sprint 05's changes to the three `src/utils/*.py` modules and notes the `Generate_OEB_dataset.ipynb` cell 2 bootstrap retirement).

**Next step:** **End-to-end-validation sprint.** Sprints 02–05 collectively constitute the full path refactor + import-shape cleanup; static checks have not exercised behaviour preservation against the in-repo data. The follow-up runs s01 → s07 → s08 → `Generate_OEB_dataset` against the existing `data/intermediate/{OBRA CIVIL,...}/` files inside a Docker / `pandas` / `pyarrow` / `llama_index` env and byte-diffs the produced `data/processed/OEB_*.parquet` / `*.pkl` against the in-repo originals. If the diffs are empty, Phase A closes and Phase B (mutator bodies — Tasks B1–B4) becomes the next unit of work.

---

### Sprint 04 — Path refactor: s08 + `Generate_OEB_dataset` notebook migration
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_04.md`](sprints/SPRINT_04.md)
**Tasks from backlog:** A4 part 3 (s08 + `Generate_OEB_dataset` notebook migration). With this sprint, **task A4 closes in full**.

**What was done:**
- Migrated [`src/s08_Llamaindex_Doc_Creation.ipynb`](../../src/s08_Llamaindex_Doc_Creation.ipynb) cell 2: added `from utils import config` and rewrote the three `Path('/work/data/...')` path literals inside `main(file)` to route through `config.stage_path(file, 7)` (the `_stage7.json` read) and `config.PROCESSED_DIR / f"{file}_{texto,resumen}.pkl"` (the two pickle writes). Diff scope: +4 / −3 in cell 2 only.
- Migrated [`src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb) cells 2, 3, 4, 8: **4 path-literal rewrites + 1 bootstrap retarget + 1 stale-comment deletion** in a single `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle. Cell 2: `from utils import config` added beside `from llama_index.core import Document`, the two-line stale `# Assuming … /work` comment block deleted, and `project_root = Path('/work')` rewritten to `project_root = config.REPO_ROOT`. **The `sys.path.append(str(project_root))` line and the `from src.utils.data_utils import load_documents` import stay intact** — both are load-bearing for the repo-rooted import chain. Cell 3: `'/work/data/processed/OBRA CIVIL_texto.pkl'` → `config.PROCESSED_DIR / "OBRA CIVIL_texto.pkl"`. Cell 4: `'/work/src/OEB_texto.pkl'` collapsed to a bare relative `"OEB_texto.pkl"` (symmetric with cell 3's save side, no `config.SRC_DIR` helper introduced). Cell 8: `'/work/data/processed/OEB_resumen.pkl'` → `config.PROCESSED_DIR / "OEB_resumen.pkl"`. Diff scope: +5 / −6 across the four cells, no metadata churn.
- Extended the regression-guard test [`tests/utils/test_notebooks_no_work_literal.py`](../../tests/utils/test_notebooks_no_work_literal.py): appended `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb` to the `NOTEBOOKS` list, and **widened the substring check** from `"/work/"` to bare `"/work"` so the `Path('/work')` bootstrap (no trailing slash) is also caught. Module docstring updated to match.

**Key results:**
- `pytest tests -q` → **51 passed in 0.08s** (49 from Sprint 03 + 2 new parametrised notebook-guard cases for s08 and Generate_OEB). No regressions.
- Both smoke checks pass: all 9 pipeline notebooks (s01–s08 + `Generate_OEB_dataset`) parse via `json.load`, and `source-cell /work hits across s01-s08 + Generate_OEB: 0`.
- The widened literal check (`"/work/"` → `"/work"`) stays green on s01–s07 — confirmed by the parametrised test: 9 passed. The Sprint 03 deletions of the s07 cells 3/8 bootstraps were the only bare-`/work` sites in those notebooks, so the tighter gate carries no false positives.
- `git status --short` matches the sprint's expected end-state: 2 modified notebooks (`src/s08_Llamaindex_Doc_Creation.ipynb`, `src/Generate_OEB_dataset.ipynb`), 1 modified test file (`tests/utils/test_notebooks_no_work_literal.py`), plus this log + `CLAUDE_SYNTHETIC.md` housekeeping and the new `docs/synthetic/sprints/SPRINT_04.md` itself. Nothing under `src/synthetic/`, `tests/synthetic/`, `data/`, `configs/`, or `src/utils/*.py` in the diff.

**Decisions made:**
- **Generate_OEB cell 2 bootstrap retargeted, not deleted.** The `sys.path.append(str(project_root))` line stays because `from src.utils.data_utils import load_documents` on the next line is a *repo-rooted* import — it requires `REPO_ROOT` (parent of `src/`) on `sys.path`, not `src/` itself. The bootstrap's purpose is unchanged; only its target literal swaps from `Path('/work')` to `config.REPO_ROOT`. **Cleaning up the import shape inside [`src/utils/data_utils.py`](../../src/utils/data_utils.py), [`src/utils/index_classes.py`](../../src/utils/index_classes.py), and [`src/utils/evaluation.py`](../../src/utils/evaluation.py) — swapping `from src.utils.X` to relative `from .X` so the bootstrap can finally retire — is a self-contained follow-up.** Doing it here would also force a cross-repo coupling check against `bc3cat-retrieval`, expanding the Sprint 04 blast radius unnecessarily. Tracked as a Sprint 05 (or "Sprint 04.5") candidate.
- **Cell 4 collapsed to a bare relative path, not promoted to a helper.** `'/work/src/OEB_texto.pkl'` → `"OEB_texto.pkl"`. Symmetric with cell 3's save side (`with open("OEB_texto.pkl", "wb") as f: pickle.dump(filtered_docs, f)`), which already saves relative to the notebook cwd of `src/`. Introducing a `config.SRC_DIR` helper for two callers in one notebook would be premature; the bare-relative form makes it obvious the file lives where cell 3 just wrote it.
- **Single `from utils import config` per notebook in the shared imports cell.** Cells 3, 4, 8 of `Generate_OEB_dataset.ipynb` inherit the import transitively through the notebook globals namespace populated by cell 2's execution. Sprinkling per-cell imports would clutter the diff without changing behaviour.
- **Regression-guard literal widened from `/work/` to `/work`.** Verified by hand that s01–s07 contain no bare-`/work` tokens after Sprint 03 — the deleted s07 cells 3/8 bootstraps (`Path('/work')`) were the only such occurrences. Sprint 04's `Generate_OEB_dataset.ipynb` cell 2 originally had the same `Path('/work')` shape (which the old `/work/` gate would have missed); the widened gate catches it. Net effect: one stricter regression-prevention rule, zero false positives.
- **LF line endings preserved.** Same recipe as Sprint 03: `Path.write_bytes(json_text.encode("utf-8") + b"\n")` bypasses Windows' text-mode CRLF translation. git's `core.autocrlf` produces the soft "LF will be replaced by CRLF" warning on both touched notebooks but the in-repo bytes are LF, matching the existing convention.

**Problems encountered:**
- The site-survey cell IDs in the sprint plan (`78375313`, `80529a1b`, `3348009c`, `a64e60f9`, `b9f644bb`) are 8-char prefixes; the actual `cell["id"]` values in the JSON are full UUIDs (e.g. `78375313-6bce-4626-bc8c-653fe1d5a8bb`). The first migration-script run tripped a strict equality assertion; relaxing to `cid.startswith(prefix)` resolved it on the second try. No notebook content was touched on the failed run (the assertion fired before any patching). Trivial; logged for future sprint authors writing similar helpers.
- Same Windows-temp-dir-cleanup `PermissionError` traceback at pytest shutdown observed in Sprints 02 + 03 still prints; 51 passed prints before the traceback. Unrelated to test outcomes.

**Changes to plan:**
- **Task A4 closes in full.** A4 part 3 (s08 + `Generate_OEB_dataset`) is the last sub-task; the path refactor across the main pipeline is complete.
- **New follow-up: import-shape cleanup of `src/utils/{data_utils,index_classes,evaluation}.py`.** Listed as a Sprint 05 / "Sprint 04.5" candidate. Scope: swap each `from src.utils.X` to a relative `from .X` (one-line edits in three files), then the `Generate_OEB_dataset.ipynb` cell 2 bootstrap (`sys.path.append(str(project_root))`) can finally retire. Requires a cross-repo coupling check against `bc3cat-retrieval`'s consumers of those modules before merging.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped s08 + `Generate_OEB_dataset` from "❌ Task A4 part 3" to "✅ Sprint 04" in the "Existing files extended" block (task A4 closes); prepended "After Sprint 04" to the Sprint History section.
**Next step:** Either the import-shape cleanup (Sprint 05 / 04.5 candidate above) or the end-to-end-validation sprint that reruns s01 → s08 → `Generate_OEB_dataset` against `data/intermediate/...` and byte-diffs `data/processed/OEB_*.parquet` / `*.pkl` against the in-repo originals to confirm the full path refactor is behaviour-preserving. The import-shape cleanup is the lower-risk pick to land first because the end-to-end rerun is gated on a Docker / `pandas` / `llama_index` env that the static-check sprints have not exercised.

---

### Sprint 03 — Path refactor: s02–s07 notebook migration
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_03.md`](sprints/SPRINT_03.md)
**Tasks from backlog:** A4 part 2 (s02–s07 notebook migration). A4 part 3 (s08 + `Generate_OEB_dataset`) remains open for Sprint 04.

**What was done:**
- Fanned the Sprint 02 migration pattern across the six remaining synthetic-critical-path notebooks. **14 source-cell `/work/...` literals** were rewritten in a single `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle per notebook, distributed as: s02 cell 2 (1), s03 cell 2 (1), s04 cell 3 (1), s05 cell 3 (1), s06 cell 2 (1), s07 cell 2 (2), s07 cell 3 (1), s07 cell 8 (4), s07 cell 11 (2). Replacements route through `config.INTERMEDIATE_DIR`, `config.chapter_path("OBRA CIVIL")`, and `config.stage_path("OBRA CIVIL", N)`; s07's three `_duplicate_*.json` side-artifacts inline as `config.INTERMEDIATE_DIR / chapter / f"{chapter}_..."`.
- Removed the two `project_root = Path('/work'); sys.path.append(str(project_root))` bootstrap pairs from `s07_Filter_duplicates.ipynb` cells 3 and 8 — **−4 source lines** of dead code. They were redundant because Jupyter's per-notebook kernel cwd is `src/` and `utils` is on the implicit `sys.path` entry (Sprint 02 finding). `from utils import config` was inserted into each touched cell's import block.
- Added [`tests/utils/test_notebooks_no_work_literal.py`](../../tests/utils/test_notebooks_no_work_literal.py) — a parametrised regression-guard test that scans the `source` arrays of s01–s07 and asserts zero `/work/` occurrences. Output arrays (`outputs`) are exempt per the s01 policy. Sprint 04 will extend the notebook list to include s08 + `Generate_OEB_dataset`.

**Key results:**
- `pytest tests -q` → **49 passed in 0.07s** (30 Sprint 01 + 12 Sprint 02 + 7 new notebook-guard cases). No regressions.
- Both smoke checks pass: all 7 notebooks parse via `json.load`, and `source-cell /work/ hits across s01-s07: 0`.
- `git status --short` matches the sprint's expected end-state exactly: 6 modified notebooks (`src/s0{2..7}*.ipynb`), 1 new test file, plus this log + `CLAUDE_SYNTHETIC.md` housekeeping. Nothing under `src/synthetic/`, `tests/synthetic/`, `data/`, or `configs/` in the diff.
- Per-notebook diff scope (`git diff --numstat`): s02 +3 / −1, s03 +3 / −1, s04 +3 / −1, s05 +3 / −1, s06 +3 / −1, s07 +14 / −13. The s07 net is only +1 because the four `project_root` / `sys.path.append` bootstrap lines are deleted while exactly five `from utils import config` insertions and the nine line-by-line path rewrites are added — confirming the bootstrap removal landed.

**Decisions made:**
- **Path objects passed bare.** `marcar_duplicados(path_entrada=config.stage_path(...), ...)` and `main(config.chapter_path(...))` go in without a `str(...)` wrapper. The static-check gate doesn't exercise runtime behaviour, but Sprint 02's s01 edit set the precedent (`os.chdir(config.RAW_DIR)` works because `os.chdir` accepts path-like objects) and the same pattern holds for every callee touched here. End-to-end validation in a future sprint is the gate that would catch a real mismatch.
- **Side-artifact paths inlined, not helper-promoted.** The three `_duplicate_*.json` paths and the `_either_duplicate.json` path in s07 cell 8 deliberately use `config.INTERMEDIATE_DIR / chapter / f"{chapter}_..."` rather than a new `chapter_artifact(chapter, suffix)` helper. YAGNI: only three callers in one cell. If a third site for `_duplicate_*` patterns surfaces in Sprint 04+, the helper can land then.
- **One helper script, one load/write cycle per notebook.** The Sprint 02 recipe (`json.load` → patch `source` arrays → `json.dumps(indent=1, ensure_ascii=False)`) reused unchanged. For s07's nine sites across four cells, a single load/edit/write cycle was used to keep the JSON pretty-printing stable across all the cell edits (avoiding nine re-pretty-prints that would have churned unrelated whitespace).
- **LF line endings preserved.** All six target notebooks use LF in-repo; the patch helper writes via `Path.write_bytes(json_text.encode("utf-8") + b"\n")` (bypassing Windows' universal-newlines text-mode translation). git's `core.autocrlf` produced a soft "LF will be replaced by CRLF" warning on each touched file but the in-repo bytes are LF, matching the existing convention.
- **Cell 11 of s07 import block.** Cell 11 originally imported only `import json` and relied on cells 3/8 to provide `Path` at notebook-execution time. After our rewrite, cell 11 no longer references `Path` (both call sites became `config.stage_path(...)`), so only `from utils import config` was added. No new transitive-import surprise — the cell stays self-sufficient for the columns it actually uses post-edit.

**Problems encountered:**
- None blocking. The atexit `cleanup_dead_symlinks` traceback observed at pytest shutdown is a known Windows-temp-dir-cleanup PermissionError unrelated to test outcomes (49 passed prints before the traceback). Same host as Sprint 02; no action.
- The Sprint 03 plan's expected `git status` does not list a `scripts/` directory. The one-shot migration helper that drove the 14 edits was authored under `scripts/sprint03_migrate_notebooks.py` for traceability, then removed after the patch landed cleanly — the durable artifact is the regression test, not the helper. Sprint 02 followed the same convention implicitly (no `scripts/` in its end-of-sprint diff either).

**Changes to plan:**
- None to the protocol. A4 part 2 closes; A4 part 3 (s08 + `Generate_OEB_dataset`) stays open for Sprint 04.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped s02–s07 from "❌ Task A4 part 2" to "✅ Sprint 03" in the "Existing files extended" block; prepended "After Sprint 03" to the Sprint History section. s08 + `Generate_OEB_dataset` remain ❌ for Sprint 04.
**Next step:** Draft `sprints/SPRINT_04.md` for A4 part 3 — fan the same migration pattern across `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb`. After Sprint 04 lands, the natural follow-up is the end-to-end-validation sprint that reruns s01 → s07 against the existing `data/intermediate/...` and byte-diffs the outputs against the in-repo `OEB_*.parquet` to confirm the path refactor is behaviour-preserving.

---

### Sprint 02 — Path refactor: config core + s01 migration
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_02.md`](sprints/SPRINT_02.md)
**Tasks from backlog:** A4 part 1 (config core + s01). A4 part 2 (s03–s07 notebook migration) remains open for Sprint 03.

**What was done:**
- Rewrote [`src/utils/config.py`](../../src/utils/config.py) into the single-source-of-truth paths module. New public surface: `REPO_ROOT`, `DATA_ROOT`, `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR`, `LLAMAINDEX_DIR`, `SYNTHETIC_DATA_ROOT`, `SYNTHETIC_INTERMEDIATE_DIR`, `SYNTHETIC_PROCESSED_DIR`, `SYNTHETIC_VARIANTS_DIR`, plus the helpers `chapter_path(chapter, *, root=INTERMEDIATE_DIR)` and `stage_path(chapter, stage_n, *, root=INTERMEDIATE_DIR)`. Env-var overrides `BC3CAT_DATA_ROOT` and `BC3CAT_SYNTHETIC_DATA_ROOT` are read at import time. The legacy `Config` class is preserved; its `DATA_DIR` / `TEXTO_PATH` / `RESUMEN_PATH` now route through `LLAMAINDEX_DIR`, so the `/work/data/llamaindex` literal disappears without touching `Config`'s public surface.
- Refactored [`src/s01_parse_fiebdc.ipynb`](../../src/s01_parse_fiebdc.ipynb): the two `os.chdir('/work/...')` sites (cell 1's `/work/data/raw` and `main()`'s `/work/data`) become `os.chdir(config.RAW_DIR)` / `os.chdir(config.DATA_ROOT)`. Cell 1 now does `from utils import config`. Jupyter's per-notebook kernel cwd is `src/` both inside Docker (`/work/src`) and on the Windows host, so `utils` resolves without a `sys.path` bootstrap. Diff scope: +4 / −2 across two cell `source` arrays, no metadata churn.
- Added [`tests/utils/`](../../tests/utils) with `conftest.py` (clone of `tests/synthetic/conftest.py` — prepends `src/` to `sys.path`) and `test_config.py` — 12 tests covering the eight Task-1 acceptance bullets: import surface, `Path` instance types, default `DATA_ROOT`, env-var override + sub-dir propagation, `SYNTHETIC_DATA_ROOT` default + env override, `chapter_path` / `stage_path` under both default and `SYNTHETIC_INTERMEDIATE_DIR` roots, `Config` back-compat, and the "no `/work/` literal in the module source" check. An autouse fixture with no fixture deps reloads the module after every test so env-var mutations don't bleed across tests in the same session.

**Key results:**
- `pytest tests -q` → **42 passed in 0.08s** (Sprint 01's 30 synthetic tests + 12 new utils tests). No regressions.
- All four smoke checks from the verification runbook pass: default paths, synthetic paths, `chapter_path`/`stage_path` helpers (default + synthetic root), `Config` back-compat. `Grep '/work/' src/utils/config.py` returns zero hits.
- Cell-source `/work/` audit on `s01_parse_fiebdc.ipynb` returns zero hits. `git diff` is exactly the two target lines plus the two-line `from utils import config` / blank-line insert in cell 1.

**Decisions made:**
- Env-var names locked: `BC3CAT_DATA_ROOT` and `BC3CAT_SYNTHETIC_DATA_ROOT`. Sprint 03+ will consume these as-is.
- Notebook bootstrap: chose the minimal `from utils import config` form over the `_REPO_ROOT` walker suggested as a fallback in the sprint plan. Verified that Jupyter's per-notebook kernel cwd is `src/` both inside the Docker container (`/work/src`) and on the Windows host (`…\bc3cat-dataset\src`), so `utils` is on the implicit notebook-dir `sys.path` entry without any bootstrap. Sprint 03's downstream-notebook fan-out will reuse this pattern.
- Notebook editing: `Edit` refuses `.ipynb` files, and full-cell `NotebookEdit` replaces would balloon the diff for the 300-line parser cell. Did byte-precise string replacements on the cell `source` arrays via a one-off `json.load` → patch → `json.dumps(..., indent=1)` script — preserves cell 2 verbatim and keeps the diff to +4 / −2.
- Test cleanup strategy: autouse fixture with no fixture dependencies, so its teardown runs after `monkeypatch`'s teardown — at which point one final `importlib.reload(config)` returns the module to defaults for any later test.

**Problems encountered:**
- The `nbformat`-based JSON-validity smoke check from the verification runbook is unavailable on this host's system Python. Substituted `json.load(...)` for the same well-formedness signal (acceptable because the rewriter emits JSON via `json.dumps`, so syntactic invalidity isn't a realistic failure mode).
- Otherwise none. Sprint plan's per-step acceptance criteria were tight enough that no clarifying questions surfaced.

**Changes to plan:**
- None to the protocol. A4 is split into two halves as the sprint plan anticipated; A4 part 2 (s03–s07 notebooks) is Sprint 03's focus.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped the s01 line in the "Top-level scaffolding" block to ✅ (part 1); noted the new `src/utils/config.py` surface; prepended "After Sprint 02" to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_03.md` for A4 part 2 — fan the same migration pattern across `s02_split_chapters.ipynb` → `s07_Filter_duplicates.ipynb`. Defer `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb` to Sprint 04 since they only emit the final main-pipeline artifacts and are not on the synthetic critical path.

---

### Sprint 01 — Taxonomy module + injection harness skeleton
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_01.md`](sprints/SPRINT_01.md)
**Tasks from backlog:** A2 (taxonomy), A5 (injection harness). A4 (path refactor) and A3 (LLM proposer spike) were deliberately deferred per the sprint's "Out of scope" block.

**What was done:**
- Created [`src/synthetic/__init__.py`](../../src/synthetic/__init__.py) — package scaffold with `__version__ = "0.1.0"`.
- Created [`src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) — `Layer` (4 members) and `ModificationType` (12 members) as `str, Enum`; `Modification` `@dataclass(frozen=True)` with the proposal §2.3 schema (`type`, `layer`, plus `param`, `var`, `condition`, `field`, `value`, `original`, `new`, `status`, `reason`); `to_dict()` / `from_dict()` JSON-friendly helpers; `TYPE_TO_LAYER` map covering all 12 → all 4 layers.
- Created [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) — `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param` public API with the signatures fixed by [`../CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md) "Stage-Hook Integration Note". Internal `_DISPATCH` registers exactly 12 stubs (`_stub_synonym_label` … `_stub_new_param`), each raising `NotImplementedError(f"Phase B: {type_code} mutator not yet implemented")`. Wrong-layer rules and unknown type codes raise `ValueError`; all four entry points deep-copy their input before any mutation.
- Created [`tests/synthetic/`](../../tests/synthetic) with `conftest.py` (prepends `src/` to `sys.path`), `test_taxonomy.py`, and `test_mutator.py` — 30 tests in total covering every acceptance bullet from Tasks 2–3.

**Key results:**
- `pytest tests/synthetic -q` → **30 passed in 0.10s**.
- All three smoke checks from the verification runbook (taxonomy invariants, four `inspect.signature` checks, `_DISPATCH` shape) pass.
- Round-trip via `json.dumps`/`json.loads` of `Modification.to_dict()` preserves all set fields; `None` fields are omitted from the serialised form.
- Stub-raise message uses the type-code string verbatim (e.g. `"Phase B: synonym_label mutator not yet implemented"`), so the parameterised 12-type test matches by substring.
- Deep-copy purity verified: snapshot-before / snapshot-after of the input JSON inside a `pytest.raises(NotImplementedError)` block compares byte-identical.

**Decisions made:**
- `to_dict()` omits `None` fields rather than emitting nulls. Cleaner JSON and round-trips fine because `from_dict()` defaults missing optional fields to `None` via the dataclass.
- Spelled out all 12 stubs as explicit named functions rather than generating them through a factory — the sprint pinned the names (`_stub_synonym_label` … `_stub_new_param`) and Phase B will physically relocate the bodies; named functions make that move mechanical.
- Routed the per-layer entry points through a single internal `_apply_rules(stage_json, concept_key, rules, expected_layer)` helper so the layer gate + deepcopy logic is in one place; `apply_new_param` has its own variant because it takes a single `rule` not a `list[dict]`.
- Test file skips optional `__init__.py` markers under `tests/` and `tests/synthetic/`. `conftest.py` alone is enough for pytest to discover and add `src/` to `sys.path`.

**Problems encountered:**
- None blocking. The sprint's signature and acceptance criteria were precise enough that no clarifying questions surfaced during implementation.

**Changes to plan:**
- None. Backlog A2 + A5 close cleanly; A4 (path refactor) remains the natural Sprint 02 candidate as suggested at the bottom of Sprint 00.

**CLAUDE_SYNTHETIC.md updated:** yes — three ❌ → ✅ flips for the new `src/synthetic/` files; new "After Sprint 01" entry prepended to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_02.md` for Task A4 — un-hardcode `/work/data/raw/` in `s01_parse_fiebdc.ipynb` and route through [`src/utils/config.py`](../../src/utils/config.py). This is the precondition for pipeline reruns from `data/synthetic/intermediate/`.

---

### Sprint 00 — Documentation scaffolding
**Date:** 2026-05-19
**Sprint file:** *(none — pre-sprint scaffolding work)*
**Tasks from backlog:** (precondition for) A1

**What was done:**
- Authored [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md). Adapts the BC3CAT-Syn rule-modification idea into the SEPLN-style proposal template used by `bc3cat-retrieval/docs/RESEARCH_PROPOSAL.md`. Contains motivation, anatomy of a BC3 concept, the 12-type modification taxonomy, the per-item metadata schema, the four-stage generation pipeline, the evaluation plan, and §6/§7 future work + open questions.
- Authored [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md). Implementation roadmap mirroring `bc3cat-retrieval/docs/RESEARCH_PROTOCOL.md`: repo context with the s01…s07 stage contract, three-layer injection interface, design-decisions table, phased task backlog (A → G), generation conditions, new file map, Spanish prompt templates, risk register.
- Authored [`../../CLAUDE.md`](../../CLAUDE.md) at the repo root — generic guidance for the dataset-generation pipeline, with a branch note routing the `synthetic` branch here.
- Authored [`CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md) — the branch-specific Claude Code context file: problem in one paragraph, mutation architecture diagram, design table, data structures, ✅/❌ file map.
- Authored this log.

**Key results:**
- Five documents created, zero source-code changes.
- Cross-links between the four docs resolve (relative paths within `docs/synthetic/`, plus one upward link to the repo-level `CLAUDE.md`).
- File-map in `CLAUDE_SYNTHETIC.md` is internally consistent with `RESEARCH_PROTOCOL.md §3.5` ("What Exists vs. What Needs Building") — every ❌ in the CLAUDE file corresponds to an unbuilt task in the protocol backlog.

**Decisions made:**
- **Injection level:** JSON-intermediate, between stages s02/s03/s04. Rejected raw-BC3 mutation because it would require re-serialising BC3 surface form for L1/L2 changes and would conflate which layer caused each surface-form delta.
- **Scope:** dataset-only. Retrieval evaluation against BC3CAT-Syn gets its own protocol in `bc3cat-retrieval`. Avoids cross-repo coupling.
- **Doc filename convention:** mirror the retrieval repo's split — repo-level `CLAUDE.md` + folder-level `CLAUDE_SYNTHETIC.md`. Confirmed with user when comparing against the structured-retrieval branch's `CLAUDE_STRUCTURED_RETRIEVAL.md`.

**Problems encountered:**
- `s01_parse_fiebdc.ipynb` hardcodes `/work/data/raw/`. Noted as Task A4 in the protocol; will be the first piece of code refactored in Sprint 01.
- The proposal's "modify the BC3 file" phrasing is at slight tension with the JSON-intermediate decision. Resolved by clarifying in `RESEARCH_PROTOCOL.md §3.3` that the mutation operates on the *parsed* representation, not the BC3 surface form, and that this is equivalent for the proposed contributions because the existing parser is bijective on the rule-defining sub-grammar.

**Changes to plan:**
- None — the protocol backlog A1…G4 reflects the agreed design.

**CLAUDE_SYNTHETIC.md updated:** yes (created in this sprint).
**Next step:** Draft `sprints/SPRINT_01.md` covering Phase A — Tasks A2 (`src/synthetic/taxonomy.py`), A4 (path refactor), and A5 (`src/synthetic/mutator.py` injection harness). A3 (LLM proposer spike) and A1 (branch scaffolding sprints/ + CLAUDE update plumbing) can be folded in or split out depending on bandwidth.
