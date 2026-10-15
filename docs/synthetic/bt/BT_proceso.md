# Back-translation (BT) sobre BC3CAT-Syn OE: proceso, intentos, problemas y soluciones

Documento de referencia para el artículo. Cubre el trabajo del 2026-10-04 al 2026-10-16 en la
rama `syn/back-translation` (fusionada en `synthetic`) y la corrección posterior de las
paráfrasis de plantilla de los conjuntos previos (rama `syn/broken-paraphrases`). Las cifras
salen de los informes de `docs/synthetic/bt/` y de los ficheros de `data/synthetic/handoff_OE/`.
Para comparar las dos formas de generar consultas sobre las mismas hojas, ver
[`OE_bt_vs_stacked_sample.md`](OE_bt_vs_stacked_sample.md).

---

## 1. Objetivo

Los conjuntos sintéticos anteriores (STACKED, SINGLE, dose, isolated) se generan recombinando
reescrituras de un menú cerrado escrito con LLM y revisado: paráfrasis de la plantilla,
sinónimos de etiquetas, números en letra, conversiones de unidad… Todas comparten el mismo
vocabulario de reescrituras. La BT añade una fuente de variación **independiente**: la
traducción automática de ida y vuelta (español → idioma pivote → español), que produce las
variaciones léxicas y sintácticas típicas de un texto reescrito por otra persona.

Requisito central: la consulta debe seguir **caracterizando la misma partida**, es decir, con
los mismos valores en todos los ejes paramétricos que aparecen en el TEXTO. Si la traducción
cambia un valor («rocoso» → «semirrocoso»), la consulta pasa a describir otra hoja y el gold es
falso.

## 2. Punto de partida

- **Catálogo.** BPA 2026, capítulo OE: 83 conceptos y 70 242 hojas (TEXTO gold).
- **STACKED.** 4 998 consultas con todas las modificaciones apiladas.
- **STACKED-P.** Subconjunto «limpio» de STACKED construido en esta fase (§3.2): 4 674 hojas.
  Son las hojas sobre las que se hace la BT.
- **Motor.** OPUS-MT (MarianMT) con revisiones fijadas, beam 4 sin muestreo, en local (GPU).

| Dirección | Modelo | Licencia |
|---|---|---|
| es→en / en→es | `Helsinki-NLP/opus-mt-es-en@c96e2c5` / `opus-mt-en-es@5bc4493` | Apache-2.0 |
| en→fr / fr→es | `opus-mt-en-fr@dd7f654` / `opus-mt-fr-es@f4263af` | Apache-2.0 |
| en→it / it→es | `opus-mt-en-it@be5a254` / `opus-mt-it-es@bf60834` | Apache-2.0 |
| en→de / de→es | `opus-mt-en-de@6183067` / `opus-mt-de-es@0c0187a` | CC-BY-4.0 / Apache-2.0 |

Todas las traducciones se guardan en cachés JSONL por dirección (modo registro y modo
reproducción), así que la generación es determinista y se reproduce sin GPU.

## 3. Cronología: qué se intentó

### 3.1 Diseño inicial: BT de STACKED con un verificador de caracterización con LLM

**Idea.** Traducir de ida y vuelta las consultas STACKED (pivote EN) y aceptar solo las que
conserven la caracterización paramétrica. Para comprobarlo, dos LLM locales (phi4 y
qwen2.5:14b, temperatura 0, JSON estricto) leen la consulta sin ver el gold y eligen, para cada
eje, una de las opciones del concepto o «no determinable» (puerta G2).

**Calibración.** Antes de usarlo se calibró con 2 254 casos de verdad conocida (semilla 42,
8 hojas por concepto):
- positivos: el TEXTO gold, en el que cada eje debe extraerse bien;
- discriminación: hojas hermanas que difieren en un valor;
- ablación: el TEXTO sin el valor, que debe dar «no determinable»;
- derivas conocidas: deben rechazarse.

| Iteración | Prompt | Positivos (≥ 99,5 %) | Discriminación (≥ 99 %) | Ablación (≥ 99 %) | Derivas (100 %) |
|---|---|---:|---:|---:|---:|
| 1 | opciones numeradas | 98,88 % | 97,69 % | 14,91 % | 90,97 % |
| 2 | letras, `null`, regla de genéricas | 98,01 % | 97,38 % | 38,46 % | 91,59 % |
| 3 (solo phi4) | opción + cita literal comprobada en código | 99,24 % | 98,77 % | 93,88 % | — |

