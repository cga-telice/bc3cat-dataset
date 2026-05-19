# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Branch note:** If working on the `synthetic` branch, read [`docs/synthetic/CLAUDE_SYNTHETIC.md`](docs/synthetic/CLAUDE_SYNTHETIC.md) for branch-specific context before doing anything else.

> ⚠ **Never merge `synthetic` back to `main`.** BC3CAT-Syn research is a permanent parallel branch: it lives in isolation so the original BC3CAT pipeline on `main` stays byte-identical. Do not propose merges, fast-forwards, or rebases of `synthetic` into `main` — neither locally nor via pull request. If a PR is opened for `synthetic` work, its base must be `synthetic` (or another sub-branch of it), never `main`.

## Project Summary

BC3CAT Dataset is the **data-generation pipeline** that turns ADIF's BC3/FIEBDC parametric construction price catalog into the retrieval benchmark consumed downstream by the [`bc3cat-retrieval`](../bc3cat-retrieval) project. The pipeline expands ~30 base templates from the OEB chapter of the BPA 2024 v2 catalog into **47,513 OEB items** through parametric Cartesian expansion, formula evaluation, and template instantiation.

Output artifacts:
- `data/processed/OEB_long_norm.parquet` — long-form `texto` descriptions (retrieval targets).
- `data/processed/OEB_short_norm.parquet` — short-form `resumen` descriptions (retrieval queries).
- `data/processed/OEB_{long,short}_feats.parquet` — same rows with extra tokenized columns for lexical retrieval.

## Environment Setup

Docker is the primary development environment:

```bash
docker-compose up -d          # Jupyter (port 8888, token: j)
```

Inside the Jupyter container the repo is mounted at `/work`. **Paths inside notebooks currently assume `/work/...`** — most notably `s01_parse_fiebdc.ipynb` reads from `/work/data/raw/`. Outside Docker this needs the path refactor described in the synthetic-branch protocol (Task A4).

Manual setup alternative:

```bash
python -m venv venv && .\venv\Scripts\activate
pip install pandas pyarrow numpy tqdm pyyaml jupyter
```

## Architecture

### Pipeline-Stage Contract

The pipeline is a **deterministic JSON → JSON cascade** across eight numbered stages, followed by a Parquet packaging step. Every stage reads its predecessor's JSON file from `data/intermediate/{CHAPTER}/` and writes its own.

```
data/raw/*.txt  ──►  s01  ──►  s02  ──►  s03  ──►  s04  ──►  s05  ──►  s06  ──►  s07  ──►  Generate_OEB_dataset
                     parse  split   expand   vars     render   stats   dedup   filter + Parquet
```

