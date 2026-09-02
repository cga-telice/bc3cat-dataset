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

`apply_l2`, `apply_l3`, `apply_new_param` follow the same shape.

**One parent-level injection, not four (corrected Sprint 18).** Earlier drafts framed Stage B as four *interleaved* injection points ("PD/L1 before s03, L2 before s04, L3 before s05"). The mutator implementations contradict that: **all four families index the same concept-keyed stage-2 record** (`stage_json[concept_key][…]`). None can consume a `run_stage3+` output — after s03 the dict is leaf-keyed (no `concept_key`), by s04 the `text_variables` are resolved `{evaluated: …}` dicts (no raw `"frag"*(cond)` for L2), and by s05 the `resumen`/`texto` are instantiated (no `$`-tokens for L3). The `layer_l2`/`layer_l3` docstrings' "stage-3/stage-4 JSON" labels name *the stage whose content the mutation conceptually targets*, **not** the dict shape consumed — that shape is the stage-2 concept record in every case. So:

> **Stage B applies PD → L1 → L2 → L3 to the single-concept stage-2 record (in the composed order Stage A pinned), then calls `run_stages_3_to_7` once.** No interleaving. Every mutation is a syntactic edit to the pre-expansion definition; because `transform_data` copies `text_variables`/`resumen`/`texto` identically to every leaf, mutating the parent and re-expanding is equivalent to (and cheaper than) mutating leaves post-expansion.

