from __future__ import annotations

import math

import pytest

from bc3param.param.ast import (
    Assign, AuxPercent, Binary, Call, Const, Decomp, Index, Num, NumVar, ParamDef, Price, Str,
    Text, TextList, TextVar, Unary,
)
from bc3param.param.parser import ParseError, parse_expression, parse_family, split_top_level


def test_precedence_arithmetic_and_comparison():
    e = parse_expression("%N(%B,%A)*(%C=a)*%K(%D)*0.10")
    assert isinstance(e, Binary) and e.op == "*"
    assert e.right == Num(0.10)
    inner = e.left.left  # %N(...)*(%C=a)
    assert inner.right == Binary("=", NumVar("C"), Const("a"))
    assert inner.left == Index(NumVar("N"), (NumVar("B"), NumVar("A")))


def test_logical_precedence_or_lower_than_and_lower_than_cmp():
    e = parse_expression("%A=a & %B<>b @ %C>c")
    assert e.op == "@"
    assert e.left.op == "&"
    assert e.left.left == Binary("=", NumVar("A"), Const("a"))
    assert e.right == Binary(">", NumVar("C"), Const("c"))


def test_string_times_condition_and_concat():
    e = parse_expression('"normal" * (%B=a) + "rocoso" * (%B=c)')
    assert e.op == "+" and e.left.op == "*" and e.left.left == Str("normal")


def test_unary_bang_and_minus_and_power():
    e = parse_expression("!(%A=b) + -2^2")
    assert e.left == Unary("!", Binary("=", NumVar("A"), Const("b")))
    assert e.right == Unary("-", Binary("^", Num(2), Num(2)))


def test_calls_and_pi():
    e = parse_expression("ATOF($A)/1000 + ROUND(PI, 2)")
    assert e.left == Binary("/", Call("ATOF", (TextVar("A"),)), Num(1000))
    assert e.right.fn == "ROUND" and e.right.args[0].value == pytest.approx(math.pi)


def test_parse_errors():
    with pytest.raises(ParseError):
        parse_expression("%A +")
    with pytest.raises(ParseError):
        parse_expression("(1")
    with pytest.raises(ParseError):
        parse_expression("1 2")


def test_split_top_level():
    assert split_top_level('"a,b", (1,2), $L(b,%C) + "x"', ",") == ['"a,b"', ' (1,2)', ' $L(b,%C) + "x"']


FAMILY = (
    "\\Nº TUBOS \\ 2 \\ 4 \\\n"
    "\\TIPO DE TERRENO \\Normal\\Rocoso\\\n"
    "$E= \"Combinación inexistente\"\n"
    "%E= (%A=a & %B=b)\n"
    "%K(2)=1.1,1.2\n"
    "%M(2,2)= 0.178,  0.219,  # normal\n"
    "\t 0.211,  0.248   # rocoso\n"
    "$G(2)=\"D\",\"N\"\n"
    "$K= \"normal\" * (%B=a) + \"rocoso\" * (%B=b)\n"
    "MOC0000600        :  %M(%B,%A)*%K(%A)\n"
    "MN10010001  :  1*%A : 2\n"
    "%%CIND: 0.06\n"
    "%%: 3\n"
    "%: 2\n"
    ":: 12.5\n"
    "\\PLIEGO\\C3\\Rellenar\\\n"
    "\\RESUMEN\\Canalización de $A T, $K. ($G(%B))\\\n"
    "\\TEXTO\\Canalización de $A tubos $K.\n"
    "Trabajo: $B\\\n"
)


def test_parse_family_statements():
    fam = parse_family("OEB020$", FAMILY)
    assert fam.code == "OEB020$"
    assert [p.var for p in fam.params] == ["A", "B"]
    assert fam.params[0] == ParamDef("A", "Nº TUBOS", (" 2 ", " 4 "), 1)
    assert fam.params[1].options == ("Normal", "Rocoso")
    st = fam.statements
    assert st[0] is fam.params[0] and st[1] is fam.params[1]
    assert st[2] == Assign("$", "E", None, (Str("Combinación inexistente"),), 3)
    assert isinstance(st[3], Assign) and st[3].name == "E" and st[3].kind == "%"
    assert st[4] == Assign("%", "K", (2,), (Num(1.1), Num(1.2)), 5)
    assert st[5].dims == (2, 2) and [v.value for v in st[5].values] == [0.178, 0.219, 0.211, 0.248]
    assert st[6] == Assign("$", "G", (2,), (Str("D"), Str("N")), 8)
    assert isinstance(st[7], Assign) and st[7].dims is None and len(st[7].values) == 1
    assert st[8] == Decomp("MOC0000600", Binary("*", Index(NumVar("M"), (NumVar("B"), NumVar("A"))), Index(NumVar("K"), (NumVar("A"),))), None, 10)
    assert st[9].code_template == "MN10010001" and st[9].factor == Num(2)
    assert st[10] == Decomp("%%CIND", Num(0.06), None, 12)
    assert st[11] == AuxPercent(Num(3), True, 13)
    assert st[12] == AuxPercent(Num(2), False, 14)
    assert st[13] == Price(Num(12.5), 15)
    assert st[14] == TextList("PLIEGO", ("C3", "Rellenar"), 16)
    assert st[15] == Text("RESUMEN", "Canalización de $A T, $K. ($G(%B))", 17)
    assert st[16] == Text("TEXTO", "Canalización de $A tubos $K.\nTrabajo: $B", 18)


def test_parse_family_label_aliases_and_spaces():
    fam = parse_family("X$", "\\ R \\ corto \\\n\\ T \\ largo \\\n\\ C \\ ayuda \\\n")
    assert [s.label for s in fam.statements] == ["RESUMEN", "TEXTO", "COMENTARIO"]
    assert fam.statements[0].template == " corto "


def test_parse_family_errors_carry_code_and_line():
    with pytest.raises(ParseError) as exc:
        parse_family("X$", "\\P1\\a\\\n%M(2,2)=1,2,3\n")
    assert exc.value.family == "X$" and exc.value.line_no == 2
    with pytest.raises(ParseError):
        parse_family("X$", "esto no es nada\n")
    with pytest.raises(ParseError):
        parse_family("X$", "MN1: %A +\n")
    too_many = "".join(f"\\P{i}\\a\\\n" for i in range(11))
    with pytest.raises(ParseError):
        parse_family("X$", too_many)
