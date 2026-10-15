"""Enmascarado de superficie para la back-translation (BT, opción A).

La BT traduce el TEXTO *renderizado* (sin placeholders) ES → pivote → ES.
Lo que no puede cambiar se oculta antes tras marcadores opacos y se
restaura literalmente después:

* ``B`` — expresión de banda completa (``i >= 5 horas``, ``3 <= i < 5 horas``):
  se enmascara entera, no solo el número;
* ``Q`` — token con dígito (``1,60``, ``30x15``, ``HE-20``) con su unidad
  si la siguiente palabra está en :data:`slot_extractor._UNIT_TOKENS`;
* ``S`` — sigla en mayúsculas (``PVC``, ``ADIF``, ``E.T.``). Decisión de
  César en CP1: las siglas se protegen, no solo se avisan.

Estrategias: ``sentinel`` (``[[Q1]]``), ``xml`` (``<x1/>``), ``bracket`` (``[1]``;
Marian los copia tal cual, ver ``OE_bt_mask_experiment.md``) y ``none``.
El ``mapping`` va de marcador literal a texto original, así que
:func:`unmask_surface` y :func:`check_masks` no necesitan saber la
estrategia.

A diferencia de :mod:`template_masking` (base para cantidades), aquí no se
enmascaran placeholders: el texto ya está renderizado (ver F-BT-2).

Funciones puras, solo stdlib.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Sequence

from .slot_extractor import _UNIT_TOKENS

STRATEGIES = ("sentinel", "xml", "bracket", "none")

_NUM = r"\d+(?:[.,]\d+)?"
_OP = r"(?:<=|>=|<|>|≤|≥)"
# Banda completa; un operador suelto (consulta degenerada) también es B.
_BAND = (
    rf"(?:{_NUM}\s*(?:<=|<|≤)\s*)?(?<!\w)i\s*{_OP}\s*{_NUM}|{_OP}"
)
# Un token con dígito; no arrastra puntuación final, paréntesis, comillas
# ni dos puntos ("mantenimiento:3 <= i" no debe robar el inicio de la banda).
_TOK = r"[^\s\[\]<>()«»\":;]"
_QTY = rf"{_TOK}*\d(?:{_TOK}*[^\s\[\]<>()«»\".,;:])?"
_CAPS = "A-ZÁÉÍÓÚÑÜ"
_ACRONYM = rf"(?<![\w$.])(?:[{_CAPS}]\.){{2,}}|(?<![\w$])[{_CAPS}]{{2,}}(?!\w)"

_SCAN_RE = re.compile(rf"(?P<B>{_BAND})|(?P<Q>{_QTY})|(?P<S>{_ACRONYM})")
_UNIT_PEEK_RE = re.compile(r"\s+([^\s\d\[\]$<>()«»\",;:]+)")

MARKER_RE = re.compile(r"\[\[[BQSVG]\d+\]\]|<x\d+/>|\[\d+\]")


class MaskError(ValueError):
    """Un marcador se perdió, se duplicó o apareció uno desconocido."""


def _unit_end(text: str, end: int) -> int:
    """Fin del literal si tras ``end`` viene una unidad conocida."""
    m = _UNIT_PEEK_RE.match(text, end)
    if m is None:
        return end
    word = m.group(1)
    if word.lower() in _UNIT_TOKENS:
        return m.end()
    bare = word.rstrip(".")
    if bare != word and bare.lower() in _UNIT_TOKENS:
        return m.start(1) + len(bare)  # los puntos son puntuación de frase
    return end


def mask_surface(text: str, strategy: str) -> tuple[str, dict[str, str]]:
    """Sustituye bandas, cantidades/códigos y siglas por marcadores.

    Devuelve ``(masked, mapping)`` con ``mapping`` de marcador a literal,
    en orden de aparición. Con ``strategy="none"`` devuelve el texto tal
    cual y un mapping vacío.
    """
    masked, mapping, _ = _mask(text, strategy, ())
    return masked, mapping


def mask_with_values(text: str, strategy: str, spans: Sequence[tuple[int, int]],
                     glossary: Sequence[tuple[int, int]] = ()) -> tuple[str, dict[str, str], list[str]]:
    """Como :func:`mask_surface`, pero cada tramo de ``spans`` (valores de eje
    y fragmentos L2, de :mod:`bt_alignment`) se enmascara entero como ``V``;
    bandas, cantidades y siglas se buscan solo fuera de esos tramos. Devuelve
    también los marcadores ``V`` en orden de texto, para
    :func:`check_value_order`. ``glossary`` (de :func:`glossary_spans`) son
    términos del oficio que también salen literales, como ``G``, pero sin
    comprobación de orden: pueden moverse dentro de la frase."""
    return _mask(text, strategy, spans, glossary)


def _mask(text: str, strategy: str, spans, glossary=()) -> tuple[str, dict[str, str], list[str]]:
    if strategy not in STRATEGIES:
        raise ValueError(f"estrategia desconocida: {strategy!r}")
    if strategy == "none":
        return text, {}, []
    kinds = {(a, b): "V" for a, b in spans if b > a}
    kinds.update({(a, b): "G" for a, b in glossary if b > a and (a, b) not in kinds})
    spans = sorted(kinds)
    for (_, b1), (a2, _) in zip(spans, spans[1:]):
        if a2 < b1:
            raise ValueError("tramos de valor solapados")

    mapping: dict[str, str] = {}
    values: list[str] = []
    counters = {"B": 0, "Q": 0, "S": 0, "V": 0, "G": 0}
    out: list[str] = []

    def emit(kind: str, literal: str) -> None:
        counters[kind] += 1
        if strategy == "sentinel":
            marker = f"[[{kind}{counters[kind]}]]"
        elif strategy == "bracket":
            marker = f"[{len(mapping) + 1}]"
        else:
            marker = f"<x{len(mapping) + 1}/>"
        mapping[marker] = literal
        out.append(marker)
        if kind == "V":
            values.append(marker)

    def scan(gap: str) -> None:
        pos = 0
        while True:
            m = _SCAN_RE.search(gap, pos)
            if m is None:
                break
            kind = m.lastgroup
            end = m.end() if kind == "S" else _unit_end(gap, m.end())
            out.append(gap[pos:m.start()])
            emit(kind, gap[m.start():end])
            pos = end
        out.append(gap[pos:])

    pos = 0
    for a, b in spans:
        scan(text[pos:a])
        emit(kinds[(a, b)], text[a:b])
        pos = b
    scan(text[pos:])
    return "".join(out), mapping, values


def check_value_order(text: str, values: Sequence[str]) -> None:
    """Los marcadores de valor aparecen en ``text`` en el mismo orden que en el
    origen (los demás marcadores pueden moverse). Un valor cambiado de sitio
    puede quedar asociado a otra etiqueta: decisión de César, se rechaza."""
    wanted = set(values)
    found = [m for m in MARKER_RE.findall(text) if m in wanted]
    if found != list(values):
        raise MaskError(f"value_order_changed: {found} != {list(values)}")


def unmask_surface(text: str, mapping: dict[str, str]) -> str:
    """Restaura los literales. Los marcadores desconocidos se dejan tal
    cual: llama antes a :func:`check_masks` para fallar en voz alta."""
    return MARKER_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), text)


def check_masks(text: str, mapping: dict[str, str]) -> None:
    """Cada marcador de ``mapping`` exactamente una vez y ninguno más
    (comprobación de multiconjunto; el orden puede cambiar). Lanza
    :class:`MaskError` que empieza por ``masks_not_preserved``."""
    found = Counter(MARKER_RE.findall(text))
    expected = Counter(mapping.keys())
    if found != expected:
        missing = sorted((expected - found).keys())
        extra = sorted((found - expected).keys())
        raise MaskError(
            f"masks_not_preserved: missing={missing} extra_or_dup={extra}"
        )


def _plural_forms(term: str) -> list[str]:
    forms = [term, term + "s", term + "es"]
    if term.endswith("ón"):
        forms.append(term[:-2] + "ones")
    if term.endswith("z"):
        forms.append(term[:-1] + "ces")
    return forms


def glossary_spans(text: str, terms: Sequence[str],
                   exclude: Sequence[tuple[int, int]] = ()) -> list[tuple[int, int]]:
    """Tramos de los términos del glosario (palabra completa, sin distinguir
    mayúsculas, singular o plural) que no caen dentro de ``exclude`` (los
    valores, que ya van enmascarados). El glosario sale de la auditoría de las
    prosas de ``bt_origv``: son los términos que el traductor confundía."""
    out = []
    for term in terms:
        alt = "|".join(re.escape(f) for f in sorted(_plural_forms(term), key=len, reverse=True))
        for m in re.finditer(rf"(?<!\w)(?:{alt})(?!\w)", text, re.IGNORECASE):
            a, b = m.span()
            if not any(a < eb and ea < b for ea, eb in exclude):
                out.append((a, b))
    out = sorted(set(out))
    keep, last = [], -1
    for a, b in out:  # sin solapes entre términos
        if a >= last:
            keep.append((a, b))
            last = b
    return keep
