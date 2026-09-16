# E3 — Conjunto de dosis equilibrado — Plan de implementación

> **Para trabajadores agénticos:** SUB-SKILL OBLIGATORIA: usa
> `superpowers:subagent-driven-development` (recomendado) o
> `superpowers:executing-plans` para ejecutar este plan tarea a tarea. Los pasos
> usan sintaxis de casilla (`- [ ]`) para el seguimiento.

**Objetivo:** generar y empaquetar el conjunto E3 —escalera de dosis anidada
(`dose_1..dose_5`) sobre un fondo común de hojas del corpus OE ya entregado, más
el conjunto de efectos aislados completos sobre esas mismas hojas— con
aplicabilidad declarada por hoja y procedencia firmada.

**Arquitectura:** un módulo planificador nuevo (`synthetic.dose_ladder`) que
produce `PlannedVariant`s y se los pasa al emisor existente
(`corpus_driver.run_corpus`, que ya recibe el plan como parámetro). Dos pasadas:
sondeo (una variante por hoja y tipo admitido, campo TEXTO) y escalera (prefijos
anidados del orden de tipos de cada hoja). Cero LLM: pura recombinación de la
despensa OE congelada.

**Stack:** Python 3.11, pandas/pyarrow, PyYAML, pytest. `PYTHONPATH=src`.
`bc3param` renderiza. Sin Ollama en toda la entrega.

**Spec de referencia:** [`E3_DOSE_DESIGN.md`](E3_DOSE_DESIGN.md) (commit `2eb2e5e`).
Las decisiones se citan como D1–D6.

---

## Contexto que el implementador necesita antes de empezar

Lee esto: ahorra media hora de arqueología.

**El pipeline sintético en 30 segundos.** La *despensa*
(`data/synthetic/menus_OE/` + `verdicts/`) contiene reescrituras aprobadas por
tipo de modificación. Un *plan* dice qué reescrituras aplicar a qué hoja. El
*emisor* (`corpus_driver.run_corpus`) renderiza el plan con `bc3param` y escribe
`BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl` + un informe QA.

**Los tipos.** Nueve tipos admitidos, en `synthetic.taxonomy.ModificationType`:
`paraphrase`, `expansion`, `compression` (L2, fragmentos de texto condicionales);
`synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`,
`abbrev_expansion`, `code_expansion` (L1, valores de parámetro); `reorder`,
`template_paraphrase` (L3, plantillas). `omission` y `new_param` están excluidos
(`pantry.EXCLUDED_TYPES`). La tupla `corpus_sampler.NINE_TYPES` es el orden
canónico y **no incluye** `abbrev_expansion` ni `code_expansion` (sin
aprobaciones en OE); usa `NINE_TYPES` siempre, nunca `list(ModificationType)`.

**APIs que vas a usar tal cual** (no las cambies):

```python
# synthetic.pantry
load_pantry(menus_dir: Path) -> Pantry
Pantry.by_type: dict[ModificationType, tuple[ApprovedRewrite, ...]]
Pantry.for_concept(concept_key: str) -> dict[ModificationType, tuple[ApprovedRewrite, ...]]
ApprovedRewrite(mtype, dedup_key: tuple, canonical: str, candidate_index: int,
                payload: dict, usages: tuple[Usage, ...])
ApprovedRewrite.uid -> str          # f"{mtype.value}:{canonical}:{candidate_index}"

# synthetic.corpus_sampler
LeafInventory(leaves_by_concept: Mapping[str, Iterable])   # (key, text[, axis_values])
LeafInventory.concepts() / .leaves(concept) / .text(leaf) / .axis_values(leaf)
leaf_inventory_from_frames(long_df, short_df) -> LeafInventory
PlannedVariant(condition: str, concept_key: str, leaf_item_key: str,
               rewrites: tuple[ApprovedRewrite, ...])
Budgets(seed: int, targets: Mapping[str, int], reuse_cap: Mapping[str, int])

# synthetic.target_scanner
scan_chapter(stage_json: dict, *, concept_filter=None) -> ChapterInventory
ChapterInventory.by_type: dict[ModificationType, tuple[UniqueTarget, ...]]
UniqueTarget(dedup_key: tuple, canonical: str, usages: tuple[TargetUsage, ...])
TargetUsage.concept_key: str

# synthetic.corpus_driver
run_corpus(stage2_json: dict, plan: Sequence[PlannedVariant], *, out_dir=None,
           report_path=None, budgets=None, workers=None,
           require_texto_changed=False) -> CorpusRunStats
```

**Formas de `dedup_key` por familia** (las fija `target_scanner`, y
`ApprovedRewrite` las hereda): L1 → `(axis_label_norm, value_norm)`;
L2 → `(fragment_norm,)`; L3 → `(field, template_norm)` con `field` ∈
`{"RESUMEN", "TEXTO"}`. Esta última es la que permite la restricción a TEXTO de D3.

**Determinismo, no negociable.** Nunca uses `hash()` de Python para derivar una
semilla: está salado por proceso y rompería la reproducibilidad entre
ejecuciones. El patrón del repo es
`random.Random(seed ^ zlib.crc32(clave.encode("utf-8")))`. Toda iteración sobre
conjuntos o diccionarios va ordenada (`sorted(...)`).

**Rutas de datos reales** (ya existen en el disco, rama `synthetic`):

```
data/synthetic/menus_OE/                              despensa + verdicts
data/synthetic/processed_OE/OE_target_long.parquet     pool de targets deduplicado (texto)
data/synthetic/processed_OE/OE_target_short.parquet    idem (resumen)
data/synthetic/processed_OE/OE_ablation_inventory_long.parquet    muestreo compartido 5 000
data/synthetic/processed_OE/OE_ablation_inventory_short.parquet
data/synthetic/intermediate/OE_2026_stage.json         stage-2 (ejes + plantillas)
```

Si `OE_2026_stage.json` no está con ese nombre exacto, localiza el stage JSON del
capítulo OE con `ls data/synthetic/intermediate/` y **usa el que el informe
`docs/synthetic/OE_corpus_report.md` cite como entrada**; no inventes uno.

**Cómo correr los tests:** `python -m pytest tests/synthetic -q` desde la raíz
(`tests/synthetic/conftest.py` ya inserta `src/` en `sys.path`). Los tests de
este plan son herméticos: fixtures diminutas a mano, sin parquet real, sin LLM,
sin `bc3param`.

**Diseño de tests que se espera aquí.** No compruebes que el código hace lo que
hace; comprueba las **propiedades** que el spec promete: anidamiento, count
exacto, determinismo, equilibrio, población común. Un test que solo reproduce la
implementación no detecta una regresión de diseño.

---

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/synthetic/dose_ladder.py` | **Nuevo.** Todo el planificador E3: aplicabilidad estructural y realizable por hoja, presupuestos de dosis, plan de sondeo, orden anidado equilibrado, selección del fondo, plan de dosis. Única responsabilidad: *decidir qué se genera*. No renderiza, no escribe. |
| `src/synthetic/corpus_sampler.py` | **Modificar.** Tres añadidos pequeños para que `dose_ladder` no importe nada privado: `is_compatible()` público, `leaf_inventory_from_frames(..., text_field=...)` y un guardián en `_condition_type`. |
| `src/synthetic/corpus_driver.py` | **Modificar.** Reconocer las familias `dose_*` / `probe_*` en el recuento de presencia por tipo, y afirmar el count exacto. |
| `configs/synthetic/variant_budgets_OE_probe.yaml` | **Nuevo.** Parámetros del sondeo. |
| `configs/synthetic/variant_budgets_OE_dose.yaml` | **Nuevo.** Parámetros de la escalera. |
| `scripts/build_dose_ladder.py` | **Nuevo.** Orquestación de las dos pasadas + sidecar de aplicabilidad + informe. Es el único fichero que hace E/S de la generación. |
| `scripts/package_for_retrieval.py` | **Modificar.** Banderas `--dose/--probe/--applicability`, los dos campos nuevos, `provenance.json` y `MANIFEST.md` con SHA-256. |
| `tests/synthetic/test_dose_ladder.py` | **Nuevo.** Propiedades del planificador. |
| `tests/synthetic/test_dose_packaging.py` | **Nuevo.** Propiedades del empaquetado (join del sidecar, campos, procedencia). |
| `docs/synthetic/OE_dose_report.md` | **Generado** por el script en la tarea 13. |

`dose_ladder.py` va aparte y no dentro de `corpus_sampler.py` (938 líneas) porque
son dos políticas de selección que no comparten nada salvo el tipo
`PlannedVariant`: fundirlas daría un fichero de ~1 200 líneas con dos regímenes
de sorteo distintos conviviendo.

---

## Notas para quien revise las tareas (evitan re-plantear lo ya decidido)

- **Imports «sin usar» a propósito.** Tanto `src/synthetic/dose_ladder.py` como
  `tests/synthetic/test_dose_ladder.py` importan nombres que la tarea en curso
  todavía no usa: son para las tareas siguientes, que extienden esos mismos dos
  ficheros. No los quites; quitarlos solo obliga a re-añadirlos una o dos tareas
  después.
- **Fuente única de las familias de tipos.** `corpus_sampler` expone
  `L1_VALUE_TYPES` (alias público de su conjunto privado, añadido en la tarea 2
  tras la revisión): `dose_ladder` lo importa y **no** mantiene una copia. Si
  alguna tarea futura necesita clasificar familias, importa, no copies.
- **Docstrings en inglés**, español en `docs/` y commits.

## Tres refinamientos de diseño fijados al escribir este plan

Van aquí porque cambian el código y el spec no los pinaba:

1. **La compatibilidad se evalúa contra el TEXTO solo, no contra el texto
   combinado.** `leaf_inventory_from_frames` concatena `resumen + " " + texto`,
   así que una reescritura cuya superficie solo aparece en el resumen se juzga
   compatible y luego el emisor la descarta por TEXTO inalterado. Como la entrega
   es texto-a-texto (consulta = TEXTO modificado), la planificación usa una
   inventario de solo-TEXTO. Sin esto, la garantía de D2 (*k* planificadas = *k*
   aplicadas) no se sostiene.
2. **Los topes de reuso son por ejecución, no por condición.** En el muestreador
   se reinician en cada condición; aquí las cinco condiciones comparten hoja y se
   construyen juntas, así que un contador único es la única semántica coherente.
   Holgura comprobada: 600 hojas × (1+2+3+4+5) = 9 000 ranuras ÷ 9 tipos ≈ 1 000
   usos por tipo, contra 2 280 de capacidad del tipo más fino (`num_to_text`).
3. **La escalera se construye atómicamente por hoja, con reserva.** Si un peldaño
   de una hoja no se puede construir (sus candidatas compatibles están agotadas
   por el tope), se revierte *toda* la escalera de esa hoja y se pasa a la
   siguiente candidata de la reserva. Una escalera parcial rompería la población
   común de D5, que es el motivo de ser del fondo.

---

## Tarea 1: Costuras públicas en `corpus_sampler`

**Ficheros:**
- Modificar: `src/synthetic/corpus_sampler.py` (`__all__`, `_condition_type`, `leaf_inventory_from_frames`)
- Test: `tests/synthetic/test_corpus_sampler.py`

- [ ] **Paso 1: Escribe los tests que fallan**

Añade al final de `tests/synthetic/test_corpus_sampler.py`:

```python
def test_is_compatible_is_public_and_matches_private():
    from synthetic.corpus_sampler import is_compatible
    r = _rewrite(ModificationType.NUM_TO_TEXT, "n-alpha")
    assert is_compatible(r, TOY_TEXT, ()) is True
    assert is_compatible(r, "texto sin la superficie", ()) is False


def test_condition_type_rejects_unknown_family():
    from synthetic.corpus_sampler import _condition_type
    with pytest.raises(ValueError, match="condition_unknown"):
        _condition_type("dose_3")


