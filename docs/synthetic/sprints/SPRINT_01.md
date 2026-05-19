# Sprint 01 — Taxonomy module + injection harness skeleton

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 01                                                                               |
| **Date**       | 2026-05-19 (drafted)                                                             |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | A2 (taxonomy) + A5 (injection harness) — see [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md) |
| **Predecessor** | Sprint 00 — docs scaffolding (see [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md))   |
| **Successor**  | Sprint 02 — A4 path refactor (TBD)                                               |

---

## Context

Sprint 00 produced the four planning documents under `docs/synthetic/` and zero source
code. The branch is now ready for its first additive code drop. This sprint introduces
the `src/synthetic/` Python package with two modules — `taxonomy.py` (the 12-type
modification enum + `Modification` dataclass) and `mutator.py` (the four `apply_*` entry
points with a dispatcher to 12 stub mutator functions). Everything below is **purely
additive** to the repo: no existing notebook, utility, or data file is touched. The
existing s01→s07 pipeline on `main` continues to run unchanged.

The sprint is intentionally narrow. Its job is to lock down the data contract
(`Modification` schema) and the public API surface (`apply_l1/l2/l3/apply_new_param`)
that every subsequent Phase B task will plug into. Stub bodies raise
`NotImplementedError`. Real mutator logic arrives in Phase B (B1–B4), and the path
refactor that unblocks pipeline reruns from an alternate data root is deferred to its
own sprint (A4).

---

## Scope

### In scope
- **A2** — `src/synthetic/taxonomy.py` (enums + `Modification` dataclass + `TYPE_TO_LAYER` map).
- **A5** — `src/synthetic/mutator.py` (4 public `apply_*` functions + internal dispatcher
  registering all 12 type stubs).
- `src/synthetic/__init__.py` package scaffold.
- Unit tests under `tests/synthetic/`.
- Housekeeping: append Sprint 01 entry to `RESEARCH_LOG.md` and flip ❌ → ✅ for the
  three new files in `CLAUDE_SYNTHETIC.md`.

### Out of scope (explicit)
- **A4** — path refactor of `s01_parse_fiebdc.ipynb` / `src/utils/config.py`. **Do not
  edit any notebook in this sprint.**
- **A3** — LLM proposer model spike. No LLM client, no API calls, no model selection.
- **Phase B bodies** — the 12 stubs all raise `NotImplementedError`. Do not implement
  real mutator logic, even for the "easy" ones (`synonym_label`, `omission`).
- `src/synthetic/composition.py`, `layer_l1.py`, `layer_l2.py`, `layer_l3.py`,
  `layer_pd.py`, `prompts/`, `llm_proposer.py`, `metadata.py`, `review.py`,
  `run_synthetic.py`, `loaders.py`.
- Anything under `configs/synthetic/` or `data/synthetic/`.
- No JSON-schema validation library (`jsonschema`, `pydantic`). Plain dataclass +
  hand-written `from_dict` is sufficient; richer validation lives in E2.
- No I/O. Neither module reads nor writes files.

---

## Tasks

### Task 1 — Package scaffold

Create `src/synthetic/__init__.py`. Empty or version stub (`__version__ = "0.1.0"`).

**Acceptance**
- `from synthetic import taxonomy, mutator` succeeds with `src/` on `PYTHONPATH`.

---

### Task 2 — Taxonomy module

File: `src/synthetic/taxonomy.py`.

Define:

1. **`Layer`** — `str, Enum` with 4 members:
   - `PARAM_VALUE = "param_value"`
   - `TEXT_VARIABLE = "text_variable"`
   - `TEMPLATE = "template"`
   - `PARAM_DEFINITION = "param_definition"`

2. **`ModificationType`** — `str, Enum` with all 12 codes from
   [`../RESEARCH_PROPOSAL.md §2.2`](../RESEARCH_PROPOSAL.md):
   ```
   synonym_label, num_to_text, unit_conversion, unit_expansion,
   abbrev_expansion, code_expansion,
   paraphrase, expansion, compression,
   omission, reorder,
   new_param
   ```

