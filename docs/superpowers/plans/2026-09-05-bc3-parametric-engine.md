# BC3 Parametric Engine (`bc3param`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dependency-free Python package + CLI that parses a FIEBDC-3 `.bc3` catalogue and expands every parametric family (`~P`) into priced, fully described items (code, texts, decomposition, price), reproducing what the ADIF viewer shows.

**Architecture:** A `Catalog` reads records (`~C ~D ~T ~K ~P`). Each `~P` body goes through `preprocess` (statement extraction per spec), `lexer` + `parser` (recursive descent, typed AST), and `evaluator` (sequential interpreter for one option selection). `pricing` applies `~K` rounding and percentage rules; `generate` expands families to `Item`s and writes JSON/JSONL; `cli` exposes `validate / inspect / resolve / generate`.

**Tech Stack:** Python 3.11+ standard library only (`re`, `dataclasses`, `decimal`, `argparse`, `json`, `itertools`). Tests with pytest. Spec: `docs/superpowers/specs/2026-09-05-bc3-parametric-engine-design.md`.

**Conventions for every task:**
- Work in the worktree on branch `claude/bc3-parametric-parser-bb6818`. Never merge to `main` or `synthetic`.
- Run tests with `python -m pytest tests -q` from the repo root (the worktree root).
- Commit after each task with the message shown; always end the message with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Python files are UTF-8; keep `from __future__ import annotations` at the top of every module.
- Backslashes: the BC3 format uses `\` as delimiter. In Python string literals write `"\\"` for one backslash. In test snippets use raw strings `r"""..."""` when convenient (a raw string cannot end with a backslash, so end snippets with a newline).

---

## File structure

```
pyproject.toml
bc3param/__init__.py            public API
bc3param/encoding.py            decode_bc3()
bc3param/fiebdc.py              iter_records(), Catalog, Concept, DecompRef, Decimals, Bc3Error
bc3param/param/__init__.py
bc3param/param/ast.py           expression/statement dataclasses, Family
bc3param/param/preprocess.py    statements()
bc3param/param/lexer.py         tokenize(), Token, LexError
bc3param/param/parser.py        parse_expression(), parse_family(), ParseError
bc3param/param/codes.py         letter/index conversion, derived codes
bc3param/param/evaluator.py     Evaluator, Evaluation, Matrix, EvalError
bc3param/pricing.py             Pricer, PricedLine, PricedConcept, quantize()
bc3param/model.py               Item, DecompLine, ParameterChoice
bc3param/generate.py            build_item(), select_families(), iter_items(), writers
bc3param/cli.py                 main()
tests/conftest.py
tests/test_encoding.py tests/test_fiebdc.py tests/test_preprocess.py tests/test_lexer.py
tests/test_parser.py tests/test_codes.py tests/test_evaluator.py tests/test_pricing.py
tests/test_generate.py tests/test_cli.py tests/test_reference.py
```

---

### Task 1: Package scaffold

**Files:**
- Create: `pyproject.toml`, `bc3param/__init__.py`, `bc3param/param/__init__.py`, `tests/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "bc3param"
version = "0.1.0"
description = "Parametric FIEBDC-3 (BC3) catalogue engine: expand ~P families into priced items"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=7"]

[project.scripts]
bc3param = "bc3param.cli:main"

