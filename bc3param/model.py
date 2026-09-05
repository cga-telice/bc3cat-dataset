"""Output model for one derived item."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass
class ParameterChoice:
    var: str
    name: str
    option: int
    letter: str
    label: str


@dataclass
class DecompLine:
    code: str
    unit: str
    summary: str
    type: str
    price: Decimal
    quantity: Decimal
    amount: Decimal


@dataclass
class Item:
    code: str
    family: str
    unit: str
    family_summary: str
    chapter_path: list[str]
    parameters: list[ParameterChoice]
    resumen: str | None
    texto: str | None
    valid: bool
    error: str | None
    direct_cost: Decimal | None = None
    price: Decimal | None = None
    decomposition: list[DecompLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "family": self.family,
            "unit": self.unit,
            "family_summary": self.family_summary,
            "chapter_path": list(self.chapter_path),
            "parameters": [vars(p) for p in self.parameters],
            "resumen": self.resumen,
            "texto": self.texto,
            "valid": self.valid,
            "error": self.error,
            "direct_cost": _num(self.direct_cost),
            "price": _num(self.price),
            "decomposition": [
                {"code": l.code, "unit": l.unit, "summary": l.summary, "type": l.type,
                 "price": _num(l.price), "quantity": _num(l.quantity), "amount": _num(l.amount)}
                for l in self.decomposition
            ],
            "warnings": list(self.warnings),
        }


def _num(value: Decimal | None) -> float | None:
    return None if value is None else float(value)
