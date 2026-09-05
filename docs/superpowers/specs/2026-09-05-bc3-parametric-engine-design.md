# BC3 parametric engine (`bc3param`) — design

Date: 2026-09-05
Branch: `claude/bc3-parametric-parser-bb6818`
Status: approved

## 1. Goal

Reconstruct, from a FIEBDC-3 (`.bc3`) price catalogue, every derived unit of work that a
parametric family (`~P` record) implicitly defines, with the same information that the ADIF
viewer (https://bpa.adif.es/bp1/) shows for one selection:

- derived code (e.g. `OEB020bbbaa`), unit, chapter path;
- resolved RESUMEN (short text) and TEXTO (long text);
- decomposition: one line per component with code, unit, summary, type, unit price,
  quantity and amount, plus percentage lines (`%CIND`, `%VOL`, ...);
- direct cost and total price;
- validity of the combination (`%E` / `$E`).

Deliverable is a Python package plus a CLI. A web viewer is out of scope for this phase.

## 2. Source facts that drive the design

Established by inspecting `data/raw/BPA_2024_v2.txt`, the FIEBDC-3/2020v2 specification and
three reference PDFs exported from the ADIF viewer (`OEB010aaa`, `OEB020bbbaa`, `AU10100001`).

- Source file is `data/raw/BPA_2024_v2.txt` (FIEBDC-3/2007, exported by Menfis, charset
  "ANSI" = cp1252; 60 bytes `0x81` are undefined in cp1252). `BPA_2024_v2_OEB_mod.txt` only
  rewrites OEB short-text arrays; the viewer uses the original abbreviations.
- Records: 28,634 `~C`, 2,996 `~P` (all codes are 7 chars with `$` at position 7), 2,176
  `~D`, 16,756 `~T`, 181 `~A`, one `~K`, one `~V`. `~D` uses only field 2 (`CHILD\FACTOR\YIELD\`).
- `~K` field 1 gives `DR=4` (yield decimals), `DI=2`, `DP=2`, `DC=2`.
- Percentage concepts: `%CI`, `%CIND`, `%VOL`, `%COMPPS` (`~C` with unit `%`, no price).
- Parametric sub-language constructs actually used: parameter statements; scalar and
  matrix assignments (`%X` up to 4 dims, `$X` up to 5 dims); decomposition lines
  `CODE : expr`; `%%CIND : 0.06` style lines (code `%CIND` after `%%` unescape);
  `%E = expr` (1,157 families) and `$E = "..."`; RESUMEN/TEXTO templates (multi-line in
  2,505 families, containing `Trabajo: $C` lines that look like decomposition lines);
  one `\PLIEGO\`; operators `+ - * / ^ @ & < > <= >= = <> !`; function `ATOF` only, but
  the spec set (`ABS INT ROUND SIN COS TAN ASIN ACOS ATAN ATAN2 SQRT ATOF FTOA`) will be
  implemented. String literals span lines in 87 places. Lines end with `,`, `=`, `+`.
  Variables are re-assigned in 7 families (`EKA100$` redefines `%T` mid-record), so
  evaluation must be sequential. Numeric literal indices are 1-based (`$P(1)` on a
  1-element array, `%T(15,%A)` on 15 rows) and `(%D-1)*16.757` in `CLA020$` shows that the
  first option is 1. Parameters have up to 40 options, so derived-code characters need
  `a-z`, `A-Z`, `0-9`.
- Viewer behaviour confirmed by the PDFs: option labels are inserted verbatim (`" blando "`
  yields `blando , sin`), whitespace runs are collapsed on display, zero-quantity lines are
  omitted, quantities show 4 decimals, amounts 2, `%CIND` price = sum of previous amounts,
  total = sum of amounts. `AU10100001` price is computed from its own `~D`.
- Scale: 1,626,335 combinations in total (max 34,272 in `EZG010$`, median 69 per
  family; OEB = 47,508).

## 3. Package layout

```
bc3param/
  __init__.py          public API re-exports
  encoding.py          cp1252-with-latin1-fallback decoder
  fiebdc.py            record splitter + Catalog (~C ~D ~T ~K ~P ~V)
  param/
    __init__.py
    preprocess.py      statement extraction per spec procedure
    lexer.py           tokens
    ast.py             expression and statement node types (dataclasses)
    parser.py          recursive-descent parser -> Family (parsed ~P)
    evaluator.py       sequential interpreter for one selection
    codes.py           option letter <-> index, derived code building/parsing
  pricing.py           rounding, percentages, recursive ~D pricing
  model.py             Item / DecompLine / ParameterChoice output dataclasses + to_dict
  generate.py          iteration over families, chapters, ranges; JSON/JSONL writers
  cli.py               argparse entry point `bc3param`
pyproject.toml         name bc3param, python>=3.11, no runtime deps, [project.scripts]
tests/
  conftest.py          fixtures: small hand-written BC3 snippets + path to the real file
  test_encoding.py test_fiebdc.py test_preprocess.py test_lexer.py test_parser.py
  test_evaluator.py test_pricing.py test_generate.py test_cli.py
  test_reference.py    checks against the three ADIF PDFs (skipped if raw file missing)
```

Existing notebooks and `src/utils` are untouched.

## 4. Module contracts

### 4.1 `encoding.decode_bc3(data: bytes) -> str`

Decode as cp1252; bytes undefined in cp1252 (`0x81 0x8D 0x8F 0x90 0x9D`) map to the same
code point (latin-1 behaviour). Also accepts UTF-8 input when the file starts with a BOM or
decodes cleanly as UTF-8 and contains non-ASCII (so the `_utf8.txt` copies keep working).
Line endings normalised to `\n`.

### 4.2 `fiebdc`

`iter_records(text) -> Iterator[Record(kind, fields, line_no)]`. A record starts at a line
beginning with `~X|`. Records are split into fields on `|`; a `~P` record's parametric body
(field 3) keeps its raw multi-line text up to and including the terminating `\|`, which is
stripped. Fields are not otherwise trimmed.

`Catalog.load(path) -> Catalog` holds:

- `concepts: dict[str, Concept]` with `code, unit, summary, price: Decimal|None, dates,
  type`. Codes are stored as written; `code_key()` strips trailing `#`/`##` so that `OEB#`
  and `OEB` resolve to the same concept (spec: references with and without `#` are the
  same concept).
- `decompositions: dict[str, list[DecompRef(child, factor, yield_)]]` from `~D`.
- `texts: dict[str, str]` from `~T`.
- `decimals: Decimals(DR=4, DI=2, DP=2, DC=2, ...)` from `~K` field 1, defaults per spec
  if absent.
- `families: dict[str, str]` raw `~P` bodies keyed by family code (`OEB020$`).
- `parents: dict[str, list[str]]` reverse of chapter `~D` records; `chapter_path(code)`
  walks it up to the root (`R_A_I_Z##`), returning `["O#", "OE#", "OEB#"]` style lists.
- `family(code) -> Family` parses lazily and caches.
- `price_of(code) -> PricedConcept` (see 4.7).

### 4.3 `param.preprocess.statements(body: str) -> list[Statement(text, line_no)]`

Implements the spec's reading procedure with these rules, applied in order:

1. Tabs become spaces.
2. Comments: `#` to end of line is removed unless inside `"..."` or inside a `\...\`
   labelled statement. Label statements (parameters, RESUMEN, TEXTO, ...) are taken
   verbatim between their backslashes; no `#` was observed inside them, but the rule keeps
   them safe.
3. Join continuation lines: a line continues into the next when, after comment removal
   and right-trim, it (a) ends with `,` or an operator (`+ - * / ^ @ & < > = ! (`), or
   (b) has an odd number of `"`, or (c) starts with `\` and does not end with `\`
   (label statements), or (d) starts with `\`, the label is RESUMEN/TEXTO/PLIEGO/... and the
   text has not yet reached a closing `\`. Joined with `\n` when inside a quoted string or
   a `\` text (to preserve line breaks), otherwise with a single space.
4. Blank lines dropped. Each statement keeps the original first line number for error
   messages.

Spaces inside `\` labels are trimmed only for the label name (so `\ RESUMEN \` is
recognised); option labels keep their spaces (viewer behaviour, see 4.6).

### 4.4 `param.lexer` and `param.ast`

Tokens: NUMBER, STRING (with `""` escape inside), NUMVAR (`%X`), TEXTVAR (`$X`), IDENT
(function names, `PI`), LETTER (single lowercase `a-z` used as index/comparison constant),
operators `+ - * / ^ @ & < > <= >= = <> !`, `( ) ,`. `%%` inside an expression is not
expected; inside decomposition codes it is handled by the parser, not the lexer.

Expression AST: `Num`, `Str`, `Const(letter)`, `NumVar(name)`, `TextVar(name)`,
`Index(var, args)`, `Call(fn, args)`, `Unary(op, x)`, `Binary(op, l, r)`.

Statements: `ParamDef(name, options)`, `Assign(kind, name, dims|None, values: list[Expr])`,
`Decomp(code_template, expr, factor_expr|None)`, `Price(expr)`, `AuxPercent(expr,
per_unit: bool)`, `Text(label, template)` for RESUMEN/TEXTO/COMENTARIO and
`TextList(label, items)` for PLIEGO/CLAVES/COMERCIAL. Every node records `line_no`.

### 4.5 `param.parser.parse_family(code, body) -> Family`

Classifies each statement:

- starts with `\` → label statement; label `RESUMEN|R`, `TEXTO|T`, `COMENTARIO|C`,
  `PLIEGO|P`, `CLAVES|K`, `COMERCIAL|F` are reserved (case-sensitive, matched only as the
  first label); anything else is a `ParamDef`. Parameters are bound to `A B C D F G H I J K`
  in order (E is reserved). More than 10 parameters is a parse error.
- starts with `::` → `Price`. Starts with `%:` or `%%:` → `AuxPercent`.
- matches `^[%$][A-Z]\s*(\(dims\))?\s*=` → `Assign`; RHS split on top-level commas into
  expressions; if dims given, the product of dims must equal the number of values (error
  otherwise, with the code/line).
- otherwise, if it contains `:` outside quotes → `Decomp` with `code_template` the text
  before the first `:` (spaces removed) and the expression after it; an optional second
  `:` gives the factor expression.
- otherwise → parse error.

Expression grammar (lowest to highest precedence, all left-associative):

```
or      := and ( '@' and )*
and     := cmp ( '&' cmp )*
cmp     := add ( ('<' | '>' | '<=' | '>=' | '=' | '<>') add )*
add     := mul ( ('+' | '-') mul )*
mul     := pow ( ('*' | '/') pow )*
pow     := unary ( '^' unary )*
unary   := ('!' | '-') unary | atom
atom    := NUMBER | STRING | LETTER | 'PI' | NUMVAR [ '(' args ')' ] | TEXTVAR [ '(' args ')' ]
         | IDENT '(' args ')' | '(' or ')'
```

Parse errors raise `ParseError(family, line_no, message)`; `Catalog.family()` lets it
propagate, `validate` collects them.

### 4.6 `param.evaluator.evaluate(family, selection) -> Evaluation`

`selection` is a tuple of 1-based option numbers, one per parameter. The interpreter keeps
`num: dict[str, float | Matrix]`, `text: dict[str, str | Matrix]` and runs statements in
order:

- Parameter `%A` = option number (1-based). `$A` = option label verbatim.
- `Const(letter)` = position in `a..z` starting at 1. Numeric literal used as an index is
  used as-is (1-based). Indices are rounded to int; out-of-range raises `EvalError` for
  that selection.
- Comparisons return 1.0/0.0. `@`/`&`/`!` operate on truthiness (non-zero, non-empty).
- Arithmetic on two numbers is numeric. `Str * number` yields the string when the number
  is non-zero, else `""`. `Str + Str` concatenates; `Str + number` concatenates `FTOA`
  form. Numeric ops on strings coerce via `ATOF` (returns 0 on failure).
- `Assign` with dims stores a `Matrix(dims, values)` in row-major order, each value
  evaluated at assignment time. Without dims and one value: scalar. Without dims and
  several values: 1-D matrix.
- Undefined `%X` → 0 and `$X` → `""`, each recorded once in `warnings`.
- `%E` assignment: after evaluating, if truthy the evaluation is marked invalid with the
  current `$E` value (default "Combinación no válida"); remaining statements are still run
  so that texts can be produced, but pricing is skipped.
- `Decomp`: substitute `$X` (text) and `%X` (letter of value, `%%` → `%`) in the code
  template, evaluate the expression (times factor if present). Quantity 0 (after rounding
  to DR) drops the line. Lines with the same resulting code are merged by summing
  quantities, keeping first position. Order is preserved otherwise.
- `Price` sets a direct price (overrides decomposition). `AuxPercent` is kept as
  `aux_percent` (per-unit) for pricing.
- `Text` templates: replace `$X(args)` and `%X(args)` first, then `$X`, then `%X` (letter of
  value). Then collapse runs of spaces/tabs to one space, trim each line, drop the trailing
  `\|` if present. Line breaks are preserved.

Result: `Evaluation(valid, error, resumen, texto, comment, lines: list[(code, qty)],
direct_price, aux_percent, warnings)`.

### 4.7 `pricing`

`Decimals` from `~K`. Half-up rounding via `decimal.Decimal.quantize(ROUND_HALF_UP)`.

`price_of(code)` (memoised, cycle-guarded) returns `PricedConcept(code, unit, summary,
type, price, lines)`:

- If the concept has a `~D`: for each child, `qty = round(factor * yield_, DR)`,
  `amount = round(child.price * qty, DI)`; percentage children (code contains `%` or `&`)
  take as price the sum of amounts of previous lines whose code starts with the prefix
  before the `%`/`&` (all previous lines when empty), and `amount = round(base * qty, DI)`;
  `price = round(sum(amounts), DC)`. If it differs from the `~C` price, a warning is kept
  on the `PricedConcept` (not fatal).
- Else the `~C` price (or 0 with a warning when missing).

`price_item(catalog, evaluation)`: same rule applied to the evaluated lines, with
`qty` rounded to DR; `direct_cost` is the sum of non-percentage lines; `price` is the
rounded sum of all lines. A `Price` statement wins over lines when present. `aux_percent`
is applied as an extra percentage line with code `%` if present (none in this file).

### 4.8 `model` and `generate`

`Item` dataclass with `to_dict()` producing exactly:

```json
{"code": "OEB020bbbaa", "family": "OEB020$", "unit": "m",
 "family_summary": "CANALIZACIÓN HORMIGONADA DE TUBO DE PVC 110 mm",
 "chapter_path": ["O#", "OE#", "OEB#"],
 "parameters": [{"var": "A", "name": "Nº TUBOS", "option": 2, "letter": "b", "label": " 4 "}],
 "resumen": "...", "texto": "...",
 "valid": true, "error": null,
 "direct_cost": 86.90, "price": 92.11,
 "decomposition": [
   {"code": "MOC0000101", "unit": "h", "summary": "CAPATAZ NOCTURNO", "type": "1",
    "price": 28.33, "quantity": 0.0558, "amount": 1.58},
   {"code": "%CIND", "unit": "%", "summary": "Costes indirectos", "type": "%",
    "price": 86.90, "quantity": 0.06, "amount": 5.21}],
 "warnings": []}
```

Money and quantities are serialised as JSON numbers (floats from the rounded Decimals).
Invalid items have `valid: false`, `error` text, `price`/`direct_cost` null and an empty
decomposition.

`generate.select(catalog, chapter=None, range_=None, families=None) -> list[str]` resolves
family codes: `chapter` walks `~D` chapter records recursively (`OEB#`, `O#`); `range_`
is `START..END` compared on the 6-char stem; `families` explicit list.
`generate.iter_items(catalog, family_codes, include_invalid=False, decomposition=True)`
yields `Item`s in option order (last parameter varies fastest, like the code letters).
`write_jsonl(items, path)` streams; `write_json(items, path)` writes a JSON array.

### 4.9 `cli`

```
bc3param validate FILE [--family CODE]        parse every ~P, report errors and counts
bc3param inspect  FILE FAMILY                  parameters, options, statement summary
bc3param resolve  FILE CODE                    CODE = derived (OEB020bbbaa) or FAMILY -s b,b,b,a,a
bc3param generate FILE (--chapter OEB# | --range OEB010..OEB300 | --family OEB020$ ...)
                  --out PATH [--format jsonl|json] [--include-invalid] [--no-decomposition]
                  [--limit N]
```

`resolve` prints the item as indented JSON. `generate` prints a progress line per family
to stderr and a final count. Exit code 1 on parse errors in `validate`.

## 5. Error handling

- File level: undecodable input or missing `~V` → `Bc3Error` with a clear message.
- Parse errors carry family code and source line; `validate` lists them all and continues.
- Evaluation errors (bad index, division by zero, unknown function) are per selection:
  the item is emitted with `valid: false` and the error text when `--include-invalid`, and
  counted in the summary otherwise. Missing child concepts are warnings on the item with
  price 0 for that line.
- No `eval`, no regex-based formula rewriting.

## 6. Testing

- Unit tests per module with small inline BC3 snippets.
- Real-file tests (skipped when `data/raw/BPA_2024_v2.txt` is absent):
  - `validate` parses all 2,996 families with zero parse errors.
  - `AU10100001` recomputed from `~D` equals its `~C` price 88.39.
  - `OEB010aaa`: quantities 0.3667, 1.2500, 3.6670, 0.6667, 0.0833, 5, 2, 4, 6, 4, 0.076,
    1.35 and `%CIND` 0.06; RESUMEN ends with `(-/-/D)` (the 2024 file defines
    `$L(3)="D","N","-"`, matching the viewer); TEXTO contains
    `En terreno blando , sin reposición de pavimento.`; price equals the 2024 arithmetic.
  - `OEB020bbbaa`: line set {MOC0000101, MOC0000601, MOC0000501, MQ04000600, MQ05020300,
    MQ04070420, MQ03000005, MQ0103D105, MN10010001, AU10100001, %CIND}; MN10010001
    quantity 4, AU10100001 0.165; RESUMEN `Canalización hormigonada de 4 T, PVC 110 mm,
    bajo vías. (N/>5/R)`.
  - `CLA020$` first selection yields MOE0000100 quantity 55.857 (checks 1-based arithmetic).
  - `EKA100$` evaluates without index errors (sequential redefinition).
  - OEB chapter generation yields 47,508 items (invalid included) and finishes in
    reasonable time (< 2 min).

## 7. Out of scope

Web viewer; `~R`/`~X` technical information; PLIEGO beyond storing text; parametric DLLs;
`~M` measurements; multi-currency `~K` field 3.