3. **`Modification`** — `@dataclass(frozen=True)` matching the schema in
   [`../RESEARCH_PROPOSAL.md §2.3`](../RESEARCH_PROPOSAL.md):
   - Required: `type: ModificationType`, `layer: Layer`.
   - Optional (`Optional[str] = None`): `param`, `var`, `condition`, `field`, `value`,
     `original`, `new`.
   - Bookkeeping (`Optional[str] = None`): `status` (e.g. `"applied"`, `"skipped"`),
     `reason` (free-text explanation when `status == "skipped"`, per the protocol's
     "Unstackable-combo handling: skip + log" decision in
     [`../RESEARCH_PROTOCOL.md §4`](../RESEARCH_PROTOCOL.md)).
   - Provide a thin `@classmethod from_dict(cls, d: dict) -> "Modification"` that
     accepts the JSON-friendly dict (string `type`/`layer` values) and converts them to
     enum members.
   - The default `dataclasses.asdict()` serialiser produces dicts where `type` and
     `layer` are enum members. The sprint includes a small `to_dict()` helper that
     coerces them to their `.value` strings so `json.dumps` round-trips cleanly.

4. **`TYPE_TO_LAYER`** — `dict[ModificationType, Layer]` covering all 12 types per the
   proposal §2.2 table:
   - `synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`,
     `abbrev_expansion`, `code_expansion` → `PARAM_VALUE`
   - `paraphrase`, `expansion`, `compression` → `TEXT_VARIABLE`
   - `omission`, `reorder` → `TEMPLATE`
   - `new_param` → `PARAM_DEFINITION`

**Acceptance**
- `len(list(ModificationType)) == 12`.
- `ModificationType("synonym_label") is ModificationType.SYNONYM_LABEL` (value
  round-trip works).
- `Modification` `to_dict` / `from_dict` round-trip preserves all fields when piped
  through `json.dumps` → `json.loads`.
- `set(TYPE_TO_LAYER) == set(ModificationType)` and
  `set(TYPE_TO_LAYER.values()) == set(Layer)`.

---

### Task 3 — Injection harness

File: `src/synthetic/mutator.py`.

Public API (signatures from [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)
"Stage-Hook Integration Note"):

```python
from typing import Callable

def apply_l1(
    stage2_json: dict,
    concept_key: str,
    rules: list[dict],
) -> tuple[dict, list[Modification]]: ...

def apply_l2(
    stage3_json: dict,
    concept_key: str,
    rules: list[dict],
) -> tuple[dict, list[Modification]]: ...

def apply_l3(
    stage4_json: dict,
    concept_key: str,
    rules: list[dict],
) -> tuple[dict, list[Modification]]: ...

def apply_new_param(
    stage2_json: dict,
    concept_key: str,
    rule: dict,
) -> tuple[dict, list[Modification]]: ...
```

Behavioural requirements:

- **Purity.** Each function `copy.deepcopy`s its input stage JSON before any mutation.
  The caller's dict must remain byte-identical to its pre-call state, even when the
  call raises `NotImplementedError`.
- **Dispatcher.** Internal module-level dict
  `_DISPATCH: dict[ModificationType, Callable[..., tuple[dict, list[Modification]]]]`
  registering exactly the 12 stubs:
  - `_stub_synonym_label`, `_stub_num_to_text`, `_stub_unit_conversion`,
    `_stub_unit_expansion`, `_stub_abbrev_expansion`, `_stub_code_expansion`,
    `_stub_paraphrase`, `_stub_expansion`, `_stub_compression`,
    `_stub_omission`, `_stub_reorder`, `_stub_new_param`.
- **Stub bodies.** Each stub raises:
  ```python
  raise NotImplementedError(
      f"Phase B: {self_type.value} mutator not yet implemented"
  )
  ```
  with the type code present in the message string verbatim.
- **Layer-to-stub gate.** Each `apply_*` only accepts rules whose `type` resolves
  (via `TYPE_TO_LAYER`) to its own layer. A rule whose layer mismatches is treated as
  a programmer error: raise `ValueError` (do not silently skip).
- **Unknown type code.** If `rule["type"]` is a string not in `ModificationType`, raise
  `ValueError(f"unknown modification type: {rule['type']!r}")`.
- **Stubs live in `mutator.py` for now.** Phase B will physically relocate them to
  `layer_l1.py` / `_l2.py` / `_l3.py` / `_pd.py` and re-register through the same
  dispatcher. The dispatcher's surface is the stable boundary; the stub location is
  not.

**Acceptance**
- `inspect.signature(apply_l1).parameters` lists exactly
  `["stage2_json", "concept_key", "rules"]` (and analogously for `apply_l2/l3`;
  `apply_new_param` lists `["stage2_json", "concept_key", "rule"]`).