def test_inventory_text_field_texto_excludes_resumen():
    import pandas as pd
    long_df = pd.DataFrame({
        "item_key": ["C1aa"], "parent_key": ["C1$"], "text": ["solo-texto"],
    })
    short_df = pd.DataFrame({
        "item_key": ["C1aa"], "parent_key": ["C1$"], "text": ["solo-resumen"],
    })
    from synthetic.corpus_sampler import leaf_inventory_from_frames
    combined = leaf_inventory_from_frames(long_df, short_df)
    assert combined.text("C1aa") == "solo-resumen solo-texto"
    texto_only = leaf_inventory_from_frames(long_df, short_df, text_field="texto")
    assert texto_only.text("C1aa") == "solo-texto"
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_corpus_sampler.py -q -k "is_public or unknown_family or text_field"`
Esperado: 3 FAILED — `ImportError: cannot import name 'is_compatible'`,
`ValueError` no levantada (hoy `_condition_type("dose_3")` levanta
`ValueError: 'dose_3' is not a valid ModificationType`, con otro mensaje),
`TypeError: unexpected keyword argument 'text_field'`.

- [ ] **Paso 3: Implementa las tres costuras**

En `src/synthetic/corpus_sampler.py`, añade `"is_compatible"` a `__all__` y, tras
la definición de `_compatible`:

```python
#: Public alias — `dose_ladder` is a second, legitimate consumer of the
#: leaf<->rewrite compatibility rule; it must not reimplement it.
is_compatible = _compatible
```

Sustituye `_condition_type` por:

```python
def _condition_type(condition: str) -> ModificationType:
    """The modification type a ``single_<type>`` condition isolates.

    Fails loud on any other condition family (``dose_*``, ``probe_*``): those
    are planned by `dose_ladder`, which never routes through here, so reaching
    this with one of them is a wiring bug, not a missing feature.
    """
    if not condition.startswith(_SINGLE_PREFIX):
        raise ValueError(
            f"condition_unknown: {condition!r} is not a single_<type> condition"
        )
    return ModificationType(condition[len(_SINGLE_PREFIX):])
```

En `leaf_inventory_from_frames`, cambia la firma y la construcción del texto:

```python
def leaf_inventory_from_frames(long_df, short_df, *, text_field: str = "combined") -> LeafInventory:
    """The real-data loader: join the long (texto) and short (resumen)
    parquets on ``item_key`` and build the inventory with each leaf's
    original text plus its selected `(axis_label, value)` pairs (from the
    long frame's ``parameters`` column, when present). Fails loud on a leaf
    missing from the short frame or on any concept-rule violation (see
    :func:`_check_parent_rule`).

    ``text_field`` selects the surface compatibility is judged against:
    ``"combined"`` (default, ``resumen + " " + texto``) or ``"texto"`` — the
    latter for TEXTO-only corpora, where a rewrite whose surface appears only
    in the resumen must NOT count as compatible.
    """
    if text_field not in ("combined", "texto"):
        raise ValueError(
            f"inventory_invalid: text_field must be 'combined' or 'texto', "
            f"got {text_field!r}"
        )
```

y, dentro del bucle, sustituye el `f"{resumen} {texto}"` por:

```python
            (
                item_key,
                texto if text_field == "texto" else f"{resumen} {texto}",
                _axis_value_pairs(params_by_key.get(item_key)),
            )
```

(La comprobación de que el leaf está en el frame corto se mantiene intacta:
sigue validando la integridad del par aunque el resumen no se use como texto.)

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_corpus_sampler.py -q`
Esperado: PASS, incluidos los ~20 tests previos del fichero (la firma nueva es
retrocompatible: `text_field` es keyword-only con el valor de hoy).

Ejecuta también: `python -m pytest tests/synthetic -q`
Esperado: PASS. Si `test_corpus_driver.py` falla por el mensaje nuevo de
`_condition_type`, es una expectativa que hay que actualizar, no un guardián que
haya que quitar.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/corpus_sampler.py tests/synthetic/test_corpus_sampler.py
git commit -m "synthetic: costuras públicas del muestreador para el planificador de dosis"
```

---

## Tarea 2: Andamiaje de `dose_ladder` y aplicabilidad estructural

**Ficheros:**
- Crear: `src/synthetic/dose_ladder.py`
- Crear: `tests/synthetic/test_dose_ladder.py`

D1, mitad estructural: los tipos que **la gramática** admite para una hoja,
independientemente de que la despensa tenga o no una reescritura aprobada.

La fuente estructural es `target_scanner.scan_chapter`, que enumera los
*targets* del capítulo por tipo — lo que existe en la gramática, antes de
cualquier propuesta del LLM. Un target es estructuralmente aplicable a una hoja
si es de su concepto y su superficie la selecciona esa hoja. Esa segunda
condición es **exactamente** la regla de compatibilidad que ya vive en
`is_compatible`, así que no se reimplementa: se envuelve el target en un
`ApprovedRewrite` sintético cuyo `payload["original"]` es la superficie que el
`dedup_key` ya lleva.

- [ ] **Paso 1: Escribe los tests que fallan**

Crea `tests/synthetic/test_dose_ladder.py`:

```python
"""E3 — tests herméticos de :mod:`synthetic.dose_ladder`.

Fixtures diminutas: 2 conceptos, hojas con pares (eje, valor) conocidos y una
despensa de juguete. Sin parquet real, sin LLM, sin bc3param.
"""
from __future__ import annotations

import pytest

from synthetic.corpus_sampler import LeafInventory
from synthetic.pantry import ApprovedRewrite, Pantry, Usage
from synthetic.target_scanner import ChapterInventory, TargetUsage, UniqueTarget
from synthetic.taxonomy import ModificationType

MT = ModificationType
C1, C2 = "C1$", "C2$"


def _target(dedup, concepts=(C1,)):
    return UniqueTarget(
        dedup_key=tuple(dedup),
        canonical=" / ".join(str(x) for x in dedup),
        usages=tuple(TargetUsage(c, None, "") for c in concepts),
    )


def _chapter_inventory(by_type):
    return ChapterInventory(concept_keys=(C1, C2), by_type=dict(by_type))


def test_structural_types_l1_requires_the_leaf_to_select_the_pair():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({
        MT.NUM_TO_TEXT: (_target(("N TUBOS", "5")),),
        MT.UNIT_CONVERSION: (_target(("SECCION", "150 mm2")),),
    })
    # the leaf selects N TUBOS=5 but not SECCION=150 mm2. The axis label must
    # match the dedup_key's case: both normalisers (corpus_sampler._norm_ws,
    # target_scanner._norm) fold whitespace only, never case, and in real data
    # both sides read the same catalogue label.
    got = structural_types(
        inv, C1, leaf_text="canalizacion de 5 tubos", leaf_axis_values=(("N TUBOS", "5"),),
    )
    assert got == frozenset({MT.NUM_TO_TEXT})


def test_structural_types_l3_applies_to_every_leaf():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({MT.REORDER: (_target(("TEXTO", "plantilla")),)})
    got = structural_types(inv, C1, leaf_text="cualquier cosa", leaf_axis_values=())
    assert got == frozenset({MT.REORDER})


def test_structural_types_ignores_other_concepts_and_excluded_types():
    from synthetic.dose_ladder import structural_types

    inv = _chapter_inventory({
        MT.REORDER: (_target(("TEXTO", "plantilla"), concepts=(C2,)),),
        MT.OMISSION: (_target(("TEXTO", "plantilla", "$L"), concepts=(C1,)),),
    })
    assert structural_types(inv, C1, leaf_text="x", leaf_axis_values=()) == frozenset()
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 3 FAILED — `ModuleNotFoundError: No module named 'synthetic.dose_ladder'`.

- [ ] **Paso 3: Crea el módulo con la aplicabilidad estructural**

Crea `src/synthetic/dose_ladder.py`:

> **Nota (aplicada en `1bfe4ea`).** El docstring de módulo va **en inglés**, como
> el de todos los módulos hermanos (`corpus_sampler`, `pantry`, `target_scanner`):
> el español es para `docs/` y los mensajes de commit. Lo mismo para el docstring
> del fichero de test. Vale para todas las tareas de este plan.

```python
"""E3 — balanced dose-ladder planner (spec: E3_DOSE_DESIGN.md).

Decides WHAT gets generated; it does not render and does not write. Produces
:class:`~synthetic.corpus_sampler.PlannedVariant`s that
:func:`~synthetic.corpus_driver.run_corpus` materialises.

Two condition families:

* ``probe_<type>`` — one variant per (leaf, admitted type) with a SINGLE
  modification, TEXTO field. Measures which types actually change each leaf's
  TEXTO, and, restricted to the leaf POOL, is the isolated-effects deliverable
  (D6). (The pool is the common set of leaves the ladder runs on — not the
  pantry, which is the stock of approved rewrites.)
* ``dose_1..dose_5`` — the nested ladder: ``types(dose_k)`` is the length-``k``
  prefix of the leaf's type order, so exactly one modification is added between
  consecutive rungs (D4).

Two notions of per-leaf applicability, both free of reuse caps (D1):

* :func:`structural_types` — the grammar admits the type. Comes from the
  chapter's *targets* (:func:`~synthetic.target_scanner.scan_chapter`), i.e.
  what exists before any LLM proposal.
* per-leaf AVAILABILITY is decided empirically, not statically: the probe pass
  renders one single-modification variant per (leaf, compatible type) and keeps
  those whose TEXTO actually changed. This module supplies the static half —
  :func:`compatible_rewrites` — and the build script turns probe survival into
  the delivered ``available_types`` (D1).

Determinism: same inputs -> same plan, byte for byte. Every seed derivation uses
``zlib.crc32`` (never ``hash()``, salted per process).
"""

from __future__ import annotations

import random
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

import yaml

from .corpus_sampler import (
    NINE_TYPES,
    Budgets,
    L1_VALUE_TYPES,
    LeafInventory,
    PlannedVariant,
    is_compatible,
)
from .pantry import ApprovedRewrite, Pantry
from .target_scanner import ChapterInventory
from .taxonomy import ModificationType

__all__ = [
    "LADDER_MAX",
    "DoseLadderError",
    "structural_types",
]

#: Rungs of the ladder: dose_1 .. dose_5 (their §1).
LADDER_MAX = 5

class DoseLadderError(RuntimeError):
    """A guarantee this module promises has been violated."""


def _surface(mtype: ModificationType, dedup_key: Sequence) -> str:
    """The reviewed surface form carried by a ``dedup_key``.

    L1: ``(axis, value)`` -> the value. L2: ``(fragment,)`` -> the fragment.
    L3: the template body, which `is_compatible` ignores anyway (L3 rewrites
    touch the shared template, so they surface in every leaf).
    """
    if mtype in L1_VALUE_TYPES and len(dedup_key) >= 2:
        return str(dedup_key[1])
    return str(dedup_key[0]) if dedup_key else ""


def _as_rewrite(mtype: ModificationType, dedup_key: Sequence) -> ApprovedRewrite:
    """Wrap a scanned target as a synthetic rewrite, so the ONE compatibility
    rule (`corpus_sampler.is_compatible`) judges structure too — no second
    implementation to drift out of sync."""
    return ApprovedRewrite(
        mtype=mtype,
        dedup_key=tuple(dedup_key),
        canonical="",
        candidate_index=-1,
        payload={"original": _surface(mtype, dedup_key)},
        usages=(),
    )


def structural_types(
    chapter_inventory: ChapterInventory,
    concept_key: str,
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> frozenset[ModificationType]:
    """The types the GRAMMAR admits for this leaf (D1, structural half).

    Independent of the pantry: a type counts as structurally applicable when
    the chapter scan found a target of that type in this leaf's concept whose
    surface the leaf selects. Only the nine admitted types are considered.
    """
    out: set[ModificationType] = set()
    for mtype in NINE_TYPES:
        for target in chapter_inventory.by_type.get(mtype, ()):
            if not any(u.concept_key == concept_key for u in target.usages):
                continue
            if is_compatible(
                _as_rewrite(mtype, target.dedup_key), leaf_text, leaf_axis_values
            ):
                out.add(mtype)
                break
    return frozenset(out)
```

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 3 passed.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — aplicabilidad estructural por hoja"
```

---

## Tarea 3: Compatibilidad por hoja (`compatible_rewrites`)

**Ficheros:**
- Modificar: `src/synthetic/dose_ladder.py`
- Test: `tests/synthetic/test_dose_ladder.py`

D1, mitad realizable: qué reescrituras **aprobadas y compatibles** admite la
hoja. Sin topes: el tope es contabilidad de la ejecución y haría que el
resultado dependiera del orden de proceso.

> **Corregido tras la revisión de la tarea 3 (commit `15fd4a9`).** El plan
> original añadía aquí también una función `available_types()`. Se eliminó por
> dos motivos, y la corrección vale para todo el plan:
>
> 1. **No la llama nadie.** Las tareas 5 y 9 usan `compatible_rewrites`
>    directamente, y el campo `available_types` que se entrega lo calcula
>    `_surviving_types()` en la tarea 11, leyendo qué ítems del sondeo
>    sobrevivieron.
> 2. **Era una trampa de nombres.** La función significaba «existe reescritura
>    compatible»; el campo entregado significa «existe reescritura compatible
>    **y cambia el TEXTO de esa hoja**», que es estrictamente más estrecho.
>    Cablear la primera donde toca la segunda entregaría en silencio un
>    superconjunto — justo el descriptor de población del que depende su §4.
>
> Además, `compatible_rewrites` recibe el concepto **ya resuelto**
> (`Pantry.for_concept(key)`) en vez de `(pantry, concept_key)`: el resultado
> solo depende del concepto, pero la función se llama una vez por HOJA, así que
> resolverlo dentro re-recorría la despensa entera (~5 900 reescrituras) para
> cada una de las ~1 500 hojas.

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/synthetic/test_dose_ladder.py`:

