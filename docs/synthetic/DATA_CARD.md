# BC3CAT-Syn — Data Card

**A Rule-Modification Synthetic Benchmark for Robustness Evaluation of Retrieval Methods on Parametric Construction Catalogs**

| Field             | Value                                                                 |
|-------------------|-----------------------------------------------------------------------|
| **Dataset**       | BC3CAT-Syn                                                            |
| **Version**       | format v1 (G1/G2 contract frozen); corpus **not yet generated** (pending F3) |
| **Branch**        | `synthetic` (parallel to `main`; never merged — see [`CLAUDE.md`](../../CLAUDE.md)) |
| **License**       | Dataset: **CC-BY 4.0** · Code: **MIT** (mirrors the parent BC3CAT release) |
| **Derived from**  | the BC3CAT OEB subset (`OEB_long_norm.parquet` / `OEB_short_norm.parquet`) |
| **Status**        | Format/schema/taxonomy/loader contract final; corpus-scale statistics are `TBD (pending F3 full generation)` |

> **One-line description.** BC3CAT-Syn is a synthetic, fully-traceable variant of
> the BC3CAT retrieval benchmark in which controlled linguistic modifications are
> applied at the *generation-rule* level (parameter values, text variables,
> output templates, parameter definitions) so that retrieval degradation can be
> attributed to specific transformations rather than aggregate noise.

> ⚠ **This card documents a frozen format, not a measured corpus.** The release
> format, schema, modification taxonomy, evaluation slices, and loader API are
> implemented and test-pinned (Phase G tasks G1/G2). The corpus itself has **not
> been generated** — F3 (full generation) is blocked on A3 (the concrete LLM
> transport). Every **corpus-scale statistic** below (item counts, per-type
> distributions, acceptance rates, throughput) is therefore an explicit
> `TBD (pending F3 full generation)` placeholder. A **post-F3 statistics refresh**
> of this card is a planned follow-up. No number here is fabricated or borrowed
> from the parent OEB corpus.

---

## 1. Provenance

BC3CAT-Syn is **derived from**, not independent of, the parent
[BC3CAT](../../README.md) dataset. BC3CAT turns ADIF's BC3/FIEBDC parametric
construction price catalog (BPA 2024 v2, OEB chapter) into a retrieval benchmark
of 47,513 OEB items via a deterministic JSON→JSON pipeline (`s01`–`s07` +
`Generate_OEB_dataset`). BC3CAT-Syn reuses **the same generation engine without
code changes**, feeding it controlled rule variations.

Every BC3 concept is generated from a **three-layer grammar** plus a
parameter-definition layer; each layer is a candidate modification site:

