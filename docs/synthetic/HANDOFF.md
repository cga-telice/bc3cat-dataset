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
