"""Alineación plantilla → texto para la BT (opción A, rediseño tras CP2).

Localiza en un TEXTO renderizado la superficie de cada placeholder de su
plantilla: valores L1 (``$C`` → «Nocturno») y fragmentos de variables de
texto L2 (``$I`` → «en cruce bajo vías»). La BT los enmascara y así salen
literalmente iguales: la traducción solo toca la prosa de la plantilla.

La plantilla se convierte en una expresión regular: literales tal cual (con
espacios flexibles) y un grupo por placeholder. Los grupos cuya superficie se
conoce van anclados; los demás son libres y se comprueban dos veces, en modo
perezoso y codicioso: si los cortes difieren, la alineación es ambigua y
falla en voz alta (:class:`AlignmentError`), nunca se adivina.

* gold — los valores L1 de la hoja anclan sus grupos; los fragmentos L2
  quedan libres (en el corpus OE la alineación es única en las 70 242 hojas);
* STACKED — plantilla TEXTO parafraseada del sidecar, con todos los grupos
  anclados: superficies del gold más los cambios L1/L2 del sidecar. Si un
  fragmento L2 no se puede reconstruir, ese grupo queda libre; si así no
  alinea, se reintenta anclando solo L1.

Funciones puras, solo stdlib.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

_PH_RE = re.compile(r"\$([A-Za-z]\w*)(?:\([^)]*\))?")


class AlignmentError(ValueError):
    """La plantilla no casa con el texto, o casa de más de una forma."""


@dataclass(frozen=True)
class Slot:
    placeholder: str  # tal cual en la plantilla: "$C", "$L(b,%F)"
    start: int
    end: int
    text: str         # superficie sin espacios de borde; "" si no renderiza


def _flat(value: object) -> str:
    return value if isinstance(value, str) else " ".join(map(str, value or ()))


def texto_template(concept: Mapping) -> str:
    return _flat(concept.get("texto") or "").lstrip("\\")


def leaf_values(concept: Mapping, leaf_key: str) -> dict[str, str]:
    """Valor (tal cual en la fuente) de cada eje para la hoja."""
    params = concept.get("parameters") or {}
    suffix = leaf_key[-len(params):] if params else ""
    return {ax: block["values"][ord(letter) - 97]["value"]
            for (ax, block), letter in zip(params.items(), suffix)}


def _lit(chunk: str) -> str:
    return r"\s*".join(re.escape(w) for w in chunk.split())


def _regex(template: str, known: Mapping[str, str], lazy: bool):
    parts, names, last = [], [], 0
    for i, m in enumerate(_PH_RE.finditer(template)):
        parts.append(_lit(template[last:m.start()]))
        ph = m.group(0)
        if ph in known:
            parts.append(f"(?P<g{i}>{_lit(known[ph])})")
        else:
            parts.append(f"(?P<g{i}>.*{'?' if lazy else ''})")
        names.append(ph)
        last = m.end()
    parts.append(_lit(template[last:]))
    body = r"\s*".join(p for p in parts if p)
    return re.compile(r"\s*" + body + r"\s*", re.S), names


def _slots(m: re.Match, names: Sequence[str], text: str) -> list[Slot]:
    out = []
    for i, ph in enumerate(names):
        a, b = m.span(f"g{i}")
        raw = text[a:b]
        a2 = a + (len(raw) - len(raw.lstrip()))
        b2 = b - (len(raw) - len(raw.rstrip()))
        if b2 < a2:
            a2 = b2 = a
        out.append(Slot(ph, a2, b2, text[a2:b2]))
    return out


def align(template: str, text: str, known: Mapping[str, str]) -> list[Slot]:
    """Superficie de cada placeholder de ``template`` en ``text``, en el orden
    de la plantilla. ``known`` ancla los grupos cuya superficie se conoce."""
    results = []
    for lazy in (True, False):
        rx, names = _regex(template, known, lazy)
        m = rx.fullmatch(text)
        if m is None:
            raise AlignmentError("no_match")
        results.append(_slots(m, names, text))
    norm = [[(s.placeholder, " ".join(s.text.split())) for s in r] for r in results]
    if norm[0] != norm[1]:
        raise AlignmentError("ambiguous")
    return results[0]


def _l1_known(concept: Mapping, leaf_key: str) -> dict[str, str]:
    return {f"${ax}": v for ax, v in leaf_values(concept, leaf_key).items()}


def gold_slots(concept: Mapping, leaf_key: str, text: str) -> list[Slot]:
    return align(texto_template(concept), text, _l1_known(concept, leaf_key))


def stacked_slots(concept: Mapping, gold_key: str, gold_text: str, query_text: str,
                  records: Sequence[Mapping]) -> list[Slot]:
    """Superficies de una consulta STACKED, ancladas con el gold y su sidecar."""
    template: Optional[str] = None
    for r in records:
        if r.get("layer") == "template" and r.get("field") == "TEXTO":
            template = r["new"]
    template = template if template is not None else texto_template(concept)

    known = {s.placeholder: s.text for s in gold_slots(concept, gold_key, gold_text)}
    l1 = _l1_known(concept, gold_key)
    for r in records:
        if r.get("layer") == "param_value":
            known[f"${r['param']}"] = r["new"]
            l1[f"${r['param']}"] = r["new"]
        elif r.get("layer") == "text_variable":
            for ph in [p for p in known if _PH_RE.fullmatch(p) and _PH_RE.fullmatch(p).group(1) == r["var"]]:
                original = r["original"].strip()
                if original and original in known[ph]:
                    known[ph] = known[ph].replace(original, r["new"].strip())
                else:
                    known.pop(ph)
    try:
        return align(template, query_text, known)
    except AlignmentError:
        return align(template, query_text, l1)
