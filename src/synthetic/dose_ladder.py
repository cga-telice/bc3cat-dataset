"""E3 — planificador de la escalera de dosis equilibrada (spec: E3_DOSE_DESIGN.md).

Decide QUÉ se genera; no renderiza y no escribe. Produce
:class:`~synthetic.corpus_sampler.PlannedVariant`s que
:func:`~synthetic.corpus_driver.run_corpus` materialisa.

Dos familias de condición:

* ``probe_<type>`` — una variante por (hoja, tipo admitido) con UNA sola
  modificación, campo TEXTO. Mide qué tipos cambian de verdad el TEXTO de cada
  hoja y, restringida al fondo, es el entregable de efectos aislados (D6).
* ``dose_1..dose_5`` — la escalera anidada: ``types(dose_k)`` es el prefijo de
  longitud ``k`` del orden de tipos de la hoja, así que entre peldaños
  consecutivos cambia exactamente una modificación añadida (D4).

Dos nociones de aplicabilidad por hoja, ambas libres de topes de reuso (D1):

* :func:`structural_types` — la gramática admite el tipo. Sale de los *targets*
  del capítulo (:func:`~synthetic.target_scanner.scan_chapter`), o sea de lo que
  existe antes de cualquier propuesta del LLM.
* :func:`available_types` — existe además una reescritura aprobada y compatible.

Determinismo: mismas entradas -> mismo plan, byte a byte. Toda derivación de
semilla usa ``zlib.crc32`` (nunca ``hash()``, salado por proceso).
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
    "available_types",
]

#: Rungs of the ladder: dose_1 .. dose_5 (their §1).
LADDER_MAX = 5

#: L1 per-value types, whose ``dedup_key`` is ``(axis_label, value)`` — the
#: reviewed surface is the SECOND element. Mirrors the sampler's own set.
_L1_VALUE_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})


class DoseLadderError(RuntimeError):
    """A guarantee this module promises has been violated."""


def _surface(mtype: ModificationType, dedup_key: Sequence) -> str:
    """The reviewed surface form carried by a ``dedup_key``.

    L1: ``(axis, value)`` -> the value. L2: ``(fragment,)`` -> the fragment.
    L3: the template body, which `is_compatible` ignores anyway (L3 rewrites
    touch the shared template, so they surface in every leaf).
    """
    if mtype in _L1_VALUE_TYPES and len(dedup_key) >= 2:
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
