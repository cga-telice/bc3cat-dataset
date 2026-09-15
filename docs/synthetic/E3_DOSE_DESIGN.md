# E3 — Conjunto de dosis equilibrado (escalera anidada + aplicabilidad) — Spec de diseño

| Campo | Valor |
|---|---|
| **Fecha** | 2026-09-15 (decisiones de César en sesión) |
| **Rama** | `syn/e3-dose`, sub-rama de `synthetic` (**nunca se fusiona a `main`**) |
| **Petición** | `bc3cat-retrieval`, rama `research/synthetic-oe`, sprint S0 — `E3_BALANCED_DOSE.md`, decisión de registro D-009, puerta G3 |
| **Entrada** | Despensa aprobada `data/synthetic/menus_OE/verdicts/{tipo}.jsonl` + inventario compartido de 5 000 hojas (`scripts/build_ablation_inventory.py`) + pool de targets deduplicado `OE_target_{long,short}.parquet` |
| **Salida** | `OE_dose_texto.json` (escalera) + `OE_isolated_texto.json` (efectos aislados completos) + sidecar de aplicabilidad + `MANIFEST.md`/`provenance.json` |
| **Predecesor** | Entrega OE del handoff (commit `8998875`). **Sucesor:** respuesta a `bc3cat-retrieval` con la salvedad de §8 + análisis H4 en su S8. |

## 1. Por qué

La petición E3 existe porque el conjunto STACKED entregado **no puede identificar
interacciones entre tipos de modificación**: `reorder` nunca coocurre (las
reescrituras de plantilla completa colisionan por campo) y `template_paraphrase`
está en el 100 % de los ítems. "Cuántas" y "cuáles" van confundidas, así que H4
—super-aditividad: que las modificaciones apiladas degraden más que la suma de
los efectos aislados— no es contrastable sobre él.

Es la única extensión de datos de la que depende su propuesta de investigación.

## 2. Decisiones de diseño (César, 2026-09-15)

| # | Decisión | Alternativas descartadas |
|---|---|---|
| **D1** | **Dos definiciones de aplicabilidad por hoja**: `applicable_types` (estructural: la gramática admite el tipo) y `available_types` (realizable: existe reescritura aprobada y compatible que cambia el TEXTO de esa hoja). Ambas **libres de topes de reuso**: el tope es un artefacto contable de la ejecución, y meterlo aquí haría que el campo dependiese del orden de proceso —la hoja 1 vería un tipo disponible y la hoja 900 no, sin motivo estructural—, justo lo que lo inutilizaría como descriptor de población (corregido al fijar APIs, 2026-09-15; los topes siguen operando en la construcción del corpus). | Solo la estructural (no dice qué se pudo aplicar) o solo la realizable (mezcla estructura con cobertura de despensa y varía con la semilla y el tope de reuso, así que la población que ellos comparan cambiaría con *nuestros* déficits). |
| **D2** | **Pasada de sondeo y construcción exacta**: una pasada determinista previa mide, por hoja, qué tipos cambian de verdad su TEXTO; el sorteo de dosis extrae solo de ese conjunto verificado, así que *k* planificadas = *k* aplicadas siempre. | Sobre-planificar y clasificar por count realizado (celdas 4–5 cortas, escaleras incompletas de forma impredecible) o el híbrido (sin garantía). |
| **D3** | `template_paraphrase` y `reorder` **restringidos al campo TEXTO** (`--texto-fields-only`), y `template_paraphrase` cuenta **una** modificación, no dos. | El conteo de STACKED (RESUMEN + TEXTO = 2 aplicadas) haría que `dose_3` entregase 4. |
| **D4** | **Escalera anidada**: `types(dose_k) ⊂ types(dose_{k+1})`; entre peldaños consecutivos cambia exactamente una modificación añadida. | Sorteos independientes por peldaño (la pendiente mezcla dosis con composición, el confundido del que huyen) o anidada + réplica independiente (+20 % de ítems por una comprobación de robustez que no piden). |
| **D5** | **Fondo común de hojas**: el sondeo mide el reparto de tipos admitidos por hoja y se elige la **mayor profundidad *d* que aún deje ≥600 hojas, con *d* ≥ 6**; esas hojas recorren la escalera completa 1→5. | 600 hojas con ≥5 admitidos (en una hoja de exactamente 5 el count 5 no tiene sorteo: composición determinada, el confundido reaparece en la celda que más importa) o las 5 000 hojas con escalera hasta `min(5, admitidos)` (la celda de count 5 la copan las hojas de repertorio grande: selección por riqueza estructural). |
| **D6** | **Se entregan los dos ficheros**: la escalera (~3 000) y el sondeo completo como conjunto de efectos aislados por hoja (~4 000–5 000). | Solo la escalera: H4 se estimaría contra el SINGLE ya entregado, que cubre ~1 tipo por hoja, así que la suma de efectos aislados seguiría siendo entre-hojas. |

