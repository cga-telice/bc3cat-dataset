# STACKED — auditoría de visibilidad en el TEXTO

Consulta = TEXTO modificado. Una modificación cuenta como visible solo si
toca algo que la plantilla del TEXTO renderiza (campo TEXTO; marcador del
eje; variable del TEXTO cuya condición se cumple en la hoja).

- ítems: **4998**
- ítems cuyo `modification_count` sobrecuenta: **4998** (100.0%)
- ítems sin ningún cambio visible en el TEXTO: **0**
- `modification_count` medio: registrado **4.69**, visible **3.31**
- desacuerdos entre el juicio estructural y la comprobación por subcadena: **10**

## Sobreconteo por ítem

| registrado − visible | ítems |
|---|---|
| 1 | 3280 |
| 2 | 1573 |
| 3 | 142 |
| 4 | 3 |

## Modificaciones no visibles, por tipo y capa

| tipo | capa / campo | modificaciones |
|---|---|---|
| template_paraphrase | RESUMEN | 4998 |
| paraphrase | text_variable | 918 |
| expansion | text_variable | 794 |
| synonym_label | param_value | 59 |
| unit_expansion | param_value | 51 |
| compression | text_variable | 44 |

## Transiciones de conteo (registrado → visible)

| registrado | visible | ítems |
|---|---|---|
| 2 | 1 | 1 |
| 3 | 1 | 4 |
| 3 | 2 | 1212 |
| 4 | 2 | 38 |
| 4 | 3 | 839 |
| 5 | 2 | 1 |
| 5 | 3 | 509 |
| 5 | 4 | 974 |
| 6 | 2 | 1 |
| 6 | 3 | 117 |
| 6 | 4 | 806 |
| 6 | 5 | 214 |
| 7 | 4 | 17 |
| 7 | 5 | 180 |
| 7 | 6 | 40 |
| 8 | 4 | 2 |
| 8 | 5 | 7 |
| 8 | 6 | 36 |

## Desacuerdos (tipo, estructural, subcadena)

| tipo | estructural | subcadena | registros |
|---|---|---|---|
| compression | False | True | 6 |
| paraphrase | False | True | 4 |