**Problema.** Ningún prompt alcanza los umbrales. El fallo principal es la ablación: los
modelos «rellenan» el valor que falta con el más probable en vez de admitir que no está, que es
justo el error que el verificador debe detectar. Además, qwen2.5:14b tardaba 5,9 s por llamada.

**Decisión (César, CP2).** Parar el verificador con LLM y rediseñar.

### 3.2 Rediseño: proteger los valores en lugar de verificarlos

**Idea.** En lugar de comprobar después si la traducción estropeó un valor, impedir que lo
toque. Cada consulta se alinea con su plantilla (`bt_alignment`). Así se sabe exactamente qué
tramo de texto es cada valor de eje (L1) y cada fragmento de variable de texto (L2). Esos
tramos, junto con cantidades, bandas horarias y siglas (PVC, PRFV, ADIF…), se **enmascaran**
antes de traducir y se restauran literalmente después. La traducción solo toca la prosa de la
plantilla.

La verificación pasa a ser **estructural, sin LLM**:
- máscaras preservadas y en el mismo orden;
- **G0**, elegibilidad: el gold existe y la hoja no está en los conjuntos de test P7/P8;
- **G1**, invariantes: mismo multiconjunto de cantidades, bandas, códigos y siglas que el origen,
  sin añadir ni perder ninguno;
- **G3**, no confundibilidad: la consulta no coincide con el TEXTO de otra hoja;
- **G6**, no trivialidad: distinta del origen, del gold y de cualquier consulta ya entregada.

**Formato de máscara.** Miniexperimento con 100 consultas:

| Estrategia | Máscara perdida | Aceptadas |
|---|---:|---:|
| `[[V1]]` (sentinel) | 82 | 16 |
| `<x1/>` (xml) | 7 | 93 |
| `[1]` (bracket) | 1 | **98** |

MarianMT parte o duplica los corchetes dobles y a veces altera las etiquetas XML, pero copia
casi siempre `[n]`. Se eligió `bracket`.

**STACKED-P.** Al alinear STACKED con sus plantillas apareció un problema previo a la BT:
14 reescrituras del menú cambian el significado de un valor. Por ejemplo, «con topo» →
«topografía» o «adosada» → «empotrada / a ras». Una auditoría determinista excluyó 324 de las
4 998 consultas:
- 321 por esas derivas conocidas;
- 2 por duplicar textos ya entregados;
- 1 degenerada.

Queda STACKED-P = 4 674. La lista se entrega aparte (`OE_stacked_P_exclusion.json`) para
poder filtrar STACKED al evaluar. César eligió la lista de exclusión en lugar de regenerar.

### 3.3 Piloto de BT de prosa (300 consultas)

Dos condiciones con pivote EN:
- `stacked_bt`: BT de la consulta STACKED;
- `bt_orig`: BT del TEXTO gold de la misma hoja.

Resultados:
- Aceptación estructural del 98,0 % y del 98,7 %, respectivamente.
- Ninguna consulta idéntica al origen.
- Distancia mediana al gold: de 34 a 42 tokens en `stacked_bt` y de 0 a 19 en `bt_orig`.
- El filtro de aceptación no sesga la dificultad de STACKED: BM25 Acc@1 del 24,1 % en las
  aceptadas frente al 23,7 % en toda la muestra.
- BM25 Acc@1 de las consultas `stacked_bt` aceptadas: 28,9 %.

### 3.4 BT de los valores (idea de César)

Con los valores enmascarados, la BT no cambiaba nada de lo que más distingue una hoja de sus
hermanas. César propuso traducir también los valores. Como son textos muy cortos, se hace con
dos ajustes:
1. **Etiqueta como contexto.** A veces se traduce «etiqueta: valor» («Tipo de terreno:
   rocoso»), en forma de frase.
2. **Un idioma más en la cadena.** ES→EN→{FR, IT, DE}→ES, para que la vuelta no devuelva
   simplemente el original.

Proceso:
- **Generación.** 11 154 candidatas sobre valores L1 y fragmentos L2.
- **Filtros automáticos.**
  - Se descartan las variantes L2 que pierden un término de dominio, es decir, una palabra que
    aparece en ≤ 35 % de los conceptos.
  - Se descartan las variantes que revierten a otro valor.
- **Auditoría por agentes con contexto limpio**, un veredicto por casilla:

  | | Casillas | Aprobadas |
  |---|---:|---:|
  | Valores L1 | 637 | 223 |
  | Fragmentos L2 | 189 | 94 |

- **Tabla cerrada final.** 218 variantes aprobadas. En la entrega se usan 64 distintas, con
  6 057 usos.