*d* no se fija en este spec a propósito: es una medición que todavía no tenemos, y
el proxy disponible —el reparto de aplicadas en STACKED (`2:1, 3:1216, 4:877,
5:1484, 6:1138, 7:237, 8:45`, media 4.69)— infla el conteo porque cuenta
`template_paraphrase` dos veces e incluye cambios solo-RESUMEN. Queda escrita la
política; el número lo rellena el sondeo y se documenta en el informe.

## 3. Arquitectura

`run_corpus(stage2_json, plan, …)` recibe el plan como parámetro, así que el
costurón de inserción ya existe: un planificador nuevo produce `PlannedVariant`s
y el emisor no se toca para planificar.

```
inventario compartido 5 000 hojas --+
despensa aprobada (menus OE) -------+
                                    |
                                    v
  PRE-FILTRO estructural      applicable_types[hoja] sin renderizar -> candidatas C
    (sin render, sin LLM)           |  |applicable| >= 6, tope ~1 500 hojas
                                    v
  PASADA 1  probe_singles     una variante por (hoja, tipo admitido), campo TEXTO
    (sobre C)                       |  --require-texto-changed
                                    v
            available_types[hoja]  -->  fondo L = mayor d con >=600 hojas (d >= 6)
                                    |
                                    v
  PASADA 2  dose_1..dose_5    prefijos anidados del orden por hoja, sobre L
```

El pre-filtro existe por coste: sondear las 5 000 hojas serían ~30 000–45 000
renders, mientras que el fondo final solo necesita ~600–1 000. El filtro es
**estructural** (D1, `applicable_types`), así que no consume renders y no puede
sesgar el fondo por nada que dependa de la despensa o de la semilla; el tope de
~1 500 candidatas deja holgura para las hojas cuya admisión estructural no se
confirma al renderizar.

La pasada 1 no es andamiaje: su salida, **restringida al fondo L**, es el segundo
entregable (D6) — ~600–1 000 hojas × ~6–7 tipos ≈ 4 000–5 000 ítems aislados. Lo
sondeado fuera de L se descarta (queda en el informe como recuento, no como
entrega).

### Capacidad de despensa (medida, 2026-09-15)

| tipo | reescrituras aprobadas | capacidad por condición (`cap=20`) |
|---|---|---|
| `template_paraphrase` | 3 166 | 63 320 |
| `reorder` | 450 | 9 000 |
| `synonym_label` | 423 | 8 460 |
| `expansion` | 421 | 8 420 |
| `paraphrase` | 385 | 7 700 |
| `unit_conversion` | 254 | 5 080 |
| `compression` | 145 | 2 900 |
| `unit_expansion` | 138 | 2 760 |
| `num_to_text` | 114 | 2 280 |

Los topes de reuso se reinician en cada condición, así que `dose_5` con 600 ítems
necesita ~333 usos por tipo: **la capacidad no ata**. Lo que ata es la
compatibilidad por hoja, que es justo lo que mide el sondeo.

## 4. Componentes

| Fichero | Cambio |
|---|---|
| `src/synthetic/dose_ladder.py` | **Nuevo** (~250 líneas): plan de sondeo, aplicabilidad por hoja, orden anidado balanceado, plan de dosis. Módulo aparte porque meterlo en `corpus_sampler.py` lo llevaría de 938 a ~1 200 líneas y mezclaría dos políticas de selección que no comparten nada salvo el tipo `PlannedVariant`. |
| `src/synthetic/corpus_sampler.py` | Exponer `is_compatible()` (hoy `_compatible`, privado) y blindar `_condition_type`, que asume prefijo `single_` y devolvería basura ante `dose_3`. |
| `src/synthetic/corpus_driver.py` | `type_presence` trata `dose_*` como `all_combined`; si el count aplicado != *k*, **levanta** en vez de descartar. |
| `configs/synthetic/variant_budgets_OE_probe.yaml` | **Nuevo**: sondeo exhaustivo por hoja sobre las candidatas del pre-filtro (umbral estructural 6, tope 1 500). |
| `configs/synthetic/variant_budgets_OE_dose.yaml` | **Nuevo**: `dose_1..dose_5`, **≥600 ítems por celda (3 000 en total)**, `reuse_cap` heredado de los corpora OE (`num_to_text`/`unit_expansion`/`unit_conversion` = 20). |
| `scripts/build_dose_ladder.py` | **Nuevo**: orquesta las dos pasadas, selecciona *d*, emite el sidecar de aplicabilidad. |
| `scripts/package_for_retrieval.py` | Extender con `--dose/--probe/--applicability`: añade los dos campos de D1 y emite `provenance.json` + `MANIFEST.md` con SHA-256 por fichero (§6 de la petición). |
| `docs/synthetic/OE_dose_report.md` | **Nuevo**: informe de celdas, presencia por tipo y count, profundidad admitida, *d* elegido, déficits, salvedad de §8. |

### Orden anidado y equilibrio

El orden de tipos de cada hoja es determinista a partir de la hoja
(`random.Random(seed ^ zlib.crc32(leaf_item_key))` — hash estable, nunca el
`hash()` interno, que rompe la determinación entre procesos), pero las posiciones
se asignan con un barrido codicioso *el tipo menos usado primero* sobre las hojas
en orden fijo. Dos consecuencias:

