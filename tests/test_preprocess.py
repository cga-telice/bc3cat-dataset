from __future__ import annotations

from bc3param.param.preprocess import Statement, statements


def texts(body: str) -> list[str]:
    return [s.text for s in statements(body)]


def test_comments_blank_lines_and_tabs():
    body = "#1 Definición Parámetros\n\\ALTURA \\<3 m\\<6 m\\\n\n\t%O(4)=1.1,1.2,1.3,1 # banda\n"
    assert texts(body) == ["\\ALTURA \\<3 m\\<6 m\\", "%O(4)=1.1,1.2,1.3,1"]


def test_matrix_rows_with_trailing_commas_and_comments_between():
    body = (
        "%M(2,3)= 0.178,  0.178,  0.219,  # Terreno normal\n"
        "\t 0.372,  0.372,  0.455   # Bajo vías\n"
        "\n"
        "MOC0000600 : %M(%B,%A)*(%C=a)\n"
    )
    assert texts(body) == [
        "%M(2,3)= 0.178,  0.178,  0.219, 0.372,  0.372,  0.455",
        "MOC0000600 : %M(%B,%A)*(%C=a)",
    ]


def test_assignment_ending_with_equals_continues():
    body = "$T(2)=\n\t\"Suministro\",\n\t\t\"Suministro e instalación\"\n\n%%CIND : 0.06\n"
    assert texts(body) == ['$T(2)= "Suministro", "Suministro e instalación"', "%%CIND : 0.06"]


def test_multiline_string_keeps_newline_and_ignores_hash_inside():
    body = '$J(2) = "línea uno # no es comentario\n* línea dos", "b"\nMN1: 1\n'
    assert texts(body) == ['$J(2) = "línea uno # no es comentario\n* línea dos", "b"', "MN1: 1"]


def test_line_ending_with_operator_continues():
    body = '$G = (%A=a)*"x" +\n (%A=b)*"y"\n'
    assert texts(body) == ['$G = (%A=a)*"x" + (%A=b)*"y"']


def test_multiline_texto_with_colon_lines_and_record_end():
    body = "\\RESUMEN\\Canal $A. ($G(%C))\\\n\\TEXTO\\Canal de $A tubos.\nTrabajo: $C\nBanda: $D\\\n"
    st = statements(body)
    assert [s.text for s in st] == [
        "\\RESUMEN\\Canal $A. ($G(%C))\\",
        "\\TEXTO\\Canal de $A tubos.\nTrabajo: $C\nBanda: $D\\",
    ]
    assert [s.is_label for s in st] == [True, True]
    assert [s.line_no for s in st] == [1, 2]


def test_label_with_spaces_and_trailing_comment():
    body = "\\ RESUMEN \\ Señal alta $Q(%A). \\ # texto corto\n"
    assert texts(body) == ["\\ RESUMEN \\ Señal alta $Q(%A). \\"]


def test_trailing_comma_before_new_statement_closes_it():
    body = '$N(3)="R","E","-",\n\\RESUMEN\\x\\\n$L(2)="a","b",\nMN1: 2\n'
    assert texts(body) == ['$N(3)="R","E","-",', "\\RESUMEN\\x\\", '$L(2)="a","b",', "MN1: 2"]


def test_stray_record_terminator_on_expression_statement():
    assert texts("%%CIND: 0.06\\\n") == ["%%CIND: 0.06"]


def test_statement_dataclass():
    s = statements("MN1: 1\n")[0]
    assert s == Statement("MN1: 1", 1, False)
