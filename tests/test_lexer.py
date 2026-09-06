from __future__ import annotations

import pytest

from bc3param.param.lexer import LexError, Token, tokenize


def kinds(text: str) -> list[tuple[str, str]]:
    return [(t.kind, t.value) for t in tokenize(text)]


def test_numbers_vars_and_operators():
    assert kinds("%M(%B,%A)*(%C=a)*%K(%D)*0.10") == [
        ("NUMVAR", "%M"), ("LPAREN", "("), ("NUMVAR", "%B"), ("COMMA", ","), ("NUMVAR", "%A"),
        ("RPAREN", ")"), ("OP", "*"), ("LPAREN", "("), ("NUMVAR", "%C"), ("OP", "="), ("LETTER", "a"),
        ("RPAREN", ")"), ("OP", "*"), ("NUMVAR", "%K"), ("LPAREN", "("), ("NUMVAR", "%D"), ("RPAREN", ")"),
        ("OP", "*"), ("NUMBER", "0.10"), ("EOF", ""),
    ]


def test_two_char_operators_and_bang():
    assert [k for k, _ in kinds("%A<>b & %B>=c @ !(%C<=d)")] == [
        "NUMVAR", "OP", "LETTER", "OP", "NUMVAR", "OP", "LETTER", "OP", "OP", "LPAREN",
        "NUMVAR", "OP", "LETTER", "RPAREN", "EOF",
    ]
    assert [v for _, v in kinds("<> <= >= = < > ! ^") if v] == ["<>", "<=", ">=", "=", "<", ">", "!", "^"]


def test_strings_with_escaped_quotes_and_newlines():
    toks = tokenize('"a ""b"" c\nd" + $A')
    assert toks[0] == Token("STRING", 'a "b" c\nd', 0)
    assert toks[1].value == "+" and toks[2] == Token("TEXTVAR", "$A", 16)


def test_functions_and_pi():
    assert kinds("ATOF($A)/1000 + PI") == [
        ("IDENT", "ATOF"), ("LPAREN", "("), ("TEXTVAR", "$A"), ("RPAREN", ")"), ("OP", "/"),
        ("NUMBER", "1000"), ("OP", "+"), ("IDENT", "PI"), ("EOF", ""),
    ]


def test_uppercase_single_letter_is_letter_constant():
    assert kinds("%A=B")[2] == ("LETTER", "B")


def test_unknown_identifier_and_char_raise():
    with pytest.raises(LexError):
        tokenize("FOO(1)")
    with pytest.raises(LexError):
        tokenize("%a")
