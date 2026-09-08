# BC3CAT-Syn — OE synthetic benchmark (handoff for bc3cat-retrieval)

Query = a MODIFIED `text` (TEXTO); target = the ORIGINAL TEXTO of the same concept.
All files are JSON lists of records with the project's schema:
`{id, item_key, parent_key, ud, concept, parameters, text}` (query files add
`gold_item_key`, `modification_types`, `modification_count`).

## Files
- `OE_texto.json` — document corpus: original OE TEXTOs (retrieval **targets**). 70242 docs.
- `OE_resumen.json` — same leaves, original RESUMEN (for the resumen→texto **baseline**). 70242 docs.
- `OE_stacked_texto.json` — **STACKED** queries: every applicable modification stacked. 4998 queries.
- `OE_single_texto.json` — **SINGLE** queries: one modification each (stratify by `modification_types[0]`). 4439 queries.
- `OE_concept_schema.json` — per concept: name, axes, item_keys, num_items. 83 concepts.

## Gold / scoring
The harness reports parent-level Acc@1: a query is correct if the retrieved item's
`parent_key` == the query's `parent_key`. For item-level, use `gold_item_key`.
Every synthetic query modifies the TEXTO, so no query equals its target verbatim.

## Notes
- Corpus deduplicated: every target `(resumen, texto)` maps to one concept
  (cross-concept twins dropped, intra-concept duplicates collapsed).
- Deterministic; LLM used only to author the rewrite menus (frozen), corpora built
  by recombination. `id` = uuid5 of `item_key` (stable).
