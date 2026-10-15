# Handoff a `bc3cat-retrieval`: v2 de los conjuntos OE y consultas BT (2026-10-16)

Nota autocontenida para la sesión que trabaja en `bc3cat-retrieval`, rama
`research/synthetic-oe`. La escribe la sesión de `bc3cat-dataset` (rama `synthetic`, commit
`467d8e51` o posterior). Las decisiones de diseño de los experimentos corresponden a ese repo y a
César: aquí solo se describe qué ha cambiado y qué conviene revisar.

**Reglas.**
- Los ficheros entregados son inmutables: la v1 sigue en el handoff byte a byte igual.
- Si algo no cuadra con esta nota, se para y se pregunta a César.
- No se modifica nada en `bc3cat-dataset`.

---

## 1. Qué hay de nuevo

Todos los ficheros están en `D:/Users/cesar/Dev/Phd/bc3cat-dataset/data/synthetic/handoff_OE/`.
Los sha256 también figuran en el `MANIFEST.md` de esa carpeta.

| Fichero | Bytes | sha256 | Qué es |
|---|---:|---|---|
| `OE_stacked_texto_v2.json` | 5 670 003 | `bc1ed968f60933d9c63270e6050de0f4cf3ed758614e7d8549256f1fd9fcb7f1` | STACKED v2 |
| `OE_single_texto_v2.json` | 4 018 964 | `b3c58fcb38fd294f817b90a206f2b5ca73644af6987ac3c24d9edd65379af1ae` | SINGLE v2 |
| `OE_dose_texto_v2.json` | 4 152 455 | `8becd49ad0fd1f37a18f060c66af46438ea7f530ade15f53ac88c05ce40a1985` | dose v2 |
| `OE_isolated_texto_v2.json` | 7 113 665 | `95c0c2edaef0c7dc54721533feae97c8dd9d3159a572bd7cb11315190514b271` | isolated v2 |
| `OE_v2_changes.jsonl` | 3 952 840 | `981896771092f6a957fa4c3dc507c7d715e88933814753df58ee2adbe75cfe0e` | Una línea por consulta cambiada: `set`, `item_key`, `paraphrase_id`, `old`, `new` |
| `OE_v2_provenance.json` | 2 164 | `1c9e4d6db1a7569b20789c0a52fa98bd1706cfe3b7c8ca0cae6af8ece6d4e96e` | Auditoría, método, verificación |
| `OE_bt_texto.json` | 9 434 707 | `421b3ca3a3d3f61f26d4653b3f84e4a614ff2dc6ade7acfb4a8f3da1da7d408c` | Consultas BT (4 670) |
| `OE_bt_modifications.jsonl` | 2 697 154 | `c1ffe3bfafa2736dcc7ab2444bfdedc046fc0a42a3ac9e7ffa14f715b109738a` | Sidecar de la BT |
| `OE_bt_provenance.json` | 4 082 | `d17653030a0b0cc320babffad9e0322a3259bc9ee07db608b97751516da01f33` | Procedencia de la BT |
| `OE_stacked_P_exclusion.json` | 60 110 | `bbe36522fdccb4fabb526a8ee029ccd5494c2f60c4b5dd87d036ab3e3f9c69c1` | 324 consultas STACKED fuera de STACKED-P (`item_keys`, `details`) |
| `OE_known_drift_rewrites.json` | 14 513 | `1431f19dfb4791f22ac4a1b8be6779ff6f6d0fe89c12362932474d6cae0dc759` | Las 14 reescrituras de deriva conocidas |

El corpus (`OE_texto.json`, `OE_resumen.json`) **no cambia**.

## 2. v2: paráfrasis de plantilla rotas, corregidas

**Defecto.** Algunas paráfrasis de plantilla aprobadas en el menú ponen un valor en un papel que
no es el suyo. Por ejemplo:
- «de 200 mm y diámetro **en cruce bajo vías**»;
- «con un diámetro de **en terreno rocoso** mm»;
- unas medidas leídas como ubicación;
- una operación leída como cantidad.

Otras presentan un valor como un documento de referencia («las condiciones de ejecución se
detallan en **Nocturno**»).

**Alcance.** Una auditoría de las 828 paráfrasis TEXTO usadas encontró 163 de estos dos tipos.
César decidió corregir solo esos dos tipos. Las unidades duplicadas («40 mm mm»), la gramática
torpe y los cambios de significado se dejan a propósito, porque aparecen en documentos reales.

**Corrección.**
- Cada paráfrasis se corrigió con el mínimo cambio y conservando los mismos huecos.
- Cada consulta afectada se volvió a renderizar con sus mismos valores.
- `id`, `item_key`, `gold_item_key`, `parent_key` y todos los demás campos son idénticos a la v1.
  Solo cambia `text` en las consultas listadas en `OE_v2_changes.jsonl`; el resto es byte a byte
  igual.
- En las consultas cambiadas los espacios están normalizados («An6 ,» → «An6,»).

**Impacto por conjunto.**

| Conjunto | Consultas | Cambiadas |
|---|---:|---:|
| STACKED | 4 998 | 2 039 (41 %) |
| SINGLE | 4 439 | 241 |
| dose | 3 000 | 547 |
| isolated | 5 400 | 348 |

**Dose e isolated, con detalle.** El defecto se concentra en las canalizaciones OEB, que son
justo los 7 conceptos de E3.

| | dev (`OEB020/030/230/290`) | test (`OEB040/280/300`) |
|---|---:|---:|
| dose cambiadas | 337 / 1 640 | 210 / 1 360 |
| isolated cambiadas | 214 / 2 952 | 134 / 2 448 |

