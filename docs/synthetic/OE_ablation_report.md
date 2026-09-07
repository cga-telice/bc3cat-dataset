# OE ablation corpora (Design A - shared base leaves)

Two corpora built purely by recombining the approved pantry rewrites (no LLM),
over one shared sample of 5000 base leaves (`OE_ablation_inventory_*.parquet`,
leaf-proportional across all 83 concepts). Every item is a query whose gold target
is the original catalog leaf it derives from; both are generated from the
deduplicated target pool, so they are duplicate-clean and cross-concept-collision
free (Guard #1 = 0/0).

Purpose: measure each modification's retrieval-degradation impact (SINGLE, one
modification per item) against the maximal combined degradation (STACKED, all
applicable modifications per item), on the SAME base leaves - so differences are
attributable to the modifications, not to leaf selection.

## STACKED - all applicable modifications per item
- items: **4998** (one per shared leaf; all unique resumen/texto)
- modifications per item: mean 5.55, min 3, max 8
- modification_count distribution: 3:22, 4:319, 5:2044, 6:2161, 7:387, 8:65
- output: `data/synthetic/processed_OE_ablation_stacked/`

## SINGLE - one modification per item (capacity-balanced, cap 600/type)
- items: **4637** (all carry exactly one modification; all unique)
- per-type counts (weak L2 types are list-form-capacity-limited):

| modification | items |
|---|---|
| num_to_text | 600 |
| template_paraphrase | 599 |
| synonym_label | 597 |
| reorder | 593 |
| unit_conversion | 549 |
| compression | 548 |
| unit_expansion | 542 |
| paraphrase | 306 |
| expansion | 303 |

- output: `data/synthetic/processed_OE_ablation_single/`

## Pairing (Design A)
Both corpora draw from the same 5000-leaf inventory; ~100%% of single-corpus leaves
have a stacked counterpart, enabling per-leaf comparison of single-vs-combined
degradation (separability assessment).

Reproduce: `scripts/build_ablation_inventory.py`, then two `corpus_driver run`
invocations with the `variant_budgets_OE_ablation_stacked.yaml` and
`variant_budgets_OE_ablation_single.yaml` configs over the shared inventory.