1. dentro de cada celda de count los nueve tipos quedan tan parejos entre sí como
   permita la admisión (§3 de la petición);
2. el anidamiento sale garantizado **sin acoplar** las cinco condiciones: cada una
   recomputa el mismo orden por hoja y toma su prefijo de longitud *k*.

## 5. Esquema de entrega

Los campos de D1 **no** entran en `BC3CAT_Syn_items.parquet`: `ITEM_COLUMNS` está
congelado y fijado por los tests de la Fase G (G1/G2). Y la aplicabilidad es
propiedad de la **hoja**, no del ítem, así que su forma normalizada es un sidecar:

```
data/synthetic/handoff_OE/OE_leaf_applicability.jsonl
{"leaf_item_key": "OEA010aaba", "applicable_types": [...], "available_types": [...]}
```

El empaquetador hace el join por `original_key` y emite los dos campos en el JSON
de handoff, que es el esquema de su §5 — no el nuestro. Así G1/G2 siguen en verde
y no se duplica la misma lista en 8 000 registros.

Registro entregado (su §5, con la adición de D1):

```json
{"item_key": "<gold>_syn_<hash>", "parent_key": "OEA010$",
 "gold_item_key": "OEA010aaba",
 "parameters": {"A": "...", "B": null},
 "text": "...",
 "modification_types": ["..."], "modification_count": 3,
 "applicable_types": ["..."], "available_types": ["..."]}
```

`parent_key` va en todos los registros (es `concept_key`): ellos parten el
conjunto por concepto contra su propia división dev/test.

Ficheros: `OE_dose_texto.json` (~3 000), `OE_isolated_texto.json` (~4 000–5 000),
el sidecar, los dos `*_modifications.jsonl` y `MANIFEST.md` + `provenance.json`
con `{run_id, semilla, ruta de script, commit de bc3cat-dataset, SHA-256 por
fichero}`.

## 6. Errores: ruidosos, nunca silenciosos

- Count aplicado != *k* → excepción. El sondeo ya lo garantizó, así que una
  discrepancia es un bug del emisor, no un dato que filtrar.
- Hoja del fondo con menos de 5 tipos verificados → excepción al construir el fondo.
- Residuo de plantilla (`$L(...)`, `$A` sin resolver) → ya levanta hoy; se mantiene.
- `original_key` sin entrada en el sidecar → fallo al empaquetar, no campo vacío.

## 7. Verificación

`tests/synthetic/test_dose_ladder.py`:

- anidamiento: `types(dose_k)` es subconjunto de `types(dose_{k+1})` para toda
  hoja y todo *k*;
- count exacto: `modification_count == k` en todo ítem de `dose_k`;
- determinismo: dos construcciones byte a byte idénticas;
- equilibrio: dentro de cada celda de count, la presencia por tipo dentro de una cota;
- TEXTO cambiado en el 100 % de los ítems;
- escalera completa: cada hoja del fondo aparece en las cinco condiciones;
- join del sidecar: toda `original_key` entregada tiene sus dos listas.

Más las garantías ya existentes sobre el corpus: `cross_concept_audit.py
--template-level` (0 colisiones introducidas) y `dedup_corpus.py`.

## 8. Salvedad que hay que contestarles (su §3)

Piden que "cada tipo aparezca a tasas aproximadamente parejas **entre** counts".
Tal como está redactado es inalcanzable con cualquier escalera de dosis: si un
ítem de count *k* lleva *k* tipos de un repertorio de ~6 aplicables, la tasa de
presencia de cada tipo es *k*/6 por construcción y **crece** con la dosis. Es una
propiedad de la dosis, no un sesgo corregible.

Lo alcanzable —y lo que de verdad protege su inferencia— es que **dentro de cada
celda de count los nueve tipos estén parejos entre sí**, de modo que ningún tipo
esté sistemáticamente sobre-representado a una dosis concreta. Eso lo garantiza el
barrido codicioso de §4, y el informe lo documenta celda por celda.

A cambio obtienen dos cosas que no piden y que refuerzan H4 más que el equilibrio:
la **contención monótona** de D4 (contraste por pares entre peldaños consecutivos,
con una sola modificación de diferencia) y los **efectos aislados completos sobre
las mismas hojas** de D6 (la suma de efectos aislados deja de ser entre-hojas).
Además, el fondo común de D5 hace que las cinco celdas compartan exactamente la
misma población de hojas: el efecto de la dosis queda libre de selección por
dificultad de la hoja por construcción, no por ajuste estadístico.

## 9. Fuera de alcance

- No se toca `main` ni el pipeline v1 (`src/s0*.ipynb`).
- No se regeneran menús: cero LLM en esta entrega; la despensa OE está congelada.
- No se modifica el esquema congelado del parquet ni la API de `synthetic.loaders`.
- El port de la parte genérica (condición de dosis + aplicabilidad) a la rama
  `synthetic-generator` se hace **después** de congelar esta entrega, como un
  commit limpio con su actualización de `GENERATOR.md`.
