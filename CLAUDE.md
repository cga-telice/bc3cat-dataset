# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BC3CAT Dataset is a Python/Jupyter pipeline that transforms raw BC3/FIEBDC format files from ADIF's (Spanish Railway Infrastructure Administrator) construction price catalog into a structured retrieval evaluation benchmark. It expands 30 parametric templates into ~47,500 unique items, each with a short-format description (*resumen*, used as query) and a long-format technical specification (*texto*, used as retrieval target).

## Development Environment

**Docker (recommended):**
```bash
docker-compose up -d
# Jupyter at http://localhost:8888 (token: j)
# Port 8050 also exposed for Dash
```
Base image: `quay.io/jupyter/pytorch-notebook:cuda12-python-3.11.8`. The container mounts the repo at `/work`.

**Manual setup:**
```bash
python -m venv venv && source venv/bin/activate
pip install jupyter pandas numpy scipy scikit-learn llama-index
```

## Running the Pipeline

Notebooks in `src/` must be executed sequentially — each stage depends on the previous stage's output:

1. `s01_parse_fiebdc.ipynb` — Parse BC3 format to JSON
2. `s02_split_chapters.ipynb` — Split into 10 technical chapters
3. `s03_generate_parametric_combinations.ipynb` — Expand parametric templates
4. `s04_evaluate_text_variables.ipynb` — Resolve formula-based text variables
5. `s05_evaluate_resumen_texto.ipynb` — Generate resumen/texto pairs
6. `s06_data_analysis.ipynb` — Statistical analysis
7. `s07_Filter duplicates.ipynb` — Deduplicate entries
8. `s08_Llamaindex_Doc_Creation.ipynb` — Convert to LlamaIndex Documents

Then run `Generate_OEB_dataset.ipynb` to extract the OEB subcategory from the OBRA CIVIL chapter.

There is no automated test suite or linter configuration.

## Architecture

**Data flow:**
`data/raw/` (BC3 text) → `data/intermediate/` (per-chapter JSON, 10 chapters) → `data/processed/` (Pickle, JSON, Parquet)

**Utility modules** in `src/utils/`:
- `config.py` — Centralized paths and retrieval hyperparameters (TOP_K, BM25_K1, BM25_B). Paths reference `/work/data/` (Docker mount).
- `custom_types.py` — Type aliases: `DocumentList`, `RetrievalResult`, `EmbeddingVector`
- `data_utils.py` — Pickle loading and document sampling
- `text_processing.py` — Spanish text normalization (accent removal, lowercasing)
- `z_formula_processing.py` — Translates BC3 formula syntax to Python (custom operators, math functions, conditionals)
- `index_classes.py` — `SparseBM25Vectorizer` (builds BM25-weighted sparse matrices) and `SparseBM25Retriever` (top-K retrieval via sparse matrix multiplication). Also contains `TreeNode` for hierarchical indexing.
- `evaluation.py` — Retrieval metrics: Success@K, MRR, MAP, mean position, prefix matching (first 6 chars of item_key = parent template)

**Document structure:** LlamaIndex `Document` objects with `text` field and metadata dict containing `item_key` (e.g., "OEB020$AAAAAA"), `parent_key` (first 6 chars, identifies base template), and `ud` (unit of measure).

## Key Conventions

- Dataset content is in **Spanish** (construction domain terminology)
- BC3/FIEBDC is the Spanish standard for construction cost database interchange; record types include `~C` (concepts), `~P` (parameters), `~T` (text blocks)
- Large files (.pkl, intermediate JSON, processed JSON) are tracked with **Git LFS** — see `.gitattributes`
- Dual licensing: **MIT** for code, **CC-BY 4.0** for dataset files
