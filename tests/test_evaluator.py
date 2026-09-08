from __future__ import annotations

import pytest

from bc3param.param.evaluator import EvalError, Evaluator, Matrix, atof, ftoa
from bc3param.param.parser import parse_family

OEB = (
    "\\Nº TUBOS \\ 2 \\ 4 \\ 6 \\\n"
    "\\TIPO DE TERRENO \\Normal\\Bajo vías\\Con topo\\\n"
    "\\TRABAJO\\Diurno\\Nocturno\\\n"
    "\\BANDA\\ i >= 5 horas\\i < 3 horas\\\n"
    "$E= \"Combinación inexistente en la base de datos\"\n"
    "%E= (%A<c & %B=c)\n"
    "%K(2)=1.1,1.2\n"
    "%L(3)=2,4,6\n"
    "#          2       4       6\n"
    "%M(3,3)= 0.178,  0.178,  0.219,  # Terreno normal\n"
    "\t 0.372,  0.372,  0.455,  # Bajo vías\n"
    "\t 0.000,  0.000,  3.309   # Con topo\n"
    "MOC0000600        :  %M(%B,%A)*(%C=a)*%K(%D)\n"
    "MOC0000601        :  %M(%B,%A)*(%C=b)*%K(%D)\n"
    "MOC0000600        :  0.5*(%C=b)\n"
    "MN10010001  :  1*%L(%A)\n"
    "MN20010617  :  %B=c\n"
    "%%CIND: 0.06\n"
    "$G(2)=\"D\",\"N\"\n"
    "$H(2)=\">5\",\"<3\"\n"
    "$K= \"normal\" * (%B=a) + \"bajo vías\" * (%B=b) + \"con topo\" * (%B=c)\n"
    "$M= \"Incluso pozo de ataque.\" * (%B=c)\n"
    "\\RESUMEN\\Canalización hormigonada de $A T, PVC 110 mm, $K. ($G(%C)/$H(%D))\\\n"
    "\\TEXTO\\Canalización hormigonada de $A tubos de PVC $K, incluso relleno. $M\n"
    "Trabajo: $C\n"
    "Banda de mantenimiento: $D \\\n"
)


def run(body: str, selection):
    return Evaluator(parse_family("OEB020$", body), selection).run()


def test_matrix_indexing_is_one_based():
    m = Matrix((2, 3), [1, 2, 3, 4, 5, 6])
    assert m.get((1, 1)) == 1 and m.get((2, 3)) == 6 and m.get((1, 3)) == 3
    with pytest.raises(EvalError):
        m.get((0, 1))
    with pytest.raises(EvalError):
        m.get((3, 1))
    with pytest.raises(EvalError):
        m.get((1,))


def test_full_evaluation_of_valid_selection():
    ev = run(OEB, (2, 2, 2, 1))  # 4 tubos, bajo vías, nocturno, >=5h
    assert ev.valid and ev.error is None
    # first-occurrence order, repeated codes summed, zero quantities dropped
    assert ev.lines == [
        ("MOC0000600", 0.5), ("MOC0000601", pytest.approx(0.372 * 1.1)), ("MN10010001", 4.0), ("%CIND", 0.06),
    ]
    assert ev.resumen == "Canalización hormigonada de 4 T, PVC 110 mm, bajo vías. (N/>5)"
    assert ev.texto == (
        "Canalización hormigonada de 4 tubos de PVC bajo vías, incluso relleno.\n"
        "Trabajo: Nocturno\n"
        "Banda de mantenimiento: i >= 5 horas"
    )
    assert ev.warnings == []


def test_repeated_codes_are_summed_and_zero_lines_dropped():
    ev = run(OEB, (1, 1, 1, 2))  # diurno: MOC0000600 twice (second is 0.5*0)
    codes = [c for c, _ in ev.lines]
    assert codes == ["MOC0000600", "MN10010001", "%CIND"]
    assert dict(ev.lines)["MOC0000600"] == pytest.approx(0.178 * 1.2)


def test_exclusion_marks_invalid_with_message_but_still_renders_text():
    ev = run(OEB, (1, 3, 1, 1))  # 2 tubos con topo -> %E true
    assert not ev.valid
    assert ev.error == "Combinación inexistente en la base de datos"
    assert ev.resumen.startswith("Canalización hormigonada de 2 T")