[tool.setuptools.packages.find]
include = ["bc3param*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create empty package files**

`bc3param/__init__.py`:
```python
"""bc3param: parametric FIEBDC-3 catalogue engine."""
from __future__ import annotations

__version__ = "0.1.0"
```

`bc3param/param/__init__.py`:
```python
"""Parametric sub-language: preprocess, lex, parse, evaluate."""
```

`tests/__init__.py`: empty file.

- [ ] **Step 3: Create `tests/conftest.py`**

```python
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "BPA_2024_v2.txt"


@pytest.fixture(scope="session")
def raw_path() -> Path:
    if not RAW_FILE.exists() or RAW_FILE.stat().st_size < 1_000_000:
        pytest.skip("real BC3 file not available")
    return RAW_FILE
```

- [ ] **Step 4: Install in editable mode and check pytest collects nothing but runs**

Run: `python -m pip install -e . -q && python -m pytest tests -q`
Expected: `no tests ran` (exit code 5 is fine).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml bc3param tests
git commit -m "Scaffold bc3param package

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: Encoding

**Files:**
- Create: `bc3param/encoding.py`
- Test: `tests/test_encoding.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_encoding.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bc3param.encoding'`

- [ ] **Step 3: Implement `bc3param/encoding.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_encoding.py -q`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/encoding.py tests/test_encoding.py
git commit -m "Add BC3 decoder with cp1252 fallback

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Record reader and Catalog

**Files:**
- Create: `bc3param/fiebdc.py`
- Test: `tests/test_fiebdc.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from decimal import Decimal

import pytest

from bc3param.fiebdc import Bc3Error, Catalog, iter_records

SNIPPET = (
    "~V||FIEBDC-3/2007\\260224|menfis 8.2.117|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|R_A_I_Z##||BASE PRECIOS||||\n"
    "~C|O#||OBRA CIVIL||||\n"
    "~C|OEB#||ZANJAS||||\n"
    "~C|OEB020$|m|CANALIZACIÓN HORMIGONADA||21022019||\n"
    "~C|MOC0000100|h|CAPATAZ|22.66||1|\n"
    "~C|MN01060004|m³|HORMIGÓN|73.88|15111998|3|\n"
    "~C|AU10100001|m³|HORMIGÓN EN MASA|88.39||EA|\n"
    "~C|%CIND|%|Costes indirectos|||%|\n"
    "~D|R_A_I_Z##|O#\\\\\\|\n"
    "~D|O#|OEB#\\\\\\|\n"
    "~D|OEB#|OEB020$\\\\\\OEB060\\\\\\|\n"
    "~D|AU10100001|MOC0000100\\\\0.0080\\MN01060004\\\\1.0500\\|\n"
    "~T|MOC0000100|Capataz de obra|\n"
    "~P|OEB020$|\\Nº TUBOS\\2\\4\\\n"
    "#comentario\n"
    "%%CIND: 0.06\n"
    "\\RESUMEN\\Canal $A\\\n"
    "\\TEXTO\\Texto $A\n"
    "Trabajo: x\\|\n"
    "~C|ZZZ|u|after|1||3|\n"
)


def test_iter_records_splits_and_keeps_p_body():
    recs = list(iter_records(SNIPPET))
    kinds = [r.kind for r in recs]
    assert kinds == ["V", "K"] + ["C"] * 8 + ["D"] * 4 + ["T", "P", "C"]
    p = [r for r in recs if r.kind == "P"][0]
    assert p.fields[0] == "OEB020$"
    assert p.fields[1].startswith("\\Nº TUBOS\\2\\4\\\n#comentario")
    assert p.fields[1].endswith("Trabajo: x\\")  # trailing '|' removed, closing '\' kept
    assert p.line_no == 16
    c = recs[2]
    assert c.fields == ["R_A_I_Z##", "", "BASE PRECIOS", "", "", ""]


def test_catalog_concepts_and_prices():
    cat = Catalog.from_text(SNIPPET)
    assert cat.version == "FIEBDC-3/2007\\260224"
    c = cat.concept("MOC0000100")
    assert c.unit == "h" and c.summary == "CAPATAZ" and c.price == Decimal("22.66") and c.type == "1"
    assert cat.concept("%CIND").price is None
    assert cat.concept("OEB").summary == "ZANJAS"  # '#' is optional in references
    assert cat.concept("nope") is None


def test_catalog_decimals_from_k_record():
    cat = Catalog.from_text(SNIPPET)
    assert (cat.decimals.DR, cat.decimals.DI, cat.decimals.DP, cat.decimals.DC) == (4, 2, 2, 2)


def test_catalog_decompositions():
    cat = Catalog.from_text(SNIPPET)
    refs = cat.decompositions["AU10100001"]
    assert [(r.child, r.factor, r.yield_) for r in refs] == [
        ("MOC0000100", Decimal(1), Decimal("0.0080")),
        ("MN01060004", Decimal(1), Decimal("1.0500")),
    ]
    assert cat.children("OEB#") == ["OEB020$", "OEB060"]


def test_catalog_chapter_path_and_families():
    cat = Catalog.from_text(SNIPPET)
    assert cat.chapter_path("OEB020$") == ["O#", "OEB#"]
    assert cat.chapter_path("MOC0000100") == []
    assert list(cat.families_raw) == ["OEB020$"]
    assert cat.texts["MOC0000100"] == "Capataz de obra"


def test_empty_input_raises():
    with pytest.raises(Bc3Error):
        Catalog.from_text("")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_fiebdc.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/fiebdc.py`**

```python
"""FIEBDC-3 record reader and in-memory catalogue."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_fiebdc.py -q`
Expected: 6 passed (the `family()` method is exercised later).

- [ ] **Step 5: Commit**

```bash
git add bc3param/fiebdc.py tests/test_fiebdc.py
git commit -m "Add FIEBDC record reader and Catalog

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: Statement preprocessor

**Files:**
- Create: `bc3param/param/preprocess.py`
- Test: `tests/test_preprocess.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_preprocess.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/param/preprocess.py`**

```python
"""Turn the raw text of a ~P record into statements (FIEBDC-3 reading procedure)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Statement:
    text: str
    line_no: int
    is_label: bool


_CONTINUE_CHARS = set("+-*/^@&<>=!(,")
_NEW_STATEMENT = re.compile(
    r"^(\\|::|%%?:|[%$][A-Z]\s*(\([^)]*\))?\s*=|[A-Za-z0-9_%.]+\s*:)"
)


def _strip_comment(line: str, in_quote: bool) -> tuple[str, bool]:
    """Remove ``#...`` outside quotes; return (text, quote state at end of line)."""
    out: list[str] = []
    quote = in_quote
    for ch in line:
        if ch == '"':
            quote = not quote
        elif ch == "#" and not quote:
            break
        out.append(ch)
    return "".join(out), quote


def _strip_label_comment(line: str) -> str:
    """In a label line only a ``#`` after the last backslash is a comment."""
    last = line.rfind("\\")
    if last < 0:
        return line
    pos = line.find("#", last)
    return line[:pos] if pos >= 0 else line


def statements(body: str) -> list[Statement]:
    result: list[Statement] = []
    buf = ""
    start = 0
    in_quote = False
    in_label = False

    def close() -> None:
        nonlocal buf, in_label
        text = buf.strip()
        if not in_label:
            text = text.rstrip("\\").rstrip()
        if text:
            result.append(Statement(text, start, in_label))
        buf = ""
        in_label = False

    for n, raw in enumerate(body.split("\n"), 1):
        line = raw.replace("\t", " ")
        if in_label:
            line = _strip_label_comment(line)
            buf += "\n" + line
            if line.rstrip().endswith("\\"):
                close()
            continue

        stripped = line.strip()
        if buf and not in_quote and buf.endswith(",") and _NEW_STATEMENT.match(stripped):
            close()

        if not buf and stripped.startswith("\\"):
            stripped = _strip_label_comment(stripped).strip()
            start = n
            buf = stripped
            in_label = True
            if len(stripped) > 1 and stripped.endswith("\\"):
                close()
            continue

        was_in_quote = in_quote
        line, in_quote = _strip_comment(line, in_quote)
        stripped = line.strip()
        if not stripped:
            continue
        if not buf:
            start = n
            buf = stripped
        else:
            buf += ("\n" if was_in_quote else " ") + stripped
        if in_quote or stripped[-1] in _CONTINUE_CHARS:
            continue
        close()

    if buf:
        close()
    return result
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_preprocess.py -q`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/param/preprocess.py tests/test_preprocess.py
git commit -m "Add ~P statement preprocessor

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: Lexer

**Files:**
- Create: `bc3param/param/lexer.py`
- Test: `tests/test_lexer.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_lexer.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/param/lexer.py`**

```python
"""Tokenizer for FIEBDC-3 parametric expressions."""
from __future__ import annotations

import re
from dataclasses import dataclass


class LexError(Exception):
    pass


@dataclass(frozen=True)
class Token:
    kind: str  # NUMBER STRING LETTER IDENT NUMVAR TEXTVAR OP LPAREN RPAREN COMMA EOF
    value: str
    pos: int


FUNCTIONS = {"ABS", "INT", "ROUND", "SIN", "COS", "TAN", "ASIN", "ACOS", "ATAN", "ATAN2", "SQRT", "ATOF", "FTOA"}

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<NUMBER>\d+(?:\.\d*)?|\.\d+)
  | (?P<STRING>"(?:[^"]|"")*")
  | (?P<NUMVAR>%[A-Z])
  | (?P<TEXTVAR>\$[A-Z])
  | (?P<OP><>|<=|>=|[-+*/^@&<>=!])
  | (?P<LPAREN>\()
  | (?P<RPAREN>\))
  | (?P<COMMA>,)
  | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    """,
    re.X,
)


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            raise LexError(f"unexpected character {text[pos]!r} at position {pos}")
        kind = m.lastgroup
        value = m.group()
        pos = m.end()
        if kind == "ws":
            continue
        if kind == "STRING":
            tokens.append(Token("STRING", value[1:-1].replace('""', '"'), m.start()))
        elif kind == "IDENT":
            if len(value) == 1:
                tokens.append(Token("LETTER", value, m.start()))
            elif value.upper() in FUNCTIONS or value.upper() == "PI":
                tokens.append(Token("IDENT", value.upper(), m.start()))
            else:
                raise LexError(f"unknown identifier {value!r} at position {m.start()}")
        else:
            tokens.append(Token(kind, value, m.start()))
    tokens.append(Token("EOF", "", len(text)))
    return tokens
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_lexer.py -q`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/param/lexer.py tests/test_lexer.py
git commit -m "Add parametric expression lexer

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: AST and option-letter codes

**Files:**
- Create: `bc3param/param/ast.py`, `bc3param/param/codes.py`
- Test: `tests/test_codes.py`

- [ ] **Step 1: Write the failing tests for codes**

```python
from __future__ import annotations

import pytest

from bc3param.param.codes import derived_code, index_to_letter, letter_to_index, split_derived_code


def test_letter_index_roundtrip():
    assert letter_to_index("a") == 1
    assert letter_to_index("z") == 26
    assert letter_to_index("A") == 27
    assert letter_to_index("0") == 53
    assert letter_to_index("9") == 62
    for i in range(1, 63):
        assert letter_to_index(index_to_letter(i)) == i


def test_invalid_letter_and_index():
    with pytest.raises(ValueError):
        letter_to_index("$")
    with pytest.raises(ValueError):
        index_to_letter(0)
    with pytest.raises(ValueError):
        index_to_letter(63)


def test_derived_code():
    assert derived_code("OEB020$", (2, 2, 2, 1, 1)) == "OEB020bbbaa"


def test_split_derived_code():
    families = {"OEB020$", "OEB0203$"}
    assert split_derived_code("OEB020bbbaa", families) == ("OEB020$", (2, 2, 2, 1, 1))
    assert split_derived_code("OEB0203ab", families) == ("OEB0203$", (1, 2))
    with pytest.raises(ValueError):
        split_derived_code("XXX", families)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_codes.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/param/codes.py`**

```python
"""Option letters (a-z, A-Z, 0-9 = 1..62) and derived concept codes."""
from __future__ import annotations

from typing import Iterable

LETTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def letter_to_index(ch: str) -> int:
    """'a' -> 1 ... 'z' -> 26, 'A' -> 27 ... '9' -> 62."""
    pos = LETTERS.find(ch)
    if len(ch) != 1 or pos < 0:
        raise ValueError(f"not an option letter: {ch!r}")
    return pos + 1


def index_to_letter(index: int) -> str:
    if not 1 <= index <= len(LETTERS):
        raise ValueError(f"option index out of range 1..{len(LETTERS)}: {index}")
    return LETTERS[index - 1]


def derived_code(family_code: str, selection: Iterable[int]) -> str:
    """``OEB020$`` + (2,2,2,1,1) -> ``OEB020bbbaa``."""
    return family_code.rstrip("$") + "".join(index_to_letter(i) for i in selection)


def split_derived_code(code: str, families: Iterable[str]) -> tuple[str, tuple[int, ...]]:
    """Find the family a derived code belongs to (longest matching stem wins)."""
    known = set(families)
    for length in range(len(code) - 1, 0, -1):
        family = code[:length] + "$"
        if family in known:
            return family, tuple(letter_to_index(ch) for ch in code[length:])
    raise ValueError(f"no parametric family matches {code!r}")
```

- [ ] **Step 4: Implement `bc3param/param/ast.py`** (no test of its own; used by parser tests)

```python
"""Typed nodes for the parametric sub-language."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union

# ---- expressions -------------------------------------------------------


@dataclass(frozen=True)
class Num:
    value: float


@dataclass(frozen=True)
class Str:
    value: str


@dataclass(frozen=True)
class Const:
    """Option constant a..z / A..Z / 0..9 (1-based)."""

    letter: str


@dataclass(frozen=True)
class NumVar:
    name: str  # "A".."Z" (without the %)


@dataclass(frozen=True)
class TextVar:
    name: str  # "A".."Z" (without the $)


@dataclass(frozen=True)
class Index:
    var: Union[NumVar, TextVar]
    args: tuple["Expr", ...]


@dataclass(frozen=True)
class Call:
    fn: str
    args: tuple["Expr", ...]


@dataclass(frozen=True)
class Unary:
    op: str  # "!" or "-"
    operand: "Expr"


@dataclass(frozen=True)
class Binary:
    op: str  # + - * / ^ @ & < > <= >= = <>
    left: "Expr"
    right: "Expr"


Expr = Union[Num, Str, Const, NumVar, TextVar, Index, Call, Unary, Binary]

# ---- statements --------------------------------------------------------


@dataclass(frozen=True)
class ParamDef:
    var: str  # A B C D F G H I J K
    name: str
    options: tuple[str, ...]
    line_no: int


@dataclass(frozen=True)
class Assign:
    kind: str  # "%" numeric or "$" text
    name: str
    dims: tuple[int, ...] | None
    values: tuple[Expr, ...]
    line_no: int


@dataclass(frozen=True)
class Decomp:
    code_template: str
    expr: Expr
    factor: Expr | None
    line_no: int


@dataclass(frozen=True)
class Price:
    expr: Expr
    line_no: int


@dataclass(frozen=True)
class AuxPercent:
    expr: Expr
    per_unit: bool
    line_no: int


@dataclass(frozen=True)
class Text:
    label: str  # RESUMEN TEXTO COMENTARIO
    template: str
    line_no: int


@dataclass(frozen=True)
class TextList:
    label: str  # PLIEGO CLAVES COMERCIAL
    items: tuple[str, ...]
    line_no: int


Statement = Union[ParamDef, Assign, Decomp, Price, AuxPercent, Text, TextList]


