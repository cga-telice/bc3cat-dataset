# BC3CAT-Syn — Branch Context for Claude Code

**Branch:** `synthetic`
**Goal:** Rule-modification synthetic benchmark — mutate the BC3 three-layer grammar at the JSON-intermediate level between pipeline stages, producing variants with full traceability metadata for robustness evaluation of retrieval methods.
**Do not modify existing files from `main`.** All new work lives in **new files** under `src/synthetic/`, `configs/synthetic/`, `data/synthetic/`, `docs/synthetic/`. The existing s01…s07 notebooks must keep running unchanged on the original BC3 input.

> ⚠ **Never merge `synthetic` back to `main`.** This branch is BC3CAT-Syn's permanent home — the research lives here in isolation by design. Never propose, suggest, perform, or accept a merge / fast-forward / rebase of `synthetic` (or any of its child branches) into `main`. If a pull request is opened from work on this branch, its base must be `synthetic` (or another sub-branch of it), never `main`. The original BC3CAT pipeline on `main` is the published artifact and must stay byte-identical regardless of what happens here.

---

## The Problem in One Paragraph

The original BC3CAT benchmark uses catalog-generated short descriptions (*resumen*) as queries against catalog-generated long descriptions (*texto*) — both produced from the same generation rules. This shared surface form favours lexical-overlap retrievers (BM25 with parameter-aware tokenization scores 97.4 % item-Acc@1) and under-stresses semantic methods. BC3CAT-Syn fixes this by mutating the BC3 grammar itself before re-running the pipeline, producing synthetic items whose `texto` is rewritten while preserving exact parametric meaning. Each synthetic item carries the list of atomic modifications applied (12 controlled types across 4 layers), enabling per-type and per-stack-depth degradation slices in downstream evaluation.

## Reference Documents

- [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md) — goals, motivation, modification taxonomy, expected contributions.
- [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) — implementation roadmap, design decisions, phased task backlog, file map.
- [`RESEARCH_LOG.md`](RESEARCH_LOG.md) — running record of decisions, results, and issues per sprint.
- `sprints/SPRINT_NN.md` — current sprint's objectives and acceptance criteria.

---

## Mutation Architecture

```
data/raw/BC3
   │
   ▼
[s01 parse]  →  [s02 split]
                    │
                    ▼
              stage-2 JSON  ──[L1 mutate]──┐
                    │                       │
                    │                  [PD mutate (new_param)]
                    │                       │
                    ▼                       │
              [s03 expand]  ◄───────────────┘
                    │
                    ▼
              stage-3 JSON  ──[L2 mutate]──►  [s04 vars]
                                                  │
                                                  ▼
                                          stage-4 JSON  ──[L3 mutate]──►  [s05 render]
                                                                                │
                                                                                ▼
                                                                          stage-5 JSON
                                                                                │
                                                                                ▼
                                                                       [s07 dedup] → [metadata join] → BC3CAT-Syn items
```

**Injection points** (see `RESEARCH_PROTOCOL.md §3.3` for the formal contract):

| Layer  | Code label         | Inject between | Mutates                                                                                      |
|:------:|--------------------|----------------|----------------------------------------------------------------------------------------------|
| **L1** | `param_value`      | s02 → s03      | `parameters[axis]["values"]` arrays (labels, numbers, units, abbreviations, codes)            |
| **L2** | `text_variable`    | s03 → s04      | `text_variables[var_key]` formula strings (paraphrase / expansion / compression of fragments) |
| **L3** | `template`         | s04 → s05      | `resumen` / `texto` template strings (omission, reordering)                                   |
| **PD** | `param_definition` | s02 → s03      | Adds a new axis + `$VAR` + template hook                                                      |

The 12 atomic modification types defined in the proposal are distributed across these four layers — see the taxonomy table in `RESEARCH_PROPOSAL.md §2.2`.

## Design Decisions

