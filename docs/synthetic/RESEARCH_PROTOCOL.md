# Research Protocol: BC3CAT-Syn — Rule-Modification Synthetic Benchmark

**Branch:** `synthetic`
**Repo:** `bc3cat-dataset`
**Author:** César · May 2026
**Target:** New paper 

---

## 1. Purpose and Scope

This protocol is the **implementation roadmap** for the research described in [RESEARCH_PROPOSAL.md](RESEARCH_PROPOSAL.md). It documents the repo context, design decisions, what needs to be built, and the task backlog. It does *not* prescribe rigid sprint boundaries — those are determined just-in-time as work progresses.

**Scope.** Dataset generation only. Retrieval evaluation against BC3CAT-Syn lives in the [`bc3cat-retrieval`](../../../bc3cat-retrieval) repository and is tracked by its own protocol. This document ends at the release of the BC3CAT-Syn artifact (Parquet + JSONL + data card).

**Companion documents:**

| Document                  | Role                                                    | When updated                          |
|---------------------------|---------------------------------------------------------|---------------------------------------|
| `RESEARCH_PROPOSAL.md`    | Goals, motivation, contributions, modification taxonomy | Rarely; only if scope changes         |
| `RESEARCH_PROTOCOL.md`    | This file; roadmap and backlog                          | When tasks are added/reprioritized    |
| `CLAUDE.md`               | Persistent context for Claude Code on this branch       | After every sprint                    |
| `RESEARCH_LOG.md`         | Running record of decisions, results, issues            | After every sprint                    |
| `sprints/SPRINT_NN.md`    | Individual sprint prompt for Claude Code                | Written just before each sprint       |
| `DATA_CARD.md` *(future)* | Data-in-Brief style description of the released dataset | At release (Phase G)                  |

---

## 2. Sprint Workflow

Sprints are **not pre-planned in detail**. Instead:

1. **Before each sprint**, César drafts a `sprints/SPRINT_NN.md` file with:
   - Context: what changed in previous sprints (or pointer to `CLAUDE.md`)
   - Objectives: specific tasks for this sprint
   - Acceptance criteria: how to verify it worked
   - Relevant code pointers and design decisions

2. **During the sprint**, Claude Code executes the sprint file. The sprint file is the prompt.

3. **After each sprint**, César:
   - Updates `RESEARCH_LOG.md` with what happened, what worked, what didn't
   - Updates `CLAUDE.md` with any new context Claude Code needs going forward
   - Decides what the next sprint should tackle (may split, reorder, or add tasks)
   - Drafts the next `sprints/SPRINT_NN.md`

This allows sprints to be split if too big, reordered based on results, and adapted as we learn.

---

## 3. Repository Context

### 3.1 Current State (main / branch baseline)

```
bc3cat-dataset/
├── data/
│   ├── raw/
│   │   └── BPA_2024_v2_OEB_mod_utf8.txt          # Source BC3 catalog (FIEBDC-3/2016)
│   ├── intermediate/
│   │   ├── BPA_2024_v2_OEB_mod_utf8.json         # Stage-1 parse
│   │   └── OBRA CIVIL/                           # Stage-2…Stage-7 outputs
│   │       ├── OBRA_CIVIL.json                   # Stage 2
│   │       ├── OBRA_CIVIL_stage3.json            # Stage 3 (expanded)
│   │       ├── OBRA_CIVIL_stage4.json            # Stage 4 (vars resolved)
│   │       ├── OBRA_CIVIL_stage5.json            # Stage 5 (templates instantiated)
│   │       └── OBRA_CIVIL_stage7.json            # Stage 7 (dedup)
│   └── processed/
│       ├── OEB_long_norm.parquet                 # 47,513 long-form items
│       ├── OEB_short_norm.parquet                # Short-form (queries)
│       ├── OEB_long_feats.parquet                # + derived features
│       └── OEB_short_feats.parquet
├── src/
│   ├── s01_parse_fiebdc.ipynb                    # BC3 → JSON
│   ├── s02_split_chapters.ipynb                  # Per-chapter JSONs
│   ├── s03_generate_parametric_combinations.ipynb # Cartesian expansion
│   ├── s04_evaluate_text_variables.ipynb         # Resolve $VAR formulas
│   ├── s05_evaluate_resumen_texto.ipynb          # Instantiate templates
│   ├── s06_data_analysis.ipynb                   # Stats / validation
│   ├── s07_Filter_duplicates.ipynb               # Dedup
│   ├── s08_Llamaindex_Doc_Creation.ipynb         # LlamaIndex packaging
│   ├── Generate_OEB_dataset.ipynb                # OEB subset → Parquet
│   └── utils/
│       ├── config.py
│       ├── custom_types.py
│       ├── data_utils.py
│       ├── evaluation.py
│       ├── index_classes.py
│       ├── text_processing.py
│       └── z_formula_processing.py
├── DataInBrief_BC3CAT.docx
├── docker-compose.yml
└── README.md
```

### 3.2 Pipeline Stage Contract

Each stage is a deterministic JSON → JSON transform. The synthetic engine mutates the JSON between stages rather than rewriting the source BC3 file (see §4, "Injection level").

