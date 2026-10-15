"""Sinónimos de los términos del glosario en la BT (idea de César, 2026-10-16).

La BT por frases restaura los términos del oficio («arqueta», «poste»,
«desmonte»…) para que el traductor no los estropee; así quedan siempre
idénticos al gold, lo que facilita la búsqueda léxica y resta realismo. Aquí,
con semilla y probabilidad ``p``, cada aparición se sustituye por una
alternativa aprobada (``data/synthetic/bt_OE/OE_glossary_approved.json``:
generación, auditoría en tres rondas y decisiones de César).

Reglas:
* nunca dentro de un marcador de valor (``[n]``): los valores van aparte;
* no se usa una alternativa que ya esté en el texto (p. ej. «firme» →
  «pavimento» en «del firme y del pavimento»); si todas están, no se sustituye;
* se copia la mayúscula inicial y, si el término está en plural, se pluraliza la
  primera palabra de la alternativa (los pequeños errores de concordancia se
  aceptan, decisión de César).
"""

from __future__ import annotations

import random
import unicodedata
import zlib
from typing import Mapping, Sequence

from .bt_masking import glossary_spans


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in t if not unicodedata.combining(c))


def _pluralise_first(text: str) -> str:
    head, _, rest = text.partition(" ")
    head = head + ("s" if head[-1:].lower() in "aeiouáéíóú" else "es")
    return head + (" " + rest if rest else "")


def substitute_glossary(text: str, alternatives: Mapping[str, Sequence[str]], *,
                        seed: int, key: str, p: float,
                        context: str | None = None) -> tuple[str, list[dict]]:
    """Devuelve el texto y la lista de sustituciones ``{term, original, new}``.
    ``context`` es el texto con los valores restaurados: la presencia de una
    alternativa se comprueba ahí (una sigla como PRFV puede ir enmascarada)."""
    occ = []
    for term in alternatives:
        for a, b in glossary_spans(text, [term]):
            occ.append((a, b, term))
    occ.sort()
    taken = _fold(text + " " + (context or ""))
    edits, subs = [], []
    for i, (a, b, term) in enumerate(occ):
        rng = random.Random(seed ^ zlib.crc32(f"{key}|{i}|{term}".encode("utf-8")))
        if rng.random() >= p:
            continue
        options = [alt for alt in sorted(alternatives[term]) if _fold(alt) not in taken]
        if not options:
            continue
        new = rng.choice(options)
        original = text[a:b]
        if _fold(original) != _fold(term) and _fold(original).endswith("s"):
            new = _pluralise_first(new)
        if original[:1].isupper():
            new = new[:1].upper() + new[1:]
        taken += " " + _fold(new)
        edits.append((a, b, new))
        subs.append({"term": term, "original": original, "new": new})
    for a, b, new in sorted(edits, reverse=True):
        text = text[:a] + new + text[b:]
    return text, subs