| Decision                              | Value                                                                       | Rationale                                                                  |
|---------------------------------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------|
| Injection level                       | **JSON-intermediate** between s02/s03/s04                                   | Skips re-parsing BC3; isolates one layer per atomic mutation               |
| Mutation atomicity                    | One layer × one target per atomic `Modification`                            | Per-type evaluation slices remain clean                                    |
| Multi-mod variants                    | Composed by stacking atomic mutations (L1 → L2 → L3 → PD)                    | Compositionality slices need explicit stack depth                          |
| Variant ID format                     | `{original_key}_syn_v{n}`                                                    | Preserves lexicographic parent grouping                                    |
| Variant catalog format                | JSON-per-concept under `data/synthetic/variants/`                            | Durable Stage-A artifact; decoupled from pipeline reruns                   |
| Stage-A locality (LLM proposer)       | Offline batch                                                                | Decouples expensive LLM calls from cheap pipeline reruns                   |
| LLM proposer model                    | **TBD** — chosen by spike in Task A3                                         | Quality of Spanish technical writing is the gating factor                  |
| Stage 2 temperature                   | 0.0                                                                          | Deterministic for reproducibility                                          |
| Manual review coverage                | 100 % for `new_param`; stratified for the other 11 types                    | Semantic-collision risk concentrated in `new_param`                        |
| Stratification axis                   | `(concept × modification_type)` crossed                                      | Per-cell statistical power for slice analyses                              |
| Path-hardcoding                       | Refactor `/work/data/raw/` → `src/utils/config.py` early (Task A4)           | Required to run pipeline from `data/synthetic/intermediate/`               |
| Pickle / cache invalidation           | Clear between runs; tracked in this file                                     | BM25/embedding caches assume stable corpus                                 |
| Unstackable-combo handling            | Skip + log                                                                   | Better to lose coverage than corrupt traceability                          |
| Release format                        | Parquet items + sidecar JSONL for `modifications`                            | Parquet stays flat; JSONL carries the nested mutation log                  |
| Scope                                 | Dataset-only — evaluation lives in `bc3cat-retrieval`                        | Avoids cross-repo coupling in this protocol                                |

## Stage-Hook Integration Note

Each layer mutator is a **pure function** over the stage-output JSON. Planned signature (see Task A5 → B*):

```python
from synthetic.taxonomy import Modification, ModificationType

def apply_l1(
    stage2_json: dict,           # parsed s02 output
    concept_key: str,            # e.g. "OEB020$"
    rules: list[dict],           # variant catalog entries for this variant
) -> tuple[dict, list[Modification]]:
    """Apply L1 (param_value) mutations to stage-2 JSON.

    Returns a new dict (does not mutate input) and the log of atomic
    Modification records actually applied. Unstackable combos are skipped
    and logged with `Modification(..., status="skipped", reason=...)`.
    """
```

`apply_l2`, `apply_l3`, `apply_new_param` follow the same shape on their respective stage JSONs.

The full orchestration (`src/synthetic/run_synthetic.py`, Task D2) reads a variant catalog, materialises mutated stage JSONs into `data/synthetic/intermediate/{concept}/`, reruns s03→s07, and emits raw synthetic items into `data/synthetic/processed/`.

## Data Structures

### Concept schema (extracted in early Phase A)

```json
{
  "OEB030$": {
    "concept": "CANALIZACIÓN CON TUBOS DE POLIETILENO...",
    "axes": {
      "TRABAJO": ["Diurno", "Nocturno"],
      "Nº TUBOS": ["1", "2", "3", "4"],
      "TIPO DE TERRENO": ["Sin clasificar", "Bajo vías", "Rocoso"]
    },
    "item_keys": ["OEB030aaa", "OEB030aab", "..."],
    "num_items": 6336
  }
}
```

25 concept groups total. Sizes range from 3 items (1 axis) to 6,336 items (5 axes).

### Parameters column shape (from `OEB_long_norm.parquet`)

```json
{
  "A": {"label": "TRABAJO",         "values": [{"label": "a", "value": "Diurno"}]},
  "B": {"label": "TIPO DE TERRENO", "values": [{"label": "a", "value": "Sin clasificar"}]},
  "...": "..."
}
```

For leaf items each axis's `values` list has exactly one element. The variant catalog mutates the parent-level definition before s03 expansion.

### `Modification` record (target schema for the synthetic items)