```python
def _rewrite(mtype, original, ci=0, concepts=(C1,), dedup=None):
    return ApprovedRewrite(
        mtype=mtype,
        dedup_key=tuple(dedup) if dedup else (original,),
        canonical=original,
        candidate_index=ci,
        payload={"original": original, "new": f"{original}-v{ci}"},
        usages=tuple(Usage(c, None) for c in concepts),
    )


def test_compatible_rewrites_keeps_only_the_compatible_ones():
    from synthetic.dose_ladder import compatible_rewrites

    pantry = Pantry(by_type={
        MT.PARAPHRASE: (_rewrite(MT.PARAPHRASE, "fragmento-a"),),
        MT.COMPRESSION: (_rewrite(MT.COMPRESSION, "ausente-del-texto"),),
    })
    applicable = pantry.for_concept(C1)
    got = compatible_rewrites(
        applicable, leaf_text="obra con fragmento-a de base", leaf_axis_values=(),
    )
    assert set(got) == {MT.PARAPHRASE}
    assert got[MT.PARAPHRASE] == (pantry.by_type[MT.PARAPHRASE][0],)


def test_compatible_rewrites_signature_is_cap_free():
    """A reuse cap must not enter this function: availability is a population
    descriptor, caps are per-run accounting. Assert the parameter set EXACTLY,
    so a future cap parameter under any name is caught."""
    from synthetic.dose_ladder import compatible_rewrites
    import inspect

    assert set(inspect.signature(compatible_rewrites).parameters) == {
        "applicable", "leaf_text", "leaf_axis_values",
    }
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k compatible_rewrites`
Esperado: 2 FAILED — `ImportError: cannot import name 'compatible_rewrites'`.

- [ ] **Paso 3: Implementa**

Añade a `src/synthetic/dose_ladder.py`:

```python
def compatible_rewrites(
    applicable: Mapping[ModificationType, Sequence[ApprovedRewrite]],
    leaf_text: str,
    leaf_axis_values: tuple[tuple[str, str], ...] = (),
) -> dict[ModificationType, tuple[ApprovedRewrite, ...]]:
    """Per type, the rewrites among ``applicable`` that are compatible with
    this leaf (cap-free), sorted by ``uid`` so downstream picking is
    deterministic.

    ``applicable`` is one concept's rewrites — ``Pantry.for_concept(key)``.
    It is taken already resolved because it depends only on the concept,
    while this function is called once per LEAF: resolving it here would
    re-walk the whole pantry for every leaf of the same concept.

    A type with no compatible rewrite is absent from the result — callers
    read the key set as "the types this leaf can take", so mapping it to an
    empty tuple would report it as available when it is not.
    """
    out: dict[ModificationType, tuple[ApprovedRewrite, ...]] = {}
    for mtype in NINE_TYPES:
        hits = tuple(sorted(
            (r for r in applicable.get(mtype, ())
             if is_compatible(r, leaf_text, leaf_axis_values)),
            key=lambda r: r.uid,
        ))
        if hits:
            out[mtype] = hits
    return out
```

Añade `"compatible_rewrites"` a `__all__`.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 5 passed.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — aplicabilidad realizable, libre de topes"
```

---

## Tarea 4: Presupuestos de dosis (`DoseBudgets`)

**Ficheros:**
- Modificar: `src/synthetic/dose_ladder.py`
- Test: `tests/synthetic/test_dose_ladder.py`

`corpus_sampler.load_budgets` exige que `targets` cubra **exactamente** las 10
condiciones del piloto, así que no sirve para `dose_*` y **no se toca** (su
validación estricta está fijada por tests). E3 lleva su propio cargador.

- [ ] **Paso 1: Escribe los tests que fallan**

```python
def test_load_dose_budgets_reads_and_validates(tmp_path):
    from synthetic.dose_ladder import load_dose_budgets

    p = tmp_path / "dose.yaml"
    p.write_text(
        "seed: 42\n"
        "per_count: 600\n"
        "structural_threshold: 6\n"
        "candidate_cap: 1500\n"
        "reuse_cap:\n"
        "  num_to_text: 20\n",
        encoding="utf-8",
    )
    b = load_dose_budgets(p)
    assert (b.seed, b.per_count, b.structural_threshold, b.candidate_cap) == (42, 600, 6, 1500)
    assert b.reuse_cap == {"num_to_text": 20}


def test_load_dose_budgets_rejects_a_threshold_below_the_ladder(tmp_path):
    from synthetic.dose_ladder import LADDER_MAX, load_dose_budgets

    p = tmp_path / "dose.yaml"
    p.write_text(
        f"seed: 42\nper_count: 10\nstructural_threshold: {LADDER_MAX - 1}\n"
        "candidate_cap: 100\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dose_budgets_invalid"):
        load_dose_budgets(p)


def test_load_dose_budgets_rejects_unknown_reuse_cap_type(tmp_path):
    from synthetic.dose_ladder import load_dose_budgets

    p = tmp_path / "dose.yaml"
    p.write_text(
        "seed: 42\nper_count: 10\nstructural_threshold: 6\ncandidate_cap: 100\n"
        "reuse_cap:\n  no_such_type: 5\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dose_budgets_invalid"):
        load_dose_budgets(p)


def test_dose_budgets_to_driver_budgets_has_one_target_per_rung():
    from synthetic.dose_ladder import LADDER_MAX, DoseBudgets

    b = DoseBudgets(seed=1, per_count=7, structural_threshold=6, candidate_cap=10,
                    reuse_cap={})
    drv = b.to_driver_budgets()
    assert drv.targets == {f"dose_{k}": 7 for k in range(1, LADDER_MAX + 1)}
    assert drv.seed == 1
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k budgets`
Esperado: 4 FAILED — `ImportError: cannot import name 'load_dose_budgets'`.

- [ ] **Paso 3: Implementa**

```python
@dataclass(frozen=True)
class DoseBudgets:
    """Validated E3 budgets.

    ``per_count`` items per rung (their §3 asks for >= 600);
    ``structural_threshold`` is the minimum number of STRUCTURALLY applicable
    types a leaf needs to enter the probe candidate set (D5 wants room to
    choose at rung 5, so it must exceed ``LADDER_MAX``); ``candidate_cap``
    bounds the probe's render cost.
    """

    seed: int
    per_count: int
    structural_threshold: int
    candidate_cap: int
    reuse_cap: Mapping[str, int]
    pool_min: Optional[int] = None

    @property
    def effective_pool_min(self) -> int:
        """Leaves the pool must reach: ``pool_min`` when given, else one leaf
        per rung item (the ladder uses the SAME leaves at every rung)."""
        return self.per_count if self.pool_min is None else self.pool_min

    def to_driver_budgets(self) -> Budgets:
        """Adapter for `run_corpus(budgets=...)`, which only reads
        ``targets``/``seed``/``reuse_cap`` to render the QA report."""
        return Budgets(
            seed=self.seed,
            targets={f"dose_{k}": self.per_count for k in range(1, LADDER_MAX + 1)},
            reuse_cap=dict(self.reuse_cap),
        )


