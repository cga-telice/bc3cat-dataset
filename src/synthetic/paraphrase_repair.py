"""Reparación de paráfrasis de plantilla rotas (César, 2026-10-16).

La auditoría de las 828 paráfrasis TEXTO usadas en STACKED, SINGLE, dose e
isolated (``data/synthetic/broken_OE/``) encontró huecos en un papel que no es
el suyo («con un diámetro de $I mm» con $I = ubicación) y valores tratados como
referencia («las condiciones se detallan en $D»). César decidió corregir esas
dos categorías y dejar las demás (unidades duplicadas, gramática, significado).

La plantilla corregida conserva los mismos huecos. Cada consulta afectada se
alinea con la plantilla rota (``bt_alignment``) para recuperar la superficie de
cada hueco —con todos sus cambios L1/L2 ya aplicados— y se vuelve a renderizar
con la corregida. Los espacios de la consulta reparada se normalizan (los
valores del catálogo traen relleno que la alineación recorta).

Funciones puras, solo stdlib.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Mapping, Sequence

from .bt_alignment import Slot, align

_PH_RE = re.compile(r"\$([A-Za-z]\w*)(?:\([^)]*\))?")


class PlaceholderMismatch(ValueError):
    """La plantilla corregida no tiene exactamente los huecos de la original."""


def slot_values(slots: Sequence[Slot]) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in slots:
        if s.placeholder in out and " ".join(out[s.placeholder].split()) != " ".join(s.text.split()):
            raise ValueError(f"superficies distintas para {s.placeholder}")
        out.setdefault(s.placeholder, s.text)
    return out


def check_placeholders(original: str, corrected: str) -> None:
    a = Counter(m.group(0) for m in _PH_RE.finditer(original))
    b = Counter(m.group(0) for m in _PH_RE.finditer(corrected))
    if a != b:
        raise PlaceholderMismatch(f"esperados {dict(a)}, encontrados {dict(b)}")


def _clean(text: str) -> str:
    text = " ".join(text.split())
    text = re.sub(r"\s+([,.;:)])", r"\1", text)
    text = re.sub(r":(?=\w)", ": ", text)
    return text.strip()


def render(template: str, values: Mapping[str, str]) -> str:
    return _clean(_PH_RE.sub(lambda m: values[m.group(0)], template.lstrip("\\")))


def repair_text(broken: str, fixed: str, query: str, known: Mapping[str, str]) -> str:
    """Consulta ``query`` (renderizada con ``broken``) vuelta a renderizar con
    ``fixed``. ``known`` ancla los huecos cuya superficie se conoce."""
    return render(fixed, slot_values(align(broken.lstrip("\\"), query, known)))