```json
{
  "item_key": "OEB020aaeaa_syn_v1",
  "original_key": "OEB020aaeaa",
  "params": {"A": "2", "B": "Normal", "...": "..."},
  "resumen": "Canalización dos T PVC 110, convencional.",
  "texto":   "Canalización de dos tubos PVC 110 mm en terreno estándar...",

  "variante_id": "v1",
  "modification_types": ["num_to_text", "synonym_label", "paraphrase", "compression"],
  "modification_count": 4,

  "modifications": [
    {"type": "num_to_text",   "layer": "param_value",
     "param": "A", "original": "2", "new": "dos"},
    {"type": "synonym_label", "layer": "param_value",
     "param": "B", "value": "a", "original": "Normal", "new": "Convencional"},
    {"type": "paraphrase",    "layer": "text_variable",
     "var": "$I", "condition": "%B=a",
     "original": "en cualquier clase de terreno, excepto roca",
     "new":      "terreno estándar"},
    {"type": "compression",   "layer": "template", "field": "RESUMEN"}
  ]
}
```

Full schema lives in `RESEARCH_PROPOSAL.md §6.1`.

---

## New Files in This Branch

Status legend: ✅ done · 🚧 in progress · ❌ not started.

```
docs/synthetic/
  RESEARCH_PROPOSAL.md                            ✅ Sprint 00
  RESEARCH_PROTOCOL.md                            ✅ Sprint 00
  CLAUDE_SYNTHETIC.md                             ✅ Sprint 00 — this file
  RESEARCH_LOG.md                                 ✅ Sprint 00
  sprints/                                        ❌ Sprint 00 — JIT
    SPRINT_00.md                                  ❌ Sprint 00 (scaffolding retro)
    SPRINT_NN.md                                  ❌ JIT — one per sprint
  DATA_CARD.md                                    ❌ Phase G — Data-in-Brief release card
  QUALITY_REPORT.md                               ❌ Phase F — pilot + full-validation quality report
  HANDOFF.md                                      ❌ Phase G — cross-repo memo to bc3cat-retrieval

src/synthetic/                                    🚧 Phase A–G
  __init__.py                                     ✅ Sprint 01
  taxonomy.py                                     ✅ Sprint 01 — Task A2 — 12-type enum + Modification dataclass
  mutator.py                                      ✅ Sprint 01 — Task A5 — apply_l1/l2/l3/new_param harness (stubs)
  layer_l1.py                                     ❌ Task B1 — param-value mutators
  layer_l2.py                                     ❌ Task B2 — text-variable mutators
  layer_l3.py                                     ❌ Task B3 — template mutators
  layer_pd.py                                     ❌ Task B4 — new_param mutator
  composition.py                                  ❌ Task B5 — stacking rules
  llm_proposer.py                                 ❌ Tasks C2–C3 — Ollama/API client + variant proposer
  prompts/                                        ❌ Task C1 — one Spanish prompt per type
    synonym_label.txt                             ❌
    num_to_text.txt                               ❌
    unit_conversion.txt                           ❌
    unit_expansion.txt                            ❌
    abbrev_expansion.txt                          ❌
    code_expansion.txt                            ❌
    paraphrase.txt                                ❌
    expansion.txt                                 ❌
    compression.txt                               ❌
    omission.txt                                  ❌
    reorder.txt                                   ❌
    new_param.txt                                 ❌
  metadata.py                                     ❌ Tasks E1–E2 — join + schema validator
  review.py                                       ❌ Tasks E3–E4 — sampler + reviewer harness
  run_synthetic.py                                ❌ Task D2 — orchestrator
  loaders.py                                      ❌ Task G2 — downstream loader utilities

configs/synthetic/                                ❌ Phase A–B
  variant_budgets.yaml                            ❌ Phase F — per-concept budgets
  new_param_allowlist.yaml                        ❌ Task B4 — admissible new axes
  composition_rules.yaml                          ❌ Task B5 — stacking constraints

data/synthetic/                                   ❌ Phases C–G
  variants/                                       ❌ Task C4 — variant catalog JSON-per-concept
  intermediate/                                   ❌ Task D2 — mutated stage JSONs
  processed/                                      ❌ Task G1 — release artifacts
    BC3CAT_Syn_items.parquet                      ❌
    BC3CAT_Syn_modifications.jsonl                ❌

Existing files extended in this branch (not new, but load-bearing for the synthetic engine):
  src/utils/config.py                            ✅ Sprint 02 — Task A4 part 1 — added `REPO_ROOT`, `DATA_ROOT`,
                                                              `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR`,
                                                              `LLAMAINDEX_DIR`, `SYNTHETIC_DATA_ROOT`,
                                                              `SYNTHETIC_INTERMEDIATE_DIR`, `SYNTHETIC_PROCESSED_DIR`,
                                                              `SYNTHETIC_VARIANTS_DIR`, `chapter_path()`, `stage_path()`,
                                                              and env-var overrides `BC3CAT_DATA_ROOT` /
                                                              `BC3CAT_SYNTHETIC_DATA_ROOT`. Legacy `Config` shim kept.
  src/s01_parse_fiebdc.ipynb                     ✅ Sprint 02 — Task A4 part 1 — `os.chdir('/work/...')` → `config.RAW_DIR`
                                                              / `config.DATA_ROOT`; `from utils import config` added.
  src/s02_split_chapters.ipynb                   ✅ Sprint 03 — Task A4 part 2 — `/work/...` literal → `config.INTERMEDIATE_DIR`;
                                                              `from utils import config` added (cell 2).
  src/s03_generate_parametric_combinations.ipynb ✅ Sprint 03 — Task A4 part 2 — `/work/...` literal → `config.chapter_path("OBRA CIVIL")`;
                                                              `from utils import config` added (cell 2).
  src/s04_evaluate_text_variables.ipynb          ✅ Sprint 03 — Task A4 part 2 — `/work/...` literal → `config.chapter_path("OBRA CIVIL")`;
                                                              `from utils import config` added (cell 3).
  src/s05_evaluate_resumen_texto.ipynb           ✅ Sprint 03 — Task A4 part 2 — `/work/...` literal → `config.chapter_path("OBRA CIVIL")`;
                                                              `from utils import config` added (cell 3).
  src/s06_data_analysis.ipynb                    ✅ Sprint 03 — Task A4 part 2 — `/work/...` literal → `config.stage_path("OBRA CIVIL", 5)`;
                                                              `from utils import config` added (cell 2).
  src/s07_Filter_duplicates.ipynb                ✅ Sprint 03 — Task A4 part 2 — 9 site rewrites across cells 2/3/8/11 →
                                                              `config.stage_path(...)` / `config.INTERMEDIATE_DIR / chapter / f"..."`;
                                                              two `project_root = Path('/work'); sys.path.append(...)` bootstraps deleted from cells 3 + 8;
                                                              `from utils import config` added to each touched cell.
  src/s08_Llamaindex_Doc_Creation.ipynb          ✅ Sprint 04 — Task A4 part 3 — 3 `/work/data/...` literals → `config.stage_path(file, 7)` +
                                                              `config.PROCESSED_DIR / f"{file}_{texto,resumen}.pkl"`;
                                                              `from utils import config` added (cell 2).
  src/Generate_OEB_dataset.ipynb                 ✅ Sprint 04 — Task A4 part 3 — 4 path-literal rewrites (cells 3/4/8 + cell 2 bootstrap retarget) +
                                                              1 stale-comment deletion. `Path('/work')` → `config.REPO_ROOT`;
                                                              `'/work/data/processed/...' → config.PROCESSED_DIR / "..."`; cell 4 collapsed to bare
                                                              relative `"OEB_texto.pkl"`. `sys.path.append(...)` + `from src.utils.data_utils import load_documents`
                                                              kept intact (repo-rooted import chain — Sprint 05 / 04.5 follow-up).
```

