# Sprint 02 — Path refactor: config core + s01 migration

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 02                                                                               |
| **Date**       | 2026-05-19 (drafted)                                                             |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | A4 part 1 (config core + s01) — see [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md) |
| **Predecessor** | [`SPRINT_01.md`](SPRINT_01.md) — taxonomy module + injection harness skeleton    |
| **Successor**  | Sprint 03 — A4 part 2 (s03–s07 path migration), TBD                              |

---

## Context

Sprint 01 landed [`src/synthetic/{__init__.py, taxonomy.py, mutator.py}`](../../../src/synthetic) and a green
30-test suite under [`tests/synthetic/`](../../../tests/synthetic). Phase-B mutator bodies (B1–B4) will eventually need to
materialise mutated stage JSONs under `data/synthetic/intermediate/{concept}/` and the
final synthetic items under `data/synthetic/processed/`. None of that is reachable
today because the existing pipeline hardcodes `/work/data/...` at ~15 sites across nine
notebooks plus [`src/utils/config.py`](../../../src/utils/config.py).

This sprint is **A4 part 1** — the first of two passes at the path-refactor task.
Its job is twofold:

1. Lock down [`src/utils/config.py`](../../../src/utils/config.py) as the single-source-of-truth paths module,
   exposing both the existing-pipeline data tree (`DATA_ROOT` and friends) and the new
   `SYNTHETIC_DATA_ROOT` sub-tree required by Phase D's orchestrator.
2. Migrate `s01_parse_fiebdc.ipynb` — the notebook explicitly named in
   [`SPRINT_01.md`](SPRINT_01.md)'s next-step recommendation — to use the new module, so the
   migration pattern is exercised end-to-end on one notebook before fanning out.

The remaining notebooks (s02, s03–s07, s08, `Generate_OEB_dataset`) are deferred to
Sprint 03 (and possibly Sprint 04). Their changes are mechanical once Sprint 02 lands;
keeping this sprint narrow makes the diff reviewable and keeps blast radius small if
the config shape needs another iteration.

---

## Scope

### In scope

- **Config module** — extend [`src/utils/config.py`](../../../src/utils/config.py) with
  `REPO_ROOT`, `DATA_ROOT`, `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR`,
  `LLAMAINDEX_DIR`, `SYNTHETIC_DATA_ROOT`, `SYNTHETIC_INTERMEDIATE_DIR`,
  `SYNTHETIC_PROCESSED_DIR`, `SYNTHETIC_VARIANTS_DIR`, plus the helpers
  `chapter_path(chapter, *, root=INTERMEDIATE_DIR)` and
  `stage_path(chapter, stage_n, *, root=INTERMEDIATE_DIR)`.
- **Env-var overrides** — `BC3CAT_DATA_ROOT` overrides `DATA_ROOT`;
  `BC3CAT_SYNTHETIC_DATA_ROOT` overrides `SYNTHETIC_DATA_ROOT`. Defaults derive from
  `REPO_ROOT`. Loaded at import time.
- **Backwards-compat** — keep the existing `Config` class. Re-route its `DATA_DIR` /
  `TEXTO_PATH` / `RESUMEN_PATH` through the new `LLAMAINDEX_DIR` so the hardcoded
  `/work/data/llamaindex` literal disappears without changing the public API. Any
  current caller that imports `Config` keeps working.
- **s01 notebook migration** — replace both `os.chdir('/work/...')` calls in
  [`src/s01_parse_fiebdc.ipynb`](../../../src/s01_parse_fiebdc.ipynb) (lines ~48 and ~580 in the JSON source) with
  config-driven equivalents. No other logic change.
- **Tests** — `tests/utils/test_config.py` exercising the four config invariants
  (default resolution, env-var override, helper outputs, `Config` back-compat).