| Stage | Notebook                                  | Output                                       | What it does                                                                            |
|:-----:|-------------------------------------------|----------------------------------------------|-----------------------------------------------------------------------------------------|
| **s01** | `s01_parse_fiebdc.ipynb`                | `BPA_2024_v2_OEB_mod_utf8.json`              | Parses FIEBDC-3/2016 — `~C`, `~P`, text variables, `\RESUMEN\`, `\TEXTO\`.              |
| **s02** | `s02_split_chapters.ipynb`              | `{CHAPTER}/{CHAPTER}.json`                   | Groups items by first character into ARQUITECTURA / OBRA CIVIL / ENERGIA / …            |
| **s03** | `s03_generate_parametric_combinations.ipynb` | `{CHAPTER}_stage3.json`                  | Cartesian product over parameter axes via `itertools.product`. The expansion happens here. |
| **s04** | `s04_evaluate_text_variables.ipynb`     | `{CHAPTER}_stage4.json`                      | Resolves `$VAR = "..." * (%X=y) + ...` formulas using `src/utils/z_formula_processing.py`. |
| **s05** | `s05_evaluate_resumen_texto.ipynb`      | `{CHAPTER}_stage5.json`                      | Replaces `$L(...)` and `$A` placeholders in the `\RESUMEN\` / `\TEXTO\` templates.       |
| **s06** | `s06_data_analysis.ipynb`               | *(stats only, no file)*                      | Word/parameter statistics; validation.                                                  |
| **s07** | `s07_Filter_duplicates.ipynb`           | `{CHAPTER}_stage7.json`                      | Marks and removes items with duplicate `resumen` / `texto`.                              |
| **fin** | `Generate_OEB_dataset.ipynb`            | `data/processed/OEB_*.parquet`               | OEB-subset filter + Parquet/Pickle export.                                              |

### Three-Layer BC3 Grammar

Every BC3 concept is generated from three composable layers. Any branch that modifies the catalog (notably `synthetic`) operates against this grammar.

| Layer | What it holds                                                       | BC3 record example                                                  |
|:-----:|---------------------------------------------------------------------|---------------------------------------------------------------------|
| **L1** | Parameter axes — labels and discrete value sets                   | `\ TIPO DE TERRENO \ Normal \ Bajo vías \ Rocoso \`<br>`%L(11)=1,2,3,4,5,6,...` |
| **L2** | Text variables — conditional string fragments selected by params  | `$K = "normal" * (%B=a) + "bajo vías" * (%B=b) + ...`              |
| **L3** | Output templates — `\RESUMEN\` and `\TEXTO\` strings              | `\TEXTO\ Canalización hormigonada de $A tubos ... $I, incluso $N ...` |

### Reusable Utilities (`src/utils/`)

- [`z_formula_processing.py`](src/utils/z_formula_processing.py) — `translate_formula_to_python()`, `quote_second_term()`. BC3 operator → Python operator translation.
- [`text_processing.py`](src/utils/text_processing.py) — `normalize_text()`. Spanish accent stripping + tokenization. Used for downstream lexical features.
- [`data_utils.py`](src/utils/data_utils.py) — IO helpers.
- [`evaluation.py`](src/utils/evaluation.py) — retrieval-eval helpers (mostly used by `bc3cat-retrieval`).
- [`index_classes.py`](src/utils/index_classes.py) — index abstractions.
- [`config.py`](src/utils/config.py) — single-source-of-truth paths. **Currently underused** — many notebooks hardcode `/work/...` paths instead of routing through here.
- [`custom_types.py`](src/utils/custom_types.py) — shared dataclasses.

### Data Layout

```
data/
├── raw/
│   └── BPA_2024_v2_OEB_mod_utf8.txt        # FIEBDC-3 source catalog (ISO-8859-1 → UTF-8)
├── intermediate/
│   ├── BPA_2024_v2_OEB_mod_utf8.json       # s01 output
│   └── OBRA CIVIL/                          # s02–s07 outputs (one folder per chapter)
│       ├── OBRA_CIVIL.json                  # s02
│       ├── OBRA_CIVIL_stage3.json           # s03 (expanded)
│       ├── OBRA_CIVIL_stage4.json           # s04 (formulas resolved)
│       ├── OBRA_CIVIL_stage5.json           # s05 (templates instantiated)
│       └── OBRA_CIVIL_stage7.json           # s07 (deduplicated)
└── processed/
    ├── OEB_long_norm.parquet                # 47,513 long-form rows
    ├── OEB_short_norm.parquet               # 47,513 short-form rows
    ├── OEB_long_feats.parquet
    └── OEB_short_feats.parquet
```

## Key Conventions

- **Item-key derivation.** `item_key = parent_key[:-1] + parameter_label_sequence` (e.g., `OEB020aaeaa`). The `parent_key` ends with `$` and groups items into concept groups.
- **Parameter structure in Parquet.** `parameters` is a dict `{axis_id: {"label": "...", "values": [{"label": "a", "value": "..."}]}}`. Leaf items have exactly one value per axis.
- **Spanish text normalization.** Accent stripping + lowercasing via `normalize_text()`. Downstream lexical retrievers tokenize on the normalized field.
- **Encoding.** Raw BC3 is ISO-8859-1; the `_utf8` suffix in `BPA_2024_v2_OEB_mod_utf8.txt` indicates the converted source already used here.
- **No state shared between stages other than the on-disk JSONs.** Stages can be rerun in isolation as long as their input file exists.
- **Pickle / LlamaIndex caches** under `data/processed/` and notebook checkpoints (`.ipynb_checkpoints/`) are derived artifacts — clear them when the underlying data changes.

## Working on This Repo

- The pipeline notebooks live in `src/` and are numbered s01–s08 plus `Generate_OEB_dataset.ipynb`. Run in order.
- New work happens on a feature branch with documentation under `docs/{branch_name}/`. See `docs/synthetic/` for the current example.
- Large data files are tracked with Git LFS (`.gitattributes`).

## See Also

- [`README.md`](README.md) — public-facing repo description.
- [`DataInBrief_BC3CAT.docx`](DataInBrief_BC3CAT.docx) — Data-in-Brief manuscript for the original BC3CAT release.
- [`docs/synthetic/`](docs/synthetic) — BC3CAT-Syn (rule-modification synthetic benchmark) work on branch `synthetic`.