Cross-check: every ❌ above corresponds to an unbuilt component listed in [`RESEARCH_PROTOCOL.md §3.5`](RESEARCH_PROTOCOL.md).

---

## Generation Conditions

| Condition            | Layers mutated         | Stack depth   | Purpose                                              |
|----------------------|------------------------|---------------|------------------------------------------------------|
| `single_L1_*`        | one of the L1 types    | 1             | Per-type isolation slices for `param_value`          |
| `single_L2_*`        | one of the L2 types    | 1             | Per-type isolation slices for `text_variable`        |
| `single_L3_*`        | one of the L3 types    | 1             | Per-type isolation slices for `template`             |
| `new_param_only`     | param_definition       | 1             | Stress new-axis introduction in isolation            |
| `stacked_2` … `5+`   | mixed                  | 2, 3, 4, ≥5   | Compositionality slices                              |
| `full_random_mix`    | all                    | sampled       | Headline robustness slice                            |

**Diagnostic interpretation** (handed off to `bc3cat-retrieval`):

- `single_*` baselines isolate per-type degradation per retriever family.
- `stacked_*` curves quantify whether degradation is sub-/linear/super-linear in mutation count.
- A retriever that fails `single_L1_synonym_label` but survives `single_L2_paraphrase` (or vice-versa) localises its weakness to the lexical-vs-semantic axis.

