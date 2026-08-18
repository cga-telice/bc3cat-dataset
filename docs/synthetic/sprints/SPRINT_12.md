# Sprint 12 — Phase C Task C1: Spanish prompt library (`prompts/`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 12                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | C1 — see [`../RESEARCH_PROTOCOL.md §5 Phase C`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 11 — `composition.py` + B5 closes; Phase B fully shipped (see [`SPRINT_11.md`](SPRINT_11.md)) |
| **Successor**   | Sprint 13 — Phase C Task C2 (`llm_proposer.py` — LLM client + retry/fallback) — TBD         |

---

## Context

Sprint 11 closed Phase B by landing the
[`src/synthetic/composition.py`](../../src/synthetic/composition.py)
pre-apply validator with **159/159 pytest pass**. All 12 atomic
mutators are live; the per-pair stacking matrix is in place; the
composer is idempotent, state-blind, and ready to consume rule
batches from a future variant proposer. The natural next concern is
**how those rule batches get produced** — Phase C's offline LLM
proposer (Stage A in the proposal's pipeline diagram).

C1 is the **prompt library** the proposer will consume. Per the
protocol's [`§5 Phase C C1`](../RESEARCH_PROTOCOL.md):

> **C1. Prompt template library.** `src/synthetic/prompts/` — one
> Spanish prompt per modification type. Each prompt declares its
> JSON-output contract.

Four representative prompts are drafted in
[`../RESEARCH_PROPOSAL.md §8`](../RESEARCH_PROPOSAL.md) (`synonym_label`,
`paraphrase`, `omission`, `new_param`). Sprint 12 lands those four
verbatim and authors the remaining eight in the same pattern, plus
a thin loader (`load_prompt(modification_type)`) and a contract test
suite that verifies each prompt is loadable, declares a JSON-output
contract, and uses the declared placeholder set.

**No LLM client, no API calls, no retry logic.** C1 is *static
templates only*. The C2 sprint (the next one) will introduce the
client and the structured-output schema; C3 will introduce the
proposer that fills placeholders and parses LLM responses. Sprint
12's deliverable is the **frozen text of the 12 prompts** plus a
trivially-mockable read path for C2 to consume.

Sprint 11's verification baseline: **159 passed**. Sprint 12 adds
the `src/synthetic/prompts/__init__.py` loader, the 12 `*.txt`
prompt files, and the new `tests/synthetic/test_prompts.py` suite
(≥18 cases). Net pytest delta target: **≥+18** new test cases =
**≥177 passed** total. Zero failures, zero skips, zero changes to
surviving tests. No changes to any `layer_*.py`, `mutator.py`,
`composition.py`, or `taxonomy.py`.

---

## Scope

### In scope

- **C1** — `src/synthetic/prompts/` package:
  - `src/synthetic/prompts/__init__.py` (new) — exposes
    `load_prompt(modification_type: ModificationType) -> str`,
    `PROMPT_DIR: Path` (resolves to the directory containing the
    `.txt` files), `PROMPT_FILENAMES: dict[ModificationType, str]`
    (the 12-entry mapping). `load_prompt` reads `PROMPT_DIR /
    PROMPT_FILENAMES[modification_type]` as UTF-8 text and returns
    the raw string verbatim (no placeholder substitution; that is
    C3's responsibility). Unknown modification types raise
    `KeyError`. Missing prompt files raise `FileNotFoundError`.
  - 12 `*.txt` files under `src/synthetic/prompts/`, one per
    `ModificationType`. Filenames are the enum *value* + `.txt`
    (e.g., `synonym_label.txt`, `num_to_text.txt`, …,
    `new_param.txt`). Each file is UTF-8 (no BOM), Spanish, ends in
    `\n`, and declares a strict JSON-output contract in its closing
    block.
  - The four representative prompts from
    [`../RESEARCH_PROPOSAL.md §8`](../RESEARCH_PROPOSAL.md) are
    lifted verbatim into `synonym_label.txt`, `paraphrase.txt`,
    `omission.txt`, `new_param.txt`. The remaining eight are
    authored in the same pattern — see §"Prompt bodies" below for
    the full text of all 12.
- **Tests** — `tests/synthetic/test_prompts.py` (new, ≥18 cases)
  covering: loadability per type (parametrised ×12); UTF-8 decode
  without errors; non-empty body; presence of the `JSON` keyword
  declaring the output contract; presence of the expected
  placeholder set per type (e.g., `synonym_label` declares
  `{concept}`, `{axis_label}`, `{value_list}`); `PROMPT_FILENAMES`
  audit (exactly 12 entries, keys are `ModificationType` members,
  values are `<enum_value>.txt`); `load_prompt` raises `KeyError`
  on a non-enum input; `load_prompt` returns the same string for
  two consecutive calls (file IO is read-only and idempotent).
- **Housekeeping**:
  - Sprint 12 entry in
    [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip ❌ → ✅ for the `prompts/` block in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files
    in This Branch" section — all 13 rows (`prompts/` directory +
    12 `.txt` files); prepend an "After Sprint 12 — …" entry to the
    Sprint History.

### Out of scope (explicit)

- **`src/synthetic/llm_proposer.py`** — the LLM client + retry +
  fallback. Sprint 12 lands prompts; the client is C2's deliverable.
  Even a stub `llm_proposer.py` with a `NotImplementedError` body
  is out of scope — no new file under `src/synthetic/` other than
  the `prompts/` package and its contents.
- **Placeholder substitution / template rendering.** `load_prompt`
  returns the raw template string with `{concept}` / `{axis_label}`
  / etc. unfilled. The C3 variant proposer is responsible for
  formatting (likely `str.format` with a per-type kwargs dict);
  Sprint 12's loader is intentionally dumber than `str.format` to
  keep the C2/C3 design surface free.
- **JSON-schema validation of the prompts' declared output.** The
  prompts declare their JSON contract in natural-language Spanish
  (`"Responde SOLO con un JSON: {…}"`). A formal JSON schema (e.g.,
  `pydantic` models matching each prompt's expected output) is C2's
  problem — Sprint 12 only checks that the word `JSON` appears in
  each prompt's body. The actual schema enforcement at LLM-response
  time lives in C2 (`llm_proposer.py`) or C3 (variant proposer).
- **Spanish-language quality review by a native speaker.** The
  four proposal-§8 prompts are taken verbatim; the eight new
  prompts are authored in the same register. A round of native
  review with the domain reviewer is a Phase F1/F2 pilot concern
  (acceptance-rate measurement informs prompt tuning); it is **not**
  a Sprint 12 gate. Document the deferral in the RESEARCH_LOG entry.
- **`configs/synthetic/variant_budgets.yaml` / `new_param_allowlist.yaml`.**
  The protocol's file-tree listing reserves these paths for Phase F
  and Phase B4 respectively. Sprint 12 does not create them. The
  `new_param` prompt's `{allowlist}` placeholder is left unfilled
  at load time; C3 / Phase B4 is responsible for resolving it.
- **Anything under `data/`, notebooks, or `src/utils/`.** Tests
  read from `src/synthetic/prompts/` (the package directory) only;
  no fixture files, no on-disk caches, no notebook reruns.
- **Changes to existing `src/synthetic/` modules.** No edits to
  `taxonomy.py`, `mutator.py`, `composition.py`, any `layer_*.py`,
  or any existing test file. C1 is purely additive in a new
  subpackage.

---

## Prompt design — common contract

Every prompt follows the same five-block layout:

```
[1] Role line — "Eres un experto en … en español."
[2] Slot block — bullet list of placeholders (concept, axis_label, …)
[3] Instruction body — what to do, what to preserve, what NOT to change
[4] JSON-output contract block — opens with "Responde SOLO con un JSON:"
    followed by a JSON literal showing the expected shape
[5] (Optional) Restriction block — e.g., new_param's {allowlist}
```

Common rules:

- **Language.** Spanish, technical register, second-person plural is
  avoided (use "Vas a …" rather than "Vais a …"). Catalog terminology
  is borrowed from the BC3 source (Spanish railway construction).
- **Temperature.** 0.0 at LLM inference time — pinned by C2, not by
  the prompt body. Sprint 12 does not embed temperature in prompts.
- **Strict JSON.** Every prompt closes with `"Responde SOLO con un
  JSON"` followed by a curly-brace literal. No prose around the
  JSON. The C2 client will use a model with structured-output
  support; the prompt's JSON literal is the schema the client will
  enforce.
- **Placeholder syntax.** Python-style `{name}` (single curly
  braces around the bare identifier). Compatible with `str.format`.
  Inside the JSON-contract block, `"..."` and `[...]` are literal
  placeholders the LLM fills, **not** Python format placeholders.
  This avoids escaping `{` and `}` inside the JSON literal — the
  loader returns the raw string and the proposer (C3) is
  responsible for using `str.format_map` with a non-`KeyError`
  dispatch or for filling only the bare-identifier slots manually.
  (Decision: Sprint 12 leaves placeholder semantics intentionally
  loose; C3 picks the rendering strategy when it has the LLM
  schema in hand.)
- **No catalog data inside prompts.** Prompts are templates, not
  data. Per-concept context (`{concept}`, `{value_list}`, etc.)
  comes from the variant proposer at runtime.
- **Semantic-equivalence pin.** Every L1/L2/L3 prompt includes the
  phrase "preservando exactamente el significado paramétrico"
  (or close paraphrase) — the modification must keep the meaning
  intact. The `new_param` prompt instead asks for "claramente
  distinguible" axes (since its semantics are inherently
  additive, not equivalence-preserving).

### Placeholder set per modification type

The contract test parametrises over this table.

| Type                | Placeholders (Python `{}` form)                                        |
|---------------------|------------------------------------------------------------------------|
| `synonym_label`     | `{concept}`, `{axis_label}`, `{value_list}`                            |
| `num_to_text`       | `{concept}`, `{axis_label}`, `{value_list}`                            |
| `unit_conversion`   | `{concept}`, `{axis_label}`, `{value_list}`                            |
| `unit_expansion`    | `{concept}`, `{axis_label}`, `{value_list}`                            |
| `abbrev_expansion`  | `{concept}`, `{axis_label}`, `{value_list}`                            |
| `code_expansion`    | `{concept}`, `{axis_label}`, `{value_list}`                            |
| `paraphrase`        | `{concept}`, `{var_key}`, `{fragment}`, `{condition}`                  |
| `expansion`         | `{concept}`, `{var_key}`, `{fragment}`, `{condition}`                  |
| `compression`       | `{concept}`, `{var_key}`, `{fragment}`, `{condition}`                  |
| `omission`          | `{concept}`, `{template}`, `{var_to_omit}`, `{axis_label}`             |
| `reorder`           | `{concept}`, `{template}`, `{constituents}`                            |
| `new_param`         | `{concept}`, `{existing_axes_with_labels}`, `{allowlist}`              |

Six L1 prompts share the same three-slot signature, three L2 prompts
share the same four-slot signature. The two L3 prompts diverge
(omission needs `{var_to_omit}` / `{axis_label}` to target a specific
parameter; reorder needs `{constituents}` to name the spans that may
move). PD's `new_param` keeps its proposal-§8.4 slot list.

---

## Prompt bodies

The full text of each prompt is the deterministic output of this
sprint. Implementers paste these verbatim into the matching
`<type>.txt` file. Every file ends with a trailing newline.

### `synonym_label.txt` (verbatim from proposal §8.1)

```
Eres un experto en terminología técnica de construcción ferroviaria en español.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Genera un sinónimo natural en español técnico para cada valor, preservando
exactamente el significado paramétrico (no cambies el referente físico).

Responde SOLO con un JSON con la forma:
{
  "synonyms": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### `num_to_text.txt`

```
Eres un redactor técnico en español. Vas a escribir números en palabras
para valores numéricos de un parámetro de catálogo ferroviario.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Para cada valor numérico, escribe su forma en palabras en español. Mantén
la misma magnitud y unidad (no conviertas: "2" → "dos", no "2" → "two" ni
"2 km" → "dos kilómetros" si la unidad no estaba en el valor original).
Preserva exactamente el significado paramétrico.

Responde SOLO con un JSON con la forma:
{
  "numerals": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### `unit_conversion.txt`

```
Eres un ingeniero de obra civil ferroviaria. Vas a convertir valores de
parámetro a una unidad equivalente del Sistema Internacional.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Para cada valor, expresa la misma magnitud física en una unidad equivalente
(p. ej., "1000 m" → "1 km", "0.5 kg" → "500 g"). El valor convertido debe
ser numéricamente exacto y preservar exactamente el referente físico. No
cambies la magnitud, sólo la representación de unidad.

Responde SOLO con un JSON con la forma:
{
  "conversions": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### `unit_expansion.txt`

```
Eres un redactor técnico en español. Vas a expandir las unidades abreviadas
de un parámetro a su forma completa.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Para cada valor, sustituye la unidad abreviada por su nombre completo en
español (p. ej., "mm" → "milímetros", "kg" → "kilogramos", "m²" → "metros
cuadrados"). Conserva la magnitud numérica exacta y el referente físico.

Responde SOLO con un JSON con la forma:
{
  "expansions": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### `abbrev_expansion.txt`

```
Eres un experto en terminología técnica de construcción ferroviaria en español.
Vas a expandir abreviaturas técnicas a su forma completa.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Para cada valor que contenga una abreviatura técnica, sustitúyela por su
forma completa en español (p. ej., "PVC" → "policloruro de vinilo", "HA"
→ "hormigón armado"). Mantén el resto del valor sin cambios y preserva
exactamente el referente físico.

Responde SOLO con un JSON con la forma:
{
  "expansions": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### `code_expansion.txt`

```
Eres un experto en catalogación de obra civil ferroviaria. Vas a expandir
códigos internos de catálogo a una descripción natural en español.

Concepto: {concept}
Eje de parámetro: {axis_label}
Valores actuales: {value_list}

Para cada valor que sea un código (alfanumérico opaco), sustitúyelo por
una descripción natural en español que preserve su referente exacto. El
texto resultante debe seguir siendo unívoco respecto al valor original.

Responde SOLO con un JSON con la forma:
{
  "expansions": [
    {"original": "...", "new": "..."},
    ...
  ]
}
```

### `paraphrase.txt` (verbatim from proposal §8.2)

```
Eres un redactor técnico en español. Vas a reformular fragmentos de texto
de un catálogo de construcción ferroviaria.

Concepto: {concept}
Variable de texto: {var_key}
Fragmento original: "{fragment}"
Condición asociada: {condition}

Reformula el fragmento manteniendo el significado técnico exacto. No alteres
las cantidades, unidades, ni el referente físico. Devuelve UN único fragmento
alternativo.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "preserves_meaning": true
}
```

### `expansion.txt`

```
Eres un redactor técnico en español. Vas a expandir un fragmento de texto
breve de un catálogo de construcción ferroviaria, añadiendo detalle
explicativo sin cambiar el significado.

Concepto: {concept}
Variable de texto: {var_key}
Fragmento original: "{fragment}"
Condición asociada: {condition}

Reescribe el fragmento añadiendo precisión técnica o un complemento que ya
estuviese implícito en el original. No introduzcas información nueva sobre
cantidades, unidades, ni referente físico — sólo expande lo que ya estaba.
El resultado debe ser estrictamente más largo que el original.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "preserves_meaning": true
}
```

### `compression.txt`

```
Eres un redactor técnico en español. Vas a comprimir un fragmento de texto
de un catálogo de construcción ferroviaria, conservando exactamente el
significado paramétrico.

Concepto: {concept}
Variable de texto: {var_key}
Fragmento original: "{fragment}"
Condición asociada: {condition}

Reescribe el fragmento usando menos palabras. Conserva todos los datos
técnicos (cantidades, unidades, referentes físicos); elimina sólo lo
redundante o lo implícito por contexto. El resultado debe ser
estrictamente más corto que el original.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "preserves_meaning": true
}
```

### `omission.txt` (verbatim from proposal §8.3)

```
Eres un redactor técnico. Vas a omitir una mención de parámetro en una plantilla.

Concepto: {concept}
Plantilla actual: "{template}"
Variable a omitir: {var_to_omit}  (corresponde al parámetro: {axis_label})

Reescribe la plantilla eliminando toda mención al parámetro {axis_label},
pero conservando TODAS las demás variables ($A, $B, …) tal cual aparecen.
El texto resultante debe ser gramatical y coherente.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "omitted_var": "..."
}
```

### `reorder.txt`

```
Eres un redactor técnico en español. Vas a reordenar los constituyentes
de una plantilla de catálogo ferroviario, conservando exactamente el
significado paramétrico.

Concepto: {concept}
Plantilla actual: "{template}"
Constituyentes reordenables: {constituents}

Reescribe la plantilla cambiando el orden de los constituyentes indicados.
Conserva TODAS las variables ($A, $B, …) intactas (no las renombres, no
las omitas). El texto resultante debe ser gramatical, coherente y debe
expresar la misma información que el original.

Responde SOLO con un JSON:
{
  "original": "...",
  "new": "...",
  "preserves_meaning": true
}
```

### `new_param.txt` (verbatim from proposal §8.4)

```
Eres un experto en catalogación técnica de obra civil ferroviaria.

Concepto: {concept}
Ejes existentes: {existing_axes_with_labels}

Propón UN nuevo eje de parámetro coherente con el concepto. El nuevo eje
debe ser claramente distinguible de los existentes (sin solapamiento semántico).
Debe tener entre 2 y 5 valores discretos.

Restricción: el nuevo eje debe estar en la lista de ejes admisibles:
{allowlist}

Responde SOLO con un JSON:
{
  "new_axis_label": "...",
  "values": [
    {"label": "a", "value": "..."},
    ...
  ],
  "var_definition": "$X = \"...\" * (%G=a) + ...",
  "template_patch": "..., con $X, ..."
}
```

---

## Tasks

### Task 1 — `src/synthetic/prompts/__init__.py`

Create [`src/synthetic/prompts/__init__.py`](../../src/synthetic/prompts/__init__.py).
Module surface:

```python
"""Per-type Spanish prompt library for Stage-A LLM variant proposing.

Twelve prompts, one per ``ModificationType``. Each prompt is a UTF-8
text file under this package directory; the loader returns the raw
string for the C3 variant proposer to format with per-concept slots.

The loader is the *only* runtime surface of this package — the prompts
themselves are static data, not code, and remain in plain .txt files
so domain reviewers can edit them without touching Python.
"""

from __future__ import annotations

from pathlib import Path

from ..taxonomy import ModificationType


PROMPT_DIR: Path = Path(__file__).parent


PROMPT_FILENAMES: dict[ModificationType, str] = {
    mtype: f"{mtype.value}.txt" for mtype in ModificationType
}


def load_prompt(modification_type: ModificationType) -> str:
    """Read the prompt file for ``modification_type`` and return its
    UTF-8 contents verbatim. Placeholder substitution is the caller's
    responsibility (likely the C3 variant proposer's `str.format_map`).

    Raises
    ------
    KeyError
        If ``modification_type`` is not a member of ``ModificationType``.
    FileNotFoundError
        If the corresponding prompt file is missing on disk.
    """
    filename = PROMPT_FILENAMES[modification_type]
    return (PROMPT_DIR / filename).read_text(encoding="utf-8")
```

#### Behavioural requirements

1. **`PROMPT_FILENAMES` is computed from `ModificationType`.** No
   hand-maintained list; the dict comprehension keeps the mapping
   in sync with the enum automatically. If a future sprint adds a
   13th type, the dict gains a 13th entry without code changes —
   the missing-file `FileNotFoundError` from `load_prompt` is the
   forcing function to author the corresponding `.txt`.
2. **`load_prompt` accepts only `ModificationType` members.** A
   string `"synonym_label"` raises `KeyError` (dict lookup fails
   because the key is the enum member, not its value). This is the
   intentional contract — C3's caller should already have the typed
   enum in hand. (Looser-coercion alternative considered and
   rejected: `ModificationType(modification_type)` would accept
   either the enum or its value, but at the cost of an extra
   conversion step every call and a less-obvious failure mode for
   typos.)
3. **`PROMPT_DIR` is resolved at module load time** via
   `Path(__file__).parent`. No environment-variable override; no
   `BC3CAT_PROMPT_DIR`. Sprint 12's deliberate simplification: if
   a future C2/C3 sprint needs to swap prompt sets (e.g., A/B
   testing variants), the override surface can be added then.
4. **No caching.** `load_prompt` does fresh disk IO every call. The
   prompts are tiny (each <2 KB); per-call IO cost is dominated by
   the eventual LLM round-trip in C2. Caching would complicate the
   test contract ("does the second call see edits to the file?")
   for no measurable benefit.
5. **No side effects at import.** The module exposes `PROMPT_DIR`,
   `PROMPT_FILENAMES`, and `load_prompt` symbols only. No
   filesystem reads at import time (so the package is import-safe
   even on a partial checkout missing some `.txt` files — the
   error surfaces at `load_prompt` call time, when the caller is
   actually using a prompt).

#### Acceptance

- `from synthetic.prompts import load_prompt, PROMPT_DIR, PROMPT_FILENAMES` succeeds.
- `len(PROMPT_FILENAMES) == 12`; `set(PROMPT_FILENAMES) == set(ModificationType)`.
- For every `mtype in ModificationType`: `load_prompt(mtype)` is a
  non-empty `str` ending in `"\n"`.
- `load_prompt("synonym_label")` raises `KeyError`.
- `load_prompt(ModificationType.SYNONYM_LABEL)` is byte-identical to
  `(PROMPT_DIR / "synonym_label.txt").read_text(encoding="utf-8")`.

---

### Task 2 — 12 prompt files

Create `src/synthetic/prompts/<type>.txt` for each
`ModificationType.value`, with the body specified in §"Prompt bodies"
above. Implementation notes:

1. **Encoding.** UTF-8 *without* BOM. PowerShell `Out-File` defaults
   to UTF-16 LE *with* BOM on Windows PowerShell 5.1 — pass
   `-Encoding utf8` explicitly, or write the files via Python (the
   `Write` tool in the harness writes UTF-8 without BOM by default).
2. **Line endings.** LF, not CRLF. The repo's `.gitattributes`
   already enforces this for text files; double-check by inspecting
   the first file's hex on Windows after creation.
3. **Trailing newline.** Every file ends in exactly one `\n`. The
   contract test pins this.
4. **No edits to the proposal-§8 prompts.** `synonym_label.txt`,
   `paraphrase.txt`, `omission.txt`, `new_param.txt` are lifted
   *verbatim* from [`../RESEARCH_PROPOSAL.md §8`](../RESEARCH_PROPOSAL.md).
   Any future polish to those four prompts must update the proposal
   in the same change (single source of truth: the prompt file, but
   the proposal's example must stay in sync).
5. **No hidden ASCII.** The contract test enforces UTF-8 decode
   success; smart-quote characters and accented vowels are
   expected and valid.

**Acceptance**
- `git status --short` shows exactly 12 new `src/synthetic/prompts/*.txt`
  files plus `src/synthetic/prompts/__init__.py`.
- Each file's byte size is between 200 and 3000 bytes (sanity
  bound — too small means content was truncated; too large means
  context was duplicated).
- `python -c "from pathlib import Path; print(Path('src/synthetic/prompts/synonym_label.txt').read_text(encoding='utf-8'))"` prints the Spanish text exactly as drafted.

---

### Task 3 — `tests/synthetic/test_prompts.py`

Create [`tests/synthetic/test_prompts.py`](../../tests/synthetic/test_prompts.py).
≥18 cases. Skeleton:

```python
import pytest

from synthetic.prompts import PROMPT_DIR, PROMPT_FILENAMES, load_prompt
from synthetic.taxonomy import ModificationType


_EXPECTED_PLACEHOLDERS: dict[ModificationType, set[str]] = {
    ModificationType.SYNONYM_LABEL:    {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.NUM_TO_TEXT:      {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.UNIT_CONVERSION:  {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.UNIT_EXPANSION:   {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.ABBREV_EXPANSION: {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.CODE_EXPANSION:   {"{concept}", "{axis_label}", "{value_list}"},
    ModificationType.PARAPHRASE:       {"{concept}", "{var_key}", "{fragment}", "{condition}"},
    ModificationType.EXPANSION:        {"{concept}", "{var_key}", "{fragment}", "{condition}"},
    ModificationType.COMPRESSION:      {"{concept}", "{var_key}", "{fragment}", "{condition}"},
    ModificationType.OMISSION:         {"{concept}", "{template}", "{var_to_omit}", "{axis_label}"},
    ModificationType.REORDER:          {"{concept}", "{template}", "{constituents}"},
    ModificationType.NEW_PARAM:        {"{concept}", "{existing_axes_with_labels}", "{allowlist}"},
}
```

Required test cases (≥18):

1. **`test_prompt_dir_exists`** — `PROMPT_DIR.is_dir()` is true.
2. **`test_prompt_filenames_size_and_keys`** — exactly 12 entries,
   keys are the full `ModificationType` enum set, values match the
   `<enum_value>.txt` pattern.
3. **`test_every_prompt_file_exists`** parametrised over the 12
   modification types — `(PROMPT_DIR / filename).is_file()` is true.
4. **`test_load_prompt_returns_str_per_type`** parametrised over the
   12 types — `load_prompt(mtype)` returns a non-empty `str`
   ending in `"\n"`.
5. **`test_load_prompt_utf8_decode_per_type`** parametrised over the
   12 types — `(PROMPT_DIR / filename).read_bytes().decode("utf-8")`
   raises no `UnicodeDecodeError`; result is byte-identical to
   `load_prompt(mtype)`.
6. **`test_load_prompt_no_bom_per_type`** parametrised over the 12
   types — the first byte is NOT `0xEF` (the start of the UTF-8 BOM
   `EF BB BF`). Guards against PowerShell's default
   UTF-16-LE-with-BOM encoding silently sneaking in.
7. **`test_load_prompt_declares_json_contract_per_type`** parametrised
   over the 12 types — the loaded text contains the substring
   `"JSON"` (case-insensitive). Pins the "every prompt declares its
   output contract" rule.
8. **`test_load_prompt_placeholders_per_type`** parametrised over
   the 12 types — every placeholder in `_EXPECTED_PLACEHOLDERS[mtype]`
   appears at least once in the loaded text. Strict equality is
   too brittle (a future polish might add an optional slot); subset
   inclusion is the binding contract.
9. **`test_load_prompt_idempotent`** — calling `load_prompt(mtype)`
   twice on the same type returns the same string (pinned for one
   representative type, `SYNONYM_LABEL`).
10. **`test_load_prompt_raises_keyerror_on_string_input`** —
    `load_prompt("synonym_label")` raises `KeyError`.
11. **`test_load_prompt_raises_filenotfound_on_missing_file`** —
    create a temporary `ModificationType`-shaped dispatch (via
    monkeypatching `PROMPT_FILENAMES`) pointing to a non-existent
    file; assert `FileNotFoundError`. (Use `monkeypatch.setitem`
    on `PROMPT_FILENAMES` to point a real enum member at
    `"NOTAFILE.txt"`.)
12. **`test_prompt_starts_with_role_line`** parametrised over the 12
    types — first non-empty line of the loaded text starts with
    `"Eres "` (the Spanish role-introducer used by all 12 prompts).
13. **`test_prompt_uses_spanish_register`** parametrised over the 12
    types — body contains at least one Spanish word from a small
    canonical set: `{"Eres", "Concepto", "Responde", "JSON"}`. (A
    smoke check that the prompt isn't accidentally English; a real
    language-detector would be overkill.)
14. **`test_prompt_contains_responder_solo_phrase_per_type`**
    parametrised over the 12 types — every prompt contains the
    phrase `"Responde SOLO con un JSON"` (the structured-output
    cue C2 will rely on).
15. **`test_prompt_no_unrendered_python_braces_outside_slots`** —
    audit: every `{` or `}` character in the file body is either
    part of a declared placeholder (member of the prompt's
    `_EXPECTED_PLACEHOLDERS` set) or part of the JSON-literal
    contract block (heuristic: the `{` appears after a line
    starting with `Responde SOLO con un JSON:`). The audit's
    purpose: catch a stray `{example}` placeholder left in the
    prompt body that would later raise `KeyError` from `str.format`
    in C3. Skip the audit for `new_param.txt` (its JSON literal
    contains nested `{` / `}` that the heuristic can't cleanly
    partition; document the exemption in a comment).
16. **`test_prompt_l1_six_types_share_placeholder_set`** — audit
    that the six L1 prompts all have placeholder set
    `{"{concept}", "{axis_label}", "{value_list}"}`. Pins the
    L1-uniformity decision (one slot signature, six prompts).
17. **`test_prompt_l2_three_types_share_placeholder_set`** — audit
    that the three L2 prompts all have placeholder set
    `{"{concept}", "{var_key}", "{fragment}", "{condition}"}`. Pins
    the L2-uniformity decision.
18. **`test_prompt_byte_sizes_within_bounds`** parametrised over
    the 12 types — `(PROMPT_DIR / filename).stat().st_size` is
    between 200 and 3000 bytes. Sanity bound against truncation
    and against accidental context duplication.

**Acceptance**
- The new file contributes ≥18 test cases (parametrisations count
  as one test function each; the 12-way parametrisations expand to
  ~70 individual cases).
- `pytest tests/synthetic/test_prompts.py -q` exits 0 with no
  skips.

---

### Task 4 — Housekeeping

After Tasks 1–3 pass:

1. Append a Sprint 12 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: files
   created (13 new files under `src/synthetic/prompts/` plus the
   test file), the test-count delta (159 → ≥177), the prompt
   library's surface (`load_prompt` + `PROMPT_DIR` +
   `PROMPT_FILENAMES`), the four-verbatim-from-§8 + eight-new
   split, the placeholder-set policy (L1 uniform, L2 uniform, L3
   per-type, PD per-type), the JSON-contract pin, the
   no-substitution-in-loader decision (C3's responsibility), the
   deferred-Spanish-native-review note (Phase F1/F2), and a
   one-line next-step recommendation (Sprint 13 — Phase C Task C2,
   `llm_proposer.py` — LLM client).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for the `prompts/` block in the "New Files in
     This Branch" listing. All 13 rows update: the directory line
     itself plus the 12 `.txt` files. Annotation pattern:
     "✅ Sprint 12 — Task C1 — Spanish prompt for `<type>`
     (verbatim from proposal §8.<n>)" for the four lifted
     prompts; "✅ Sprint 12 — Task C1 — Spanish prompt for `<type>`
     (authored in proposal-§8 pattern)" for the eight new prompts.
     Add a new `__init__.py` row immediately under the `prompts/`
     directory line with annotation "✅ Sprint 12 — Task C1 —
     `load_prompt` + `PROMPT_DIR` + `PROMPT_FILENAMES` loader
     surface".
   - Prepend a new "After Sprint 12 — …" entry to the Sprint
     History section.
3. Do **not** modify
   [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md). The
   proposal's §8 representative prompts are the source of truth
   for the four verbatim files; any future polish must update both
   the proposal and the prompt file in the same change.
4. Do **not** modify
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §5 Phase C
   C1. The protocol entry already names `src/synthetic/prompts/`
   as the deliverable and states "one Spanish prompt per
   modification type. Each prompt declares its JSON-output
   contract" — Sprint 12 ships exactly what the protocol asked
   for, no clarification needed.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥177 passed** (159 from Sprint 11 + 18 minimum new
prompt cases = 177 minimum). Zero failures, zero skips. If Task 3
lands all 18 listed cases with parametrisation expansion (most
parametrise ×12), the total individual count is ~159 + ~70 =
**≥229** — well above the binding gate.

> ⚠ **Plan-self-consistency cross-check** (continuing the
> Sprint 07–11 convention): the binding gate is "≥18 new prompt
> cases, all green, no skips, no regressions in the 159-pass
> baseline". The headline pytest number depends on how many
> parametrisations the implementer keeps. Update the RESEARCH_LOG
> entry with the actual count.

Smoke checks (PowerShell-friendly one-liners):

```powershell
python -c "from synthetic.prompts import load_prompt, PROMPT_FILENAMES; from synthetic.taxonomy import ModificationType; print('imports ok'); print('filenames count:', len(PROMPT_FILENAMES)); assert set(PROMPT_FILENAMES) == set(ModificationType); print('keys match enum')"

python -c "from synthetic.prompts import load_prompt; from synthetic.taxonomy import ModificationType; text = load_prompt(ModificationType.SYNONYM_LABEL); assert text.startswith('Eres '); assert 'JSON' in text; assert text.endswith('\n'); print('synonym_label prompt ok -', len(text), 'chars')"
```

End-to-end smoke (write to `_smoke_prompts.py` then run, then delete):

```python
from synthetic.prompts import load_prompt
from synthetic.taxonomy import ModificationType

required_placeholders = {
    ModificationType.PARAPHRASE: {"{concept}", "{var_key}", "{fragment}", "{condition}"},
    ModificationType.NEW_PARAM:  {"{concept}", "{existing_axes_with_labels}", "{allowlist}"},
}

for mtype in ModificationType:
    text = load_prompt(mtype)
    assert text.startswith("Eres "), mtype
    assert "Responde SOLO con un JSON" in text, mtype
    assert text.endswith("\n"), mtype

for mtype, slots in required_placeholders.items():
    text = load_prompt(mtype)
    missing = slots - {tok for tok in slots if tok in text}
    assert not missing, (mtype, missing)

print(f"prompts smoke ok - all {len(list(ModificationType))} prompts load and validate")
```

End-of-sprint expected `git status --short` (sprint-scoped subset only):

```
new file:   src/synthetic/prompts/__init__.py
new file:   src/synthetic/prompts/synonym_label.txt
new file:   src/synthetic/prompts/num_to_text.txt
new file:   src/synthetic/prompts/unit_conversion.txt
new file:   src/synthetic/prompts/unit_expansion.txt
new file:   src/synthetic/prompts/abbrev_expansion.txt
new file:   src/synthetic/prompts/code_expansion.txt
new file:   src/synthetic/prompts/paraphrase.txt
new file:   src/synthetic/prompts/expansion.txt
new file:   src/synthetic/prompts/compression.txt
new file:   src/synthetic/prompts/omission.txt
new file:   src/synthetic/prompts/reorder.txt
new file:   src/synthetic/prompts/new_param.txt
new file:   tests/synthetic/test_prompts.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_12.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`,
nothing under `configs/`. **No changes to any `layer_*.py`, to
`mutator.py`, to `composition.py`, or to `taxonomy.py`** — C1 is
additive in a new `src/synthetic/prompts/` subpackage.

---

## Design notes worth committing to memory

- **Static text first, code last.** The 12 prompts are *data*, not
  code — they will be edited by domain reviewers in Phase F1/F2
  without touching Python. Keeping them as plain `.txt` files
  (versus, say, multi-line string constants in a Python module)
  makes diff-review readable and avoids the temptation to embed
  rendering logic next to the template. The `__init__.py` exposes
  only a loader; the rendering strategy is the C3 proposer's
  decision.
- **Loader returns the raw template.** `load_prompt` does **not**
  call `str.format`. Reason: the JSON-contract block contains
  literal `{` and `}` characters that aren't Python placeholders
  but JSON-literal delimiters. A formatter would either (a)
  require escaping every brace in the JSON literal (ugly and
  error-prone for domain reviewers), or (b) require a careful
  policy on which braces are slots and which aren't. Deferring
  the rendering decision to C3 keeps Sprint 12's surface narrow
  — the loader is dumb enough that there's nothing to test beyond
  file IO.
- **Placeholder syntax is `{name}`, but slot semantics are still
  C3's call.** The bare-identifier placeholders inside the prompt
  body (`{concept}`, `{axis_label}`, etc.) follow Python's
  `str.format` convention. C3 may choose `str.format_map`
  (raises on missing keys), a custom `string.Template`-style
  substituter, or a more permissive regex-based replacer that
  ignores braces inside the JSON contract block. Sprint 12 does
  not commit to a strategy; it only commits to the syntax.
- **Four prompts verbatim from proposal §8, eight new in the same
  pattern.** Sprint 12 makes the prompt library *complete*; the
  protocol's representative-only framing in §8 ("The remaining
  prompts … follow the same JSON-contract pattern") is operationalised
  by this sprint. The verbatim-from-proposal pin means the
  proposal's §8 examples are the single source of truth for those
  four prompts; any future polish to those prompts must update the
  proposal in the same change.
- **L1 prompts share the same three slots; L2 prompts share the
  same four slots.** L1's six modification types all operate on
  `parameters[axis]["values"]` arrays; they receive the same per-axis
  context. L2's three types all operate on a single
  `(var, condition, fragment)` triple. L3's two types diverge
  (omission needs to know *which* `$var` to drop;
  reorder needs to know which constituents may move), and PD's
  single type has its own four-slot signature (concept + existing
  axes + allowlist). The uniformity per layer is a feature: it
  makes the C3 variant proposer's slot-population logic uniform
  per layer.
- **JSON literal in the contract block uses `"..."` and `[...]`
  as fill targets.** The LLM sees the literal `"..."` and is
  expected to replace it with content. This is more readable than
  formal JSON-schema notation and matches the proposal's §8
  pattern. The C2 client (next sprint) will pair the prompt with
  a `pydantic` or `jsonschema` model that enforces the actual
  shape — the prompt's job is to *cue* the model, not to *enforce*
  the schema.
- **`new_param` is the only PD prompt; its slot list includes
  `{allowlist}`.** The protocol's Phase B4 mentions a controlled
  list (`configs/synthetic/new_param_allowlist.yaml`) to gate
  axis introduction. Sprint 12 ships the prompt with the
  `{allowlist}` placeholder unfilled; C3's `new_param` codepath
  is responsible for loading the allowlist YAML (when it lands)
  and formatting the prompt accordingly. Until then, the slot
  stays empty and the LLM is asked to use its best judgement
  about axis distinctness — a temporary state that prompt-tuning
  in Phase F will revisit.
- **No native-Spanish review gate.** Sprint 12's quality gate is
  *structural* (placeholders present, JSON contract declared,
  Spanish register markers present), not *linguistic*. A native
  domain reviewer (the same person who runs the E4 review
  harness) will polish prompts during the F1 pilot retrospective
  when real acceptance-rate numbers are available. Pre-polish
  review would be hand-wavy without the LLM-output data to ground
  it.
- **No prompt versioning, no template inheritance.** The 12
  prompts are independent text files. Cross-prompt sharing (e.g.,
  a common "preserve significado paramétrico" header) is
  *intentionally* not factored out — Phase F may discover that
  some types need a stronger preservation cue than others, and
  premature DRY-ing would lock in a uniform header that's not
  optimal per type. If Phase F or later research uncovers a
  shared structure worth lifting, a Phase E or Phase F sprint can
  introduce template composition then.
- **Tests parametrise heavily.** Twelve types × multiple
  properties means most test functions parametrise over
  `ModificationType` and run 12 times. The headline pytest count
  jumps by ~70 cases (8 parametrised-×12 functions + ~6 specific
  cases). The binding gate is "≥18 listed test functions"; the
  expanded count is incidental.
- **No `llm_proposer.py` stub in this sprint.** Sprint 12 does
  not create a placeholder C2 file. Reason: a stub would either
  (a) raise `NotImplementedError` from a function call (forcing
  C2 to delete-and-rewrite rather than fill-in) or (b) be empty,
  which adds a file to the file tree that conveys nothing. The
  cleaner sprint boundary is "Sprint 12 lands prompts; Sprint 13
  creates `llm_proposer.py` from scratch".

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch
  context, file map (the `prompts/` block flips ❌ → ✅ in this
  sprint).
- [`../RESEARCH_PROPOSAL.md §8`](../RESEARCH_PROPOSAL.md) — the
  source of truth for the four verbatim prompts (`synonym_label`,
  `paraphrase`, `omission`, `new_param`). §3 (Stage-A pipeline
  framing) and §6.1 (`modifications` array schema the prompt's
  JSON output ultimately populates).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §5 Phase
  C C1 (task definition, unchanged by this sprint), §5 Phase B B4
  (the `new_param_allowlist.yaml` referenced by the `new_param`
  prompt's `{allowlist}` placeholder), §8 LLM Prompt Templates
  (the four representative prompts duplicated from the proposal).
- [`SPRINT_11.md`](SPRINT_11.md) — the immediate predecessor;
  closed Phase B with `composition.py`. Sprint 12 begins Phase C.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py)
  — `ModificationType` (the 12 enum members the prompt library
  parametrises over).

---

## Non-goals reminder

If you find yourself opening `src/synthetic/llm_proposer.py`,
creating any new file under `src/synthetic/` other than the
`prompts/` package, opening any notebook, opening anything under
`data/` or `src/utils/`, or writing `configs/synthetic/*.yaml` —
**stop**. That's outside Sprint 12. Either the work belongs to a
future sprint (C2+, F1+) or it should be raised as a clarifying
question in `RESEARCH_LOG.md` before being addressed.

If you find yourself running `str.format` inside `load_prompt` or
adding placeholder-substitution logic to the loader — **stop**.
The loader returns the raw template; rendering is C3's call. The
"loader is dumb" contract is pinned by the test suite.

If you find yourself editing the four proposal-§8 prompts to
"improve" them — **stop**. Those four are verbatim from the
proposal. Polish belongs to a coordinated Phase F1/F2 prompt-tuning
sprint that updates the proposal in the same change.

If you find yourself adding cross-prompt template inheritance,
shared header constants, or Jinja-style composition — **stop**.
The 12 prompts are independent. DRY-ing prompts is a Phase F
concern once acceptance-rate data exists.

If you find yourself running the prompt through an LLM as part of
the sprint's verification — **stop**. Sprint 12 is text-static.
LLM round-trips begin in Sprint 13 (C2). The verification gate is
structural (placeholders, JSON-contract markers, UTF-8 decode),
not behavioural.

If you find yourself adding a `BC3CAT_PROMPT_DIR` environment
variable or other override surface to `PROMPT_DIR` — **stop**.
Sprint 12 pins `PROMPT_DIR = Path(__file__).parent`. Override
surface (for A/B testing prompt variants, for sourcing prompts
from a database, etc.) is a deferred concern; the C2 sprint will
decide whether it's needed once the LLM client surface is
visible.