@dataclass
class Family:
    code: str
    params: list[ParamDef] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)

    def option_counts(self) -> tuple[int, ...]:
        return tuple(len(p.options) for p in self.params)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_codes.py -q`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add bc3param/param/ast.py bc3param/param/codes.py tests/test_codes.py
git commit -m "Add parametric AST nodes and option code helpers

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: Expression and family parser

**Files:**
- Create: `bc3param/param/parser.py`
- Test: `tests/test_parser.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_parser.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/param/parser.py`**

```python
"""Recursive-descent parser: expressions and whole ~P families."""
from __future__ import annotations

import math
import re
from functools import lru_cache

from .ast import (
    Assign, AuxPercent, Binary, Call, Const, Decomp, Expr, Family, Index, Num, NumVar, ParamDef,
    Price, Statement, Str, Text, TextList, TextVar, Unary,
)
from .lexer import FUNCTIONS, LexError, Token, tokenize
from .preprocess import statements as extract_statements

PARAM_VARS = "ABCDFGHIJK"
_LABEL_ALIASES = {"R": "RESUMEN", "T": "TEXTO", "C": "COMENTARIO", "P": "PLIEGO", "K": "CLAVES", "F": "COMERCIAL"}
_TEXT_LABELS = {"RESUMEN", "TEXTO", "COMENTARIO"}
_LIST_LABELS = {"PLIEGO", "CLAVES", "COMERCIAL"}
_LABEL_RE = re.compile(r"^\\\s*([^\\]*?)\s*\\(.*)\\$", re.S)
_ASSIGN_RE = re.compile(r"^([%$])([A-Z])\s*(?:\(([\d\s,]+)\))?\s*=(.*)$", re.S)
_CMP_OPS = {"<", ">", "<=", ">=", "=", "<>"}


class ParseError(Exception):
    def __init__(self, message: str, family: str = "", line_no: int = 0) -> None:
        super().__init__(f"{family} line {line_no}: {message}" if family else message)
        self.family = family
        self.line_no = line_no
        self.message = message


class _ExprParser:
    def __init__(self, tokens: list[Token]) -> None:
        self.toks = tokens
        self.i = 0

    def peek(self) -> Token:
        return self.toks[self.i]

    def advance(self) -> Token:
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def expect(self, kind: str, value: str | None = None) -> Token:
        tok = self.peek()
        if tok.kind != kind or (value is not None and tok.value != value):
            want = value or kind
            raise ParseError(f"expected {want!r} but found {tok.value or 'end of expression'!r} at position {tok.pos}")
        return self.advance()

    def is_op(self, *values: str) -> bool:
        tok = self.peek()
        return tok.kind == "OP" and tok.value in values

    def parse(self) -> Expr:
        expr = self.parse_or()
        if self.peek().kind != "EOF":
            tok = self.peek()
            raise ParseError(f"unexpected {tok.value!r} at position {tok.pos}")
        return expr

    def parse_or(self) -> Expr:
        left = self.parse_and()
        while self.is_op("@"):
            self.advance()
            left = Binary("@", left, self.parse_and())
        return left

    def parse_and(self) -> Expr:
        left = self.parse_cmp()
        while self.is_op("&"):
            self.advance()
            left = Binary("&", left, self.parse_cmp())
        return left

    def parse_cmp(self) -> Expr:
        left = self.parse_add()
        while self.is_op(*_CMP_OPS):
            op = self.advance().value
            left = Binary(op, left, self.parse_add())
        return left

    def parse_add(self) -> Expr:
        left = self.parse_mul()
        while self.is_op("+", "-"):
            op = self.advance().value
            left = Binary(op, left, self.parse_mul())
        return left

    def parse_mul(self) -> Expr:
        left = self.parse_pow()
        while self.is_op("*", "/"):
            op = self.advance().value
            left = Binary(op, left, self.parse_pow())
        return left

    def parse_pow(self) -> Expr:
        left = self.parse_unary()
        while self.is_op("^"):
            self.advance()
            left = Binary("^", left, self.parse_unary())
        return left

    def parse_unary(self) -> Expr:
        # Unary operators bind looser than '^' so that -2^2 == -(2^2).
        if self.is_op("!", "-"):
            op = self.advance().value
            return Unary(op, self.parse_pow())
        if self.is_op("+"):
            self.advance()
            return self.parse_pow()
        return self.parse_atom()

    def parse_args(self) -> tuple[Expr, ...]:
        self.expect("LPAREN")
        args: list[Expr] = []
        if self.peek().kind != "RPAREN":
            args.append(self.parse_or())
            while self.peek().kind == "COMMA":
                self.advance()
                args.append(self.parse_or())
        self.expect("RPAREN")
        return tuple(args)

    def parse_atom(self) -> Expr:
        tok = self.peek()
        if tok.kind == "NUMBER":
            self.advance()
            return Num(float(tok.value))
        if tok.kind == "STRING":
            self.advance()
            return Str(tok.value)
        if tok.kind == "LETTER":
            self.advance()
            return Const(tok.value)
        if tok.kind in ("NUMVAR", "TEXTVAR"):
            self.advance()
            var: NumVar | TextVar = NumVar(tok.value[1]) if tok.kind == "NUMVAR" else TextVar(tok.value[1])
            if self.peek().kind == "LPAREN":
                return Index(var, self.parse_args())
            return var
        if tok.kind == "IDENT":
            self.advance()
            if tok.value == "PI":
                return Num(math.pi)
            if tok.value in FUNCTIONS:
                return Call(tok.value, self.parse_args())
            raise ParseError(f"unknown function {tok.value!r}")
        if tok.kind == "LPAREN":
            self.advance()
            expr = self.parse_or()
            self.expect("RPAREN")
            return expr
        raise ParseError(f"unexpected {tok.value or 'end of expression'!r} at position {tok.pos}")


@lru_cache(maxsize=None)
def parse_expression(text: str) -> Expr:
    try:
        return _ExprParser(tokenize(text)).parse()
    except LexError as exc:
        raise ParseError(str(exc)) from exc


def split_top_level(text: str, sep: str) -> list[str]:
    """Split on ``sep`` occurrences that are outside quotes and parentheses."""
    parts: list[str] = []
    depth = 0
    quote = False
    current: list[str] = []
    for ch in text:
        if ch == '"':
            quote = not quote
        elif not quote:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(depth - 1, 0)
            elif ch == sep and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(ch)
    parts.append("".join(current))
    return parts


def _find_top_level(text: str, ch: str) -> int:
    quote = False
    for i, c in enumerate(text):
        if c == '"':
            quote = not quote
        elif c == ch and not quote:
            return i
    return -1


def _parse_statement(text: str, line_no: int, is_label: bool, params: list[ParamDef]) -> Statement:
    if is_label:
        m = _LABEL_RE.match(text)
        if not m:
            raise ParseError("malformed label statement")
        label = m.group(1)
        rest = m.group(2)
        canon = _LABEL_ALIASES.get(label, label)
        if canon in _TEXT_LABELS:
            return Text(canon, rest, line_no)
        if canon in _LIST_LABELS:
            return TextList(canon, tuple(rest.split("\\")), line_no)
        if len(params) >= len(PARAM_VARS):
            raise ParseError("more than 10 parameters")
        param = ParamDef(PARAM_VARS[len(params)], label, tuple(rest.split("\\")), line_no)
        params.append(param)
        return param
    if text.startswith("::"):
        return Price(parse_expression(text[2:]), line_no)
    if text.startswith("%%:"):
        return AuxPercent(parse_expression(text[3:]), True, line_no)
    if text.startswith("%:"):
        return AuxPercent(parse_expression(text[2:]), False, line_no)
    m = _ASSIGN_RE.match(text)
    if m:
        kind, name, dims_text, rhs = m.groups()
        values = split_top_level(rhs, ",")
        while values and not values[-1].strip():
            values.pop()
        exprs = tuple(parse_expression(v) for v in values)
        dims = tuple(int(d) for d in dims_text.split(",")) if dims_text else None
        if dims is not None:
            expected = math.prod(dims)
            if expected != len(exprs):
                raise ParseError(f"{kind}{name}{dims} declares {expected} values but {len(exprs)} given")
        if not exprs:
            raise ParseError(f"empty assignment to {kind}{name}")
        return Assign(kind, name, dims, exprs, line_no)
    colon = _find_top_level(text, ":")
    if colon > 0:
        code_template = re.sub(r"\s+", "", text[:colon])
        parts = split_top_level(text[colon + 1:], ":")
        expr = parse_expression(parts[0])
        factor = parse_expression(parts[1]) if len(parts) > 1 and parts[1].strip() else None
        return Decomp(code_template, expr, factor, line_no)
    raise ParseError(f"unrecognised statement {text[:60]!r}")


def parse_family(code: str, body: str) -> Family:
    family = Family(code)
    for st in extract_statements(body):
        try:
            node = _parse_statement(st.text, st.line_no, st.is_label, family.params)
        except ParseError as exc:
            raise ParseError(exc.message, code, st.line_no) from None
        family.statements.append(node)
    return family
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_parser.py -q`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/param/parser.py tests/test_parser.py
git commit -m "Add parametric expression and family parser

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: Evaluator

**Files:**
- Create: `bc3param/param/evaluator.py`
- Test: `tests/test_evaluator.py`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_evaluator.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/param/evaluator.py`**

