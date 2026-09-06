"""Recursive-descent parser: expressions and whole ~P families."""
from __future__ import annotations

import math
import re
from functools import lru_cache

from .ast import (
    Assign, AuxPercent, Binary, Call, Const, Decomp, Expr, Family, Index, Num, NumVar, ParamDef,
    Price, Statement, Str, Text, TextList, TextVar, Unary,
)
from .lexer import FUNCTIONS, LexError, Token, tokenize
from .preprocess import statements as extract_statements

PARAM_VARS = "ABCDFGHIJK"
_LABEL_ALIASES = {"R": "RESUMEN", "T": "TEXTO", "C": "COMENTARIO", "P": "PLIEGO", "K": "CLAVES", "F": "COMERCIAL"}
_TEXT_LABELS = {"RESUMEN", "TEXTO", "COMENTARIO"}
_LIST_LABELS = {"PLIEGO", "CLAVES", "COMERCIAL"}
_LABEL_RE = re.compile(r"^\\\s*([^\\]*?)\s*\\(.*)\\$", re.S)
_ASSIGN_RE = re.compile(r"^([%$])([A-Z])\s*(?:\(([\d\s,]+)\))?\s*=(.*)$", re.S)
_CMP_OPS = {"<", ">", "<=", ">=", "=", "<>"}


class ParseError(Exception):
    def __init__(self, message: str, family: str = "", line_no: int = 0) -> None:
        super().__init__(f"{family} line {line_no}: {message}" if family else message)
        self.family = family
        self.line_no = line_no
        self.message = message


class _ExprParser:
    def __init__(self, tokens: list[Token]) -> None:
        self.toks = tokens
        self.i = 0

    def peek(self) -> Token:
        return self.toks[self.i]

    def advance(self) -> Token:
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, kind: str, value: str | None = None) -> Token:
        tok = self.peek()
        if tok.kind != kind or (value is not None and tok.value != value):
            want = value or kind
            raise ParseError(f"expected {want!r} but found {tok.value or 'end of expression'!r} at position {tok.pos}")
        return self.advance()

    def is_op(self, *values: str) -> bool:
        tok = self.peek()
        return tok.kind == "OP" and tok.value in values

    def parse(self) -> Expr:
        expr = self.parse_or()
        if self.peek().kind != "EOF":
            tok = self.peek()
            raise ParseError(f"unexpected {tok.value!r} at position {tok.pos}")
        return expr

    def parse_or(self) -> Expr:
        left = self.parse_and()
        while self.is_op("@"):
            self.advance()
            left = Binary("@", left, self.parse_and())
        return left

    def parse_and(self) -> Expr:
        left = self.parse_cmp()
        while self.is_op("&"):
            self.advance()
            left = Binary("&", left, self.parse_cmp())
        return left

    def parse_cmp(self) -> Expr:
        left = self.parse_add()
        while self.is_op(*_CMP_OPS):
            op = self.advance().value
            left = Binary(op, left, self.parse_add())
        return left

    def parse_add(self) -> Expr:
        left = self.parse_mul()
        while self.is_op("+", "-"):
            op = self.advance().value
            left = Binary(op, left, self.parse_mul())
        return left

    def parse_mul(self) -> Expr:
        left = self.parse_pow()
        while self.is_op("*", "/"):
            op = self.advance().value
            left = Binary(op, left, self.parse_pow())
        return left

    def parse_pow(self) -> Expr:
        left = self.parse_unary()
        while self.is_op("^"):
            self.advance()
            left = Binary("^", left, self.parse_unary())
        return left

    def parse_unary(self) -> Expr:
        # Unary operators bind looser than '^' so that -2^2 == -(2^2).
        if self.is_op("!", "-"):
            op = self.advance().value
            return Unary(op, self.parse_pow())
        if self.is_op("+"):
            self.advance()
            return self.parse_pow()
        return self.parse_atom()

    def parse_args(self) -> tuple[Expr, ...]:
        self.expect("LPAREN")
        args: list[Expr] = []
        if self.peek().kind != "RPAREN":
            args.append(self.parse_or())
            while self.peek().kind == "COMMA":
                self.advance()
                args.append(self.parse_or())
        self.expect("RPAREN")
        return tuple(args)

    def parse_atom(self) -> Expr:
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.advance()
            return Num(float(tok.value))
        if tok.kind == "STRING":
            self.advance()
            return Str(tok.value)
        if tok.kind == "LETTER":
            self.advance()
            return Const(tok.value)
        if tok.kind in ("NUMVAR", "TEXTVAR"):
            self.advance()
            var: NumVar | TextVar = NumVar(tok.value[1]) if tok.kind == "NUMVAR" else TextVar(tok.value[1])
            if self.peek().kind == "LPAREN":
                return Index(var, self.parse_args())
            return var
        if tok.kind == "IDENT":
            self.advance()
            if tok.value == "PI":
                return Num(math.pi)
            if tok.value in FUNCTIONS:
                return Call(tok.value, self.parse_args())
            raise ParseError(f"unknown function {tok.value!r}")
        if tok.kind == "LPAREN":
            self.advance()
            expr = self.parse_or()
            self.expect("RPAREN")
            return expr
        raise ParseError(f"unexpected {tok.value or 'end of expression'!r} at position {tok.pos}")


