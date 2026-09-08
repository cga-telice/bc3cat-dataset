# OE ablation corpora (Design A - shared base leaves)

Two corpora built by recombining the approved pantry rewrites (no LLM at corpus time),
over one shared sample of 5000 base leaves; every item paired on the same base leaf.
template_paraphrase menus were regenerated at depth (>=10 valid candidates/target, both
RESUMEN and TEXTO for all concepts). modification_count counts APPLIED modifications only.

## STACKED - all applicable modifications per item
- items: **4998** (one per shared leaf; all unique)
- applied modifications per item: mean 4.69, min 2, max 8
- distribution: 2:1, 3:1216, 4:877, 5:1484, 6:1138, 7:237, 8:45

## SINGLE - one modification per item (capacity-balanced, cap 600/type)
- items: **4650**

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

Both from the deduped target pool; Guard #1 = 0/0.