```python
"""Sequential interpreter for one option selection of a parametric family."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence, Union

from .ast import (
    Assign, AuxPercent, Binary, Call, Const, Decomp, Expr, Family, Index, Num, NumVar, ParamDef,
    Price, Str, Text, TextList, TextVar, Unary,
)
from .codes import index_to_letter, letter_to_index
from .parser import parse_expression

DEFAULT_ERROR = "Combinación no válida"
_ATOF_RE = re.compile(r"^\s*[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)")
_VAR_RE = re.compile(r"%%|([%$])([A-Z])(?:\(([^()]*)\))?")
_CMP = {"<", ">", "<=", ">=", "=", "<>"}


class EvalError(Exception):
    pass


def atof(text: str) -> float:
    m = _ATOF_RE.match(text)
    if not m:
        return 0.0
    return float(m.group().strip().replace(",", "."))


def ftoa(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")


@dataclass
class Matrix:
    dims: tuple[int, ...]
    values: list

    def get(self, idx: tuple[int, ...]):
        if len(idx) != len(self.dims):
            raise EvalError(f"matrix needs {len(self.dims)} indices, got {len(idx)}")
        flat = 0
        for n, (k, d) in enumerate(zip(idx, self.dims), 1):
            if not 1 <= k <= d:
                raise EvalError(f"index {k} out of range 1..{d} in dimension {n}")
            flat = flat * d + (k - 1)
        return self.values[flat]


Value = Union[float, str, Matrix]


@dataclass
class Evaluation:
    valid: bool = True
    error: str | None = None
    resumen: str | None = None
    texto: str | None = None
    comment: str | None = None
    lines: list[tuple[str, float]] = field(default_factory=list)
    direct_price: float | None = None
    aux_percent: float | None = None
    texts: dict[str, tuple[str, ...]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class Evaluator:
    def __init__(self, family: Family, selection: Sequence[int]) -> None:
        if len(selection) != len(family.params):
            raise EvalError(f"{family.code}: expected {len(family.params)} options, got {len(selection)}")
        self.family = family
        self.selection = tuple(selection)
        self.num: dict[str, Value] = {}
        self.text: dict[str, Value] = {}
        for param, k in zip(family.params, self.selection):
            if not 1 <= k <= len(param.options):
                raise EvalError(f"{family.code}: option {k} out of range for parameter {param.var}")
            self.num[param.var] = float(k)
            self.text[param.var] = param.options[k - 1]
        self.result = Evaluation()
        self._lines: dict[str, float] = {}
        self._warned: set[str] = set()

    # ---- driver ----------------------------------------------------------
    def run(self) -> Evaluation:
        for st in self.family.statements:
            self._exec(st)
        # first-occurrence order; repeated codes were summed; exact zeros are dropped here,
        # quantities that round to zero are dropped by the pricer.
        self.result.lines = [(code, qty) for code, qty in self._lines.items() if qty != 0]
        return self.result

    def _warn(self, message: str) -> None:
        if message not in self._warned:
            self._warned.add(message)
            self.result.warnings.append(message)

    def _exec(self, st) -> None:
        if isinstance(st, ParamDef):
            return
        if isinstance(st, Assign):
            values = [self._eval(v) for v in st.values]
            if st.kind == "%":
                values = [self._to_num(v) for v in values]
                store = self.num
            else:
                values = [self._to_text(v) for v in values]
                store = self.text
            if st.dims:
                value: Value = Matrix(st.dims, values)
            elif len(values) == 1:
                value = values[0]
            else:
                value = Matrix((len(values),), values)
            store[st.name] = value
            if st.kind == "%" and st.name == "E" and not isinstance(value, Matrix) and self._truthy(value):
                if self.result.valid:
                    self.result.valid = False
                    message = self.text.get("E")
                    self.result.error = message if isinstance(message, str) and message else DEFAULT_ERROR
        elif isinstance(st, Decomp):
            code = self._substitute(st.code_template)
            qty = self._to_num(self._eval(st.expr))
            if st.factor is not None:
                qty *= self._to_num(self._eval(st.factor))
            self._lines[code] = self._lines.get(code, 0.0) + qty
        elif isinstance(st, Price):
            self.result.direct_price = self._to_num(self._eval(st.expr))
        elif isinstance(st, AuxPercent):
            v = self._to_num(self._eval(st.expr))
            self.result.aux_percent = v if st.per_unit else v / 100.0
        elif isinstance(st, Text):
            rendered = self._render(st.template)
            if st.label == "RESUMEN":
                self.result.resumen = rendered
            elif st.label == "TEXTO":
                self.result.texto = rendered
            else:
                self.result.comment = rendered
        elif isinstance(st, TextList):
            self.result.texts[st.label] = tuple(self._render(t) for t in st.items)

    # ---- values ----------------------------------------------------------
    @staticmethod
    def _truthy(v: Value) -> bool:
        if isinstance(v, str):
            return v != ""
        if isinstance(v, Matrix):
            raise EvalError("matrix used as a condition")
        return v != 0

    @staticmethod
    def _to_num(v: Value) -> float:
        if isinstance(v, str):
            return atof(v)
        if isinstance(v, Matrix):
            raise EvalError("matrix used as a number")
        return float(v)

    @staticmethod
    def _to_text(v: Value) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, Matrix):
            raise EvalError("matrix used as text")
        return ftoa(v)

    def _lookup(self, kind: str, name: str) -> Value:
        store = self.num if kind == "%" else self.text
        if name in store:
            return store[name]
        self._warn(f"undefined variable {kind}{name}")
        return 0.0 if kind == "%" else ""

    def _index_value(self, kind: str, name: str, args: Sequence[Value]) -> Value:
        value = self._lookup(kind, name)
        if not isinstance(value, Matrix):
            if not args:
                return value
            raise EvalError(f"{kind}{name} is not a matrix")
        if not args:
            if len(value.values) == 1:
                return value.values[0]
            raise EvalError(f"{kind}{name} is a matrix and needs indices")
        idx = tuple(int(round(self._to_num(a))) for a in args)
        return value.get(idx)

    # ---- expressions -----------------------------------------------------
    def _eval(self, e: Expr) -> Value:
        if isinstance(e, Num):
            return e.value
        if isinstance(e, Str):
            return e.value
        if isinstance(e, Const):
            return float(letter_to_index(e.letter))
        if isinstance(e, NumVar):
            return self._index_value("%", e.name, ())
        if isinstance(e, TextVar):
            return self._index_value("$", e.name, ())
        if isinstance(e, Index):
            kind = "%" if isinstance(e.var, NumVar) else "$"
            return self._index_value(kind, e.var.name, [self._eval(a) for a in e.args])
        if isinstance(e, Call):
            return self._call(e.fn, [self._eval(a) for a in e.args])
        if isinstance(e, Unary):
            v = self._eval(e.operand)
            if e.op == "!":
                return 0.0 if self._truthy(v) else 1.0
            return -self._to_num(v)
        if isinstance(e, Binary):
            return self._binary(e.op, self._eval(e.left), self._eval(e.right))
        raise EvalError(f"unknown node {e!r}")

    def _binary(self, op: str, l: Value, r: Value) -> Value:
        if op == "@":
            return 1.0 if self._truthy(l) or self._truthy(r) else 0.0
        if op == "&":
            return 1.0 if self._truthy(l) and self._truthy(r) else 0.0
        if op in _CMP:
            if isinstance(l, str) and isinstance(r, str):
                a, b = l, r
            else:
                a, b = self._to_num(l), self._to_num(r)
            ok = {"<": a < b, ">": a > b, "<=": a <= b, ">=": a >= b, "=": a == b, "<>": a != b}[op]
            return 1.0 if ok else 0.0
        if op == "+":
            if isinstance(l, str) or isinstance(r, str):
                return self._to_text(l) + self._to_text(r)
            return self._to_num(l) + self._to_num(r)
        if op == "*":
            if isinstance(l, str) and not isinstance(r, str):
                return l if self._to_num(r) != 0 else ""
            if isinstance(r, str) and not isinstance(l, str):
                return r if self._to_num(l) != 0 else ""
            return self._to_num(l) * self._to_num(r)
        a, b = self._to_num(l), self._to_num(r)
        if op == "-":
            return a - b
        if op == "/":
            if b == 0:
                raise EvalError("division by zero")
            return a / b
        if op == "^":
            return a ** b
        raise EvalError(f"unknown operator {op}")

    def _call(self, fn: str, args: list[Value]) -> Value:
        if fn == "ATOF":
            return atof(self._to_text(args[0]))
        if fn == "FTOA":
            return ftoa(self._to_num(args[0]))
        n = [self._to_num(a) for a in args]
        if fn == "ABS":
            return abs(n[0])
        if fn == "INT":
            return float(math.trunc(n[0]))
        if fn == "ROUND":
            places = int(n[1]) if len(n) > 1 else 0
            return float(Decimal(repr(n[0])).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))
        if fn == "SIN":
            return math.sin(math.radians(n[0]))
        if fn == "COS":
            return math.cos(math.radians(n[0]))
        if fn == "TAN":
            return math.tan(math.radians(n[0]))
        if fn == "ASIN":
            return math.degrees(math.asin(n[0]))
        if fn == "ACOS":
            return math.degrees(math.acos(n[0]))
        if fn == "ATAN":
            return math.degrees(math.atan(n[0]))
        if fn == "ATAN2":
            return math.degrees(math.atan2(n[0], n[1]))
        if fn == "SQRT":
            if n[0] < 0:
                raise EvalError("square root of negative number")
            return math.sqrt(n[0])
        raise EvalError(f"unknown function {fn}")

    # ---- substitution in templates --------------------------------------
    def _template_arg(self, text: str) -> Value:
        return self._eval(parse_expression(text))

    def _substitute(self, template: str) -> str:
        def repl(m: re.Match) -> str:
            if m.group(0) == "%%":
                return "%"
            kind, name, args_text = m.group(1), m.group(2), m.group(3)
            args = [self._template_arg(a) for a in args_text.split(",")] if args_text is not None else []
            value = self._index_value(kind, name, args)
            if kind == "$":
                return self._to_text(value)
            index = int(round(self._to_num(value)))
            try:
                return index_to_letter(index)
            except ValueError:
                raise EvalError(f"%{name} = {index} cannot be written as an option letter") from None

        return _VAR_RE.sub(repl, template)

    def _render(self, template: str) -> str:
        text = self._substitute(template)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        return "\n".join(lines).strip()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_evaluator.py -q`
