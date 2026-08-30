"""Mask meaning-critical invariants behind opaque sentinels.

Sprint 38.6-B. Long TEXTO templates die in validation because one corrupt
placeholder or digit kills a 150-word rewrite (pilot: 23 placeholder + 9
quantity drops of 47). Instead of asking a 14B model to copy ~15 numbers
and 8 placeholders faithfully at temperature 0.8, we replace them with
sentinels (``[[P1]]``, ``[[Q3]]``) the model is told to leave untouched,
and restore the exact literals afterwards. Quantity and placeholder
preservation become guaranteed by construction; the downstream validators
still run on the restored text as a belt-and-braces check.

Sentinels are ASCII (``[[..]]``) because unicode brackets get normalised
away by some models. ``P`` = placeholder (``$A``, ``$L(%C)``), ``Q`` =
quantity (number, number+unit, or digit-bearing code like ``HM-20``).

Pure functions, stdlib only. Used by :mod:`menu_diversity`.
"""

from __future__ import annotations

import re
from collections import Counter

from .slot_extractor import _UNIT_TOKENS

_PLACEHOLDER_PART = r"\$[A-Za-z0-9]+(?:\(%[A-Z]\))?"
# A whitespace-delimited token containing a digit ("220", "1,60", "HM-20",
# "4x40"), optionally followed by one unit word from the shared unit
# vocabulary ("m", "mm", "kV", "At."), which travels with its number.
# The unit peek excludes "$" so a placeholder following a number (e.g.
# "clase 5.6 ($L(%C)…") can never be swallowed as a pseudo-unit — it must
# stay available for the placeholder alternative to mask.
_QUANTITY_PART = r"[^\s\[\]]*\d[^\s\[\]]*(?:\s+(?P<unit>[^\s\d\[\]$]+?)\.?(?=\s|$|[,;:)]))?"

_MASK_RE = re.compile(rf"(?P<ph>{_PLACEHOLDER_PART})|(?P<qty>{_QUANTITY_PART})")
_SENTINEL_RE = re.compile(r"\[\[([PQ]\d+)\]\]")


def mask_invariants(text: str) -> tuple[str, dict[str, str]]:
    """Replace placeholders and quantities with ``[[Pn]]``/``[[Qn]]``.

    Returns ``(masked_text, mapping)`` where ``mapping`` maps sentinel id
    ("P1", "Q2", …) to the exact literal it replaced. Single combined
    pass so inserted sentinel digits are never re-masked. A trailing unit
    word is included in the quantity literal only if it is in
    :data:`slot_extractor._UNIT_TOKENS` (case-insensitive, optional dot).
    """
    mapping: dict[str, str] = {}
    counters = {"P": 0, "Q": 0}

    def _sub(m: re.Match) -> str:
        if m.group("ph") is not None:
            kind, literal = "P", m.group("ph")
        else:
            kind, literal = "Q", m.group("qty")
            unit = m.group("unit")
            if unit is not None and unit.lower() not in _UNIT_TOKENS:
                # The peeked word is not a unit — put it back.
                literal = literal[: literal.rfind(unit)].rstrip()
                trailing = m.group("qty")[len(literal):]
                counters[kind] += 1
                sid = f"{kind}{counters[kind]}"
                mapping[sid] = literal
                return f"[[{sid}]]{trailing}"
        counters[kind] += 1
        sid = f"{kind}{counters[kind]}"
        mapping[sid] = literal
        return f"[[{sid}]]"

    return _MASK_RE.sub(_sub, text), mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    """Restore the exact literals. Unknown sentinels are left in place —
    call :func:`check_sentinels` first to fail loud on them."""
    return _SENTINEL_RE.sub(lambda m: mapping.get(m.group(1), m.group(0)), text)


def check_sentinels(text: str, mapping: dict[str, str]) -> None:
    """Every sentinel of ``mapping`` exactly once in ``text``, and no
    sentinel that is not in ``mapping``. Raises ``ValueError`` starting
    with ``sentinels_not_preserved`` otherwise."""
    found = Counter(_SENTINEL_RE.findall(text))
    expected = Counter(mapping.keys())
    if found != expected:
        missing = sorted((expected - found).keys())
        extra = sorted((found - expected).keys())
        raise ValueError(
            f"sentinels_not_preserved: missing={missing} extra_or_dup={extra}"
        )
