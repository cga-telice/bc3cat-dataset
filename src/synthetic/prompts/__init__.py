"""Per-type Spanish prompt library for Stage-A LLM variant proposing.

Twelve prompts, one per ``ModificationType``. Each prompt is a UTF-8
text file under this package directory; the loader returns the raw
string for the C3 variant proposer to format with per-concept slots.

The loader is the *only* runtime surface of this package — the prompts
themselves are static data, not code, and remain in plain .txt files
so domain reviewers can edit them without touching Python.
"""

from __future__ import annotations

from pathlib import Path

from ..taxonomy import ModificationType


PROMPT_DIR: Path = Path(__file__).parent


PROMPT_FILENAMES: dict[ModificationType, str] = {
    mtype: f"{mtype.value}.txt" for mtype in ModificationType
}


def load_prompt(modification_type: ModificationType) -> str:
    """Read the prompt file for ``modification_type`` and return its
    UTF-8 contents verbatim. Placeholder substitution is the caller's
    responsibility (likely the C3 variant proposer's `str.format_map`).

    Raises
    ------
    KeyError
        If ``modification_type`` is not a member of ``ModificationType``.
    FileNotFoundError
        If the corresponding prompt file is missing on disk.
    """
    # ``ModificationType`` subclasses ``str``, so a plain string equal to an
    # enum value would otherwise hash-and-equal its way into the dict. The
    # spec's contract is enum-only — coerce the failure case explicitly.
    if not isinstance(modification_type, ModificationType):
        raise KeyError(modification_type)
    filename = PROMPT_FILENAMES[modification_type]
    return (PROMPT_DIR / filename).read_text(encoding="utf-8")