Expected: 16 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/param/evaluator.py tests/test_evaluator.py
git commit -m "Add sequential evaluator for parametric families

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 9: Pricing

**Files:**
- Create: `bc3param/pricing.py`
- Test: `tests/test_pricing.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

from decimal import Decimal

import pytest

from bc3param.fiebdc import Bc3Error, Catalog
from bc3param.param.evaluator import Evaluation
from bc3param.pricing import Pricer, is_percentage, percentage_prefix, quantize

SNIPPET = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|MOC0000100|h|CAPATAZ|22.66||1|\n"
    "~C|MOC0000400|h|PEÓN ESPECIALISTA|21.00||1|\n"
    "~C|MOC0000500|h|PEÓN|20.66||1|\n"
    "~C|MN01060004|m³|HORMIGÓN|73.88||3|\n"
    "~C|AU10100001|m³|HORMIGÓN EN MASA HM-20|80.00||EA|\n"
    "~C|AU10100002|m³|AUX SIN LINEAS|||EA|\n"
    "~C|%CIND|%|Costes indirectos|||%|\n"
    "~C|%VOL|%|Sobrecoste por volumen escaso|||%|\n"
    "~C|MO%X|%|Sólo mano de obra|||%|\n"
    "~D|AU10100001|MOC0000100\\\\0.0080\\MOC0000400\\\\0.0800\\MOC0000500\\\\0.0400\\MN01060004\\\\1.0500\\|\n"
    "~D|CYC1|CYC2\\\\1\\|\n"
    "~D|CYC2|CYC1\\\\1\\|\n"
)


@pytest.fixture
def pricer() -> Pricer:
    return Pricer(Catalog.from_text(SNIPPET))


def test_quantize_half_up():
    assert quantize(Decimal("0.05115"), 4) == Decimal("0.0512")
    assert quantize(Decimal("0.08333"), 4) == Decimal("0.0833")
    assert quantize(Decimal("35.0778"), 2) == Decimal("35.08")


def test_percentage_helpers():
    assert is_percentage("%CIND") and is_percentage("MO%X") and not is_percentage("MOC0000100")
    assert percentage_prefix("%CIND") == "" and percentage_prefix("MO%X") == "MO"


def test_composite_price_from_decomposition_prevails_over_c_price(pricer):
    pc = pricer.concept_price("AU10100001")
    # 22.66*0.008=0.18 ; 21*0.08=1.68 ; 20.66*0.04=0.83 ; 73.88*1.05=77.57  -> 80.26
    assert [(l.code, l.quantity, l.amount) for l in pc.lines] == [
        ("MOC0000100", Decimal("0.0080"), Decimal("0.18")),
        ("MOC0000400", Decimal("0.0800"), Decimal("1.68")),
        ("MOC0000500", Decimal("0.0400"), Decimal("0.83")),
        ("MN01060004", Decimal("1.0500"), Decimal("77.57")),
    ]
    assert pc.price == Decimal("80.26")
    assert pc.unit == "m³" and pc.type == "EA"
    assert any("differs" in w for w in pc.warnings)
    assert pricer.concept_price("AU10100001") is pc  # cached


def test_simple_and_unknown_concepts(pricer):
    assert pricer.concept_price("MOC0000100").price == Decimal("22.66")
    unknown = pricer.concept_price("NOPE")
    assert unknown.price == 0 and unknown.warnings == ["unknown concept NOPE"]
    nolines = pricer.concept_price("AU10100002")
    assert nolines.price == 0 and nolines.warnings == ["AU10100002 has no price"]


def test_cycle_raises(pricer):
    with pytest.raises(Bc3Error):
        pricer.concept_price("CYC1")


def test_price_lines_with_percentages_and_masks(pricer):
    lines, total = pricer.price_lines([
        ("MOC0000100", 0.0558), ("MN01060004", 0.0), ("AU10100001", 0.165),
        ("MO%X", 0.10), ("%VOL", 0.20), ("%CIND", 0.06),
    ])
    assert [l.code for l in lines] == ["MOC0000100", "AU10100001", "MO%X", "%VOL", "%CIND"]
    assert lines[0].amount == Decimal("1.26")           # 22.66*0.0558=1.264
    assert lines[1].amount == Decimal("13.24")          # 80.26*0.165=13.243
    assert lines[2].price == Decimal("1.26") and lines[2].amount == Decimal("0.13")  # mask MO
    assert lines[3].price == Decimal("14.63") and lines[3].amount == Decimal("2.93")  # 20% of all previous incl. %
    assert lines[4].price == Decimal("17.56") and lines[4].amount == Decimal("1.05")
    assert lines[4].summary == "Costes indirectos" and lines[4].unit == "%"
    assert total == Decimal("18.61")


def test_price_evaluation(pricer):
    ev = Evaluation(lines=[("MOC0000100", 1.0), ("%CIND", 0.06)])
    lines, direct, total = pricer.price_evaluation(ev)
    assert direct == Decimal("22.66") and total == Decimal("24.02") and len(lines) == 2
    ev = Evaluation(direct_price=12.345)
    assert pricer.price_evaluation(ev) == ([], None, Decimal("12.35"))
    ev = Evaluation(lines=[("MOC0000100", 1.0)], aux_percent=0.03)
    lines, direct, total = pricer.price_evaluation(ev)
    assert lines[-1].code == "%" and lines[-1].summary == "Medios auxiliares" and total == Decimal("23.34")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_pricing.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/pricing.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_pricing.py -q`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/pricing.py tests/test_pricing.py
git commit -m "Add pricing with ~K rounding and percentage concepts

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 10: Item model and generation

