"""Sequential interpreter for one option selection of a parametric family."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence, Union

from .ast import (
    Assign, AuxPercent, Binary, Call, Const, Decomp, Expr, Family, Index, Num, NumVar, ParamDef,
    Price, Str, Text, TextList, TextVar, Unary,
)
from .codes import index_to_letter, letter_to_index
from .parser import parse_expression

DEFAULT_ERROR = "Combinación no válida"
_ATOF_RE = re.compile(r"^\s*[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)")
_VAR_RE = re.compile(r"%%|([%$])([A-Z])(?:\(([^()]*)\))?")
_CMP = {"<", ">", "<=", ">=", "=", "<>"}


class EvalError(Exception):
    pass


def atof(text: str) -> float:
    m = _ATOF_RE.match(text)
    if not m:
        return 0.0
    return float(m.group().strip().replace(",", "."))


def ftoa(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


@dataclass
class Matrix:
    dims: tuple[int, ...]
    values: list

    def get(self, idx: tuple[int, ...]):
        if len(idx) != len(self.dims):
            raise EvalError(f"matrix needs {len(self.dims)} indices, got {len(idx)}")
        flat = 0
        for n, (k, d) in enumerate(zip(idx, self.dims), 1):
            if not 1 <= k <= d:
                raise EvalError(f"index {k} out of range 1..{d} in dimension {n}")
            flat = flat * d + (k - 1)
        return self.values[flat]


Value = Union[float, str, Matrix]


@dataclass
class Evaluation:
    valid: bool = True
    error: str | None = None
    resumen: str | None = None
    texto: str | None = None
    comment: str | None = None
    lines: list[tuple[str, float]] = field(default_factory=list)
    direct_price: float | None = None
    aux_percent: float | None = None
    texts: dict[str, tuple[str, ...]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class Evaluator:
    def __init__(self, family: Family, selection: Sequence[int]) -> None:
        if len(selection) != len(family.params):
            raise EvalError(f"{family.code}: expected {len(family.params)} options, got {len(selection)}")
        self.family = family
        self.selection = tuple(selection)
        self.num: dict[str, Value] = {}
        self.text: dict[str, Value] = {}
        for param, k in zip(family.params, self.selection):
            if not 1 <= k <= len(param.options):
                raise EvalError(f"{family.code}: option {k} out of range for parameter {param.var}")
            self.num[param.var] = float(k)
            self.text[param.var] = param.options[k - 1]
        self.result = Evaluation()
        self._lines: dict[str, float] = {}
        self._warned: set[str] = set()

    # ---- driver ----------------------------------------------------------
    def run(self) -> Evaluation:
        for st in self.family.statements:
            self._exec(st)
        # first-occurrence order; repeated codes were summed; exact zeros are dropped here,
        # quantities that round to zero are dropped by the pricer.
        self.result.lines = [(code, qty) for code, qty in self._lines.items() if qty != 0]
        return self.result

    def _warn(self, message: str) -> None:
        if message not in self._warned:
            self._warned.add(message)
            self.result.warnings.append(message)

    def _exec(self, st) -> None:
        if isinstance(st, ParamDef):
            return
        if isinstance(st, Assign):
            values = [self._eval(v) for v in st.values]
            if st.kind == "%":
                values = [self._to_num(v) for v in values]
                store = self.num
            else:
                values = [self._to_text(v) for v in values]
                store = self.text
            if st.dims:
                value: Value = Matrix(st.dims, values)
            elif len(values) == 1:
                value = values[0]
            else:
                value = Matrix((len(values),), values)
            store[st.name] = value
            if st.kind == "%" and st.name == "E" and not isinstance(value, Matrix) and self._truthy(value):
                if self.result.valid:
                    self.result.valid = False
                    message = self.text.get("E")
                    self.result.error = message if isinstance(message, str) and message else DEFAULT_ERROR
        elif isinstance(st, Decomp):
            code = self._substitute(st.code_template)
            qty = self._to_num(self._eval(st.expr))
            if st.factor is not None:
                qty *= self._to_num(self._eval(st.factor))
            self._lines[code] = self._lines.get(code, 0.0) + qty
        elif isinstance(st, Price):
            self.result.direct_price = self._to_num(self._eval(st.expr))
        elif isinstance(st, AuxPercent):
            v = self._to_num(self._eval(st.expr))
            self.result.aux_percent = v if st.per_unit else v / 100.0
        elif isinstance(st, Text):
            rendered = self._render(st.template)
            if st.label == "RESUMEN":
                self.result.resumen = rendered
            elif st.label == "TEXTO":
                self.result.texto = rendered
            else:
                self.result.comment = rendered
        elif isinstance(st, TextList):
            self.result.texts[st.label] = tuple(self._render(t) for t in st.items)

    # ---- values ----------------------------------------------------------
    @staticmethod
    def _truthy(v: Value) -> bool:
        if isinstance(v, str):
            return v != ""
        if isinstance(v, Matrix):
            raise EvalError("matrix used as a condition")
        return v != 0

    @staticmethod
    def _to_num(v: Value) -> float:
        if isinstance(v, str):
            return atof(v)
        if isinstance(v, Matrix):
            raise EvalError("matrix used as a number")
        return float(v)

    @staticmethod
    def _to_text(v: Value) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, Matrix):
            raise EvalError("matrix used as text")
        return ftoa(v)

    def _lookup(self, kind: str, name: str) -> Value:
        store = self.num if kind == "%" else self.text
        if name in store:
            return store[name]
        self._warn(f"undefined variable {kind}{name}")
        return 0.0 if kind == "%" else ""

    def _index_value(self, kind: str, name: str, args: Sequence[Value]) -> Value:
        value = self._lookup(kind, name)
        if not isinstance(value, Matrix):
            if not args:
                return value
            raise EvalError(f"{kind}{name} is not a matrix")
        if not args:
            if len(value.values) == 1:
                return value.values[0]
            raise EvalError(f"{kind}{name} is a matrix and needs indices")
        idx = tuple(int(round(self._to_num(a))) for a in args)
        return value.get(idx)

    # ---- expressions -----------------------------------------------------
    def _eval(self, e: Expr) -> Value:
        if isinstance(e, Num):
            return e.value
        if isinstance(e, Str):
            return e.value
        if isinstance(e, Const):
            return float(letter_to_index(e.letter))
        if isinstance(e, NumVar):
            return self._index_value("%", e.name, ())
        if isinstance(e, TextVar):
            return self._index_value("$", e.name, ())
        if isinstance(e, Index):
            kind = "%" if isinstance(e.var, NumVar) else "$"
            return self._index_value(kind, e.var.name, [self._eval(a) for a in e.args])
        if isinstance(e, Call):
            return self._call(e.fn, [self._eval(a) for a in e.args])
        if isinstance(e, Unary):
            v = self._eval(e.operand)
            if e.op == "!":
                return 0.0 if self._truthy(v) else 1.0
            return -self._to_num(v)
        if isinstance(e, Binary):
            return self._binary(e.op, self._eval(e.left), self._eval(e.right))
        raise EvalError(f"unknown node {e!r}")

    def _binary(self, op: str, l: Value, r: Value) -> Value:
        if op == "@":
            return 1.0 if self._truthy(l) or self._truthy(r) else 0.0
        if op == "&":
            return 1.0 if self._truthy(l) and self._truthy(r) else 0.0
        if op in _CMP:
            if isinstance(l, str) and isinstance(r, str):
                a, b = l, r
            else:
                a, b = self._to_num(l), self._to_num(r)
            ok = {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b, "=": a == b, "<>": a != b}[op]
            return 1.0 if ok else 0.0
        if op == "+":
            if isinstance(l, str) or isinstance(r, str):
                return self._to_text(l) + self._to_text(r)
            return self._to_num(l) + self._to_num(r)
        if op == "*":
            if isinstance(l, str) and not isinstance(r, str):
                return l if self._to_num(r) != 0 else ""
            if isinstance(r, str) and not isinstance(l, str):
                return r if self._to_num(l) != 0 else ""
            return self._to_num(l) * self._to_num(r)
        a, b = self._to_num(l), self._to_num(r)
        if op == "-":
            return a - b
        if op == "/":
            if b == 0:
                raise EvalError("division by zero")
            return a / b
        if op == "^":
            return a ** b
        raise EvalError(f"unknown operator {op}")

    def _call(self, fn: str, args: list[Value]) -> Value:
        if fn == "ATOF":
            return atof(self._to_text(args[0]))
        if fn == "FTOA":
            return ftoa(self._to_num(args[0]))
        n = [self._to_num(a) for a in args]
        if fn == "ABS":
            return abs(n[0])
        if fn == "INT":
            return float(math.trunc(n[0]))
        if fn == "ROUND":
            places = int(n[1]) if len(n) > 1 else 0
            return float(Decimal(repr(n[0])).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))
        if fn == "SIN":
            return math.sin(math.radians(n[0]))
        if fn == "COS":
            return math.cos(math.radians(n[0]))
        if fn == "TAN":
            return math.tan(math.radians(n[0]))
        if fn == "ASIN":
            return math.degrees(math.asin(n[0]))
        if fn == "ACOS":
            return math.degrees(math.acos(n[0]))
        if fn == "ATAN":
            return math.degrees(math.atan(n[0]))
        if fn == "ATAN2":
            return math.degrees(math.atan2(n[0], n[1]))
        if fn == "SQRT":
            if n[0] < 0:
                raise EvalError("square root of negative number")
            return math.sqrt(n[0])
        raise EvalError(f"unknown function {fn}")

    # ---- substitution in templates --------------------------------------
    def _template_arg(self, text: str) -> Value:
        return self._eval(parse_expression(text))

    def _substitute(self, template: str) -> str:
        def repl(m: re.Match) -> str:
            if m.group(0) == "%%":
                return "%"
            kind, name, args_text = m.group(1), m.group(2), m.group(3)
            args = [self._template_arg(a) for a in args_text.split(",")] if args_text is not None else []
            value = self._index_value(kind, name, args)
            if kind == "$":
                return self._to_text(value)
            index = int(round(self._to_num(value)))
            try:
                return index_to_letter(index)
            except ValueError:
                raise EvalError(f"%{name} = {index} cannot be written as an option letter") from None

        return _VAR_RE.sub(repl, template)

    def _render(self, template: str) -> str:
        text = self._substitute(template)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        return "\n".join(lines).strip()
