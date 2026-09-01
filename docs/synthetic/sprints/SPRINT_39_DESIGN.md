# Sprint 39 — Presupuestos + sampler determinista + driver de capítulo — Spec de diseño

| Campo | Valor |
|---|---|
| **Fecha** | 2026-08-31 (decisiones de César en sesión) |
| **Rama** | `synthetic` (nunca se fusiona a `main`) |
| **Entrada** | La despensa aprobada: `data/synthetic/menus/verdicts/{tipo}.jsonl` (2 609 A bajo rúbrica v2) |
| **Salida** | El corpus sintético piloto: `BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl` (esquema congelado en `HANDOFF.md`/Fase G) + informe de corpus |
| **Predecesor** | Sprint 38.7-B (revisión cerrada). **Sucesor:** Sprint 40 (escala a todo OBRA CIVIL), F4 (QA), experimentos en `bc3cat-retrieval`. |

## Decisiones de diseño (César, 2026-08-31)

1. **Tipos excluidos: `omission` y `new_param`.** Son los dos únicos que no preservan el
   contenido informativo (uno quita señal, el otro la inventa). El benchmark queda como
   *"el mismo ítem dicho de otra forma"*. Quedan 9 tipos / 1 931 reescrituras aprobadas.
2. **Sin apilamiento intermedio.** Se eliminan las condiciones `stacked_2…5+` del
   protocolo §6. Quedan **10 condiciones**: las 9 `single_<tipo>` y una única
   **`all_combined`** (una reescritura de *cada* tipo aplicable al ítem, todas a la vez).
3. **Tamaños por significación estadística** (margen ≈ error estándar binomial, peor caso):

| Condición | n objetivo | Reescrituras aprobadas | Margen 95 % (peor caso) |
|---|---|---|---|
| single · paraphrase | 1 000 | 420 | ±3,1 |
| single · expansion | 1 000 | 444 | ±3,1 |
| single · template_paraphrase | 1 000 | 610 | ±3,1 |
| single · synonym_label | 1 000 | 157 | ±3,1 |
| single · compression | 1 000 | 107 | ±3,1 |
| single · reorder | 1 000 | 109 | ±3,1 |
| single · num_to_text | 650 ⚠ | 33 | ±3,8 |
| single · unit_expansion | 650 ⚠ | 33 | ±3,8 |
| single · unit_conversion | 350 ⚠ | 18 | ±5,2 |
| **all_combined** (5–9 cambios/ítem) | **1 500** | todas | ±2,5 |
| **Total objetivo** | **≈ 9 150** | | |

   ⚠ Tipos finos: tope de **≤ 20 usos por reescritura única** (la precisión estadística no
   debe superar a la diversidad lingüística real). Cada rebanada publica su **nº de
   reescrituras únicas** junto al n — obligatorio en el informe y en la Data Card.
   Un déficit en una rebanada NO se reasigna a otros tipos (las rebanadas quedan limpias);
   simplemente se informa.

## Definición de ítem sintético

- **Un ítem = una hoja** (una combinación concreta de valores de parámetros de un
  concepto), con su `resumen` y `texto` re-renderizados tras aplicar las reescrituras.
- Cada ítem lleva: `item_key`, `original_key` (la hoja original — su "respuesta correcta"
  para el retriever), `variante_id`, `modification_types` (lista), `modification_count`,
  y la **condición** (`single_<tipo>` / `all_combined`).
- El release contiene **solo ítems sintéticos**; los originales viven en
  `OEB_{long,short}_norm.parquet` y se emparejan vía `original_key` (evaluación pareada).
- La tripleta `(item_key, original_key, variante_id)` es única (contrato HANDOFF).

## Método de generación (el paso a paso acordado)

1. **Aplicabilidad.** Una reescritura aplica a un concepto si su objetivo (`dedup_key`)
   tiene un `usage` en ese concepto (dato ya presente en los menús). El sampler
   pre-computa la matriz tipo × concepto de reescrituras aplicables.
2. **Reparto por concepto.** El n de cada condición se distribuye entre los 25 conceptos
   proporcionalmente a sus hojas aplicables (con mínimos para no dejar conceptos a cero),
   todo con **semilla fija** → corpus reproducible byte a byte.
3. **Por cada hueco:** elegir hoja (sin repetición dentro de la condición) → elegir
   reescritura(s): una del tipo en las `single`; en `all_combined`, una de **cada** tipo
   aplicable a esa hoja (5–9 típicamente), validadas contra las reglas de composición
   y aplicadas en el orden canónico **L1 → L2 → L3**.
4. **Aplicar en capa, no en texto:** modificar la tabla de parámetros / la fórmula del
   fragmento / la plantilla del concepto (funciones `layer_l1/l2/l3` existentes, con el
   adaptador `l2_repr` como en el pilotaje F1).
5. **Re-renderizar** con la tubería s03→s07 de siempre y extraer la hoja elegida.
6. **Filtros finales:** deduplicación exacta, descarte de no-ops (texto sintético ==
   original), verificación de render (0 placeholders sin resolver, 0 sentinelas).

## Informe de corpus (QA, sale con el release)

Por condición: n conseguido vs objetivo, nº de reescrituras únicas usadas, tasa de
reutilización máx/media, no-ops descartados, duplicados descartados, distancia media de
token al original (estilo `menu_profile`). Global: recuento por capa (L1/L2/L3),
por concepto, y verificación de unicidad de la tripleta.

## Métricas que este corpus habilita (en `bc3cat-retrieval`, para contexto)

Accuracy@1, Success@10, MRR y Prefix-Success@10 (funciones ya existentes en
`utils/evaluation.py`), evaluadas pareado (sintético vs su original) y rebanadas por las
10 condiciones → el mapa de fragilidad por tipo y la cifra titular de `all_combined`,
por familia de retriever.

## Fuera de alcance

- Escala a todo OBRA CIVIL (Sprint 40; misma maquinaria, más conceptos y despensa nueva).
- Regenerar los tipos finos para ensancharlos (candidato a Sprint 40).
- Los experimentos de retrieval (repo hermano; el contrato de carga ya está congelado).
- Las condiciones apiladas eliminadas: si algún día interesan, el sampler las readmite
  por configuración sin cambiar el esquema (el campo `modification_count` ya lo soporta).

## Riesgos

| Riesgo | Mitigación |
|---|---|
| Hojas insuficientes en conceptos pequeños para el n repartido | reparto proporcional a hojas + informe de déficit por rebanada |
| Reescrituras de un mismo eje colisionando en `all_combined` | reglas de composición + orden canónico; conflictos se saltan y se loguean |
| Pseudo-replicación en tipos finos | tope 20×, nº de reescrituras únicas publicado |
| No-ops silenciosos inflando n | filtro no-op + su tasa en el informe |
