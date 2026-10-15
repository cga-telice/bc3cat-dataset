# BC3CAT-Syn → `bc3cat-retrieval` Handoff

A short cross-repo memo for the `bc3cat-retrieval` maintainer. It tells you where
the BC3CAT-Syn release lives, how to load it, and what new evaluation slices it
adds. **It does not modify `bc3cat-retrieval`** — the `import`/index wiring on the
retrieval side is that repo's change.

> **Status: pilot corpus GENERATED (Sprint 39, 2026-09-02).** The release
> **format, schema, and loader API are frozen and test-pinned** (Phase G tasks
> G1/G2), and the files now exist on disk — release commit `6b52053`:
>
> | | |
> |---|---|
> | Items | **8 687** produced (of 8 734 planned) |
> | Conditions | 10 — nine `single_<type>` + `all_combined` |
> | Dropped | 45 no-ops (0.5 %), 2 exact duplicates |
> | Hard failures | 0 (emission / composition / placeholder residue) |
> | Determinism | two full runs byte-identical (items SHA-256 `7A99A754…`, modifications `DA8A140A…`) |
>
> Per-condition detail lives in
> [`sprints/SPRINT_39_corpus_report.md`](sprints/SPRINT_39_corpus_report.md).
> Scale-up to all of OBRA CIVIL is Sprint 40; this pilot covers the 25 OEB
> concept groups.
>
> **Three accepted caveats (César, 2026-09-02)** — documented stress, not bugs;
> all traceable per item through the modifications sidecar:
> 1. `reorder` never appears in `all_combined` (full-template rewrites collide
>    per field, and every `all_combined` item carries a `template_paraphrase`
>    for BOTH fields); `reorder` is measured in `single_reorder` (1 000/1 000).
> 2. Thin-type deficits: `unit_expansion` 373/650, `unit_conversion` 209/350
>    (pantry-limited under the ≤20-uses-per-rewrite cap; worst-case 95 %
>    margins ≈ ±5.1 / ±6.8).
> 3. Pantry artifacts kept as stress: "tubos tubos" (~376 items), "mm mm"
>    (~280), "con topo"→"con topografía" (~245; semantic drift).

---

## 1. The two release files

Under `data/synthetic/processed/` in `bc3cat-dataset` (branch `synthetic`),
joined **1:1 on `item_key`**:

| File                              | Shape          | Carries                                            |
|-----------------------------------|----------------|----------------------------------------------------|
| `BC3CAT_Syn_items.parquet`        | flat columnar  | one row per synthetic item (the 9 `ITEM_COLUMNS`)  |
| `BC3CAT_Syn_modifications.jsonl`  | ragged, 1 / key| the per-item `modifications` log (kept out of Parquet) |

Items columns (frozen order): `item_key, original_key, concept_key, params,
resumen, texto, variante_id, modification_types, modification_count`.

---

## 2. New evaluation slice columns

Beyond the retrieval text, two item-level columns drive slice-aware evaluation:

- **`modification_types`** (`list[str]`) — per-type slicing (the 12 codes); a
  per-layer slice aggregates these via `synthetic.taxonomy.TYPE_TO_LAYER`.
- **`modification_count`** (`int`) — compositionality slicing
  (`{1, 2, 3, 4, ≥5}`; `0` = baseline).

The pilot corpus runs **10 generation conditions** (`RESEARCH_PROTOCOL.md §6`
as amended 2026-09-02): nine `single_<type>` plus `all_combined` (the
`stacked_*` / `new_param_only` conditions were retired from the pilot on
2026-08-31; the schema still supports them).

**Condition is not a column of the frozen schema, but it is derivable
unambiguously:**

```python
condition = (
    f"single_{row.modification_types[0]}" if row.modification_count == 1
    else "all_combined"
)
```

(`modification_count == 1` → that type's single condition; `> 1` →
`all_combined` — in this release every `all_combined` item carries ≥ 3
distinct types, so the rule cannot misclassify.)

The join key back to the original BC3CAT/OEB item is `original_key` (the
`(item_key, original_key, variante_id)` triple is unique) — paired evaluation
compares each synthetic item against its original leaf in
`OEB_{long,short}_norm.parquet`.

---

## 3. Loader API (`synthetic.loaders`)

With `PYTHONPATH=src` in `bc3cat-dataset`:

