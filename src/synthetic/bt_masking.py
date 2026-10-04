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

Estrategias: ``sentinel`` (``[[Q1]]``), ``xml`` (``<x1/>``) y ``none``.
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

from .slot_extractor import _UNIT_TOKENS

STRATEGIES = ("sentinel", "xml", "none")

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

MARKER_RE = re.compile(r"\[\[[BQS]\d+\]\]|<x\d+/>")


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
    if strategy not in STRATEGIES:
        raise ValueError(f"estrategia desconocida: {strategy!r}")
    if strategy == "none":
        return text, {}

    mapping: dict[str, str] = {}
    counters = {"B": 0, "Q": 0, "S": 0}
    out: list[str] = []
    pos = 0
    while True:
        m = _SCAN_RE.search(text, pos)
        if m is None:
            break
        kind = m.lastgroup
        end = m.end() if kind == "S" else _unit_end(text, m.end())
        counters[kind] += 1
        if strategy == "sentinel":
            marker = f"[[{kind}{counters[kind]}]]"
        else:
            marker = f"<x{len(mapping) + 1}/>"
        mapping[marker] = text[m.start():end]
        out.append(text[pos:m.start()])
        out.append(marker)
        pos = end
    out.append(text[pos:])
    return "".join(out), mapping


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
