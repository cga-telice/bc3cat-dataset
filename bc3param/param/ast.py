"""Typed nodes for the parametric sub-language."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

# ---- expressions -------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class Str:
    value: str


@dataclass(frozen=True)
class Const:
    """Option constant a..z / A..Z / 0..9 (1-based)."""

    letter: str


@dataclass(frozen=True)
class NumVar:
    name: str  # "A".."Z" (without the %)


@dataclass(frozen=True)
class TextVar:
    name: str  # "A".."Z" (without the $)


@dataclass(frozen=True)
class Index:
    var: Union[NumVar, TextVar]
    args: tuple["Expr", ...]


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple["Expr", ...]


@dataclass(frozen=True)
class Unary:
    op: str  # "!" or "-"
    operand: "Expr"


@dataclass(frozen=True)
class Binary:
    op: str  # + - * / ^ @ & < > <= >= = <>
    left: "Expr"
    right: "Expr"


Expr = Union[Num, Str, Const, NumVar, TextVar, Index, Call, Unary, Binary]

# ---- statements --------------------------------------------------------


@dataclass(frozen=True)
class ParamDef:
    var: str  # A B C D F G H I J K
    name: str
    options: tuple[str, ...]
    line_no: int


@dataclass(frozen=True)
class Assign:
    kind: str  # "%" numeric or "$" text
    name: str
    dims: tuple[int, ...] | None
    values: tuple[Expr, ...]
    line_no: int


@dataclass(frozen=True)
class Decomp:
    code_template: str
    expr: Expr
    factor: Expr | None
    line_no: int


@dataclass(frozen=True)
class Price:
    expr: Expr
    line_no: int


@dataclass(frozen=True)
class AuxPercent:
    expr: Expr
    per_unit: bool
    line_no: int


@dataclass(frozen=True)
class Text:
    label: str  # RESUMEN TEXTO COMENTARIO
    template: str
    line_no: int


@dataclass(frozen=True)
class TextList:
    label: str  # PLIEGO CLAVES COMERCIAL
    items: tuple[str, ...]
    line_no: int


Statement = Union[ParamDef, Assign, Decomp, Price, AuxPercent, Text, TextList]


@dataclass
class Family:
    code: str
    params: list[ParamDef] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)

    def option_counts(self) -> tuple[int, ...]:
        return tuple(len(p.options) for p in self.params)