```python
from synthetic.loaders import (
    load_items, load_modifications, join, long_view, short_view,
)

items  = load_items()          # ITEM_COLUMNS frame
mods   = load_modifications()  # {item_key: [Modification, ...]}, baseline -> []
joined = join(items, mods)     # 1:1 on item_key, fail-loud; + `modifications` list[dict] column

targets = long_view(items)     # text == texto
queries = short_view(items)    # text == resumen
```

`long_view` / `short_view` return the OEB-style projection: the key + slice
columns (`item_key, original_key, concept_key, params, variante_id,
modification_types, modification_count`), the retrieval text in a single `text`
column, and a derived `text_norm`.

**`text_norm` is byte-for-byte consistent with the parent OEB.** It is produced
by `utils.text_processing.normalize_text` — the *same* normalizer behind the
`OEB_long_norm` / `OEB_short_norm` `text_norm` columns this repo already indexes.
So `long_view` maps to `OEB_long_norm` and `short_view` to `OEB_short_norm`:
`text` + `text_norm` in the same shape, plus the synthetic key/slice metadata.
No OEB-only `id`/`ud`/`concept` columns are fabricated.

`join` returns a sorted copy and raises `LoaderError` on any non-1:1 `item_key`
match (a partial release fails loud rather than silently dropping/duplicating
rows).

---

## 4. What this memo is not

- It does **not** add an import or index path in `bc3cat-retrieval` — that is the
  retrieval repo's own change.
- It ships the **pilot** corpus (25 OEB concept groups); the full OBRA CIVIL
  scale-up is Sprint 40 and will regenerate the two files in place (same
  schema, same paths).
- `synthetic` is a permanent parallel branch and is **never merged to `main`**
  (see [`CLAUDE.md`](../../CLAUDE.md)).

See [`DATA_CARD.md`](DATA_CARD.md) for the full schema, taxonomy, slices, and
provenance.


## 5. E3 — conjunto de dosis

Entrega del 2026-09-17 (`run_id` `e3-20260917T093057Z`, commit de generación
`e057907`, semilla 42 leída de `configs/synthetic/variant_budgets_OE_dose.yaml`).
Catálogo BPA 2026, capítulo OE. Informe completo: `docs/synthetic/OE_dose_report.md`.

### Ficheros (`data/synthetic/handoff_OE/`)

| fichero | contenido |
|---|---|
| `OE_dose_texto.json` | **3 000 consultas**: 600 hojas × 5 peldaños (`modification_count` 1–5) |
| `OE_isolated_texto.json` | **5 400 consultas**: los 9 tipos por separado sobre **las mismas 600 hojas** |
| `OE_leaf_applicability.jsonl` | una fila por hoja sondeada (1 500): `applicable_types`, `available_types`, `in_pool` |
| `MANIFEST.md`, `provenance.json` | SHA-256 por fichero, commit, semilla y configuración |

Convención de gold idéntica a STACKED/SINGLE: la consulta es el TEXTO modificado
y el objetivo es el TEXTO original (`parent_key` + `gold_item_key`). Cada registro
lleva además `applicable_types` (la gramática admite el tipo) y `available_types`
(hay una reescritura aprobada que cambia el TEXTO de esa hoja). Ambos son
independientes de los topes de reuso. `in_pool` marca las 600 hojas con escalera.

### Garantías

- **Escalera anidada:** los tipos del peldaño *k* son los del peldaño *k*−1 más
  uno. Entre peldaños consecutivos cambia exactamente una modificación.
- **Población común:** los cinco peldaños y los efectos aislados usan las mismas
  600 hojas. El efecto de la dosis no se mezcla con la dificultad de la hoja.
- **Conteo exacto sobre el TEXTO:** cada modificación contada aparece en el TEXTO
  de la consulta, en tramos distintos. La generación falla si alguna no se ve.
- **Profundidad** *d* = 9 tipos disponibles y al menos 5 que caben en tramos
  distintos. Fondo de 750 hojas seleccionadas, de las que se usan 600.
- Reproducible byte a byte (verificado con una segunda corrida) y sin colisiones
  entre conceptos introducidas, ni a nivel de corpus ni de plantilla.

### Limitaciones que conviene citar

