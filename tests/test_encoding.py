from __future__ import annotations

from bc3param.encoding import decode_bc3


def test_cp1252_with_undefined_byte_and_crlf():
    data = b"~V|x\r\nHormig\xf3n \x81 fin\r\n"
    assert decode_bc3(data) == "~V|x\nHormigón \x81 fin\n"


def test_cp1252_smart_quote():
    assert decode_bc3(b"a\x92b") == "a’b"


def test_utf8_input_is_accepted():
    text = "~C|AAA010$|m²|APEO|\n"
    assert decode_bc3(text.encode("utf-8")) == text


def test_utf8_bom_is_stripped():
    assert decode_bc3(b"\xef\xbb\xbf~V|\n") == "~V|\n"
