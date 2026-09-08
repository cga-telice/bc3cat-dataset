# OE synthetic corpus - leaf-proportionality (Option A)

Each concept's item budget is proportional to its leaf share of the deduplicated
target pool (70242 leaves), clamped `[floor=5, cap_per_leaf*leaves]`, split by
`type_mix`; single-type shortfalls absorbed by the concept's own all_combined.
modification_count reflects APPLIED modifications only (skipped/no-op rewrites are
not counted).

- synthetic items: **4537** (all unique resumen/texto; sidecar 1:1)
- **Pearson corr(leaves, syn) across 83 concepts: 0.998**
- concepts with 0 synthetic items: **0**

## Per subchapter
| sub | leaves | syn | leaf % | syn % | syn per 1k |
|---|---|---|---|---|---|
| OEA | 2926.0 | 172.0 | 4.2 | 3.8 | 58.8 |
| OEB | 47511.0 | 3236.0 | 67.6 | 71.3 | 68.1 |
| OEC | 4409.0 | 240.0 | 6.3 | 5.3 | 54.4 |
| OED | 14328.0 | 809.0 | 20.4 | 17.8 | 56.5 |
| OEE | 216.0 | 15.0 | 0.3 | 0.3 | 69.4 |
| OEF | 36.0 | 3.0 | 0.1 | 0.1 | 83.3 |
| OEG | 816.0 | 62.0 | 1.2 | 1.4 | 76.0 |
