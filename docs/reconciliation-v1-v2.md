# Reconciliation report: v1 (notebooks) vs v2 (bc3param)

Shared source: `data/raw/BPA_2024_v2_OEB_mod_utf8.txt`. Chapter: OEB#.

- v2 total combinations: 47508 | valid: 40407 | invalid via %E (absent in normal use): 7101

## RESUMEN

- v1 keys: 47508 | v2 keys: 47508 | common: 47508
- only in v1: 0 | only in v2: 0
- exact match: 636
- match up to whitespace (cosmetic): 11322
- differ only by v1's literal corruption (v2 fixes it): 35550
- other substantive differences: 0

Examples where v2 corrects v1's corruption:

- `OEB300jbeac`
  - v1: Canalización hormigonada 18 T, polietileno libre de halógenos de 90 mm, bajo vías. (Cualquier franja horaria/i >== 5 horas/Cualquier condición de ejecución)
  - v2: Canalización hormigonada 18 T, polietileno libre de halógenos de 90 mm, bajo vías. (Cualquier franja horaria/i >= 5 horas/Cualquier condición de ejecución)
- `OEB230bacba`
  - v1: Canalización hormigonada 2 T, polietileno libre de halógenos de 200 mm, normal. (Diurno excepcional/3 <== i < "5" horas/Volumen relevante)
  - v2: Canalización hormigonada 2 T, polietileno libre de halógenos de 200 mm, normal. (Diurno excepcional/3 <= i < 5 horas/Volumen relevante)
- `OEB280jedcc`
  - v1: Canalización hormigonada 18 T, polietileno libre de halógenos de 40 mm, en andén. (Nocturno excepcional/i < "3" horas/Cualquier condición de ejecución)
  - v2: Canalización hormigonada 18 T, polietileno libre de halógenos de 40 mm, en andén. (Nocturno excepcional/i < 3 horas/Cualquier condición de ejecución)
- `OEB030jafcc`
  - v1: Canalización hormigonada 18 T, polietileno libre de halógenos de 110 mm, normal. (Cualquier franja horaria excepcional/i < "3" horas/Cualquier condición de ejecución)
  - v2: Canalización hormigonada 18 T, polietileno libre de halógenos de 110 mm, normal. (Cualquier franja horaria excepcional/i < 3 horas/Cualquier condición de ejecución)

## TEXTO

- v1 keys: 47508 | v2 keys: 47508 | common: 47508
- only in v1: 0 | only in v2: 0
- exact match: 0
- match up to whitespace (cosmetic): 47508
- differ only by v1's literal corruption (v2 fixes it): 0
- other substantive differences: 0

## Conclusion

- The set of keys (derived items) is identical between v1 and v2.
- TEXTO: matches 100% up to whitespace (v2 collapses repeated spaces).
- RESUMEN: there is no unexplained difference. Every non-whitespace difference is v2 correcting v1's literal corruption (`>==`, `<==`, spurious quotes such as `"3"`), caused by rewriting formulas with regular expressions over quoted text.
- v2 additionally provides per-item price and decomposition, which v1 did not compute, and marks 7101 combinations invalid via the `%E` statement (they do not exist in normal catalogue use). These have no counterpart in v1, which included them.

v2 source for this comparison: the same `_mod` file v1 used, so that the differences reflect the engine and not the choice of source file.