| Stage | Notebook                                  | Input                                  | Output                                          | Key function(s)                                                |
|:-----:|-------------------------------------------|----------------------------------------|-------------------------------------------------|----------------------------------------------------------------|
| **s01** | `s01_parse_fiebdc.ipynb`                | `data/raw/BPA_2024_v2_OEB_mod_utf8.txt` | `data/intermediate/BPA_2024_v2_OEB_mod_utf8.json` | `FIEBDCParser` class — `~C` / `~P` / text-vars / `\RESUMEN\` / `\TEXTO\` extraction |
| **s02** | `s02_split_chapters.ipynb`              | Stage-1 JSON                            | `data/intermediate/{CHAPTER}/{CHAPTER}.json`    | `split_chapters()` — groups by first character (A, C, E, G, O, P, S, T, V) |
| **s03** | `s03_generate_parametric_combinations.ipynb` | Stage-2 JSON                       | `{CHAPTER}_stage3.json`                          | `transform_data()` + `generate_combinations()` — `itertools.product` over axes |
| **s04** | `s04_evaluate_text_variables.ipynb`     | Stage-3 JSON                            | `{CHAPTER}_stage4.json`                          | `process_text_variables()`, `evaluate_formula()` → uses [src/utils/z_formula_processing.py](../../src/utils/z_formula_processing.py) |
| **s05** | `s05_evaluate_resumen_texto.ipynb`      | Stage-4 JSON                            | `{CHAPTER}_stage5.json`                          | `evaluate_string()` — `$L(...)` and `$A` substitution           |
| **s06** | `s06_data_analysis.ipynb`               | Stage-5 JSON                            | (stats, no file)                                 | `normalize_data()` — characterization                          |
| **s07** | `s07_Filter_duplicates.ipynb`           | Stage-5 JSON                            | `{CHAPTER}_stage7.json`                          | `marcar_duplicados()`, `filter_json()`                          |
| **fin** | `Generate_OEB_dataset.ipynb`            | Stage-7 JSON                            | `data/processed/OEB_*.parquet`                  | OEB-subset filter + Parquet export                              |

### 3.3 Three-Layer Mutation Interface

The synthetic engine treats each between-stage JSON as a typed contract. Each mutator is a pure function over a stage-JSON dict.

| Layer | Code label         | Mutation point                    | Receives                                          | Returns                                                      |
|:-----:|--------------------|-----------------------------------|---------------------------------------------------|--------------------------------------------------------------|
| **L1** | `param_value`     | Between **s02** and **s03**       | `parameters[axis_key]["values"]` arrays           | New values + `Modification` log entries                      |
| **L2** | `text_variable`   | Between **s03** and **s04**       | `text_variables[var_key]` formula strings          | New formula strings + `Modification` log entries             |
| **L3** | `template`        | Between **s04** and **s05**       | `resumen` and `texto` template strings             | New templates + `Modification` log entries                   |
| **PD** | `param_definition` | Between **s02** and **s03**      | Full `parameters` dict (adds a new axis)           | Augmented `parameters` + `$VAR` definition + template patch  |

Mutations from different layers compose by stacking. **Canonical apply order (pinned by §B5 / Sprint 11):** **PD → L1 → L2 → L3.** PD runs first because its job is to install a new axis that subsequent L1/L2/L3 rules in the same batch may reference; L1 / L2 / L3 follow in stage-numerical order. The protocol's earlier "L1 first, then L2, L3, PD" phrasing was written before PD's cross-block edits were specified — the PD-first order is now the unconditional canonical pin (the conditional "PD-first if the new axis affects L2/L3" framing is superseded). The engine logs every applied mutation as a `Modification` record (proposal §6.1 schema).

### 3.4 Key Data Facts

- **OEB long-form corpus** (`OEB_long_norm.parquet`): 47,513 rows. Columns include `item_key`, `parent_key`, `concept`, `parameters` (dict), `text`, `text_norm`, `text_word_params`, `numbers`, `param_tokens`.
- **OEB short-form corpus** (`OEB_short_norm.parquet`): same row count, used as queries by `bc3cat-retrieval`.
- **Stage-7 full chapter**: 111,644 unique items in OBRA CIVIL; the OEB subset is 47,513.
- **Concept groups**: 25, sizes 3–6,336.
- **Parameter structure**: `parameters[axis_key] = {"label": "...", "values": [{"label": "a", "value": "..."}, ...]}`.
- **Item-key derivation**: `parent_key[:-1] + parameter_label_sequence` (e.g., `OEB020aaeaa`).
- **Synthetic variant key**: `(original_key, variante_id)` → synthetic `item_key = f"{original_key}_syn_{variante_id}"`.

### 3.5 What Exists vs. What Needs Building

| Component                                | Exists? | Notes                                                                                  |
|------------------------------------------|:-------:|----------------------------------------------------------------------------------------|
| BC3 parser (`FIEBDCParser`)              | ✅      | `s01_parse_fiebdc.ipynb`                                                              |
| Parametric expander (`generate_combinations`) | ✅  | `s03_generate_parametric_combinations.ipynb`                                          |
| Formula translator (`translate_formula_to_python`) | ✅ | [src/utils/z_formula_processing.py](../../src/utils/z_formula_processing.py)         |
| Text-variable resolver (`process_text_variables`, `evaluate_formula`) | ✅ | `s04_evaluate_text_variables.ipynb` |
| Template instantiator (`evaluate_string`) | ✅      | `s05_evaluate_resumen_texto.ipynb`                                                    |
| Deduplicator (`marcar_duplicados`, `filter_json`) | ✅ | `s07_Filter_duplicates.ipynb`                                                       |
| Text normalizer (`normalize_text`)       | ✅      | [src/utils/text_processing.py](../../src/utils/text_processing.py)                    |
| Parquet packager                          | ✅      | `Generate_OEB_dataset.ipynb`                                                          |
| Modification taxonomy module              | ❌      | A2 — 12-type enum + `Modification` dataclass                                          |
| L1 / L2 / L3 mutators                     | ❌      | B1–B3 — per-layer pure-function transformers                                          |
| L2 real-data representation adapter       | ✅      | B6 (Sprint 26) — `l2_repr.py`: reference-style-aware adapter; fixes the silent L2 no-op across **all three** real text-variable shapes (`LIST_plain` indexed, `STR_formula` bare, `LIST_conditional` bare). Two-mode `list_to_formula` (enumerate vs apply) + `formula_to_list` (restores only indexed vars) + `assert_l2_targets_or_warn` guard; byte-faithful baseline. Consumer above the frozen seam. |
| Single-concept pilot harness              | ✅      | F1-build (Sprint 27) — `f1_pilot.py`: `run_pilot` composes `run_concept`→`stage_b`→`metadata`→`review` over one concept with the `l2_repr` adapter bracketed in (via a default-identity `pre_rerun` hook on `stage_b`); live LLM through `RecordingClient` (offline `replay`); `PilotScore` + 100 %-coverage queue. F1-run (live + manual review) is Sprint 28. |
| `new_param` mutator                       | ❌      | B4 — adds axis + `$VAR` + template hook                                               |
| Three-layer injection harness             | ❌      | A5 — `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`                         |
| LLM-assisted variant proposer             | ❌      | C1–C3 — prompt library + client + JSON validator                                      |
| Concrete `LLMClient` transport            | ✅      | A3a (Sprint 24) — `llm_client.py`: stdlib `urllib` OpenAI-compat `HttpLLMClient` + `ReplayClient`/`RecordingClient`, behind the frozen Protocol. |
| Model-choice spike harness                | ✅      | A3b-build (Sprint 25) — `spike.py`: composes the unedited `run_concept` over the 12 single-type conditions per candidate through a `RecordingClient`; automatable scorecard (parse/schema/skip/latency/length). A3b-run (live ≥2-model spike + §4 flip) still ⏳ (manual, paid, César). |
| Variant catalog format                    | ❌      | C4 — JSON-per-concept, durable artifact of Stage A                                    |
| Stage hooks (s03/s04/s05 acceptors)       | ❌      | D1 — accept mutated stage-N JSONs transparently                                       |
| Synthetic orchestrator                    | ❌      | D2 — variant catalog → mutated JSONs → pipeline → raw synthetic items                 |
| Metadata join + schema validator          | ❌      | E1–E2 — bind synthetic items to their `modifications` list                            |
| Validation sampler + reviewer harness     | ✅      | E3–E4 — stratified sampling + CLI for verdicts                                        |
| Dataset packager + loader utilities       | ✅      | G1 ✅ (`packaging.py`, Sprint 21 — Parquet + sidecar JSONL) / G2 ✅ (`loaders.py`, Sprint 22 — read API + 1:1 join + long/short views) |
| Path / config refactor                    | ❌      | A4 — un-hardcode `/work/data/raw/`; route through `src/utils/config.py`               |

---

## 4. Design Decisions

| Question                                   | Decision                                                                              | Rationale                                                              |
|--------------------------------------------|---------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| Injection level                            | **JSON-intermediate** (between s02/s03/s04 outputs)                                   | Skips re-parsing BC3; isolates one layer per atomic mutation           |
| Mutation atomicity                         | One layer × one target per atomic `Modification`                                      | Per-type evaluation slices remain clean                                |
| Multi-mod variants                         | Composed by stacking atomic mutations (L1 → L2 → L3 → PD)                              | Compositionality slices need explicit stack depth                      |
| Variant ID format                          | `{original_key}_syn_v{n}`                                                              | Preserves lexicographic parent grouping                                |
| Variant catalog format                     | JSON-per-concept under `data/synthetic/variants/`                                      | Durable Stage-A artifact; decoupled from pipeline reruns               |
| LLM proposer model                         | **`llama3.1:8b`, local via Ollama** (`base_url http://localhost:11434/v1`; use the **exact** tag `llama3.1:8b` — the bare `llama3.1` resolves to `:latest` and 404s unless separately pulled) — committed (A3b-run, 2026-05-20) as a deliberate strategic choice (cost / privacy / reproducibility), **not** a measured fluency winner; the `spike.py` harness stays available to compare local variants if F1 review flags quality | Local-only, free + reproducible to re-run; Spanish-technical fluency is validated in the F1 100 %-manual pilot review rather than a pre-generation spike |
| Stage-A locality                           | Offline batch                                                                         | Decouples expensive LLM calls from cheap pipeline reruns               |
| Manual review coverage                     | 100 % for `new_param`; stratified sampling for the other 11 types                     | Semantic-collision risk is concentrated in `new_param`                 |
| Stratification axis                        | `(concept × modification_type)` crossed                                                | Per-cell statistical power for the slice analyses                      |
| Path-hardcoding                            | Refactor `/work/data/raw/` → `src/utils/config.py` early (A4)                          | Required for synthetic re-runs from a different data root              |
| Pickle / cache invalidation                | Cleared between runs; documented in `CLAUDE.md`                                        | BM25/embedding caches assume stable corpus                             |
| Unstackable-combo handling                 | Skip + log                                                                            | Better to lose coverage than corrupt traceability                      |
| Release format                             | Parquet for items + sidecar JSONL for `modifications` arrays                           | Parquet stays columnar/flat; JSONL carries the nested mutation log     |
| Identity invariant                         | Synthetic items preserve the original `params` dict semantics                          | Enables direct join to original ground-truth item                      |