@lru_cache(maxsize=None)
def parse_expression(text: str) -> Expr:
    try:
        return _ExprParser(tokenize(text)).parse()
    except LexError as exc:
        raise ParseError(str(exc)) from exc


def split_top_level(text: str, sep: str) -> list[str]:
    """Split on ``sep`` occurrences that are outside quotes and parentheses."""
    parts: list[str] = []
    depth = 0
    quote = False
    current: list[str] = []
    for ch in text:
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(depth - 1, 0)
            elif ch == sep and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(ch)
    parts.append("".join(current))
    return parts


def _find_top_level(text: str, ch: str) -> int:
    quote = False
    for i, c in enumerate(text):
        if c == '"':
            quote = not quote
        elif c == ch and not quote:
            return i
    return -1


def _parse_statement(text: str, line_no: int, is_label: bool, params: list[ParamDef]) -> Statement | None:
    if is_label:
        m = _LABEL_RE.match(text)
        if not m:
            raise ParseError("malformed label statement")
        label = m.group(1)
        rest = m.group(2)
        canon = _LABEL_ALIASES.get(label, label)
        if canon in _TEXT_LABELS:
            return Text(canon, rest, line_no)
        if canon in _LIST_LABELS:
            return TextList(canon, tuple(rest.split("\\")), line_no)
        if len(params) >= len(PARAM_VARS):
            raise ParseError("more than 10 parameters")
        param = ParamDef(PARAM_VARS[len(params)], label, tuple(rest.split("\\")), line_no)
        params.append(param)
        return param
    if text.startswith("::"):
        return Price(parse_expression(text[2:]), line_no)
    if text.startswith("%%:"):
        return AuxPercent(parse_expression(text[3:]), True, line_no)
    if text.startswith("%:"):
        return AuxPercent(parse_expression(text[2:]), False, line_no)
    m = _ASSIGN_RE.match(text)
    if m:
        kind, name, dims_text, rhs = m.groups()
        values = split_top_level(rhs, ",")
        while values and not values[-1].strip():
            values.pop()
        exprs = tuple(parse_expression(v) for v in values)
        dims = tuple(int(d) for d in dims_text.split(",")) if dims_text else None
        if dims is not None:
            expected = math.prod(dims)
            if expected != len(exprs):
                raise ParseError(f"{kind}{name}{dims} declares {expected} values but {len(exprs)} given")
        if not exprs:
            raise ParseError(f"empty assignment to {kind}{name}")
        return Assign(kind, name, dims, exprs, line_no)
    colon = _find_top_level(text, ":")
    if colon > 0:
        code_template = re.sub(r"\s+", "", text[:colon])
        parts = split_top_level(text[colon + 1:], ":")
        expr = parse_expression(parts[0])
        factor = parse_expression(parts[1]) if len(parts) > 1 and parts[1].strip() else None
        return Decomp(code_template, expr, factor, line_no)
    try:
        parse_expression(text)
    except ParseError:
        raise ParseError(f"unrecognised statement {text[:60]!r}") from None
    # A bare expression with no assignment or code is a leftover in the source
    # (the ADIF catalogue has a couple); the viewer ignores them, so do we.
    return None


def parse_family(code: str, body: str) -> Family:
    family = Family(code)
    for st in extract_statements(body):
        try:
            node = _parse_statement(st.text, st.line_no, st.is_label, family.params)
        except ParseError as exc:
            raise ParseError(exc.message, code, st.line_no) from None
        if node is None:
            family.warnings.append(f"line {st.line_no}: ignored stray expression {st.text[:40]!r}")
            continue
        family.statements.append(node)
    return family
