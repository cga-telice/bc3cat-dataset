"""Decoding of BC3 files: cp1252 (with latin-1 fallback for undefined bytes) or UTF-8."""
from __future__ import annotations

import codecs


def _fallback(err: UnicodeError) -> tuple[str, int]:
    if isinstance(err, UnicodeDecodeError):
        chunk = err.object[err.start:err.end]
        return "".join(chr(b) for b in chunk), err.end
    raise err


codecs.register_error("bc3fallback", _fallback)


def decode_bc3(data: bytes) -> str:
    """Decode raw BC3 bytes to text with normalised ``\\n`` line endings.

    UTF-8 (with or without BOM) is accepted when it decodes cleanly; otherwise the
    file is treated as Windows cp1252, mapping the five undefined bytes to the same
    code point as latin-1 would.
    """
    if data.startswith(codecs.BOM_UTF8):
        text = data[len(codecs.BOM_UTF8):].decode("utf-8")
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="bc3fallback")
    return text.replace("\r\n", "\n").replace("\r", "\n")
