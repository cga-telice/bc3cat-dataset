# BC3CAT-Syn: A Rule-Modification Synthetic Benchmark for Robustness Evaluation of Retrieval Methods on Parametric Construction Catalogs

**Research Proposal — Companion Benchmark to BC3CAT**

| Field        | Value                                                       |
|--------------|-------------------------------------------------------------|
| **Author**   | César                                                       |
| **Date**     | May 2026                                                    |
| **Target**   | SEPLN Congress / Data-in-Brief companion submission         |
| **Status**   | Initial draft — branch `synthetic`                          |
| **Deadline** | TBD                                                         |

---

## 1. Context and Motivation

### 1.1 The Evaluation Gap in Parametric Catalog Retrieval

Recent work on BC3CAT benchmarked lexical (BM25), dense (BGE-M3, E5, GTE), sparse learned (BGE-M3 sparse), and late-interaction (ColBERT) retrievers on a Spanish-language construction price catalog. The reported numbers exposed a structural failure mode in parametric domains: dense models reach 96–99.7% parent-level accuracy but collapse to 12–45% at the item level, while parameter-aware BM25 reaches 97.4% item-level Acc@1. See the companion proposal [Structure-Aware Retrieval for Parametric Catalogs](../RESEARCH_PROPOSAL.md) for the full numbers and analysis.

The BM25 result, however, must be read with a caveat. The benchmark uses catalog-generated short descriptions (*resumen*) as queries against catalog-generated long descriptions (*texto*). Both surface forms are produced by the same generation rules — they share lexical roots, abbreviations, unit conventions, ordering, and parameter labels. Exact-match methods exploit this overlap directly. In any real deployment — cost estimators mapping project specifications to catalog entries, field engineers reconciling daily reports with line items — queries are drafted independently with company-specific wording, regional terminology, abbreviations, and implicit context. Standard (non-parameter-aware) BM25 already drops to 86.9% Acc@1 on the catalog-generated benchmark; real-world phrasing would erode it further.

This produces an evaluation gap:

> **Current BC3CAT results characterize methods under a best-case lexical-overlap scenario. They do not measure how each retrieval family degrades when surface form varies while parametric meaning is preserved.**

Closing this gap requires controlled linguistic variability — variants of the same item that mean the same thing but are written differently — with **full traceability back to the originating modification**, so that performance drops can be attributed to specific transformations rather than aggregate "noise".

### 1.2 Why a Rule-Modification Approach

Two strategies have been used in the literature to inject linguistic variability into retrieval benchmarks:

| Strategy                                  | Trade-off                                                                 |
|-------------------------------------------|---------------------------------------------------------------------------|
| **Post-hoc text rewriting** (e.g., LLM paraphrase the generated text) | Cheap to produce, but loses traceability: a single rewritten sentence mixes synonym swaps, reordering, and compression in ways that cannot be cleanly attributed. |
| **Rule-modification** (this work)         | Each modification is applied at the *generation rule* level, before the catalog text is rendered. Provenance is preserved by construction. |

The rule-modification strategy is the natural fit for BC3CAT because BC3 catalog items are not free text — they are emitted by an explicit three-layer generation grammar (parameter values → text variables → output templates). Modifying that grammar yields a synthetic catalog with three properties:

1. **Same generation engine.** The existing BC3CAT pipeline is reused without code changes.
2. **Inherited traceability.** Each synthetic item is bound to its `original_key`, its rule variant ID, and the exact list of modifications applied.
3. **Segmentable evaluation.** Per-item metadata (modification type, layer, parameter, original/new values) enables fine-grained slicing of retrieval results by transformation type.

The result is a benchmark that supports questions standard benchmarks cannot answer: *Which methods are most robust to number-to-text conversion? How does compression affect lexical vs. semantic retrievers? Does omitting a parameter mention from the long description hurt dense methods more than late-interaction methods? How does degradation scale with the number of stacked modifications?*

---

## 2. Dataset Design

### 2.1 Anatomy of a BC3 Parametric Concept

A BC3 concept defines three modifiable layers. Each layer is a candidate site for rule-level transformation.

