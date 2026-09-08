# OE ablation corpora (Design A - shared base leaves)

Two corpora built purely by recombining the approved pantry rewrites (no LLM), over
one shared sample of 5000 base leaves. Every item is paired on the same base leaf so
retrieval-degradation differences are attributable to the modifications, not to leaf
selection. modification_count counts APPLIED modifications only (skipped/no-op
rewrites excluded).

## STACKED - all applicable modifications per item
- items: **4998** (one per shared leaf; all unique)
- applied modifications per item: mean 4.67, min 2, max 8
- modification_count distribution: 2:21, 3:1199, 4:874, 5:1535, 6:1087, 7:237, 8:45
- output: `data/synthetic/processed_OE_ablation_stacked/`

## SINGLE - one modification per item (capacity-balanced, cap 600/type)
- items: **4650** (each exactly one applied modification; all unique)

| modification | items |
|---|---|
| reorder | 600 |
| num_to_text | 600 |
| template_paraphrase | 599 |
| synonym_label | 598 |
| unit_conversion | 549 |
| compression | 548 |
| unit_expansion | 542 |
| paraphrase | 311 |
| expansion | 303 |

- output: `data/synthetic/processed_OE_ablation_single/`

Both from the deduped target pool; Guard #1 = 0/0; ~100%% pairing.
