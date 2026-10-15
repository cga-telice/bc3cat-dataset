# BC3CAT-Syn — OE synthetic benchmark (handoff for bc3cat-retrieval)

Query = a MODIFIED `text` (TEXTO); target = the ORIGINAL TEXTO of the same concept.
All files are JSON lists of records with the project's schema:
`{id, item_key, parent_key, ud, concept, parameters, text}` (query files add
`gold_item_key`, `modification_types`, `modification_count`).

**Dose seen by the query.** `modification_count`/`modification_types` count every
applied modification record. The query is the TEXTO, and in STACKED some records
never reach it: the RESUMEN-field template rewrite (one per item) and rewrites of
text variables or axes the TEXTO template does not render. STACKED records therefore
also carry `texto_modification_count`/`texto_modification_types`, the modifications
visible in the TEXTO; use those for any analysis by dose or type. The texts are
unchanged. SINGLE, dose and isolated sets are exact by construction
(`modification_count` = visible in the TEXTO).

**Leaves that share a TEXTO (D-031: flagged, not collapsed).** In `OE_texto.json` /
`OE_resumen.json` every record carries `duplicate_texto_group`: the smallest
`item_key` of the leaves whose TEXTO is identical (`null` outside any group). Groups
never cross concepts, so parent-level scoring has no ceiling from them; item-level
identity caps below 1.0. `OE_duplicate_texto_groups.json` is the same grouping as a
small file, so the flag can be taken without re-taking the corpus.

## Files
- `OE_texto.json` — document corpus: original OE TEXTOs (retrieval **targets**). 70242 docs.
- `OE_resumen.json` — same leaves, original RESUMEN (for the resumen→texto **baseline**). 70242 docs.
- `OE_stacked_texto.json` — **STACKED** queries: every applicable modification stacked. 4998 queries.
- `OE_single_texto.json` — **SINGLE** queries: one modification each (stratify by `modification_types[0]`). 4439 queries.
- `OE_concept_schema.json` — per concept: name, axes, item_keys, num_items. 83 concepts.
- `OE_duplicate_texto_groups.json` — leaves sharing a TEXTO: group id → members. 292 groups, 776 leaves.

## Gold / scoring
The harness reports parent-level Acc@1: a query is correct if the retrieved item's
`parent_key` == the query's `parent_key`. For item-level, use `gold_item_key`.
Every synthetic query modifies the TEXTO, so no query equals its target verbatim.

## Notes
- Corpus deduplicated: every target `(resumen, texto)` maps to one concept
  (cross-concept twins dropped, intra-concept duplicates collapsed).
- Deterministic; LLM used only to author the rewrite menus (frozen), corpora built
  by recombination. `id` = uuid5 of `item_key` (stable).

## Back-translation (BT) queries — added 2026-10-16

- `OE_bt_texto.json` — **BT** queries: the gold TEXTO of each STACKED-P leaf, round-trip
  translated sentence by sentence (ES→EN→ES and ES→EN→{FR, IT, DE}→ES, OPUS-MT). 4 670 queries,
  79 concepts. Gold = `gold_item_key` (the source leaf itself), as in the other sets.
- `OE_bt_modifications.jsonl` — sidecar, one row per query: translated sentences, value
  substitutions and glossary synonyms.
- `OE_bt_provenance.json` — models and revisions, audits, input and output digests.
- `OE_stacked_P_exclusion.json` + `OE_known_drift_rewrites.json` — 324 STACKED queries outside
  STACKED-P (321 with a known drift rewrite such as «con topo» → «topografía» or «adosada» →
  «empotrada / a ras», 2 duplicates of other sets, 1 degenerate). Consider excluding them when
  scoring STACKED.

How a BT query is built:
- **Prose.** Each sentence uses the first translation that passed a sentence-level audit, or
  stays in its original form. `bt_sentences.fraction` = translated / total sentences (mean 0.48;
  label-only sentences such as «Trabajo: X.» come back unchanged from MT, so about two thirds of
  the translatable prose is translated). Trade terms (arqueta, canaleta, desmonte, hastial…) are
  restored after translation.
- **Values.** Axis values and text-variable fragments are masked during translation and then
  replaced by an audited variant when one exists («Volumen relevante» → «volumen importante»);
  sometimes with the parameter label in front.
- **Glossary synonyms.** 50 % of trade-term occurrences are replaced by an audited alternative
  («zanja» → «rasa», «poste» → «apoyo»).

`modification_types` lists `back_translation`, plus `value_back_translation` and
`glossary_synonym` when present; use `texto_modification_types_post_bt` for analyses by type.
Every query passed a structural check (no new quantities, codes or acronyms; not equal to any
other leaf or to a delivered query). Item keys end in `_btorigv_en`.

## v2 of STACKED, SINGLE, dose and isolated — added 2026-10-16

- `OE_stacked_texto_v2.json`, `OE_single_texto_v2.json`, `OE_dose_texto_v2.json`,
  `OE_isolated_texto_v2.json` — same queries, ids and gold as the v1 files, with 163 broken
  template paraphrases repaired. **Use v2 instead of v1.**
- `OE_v2_changes.jsonl` — one row per changed query: set, `item_key`, paraphrase id, old and new
  text. Changed queries: STACKED 2 039, SINGLE 241, dose 547, isolated 348.
- `OE_v2_provenance.json` — audit, repair method, verification and digests.

What was repaired: an audit of the 828 TEXTO template paraphrases used in these sets found
paraphrases that put a value in the wrong role («de 200 mm y diámetro **en cruce bajo vías**»,
dimensions read as a location, an operation read as a quantity) or present a value as a reference
document («las condiciones se detallan en **Nocturno**»). Those 163 paraphrases were minimally
corrected and every affected query re-rendered with the same values; all other queries are
byte-identical to v1. Duplicated units («40 mm mm»), awkward grammar and looser wording were left
on purpose (they occur in real documents). Whitespace is normalized in the changed queries.
`OE_stacked_P_exclusion.json` applies unchanged to v2 (same `item_key`).