---

## 5. Task Backlog

Ordered by dependency and priority. Tasks will be grouped into sprints as work progresses — a task may be split into multiple sprints or combined depending on what we learn.

### Phase A — Setup

- **A1. Branch scaffolding.** Create `docs/synthetic/sprints/`, initial `RESEARCH_LOG.md`, and a branch-specific `CLAUDE.md` summarising the protocol's design decisions for Claude Code.
- **A2. Modification taxonomy module.** `src/synthetic/taxonomy.py` — `ModificationType` enum (12 codes), `Layer` enum (4 layers), `Modification` dataclass matching the proposal §6.1 schema.
- **A3. LLM proposer transport + choice spike.** Split into two:
  - **A3a ✅ (Sprint 24) — concrete transport + record/replay harness.** `src/synthetic/llm_client.py`: a stdlib-`urllib` OpenAI-compatible `HttpLLMClient` (two-layer-separated network-fault retry/backoff, injectable sender, fail-loud) plus `ReplayClient`/`RecordingClient`, all behind the already-frozen `llm_proposer.LLMClient` Protocol. Hermetic test suite (zero network calls); one env-gated live smoke that skips-not-fails.
  - **A3b.** Split into two, same fault line as A3:
    - **A3b-build ✅ (Sprint 25) — the spike harness.** `src/synthetic/spike.py`: a consumer module (above the seam, never imported by it) that composes the **unedited** `run_concept` over the 12 single-type conditions for each candidate, wraps every client in a `RecordingClient` (per-candidate store), and tallies an **automatable** `CandidateScore` (JSON-parse/schema-pass, the C2/C3 skip split, per-type outcome, latency, response length) off the returned `VariantCatalogEntry`. `format_scorecard` emits a comparison table (automatable columns only — **no fluency column**). Hermetic test suite (zero network calls); the live run is the manual CLI, not a `pytest` case.
    - **A3b-run ✅ (2026-05-20 — strategic commitment, not a live spike).** Decision: generate with **local Llama (`llama3.1` 8B via Ollama)**, chosen for cost, privacy, and reproducibility rather than a measured ≥2-model fluency comparison. §4's `LLM proposer model` row is flipped from `TBD` accordingly (the default config already points here). The `spike.py` harness remains available to compare local variants (8B vs 70B vs a Spanish-tuned model) **if** the F1 pilot review surfaces Spanish-quality concerns — at which point fluency is judged on the harness's recorded transcripts. Spanish-fluency validation otherwise moves into the F1 100 %-manual review.
