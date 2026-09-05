"""FIEBDC-3 record reader and in-memory catalogue."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from .encoding import decode_bc3

if TYPE_CHECKING:  # pragma: no cover
    from .param.ast import Family


class Bc3Error(Exception):
    """File-level error (bad file, unknown concept, cycle...)."""


_RECORD_START = re.compile(r"^~[A-Z]\|")


@dataclass
class Record:
    kind: str
    fields: list[str]
    line_no: int


def _make_record(lines: list[str], start: int) -> Record:
    raw = "\n".join(lines).rstrip()
    kind = raw[1]
    payload = raw[3:]  # after "~X|"
    if kind == "P":
        code, _, body = payload.partition("|")
        if body.endswith("|"):
            body = body[:-1]
        return Record("P", [code.strip(), body], start)
    fields = payload.split("|")
    if fields and fields[-1] == "":
        fields.pop()
    return Record(kind, fields, start)


def iter_records(text: str) -> Iterator[Record]:
    """Yield records; a record starts at a line beginning with ``~X|``."""
    buf: list[str] = []
    start = 0
    for n, line in enumerate(text.split("\n"), 1):
        if _RECORD_START.match(line):
            if buf:
                yield _make_record(buf, start)
            buf = [line]
            start = n
        elif buf:
            buf.append(line)
    if buf:
        yield _make_record(buf, start)


def code_key(code: str) -> str:
    """Normalise a concept code for lookups: trailing '#' / '##' are optional."""
    return code.strip().rstrip("#")


def _dec(text: str, default: Decimal | None) -> Decimal | None:
    text = text.strip()
    if not text:
        return default
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation as exc:
        raise Bc3Error(f"bad number {text!r}") from exc


@dataclass
class Concept:
    code: str
    unit: str
    summary: str
    price: Decimal | None
    date: str
    type: str


@dataclass
class DecompRef:
    child: str
    factor: Decimal
    yield_: Decimal


@dataclass
class Decimals:
    """Decimal places from ~K field 1 (spec defaults when absent)."""

    DN: int = 2
    DD: int = 2
    DS: int = 2
    DR: int = 3
    DI: int = 2
    DP: int = 2
    DC: int = 2
    DM: int = 2


def _parse_decimals(field1: str) -> Decimals:
    names = ["DN", "DD", "DS", "DR", "DI", "DP", "DC", "DM"]
    dec = Decimals()
    for name, value in zip(names, field1.split("\\")):
        value = value.strip()
        if value.lstrip("-").isdigit():
            setattr(dec, name, abs(int(value)))
    return dec


class Catalog:
    def __init__(self) -> None:
        self.version: str = ""
        self.concepts: dict[str, Concept] = {}
        self.decompositions: dict[str, list[DecompRef]] = {}
        self.texts: dict[str, str] = {}
        self.decimals: Decimals = Decimals()
        self.families_raw: dict[str, str] = {}
        self.parents: dict[str, str] = {}
        self._families: dict[str, Family] = {}

    # ---- loading -------------------------------------------------------
    @classmethod
    def load(cls, path: str | Path) -> "Catalog":
        return cls.from_text(decode_bc3(Path(path).read_bytes()))

    @classmethod
    def from_text(cls, text: str) -> "Catalog":
        cat = cls()
        count = 0
        for rec in iter_records(text):
            count += 1
            cat._add(rec)
        if count == 0:
            raise Bc3Error("no FIEBDC-3 records found")
        return cat

    def _add(self, rec: Record) -> None:
        f = rec.fields

        def fld(i: int) -> str:
            return f[i] if len(f) > i else ""

        if rec.kind == "V":
            self.version = fld(1)
        elif rec.kind == "C":
            price = _dec(fld(3).split("\\")[0], None)
            concept_type = fld(5).strip()
            for code in fld(0).split("\\"):
                if code.strip():
                    self.concepts[code_key(code)] = Concept(
                        code.strip(), fld(1).strip(), fld(2).strip(), price,
                        fld(4).split("\\")[0].strip(), concept_type,
                    )
        elif rec.kind == "D":
            parent = fld(0).strip()
            parts = fld(1).split("\\")
            refs: list[DecompRef] = []
            for i in range(0, len(parts) - 2, 3):
                child = parts[i].strip()
                if not child:
                    continue
                refs.append(DecompRef(child, _dec(parts[i + 1], Decimal(1)), _dec(parts[i + 2], Decimal(1))))
                if parent.endswith("#"):  # only chapters/root define the hierarchy
                    self.parents.setdefault(code_key(child), parent)
            self.decompositions[code_key(parent)] = refs
        elif rec.kind == "T":
            self.texts[code_key(fld(0))] = fld(1)
        elif rec.kind == "K":
            self.decimals = _parse_decimals(fld(0))
        elif rec.kind == "P":
            if fld(0):
                self.families_raw[fld(0)] = fld(1)

    # ---- queries -------------------------------------------------------
    def concept(self, code: str) -> Concept | None:
        return self.concepts.get(code_key(code))

    def children(self, code: str) -> list[str]:
        return [r.child for r in self.decompositions.get(code_key(code), [])]

    def chapter_path(self, code: str) -> list[str]:
        """Chapter codes from the top chapter down to the direct parent (root excluded)."""
        path: list[str] = []
        key = code_key(code)
        seen: set[str] = set()
        while key in self.parents and key not in seen:
            seen.add(key)
            parent = self.parents[key]
            if parent.endswith("##"):
                break
            path.append(parent)
            key = code_key(parent)
        path.reverse()
        return path

    @property
    def families(self) -> list[str]:
        return sorted(self.families_raw)

    def family(self, code: str) -> "Family":
        """Parse (once) and return the parametric family ``code`` (e.g. ``OEB020$``)."""
        from .param.parser import parse_family

        if code not in self._families:
            if code not in self.families_raw:
                raise Bc3Error(f"unknown parametric family {code!r}")
            self._families[code] = parse_family(code, self.families_raw[code])
        return self._families[code]