| Layer  | Code (`layer`)     | Content                                                          |
|:------:|--------------------|------------------------------------------------------------------|
| **L1** | `param_value`      | Discrete parameter value sets and their descriptive labels       |
| **L2** | `text_variable`    | Conditional text fragments selected by parameter combinations    |
| **L3** | `template`         | `\RESUMEN\` / `\TEXTO\` output templates interleaving literals and `$vars` |
| **PD** | `param_definition` | Introduction of a new parameter axis not present in the original |

Generation is a three-stage process (`RESEARCH_PROPOSAL.md §3`):

1. **LLM-proposed** (Phase C): per `(concept, modification_type)`, an offline LLM
   proposes a candidate rule variant under a strict-JSON contract at
   temperature 0.0 (one retry, then a `fallback: skipped` log entry).
2. **Rule-applied** (Phase B): the mutators (`layer_l1`/`layer_l2`/`layer_l3`/
   `layer_pd`) apply the accepted variant to the between-stage JSON; the existing
   `s03`–`s07` pipeline then renders it. Canonical apply order is **PD → L1 → L2
   → L3**.
3. **Reviewer-validated** (Phase E/F): a domain reviewer checks grammaticality,
   semantic preservation, axis distinguishability (for `new_param`), and metadata
   accuracy (`review.py`; F4 quality pass), with 100 % review of `new_param` and
   stratified sampling for the other eleven types.

See [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md) (motivation, taxonomy,
contributions) and [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) (roadmap,
design decisions, generation conditions).

---

## 2. Release files

The release is **two files, one key**, both under `data/synthetic/processed/`,
joined **1:1 on `item_key`**:

| File                                | Shape                  | Carries                                                        |
|-------------------------------------|------------------------|----------------------------------------------------------------|
| `BC3CAT_Syn_items.parquet`          | flat, columnar         | one row per synthetic item: the `ITEM_COLUMNS` record (§3)     |
| `BC3CAT_Syn_modifications.jsonl`    | ragged, one line / key | the per-item `modifications` log kept out of the flat Parquet (§4) |

The Parquet stays columnar and flat; the nested per-item modification log lives
in the JSONL sidecar. A baseline (zero-modification) item still gets a sidecar
line with `modifications: []`. The two files are a deterministic function of the
joined synthetic items; both writes are atomic and run-twice byte-identical.

---

## 3. Items schema (`BC3CAT_Syn_items.parquet`)

Exactly nine columns, in this frozen order (`packaging.ITEM_COLUMNS`):

| # | Column                | Type            | Semantics                                                                 |
|:-:|-----------------------|-----------------|---------------------------------------------------------------------------|
| 1 | `item_key`            | `str`           | Unique synthetic item key, `f"{leaf_key}_syn_{variante_id}"`.             |
| 2 | `original_key`        | `str`           | The originating catalog leaf key (`leaf_key[:-K]`, K = applied `new_param` count). The join key back to the parent OEB item. |
| 3 | `concept_key`         | `str`           | Concept-group back-pointer (grouping; not part of the §2.3 `to_dict`).    |
| 4 | `params`              | `dict[str,str]` | `{axis_id: value}` — one resolved value per axis (the leaf's parameter assignment). |
| 5 | `resumen`             | `str`           | Short-form description (retrieval **query** surface).                     |
| 6 | `texto`               | `str`           | Long-form description (retrieval **target** surface).                     |
| 7 | `variante_id`         | `str`           | Per-variant id (`{condition}_{sha1[:10]}`); `(item_key, original_key, variante_id)` is the unique join triple. |
| 8 | `modification_types`  | `list[str]`     | Flat list of `ModificationType.value`s applied to this item (§5). Supports per-type slicing. |
| 9 | `modification_count`  | `int`           | `len(modifications)`; `0` for baselines. Supports compositionality slicing. |

`modification_types` / `modification_count` are **recomputed** from the applied
`modifications` log at join time, never trusted from upstream copies. There is
**no** `modifications` column in the Parquet (it is the sidecar), and **no**
OEB-only `id`/`ud`/`concept` column — the items table mirrors the
`RESEARCH_PROPOSAL.md §2.3` per-item record plus `concept_key`, exactly.

---

## 4. Modifications sidecar (`BC3CAT_Syn_modifications.jsonl`)

One JSON object per line, 1:1 with the items table on `item_key`:

```json
{"item_key": "OEB020aaeaa_syn_v1",
 "modifications": [
   {"type": "num_to_text",   "layer": "param_value",   "param": "A", "original": "2",      "new": "dos"},
   {"type": "synonym_label", "layer": "param_value",   "param": "B", "value": "a", "original": "Normal", "new": "Convencional"},
   {"type": "paraphrase",    "layer": "text_variable", "var": "$I", "condition": "%B=a", "original": "...", "new": "..."},
   {"type": "compression",   "layer": "template",      "field": "RESUMEN"}
 ]}
