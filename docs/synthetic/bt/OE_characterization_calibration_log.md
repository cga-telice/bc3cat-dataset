# Calibración del verificador de caracterización (OE): registro de iteraciones

CP2 del handoff de BT (opción A). Muestra fija: semilla 42, 8 hojas por concepto. 2 254 casos: 648 positivos, 648 de discriminación (637 a 1 token), 637 de ablación y 321 de deriva. Extractores phi4:latest y qwen2.5:14b, temperatura 0, JSON estricto (`response_format`). Los umbrales no se han tocado.

## Resultados

Par = los dos extractores aciertan (regla de G2).

| Iteración | Prompt | Positivos (≥ 99,5 %) | Discriminación (≥ 99 %) | Ablación (≥ 99 %) | Derivas (100 %) | Estabilidad |
|---|---|---:|---:|---:|---:|---:|
| 1 | opciones numeradas | 98,88 % | 97,69 % | 14,91 % | 90,97 % | 100 % |
| 2 | letras, `null`, regla de genéricas | 98,01 % | 97,38 % | 38,46 % | 91,59 % | 100 % |
| 3 (solo phi4) | opción + cita literal comprobada | 99,24 % | 98,77 % | 93,88 % | — | — |

Por extractor:

| Iteración | Extractor | Positivos | Ablación |
|---|---|---:|---:|
| 1 | phi4 | 99,80 % | 26,37 % |
| 1 | qwen | 99,08 % | 17,58 % |
| 2 | phi4 | 99,72 % | 86,66 % |
| 2 | qwen | 98,25 % | 43,01 % |
| 3 | phi4 | 99,24 % | 93,88 % |
| 3 | qwen | sin terminar (≈ 200/2 092; 5,9 s por llamada) | — |

Informes completos de cada iteración: `OE_characterization_calibration_iter1.md`, `_iter2.md`. Respuestas: `data/synthetic/bt_OE/OE_characterization_calibration_iter*.json`.

## Qué cambió en cada iteración

1. **Iteración 1.** Prompt del handoff, opciones numeradas. Fallos:
   - En la ablación, los dos modelos eligen la opción genérica cuando el campo queda vacío («Trabajo:.» → «Cualquier franja horaria»). Es el «elegir por descarte».
   - qwen confunde el número de opción con el valor: elige 4 para «d4», que es la opción 3, o 1 para «Nº tubos: 2».
   - qwen omite claves en 59 respuestas.
2. **Iteración 2.** Opciones con letras, una por línea. `null` si el parámetro falta o está vacío. Las opciones genéricas solo si el texto lo dice. Además:
   - Salvaguarda de la ablación: solo vale si el texto ablacionado es idéntico para todas las hermanas que difieren en ese eje. No descartó ningún caso: la prueba estaba bien.
   - **G4 reinterpretado:** en los ejes fuera de R(C) se admite `null` o un valor del grupo D-031 del gold, ver la decisión 2.

   phi4 mejora mucho. qwen sigue eligiendo la opción genérica (185 de 637 en la ablación).
3. **Iteración 3.** Cada opción lleva una cita literal de la descripción. Código determinista la comprueba: tiene que estar en el texto y aportar alguna palabra que no sea la etiqueta del parámetro. Sin cita válida, cuenta como `null`. Una clave omitida o un `"null"` escrito como texto cuentan como `null`. Resultado de phi4 en la ablación: 93,9 %. Fallos que quedan:
   - 25 cita el texto de otro eje: la comprobación no exige que la cita pertenezca al eje;
   - 11 inventan un valor en un campo vacío;
   - 17 positivos pasan a `null`.

## Decisiones pendientes (CP2)

1. **Derivas «con topo» → «con topografía»** (29 aceptadas de 321 derivas conocidas, todas en canalizaciones OEB). El valor «Con topo» sigue siendo determinable porque el TEXTO describe el pozo de ataque y el tubo guía. Así que la consulta cumple (a) y (b), pero mete una especificación falsa, que es el criterio (c). Un extractor de conjunto cerrado no puede verlo.
2. **G4 en ejes fuera de R(C).** En OEG010, el eje F («diurno, con corte de corriente») no está en la plantilla TEXTO, pero se deduce de lo que dice el eje C. Exigir `null` rechazaría información que sí está en el texto. Propuesta aplicada desde la iteración 2: un valor del grupo D-031 del gold no es información nueva.
3. **Cómo seguir con la calibración.** Ver las opciones en el mensaje de CP2.