| Layer            | Content                                                                 | Example                                                                 |
|------------------|-------------------------------------------------------------------------|-------------------------------------------------------------------------|
| **L1 — Parameter values** | Discrete value sets and their descriptive labels                   | `\ TIPO DE TERRENO \ Normal \ Bajo vías \ Rocoso \ ...`<br>`%L(11)=1,2,3,4,5,6,8,12,16,18,24` |
| **L2 — Text variables**   | Conditional text fragments selected by parameter combinations      | `$K = "normal" * (%B=a) + "bajo vías" * (%B=b) + ...`                  |
| **L3 — Output templates** | `\RESUMEN\` and `\TEXTO\` strings that interleave literals and `$vars` | `\TEXTO\ Canalización hormigonada de $A tubos de PVC de 110 mm $I, incluso $N...` |

Every catalog item is a deterministic function of these three layers. Modifying any layer in a controlled way produces a new item with the same underlying parameters but a different surface form.

### 2.2 Modification Taxonomy

Twelve modification types are defined, organized by the layer they affect. Each type is a controlled-vocabulary code that is recorded in the item metadata.

| Code (`type`)        | Layer (`layer`)     | Description                                            | Example                                              |
|----------------------|---------------------|--------------------------------------------------------|------------------------------------------------------|
| `synonym_label`      | `param_value`       | Replace a descriptive label with a synonym             | Normal → Estándar                                    |
| `num_to_text`        | `param_value`       | Convert numeric value to written word                  | 2 → dos                                              |
| `unit_conversion`    | `param_value`       | Convert to a different unit                            | 110 mm → 11 cm                                       |
| `unit_expansion`     | `param_value`       | Expand a unit abbreviation                             | mm → milímetros                                      |
| `abbrev_expansion`   | `param_value`       | Expand a technical acronym                             | PVC → policloruro de vinilo                          |
| `code_expansion`     | `param_value`       | Expand a domain code                                   | HE-20 → hormigón estructural tipo 20                 |
| `paraphrase`         | `text_variable`     | Reformulate while preserving meaning                   | "en cualquier clase de terreno" → "en terreno normal"|
| `expansion`          | `text_variable`     | Verbose reformulation                                  | Normal → Terreno de tipo normal                      |
| `compression`        | `text_variable`     | Concise reformulation                                  | "en cualquier clase de terreno" → "terreno normal"   |
| `omission`           | `template`          | Remove a `$var` mention from the template              | Drop `$I` (terrain) from `\TEXTO\`                   |
| `reorder`            | `template`          | Reorder template constituents                          | `$A tubos ... $I` → `$I ... $A tubos`                |
| `new_param`          | `param_definition`  | Add a parameter axis not present in the original       | Add `CALIDAD ACABADO` ∈ {Estándar, Premium, Industrial} |

`new_param` is the only operation that does not preserve the parameter space of the original concept; its purpose is to test whether retrievers can ignore newly-introduced axes that are absent from query intent, and whether they degrade gracefully when the catalog gains new dimensions.

### 2.3 Per-Item Metadata Schema

Each synthetic item carries a metadata block that supports both traceability and segmented evaluation:

```json
{
  "item_key": "OEB020aaeaa_syn_v1",
  "original_key": "OEB020aaeaa",
  "params": {"A": "2", "B": "Normal", "...": "..."},
  "resumen": "Canalización dos T PVC 110, convencional.",
  "texto": "Canalización de dos tubos PVC 110 mm en terreno estándar...",

  "variante_id": "v1",
  "modification_types": ["num_to_text", "synonym_label", "paraphrase", "compression"],
  "modification_count": 4,

  "modifications": [
    {"type": "num_to_text",    "layer": "param_value",    "param": "A",
     "original": "2",          "new": "dos"},
    {"type": "synonym_label",  "layer": "param_value",    "param": "B", "value": "a",
     "original": "Normal",     "new": "Convencional"},
    {"type": "paraphrase",     "layer": "text_variable",  "var": "$I", "condition": "%B=a",
     "original": "en cualquier clase de terreno, excepto roca",
     "new":      "terreno estándar"},
    {"type": "compression",    "layer": "template",       "field": "RESUMEN"}
  ]
}
```

Three fields enable the downstream evaluation slicing:

- `modification_types` — flat list, supports per-type stratified evaluation.
- `modification_count` — supports compositionality analysis (how degradation scales with stacked modifications).
- `modifications` — full detail, supports interaction-level analysis (which combinations are hardest).

The triple `(item_key, original_key, variante_id)` is the unique join key against the original catalog.

---

## 3. Generation Pipeline

The generation pipeline reuses the existing BC3CAT processing stack and adds a rule-mutation step in front of it.

```
Original BC3 catalog
  │
  ▼
[Stage A] Rule-variant generation
  │  (LLM-assisted proposals + manual review)
  │  per concept: N value variants × M text variants × P template variants × Q new-param variants
  ▼
Modified BC3 files + modification-log JSON
  │
  ▼
[Stage B] Existing BC3CAT pipeline (s01–s07, unchanged)
  │
  ▼
Synthetic items (resumen + texto)
  │
  ▼
[Stage C] Metadata injection
  │  (join synthetic items with the modification log)
  ▼