---

## Sprint History

*Newest entries at the top. New entries follow the template: title, date, what changed (bullets), key results (table or bullets), known issues.*

### After Sprint 04 — Path refactor: s08 + `Generate_OEB_dataset` notebook migration
**Date:** 2026-05-19
**What changed:**
- Migrated [`src/s08_Llamaindex_Doc_Creation.ipynb`](../../src/s08_Llamaindex_Doc_Creation.ipynb) cell 2: 3 `Path('/work/data/...')` literals inside `main(file)` rewritten to `config.stage_path(file, 7)` and `config.PROCESSED_DIR / f"{file}_{texto,resumen}.pkl"`; `from utils import config` added beside `from llama_index.core import Document`.
- Migrated [`src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb) across cells 2, 3, 4, 8 in one `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle: cell 2 bootstrap retargeted (`Path('/work')` → `config.REPO_ROOT`) and two-line stale `# Assuming … /work` comment block deleted, with `sys.path.append(str(project_root))` and `from src.utils.data_utils import load_documents` deliberately preserved; cells 3/8 pickle-path literals → `config.PROCESSED_DIR / "..."`; cell 4 collapsed from `'/work/src/OEB_texto.pkl'` to bare relative `"OEB_texto.pkl"` (symmetric with cell 3's save side). `from utils import config` added once in cell 2 — cells 3/4/8 inherit transitively.
- Extended [`tests/utils/test_notebooks_no_work_literal.py`](../../tests/utils/test_notebooks_no_work_literal.py): `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb` appended to the `NOTEBOOKS` list, and the substring check widened from `"/work/"` to bare `"/work"` so the `Path('/work')` bootstrap shape is also caught. Docstring updated to match. The widened gate stays green on s01–s07.

**Key results:**
- `pytest tests -q` → **51 passed in 0.08s** (49 from Sprint 03 + 2 new notebook-guard cases). No regressions.
- Both smoke checks pass: all 9 pipeline notebooks (s01–s08 + `Generate_OEB_dataset`) parse via `json.load`; `source-cell /work hits across s01-s08 + Generate_OEB: 0`.
- `git diff --numstat`: s08 +4/−3 (cell 2 only), `Generate_OEB_dataset` +5/−6 (cells 2/3/4/8 only), test file ~+5/−5. End-of-sprint `git status --short` matches the sprint plan's expected file list exactly.

**Decisions confirmed:**
- **Generate_OEB cell 2 bootstrap retargeted, not deleted.** `sys.path.append(str(project_root))` stays because the next line `from src.utils.data_utils import load_documents` is a *repo-rooted* import requiring `REPO_ROOT` (not `src/`) on `sys.path`. Only the literal swaps (`Path('/work')` → `config.REPO_ROOT`). Cleaning up the import shape inside [`src/utils/data_utils.py`](../../src/utils/data_utils.py), [`src/utils/index_classes.py`](../../src/utils/index_classes.py), and [`src/utils/evaluation.py`](../../src/utils/evaluation.py) — swapping `from src.utils.X` → relative `from .X` so the bootstrap can finally retire — is a Sprint 05 (or "Sprint 04.5") candidate. Requires a cross-repo coupling check against `bc3cat-retrieval` before merging.
- **Cell 4 collapsed to bare relative `"OEB_texto.pkl"`.** Symmetric with cell 3's save side, which already writes the file as a bare relative path resolved against the notebook cwd of `src/`. No `config.SRC_DIR` helper introduced — YAGNI for two callers in one notebook.
- **Single `from utils import config` per notebook in the shared imports cell.** Cells 3/4/8 of `Generate_OEB_dataset` inherit transitively via notebook globals. Sprinkling per-cell imports would clutter the diff with no behavioural change.
- **Regression-guard literal widened from `/work/` to `/work`.** Catches the `Path('/work')` bootstrap shape (no trailing slash) while staying green on s01–s07 — verified by hand and by the parametrised test (9 passed). Net effect: one stricter regression-prevention rule, zero false positives.
- **LF line endings preserved** via `Path.write_bytes(...)` per the Sprint 03 recipe.

**Known issues:**
- The `Generate_OEB_dataset.ipynb` cell 2 bootstrap is the last in-repo `sys.path.append(...)` shim. It cannot retire until [`src/utils/data_utils.py`](../../src/utils/data_utils.py), [`src/utils/index_classes.py`](../../src/utils/index_classes.py), and [`src/utils/evaluation.py`](../../src/utils/evaluation.py) switch from absolute `from src.utils.X` to relative `from .X` imports. Tracked as the Sprint 05 / 04.5 candidate above.
- End-to-end behaviour-preserving validation across the full main pipeline (s01 → s08 → `Generate_OEB_dataset`, byte-diff against in-repo `OEB_*.parquet` / `*.pkl`) still pending — requires a Docker / `pandas` / `llama_index` env. Static-check gate only across Sprints 02–04.
- The atexit `cleanup_dead_symlinks` PermissionError on Windows after pytest exits is unchanged from Sprints 02 + 03 (51 passed prints before the traceback). Cosmetic; no action.

**Next step:** Either the import-shape cleanup (Sprint 05 / 04.5 candidate above) — lower-risk, lands the path refactor's final cleanup and unblocks the Generate_OEB cell 2 bootstrap deletion — or the end-to-end-validation sprint that reruns the full main pipeline against `data/intermediate/...` and byte-diffs `data/processed/OEB_*.parquet` / `*.pkl` against the in-repo originals. Recommendation: do the import-shape cleanup first.

### After Sprint 03 — Path refactor: s02–s07 notebook migration
**Date:** 2026-05-19
**What changed:**
- Fanned the Sprint 02 migration pattern across the six remaining synthetic-critical-path notebooks: [`s02_split_chapters.ipynb`](../../src/s02_split_chapters.ipynb), [`s03_generate_parametric_combinations.ipynb`](../../src/s03_generate_parametric_combinations.ipynb), [`s04_evaluate_text_variables.ipynb`](../../src/s04_evaluate_text_variables.ipynb), [`s05_evaluate_resumen_texto.ipynb`](../../src/s05_evaluate_resumen_texto.ipynb), [`s06_data_analysis.ipynb`](../../src/s06_data_analysis.ipynb), [`s07_Filter_duplicates.ipynb`](../../src/s07_Filter_duplicates.ipynb). 14 hardcoded `/work/...` source-cell literals were rewritten to route through `config.INTERMEDIATE_DIR`, `config.chapter_path(...)`, or `config.stage_path(...)`. s07's three `_duplicate_*.json` side-artifacts inline as `config.INTERMEDIATE_DIR / chapter / f"{chapter}_..."` per the YAGNI decision noted below.
- Removed the two `project_root = Path('/work'); sys.path.append(str(project_root))` bootstrap pairs from `s07_Filter_duplicates.ipynb` cells 3 and 8 — −4 dead-code lines. They were redundant once the cells gain `from utils import config` and Jupyter's per-notebook kernel cwd is `src/` (Sprint 02 finding).
- Added [`tests/utils/test_notebooks_no_work_literal.py`](../../tests/utils/test_notebooks_no_work_literal.py) — a parametrised regression guard scanning the `source` arrays of all seven s01–s07 notebooks for `/work/` literals. Sprint 04 extends the notebook list to include `s08_Llamaindex_Doc_Creation.ipynb` + `Generate_OEB_dataset.ipynb`.

**Key results:**
- `pytest tests -q` → **49 passed in 0.07s** (Sprint 01's 30 + Sprint 02's 12 + 7 new notebook-guard cases). No regressions.
- Both Sprint-03 smoke checks pass: all 7 notebooks parse via `json.load`; `source-cell /work/ hits across s01-s07: 0`.
- `git diff --numstat`: s02 +3/−1, s03 +3/−1, s04 +3/−1, s05 +3/−1, s06 +3/−1, s07 +14/−13. End-of-sprint `git status --short` matches the sprint plan's expected file list exactly — six modified notebooks + the new test file + this file + `RESEARCH_LOG.md` + the already-untracked `SPRINT_03.md`.

**Decisions confirmed:**
- **Path objects passed bare** to the user functions inside the notebook cells (`marcar_duplicados(path_entrada=config.stage_path(...))`, `main(config.chapter_path(...))`). No `str(...)` wrapping. Mirrors Sprint 02's `os.chdir(config.RAW_DIR)` pattern; the runtime-behaviour gate is the future end-to-end-validation sprint after Sprint 04.
- **Side-artifact paths inlined, not helper-promoted.** s07's three `_duplicate_*.json` and one `_either_duplicate.json` artifacts use the literal `config.INTERMEDIATE_DIR / chapter / f"..."` shape — no new helper added to `config.py`. YAGNI: three callers in one cell. Sprint 04+ can promote a `chapter_artifact(chapter, suffix)` helper if a third site for this pattern surfaces (e.g. inside the LlamaIndex notebook's pickle path).
- **Single load/edit/write cycle per notebook.** For s07 (9 sites across 4 cells), the helper applied all edits in one `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle to keep pretty-printing stable across cells. Migration script was authored under `scripts/sprint03_migrate_notebooks.py` for traceability and removed after the patch landed cleanly — the durable artifact is the regression test, not the helper.
- **LF line endings preserved on Windows.** Notebooks written via `Path.write_bytes(text.encode("utf-8") + b"\n")` to bypass Python's text-mode newline translation. git's `core.autocrlf` produces a soft "LF will be replaced by CRLF" warning on each touched file, but the in-repo bytes are LF — matching the existing convention for s02–s07.

**Known issues:**
- s08 + `Generate_OEB_dataset` still hardcode `/work/...` (5 + 3 source-cell hits respectively). They are off the synthetic critical path (they only emit the final main-pipeline artifacts: the LlamaIndex pickle and the OEB Parquet release). Their migration is Sprint 04, A4 part 3.
- The atexit `cleanup_dead_symlinks` PermissionError on Windows after pytest exits is unchanged from Sprint 02 (49 passed prints before the traceback). Cosmetic; no action.

**Next step:** Draft `sprints/SPRINT_04.md` for A4 part 3 — fan the same migration pattern across `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb`, and extend the notebook-guard test's `NOTEBOOKS` list to cover them. After Sprint 04 lands, the natural follow-up is the end-to-end-validation sprint: rerun s01 → s07 against the existing `data/intermediate/...` and byte-diff the outputs against the in-repo `OEB_*.parquet` to confirm the refactor is behaviour-preserving.

### After Sprint 02 — Path refactor: config core + s01 migration
**Date:** 2026-05-19
**What changed:**
- Rewrote [`src/utils/config.py`](../../src/utils/config.py) into the single-source-of-truth paths module: `REPO_ROOT`, `DATA_ROOT`, `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR`, `LLAMAINDEX_DIR`, plus the synthetic sub-tree `SYNTHETIC_DATA_ROOT` / `SYNTHETIC_INTERMEDIATE_DIR` / `SYNTHETIC_PROCESSED_DIR` / `SYNTHETIC_VARIANTS_DIR`, plus the helpers `chapter_path(chapter, *, root=INTERMEDIATE_DIR)` and `stage_path(chapter, stage_n, *, root=INTERMEDIATE_DIR)`. Env-var overrides `BC3CAT_DATA_ROOT` and `BC3CAT_SYNTHETIC_DATA_ROOT` are read at import time. Legacy `Config` shim preserved — its `DATA_DIR` / `TEXTO_PATH` / `RESUMEN_PATH` now route through `LLAMAINDEX_DIR`, removing the `/work/data/llamaindex` literal without touching `Config`'s public surface.
- Refactored [`src/s01_parse_fiebdc.ipynb`](../../src/s01_parse_fiebdc.ipynb): two `os.chdir('/work/...')` sites swapped for `os.chdir(config.RAW_DIR)` / `os.chdir(config.DATA_ROOT)`; `from utils import config` added in cell 1. Diff scope: +4 / −2.
- Added [`tests/utils/`](../../tests/utils) with `conftest.py` and `test_config.py` (12 tests covering the eight Task-1 acceptance bullets, including env-var overrides with `monkeypatch.setenv` + `importlib.reload`).

**Key results:**
- `pytest tests -q` → 42 passed in 0.08s (Sprint 01's 30 + Sprint 02's 12). No regressions.
- All four smoke checks from `sprints/SPRINT_02.md`'s verification runbook pass.
- `Grep '/work/' src/utils/config.py` returns zero hits. Cell-source `/work/` audit on `s01_parse_fiebdc.ipynb` returns zero hits.

**Decisions confirmed:**
- Env-var names locked: `BC3CAT_DATA_ROOT` and `BC3CAT_SYNTHETIC_DATA_ROOT`. Sprint 03+ will consume these unchanged.
- Notebook bootstrap: minimal `from utils import config` — Jupyter's per-notebook kernel cwd is `src/` both in Docker (`/work/src`) and on the Windows host, so `utils` resolves without a `sys.path` bootstrap. Sprint 03's downstream-notebook fan-out reuses this pattern.
- Notebook editing: `Edit` refuses `.ipynb`; full-cell `NotebookEdit` would balloon the diff for the 300-line parser cell. Pattern adopted: byte-precise string replacements on cell `source` arrays via a `json.load` → patch → `json.dumps(..., indent=1)` script, preserving the existing JSON indent style and keeping the diff to the two target lines.

**Known issues:**
- s02–s07 (and s08, `Generate_OEB_dataset`) still hardcode `/work/...`. A4 part 2 is Sprint 03's focus (s03–s07 are the synthetic critical path); s08 + `Generate_OEB_dataset` deferred to Sprint 04.
- `nbformat` not installed on this host's system Python — substituted `json.load(...)` for the JSON-well-formedness smoke check. Equivalent signal; no action needed.

**Next step:** Draft `sprints/SPRINT_03.md` for A4 part 2 — fan the s01 migration pattern across `s02_split_chapters.ipynb` → `s07_Filter_duplicates.ipynb`.

### After Sprint 01 — Taxonomy module + injection harness skeleton
**Date:** 2026-05-19
**What changed:**
- Created [`src/synthetic/__init__.py`](../../src/synthetic/__init__.py), [`src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py), [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py).
- `taxonomy.py` exports `Layer` (4), `ModificationType` (12), `TYPE_TO_LAYER`, and `Modification` (frozen dataclass with `to_dict()` / `from_dict()`).
- `mutator.py` exposes `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param`. Internal `_DISPATCH` registers 12 named stubs; each raises `NotImplementedError("Phase B: <type_code> mutator not yet implemented")`. Wrong-layer and unknown-type rules raise `ValueError`. All four entry points `copy.deepcopy` their input before any mutation, so the caller's dict stays byte-identical even when a stub raises.
- Added the test suite under [`tests/synthetic/`](../../tests/synthetic) — `conftest.py` + `test_taxonomy.py` + `test_mutator.py`.