**Files:**
- Create: `bc3param/model.py`, `bc3param/generate.py`
- Modify: `bc3param/__init__.py`
- Test: `tests/test_generate.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import io
import json

import pytest

from bc3param.fiebdc import Bc3Error, Catalog
from bc3param.generate import (
    build_item, iter_items, resolve_code, select_families, selections, write_json, write_jsonl,
)
from bc3param.model import Item
from bc3param.pricing import Pricer

SNIPPET = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|R_A_I_Z##||BASE||||\n"
    "~C|O#||OBRA CIVIL||||\n"
    "~C|OEB#||ZANJAS||||\n"
    "~C|OEC#||ARQUETAS||||\n"
    "~C|OEB020$|m|CANALIZACIÓN HORMIGONADA||21022019||\n"
    "~C|OEB030$|m|OTRA||||\n"
    "~C|OEC010$|ud|ARQUETA||||\n"
    "~C|OEB060|m|SIMPLE|5||3|\n"
    "~C|MOC0000101|h|CAPATAZ NOCTURNO|28.33||1|\n"
    "~C|MN10010001|m|TUBO PVC 110|3.21||3|\n"
    "~C|%CIND|%|Costes indirectos|||%|\n"
    "~D|R_A_I_Z##|O#\\\\\\|\n"
    "~D|O#|OEB#\\\\\\OEC#\\\\\\|\n"
    "~D|OEB#|OEB020$\\\\\\OEB030$\\\\\\OEB060\\\\\\|\n"
    "~D|OEC#|OEC010$\\\\\\|\n"
    "~P|OEB020$|\\Nº TUBOS \\ 2 \\ 4 \\\n"
    "\\TRABAJO\\Diurno\\Nocturno\\\n"
    "$E= \"Combinación inexistente\"\n"
    "%E= (%A=b & %B=b)\n"
    "%L(2)=2,4\n"
    "MOC0000101 : 0.05*(%B=b)\n"
    "MN10010001 : %L(%A)\n"
    "%%CIND: 0.06\n"
    "$G(2)=\"D\",\"N\"\n"
    "\\RESUMEN\\Canalización de $A T. ($G(%B))\\\n"
    "\\TEXTO\\Canalización de $A tubos.\nTrabajo: $B\\|\n"
    "~P|OEB030$|\\X\\a\\\nMN10010001: 1\\|\n"
    "~P|OEC010$|\\X\\a\\\nMN10010001: 2\\|\n"
)


@pytest.fixture
def cat() -> Catalog:
    return Catalog.from_text(SNIPPET)


def test_selections_order_last_parameter_fastest(cat):
    fam = cat.family("OEB020$")
    assert list(selections(fam)) == [(1, 1), (1, 2), (2, 1), (2, 2)]


def test_build_item_valid(cat):
    item = build_item(cat, Pricer(cat), cat.family("OEB020$"), (1, 2))
    assert isinstance(item, Item)
    d = item.to_dict()
    assert d["code"] == "OEB020ab" and d["family"] == "OEB020$" and d["unit"] == "m"
    assert d["family_summary"] == "CANALIZACIÓN HORMIGONADA"
    assert d["chapter_path"] == ["O#", "OEB#"]
    assert d["parameters"] == [
        {"var": "A", "name": "Nº TUBOS", "option": 1, "letter": "a", "label": " 2 "},
        {"var": "B", "name": "TRABAJO", "option": 2, "letter": "b", "label": "Nocturno"},
    ]
    assert d["resumen"] == "Canalización de 2 T. (N)"
    assert d["texto"] == "Canalización de 2 tubos.\nTrabajo: Nocturno"
    assert d["valid"] is True and d["error"] is None
    # 28.33*0.05=1.42 ; 3.21*2=6.42 ; direct 7.84 ; CIND 0.47 ; total 8.31
    assert d["direct_cost"] == 7.84 and d["price"] == 8.31
    assert d["decomposition"] == [
        {"code": "MOC0000101", "unit": "h", "summary": "CAPATAZ NOCTURNO", "type": "1",
         "price": 28.33, "quantity": 0.05, "amount": 1.42},
        {"code": "MN10010001", "unit": "m", "summary": "TUBO PVC 110", "type": "3",
         "price": 3.21, "quantity": 2.0, "amount": 6.42},
        {"code": "%CIND", "unit": "%", "summary": "Costes indirectos", "type": "%",
         "price": 7.84, "quantity": 0.06, "amount": 0.47},
    ]
    assert d["warnings"] == []
    assert list(d) == ["code", "family", "unit", "family_summary", "chapter_path", "parameters", "resumen",
                       "texto", "valid", "error", "direct_cost", "price", "decomposition", "warnings"]


def test_build_item_invalid_and_without_decomposition(cat):
    item = build_item(cat, Pricer(cat), cat.family("OEB020$"), (2, 2))
    d = item.to_dict()
    assert d["valid"] is False and d["error"] == "Combinación inexistente"
    assert d["price"] is None and d["direct_cost"] is None and d["decomposition"] == []
    assert d["resumen"] == "Canalización de 4 T. (N)"
    item = build_item(cat, Pricer(cat), cat.family("OEB020$"), (1, 1), with_decomposition=False)
    assert item.price is not None and item.decomposition == []


def test_select_families(cat):
    assert select_families(cat, chapter="OEB#") == ["OEB020$", "OEB030$"]
    assert select_families(cat, chapter="O#") == ["OEB020$", "OEB030$", "OEC010$"]
    assert select_families(cat, range_="OEB025..OEC010") == ["OEB030$", "OEC010$"]
    assert select_families(cat, families=["OEC010$", "OEB020"]) == ["OEB020$", "OEC010$"]
    with pytest.raises(Bc3Error):
        select_families(cat, families=["NOPE$"])
    with pytest.raises(Bc3Error):
        select_families(cat, chapter="ZZZ#")
    with pytest.raises(Bc3Error):
        select_families(cat)


def test_iter_items_and_writers(cat):
    items = list(iter_items(cat, ["OEB020$"]))
    assert [i.code for i in items] == ["OEB020aa", "OEB020ab", "OEB020ba"]
    items = list(iter_items(cat, ["OEB020$"], include_invalid=True))
    assert [i.code for i in items] == ["OEB020aa", "OEB020ab", "OEB020ba", "OEB020bb"]
    buf = io.StringIO()
    n = write_jsonl(iter_items(cat, ["OEB030$"]), buf)
    assert n == 1 and json.loads(buf.getvalue().strip())["code"] == "OEB030a"
    buf = io.StringIO()
    n = write_json(iter_items(cat, ["OEB030$", "OEC010$"]), buf)
    assert n == 2 and [x["code"] for x in json.loads(buf.getvalue())] == ["OEB030a", "OEC010a"]


def test_resolve_code(cat):
    assert resolve_code(cat, "OEB020ab").code == "OEB020ab"
    assert resolve_code(cat, "OEB020$", (1, 2)).code == "OEB020ab"
    with pytest.raises(Bc3Error):
        resolve_code(cat, "OEB020abc")
    with pytest.raises(Bc3Error):
        resolve_code(cat, "XXXXXXab")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_generate.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/model.py`**

```python
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
```

- [ ] **Step 4: Implement `bc3param/generate.py`**

```python
"""Expand parametric families into Items and write them out."""
from __future__ import annotations

import itertools
import json
from typing import IO, Iterable, Iterator, Sequence

from .fiebdc import Bc3Error, Catalog, code_key
from .model import DecompLine, Item, ParameterChoice
from .param.ast import Family
from .param.codes import derived_code, index_to_letter, split_derived_code
from .param.evaluator import EvalError, Evaluation, Evaluator
from .pricing import Pricer


def selections(family: Family) -> Iterator[tuple[int, ...]]:
    """All option tuples, last parameter varying fastest (same order as code letters)."""
    return itertools.product(*(range(1, n + 1) for n in family.option_counts()))


def build_item(catalog: Catalog, pricer: Pricer, family: Family, selection: Sequence[int],
               with_decomposition: bool = True) -> Item:
    concept = catalog.concept(family.code)
    try:
        ev = Evaluator(family, selection).run()
    except EvalError as exc:
        ev = Evaluation(valid=False, error=f"evaluation error: {exc}")
    params = [
        ParameterChoice(p.var, p.name, k, index_to_letter(k), p.options[k - 1] if k <= len(p.options) else "")
        for p, k in zip(family.params, selection)
    ]
    item = Item(
        code=derived_code(family.code, selection),
        family=family.code,
        unit=concept.unit if concept else "",
        family_summary=concept.summary if concept else "",
        chapter_path=catalog.chapter_path(family.code),
        parameters=params,
        resumen=ev.resumen,
        texto=ev.texto,
        valid=ev.valid,
        error=ev.error,
        warnings=list(ev.warnings),
    )
    if not ev.valid:
        return item
    try:
        lines, direct, total = pricer.price_evaluation(ev)
    except Bc3Error as exc:
        item.valid = False
        item.error = f"pricing error: {exc}"
        return item
    item.direct_cost = direct
    item.price = total
    for line in lines:
        if line.warning:
            item.warnings.append(line.warning)
    if with_decomposition:
        item.decomposition = [
            DecompLine(l.code, l.unit, l.summary, l.type, l.price, l.quantity, l.amount) for l in lines
        ]
    return item


def _chapter_families(catalog: Catalog, chapter: str, out: set[str], seen: set[str]) -> None:
    key = code_key(chapter)
    if key in seen:
        return
    seen.add(key)
    for child in catalog.children(chapter):
        if child in catalog.families_raw:
            out.add(child)
        elif code_key(child) in catalog.decompositions:
            _chapter_families(catalog, child, out, seen)


def select_families(catalog: Catalog, chapter: str | None = None, range_: str | None = None,
                    families: Iterable[str] | None = None) -> list[str]:
    codes: set[str] = set()
    if chapter is not None:
        if code_key(chapter) not in catalog.decompositions:
            raise Bc3Error(f"unknown chapter {chapter!r}")
        _chapter_families(catalog, chapter, codes, set())
    if range_ is not None:
        start, sep, end = range_.partition("..")
        if not sep or not start or not end:
            raise Bc3Error("range must be START..END, e.g. OEB010..OEB300")
        start, end = start.rstrip("$"), end.rstrip("$")
        codes.update(f for f in catalog.families_raw if start <= f.rstrip("$") <= end)
    if families is not None:
        for f in families:
            code = f if f.endswith("$") else f + "$"
            if code not in catalog.families_raw:
                raise Bc3Error(f"unknown parametric family {f!r}")
            codes.add(code)
    if chapter is None and range_ is None and families is None:
        raise Bc3Error("nothing selected: give a chapter, a range or family codes")
    return sorted(codes)


def iter_items(catalog: Catalog, family_codes: Iterable[str], include_invalid: bool = False,
               with_decomposition: bool = True, pricer: Pricer | None = None) -> Iterator[Item]:
    pricer = pricer or Pricer(catalog)
    for code in family_codes:
        family = catalog.family(code)
        for sel in selections(family):
            item = build_item(catalog, pricer, family, sel, with_decomposition)
            if item.valid or include_invalid:
                yield item


def resolve_code(catalog: Catalog, code: str, selection: Sequence[int] | None = None,
                 with_decomposition: bool = True) -> Item:
    """Resolve a derived code (``OEB020bbbaa``) or a family code plus selection."""
    if selection is None:
        try:
            family_code, selection = split_derived_code(code, catalog.families_raw)
        except ValueError as exc:
            raise Bc3Error(str(exc)) from None
    else:
        family_code = code if code.endswith("$") else code + "$"
        if family_code not in catalog.families_raw:
            raise Bc3Error(f"unknown parametric family {code!r}")
    family = catalog.family(family_code)
    counts = family.option_counts()
    if len(selection) != len(counts) or any(not 1 <= k <= n for k, n in zip(selection, counts)):
        raise Bc3Error(f"{code}: selection {selection} does not fit parameters with {counts} options")
    return build_item(catalog, Pricer(catalog), family, selection, with_decomposition)


def write_jsonl(items: Iterable[Item], fp: IO[str]) -> int:
    n = 0
    for item in items:
        fp.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
        n += 1
    return n


def write_json(items: Iterable[Item], fp: IO[str]) -> int:
    fp.write("[\n")
    n = 0
    for item in items:
        if n:
            fp.write(",\n")
        fp.write(json.dumps(item.to_dict(), ensure_ascii=False))
        n += 1
    fp.write("\n]\n")
    return n
```

- [ ] **Step 5: Export the public API in `bc3param/__init__.py`**

