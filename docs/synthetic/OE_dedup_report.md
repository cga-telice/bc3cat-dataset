# OE cross-concept twin de-duplication

Policy: keep one canonical concept (lexicographically-first) per identical
`(resumen, texto)`; **drop** the twin's leaves and the synthetic items derived
from them (dropping, not relabelling, so the survivor is not over-represented).

- twin concepts collapsed: OED170$→OED020$
- **target corpus**: 73302 → **71034** leaves (2268 dropped)
  - written: `data/synthetic/processed_OE/OE_target_long.parquet`, `data/synthetic/processed_OE/OE_target_short.parquet`
- **synthetic corpus**: 5038 → **4912** items (126 dropped)
  - written: `data/synthetic/processed_OE/BC3CAT_Syn_items.parquet`, `data/synthetic/processed_OE/BC3CAT_Syn_modifications.jsonl`

Verification: every surviving target `(resumen, texto)` maps to exactly one concept.
