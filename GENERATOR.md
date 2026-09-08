# BC3CAT-Syn — synthetic corpus generator

Reusable pipeline to generate **synthetic query corpora** from any FIEBDC/BC3
price catalogue, for retrieval-degradation studies.

The retrieval task these corpora serve: **query = a modified `TEXTO`** (long
description), **target = the original `TEXTO`**. Every synthetic item modifies the
`TEXTO`, so its query differs from its gold target.

Two corpora are produced:

- **STACKED** — each item stacks *all* modifications the concept structurally
  admits (maximum degradation).
- **SINGLE** — each item carries exactly *one* modification (to measure the
  retrieval impact of each modification type in isolation), and every item
  changes the `TEXTO`.

This branch is the clean, reusable code only. The full research history
(scaffolding, dead ends, resolutions) lives on the `synthetic` branch and the
tag `syn/research-2026-09-08`.

## Requirements

- Python deps in `requirements.txt` (pandas, pyarrow, pyyaml, …).
- `bc3param/` (bundled) parses and renders the BC3 catalogue.
- **Ollama** (e.g. via Docker) with `phi4:latest` and `qwen2.5:14b` — **only** to
  (re)generate the LLM rewrite *menus*. Building corpora from existing menus is
  pure deterministic recombination with **no LLM**.

## Inputs

1. A BC3 catalogue (`data/raw/<catalogue>.bc3`).
2. A stage JSON of the chapter's concept definitions (parameter axes and the
   `RESUMEN`/`TEXTO` templates).
3. A leaf inventory as long/short parquets (`item_key`, `parent_key`, `text`),
   derived from the catalogue via `bc3param`.

## Pipeline

Layers of the FIEBDC grammar: **L1** parameter values, **L2** conditional text
fragments, **L3** `RESUMEN`/`TEXTO` templates. Modification types:
`synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`,
`abbrev_expansion`, `code_expansion` (L1); `paraphrase`, `compression`,
`expansion` (L2); `reorder`, `template_paraphrase` (L3). (`omission` and
`new_param` are excluded from the corpora.)

1. **Menus (LLM, once per catalogue).**
   - L1/L2/L3 except template_paraphrase: `python -m synthetic.menu_runner run
     --stage-json <stage.json> --chapter-label <CH> --n 10
     --skip-types template_paraphrase`.
   - `template_paraphrase` (rounds × models, restore-and-validate):
     `python scripts/regen_template_paraphrase.py --stage-json <stage.json>`
     (phi4+qwen; ≥10 validated candidates per target, both RESUMEN and TEXTO).
   - Output: `data/synthetic/menus_<CH>/<type>.jsonl` (+ an LLM cache per model
     for reproducible replay without Ollama).

2. **Verdicts (mechanical, no LLM).**
   `python scripts/auto_verdicts_v2.py <menus-dir>` — rubric-v2 approval that
   rejects empty rewrites, generation residue, and no-ops (`new == original`).

3. **De-duplicate the target pool.**
   - Cross-concept twins (two concepts with byte-identical leaf text):
     `python scripts/dedup_corpus.py …` → `<CH>_target_{long,short}.parquet`.
   - Intra-concept duplicate descriptions:
     `python scripts/collapse_intra_dupes.py …`.
   Result: every target `(resumen, texto)` maps to exactly one concept.

4. **Corpora (recombination, no LLM).** Shared base-leaf sample:
   `python scripts/build_ablation_inventory.py --n 5000 …`. Then:
   - STACKED: `python -m synthetic.corpus_driver run --budgets
     configs/synthetic/variant_budgets_<CH>_ablation_stacked.yaml
     --require-texto-changed …`
   - SINGLE: `… variant_budgets_<CH>_ablation_single.yaml
     --require-texto-changed --texto-fields-only template_paraphrase,reorder …`
   `--require-texto-changed` drops any variant whose rendered `TEXTO` equals the
   original; `--texto-fields-only` restricts the named field-type modifications
   to their `TEXTO`-field rewrites.

5. **QA / guarantees.**
   - `python scripts/cross_concept_audit.py … --template-level` — 0 introduced
     cross-concept collisions (corpus- and template-level).
   - `python scripts/meaning_drift_flag.py …` — ranked review of paraphrases
     that drop source content (semantic-drift aid).

## Output

- `BC3CAT_Syn_items.parquet` — `item_key`, `original_key`, `concept_key`,
  `params`, `resumen`, `texto`, `modification_types`, `modification_count`.
- `BC3CAT_Syn_modifications.jsonl` — one record per item (1:1), listing the
  applied modifications.

## Design notes

- `modification_count` counts **applied** modifications only (skipped rules and
  no-op rewrites are never counted).
- A leaf can only take the modifications its structure admits: L2 needs
  conditional (non list-form) text variables; `unit_*` needs a unit embedded in
  the value (not only in the template).
- The whole corpus step is deterministic (seeded); the LLM menus are frozen and
  cached, so a corpus reproduces without Ollama.

## Tests

`python -m pytest tests` (reference/equivalence tests that need catalogue or
legacy data skip cleanly when those files are absent).