```python
"""bc3param: parametric FIEBDC-3 catalogue engine."""
from __future__ import annotations

from .fiebdc import Bc3Error, Catalog
from .generate import build_item, iter_items, resolve_code, select_families, write_json, write_jsonl
from .model import DecompLine, Item, ParameterChoice
from .param.evaluator import EvalError, Evaluator
from .param.parser import ParseError
from .pricing import Pricer

__version__ = "0.1.0"
__all__ = [
    "Bc3Error", "Catalog", "DecompLine", "EvalError", "Evaluator", "Item", "ParameterChoice",
    "ParseError", "Pricer", "build_item", "iter_items", "resolve_code", "select_families",
    "write_json", "write_jsonl",
]
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests -q`
Expected: all passed (about 60 tests)

- [ ] **Step 7: Commit**

```bash
git add bc3param/model.py bc3param/generate.py bc3param/__init__.py tests/test_generate.py
git commit -m "Add item model, family expansion and JSON writers

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 11: CLI

**Files:**
- Create: `bc3param/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
from __future__ import annotations

import json

import pytest

from bc3param.cli import main
from tests.test_generate import SNIPPET


@pytest.fixture
def bc3(tmp_path):
    p = tmp_path / "mini.bc3"
    p.write_bytes(SNIPPET.encode("cp1252"))
    return p


def test_validate_ok(bc3, capsys):
    assert main(["validate", str(bc3)]) == 0
    out = capsys.readouterr().out
    assert "3 families" in out and "0 errors" in out


def test_validate_reports_errors(tmp_path, capsys):
    p = tmp_path / "bad.bc3"
    p.write_text("~V|||\n~P|BAD001$|\\A\\a\\\n%M(2,2)=1,2\\|\n", encoding="cp1252")
    assert main(["validate", str(p)]) == 1
    out = capsys.readouterr().out
    assert "BAD001$ line 2" in out and "1 errors" in out


def test_inspect(bc3, capsys):
    assert main(["inspect", str(bc3), "OEB020$"]) == 0
    out = capsys.readouterr().out
    assert "A  Nº TUBOS" in out and "1: ' 2 '" in out and "Nocturno" in out
    assert "combinations: 4" in out


def test_resolve_derived_and_selection(bc3, capsys):
    assert main(["resolve", str(bc3), "OEB020ab"]) == 0
    d = json.loads(capsys.readouterr().out)
    assert d["code"] == "OEB020ab" and d["price"] == 8.31
    assert main(["resolve", str(bc3), "OEB020$", "-s", "1,2"]) == 0
    assert json.loads(capsys.readouterr().out)["code"] == "OEB020ab"


def test_resolve_unknown_code_fails(bc3, capsys):
    assert main(["resolve", str(bc3), "ZZZ999ab"]) == 1
    assert "error" in capsys.readouterr().err


def test_generate_jsonl_and_json(bc3, tmp_path, capsys):
    out = tmp_path / "items.jsonl"
    assert main(["generate", str(bc3), "--chapter", "OEB#", "--out", str(out)]) == 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert [json.loads(l)["code"] for l in lines] == ["OEB020aa", "OEB020ab", "OEB020ba", "OEB030a"]
    assert "4 items" in capsys.readouterr().err
    out2 = tmp_path / "items.json"
    assert main(["generate", str(bc3), "--family", "OEB020$", "--format", "json", "--include-invalid",
                 "--no-decomposition", "--limit", "2", "--out", str(out2)]) == 0
    data = json.loads(out2.read_text(encoding="utf-8"))
    assert [x["code"] for x in data] == ["OEB020aa", "OEB020ab"] and data[0]["decomposition"] == []