- **Housekeeping** — append Sprint 02 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md), flip the new files in
  [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files" block, and prepend an "After Sprint 02 — …"
  entry to its Sprint History.

### Out of scope (explicit)

- **s02, s03, s04, s05, s06, s07, s08, `Generate_OEB_dataset` notebooks** — all hardcode
  `/work/...`. Migration deferred to Sprint 03 (s03–s07 are the synthetic-engine
  critical path) and possibly Sprint 04 (s08 + `Generate_OEB_dataset` only ship the
  final main-pipeline artifacts, not on the synthetic critical path).
- **`.ipynb_checkpoints/` files** — Jupyter auto-save backups. **Do not touch.** They
  regenerate when the source notebook is re-saved. Same applies to any
  `*-checkpoint.py` files under `src/utils/.ipynb_checkpoints/`.
- **Phase B mutator bodies** (B1–B4) — still stubs from Sprint 01. Not this sprint.
- **Creating the actual `data/synthetic/*` directories on disk.** Sprint 02 only names
  them in code. They get created on first write by the synthetic orchestrator (D2).
- **Re-running the existing pipeline end-to-end against the refactored s01.** Treat
  the already-checked-in `data/intermediate/BPA_2024_v2_OEB_mod_utf8.json` as evidence
  that parser logic is unchanged. A full s01 rerun is a Sprint 03 (or later) sanity
  check, once the downstream notebooks are also migrated.
- **Renaming env vars later.** `BC3CAT_DATA_ROOT` / `BC3CAT_SYNTHETIC_DATA_ROOT` are
  the stable names — Sprint 03+ will consume them as-is.

---

## Tasks

### Task 1 — Extend `src/utils/config.py`

File: [`src/utils/config.py`](../../../src/utils/config.py).

Target shape after the edit (illustrative, not a literal source — the executor may
prefer slightly different layout as long as the public surface matches):

```python
"""Single-source-of-truth paths for the BC3CAT pipeline and BC3CAT-Syn sub-tree.

REPO_ROOT  → DATA_ROOT  → {RAW_DIR, INTERMEDIATE_DIR, PROCESSED_DIR, LLAMAINDEX_DIR,
                          SYNTHETIC_DATA_ROOT}
SYNTHETIC_DATA_ROOT → {SYNTHETIC_INTERMEDIATE_DIR, SYNTHETIC_PROCESSED_DIR,
                       SYNTHETIC_VARIANTS_DIR}

Env-var overrides (loaded at import time):
  BC3CAT_DATA_ROOT            → DATA_ROOT
  BC3CAT_SYNTHETIC_DATA_ROOT  → SYNTHETIC_DATA_ROOT
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_ROOT = Path(os.environ.get("BC3CAT_DATA_ROOT", REPO_ROOT / "data"))
RAW_DIR          = DATA_ROOT / "raw"
INTERMEDIATE_DIR = DATA_ROOT / "intermediate"
PROCESSED_DIR    = DATA_ROOT / "processed"
LLAMAINDEX_DIR   = DATA_ROOT / "llamaindex"

SYNTHETIC_DATA_ROOT = Path(
    os.environ.get("BC3CAT_SYNTHETIC_DATA_ROOT", DATA_ROOT / "synthetic")
)
SYNTHETIC_INTERMEDIATE_DIR = SYNTHETIC_DATA_ROOT / "intermediate"
SYNTHETIC_PROCESSED_DIR    = SYNTHETIC_DATA_ROOT / "processed"
SYNTHETIC_VARIANTS_DIR     = SYNTHETIC_DATA_ROOT / "variants"


def chapter_path(chapter: str, *, root: Path = INTERMEDIATE_DIR) -> Path:
    """`{root}/{chapter}/{chapter}.json` — the s02-output flavour."""
    return root / chapter / f"{chapter}.json"


def stage_path(chapter: str, stage_n: int, *, root: Path = INTERMEDIATE_DIR) -> Path:
    """`{root}/{chapter}/{chapter}_stage{n}.json` — s03+ flavour."""
    return root / chapter / f"{chapter}_stage{stage_n}.json"


class Config:
    """Back-compat shim for the original retrieval-side helpers."""
    DATA_DIR     = LLAMAINDEX_DIR
    TEXTO_PATH   = LLAMAINDEX_DIR / "IISS_plataforma_texto.pkl"
    RESUMEN_PATH = LLAMAINDEX_DIR / "IISS_plataforma_resumen.pkl"

    TOP_K        = 10
    NUM_SAMPLES  = 5
    BM25_K1      = 1.5
    BM25_B       = 0.75
```

**Notes on the shape:**

- `REPO_ROOT` resolves to `/work` inside the Docker container (where the repo is
  mounted at `/work`) and to the repo checkout root outside Docker. Both branches
  collapse to the same on-disk layout — no special-casing needed.
- Env vars are read *at import time* and stored as plain `Path` constants. Tests that
  exercise the override path must use `monkeypatch.setenv(...)` followed by
  `importlib.reload(config)`.
- `Config` is preserved intact; only the literal `/work/data/llamaindex` is removed.
- `chapter_path` and `stage_path` accept a `root` kwarg so the synthetic orchestrator
  (D2) can pass `SYNTHETIC_INTERMEDIATE_DIR` and reuse the same helpers without
  branching.

**Acceptance**

- `from utils.config import REPO_ROOT, DATA_ROOT, RAW_DIR, INTERMEDIATE_DIR, PROCESSED_DIR, LLAMAINDEX_DIR, SYNTHETIC_DATA_ROOT, SYNTHETIC_INTERMEDIATE_DIR, SYNTHETIC_PROCESSED_DIR, SYNTHETIC_VARIANTS_DIR, chapter_path, stage_path, Config` succeeds.
- All path constants are `pathlib.Path` instances.
- `DATA_ROOT == REPO_ROOT / "data"` when `BC3CAT_DATA_ROOT` is unset.
- After `monkeypatch.setenv("BC3CAT_DATA_ROOT", "/tmp/foo")` + `importlib.reload(config)`, `DATA_ROOT == Path("/tmp/foo")` and the four sub-dirs follow.
- `SYNTHETIC_DATA_ROOT == DATA_ROOT / "synthetic"` when `BC3CAT_SYNTHETIC_DATA_ROOT` is unset.
- `chapter_path("OBRA CIVIL") == INTERMEDIATE_DIR / "OBRA CIVIL" / "OBRA CIVIL.json"`.
- `stage_path("OBRA CIVIL", 5) == INTERMEDIATE_DIR / "OBRA CIVIL" / "OBRA CIVIL_stage5.json"`.
- `stage_path("OBRA CIVIL", 3, root=SYNTHETIC_INTERMEDIATE_DIR)` returns a path rooted under `SYNTHETIC_INTERMEDIATE_DIR`.
- `Config.DATA_DIR == LLAMAINDEX_DIR` (no `/work/` literal anywhere in the module).
- A `ripgrep -F '/work/' src/utils/config.py` finds zero hits.

---

### Task 2 — Refactor `s01_parse_fiebdc.ipynb`

File: [`src/s01_parse_fiebdc.ipynb`](../../../src/s01_parse_fiebdc.ipynb).

Two hardcoded sites (per `git grep '/work/' src/s01_parse_fiebdc.ipynb`):

| Line ~ | Current cell source                              | Replacement                                                |
|-------:|--------------------------------------------------|------------------------------------------------------------|
|     48 | `os.chdir('/work/data/raw')`                     | `os.chdir(config.RAW_DIR)`                                  |
|    580 | `os.chdir('/work/data')  # Running in a container` | `os.chdir(config.DATA_ROOT)`                                |

Both edits live inside the notebook's "source" arrays. Use `NotebookEdit` if available,
otherwise edit the `.ipynb` JSON via `Edit` — the surrounding strings are unique enough
for a literal replacement.

The cell that performs the `os.chdir` must also import the config. The cleanest pattern
(matching how `src/utils` is laid out as a namespace package) is to add to the cell's
imports:

```python
import sys
from pathlib import Path

_REPO_ROOT = Path.cwd().resolve()
while _REPO_ROOT.name != "bc3cat-dataset" and _REPO_ROOT.parent != _REPO_ROOT:
    _REPO_ROOT = _REPO_ROOT.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from utils import config
```

If the notebook already has a sys.path-manipulation cell that exposes `utils`, reuse
it — don't duplicate. If a simpler `from utils import config` works as-is inside the
Jupyter container (because `/work` is the cwd and `src/` is the python path), use the
simpler form and skip the bootstrap. The executor should pick the minimum change that
keeps the notebook runnable both inside Docker (`/work` mounted) and outside (Windows
host).

**Behavioural invariant.** After the refactor, running s01 end-to-end inside the
existing Jupyter container must produce a `data/intermediate/BPA_2024_v2_OEB_mod_utf8.json`
byte-identical to the currently-checked-in copy. This is the regression gate. **Do
not run the full notebook in this sprint** — Sprint 03 will validate end-to-end once
s03+ are also migrated. For Sprint 02, the gate is "the two changed lines compile,
the rest of the notebook is untouched, and the bytes of every other cell's `source`
field are unchanged."

**Acceptance**

- `grep -F '/work/' src/s01_parse_fiebdc.ipynb` finds zero hits in any cell's `source`
  array. (Output cells — `outputs` — are allowed to retain `/work/...` from the
  previous run; cleaning them is a separate cosmetic concern.)
- A `git diff src/s01_parse_fiebdc.ipynb` shows changes confined to the two target
  cells plus any new import lines. No spurious metadata diffs.
- The notebook still opens in Jupyter without parse errors (Jupyter's JSON
  well-formedness is a hard gate; spot-check via `python -c "import nbformat; nbformat.read('src/s01_parse_fiebdc.ipynb', 4)"`).

---

### Task 3 — Tests

Layout (additive to Sprint 01's `tests/synthetic/` tree):

```
tests/
  synthetic/          # from Sprint 01, unchanged
    conftest.py
    test_taxonomy.py
    test_mutator.py
  utils/              # NEW
    conftest.py       # same body as tests/synthetic/conftest.py
    test_config.py
```

`tests/utils/conftest.py` minimal shape (clone of the Sprint 01 one — single-file
copy is cheaper than introducing a shared parent `tests/conftest.py`):

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
```

`tests/utils/test_config.py` covers the seven acceptance bullets from Task 1. Test
strategy for the env-var override path:

```python
import importlib
from pathlib import Path

def test_data_root_default(monkeypatch):
    monkeypatch.delenv("BC3CAT_DATA_ROOT", raising=False)
    from utils import config
    importlib.reload(config)
    assert config.DATA_ROOT == config.REPO_ROOT / "data"

def test_data_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("BC3CAT_DATA_ROOT", str(tmp_path))
    from utils import config
    importlib.reload(config)
    assert config.DATA_ROOT == tmp_path
    assert config.RAW_DIR == tmp_path / "raw"
    assert config.SYNTHETIC_DATA_ROOT == tmp_path / "synthetic"
```

After the override tests, **a final `importlib.reload(config)` with the env var
restored to its default state** keeps the module clean for any later test in the
same pytest session. Put this in a session-scoped autouse fixture if convenient.

**Acceptance**

- `pytest tests/utils -q` from the repo root exits 0.
- `pytest tests -q` (the umbrella) also exits 0 — the Sprint 01 synthetic suite must
  not regress because of import-time changes in `utils/config.py`.
- No new external dependencies introduced beyond `pytest` (already in the stack from
  Sprint 01).

---

### Task 4 — Housekeeping

After Tasks 1–3 pass:

1. Append a Sprint 02 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (newest-first).
   Cover: what was built, key acceptance numbers (pytest count, paths verified),
   decisions taken (env-var names, helper signatures, deferral of s03–s07),
   next-step recommendation (Sprint 03 — s03–s07 migration).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - The "New Files in This Branch" block currently describes only the
     `src/synthetic/` tree. Add a brief subsection (or footnote) noting that
     [`src/utils/config.py`](../../../src/utils/config.py) gained `SYNTHETIC_DATA_ROOT` and the helper functions
     used by D2.
   - Prepend a new "After Sprint 02 — …" entry to the Sprint History section.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Task A4 part 1 closes; A4 part 2 stays open in the
   backlog for Sprint 03.

---

## Verification runbook

Run from the repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```bash
pytest tests -q                       # full suite — must stay green
```

Smoke checks (PowerShell-friendly one-liners):

```bash
python -c "from utils import config; assert config.DATA_ROOT == config.REPO_ROOT / 'data'; assert config.RAW_DIR.name == 'raw' and config.INTERMEDIATE_DIR.name == 'intermediate' and config.PROCESSED_DIR.name == 'processed'; print('default paths ok')"

python -c "from utils import config; assert config.SYNTHETIC_DATA_ROOT == config.DATA_ROOT / 'synthetic'; assert config.SYNTHETIC_INTERMEDIATE_DIR.name == 'intermediate'; print('synthetic paths ok')"

python -c "from utils.config import chapter_path, stage_path, INTERMEDIATE_DIR, SYNTHETIC_INTERMEDIATE_DIR; assert chapter_path('OBRA CIVIL') == INTERMEDIATE_DIR / 'OBRA CIVIL' / 'OBRA CIVIL.json'; assert stage_path('OBRA CIVIL', 5) == INTERMEDIATE_DIR / 'OBRA CIVIL' / 'OBRA CIVIL_stage5.json'; assert stage_path('OBRA CIVIL', 3, root=SYNTHETIC_INTERMEDIATE_DIR).parts[-3] == 'synthetic'; print('helpers ok')"

python -c "from utils.config import Config, LLAMAINDEX_DIR; assert Config.DATA_DIR == LLAMAINDEX_DIR; print('config backcompat ok')"

python -c "import nbformat; nbformat.read('src/s01_parse_fiebdc.ipynb', 4); print('s01 notebook parses')"
```

Set `PYTHONPATH` first if needed:

```powershell
$env:PYTHONPATH = "src"
```

End-of-sprint expected `git status`:

```
modified:   src/utils/config.py
modified:   src/s01_parse_fiebdc.ipynb
new file:   tests/utils/conftest.py
new file:   tests/utils/test_config.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_02.md   (this file, already committed)
```

Nothing under `src/synthetic/`, nothing under `tests/synthetic/`, no other notebook
under `src/`, nothing under `data/` or `configs/` should appear.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file map, design table
  (specifically the "Path-hardcoding" row).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.5 (what exists vs. what needs building),
  §5 Phase A (A4 task definition).
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 01 retro (closing recommendation pointing here).
- [`SPRINT_01.md`](SPRINT_01.md) — predecessor; same template structure.
- [`../../../src/utils/config.py`](../../../src/utils/config.py) — file to extend.
- [`../../../src/s01_parse_fiebdc.ipynb`](../../../src/s01_parse_fiebdc.ipynb) — notebook to migrate.

---

## Non-goals reminder

If you find yourself opening `s02_split_chapters.ipynb`,
`s03_generate_parametric_combinations.ipynb`, `s04_evaluate_text_variables.ipynb`,
`s05_evaluate_resumen_texto.ipynb`, `s06_data_analysis.ipynb`,
`s07_Filter_duplicates.ipynb`, `s08_Llamaindex_Doc_Creation.ipynb`, or
`Generate_OEB_dataset.ipynb`, **stop**. They each still hardcode `/work/...`; their
migration is Sprint 03's job, and bundling them into Sprint 02 makes the diff
unreviewable. The migration pattern lives in this sprint's s01 edit — Sprint 03 will
fan it out, with this sprint's pattern as the template.

Similarly, do not edit any `.ipynb_checkpoints/` file. They are Jupyter auto-saves
and will regenerate on next save. Touching them only creates noise.
