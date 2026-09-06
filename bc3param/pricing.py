"""Price computation with FIEBDC rounding (~K) and percentage concepts."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable

from .fiebdc import Bc3Error, Catalog, code_key
from .param.evaluator import Evaluation


def quantize(value: Decimal, places: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def to_decimal(value: float | int | str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value))


def is_percentage(code: str) -> bool:
    return "%" in code or "&" in code


def percentage_prefix(code: str) -> str:
    positions = [i for i in (code.find("%"), code.find("&")) if i >= 0]
    return code[: min(positions)] if positions else code


@dataclass
class PricedLine:
    code: str
    unit: str
    summary: str
    type: str
    price: Decimal
    quantity: Decimal
    amount: Decimal
    warning: str | None = None


@dataclass
class PricedConcept:
    code: str
    unit: str
    summary: str
    type: str
    price: Decimal
    lines: list[PricedLine] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class Pricer:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self.dec = catalog.decimals
        self._cache: dict[str, PricedConcept] = {}
        self._stack: set[str] = set()

    def concept_price(self, code: str) -> PricedConcept:
        key = code_key(code)
        if key in self._cache:
            return self._cache[key]
        concept = self.catalog.concept(code)
        refs = self.catalog.decompositions.get(key)
        unit = concept.unit if concept else ""
        summary = concept.summary if concept else ""
        ctype = concept.type if concept else ""
        warnings: list[str] = []
        lines: list[PricedLine] = []
        if refs:
            if key in self._stack:
                raise Bc3Error(f"decomposition cycle at {code}")
            self._stack.add(key)
            try:
                lines, price = self.price_lines((r.child, r.factor * r.yield_) for r in refs)
            finally:
                self._stack.discard(key)
            warnings.extend(l.warning for l in lines if l.warning)
            if concept is not None and concept.price is not None and price != concept.price:
                warnings.append(f"{code}: computed price {price} differs from ~C price {concept.price}")
        elif concept is None:
            price = Decimal(0)
            warnings.append(f"unknown concept {code}")
        elif concept.price is None:
            price = Decimal(0)
            warnings.append(f"{code} has no price")
        else:
            price = concept.price
        result = PricedConcept(code, unit, summary, ctype, price, lines, warnings)
        self._cache[key] = result
        return result

    def price_lines(self, items: Iterable[tuple[str, float | Decimal]]) -> tuple[list[PricedLine], Decimal]:
        lines: list[PricedLine] = []
        for code, qty in items:
            quantity = quantize(to_decimal(qty), self.dec.DR)
            if quantity == 0:
                continue
            if is_percentage(code):
                prefix = percentage_prefix(code)
                base = sum((l.amount for l in lines if l.code.startswith(prefix)), Decimal(0))
                base = quantize(base, self.dec.DI)
                concept = self.catalog.concept(code)
                unit = concept.unit if concept and concept.unit else "%"
                summary = concept.summary if concept else ("Medios auxiliares" if code == "%" else "")
                ctype = concept.type if concept else "%"
                lines.append(PricedLine(code, unit, summary, ctype, base, quantity, quantize(base * quantity, self.dec.DI)))
            else:
                pc = self.concept_price(code)
                warning = "; ".join(pc.warnings) or None
                lines.append(PricedLine(code, pc.unit, pc.summary, pc.type, pc.price, quantity,
                                        quantize(pc.price * quantity, self.dec.DI), warning))
        total = quantize(sum((l.amount for l in lines), Decimal(0)), self.dec.DC)
        return lines, total

    def price_evaluation(self, ev: Evaluation) -> tuple[list[PricedLine], Decimal | None, Decimal]:
        """Return (lines, direct_cost, price) for an evaluated selection."""
        if ev.direct_price is not None:
            return [], None, quantize(to_decimal(ev.direct_price), self.dec.DC)
        items: list[tuple[str, float]] = list(ev.lines)
        if ev.aux_percent:
            items.append(("%", ev.aux_percent))
        lines, total = self.price_lines(items)
        direct = quantize(sum((l.amount for l in lines if not is_percentage(l.code)), Decimal(0)), self.dec.DP)
        return lines, direct, total