def test_generate_range_to_stdout(bc3, capsys):
    assert main(["generate", str(bc3), "--range", "OEC000..OEC999"]) == 0
    assert json.loads(capsys.readouterr().out.strip())["code"] == "OEC010a"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_cli.py -q`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement `bc3param/cli.py`**

```python
"""Command line interface: bc3param validate | inspect | resolve | generate."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence

from .fiebdc import Bc3Error, Catalog
from .generate import iter_items, resolve_code, select_families, write_json, write_jsonl
from .param.parser import ParseError


def _load(path: str) -> Catalog:
    p = Path(path)
    if not p.is_file():
        raise Bc3Error(f"file not found: {path}")
    return Catalog.load(p)


def cmd_validate(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    codes = [args.family] if args.family else catalog.families
    errors: list[ParseError] = []
    for code in codes:
        try:
            catalog.family(code)
        except ParseError as exc:
            errors.append(exc)
    for exc in errors:
        print(f"{exc.family} line {exc.line_no}: {exc.message}")
    print(f"{len(codes)} families, {len(errors)} errors")
    return 1 if errors else 0


def cmd_inspect(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    family = catalog.family(args.family if args.family.endswith("$") else args.family + "$")
    concept = catalog.concept(family.code)
    print(f"{family.code}  {concept.unit if concept else ''}  {concept.summary if concept else ''}")
    print("chapters: " + " > ".join(catalog.chapter_path(family.code)))
    for p in family.params:
        print(f"{p.var}  {p.name}")
        for i, opt in enumerate(p.options, 1):
            print(f"    {i}: {opt!r}")
    kinds: dict[str, int] = {}
    for st in family.statements:
        kinds[type(st).__name__] = kinds.get(type(st).__name__, 0) + 1
    print("statements: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    print(f"combinations: {math.prod(family.option_counts())}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    selection = tuple(int(x) for x in args.select.split(",")) if args.select else None
    item = resolve_code(catalog, args.code, selection, with_decomposition=not args.no_decomposition)
    print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    codes = select_families(catalog, chapter=args.chapter, range_=args.range,
                            families=args.family or None)
    print(f"{len(codes)} families selected", file=sys.stderr)

    def items():
        n = 0
        for code in codes:
            print(f"  {code}", file=sys.stderr)
            for item in iter_items(catalog, [code], include_invalid=args.include_invalid,
                                   with_decomposition=not args.no_decomposition):
                if args.limit is not None and n >= args.limit:
                    return
                n += 1
                yield item

    writer = write_json if args.format == "json" else write_jsonl
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fp:
            count = writer(items(), fp)
    else:
        count = writer(items(), sys.stdout)
    print(f"{count} items written", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bc3param", description="Parametric FIEBDC-3 catalogue engine")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="parse every ~P family and report errors")
    p.add_argument("file")
    p.add_argument("--family", help="only this family code")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("inspect", help="show parameters and options of a family")
    p.add_argument("file")
    p.add_argument("family")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("resolve", help="resolve one derived code or family+selection")
    p.add_argument("file")
    p.add_argument("code", help="derived code (OEB020bbbaa) or family code (OEB020$) with -s")
    p.add_argument("-s", "--select", help="1-based option numbers, e.g. 2,2,2,1,1")
    p.add_argument("--no-decomposition", action="store_true")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("generate", help="expand families to JSON/JSONL")
    p.add_argument("file")
    p.add_argument("--chapter", help="chapter code, e.g. OEB# (recursive)")
    p.add_argument("--range", help="START..END on family stems, e.g. OEB010..OEB300")
    p.add_argument("--family", action="append", help="family code (repeatable)")
    p.add_argument("--out", help="output path (default: stdout)")
    p.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    p.add_argument("--include-invalid", action="store_true")
    p.add_argument("--no-decomposition", action="store_true")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_generate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, AttributeError):  # pragma: no cover
                pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (Bc3Error, ParseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests -q`
Expected: all passed. Note: `capsys` captures via replaced streams; if `reconfigure` on a capture object raises, the `try` swallows it.

- [ ] **Step 5: Commit**

```bash
git add bc3param/cli.py tests/test_cli.py
git commit -m "Add bc3param command line interface

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 12: Reference tests on the real ADIF file

**Files:**
- Test: `tests/test_reference.py`

These tests encode what the three ADIF viewer PDFs and the 2024 file establish. They skip when `data/raw/BPA_2024_v2.txt` is missing.

- [ ] **Step 1: Write the tests**

```python
from __future__ import annotations

import math
from decimal import Decimal

import pytest

from bc3param.fiebdc import Catalog
from bc3param.generate import build_item, iter_items, resolve_code, select_families, selections
from bc3param.param.evaluator import EvalError, Evaluator
from bc3param.param.parser import ParseError
from bc3param.pricing import Pricer


@pytest.fixture(scope="module")
def catalog(raw_path) -> Catalog:
    return Catalog.load(raw_path)


def quantities(item) -> dict[str, float]:
    return {l.code: float(l.quantity) for l in item.decomposition}


def test_catalog_shape(catalog):
    assert len(catalog.families_raw) == 2996
    assert len(catalog.concepts) > 28000
    assert catalog.decimals.DR == 4 and catalog.decimals.DI == 2


def test_every_family_parses(catalog):
    errors = []
    for code in catalog.families:
        try:
            catalog.family(code)
        except ParseError as exc:
            errors.append(str(exc))
    assert errors == []


def test_au10100001_price_from_decomposition_matches_c_record(catalog):
    pc = Pricer(catalog).concept_price("AU10100001")
    assert pc.price == Decimal("88.39")
    assert [l.code for l in pc.lines][:3] == ["MOC0000100", "MOC0000400", "MOC0000500"]
    assert not any("differs" in w for w in pc.warnings)


def test_oeb010aaa_matches_viewer(catalog):
    item = resolve_code(catalog, "OEB010aaa")
    assert item.valid and item.chapter_path == ["O#", "OE#", "OEB#"]
    q = quantities(item)
    assert q["MOC0000100"] == 0.3667 and q["MOC0000200"] == 1.25 and q["MOC0000500"] == 3.667
    assert q["MQ04020010"] == 0.6667 and q["MQ05000010"] == 0.0833
    assert q["MN10010019"] == 5 and q["MN10010021"] == 2 and q["MN10010020"] == 4
    assert q["MN10010018"] == 6 and q["MN10010022"] == 4 and q["MN01010001"] == 0.076
    assert q["AU10100001"] == 1.35 and q["%CIND"] == 0.06
    assert item.resumen.endswith("(-/-/D)")
    assert item.resumen.startswith("Ejecución de canalización para línea subterranea doble circuito")
    assert "En terreno blando , sin reposición de pavimento." in item.texto
    assert item.texto.endswith("Condiciones de ejecución: Volumen relevante.")
    cind = [l for l in item.decomposition if l.code == "%CIND"][0]
    assert cind.price == item.direct_cost
    assert item.price == item.direct_cost + cind.amount


def test_oeb020bbbaa_matches_viewer_structure(catalog):
    item = resolve_code(catalog, "OEB020bbbaa")
    assert item.valid
    assert [p.letter for p in item.parameters] == ["b", "b", "b", "a", "a"]
    q = quantities(item)
    assert set(q) == {"MOC0000101", "MOC0000601", "MOC0000501", "MQ04000600", "MQ05020300", "MQ04070420",
                      "MQ03000005", "MQ0103D105", "MN10010001", "AU10100001", "%CIND"}
    assert q["MN10010001"] == 4 and q["AU10100001"] == 0.165
    assert q["MOC0000601"] == round(0.372 * 1.1, 4) and q["MQ04000600"] == 0.118
    assert item.resumen == "Canalización hormigonada de 4 T, PVC 110 mm, bajo vías. (N/>5/R)"
    assert item.texto.startswith(
        "Canalización hormigonada de 4 tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso el "
        "descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno"
    )
    assert "Trabajo: Nocturno" in item.texto and "Banda de mantenimiento: i >= 5 horas" in item.texto


def test_oeb020_excluded_combination(catalog):
    item = resolve_code(catalog, "OEB020ahaaa")  # 2 tubos con topo
    assert not item.valid and item.error == "Combinación inexistente en la base de datos"


def test_cla020_one_based_arithmetic(catalog):
    fam = catalog.family("CLA020$")
    assert not Evaluator(fam, (1, 1, 1, 1)).run().valid
    ev = Evaluator(fam, (2, 1, 1, 1)).run()
    assert ev.valid and dict(ev.lines)["MOE0000100"] == pytest.approx(55.857 + 5 * 8.379)


def test_eka100_sequential_redefinition_evaluates_everywhere(catalog):
    fam = catalog.family("EKA100$")
    for sel in selections(fam):
        Evaluator(fam, sel).run()


def test_eib030_text_array_with_literal_index(catalog):
    fam = catalog.family("EIB030$")
    ev = Evaluator(fam, tuple(1 for _ in fam.params)).run()
    assert ev.texto and "interruptor" in ev.texto


def test_all_families_evaluate_first_selection_without_crash(catalog):
    pricer = Pricer(catalog)
    crashes = []
    for code in catalog.families:
        fam = catalog.family(code)
        sel = tuple(1 for _ in fam.params)
        try:
            build_item(catalog, pricer, fam, sel)
        except Exception as exc:  # noqa: BLE001 - we want the full list
            crashes.append(f"{code}: {exc}")
    assert crashes == []


def test_oeb_chapter_expands_to_expected_count(catalog):
    codes = select_families(catalog, chapter="OEB#")
    assert "OEB020$" in codes
    total = sum(math.prod(catalog.family(c).option_counts()) for c in codes)
    assert total == 47508
    n = sum(1 for _ in iter_items(catalog, codes, include_invalid=True, with_decomposition=False))
    assert n == 47508
```

- [ ] **Step 2: Run the reference tests**

Run: `python -m pytest tests/test_reference.py -q -x`
Expected: the first run will very likely surface real-file surprises (unparsed statements, unexpected tokens, index errors). This step is a loop:

1. Read the failure (family code + line number are in the message).
2. Look at the source with `grep -n "^~P|CODE\$" data/raw/BPA_2024_v2_OEB_mod_utf8.txt` and `sed -n 'L,L+80p'` (the utf8 copy is easier to read; line numbers match the original).
3. Decide whether it is a data quirk to tolerate (add handling in `preprocess`/`parser`/`evaluator` with a unit test that reproduces the snippet) or a genuine authoring error in the catalogue (leave it; `validate` must report it, and then relax `test_every_family_parses` to assert the exact list of known bad families, documented in the test).
4. Re-run until green. Do not weaken the viewer-derived assertions (`OEB010aaa`, `OEB020bbbaa`, `AU10100001`): those are ground truth. The single allowed adjustment: the viewer PDFs come from the 2026 base while the file is 2024 v2, so if a literal text fragment (e.g. `En terreno blando , sin reposición de pavimento.`) is absent because the 2024 template wording differs, print the family's `\TEXTO\` template from the raw record, adapt the literal to the 2024 wording and leave a comment saying so. Quantities and the `(N/>5/R)` / `(-/-/D)` resumen suffixes must match as written.

Expected final: 12 passed (runtime a few minutes because of `test_oeb_chapter_expands_to_expected_count`).

- [ ] **Step 3: Run the whole suite and the CLI end-to-end**

Run:
```bash
python -m pytest tests -q
bc3param validate data/raw/BPA_2024_v2.txt
bc3param resolve data/raw/BPA_2024_v2.txt OEB020bbbaa
bc3param generate data/raw/BPA_2024_v2.txt --chapter OEB# --out data/processed/OEB_parametric.jsonl
```
Expected: all tests pass; `validate` prints `2996 families, 0 errors` (or the documented known-bad list); `resolve` prints the item JSON with 11 decomposition lines; `generate` writes 47,508 minus invalid lines and reports the count on stderr. Do not commit the generated JSONL (add `data/processed/OEB_parametric.jsonl` to `.gitignore` if git shows it).

- [ ] **Step 4: Commit**

```bash
git add tests/test_reference.py bc3param tests .gitignore
git commit -m "Add reference tests against ADIF viewer examples

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 13: Documentation

**Files:**
- Modify: `README.md` (append a section before "## Citation")

- [ ] **Step 1: Add the README section**

Insert before the `## Citation` heading:

````markdown
## bc3param: parametric engine (new)

`bc3param/` is a standalone, dependency-free Python package that parses the BC3 file and
reconstructs every derived unit of work defined by a parametric family (`~P` record), with
texts, decomposition and price, as shown by the ADIF viewer (https://bpa.adif.es/bp1/).
It replaces the notebook pipeline stages 1-5 for that purpose (the notebooks are kept as-is).

```bash
pip install -e .
bc3param validate data/raw/BPA_2024_v2.txt                 # parse all 2,996 families
bc3param inspect  data/raw/BPA_2024_v2.txt OEB020$          # parameters and options
bc3param resolve  data/raw/BPA_2024_v2.txt OEB020bbbaa      # one item as JSON
bc3param generate data/raw/BPA_2024_v2.txt --chapter OEB# --out OEB.jsonl
bc3param generate data/raw/BPA_2024_v2.txt --range OEB010..OEB300 --format json --out OEB.json
```

Python API:

```python
from bc3param import Catalog, resolve_code, iter_items, select_families

cat = Catalog.load("data/raw/BPA_2024_v2.txt")
item = resolve_code(cat, "OEB020bbbaa")
print(item.price, item.resumen)
for it in iter_items(cat, select_families(cat, chapter="OEB#")):
    ...
```

Semantics follow the FIEBDC-3/2020 specification with the conventions observed in the ADIF
base and viewer: option constants are 1-based (`a` = 1), statements are evaluated
sequentially, quantities round to 4 decimals and amounts to 2 (from `~K`), percentage
concepts (`%CIND`, `%VOL`) apply to the sum of previous lines, zero-quantity lines are
omitted, and `%E` exclusions mark combinations invalid. Design notes:
`docs/superpowers/specs/2026-09-05-bc3-parametric-engine-design.md`.
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Document bc3param usage

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## Self-review notes

- Spec coverage: encoding (T2), records/Catalog/`~K`/chapter path (T3), preprocessing rules (T4), lexer (T5), AST + codes (T6), grammar and statement classification incl. `::`, `%:`, `%%:`, labels and aliases, dims check (T7), evaluator semantics: 1-based, sequential, `%E`, merge, zero drop, undefined warnings, template rendering (T8), pricing rules and `~D` recursion with warning on mismatch (T9), output model and selection/iteration/writers (T10), CLI commands (T11), reference validation (T12), docs (T13). PLIEGO/CLAVES/COMERCIAL are stored on `Evaluation.texts` and not exported in JSON, per spec "out of scope beyond storing text".
- Names used consistently: `Catalog.families_raw`, `Catalog.family()`, `Catalog.children()`, `Catalog.chapter_path()`, `Pricer.concept_price()`, `Pricer.price_lines()`, `Pricer.price_evaluation()`, `Evaluator(...).run() -> Evaluation`, `build_item`, `iter_items`, `select_families`, `resolve_code`, `write_json`, `write_jsonl`, `split_derived_code`, `derived_code`, `index_to_letter`, `letter_to_index`.
- Known judgement calls carried from the spec: option labels are not trimmed (viewer behaviour); repeated decomposition codes are summed; `INT` truncates toward zero; `ATAN2(x, y)` follows the argument order written in the spec.