1. **Cobertura por concepto: 7 conceptos** de 83, todos canalizaciones de OEB
   (`OEB020`, `030`, `040`, `230`, `280`, `290`, `300`; entre 61 y 96 hojas cada
   uno). Es estructural, no un fallo: solo esas familias tienen descripciones con
   ≥6 tipos de cambio que además caben en tramos distintos del TEXTO. Se decidió
   no relajar el criterio. Con menos tipos, la composición del peldaño 5 quedaría
   fijada y la dosis se confundiría con el tipo. Una partición dev/test por
   concepto solo puede repartir estos 7.
2. **Presencia por tipo (salvedad de su §3).** Que cada tipo aparezca a tasas
   parejas *entre* peldaños es inalcanzable por construcción: con *k* tipos de un
   repertorio de *d*, la tasa de cada tipo crece con la dosis. Lo alcanzable es el
   equilibrio *dentro* de cada peldaño, y se cumple para ocho de los nueve tipos
   (p. ej. peldaño 1: 70–71 hojas por tipo). **`unit_conversion` queda por debajo**
   (39 en el peldaño 1, 160 en el 5), porque en estos conceptos solo tiene 4
   reescrituras distintas. Para no repetir siempre la misma, cada reescritura se
   usa como mucho 40 veces (`num_to_text`, `unit_expansion` y `unit_conversion`),
   y el reparto se ajusta a esa capacidad.
3. Los efectos aislados son completos (9 tipos × 600 hojas), así que la suma de
   efectos aislados es intra-hoja y comparable con la escalera.


## 6. STACKED — conteo visible en el TEXTO (corrección del 2026-09-17)

**Qué estaba mal.** En `OE_stacked_texto.json`, `modification_count` y
`modification_types` cuentan todos los registros de modificación aplicados. La
consulta es el TEXTO, y algunos registros no llegan a él:

- la reescritura de la plantilla del **RESUMEN**, presente en las 4 998 consultas
  (por eso `template_paraphrase` salía dos veces en la lista);
- 1 756 reescrituras de variables de texto que la plantilla del TEXTO no usa, o
  cuya condición no se cumple en la hoja (`paraphrase` 918, `expansion` 794,
  `compression` 44);
- 110 cambios de valor de ejes que solo aparecen en el RESUMEN.

Las 4 998 consultas sobrecuentan: la media registrada es 4,69 y la visible 3,31.
Auditoría completa en `docs/synthetic/OE_stacked_texto_visibility_audit.md`.
SINGLE está limpio (`docs/synthetic/OE_single_texto_visibility_audit.md`).

**Qué cambia.** Cada registro de STACKED añade:

- `texto_modification_count`: modificaciones visibles en el TEXTO;
- `texto_modification_types`: sus tipos, en el orden de aplicación.

**Qué no cambia.** Los textos, los identificadores, el orden de los registros y los
campos existentes son idénticos. Por tanto siguen valiendo los resultados de
recuperación por consulta (Acc@1, rankings); solo hay que rehacer los análisis que
agrupan por número o por tipo de modificación. Usad los campos `texto_*`.

- STACKED antes: `1bde21157ef974218b9e26ae7eecb8f5ba2a25a42b66034143201165ad015116` (entregado) · ahora:
  `c34a222ae2af05a0b5335b774cb7fb45f14064cc17234d9d885e809fb29b6f45`.
- Distribución del conteo visible: 1 → 5 · 2 → 1 252 · 3 → 1 465 · 4 → 1 799 ·
  5 → 401 · 6 → 76 (el registrado iba de 2 a 8).
- Aun con el conteo corregido, `template_paraphrase` es visible en las 4 998
  consultas y `reorder` en ninguna: la confusión entre dosis y composición que
  describe su petición E3 sigue en STACKED. El conjunto E3 existe para eso.

`provenance.json` conserva el sello original del E3 y anota el reempaquetado
(`repackaged_commit`, `repackaged_utc`). `MANIFEST.md` lista ahora también
STACKED y SINGLE.


## 7. Hojas con el TEXTO idéntico — marcadas, no colapsadas (D-031, 2026-09-27)

**Qué pasa.** 776 hojas del corpus (292 grupos) tienen el mismo TEXTO que una hermana
del mismo concepto: `OEA050$` (192 grupos de 3) y `OEG050$` (100 de 2). La plantilla
del TEXTO de esos conceptos no cita uno de sus ejes, así que las hojas que solo
difieren en él rinden igual; el RESUMEN sí las separa, y por eso la deduplicación
por pareja (resumen, texto) las conservó. Análisis completo en
`docs/synthetic/OE_duplicate_texto_groups.md`.