def _positive_int(value: object, what: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(
            f"dose_budgets_invalid: {what} must be a positive int, got {value!r}"
        )
    return value


def load_dose_budgets(path: Path) -> DoseBudgets:
    """Read + validate the E3 budgets YAML. Fails loud
    (``ValueError("dose_budgets_invalid: ...")``)."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"dose_budgets_invalid: {Path(path).name} is not a mapping")

    seed = _positive_int(raw.get("seed"), "seed")
    per_count = _positive_int(raw.get("per_count"), "per_count")
    threshold = _positive_int(raw.get("structural_threshold"), "structural_threshold")
    candidate_cap = _positive_int(raw.get("candidate_cap"), "candidate_cap")
    if threshold <= LADDER_MAX:
        raise ValueError(
            f"dose_budgets_invalid: structural_threshold must exceed "
            f"LADDER_MAX={LADDER_MAX} so rung {LADDER_MAX} still has a choice "
            f"(D5), got {threshold}"
        )
    pool_min = raw.get("pool_min")
    if pool_min is not None:
        pool_min = _positive_int(pool_min, "pool_min")

    reuse_cap = raw.get("reuse_cap") or {}
    if not isinstance(reuse_cap, dict):
        raise ValueError("dose_budgets_invalid: reuse_cap is not a mapping")
    valid = {t.value for t in NINE_TYPES}
    for mtype, cap in reuse_cap.items():
        if mtype not in valid:
            raise ValueError(
                f"dose_budgets_invalid: reuse_cap type {mtype!r} is not one of "
                f"the nine admitted types"
            )
        _positive_int(cap, f"reuse_cap[{mtype}]")

    return DoseBudgets(
        seed=seed, per_count=per_count, structural_threshold=threshold,
        candidate_cap=candidate_cap, reuse_cap=dict(reuse_cap), pool_min=pool_min,
    )
```

Añade `"DoseBudgets"` y `"load_dose_budgets"` a `__all__`.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 9 passed.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — presupuestos E3 con validación propia"
```

---

## Tarea 5: Candidatas y plan de sondeo

**Ficheros:**
- Modificar: `src/synthetic/dose_ladder.py`
- Test: `tests/synthetic/test_dose_ladder.py`

El pre-filtro estructural (sin renders) y el plan de sondeo: una variante por
(hoja, tipo disponible), condición `probe_<type>`, una sola reescritura.

- [ ] **Paso 1: Escribe los tests que fallan**

```python
def _toy_setup():
    """2 conceptos; C1 con 3 hojas que admiten 3 tipos, C2 con 1 hoja que admite 1."""
    text = "obra frag-a frag-b tpl"
    inventory = LeafInventory({
        C1: [(f"C1a{i}", text, (("eje", "v"),)) for i in "abc"],
        C2: [("C2aa", "otra obra", ())],
    })
    pantry = Pantry(by_type={
        MT.PARAPHRASE: (_rewrite(MT.PARAPHRASE, "frag-a", concepts=(C1,)),),
        MT.COMPRESSION: (_rewrite(MT.COMPRESSION, "frag-b", concepts=(C1,)),),
        MT.REORDER: (
            _rewrite(MT.REORDER, "tpl", concepts=(C1,), dedup=("TEXTO", "tpl")),
            _rewrite(MT.REORDER, "tpl2", concepts=(C2,), dedup=("TEXTO", "tpl2")),
        ),
    })
    return inventory, pantry


def test_candidate_leaves_applies_the_structural_threshold_and_cap():
    from synthetic.dose_ladder import candidate_leaves

    inventory, _ = _toy_setup()
    inv = _chapter_inventory({
        MT.PARAPHRASE: (_target(("frag-a",)),),
        MT.COMPRESSION: (_target(("frag-b",)),),
        MT.REORDER: (_target(("TEXTO", "tpl")),),
    })
    got = candidate_leaves(inv, inventory, threshold=3, cap=2)
    assert got == ("C1aa", "C1ab")          # sorted, capped, C2 excluded (1 type)
    assert candidate_leaves(inv, inventory, threshold=4, cap=10) == ()


def test_build_probe_plan_is_one_single_modification_per_leaf_and_type():
    from synthetic.dose_ladder import build_probe_plan

    inventory, pantry = _toy_setup()
    plan = build_probe_plan(pantry, inventory, ("C1aa", "C1ab"))
    assert {p.condition for p in plan} == {
        "probe_paraphrase", "probe_compression", "probe_reorder",
    }
    assert all(len(p.rewrites) == 1 for p in plan)
    assert len(plan) == 6                    # 2 leaves x 3 types
    # a leaf never repeats within a condition
    for cond in {p.condition for p in plan}:
        leaves = [p.leaf_item_key for p in plan if p.condition == cond]
        assert len(leaves) == len(set(leaves))


def test_build_probe_plan_is_deterministic():
    from synthetic.dose_ladder import build_probe_plan

    inventory, pantry = _toy_setup()
    a = build_probe_plan(pantry, inventory, ("C1aa", "C1ab"))
    b = build_probe_plan(pantry, inventory, ("C1aa", "C1ab"))
    key = lambda pl: [(p.condition, p.leaf_item_key, tuple(r.uid for r in p.rewrites)) for p in pl]
    assert key(a) == key(b)
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k "candidate or probe"`
Esperado: 3 FAILED — `ImportError: cannot import name 'candidate_leaves'`.

- [ ] **Paso 3: Implementa**

```python
def _concept_of(inventory: LeafInventory) -> dict[str, str]:
    """``{leaf_item_key: concept_key}`` for the whole inventory."""
    return {
        leaf: concept
        for concept in inventory.concepts()
        for leaf in inventory.leaves(concept)
    }


def candidate_leaves(
    chapter_inventory: ChapterInventory,
    inventory: LeafInventory,
    *,
    threshold: int,
    cap: int,
) -> tuple[str, ...]:
    """Leaves worth probing: at least ``threshold`` STRUCTURALLY applicable
    types, capped at ``cap`` (deterministic, sorted by item key).

    The filter is structural on purpose (D5): it costs no renders and cannot
    bias the pool by anything that depends on the pantry or the seed.
    """
    picked: list[str] = []
    for leaf, concept in sorted(_concept_of(inventory).items()):
        types = structural_types(
            chapter_inventory, concept, inventory.text(leaf),
            inventory.axis_values(leaf),
        )
        if len(types) >= threshold:
            picked.append(leaf)
        if len(picked) >= cap:
            break
    return tuple(picked)


def _least_used(
    candidates: Sequence[ApprovedRewrite],
    cap: Optional[int],
    usage: Mapping[str, int],
    used_dedup: frozenset = frozenset(),
) -> Optional[ApprovedRewrite]:
    """Least-used-first pick honouring ``cap`` and the per-variant dedup set.

    ``None`` when every candidate is capped out or dedup-blocked. Ties break on
    ``uid`` so the pick is reproducible.
    """
    for rewrite in sorted(candidates, key=lambda r: (usage.get(r.uid, 0), r.uid)):
        if cap is not None and usage.get(rewrite.uid, 0) >= cap:
            continue
        if rewrite.dedup_key in used_dedup:
            continue
        return rewrite
    return None


def build_probe_plan(
    pantry: Pantry,
    inventory: LeafInventory,
    leaves: Sequence[str],
    *,
    reuse_cap: Optional[Mapping[str, int]] = None,
) -> tuple[PlannedVariant, ...]:
    """One single-modification variant per (leaf, available type).

    Condition ``probe_<type>``, so leaves stay unique within a condition and
    the driver's report breaks the probe down per type. Caps (when given) only
    throttle WHICH rewrite is picked; a type with every candidate capped out is
    skipped for that leaf and the deficit shows up in the report.
    """
    caps = dict(reuse_cap or {})
    concept_of = _concept_of(inventory)
    # `Pantry.for_concept` walks the whole pantry but its result depends only
    # on the concept, so resolve it once per concept rather than once per leaf.
    applicable: dict[str, dict] = {}
    usage: dict[str, int] = {}
    plan: list[PlannedVariant] = []
    for leaf in sorted(leaves):
        concept = concept_of[leaf]
        if concept not in applicable:
            applicable[concept] = pantry.for_concept(concept)
        by_type = compatible_rewrites(
            applicable[concept], inventory.text(leaf), inventory.axis_values(leaf),
        )
        for mtype in NINE_TYPES:
            cands = by_type.get(mtype)
            if not cands:
                continue
            pick = _least_used(cands, caps.get(mtype.value), usage)
            if pick is None:
                continue
            usage[pick.uid] = usage.get(pick.uid, 0) + 1
            plan.append(PlannedVariant(
                condition=f"probe_{mtype.value}", concept_key=concept,
                leaf_item_key=leaf, rewrites=(pick,),
            ))
    return tuple(plan)
```

Añade `"candidate_leaves"` y `"build_probe_plan"` a `__all__`.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 12 passed.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — pre-filtro estructural y plan de sondeo"
```

---

## Tarea 6: El emisor reconoce las familias nuevas

**Ficheros:**
- Modificar: `src/synthetic/corpus_driver.py:633-641` (recuento de presencia) y el bucle de emisión
- Test: `tests/synthetic/test_corpus_driver.py`

Dos cambios. El recuento de presencia por tipo hoy solo se lleva para
`all_combined`; las dosis lo necesitan igual (es lo que documenta el equilibrio
por celda). Y el count exacto de D2 debe **afirmarse**: si el sondeo verificó la
disponibilidad y el emisor aplica menos de *k*, eso es un bug, no un dato.

- [ ] **Paso 1: Escribe los tests que fallan**

Añade a `tests/synthetic/test_corpus_driver.py` (mira las fixtures del fichero y
reutiliza su `_stage_json()`/helpers; si su corrida mínima se apoya en un
`monkeypatch` del render, reutilízalo igual):

```python
def test_dose_conditions_are_counted_as_multi_type():
    from synthetic.corpus_driver import _counts_type_presence
    assert _counts_type_presence("all_combined") is True
    assert _counts_type_presence("dose_3") is True
    assert _counts_type_presence("single_reorder") is False
    assert _counts_type_presence("probe_reorder") is False


def test_dose_condition_expected_count_is_parsed():
    from synthetic.corpus_driver import _expected_applied_count
    assert _expected_applied_count("dose_4") == 4
    assert _expected_applied_count("all_combined") is None
    assert _expected_applied_count("single_reorder") is None
    assert _expected_applied_count("probe_num_to_text") == 1
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_corpus_driver.py -q -k "dose_conditions or expected_count"`
Esperado: 2 FAILED — `ImportError: cannot import name '_counts_type_presence'`.

- [ ] **Paso 3: Implementa**

En `src/synthetic/corpus_driver.py`, junto a `_ALL_COMBINED = "all_combined"`
(línea 120):

```python
_DOSE_PREFIX = "dose_"
_PROBE_PREFIX = "probe_"


def _counts_type_presence(condition: str) -> bool:
    """Whether per-type presence is worth tallying for this condition.

    True for the multi-type families — ``all_combined`` and the ``dose_*``
    rungs, where "which types rode this item" is the thing the QA report has
    to show. A single-modification condition's presence is its own count.
    """
    return condition == _ALL_COMBINED or condition.startswith(_DOSE_PREFIX)


def _expected_applied_count(condition: str) -> Optional[int]:
    """The exact number of APPLIED modifications this condition promises.

    ``dose_k`` -> k and ``probe_*`` -> 1 (E3 plans them from verified
    availability, so a shortfall is a bug — see D2). ``None`` where no exact
    promise exists (``all_combined`` stacks whatever applies; ``single_*``
    items are already dropped when their one modification no-ops).
    """
    if condition.startswith(_DOSE_PREFIX):
        return int(condition[len(_DOSE_PREFIX):])
    if condition.startswith(_PROBE_PREFIX):
        return 1
    return None
```

En el bucle de emisión, sustituye la condición del recuento de presencia
(`if planned.condition == _ALL_COMBINED:`) por:

```python
            if _counts_type_presence(planned.condition):
```

Y justo después de construir `modifications` (antes del `items.append(...)`),
añade la afirmación:

```python
        expected = _expected_applied_count(planned.condition)
        if expected is not None and len(modifications) != expected:
            raise ValueError(
                f"applied_count_mismatch: {planned.condition} on leaf "
                f"{leaf_key!r} applied {len(modifications)} modifications, "
                f"expected {expected}. E3 plans from verified availability, so "
                f"this is a planning/emission bug, not data to filter "
                f"(types planned: "
                f"{[r.mtype.value for r in planned.rewrites]})"
            )
```

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_corpus_driver.py -q`
Esperado: PASS (los tests previos del emisor siguen verdes: ninguna condición del
piloto entra en las familias nuevas, así que `expected` es `None` para todas
salvo las de E3).

Ejecuta: `python -m pytest tests/synthetic -q`
Esperado: PASS.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/corpus_driver.py tests/synthetic/test_corpus_driver.py
git commit -m "synthetic: el emisor reconoce dose_*/probe_* y afirma el count exacto"
```

---

## Tarea 7: Orden anidado equilibrado

**Ficheros:**
- Modificar: `src/synthetic/dose_ladder.py`
- Test: `tests/synthetic/test_dose_ladder.py`

El corazón de D4 + §3. El orden de tipos de cada hoja se sortea con la semilla de
la hoja, pero cada posición se rellena con el tipo **menos colocado en esa misma
posición** hasta ahora, así que las celdas quedan parejas sin romper el
anidamiento.

- [ ] **Paso 1: Escribe los tests que fallan**

```python
def test_nested_order_prefixes_are_the_rungs():
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(20)}
    order = nested_order(admitted, seed=42)
    for leaf, types in order.items():
        assert len(types) == LADDER_MAX
        assert len(set(types)) == LADDER_MAX            # no repeats
        assert set(types) <= admitted[leaf]
        for k in range(1, LADDER_MAX):
            assert set(types[:k]) < set(types[:k + 1])  # strictly nested


def test_nested_order_is_deterministic():
    from synthetic.dose_ladder import nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(20)}
    assert nested_order(admitted, seed=42) == nested_order(admitted, seed=42)
    assert nested_order(admitted, seed=43) != nested_order(admitted, seed=42)


def test_nested_order_balances_types_within_each_rung():
    """Their §3, achievable half: within a count cell no type may be
    systematically over-represented."""
    from synthetic.dose_ladder import LADDER_MAX, nested_order

    admitted = {f"L{i:03d}": frozenset(NINE_SUBSET) for i in range(180)}
    order = nested_order(admitted, seed=42)
    from collections import Counter
    for k in range(1, LADDER_MAX + 1):
        presence = Counter(t for types in order.values() for t in types[:k])
        # every admitted type present, and the spread within one item
        assert set(presence) == set(NINE_SUBSET)
        assert max(presence.values()) - min(presence.values()) <= 1


def test_nested_order_rejects_a_leaf_that_cannot_fill_the_ladder():
    from synthetic.dose_ladder import DoseLadderError, nested_order

    with pytest.raises(DoseLadderError, match="ladder_too_deep"):
        nested_order({"L1": frozenset(list(NINE_SUBSET)[:2])}, seed=42)
```

Y arriba, junto a las fixtures del fichero:

```python
NINE_SUBSET = (
    MT.PARAPHRASE, MT.EXPANSION, MT.TEMPLATE_PARAPHRASE, MT.SYNONYM_LABEL,
    MT.COMPRESSION, MT.REORDER,
)
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k nested`
Esperado: 4 FAILED — `ImportError: cannot import name 'nested_order'`.

- [ ] **Paso 3: Implementa**

```python
def nested_order(
    admitted: Mapping[str, frozenset],
    seed: int,
) -> dict[str, tuple[ModificationType, ...]]:
    """Per-leaf type order whose prefixes ARE the ladder rungs (D4).

    Position ``p`` of a leaf is filled with the type that the leaf admits, is
    not already placed for it, and has been placed at position ``p`` across the
    fewest leaves so far — ties broken by that leaf's own deterministic
    shuffle. Two properties follow:

    * ``types(dose_k)`` is the length-``k`` prefix, so consecutive rungs differ
      by exactly one added modification (D4);
    * within every rung the admitted types come out as even as admission
      allows (their §3, achievable half), because the greedy sweep equalises
      each position independently and a count cell is the union of positions
      ``1..k``.

    Raises :class:`DoseLadderError` for a leaf admitting fewer than
    ``LADDER_MAX`` types — the pool selection must have excluded it already.
    """
    per_position: list[Counter] = [Counter() for _ in range(LADDER_MAX)]
    order: dict[str, tuple[ModificationType, ...]] = {}
    for leaf in sorted(admitted):
        types = admitted[leaf]
        if len(types) < LADDER_MAX:
            raise DoseLadderError(
                f"ladder_too_deep: leaf {leaf!r} admits {len(types)} types, "
                f"needs {LADDER_MAX} — it should not be in the pool"
            )
        rng = random.Random(seed ^ zlib.crc32(leaf.encode("utf-8")))
        shuffled = rng.sample(sorted(types, key=lambda t: t.value), len(types))
        rank = {t: i for i, t in enumerate(shuffled)}
        chosen: list[ModificationType] = []
        for position in range(LADDER_MAX):
            remaining = [t for t in shuffled if t not in chosen]
            pick = min(remaining, key=lambda t: (per_position[position][t], rank[t]))
            chosen.append(pick)
            per_position[position][pick] += 1
        order[leaf] = tuple(chosen)
    return order
```

Añade `"nested_order"` a `__all__`.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 16 passed.

Si `test_nested_order_balances_types_within_each_rung` falla por 1 unidad con
180 hojas y 6 tipos (180 no es múltiplo de 6 en las posiciones altas), **no
relajes la cota sin pensar**: comprueba primero el reparto real
(`print(presence)`), porque una desviación > 1 indica que el barrido no está
equilibrando y eso sí es un fallo de diseño.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — orden anidado equilibrado por posicion"
```

---

## Tarea 8: Selección del fondo común

**Ficheros:**
- Modificar: `src/synthetic/dose_ladder.py`
- Test: `tests/synthetic/test_dose_ladder.py`

D5: la mayor profundidad *d* que aún deje suficientes hojas, con *d* >
`LADDER_MAX`. El valor lo decide la medición, no el spec.

- [ ] **Paso 1: Escribe los tests que fallan**

```python
def test_select_pool_takes_the_deepest_level_that_still_fills():
    from synthetic.dose_ladder import select_pool

    avail = {}
    for i in range(10):                      # 10 leaves admit 8 types
        avail[f"D8_{i:02d}"] = frozenset(list(NINE_SUBSET)[:6]) | {MT.NUM_TO_TEXT, MT.UNIT_EXPANSION}
    for i in range(50):                      # 50 more admit 6
        avail[f"D6_{i:02d}"] = frozenset(NINE_SUBSET)
    depth, pool = select_pool(avail, pool_min=40, min_depth=6)
    assert depth == 6                        # 8 would only give 10 leaves
    assert len(pool) == 40
    assert pool == tuple(sorted(pool))       # deterministic, sorted


def test_select_pool_prefers_depth_when_supply_allows():
    from synthetic.dose_ladder import select_pool

    avail = {
        f"D8_{i:02d}": frozenset(list(NINE_SUBSET)[:6]) | {MT.NUM_TO_TEXT, MT.UNIT_EXPANSION}
        for i in range(50)
    }
    depth, pool = select_pool(avail, pool_min=40, min_depth=6)
    assert depth == 8


def test_select_pool_fails_loud_when_no_depth_fills():
    from synthetic.dose_ladder import DoseLadderError, select_pool

    avail = {f"L{i}": frozenset(NINE_SUBSET) for i in range(5)}
    with pytest.raises(DoseLadderError, match="pool_too_small"):
        select_pool(avail, pool_min=600, min_depth=6)


def test_depth_histogram_reports_the_distribution():
    from synthetic.dose_ladder import depth_histogram

    avail = {"a": frozenset(NINE_SUBSET), "b": frozenset(list(NINE_SUBSET)[:3])}
    assert depth_histogram(avail) == {3: 1, 6: 1}
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k "pool or histogram"`
Esperado: 4 FAILED — `ImportError: cannot import name 'select_pool'`.

- [ ] **Paso 3: Implementa**

```python
def depth_histogram(available: Mapping[str, frozenset]) -> dict[int, int]:
    """``{number of available types: number of leaves}`` — the measurement D5
    defers to, and a row of the corpus report."""
    return dict(sorted(Counter(len(v) for v in available.values()).items()))


def select_pool(
    available: Mapping[str, frozenset],
    *,
    pool_min: int,
    min_depth: int,
) -> tuple[int, tuple[str, ...]]:
    """The common leaf pool (D5): ``(depth, leaves)``.

    Picks the DEEPEST ``d >= min_depth`` for which at least ``pool_min`` leaves
    admit ``d`` types, then takes the first ``pool_min`` of them in sorted
    order. All five rungs run on these same leaves, so the count cells share
    one population and the dose effect carries no leaf-difficulty selection.

    Raises :class:`DoseLadderError` when no depth fills the pool — silently
    dropping to a shallower ladder would void D5's guarantee.
    """
    if min_depth <= LADDER_MAX:
        raise DoseLadderError(
            f"min_depth_too_shallow: {min_depth} <= LADDER_MAX={LADDER_MAX} "
            f"would leave rung {LADDER_MAX} with no choice of composition (D5)"
        )
    histogram = depth_histogram(available)
    deepest = max(histogram, default=0)
    for depth in range(deepest, min_depth - 1, -1):
        eligible = tuple(sorted(k for k, v in available.items() if len(v) >= depth))
        if len(eligible) >= pool_min:
            return depth, eligible[:pool_min]
    raise DoseLadderError(
        f"pool_too_small: no depth >= {min_depth} yields {pool_min}+ leaves; "
        f"depth histogram = {histogram}"
    )
```

Añade `"select_pool"` y `"depth_histogram"` a `__all__`.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 20 passed.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — seleccion del fondo comun por profundidad"
```

---

## Tarea 9: Plan de dosis atómico por hoja

**Ficheros:**
- Modificar: `src/synthetic/dose_ladder.py`
- Test: `tests/synthetic/test_dose_ladder.py`

Refinamiento 3: las cinco escaleras de una hoja se construyen juntas; si un
peldaño no sale, se revierte la hoja entera y se pasa a la reserva.

- [ ] **Paso 1: Escribe los tests que fallan**

```python
def _ladder_setup(n_leaves=12):
    """n hojas de un concepto, cada una compatible con 6 tipos (2 reescrituras/tipo)."""
    surfaces = {t: f"s-{t.value}" for t in NINE_SUBSET}
    text = "obra " + " ".join(surfaces.values())
    inventory = LeafInventory({C1: [(f"C1{i:03d}", text, ()) for i in range(n_leaves)]})
    pantry = Pantry(by_type={
        t: tuple(
            _rewrite(t, surfaces[t], ci=ci, concepts=(C1,), dedup=(f"{t.value}-{ci}",))
            for ci in range(2)
        )
        for t in NINE_SUBSET
    })
    return inventory, pantry


def test_build_dose_plan_has_exact_counts_and_nesting():
    from synthetic.dose_ladder import (
        LADDER_MAX, build_dose_plan, nested_order,
    )

    inventory, pantry = _ladder_setup()
    pool = tuple(f"C1{i:03d}" for i in range(10))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    plan = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)

    assert len(plan) == 10 * LADDER_MAX
    by_leaf = {}
    for p in plan:
        k = int(p.condition[len("dose_"):])
        assert len(p.rewrites) == k                      # exact count
        by_leaf.setdefault(p.leaf_item_key, {})[k] = {r.mtype for r in p.rewrites}
    for leaf, rungs in by_leaf.items():
        assert set(rungs) == set(range(1, LADDER_MAX + 1))   # complete ladder
        for k in range(1, LADDER_MAX):
            assert rungs[k] < rungs[k + 1]                   # strictly nested


def test_build_dose_plan_uses_the_same_leaves_at_every_rung():
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup()
    pool = tuple(f"C1{i:03d}" for i in range(10))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    plan = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)
    per_rung = {}
    for p in plan:
        per_rung.setdefault(p.condition, set()).add(p.leaf_item_key)
    assert len(per_rung) == LADDER_MAX
    assert len(set(map(frozenset, per_rung.values()))) == 1   # one population


def test_build_dose_plan_skips_a_leaf_whose_ladder_cannot_be_built():
    """A cap that exhausts mid-ladder must drop the WHOLE leaf and move to the
    reserve — a partial ladder would break the common population (D5)."""
    from synthetic.dose_ladder import LADDER_MAX, build_dose_plan, nested_order

    inventory, pantry = _ladder_setup(n_leaves=12)
    pool = tuple(f"C1{i:03d}" for i in range(12))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    # 2 rewrites x cap 1 = 2 uses of paraphrase in the whole run: at most 2
    # leaves can carry it, so fewer than 12 ladders are buildable
    plan = build_dose_plan(
        pantry, inventory, order, pool, reuse_cap={"paraphrase": 1}, per_count=12,
    )
    leaves = {p.leaf_item_key for p in plan}
    assert len(plan) == len(leaves) * LADDER_MAX     # every kept leaf is complete
    assert len(leaves) < 12                          # some were skipped


def test_build_dose_plan_is_deterministic():
    from synthetic.dose_ladder import build_dose_plan, nested_order

    inventory, pantry = _ladder_setup()
    pool = tuple(f"C1{i:03d}" for i in range(10))
    order = nested_order({leaf: frozenset(NINE_SUBSET) for leaf in pool}, seed=42)
    key = lambda pl: [
        (p.condition, p.leaf_item_key, tuple(r.uid for r in p.rewrites)) for p in pl
    ]
    a = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)
    b = build_dose_plan(pantry, inventory, order, pool, reuse_cap={}, per_count=10)
    assert key(a) == key(b)
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k dose_plan`
Esperado: 5 FAILED — `ImportError: cannot import name 'build_dose_plan'`.

- [ ] **Paso 3: Implementa**

```python
def build_dose_plan(
    pantry: Pantry,
    inventory: LeafInventory,
    order: Mapping[str, tuple[ModificationType, ...]],
    pool: Sequence[str],
    *,
    reuse_cap: Mapping[str, int],
    per_count: int,
) -> tuple[PlannedVariant, ...]:
    """The five rungs, built leaf-atomically over a common pool (D4 + D5).

    For each candidate leaf in ``pool`` order, all ``LADDER_MAX`` rungs are
    built together from the leaf's nested type order. If any rung cannot be
    filled — every compatible rewrite of the type it needs is capped out — the
    leaf's whole ladder is reverted and the next candidate is tried, so the
    accepted leaves always carry a COMPLETE ladder and the five count cells
    share one population. Stops at ``per_count`` accepted leaves.

    Reuse caps count per RUN here, not per condition: the five rungs of a leaf
    are built together, so a single counter is the only coherent accounting.
    """
    concept_of = _concept_of(inventory)
    # resolved once per concept, not once per leaf (see `compatible_rewrites`)
    applicable: dict[str, dict] = {}
    usage: dict[str, int] = {}
    plan: list[PlannedVariant] = []
    accepted = 0

    for leaf in pool:
        if accepted >= per_count:
            break
        concept = concept_of[leaf]
        if concept not in applicable:
            applicable[concept] = pantry.for_concept(concept)
        by_type = compatible_rewrites(
            applicable[concept], inventory.text(leaf), inventory.axis_values(leaf),
        )
        types = order[leaf]
        picks: list[ApprovedRewrite] = []
        used_dedup: set = set()
        ok = True
        for mtype in types:
            pick = _least_used(
                by_type.get(mtype, ()), reuse_cap.get(mtype.value), usage,
                frozenset(used_dedup),
            )
            if pick is None:
                ok = False
                break
            picks.append(pick)
            used_dedup.add(pick.dedup_key)
            usage[pick.uid] = usage.get(pick.uid, 0) + 1
        if not ok:
            for pick in picks:            # revert this leaf's whole ladder
                usage[pick.uid] -= 1
            continue
        for k in range(1, LADDER_MAX + 1):
            plan.append(PlannedVariant(
                condition=f"dose_{k}", concept_key=concept,
                leaf_item_key=leaf, rewrites=tuple(picks[:k]),
            ))
        accepted += 1

    return tuple(plan)
```

Añade `"build_dose_plan"` a `__all__`.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 25 passed.

- [ ] **Paso 5: Commit**

```bash
git add src/synthetic/dose_ladder.py tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: dose_ladder — plan de dosis atomico por hoja"
```

---

## Tarea 10: Ficheros de configuración

**Ficheros:**
- Crear: `configs/synthetic/variant_budgets_OE_probe.yaml`
- Crear: `configs/synthetic/variant_budgets_OE_dose.yaml`
- Test: `tests/synthetic/test_dose_ladder.py`

- [ ] **Paso 1: Escribe el test que falla**

```python
def test_committed_dose_configs_load():
    from pathlib import Path
    from synthetic.dose_ladder import LADDER_MAX, load_dose_budgets

    root = Path(__file__).resolve().parents[2] / "configs" / "synthetic"
    dose = load_dose_budgets(root / "variant_budgets_OE_dose.yaml")
    assert dose.per_count >= 600                 # their §3
    assert dose.structural_threshold > LADDER_MAX
    assert dose.reuse_cap.get("num_to_text") == 20

    probe = load_dose_budgets(root / "variant_budgets_OE_probe.yaml")
    assert probe.candidate_cap >= dose.per_count
```

- [ ] **Paso 2: Corre el test y comprueba que falla**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q -k committed_dose_configs`
Esperado: FAILED — `FileNotFoundError`.

- [ ] **Paso 3: Crea los dos ficheros**

`configs/synthetic/variant_budgets_OE_probe.yaml`:

```yaml
# E3 — PROBE pass: one single-modification variant per (leaf, available type),
# TEXTO field only. Two jobs: measure which types really change each leaf's
# TEXTO (so the dose ladder can promise k planned = k applied, D2), and be the
# isolated-effects deliverable over the ladder's own leaves (D6).
# Candidates come from the structural pre-filter: leaves admitting >= 6 types,
# capped at 1500 to bound render cost (probing all 5000 would be ~30-45k renders
# for a pool that needs ~600).
seed: 42
per_count: 600
structural_threshold: 6
candidate_cap: 1500
reuse_cap:
  num_to_text: 20
  unit_expansion: 20
  unit_conversion: 20
```

`configs/synthetic/variant_budgets_OE_dose.yaml`:

```yaml
# E3 — DOSE ladder: dose_1..dose_5 over one common leaf pool, nested
# composition (types(dose_k) subset of types(dose_k+1)), >= 600 items per rung.
# Caps match the OE corpora so a thin type is not repeated more here than there;
# they count per RUN, since a leaf's five rungs are built together.
seed: 42
per_count: 600
structural_threshold: 6
candidate_cap: 1500
reuse_cap:
  num_to_text: 20
  unit_expansion: 20
  unit_conversion: 20
```

- [ ] **Paso 4: Corre el test y comprueba que pasa**

Ejecuta: `python -m pytest tests/synthetic/test_dose_ladder.py -q`
Esperado: 26 passed.

- [ ] **Paso 5: Commit**

```bash
git add configs/synthetic/variant_budgets_OE_probe.yaml configs/synthetic/variant_budgets_OE_dose.yaml tests/synthetic/test_dose_ladder.py
git commit -m "synthetic: configs de sondeo y escalera E3"
```

---

## Tarea 11: Script de orquestación

**Ficheros:**
- Crear: `scripts/build_dose_ladder.py`

Único fichero con E/S de generación: carga, encadena las dos pasadas, escribe el
sidecar de aplicabilidad. Sigue el patrón del CLI de `corpus_driver`
(`corpus_driver.py:790-835`): cargar stage JSON → despensa → filtro TEXTO →
inventario → plan → `run_corpus`.

- [ ] **Paso 1: Escribe el script**

```python
"""E3 — build the balanced dose ladder + isolated-effects set (spec: E3_DOSE_DESIGN.md).

Two passes over the SAME shared base-leaf sample the OE ablation corpora use, so
every dose item is paired on the same leaf as its stacked/single counterparts:

1. PROBE — one single-modification variant per (leaf, available type), TEXTO
   only, over the structurally pre-filtered candidates. Its surviving items give
   `available_types` per leaf and, restricted to the pool, the isolated-effects
   deliverable (D6).
2. DOSE — dose_1..dose_5 over the common pool, nested composition (D4/D5).

Deterministic, no LLM. Run (PYTHONPATH=src):

  python scripts/build_dose_ladder.py \
    --stage-json   data/synthetic/intermediate/OE_2026_stage.json \
    --menus-dir    data/synthetic/menus_OE \
    --inventory-long  data/synthetic/processed_OE/OE_ablation_inventory_long.parquet \
    --inventory-short data/synthetic/processed_OE/OE_ablation_inventory_short.parquet \
    --probe-budgets configs/synthetic/variant_budgets_OE_probe.yaml \
    --dose-budgets  configs/synthetic/variant_budgets_OE_dose.yaml \
    --concepts OE \
    --out-probe data/synthetic/processed_OE_probe \
    --out-dose  data/synthetic/processed_OE_dose \
    --applicability data/synthetic/handoff_OE/OE_leaf_applicability.jsonl \
    --source data/raw/BPA_2026.bc3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from synthetic import bc3param_backend, dose_ladder  # noqa: E402
from synthetic.corpus_driver import run_corpus  # noqa: E402
from synthetic.corpus_sampler import leaf_inventory_from_frames  # noqa: E402
from synthetic.pantry import Pantry, load_pantry  # noqa: E402
from synthetic.target_scanner import scan_chapter  # noqa: E402
from synthetic.taxonomy import ModificationType  # noqa: E402

#: L3 types whose rewrites must be restricted to their TEXTO-field variant, so
#: one modification always moves the TEXTO and counts once, not twice (D3).
_TEXTO_FIELD_TYPES = (
    ModificationType.TEMPLATE_PARAPHRASE,
    ModificationType.REORDER,
)


def _texto_only_pantry(pantry: Pantry) -> Pantry:
    """Keep only the TEXTO-field rewrites of the L3 types (D3).

    Same transform the OE SINGLE corpus applied via `--texto-fields-only`; here
    it is unconditional, because every E3 item must change the TEXTO.
    """
    keep = set(_TEXTO_FIELD_TYPES)
    by_type = {
        mt: (tuple(r for r in rws if str(r.dedup_key[0]) == "TEXTO")
             if mt in keep else rws)
        for mt, rws in pantry.by_type.items()
    }
    return Pantry(by_type={mt: rws for mt, rws in by_type.items() if rws})


def _surviving_types(items_path: Path) -> dict[str, frozenset]:
    """`{leaf: types whose probe item survived}` — read back from the probe
    release. A type survives when its single-modification item was emitted,
    which (with --require-texto-changed) means it really changed the TEXTO."""
    frame = pd.read_parquet(items_path)
    out: dict[str, set] = {}
    for original_key, mtypes in zip(frame["original_key"], frame["modification_types"]):
        types = list(mtypes) if not isinstance(mtypes, str) else json.loads(mtypes)
        out.setdefault(original_key, set()).update(
            ModificationType(t) for t in types
        )
    return {k: frozenset(v) for k, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-json", required=True)
    ap.add_argument("--menus-dir", required=True)
    ap.add_argument("--inventory-long", required=True)
    ap.add_argument("--inventory-short", required=True)
    ap.add_argument("--probe-budgets", required=True)
    ap.add_argument("--dose-budgets", required=True)
    ap.add_argument("--concepts", default="OE")
    ap.add_argument("--out-probe", required=True)
    ap.add_argument("--out-dose", required=True)
    ap.add_argument("--applicability", required=True)
    ap.add_argument("--report-probe", default=None)
    ap.add_argument("--report-dose", default=None)
    ap.add_argument("--source", default=None, help="BC3 catalogue for bc3param")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()

    if a.source:
        bc3param_backend.set_source(a.source)

    stage_json = json.loads(Path(a.stage_json).read_text(encoding="utf-8"))
    prefixes = tuple(p for p in a.concepts.split(",") if p)
    concepts = [k for k in stage_json if k.endswith("$") and k.startswith(prefixes)]
    if not concepts:
        raise SystemExit(f"no concepts match prefixes {prefixes!r}")

    pantry = _texto_only_pantry(load_pantry(Path(a.menus_dir)))
    probe_budgets = dose_ladder.load_dose_budgets(Path(a.probe_budgets))
    dose_budgets = dose_ladder.load_dose_budgets(Path(a.dose_budgets))

    long_df = pd.read_parquet(a.inventory_long)
    short_df = pd.read_parquet(a.inventory_short)
    # compatibility is judged against the TEXTO alone: a rewrite surfacing only
    # in the resumen must not count (refinement 1 of the plan)
    inventory = leaf_inventory_from_frames(long_df, short_df, text_field="texto")

    chapter = scan_chapter(stage_json, concept_filter=lambda k: k.startswith(prefixes))

    # ----- structural pre-filter (no renders) -----------------------------
    candidates = dose_ladder.candidate_leaves(
        chapter, inventory,
        threshold=probe_budgets.structural_threshold,
        cap=probe_budgets.candidate_cap,
    )
    print(f"[E3] candidatas tras el pre-filtro estructural: {len(candidates)}")

    # ----- pass 1: probe --------------------------------------------------
    probe_plan = dose_ladder.build_probe_plan(
        pantry, inventory, candidates, reuse_cap=probe_budgets.reuse_cap,
    )
    print(f"[E3] sondeo planificado: {len(probe_plan)} items")
    probe_stats = run_corpus(
        stage_json, probe_plan,
        out_dir=Path(a.out_probe),
        report_path=Path(a.report_probe) if a.report_probe else None,
        budgets=probe_budgets.to_driver_budgets(),
        workers=a.workers,
        require_texto_changed=True,
    )
    available = _surviving_types(Path(probe_stats.items_path))
    print(f"[E3] sondeo producido: {probe_stats.totals['produced']} items; "
          f"hojas con >=1 tipo disponible: {len(available)}")

    # ----- pool ------------------------------------------------------------
    histogram = dose_ladder.depth_histogram(available)
    depth, pool = dose_ladder.select_pool(
        available,
        pool_min=dose_budgets.effective_pool_min,
        min_depth=dose_budgets.structural_threshold,
    )
    print(f"[E3] profundidad elegida d={depth}; fondo={len(pool)} hojas; "
          f"histograma={histogram}")

    # ----- pass 2: dose ladder --------------------------------------------
    order = dose_ladder.nested_order(
        {leaf: available[leaf] for leaf in pool}, seed=dose_budgets.seed,
    )
    dose_plan = dose_ladder.build_dose_plan(
        pantry, inventory, order, pool,
        reuse_cap=dose_budgets.reuse_cap, per_count=dose_budgets.per_count,
    )
    print(f"[E3] escalera planificada: {len(dose_plan)} items")
    dose_stats = run_corpus(
        stage_json, dose_plan,
        out_dir=Path(a.out_dose),
        report_path=Path(a.report_dose) if a.report_dose else None,
        budgets=dose_budgets.to_driver_budgets(),
        workers=a.workers,
        require_texto_changed=True,
    )

    # ----- applicability sidecar ------------------------------------------
    structural = {
        leaf: dose_ladder.structural_types(
            chapter, concept, inventory.text(leaf), inventory.axis_values(leaf),
        )
        for concept in inventory.concepts()
        for leaf in inventory.leaves(concept)
        if leaf in available
    }
    out_side = Path(a.applicability)
    out_side.parent.mkdir(parents=True, exist_ok=True)
    with out_side.open("w", encoding="utf-8", newline="\n") as fh:
        for leaf in sorted(available):
            fh.write(json.dumps({
                "leaf_item_key": leaf,
                "applicable_types": sorted(t.value for t in structural.get(leaf, ())),
                "available_types": sorted(t.value for t in available[leaf]),
            }, ensure_ascii=False) + "\n")

    print(json.dumps({
        "candidates": len(candidates),
        "probe_produced": probe_stats.totals["produced"],
        "depth": depth,
        "pool": len(pool),
        "dose_produced": dose_stats.totals["produced"],
        "depth_histogram": histogram,
        "probe_items": str(probe_stats.items_path),
        "dose_items": str(dose_stats.items_path),
        "applicability": str(out_side),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Paso 2: Comprueba que el script arranca y valida**

Ejecuta: `python scripts/build_dose_ladder.py --help`
Esperado: la ayuda con las banderas; exit 0.

Ejecuta (sin `--source`, con rutas inexistentes, para ver que falla ruidosamente):
`PYTHONPATH=src python scripts/build_dose_ladder.py --stage-json noexiste.json --menus-dir x --inventory-long x --inventory-short x --probe-budgets configs/synthetic/variant_budgets_OE_probe.yaml --dose-budgets configs/synthetic/variant_budgets_OE_dose.yaml --out-probe /tmp/p --out-dose /tmp/d --applicability /tmp/a.jsonl`
Esperado: `FileNotFoundError` sobre `noexiste.json`. **No** un traceback dentro de
pandas ni un fichero vacío escrito.

- [ ] **Paso 3: Commit**

```bash
git add scripts/build_dose_ladder.py
git commit -m "synthetic: script de orquestacion de la escalera E3"
```

---

## Tarea 12: Empaquetado, aplicabilidad y procedencia

**Ficheros:**
- Modificar: `scripts/package_for_retrieval.py`
- Crear: `tests/synthetic/test_dose_packaging.py`

El esquema de su §5 con los dos campos de D1, más `MANIFEST.md` y
`provenance.json` de su §6.

- [ ] **Paso 1: Escribe los tests que fallan**

Crea `tests/synthetic/test_dose_packaging.py`:

```python
"""E3 — tests del empaquetado: join del sidecar, campos nuevos, procedencia."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_packager():
    """Import the script by path (it lives in scripts/, not a package)."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "package_for_retrieval", ROOT / "scripts" / "package_for_retrieval.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sidecar(tmp_path, rows):
    p = tmp_path / "applicability.jsonl"
    p.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    return p


def test_applicability_fields_are_joined_onto_every_record(tmp_path):
    mod = _load_packager()
    side = _sidecar(tmp_path, [
        {"leaf_item_key": "OEA010aaba",
         "applicable_types": ["paraphrase", "reorder"],
         "available_types": ["reorder"]},
    ])
    table = mod.load_applicability(side)
    rec = mod.apply_applicability(
        {"item_key": "x", "gold_item_key": "OEA010aaba"}, table,
    )
    assert rec["applicable_types"] == ["paraphrase", "reorder"]
    assert rec["available_types"] == ["reorder"]


def test_missing_sidecar_entry_fails_loud(tmp_path):
    mod = _load_packager()
    table = mod.load_applicability(_sidecar(tmp_path, []))
    with pytest.raises(KeyError, match="applicability_missing"):
        mod.apply_applicability({"item_key": "x", "gold_item_key": "OEA010aaba"}, table)


def test_manifest_lists_a_sha256_per_file(tmp_path):
    mod = _load_packager()
    (tmp_path / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.jsonl").write_text("{}\n", encoding="utf-8")
    text = mod.render_manifest(
        tmp_path, ["a.json", "b.jsonl"],
        provenance={"run_id": "r1", "seed": 42, "script": "s", "commit": "c"},
    )
    assert "a.json" in text and "b.jsonl" in text
    assert text.count("sha256") >= 1
    # the digest of an empty JSON list, to pin the hashing itself
    import hashlib
    assert hashlib.sha256(b"[]").hexdigest() in text
```

- [ ] **Paso 2: Corre los tests y comprueba que fallan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_packaging.py -q`
Esperado: 3 FAILED — `AttributeError: module has no attribute 'load_applicability'`.

- [ ] **Paso 3: Implementa en `scripts/package_for_retrieval.py`**

Añade estas funciones a nivel de módulo (y `import hashlib`, `import subprocess`,
`import datetime as _dt` arriba):

```python
def load_applicability(path):
    """`{leaf_item_key: (applicable_types, available_types)}` from the sidecar.

    The sidecar is keyed by LEAF because applicability is a property of the leaf,
    not of the synthetic item: the same leaf's five rungs share it, so storing it
    once avoids repeating the two lists on every record.
    """
    table = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        table[row["leaf_item_key"]] = (
            list(row.get("applicable_types") or []),
            list(row.get("available_types") or []),
        )
    return table


def apply_applicability(record, table):
    """Add the two D1 fields to one query record, joined on `gold_item_key`.

    Fails loud: a delivered record whose leaf is absent from the sidecar would
    silently ship an empty population descriptor, which is exactly the "compares
    different populations in silence" failure their §4 asks us to prevent.
    """
    leaf = record["gold_item_key"]
    if leaf not in table:
        raise KeyError(
            f"applicability_missing: leaf {leaf!r} (item {record['item_key']!r}) "
            f"has no sidecar entry"
        )
    applicable, available = table[leaf]
    out = dict(record)
    out["applicable_types"] = applicable
    out["available_types"] = available
    return out


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit():
    """The bc3cat-dataset commit that produced this delivery (their §6)."""
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True,
            text=True, check=True,
        ).stdout.strip()
    except Exception:            # a delivery from a tarball is still deliverable
        return "unknown"


def render_manifest(out_dir, filenames, provenance):
    """The §6 manifest: one SHA-256 per delivered file plus the provenance stamp."""
    lines = [
        "# BC3CAT-Syn — E3 dose delivery manifest",
        "",
        "| clave | valor |",
        "|---|---|",
    ]
    for key in sorted(provenance):
        lines.append(f"| `{key}` | `{provenance[key]}` |")
    lines += ["", "| fichero | bytes | sha256 |", "|---|---|---|"]
    for name in filenames:
        p = Path(out_dir) / name
        lines.append(f"| `{name}` | {p.stat().st_size} | `{_sha256(p)}` |")
    return "\n".join(lines) + "\n"
```

Después, en `main()`, añade las banderas y el cableado:

```python
    ap.add_argument("--dose", default=None, help="dose-ladder release dir")
    ap.add_argument("--probe", default=None, help="isolated-effects release dir")
    ap.add_argument("--applicability", default=None,
                    help="OE_leaf_applicability.jsonl (required with --dose/--probe)")
    ap.add_argument("--run-id", default=None)
```

y, tras la emisión de los conjuntos existentes:

```python
    written = []
    if a.dose or a.probe:
        if not a.applicability:
            raise SystemExit("--applicability is required with --dose/--probe")
        table = load_applicability(a.applicability)
        for flag, name in ((a.dose, "dose"), (a.probe, "isolated")):
            if not flag:
                continue
            recs = [apply_applicability(r, table) for r in query_records(flag)]
            fn = f"{col}_{name}_texto.json"
            (out / fn).write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
            written.append(fn)
            print(f"{fn}: {len(recs)} queries")
        side_name = Path(a.applicability).name
        (out / side_name).write_text(
            Path(a.applicability).read_text(encoding="utf-8"), encoding="utf-8",
        )
        written.append(side_name)
        provenance = {
            "run_id": a.run_id or _dt.datetime.now(_dt.timezone.utc).strftime("e3-%Y%m%dT%H%M%SZ"),
            "seed": 42,
            "script": "scripts/build_dose_ladder.py",
            "commit": git_commit(),
            "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        }
        (out / "provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        (out / "MANIFEST.md").write_text(
            render_manifest(out, written, provenance), encoding="utf-8",
        )
        print(f"MANIFEST.md + provenance.json written to {out}")
```

`REPO` ya debe existir en el script (patrón `Path(__file__).resolve().parents[1]`);
si no, añádelo junto a los imports.

- [ ] **Paso 4: Corre los tests y comprueba que pasan**

Ejecuta: `python -m pytest tests/synthetic/test_dose_packaging.py -q`
Esperado: 3 passed.

Ejecuta: `python -m pytest tests/synthetic -q`
Esperado: PASS.

- [ ] **Paso 5: Commit**

```bash
git add scripts/package_for_retrieval.py tests/synthetic/test_dose_packaging.py
git commit -m "synthetic: empaquetado E3 con aplicabilidad y procedencia firmada"
```

---

## Tarea 13: Informe del corpus de dosis

**Ficheros:**
- Crear: `scripts/report_dose_ladder.py`
- Test: `tests/synthetic/test_dose_packaging.py`

Lo que el informe tiene que dejar por escrito (§7 del spec): celdas por count,
presencia por tipo **dentro de cada celda** (la mitad alcanzable de su §3), el
histograma de profundidad, la *d* elegida y los déficits.

- [ ] **Paso 1: Escribe el test que falla**

Añade a `tests/synthetic/test_dose_packaging.py`:

```python
def test_dose_report_shows_per_cell_type_presence(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "report_dose_ladder", ROOT / "scripts" / "report_dose_ladder.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    items = pd.DataFrame({
        "item_key": ["a_syn_1", "b_syn_1", "c_syn_1"],
        "original_key": ["L1", "L1", "L2"],
        "concept_key": ["C1$", "C1$", "C1$"],
        "modification_types": [["reorder"], ["reorder", "paraphrase"], ["paraphrase"]],
        "modification_count": [1, 2, 1],
    })
    text = mod.render_report(items, depth=6, histogram={6: 2}, pool_size=2)
    assert "dose_1" in text and "dose_2" in text
    assert "reorder" in text and "paraphrase" in text
    assert "| 1 | 2 |" in text or "dose_1 | 2" in text   # 2 items at count 1
```

- [ ] **Paso 2: Corre el test y comprueba que falla**

Ejecuta: `python -m pytest tests/synthetic/test_dose_packaging.py -q -k report`
Esperado: FAILED — `FileNotFoundError: scripts/report_dose_ladder.py`.

- [ ] **Paso 3: Implementa**

```python
"""E3 — corpus report for the dose ladder (spec E3_DOSE_DESIGN.md §7).

Reads the dose release and writes docs/synthetic/OE_dose_report.md: cells per
count, per-type presence WITHIN each cell (their §3, achievable half), the
admitted-depth histogram, the chosen depth and any deficits.

Run (PYTHONPATH=src):
  python scripts/report_dose_ladder.py \
    --items data/synthetic/processed_OE_dose/BC3CAT_Syn_items.parquet \
    --depth 6 --pool-size 600 \
    --out docs/synthetic/OE_dose_report.md
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd


def _types(value):
    return list(value) if not isinstance(value, str) else json.loads(value)


def render_report(items: pd.DataFrame, *, depth: int, histogram: dict,
                  pool_size: int) -> str:
    counts = Counter(int(c) for c in items["modification_count"])
    lines = [
        "# E3 — informe del corpus de dosis (escalera anidada)",
        "",
        "Consulta = TEXTO modificado; objetivo = TEXTO original de la misma hoja.",
        "`modification_count` cuenta modificaciones APLICADAS y es exacto por",
        "construcción (D2): el sondeo verificó la disponibilidad antes de sortear.",
        "",
        f"- profundidad elegida **d = {depth}**",
        f"- fondo común: **{pool_size} hojas**, las mismas en las cinco celdas",
        f"- histograma de profundidad admitida: `{histogram}`",
        f"- ítems: **{len(items)}**, hojas distintas: **{items['original_key'].nunique()}**",
        "",
        "## Celdas por dosis",
        "",
        "| dosis | ítems |",
        "|---|---|",
    ]
    for k in sorted(counts):
        lines.append(f"| dose_{k} | {counts[k]} |")

    all_types = sorted({t for v in items["modification_types"] for t in _types(v)})
    lines += [
        "",
        "## Presencia por tipo dentro de cada celda",
        "",
        "Lo alcanzable de su §3: dentro de una celda ningún tipo debe estar",
        "sistemáticamente sobre-representado. La tasa de un tipo CRECE con la",
        "dosis por construcción (k tipos de un repertorio de d), y eso es una",
        "propiedad de la dosis, no un sesgo.",
        "",
        "| dosis | " + " | ".join(all_types) + " |",
        "|" + "---|" * (len(all_types) + 1),
    ]
    for k in sorted(counts):
        rows = items[items["modification_count"] == k]
        presence = Counter(t for v in rows["modification_types"] for t in _types(v))
        lines.append(
            f"| dose_{k} | " + " | ".join(str(presence.get(t, 0)) for t in all_types) + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--depth", type=int, required=True)
    ap.add_argument("--pool-size", type=int, required=True)
    ap.add_argument("--histogram", default="{}",
                    help="JSON dict from build_dose_ladder.py's output")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    items = pd.read_parquet(a.items)
    text = render_report(
        items, depth=a.depth, histogram=json.loads(a.histogram),
        pool_size=a.pool_size,
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"informe escrito en {a.out} ({len(items)} ítems)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Paso 4: Corre el test y comprueba que pasa**

Ejecuta: `python -m pytest tests/synthetic/test_dose_packaging.py -q`
Esperado: 4 passed.

- [ ] **Paso 5: Commit**

```bash
git add scripts/report_dose_ladder.py tests/synthetic/test_dose_packaging.py
git commit -m "synthetic: informe del corpus de dosis E3"
```

---

## Tarea 14: Generación real, QA y entrega

**Ficheros:**
- Genera: `data/synthetic/processed_OE_{probe,dose}/`, `data/synthetic/handoff_OE/`
- Crea: `docs/synthetic/OE_dose_report.md`
- Modifica: `docs/synthetic/HANDOFF.md`, `docs/synthetic/RESEARCH_LOG.md`

**Esta tarea se corre entera antes de dar nada por bueno.** Las anteriores son
herméticas; aquí se toca el catálogo real.

- [ ] **Paso 1: Comprueba que la suite completa está verde**

Ejecuta: `python -m pytest tests/synthetic -q`
Esperado: PASS, 0 failed. Si algo falla, **para**: no se genera sobre una suite roja.

- [ ] **Paso 2: Corre las dos pasadas**

```bash
PYTHONPATH=src python scripts/build_dose_ladder.py \
  --stage-json   data/synthetic/intermediate/OE_2026_stage.json \
  --menus-dir    data/synthetic/menus_OE \
  --inventory-long  data/synthetic/processed_OE/OE_ablation_inventory_long.parquet \
  --inventory-short data/synthetic/processed_OE/OE_ablation_inventory_short.parquet \
  --probe-budgets configs/synthetic/variant_budgets_OE_probe.yaml \
  --dose-budgets  configs/synthetic/variant_budgets_OE_dose.yaml \
  --concepts OE \
  --out-probe data/synthetic/processed_OE_probe \
  --out-dose  data/synthetic/processed_OE_dose \
  --applicability data/synthetic/handoff_OE/OE_leaf_applicability.jsonl \
  --report-probe docs/synthetic/sprints/E3_probe_qa.md \
  --report-dose  docs/synthetic/sprints/E3_dose_qa.md \
  --source data/raw/BPA_2026.bc3
```

Esperado en el JSON final: `dose_produced == 5 * pool`, `depth >= 6`,
`pool >= 600`. Anota `depth_histogram`: va al informe y a la respuesta.

**Si `pool_too_small`:** el fondo no llega a 600 hojas a profundidad ≥6. NO bajes
`structural_threshold` por tu cuenta — rompe D5. Sube `candidate_cap` (más
candidatas sondeadas) y vuelve a correr; si tampoco, para y consulta: es una
decisión de diseño experimental, no de implementación.

**Si `applied_count_mismatch`:** el sondeo dijo disponible y el emisor aplicó
menos. Es un bug real. Depúralo con `superpowers:systematic-debugging`; no
relajes la afirmación.

- [ ] **Paso 3: Comprueba el determinismo**

```bash
sha256sum data/synthetic/processed_OE_dose/BC3CAT_Syn_items.parquet \
          data/synthetic/processed_OE_dose/BC3CAT_Syn_modifications.jsonl
```

Vuelve a correr el comando del paso 2 con `--out-dose data/synthetic/_dose_check`
y compara los dos digests.
Esperado: idénticos. Si no, hay una fuente de orden no determinista (un `set` sin
ordenar, un `hash()`): arréglala antes de seguir.

- [ ] **Paso 4: QA del corpus**

```bash
PYTHONPATH=src python scripts/cross_concept_audit.py \
  --items data/synthetic/processed_OE_dose/BC3CAT_Syn_items.parquet \
  --target-long data/synthetic/processed_OE/OE_target_long.parquet \
  --template-level
```
Esperado: 0 colisiones introducidas. (Si las banderas del script difieren,
`python scripts/cross_concept_audit.py --help`; no adivines.)

- [ ] **Paso 5: Genera el informe**

```bash
PYTHONPATH=src python scripts/report_dose_ladder.py \
  --items data/synthetic/processed_OE_dose/BC3CAT_Syn_items.parquet \
  --depth <d del paso 2> --pool-size <pool del paso 2> \
  --histogram '<depth_histogram del paso 2>' \
  --out docs/synthetic/OE_dose_report.md
```

Lee el informe. Comprueba a ojo: cinco celdas con ≥600 ítems, y dentro de cada
celda ningún tipo a cero mientras otro va al máximo.

- [ ] **Paso 6: Empaqueta la entrega**

```bash
PYTHONPATH=src python scripts/package_for_retrieval.py \
  --stage-json data/synthetic/intermediate/OE_2026_stage.json \
  --dose  data/synthetic/processed_OE_dose \
  --probe data/synthetic/processed_OE_probe \
  --applicability data/synthetic/handoff_OE/OE_leaf_applicability.jsonl \
  --out-dir data/synthetic/handoff_OE
```
Esperado: `OE_dose_texto.json`, `OE_isolated_texto.json`,
`OE_leaf_applicability.jsonl`, `provenance.json`, `MANIFEST.md`.

Comprueba un registro a mano:

```bash
python -c "import json;r=json.load(open('data/synthetic/handoff_OE/OE_dose_texto.json',encoding='utf-8'))[0];print(json.dumps(r,ensure_ascii=False,indent=2)[:800])"
```
Esperado: están `parent_key`, `gold_item_key`, `modification_types`,
`modification_count`, `applicable_types`, `available_types`.

- [ ] **Paso 7: Actualiza la documentación**

En `docs/synthetic/HANDOFF.md`, añade una sección "E3 — conjunto de dosis" con:
los dos ficheros y sus recuentos reales, la *d* elegida, el tamaño del fondo, la
convención de gold (idéntica), y **la salvedad de §8 del spec** redactada para
que puedan citarla en sus limitaciones.

En `docs/synthetic/RESEARCH_LOG.md`, una entrada con fecha, el commit de
generación, los digests SHA-256 y el `run_id`.

- [ ] **Paso 8: Commit**

```bash
git add docs/synthetic/OE_dose_report.md docs/synthetic/HANDOFF.md \
        docs/synthetic/RESEARCH_LOG.md docs/synthetic/sprints/E3_*_qa.md \
        data/synthetic/handoff_OE/
git commit -m "synthetic: entrega E3 — escalera de dosis + efectos aislados (d=<d>, fondo=<n>)"
```

**No** hagas commit de `data/synthetic/processed_OE_{probe,dose}/` sin comprobar
antes qué está trazado y qué no: sigue la misma política que la entrega OE, donde
el corpus de documentos (~124 MB) se dejó fuera por ser regenerable
(`git log --stat -1 f7aa661` y `8998875` muestran el criterio). Los ficheros del
handoff sí se versionan.

---

## Auto-revisión del plan (hecha)

**Cobertura del spec.** §1 → tareas 11/14. §2 D1 → 2, 3, 12. D2 → 5, 6, 11.
D3 → 11 (`_texto_only_pantry`). D4 → 7, 9. D5 → 8, 9. D6 → 5, 11, 12.
§3 arquitectura (pre-filtro, dos pasadas) → 5, 11. §4 componentes → 1–13, uno por
fila de la tabla. §5 esquema y sidecar → 12. §6 errores → 1 (`condition_unknown`),
6 (`applied_count_mismatch`), 8 (`pool_too_small`), 12 (`applicability_missing`);
el residuo de plantilla ya levanta hoy y no se toca. §7 verificación → los tests
de 2–10 más 12/13; `cross_concept_audit`/`dedup` → 14 paso 4. §8 salvedad → 13
(informe) y 14 paso 7 (HANDOFF). §9 fuera de alcance → respetado: no se toca
`main`, ni el esquema congelado, ni `synthetic.loaders`, y el port a
`synthetic-generator` queda explícitamente fuera.

**Sin huecos.** Todos los pasos de código llevan el código. Los dos valores que
no puedo fijar de antemano (*d* y el tamaño del fondo) son **salidas de una
medición**, con el procedimiento y el criterio de fallo escritos, no marcadores.

**Consistencia de tipos.** `is_compatible(rewrite, leaf_text, leaf_axis_values)`,
`structural_types(chapter_inventory, concept_key, leaf_text, leaf_axis_values)`,
`compatible_rewrites(applicable, leaf_text, leaf_axis_values)` →
`dict[ModificationType, tuple[ApprovedRewrite, ...]]`,
`nested_order(admitted, seed)` → `dict[str, tuple[ModificationType, ...]]`,
`select_pool(available, *, pool_min, min_depth)` → `(int, tuple[str, ...])`,
`build_probe_plan(pantry, inventory, leaves, *, reuse_cap)`,
`build_dose_plan(pantry, inventory, order, pool, *, reuse_cap, per_count)`.
Los nombres se usan igual en las tareas 11–13 que donde se definen.