```

Each modification record (`Modification.to_dict`) always carries `type` and
`layer`; the remaining keys are per-type optional context, emitted only when
present:

| Key         | Meaning                                                            |
|-------------|-------------------------------------------------------------------|
| `type`      | one of the 12 `ModificationType`s (required)                      |
| `layer`     | the modification's `Layer` (required)                             |
| `param`     | target parameter axis id (L1)                                     |
| `var`       | target text variable, e.g. `$I` (L2)                              |
| `condition` | the conditional selector, e.g. `%B=a` (L2)                        |
| `field`     | target template field, `RESUMEN` / `TEXTO` (L3)                   |
| `value`     | target value label within an axis                                |
| `original`  | the pre-modification surface form                                 |
| `new`       | the post-modification surface form                               |
| `status`    | `skipped` for an unstackable combination that was logged not applied |
| `reason`    | free-text reason accompanying a `skipped` status                 |

**Skip-and-log convention.** When a proposed modification cannot be stacked on a
target (an unstackable combination), it is **skipped and logged** (a record with
`status: "skipped"` + `reason`) rather than silently dropped — coverage may be
lost, but traceability is never corrupted.

---

## 5. Modification taxonomy

Twelve modification types across four layers (`taxonomy.ModificationType` /
`taxonomy.TYPE_TO_LAYER`):

| `type`             | `layer`            | Description                                  | Example                                  |
|--------------------|--------------------|----------------------------------------------|------------------------------------------|
| `synonym_label`    | `param_value`      | Replace a descriptive label with a synonym   | Normal → Estándar                        |
| `num_to_text`      | `param_value`      | Convert a numeric value to a written word     | 2 → dos                                  |
| `unit_conversion`  | `param_value`      | Convert to a different unit                  | 110 mm → 11 cm                           |
| `unit_expansion`   | `param_value`      | Expand a unit abbreviation                   | mm → milímetros                          |
| `abbrev_expansion` | `param_value`      | Expand a technical acronym                   | PVC → policloruro de vinilo              |
| `code_expansion`   | `param_value`      | Expand a domain code                         | HE-20 → hormigón estructural tipo 20     |
| `paraphrase`       | `text_variable`    | Reformulate while preserving meaning         | "en cualquier clase de terreno" → "en terreno normal" |
| `expansion`        | `text_variable`    | Verbose reformulation                        | Normal → Terreno de tipo normal          |
| `compression`      | `text_variable`    | Concise reformulation                        | "en cualquier clase de terreno" → "terreno normal" |
| `omission`         | `template`         | Remove a `$var` mention from the template     | Drop `$I` (terrain) from `\TEXTO\`       |
| `reorder`          | `template`         | Reorder template constituents                | `$A tubos ... $I` → `$I ... $A tubos`    |
| `new_param`        | `param_definition` | Add a parameter axis absent in the original  | Add `CALIDAD ACABADO` ∈ {Estándar, Premium, Industrial} |

The four layers are `param_value`, `text_variable`, `template`,
`param_definition`. `new_param` is the only type that does **not** preserve the
original parameter space; it tests whether retrievers degrade gracefully when the
catalog gains a new axis absent from query intent.

---

## 6. Evaluation slices

Two item-level slice columns ship in the items table:

- **`modification_types`** — per-type stratified evaluation (Acc@1 conditioned on
  the list containing each of the 12 codes); a per-**layer** slice is obtained by
  aggregating per-type via `TYPE_TO_LAYER`.
- **`modification_count`** — compositionality analysis (Acc@1 conditioned on
  `modification_count ∈ {1, 2, 3, 4, ≥5}`).

The orchestrator emits items under named **generation conditions**
(`RESEARCH_PROTOCOL.md §6`):

| Condition          | Layers mutated      | Stack depth   | Diagnostic purpose                              |
|--------------------|---------------------|---------------|-------------------------------------------------|
| `single_L1_*`      | one L1 type         | 1             | Per-type isolation slices for `param_value`     |
| `single_L2_*`      | one L2 type         | 1             | Per-type isolation slices for `text_variable`   |
| `single_L3_*`      | one L3 type         | 1             | Per-type isolation slices for `template`        |
| `new_param_only`   | `param_definition`  | 1             | Stress new-axis introduction in isolation       |
| `stacked_2` … `5+` | mixed               | 2, 3, 4, ≥5   | Compositionality slices                         |
| `full_random_mix`  | all                 | sampled       | Headline robustness slice                       |

Interpretation: `single_*` baselines isolate per-type degradation per retriever
family; `stacked_*` curves quantify whether degradation is sub-/linear/super-linear
in mutation count; a family that fails `single_L1_synonym_label` but survives
`single_L2_paraphrase` (or vice-versa) reveals a lexical-vs-semantic weakness.

---

## 7. Loader quickstart

The read-only consumer API (`src/synthetic/loaders.py`) turns the two release
files into the frames a retrieval harness indexes:

```python
from synthetic.loaders import (
    load_items, load_modifications, join, long_view, short_view,
)

items = load_items()                 # ITEM_COLUMNS frame (default path under SYNTHETIC_PROCESSED_DIR)
mods  = load_modifications()         # {item_key: [Modification, ...]}, baseline -> []
joined = join(items, mods)           # 1:1 on item_key, fail-loud; adds a `modifications` list[dict] column