- **A4. Path refactor.** Un-hardcode `/work/data/raw/` in s01 and any downstream stages; route everything through [src/utils/config.py](../../src/utils/config.py). Add a `SYNTHETIC_DATA_ROOT` config entry.
- **A5. Three-layer injection harness.** `src/synthetic/mutator.py` exposing `apply_l1`, `apply_l2`, `apply_l3`, `apply_new_param` over stage-JSON dicts. Each returns `(mutated_json, list[Modification])`.

### Phase B — Per-layer mutator implementations

- **B1. L1 value-set mutators.** `src/synthetic/layer_l1.py` — `synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`. Each `(values, rules) → (new_values, log)`.
- **B2. L2 text-variable mutators.** `src/synthetic/layer_l2.py` — `paraphrase`, `expansion`, `compression`. Operates on `$VAR = "fragment" * (%X=y) + ...` formulas; never touches the conditional structure, only the string fragments.
- **B3. L3 template mutators.** `src/synthetic/layer_l3.py` — `omission`, `reorder`. Operates on `\RESUMEN\` / `\TEXTO\` strings; preserves untargeted `$var` references.
- **B4. `new_param` mutator.** `src/synthetic/layer_pd.py` — adds a new axis to `parameters`, a corresponding `$VAR` definition, and injects the variable into the template. Requires a controlled-list veto against collisions with existing axes.
- **B5. Composition rules.** Encode which atomic mutations may stack on the same target (e.g., `unit_conversion` ∘ `num_to_text` requires an explicit ordering). Conflicts: skip + log via the `Modification` record. Matrix lives in `src/synthetic/composition.py` as a Python module-level constant for B5; YAML externalisation (`configs/synthetic/composition_rules.yaml`) deferred to a later phase if Phase C / E tooling needs an editable surface without code changes.
- **B6 ✅ (Sprint 26) — L2 real-data representation adapter.** `src/synthetic/l2_repr.py`: a **reference-style-aware** adapter that fixes the **silent L2 no-op** — `slot_extractor.enumerate_targets` skips any non-string text-variable, and real data has **three shapes** whose rerun form is set by the template ref: `LIST_plain` (`['"Diurno"', …]`, indexed `$L(%B)` → positional list), `STR_formula` (`'"normal" * (%B=="a") + …'`, bare `$K` → formula string), and `LIST_conditional` (`['"…" * (%B=="f")', …]`, bare `$P` → list of conditional fragments). The two list shapes were silently un-enumerable. Two-mode `list_to_formula` makes all three enumerable for Stage A (`include_conditional=True`) or converts only `LIST_plain` for application (`include_conditional=False`, so `STR_formula`/`LIST_conditional` mutate natively via `layer_l2` and stay byte-faithful); `formula_to_list` restores **only indexed-referenced** vars to positional lists before the s03→s07 rerun. Per-var report (nothing silent); `assert_l2_targets_or_warn` guard; **byte-faithful baseline** verified (unmutated round-trip == original rerun on `OEB020$`'s 4608 leaves). Consumer above the frozen seam — `slot_extractor`/`layer_l2`/`rule_emitter` untouched. *(Discovered while selecting the F1 pilot concept; fixed before F1 so the pilot covers all 12 types. Two error-swallowing risks — `stage_runners` s04 bare `except`, `stage_b` skip-and-log — are a documented follow-up, not B6.)*

### Phase C — LLM-assisted variant proposer (Stage A of the proposal)

- **C1. Prompt template library.** `src/synthetic/prompts/` — one Spanish prompt per modification type. Each prompt declares its JSON-output contract.
- **C2. LLM client.** `src/synthetic/llm_proposer.py` — wraps the model chosen in A3. Structured JSON output, malformed-response retry (×1), fallback log entry.
- **C3. Variant proposer.** Given `(concept, modification_type, layer_state)`, calls the LLM, validates output shape against the `Modification` schema, and returns a candidate. Reviewer harness (E4) gates acceptance.
- **C4. Variant catalog.** JSON-per-concept files under `data/synthetic/variants/` storing every accepted variant with its full `modifications` log. Durable artifact of Stage A; pipeline reruns consume this catalog.

### Phase D — Pipeline integration

- **D1. Stage hooks.** Wrap s03 / s04 / s05 entry points so they accept either the original stage-N JSON or a mutated one transparently. No changes to the stages' internal logic.
- **D2. Synthetic orchestrator.** `src/synthetic/run_synthetic.py` (or notebook) — given a variant catalog, materialises mutated stage JSONs, reruns s03→s07, emits raw synthetic items into `data/synthetic/intermediate/`.
- **D3. Cache hygiene.** Identify and clear any pickled BM25 / embedding / LlamaIndex caches between runs. Document the list in `CLAUDE.md`.

### Phase E — Metadata + validation (Stages C–D of the proposal)

- **E1. Metadata join.** `src/synthetic/metadata.py` — bind synthetic items to their `modifications` list via `(original_key, variante_id)`. Produces the final per-item record (proposal §6.1).
- **E2. Schema validator.** Assert every synthetic item carries `original_key`, `variante_id`, `modification_types`, `modification_count`, and a well-formed `modifications` array. Fail-loud on missing fields.
- **E3. Validation sampler.** Stratified sampler over `(concept × modification_type)`; surfaces a review queue with target coverage per cell.
- **E4. Domain reviewer harness.** `src/synthetic/review.py` — CLI / notebook capturing verdicts on (i) grammaticality, (ii) semantic preservation, (iii) axis distinguishability (for `new_param`), (iv) metadata accuracy. Records inter-annotator agreement when multiple reviewers participate.

### Phase F — Pilot then full generation

- **F1. Single-concept pilot.** Pick 1–2 concept groups of moderate size (50–200 items each, e.g., a mid-sized OEB group); generate one variant per modification type; 100 % manual review. Pilot concept pinned: **`OEB070$`** (144 items). Split:
  - **F1-build ✅ (Sprint 27) — the runnable harness.** `src/synthetic/f1_pilot.py`: `run_pilot` composes the unedited stack (`run_concept` → `stage_b` → `metadata` → `review`) over one concept across all conditions, with the `l2_repr` two-mode adapter bracketing the mutation (and a default-identity `pre_rerun` hook in `stage_b` as the `formula_to_list` insertion point). Live LLM through a `RecordingClient` (offline `replay`); automatable `PilotScore`; 100 %-coverage review queue. Hermetic tests; no live `pytest` case. Consumer above the orchestrator.
  - **F1-run-generate ✅ (Sprint 28, then re-run after F2 fixes).** Ran `f1_pilot run` on `OEB070$` against Ollama `llama3.1:8b`, all 17 conditions. First run exposed 8B defects (prose/fence-wrapped JSON, wrong list keys, placeholder corruption). After the **F2 process-hardening** (below) the re-run yields **48 placeholder-clean variants** (malformed 31→7, wrong-key 24→0); the residual is `unmatched_original` on L1-expansion-of-inapplicable-axes (a targeting matter, largely legitimate).
  - **F2 process-hardening ✅ (3 iterations).** (1) `llm_proposer._extract_json_object` recovers JSON from prose+fence; (2) `variant_proposer` placeholder-preservation validator (reorder/omission); (3) L1 prompt fixes — JSON keys aligned to the schema (`conversions`/`expansions` → `synonyms`) and a verbatim-`original` instruction (kill the `"a: "` label-prefix echo). `pytest` 826 passed, 2 skipped.
  - **F1-review ⏳ (pending — César).** Review the 43 distinct modifications (digest: `docs/synthetic/F1_PILOT_REVIEW_DIGEST.md`) — Spanish fluency + retrieval-safety + per-type semantics; verdicts via `review.write_verdicts`; the `llama3.1:8b` verdict feeding F2.
- **F2. Pilot retro.** ✅ (Sprints 30–36) Measured acceptance rate per type, tuned prompts (sibling-fragments slot, per-axis targeting gate, paired L1+L2 mutation for indexed twins, collision guard), added the 13th modification type (`template_paraphrase`), and validated multi-concept generalisation on OEB020$ + OEB050$ + OEB070$. `phi4:latest` selected as the F3 model.
- **F3. Full generation.** Run across all 25 concept groups. Variant count scales with original group size, capped on the largest group (6,336 items) to control combinatorial blowup. **Split (Sprint 37):**
  - **F3-prep-1 ✅ (Sprint 37) — menu builder** (hermetic). `src/synthetic/target_scanner.py` + `menu_proposer.py` + `menu_artefacts.py` implement the *menu-first* Stage-A flow requested by César (2026-07-08): dedup targets across concepts (83 % savings, 673→562 unique on OEB subset), propose **N=10 candidates per unique target**, write both a machine-readable JSONL (for the sampler) and a human-review Markdown (for the reviewer) per rewrite type. 990 passed, 2 skipped; zero seam edits.
  - **F3-prep-2 ⏳ (Sprint 38) — live run + manual review.** Split into four landmarks:
    - **F3-prep-2-code ✅ (Sprint 38, 2026-07-09).** `src/synthetic/menu_runner.py` (CLI driver above the frozen seam; `MenuRun` scorecard, `run`/`replay` subcommands, `ResumingRecordingClient` cache-first wrapper) + `menu_review_parser.py` (reads ticked Markdown back into structured `MenuVerdict` JSONL; fail-loud on structural drift; reject-by-default). 1018 passed, 2 skipped; zero seam edits.
    - **F3-prep-2-generate ✅ (Sprint 38, 2026-07-09).** Ran against `phi4:latest`, `temperature 0`, `BC3CAT_LLM_TIMEOUT=300`. 5528 s wall-clock, 562 unique targets across 25 OEB concepts, 636 phi4 calls (89 L1 targets served by 29 batched calls). **2 918 candidates** across 11 populated rewrite types; per-type generation rate 100 % on L2 + new_param, 88 % on synonym_label, 53 % on omission (`_require_placeholders_omitted` filter working as designed). Artefacts under `data/synthetic/menus/{mtype}.jsonl` + `docs/synthetic/menus/{mtype}.md`; recorded transcripts under `data/synthetic/llm_cache/menu_OEB/` (502 prompts, offline-replayable).
    - **F3-prep-2-review ⏳ (César, manual, ~7-9 h).** Tick approvals in the 11 Markdown files under `docs/synthetic/menus/`.
    - **F3-prep-2-parse ⏳ (Claude, post-review).** `python -m synthetic.menu_review_parser parse` translates ticks into `data/synthetic/menus/verdicts/{mtype}.jsonl` + a coverage-summary report.
  - **F3-prep-3 ⏳ (Sprint 39) — variant budgets + sampler + chapter driver.** `configs/synthetic/variant_budgets.yaml` (flat 50 per concept, César 2026-07-08), the deterministic sampler that draws N variants per concept from the approved menu, and the chapter driver that iterates concept keys.
  - **F3-run ⏳ (Sprint 40)** — execute the chapter driver over OBRA CIVIL; land the corpus.
- **F4. Validation pass.** Stratified sample reviewed against the F1 protocol; produce a quality report under `docs/synthetic/QUALITY_REPORT.md`.

### Phase G — Release

- **G1. Packaging.** Parquet items mirroring `OEB_long_norm.parquet` schema plus four metadata columns (`original_key`, `variante_id`, `modification_types`, `modification_count`); sidecar JSONL keyed by `item_key` carrying the full `modifications` array.
- **G2. Loader utilities.** `src/synthetic/loaders.py` — `load_items()`, `load_modifications()`, `join()`. Used by downstream consumers, primarily `bc3cat-retrieval`.
- **G3. Documentation.** ✅ (Sprint 23) `docs/synthetic/DATA_CARD.md` (Data-in-Brief style) + a "Synthetic Variant" section appended to the top-level `README.md`. Documents the frozen G1/G2 contract; all corpus-scale statistics are `TBD (pending F3)` placeholders pending a post-F3 refresh.
- **G4. Cross-repo handoff.** ✅ (Sprint 23) Short memo in `docs/synthetic/HANDOFF.md` pointing `bc3cat-retrieval` at the new dataset, the new slice columns (`modification_types`, `modification_count`), and the loader API.

### Backlog (if time permits)

- Query-side variability (modify queries against unmodified catalog, mirroring real-deployment asymmetry).
- Difficulty-controlled negative mining (single-axis-differing pairs as contrastive triplets).
- Multi-language extension (replicate L2/L3 prompts in additional languages).
- Cross-domain replication (apply to a non-construction parametric catalog).
- Use of BC3CAT-Syn as a fine-tuning corpus (per-type adapters, denoising objectives).

---

## 6. Generation Conditions

Each condition is a recipe for the synthetic orchestrator, used both for development sanity-checks and for slice-aware downstream evaluation.

| Condition            | Layers mutated         | Stack depth   | Purpose                                          |
|----------------------|------------------------|---------------|--------------------------------------------------|
| `single_L1_*`        | one of the L1 types    | 1             | Per-type isolation slices for `param_value`      |
| `single_L2_*`        | one of the L2 types    | 1             | Per-type isolation slices for `text_variable`    |
| `single_L3_*`        | one of the L3 types    | 1             | Per-type isolation slices for `template`         |
| `new_param_only`     | param_definition       | 1             | Stress new-axis introduction in isolation        |
| `stacked_2` … `5+`   | mixed                  | 2, 3, 4, ≥5   | Compositionality slices                          |
| `full_random_mix`    | all                    | sampled       | Headline robustness slice                        |

**Diagnostic interpretation** (for the downstream `bc3cat-retrieval` evaluation):
- `single_*` baselines isolate per-type degradation per retriever family.
- `stacked_*` curves quantify whether degradation is sub-/linear/super-linear in mutation count.
- A retriever family failing `single_L1_synonym_label` but surviving `single_L2_paraphrase` (or vice-versa) localises its weakness to the lexical-vs-semantic axis.

---

## 7. New File Map

```
src/
  synthetic/                                # NEW package
    __init__.py
    taxonomy.py                             # A2 — enums + Modification dataclass
    mutator.py                              # A5 — apply_l1/l2/l3/new_param
    layer_l1.py                             # B1 — param-value mutators
    layer_l2.py                             # B2 — text-variable mutators
    layer_l3.py                             # B3 — template mutators
    layer_pd.py                             # B4 — new_param mutator
    composition.py                          # B5 — stacking rules
    llm_proposer.py                         # C2–C3 — client + variant proposer
    prompts/                                # C1
      synonym_label.txt
      num_to_text.txt
      unit_conversion.txt
      unit_expansion.txt
      abbrev_expansion.txt
      code_expansion.txt
      paraphrase.txt
      expansion.txt
      compression.txt
      omission.txt
      reorder.txt
      new_param.txt
    metadata.py                             # E1–E2
    review.py                               # E3–E4
    run_synthetic.py                        # D2
    loaders.py                              # G2