def test_exclusion_default_message():
    ev = run("\\PAR\\a\\b\\\n%E= %A=a\n", (1,))
    assert ev.error == "Combinación no válida"


def test_letters_in_code_templates_and_percent_escape():
    # note: single-letter labels R T C P K F are reserved aliases, so parameters use longer names
    body = "\\PAR\\x\\y\\\n\\Q\\u\\v\\w\\\nMN%A%B: 1\n%%VOL: 0.2\n"
    ev = run(body, (2, 3))
    assert ev.lines == [("MNbc", 1.0), ("%VOL", 0.2)]


def test_arithmetic_on_parameters_is_one_based():
    body = "\\N\\0\\1\\2\\\n%P(3)= 0, 5, 10\nMOE1: 55.857 + %P(%A)*8.379 + (%A-1)*16.757\n"
    assert dict(run(body, (1,)).lines)["MOE1"] == pytest.approx(55.857)
    assert dict(run(body, (3,)).lines)["MOE1"] == pytest.approx(55.857 + 10 * 8.379 + 2 * 16.757)


def test_sequential_redefinition():
    body = "\\PAR\\a\\b\\\n%T(2)=1,2\nMN1: %T(%A)\n%T(2)=10,20\nMN2: %T(%A)\n"
    assert run(body, (2,)).lines == [("MN1", 2.0), ("MN2", 20.0)]


def test_text_arrays_with_expressions_and_literal_index():
    body = (
        "\\OP\\Suministro\\Montaje\\\n\\TENSION\\10 kV\\20 kV\\\n"
        "$Y(2)=\"a\",\"b\"\n"
        "$P(1) = $A + \" de interruptor \" + $B + \" \" + $Y(%B)\n"
        "\\TEXTO\\ $P(1)\nFin.\\\n"
    )
    ev = run(body, (2, 1))
    assert ev.texto == "Montaje de interruptor 10 kV a\nFin."


def test_undefined_variables_warn_and_default():
    ev = run("\\PAR\\a\\\nMN1: %Z + 1\n\\RESUMEN\\x $Q y\\\n", (1,))
    assert ev.lines == [("MN1", 1.0)]
    assert ev.resumen == "x y"
    assert any("Z" in w for w in ev.warnings) and any("Q" in w for w in ev.warnings)


def test_functions_and_string_comparison():
    body = (
        "\\D\\ 110 \\ 160 \\\n"
        "%P=ATOF($A)/1000\n"
        "MN1: ROUND(%P*3, 2) + INT(2.7) + ABS(-1) + SQRT(16) + ($A=$A) + ($A<>$A)\n"
        "$Q= FTOA(%P) + \" m\"\n\\RESUMEN\\$Q\\\n"
    )
    ev = run(body, (2,))
    assert dict(ev.lines)["MN1"] == pytest.approx(0.48 + 2 + 1 + 4 + 1)
    assert ev.resumen == "0.16 m"


def test_bang_operator_and_or():
    body = "\\A\\a\\b\\\n\\B\\a\\b\\\nMN1: !(%A=b & %B=b) + 10*(%A=a @ %B=b)\n"
    assert dict(run(body, (2, 2)).lines)["MN1"] == 10.0
    assert dict(run(body, (1, 1)).lines)["MN1"] == 11.0


def test_price_and_aux_percent_statements():
    ev = run("\\A\\a\\\n:: 12.5\n%: 3\n", (1,))
    assert ev.direct_price == 12.5 and ev.aux_percent == pytest.approx(0.03)
    ev = run("\\A\\a\\\n%%: 0.04\n", (1,))
    assert ev.aux_percent == pytest.approx(0.04)


def test_selection_validation():
    fam = parse_family("X$", "\\A\\a\\b\\\n")
    with pytest.raises(EvalError):
        Evaluator(fam, (3,))
    with pytest.raises(EvalError):
        Evaluator(fam, (1, 1))


def test_index_out_of_range_is_eval_error():
    with pytest.raises(EvalError):
        run("\\A\\a\\b\\\n%P(1)=5\nMN1: %P(%A)\n", (2,))


def test_atof_and_ftoa_helpers():
    assert atof(" 2 ") == 2.0 and atof("1-5") == 1.0 and atof("6,5 kV") == 6.5 and atof("x") == 0.0
    assert ftoa(2.0) == "2" and ftoa(0.16) == "0.16" and ftoa(1234.5) == "1234.5"
