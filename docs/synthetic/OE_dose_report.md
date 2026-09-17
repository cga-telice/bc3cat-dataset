# E3 — informe del corpus de dosis (escalera anidada)

Consulta = TEXTO modificado; objetivo = TEXTO original de la misma hoja.
`modification_count` cuenta modificaciones APLICADAS y es exacto por
construcción (D2): el sondeo verificó la disponibilidad antes de sortear.

- profundidad elegida **d = 9**
- fondo común: **600 hojas**, las mismas en las cinco celdas (750 seleccionadas, 150 de reserva sin usar)
- histograma de profundidad admitida: `{'2': 1, '3': 13, '4': 8, '5': 173, '6': 22, '7': 361, '9': 922}`
- histograma de modificaciones que caben en tramos distintos: `{2: 14, 3: 70, 4: 186, 5: 422, 6: 808}` — 270 hojas sondeadas admiten menos de 5 y no entran al fondo
- ítems: **3000**, hojas distintas: **600**

## Celdas por dosis

El plan construye exactamente `per_count` escaleras completas o levanta
(`pool_too_small`/`DoseLadderError`); una celda por debajo de **600**
aquí solo puede venir del emisor filtrando ítems ya planificados —
duplicado exacto de `(resumen, texto)` en el corpus.

| dosis | ítems | estado |
|---|---|---|
| dose_1 | 600 | ok |
| dose_2 | 600 | ok |
| dose_3 | 600 | ok |
| dose_4 | 600 | ok |
| dose_5 | 600 | ok |

## Presencia por tipo dentro de cada celda

Lo alcanzable de su §3: dentro de una celda ningún tipo debe estar
sistemáticamente sobre-representado. La tasa de un tipo CRECE con la
dosis por construcción (k tipos de un repertorio de d), y eso es una
propiedad de la dosis, no un sesgo.

Las columnas son los nueve tipos admitidos (fijos); un 0 significa que
el tipo nunca disparó en esa celda, no que quedó sin tabular.

| dosis | paraphrase | expansion | template_paraphrase | synonym_label | compression | reorder | num_to_text | unit_expansion | unit_conversion |
|---|---|---|---|---|---|---|---|---|---|
| dose_1 | 70 | 70 | 70 | 71 | 70 | 70 | 70 | 70 | 39 |
| dose_2 | 140 | 140 | 140 | 141 | 140 | 139 | 141 | 140 | 79 |
| dose_3 | 210 | 211 | 211 | 211 | 210 | 209 | 212 | 209 | 117 |
| dose_4 | 284 | 284 | 279 | 284 | 283 | 280 | 285 | 274 | 147 |
| dose_5 | 369 | 370 | 300 | 388 | 369 | 300 | 387 | 357 | 160 |

## Cobertura por concepto

La escalera cubre **7 conceptos**. Una partición
dev/test por concepto solo puede repartir estos.

| concepto | hojas con escalera |
|---|---|
| OEB040$ | 96 |
| OEB230$ | 93 |
| OEB300$ | 89 |
| OEB280$ | 87 |
| OEB030$ | 87 |
| OEB290$ | 87 |
| OEB020$ | 61 |