configs/
  synthetic/                                # NEW
    variant_budgets.yaml                    # per-concept variant counts
    new_param_allowlist.yaml                # controlled list of admissible new axes
    composition_rules.yaml                  # B5 stacking constraints (deferred — matrix is in `src/synthetic/composition.py`)

data/
  synthetic/                                # NEW
    variants/                               # variant catalog JSON-per-concept (C4)
    intermediate/                           # mutated stage JSONs (D2)
    processed/                              # final BC3CAT-Syn release (G1)
      BC3CAT_Syn_items.parquet
      BC3CAT_Syn_modifications.jsonl

docs/
  synthetic/
    RESEARCH_PROPOSAL.md                    # done
    RESEARCH_PROTOCOL.md                    # this file
    RESEARCH_LOG.md                         # running log
    CLAUDE.md                               # branch-specific
    DATA_CARD.md                            # G3
    QUALITY_REPORT.md                       # F4
    HANDOFF.md                              # G4
    sprints/                                # JIT
      SPRINT_00.md
      SPRINT_01.md
      ...
```

---

## 8. LLM Prompt Templates (Stage A)

All prompts are in Spanish (catalog language), enforce a strict JSON output contract, and run at temperature 0.0. Malformed responses get one retry, then a `fallback: skipped` log entry.

### 8.1 Representative prompt — `synonym_label` (L1)

```
Eres un experto en terminología técnica de construcción ferroviaria en español.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Genera un sinónimo natural en español técnico para cada valor, preservando
exactamente el significado paramétrico (no cambies el referente físico).