- **Revisión final.** Hecha por Claude con el criterio de César: 64/64 aceptadas.

**Regla de montaje.** Cuando hay variante aprobada se usa siempre. La etiqueta se antepone con
p = 0,5 y solo si el valor no lleva dígitos; se copia la mayúscula inicial del original.

### 3.5 Cambio de origen: del STACKED al gold

Hasta aquí la BT se aplicaba sobre STACKED, con dos problemas:
- **Mezcla de efectos.** La consulta acumula paráfrasis del menú más traducción, así que no se
  puede medir el efecto de la BT por separado.
- **Errores heredados.** Una deriva o paráfrasis rota de STACKED pasa a la BT (§5).

César decidió partir del **TEXTO gold** de cada hoja de STACKED-P. Es la condición `bt_origv`:
BT de la prosa del gold más variantes de valor. Las mismas hojas que STACKED-P permiten la
comparación directa entre las dos formas de generar consultas.

### 3.6 Primer intento sobre el gold: BT de la prosa entera

**Sin protección del glosario.** Agentes con contexto limpio auditaron las 82 prosas
distintas del gold traducidas: solo 22 se aprobaron (11 dudosas, 49 rechazadas). La mayoría de
los rechazos venían de términos del oficio que el traductor no conoce:
- «canaleta» → «canal», «canalones» o «alcantarillas»;
- «tapa» → «parte superior»;
- «tapado» → «tapeado»;
- «balasto» → «lastre»;
- etiquetas como «Horario» → «Calendario».

**Con los 27 términos del glosario enmascarados.** Al enmascararlos aparece otro problema:
MarianMT reordena o pierde los marcadores cuando hay muchos en una misma frase. Solo 35 de las
81 prosas se aprobaron, que cubren 3 704 hojas pero solo **28 conceptos**. La cobertura era
insuficiente.

### 3.7 Solución: BT por frases con restauración posterior del glosario

Propuesta de César: no proteger los términos antes de traducir, sino **restaurarlos después**.
Si la traducción cambió «arqueta» por otra palabra, se vuelve a poner «arqueta».

**Implementación (`bt_restore.restore_terms`).**
1. Se alinea la frase de origen con la traducida (difflib).
2. Se sustituye el bloque traducido por el término original cuando el término se perdió.
3. Salvaguardas:
   - bloques de igual longitud;
   - o bloques desiguales de hasta 3 palabras con solo palabras funcionales;
   - rechazo si en un bloque hay varios términos perdidos;
   - comprobación final del recuento de cada término.

El glosario se amplió a 33 términos (poste, corrugada, composite, solera…).

**Unidad: la frase.**
- Hay 119 frases distintas.
- Cada una tiene hasta 4 traducciones candidatas, por las cadenas EN, EN-FR, EN-IT y EN-DE.
- Una auditoría por agentes juzgó 281 pares frase–candidata y aprobó 107.
- Para cada frase se usa la primera candidata aprobada; si no hay ninguna, se deja la frase
  original. Así una frase difícil no hace perder la hoja entera.
- 61 de las 119 frases tienen al menos una traducción aprobada.

**Resultado.** 4 670 consultas de **79 conceptos**, frente a los 28 anteriores.

### 3.8 Sinónimos del glosario (idea de César)

La restauración deja los términos del oficio siempre idénticos al gold. Eso facilita
artificialmente la búsqueda léxica y resta realismo. Por eso, con semilla y p = 0,5, cada
aparición se sustituye por una alternativa aprobada.

**Cómo se reunieron las alternativas.**
- Un agente propuso alternativas a partir de frases reales del catálogo.
- Otro agente las auditó, en tres rondas.
- César añadió y retiró alternativas.

Por ejemplo: «zanja» → «rasa / zanjeo / excavación longitudinal», «poste» → «apoyo / mástil»,
«talud» → «ladera / vertiente». César fijó como mínimo 3 alternativas por término y pidió no
preocuparse por pequeños errores de artículos o concordancia, porque también aparecen en
textos reales.

**Cifras.** 122 alternativas para 33 términos. 2 898 consultas llevan al menos un sinónimo.

**Reglas.**
- Nunca se sustituye dentro de un valor.
- No se elige una alternativa que ya esté en el texto (por ejemplo, no se cambia «firme» por
  «pavimento» si la frase ya dice «pavimento»).
- Se copian la mayúscula inicial y el plural.

## 4. Resultado entregado

`handoff_OE/OE_bt_texto.json`, con su sidecar (`OE_bt_modifications.jsonl`) y su procedencia
(`OE_bt_provenance.json`).

