# OE ablation corpora (Design A - shared base leaves)

Query = MODIFIED TEXTO; target = ORIGINAL TEXTO. Both corpora contain only items
whose TEXTO is modified (100%). Built by recombining the approved pantry rewrites
(no LLM at corpus time), over one shared 5000-leaf sample; every item paired on the
same base leaf. modification_count counts APPLIED modifications only.

## STACKED - all applicable modifications per item
- items: **4998** (one per shared leaf; 100% TEXTO changed; all unique)
- applied modifications per item: mean 4.69, min 2, max 8
- distribution: 2:1, 3:1216, 4:877, 5:1484, 6:1138, 7:237, 8:45

## SINGLE - one modification per item (each changes the TEXTO)
- items: **4439** (100% TEXTO changed; all unique). template_paraphrase and
  reorder are restricted to their TEXTO-field rewrites; L2 (paraphrase/expansion)
  are lower because many fragments surface only in the resumen.

| modification | items |
|---|---|
| template_paraphrase | 600 |
| num_to_text | 600 |
| reorder | 595 |
| synonym_label | 588 |
| unit_conversion | 549 |
| compression | 548 |
| unit_expansion | 542 |
| paraphrase | 211 |
| expansion | 206 |

Both from the deduped target pool; Guard #1 = 0/0.