- For each of the 12 type codes, calling the matching `apply_*` with a single rule
  carrying that `type` raises `NotImplementedError` whose message contains the type
  code string. Test parameterised over all 12.
- Wrong-layer rule (e.g. passing a `paraphrase` rule into `apply_l1`) raises
  `ValueError`.
- Unknown type code raises `ValueError`.
- `_DISPATCH` has exactly 12 entries; `set(_DISPATCH) == set(ModificationType)`.
- Deep-copy purity: snapshot `json.dumps(stage_json, sort_keys=True)`, call the harness
  inside a `pytest.raises(NotImplementedError)` block, then re-snapshot — the strings
  must be identical.

---

### Task 4 — Tests

Layout:
```
tests/
  __init__.py                  (optional)
  synthetic/
    __init__.py                (optional)
    conftest.py                 # prepends repo `src/` to sys.path
    test_taxonomy.py
    test_mutator.py
```

`conftest.py` minimal shape:
```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]   # repo root
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

`test_taxonomy.py` covers all four acceptance bullets from Task 2.

`test_mutator.py` covers all six acceptance bullets from Task 3, including the
parameterised 12-type stub check and the deep-copy purity assertion.

**Acceptance**
- `pytest tests/synthetic -q` from the repo root exits 0.
- No external dependencies introduced beyond `pytest` (already implied by the test
  framework choice).

---

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 01 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (newest-first).
   Cover: what was built, key acceptance numbers, any deviations from this sprint file,
   next-step recommendation.
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip ❌ → ✅ for `src/synthetic/__init__.py`, `src/synthetic/taxonomy.py`,
     `src/synthetic/mutator.py` in the "New Files in This Branch" block.
   - Prepend a new "After Sprint 01 — …" entry to the Sprint History section.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Their content stands; the
   protocol's task backlog A2/A5 simply become "done" from the next sprint's
   perspective.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```bash
pytest tests/synthetic -q
```

Smoke checks (PowerShell-friendly one-liners):

```bash
python -c "from synthetic.taxonomy import ModificationType, Layer, TYPE_TO_LAYER; assert len(list(ModificationType)) == 12 and set(TYPE_TO_LAYER) == set(ModificationType) and set(TYPE_TO_LAYER.values()) == set(Layer)"

python -c "import inspect; from synthetic.mutator import apply_l1, apply_l2, apply_l3, apply_new_param; assert list(inspect.signature(apply_l1).parameters) == ['stage2_json','concept_key','rules']; assert list(inspect.signature(apply_l2).parameters) == ['stage3_json','concept_key','rules']; assert list(inspect.signature(apply_l3).parameters) == ['stage4_json','concept_key','rules']; assert list(inspect.signature(apply_new_param).parameters) == ['stage2_json','concept_key','rule']"

python -c "from synthetic.mutator import _DISPATCH; from synthetic.taxonomy import ModificationType; assert len(_DISPATCH) == 12 and set(_DISPATCH) == set(ModificationType)"
```

Set `PYTHONPATH` first if needed:

```powershell
$env:PYTHONPATH = "src"
```

End-of-sprint expected `git status`:
```
new file:   src/synthetic/__init__.py
new file:   src/synthetic/taxonomy.py
new file:   src/synthetic/mutator.py
new file:   tests/synthetic/__init__.py            (if created)
new file:   tests/synthetic/conftest.py
new file:   tests/synthetic/test_taxonomy.py
new file:   tests/synthetic/test_mutator.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_01.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks under `src/`, nothing under `data/` or
`configs/` should appear.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file map,
  stage-hook integration note (signature source-of-truth).
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.2 (12-type taxonomy table),
  §2.3 (`Modification` schema).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.3 (three-layer mutation
  interface), §4 (design decisions, incl. "Unstackable-combo handling: skip + log"),
  §5 Phase A (A2, A5 task definitions).
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 00 retro.

---

## Non-goals reminder

If you find yourself opening `src/utils/config.py`, any `.ipynb` file, anything under
`configs/`, or anything under `data/`, **stop**. That's outside Sprint 01. Either the
work belongs to a future sprint (A4, A3, Phase B+) or it should be raised as a
clarifying question in `RESEARCH_LOG.md` before being addressed.