| Medida | Valor |
|---|---:|
| Consultas | 4 670 |
| Conceptos | 79 de 83 |
| Fracción media de frases traducidas | 0,48 |
| Consultas con todas las frases traducidas | 3 |
| Consultas con variante de valor | 3 787 |
| Consultas con sinónimo del glosario | 2 898 |
| Frases traducidas por cadena (EN-FR / EN / EN-DE / EN-IT) | 4 843 / 4 503 / 72 / 54 |
| BM25 Acc@1, prosa + valores (sobre STACKED) | 20,4 % frente a 23,7 % sin BT |

Notas:
- **Fracción de frases traducidas.** La media es baja porque las frases de etiqueta
  («Trabajo: X.») vuelven idénticas del traductor. Contando solo las frases traducibles, se
  traducen unas dos de cada tres.
- **Conceptos que faltan.** Dos no están en STACKED-P, y OEB160 y OEE020 no tienen ninguna frase
  con traducción aprobada.

**Garantías.**
- Todo lo que contiene una consulta está auditado: frases aprobadas u originales, variantes de
  valor y sinónimos de listas aprobadas.
- Verificación estructural G0, G1, G3 y G6.
- Doble ejecución en modo reproducción con sha256 idénticos.
- Ningún fichero entregado antes ha cambiado.

## 5. Hallazgos colaterales en los conjuntos previos

### 5.1 «hormigonada» (F-BT-1, cerrado)

Las paráfrasis de STACKED (y también la BT) cambian «Canalización hormigonada» por
«Conducción enterrada» o «Canalización de hormigón».
- Afecta a 2 969 consultas de STACKED, 339 de SINGLE, 975 de dose y 587 de isolated.
- Se pierde la palabra, no el tipo de partida: la plantilla vuelve a decir «hormigón tipo HE-20»
  y no hay ninguna canalización no hormigonada de tubo con la que confundirla.
- Solo 34 consultas no mencionan hormigón en ningún sitio. Están listadas en
  `data/synthetic/bt_OE/OE_hormigonada_no_concrete.json`.

### 5.2 Paráfrasis de plantilla rotas → v2 de los conjuntos

Mientras se revisaba F-BT-1 aparecieron consultas como «con un diámetro de **en plataforma de
estación** mm». Causa: paráfrasis de plantilla, aprobadas en la revisión de agosto, en las que el
LLM malinterpretó un hueco. La plantilla dice «de 110 mm de diámetro $I», con $I = ubicación, y
la paráfrasis dice «con un diámetro de $I mm».

**Auditoría.** 8 agentes con contexto limpio revisaron las 828 paráfrasis TEXTO que se usan:

| Defecto | Paráfrasis | Decisión de César |
|---|---:|---|
| Hueco en un papel que no es el suyo | 134 | corregir |
| Valor tratado como referencia («se detallan en Nocturno») | 29 | corregir |
| Unidad duplicada («40 mm mm») | 17 | dejar: pasa en documentos reales |
| Gramática incoherente | 19 | dejar |
| Cambio de significado | 222 | dejar |

**Corrección.**
- Cada una de las 163 paráfrasis se corrigió con el mínimo cambio y conservando los mismos
  huecos.
- Cada consulta afectada se alinea con la paráfrasis rota para recuperar sus valores y se
  vuelve a renderizar con la corregida.
- Cambian 3 175 consultas: 2 039 de STACKED, 241 de SINGLE, 547 de dose y 348 de isolated. El
  resto queda byte a byte igual.
- Dos agentes nuevos verificaron las 163 correcciones: todas resuelven el fallo y ninguna
  introduce un error nuevo.

Se entrega como `OE_*_texto_v2.json`. Para el artículo: la v2 es la versión que debe usarse.

## 6. Problemas encontrados y cómo se resolvieron