**Decisión (César, 2026-09-17, D-031 en `bc3cat-retrieval`).** Se **marcan**, no se
colapsan: colapsar cambiaría el conjunto de objetivos ya entregado (70 242 hojas) y
con él el digest sobre el que están sellados los runs de S2. Ningún grupo cruza
conceptos, así que la puntuación por `parent_key` no tiene techo; la identidad a
nivel de hoja de un método que solo indexa el TEXTO queda acotada en
1 − 776/70 242 ≈ 0,989 (el techo que ellos midieron, 0,9863, es sobre dev).

**Qué cambia.**

- Cada registro de `OE_texto.json` y `OE_resumen.json` lleva `duplicate_texto_group`:
  el `item_key` **mínimo** del grupo (estable, legible, y la hoja canónica si algún
  día se colapsa), o `null` fuera de grupo.
- Nuevo fichero pequeño y versionado `OE_duplicate_texto_groups.json`
  (`{group_id: [miembros]}`, con `n_groups` y `n_leaves`), sha256 `b3cfcad47c71c5ebaf86b0e77eaa741c8f6111efd4e8543262b4f1b8e4ced0df`.
  Es la misma agrupación en forma tomable **sin re‑tomar el corpus**: los digests de
  los ficheros sobre los que están sellados los runs de S2 no cambian.

**Qué no cambia.** Textos, identificadores, orden y campos existentes de todos los
ficheros. STACKED, SINGLE, dose, isolated, applicability y concept_schema son byte a
byte idénticos a la entrega anterior (verificado por sha256). El corpus completo
reempaquetado: texto `54c83faadd41bd86177006c5d7dc85e2145fa35f4bf98450870598bff70f23e9` · resumen `4511eeac0135f594ecb9094e1831abe1cbb6ef2286c12de8a86e16381a9bafde`.

`provenance.json` conserva el sello del E3 y actualiza `repackaged_commit` /
`repackaged_utc` (el commit que anota es el que estaba en HEAD al empaquetar, es
decir, el anterior al que versiona esta entrega, como en §6).

## 8. Consultas por back-translation sobre el TEXTO gold (BT, 2026-10-16)

**Qué es.** Una consulta por hoja de STACKED-P: el TEXTO gold traducido de ida y vuelta
frase a frase (ES→EN→ES y ES→EN→{FR, IT, DE}→ES, OPUS-MT con revisión fijada). 4 670
consultas de 79 conceptos. Gold = la propia hoja (`gold_item_key`).

### Ficheros (`data/synthetic/handoff_OE/`)

| Fichero | Contenido |
|---|---|
| `OE_bt_texto.json` | 4 670 consultas, esquema de STACKED más `bt`, `bt_sentences`, `characterization_check` |
| `OE_bt_modifications.jsonl` | Sidecar: frases traducidas, sustituciones de valor y sinónimos del glosario |
| `OE_bt_provenance.json` | Modelos y revisiones, licencias, auditorías, sha256 de entradas y salidas |
| `OE_stacked_P_exclusion.json` | 324 consultas STACKED fuera de STACKED-P, con motivo |
| `OE_known_drift_rewrites.json` | Las 14 reescrituras de deriva conocidas («con topo» → «topografía»…) |

### Cómo se construye

1. **Prosa por frases.** 119 frases distintas; cada una con hasta 4 traducciones candidatas.
   Los términos del oficio que el traductor pierde (arqueta, canaleta, desmonte, hastial…)
   se restauran después de traducir. Por frase se usa la primera candidata aprobada en una
   auditoría por frase (107 de 281 pares); si ninguna, la frase original.
2. **Valores.** Valores de eje y fragmentos L2 enmascarados durante la traducción; después,
   una variante auditada cuando existe (218 aprobadas), a veces con la etiqueta delante.
3. **Sinónimos del glosario.** El 50 % de las apariciones de los 33 términos del oficio se
   sustituye por una alternativa auditada (122, en tres rondas más decisiones de César).
4. **Verificación estructural**, sin LLM: máscaras y orden de valores preservados, G0, G1
   (sin cantidades, códigos ni siglas nuevas), G3 (no igual a otra hoja), G6.

### Garantías

