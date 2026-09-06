"""Option letters (a-z, A-Z, 0-9 = 1..62) and derived concept codes."""
from __future__ import annotations

from typing import Iterable

LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def letter_to_index(ch: str) -> int:
    """'a' -> 1 ... 'z' -> 26, 'A' -> 27 ... '9' -> 62."""
    pos = LETTERS.find(ch)
    if len(ch) != 1 or pos < 0:
        raise ValueError(f"not an option letter: {ch!r}")
    return pos + 1


def index_to_letter(index: int) -> str:
    if not 1 <= index <= len(LETTERS):
        raise ValueError(f"option index out of range 1..{len(LETTERS)}: {index}")
    return LETTERS[index - 1]


def derived_code(family_code: str, selection: Iterable[int]) -> str:
    """``OEB020$`` + (2,2,2,1,1) -> ``OEB020bbbaa``."""
    return family_code.rstrip("$") + "".join(index_to_letter(i) for i in selection)


def split_derived_code(code: str, families: Iterable[str]) -> tuple[str, tuple[int, ...]]:
    """Find the family a derived code belongs to (longest matching stem wins)."""
    known = set(families)
    for length in range(len(code) - 1, 0, -1):
        family = code[:length] + "$"
        if family in known:
            return family, tuple(letter_to_index(ch) for ch in code[length:])
    raise ValueError(f"no parametric family matches {code!r}")