| Problema | Causa | Solución |
|---|---|---|
| El verificador LLM no alcanza los umbrales | Los modelos rellenan el valor ausente (ablación del 15–94 %) | Enmascarar valores y verificación estructural sin LLM |
| Máscaras perdidas | MarianMT parte `[[V1]]` y altera `<x1/>` | Máscara `[n]` (98/100) |
| Derivas de significado en STACKED | 14 reescrituras del menú cambian un valor | STACKED-P por lista de exclusión (324) |
| FR→ES colgado con salidas degeneradas | Bucles hasta `max_new_tokens = 512` | Tope de 2 × tokens de entrada + 16 |
| Etiquetas en mayúsculas tratadas como siglas | «TIPO DE TERRENO» se enmascaraba | Etiqueta en forma de frase («Tipo de terreno») |
| G1 rechazaba conversiones aprobadas | La variante de valor cambia cantidades a propósito | G1 compara en el espacio original, deshaciendo las sustituciones registradas |
| G1 perdía siglas enmascaradas (PRFV) | La presencia se miraba sobre el texto enmascarado | Comprobación sobre el texto con los valores restaurados |
| «Trabajos: Trabajo: Diurno» | La BT ya había dejado la etiqueta, en plural | Detección de la etiqueta por raíz |
| Variante con mayúscula a mitad de frase | La variante venía de una traducción aislada | Se copia la mayúscula inicial del original |
| Términos del oficio mal traducidos (22/82 prosas aprobadas) | El vocabulario técnico es raro en OPUS | Restauración posterior del glosario |
| Pocas prosas aprobadas con glosario enmascarado (28 conceptos) | Muchos marcadores en una frase → reordenación | Unidad = frase, varias cadenas y respaldo con la frase original |
| La restauración pegaba bloques con varios términos | Bloques desiguales en difflib | Salvaguardas de longitud, palabras funcionales y recuento |
| Términos del oficio siempre literales | Efecto de la restauración | Sinónimos auditados con p = 0,5 |
| Paráfrasis de STACKED con huecos mal asignados | Revisión de agosto sin ver el texto rellenado | Auditoría con ejemplo rellenado y corrección → v2 |

## 7. Limitaciones para el artículo

- **Traducción parcial.** Una consulta BT traduce de media el 48 % de sus frases; el resto queda
  como en el gold, sobre todo las frases de etiqueta.
- **Auditorías por agentes.** Las auditorías de frases, valores, glosario y paráfrasis las
  hicieron agentes LLM con contexto limpio. César revisó y decidió sobre casos concretos y sobre
  los criterios, pero no hubo una auditoría humana completa.
- **Etiquetas torpes.** Las etiquetas antepuestas quedan a veces forzadas («con acceso por
  Acceso: vía»). Se dejaron con el criterio de realismo.
- **Cobertura.** 79 de 83 conceptos.
- **Modelos.** Solo OPUS-MT. Otros motores, como los LLM, darían paráfrasis más libres, pero con
  más riesgo para los valores.
- **Verificación de caracterización.** No hay un verificador semántico automático fiable (§3.1).
  La garantía viene del enmascarado y de las auditorías.

## 8. Decisiones de César (resumen)

| Momento | Decisión |
|---|---|
| CP1 | Valores por defecto del handoff; siglas enmascaradas antes de traducir |
| CP2 | Parar el verificador con LLM; enmascarar valores; STACKED-P por lista de exclusión; G4 por grupo D-031; cachés en git |
| CP3 | STACKED-P aprobado |
| CP4 | BT de valores con etiqueta y cadena de idioma adicional; partir del gold; auditorías por agentes |
| Después | Prosa por frases con restauración posterior del glosario y respaldo con la frase original; sinónimos del glosario (≥ 3 por término; artículos y concordancia sin importancia) |
| Cierre | F-BT-1 cerrado; paráfrasis rotas: corregir hueco y referencia, dejar el resto; v2 como ficheros nuevos |

## 9. Código y datos

| Pieza | Ruta |
|---|---|
| Enmascarado | `src/synthetic/bt_masking.py` |
| Alineación plantilla → texto | `src/synthetic/bt_alignment.py` |
| Motor BT y cachés | `src/synthetic/back_translation.py` |
| Variantes de valor | `src/synthetic/bt_values.py` |
| Restauración del glosario | `src/synthetic/bt_restore.py` |
| Sinónimos del glosario | `src/synthetic/bt_glossary.py` |
| Verificador (G0–G6) | `src/synthetic/characterization.py` |
| Reparación de paráfrasis | `src/synthetic/paraphrase_repair.py` |
| Scripts | `scripts/build_bt*.py`, `scripts/calibrate_characterization.py`, `scripts/audit_stacked_characterization.py`, `scripts/repair_broken_paraphrases.py`, `scripts/package_*_handoff.py`, `scripts/sample_bt_vs_stacked.py` |
| Configuración | `configs/synthetic/bt_OE.yaml` |
| Datos intermedios, veredictos y cachés | `data/synthetic/bt_OE/`, `data/synthetic/broken_OE/` |
| Informes | `docs/synthetic/bt/` |
| Entregables | `data/synthetic/handoff_OE/` (§8 y §9 de `HANDOFF.md`) |
