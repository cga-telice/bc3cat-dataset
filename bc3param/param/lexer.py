"""Tokenizer for FIEBDC-3 parametric expressions."""
from __future__ import annotations

import re
from dataclasses import dataclass


class LexError(Exception):
    pass


@dataclass(frozen=True)
class Token:
    kind: str  # NUMBER STRING LETTER IDENT NUMVAR TEXTVAR OP LPAREN RPAREN COMMA EOF
    value: str
    pos: int


FUNCTIONS = {"ABS", "INT", "ROUND", "SIN", "COS", "TAN", "ASIN", "ACOS", "ATAN", "ATAN2", "SQRT", "ATOF", "FTOA"}

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<NUMBER>\d+(?:\.\d*)?|\.\d+)
  | (?P<STRING>"(?:[^"]|"")*")
  | (?P<NUMVAR>%[A-Z])
  | (?P<TEXTVAR>\$[A-Z])
  | (?P<OP><>|<=|>=|[-+*/^@&<>=!])
  | (?P<LPAREN>\()
  | (?P<RPAREN>\))
  | (?P<COMMA>,)
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.X,
)


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise LexError(f"unexpected character {text[pos]!r} at position {pos}")
        kind = m.lastgroup
        value = m.group()
        pos = m.end()
        if kind == "ws":
            continue
        if kind == "STRING":
            tokens.append(Token("STRING", value[1:-1].replace('""', '"'), m.start()))
        elif kind == "IDENT":
            if len(value) == 1:
                tokens.append(Token("LETTER", value, m.start()))
            elif value.upper() in FUNCTIONS or value.upper() == "PI":
                tokens.append(Token("IDENT", value.upper(), m.start()))
            else:
                raise LexError(f"unknown identifier {value!r} at position {m.start()}")
        else:
            tokens.append(Token(kind, value, m.start()))
    tokens.append(Token("EOF", "", len(text)))
    return tokens
