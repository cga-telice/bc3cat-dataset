"""Restauración posterior de términos del glosario en la BT de prosa.

Idea de César (vuelta tras la auditoría de prosas): enmascarar los términos
antes de traducir hace que el traductor reordene la frase a su alrededor. En
su lugar, la prosa se traduce sin enmascararlos y, después, cada término que
haya desaparecido se devuelve a su forma original en el sitio que ocupa su
traducción.

El sitio se encuentra alineando palabra a palabra origen y salida
(``difflib``). Solo se restaura cuando la alineación es segura:

* bloque sustituido de igual longitud → correspondencia posición a posición
  (se restaura el término y, si cambió, la preposición que lo precede: «no
  montados» → «en desmonte»);
* bloque de distinta longitud → solo si los dos lados tienen como mucho 3
  palabras (se restaura el bloque de origen entero: «Parte superior» → «Tapa»).

Si el término desaparece en un reordenamiento mayor, no se adivina: el
resultado es ``ok=False`` y la frase no se usa con esa candidata. Los artículos
no se corrigen (decisión de César: la gente real también se equivoca).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

_TOKEN_RE = re.compile(r"\[\d+\]|\w+|[^\w\s]")
_MARKER_RE = re.compile(r"\[\d+\]")
_PREPS = frozenset({"en", "de", "del", "sobre", "con", "para", "por", "a", "al", "desde", "bajo"})
_FUNCTION = _PREPS | {"el", "la", "los", "las", "un", "una", "y", "o", "su", "sus"}


def _fold(word: str) -> str:
    t = unicodedata.normalize("NFKD", word.casefold())
    return "".join(c for c in t if not unicodedata.combining(c))


def _stem(term: str) -> str:
    t = _fold(term)
    return t[:max(4, len(t) - 2)]


@dataclass
class RestoreResult:
    text: str
    ok: bool
    reason: str | None = None
    restored: list = field(default_factory=list)  # (término, texto sustituido)
    missing: list = field(default_factory=list)


def restore_terms(source: str, output: str, terms: Sequence[str]) -> RestoreResult:
    if Counter(_MARKER_RE.findall(source)) != Counter(_MARKER_RE.findall(output)):
        return RestoreResult(output, False, "markers_changed")
    src = list(_TOKEN_RE.finditer(source))
    out = list(_TOKEN_RE.finditer(output))
    sf = [_fold(m.group(0)) for m in src]
    of = [_fold(m.group(0)) for m in out]
    stems = {_fold(t): _stem(t) for t in terms}

    # términos del origen que ya no están en la salida
    lost = []
    for i, w in enumerate(sf):
        for t, st in stems.items():
            if w.startswith(st) and not any(o.startswith(st) for o in of):
                lost.append((i, t))
                break
    if not lost:
        return RestoreResult(output, True)

    ops = difflib.SequenceMatcher(a=sf, b=of, autojunk=False).get_opcodes()
    edits: dict[tuple, str] = {}  # (inicio, fin) en la salida -> texto de origen
    restored, missing = [], []
    block_of = {i: next((o for o in ops if o[1] <= i < o[2]), None) for i, _ in lost}
    per_block = Counter(b for b in block_of.values() if b is not None)
    for i, term in lost:
        block = block_of[i]
        if block is None or block[0] != "replace" or per_block[block] > 1:
            # sin bloque sustituido, o varios términos perdidos en el mismo bloque:
            # es un reordenamiento y la correspondencia no es fiable
            missing.append(term)
            continue
        _, i1, i2, j1, j2 = block
        if i2 - i1 == j2 - j1:
            positions = [i]
            if i - 1 >= i1 and sf[i - 1] in _PREPS and of[j1 + (i - 1 - i1)] != sf[i - 1]:
                positions.insert(0, i - 1)
            a, b = j1 + (positions[0] - i1), j1 + (positions[-1] - i1)
            s0, s1 = positions[0], positions[-1]
        elif max(i2 - i1, j2 - j1) <= 3 and all(
                k == i or sf[k] in _FUNCTION for k in range(i1, i2)):
            # el bloque de origen es el término y, como mucho, palabras funcionales
            a, b, s0, s1 = j1, j2 - 1, i1, i2 - 1
        else:
            missing.append(term)
            continue
        span = (out[a].start(), out[b].end())
        edits[span] = source[src[s0].start():src[s1].end()]
        restored.append((term, output[span[0]:span[1]]))

    text = output
    for (a, b), new in sorted(edits.items(), reverse=True):
        text = text[:a] + new + text[b:]
    # comprobación final: cada término perdido vuelve a estar, sin duplicarse
    tf = [_fold(m.group(0)) for m in _TOKEN_RE.finditer(text)]
    for _, term in lost:
        st = stems[term]
        if term not in missing and sum(w.startswith(st) for w in tf) != sum(w.startswith(st) for w in sf):
            missing.append(term)
    if missing:
        return RestoreResult(text, False, "term_lost", restored, sorted(set(missing)))
    return RestoreResult(text, True, None, restored)


def renumber(rep_output: str, rep_source: str, target_source: str) -> str:
    """Traslada la traducción de una frase representativa a otra hoja con la
    misma frase y otra numeración de marcadores: el k-ésimo marcador del origen
    representativo pasa a ser el k-ésimo del origen de destino."""
    a, b = _MARKER_RE.findall(rep_source), _MARKER_RE.findall(target_source)
    if len(a) != len(b):
        raise ValueError("frases con distinto número de marcadores")
    mapping = dict(zip(a, b))
    return _MARKER_RE.sub(lambda m: mapping.get(m.group(0), m.group(0)), rep_output)
