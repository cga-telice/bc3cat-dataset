# BC3CAT-Syn — Branch Context for Claude Code

**Branch:** `synthetic`
**Goal:** Rule-modification synthetic benchmark — mutate the BC3 three-layer grammar at the JSON-intermediate level between pipeline stages, producing variants with full traceability metadata for robustness evaluation of retrieval methods.
**Do not modify existing files from `main`.** All new work lives in **new files** under `src/synthetic/`, `configs/synthetic/`, `data/synthetic/`, `docs/synthetic/`. The existing s01…s07 notebooks must keep running unchanged on the original BC3 input.

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

src/synthetic/                                    ❌ Phase A–G
  __init__.py                                     ❌ Phase A
  taxonomy.py                                     ❌ Task A2 — 12-type enum + Modification dataclass
  mutator.py                                      ❌ Task A5 — apply_l1/l2/l3/new_param harness
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

Top-level scaffolding (depends on existing pipeline):
  Path refactor in s01 + downstream notebooks    ❌ Task A4 — un-hardcode `/work/data/raw/`
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