BC3CAT-Syn dataset (items + traceability metadata)
  │
  ▼
[Stage D] Manual validation sample
```

| Stage | Name                          | Method                                                                 | Output                                          |
|:-----:|-------------------------------|------------------------------------------------------------------------|-------------------------------------------------|
| **A** | Rule-variant generation       | LLM proposes variants per layer; human reviews for semantic equivalence | Modified BC3 + modification log                 |
| **B** | Catalog expansion             | Existing pipeline (`s01_parse_fiebdc` → `s07_Filter_duplicates`)         | Raw synthetic items (untraced)                  |
| **C** | Metadata join                 | Merge by `(original_key, variante_id)`                                  | Final synthetic items with full metadata        |
| **D** | Validation sample             | Stratified sample reviewed by domain reviewer                           | Quality report; rejection of broken variants    |

**Stage A — Rule-variant generation.** For each concept group in the original catalog, an LLM is prompted with the layer's current content (e.g., the parameter label set) and the modification type to apply. The output is a candidate modified layer plus an explicit list of changes. A human reviewer either accepts, edits, or rejects each candidate. This is the bottleneck of the pipeline; the metadata is generated alongside the variant so that downstream stages do not need to reverse-engineer what changed.

**Stage B — Catalog expansion.** The existing BC3CAT pipeline operates unchanged on the modified BC3 files. This is the central design decision of BC3CAT-Syn: the synthetic catalog is *not* a different format or a different tool — it is the same engine fed with controlled rule variations. This guarantees that any artifact discoverable in BC3CAT-Syn is also discoverable in BC3CAT and vice versa.

**Stage C — Metadata injection.** Stage B produces items that share the `item_key` derivation rule with the original catalog. The modification log from Stage A is joined back in to produce the final metadata block.

**Stage D — Validation.** A stratified sample (per concept group × per modification type) is reviewed by a domain reviewer. Validation checks: (i) the synthetic text is grammatical Spanish; (ii) the synthetic text preserves the parametric meaning of the original; (iii) `new_param` variants introduce axes that are clearly distinguishable from existing ones (no semantic collisions); (iv) the metadata accurately describes what changed.

---

## 4. Evaluation Plan

### 4.1 Methods Under Evaluation

The benchmark is designed to evaluate the same retrieval families used in the original BC3CAT study, plus future structure-aware methods:

- **Lexical:** BM25 (standard unigram), BM25 with parameter-aware tokenization, TF-IDF.
- **Dense:** BGE-M3, E5, GTE.
- **Sparse learned:** BGE-M3 sparse.
- **Late interaction:** BGE-M3 ColBERT.
- **Structure-aware (this lab):** the three-stage pipeline proposed in [Structure-Aware Retrieval for Parametric Catalogs](../RESEARCH_PROPOSAL.md).

### 4.2 Metrics

Primary: **item-level Acc@1**. Additional: **parent Acc@1, Recall@10, MRR, nDCG@10**, matching the metric set used in the original BC3CAT report. Each metric is reported in three slices:

1. **Aggregate** — over the full synthetic dataset, for headline robustness numbers.
2. **Per modification type** — Acc@1 conditioned on `modification_types` containing each of the 12 codes.
3. **Per modification count** — Acc@1 conditioned on `modification_count ∈ {1, 2, 3, 4, ≥5}`, for compositionality.

A fourth slice (per layer) is computed by aggregating per-type metrics by `layer ∈ {param_value, text_variable, template, param_definition}`, to report whether degradation is driven by lexical-level changes (L1), semantic-level changes (L2), or structural changes (L3).

### 4.3 Reference Conditions

| Condition                             | Description                                                                       | Purpose                                                   |
|---------------------------------------|-----------------------------------------------------------------------------------|-----------------------------------------------------------|
| **Floor — Original BC3CAT**           | Run every method on the unmodified catalog                                        | Anchor: each method's best-case lexical-overlap number    |
| **Per-type single-modification**      | Synthetic items where exactly one modification type was applied                   | Isolate the effect of each transformation                 |
| **Stacked-modifications**             | Items with 2, 3, 4, ≥5 modifications combined                                     | Compositionality / scaling of degradation                 |
| **Full BC3CAT-Syn**                   | All synthetic items                                                               | Headline robustness leaderboard                           |

### 4.4 Analytical Questions

The evaluation is designed to answer:

1. **Per family, which transformation type causes the largest degradation?** Hypothesis: lexical methods will degrade most on `synonym_label`, `paraphrase`, `num_to_text`, `unit_expansion`; dense methods on `omission`, `compression`, `new_param`.
2. **Is the BM25 vs. dense gap robust to phrasing variation?** The original BC3CAT result favors parameter-aware BM25 dramatically. If that gap shrinks (or inverts) under high-variability slices, the original benchmark's lexical-overlap bias is empirically confirmed.
3. **How does degradation scale with composition?** Sublinear (each method has a robust core) vs. linear (degradation accumulates) vs. superlinear (interaction effects compound).
4. **Does parameter-aware tokenization remain effective under unit conversion and number-to-text?** This stress-tests the assumption baked into the original BM25-PA variant.

---

## 5. Expected Contributions

1. **A public synthetic benchmark with full transformation traceability.** BC3CAT-Syn provides per-item metadata identifying the linguistic transformations applied, enabling segmented evaluation in a way that post-hoc paraphrase benchmarks cannot.

2. **A rule-modification methodology generalizable to other parametric catalogs.** The three-layer schema (parameter values, text variables, output templates) and the twelve-type modification taxonomy are not BC3-specific; they describe any template-driven catalog generation system.

3. **Empirical robustness profiles for major retrieval families on a Spanish-language industrial dataset.** Per-type degradation curves for BM25, dense embeddings, sparse learned, and late-interaction methods on a real-world dataset, in Spanish.

4. **Reframing of the BC3CAT BM25 result.** By measuring how parameter-aware BM25 degrades under controlled linguistic variability, we contextualize its near-perfect score on the catalog-generated benchmark and quantify the lexical-overlap bias.

---

## 6. Future Work and Extensions

- **Query-side variability.** This proposal modifies the *catalog* side (documents). A complementary effort would generate synthetic *queries* against the unmodified catalog, mirroring real deployment patterns where the catalog is fixed and user queries are the variable surface. Both sides need to be covered eventually; we start with the catalog side because the BC3 grammar gives us a tractable handle there.

- **Difficulty-controlled negative mining.** Per-item metadata enables principled hard-negative construction: items differing only in a single parameter axis, or items sharing a concept but varying along a specific modification type. Useful both for training (contrastive fine-tuning) and for fine-grained evaluation.

- **Multi-language extension.** The modification taxonomy is language-independent; the rule-variant generation is the only language-dependent step. Extending to other languages (English construction catalogs, multilingual variants) is mechanical given a domain reviewer per language.

- **Cross-domain replication.** Apply the rule-modification framework to non-construction parametric catalogs (industrial parts, e-commerce configurators, insurance products) to verify that the failure-mode profiles found in BC3CAT-Syn replicate.

- **Use as a training signal.** With traceability, BC3CAT-Syn doubles as a fine-tuning corpus: per-modification-type adapters, contrastive triplets, or denoising objectives become directly definable.

---

## 7. Open Questions (Pre-Implementation)

These should be resolved before Sprint 1:

1. **Variant budget per concept.** How many rule variants per concept group? A small N (e.g., 3) yields a manageable benchmark; a large N gives statistical power for per-type slices. Likely answer: scale variant count with original group size, capped to avoid combinatorial blowup on the largest groups (6,336 items).

2. **Stage A LLM choice.** The variant generator runs offline and is human-reviewed, so model latency is not a constraint. Quality of Spanish technical writing is. Candidates: GPT-4-class API for highest fluency, Llama 3.1 70B local for self-contained reproducibility, or a Spanish-tuned model.

3. **Manual review coverage.** Full review (every variant) is unrealistic at scale; stratified sampling is realistic but introduces unknown error rates in non-sampled variants. Proposal: 100% review of `new_param` (highest risk of semantic collision), stratified sampling for the other eleven types with a target inter-annotator agreement.

4. **`new_param` design constraints.** New parameters must be clearly distinguishable from originals to avoid semantic collisions (e.g., adding "QUALITY" when "GRADE" already exists). Should there be a controlled list of admissible new-parameter axes per concept group?

5. **Query side.** The current proposal modifies catalog text only; queries (`resumen`) are also generated by the modified grammar and therefore inherit the same modifications. Should we additionally produce a *query-independent* modification set (modify documents but leave queries from the original catalog) to mirror the real-deployment asymmetry where the catalog is the variable surface and queries are stable?

6. **Public release format.** JSONL with per-item metadata vs. Parquet (matching the existing BC3CAT release format) vs. both. Likely answer: Parquet for the items + a sidecar JSONL of `modifications` to keep the columnar file flat.

---

## 8. Changelog

| Version | Date       | Changes                                                                 |
|---------|------------|-------------------------------------------------------------------------|
| v0.1    | May 2026   | Initial draft on branch `synthetic`. Adapts BC3CAT-Syn proposal into the research-proposal template used by the structure-aware retrieval companion document. |

---

*End of proposal — this document serves as persistent context for the BC3CAT-Syn implementation sprints on branch `synthetic`.*
