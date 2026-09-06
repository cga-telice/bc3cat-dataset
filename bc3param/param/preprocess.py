"""Turn the raw text of a ~P record into statements (FIEBDC-3 reading procedure)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Statement:
    text: str
    line_no: int
    is_label: bool


_CONTINUE_CHARS = set("+-*/^@&<>=!(,")
_NEW_STATEMENT = re.compile(
    r"^(\\|::|%%?:|[%$][A-Z]\s*(\([^)]*\))?\s*=|[A-Za-z0-9_%.]+\s*:)"
)


def _strip_comment(line: str, in_quote: bool) -> tuple[str, bool]:
    """Remove ``#...`` outside quotes; return (text, quote state at end of line)."""
    out: list[str] = []
    quote = in_quote
    for ch in line:
        if ch == '"':
            quote = not quote
        elif ch == "#" and not quote:
            break
        out.append(ch)
    return "".join(out), quote


def _strip_label_comment(line: str) -> str:
    """In a label line only a ``#`` after the last backslash is a comment."""
    last = line.rfind("\\")
    if last < 0:
        return line
    pos = line.find("#", last)
    return line[:pos] if pos >= 0 else line


def statements(body: str) -> list[Statement]:
    result: list[Statement] = []
    buf = ""
    start = 0
    in_quote = False
    in_label = False

    def close() -> None:
        nonlocal buf, in_label
        text = buf.strip()
        if not in_label:
            text = text.rstrip("\\").rstrip()
        if text:
            result.append(Statement(text, start, in_label))
        buf = ""
        in_label = False

    for n, raw in enumerate(body.split("\n"), 1):
        line = raw.replace("\t", " ")
        if in_label:
            line = _strip_label_comment(line)
            buf += "\n" + line
            if line.rstrip().endswith("\\"):
                close()
            continue

        stripped = line.strip()
        if buf and not in_quote and buf.endswith(",") and _NEW_STATEMENT.match(stripped):
            close()

        if not buf and stripped.startswith("\\"):
            stripped = _strip_label_comment(stripped).strip()
            start = n
            buf = stripped
            in_label = True
            if len(stripped) > 1 and stripped.endswith("\\"):
                close()
            continue

        was_in_quote = in_quote
        line, in_quote = _strip_comment(line, in_quote)
        stripped = line.strip()
        if not stripped:
            continue
        if not buf:
            start = n
            buf = stripped
        else:
            buf += ("\n" if was_in_quote else " ") + stripped
        if in_quote or stripped[-1] in _CONTINUE_CHARS:
            continue
        close()

    if buf:
        close()
    return result