- **Las 348 consultas cambiadas de isolated son todas del tipo `template_paraphrase`.** Isolated
  tiene 600 consultas de ese tipo, así que **el 58 % del efecto aislado de `template_paraphrase`
  se midió en la v1 con paráfrasis rotas**.
- En dose, las consultas cambiadas por peldaño (1–5) son 34, 69, 114, 158 y 172. Las consultas
  con `template_paraphrase` por peldaño son 70, 140, 211, 279 y 300. En todos los peldaños, más o
  menos la mitad de las consultas con paráfrasis de plantilla estaban rotas, y su peso crece con
  la dosis.
- Es de esperar que se muevan la pendiente de dosis (S7/S8) y la comparación con la suma de
  efectos aislados (H4).

## 3. Consultas BT

**Qué son.**
- 4 670 consultas, una por hoja de STACKED-P, de 79 conceptos.
- Cada una es el TEXTO gold de su hoja, traducido de ida y vuelta frase a frase con OPUS-MT
  (ES→EN→ES y ES→EN→{FR, IT, DE}→ES).
- Los valores paramétricos se protegen durante la traducción. Después se sustituyen por variantes
  auditadas, a veces con la etiqueta del eje delante.
- El 50 % de los términos del oficio («zanja», «poste»…) se cambian por sinónimos auditados.
- Gold = `gold_item_key` (la hoja de origen), igual que en los demás conjuntos.

**Esquema.** El de STACKED más estos campos:
- `condition`: `bt_origv_en`;
- `source_item_key`, `source_text_sha256`;
- `bt` (motor, cadenas, máscara);
- `bt_sentences` (`translated`, `total`, `fraction`, `chains`);
- `characterization_check`;
- `texto_modification_types_post_bt` y `reverted_types`.

`modification_types` ⊆ {`back_translation`, `value_back_translation`, `glossary_synonym`}. Los
`item_key` terminan en `_btorigv_en`.

**Datos que conviene tener en cuenta.**
- Fracción media de frases traducidas: 0,48. Las frases de etiqueta («Trabajo: X.») suelen volver
  idénticas.
- 3 787 consultas llevan variante de valor y 2 898 sinónimo del glosario.
- Faltan 4 de los 83 conceptos.
- Ninguna consulta BT es igual a un TEXTO gold ni a una consulta ya entregada.

**Emparejamiento con STACKED.** Las 4 670 hojas de la BT están todas en STACKED. Cada una tiene
una consulta STACKED v2 y una BT con el mismo gold, así que la comparación puede ser emparejada
por hoja. Hay 4 hojas de STACKED-P sin consulta BT.

## 4. STACKED-P

`OE_stacked_P_exclusion.json` lista 324 consultas de STACKED:
- 321 con una reescritura de deriva conocida («con topo» → «topografía», «adosada» →
  «empotrada / a ras»…), que cambia un valor y deja el gold en entredicho;
- 2 duplicadas de otros conjuntos;
- 1 degenerada.

La lista vale igual para la v2 porque los `item_key` son los mismos. César decidió no repetir la
auditoría de deriva sobre la v2.

## 5. Qué conviene hacer (propuesta; lo decide el repo de retrieval con César)

1. **Entrada.**
   - Copiar los ficheros de §1 a `data/processed/` y comprobar los sha256.
   - Comprobar que en la v2 los `id`, `item_key` y `gold_item_key` coinciden con la v1, en el
     mismo orden.
   - Comprobar que solo cambia `text` en las consultas de `OE_v2_changes.jsonl`.
   - Comprobar que todos los `gold_item_key` de la BT existen en el corpus.
   - Registrarlo en `DELIVERIES.md` y `INTAKE.md`.
2. **Defectos.** Añadir a `DATASET_DEFECTS.md` el defecto de las paráfrasis con huecos mal
   asignados o valores como referencia, resuelto con la v2. Conviene revisar el apartado P5
   («Pantry artefacts… kept deliberately»): las unidades duplicadas siguen en la v2 a propósito.
3. **Volver a ejecutar sobre la v2.**
   - Todos los resultados sobre STACKED y SINGLE.
   - En especial, dose e isolated (S7/S8 y H4), donde el efecto de `template_paraphrase` estaba
     medido sobre un 50–58 % de consultas rotas.
   - Se sugiere mostrar la v1 junto a la v2 como análisis de sensibilidad en lugar de borrarla.
4. **STACKED-P.** Dar los resultados de STACKED también filtrados a STACKED-P.
5. **BT.**
   - Registrar un conjunto de consultas nuevo (p. ej. `bt_texto`) en `run_context.QUERY_SETS`.
   - Hacer la comparación emparejada STACKED-P frente a BT sobre las 4 670 hojas comunes.
   - Opcional: análisis por `bt_sentences.fraction` y por presencia de `value_back_translation`
     y `glossary_synonym`.

## 6. Referencias en `bc3cat-dataset`

- `docs/synthetic/bt/BT_proceso.md`: proceso completo de la BT para el artículo (intentos,
  problemas, soluciones, limitaciones).
- `docs/synthetic/bt/OE_bt_vs_stacked_sample.md`: 12 hojas con gold, STACKED v2 y BT.
- `docs/synthetic/HANDOFF.md` §8 (BT) y §9 (v2).
- `data/synthetic/broken_OE/`: auditoría de las 828 paráfrasis, las 163 correcciones y su
  verificación.