Responde SOLO con un JSON con la forma:
{
  "synonyms": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### 8.2 Representative prompt — `paraphrase` (L2)

```
Eres un redactor técnico en español. Vas a reformular fragmentos de texto
de un catálogo de construcción ferroviaria.

Concepto: {concept}
Variable de texto: {var_key}
Fragmento original: "{fragment}"
Condición asociada: {condition}

Reformula el fragmento manteniendo el significado técnico exacto. No alteres
las cantidades, unidades, ni el referente físico. Devuelve UN único fragmento
alternativo.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "preserves_meaning": true
}
```

### 8.3 Representative prompt — `omission` (L3)

```
Eres un redactor técnico. Vas a omitir una mención de parámetro en una plantilla.

Concepto: {concept}
Plantilla actual: "{template}"
Variable a omitir: {var_to_omit}  (corresponde al parámetro: {axis_label})

Reescribe la plantilla eliminando toda mención al parámetro {axis_label},
pero conservando TODAS las demás variables ($A, $B, …) tal cual aparecen.
El texto resultante debe ser gramatical y coherente.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "omitted_var": "..."
}
```

### 8.4 Representative prompt — `new_param` (PD)

```
Eres un experto en catalogación técnica de obra civil ferroviaria.

Concepto: {concept}
Ejes existentes: {existing_axes_with_labels}

Propón UN nuevo eje de parámetro coherente con el concepto. El nuevo eje
debe ser claramente distinguible de los existentes (sin solapamiento semántico).
Debe tener entre 2 y 5 valores discretos.

Restricción: el nuevo eje debe estar en la lista de ejes admisibles:
{allowlist}

Responde SOLO con un JSON:
{
  "new_axis_label": "...",
  "values": [
    {"label": "a", "value": "..."},
    ...
  ],
  "var_definition": "$X = \"...\" * (%G=a) + ...",
  "template_patch": "..., con $X, ..."
}
```

The remaining prompts (`num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`, `expansion`, `compression`, `reorder`) follow the same JSON-contract pattern, one per file under `src/synthetic/prompts/`.

---

## 9. Risk Register

| Risk                                                                | Mitigation                                                                                                  |
|---------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| LLM proposals are not semantically equivalent to the original       | Domain reviewer harness (E4) gates acceptance; 100 % review on `new_param`; stratified review on others     |
| Mutation interaction effects (e.g., `unit_conversion` × `num_to_text` produces nonsense) | Composition rules (B5) declare admissible stacks; conflicts are skipped and logged                |
| Combinatorial blowup on the largest concept group (6,336 items)     | Variant budget formula in `configs/synthetic/variant_budgets.yaml` caps per-concept variant count           |
| `new_param` collisions with existing axes                           | Controlled allow-list (`new_param_allowlist.yaml`) + 100 % manual review                                    |
| Hardcoded `/work/data/raw/` path blocks reproducibility             | A4 path refactor scheduled before any generation work                                                       |
| Pickle / cache staleness across reruns                              | D3 cache-hygiene step; documented in `CLAUDE.md` after first run                                            |
| LLM cost / throughput on full-scale generation                      | Pilot (F1) measures throughput before committing to F3; offline batch + retry budget                        |
| Reviewer time on full-scale validation                              | Stratified sampling (E3) with explicit per-cell coverage targets                                            |
| Variant catalog (Stage A) drifts out of sync with mutator code      | Catalog records full atomic `Modification` payloads; mutator deterministically replays from the catalog    |
| BC3 surface form changes break injection                             | Injection works on parsed JSON, not BC3 text; any future BC3 schema change is caught at s01 boundary       |

---

## 10. Open Questions (Pre-Implementation)

These should be resolved before Sprint A1 begins:

1. **LLM proposer choice.** Deferred to A3 spike. Candidates to test on the 1-concept smoke task: GPT-4-class API for fluency ceiling, Llama 3.1 70B local for reproducibility, plus a Spanish-tuned model if one is competitive in technical-domain Spanish.
2. **Variant budget formula.** Concrete function of original concept-group size → number of variants per modification type. Default proposal: `min(group_size, 50)` per type per concept, revised after F2 retro.
3. **Sample-coverage thresholds for validation.** Per-cell target for the stratified sampler (e.g., 10 % per `(concept × modification_type)` cell with a floor of 5 variants per cell).
4. **Query side.** Decision deferred to backlog. Current pass modifies catalog only; queries are catalog-generated and inherit the modifications. A query-independent variant set is left as a backlog item.
5. **Public release license.** Match BC3CAT licensing; confirm before G3 publication.

---

## 11. Changelog

| Version | Date     | Changes                                                                                                                                                       |
|---------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| v0.1    | May 2026 | Initial protocol on branch `synthetic`. Mirrors the structure of `bc3cat-retrieval/docs/RESEARCH_PROTOCOL.md`. JSON-intermediate injection, dataset-only scope. |

---

*This document is the stable roadmap. Sprint-level detail lives in `docs/synthetic/sprints/SPRINT_NN.md` files, written just-in-time.*