**Key results:**
- `pytest tests/synthetic -q` → 30 passed in 0.10s.
- All three verification-runbook smoke checks pass (taxonomy invariants, four signature checks, `_DISPATCH` shape).

**Decisions confirmed:**
- `to_dict()` omits `None` fields (cleaner JSON; round-trips via `from_dict()` defaulting).
- 12 stubs spelled out explicitly rather than factory-generated — Phase B will physically relocate them to `layer_l1.py` / `_l2.py` / `_l3.py` / `_pd.py` and re-register through the same dispatcher, so named functions make that move mechanical.

**Known issues:**
- All 12 mutator bodies are still stubs. Real bodies land in Phase B (B1–B4).
- `s01_parse_fiebdc.ipynb` still hardcodes `/work/data/raw/`. Path refactor (A4) is the next sprint.

**Next step:** Draft `sprints/SPRINT_02.md` for Task A4 — un-hardcode `/work/data/raw/` in `s01_parse_fiebdc.ipynb` and route through [`src/utils/config.py`](../../src/utils/config.py).

### After Sprint 00 — Documentation scaffolding
**Date:** 2026-05-19
**What changed:**
- Created [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md) — SEPLN-style proposal mirroring the structure of `bc3cat-retrieval/docs/RESEARCH_PROPOSAL.md`.
- Created [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) — implementation roadmap mirroring `bc3cat-retrieval/docs/RESEARCH_PROTOCOL.md`.
- Created the repo-level [`CLAUDE.md`](../../CLAUDE.md) at the dataset repo root with a branch note pointing here.
- Created this file (`CLAUDE_SYNTHETIC.md`) and [`RESEARCH_LOG.md`](RESEARCH_LOG.md).

**Decisions confirmed with user:**
- Injection level: **JSON-intermediate** (between s02/s03/s04), not raw BC3.
- Scope: **dataset-only** — retrieval evaluation lives in `bc3cat-retrieval`.

**Known issues:**
- No code yet. Source-side `src/synthetic/` is untouched.
- `s01_parse_fiebdc.ipynb` still hardcodes `/work/data/raw/`. Task A4 in the protocol unblocks running the pipeline from an alternate data root.

**Next step:** Draft `sprints/SPRINT_01.md` for Phase A (taxonomy module, path refactor, three-layer injection harness — Tasks A2 + A4 + A5).