targets = long_view(items)           # text == texto  + text_norm  (retrieval targets)
queries = short_view(items)          # text == resumen + text_norm  (retrieval queries)
```

`long_view` / `short_view` project to the OEB-style target/query layout: the
key + slice-metadata columns (`item_key, original_key, concept_key, params,
variante_id, modification_types, modification_count`), the retrieval text in a
single `text` column, and a derived `text_norm` produced by
`utils.text_processing.normalize_text` — the **same** normalizer the parent OEB
`OEB_long_norm` / `OEB_short_norm` `text_norm` columns use, so the synthetic
lexical column is byte-for-byte consistent with the parent. No OEB-only
`id`/`ud`/`concept` columns are fabricated. `join` returns a sorted copy and
raises `LoaderError` on any non-1:1 `item_key` match.

---

## 8. Statistics

> **All corpus-scale statistics are `TBD (pending F3 full generation)`.** No F3
> run exists, so there is no corpus to count. These will be filled by a post-F3
> statistics refresh; nothing below is a real or borrowed number.

| Statistic                                       | Value                          |
|-------------------------------------------------|--------------------------------|
| Total synthetic items                           | `TBD (pending F3)`             |
| Concept groups covered                          | `TBD (pending F3)`             |
| Items per concept group (distribution)          | `TBD (pending F3)`             |
| Items per `modification_type` (12 types)        | `TBD (pending F3)`             |
| Items per `modification_count` (1, 2, 3, 4, ≥5) | `TBD (pending F3)`             |
| Items per generation condition (§6)             | `TBD (pending F3)`             |
| Reviewer acceptance rate per type               | `TBD (pending F3)`             |
| `new_param` semantic-collision rate             | `TBD (pending F3)`             |
| Generation throughput                           | `TBD (pending F3)`             |

---

## 9. AI disclosure / provenance

The synthetic modifications are **LLM-proposed**: an offline LLM proposes each
rule variant under a strict-JSON contract at temperature 0.0, with one retry then
a `fallback: skipped` log entry (Phase C). Proposals are **rule-applied** by
deterministic mutators on the parsed between-stage JSON (Phase B), and
**reviewer-validated** by a domain reviewer (Phase E `review.py`; F4 quality
pass) — 100 % review for `new_param`, stratified sampling for the other eleven
types. This mirrors the parent BC3CAT `### AI Disclosure`: AI-assisted outputs
are reviewed and verified by the authors, who take responsibility for the
content.

## 10. Known limitations / ethical considerations

- **Corpus not yet generated.** This card documents the frozen format; the
  corpus and its statistics await F3 (blocked on A3).
- **Synthetic surface forms.** Modifications are model-proposed; despite the
  reviewer gate, residual non-equivalence or ungrammaticality in non-sampled
  variants cannot be fully excluded — the stratified-review error rate is itself
  a measured quantity (`TBD pending F4`).
- **Single language / single domain.** Spanish-language railway-construction
  catalog; cross-language and cross-domain generalization is future work.
- **Derived data.** Source data is ADIF's public price catalog (Base de Precios
  ADIF); BC3CAT-Syn inherits its provenance and the parent's attribution terms.

---

## 11. Citation and license

Cite the parent BC3CAT work (a BC3CAT-Syn-specific citation will be added on
publication):

```bibtex
@article{gonzalez2025systematic,
  title={A Systematic Comparative Study of Retrieval Methods for Parametric Construction Catalogs: From Lexical to Neural Approaches},
  author={González-Alvarez, Cesáreo and Fernández-Robles, Laura and Alegre, Enrique and Castejón-Limas, Manuel},
  journal={Automation in Construction},
  year={2025},
  note={Under review}
}
```

**License.** Dataset: [CC-BY 4.0](https://creativecommons.org/licenses/by/4.0/)
(mirroring the parent BC3CAT dataset). Code: MIT. Source data derived from ADIF's
public price catalog.

---

## See also

- [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md) — §2.2 taxonomy, §2.3 per-item record, §3 pipeline.
- [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md) — §5 Phase G, §6 generation conditions, §7 file map.
- [`HANDOFF.md`](HANDOFF.md) — cross-repo memo for `bc3cat-retrieval`.
- [`../../src/synthetic/packaging.py`](../../src/synthetic/packaging.py) — `ITEM_COLUMNS`, the two filenames, the release writer/reader.
- [`../../src/synthetic/loaders.py`](../../src/synthetic/loaders.py) — the loader API documented in §7.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) — `ModificationType` × `Layer` (§5), `Modification.to_dict` (§4).
