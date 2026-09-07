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


## Intra-concept collapse (second dedup pass)

A single concept rendering the same description under several leaves (a parameter
axis absent from its templates) is redundant, though not label-ambiguous. Keep one
leaf per description; REMAP the derived synthetic queries to it (not drop).

- concept(s) collapsed: OEG010$
- **target corpus**: 71034 → **70242** leaves (792 redundant leaves removed)
- **synthetic corpus**: 4912 items unchanged; **42** had `original_key` remapped to the surviving sibling leaf

Verification: every target `(resumen, texto)` is now unique.
