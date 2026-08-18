# Sprint 05 — Import-shape cleanup: relative imports in `src/utils/*.py` + Generate_OEB bootstrap retirement

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 05                                                                               |
| **Date**       | 2026-05-19 (drafted)                                                             |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | Post-A4 follow-up identified in the [Sprint 04 retro](../RESEARCH_LOG.md). Not in the original Phase A backlog — A1–A4 closed with Sprint 04. Tracked as a refinement to the file map, not a new task. |
| **Predecessor** | [`SPRINT_04.md`](SPRINT_04.md) — s08 + `Generate_OEB_dataset` notebook migration |
| **Successor**  | End-to-end-validation sprint (s01 → s08 → `Generate_OEB_dataset` rerun + byte-diff `OEB_*.parquet` / `*.pkl`), TBD |

---

## Context

Sprint 04 closed Task A4 by migrating [`src/s08_Llamaindex_Doc_Creation.ipynb`](../../../src/s08_Llamaindex_Doc_Creation.ipynb) and [`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb) off `/work/...` literals. One bootstrap survived the cleanup: the `sys.path.append(str(project_root))` pair in `Generate_OEB_dataset.ipynb` cell 2. The bootstrap is load-bearing because the next line — `from src.utils.data_utils import load_documents` — is a *repo-rooted* import that needs `REPO_ROOT` (the parent of `src/`) on `sys.path`, not `src/` itself. Three modules ship this absolute-import shape: [`src/utils/data_utils.py`](../../../src/utils/data_utils.py), [`src/utils/index_classes.py`](../../../src/utils/index_classes.py), [`src/utils/evaluation.py`](../../../src/utils/evaluation.py). Together they carry **5 `from src.utils.X` lines**.

Sprint 05 makes those imports relative (`from src.utils.X` → `from .X`), updates `Generate_OEB_dataset.ipynb` cell 2 to load `load_documents` via the kernel-cwd-anchored `from utils.data_utils import load_documents` shape that the other notebooks already use for `from utils import config`, then deletes the bootstrap. Net result: the path refactor's final shim retires and the in-repo import surface becomes uniform — every notebook touches `utils.*` directly without a `sys.path` mutation.

The change is **static-check only** (same gate as Sprints 02–04). Pytest count goes **51 → 54** with three new parametrised cases that scan the three target files for surviving `from src.utils.X` literals.

---

## Site survey (audited 2026-05-19, post-Sprint-04)

### Absolute imports inside `src/utils/*.py`

```
$ grep -n '^from src\.utils' src/utils/*.py
src/utils/data_utils.py:6:from src.utils.custom_types import DocumentList
src/utils/evaluation.py:4:from src.utils.custom_types import RetrievalResult
src/utils/index_classes.py:10:from src.utils.text_processing import normalize_text
src/utils/index_classes.py:11:from src.utils.custom_types import DocumentList, EmbeddingVector
src/utils/index_classes.py:12:from src.utils.config import Config
```

**Total: 5 lines across 3 files.** The other five modules in `src/utils/` (`__init__.py`, `config.py`, `custom_types.py`, `text_processing.py`, `z_formula_processing.py`) contain no `from src.utils.X` imports — they're either standalone or only used by the three offenders.

`src/utils/__init__.py` is currently empty (0 bytes). It stays empty — `src/utils/` is already a real package via the file's presence; relative imports work as soon as the package is loaded under any name.

### `Generate_OEB_dataset.ipynb` cell 2 (post-Sprint-04 state)

```python
import os
import sys
from pathlib import Path
import gc
import json
import pickle
from llama_index.core import Document
from utils import config

project_root = config.REPO_ROOT
sys.path.append(str(project_root))

from src.utils.data_utils import load_documents
```

Usage audit (`os.*` / `sys.*` / `Path(...)` / `gc.*` scanned across all 10 cells): **only `sys` is referenced**, and only by `sys.path.append(str(project_root))`. `os`, `Path`, `gc` are imported but never used. Pruning the unused trio is cosmetic-only and **out of scope** — same policy Sprints 03/04 applied to `from pathlib import Path` in s07 / s08.

### `bc3cat-retrieval` coupling check

[`bc3cat-retrieval`](../../../../bc3cat-retrieval) carries **parallel copies** of `src/utils/{config,custom_types,text_processing,data_utils,index_classes,evaluation}.py` under its own `src/utils/` tree. The two repos do **not** share files at the filesystem level. The Sprint 04 retro's "cross-repo coupling check needed" hedge therefore reduces to a *consistency* question, not a *correctness* one: if `bc3cat-retrieval` ever rebases off these modules it should mirror the same relative-import shape, but the in-repo Sprint 05 diff cannot break the sibling repo's runtime.

```
$ grep -rn '^from src\.utils' D:/Users/cesar/Dev/Phd/bc3cat-retrieval/src
D:/.../bc3cat-retrieval/src/utils/index_classes.py:10: from src.utils.text_processing import normalize_text
D:/.../bc3cat-retrieval/src/utils/index_classes.py:11: from src.utils.custom_types import DocumentList, EmbeddingVector
D:/.../bc3cat-retrieval/src/utils/index_classes.py:12: from src.utils.config import Config
D:/.../bc3cat-retrieval/src/utils/evaluation.py:4:   from src.utils.custom_types import RetrievalResult
D:/.../bc3cat-retrieval/src/utils/data_utils.py:6:   from src.utils.custom_types import DocumentList
D:/.../bc3cat-retrieval/src/pipeline/param_extractor_rules.py:23: from src.utils.text_processing import normalize_text
```

Same 5 lines in the parallel modules, plus one consumer in `src/pipeline/param_extractor_rules.py`. Mirroring the cleanup over there is a separate, optional task; **not in Sprint 05's scope**.

### `Generate_OEB_dataset.ipynb` `load_documents` callers

`grep load_documents src/*.ipynb` returns three hits, all inside `Generate_OEB_dataset.ipynb`:

- Cell 2: `from src.utils.data_utils import load_documents` (the import).
- Cell 3: `documents = load_documents(documents_path)`.
- Cell 8: `documents = load_documents(documents_path)`.
- Cell 4: `doc = load_documents("OEB_texto.pkl")`.

No other notebook in the pipeline imports from `data_utils.py`, `index_classes.py`, or `evaluation.py`. The `index_classes.py` / `evaluation.py` modules are dead weight inside `bc3cat-dataset` — they're only meaningful for `bc3cat-retrieval`. Sprint 05 still cleans up their imports for consistency; deleting them entirely is a separate question (and probably the wrong call — they're part of the public file surface the retrieval repo originally copied from).

---

## Scope

### In scope

- **`src/utils/data_utils.py`** — rewrite line 6:
  - `from src.utils.custom_types import DocumentList` → `from .custom_types import DocumentList`.
- **`src/utils/evaluation.py`** — rewrite line 4:
  - `from src.utils.custom_types import RetrievalResult` → `from .custom_types import RetrievalResult`.
- **`src/utils/index_classes.py`** — rewrite lines 10–12:
  - `from src.utils.text_processing import normalize_text` → `from .text_processing import normalize_text`.
  - `from src.utils.custom_types import DocumentList, EmbeddingVector` → `from .custom_types import DocumentList, EmbeddingVector`.
  - `from src.utils.config import Config` → `from .config import Config`.

  Total: **5 single-line edits across 3 files.** No other lines in those modules change; the diff stat per file is exactly `+1/−1` × (1, 1, 3) = `+5/−5` across the three.

- **`src/Generate_OEB_dataset.ipynb` cell 2** — three edits in one `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle:
  1. Replace `from src.utils.data_utils import load_documents` with `from utils.data_utils import load_documents`. This is the symmetric form of `from utils import config` already present in the same cell — anchored at the Jupyter kernel cwd (`src/`), no `REPO_ROOT` needed.
  2. Delete the two lines `project_root = config.REPO_ROOT` and `sys.path.append(str(project_root))`. With the import on line just above no longer repo-rooted, `sys.path` doesn't need mutating — the bootstrap was load-bearing only for the absolute import.
  3. Delete the now-orphaned blank line that separated the bootstrap from the import. The cell ends as a single contiguous import block; resulting target shape:

     ```python
     import os
     import sys
     from pathlib import Path
     import gc
     import json
     import pickle
     from llama_index.core import Document
     from utils import config
     from utils.data_utils import load_documents
     ```

  Diff stat for the notebook: roughly `+1/−4` in cell 2 only. No other cells touched.

- **New regression test** — [`tests/utils/test_utils_no_absolute_self_imports.py`](../../../tests/utils/test_utils_no_absolute_self_imports.py) (new file):

  ```python
  """Regression guard: no module inside `src/utils/` may use absolute self-imports
  of the form `from src.utils.X` — they break unless the caller has set up
  `REPO_ROOT` on sys.path (the bootstrap that Sprint 05 retires from
  Generate_OEB_dataset.ipynb cell 2). Use relative imports instead.
  """
  import re
  from pathlib import Path

  import pytest

  REPO_ROOT = Path(__file__).resolve().parents[2]
  UTILS_DIR = REPO_ROOT / "src" / "utils"

  MODULES = [
      "data_utils.py",
      "evaluation.py",
      "index_classes.py",
  ]

  ABS_IMPORT = re.compile(r"^\s*(from|import)\s+src\.utils\b", re.MULTILINE)


  @pytest.mark.parametrize("module", MODULES)
  def test_no_absolute_self_imports(module):
      path = UTILS_DIR / module
      source = path.read_text(encoding="utf-8")
      hits = ABS_IMPORT.findall(source)
      assert not hits, (
          f"{module}: found {len(hits)} `from src.utils.X` / `import src.utils.X` "
          f"line(s); switch to relative imports (`from .X` / `from . import X`)."
      )
  ```

  Three parametrised cases, one per file. The other five `src/utils/*.py` modules are not tested because they have no relative-import-eligible self-imports to begin with — adding them would just inflate the test count for no extra coverage.

- **Notebook-guard test** — [`tests/utils/test_notebooks_no_work_literal.py`](../../../tests/utils/test_notebooks_no_work_literal.py) **stays unchanged.** Sprint 04 widened the gate to bare `/work`; Sprint 05's bootstrap deletion does not change any `/work` literal (Sprint 04 already swapped `Path('/work')` for `config.REPO_ROOT`). No new notebook-content invariant is being introduced — the test already covers the surface.

- **Housekeeping.** Append Sprint 05 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md); prepend "After Sprint 05 — …" to [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s Sprint History; in the "Existing files extended" block flip the three `src/utils/*.py` modules from "(originally `from src.utils.X` shape; Sprint 05 — relative imports)" or simply add a one-line entry noting Sprint 05's contribution. The `Generate_OEB_dataset.ipynb` row already says ✅ Sprint 04 — append a parenthetical that Sprint 05 retired its bootstrap.

### Out of scope (explicit)

- **Pruning unused imports in `Generate_OEB_dataset.ipynb` cell 2.** `os`, `Path`, `gc` are imported but never referenced anywhere in the notebook. Removing them is cosmetic-only and matches the Sprint 03/04 policy of leaving unused imports in place. `sys` is removed naturally because the bootstrap that used it disappears — that's the only line the strict scope touches in the import block. If a future sprint does an "unused-imports sweep" across all nine notebooks, this is a candidate.

- **Mirroring the cleanup in `bc3cat-retrieval`.** The sibling repo carries parallel copies with the same `from src.utils.X` shape (see the site survey). Mirroring is a consistency concern, not a correctness one — Sprint 05 cannot break the sibling repo's runtime because no file is shared. Tracked as a separate optional task on the `bc3cat-retrieval` side, not as a `bc3cat-dataset` sprint follow-up.

- **Adding `src/__init__.py` to make `src/` a real package.** `src/` works as a namespace package today (no `__init__.py`, but `from src.utils.X` resolves through Python's implicit namespace-package handling when `REPO_ROOT` is on `sys.path`). Sprint 05 *removes* the dependency on namespace-package behaviour by switching to relative imports inside `src/utils/` and to `from utils.X` (anchored at `src/`) from the notebook. After Sprint 05 no caller in `bc3cat-dataset` needs `src` to be importable. **Do not add `src/__init__.py`.** It would only help if some future caller wants to do `from src.utils.X` — which after Sprint 05 nobody does.

- **End-to-end pipeline rerun.** Same as Sprint 04 — the static-check gate stays this sprint's scope. The end-to-end-validation sprint (s01 → s08 → `Generate_OEB_dataset` rerun + byte-diff against `OEB_*.parquet` / `*.pkl`) is the next planned follow-up.

- **`.ipynb_checkpoints/`.** Both [`src/.ipynb_checkpoints/`](../../../src/.ipynb_checkpoints) and [`src/utils/.ipynb_checkpoints/`](../../../src/utils/.ipynb_checkpoints) carry the old `from src.utils.X` shape in their stale `data_utils-checkpoint.py` / `evaluation-checkpoint.py` / `index_classes-checkpoint.py`. They are Jupyter auto-saves that regenerate on next save. **Do not touch.** Same policy as Sprints 02–04.

- **Phase B mutator bodies.** Still stubs from Sprint 01. Not this sprint.

- **Renaming `OBRA CIVIL` to something without an internal space.** Same standing decision as Sprints 02–04: stays as-is.

---

## Tasks

The migration touches 3 `.py` files (one-line edits each), 1 notebook (one `json.load`-cycle), and 1 new test file. Order is non-critical — the `.py` edits and the notebook edit are independent and can be applied in any sequence, but **the test must land last** because it asserts the post-edit invariant.

### Task 1 — Switch `src/utils/data_utils.py` to a relative import

File: [`src/utils/data_utils.py`](../../../src/utils/data_utils.py).

Single line edit on line 6:

```python
-from src.utils.custom_types import DocumentList
+from .custom_types import DocumentList
```

**Acceptance**

- `git diff src/utils/data_utils.py` shows exactly `+1/−1` on line 6, nothing else.
- `python -c "import sys; sys.path.insert(0, 'src'); from utils.data_utils import load_documents; print(load_documents)"` runs without raising (sanity import — only stdlib + `custom_types` needed).

---

### Task 2 — Switch `src/utils/evaluation.py` to a relative import

File: [`src/utils/evaluation.py`](../../../src/utils/evaluation.py).

Single line edit on line 4:

```python
-from src.utils.custom_types import RetrievalResult
+from .custom_types import RetrievalResult
```

**Acceptance**

- `git diff src/utils/evaluation.py` shows exactly `+1/−1` on line 4, nothing else.
- `python -c "import sys; sys.path.insert(0, 'src'); from utils import evaluation; print(evaluation.perform_analysis)"` runs without raising. (Only `numpy` is needed beyond stdlib + `custom_types`; numpy is in the env per Sprint 01.)

---

### Task 3 — Switch `src/utils/index_classes.py` to relative imports

File: [`src/utils/index_classes.py`](../../../src/utils/index_classes.py).

Three line edits on lines 10–12:

```python
-from src.utils.text_processing import normalize_text
-from src.utils.custom_types import DocumentList, EmbeddingVector
-from src.utils.config import Config
+from .text_processing import normalize_text
+from .custom_types import DocumentList, EmbeddingVector
+from .config import Config
```

**Acceptance**

- `git diff src/utils/index_classes.py` shows exactly `+3/−3` on lines 10–12, nothing else.
- `index_classes.py` is **not** importability-tested in this sprint — it pulls in `scipy`, `sklearn`, and `llama_index`, which inflate the env requirement well past the lightweight static-check footprint Sprints 02–04 maintained. The new regression test (Task 5) covers it via source-text scan instead. If a future sprint promotes to runtime-import testing, this is the first module to gate on.

---

### Task 4 — Retire the `Generate_OEB_dataset.ipynb` cell 2 bootstrap

File: [`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb), cell 2 (id prefix `80529a1b`).

Apply three changes in a single `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle, writing via `Path.write_bytes(text.encode("utf-8") + b"\n")` to preserve LF on Windows (matches Sprint 04 recipe):

1. Replace the line
   ```python
   from src.utils.data_utils import load_documents
   ```
   with
   ```python
   from utils.data_utils import load_documents
   ```
2. Delete the two-line block
   ```python
   project_root = config.REPO_ROOT
   sys.path.append(str(project_root))
   ```
3. Delete the blank separator line above that block (the one between `from utils import config` and `project_root = …`) so the imports collapse into one contiguous block. The cell's source array should end as a single block of import statements followed by no trailing blank line inside the cell.

Target post-Sprint-05 contents:

```python
import os
import sys
from pathlib import Path
import gc
import json
import pickle
from llama_index.core import Document
from utils import config
from utils.data_utils import load_documents
```

(`import sys` and `from pathlib import Path` and `import os` / `import gc` remain — see "Out of scope" rationale.)

**Acceptance**

- `git diff src/Generate_OEB_dataset.ipynb` confined to cell 2 only — no other cells modified, no metadata churn.
- `Grep '^from src\.' src/Generate_OEB_dataset.ipynb` → 0 hits anywhere (source or output arrays).
- `Grep 'sys\.path\.append' src/Generate_OEB_dataset.ipynb` → 0 hits.
- The notebook still parses (`json.load` smoke check).
- Existing notebook-guard test (`/work` literal) continues to pass — the bootstrap deletion did not introduce any new `/work` strings.

---

### Task 5 — Add the `from src.utils.X` regression-guard test

File: [`tests/utils/test_utils_no_absolute_self_imports.py`](../../../tests/utils/test_utils_no_absolute_self_imports.py) (new file).

Contents as shown in the "In scope" block above. The test:
- Reads each of the three modules as text.
- Regex-scans for `^\s*(from|import)\s+src\.utils\b` (catches both `from src.utils.X import Y` and `import src.utils.X`).
- Asserts zero matches per module — 3 parametrised cases.

**Acceptance**

- `pytest tests/utils/test_utils_no_absolute_self_imports.py -q` exits 0 with **3 passed**.
- Spot-check: manually reintroduce `from src.utils.custom_types import DocumentList` at the top of `data_utils.py` (without committing) → the corresponding parametrised case fails. Revert before continuing.

---

### Task 6 — Verification

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```bash
pytest tests -q
```

Expected: **54 passed** (Sprint 04's 51 + 3 new `from src.utils.X` guard cases). No regressions; no skips.

Smoke checks (PowerShell-friendly):

```bash
python -X utf8 -c "
import sys
sys.path.insert(0, 'src')
from utils.data_utils import load_documents
from utils import evaluation
print('data_utils + evaluation import via from utils.X: OK')
print(load_documents.__name__, evaluation.perform_analysis.__name__)
"
```

Expected output:
```
data_utils + evaluation import via from utils.X: OK
load_documents perform_analysis
```

(Skip `index_classes` — heavy deps. Its coverage is the text-scan test from Task 5.)

```bash
python -X utf8 -c "
import json
nb = json.load(open('src/Generate_OEB_dataset.ipynb','r',encoding='utf-8'))
cell2 = ''.join(nb['cells'][2]['source'])
assert 'sys.path.append' not in cell2, 'bootstrap still present'
assert 'from src.utils' not in cell2, 'absolute import still present'
assert 'from utils.data_utils import load_documents' in cell2, 'new import missing'
print('Generate_OEB cell 2 invariants: OK')
"
```

Expected output: `Generate_OEB cell 2 invariants: OK`.

End-of-sprint expected `git status`:

```
modified:   src/utils/data_utils.py
modified:   src/utils/evaluation.py
modified:   src/utils/index_classes.py
modified:   src/Generate_OEB_dataset.ipynb
new file:   tests/utils/test_utils_no_absolute_self_imports.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_05.md   (this file, may be bundled with the execution commit per the Sprint 03/04 precedent)
```

Nothing under `src/synthetic/`, `tests/synthetic/`, `tests/utils/conftest.py`, `tests/utils/test_config.py`, `tests/utils/test_notebooks_no_work_literal.py`, any of s01–s08 under `src/`, anything under `data/` or `configs/`, the other `src/utils/*.py` files (`config.py`, `custom_types.py`, `text_processing.py`, `z_formula_processing.py`, `__init__.py`), or `.ipynb_checkpoints/` should appear in the diff.

---

### Task 7 — Housekeeping

After Tasks 1–6 pass:

1. Append a Sprint 05 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (newest-first). Cover:
   - 5 line edits across 3 `src/utils/*.py` modules (`from src.utils.X` → `from .X`).
   - `Generate_OEB_dataset.ipynb` cell 2: import shape switched (`from src.utils.data_utils` → `from utils.data_utils`); 2-line `project_root = … ; sys.path.append(…)` bootstrap deleted; 1 blank separator removed. The path refactor's final shim retires.
   - New regression test (`test_utils_no_absolute_self_imports.py`) — 3 parametrised cases; pytest count 51 → 54.
   - Decisions confirmed:
     (a) Relative imports inside `src/utils/` are robust regardless of whether the caller imports the module as `from src.utils.X` (namespace-package shape) or `from utils.X` (kernel-cwd-anchored shape) — Python resolves `.custom_types` against the module's loaded package context either way. So Sprint 05's cleanup does not break any hypothetical absolute-import caller that hasn't been migrated yet.
     (b) `bc3cat-retrieval` carries parallel copies with the same shape; mirroring is a sibling-repo task, not a `bc3cat-dataset` follow-up.
     (c) `src/__init__.py` deliberately not added — after Sprint 05 no caller needs `src` to be a package.
     (d) Unused imports (`os`, `Path`, `gc`) in cell 2 left in place per Sprint 03/04 policy.
   - Next-step recommendation: the **end-to-end-validation sprint** — rerun s01 → s08 → `Generate_OEB_dataset` against the existing `data/intermediate/...` files and byte-diff the produced `data/processed/OEB_*.parquet` / `*.pkl` against the in-repo originals to confirm Sprints 02–05 are collectively behaviour-preserving across the full main pipeline. Requires a Docker / `pandas` / `pyarrow` / `llama_index` env, which Sprints 02–05's static gate has not exercised.

2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - In the "Existing files extended" block, add a new row (or append a parenthetical) noting that `src/utils/{data_utils,evaluation,index_classes}.py` had their `from src.utils.X` self-imports switched to relative in Sprint 05.
   - In the same block, append to the `Generate_OEB_dataset.ipynb` row a parenthetical noting Sprint 05 retired the cell 2 `sys.path.append` bootstrap.
   - Prepend a new "After Sprint 05 — …" entry to the Sprint History section.

3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Task A4 already closed in Sprint 04; Sprint 05 is a refinement to the file map, not a backlog item.

---

## Verification runbook

Already inlined in Task 6 above. The `pytest` invocation and the two smoke one-liners are the gates.

If a relative-import edit accidentally introduces a `SyntaxError` (e.g. a typo in `from .custom_types`), the lightweight importability check in the first smoke command will raise the ImportError loudly with the file name. The Task-5 text-scan test only checks for the *old* absolute-import pattern; it cannot detect a malformed *new* import. The smoke import is the gate for that.

If the notebook fails to round-trip through `json.load` / `json.dumps`, that is a hard error — confirm the executor used `json.dumps(..., indent=1, ensure_ascii=False)` and wrote bytes (`Path.write_bytes(text.encode("utf-8") + b"\n")`) rather than text-mode. Sprints 03 + 04 confirmed text-mode CRLF-corrupts LF on Windows.

If the new regression test (Task 5) flags a hit it cannot explain, dump the surviving line:

```bash
python -X utf8 -c "
import re
from pathlib import Path
ABS = re.compile(r'^\s*(from|import)\s+src\.utils\b', re.MULTILINE)
for name in ['data_utils.py', 'evaluation.py', 'index_classes.py']:
    p = Path('src/utils') / name
    for m in ABS.finditer(p.read_text(encoding='utf-8')):
        line_no = p.read_text(encoding='utf-8')[:m.start()].count(chr(10)) + 1
        print(f'{name}:{line_no}: {m.group(0)}')
"
```

Typical culprit: a line that wasn't on the line-number list above slipped in via a recent edit, or an `import src.utils.X` form (rare but the regex catches both).

---

## References

- [`SPRINT_04.md`](SPRINT_04.md) — predecessor; retro identifies this sprint's scope and the bootstrap retirement.
- [`SPRINT_03.md`](SPRINT_03.md) — establishes the notebook `json.load`-cycle recipe and the `Path.write_bytes` LF discipline reused here.
- [`SPRINT_02.md`](SPRINT_02.md) — defines the `config.py` public surface and the `from utils import config` shape Sprint 05 mirrors for `from utils.data_utils import load_documents`.
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file map.
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 04 retro closing recommendation pointing here.
- [`../../../src/utils/`](../../../src/utils) — the three target modules.
- [`../../../tests/utils/conftest.py`](../../../tests/utils/conftest.py) — puts `src/` on `sys.path`, which is why `from utils.data_utils import load_documents` works in the test env (and in the Jupyter kernel cwd) without any bootstrap.

---

## Non-goals reminder

If you find yourself opening any of `s01_parse_fiebdc.ipynb` … `s08_Llamaindex_Doc_Creation.ipynb`, **stop**. They were migrated in Sprints 02–04 and contain no `from src.utils.X` import shape (`s01–s07` never did; s08 imports `from utils import config` only). Only `Generate_OEB_dataset.ipynb` is in scope here, and only its cell 2.

If you find yourself touching `src/utils/config.py`, `src/utils/custom_types.py`, `src/utils/text_processing.py`, `src/utils/z_formula_processing.py`, or `src/utils/__init__.py`, **stop and reconsider**. None of them currently has a `from src.utils.X` self-import (verified by the site survey); they are out of scope.

If you find yourself rewriting `Generate_OEB_dataset.ipynb` cell 2 to also remove `import os`, `from pathlib import Path`, or `import gc`, **stop**. Unused imports stay per the Sprint 03/04 standing decision. Sprint 05's diff in that cell is `+1/−4` (one new import line, four lines deleted: the absolute import, the `project_root = …`, the `sys.path.append(…)`, and the blank separator). Anything beyond that bloats the diff.

If you find yourself editing the sibling `bc3cat-retrieval` repo to mirror the cleanup, **stop**. That's a separate, optional task that lives on the retrieval side. Sprint 05 cannot break `bc3cat-retrieval` because no files are shared at the filesystem level.

If you find yourself running any notebook end-to-end (importing `pandas` / `llama_index` / `scipy` / `sklearn`, constructing a `Document`, etc.), **stop**. Static checks only — same gate as Sprints 02–04. The end-to-end-validation sprint is the planned follow-up.

Similarly, do not edit any `.ipynb_checkpoints/` file or add `src/__init__.py`. The first is Jupyter auto-save noise; the second would re-introduce the namespace-package dependency that Sprint 05 specifically eliminates.