Stage A and Stage B live in **separate modules**: `run_synthetic.py` composes + catalogs (mutator-free; a test asserts it never imports `mutator`); `stage_b.py` (Task D2) applies + reruns. `run_stage_b` reads each `VariantCatalogEntry` from `data/synthetic/variants/`, materialises every variant, and writes one raw-item JSON per variant to `data/synthetic/intermediate/{concept}/{variant_id}.json`. Joining those into the flat Parquet/JSONL release schema is Phase E (`metadata.py`). Synthetic dedup is **per-variant** (each variant's own leaves only); the faithful-rerun equivalence gate is at **stage-5 granularity** (pre-dedup, per-item independent), not stage-7.

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

Full schema lives in `RESEARCH_PROPOSAL.md §6.1`. As of Sprint 19 this record
is produced by [`src/synthetic/metadata.py`](../../src/synthetic/metadata.py)
(`SyntheticItem.to_dict()`), which joins the variant-grained Stage-B payloads
into one flat record per item.

**Per-item join-key triple `(item_key, original_key, variante_id)`** (Sprint 19):
- `item_key = f"{leaf_key}_syn_{variante_id}"` — the *mutated* leaf key keeps
  `new_param` siblings that share an `original_key` globally unique.
- `original_key = leaf_key[:-K]`, where `K` = count of *applied*
  (`status != "skipped"`) `new_param` modifications in the variant. Each applied
  `new_param` appends one axis last, contributing exactly one trailing label
  char to the leaf key. Non-PD variants: `K = 0`, so `original_key == leaf_key`.
- `variante_id` = Stage B's `variant_id` verbatim (`{condition}_{sha1[:10]}`).
- `modification_count` / `modification_types` are **recomputed** by the join
  from the applied `modifications` log, never trusted from the payload's copies.

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
  DATA_CARD.md                                    ✅ Sprint 23 (G3) — Data-in-Brief release card (stats TBD pending F3)
  QUALITY_REPORT.md                               ❌ Phase F — pilot + full-validation quality report
  HANDOFF.md                                      ✅ Sprint 23 (G4) — cross-repo memo to bc3cat-retrieval

src/synthetic/                                    🚧 Phase A–G
  __init__.py                                     ✅ Sprint 01
  taxonomy.py                                     ✅ Sprint 01 — Task A2 — 12-type enum + Modification dataclass
  mutator.py                                      ✅ Sprint 01 — Task A5 — apply_l1/l2/l3/new_param harness (stubs)
  layer_l1.py                                     ✅ Sprint 07 — Task B1 — apply_synonym_label / num_to_text / unit_conversion / unit_expansion / abbrev_expansion / code_expansion bodies; `_replace_value` shared worker; 6 stubs removed from `mutator.py`.
  layer_l2.py                                     ✅ Sprint 08 — Task B2 — apply_paraphrase / apply_expansion / apply_compression bodies; `_replace_fragment` shared worker; 3 stubs removed from `mutator.py`; condition-addressed rule schema with `$`-strip and whitespace-normalized matching; lookup-table-list entries raise `ValueError`.
  layer_l3.py                                     ✅ Sprint 09 — Task B3 — apply_omission / apply_reorder bodies; `_replace_substring` shared worker; 2 stubs removed from `mutator.py`; substring-addressed rule schema with `field`-case-normalisation and uniqueness-by-substring enforcement.
  layer_pd.py                                     ✅ Sprint 10 — Task B4 — apply_new_param body; cross-block edits (parameters + text_variables + template_patches) in one rule; param/var collision raises `ValueError`; template patches reuse L3 uniqueness-by-substring contract; `text_variables` block auto-created when absent; last stub removed from `mutator.py`.
  composition.py                                  ✅ Sprint 11 — Task B5 — `compose_rules` pre-apply validator; `COMPATIBILITY_MATRIX` Python constant (starter matrix: six `(NEW_PARAM, L1-type)` `LAYER_DEPENDENCY` entries); PD→L1→L2→L3 apply order; canonical-key dedup with L2-`$`-strip / whitespace-norm and L3-field-case symmetry; no `configs/synthetic/composition_rules.yaml` (matrix is the Python constant; YAML deferred).
  llm_proposer.py                                 ✅ Sprint 13 — Task C2 — `LLMClient` Protocol + `ProposalResult` (frozen dataclass) + `propose()` with structured-JSON parse, one-shot retry on malformed output, and `Modification(status="skipped", reason="malformed_llm_response_after_retry: …")` fallback. Concrete transport (Ollama / Anthropic / OpenAI / …) deferred to A3.
  variant_proposer.py                             ✅ Sprint 14 — Task C3 — `propose_variant` + per-type schema validation + JSON-aware template renderer (`EXPECTED_SLOTS` constant; pre-escape + selective un-escape of declared placeholders); `VariantProposal` frozen dataclass with two distinguishable skip-reason prefixes (`malformed_llm_response_after_retry: ` from C2, `schema_validation_failed: ` from C3). Slot-extraction (stage-JSON → slots dict) and payload-to-Phase-B-rule emission deferred to Sprint 15.
  slot_extractor.py                               ✅ Sprint 15 — Task C4-prep — `enumerate_targets(stage_json, concept_key, mtype)` + `extract_slots(stage_json, concept_key, mtype, target_id)` + `concept_resumen` helper. Per-type semantics: L1 axis key / L2 `(var_key, condition)` / L3-omission `(field, var_token)` / L3-reorder field / PD single `None`. Slot keys match `variant_proposer.EXPECTED_SLOTS` exactly (binding round-trip pinned by test). Narrow `_parse_l2_formula` regex (no import from `z_formula_processing.py`).
  rule_emitter.py                                 ✅ Sprint 15 — Task C4-prep — `emit_rules(payload, mtype, *, target_id, stage_json, concept_key) -> EmissionResult(rules, unmatched)` per-type dispatch lifting validated LLM payloads into Phase-B `layer_*.apply_*` rule dicts. L1 cross-references `entry["original"]` against the target axis's `value` field, dropping typos into `unmatched`. PD `new_param` allocates the first free axis letter A-Z; `var_definition`/`template_patch` ride as raw `metadata.*` strings (full parse deferred to Sprint 16).
  variant_catalog.py                              ✅ Sprint 15 — Task C4 — `VariantCatalogEntry` + `VariantRecord` + `ProvenanceRecord` frozen dataclasses; `write_catalog_entry(entry, out_dir) -> Path` (atomic `.tmp` + `os.replace` write; creates `out_dir` on-demand); `read_catalog_entry(path) -> VariantCatalogEntry` (strict JSON load + `Modification.from_dict` rebuild). Round-trip-safe.
  prompts/                                        ✅ Sprint 12 — Task C1 — Spanish prompt library (12 templates + loader); `load_prompt(modification_type)` returns the raw UTF-8 text verbatim, placeholder substitution deferred to C3; `PROMPT_DIR = Path(__file__).parent`; `PROMPT_FILENAMES` is auto-computed from `ModificationType` so the dict stays in sync with the enum.
    __init__.py                                   ✅ Sprint 12 — Task C1 — `load_prompt` + `PROMPT_DIR` + `PROMPT_FILENAMES` loader surface; explicit `isinstance(..., ModificationType)` guard rejects bare-string inputs (the `(str, Enum)` mixin would otherwise let `"synonym_label"` succeed by string-equality).
    synonym_label.txt                             ✅ Sprint 12 — Task C1 — Spanish prompt for `synonym_label` (verbatim from proposal §8.1)
    num_to_text.txt                               ✅ Sprint 12 — Task C1 — Spanish prompt for `num_to_text` (authored in proposal-§8 pattern)
    unit_conversion.txt                           ✅ Sprint 12 — Task C1 — Spanish prompt for `unit_conversion` (authored in proposal-§8 pattern)
    unit_expansion.txt                            ✅ Sprint 12 — Task C1 — Spanish prompt for `unit_expansion` (authored in proposal-§8 pattern)
    abbrev_expansion.txt                          ✅ Sprint 12 — Task C1 — Spanish prompt for `abbrev_expansion` (authored in proposal-§8 pattern)
    code_expansion.txt                            ✅ Sprint 12 — Task C1 — Spanish prompt for `code_expansion` (authored in proposal-§8 pattern)
    paraphrase.txt                                ✅ Sprint 12 — Task C1 — Spanish prompt for `paraphrase` (verbatim from proposal §8.2)
    expansion.txt                                 ✅ Sprint 12 — Task C1 — Spanish prompt for `expansion` (authored in proposal-§8 pattern)
    compression.txt                               ✅ Sprint 12 — Task C1 — Spanish prompt for `compression` (authored in proposal-§8 pattern)
    omission.txt                                  ✅ Sprint 12 — Task C1 — Spanish prompt for `omission` (verbatim from proposal §8.3)
    reorder.txt                                   ✅ Sprint 12 — Task C1 — Spanish prompt for `reorder` (authored in proposal-§8 pattern)
    new_param.txt                                 ✅ Sprint 12 — Task C1 — Spanish prompt for `new_param` (verbatim from proposal §8.4; `{allowlist}` slot left unfilled — C3 / Phase B4 binds it).
  metadata.py                                     ✅ Sprint 19 — Tasks E1–E2 — `SyntheticItem` + `to_dict` (proposal §2.3 shape) + `join_variant_payload/file/intermediate` (variant-grained → item-grained join; `original_key = leaf_key[:-K]`; recompute count/types) + `validate_item/items` + `SchemaError` (fail-loud). Stdlib + `taxonomy` + `utils.config` only; imports neither `stage_b` nor `run_synthetic`. Parquet/JSONL is G1.
  review.py                                       ✅ Sprint 20 — Tasks E3–E4 — `stratify` ((concept_key, ModificationType) cells; baselines excluded; stacked → multi-cell) + `sample_review_queue` (floor/fraction `min(size,max(floor,ceil(coverage·size)))`; 100 %-`new_param`; seeded-deterministic; de-dup by `item_key`) + `CoverageReport` + queue JSONL (`write_queue`/`read_queue`, atomic) + `Verdict`/`write_verdicts`/`read_verdicts` (fail-loud duplicate `(item_key,reviewer)`) + `agreement` (percent + Cohen's κ over ≥2-reviewer subset; `axis_distinguishable` over `new_param` only) + `ReviewError` + `main` (build/agree CLI). Stdlib + `metadata` + `taxonomy` + `utils.config` only; never `stage_b`/`run_synthetic`/`stage_runners`. Coverage defaults `coverage=0.10, floor=5`. Running a real review pass + `QUALITY_REPORT.md` is F4; Parquet is G1.
  run_synthetic.py                                ✅ Sprint 16 — Task D2 (Stage-A half) — concept-loop driver + `CONDITION_SPECS` condition matrix + deterministic seeded planner; populates the variant catalog. Rule application (`mutator.apply_*`) + pipeline rerun (s03→s07) deferred to Sprint 18 (now gated only on the D1 stage hooks, shipped Sprint 17).
  stage_runners.py                                ✅ Sprint 17 — Task D1 — in-memory pure stage runners (`run_stage3/4/5/7` + `run_stages_3_to_7`) extracted from the s03/s04/s05/s07 notebooks; the notebooks now import their core from here. Rule injection + the Stage-B rerun are Sprint 18.
  stage_b.py                                      ✅ Sprint 18 — Task D2 (Stage-B half) — `apply_variant_rules` (single parent-level injection PD→L1→L2→L3, skip-and-log per rule) + `materialize_variant` (slice → apply → `run_stages_3_to_7` → `MaterializedVariant`) + `materialize_catalog_entry` / `run_stage_b` (per-variant atomic JSON writes under `data/synthetic/intermediate/{concept}/`). Imports `mutator`/`stage_runners`/`variant_catalog`, NOT `run_synthetic` (Stage-A/Stage-B seam guard). **Sprint 27 (F1-build):** `materialize_variant`/`materialize_catalog_entry` gained `pre_rerun: Callable[[dict],dict] = _identity`, applied to the mutated concept before the rerun (default identity → byte-identical for existing callers); `f1_pilot` passes `l2_repr.formula_to_list` so `LIST_plain` text-variables mutated in formula form are restored to positional lists for s05.
  cache_hygiene.py                                ✅ Sprint 18 — Task D3 — `stale_cache_paths` (pure enumeration: `processed/*.pkl`, `llamaindex/` contents, stray `chunk_*.json`, `**/.ipynb_checkpoints`) + `clear_caches` (dry-run default; deletion opt-in, tested only against `tmp_path`).
  packaging.py                                    ✅ Sprint 21 — Task G1 — release packager: `ITEM_COLUMNS` (frozen §2.3-record + `concept_key`; **no** `parent_key`, **no** `_feats`, **no** `modifications`) + `items_to_frame` (validate→sorted rows→frozen columns; `params` nested, `modification_types` list) + `modifications_sidecar` (one line per `item_key`; baseline→`[]`) + `write_items_parquet`/`write_modifications_jsonl` (atomic `.tmp` rename; sidecar fail-loud dup key) + `write_release` (validate-first; both files under `SYNTHETIC_PROCESSED_DIR`) + `read_items_parquet`/`read_modifications_jsonl` (minimal round-trip; full loader is G2) + `PackagingError` + `main` (build CLI). Imports `metadata`/`taxonomy`/`utils.config` + lazy `pandas`/`pyarrow` + stdlib only; never `stage_b`/`run_synthetic`/`stage_runners`/`review`. Packages `join_intermediate()` output — does NOT generate.
  llm_client.py                                   ✅ Sprint 24 — Task A3a — the one concrete `llm_proposer.LLMClient` implementation, slotting in *under* the frozen Protocol (no seam edit). `LLMConfig` (frozen; `temperature` default `0.0`; `from_config`/`from_env`; stores only the API-key env-var *name*) + `HttpLLMClient` (OpenAI-compatible `/chat/completions` over **stdlib `urllib.request` + `json`**, no new dep; one user message at temp 0.0; returns `choices[0].message.content`; *network-fault* retry layer — timeouts/connection/429/5xx → bounded exponential backoff, non-429 4xx + exhausted retries → fail-loud `LLMTransportError`; injectable `sender` seam so the suite opens zero sockets) + `ReplayClient` (content-addressed `sha256(prompt)` JSON-per-prompt store; unknown prompt → fail-loud) + `RecordingClient` (wraps any client, persists `prompt-hash → response`; captures the A3b spike transcript for offline replay) + `LLMClientError`/`LLMTransportError` + thin `main` `complete` CLI. Imports `utils.config`/`taxonomy` + stdlib only; never `llm_proposer`-edits/`variant_proposer`/`run_synthetic`/`stage_*`/`mutator`/`layer_*`. The malformed-JSON resend stays in `llm_proposer.propose` — two retry layers, never merged. **A3b** (live ≥2-model fluency/JSON/cost spike + §4 model flip) is the manual, paid follow-up — Sprint 25's opening step; A3a only *enables* it.
  spike.py                                        ✅ Sprint 25 — Task A3b-build — the model-choice spike harness; a *consumer* of the orchestrator that sits **above** the frozen seam (never imported by it). `SINGLE_TYPE_CONDITIONS` (the 12 single-type §6 conditions, sorted/deterministic) + `CandidateSpec` (slug + `LLMConfig`; `.parse("name:base_url:model[:API_KEY_ENV]")`) + `CandidateScore` (**automatable-only** scorecard: proposed/skipped, per-`ModificationType` outcome, the C2/C3 skip split on `malformed_llm_response_after_retry:`/`schema_validation_failed:`, `llm_calls`, total/mean latency, mean response length — **no fluency field**) + `run_candidate` (wraps `RecordingClient(_MeasuringClient(client_factory(cfg)))` into a per-candidate store `store_root/<name>`, calls the **unedited** `run_concept`, tallies off the `VariantCatalogEntry`; injectable `clock`; `replay=True` re-tallies an old store via `ReplayClient` with no live call) + `run_spike` (each candidate → its own store) + `format_scorecard` (Markdown table, automatable columns only, **no fluency column**) + thin `main` `run` CLI. Imports `run_synthetic`/`llm_client`/`taxonomy`/`utils.config` + stdlib only; never edits the seam. **A3b-run** (the live ≥2-model fluency read + the §4 `TBD → model` flip) is César's manual, paid close-out — the harness only *enables* it.
  f1_pilot.py                                     ✅ Sprint 27 — Task F1-build — the single-concept pilot harness; a *consumer above the orchestrator* (like `spike.py`; imports the seam, never imported by it). `run_pilot` composes the **unedited** stack with the `l2_repr` two-mode adapter bracketed in: `list_to_formula(include_conditional=True)` → `run_concept` (through `RecordingClient(HttpLLMClient(llama3.1:8b))`) → `list_to_formula(include_conditional=False)` → `materialize_catalog_entry(pre_rerun=formula_to_list)` → `metadata.join_intermediate` → `review.sample_review_queue(coverage=1.0)` → a `PilotScore` (generated/skipped + C2/C3 split, l2_targets, materialized/reviewable items, queue size, coverage). `load_pilot_concept` + `default_conditions` (all 17) + `format_scorecard` + offline `replay=True` (ReplayClient) + thin `run`/`replay` CLI. `coverage_fraction` is measured against *reviewable* (mod-bearing) items (0-mod baselines from Stage-B-skipped variants are correctly excluded by `review.stratify`). Stdlib + `l2_repr`/`run_synthetic`/`stage_b`/`stage_runners`/`metadata`/`review`/`llm_client`/`taxonomy`/`utils.config`. The live run is Sprint 28 (F1-run); the harness is hermetic (no live `pytest` case).
  l2_repr.py                                      ✅ Sprint 26 — Task B6 — **reference-style-aware** L2 text-variable representation adapter; a *consumer above the frozen seam* (imports `slot_extractor`/`taxonomy` + stdlib; never imported by any seam module). Fixes the **silent L2 no-op**: `enumerate_targets` skips any non-string text-variable, and real data has **three shapes** whose rerun form is set by the template ref — `LIST_plain` (`['"Diurno"', …]`, indexed `$L(%B)` → positional list), `STR_formula` (`'"normal" * (%B=="a") + …'`, bare `$K` → formula), `LIST_conditional` (`['"…" * (%B=="f")', …]`, bare `$P` → list of conds). Two conversion modes: `list_to_formula(stage_json, include_conditional=True)` makes all three enumerable for Stage A (LIST_plain paired with axis values; LIST_conditional joined verbatim; STR_formula passthrough); `include_conditional=False` converts only LIST_plain so STR_formula/LIST_conditional mutate **natively** (layer_l2 handles both) and stay byte-faithful; `formula_to_list(stage_json)` restores **only indexed-referenced** vars to positional lists (leaving bare STR_formula strings + native LIST_conditional lists — fixes a latent corruption bug). Plus `derive_var_axis_map` + `assert_l2_targets_or_warn` (silent-no-op guard). Per-var report (`converted`/`joined_conditional`/`native_conditional`/`already_formula`/`unreferenced`/`multi_axis_conflict`/`length_mismatch`/`embedded_quote`/`unsupported_shape`); nothing silent. Pure/deep-copying. **Byte-faithful baseline verified** (unmutated round-trip == original rerun on `OEB020$`'s 4608 leaves). The F1 driver (Sprint 27) brackets the mutation: `list_to_formula(True)` → `run_concept`; `list_to_formula(False)` → `apply_variant_rules` → `formula_to_list` → `run_stages_3_to_7`. Enumerable PARAPHRASE targets on `OEB020$`: 20 → 31; on `OEB070$`: 0 → 9.
  loaders.py                                      ✅ Sprint 22 — Task G2 — read-only consumer layer over the G1 release. `load_items`/`load_modifications` (thin wrappers over `packaging.read_*`; default paths via `default_items_path()`/`default_modifications_path()`, resolved at call time under `SYNTHETIC_PROCESSED_DIR`) + `join` (re-attaches the ragged sidecar as an in-memory `modifications` `list[dict]` column on a sorted **copy**; **1:1** on `item_key`, fail-loud `LoaderError` on any unmatched key; no input mutation) + `long_view`/`short_view` (`texto`/`resumen`→single `text` col + key/slice metadata + derived `text_norm` via `normalize_text` reused verbatim; no fabricated OEB-only `id`/`ud`/`concept`, no `modifications`) + `LoaderError` + `main` (info CLI). Imports `packaging`/`taxonomy`/`utils.config`/`utils.text_processing` + lazy `pandas` + stdlib only; never `stage_b`/`run_synthetic`/`stage_runners`/`review`/`mutator`/`layer_*`. **Read-only — writes no new on-disk artifact** (every projection is an in-memory, re-derivable frame; G1's "two files are the canonical release" holds).
  target_scanner.py                               ✅ Sprint 37 — Task F3-prep-1-A — chapter-level target enumeration + dedup for the menu-first Stage-A flow. `ChapterInventory` + `UniqueTarget` + `TargetUsage` frozen dataclasses; `scan_chapter(stage_json, *, concept_filter=None, apply_l2_conversion=True) -> ChapterInventory` walks every `$`-suffixed concept, reuses `slot_extractor.enumerate_targets` per concept, deduplicates across concepts by family-specific keys (L1 `(axis_label, value)` — one per per-value target, drilling below the axis-level enumerator; L2 fragment-text-only; L3 `(field, template[, var_token])`; PD per-concept). Applies `l2_repr.list_to_formula(include_conditional=True)` internally by default so LIST_plain / LIST_conditional shapes enumerate (matches the Sprint 26 pipeline discipline). Whitespace-normalised, case-preserving (Spanish accents are load-bearing). Deterministic ordering. Empirical dedup on OEB subset (25 concepts, 2026-07-08 preflight `dedup_scan.py`): **83 % savings — 3 847 → 673 raw / 562 with the Sprint 34 gate applied**. Imports `slot_extractor` + `l2_repr` + `taxonomy` + stdlib only; never `stage_b`/`run_synthetic`/`mutator`/`layer_*`/`metadata`/`packaging`/`review`/`stage_runners`. Sits *above* the frozen seam like `spike.py` / `f1_pilot.py`.
  menu_proposer.py                                ✅ Sprint 37 — Task F3-prep-1-B — N-candidate proposer for the menu-first flow. `DEFAULT_N_CANDIDATES = 10` + `CandidateProposal` + `CandidateSet` frozen dataclasses; `propose_type(stage_json, inventory, mtype, client, *, n) -> dict[dedup_key, CandidateSet]` batches at prompt granularity — **one LLM call per axis for L1** (response decomposed into per-value CandidateSets), one call per target for L2 / L3 / NEW_PARAM. Multi-candidate wrapper appended at runtime as a single f-string (*"Devuelve una lista JSON de {n} alternativas … No repitas alternativas."*): the 13 prompt files stay byte-identical. List-level parse tolerates prose- and fence-wrapped output (reuses `llm_proposer._FENCE_RE` + `_extract_json_object`); per-element schema validation via the existing `variant_proposer._validate_payload` — per-item failures drop only the offender, whole-target skip only on `malformed_list_after_retry:` (distinct prefix from C2's per-item shape). **Inter-candidate dedup** at parse time (casefold + whitespace) collapses phi4's near-duplicate hedging. Imports `slot_extractor` + `variant_proposer` (private `_validate_payload` / `_render_prompt`) + `llm_proposer` (private `_extract_json_object` / `_FENCE_RE`) + `prompts.load_prompt` + `target_scanner` + `taxonomy` + stdlib only.
  menu_artefacts.py                               ✅ Sprint 37 — Task F3-prep-1-C — writer for both menu artefacts. `write_menu(inventory, sets_by_type, *, machine_dir, review_dir, chapter_label) -> tuple[WriteReport, ...]` writes **two parallel files per rewrite type from one call**: machine-readable JSONL under `data/synthetic/menus/{mtype}.jsonl` (one line per unique target, `approved: null` on every candidate for Sprint 38's parser to flip); human-review Markdown under `docs/synthetic/menus/{mtype}.md` (one `##` heading per target, `_Used in N concept(s): …_` line, numbered `- [ ] i. <candidate>` checkboxes up to *n* per target, skipped targets show `_Skipped: <reason>_` instead of checkboxes). Deterministic ordering by dedup key + candidate index. Atomic write via `.tmp` + `os.replace`. Imports `target_scanner` + `menu_proposer` + `taxonomy` + stdlib only.
  menu_runner.py                                  ✅ Sprint 38 — Task F3-prep-2-code-A — CLI driver above the frozen seam (sibling of `spike.py`/`f1_pilot.py`). `MenuRun` + `TypeStat` frozen dataclasses; `run_menu(stage_json, *, concept_filter, n, client, chapter_label, out_dir_machine, out_dir_review, clock) -> MenuRun` composes `target_scanner.scan_chapter → menu_proposer.propose_type (per mtype) → menu_artefacts.write_menu`; `default_client(chapter_label, replay=False)` wires `RecordingClient(HttpLLMClient(LLMConfig.from_env()), store)` for live and `ReplayClient(store)` for offline replay; `default_store_dir(chapter_label) = LLM_CACHE_DIR / f"menu_{chapter_label}"` + `default_out_machine_dir()` (SYNTHETIC_DATA_ROOT / "menus") + `default_out_review_dir()` (REPO_ROOT / "docs" / "synthetic" / "menus"); internal `_CountingClient` attributes LLM calls per rewrite type without touching the client interface; `format_scorecard(run)` emits a Markdown-table generation report for `RESEARCH_LOG.md`; `main(argv)` with `run` (live) / `replay` (offline) subcommands. Imports `target_scanner`/`menu_proposer`/`menu_artefacts`/`llm_client`/`taxonomy`/`utils.config` + stdlib. Never imported by any seam module (asserted). **Sprint 38.6:** `run_menu` gained `skip_types: frozenset` + a `--skip-types` CLI flag — full menu passes must use `--skip-types template_paraphrase`, because that type's artefacts are owned by `menu_diversity` from Sprint 38.6 on (a plain full replay would clobber the diversity-generated menu).
  menu_review_parser.py                           ✅ Sprint 38 — Task F3-prep-2-code-B — reads ticked Markdown menus (Sprint 37 output) back into structured verdict JSONL for the Sprint 39 sampler to consume. `MenuVerdict` + `CandidateVerdict` + `ParseReport` + `TypeParseStat` frozen dataclasses; `ParseError` (distinguishes structural drift from review verdicts). Regex-based Markdown scan (`_HEADING_RE`, `_TICK_RE = r"^- \[([ xX])\] (\d+)\. "`). **Machine JSONL is source of truth; Markdown contributes only tick state.** `parse_review_file(md_path, jsonl_path)` fails loud on heading-count mismatch / canonical drift / out-of-range tick index. `write_verdicts` / `read_verdicts` atomic JSONL round-trip. `parse_all(machine_dir, review_dir, out_dir)` sweeps every rewrite type; falls back to *reject-all* when review file is missing (never fabricates approvals). `format_parse_report` coverage-summary Markdown. `main(argv)` with `parse` subcommand. **Reject-by-default review contract:** anything not `- [x]` (case-insensitive) rejects. Imports `menu_runner` (default paths only) + `taxonomy` + `utils.config` + stdlib; never any forbidden seam.
  menu_profile.py                                 ✅ Sprint 38.5 — read-only per-type scorecard over `data/synthetic/menus/*.jsonl` (targets / empty / candidates / no-ops / dups / skips). `python -m synthetic.menu_profile`. Stdlib + `utils.config`. **Sprint 38.6:** two diversity columns — `dist_orig` (mean 1 − token-Jaccard(new, original) over candidates) + `pair_sim` (mean pairwise token-Jaccard among a target's candidates, pinned as the mean of per-target means). Baselines they measured on the 38.5 menus: template_paraphrase p_sim 0.76 / d_orig 0.41.
  menu_diversity.py                               ✅ Sprint 38.6 + 38.6-B — transformation-slotted, multi-model proposer that **owns the `template_paraphrase` menu artefacts from Sprint 38.6 on** (full `menu_runner` passes must pass `--skip-types template_paraphrase`). Consumer above the frozen seam (sibling of `menu_runner`). Per target: 3 rounds (R1 voice/frame, R2 architecture, R3 free restructuring with R1/R2 keeps' openings forbidden) × N models (default `phi4:latest` + `qwen2.5:14b`) at temperature 0.8; per-model transcript stores `data/synthetic/llm_cache/menu_OEB_tpar_{phi4latest,qwen2514b}`; `proposer_model` provenance tagged post-validation, rendered as `— _model_` in the review MD. Slots sanitized of FIEBDC `\` then invariant-masked via `template_masking` (sentinel instruction in `_wrap_round`); per candidate: `remask` rescue (self-unmasked literals forgiven when unambiguous) → `check_sentinels` → `unmask` → the FULL validator stack on restored text (schema + placeholders + quantities + scaffold-echo + `sentinel_residue` guard + exact dedup + similarity gate). Top-up rounds to `MIN_CANDIDATES = 6` (max `MAX_TOPUP_ROUNDS = 2`). `run`/`replay` CLI; replay is byte-deterministic (sha1-verified on the 2026-08-30 full run: 49 targets → 709 candidates, p_sim 0.41 / d_orig 0.55). Imports `menu_proposer`/`menu_artefacts`/`menu_runner`/`template_masking`/`variant_proposer`/`target_scanner`/`l2_repr`/`llm_client`/`prompts`/`taxonomy`/`utils.config` + stdlib.
  template_masking.py                             ✅ Sprint 38.6-B — pure-function sentinel masking of meaning-critical invariants for the diversity path. `mask_invariants(text) -> (masked, mapping)` replaces placeholders (`$A`, `$L(%C)` → `[[Pn]]`) and quantities incl. digit-bearing codes and attached unit words (`760 mm`, `HM-20`, `4x40 mm` → `[[Qn]]`); `unmask` restores the exact literals; `remask` re-hides literals a model self-unmasked (forgiven only when the literal appears exactly once — provably harmless: restoring a remasked text yields the model's own text); `check_sentinels` fail-loud multiset check (`sentinels_not_preserved`). `$` is excluded from the unit peek so a placeholder after a number is never swallowed as a pseudo-unit (hardening `e06bf97`, follow-up F7 resolved same day). **902/902 catalog surfaces round-trip identically.** Stdlib + `slot_extractor._UNIT_TOKENS` only; used by `menu_diversity`.
  pantry.py                                       ✅ Sprint 39 — the approved-rewrite pantry: joins `data/synthetic/menus/{tipo}.jsonl` (payloads + usages) with `data/synthetic/menus/verdicts/{tipo}.jsonl` (approved flags) by line index into per-type tuples of `ApprovedRewrite` (dedup_key, canonical, candidate_index, payload, usages; stable `uid` for reuse accounting) + `Pantry.for_concept` applicability index. `omission`/`new_param` excluded (`EXCLUDED_TYPES`, César 2026-08-31). Fail-loud `pantry_misaligned` on any menus↔verdicts drift. Real data: 9 types, **1 931 approved rewrites**. Note: on-disk usages carry `slot_extractor_target_id=None` (dropped at menu serialization) — the driver re-derives target ids via `target_scanner`. Stdlib + `taxonomy` + `utils.config`.
  corpus_sampler.py                               ✅ Sprint 39 — deterministic sampling plan. `load_budgets` (validates `variant_budgets.yaml`: exactly the 10 conditions, positive ints) + `LeafInventory` (leaves grouped by `parent_key`, each with normalized combined original text + selected `(axis, value)` pairs; `leaf_inventory_from_frames(long_df, short_df)` joins the two OEB parquets on `item_key`) + `build_plan` → `PlannedVariant(condition, concept_key, leaf_item_key, rewrites)`: proportional largest-remainder allocation per concept, leaves unique within a condition (`random.Random(seed ^ zlib.crc32(condition))` — never builtin `hash()`), least-used-first rewrite choice with per-condition ≤20× caps on thin types (deficit reported, never refilled cross-type), capacity-aware allocation + recovery sweeps, **value-precise leaf↔rewrite compatibility** (L1 = exact `(axis, value)` pair AND rendered surface; L2 = selected-value equality with longer-sibling-swallow rejection; word-boundary text fallback; L3 always compatible), and `all_combined` = one rewrite per applicable type with **one `template_paraphrase` per FIELD (RESUMEN + TEXTO — César 2026-09-02)**, no two rewrites sharing a dedup_key. `plan_report` per-condition diagnostics. Same inputs → identical plan.
  corpus_driver.py                                ✅ Sprint 39 — plan → frozen release. Copies the f1_pilot `l2_repr` bracket verbatim (enum view for emission+scan, apply view + `pre_rerun=formula_to_list` for materialization). Re-derives slot ids by scanning the enum view once (`target_scanner.scan_chapter`) and joining on `(mtype, dedup_key)`; emits **one rule per slot** per rewrite (same-var duplicate fragments: the planned leaf's slot wins — frozen `layer_l2` sibling-collision guard); L1 payload `original`s aligned to the raw padded value texts. `compose_rules` conflict → variant skipped + counted, never raised. Materialization **grouped by `(concept, ruleset)`** — one `materialize_variant` per group, every planned leaf extracted from it — and parallelized (`ProcessPoolExecutor`, `--workers`, default `cpu_count()//2`; workers=1 inline; byte-identical output regardless, test-pinned). Filters in sorted `(condition, concept, leaf)` order: no-op backstop + exact `(resumen, texto)` corpus-wide dedup (dropped + counted); unresolved `$`/`[[` residue **raises** `ResidueError`. One representative `Modification` per distinct rewrite (`modification_count == len(planned.rewrites)`; E2 couples count to the record list). `packaging.write_release` + per-condition Markdown QA report (`all_combined` type presence split by template field). CLI `python -m synthetic.corpus_driver run --stage-json … --concepts OEB --budgets … [--workers N]`. No LLM anywhere.

configs/synthetic/                                🚧 Phase A–B
  variant_budgets.yaml                            ✅ Sprint 39 — Task F3-prep-3 — the pilot corpus budgets as config (seed 39; per-condition targets 1000/650/350 + all_combined 1500; ≤20× reuse caps on num_to_text / unit_expansion / unit_conversion — César's 2026-08-31 significance-based sizing, superseding the 2026-07-08 flat-50 sketch). Validated by `corpus_sampler.load_budgets`; editable without touching code.
  new_param_allowlist.yaml                        ❌ Task B4 — admissible new axes
  composition_rules.yaml                          ❌ Task B5 — stacking constraints

data/synthetic/                                   ❌ Phases C–G
  variants/                                       ✅ Sprint 15 — Task C4 — `variant_catalog.write_catalog_entry` writes here; orchestrator (Sprint 16) populates per-concept files
  intermediate/                                   ✅ Sprint 18 — Task D2 — `stage_b.run_stage_b` writes mutated raw items here as `{concept}/{variant_id}.json` (variant metadata + modification log + regenerated items)
  processed/                                      ✅ Sprint 21 — Task G1 — `packaging.write_release` writes the two release artifacts here
    BC3CAT_Syn_items.parquet                      ✅ Sprint 21 — Task G1 — flat columnar items table (one row per `SyntheticItem`, `ITEM_COLUMNS`, sorted by `item_key`); `pyarrow`/atomic/deterministic. **Sprint 39: pilot corpus generated** — 8 687 items, 10 conditions, release commit `6b52053`, byte-reproducible (SHA-256 `7A99A754…`).
    BC3CAT_Syn_modifications.jsonl                ✅ Sprint 21 — Task G1 — sidecar JSONL (one line per `item_key`, full `modifications` log; baseline→`[]`); joins 1:1 with the items table on `item_key`. **Sprint 39: generated** alongside the parquet (SHA-256 `DA8A140A…`).

Existing files extended in this branch (not new, but load-bearing for the synthetic engine).
**All rows below were runtime-verified end-to-end in Sprint 06** ([`SPRINT_06_REPORT.md`](sprints/SPRINT_06_REPORT.md), 24/24 PASS):
  src/utils/config.py                            ✅ Sprint 02 — Task A4 part 1 — added `REPO_ROOT`, `DATA_ROOT`,
                                                              `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR`,
                                                              `LLAMAINDEX_DIR`, `SYNTHETIC_DATA_ROOT`,
                                                              `SYNTHETIC_INTERMEDIATE_DIR`, `SYNTHETIC_PROCESSED_DIR`,
                                                              `SYNTHETIC_VARIANTS_DIR`, `SYNTHETIC_REVIEW_DIR` (Sprint 20 — queue + verdict JSONL home),
                                                              `chapter_path()`, `stage_path()`,
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
                                                  ✅ Sprint 6.5 — cell 8 (id `8d1aea31`) line 86 of source: `for key in either_duplicate_keys:` →
                                                              `for key in sorted(either_duplicate_keys):`. Makes `_either_duplicate.json` byte-deterministic
                                                              run-to-run (set iteration was PYTHONHASHSEED-randomized).
  src/s08_Llamaindex_Doc_Creation.ipynb          ✅ Sprint 04 — Task A4 part 3 — 3 `/work/data/...` literals → `config.stage_path(file, 7)` +
                                                              `config.PROCESSED_DIR / f"{file}_{texto,resumen}.pkl"`;
                                                              `from utils import config` added (cell 2).
  src/Generate_OEB_dataset.ipynb                 ✅ Sprint 04 — Task A4 part 3 — 4 path-literal rewrites (cells 3/4/8 + cell 2 bootstrap retarget) +
                                                              1 stale-comment deletion. `Path('/work')` → `config.REPO_ROOT`;
                                                              `'/work/data/processed/...' → config.PROCESSED_DIR / "..."`; cell 4 collapsed to bare
                                                              relative `"OEB_texto.pkl"`. `sys.path.append(...)` + `from src.utils.data_utils import load_documents`
                                                              kept intact (repo-rooted import chain — Sprint 05 / 04.5 follow-up).
                                                  ✅ Sprint 05 — cell 2 bootstrap retired: `from src.utils.data_utils import load_documents` →
                                                              `from utils.data_utils import load_documents`; `project_root = config.REPO_ROOT` +
                                                              `sys.path.append(str(project_root))` + blank separator deleted (path refactor's final `sys.path` shim).
                                                  ✅ Sprint 6.5 — new code cell inserted at index 8 (id `6060ae5d`) writing `OEB_resumen.pkl` to
                                                              `config.PROCESSED_DIR`. Cell count 10 → 11; JSON-producer cell (id `b9f644bb`) shifted index 8 → 9
                                                              with identical content. Generate_OEB now runs end-to-end without errors.
  src/utils/data_utils.py                        ✅ Sprint 05 — `from src.utils.custom_types import DocumentList` →
                                                              `from .custom_types import DocumentList` (single line, +1/−1).
  src/utils/evaluation.py                        ✅ Sprint 05 — `from src.utils.custom_types import RetrievalResult` →
                                                              `from .custom_types import RetrievalResult` (single line, +1/−1).
  src/utils/index_classes.py                     ✅ Sprint 05 — `from src.utils.{text_processing,custom_types,config}` → `from .{...}` (lines 10–12, +3/−3).
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

### After Sprint 39 — pilot synthetic corpus (budgets + deterministic sampler + corpus driver)
**Date:** 2026-09-02
**Sprint files:** [`sprints/SPRINT_39.md`](sprints/SPRINT_39.md) (spec: [`sprints/SPRINT_39_DESIGN.md`](sprints/SPRINT_39_DESIGN.md), + 2026-09-02 addendum) · QA report [`sprints/SPRINT_39_corpus_report.md`](sprints/SPRINT_39_corpus_report.md) · log entry in [`RESEARCH_LOG.md`](RESEARCH_LOG.md) (`2026-09-02`).
**What changed:** three new consumer modules above the frozen seam — [`pantry.py`](../../src/synthetic/pantry.py) (menus+verdicts → 1 931 approved rewrites, 9 types, applicability per concept), [`corpus_sampler.py`](../../src/synthetic/corpus_sampler.py) (budgets YAML → deterministic per-concept/per-condition plan; value-precise leaf↔rewrite compatibility) and [`corpus_driver.py`](../../src/synthetic/corpus_driver.py) (plan → per-slot rule emission → composition → grouped parallel Stage-B materialization → filters → `packaging.write_release` + QA report) — plus `configs/synthetic/variant_budgets.yaml`. No LLM anywhere; generation is pure CPU.

**Key results:**
- **Pilot corpus generated** (release commit `6b52053`; prior `15f8bda` first generation, `9caefed`+`b7ea363` pre-generation fixes, `0f52c3a` both-field sampler): **8 687 items / 8 734 planned**, 10 conditions; 45 no-ops dropped (0.5 %), 2 dups, **0** emission/composition/residue failures; two full runs **byte-identical** (items SHA-256 `7A99A754…`, modifications `DA8A140A…`); ~60 min wall with 8 workers.
- **César's rulings (2026-09-02):** every `all_combined` item rewrites BOTH templates (RESUMEN + TEXTO presence 1 500/1 500; mean token distance 73.7 → 90.0); `reorder`'s structural absence from `all_combined` accepted (full-template rewrites collide per field; measured in `single_reorder` 1 000/1 000); thin-type deficits accepted (`unit_expansion` 373/650, `unit_conversion` 209/350 — pantry-limited under the 20× cap, margins ≈ ±5.1/±6.8; Sprint 40 regeneration backlog); pantry artifacts kept as documented stress ("tubos tubos" ~376, "mm mm" ~280, "con topo"→"con topografía" ~245 — traceable in the sidecar).
- The release `condition` is derivable (not a column): `modification_count == 1` → `single_<modification_types[0]>`, `> 1` → `all_combined` (every `all_combined` here carries ≥ 3 types). Rule documented in `HANDOFF.md`.
- `pytest tests/synthetic -q` → **1 092 passed, 2 skipped** (was 1 061 at sprint start).

**Known issues / next:** Sprint 40 (scale to all OBRA CIVIL; regenerate thin types; strip the FIEBDC backslash at prompt-build; arithmetic for unit_conversion/num_to_text). The sibling `bc3cat-retrieval` can consume `data/synthetic/processed/` now (loader contract frozen since G2).

### After Sprints 38.6 + 38.6-B — template_paraphrase diversity (rounds × models, invariant masking, remask rescue)
**Date:** 2026-08-30
**Sprint files:** [`sprints/SPRINT_386.md`](sprints/SPRINT_386.md) (spec: [`sprints/SPRINT_386_DESIGN.md`](sprints/SPRINT_386_DESIGN.md)) + addendum [`sprints/SPRINT_386B.md`](sprints/SPRINT_386B.md) · log entry in [`RESEARCH_LOG.md`](RESEARCH_LOG.md) (`2026-08-30`).
**What changed:** the dull `template_paraphrase` menu (p_sim 0.76 / d_orig 0.41 on the 38.5 menus, measured by `menu_profile`'s new diversity columns) was regenerated **live** by the new [`menu_diversity.py`](../../src/synthetic/menu_diversity.py): 3 transformation-slotted rounds × 2 models (`phi4:latest` + `qwen2.5:14b`) at temperature 0.8, invariants masked behind sentinels ([`template_masking.py`](../../src/synthetic/template_masking.py), 902/902 catalog round-trips), remask rescue for model self-unmasking, top-up rounds to `MIN_CANDIDATES = 6`. Two new mechanical gates landed for every type: quantity conservation (`variant_proposer`, TEMPLATE_PARAPHRASE + REORDER; zero false positives on the 532 existing menu candidates) and a token-Jaccard-0.8 similarity gate (`menu_proposer`, REORDER exempt — an order-blind metric would kill pure reorders). `menu_runner` gained the `--skip-types` ownership guard.

**Key results:**
- Full run (commit `fa7b7bc`): **49 targets → 709 candidates, 0 skipped, 0 empty, 0 sentinel leaks, 0 prompt echoes**; **p_sim 0.41** (target ≤ 0.55) / **d_orig 0.55** (target ≥ 0.45) — both gates met with margin; uniq/tgt 14.5 (was 8.3); model balance phi4 383 / qwen 326; weakest target 3 candidates (OEB020$ TEXTO), none below 3. Snapshot: [`sprints/SPRINT_386_profile.txt`](sprints/SPRINT_386_profile.txt).
- Pilot progression (pre-mask / mask / mask+rescue over the 5-concept pilot): 133 / 99 / 119 candidates; OEB010$ TEXTO 2 / 7 / 7 — masking fixed long-template starvation, the rescue recovered the self-unmask losses (OEB250$ RESUMEN 12 / 2 / 6).
- `replay` reproduces both artefact files **byte-identically (sha1-verified)**; wall ≈ 55 min GPU total in two phases (phi4 alone, then both — phase 2 serves phi4 from its store; avoids dual-residency on the 24 GB GPU after a WSL2-wedge CUDA-OOM incident).
- `pytest tests/synthetic -q` → **1061 passed, 2 skipped** (was 1016 at sprint start); full `pytest tests -q` → **1085 passed, 2 skipped**.

**Known issues / next:** F8 (selective 3rd top-up round for targets still < 6 — only OEB020$ TEXTO qualifies) and F9 (soften the static "conserva las variables $X" prompt line to reduce self-unmasking; invalidates all tpar caches — bundle with Sprint 40) are open; F7 (masking unit-peek `$`) was resolved same day (`e06bf97`). **Next is F3-prep-2-review (César, ~6–7 h)** over all 11 menus including the regenerated `template_paraphrase` (~1.5–2 h alone; each line carries a `— _phi4latest_` / `— _qwen2514b_` provenance suffix — judge Spanish naturalness), then F3-prep-2-parse (`python -m synthetic.menu_review_parser parse`), then Sprint 39 (F3-prep-3: budgets + sampler + chapter driver).

### After Sprint 38.5 — Phase F Task F3-prep-2-fix (menu recovery: parser repair, per-type caps, targeting gates — offline replay)
**Date:** 2026-08-18
**Sprint file:** [`sprints/SPRINT_385.md`](sprints/SPRINT_385.md) · log entry in [`RESEARCH_LOG.md`](RESEARCH_LOG.md) (`2026-08-18 — Sprint 38.5`).
**What changed:** a pre-review profile of the Sprint 38 menus showed 127 template targets (almost all TEXTO) silently skipped as `malformed_json: Invalid \escape` — the raw stage-2 `texto` begins with `\` / `resumen` ends with `\` (FIEBDC delimiters s01 leaves in) and phi4 echoes it inside its JSON string. Three cache-neutral fixes above the frozen seam (no prompt text changed → all 502 recorded transcripts still hit), then the menus were regenerated offline:
- **`menu_proposer._parse_json_list`** retries after `_repair_invalid_escapes` (drops backslashes that don't open a valid JSON escape; only after a strict parse fails). 502/502 cached transcripts parse (was 369).
- **`MENU_CAP_BY_TYPE`** — post-parse cap of 3 for omission / reorder / num_to_text / unit_conversion / unit_expansion (`n = 10` request unchanged; head of the deduped best→worst list kept).
- **`slot_extractor.value_applies`** per-value gate (`SYNONYM_LABEL` excludes digit-bearing values; `_axis_applies` delegates) + `MIN_COMPRESSION_WORDS = 4`; `target_scanner._emit_entries` applies the per-value gate. Real-data synonym_label unique targets 49 → 34.
- **[`menu_profile.py`](../../src/synthetic/menu_profile.py)** (new) — read-only per-type scorecard over the menu JSONL; before/after frozen in `sprints/SPRINT_385_profile_{before,after}.txt`.
- `python -m synthetic.menu_runner replay … --concept-filter OEB --n 10 --seed 7 --chapter-label OEB` — 484 calls served from cache in 0.2 s, no misses (`sprints/SPRINT_385_replay_scorecard.txt`).

**Key results (from the profile files):**

| type | targets | empty (before → after) | candidates (before → after) |
|---|---:|---:|---:|
| omission | 212 | 100 → 8 | 590 → 496 (drop 51 → 119: recovered TEXTO responses now reach schema validation — expected) |
| reorder | 49 | 19 → 5 | 215 → 132 |
| template_paraphrase | 49 | 15 → 0 | 286 → 406 |
| synonym_label | 49 → 34 | 6 → 2 | 236 → 158 |
| compression | 46 → 22 | 0 | 291 → 107 |
| num_to_text / unit_conversion / unit_expansion | 12 → 11 / 14 → 12 / 14 → 12 | 0 / 7 → 5 / 2 → 0 | 105 → 33 / 21 → 18 / 49 → 33 |
| paraphrase / expansion / new_param | 46 / 46 / 25 | 0 | 420 / 454 / 251 — **byte-identical** |
| **TOTAL candidates** | | | **2 918 → 2 508** |

- TEXTO targets with candidates: omission 18 → 110, reorder 9 → 23, template_paraphrase 9 → 24.
- `pytest tests/synthetic -q` → **1014 passed, 2 skipped**; `pytest tests -q` → **1038 passed, 2 skipped**. Zero LLM calls, zero GPU.
- Residue: 10 candidate lines in `docs/synthetic/menus/template_paraphrase.md` (`TEXTO template (OEB140$)`) start with a cosmetic literal `\` (phi4 double-escaped the delimiter; harmless downstream — `layer_l3` substring replace, s05 strips the delimiter; judge the text). The 6 `OEB010$` prompt echoes were scrubbed by the `prompt_scaffold_echo` guard in `menu_proposer._validate_variants` (same-day addendum); that target now shows as skipped. Follow-up F1 (strip `\` at prompt-build) lands before Sprint 40.

**Known issues / next:** *(superseded by Sprints 38.6 + 38.6-B above — the `template_paraphrase` menu was regenerated with structural diversity on 2026-08-30; the review estimate is now ~6–7 h.)* Sprint 38.5 (2026-08-18) recovered the menus offline. **Next is F3-prep-2-review (César, ~5–6 h)** on the regenerated `docs/synthetic/menus/*.md` — reject-by-default, review guidance in [`STATUS_2026-08-18.md`](STATUS_2026-08-18.md). Then F3-prep-2-parse (Claude: `python -m synthetic.menu_review_parser parse`), then Sprint 39 (F3-prep-3: budgets + sampler + chapter driver). Deferred follow-ups F1–F4 + F6 are tabled in `sprints/SPRINT_385.md`.

### After Sprint 38 (cont.) — Phase F Task F3-prep-2-generate (live phi4 menu build on OEB subset)
**Date:** 2026-07-09
**What changed:** first real menu build against `phi4:latest`, live. Two crashes uncovered real-data bugs before third-time success — each fix landed with a regression test.
- **Bug 1 (LIST-shaped text-variables crashed `slot_extractor`)** — fixed by applying `l2_repr.list_to_formula(include_conditional=True)` in `run_menu` before feeding stage_json downstream (matches the `f1_pilot` discipline). Regression test uses a mixed-shape concept.
- **Bug 2 (60 s timeout exhausted on heavy L1-batched prompts)** — fixed by (a) `BC3CAT_LLM_TIMEOUT=300`, (b) new `menu_runner.ResumingRecordingClient` (cache-first wrapper; same on-disk format as `RecordingClient`, so partial runs resume automatically). The 264 transcripts recorded before the timeout were served from disk on relaunch.
- Third attempt: **completed cleanly in 5528 s (~92 min).** 636 phi4 calls, 2 918 candidates across 11 populated rewrite types.

**Key results (scorecard):**

| Rewrite type | Targets | Generated | Skipped | Candidates |
|---|---:|---:|---:|---:|
| synonym_label | 49 | 43 | 6 | 236 |
| paraphrase / expansion / compression | 46 / 46 / 46 | 46 / 46 / 46 | 0 / 0 / 0 | 420 / 454 / 291 |
| omission | 212 | 112 | 100 | 590 |
| reorder / template_paraphrase | 49 / 49 | 30 / 34 | 19 / 15 | 215 / 286 |
| new_param | 25 | 25 | 0 | 251 |
| **TOTAL** | **562** | **413** | **149** | **2 918** |

- **L1 batching held on real data** — 89 L1 targets served by only 29 phi4 calls.
- **Dedup at scale confirmed** — e.g. `BANDA DE MANTENIMIENTO / i >= 5 horas` reviewed once for 21 concepts.
- 11 machine JSONL + 11 Markdown files landed under `data/synthetic/menus/` and `docs/synthetic/menus/`. 502-prompt recorded store under `data/synthetic/llm_cache/menu_OEB/` makes every subsequent re-run offline and free.

**Known issues / next:** *(superseded by Sprint 38.5 above — these menus were regenerated offline on 2026-08-18; the review starts from the regenerated files, ~5–6 h.)* F3-prep-2-review (César, ~7-9 h) — tick the 5 600 candidate lines. Then F3-prep-2-parse writes verdict JSONL and F3-prep-3 (Sprint 39) builds the sampler.

### After Sprint 38 — Phase F Task F3-prep-2-code (menu builder: live driver + review parser)
**Date:** 2026-07-09
**What changed:** two new modules (both above the frozen seam) that make the Sprint 37 menu builder runnable and its Markdown output readable.
- **[`menu_runner.py`](../../src/synthetic/menu_runner.py)** — `MenuRun` scorecard + `run_menu()` composition + `main(argv)` with `run`/`replay` subcommands. `default_client()` wires `RecordingClient(HttpLLMClient(LLMConfig.from_env()), store)` for live and `ReplayClient(store)` for offline replay. Same consumer-above-orchestrator shape as `f1_pilot.py` / `spike.py`.
- **[`menu_review_parser.py`](../../src/synthetic/menu_review_parser.py)** — reads ticked Markdown back into `MenuVerdict` records + writes verdict JSONL. Fail-loud on heading-count mismatch / canonical drift / out-of-range tick. Reject-by-default (`- [ ]` = reject, `- [x]` = approve, case-insensitive). `parse_all` sweeps 13 rewrite types with reject-all fallback for unreviewed files.
- **[`test_menu_runner.py`](../../tests/synthetic/test_menu_runner.py) + [`test_menu_review_parser.py`](../../tests/synthetic/test_menu_review_parser.py)** — 25 hermetic tests: end-to-end over the tiny fixture, per-type TypeStat accounting, malformed-then-skipped, empty-type-bypasses-LLM, tick round-trips, structural-error fail-loud cases, boundary checks (AST-based import audit).

**Key results:**
- `pytest tests -q` → **1015 passed, 2 skipped** (Sprint 37 baseline 990 + 25 new). Zero regressions, zero sockets.
- **Zero seam edits.** The driver + parser compose Sprint 37's frozen library trio without touching it, and don't touch any older seam module either. `git diff` against every seam file returns empty.

**Known issues / next:** *(historical — F3-prep-2-generate ran 2026-07-09, see the entry above; Sprint 38.5 then recovered the menus offline on 2026-08-18. Current next step is F3-prep-2-review (César, ~5–6 h) on the regenerated `docs/synthetic/menus/*.md`, then F3-prep-2-parse, then Sprint 39.)* Original text: F3-prep-2-generate (Claude, live) — the live phi4 pass that produces the real menu artefacts. Ollama serving `phi4:latest`; `python -m synthetic.menu_runner run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7 --chapter-label OEB`. Then F3-prep-2-review (César, ~7-9 h) → F3-prep-2-parse (Claude) → Sprint 39 (F3-prep-3).

### After Sprint 37 — Phase F Task F3-prep-1 (menu builder: dedup-first target scan + N-candidate proposer + human-review artefact)
**Date:** 2026-07-08
**What changed:** three new modules that pivot Stage-A to a **menu-first** flow — propose N=10 alternatives per unique target, human reviews the whole menu once, sampler draws from approved candidates only.
- **[`target_scanner.py`](../../src/synthetic/target_scanner.py)** — walks a stage-2 chapter and dedupes targets across concepts. L1 deduped by `(axis_label, value)`; L2 by fragment-text; L3 by `(field, template[, var_token])`; PD per concept. Applies `l2_repr.list_to_formula(include_conditional=True)` by default so all three text-variable shapes enumerate.
- **[`menu_proposer.py`](../../src/synthetic/menu_proposer.py)** — `propose_type` batches at the existing prompts' natural granularity (one call per axis for L1 → per-value CandidateSets; one call per target elsewhere). The 13 prompt files stay byte-identical; the multi-candidate instruction is a runtime f-string. List-level parse tolerates fence-wrapped output; per-element schema validation drops only offenders; inter-candidate dedup (casefold + whitespace) collapses phi4 hedging.
- **[`menu_artefacts.py`](../../src/synthetic/menu_artefacts.py)** — writes both artefacts from one call: machine-readable JSONL under `data/synthetic/menus/` (with `approved: null` slots) and human-review Markdown under `docs/synthetic/menus/` (one `##` heading per target, up to *n* `- [ ]` checkboxes; skipped targets show `_Skipped: <reason>_`). Deterministic ordering, atomic write.
- **[`test_menu_builder.py`](../../tests/synthetic/test_menu_builder.py)** — 39 hermetic tests + a 3-concept fixture + an integration test against the real OBRA CIVIL stage-2 (pins per-family dedup counts on the OEB subset).

**Key results:**
- `pytest tests -q` → **990 passed, 2 skipped** (Sprint 36 baseline 951 + 39; zero regressions, zero sockets, zero new dependency).
- **Empirical dedup on OEB subset** (25 concepts, integration test): **562 unique targets** total after Sprint 34's gate + `l2_repr` conversion (synonym_label 49 / paraphrase 46 / omission 212 / new_param 25 / …). Preflight upper bound was 673 without the gate. Workhorse-axis insight held: `TRABAJO/Diurno` shares 20 of 25 concepts.
- **Menu-first review effort** at N=10: ~6 700 candidate lines → **7–9 h manual** (~10× cheaper than per-concept naïve). Menu review supersedes the pre-Sprint-37 "review a sample of rendered items" flow.
- **Seam untouched:** no edits to `variant_proposer` / `run_synthetic` / `slot_extractor` / `layer_*` / `mutator` / `stage_b` / `metadata` / `review` / `packaging` / `loaders` / `l2_repr` / `llm_client` / `f1_pilot` / `spike` / the 13 `prompts/*.txt` files.

**Known issues / next:** F3-prep-2 (Sprint 38, live) runs the menu builder against phi4 + reviews the Markdown. F3-prep-3 (Sprint 39) adds `variant_budgets.yaml` (flat 50/concept per César's 2026-07-08 decision) + the sampler + the chapter driver. Then F3 launches.

### After Sprint 29 — Phase F Task F2 (process-hardening from F1 findings) + F1-review hand-off
**Date:** 2026-05-21
**What changed:** three process fixes driven by the F1-run findings, each verified by re-running the `OEB070$` pilot:
- **JSON hardening** — [`llm_proposer`](../../src/synthetic/llm_proposer.py) `_extract_json_object` recovers a JSON object from prose + Markdown-fence wrapping (8B's habit) and brace-slices; genuine garbage still fails. Malformed **31→7**.
- **Placeholder-preservation validator** — [`variant_proposer`](../../src/synthetic/variant_proposer.py): reorder requires the `$VAR(%AXIS)` set to survive; omission requires it minus the omitted var's tokens. Catches the `$L(%B)→$/($B)` corruptions that string-only validation accepted.
- **L1 prompt fixes** — the 4 expansion/conversion prompts declared keys the schema rejects (`conversions`/`expansions` vs `synonyms`) — our own bug; aligned to `synonyms`. Added a verbatim-`original` instruction to all 6 L1 prompts (kill the `"a: Diurno"` label-prefix echo). Wrong-key fails **24→0**; `generated` **37→48**; synonym unmatched **10→2**.
- New tests [`test_f2_json_and_placeholders.py`](../../tests/synthetic/test_f2_json_and_placeholders.py) (18); `test_prompts` pins stay green; `pytest tests -q` → **826 passed, 2 skipped**.
- Generated [`F1_PILOT_REVIEW_DIGEST.md`](F1_PILOT_REVIEW_DIGEST.md) — condenses the 6144-item queue to **43 distinct modifications** for the manual review.

**Key results / decisions:**
- **Three iterations on 8B.** it0 (raw) 38 gen / 38 skip (31 malformed) → it1 (json+placeholder) 37 / 60 → it2 (prompts) **48 / 120**, all placeholder-clean. The genuine bugs (parse, key, placeholder, label-prefix) are fixed.
- **Remaining residual is targeting, not a bug:** `unmatched_original` (107) is dominated by `abbrev/code/unit_*` enumerated on axes with nothing to expand (legitimate skips). `reorder` still weak on 8B (0 generated). Deferred to F2-followup/F3.
- **F1-review is the human gate** — Claude does not judge Spanish fluency; the digest + queue are handed to César.

**Known issues:** L1-expansion targeting (inapplicable axes) and reorder-on-8B remain open; both are post-review decisions.

### After Sprint 28 — Phase F Task F1-run-generate (first live local pilot generation)
**Date:** 2026-05-21
**What changed:** ran the **first real generation pass** — `f1_pilot run` on `OEB070$` against Ollama `llama3.1:8b`, all 17 conditions. Artefacts under `data/synthetic/` (62 transcripts, 38 materialized variants, the catalog, a 4704-item 100 %-coverage review queue). No code change (the harness is frozen).

**Key results / decisions:**
- Mechanical scorecard: `generated 38 / skipped 38` (31 malformed + 7 schema), `l2_targets 9` (L2 fired), 4704 items, coverage 1.0, items validated. End-to-end plumbing works on real data.
- **JSON reliability finding (bimodal):** L2 succeeded ~fully (paraphrase/expansion/compression = 28 variants); L1 mostly failed (synonym/unit/abbrev/code) because 8B wraps JSON in prose + markdown fences and uses wrong list keys. Genuinely the model (confirmed from `raw_responses`), not a harness bug.
- **F2 agenda item identified:** harden the JSON contract for 8B (prompt "JSON only, no markdown" and/or a fence/prose-stripping C2 parser) — could flip L1 to near-100 %; measurable offline from the recorded store.
- This is the **mechanical half**; the Spanish-quality judgement is the pending **F1-review** (César). Generated artefacts are derived data; `pytest` unchanged (808 passed, 2 skipped).

**Known issues:** 8B JSON reliability on the keyed-list (L1) prompts is the main open issue, deferred to F2. `$M` on `OEB070$` (malformed source, `embedded_quote`) is not L2-targetable as expected.

### After Sprint 27 — Phase F Task F1-build (pilot harness + `stage_b` pre-rerun hook)
**Date:** 2026-05-20
**What changed:**
- Added a `pre_rerun: Callable[[dict],dict] = _identity` hook to
  [`stage_b`](../../src/synthetic/stage_b.py) `materialize_variant` /
  `materialize_catalog_entry` (applied to the mutated concept before
  `run_stages_3_to_7`; default identity = byte-identical for existing callers).
  The single deliberate seam edit — the insertion point for `l2_repr.formula_to_list`.
- Created [`src/synthetic/f1_pilot.py`](../../src/synthetic/f1_pilot.py) — the
  single-concept pilot driver (`run_pilot` + `PilotScore` + `load_pilot_concept` +
  `default_conditions` + `format_scorecard` + `replay` + CLI); a consumer above
  the orchestrator, never imported by the seam.
- Created [`tests/synthetic/test_f1_pilot.py`](../../tests/synthetic/test_f1_pilot.py)
  (14) — hermetic; `run_pilot` composition + the `stage_b` hook (default==identity,
  invoked-once, formula_to_list renders clean) + offline replay + hygiene.
- Added the `f1_pilot.py` ✅ file-map row + the `stage_b` hook note; renumbered the
  F1 draft `SPRINT_27 → SPRINT_28` (F1-run); `RESEARCH_LOG.md` Sprint 27 entry;
  `RESEARCH_PROTOCOL.md` §3.5 driver row ✅ + §5 F1-build ✅ / F1-run ⏳.

**Key results / decisions:**
- **Build-vs-run split.** Sprint 27 ships the hermetic harness; the live local
  generation + 100 %-manual review is Sprint 28 (F1-run).
- **One deliberate seam touch** (the default-identity `pre_rerun` hook) — smaller
  and safer than duplicating the materialize loop in the driver.
- **`coverage_fraction` measured against reviewable (mod-bearing) items** — 0-mod
  baselines from Stage-B-skipped variants are correctly excluded by
  `review.stratify` (surfaced by the smoke test).
- **The `metadata` integration risk did not materialize** — the materialized
  payload is exactly what `join_variant_payload` consumes; items validate.
- `pytest tests -q` → **808 passed, 2 skipped** (794 baseline + 14 new), zero
  failures, zero network.

**Known issues:** none new. The live `llama3.1:8b` Spanish-quality judgement is
deferred to the F1-run manual review (Sprint 28).

### After Sprint 26 — Phase B Task B6 (L2 text-variable representation adapter)
**Date:** 2026-05-20
**What changed:**
- Found a **silent L2 no-op**: `enumerate_targets` skips any non-string
  text-variable, and real data has **three shapes** — `LIST_plain` (indexed
  `$L(%B)`), `STR_formula` (bare `$K`), `LIST_conditional` (bare `$P`). The two
  list shapes (~96 of ~117 OEB L2 vars) were silently un-enumerable. The L2 tests
  passed only because their fixtures used the formula form the pipeline never
  emits for those.
- Created [`src/synthetic/l2_repr.py`](../../src/synthetic/l2_repr.py) — a pure,
  **reference-style-aware** adapter (`derive_var_axis_map`, two-mode
  `list_to_formula`, `formula_to_list`, `assert_l2_targets_or_warn`); a consumer
  above the frozen seam, never imported by it.
- Created [`tests/synthetic/test_l2_repr.py`](../../tests/synthetic/test_l2_repr.py)
  (20) + [`test_l2_integration.py`](../../tests/synthetic/test_l2_integration.py)
  (8) — hermetic; all three shapes, the byte-faithful baseline through
  `run_stages_3_to_7`, mutated round-trips for plain + conditional.
- Added the `l2_repr.py` ✅ file-map row; renumbered the F1 draft `SPRINT_26 →
  SPRINT_27` (now all 12 types); `RESEARCH_LOG.md` Sprint 26 entry prepended;
  `RESEARCH_PROTOCOL.md` §3.5 adapter row ✅ + §5 B6 entry.

**Key results / decisions:**
- **Reference style decides the rerun form (empirically verified).** Indexed
  `$L(%B)` → positional list; bare → formula string / native list. Wrong form
  corrupts the rerun (mangled index / collapsed leaves / unfaithful render). My
  first cut handled only `LIST_plain` and would have **corrupted bare
  `STR_formula` vars** — the user flagged the missing shapes; the fix is
  reference-style-aware.
- **Two conversion modes.** `include_conditional=True` for `run_concept` (all
  enumerable), `False` for `apply_variant_rules` (STR/conditional native);
  `formula_to_list` restores only indexed `LIST_plain`. **Byte-faithful baseline**
  is the gate (verified dict-equal on `OEB020$`'s 4608 leaves).
- **Fix by adapting representation, not editing the seam** — `slot_extractor`/
  `layer_l2`/`rule_emitter` untouched; `layer_l2` already mutates `STR_formula`/
  `LIST_conditional` natively. Per-var report + `assert_l2_targets_or_warn` guard.
- **Reflection — L2 is the only fixture/real-data mismatch** (L1/L3/`new_param`
  fire on real data). Two error-swallowing risks (`stage_runners` s04 bare
  `except`; `stage_b` skip-and-log) are a documented follow-up, not fixed here.
- Enumerable PARAPHRASE targets `OEB020$` **20 → 31**, `OEB070$` **0 → 9**.
  `pytest tests -q` → **794 passed, 2 skipped** (766 baseline + 28 new), zero
  failures, zero network.

**Known issues:** embedded-quote vars (malformed source values) stay native and
are recorded — full coverage of malformed source formulas is out of scope. The
stage-runner error-swallowing follow-up remains open.

### After Sprint 25 — Phase A Task A3b-build (model-choice spike harness `spike.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/spike.py`](../../src/synthetic/spike.py) — the model-choice spike harness: `SINGLE_TYPE_CONDITIONS` (the 12 single-type §6 conditions, sorted/deterministic), `CandidateSpec` (slug + `LLMConfig`; `.parse("name:base_url:model[:API_KEY_ENV]")`), `CandidateScore` (automatable-only scorecard — proposed/skipped, per-`ModificationType` outcome, the C2/C3 skip split, `llm_calls`, total/mean latency, mean response length; **no fluency field**), `run_candidate` (wraps `RecordingClient(_MeasuringClient(client_factory(cfg)))` into a per-candidate store, calls the **unedited** `run_concept`, tallies off the `VariantCatalogEntry`; injectable `clock`; `replay=True`), `run_spike`, `format_scorecard` (Markdown table, automatable columns only), thin `main` `run` CLI. Consumer *above* the seam; never imported by it; stdlib + `run_synthetic`/`llm_client`/`taxonomy`/`utils.config` only.
- Created [`tests/synthetic/test_spike.py`](../../tests/synthetic/test_spike.py) — 17 hermetic tests (zero network): scorecard tallies + `ReplayClient` store round-trip + `replay=True` re-tally (exploding live factory); C2/C3 skip-reason split; full 12-condition drive; deterministic latency under an injected clock; `run_spike` ≥2 candidates → distinct stores; `format_scorecard` columns + no-fluency-column guard; no-secret-leak; no-reverse-import + no-new-dep tripwires.
- Added the `spike.py` ✅ row to the "New Files in This Branch" map; Sprint 25 entry prepended to [`RESEARCH_LOG.md`](RESEARCH_LOG.md); [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) §3.5 gained a Model-choice-spike-harness ✅ row, §5 A3b split into A3b-build ✅ / A3b-run ⏳, §4 model row left `TBD` with the harness-now-exists note.

**Key results / decisions:**
- **A3b-build (code, hermetic) vs A3b-run (live, paid, prose) split:** Sprint 25 ships the `spike.py` harness + scorecard; the live ≥2-model fluency read and the §4 `TBD → model` flip are César's manual close-out — the gate on Phase F. The harness *enables* it (`RecordingClient` captures each candidate transcript for offline replay); it does not run it. Same discipline as Sprints 23–24.
- **The spike is a composition, not new logic:** it wraps each candidate in a `RecordingClient` and calls the unedited `run_concept`; the scorecard is tallied off the `VariantCatalogEntry`. No new prompt/parse/schema logic — the C2/C3 seam is frozen.
- **Consumer of the orchestrator, never imported by it** (asserted). **Code measures the measurable; fluency is human** — no `fluency` field/column (guarded). **`RecordingClient` is mandatory** — the chosen model's store replays offline forever and F1 inherits it. **No secrets, no new dependency** (carried over from A3a; key absence asserted).
- `pytest tests -q` → **766 passed, 2 skipped** (Sprint 24's 749 + 17 new hermetic; the 2 skips unchanged — the spike's live path is the manual CLI, not a `pytest` gate). Zero failures, zero network calls. Seam `git diff` empty.

**Known issues:** the CLI `--replay` could not key the per-candidate store off `LLMConfig` alone; resolved with an explicit `replay=True` flag that swaps the inner transport for a `ReplayClient(store_dir)`. A3b-run (the live spike + §4 flip) is the next open item, then F1 single-concept pilot (Sprint 26).

### After Sprint 24 — Phase A Task A3a (concrete `LLMClient` transport + record/replay harness)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/llm_client.py`](../../src/synthetic/llm_client.py) — `LLMConfig` (frozen; temp default `0.0`; `from_config`/`from_env`; stores only the API-key env-var *name*), `HttpLLMClient` (OpenAI-compatible `/chat/completions` over stdlib `urllib.request` + `json`; injectable `sender`; network-fault retry/backoff; fail-loud `LLMTransportError`), `ReplayClient`, `RecordingClient`, `LLMClientError`/`LLMTransportError`, thin `main` `complete` CLI. Slots in *under* the frozen Protocol — no seam edit.
- Added additive LLM transport settings to [`src/utils/config.py`](../../src/utils/config.py) (`LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY_ENV`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`, `LLM_BACKOFF_BASE`, `LLM_TEMPERATURE`, `LLM_CACHE_DIR` under `SYNTHETIC_DATA_ROOT`), all env-overridable; no key value, no I/O.
- Created [`tests/synthetic/test_llm_client.py`](../../tests/synthetic/test_llm_client.py) — 30 hermetic tests + 1 env-gated live smoke.
- Added the `llm_client.py` ✅ row to the "New Files in This Branch" map; Sprint 24 entry prepended to [`RESEARCH_LOG.md`](RESEARCH_LOG.md); [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) §3.5/§5 A3a flipped ✅, A3b annotated pending, §4 model row left `TBD` with the transport-now-exists note.

**Key results / decisions:**
- **A3a (code, hermetic) vs A3b (live, paid, prose) split:** Sprint 24 ships the `complete()` transport + record/replay harness; the live ≥2-model fluency/JSON/cost spike and the §4 model flip are Sprint 25's opening step. A3a *enables* the spike (`RecordingClient` captures each candidate transcript for offline replay); it does not run it. Same discipline as Sprint 23 — build the runnable contract, never fabricate the measured result.
- **One module behind the frozen Protocol:** A3 implements `complete(prompt) -> str` and edits none of the Stage-A seam. **Two retry layers, cleanly separated:** the malformed-JSON resend stays in `llm_proposer.propose`; the transport adds a *separate* network-fault retry.
- **Stdlib transport, no new dependency:** `urllib.request` + `json` against the OpenAI-compatible contract covers the API and local-Llama candidates by config alone.
- **Hermetic suite, env-gated live smoke:** injected sender / `ReplayClient` keep `pytest` socket-free; the live smoke skips-not-fails without `BC3CAT_LLM_LIVE=1` + a key. **No secret leaks:** the key value never enters the store, a log, or an exception message (asserted).
- `pytest tests -q` → **749 passed, 2 skipped** (Sprint 23's 719 + 30 new hermetic; 2 skips = the Sprint-12 `new_param` brace-audit skip + the new live smoke). Zero failures, zero network calls.

**Known issues:** the `LLMClient` Protocol is not `@runtime_checkable`, so conformance is tested as duck-typed acceptance by `propose`, not via `isinstance`. A3b (live spike + §4 flip) is the next open item, then F1 single-concept pilot.

### After Sprint 23 — Phase G Tasks G3 + G4 (release docs: `DATA_CARD.md` + README "Synthetic Variant" + `HANDOFF.md`)
**Date:** 2026-05-20
**What changed:**
- Created [`DATA_CARD.md`](DATA_CARD.md) — Data-in-Brief card for the frozen G1/G2 contract: provenance, the two release files (1:1 on `item_key`), the items schema (exactly the nine `ITEM_COLUMNS`, in order), the sidecar `Modification.to_dict` payload, the 12-type × 4-layer taxonomy, the `modification_types`/`modification_count` + §6 generation-condition slices, the `synthetic.loaders` quickstart (`long_view`/`short_view` `text`+`text_norm` ↔ OEB `_norm`), AI disclosure, limitations, CC-BY-4.0/MIT license, citation. **Every corpus-scale statistic is a marked `TBD (pending F3)` placeholder.**
- Created [`HANDOFF.md`](HANDOFF.md) — cross-repo memo for `bc3cat-retrieval`: file locations + 1:1 join, slice columns + §6 conditions, the loader surface, the `long_view`→`OEB_long_norm`/`short_view`→`OEB_short_norm` mapping, and the "pending A3 + F3" status. Does **not** modify `bc3cat-retrieval`.
- Appended `## Synthetic Variant (BC3CAT-Syn)` to [`README.md`](../../README.md) — additive only; existing sections verbatim.
- Flipped the `DATA_CARD.md` + `HANDOFF.md` rows ✅ in the "New Files in This Branch" map.

**Key results / decisions:**
- **G3 + G4 over A3:** finishes the phase Sprints 21–22 opened; fully unblocked (G1 froze the format, G2 the loader contract — both test-pinned). A3 (LLM transport) is its own Sprint 24.
- **Document the frozen contract; never fabricate corpus statistics:** all schema/taxonomy/slice/loader facts are code-derivable; all corpus-scale numbers are `TBD (pending F3)`. A **post-F3 `DATA_CARD.md` statistics refresh** is the explicit follow-up.
- **Documentation-only — suite unchanged:** no code module, no test, no Markdown doc-drift guard (the schema is already pinned in `test_packaging.py`/`test_loaders.py`). `pytest tests -q` → **719 passed, 1 skipped**, unchanged from Sprint 22.
- **Additive README; handoff points, does not wire;** `synthetic` never merges to `main`.

**Known issues:** none. Phase G documentation complete. Remaining: A3 (Sprint 24) then the Phase F pilot/generation (F1–F4); the post-F3 statistics refresh then fills the `DATA_CARD.md` `TBD`s.

### After Sprint 22 — Phase G Task G2 (loader utilities: `loaders.py` — read API + 1:1 join + long/short views)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/loaders.py`](../../src/synthetic/loaders.py) — the read-only consumer layer over the two G1 release files. `load_items`/`load_modifications` are thin wrappers over `packaging.read_*` (default paths resolved at call time under `SYNTHETIC_PROCESSED_DIR`). `join` re-attaches the ragged sidecar to the flat items frame as an in-memory `modifications` `list[dict]` column on a sorted **copy** — **1:1** on `item_key`, fail-loud `LoaderError` on any unmatched key, no input mutation. `long_view`/`short_view` project to the OEB-style target/query views (`texto`/`resumen`→single `text` col, key+slice metadata, derived `text_norm` via `normalize_text` reused verbatim; no fabricated OEB-only `id`/`ud`/`concept`, no `modifications`). `main(argv)` is a thin `info` CLI. `pandas` imported lazily so the module + stdlib `load_modifications` path stay importable without it; never imports `stage_b`/`run_synthetic`/`stage_runners`/`review`/`mutator`/`layer_*`. **Writes no new on-disk artifact** — projections are in-memory frames.
- Flipped the `loaders.py` row ✅ in the "New Files in This Branch" map.

**Key results / decisions:**
- **G2 over G3/A3:** G2 directly continues G1 and is fully unblocked; G3 docs are better written after the loader API exists; A3 (LLM transport) is its own track. One module per sprint.
- **Read-only, builds on `packaging`, no new artifact:** the file-format contract lives in G1; G2 adds consumer ergonomics. Every projection is in-memory and re-derivable, so G1's "two files are the canonical release" invariant holds.
- **`join()` is the in-memory reunion of what the Parquet deliberately dropped — 1:1 and fail-loud:** a partial release (a key on one side only) raises `LoaderError` before returning, never a silent drop/duplicate; the input frame is not mutated.
- **Views mirror the OEB *record subset*, not its LlamaIndex columns:** `text` + `text_norm` + keys + slice metadata. `text_norm` reuses `normalize_text` verbatim (byte-for-byte consistent with the OEB `_norm` columns), derived in-memory, never stored — the G1-deferred "feats pass" with no new file or dep.
- **`pyarrow` stays gated; the stdlib JSONL path stays always-on** (Sprint 21 rule). The join-mismatch unit is `pandas`-only (no Parquet engine); frame/Parquet tests `importorskip("pyarrow")`.
- `pytest tests -q` → **719 passed, 1 skipped** (was 703 + 1; +16 new); `pyarrow`/data-gated tests skip-never-fail in a bare tree.

**Known issues:** none. G3 (`DATA_CARD.md` / README "Synthetic Variant") and G4 (`HANDOFF.md`) remain; A3 (concrete LLM transport) is the prerequisite for the Phase F real pilot.

### After Sprint 21 — Phase G Task G1 (release packaging: items Parquet + modifications sidecar JSONL)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/packaging.py`](../../src/synthetic/packaging.py) — the durable BC3CAT-Syn release packager. Packages `metadata.join_intermediate()` output into **two files, one key** (protocol §7): `BC3CAT_Syn_items.parquet` (flat columnar, frozen `ITEM_COLUMNS`, one row per item sorted by `item_key`, `params` nested dict, `modification_types` as `list[str]`, no `modifications` column) + `BC3CAT_Syn_modifications.jsonl` (ragged per-`item_key` log; baseline→`[]`), joining 1:1 on `item_key`. `write_release` validates (E2 `validate_items`) **before** any write and re-raises `SchemaError` as `PackagingError` — no partial release on disk. Both writes atomic (`.tmp` rename) + run-twice byte-identical. `read_items_parquet`/`read_modifications_jsonl` are the minimal round-trip read (full loader is G2). `pandas`/`pyarrow` imported lazily so the module + stdlib sidecar path stay importable without them; never imports `stage_b`/`run_synthetic`/`stage_runners`/`review`.
- Flipped the `packaging.py` row ✅ in the "New Files in This Branch" map; flipped `data/synthetic/processed/` + both `BC3CAT_Syn_*` artifact rows ❌ → ✅.

**Key results / decisions:**
- **G1 over F1–F2:** the Phase F real pilot is blocked on A3 (no concrete `LLMClient` transport in the tree); G1 is fully unblocked and consumes `SyntheticItem`s as-is.
- **Items table = §2.3 record + `concept_key`, not the OEB `_feats` schema.** The `_norm`/`_feats` lexical columns are a re-derivable downstream feature-stage product, deferred to G2.
- **`parent_key`-column deviation (documented):** the sprint's decision-2 column list named `parent_key`, but neither the canonical §2.3 record nor the `SyntheticItem` dataclass carries one — `SyntheticItem` exposes only `concept_key` (the `$`-terminated concept group key). `ITEM_COLUMNS` ships the §2.3 record + `concept_key` only; an explicit `parent_key` would be a one-line G2-loader derivation, not a packaging concern.
- **One row per item with both `resumen` + `texto`** (not the OEB long/short two-file split); the long/short projection is a G2 loader one-liner.
- **`pyarrow` is the synthetic suite's first non-stdlib dep — gated, not failed.** Parquet tests `importorskip("pyarrow")`; sidecar JSONL tests stay always-on stdlib. `pandas`/`pyarrow` are already a main-pipeline dependency (no new repo dep).
- `pytest tests -q` → **703 passed, 1 skipped** (was 683 + 1; +20 new); `pyarrow`/data-gated tests skip-never-fail in a bare tree.

**Known issues:** none. G2 (loaders + long/short projection) and G3 (`DATA_CARD.md` / README) remain; A3 (concrete LLM transport) is the prerequisite for the Phase F real pilot.

### After Sprint 20 — Phase E Tasks E3 (validation sampler) + E4 (reviewer harness)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/review.py`](../../src/synthetic/review.py) — the quality-gate machinery. **E3:** `stratify` buckets `SyntheticItem`s into `(concept_key, ModificationType)` cells (baselines `modification_count == 0` excluded; a stacked item is a member of *each* of its types' cells); `sample_review_queue` draws a seeded, deterministic, de-duplicated queue — full coverage for `new_param`, otherwise `min(size, max(floor, ceil(coverage·size)))` per cell — returning `(list[ReviewTask], CoverageReport)`. **E4:** `Verdict` (four dimensions; `axis_distinguishable` is `Optional[bool]`, `None` off `new_param`) + `write_verdicts`/`read_verdicts` (JSONL keyed by `(item_key, reviewer)`, fail-loud duplicate) + `agreement` (percent + hand-rolled Cohen's κ over the ≥2-reviewer subset). `ReviewError(ValueError)` is the distinct failure type; `main(argv)` is a thin `build`/`agree` argparse CLI.
- Added `SYNTHETIC_REVIEW_DIR = SYNTHETIC_DATA_ROOT / "review"` to [`../../src/utils/config.py`](../../src/utils/config.py) (queue + verdict JSONL home).
- Recorded the stratum key `(concept_key, modification_type)`, the 100 %-`new_param` rule, and the coverage/floor defaults (`coverage=0.10`, `floor=5`) on the `review.py` row above.
- Created [`tests/synthetic/test_review.py`](../../tests/synthetic/test_review.py) (28) — 27 always-on (stratify cells/baseline-exclusion/stacking, the four floor/fraction + full-`new_param` sampling cases, seeded determinism, de-dup-to-one-task, coverage-report consistency, queue + verdict JSONL round-trips + atomic write, fail-loud duplicate verdict, percent + hand-checked κ=0.6 agreement, axis-only-over-`new_param`, single-reviewer exclusion, CLI no-subcommand exit, import-hygiene + no-side-effects audits) + 1 data-gated real-concept sample on `OBRA CIVIL`.

**Key results:**
- `pytest tests -q` → **683 passed, 1 skipped** (was 654 + 1; +28 always-on, +1 data-gated; the lone skip is Sprint 12's `new_param` brace audit). Data-gated review-sample ran (OBRA CIVIL present).

**Decisions made and rationale:**
- **Stratify by `(concept, type)`, queue by `item_key`.** Coverage is a per-cell property; reviewer effort is a per-item property — reconciled by de-duplicating the per-cell draws into one task per item, whose `strata` lists every cell it was a candidate for.
- **`new_param` is the 100 %-review type** (highest semantic-collision risk, proposal §4); the policy is the tunable `full_coverage_types` argument defaulting to `{NEW_PARAM}`, not a hard-coded constant. Coverage/floor are arguments seeded with the proposal §10.3 defaults.
- **Sampling is seeded-deterministic** (`random.Random` over a per-cell string seed of sorted `item_key`s) — a review queue must be reproducible so a re-run does not reshuffle reviewer assignments.
- **Agreement only where there is agreement to measure** — percent + Cohen's κ over the ≥2-reviewer subset; `axis_distinguishable` only over the `new_param` subset (verdicts where it is non-`None`). κ is `None` when undefined.
- **E4 reviews the diff, not the baseline.** Semantic-preservation review works off the per-`Modification` `original`/`new` fragments + synthetic text already in the record; full original-vs-synthetic re-expansion is baseline-dependent and deferred to F4 (same deferral Sprint 19 made for the `original_key`-existence cross-check). `review.py` imports neither `stage_b`/`run_synthetic`/`stage_runners` nor re-expands the catalog.

**Known issues / deferred:**
- Running a real validation pass + writing `docs/synthetic/QUALITY_REPORT.md` is **F4** — E3/E4 build the sampler + harness; *using* them on real reviewers' verdicts is Phase F.
- Parquet + sidecar JSONL release packaging is **G1** — the queue + verdicts are reviewer-workflow JSONL, not the release artifact.
- The data-gated test uses a baseline (no-rule) variant, so its queue is empty by construction (all items are baselines); the sampling logic itself is exercised by the always-on tier.

### After Sprint 19 — Phase E Tasks E1 (metadata join) + E2 (schema validator)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/metadata.py`](../../src/synthetic/metadata.py) — `@dataclass(frozen=True) SyntheticItem` + `to_dict()` (proposal §2.3 shape, no `concept_key` key). `join_variant_payload` fans a variant's modification log out across its leaves (one record per `(leaf_key, item)`); `join_variant_file` / `join_intermediate` walk the on-disk per-variant JSON in sorted, deterministic order. `validate_item` / `validate_items` + `SchemaError(ValueError)` are the fail-loud E2 surface. Imports stdlib + `taxonomy` + `utils.config` only — never `stage_b` / `run_synthetic`.
- Recorded the per-item join-key triple `(item_key, original_key, variante_id)` and the `original_key = leaf_key[:-K]` rule next to the `Modification`-record schema above.
- Created [`tests/synthetic/test_metadata.py`](../../tests/synthetic/test_metadata.py) (29) — 28 always-on (L1 / PD-stacked / all-skipped fixtures, per-class fail-loud validator cases, import-hygiene + no-side-effects audits) + 1 data-gated `stage_b → join → validate` roundtrip on a real `OBRA CIVIL` concept.

**Key results:**
- `pytest tests -q` → **654 passed, 1 skipped** (was 626 + 1; +28 always-on). The data-gated roundtrip ran (OBRA CIVIL data present): every baseline-variant `SyntheticItem` has `modification_count == 0` and an `original_key` that is a real chapter stage-5 leaf key.

**Known issues / deferred:**
- Parquet + sidecar JSONL serialization (`BC3CAT_Syn_items.parquet` / `BC3CAT_Syn_modifications.jsonl`, the `pyarrow` dependency) is **Phase G (G1)** — E1 returns in-memory `SyntheticItem` records + `to_dict()`.
- `original_key` is validated *structurally* (prefix-of-leaf-segment); cross-checking it names an actually-existing baseline catalog row is deferred to F4/G1.
- Stratified validation sampler + reviewer harness (`review.py`, E3–E4) is Sprint 20.

### After Sprint 18 — Phase D Tasks D2 (Stage-B half) + D3 (cache hygiene)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/stage_b.py`](../../src/synthetic/stage_b.py) — the Stage-A→Stage-B join. `apply_variant_rules` partitions a variant's pre-composed rules by layer and threads the single-concept stage-2 dict through **PD → L1 → L2 → L3** (skip-and-log per non-applying rule); `materialize_variant` slices `{concept_key: …}`, applies, runs `run_stages_3_to_7` once, and wraps the result in a frozen `MaterializedVariant`; `materialize_catalog_entry` / `run_stage_b` write one atomic JSON per variant under `data/synthetic/intermediate/{concept}/{variant_id}.json`.
- Created [`src/synthetic/cache_hygiene.py`](../../src/synthetic/cache_hygiene.py) — `stale_cache_paths` (pure) + `clear_caches` (dry-run default, opt-in deletion).
- Created [`tests/synthetic/test_stage_b.py`](../../tests/synthetic/test_stage_b.py) (28) + [`tests/synthetic/test_cache_hygiene.py`](../../tests/synthetic/test_cache_hygiene.py) (10) — 38 always-on + 1 data-gated stage-5-granularity slice-equivalence test.
- **Corrected the "four injection points" framing to one parent-level injection** — see the Stage-Hook Integration Note above. Re-asserted (did not delete) the Sprint-16 no-`mutator`-import tripwire; added a new audit that `stage_b` does not import `run_synthetic`. Added a cache-hygiene section to [`../../CLAUDE.md`](../../CLAUDE.md).

**Key results:**
- `pytest tests -q` → **626 passed, 1 skipped** (was 588 + 1; +38 always-on). Data-gated slice-equivalence passes against the committed `OBRA_CIVIL_stage5.json`.

**Known issues / deferred:**
- The flat Parquet/JSONL release schema (`metadata.py`, Phase E / Task G1) — Stage B emits **raw** per-variant JSON; the join is Sprint 19+.
- Synthetic dedup is **per-variant** by design (chapter-wide dedup was a packaging artefact); the rerun gate is at stage-5, not stage-7.

### After Sprint 17 — Phase D Task D1: stage hooks (`stage_runners.py`) + golden equivalence harness
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/stage_runners.py`](../../src/synthetic/stage_runners.py) — importable, pure, in-memory stage runners extracted **verbatim** from the s03/s04/s05/s07 notebook cores. Public surface: `run_stage3` (Cartesian expansion), `run_stage4` (text-variable resolution, both passes), `run_stage5` (template instantiation + field filter), `run_stage7` (in-memory dedup, mark+filter fused, no IO), `run_stages_3_to_7` (chains the four, **s06 skipped**, no rule injection). Each runner deep-copies its input, does no disk IO, has no import-time side effects, and imports nothing from the synthetic mutation stack.
- Refactored s03/s04/s05/s07 to `import` their core transform from `stage_runners`, keeping each notebook's own file-IO / chunking / logging driver cells. s07's `marcar_duplicados` / `filter_json` now delegate to the pure `_mark_duplicates` / `_filter_json`.
- Created [`tests/synthetic/test_stage_runners.py`](../../tests/synthetic/test_stage_runners.py) — 27 always-on unit tests + a 4-test data-gated golden tier proving each runner reproduces the committed `OBRA_CIVIL_stage{3,4,5,7}.json`.
- **Formula-translate reconciliation (surfaced, not silently resolved):** s04's inline `translate_formula_to_python` had drifted from the canonical `utils.z_formula_processing` export (no `=`→`==` map, `\b`-anchored ops, no `quote_second_term` call). Empirically the inline variant matches golden (0 mismatches/8k) while the util mismatches 324 (it turns `==`→`====`). `run_stage4` preserves the inline semantics (`_translate_formula_to_python_s04`) to keep golden byte-equivalence; full diff + rationale in the Sprint 17 RESEARCH_LOG entry.
- Edited this file — added the `stage_runners.py` row to the "New Files in This Branch" map, retargeted the `run_synthetic.py` rerun note to Sprint 18, prepended this entry.
- Prepended a Sprint 17 entry to [`docs/synthetic/RESEARCH_LOG.md`](RESEARCH_LOG.md).

**Key results:**
- `pytest tests -q` → **588 passed, 1 skipped** (was 557 + 1; +31 new, the lone skip is Sprint 12's `new_param` brace-audit). Golden stage files reproduced byte-for-byte modulo JSON normalisation (a `tuple` from `eval()` of a comma-list serialises to the same array — comparison is JSON-normalised per item).

**Known issues / deferred:**
- The Stage-B rerun (apply catalog rules across the four injection points, interleave `mutator.apply_*` between these runners, emit raw items into `data/synthetic/intermediate/`) + D3 cache hygiene → Sprint 18.
- Whether to reconcile the repo-wide `utils.z_formula_processing` translate to the notebook behaviour (or vice-versa) is left open — out of scope for D1's faithful extraction.

### After Sprint 16 — Phase D Task D2 (Stage-A half): synthetic orchestrator (`run_synthetic.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/run_synthetic.py`](../../src/synthetic/run_synthetic.py) — the concept-loop driver that wires the Sprint-12–15 Stage-A primitives together and populates the variant catalog. Public surface: `CONDITION_SPECS` (module-level constant, 17 condition labels, built from the enum by `_build_condition_specs()`); `ConditionSpec` / `Attempt` / `VariantPlan` frozen dataclasses; `plan_concept_variants(stage_json, concept_key, conditions, *, rng)` (pure, deterministic planner — `single_*`/`new_param_only` exhaustive over `enumerate_targets`, `stacked_n`/`full_random_mix` sampled via the threaded `rng`); `run_variant` (per-attempt render→`propose_variant`→`emit_rules`, then a single `compose_rules` over the accumulated batch; one `ProvenanceRecord` per attempt; `VariantRecord` only if admissible rules survive composition); `run_concept` (seeds `random.Random(seed)`, aggregates into one `VariantCatalogEntry`, `write_catalog_entry`); `run_catalog` (outer loop; each concept gets a stable `sha256`-derived per-concept seed via `_seed_for` so sampling is independent of batch composition). Module constants `ALL_TYPES`, `MAX_MIX_DEPTH=5`, `_L1_TYPES`/`_L2_TYPES`/`_L3_TYPES`.
- **Stage-A close, not Stage-B.** The orchestrator composes and catalogs admissible, ordered rules; it does **not** apply them. `compose_rules` (state-blind rule-vs-rule: same-target dedup, layer-dependency conflict, PD→L1→L2→L3 ordering) belongs in Stage A; `mutator.apply_*` (rule-vs-data, needs live stage JSON, interleaved across the four injection points) is Sprint 17, gated on D1 stage hooks. A test asserts `run_synthetic` never imports `mutator`.
- **Determinism is threaded, never global.** Every sample goes through the passed `random.Random`; `_seed_for` uses `sha256` (stable across processes, unlike per-process-salted `hash()`). Pinned by run-twice-equal and batch-size-invariant tests.
- Created [`tests/synthetic/test_run_synthetic.py`](../../tests/synthetic/test_run_synthetic.py) — 31 functions: condition-matrix shape (key set, singleton singles + layer-tag match, stacked depths, pool membership); planner (exhaustive singles, no-target graceful skip, monotonic variant ids, run-twice determinism, stacked distinct/degraded, mix depth bounds); `run_variant` (per-attempt provenance, success lands rules, all-skipped lands no record, unmatched→skip, compose-not-apply collision, no-mutator audit, provenance payload/skip); `run_concept` (one file, round-trip, resumen/parent_key, end-to-end `layer_l1.apply_synonym_label` gate, same-seed determinism); `run_catalog` (one file per concept, order-stable, per-concept-seed stable across batch size); `_seed_for` pinned value; import no-side-effects.
- Edited this file — flipped `run_synthetic.py` ❌ → ✅ in the "New Files in This Branch" map (Stage-A-half annotation); prepended this entry.
- Appended a Sprint 16 entry to [`docs/synthetic/RESEARCH_LOG.md`](RESEARCH_LOG.md).

**Key results:**
- `pytest tests -q` → **557 passed, 1 skipped** (was 526 + 1; +31 new, the lone skip is Sprint 12's `new_param` brace-audit). Zero failures, zero new skips, zero changes to surviving tests or prior `src/synthetic/*.py` modules.

**Known issues / deferred:**
- Rule application + the s03→s07 rerun + raw-item emission (Stage-B half of D2) and D1 stage hooks → Sprint 17.
- PD `var_definition` / `template_patch` still catalogued as raw `metadata.*` strings (full parse lands when the Stage-B rerun needs it). Per-concept budgets (`variant_budgets.yaml`) → Phase F. `new_param_allowlist.yaml` still deferred (`allowlist` slot stays `"[]"`).

### After Sprint 15 — Phase C Task C4 (variant catalog) + slot-extraction shim + payload-to-rule lift
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/slot_extractor.py`](../../src/synthetic/slot_extractor.py) — new module exposing `enumerate_targets(stage_json, concept_key, mtype) -> Iterator[Any]`, `extract_slots(stage_json, concept_key, mtype, target_id) -> dict[str, Any]`, and `concept_resumen(stage_json, concept_key) -> str`. Per-type target shapes: L1 single axis key (e.g., `"B"`); L2 `(var_key, condition)` tuple parsed from `text_variables[var_key]` via the narrow `_parse_l2_formula` regex; L3-omission `(field, var_token)`; L3-reorder field (string); PD single `None`. Per-type slot shapes match `variant_proposer.EXPECTED_SLOTS[mtype]` exactly. L2 fragments are picked by looking up `condition` in the parsed `"literal" * (cond)` table. Omission's `axis_label` is best-effort: walks `text_variables[var_to_omit]` for the first `%<axis>=` reference and returns the matching parameter label, or `""` if not derivable. Reorder's `constituents` is `"; "`-joined sorted-unique `$<letter>` tokens. PD's `existing_axes_with_labels` is `"; "`-joined `"key: label"`; `allowlist` is the placeholder `"[]"` (the YAML loader is still deferred per Sprint 14). Both lowercase (`resumen`/`texto`) and uppercase (`RESUMEN`/`TEXTO`) field keys are tolerated via `_field_text`. No import from `src/utils/z_formula_processing.py`.
- Created [`src/synthetic/rule_emitter.py`](../../src/synthetic/rule_emitter.py) — new module exposing `EmissionResult(rules: tuple[dict, ...], unmatched: tuple[dict, ...])` frozen dataclass and `emit_rules(payload, modification_type, *, target_id, stage_json, concept_key) -> EmissionResult`. Per-type private emitters: `_emit_l1` (one rule per `synonyms` / `numerals` entry; cross-references `entry["original"]` against the target axis's `value` field via a `{value: label}` lookup; LLM typos with no match ride in `EmissionResult.unmatched`); `_emit_l2` (one rule per call; carries `var`/`condition` from `target_id` and `new` from payload); `_emit_l3_omission` (carries `field`/`original`/`new`); `_emit_l3_reorder` (same shape); `_emit_new_param` (allocates first free A-Z axis letter via `_allocate_axis_key`; carries `param`/`label`/`values`; raw `var_definition` and `template_patch` strings ride as nested `metadata.*` fields — full FIEBDC-formula + template-anchor parse deferred to Sprint 16). `_allocate_axis_key` raises `ValueError("no_free_axis_letter")` when all 26 letters are taken (defensive; BC3 catalogs cap well below). No `compose_rules` invocation; emission and composition are separate concerns.
- Created [`src/synthetic/variant_catalog.py`](../../src/synthetic/variant_catalog.py) — new module exposing `VariantCatalogEntry`, `VariantRecord`, `ProvenanceRecord` (all `@dataclass(frozen=True)`), `write_catalog_entry(entry, out_dir) -> Path`, and `read_catalog_entry(path) -> VariantCatalogEntry`. Writer: `out_dir.mkdir(parents=True, exist_ok=True)` then `tmp.write_text(json.dumps(...indent=2, ensure_ascii=False) + "\n")` then `os.replace(tmp, final)` — atomic on POSIX, best-effort-atomic on Windows (`MoveFileExW(MOVEFILE_REPLACE_EXISTING)`). Reader: strict `json.loads` + `Modification.from_dict` + `ModificationType` enum coercion; raises on malformed JSON or missing top-level keys. Round-trip-safe: `read(write(entry)) == entry`.
- Added three new test files. **78 individual test cases**, 36 functions:
  - [`tests/synthetic/test_slot_extractor.py`](../../tests/synthetic/test_slot_extractor.py) — 14 functions, ~30 cases. Public surface; `concept_resumen` lowercase/uppercase/missing; per-type enumerator (L1 ×6 parametrised; L2; L3-omission; L3-reorder including empty-field skip; PD); `extract_slots` ×12 round-trip against `EXPECTED_SLOTS`; L1 value-list format; L2 fragment lookup; L3-omission axis-label derivation (binding + empty); L3-reorder constituents format; PD allowlist placeholder; L2 unknown-condition raises; `_parse_l2_formula` empty-match raises; `_field_text` lowercase + missing; `importlib.reload` no-side-effects.
  - [`tests/synthetic/test_rule_emitter.py`](../../tests/synthetic/test_rule_emitter.py) — 16 functions, ~33 cases. Public surface; L1 happy-path ×6; L1 multi-entry emission (3 rules from 3 entries); L1 unmatched (LLM typo) diagnostic; L1 value-label (not value-string) audit; L1 empty list → empty result; L2 happy-path ×3; L2 var+condition pin; L3-omission rule shape; L3-reorder rule shape; PD axis allocation A→D; PD axis-allocation gaps (A, C, E → B); PD 26-axis exhaustion raises; PD metadata raw-string passthrough; PD `values` copy-not-reference; `EmissionResult` frozen; dispatcher ×12 across `ModificationType`; `importlib.reload` no-side-effects.
  - [`tests/synthetic/test_variant_catalog.py`](../../tests/synthetic/test_variant_catalog.py) — 15 functions, 15 cases. Public surface; writes-at-expected-path; auto-creates `out_dir`; round-trip write→read equality; overwrite-existing-file; atomic-on-replace-failure (`monkeypatch.setattr(os, "replace", raise OSError)` — final absent, tmp present); on-disk `modification_type` is `value` string; on-disk lists vs in-memory tuples; frozen dataclasses; provenance `validated_payload ⊕ skipped` invariant; malformed-JSON read raises; missing-keys read raises; `skipped` modifications round-trip with reason-prefix; `importlib.reload` no-side-effects.
- Edited [`docs/synthetic/CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md) (this file) — added three new rows (`slot_extractor.py`, `rule_emitter.py`, `variant_catalog.py`) under the existing `variant_proposer.py` row in the "New Files in This Branch" section; flipped `data/synthetic/variants/` row ❌ → ✅ with the annotation pointing at `variant_catalog.write_catalog_entry`. Prepended this "After Sprint 15" entry to the Sprint History section.
- Appended a Sprint 15 entry to [`docs/synthetic/RESEARCH_LOG.md`](RESEARCH_LOG.md).

**Key results:**
- `pytest tests -q` → **526 passed, 1 skipped in 0.38s, zero failures.** Baseline 448 (Sprint 14); net delta +78 cases (36 new functions × parametrisation expansion). The skip count stays at exactly 1 (Sprint 12's intentional `new_param` brace-audit skip — no new skips). Sprint plan's "≥40 new test functions / ≥488 total passed" gate is satisfied with comfortable margin (36 functions × parametrisation = 78 cases / 526 total).
- `from synthetic.slot_extractor import enumerate_targets, extract_slots, concept_resumen` succeeds. `from synthetic.rule_emitter import emit_rules, EmissionResult` succeeds. `from synthetic.variant_catalog import (VariantCatalogEntry, VariantRecord, ProvenanceRecord, write_catalog_entry, read_catalog_entry)` succeeds.
- **End-to-end smoke (PowerShell-equivalent, ran via Bash)** — `enumerate_targets → extract_slots → emit_rules → apply_synonym_label → VariantCatalogEntry → write_catalog_entry → read_catalog_entry` all chained successfully against a single-axis fixture. The emitted rule for `synonym_label` was consumed by `layer_l1.apply_synonym_label` without raising — the rule shape lifted by the emitter matches the Phase-B mutator's expected schema. Round-trip equality `read(write(entry)) == entry` held.
- **No changes** to any `layer_*.py`, to `mutator.py`, to `composition.py`, to `taxonomy.py`, to `src/synthetic/prompts/`, to `src/synthetic/llm_proposer.py`, or to `src/synthetic/variant_proposer.py`. Sprint 15 is purely additive — three new module files plus three test files (+ two documentation files updated).

**Decisions confirmed:**
- **Three modules, one sprint.** Slot extractor, rule emitter, and catalog writer share the per-concept context (stage JSON walk → slots dict → validated payload → emitted rules → final `Modification` records). Splitting into three sprints would force a temporary intra-sprint shim per boundary; bundling keeps the information-flow boundaries sharp while preserving independent test surfaces (one test file per module).
- **`enumerate_targets` is sorted-deterministic.** L1 axes by axis key; L2 by `(var_key, condition)`; L3-omission by `(field, var_token)`; L3-reorder by field. Set iteration was PYTHONHASHSEED-randomized — same trap Sprint 6.5 fixed in `s07_Filter_duplicates.ipynb`. Pinned by per-type tests.
- **`extract_slots` returns a dict matching `EXPECTED_SLOTS[mtype]` exactly.** Binding round-trip with Sprint 14: `set(extract_slots(...).keys()) == EXPECTED_SLOTS[mtype]` for every `(stage_json, concept_key, mtype, target_id)` tuple `enumerate_targets` produces. Pinned by `test_extract_slots_matches_expected_slots_per_type` ×12.
- **`EmissionResult` is the right return type — not bare `list[dict]`.** A bare list would hide the unmatched-payload diagnostic; a raise-on-mismatch contract would couple per-entry-failure handling into the caller. The frozen dataclass keeps the caller's path uniform: success → rules tuple populated, unmatched tuple empty; partial → both populated.
- **L1 rule cross-references `value` (not `label`).** The C3 prompt speaks in human-readable terms (`Normal`, `Rocoso`); the parameters block's `value` field is the matching key, `label` is the per-axis code letter (`a`, `b`). The rule emitter does the indirection — `original="Normal"` is looked up in `{value: label}` to fill `rule["value"] = "a"`. Pinned by `test_emit_l1_rule_carries_value_label_not_value_string`.
- **LLM typos diverted to `EmissionResult.unmatched`, not raised.** A `{"original": "Stándard"}` entry with no matching value appends to `unmatched`; the rest of the synonyms still produce rules. Drift-handling is intentional — no silent drop (the diagnostic is visible), no raise (one bad entry doesn't kill the batch). Pinned by `test_emit_l1_unmatched_original_rides_in_unmatched_list`.
- **PD ships partial credit.** The structural fields (`param`, `label`, `values`) are emitted; the raw `var_definition` and `template_patch` strings ride as `metadata.var_definition` / `metadata.template_patch`. The minimal rule is applicable by `layer_pd.apply_new_param` because `text_variable` and `template_patches` are optional in the PD rule schema. Parsing the FIEBDC formula grammar + anchoring the template patch is Sprint 16's scope. The catalog file still records the raw LLM strings, so a future re-parse can hydrate the optional fields without re-querying the LLM.
- **`_allocate_axis_key` is alphabetical-first-free.** Picks the first uppercase letter not in the existing `parameters` block (A→Z scan). The 26-axis cap raises `ValueError("no_free_axis_letter")` defensively; BC3 catalogs cap well below. Pinned by happy (A,B,C → D), gaps (A,C,E → B), and stress (full A-Z → raise) tests.
- **Atomic catalog writes via tmp + `os.replace`.** Defensive against interrupted writes (Ctrl-C, OOM, machine reboot mid-write). `tmp.write_text` then `os.replace`; if replace raises, the `.tmp` file is the only artifact left. Pinned by `test_write_catalog_entry_is_atomic_on_replace_failure` (monkeypatch `os.replace` to raise; assert final absent, tmp present).
- **Catalog file format is JSON, not Parquet.** Per-concept files are small (one concept × handful of variants × per-attempt provenance = a few KB); the read side is human-eyeball diagnostic, not bulk-analysis. Parquet would optimise the wrong axis. A `materialize_catalog_to_parquet` aggregator can land later if Phase F needs bulk querying — it doesn't here.
- **`_parse_l2_formula` regex is narrow by design.** Matches `"<literal>" * (<condition>)` and nothing else. The richer FIEBDC operator grammar (conditional chains, nested parens) lives in `src/utils/z_formula_processing.py`. The L2 slot extractor only needs the literal-by-condition table — anything richer is overkill for the slot extraction case. Pinned by `test_parse_l2_formula_unparseable_raises`.
- **Both `resumen`/`texto` (lowercase) and `RESUMEN`/`TEXTO` (uppercase) keys are accepted.** Lowercase is the pipeline's canonical post-s05 shape; uppercase is the BC3 grammar key and the test fixtures' style. `_field_text` does the case-fold lookup. Tested explicitly.
- **No module-level side effects.** No env reads, no on-import I/O, no `out_dir` resolution at import time. Same Sprint 13/14 convention; pinned per module via `importlib.reload`.
- **No new runtime dependencies.** Stdlib + in-repo only. Same Sprint 13/14 rationale.
- **No live LLM, no real stage-JSON IO in tests.** All fixtures are inline literal dicts. Real-stage-JSON smoke is the orchestrator's problem (Sprint 16+) or a Phase F pilot concern.

**Known issues:**
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (`526 passed, 1 skipped` prints before the traceback). Cosmetic; no action.
- PD rule emission ships partial credit: `var_definition` and `template_patch` are raw pass-through strings under `metadata.*`. The full FIEBDC formula parser + template anchor heuristic is Sprint 16's scope.
- `new_param_allowlist.yaml` is still not authored; the `allowlist` slot stays the placeholder `"[]"`. Phase B4 follow-up.

**Next step:** **Sprint 16 — Phase D Task D2 (`run_synthetic.py` — orchestrator).** Wire the concept-loop driver that ties `prompts.load_prompt` → `variant_proposer.propose_variant` → `slot_extractor.{enumerate_targets, extract_slots}` → `rule_emitter.emit_rules` → `composition.compose_rules` → `mutator.apply_*` → `variant_catalog.write_catalog_entry` together. The per-concept condition matrix (`single_L1_*`, `single_L2_*`, `single_L3_*`, `new_param_only`, `stacked_2..5+`, `full_random_mix`) is D2's natural home. A natural Sprint 16+ follow-up is widening the PD rule emitter to parse `var_definition` and `template_patch` strings into the optional `text_variable` / `template_patches` rule fields (so the orchestrator's `apply_new_param` call gets the full PD effect, not just the param/label/values structural minimum).

---

### After Sprint 14 — Phase C Task C3: variant proposer (`variant_proposer.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/variant_proposer.py`](../../src/synthetic/variant_proposer.py) — new module exposing `VariantProposal` (`@dataclass(frozen=True)` with fields `payload: Optional[dict]`, `raw_responses: tuple[str, ...]`, `skipped: Optional[Modification]`), `propose_variant(prompt_template, slots, client, modification_type, *, retry_once=True) -> VariantProposal`, and the `EXPECTED_SLOTS: dict[ModificationType, frozenset[str]]` constant (one entry per `ModificationType`, in lockstep with Sprint 12's `tests/synthetic/test_prompts.py::_EXPECTED_PLACEHOLDERS`). Private helpers `_render_prompt` (JSON-aware brace renderer — pre-escape every `{`/`}` to `{{`/`}}`, then selectively un-escape the declared placeholders, then `str.format_map(slots)`) and `_validate_payload` (per-type structural validator dispatching across `_validate_pair_list` for the six L1-style `synonyms`/`numerals` payloads, `_validate_original_new_preserves` for `paraphrase`/`expansion`/`compression`/`reorder`, `_validate_omission` for `{"original", "new", "omitted_var"}`, and `_validate_new_param` for the PD payload with a `2 ≤ len(values) ≤ 5` bound matching the prompt's "entre 2 y 5 valores discretos" wording). Three terminal shapes: success (validated payload + `skipped=None`), C2 fallback (`skipped.reason.startswith("malformed_llm_response_after_retry: ")`), and C3 schema-validation failure (`skipped.reason.startswith("schema_validation_failed: ")`). `propose_variant` never raises on LLM- or schema-failure paths; `_render_prompt` does raise (`KeyError` on missing slots, `ValueError` on extra slots) because those are catalog-authoring programming errors at build time. Stdlib-only imports (`dataclasses`, `typing`); two in-repo imports (`llm_proposer.{LLMClient, propose}`, `taxonomy.{Modification, ModificationType, TYPE_TO_LAYER}`).
- Added [`tests/synthetic/test_variant_proposer.py`](../../tests/synthetic/test_variant_proposer.py) — 30 contract test functions; with parametrisation expansion (×12 over `ModificationType` for happy-path, ×12 over `ModificationType` for schema-violation, ×4 over `original/new/preserves_meaning` types, ×3 over `omission` missing-key flavours, ×4 over `new_param.values` out-of-range lengths, ×9 over malformed/wrong-shape stub responses) the total is **86 individual cases**. Coverage: public-surface import audit; `EXPECTED_SLOTS` covers all 12 `ModificationType` members; cross-file lockstep audit (every declared slot appears as `{name}` in the corresponding prompt body before the `Responde SOLO con un JSON` marker); per-type happy path; per-type schema-violation skip emission; C2-fallback propagation; two-skip-prefix distinguishability; slot substitution + JSON-literal brace preservation (synthetic templates + the real `new_param.txt`); slot/placeholder mismatch raises (`KeyError`/`ValueError`); per-validator-helper happy + sad paths (missing key / wrong inner shape / empty list / non-str value / not-list / `bool`-not-`int` for `preserves_meaning` / `new_param.values` length bounds [0,1,6,7] / `new_param.values` inner-shape rejection / `new_param` missing top-keys); `raw_responses` propagation (single-success / retry-success); `retry_once=False` short-circuit; never-raises across nine malformed stub responses; `FrozenInstanceError` on `VariantProposal.payload` reassignment; equality of two structurally-identical proposals; `importlib.reload` no-side-effects; rendered-prompt passthrough verbatim with slot-value count assertions; skip-record other-fields-are-None on validation failure.
- Edited [`docs/synthetic/CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md) (this file) — added a new `variant_proposer.py` row under the existing `llm_proposer.py` row in the "New Files in This Branch" section with annotation "✅ Sprint 14 — Task C3 — `propose_variant` + per-type schema validation + JSON-aware template renderer; slot-extraction and payload-to-Phase-B-rule emission deferred to Sprint 15", and dropped the "; C3 still ❌" suffix from the `llm_proposer.py` row now that C3 lands in its own row. Prepended this "After Sprint 14" entry to the Sprint History section.
- Appended a Sprint 14 entry to [`docs/synthetic/RESEARCH_LOG.md`](RESEARCH_LOG.md).

**Key results:**
- `pytest tests -q` → **448 passed, 1 skipped in 0.35s, zero failures.** Baseline 362 (Sprint 13); net delta +86 (30 new functions × parametrisation expansion). The skip count stays at exactly 1 (Sprint 12's intentional `new_param` brace-audit skip — no new skips). Sprint plan's "≥25 new test functions / ≥392 total passed" gate is satisfied with comfortable margin (30 functions / 448 total).
- `from synthetic.variant_proposer import VariantProposal, propose_variant, EXPECTED_SLOTS` succeeds. `len(EXPECTED_SLOTS) == 12`; `set(EXPECTED_SLOTS) == set(ModificationType)`. Happy-path smoke: `propose_variant(tmpl, slots, _StubLLMClient([json.dumps({"synonyms": [{"original": "Normal", "new": "Estándar"}]})]), ModificationType.SYNONYM_LABEL).payload == {"synonyms": [...]}`. C3 schema-violation smoke: stub returning `'{"unrelated": []}'` → `result.skipped.reason == "schema_validation_failed: missing_key: 'synonyms'"`. C2-fallback propagation smoke: stub `["junk1", "junk2"]` → `result.skipped.reason.startswith("malformed_llm_response_after_retry: ")`. Cross-file lockstep audit (`test_expected_slots_matches_prompt_audit` ×12) passes for every `ModificationType`, confirming Sprint 12's prompt placeholders and Sprint 14's `EXPECTED_SLOTS` are byte-aligned.
- **No changes** to any `layer_*.py`, to `mutator.py`, to `composition.py`, to `taxonomy.py`, to `src/synthetic/prompts/`, or to `src/synthetic/llm_proposer.py`. C3 is purely additive — one new module file plus its test file (+ two documentation files updated).

**Decisions confirmed:**
- **Render → propose → validate is the right pipeline.** Three pure functions composed by `propose_variant` (the orchestrator). Each helper has a narrow contract and a tight test surface. Symmetric with Sprint 13's "C2 owns parse + retry, C3 owns shape".
- **Brace-escape uses pre-escape + selective un-escape, not split-at-marker.** The alternative "split the template at `Responde SOLO con un JSON` and only format the prefix" would couple the renderer to that exact phrase — if a future prompt drops or rewords it, the splitter silently mis-classifies. Pre-escape is marker-agnostic. Pinned by `test_render_handles_nested_json_in_new_param_prompt`, which exercises the renderer against the *real* `new_param.txt` (the only prompt Sprint 12 had to exempt from its no-stray-braces audit) and confirms the JSON literal block survives intact.
- **`EXPECTED_SLOTS` is a module-level production constant; `test_prompts.py::_EXPECTED_PLACEHOLDERS` is the test-side declaration; the cross-file audit test is the binding contract.** Drift between them is caught by `test_expected_slots_matches_prompt_audit`, which loads each prompt off disk and re-checks the production constant against the prompt body. If a future sprint adds a new `ModificationType`, both constants must update together — and the audit fires if they don't.
- **`_validate_payload` is shape-only, by intent.** Reviewer-grade validation (does this paraphrase preserve meaning? is this synonym idiomatic technical Spanish? does the omission produce grammatical text? are the new axis values distinct from existing ones?) is Phase E's reviewer harness. C3's schema check is the contractually-pinned shape — dict-shape, key presence, value types, and (for `new_param`'s `values`) the 2..5 length bound — nothing more.
- **Two distinguishable skip-reason prefixes.** `"malformed_llm_response_after_retry: "` (C2 fallback — LLM never produced parseable JSON) vs. `"schema_validation_failed: "` (C2 succeeded but shape was wrong). Phase E1's metadata pipeline grep on the prefix to count failure families per `ModificationType`. Pinned by `test_two_skip_prefixes_are_distinguishable` (non-overlapping substring assertion) and by the per-prefix happy/sad-path tests.
- **`propose_variant` never raises on LLM- or schema-failure paths.** Uniform-return-value contract — the orchestrator (D2) walks `result.payload` / `result.skipped` without `try`/`except`. But `_render_prompt` *does* raise on slot/placeholder mismatch — those are build-time programming errors (the caller authored a slots dict that doesn't match the prompt's signature), not run-time data shapes. Silent skipping would hide the bug.
- **`_render_prompt` raises `KeyError` on missing slots and `ValueError` on extra slots, with sorted slot names in the message.** Sorted names are byte-deterministic across PYTHONHASHSEED values (set iteration is hash-randomised — same trap Sprint 6.5 fixed in `s07_Filter_duplicates.ipynb`). Pinned by `test_render_missing_slot_raises_keyerror` (all three expected slots listed) and `test_render_extra_slot_raises_valueerror`.
- **`bool` check uses `isinstance(x, bool)` directly, not via `isinstance(x, int)`.** `bool` subclasses `int` in Python, so `isinstance(True, int)` returns `True`. The validator must check `bool` directly to reject `0`/`1` int payloads on `preserves_meaning`. Pinned by `test_validate_original_new_preserves_rejects_int_bool` — `{"preserves_meaning": 1}` is rejected with `preserves_meaning_not_bool, type=int`.
- **`new_param.values` length-gate at 2 ≤ N ≤ 5 is the only numeric bound the schema enforces.** Matches the prompt's "entre 2 y 5 valores discretos" wording. Every other constraint (label uniqueness, admissibility against `new_param_allowlist.yaml`, axis-distinctness from existing axes) is structural-blind and falls to Phase E. The 2..5 bound is in the prompt itself, so it's the natural place to enforce it.
- **C3 ships the validated *payload*, not a Phase-B *rule*.** A `synonym_label` LLM payload `{"synonyms": [{"original": "Normal", "new": "Estándar"}, …]}` is not yet a Phase-B `apply_synonym_label` rule — the rule shape requires `{"type", "param", "value", "original", "new"}`, and `param` / `value` aren't in the LLM payload (they need to be lifted from the per-concept stage JSON context). Bundling that lift into Sprint 14 would pull slot-extraction (stage-JSON → slots dict) into the same sprint. Both are deferred to Sprint 15 (slot extraction + rule emission + C4 variant catalog writer). Keeping the payload→rule mapping out of C3 keeps the 12 schemas free from per-concept context noise.
- **No `pydantic` / `jsonschema` runtime dependency.** The 12 schemas are simple enough that hand-coded `isinstance` checks + key-presence checks are cleaner than declaring a `pydantic.BaseModel` per type. The hand-coded validators emit tight `schema_validation_failed: missing_key: 'X'` / `..._not_str: type=int` messages that Phase E1's grep handles directly — `pydantic.ValidationError` noise would need post-processing. Reversible: a future sprint can swap `_validate_payload` to delegate to `pydantic` without changing the public surface.
- **No slot extraction in Sprint 14.** `propose_variant` takes an *already-built* `slots: dict[str, Any]`. Building a slot extractor (per-concept stage JSON + `ModificationType` → slots dict) needs deep familiarity with stage-2/3/4 JSON layouts — axis-key allocation, value-label lookup, var-key resolution, reorderable-constituent identification in templates. It deserves its own sprint. Tests pass deterministic slots dicts inline; no stage-JSON fixtures needed.
- **No `EXPECTED_SLOTS` for `new_param`'s `{allowlist}` slot population.** Phase B4's `configs/synthetic/new_param_allowlist.yaml` is still not authored. The slot remains the caller's responsibility; tests pass a stub string like `"[acabado, recubrimiento]"`. Phase F prompt-tuning revisits.
- **No live LLM calls in pytest.** Identical Sprint 13 rationale — all tests use the same `_StubLLMClient` pattern from `test_llm_proposer.py`. Real-model smoke tests live in `scripts/spike_a3_*.py` or a manually-run notebook.
- **No module-level side effects.** No env reads, no on-import I/O, no logger setup. Pinned by `test_module_has_no_side_effects_at_import` via `importlib.reload`.
- **`VariantProposal.raw_responses` mirrors `ProposalResult.raw_responses` exactly.** No filtering, no reformatting — Sprint 14 just passes the C2 capture through. Phase E1's metadata pipeline can compare the raw payload against the validated payload for diagnostic purposes (e.g., "the LLM returned `{"synonimos": ...}` instead of `{"synonyms": ...}` — consider a prompt polish").

**Known issues:**
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (`448 passed, 1 skipped` prints before the traceback). Cosmetic; no action.
- No concrete LLM transport yet. A3's outcome (Llama 3.1 70B local vs. GPT-4-class API vs. Spanish-tuned alternative) is still the prerequisite. Real-model integration tests are a Phase F1 pilot concern.
- Slot extraction (per-concept stage JSON → slots dict) and payload-to-rule lift (validated LLM payload → Phase-B `{"type", "param", ...}` rule) are deferred to Sprint 15.

**Next step:** **Sprint 15 — Phase C Task C4 (variant catalog writer) + slot-extraction shim + payload-to-rule lift.** Three concerns to bundle: (a) a function `extract_slots(stage_json, concept_key, modification_type) -> dict[str, Any]` that walks stage-2/3/4 JSON for the per-concept context every prompt type needs (axis keys, value labels, var keys, conditions, template fields, reorderable constituents); (b) a per-type payload-to-rule emitter that lifts the validated LLM payload to the `{"type": ..., "param": ..., ...}` shape `layer_*.py` mutators consume (cross-referencing the slots context for axis keys and value labels); (c) the C4 variant catalog writer that pairs the emitter output with provenance metadata and writes `data/synthetic/variants/{concept_key}.json` JSON-per-concept artefacts. Once Sprint 15 closes, the Phase C ladder (C1 prompts → C2 client → C3 proposer → C4 catalog) is complete and the orchestrator (D2) can consume the catalog stream.

---

### After Sprint 13 — Phase C Task C2: LLM client (`llm_proposer.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/llm_proposer.py`](../../src/synthetic/llm_proposer.py) — new module exposing the `LLMClient` `Protocol` (one method `complete(self, prompt: str) -> str`), the `ProposalResult` `@dataclass(frozen=True)` (fields `payload: Optional[dict]`, `raw_responses: tuple[str, ...]`, `fallback: Optional[Modification]`), and the single entry point `propose(prompt, client, modification_type, *, retry_once=True) -> ProposalResult`. Internal helpers `_parse_json_object`, `_strip_code_fence`, `_build_fallback`. `propose` calls `client.complete(prompt)`, attempts a strict-JSON-object parse (stripping a leading ` ```json `… `'''` or bare ` ``` `… `'''` fence first), retries once on `ValueError`, and on a second failure returns a `Modification(type=…, layer=TYPE_TO_LAYER[…], status="skipped", reason="malformed_llm_response_after_retry: <detail>")` inside the result. Never raises; all failures encoded in the result. Stdlib-only imports (`dataclasses`, `json`, `typing`); single in-repo import is `from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER`.
- Added [`tests/synthetic/test_llm_proposer.py`](../../tests/synthetic/test_llm_proposer.py) — 24 contract test functions; with parametrisation expansion (three ×12 over `ModificationType` for fallback type/layer/status; one ×6 over malformed payload shapes) the total is **65 individual cases**. Coverage: public-surface import audit; happy / retry / double-failure paths; per-`ModificationType` fallback shape (type / layer / status / other-fields-are-None); reason-prefix grep handle; raw-responses capture per path (singleton tuple / pair / pair); tuple-not-list audit; `retry_once=False` short-circuit; ` ```json `-fenced parse; bare ` ``` `-fenced parse; whitespace tolerance; non-dict-root rejection (array / string / number / empty); prompt passthrough verbatim; never-raises on malformed input variants; `FrozenInstanceError` on payload reassignment; equality of two structurally-identical results; module re-import via `importlib.reload`; `Protocol` duck-typing with an ad-hoc client class.
- Flipped ❌ → ✅ for the `llm_proposer.py` row in this file's "New Files in This Branch" section with the partial-credit annotation "Sprint 13 — Task C2 — Protocol + retry/fallback contract; concrete transport deferred to A3; C3 still ❌".

**Key results:**
- `pytest tests -q` → **362 passed, 1 skipped in 0.30s, zero failures.** Baseline 297 (Sprint 12); net delta +65 (24 new functions × parametrisation expansion). The skip count stays at exactly 1 (Sprint 12's intentional `new_param` brace-audit skip — no new skips). Sprint plan's "≥22 new test functions / ≥319 total passed" gate is satisfied (24 functions / 362 total).
- `from synthetic.llm_proposer import LLMClient, ProposalResult, propose` succeeds. `ProposalResult.__dataclass_fields__` keys are `('payload', 'raw_responses', 'fallback')`; `dataclasses.fields(ProposalResult)` reports the same in order. Happy-path smoke: `propose('hola', _StubLLMClient(['{"synonyms": []}']), ModificationType.SYNONYM_LABEL).payload == {"synonyms": []}`. Retry-path smoke: `propose('hola', _StubLLMClient(['garbage', '{"k": "v"}']), ModificationType.PARAPHRASE).payload == {"k": "v"}` with `len(raw_responses) == 2`. Double-failure smoke over all 12 `ModificationType` members: every fallback carries `type=mtype`, `layer=TYPE_TO_LAYER[mtype]`, `status="skipped"`, `reason.startswith("malformed_llm_response_after_retry: ")`. Code-fence smoke: `'```json\n{"k": 1}\n```'` parses to `{"k": 1}` on first attempt. `retry_once=False` smoke: malformed singleton → exactly 1 client call, 1 raw response, fallback set.
- **No changes** to any `layer_*.py`, to `mutator.py`, to `composition.py`, to `taxonomy.py`, or to `src/synthetic/prompts/`. C2 is purely additive — one new module file plus its test file.

**Decisions confirmed:**
- **Pluggable transport before model choice.** A3 (LLM proposer choice spike — Llama 3.1 70B local vs. GPT-4-class API vs. Spanish-tuned alternative) is unresolved. The `LLMClient` `Protocol` surface is the abstraction A3 will fill — one concrete `complete(prompt) -> str` implementation, shipped in a follow-up sprint. Committing to a vendor SDK in Sprint 13 would force a rewrite when A3 lands. The protocol's risk-table "LLM proposer model: TBD" cell stays open; the `llm_proposer.py` row in this file is annotated as partial-credit (Protocol shipped; concrete client pending).
- **`Protocol`, not `ABC`.** Structural subtyping fits the one-method contract. No `@runtime_checkable` (we don't need `isinstance(x, LLMClient)`; duck typing in tests is sufficient). Pinned by `test_protocol_duck_typing_works` — an ad-hoc class without inheritance works as a client.
- **`propose` never raises.** Every failure mode — malformed JSON, wrong root type, empty response, double-failure, `retry_once=False` short-circuit — returns a `ProposalResult` with `fallback` populated. Pinned by `test_propose_does_not_raise_on_any_failure_path` (parametrised ×6 over malformed shapes). The orchestrator (D2) walks a uniform return-value path; no `try/except` around the call.
- **One retry, fixed.** The `retry_once: bool` parameter is an on/off knob for tests, never a production-time tunable. Protocol §5 Phase C C2 specifies one retry; richer retry semantics (rate-limit-aware, exponential backoff) belong in the concrete transport's `complete` method when A3 lands, not in `propose`.
- **`_parse_json_object` is C2's "malformed" detector — not C3's schema validator.** C2 checks JSON validity + dict-root only. C3 checks the per-type structural shape (does a `synonym_label` response carry `{"synonyms": [{"original", "new"}, …]}`?). The retry mechanism only fires on C2-level malformity; C3-level shape failures are a separate reject-and-log path C3 owns.
- **Code-fence stripping is best-effort, not regex-based.** Three shapes handled: ` ```json\n…\n``` ` / ` ```\n…\n``` ` / no-fence. Drift to ` ~~~ ` triggers a retry — acceptable degradation. Don't over-engineer the fence detector; let retry absorb the rare cases.
- **`_parse_json_object` rejects non-dict roots.** JSON permits arrays, strings, numbers, booleans, `null` at the root. The 12 prompts all declare an object-shaped contract (`Responde SOLO con un JSON: { ... }`), so a top-level array or scalar is malformed by C2's definition. Pinned by three rejection tests (array, string, number).
- **`raw_responses: tuple[str, ...]`, not `list[str]`.** Pinned by `frozen=True`. Phase E1's metadata pipeline may want to log the raw response verbatim for diagnostic purposes; an immutable tuple keeps the contract clean. Pinned by `test_raw_responses_is_tuple_not_list`.
- **`_build_fallback`'s reason prefix is a grep handle.** Exactly `"malformed_llm_response_after_retry: "`. Phase E1 / F1 will count fallbacks per `ModificationType` via substring match: "5.2% of `paraphrase` proposals fell back; 11.4% of `unit_conversion` did". Pinned by `test_fallback_reason_starts_with_known_prefix`.
- **Fallback `Modification` populates only `type`, `layer`, `status`, `reason`.** Every other field (`param`, `var`, `condition`, `field`, `value`, `original`, `new`) is `None` — by definition the LLM didn't produce a usable payload to populate them with. Pinned by `test_fallback_other_fields_are_none`.
- **No new runtime dependency.** Sprint 13 imports stdlib only (`dataclasses`, `json`, `typing`) plus in-repo `synthetic.taxonomy`. No `httpx`, no `pydantic`, no `tenacity`, no `ollama`, no `anthropic`, no `openai`. Per-type structural validation in C3 may revisit (`pydantic` or `jsonschema` is on the table then), but C2 is dep-free.
- **No live LLM calls in pytest.** All tests use an in-test `_StubLLMClient` that pops queued responses off a list. Real-model smoke tests are A3's problem — they belong in `scripts/spike_a3_*.py` or a manually-run notebook, not in `tests/`.
- **No module-level side effects.** No env-var reads, no on-import I/O, no logger setup. Pinned by `test_module_has_no_side_effects_at_import` via `importlib.reload`.

**Known issues:**
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (`362 passed, 1 skipped` prints before the traceback). Cosmetic; no action.
- The concrete LLM transport is **not** wired in this sprint. A3's outcome (which model? which vendor / runtime? which native API shape?) is the prerequisite for the concrete client. Until A3 lands, the C3 variant proposer (Sprint 14) will exercise `propose()` against the in-test `_StubLLMClient` shape; integration tests against a real endpoint are a Phase F1 pilot concern.

**Next step:** **Sprint 14 — Phase C Task C3 (`variant_proposer.py` — per-concept slot rendering + per-type schema validation).** With the LLM client shipped, C3 owns: (a) loading the per-type prompt via `synthetic.prompts.load_prompt(mtype)`; (b) rendering slots (`{concept}`, `{axis_label}`, `{value_list}`, `{var_key}`, `{condition}`, `{template}`, `{constituents}`, `{var_to_omit}`, `{existing_axes_with_labels}`, `{allowlist}`) from a per-concept slots dict via a `str.format_map` variant that ignores braces inside the JSON-contract block; (c) calling `propose()`; (d) per-`ModificationType` structural validation of the parsed payload (does a `synonym_label` response have `{"synonyms": [{"original", "new"}, …]}`? does a `paraphrase` response have `{"original", "new", "preserves_meaning"}`?); (e) returning a per-concept `Modification` candidate (success) or appending to the skipped log (validation failure). Once C3 closes, C4 (variant catalog writer) consumes the candidate stream and the variant proposer's end-to-end ladder is complete.

---

### After Sprint 12 — Phase C Task C1: Spanish prompt library (`prompts/`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/prompts/__init__.py`](../../src/synthetic/prompts/__init__.py) — `load_prompt(modification_type) -> str`, `PROMPT_DIR: Path`, and `PROMPT_FILENAMES: dict[ModificationType, str]` (auto-computed from the enum). The loader returns the raw UTF-8 text verbatim; placeholder substitution is C3's responsibility. The reference implementation in the sprint spec was extended with an `isinstance(modification_type, ModificationType)` guard — `ModificationType(str, Enum)` would otherwise let a bare string `"synonym_label"` succeed at dict lookup by string-equality, contradicting the spec's "`load_prompt('synonym_label')` raises `KeyError`" acceptance.
- Authored 12 `*.txt` prompt files under `src/synthetic/prompts/`, one per `ModificationType`. Four are lifted *verbatim* from [`RESEARCH_PROPOSAL.md §8`](../RESEARCH_PROPOSAL.md): `synonym_label.txt`, `paraphrase.txt`, `omission.txt`, `new_param.txt`. The remaining eight (`num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`, `expansion`, `compression`, `reorder`) are authored in the proposal-§8 pattern: role line → slot block → instruction body → `Responde SOLO con un JSON:` literal. All files are UTF-8 without BOM, LF line endings, trailing newline; byte sizes 434–699 bytes (within the spec's 200–3000 sanity bound).
- Added [`tests/synthetic/test_prompts.py`](../../tests/synthetic/test_prompts.py) — 18 contract test functions, expanding to 138 individual cases (11 functions parametrised ×12 over `ModificationType`, 7 singletons). Coverage: dir/filenames audit; per-type file existence; per-type loadability + non-empty + LF-terminated; UTF-8 decode + no-BOM byte audit; "JSON" keyword presence; expected-placeholder subset audit per type; idempotence; `KeyError` on bare-string input; `FileNotFoundError` on missing-file monkeypatch; role-line "Eres" prefix; Spanish-register marker presence; `"Responde SOLO con un JSON"` phrase presence; unrendered-braces-outside-slots audit (with `new_param.txt` exempted per spec because its JSON literal has nested `{` / `}` that the prefix-vs-JSON heuristic can't cleanly partition); L1-six-types-share-placeholder-set and L2-three-types-share-placeholder-set uniformity audits; byte-size sanity bounds.
- Flipped ❌ → ✅ for the `prompts/` block in this file's "New Files in This Branch" section — all 13 rows (the directory itself + 12 `.txt` files + an inserted `__init__.py` row).

**Key results:**
- `pytest tests -q` → **297 passed, 1 skipped in 0.24s, zero failures.** Baseline 159 (Sprint 11); net delta +138 (138 new prompt cases) + 1 skip = +139 cases. The skip is the `new_param.txt` exemption in `test_prompt_no_unrendered_python_braces_outside_slots`, which is intentional and pinned by spec. The binding gate (≥18 new test functions, all green, no regressions) is satisfied; the parametrisation-expanded headline (~70 cases recommended by the spec) is exceeded.
- `from synthetic.prompts import load_prompt, PROMPT_DIR, PROMPT_FILENAMES` succeeds. `len(PROMPT_FILENAMES) == 12`; `set(PROMPT_FILENAMES) == set(ModificationType)`. For every `mtype in ModificationType`: `load_prompt(mtype)` returns a non-empty UTF-8 string starting with `"Eres "`, containing `"Responde SOLO con un JSON"`, and ending with `"\n"`.
- **No changes to any `layer_*.py`, to `mutator.py`, to `composition.py`, or to `taxonomy.py`.** C1 is purely additive in the new `src/synthetic/prompts/` subpackage.

**Decisions confirmed:**
- **Loader returns the raw template; no `str.format` inside `load_prompt`.** The JSON-contract block contains literal `{` / `}` characters that aren't Python placeholders. A formatter inside the loader would either require escaping every brace in the JSON literal (ugly for domain reviewers) or commit to a brace-classification policy. Deferring rendering to C3 keeps the loader's surface narrow — IO is the only thing to test.
- **`PROMPT_FILENAMES` is auto-computed from `ModificationType`.** No hand-maintained dict; future enum additions surface as `FileNotFoundError` at call time, which is the right forcing function to author the corresponding `.txt`.
- **Explicit type guard in `load_prompt`.** `ModificationType` mixes in `str`, so `"synonym_label" == ModificationType.SYNONYM_LABEL` and hash-equal — a bare-string lookup would silently succeed without the guard. Added one-line `isinstance` check; matches the spec's "looser-coercion alternative considered and rejected" rationale.
- **No `PROMPT_DIR` env-var override surface.** `PROMPT_DIR = Path(__file__).parent` is pinned. Override (for A/B prompt variants, DB-backed prompts) is a deferred concern; C2's LLM-client sprint will revisit if it needs the surface.
- **No caching.** `load_prompt` does fresh disk IO every call. Prompts are tiny (<2 KB each); per-call IO is dominated by the eventual LLM round-trip in C2. Caching would complicate the test contract for no measurable benefit.
- **Four prompts verbatim from proposal §8; eight new in the same pattern.** Sprint 12 operationalises §8's representative-only framing. The verbatim pin means any future polish to those four prompts must update the proposal in the same change.
- **L1's six prompts share the same three-slot signature; L2's three share the same four-slot signature.** Uniformity per layer is a feature — it makes C3's slot-population logic uniform per layer. L3's two prompts and PD's one diverge (omission/reorder/new_param each carry per-type structural slots).
- **JSON-contract block uses `"..."` and `[...]` as fill targets.** The LLM sees the literal `"..."` and replaces it. More readable than formal JSON-schema notation; matches the proposal's §8 pattern. The C2 client will pair the prompt with a `pydantic` / `jsonschema` model that enforces the actual shape — the prompt's job is to *cue* the model, not to *enforce* the schema.
- **`new_param`'s `{allowlist}` slot stays unfilled.** Phase B4's `configs/synthetic/new_param_allowlist.yaml` is not yet authored; C3's `new_param` codepath will load the YAML (when it lands) and format the prompt accordingly. Until then the slot is empty and the LLM is asked to use its best judgement about axis distinctness — a temporary state that Phase F prompt-tuning will revisit.
- **No native-Spanish review gate.** Sprint 12's quality gate is *structural* (placeholders present, JSON contract declared, Spanish register markers present), not *linguistic*. A native domain reviewer (the same person who runs the E4 review harness) will polish prompts during the F1 pilot retrospective when real LLM-output acceptance-rate data exists. Pre-polish review would be hand-wavy without that grounding.
- **No prompt versioning, no template inheritance.** The 12 prompts are independent text files. Cross-prompt sharing (e.g., a common "preserve significado paramétrico" header) is *intentionally* not factored out — Phase F may discover that some types need a stronger preservation cue than others, and premature DRY-ing would lock in a uniform header that's not optimal per type.
- **No `llm_proposer.py` stub.** Sprint 12 does not create a placeholder C2 file. A stub would either raise `NotImplementedError` (forcing C2 to delete-and-rewrite) or be empty (conveying nothing). The cleaner sprint boundary is "Sprint 12 lands prompts; Sprint 13 creates `llm_proposer.py` from scratch".

**Known issues:**
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (`297 passed, 1 skipped` prints before the traceback). Cosmetic; no action.
- The Spanish text of the eight newly-authored prompts has not been reviewed by a native domain reviewer. Deferred to Phase F1/F2 prompt-tuning with acceptance-rate data as ground.

**Next step:** **Sprint 13 — Phase C Task C2 (`llm_proposer.py` — LLM client + retry/fallback).** With the prompt library frozen, the next concern is the offline client that pairs each prompt with a `pydantic` or `jsonschema` model and a per-type retry/fallback policy. The variant proposer (C3) consumes the client; the variant catalog writer (C4) writes the JSON-per-concept artefacts the orchestrator (D2) reads.

---

### After Sprint 11 — Phase B Task B5: composition rules (`composition.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/composition.py`](../../src/synthetic/composition.py) — new module exposing `compose_rules(rules) -> (admissible_rules_in_apply_order, skipped_modifications)`, the `COMPATIBILITY_MATRIX: dict[(ModificationType, ModificationType), CompatibilityVerdict]` constant (six entries, all `(NEW_PARAM, L1-type) → LAYER_DEPENDENCY`), the `CompatibilityVerdict(str, Enum)` with four values (`COMPATIBLE`, `SAME_TARGET`, `LAYER_DEPENDENCY`, `UNSTACKABLE`), and a private `_canonical_key(rule)` helper. The composer is a pure, state-blind validator: it sorts rules into **PD → L1 → L2 → L3** apply order with stable within-layer ordering, runs three passes (canonical-key dedup → PD-axis-vs-L1-param same-axis pass → matrix pass), and returns the surviving rules together with `Modification(status="skipped", reason=...)` entries for every dropped rule. The canonical key reuses L2's `_norm` (imported as `_norm_cond`) for whitespace-collapse on conditions and lowercases L3's `field` for the addressing component, so L2-`$`-strip and L3-field-case symmetry collapse same-target rules across rule-side cosmetic differences. The matrix-pass treats `LAYER_DEPENDENCY` entries as no-ops because step 2 (PD-vs-L1 same-axis pass) is the authoritative detector — step 2 catches the actual value-pair conflict; the matrix entry exists to document the type-pair policy and to make `UNSTACKABLE` entries an additive future change. No deep-copying of input or output: admissible rules are aliases of the input dicts; input list and dicts are bytewise-unchanged across the call.
- Surgically edited [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py) — added `from synthetic.composition import compose_rules` under the existing import block and one new test `test_composition_module_exposes_compose_rules` at the bottom asserting the composer's `(rules,)` parameter list. The nine surviving Sprint-10 tests are untouched.
- Added [`tests/synthetic/test_composition.py`](../../tests/synthetic/test_composition.py) — 26 explicit test functions; with parametrisation expansion (one 4-way over per-layer pass-through, one 6-way over all L1 types under PD-axis conflict) the total is **34 individual cases**. Coverage: signature pin, empty-input edge case, single-rule pass-through per layer (×4), layer apply-order from a reverse-submission batch, stable within-layer order, same-target dedup per layer (L1, L1-across-types, L2 with $-strip and whitespace symmetry, L3 with field-case symmetry, PD), distinct-targets-no-conflict (L1), PD-vs-L1 same-axis skip with axis named in reason, PD-vs-L1 different-axis admissible, all six L1 types skipped under same-axis PD (×6), PD+L2-on-different-var compatible, mixed-layer-no-conflicts happy path, no-mutation-of-input contract, admissible-aliases-input identity contract, malformed-input exceptions (`ValueError` on unknown type code; `KeyError` on missing addressing field per layer), idempotence under recomposition, matrix audit (only valid enum members; exactly the six starter entries).
- Did **not** create `configs/synthetic/composition_rules.yaml` — the matrix lives as a Python module-level constant in `composition.py` for B5. YAML externalisation is deferred; the rationale is in the sprint plan's "Out of scope" block.
- Updated [`docs/synthetic/RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md): §5 Phase B B5 row appended postscript "Matrix lives in `src/synthetic/composition.py` as a Python module-level constant for B5; YAML externalisation (`configs/synthetic/composition_rules.yaml`) deferred to a later phase if Phase C / E tooling needs an editable surface without code changes."; line 302 of the file-tree listing now annotates `composition_rules.yaml` as deferred. §3.3's "L1 first, then L2, L3, PD" phrasing is now reconciled with §B5 by the explicit canonical-order pin in this sprint's design notes (the protocol's parenthetical "PD-first if the new axis affects L2/L3" framing is superseded — PD is *always* first when present, since its job is to install the axis subsequent rules may reference).

**Key results:**
- `pytest tests -q` → **159 passed in 0.19s, zero failures, zero skips.** Baseline 124 (Sprint 10); net delta +34 (`test_composition.py` cases counting parametrisations) + 1 (`test_mutator.py` audit) = +35, landing at 159. Sprint plan's projected minimum (≥145) is exceeded; the "if all 26 listed cases land with parametrisation expansion to ~33" headline (≥158) is also exceeded.
- Smoke checks pass. `python -c "from synthetic.composition import compose_rules, COMPATIBILITY_MATRIX, CompatibilityVerdict; print('imports ok'); print('matrix size:', len(COMPATIBILITY_MATRIX))"` printed `imports ok` / `matrix size: 6`. `compose_rules([])` returns `([], [])`. The end-to-end `_smoke_compose.py` script with 5 mixed-order rules (one same-target dup and one PD-vs-L1 same-axis conflict) returned 4 admissible in `[new_param, synonym_label, paraphrase, omission]` order and 1 skipped `SYNONYM_LABEL` `Modification` whose reason contained `layer_dependency_conflict` and named the `K` axis.
- `git status --short` end-of-sprint reflects exactly the sprint-scoped files: new `src/synthetic/composition.py`, new `tests/synthetic/test_composition.py`, modified `tests/synthetic/test_mutator.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`, modified `docs/synthetic/RESEARCH_PROTOCOL.md`, new `docs/synthetic/sprints/SPRINT_11.md` (sprint plan, already drafted). Nothing under `src/utils/`, no notebooks, nothing under `data/` / `configs/`. **No changes to `src/synthetic/mutator.py`, no changes to any `layer_*.py`, no changes to `taxonomy.py`** — B5 is purely additive in `src/synthetic/`.

**Decisions confirmed:**
- **Matrix pass treats `LAYER_DEPENDENCY` as a no-op.** The PD-vs-L1 same-axis pass (step 2) is the authoritative detector for layer-dependency conflicts. The matrix entry expresses *type-pair policy*; whether a specific rule pair triggers it is a *value-pair check* (do `pd_rule["param"]` and `l1_rule["param"]` match?). If step 2 found no conflict, the matrix entry is a no-op. Test 13 (`test_pd_introduces_axis_l1_on_different_axis_no_conflict`) is the binding constraint: a PD-on-K paired with an L1-on-A must both survive, even though `(NEW_PARAM, SYNONYM_LABEL)` has a `LAYER_DEPENDENCY` matrix entry. The matrix is in place for future `UNSTACKABLE` entries (which the matrix pass *does* act on) without code changes.
- **Layer apply-order canonicalised as PD → L1 → L2 → L3.** Protocol §3.3 said "L1 first, then L2, L3, PD"; §B5 hinted at "PD-first if the new axis affects L2/L3". Sprint 11 pins the canonical order as **PD → L1 → L2 → L3** — PD's job is to *add an axis*; L1's job is to *mutate values on an axis*. If a batch contains both, PD must run first so L1's `(param, value)` addressing key resolves against a real axis. The protocol's §3.3 phrasing was written before PD's cross-block edits were specified; the sprint's protocol patch supersedes the conditional framing.
- **Canonical-key dedup is the workhorse; the matrix is the exception list.** Most real-world conflicts (two `synonym_label`s on the same `(param, value)`, two `paraphrase`s on the same `(var, condition)`, two `omission`s on the same `(field, original)`) are caught by canonical-key equality without consulting the matrix. The starter matrix's six entries are all redundant with the dedicated PD-vs-L1 same-axis pass. The matrix exists for future extension (e.g., adding `UNSTACKABLE` entries for `OMISSION` × `REORDER` on overlapping spans if research uncovers a structural problem) without changing pass logic.
- **`Modification(status="skipped", reason=...)` is the conflict signal, not exceptions.** Matches the protocol §4 "skip + log via the `Modification` record" decision. A composer that raised on conflict would force the orchestrator to wrap every batch in try/except, and the conflict signal would never reach the per-item metadata where Phase E's slice analysis needs it. Skipping + logging keeps the variant catalog's audit trail uniform.
- **YAML deferral is deliberate and reversible.** Externalising six near-identical entries to YAML costs a parse step at module load, a schema validation surface, and an asymmetric edit path (humans edit YAML; tests read YAML; the composer reads YAML). For Sprint 11's starter content the cost outweighs the benefit. When Phase C / E tooling needs to add ten-plus entries without code changes, a single follow-up sprint can wrap `COMPATIBILITY_MATRIX = _load_matrix(...)` around the current inline definition; the composer's public surface is unchanged.
- **No mutation of input; admissible output aliases input rules.** The composer is pure. The orchestrator's `_apply_rules` already deep-copies stage JSON at entry; rule dicts are the *caller's* (variant catalog's) property and should not be cloned by an intermediate validator. Two complementary tests pin this from opposite directions: `test_no_mutation_of_input_rules` checks the input is byte-identical after the call; `test_admissible_output_aliases_input_rules` uses `is`-identity to confirm the output dict objects are the same instances.
- **Re-composition is idempotent (a fixed-point property).** Passing the composer's admissible output back through `compose_rules` returns the same admissible list with empty skipped log. Pinned by `test_idempotent_under_recomposition` over a 6-rule mixed batch. Phase E1's metadata-join pipeline can re-run the composer as part of metadata reconstruction without inflating the skipped log.

**Known issues:**
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (159 passed prints before the traceback). Cosmetic; no action.
- The composer is **not yet wired** into the orchestrator (`mutator._apply_rules` does not consult it). This is intentional — the wiring decision (applier-side filter vs orchestrator-side filter vs Phase C3 proposer-side filter) is a Phase C/D concern, not Phase B5. Sprint 11 lands the composer as an importable function with a verified contract; the consumer is determined later.

**Next step:** **Sprint 12 — Phase C Task C1 (`prompts/` — per-type Spanish prompt library).** Phase B is now closed. Phase C's prompt library is the natural successor: one Spanish prompt per `ModificationType` declaring its JSON-output contract. The Stage-A LLM proposer (C2/C3) reads these prompts; the composer (B5) validates the resulting rule batches before they reach the orchestrator (D1/D2). Sprint 12 will likely scaffold the 12 prompt files with minimal contract enforcement (output shape pin) and defer per-type Spanish-fluency tuning to a Phase C polish sprint.

### After Sprint 10 — Phase B Task B4: PD `new_param` mutator body (`layer_pd.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/layer_pd.py`](../../src/synthetic/layer_pd.py) — a single public function `apply_new_param(stage_json, concept_key, rule)` that adds a new parameter axis to `concept["parameters"]`, optionally registers a new `$VAR` formula on `concept["text_variables"]` (auto-creating the block if absent), and optionally applies one or more L3-style substring patches to `concept["resumen"]` / `concept["texto"]`. Validates rule shape upfront (`param` non-empty string, `label` non-empty string, `values` non-empty list with pairwise-unique value labels and `{"label": str, "value": str}` shape on each entry, optional `text_variable` dict with non-empty `var` and `formula`, optional `template_patches` list of L3-style patches with case-insensitive `field` coercion). Collision detection on `param` and `var` keys raises `ValueError`; missing concept-key and missing `parameters` block raise `KeyError`; template-patch substring-uniqueness uses `template.count(original)` (zero → `KeyError`, >1 → `ValueError` naming substring/count/field). Emits exactly one `Modification(type=NEW_PARAM, layer=PARAM_DEFINITION, param=<new axis key>, new=<new axis label>, var=<new var key or None>, status="applied")` per rule, regardless of how many blocks were touched. Diverges from L1/L2/L3's "wrappers, one worker" pattern: PD has exactly one `ModificationType`, so it has one function — no fan-out to compress.
- Wired the PD mutator into [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH`. Added `from .layer_pd import apply_new_param as _layer_pd_apply_new_param` (the alias is load-bearing — the worker shares its natural name with the orchestrator function defined later in the same module). Deleted the `_stub_new_param` function definition. Swapped the `ModificationType.NEW_PARAM` entry in `_DISPATCH` to `_layer_pd_apply_new_param`. Updated the module docstring from "6 L1 + 3 L2 + 2 L3 live, 1 still stub (PD — `new_param`)" to "all 12 (6 L1 + 3 L2 + 2 L3 + 1 PD) mutators live; dispatcher fully promoted from stubs". The orchestrator `apply_new_param` (single-rule public entry-point) is byte-identical pre/post — its body already deep-copied input, resolved the type, gated the layer, and dispatched via `_DISPATCH[mtype]`. `_StubResult` was left in place per the sprint recommendation — vestigial but harmless, will be renamed to `_MutatorResult` only if a future sprint needs to touch orchestrator type annotations.
- Added [`tests/synthetic/test_layer_pd.py`](../../tests/synthetic/test_layer_pd.py) — 26 contract test cases driving an inline `oeb020_stage2` fixture (two axes `A`/`B`, non-empty `text_variables["K"]`, `resumen`/`texto` templates with `$A`/`$K` references). Coverage: 4 happy-path cases (axis-only, axis+text_variable, axis+single-template-patch, full combo with axis + text_variable + 2 patches on `RESUMEN` and `TEXTO`); 2 collision cases (`param="A"` clash, `var="K"` clash both raising `ValueError` whose message names the colliding key and the concept); 2 template-patch error cases (substring not found → `KeyError`; duplicated `"tubos"` in a tweaked `texto` → `ValueError` naming substring/count/field); 2 missing-block cases (concept-key absent → `KeyError`; concept lacks `parameters` block → `KeyError`); 5 rule-shape validation cases (empty `param`, missing `param`, empty `label`, empty `values`, duplicated value labels); 1 `text_variable` without `formula` case; 1 auto-create-`text_variables`-block case (one-off fixture with no `text_variables` key); 1 unknown-template-patch-field case (`"DESCRIPCION"` → `ValueError` naming the accepted values); 4 parametrised field-case-normalisation cases (`TEXTO` / `texto` / `Texto` / `tExTo` all produce byte-identical `out["OEB020$"]["texto"]`, and the emitted `Modification.field` is `None` for PD — the patch's field doesn't propagate to the audit record); 1 orchestrator-routing case (caller dict byte-identical via `json.dumps(sort_keys=True, ensure_ascii=False)`); 1 wrong-layer-rule case (`paraphrase` rule on the PD orchestrator raises `ValueError` from `_gate_layer`); 1 `len(log) == 1`-for-full-combo case (pins the "one rule → one `Modification`" contract); 1 caller-dict-unchanged-after-full-combo-apply case. The plan's ≥18 minimum is exceeded; the recommended ~23 headline is exceeded (parametrisations pushed to 26).
- Pruned [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py). Deleted `_LAYER_TO_APPLY`, `_STUB_TYPES`, the parametrised `test_each_stub_raises_notimplemented_with_type_code` function, and `test_deep_copy_purity_on_notimplemented` (all four assumed at least one stub remained). Dropped the now-unused `Layer` and `TYPE_TO_LAYER` imports from `synthetic.taxonomy`; kept `ModificationType` for the dispatch-table-size test. Added `test_no_stubs_remain_in_dispatch` at the bottom: asserts every `_DISPATCH` value's `__name__` starts with `apply_` and no value's `__name__` starts with `_stub_`. Net delta for this file: −2 (parametrised stub + deep-copy-purity removed) + 1 (audit added) = −1 case.

**Key results:**
- `pytest tests -q` → **124 passed in 0.11s, zero failures, zero skips.** Baseline 99 (Sprint 09); net delta −2 (retired `test_mutator.py` cases) + 26 (new `test_layer_pd.py` cases — 22 specific + 4 field-case parametrisations) + 1 (new dispatch audit test) = +25, landing at 124. Sprint plan's projected minimum 116, recommended 121 — both exceeded.
- Dispatcher fully promoted: **12 live, 0 stubs.** Smoke check `python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import ModificationType; assert all(_DISPATCH[t].__name__.startswith('apply_') for t in ModificationType); assert len(_DISPATCH) == 12; print('dispatcher fully promoted:', len(_DISPATCH), 'live, 0 stubs')"` printed `dispatcher fully promoted: 12 live, 0 stubs`. The 12-entry total and `set(_DISPATCH) == set(ModificationType)` invariants are unchanged.
- `from synthetic.mutator import _stub_new_param` correctly raises `ImportError` — the last stub function definition is physically gone. The `_stub_*` prefix has been eliminated from `mutator.py` entirely.
- End-to-end smoke ok: `mutator.apply_new_param(stage, "OEB020$", rule)` with a full-combo rule (axis `F: CALIDAD ACABADO` with two values, `text_variable={"var":"F","formula":'"estándar" * (%F=="a") + "premium" * (%F=="b")'}`, one `TEXTO` patch injecting `calidad $F`) mutates only the targeted blocks inside the returned `out`, caller input is byte-identical under `json.dumps(sort_keys=True, ensure_ascii=False)` pre/post, emitted `Modification` carries `param="F"`, `new="CALIDAD ACABADO"`, `var="F"`, `status="applied"`, `layer=PARAM_DEFINITION`.
- `git status --short` end-of-sprint reflects exactly the four sprint-scoped files plus the two log files: new `src/synthetic/layer_pd.py`, modified `src/synthetic/mutator.py`, new `tests/synthetic/test_layer_pd.py`, modified `tests/synthetic/test_mutator.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`. Nothing under `src/utils/`, no notebooks, nothing under `data/` / `configs/`.

**Decisions confirmed:**
- **PD breaks the "wrappers, one worker" pattern — deliberately.** L1 has six wrappers + one worker; L2 three + one; L3 two + one. PD has exactly one `ModificationType` (`NEW_PARAM`), so it has one function. Forcing a private `_install_new_param` worker + a thin `apply_new_param` wrapper would add zero structural benefit (no fan-out to compress) and would obscure that PD is genuinely different. The single-function surface is the right shape for a "one type, one wrapper" layer.
- **Orchestrator/worker name clash resolved with an import alias, not a rename.** `apply_new_param` is simultaneously the orchestrator's public name in `mutator.py` (part of the dispatcher surface `apply_l1`/`l2`/`l3`/`apply_new_param`) and the natural name for the layer worker (matching `apply_synonym_label` / `apply_paraphrase` / `apply_omission`). The `from .layer_pd import apply_new_param as _layer_pd_apply_new_param` alias is the strictly-smaller change — one line in `mutator.py`, no test changes, no ripple downstream.
- **PD `add` semantics replace L1/L2/L3 `replace` semantics — collisions raise loudly.** A `new_param` rule that targets a `param` key already present on the concept is a catalog-authoring error; same for var-key collisions on `text_variables`. The applier raises `ValueError` with a message naming the colliding key and the concept. Silent overwrite (a Phase D run silently destroys an existing axis or formula) vastly outweighs a loud failure the variant catalog reviewer must investigate. Verified by `test_param_collision_raises` and `test_var_collision_raises`.
- **`text_variables` block auto-creation is the only "create-on-write" path in PD.** A stage-2 concept legitimately may have no `text_variables` (every template token is a direct `$A`/`$B` axis reference). When the rule supplies a `text_variable` block, the worker creates `concept["text_variables"] = {}` and inserts the new var. The asymmetry is principled: a concept without `parameters` isn't parametric (PD has nothing to mutate, the worker raises `KeyError`); a concept without `text_variables` is fine — PD can install the first one. Verified by `test_text_variables_block_auto_created`.
- **Template patches reuse the L3 substring-uniqueness contract but the worker re-implements the loop inline rather than importing L3's `_replace_substring`.** L3's worker emits one `Modification` per patch (matching the per-rule contract for L3); PD wants exactly one `Modification` per rule even when N patches were applied. Importing L3's private worker would force a choice between L3's per-patch emission and PD's one-Modification-per-rule contract. The ~10 lines of patch-validation duplication is the deliberate price of contract isolation.
- **Template patches apply in submission order; later patches may fail if earlier patches rewrote their region.** The intentional semantic-blind contract — patch ordering is the rule author's responsibility, exactly like the L3 stacked-rule contract from Sprint 09. Phase C's variant proposer is responsible for ordering patches such that each match site survives.
- **One `Modification` per rule, even when three blocks were edited.** The `Modification` dataclass overloads its existing fields for PD: `param=<new axis key>`, `new=<new axis label>`, `var=<new var key if any>`. Full mutation delta (`values` list, `formula` string, every `template_patch`'s `(field, original, new)` triple) lives in the rule payload — the variant catalog (Phase C4) stores the rule alongside the `Modification`, and the metadata-join (Phase E1) reconstructs the per-item metadata from both. Maintaining "one rule → one `Modification`" uniformly across all 12 types is more valuable than capturing every PD edit in the dataclass. Verified by `test_modification_has_exactly_one_entry`.
- **No `new_param_allowlist.yaml` lookup, no semantic-similarity check, no Spanish heuristic in the applier.** The applier is semantic-blind, exactly like Sprints 07–09's L1/L2/L3 appliers. Cross-axis semantic collision detection lives in Phase E (reviewer harness); allowlist enforcement lives in Phase C (variant proposer) and Phase E. Phase B's applier remains the dumbest possible substitution engine that still preserves the data contract.

**Known issues:**
- *No stubs remain* — the audit test `test_no_stubs_remain_in_dispatch` pins this invariant. Phase B's mutator-body work is complete; Sprint 11 moves to a different code shape (`composition.py` — stacking-rule encoder, not per-type mutators).
- `_StubResult` typedef in `mutator.py` is vestigial after stub removal but harmless. Cosmetic rename to `_MutatorResult` is deferred per the sprint plan recommendation (would touch orchestrator type annotations for no functional benefit).
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (124 passed prints before the traceback). Cosmetic; no action.

**Next step:** **Sprint 11 — Phase B Task B5 (`composition.py` — stacking rules).** With all 12 mutator bodies live, the next concern is the per-pair compatibility matrix that gates which rule types may stack on the same item (e.g., `OMISSION` + `REORDER` on the same template is structurally fragile; `NUM_TO_TEXT` + `UNIT_CONVERSION` on the same `(param, value_label)` is a no-op-overwrite hazard). Sprint 11 will encode the matrix and add a `compose_rules(rules)` validator the orchestrator can consult before fanning rules through `_DISPATCH`. The "one worker, N wrappers" pattern that drove Sprints 07–09 is permanently retired — B5's design will be matrix-shaped, not fan-out-shaped.

### After Sprint 09 — Phase B Task B3: L3 `template` mutator bodies (`layer_l3.py`)
**Date:** 2026-05-20
**What changed:**
- Created [`src/synthetic/layer_l3.py`](../../src/synthetic/layer_l3.py) — one private worker `_replace_substring(stage_json, concept_key, rule, mod_type)` plus two thin public wrappers `apply_omission`, `apply_reorder`. The worker locates the unique occurrence of `rule["original"]` inside `stage_json[concept_key][field.lower()]` (the `resumen` or `texto` stage-4 template string), overwrites the matched span with `rule["new"]` via `str.replace(original, new, 1)`, and emits exactly one `Modification(layer=TEMPLATE, type=<wrapper's mod_type>, field=<UPPERCASE>, original=<rule's substring>, new=<rule's replacement>, status="applied")`. Rule's `field` is accepted in any case (`TEXTO` / `texto` / `Texto` / `tExTo`); normalised to lowercase for the stage-JSON lookup and emitted in canonical uppercase on the `Modification`. Uniqueness is enforced by `template.count(original)`: zero matches → `KeyError`, two or more → `ValueError` whose message names the substring, the count, and the field. Empty `original` raises `ValueError`; missing `new` raises `ValueError` (symmetric with L1/L2's missing-`new` test); empty `new` is allowed (omission's canonical case). The two wrappers exist purely to set the `Modification.type` enum — mechanics are uniform; per-type semantics ride on the type code, exactly as Sprints 07–08's "wrappers, one worker" pattern prescribes.
- Promoted the two L3 entries inside [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH` from stubs to the new `apply_*` wrappers. Added the `from .layer_l3 import (apply_omission, apply_reorder)` import block under the existing L2 import. Deleted the two obsolete `_stub_omission` / `_stub_reorder` function definitions. Updated the module docstring from "6 L1 + 3 L2 live, 3 still stubs (L3 / PD)" to "6 L1 + 3 L2 + 2 L3 live, 1 still stub (PD — `new_param`)". `_apply_rules` / `_resolve_type` / `_gate_layer` / `apply_l1`/`l2`/`l3`/`apply_new_param` and the surviving `_stub_new_param` are untouched.
- Added [`tests/synthetic/test_layer_l3.py`](../../tests/synthetic/test_layer_l3.py) — 21 contract test cases driving an inline `oeb020_stage4` fixture mirroring the real `OEB020aaaaa` shape (the verified stage-4 JSON from `OBRA CIVIL_stage4.json`): 4 happy-path cases (omission on `texto`, omission on `resumen`, reorder on `texto`, reorder on `resumen`), 2 parametrised cross-template-isolation cases, 4 parametrised `field`-case-normalisation cases (`TEXTO` / `texto` / `Texto` / `tExTo` all produce byte-identical out dicts and `Modification.field == "TEXTO"`), 1 orchestrator-threading case (2-rule batch through `apply_l3` with deep-copy purity assertion), 1 empty-`new` omission case (pins "omission with `new=""` is allowed" semantic), 1 no-op `new == original` reorder case (pins semantic-blind contract — still emits `status="applied"`), 5 error-path cases (missing concept_key, missing field template, unknown field `"DESCRIPCION"`, original-not-found, multiple-match → `ValueError`), 2 invalid-rule-shape cases (empty `original`, missing `new` field), 1 byte-equality contract test pinning the L1/L2 divergence (rule's `original` IS the addressing key for L3, not informational), 1 caller-purity snapshot test, 1 direct `_replace_substring` call. The plan's "≥15 new tests" gate is exceeded.
- Narrowed [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py): `_STUB_TYPES` shrinks from "TEMPLATE or PARAM_DEFINITION" (3 cases) to "PARAM_DEFINITION only" (1 case — `new_param`) via `[t for t in ModificationType if TYPE_TO_LAYER[t] is Layer.PARAM_DEFINITION]`. `test_deep_copy_purity_on_notimplemented` swapped its rule from `{"type": "omission"}` against `apply_l3` (now live) to `{"type": "new_param"}` against `apply_new_param` (the last surviving stub). No other tests touched.

**Key results:**
- `pytest tests -q` → **99 passed in 0.13s, zero failures, zero skips.** Baseline 78 (Sprint 08); net delta −2 (L3 stub cases narrowed out of the parametrised stub test) + 21 (new `test_layer_l3.py` cases — counting parametrisations: 4 happy-path + 2 cross-template parametrised + 4 field-case parametrised + 11 specific cases) = +19. The sprint plan's projected minimum (91) is exceeded; the recommended count (~95 if 19 cases) is exceeded as well because two of the spec's bullets unfolded into parametrised pairs.
- Dispatcher audit smoke check: `11 live, 1 still stubs`. Every `PARAM_VALUE` / `TEXT_VARIABLE` / `TEMPLATE` entry in `_DISPATCH` resolves to an `apply_*` function; only `NEW_PARAM` still resolves to `_stub_new_param`. The 12-entry invariant (`set(_DISPATCH) == set(ModificationType)`) is unchanged.
- `from synthetic.mutator import _stub_omission` correctly raises `ImportError` — the two obsolete L3 stub definitions are physically gone.
- End-to-end smoke: `apply_l3(stage, "OEB020aaaaa", [{"type":"omission","field":"TEXTO","original":" $I,","new":""}])` mutates only the targeted span inside the returned `out` (`" $I,"` removed once), caller input is byte-identical under `json.dumps(sort_keys=True)` pre/post, emitted `Modification` carries `field="TEXTO"`, `original=" $I,"`, `new=""`, `status="applied"`, `layer=TEMPLATE`.
- `git status --short` end-of-sprint reflects exactly the four sprint-scoped files plus the two log files: new `src/synthetic/layer_l3.py`, modified `src/synthetic/mutator.py`, new `tests/synthetic/test_layer_l3.py`, modified `tests/synthetic/test_mutator.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`. Nothing under `src/utils/`, no notebooks, nothing under `data/` / `configs/`.

**Decisions confirmed:**
- **Field-case normalisation lives at the rule boundary, not in the data.** Stage-4 JSON dict keys are lowercase (`resumen`, `texto`); the proposal's worked example (`§2.3`) uses uppercase (`"field": "RESUMEN"`). The worker accepts either case, coerces to lowercase for the stage-JSON lookup, and emits `Modification.field` in canonical uppercase. Reason: the catalog's authors think in screaming-snake-case (matching the BC3 `\RESUMEN\` / `\TEXTO\` record-type sentinels), but the JSON parser landed on lowercase; the rule schema accommodates the human convention; the data lookup uses the machine convention; the log pins the canonical proposal form. Verified by `test_field_case_normalization` (4 parametrised cases).
- **Rule's `original` is load-bearing for L3, not informational — deliberate divergence from L1/L2.** In L1 the rule's `original` was ignored (informational); in L2 the rule had no `original` field. In L3 the rule's `original` IS the addressing key — there is no other structural handle to identify which substring to mutate. The "log-`original`-is-authoritative" contract is preserved by a different mechanism: the worker raises `KeyError` if the substring doesn't occur, so a stale rule cannot silently emit an out-of-date `original`. Variant-catalog drift detection at Phase E review remains the safety net. Verified by `test_modification_original_byte_equals_rule_original`.
- **Uniqueness is by substring, not by regex.** `str.count` and `str.replace(original, new, 1)` are the entire matching primitive. The worker does **not** interpret `$var` references, does not parse the template grammar, and does not normalise whitespace. The rule author is responsible for picking an `original` that occurs exactly once and starts/ends at the right boundary (e.g., `" $I,"` rather than `"$I"` to capture surrounding whitespace and punctuation). This pushes the "what should the precise mutation be?" complexity to Phase C prompts. Verified by `test_original_matches_multiple_times_raises` (the substring `"de "` appears many times in the real `texto` template — the worker raises `ValueError` with the count).
- **Empty-`new` is allowed; no-op `new == original` is allowed.** The worker is semantic-blind. An omission rule with `new = ""` deletes the matched span and emits a `Modification(new="")`; a reorder rule with `new == original` is a structural no-op but still emits a `Modification(status="applied", original==new)`. Phase C will constrain its proposer to emit empty `new` for `omission` and non-trivial reorderings for `reorder` — that's a generation-time invariant, not an applier-time invariant. Verified by `test_omission_with_empty_new` and `test_reorder_with_no_op_new_succeeds`.
- **Cross-template isolation is bytewise.** A rule's `field` is authoritative; the worker touches only the named template (`resumen` or `texto`), never the other. A rule that wants to mutate both must be issued as two separate rules. Verified by `test_other_template_untouched` (2 parametrised cases — `RESUMEN` rule preserves `texto`; `TEXTO` rule preserves `resumen`).
- **Two wrappers, one worker — Sprints 07–08's pattern lands cleanly on L3.** `_replace_substring` is the L1 `_replace_value` and L2 `_replace_fragment` patterns adapted for arbitrary template substrings. The wrappers exist purely to set the `Modification.type` enum on the emitted record. Per-type semantic enforcement (does this "omission" really remove a `$var` and only a `$var`? does this "reorder" really change constituent order rather than just modify the prose?) lives upstream in Phase C prompts and downstream in Phase E review, never inside the applier.
- **Outer-level `copy.deepcopy(stage_json)` stays inside `_apply_rules`, not the worker.** Same Sprints 07–08 contract — worker-level deep-copy would balloon costs on stacked rules in Phase B5 composition. The worker mutates its received `out` in place; caller purity is pinned by `test_caller_dict_unchanged_after_apply` and by the orchestrator-threading test's snapshot assertion.

**Known issues:**
- 1 stub remains in `mutator.py` (PD — `new_param`). It continues to raise `NotImplementedError`; Sprint 10 (B4 — `layer_pd.py`) will narrow `_STUB_TYPES` to `[]` and the parametrised stub test in `test_mutator.py` will be deleted entirely.
- Sprint plan's projected pytest count (91 minimum, 95 if all 19 listed cases are written) was an underestimate: two of the spec's bullets (`test_other_template_untouched` and `test_field_case_normalization`) unfolded into parametrised pairs/quads, landing at 99 instead of 95. The binding gate ("≥15 new L3 contract cases, all green, no skips, no regressions in the surviving baseline") is satisfied; the headline pytest number tracks the actual parametrised case count.
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (99 passed prints before the traceback). Cosmetic; no action.

**Next step:** **Sprint 10 — Phase B Task B4 (`layer_pd.py` — `new_param` mutator).** The last remaining stub. Note: PD is structurally different from L1/L2/L3 — `new_param` introduces a *new* parameter axis (with label, values, and a new text variable referencing it) rather than mutating an existing one. The `apply_new_param` entry-point in `mutator.py` accepts a single rule (not a list); the worker will need to coordinate edits across `parameters` and `text_variables` blocks in one stage-2 JSON. After B4 lands, `_STUB_TYPES` becomes `[]` and the parametrised stub test in `test_mutator.py` is removed entirely.

### After Sprint 08 — Phase B Task B2: L2 `text_variable` mutator bodies (`layer_l2.py`)
**Date:** 2026-05-19
**What changed:**
- Created [`src/synthetic/layer_l2.py`](../../src/synthetic/layer_l2.py) — one private worker `_replace_fragment(stage_json, concept_key, rule, mod_type)` plus three thin public wrappers `apply_paraphrase`, `apply_expansion`, `apply_compression`. The worker locates the `"FRAG" * (CONDITION)` segment inside `stage_json[concept_key]["text_variables"][var_key]` (after stripping a leading `$` from the rule's `var`), captures the live quoted fragment as `original`, and rewrites the segment with `f'"{rule["new"]}" * ({as_written_cond})'` — preserving the catalog's as-written condition verbatim. The module-level regex `_FRAGMENT_PAT = re.compile(r'"(?P<frag>[^"]*)"\s*\*\s*\(\s*(?P<cond>[^)]*)\s*\)')` enumerates candidate fragments; `_norm(s)` collapses runs of whitespace before condition equality comparison so a single-space rule still matches the catalog's double-space `or` clause. Supports both str-typed entries (single-formula vars like `K`, `I`, `N`) and list-typed entries with at least one conditional element (`P`). Pure lookup-table list entries (`G` = `['"Diurno"', '"Nocturno"', ...]` with no `* (` segment in any element) raise `ValueError` with a message naming the var and explaining the shape mismatch.
- Promoted the three L2 entries inside [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH` from stubs to the new `apply_*` wrappers. Added the `from .layer_l2 import (apply_compression, apply_expansion, apply_paraphrase)` import block under the existing L1 import. Deleted the three obsolete `_stub_paraphrase` / `_stub_expansion` / `_stub_compression` function definitions. Updated the module docstring from "6 L1 live, 6 still stubs" to "6 L1 + 3 L2 live, 3 still stubs (L3 / PD)". `_apply_rules` / `_resolve_type` / `_gate_layer` / `apply_l1`/`l2`/`l3`/`apply_new_param` are untouched.
- Added [`tests/synthetic/test_layer_l2.py`](../../tests/synthetic/test_layer_l2.py) — 18 contract test cases driving an inline `oeb020_stage3` fixture mirroring the real `OEB020$` shape (str-typed `K` / `I` / `N`, list-typed conditional `P`, and lookup-table list `G` for the out-of-scope error path): 3 parametrised happy-path cases (one per wrapper, on `K` / `I` / `K` respectively), 1 list-typed-conditional case (`P`), 1 `$`-strip equivalence test, 1 stale-`original` test pinning the "log-`original`-is-authoritative" asymmetry, 1 orchestrator-threading test (3-rule batch through `apply_l2` with deep-copy purity assertion), 1 compound-`or` preservation test (double-space `%B=="b"  or  %B=="g"` survives verbatim), 1 whitespace-normalised-match test (single-space rule matches double-space fixture, emits as-written form), 1 lookup-table-list `ValueError` test (`var="G"`), 3 missing-target tests (concept/var/condition all assert the `KeyError` message names the missing entry), 2 invalid-rule-shape tests (empty `new`, missing `condition` field), 1 caller-purity snapshot test, 1 fragment-bytewise-preservation test (`re.findall(r'"[^"]*"', ...)` pre/post — exactly one element differs), 1 direct `_replace_fragment` call.
- Narrowed [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py): `_STUB_TYPES` shrinks from "non-PARAM_VALUE" (6 cases) to "TEMPLATE or PARAM_DEFINITION" (3 cases: `omission`, `reorder`, `new_param`) — `[t for t in ModificationType if TYPE_TO_LAYER[t] in (Layer.TEMPLATE, Layer.PARAM_DEFINITION)]`. `test_deep_copy_purity_on_notimplemented` swapped its rule from `{"type": "paraphrase"}` against `apply_l2` (now live) to `{"type": "omission"}` against `apply_l3` (still a stub). No other tests touched.

**Key results:**
- `pytest tests -q` → **78 passed in 0.12s, zero failures, zero skips.** Baseline 63 (Sprint 07); net delta −3 (L2 stub cases narrowed out of the parametrised stub test) + 18 (new `test_layer_l2.py` cases — 3 parametrised happy-path + 15 specific cases) = +15. The sprint plan's projected "75 passed" target modelled exactly 15 new tests; 18 ≥ 15 satisfies the binding gate.
- Dispatcher audit smoke check: `9 live, 3 still stubs`. Every `PARAM_VALUE` and `TEXT_VARIABLE` entry in `_DISPATCH` resolves to an `apply_*` function; every other entry still resolves to a `_stub_*`. The 12-entry invariant (`set(_DISPATCH) == set(ModificationType)`) is unchanged.
- `from synthetic.mutator import _stub_paraphrase` correctly raises `ImportError` — the three obsolete L2 stub definitions are physically gone.
- End-to-end smoke: `apply_l2(stage, "OEB020$", [{"type":"paraphrase","var":"K","condition":'%B=="a"',"new":"estandar"}])` mutates only the targeted fragment inside the returned `out`, caller input is byte-identical under `json.dumps(sort_keys=True)` pre/post, emitted `Modification` carries `var="K", condition='%B=="a"', original="normal", new="estandar", status="applied", layer=TEXT_VARIABLE`.
- `git status --short` end-of-sprint reflects exactly the four sprint-scoped files plus the two log files: new `src/synthetic/layer_l2.py`, modified `src/synthetic/mutator.py`, new `tests/synthetic/test_layer_l2.py`, modified `tests/synthetic/test_mutator.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`. Nothing under `src/utils/`, no notebooks, nothing under `data/` / `configs/`.

**Decisions confirmed:**
- **Whitespace normalisation is matcher-only, never writer.** `_norm` collapses runs of whitespace before condition equality comparison; the writer preserves the catalog's as-written `cond` group verbatim. The rewritten formula stays byte-equivalent to the original in every region the rule didn't target. `Modification.condition` records the as-written form so downstream consumers see what's actually in the formula. Verified by `test_compound_or_condition_preserved` (double-space survives) and `test_whitespace_normalized_condition_match` (single-space rule still matches).
- **`$`-prefix tolerance lives at the L2 rule boundary, not in the data.** Stage-3 JSON keys are bare (`K`, `I`, `N`); `RESEARCH_PROPOSAL.md §6.1`'s worked example shows `"var": "$I"` because the catalog's authors think in reference-syntax terms. The worker strips a single leading `$` if present; `Modification.var` is emitted in the bare form for consistency with the stage JSON's internal naming. Verified by `test_var_prefix_stripped`.
- **Pure lookup-table list entries fail loudly with `ValueError`, not `status="skipped"`.** A rule targeting `var="G"` with a `condition` has no fragment to address — the variant catalog (Phase C) is human-curated and a condition-on-lookup-table mismatch is a catalog-authoring error to surface at apply-time, not a runtime edge case to absorb. An `index`-addressed rule shape (`{"var": "G", "index": 0, "new": "..."}`) is **explicitly deferred** to keep B2's rule schema uniform with `(var, condition)`. Verified by `test_lookup_table_list_raises`.
- **Compound `or` conditions are opaque to the worker.** The condition is treated as a literal string handle for matching; the worker does not parse `%B=="b" or %B=="g"` into clauses. If a future variant catalog wants to mutate only one half of the disjunction, that's a different rule shape — explicitly deferred. The whole parenthesised expression is the addressing key.
- **Three wrappers, one worker — Sprint 07's pattern generalises cleanly.** L2's `_replace_fragment` is the L1 `_replace_value` pattern adapted for condition-addressed fragments inside formulas. The wrappers exist purely to set the `Modification.type` enum on the emitted record. Per-type semantic enforcement (does this "paraphrase" actually preserve meaning?) lives upstream in Phase C prompts and downstream in Phase E review, never inside the applier.
- **Outer-level `copy.deepcopy(stage_json)` stays inside `_apply_rules`, not the worker.** Same Sprint 07 contract — worker-level deep-copy would balloon costs on stacked rules in Phase B5 composition. The worker mutates its received `out` in place; caller purity is pinned by `test_caller_dict_unchanged_after_apply` and by the orchestrator-threading test's snapshot assertion.
- **No Spanish reference data inside `layer_l2.py`.** No paraphrase dictionaries, no expansion templates, no compression rules. The rule carries `new` as a literal fragment string; the mutator is semantic-blind. Per-type semantics belong in Phase C (`llm_proposer.py` + `prompts/paraphrase.txt` / `expansion.txt` / `compression.txt`) and Phase E (reviewer harness).

**Known issues:**
- Initial `test_missing_condition_raises` hit a subtle `KeyError.__str__` repr-wrapping quirk on Python (the message gets repr'd so embedded single quotes appear as `\\'`). Worked around by using `excinfo.value.args[0]` to inspect the raw message string. Documented for future stub tests; non-blocking.
- 3 stubs remain in `mutator.py` (L3 ×2, PD ×1). They continue to raise `NotImplementedError`; B3 + B4 will narrow this to zero, at which point the parametrised stub test in `test_mutator.py` gets deleted entirely.
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (78 passed prints before the traceback). Cosmetic; no action.

**Next step:** **Sprint 09 — Phase B Task B3 (`layer_l3.py` — template mutators).** Promote the two L3 stubs (`omission`, `reorder`) to real bodies. Templates are the `resumen` / `texto` strings at stage-4 (post-variable-substitution). The addressing scheme is structural (`field` + sentence/token/paragraph span), not condition-keyed — design the worker accordingly. After B3 lands, `_STUB_TYPES` shrinks to `[NEW_PARAM]`; after B4 it becomes `[]` and the parametrised stub test in `test_mutator.py` is removed entirely.

### After Sprint 07 — Phase B Task B1: L1 `param_value` mutator bodies (`layer_l1.py`)
**Date:** 2026-05-19
**What changed:**
- Created [`src/synthetic/layer_l1.py`](../../src/synthetic/layer_l1.py) — one private worker `_replace_value(stage_json, concept_key, rule, mod_type)` plus six thin public wrappers `apply_synonym_label`, `apply_num_to_text`, `apply_unit_conversion`, `apply_unit_expansion`, `apply_abbrev_expansion`, `apply_code_expansion`. The worker resolves `(concept_key, param, value_label)` against the stage JSON, captures the live `value_entry["value"]` as `original`, overwrites it with `rule["new"]`, and emits exactly one `Modification(layer=PARAM_VALUE, type=<wrapper's mod_type>, …, status="applied")`. The wrappers exist only to set the per-type enum on the emitted record — the *mechanics* are uniform across the six L1 types; the *semantics* live in `Modification.type`.
- Promoted the six L1 entries inside [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py)'s `_DISPATCH` from stubs to the new `apply_*` wrappers. Added the `from .layer_l1 import …` block under the existing `from .taxonomy import …`, deleted the six obsolete `_stub_synonym_label` / `_stub_num_to_text` / `_stub_unit_conversion` / `_stub_unit_expansion` / `_stub_abbrev_expansion` / `_stub_code_expansion` function definitions, and swapped the six matching `_DISPATCH` entries. Updated the module docstring from "all 12 stubs raise" to "6 L1 live, 6 still stubs". `_apply_rules` / `_resolve_type` / `_gate_layer` / `apply_l1`/`l2`/`l3`/`apply_new_param` are untouched.
- Added [`tests/synthetic/test_layer_l1.py`](../../tests/synthetic/test_layer_l1.py) — 15 contract test cases driving an inline 5-axis `oeb020_stage2` fixture: 6 parametrised happy-path cases (one per type), 1 orchestrator threading test, 1 stale-`original` test pinning the "log-`original`-is-authoritative" asymmetry, 3 missing-target cases (concept/param/value-label all assert the `KeyError` message names the missing entry), 2 invalid-`new` cases (empty string + missing key), 1 caller-purity snapshot test, 1 direct `_replace_value` call.
- Narrowed [`tests/synthetic/test_mutator.py`](../../tests/synthetic/test_mutator.py): `test_each_stub_raises_notimplemented_with_type_code` parametrises over `_STUB_TYPES = [t for t in ModificationType if TYPE_TO_LAYER[t] is not Layer.PARAM_VALUE]` (6 cases — paraphrase, expansion, compression, omission, reorder, new_param) instead of all 12; `test_deep_copy_purity_on_notimplemented` swapped its rule from `synonym_label` to `paraphrase` and its entry-point from `apply_l1` to `apply_l2`. No other tests touched.

**Key results:**
- `pytest tests -q` → **63 passed in 0.12s, zero failures, zero skips.** Baseline 54 (Sprints 01–05); net delta −6 (L1 stub cases narrowed out of the parametrised stub test) + 15 (new `test_layer_l1.py` cases) = +9. Binding gate satisfied (≥13 new L1 contract cases; all surviving baseline tests still green).
- Dispatcher audit smoke check: `6 L1 live, 6 still stubs`. Every `PARAM_VALUE` entry in `_DISPATCH` resolves to an `apply_*` function; every other entry still resolves to a `_stub_*`. The 12-entry invariant (`set(_DISPATCH) == set(ModificationType)`) is unchanged.
- `from synthetic.mutator import _stub_synonym_label` correctly raises `ImportError` — the six obsolete stub definitions are physically gone.
- End-to-end smoke: `apply_l1(stage, "OEB020$", [{"type":"synonym_label","param":"B","value":"a","new":"Estandar"}])` mutates only the targeted value entry inside the returned `out`, caller input is byte-identical under `json.dumps(sort_keys=True)` pre/post, emitted `Modification` carries `original="Normal", new="Estandar", status="applied"`.
- `git status --short` end-of-sprint reflects exactly the four sprint-scoped files plus the two log files this sprint touches: new `src/synthetic/layer_l1.py`, modified `src/synthetic/mutator.py`, new `tests/synthetic/test_layer_l1.py`, modified `tests/synthetic/test_mutator.py`, modified `docs/synthetic/CLAUDE_SYNTHETIC.md`, modified `docs/synthetic/RESEARCH_LOG.md`. Nothing under `src/utils/`, no notebooks, nothing under `data/` / `configs/`. Unrelated pre-existing untracked items (Sprint 05/06/6.5 docs, `scripts/`, `.gitignore`, `__pycache__/`) are preserved untouched.

**Decisions confirmed:**
- **Rule's `original` is informational; log's `original` is authoritative.** The worker never reads `rule.get("original")`; `Modification.original` is sourced from the live stage value the worker overwrites. Pinned by `test_modification_original_sourced_from_stage_json` (rule says `"WRONG"`, log says `"Normal"`). The reason: variant catalogs (Phase C) may be reused across pipeline reruns where stage-2 JSON has shifted, and the log must record what *actually* changed at apply-time. Catalog-drift detection escalates to Phase E (reviewer harness), not to the applier.
- **Outer-level `copy.deepcopy(stage_json)` stays inside `_apply_rules`, not the worker.** Worker-level deep-copy would balloon costs on stacked rules (Phase B5 composition). The worker mutates its received `out` in place — legitimate because `_apply_rules` deep-copies once at the orchestrator boundary. Caller purity is verified by `test_caller_dict_unchanged_after_apply` and by the orchestrator-threading test's snapshot assertion.
- **No Spanish reference data ships inside `layer_l1.py`.** No number-word tables, no unit-conversion lookups, no acronym dictionaries, no code expanders. The rule carries `new` as a literal string; the mutator is semantic-blind. Per-type semantics belong in Phase C (`llm_proposer.py` + `prompts/synonym_label.txt` / `num_to_text.txt` / etc.) and Phase E (reviewer harness). The applier is intentionally deterministic value-replacement.
- **Six wrappers, one worker — uniform mechanics is the design, not a smell.** Per-type behavioural divergence at the applier layer would couple unrelated semantic concerns (a unit-conversion mutator validating "is this still a valid unit string?" would have to ship Spanish unit grammar). Keeping the wrappers thin pins the "meaning lives in the type code, mechanism is value-replacement" contract — downstream slice analysis reads the type code, not the mechanism.
- **Unstackable-combo handling deferred to B5.** Workers don't check whether an earlier rule in the same batch already rewrote the target value — they just overwrite. The composition layer (B5) will enforce stacking constraints (reorder / skip with `status="skipped"` + `reason` / reject up-front). Per-mutator pre-checks would couple unrelated layers and complicate the worker's single-responsibility contract.
- **`_replace_value` imported by the test suite as a deliberate internal-consumer exception.** The underscore-prefix signals "not part of the public surface", but `test_replace_value_directly` exercises it to verify worker-level correctness without going through a wrapper. Keeps the test suite honest about the boundary between the wrappers (which exist for semantic labelling) and the worker (which exists for mechanical replacement).

**Known issues:**
- Sprint plan's headline pytest target (≥67) is internally inconsistent with the plan's own stub-narrowing instruction. Actual count is 54 - 6 + 15 = 63. The binding gate (≥13 new L1 contract cases, no skips, no regressions) is met; logging the inconsistency here so the next sprint's plan review catches this earlier.
- 6 stubs remain in `mutator.py` (L2 ×3, L3 ×2, PD ×1). They continue to raise `NotImplementedError`; B2–B4 will narrow this further.
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from prior sprints (63 passed prints before the traceback). Cosmetic; no action.

**Next step:** **Sprint 08 — Phase B Task B2 (`layer_l2.py` — text-variable mutators).** The dispatcher wiring pattern (import block + `_DISPATCH` swap + obsolete stub deletion) generalises directly to L2. Note: the L2 rule schema is *not* the same as L1's — it needs `var` + `condition` keys (per the `Modification` dataclass fields and the worked example in `RESEARCH_PROPOSAL.md §6.1`), not `param` + `value`. Design the worker accordingly. After B2 + B3 land, `_STUB_TYPES` in `test_mutator.py` shrinks to `[NEW_PARAM]`; after B4 it becomes `[]` and the parametrised stub test is removed entirely.

### After Sprint 6.5 — Cleanup fixes from Sprint 06 findings (s07 sorted iter + Generate_OEB resumen writer)
**Date:** 2026-05-19
**What changed:**
- [`src/s07_Filter_duplicates.ipynb`](../../src/s07_Filter_duplicates.ipynb) cell 8 (id `8d1aea31`): `for key in either_duplicate_keys:` → `for key in sorted(either_duplicate_keys):`. Single-token fix that makes `_either_duplicate.json` byte-deterministic run-to-run (set iteration order was PYTHONHASHSEED-randomized).
- [`src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb): inserted new code cell at index 8 (id `6060ae5d-136a-4cd4-8e53-848cec21af70`) that writes `OEB_resumen.pkl` to `config.PROCESSED_DIR` — mirrors cell 3's filter-and-pickle pattern for resumen. Cell count 10 → 11; the JSON producer (id `b9f644bb`) shifted from index 8 to 9 with no content change. Cell 3's cwd-relative output left untouched (Sprint 04 policy preserved).
- [`scripts/sprint06_validate_e2e.py`](../../scripts/sprint06_validate_e2e.py) `PICKLE_DIFFS` extended with `processed/OEB_resumen.pkl`. Total rows 24 → 25.

**Key results:**
- **Differ: 25/25 PASS, exit 0.** All Sprint 06 rows still PASS (no regressions). New `OEB_resumen.pkl` row PASSES with 47,514 docs, text+metadata identical to the in-repo Jan-12 reference.
- **In-repo `OEB_resumen.pkl` is content-identical to the new cell's output.** Whatever historical process produced the in-repo file used the same filter rule (`item_key.startswith("OEB")` on `OBRA CIVIL_resumen.pkl`). The new cell is the canonical writer going forward.
- **Fix 1 determinism gate PASS.** Two consecutive s07 runs produced `_either_duplicate.json` with MD5 `0e1d872bbaf5bf81bc0d3011c1d254e4` both times — byte-identical across runs. Sprint 06's set-iteration nondeterminism is gone.
- Validation rerun wall-clock: ~3m30s (consistent with Sprint 06's 3m44s).

**Decisions confirmed:**
- **In-repo `data/` stays frozen at Jan-12 ground truth.** Neither `OEB_resumen.pkl` nor `_either_duplicate.json` overwritten despite content equivalence — the policy is "validate against ground truth, don't move it".
- **Generate_OEB asymmetry preserved.** Cell 3 cwd-relative + new cell `config.PROCESSED_DIR`-relative is intentional minimum-radius design. Future cleanup candidate if Generate_OEB ever gets a comprehensive refactor.
- **Sprint named "6.5" not "07".** Patch sprint for Sprint 06 findings; Sprint 07 stays reserved for Phase B Task B1.
- **`bc3cat-retrieval` coupling check (pre-execution): zero `OEB_resumen.pkl` hits in the sibling repo.** The pickle is dataset-internal; sibling reads `OEB_resumen.json` in two notebooks (`cross_encoder.ipynb`, `hybrid.ipynb`). No cross-repo coordination needed.

**Known issues:**
- `bc3cat-sprint06` container reports "(unhealthy)" because no Jupyter HTTP endpoint runs in the standalone `sleep 3600` loop. Cosmetic; `docker exec` works fine.
- `data_validation/` tree (1.9 GB, gitignored) can be deleted with `rm -rf data_validation/` after validation done.

**Next step:** **Sprint 07 — Phase B Task B1 (`layer_l1.py`)**. Foundation now fully verified-clean. Promote Sprint 01's `_DISPATCH` stubs to real bodies for the 6 L1 `param_value` mutator types on `OEB020$` as the canonical test concept.

### After Sprint 06 — End-to-end validation in Docker; Sprints 02–05 runtime-verified; **Phase A closed**
**Date:** 2026-05-19
**What changed:**
- Built [`scripts/sprint06_validate_e2e.py`](../../scripts/sprint06_validate_e2e.py) (new) — 20 byte-diff rows + 1 JSON content-diff row + 3 pickle content-diff rows = 24 total. Pickle comparison sorts by `item_key` and ignores LlamaIndex's auto-`id_`. JSON content-diff handles dict ordering tolerantly while still reporting whether bytes matched.
- Added [`.gitignore`](../../.gitignore) (new file) with single entry `data_validation/`.
- Ran s01 → s07 → s08 → `Generate_OEB_dataset` in a standalone Docker container (`bc3cat-sprint06`, same image as `docker-compose.yml` but no port bindings — workaround for Windows port-8050 reservation) with `BC3CAT_DATA_ROOT=/work/data_validation`. Pipeline wall-clock **3m44s**; aggregate output 1.8 GB intermediate + ~240 MB processed.
- Captured the validation report at [`docs/synthetic/sprints/SPRINT_06_REPORT.md`](sprints/SPRINT_06_REPORT.md).

**Key results:**
- **24 / 24 PASS, exit code 0.** Sprints 02–05 are runtime-verified behavior-preserving.
- The 786 MB `OBRA CIVIL_stage4.json` is byte-identical between original and rerun. So are stage3 (387 MB), stage5 (250 MB), stage6 (201 MB), stage7 (225 MB). The path refactor + import-shape cleanup did not perturb any downstream byte.
- LlamaIndex `Document` content (text + metadata, 111,644 docs in each of the OBRA CIVIL pickles + 47,514 in `OEB_texto.pkl`) is identical when ignoring auto-generated `id_` UUIDs.
- Two findings surfaced — both pre-existing, neither a refactor regression:
  1. `OBRA CIVIL_either_duplicate.json` bytes differ run-to-run because s07 cell 8 iterates `either_duplicate_keys = set()` (PYTHONHASHSEED randomization). Content (15,294 entries) is identical per-key. One-line fix candidate: `sorted(either_duplicate_keys)`.
  2. `Generate_OEB_dataset.ipynb` cell 8 errors reading `OEB_resumen.pkl` that no cell writes — the in-repo `data/processed/OEB_resumen.pkl` is produced by `bc3cat-retrieval`. Cell 4 (writes `OEB_texto.pkl`) runs cleanly and is the one Sprint 06 gates on.

**Decisions confirmed:**
- **Phase A closes with Sprint 06.** The path refactor (Sprints 02–04) and import-shape cleanup (Sprint 05) collectively land the file-map deliverables A1–A5 (excluding A3 which was already done at the protocol-design level). With the static-check gate now backed by runtime byte-and-content equivalence, the only remaining Phase-A work is the s07 set-iteration and the missing `OEB_resumen.pkl` writer cell — both classified as low-priority quality-of-life cleanups, not Phase-A blockers.
- **Spun up `bc3cat-sprint06` standalone container** instead of editing `docker-compose.yml`. The compose port-8050 conflict is host-environment-specific; modifying the compose file is a cosmetic config change that doesn't belong in a validation sprint.
- **Added a JSON content-diff bucket** to the differ mid-sprint after the first run flagged `_either_duplicate.json` as a byte mismatch. Accepting it as a FAIL would have buried a genuine PASS signal under nondeterminism noise. The differ now reports both axes: `bytes differ (set-iteration order)` honestly, with `content identical, 15,294 entries`.
- **Did NOT fix either pre-existing notebook bug.** Sprint 06 is a validation sprint; mutating notebooks during validation would defeat its purpose. Both are logged as future-cleanup candidates.

**Known issues:**
- s07 cell 8 set-iteration: 1-line fix candidate, not Phase-B-blocking.
- `Generate_OEB_dataset.ipynb` missing `OEB_resumen.pkl` writer cell: small fix, not Phase-B-blocking.
- `data_validation/` tree (1.9 GB) is gitignored — can be deleted with `rm -rf data_validation/` if disk pressure matters.
- `bc3cat-sprint06` container kept around for follow-up; remove with `docker rm -f bc3cat-sprint06` when no longer needed.

**Next step:** **Sprint 07 — Phase B Task B1 (`layer_l1.py`).** Write real bodies for the 6 L1 `param_value` mutators: `synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`. Promote the Sprint 01 stubs through the existing `_DISPATCH` table in [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py). Add a contract-test suite that exercises each of the 6 types on a representative concept (`OEB020$` is the canonical example). Sprint 07's gate: 30 + 12 + 7 + 2 + 3 = pytest count stays at 54 baseline (no removals) + new B1 contract tests.

### After Sprint 05 — Import-shape cleanup: relative imports in `src/utils/*.py` + `Generate_OEB_dataset` bootstrap retirement
**Date:** 2026-05-19
**What changed:**
- Switched the 5 `from src.utils.X` absolute self-imports inside `src/utils/` to relative form across three files: [`src/utils/data_utils.py`](../../src/utils/data_utils.py) line 6 (`.custom_types`), [`src/utils/evaluation.py`](../../src/utils/evaluation.py) line 4 (`.custom_types`), [`src/utils/index_classes.py`](../../src/utils/index_classes.py) lines 10–12 (`.text_processing`, `.custom_types`, `.config`). Five single-line edits totalling `+5/−5` across the three modules.
- Retired the [`src/Generate_OEB_dataset.ipynb`](../../src/Generate_OEB_dataset.ipynb) cell 2 bootstrap in one `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle: `from src.utils.data_utils import load_documents` → `from utils.data_utils import load_documents` (symmetric with the cell's existing `from utils import config`); `project_root = config.REPO_ROOT` + `sys.path.append(str(project_root))` + the blank separator above them deleted; cell 2 ends as a single 9-line contiguous import block. **The path refactor's final `sys.path.append(...)` shim retires here.**
- Added the regression-guard test [`tests/utils/test_utils_no_absolute_self_imports.py`](../../tests/utils/test_utils_no_absolute_self_imports.py) — 3 parametrised cases scanning each of the three modules for `^\s*(from|import)\s+src\.utils\b` and asserting zero hits.

**Key results:**
- `pytest tests -q` → **54 passed in 0.17s** (51 from Sprint 04 + 3 new `from src.utils.X` guard cases). No regressions; no skips.
- Both smoke checks pass: `py_compile` on the three edited modules compiles cleanly (substituted for the planned runtime-import check because `custom_types.py` imports `llama_index` + `scipy` at module level, outside this host's static-check env — same gap Sprints 02–04 maintained); `Generate_OEB_dataset.ipynb` cell 2 invariants check passes (`sys.path.append`: absent, `from src.utils`: absent, `from utils.data_utils import load_documents`: present).
- `git diff --numstat`: `src/utils/data_utils.py +1/−1`, `src/utils/evaluation.py +1/−1`, `src/utils/index_classes.py +3/−3`, `src/Generate_OEB_dataset.ipynb +1/−5` (vs the plan's "roughly +1/−4" — git accounts for the import swap as add+delete on top of the four pure deletions; semantically identical to the plan). End-of-sprint `git status --short` matches the sprint plan's expected file list exactly.

**Decisions confirmed:**
- **Relative imports inside `src/utils/` are caller-agnostic.** Python resolves `.custom_types` against the loaded package context regardless of whether the caller imports as `from src.utils.X` (namespace-package shape) or `from utils.X` (kernel-cwd-anchored shape). Sprint 05's cleanup does not break any hypothetical absolute-import caller that hasn't been migrated yet — it only removes the absolute self-imports *inside* the package.
- **`bc3cat-retrieval` mirror is a sibling-repo task, not a follow-up here.** The retrieval repo carries parallel filesystem copies of all five `from src.utils.X` lines plus one downstream consumer (`src/pipeline/param_extractor_rules.py`). No files are shared at the FS level, so Sprint 05's diff cannot break sibling runtime. Mirroring the cleanup is optional consistency work on the retrieval side.
- **`src/__init__.py` deliberately not added.** After Sprint 05 no in-repo caller needs `src` to be importable — the three `src/utils/*.py` modules use relative imports, the notebook uses `from utils.X`. Adding `src/__init__.py` would reintroduce the namespace-package dependency the sprint specifically eliminates.
- **Unused imports (`os`, `Path`, `gc`) in cell 2 left in place.** Same Sprint 03/04 policy. `import sys` is removed naturally because the bootstrap that used it is gone — that's the only line in the import block the strict scope touched besides the swap.
- **`index_classes.py` not importability-tested at runtime.** Transitive `scipy`/`sklearn`/`llama_index` deps inflate the env requirement past the static-check footprint. Source-text scan (Task 5) covers it instead; first module to gate on if a future sprint promotes to runtime-import testing.
- **LF line endings preserved** via `Path.write_bytes(...)` per the Sprint 03/04 recipe.

**Known issues:**
- End-to-end behaviour-preserving validation across the full main pipeline (s01 → s08 → `Generate_OEB_dataset` rerun + byte-diff against in-repo `OEB_*.parquet` / `*.pkl`) still pending — same hedge as Sprints 02–04. Static-check gate only across Sprints 02–05. Requires Docker / `pandas` / `pyarrow` / `llama_index` env.
- `.ipynb_checkpoints/` under `src/` and `src/utils/` still carry the old `from src.utils.X` shape in stale `*-checkpoint.py` files; Jupyter auto-saves regenerate on next save. No action — same policy as Sprints 02–04.
- The atexit `cleanup_dead_symlinks` `PermissionError` on Windows after pytest exits is unchanged from Sprints 02–04 (54 passed prints before the traceback). Cosmetic; no action.

**Next step:** **End-to-end-validation sprint.** Sprints 02–05 collectively close the path refactor + import-shape cleanup; rerun s01 → s08 → `Generate_OEB_dataset` against the in-repo `data/intermediate/...` files inside a Docker / `pandas` / `llama_index` env and byte-diff the produced `data/processed/OEB_*.parquet` / `*.pkl` against the originals. If the diffs are empty, Phase A closes and Phase B (mutator bodies — Tasks B1–B4) becomes the next unit of work.

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