- Todo lo que contiene una consulta está auditado: frases aprobadas u originales, variantes de
  valor y sinónimos de listas aprobadas.
- Doble ejecución en modo replay con sha256 idénticos; cachés de traducción en el repo.
- Ningún fichero entregado antes ha cambiado (sha256 frente a la línea base del 2026-10-04).

### Limitaciones que conviene citar

- **Traducción parcial.** Media de 0,48 frases traducidas por consulta; contando que las frases
  de etiqueta («Trabajo: X.») vuelven idénticas del traductor, se traducen unas dos de cada tres
  frases traducibles. Las 3 consultas con el 100 % son la excepción.
- **79 de 83 conceptos.** Dos conceptos no están en STACKED-P; OEB160 y OEE020 no tienen ninguna
  frase con traducción aprobada.
- **Auditoría por agentes.** Las auditorías las hicieron agentes con contexto limpio; César
  revisó decisiones concretas, pero la muestra de las variantes de valor está pendiente.
- **«hormigonada» (F-BT-1, cerrado).** La BT dice «Canalización de hormigón» donde el gold dice
  «Canalización hormigonada» (2 713 consultas), y las paráfrasis de STACKED, SINGLE, dose e
  isolated también quitan la palabra. No es un cambio de tipo: la plantilla vuelve a decir
  «hormigón tipo HE-20» y no hay ninguna canalización no hormigonada de tubo con la que
  confundirla. Solo 34 consultas entregadas antes (22 STACKED, 2 SINGLE, 5 dose, 5 isolated)
  no mencionan hormigón; están listadas en `data/synthetic/bt_OE/OE_hormigonada_no_concrete.json`.
- **Variantes de valor.** La entrega usa 64 de las 218 variantes aprobadas (6 057 usos),
  revisadas una a una por Claude con el criterio de César (2026-10-16): ninguna pone un valor en
  un papel que no es el suyo ni lo trata como referencia; las etiquetas torpes («Acceso: vía») se
  dejan. Lista en `docs/synthetic/bt/OE_bt_value_used_review.md`. `OE_bt_provenance.json`, ya
  entregado, sigue diciendo «muestra de César pendiente»: esta revisión la sustituye.

## 9. v2 de STACKED, SINGLE, dose e isolated: paráfrasis rotas corregidas (2026-10-16)

**Qué es.** Los mismos cuatro conjuntos, con los mismos ids, `item_key` y gold, en los que se han
corregido 163 paráfrasis de plantilla. **Usar la v2 en lugar de la v1.** La v1 sigue en
`handoff_OE` sin cambios.

| Fichero | Contenido |
|---|---|
| `OE_{stacked,single,dose,isolated}_texto_v2.json` | Conjuntos v2 |
| `OE_v2_changes.jsonl` | Una línea por consulta cambiada: conjunto, `item_key`, paráfrasis, texto antes y después |
| `OE_v2_provenance.json` | Auditoría, método, verificación y sha256 |

**Por qué.** Una auditoría por agentes de las 828 paráfrasis TEXTO usadas encontró 421 con algún
defecto. César decidió corregir dos categorías: el hueco en un papel que no es el suyo (134, p. ej.
«de 200 mm y diámetro en cruce bajo vías») y el valor tratado como referencia (29, «las condiciones
se detallan en Nocturno»). Las unidades duplicadas, la gramática torpe y los cambios de
significado se dejan, porque también aparecen en documentos reales.

**Cómo.** Cada paráfrasis se corrigió con el mínimo cambio y los mismos huecos. Cada consulta
afectada se alinea con la paráfrasis rota (mismos anclajes que la auditoría de STACKED) y se
vuelve a renderizar con la corregida y sus mismos valores. Cambian 2 039 consultas de STACKED,
241 de SINGLE, 547 de dose y 348 de isolated; el resto es byte a byte igual. En las cambiadas los
espacios quedan normalizados.

**Garantías.** Dos agentes nuevos verificaron las 163 correcciones: todas resuelven el fallo y
ninguna introduce un error nuevo (11 conservan defectos de significado que se decidió dejar). Sin
residuos de plantilla, sin textos duplicados, ninguno igual a un TEXTO gold. Doble ejecución con
sha256 idénticos. `OE_stacked_P_exclusion.json` vale para la v2; la auditoría de deriva no se
repitió (decisión de César).
