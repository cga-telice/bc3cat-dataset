# OE synthetic corpus — leaf-proportionality (Option A)

Allocation: each concept gets an item budget proportional to its share of leaves in
the deduplicated target pool (70242 leaves), clamped to
`[floor=5, cap_per_leaf*leaves]`; the budget is split across conditions by `type_mix`,
and any single-type shortfall is absorbed by the concept's own `all_combined`
(no cross-concept leakage). Generated from the deduped pool, so the corpus is
duplicate-clean by construction.

- synthetic items: **4527** (all unique resumen/texto; sidecar 1:1)
- **Pearson corr(leaves, syn) across 83 concepts: 0.998**
- concepts with 0 synthetic items: **0** (full coverage)
- per-leaf density (syn per 1k leaves): min 41.7, median 56.6, max 1333 (a ~4-leaf concept at the coverage floor)

## Per subchapter

| sub | leaves | syn | leaf % | syn % | syn per 1k |
|---|---|---|---|---|---|
| OEA | 2926.0 | 172.0 | 4.2 | 3.8 | 58.8 |
| OEB | 47511.0 | 3233.0 | 67.6 | 71.4 | 68.0 |
| OEC | 4409.0 | 238.0 | 6.3 | 5.3 | 54.0 |
| OED | 14328.0 | 804.0 | 20.4 | 17.8 | 56.1 |
| OEE | 216.0 | 15.0 | 0.3 | 0.3 | 69.4 |
| OEF | 36.0 | 3.0 | 0.1 | 0.1 | 83.3 |
| OEG | 816.0 | 62.0 | 1.2 | 1.4 | 76.0 |

Vs. the previous flat-budget corpus: OED rose from 14.8%% to 17.8%% of the
corpus (leaf share 20.4%%), and the per-leaf density spread tightened (median 74.5 -> 56.6),
because single-type shortfalls now stay within each concept instead of leaking to OEB.
