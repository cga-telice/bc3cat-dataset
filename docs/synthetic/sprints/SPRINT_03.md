# Sprint 03 — Path refactor: s02–s07 notebook migration

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 03                                                                               |
| **Date**       | 2026-05-19 (drafted)                                                             |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | A4 part 2 (s02–s07 notebook migration) — see [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md) |
| **Predecessor** | [`SPRINT_02.md`](SPRINT_02.md) — config core + s01 migration                     |
| **Successor**  | Sprint 04 — A4 part 3 (s08 + `Generate_OEB_dataset` migration), TBD              |

---

## Context

Sprint 02 locked down [`src/utils/config.py`](../../../src/utils/config.py) as the single-source-of-truth paths
module (`DATA_ROOT`, `INTERMEDIATE_DIR`, `SYNTHETIC_*` sub-tree, `chapter_path` /
`stage_path` helpers, env-var overrides) and migrated
[`s01_parse_fiebdc.ipynb`](../../../src/s01_parse_fiebdc.ipynb) as the one-notebook proof of the migration pattern.
42 tests pass.

Sprint 03 is **A4 part 2** — fan that pattern across the six remaining
synthetic-critical-path notebooks. The downstream-notebook source cells together
contain **14 hardcoded `/work/...` literals** (see the table in Task scopes
below); output cells contain another **18** that will regenerate on the next
rerun and are deliberately left alone, matching the s01 policy.

After Sprint 03 every notebook the synthetic orchestrator (`run_synthetic.py`,
Task D2) needs to drive will read from `config.INTERMEDIATE_DIR` /
`config.chapter_path(...)` / `config.stage_path(...)`, so the orchestrator can
swap in `SYNTHETIC_INTERMEDIATE_DIR` simply by setting the
`BC3CAT_DATA_ROOT` / `BC3CAT_SYNTHETIC_DATA_ROOT` env vars Sprint 02 locked.

[`s08_Llamaindex_Doc_Creation.ipynb`](../../../src/s08_Llamaindex_Doc_Creation.ipynb) and
[`Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb) are deferred to Sprint 04: they only emit
the final main-pipeline artifacts (the LlamaIndex pickle and the OEB Parquet
release), and are not invoked by the synthetic orchestrator.

---

## Scope

### In scope

- **Source-cell migrations across s02 → s07.** Total: 14 site replacements in
  the cell `source` arrays of six notebooks. Exact site table:

  | Notebook                                              | Cell idx | id (8-char) | Sites |
  |-------------------------------------------------------|---------:|-------------|------:|
  | `s02_split_chapters.ipynb`                            | 2        | `8ad4ae45`  | 1     |
  | `s03_generate_parametric_combinations.ipynb`          | 2        | `3425c1d1`  | 1     |
  | `s04_evaluate_text_variables.ipynb`                   | 3        | `69ee396a`  | 1     |
  | `s05_evaluate_resumen_texto.ipynb`                    | 3        | `adfd5a47`  | 1     |
  | `s06_data_analysis.ipynb`                             | 2        | `39432bd0`  | 1     |
  | `s07_Filter_duplicates.ipynb`                         | 2        | `e901816d`  | 2     |
  | `s07_Filter_duplicates.ipynb`                         | 3        | `11833a3d`  | 1     |
  | `s07_Filter_duplicates.ipynb`                         | 8        | `8d1aea31`  | 4     |
  | `s07_Filter_duplicates.ipynb`                         | 11       | `949ea377`  | 2     |

- **`from utils import config`** added once per notebook to the first code cell
  that uses `config.*`. Reuse the Sprint 02 finding: Jupyter's per-notebook
  kernel cwd is `src/` both in Docker and on the Windows host, so no `sys.path`
  bootstrap is needed. The `s07` cells 3 and 8 currently include
  `project_root = Path('/work'); sys.path.append(str(project_root))` — **remove
  those two-line bootstraps** as part of the migration; they served the same
  purpose and become dead code once `config` is on the implicit notebook-dir
  path entry.

- **Regression-guard test.** Add `tests/utils/test_notebooks_no_work_literal.py`
  that scans the cell `source` arrays of s01–s07 and asserts zero `/work/`
  occurrences. Output cells (`outputs`) are explicitly skipped. Sprint 04 will
  extend the notebook list to include s08 + `Generate_OEB_dataset`.

- **Housekeeping.** Append Sprint 03 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md), prepend "After
  Sprint 03 — …" to [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s Sprint History, and flip the
  "Existing files extended" block to mark s02–s07 ✅.

### Out of scope (explicit)

- **`s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb`.** Both
  still hardcode `/work/...` (5 and 3 source-cell hits respectively). Their
  migration is Sprint 04. They are not on the synthetic critical path, so
  deferring them keeps Sprint 03's diff reviewable.
- **`.ipynb_checkpoints/` files.** Jupyter auto-saves under
  `src/.ipynb_checkpoints/` (and the matching `src/utils/.ipynb_checkpoints/`)
  will regenerate on the next save. **Do not touch.** Same rule as Sprint 02.
- **Output-cell `/work/` strings.** The 18 occurrences in `outputs` arrays are
  printed by `print()` statements from the previous run; they regenerate on
  rerun. Editing them is cosmetic-only and explicitly excluded — matches the
  s01 policy in Sprint 02.
- **Phase B mutator bodies.** Still stubs from Sprint 01. Not this sprint.
- **End-to-end pipeline rerun.** Running each refactored notebook against the
  existing `data/intermediate/...` files and byte-diffing the outputs is the
  natural validation gate, but it requires Docker / a configured Python env
  with `pandas` / `pyarrow` / etc., and the executor for this sprint may not
  have that. Acceptance is **static** — see Task 8. The first end-to-end
  validation sprint is planned as a follow-up after Sprint 04 lands s08 +
  `Generate_OEB_dataset`.
- **Renaming the existing chapter folder convention.** `OBRA CIVIL` (with
  internal space) stays as-is; `chapter_path("OBRA CIVIL")` and
  `stage_path("OBRA CIVIL", N)` already handle the space correctly (verified
  in Sprint 02's `tests/utils/test_config.py`).

---

## Tasks

The migration uses the same `json.load` → patch the `source` array → `json.dumps(..., indent=1)`
technique Sprint 02 adopted, because `Edit` refuses `.ipynb` files and full-cell
`NotebookEdit` replaces would balloon the diff for any cell larger than a few
lines.

For each notebook task, the executor should run **one** Python helper script
that does *all* of that notebook's site replacements in a single load/write
cycle (so the JSON is re-pretty-printed once, not N times — keeps diff stable).

### Task 1 — Migrate `s02_split_chapters.ipynb`

File: [`src/s02_split_chapters.ipynb`](../../../src/s02_split_chapters.ipynb).

**Cell 2** (id `8ad4ae45`) — single line, currently:

```python
split_chapters("/work/data/intermediate/BPA_2024_v2_OEB_mod_utf8.json")
```

Replace cell source with:

```python
from utils import config

split_chapters(config.INTERMEDIATE_DIR / "BPA_2024_v2_OEB_mod_utf8.json")
```

(The file `BPA_2024_v2_OEB_mod_utf8.json` lives directly in `data/intermediate/`,
not under a chapter sub-folder — so `INTERMEDIATE_DIR / "..."` rather than
`chapter_path(...)`.)

**Acceptance**

- `Grep '/work/' src/s02_split_chapters.ipynb` matches **0** source-array lines
  (output-array lines may remain — they regenerate on rerun).
- `git diff src/s02_split_chapters.ipynb` shows changes confined to cell 2's
  `source` array. No metadata churn.
- `python -c "import json; json.load(open('src/s02_split_chapters.ipynb', 'r', encoding='utf-8'))"` succeeds.

---

### Task 2 — Migrate `s03_generate_parametric_combinations.ipynb`

File: [`src/s03_generate_parametric_combinations.ipynb`](../../../src/s03_generate_parametric_combinations.ipynb).

**Cell 2** (id `3425c1d1`) — currently:

```python
input_file = '/work/data/intermediate/OBRA CIVIL/OBRA CIVIL.json'  # Path to the source file; change dynamically as needed
run_s03_generate_parametric_combinations(input_file)
```

Replace cell source with:

```python
from utils import config

input_file = config.chapter_path("OBRA CIVIL")  # change chapter name as needed
run_s03_generate_parametric_combinations(input_file)
```

**Acceptance**

- `Grep '/work/' src/s03_generate_parametric_combinations.ipynb` matches **0**
  source-array lines.
- `git diff src/s03_generate_parametric_combinations.ipynb` confined to cell 2.
- `python -c "import json; json.load(open('src/s03_generate_parametric_combinations.ipynb', 'r', encoding='utf-8'))"` succeeds.

---

### Task 3 — Migrate `s04_evaluate_text_variables.ipynb`

File: [`src/s04_evaluate_text_variables.ipynb`](../../../src/s04_evaluate_text_variables.ipynb).

**Cell 3** (id `69ee396a`) — currently:

```python
input_file = '/work/data/intermediate/OBRA CIVIL/OBRA CIVIL.json'
main(input_file)
```

Replace cell source with:

```python
from utils import config

input_file = config.chapter_path("OBRA CIVIL")
main(input_file)
```

**Acceptance**

- `Grep '/work/' src/s04_evaluate_text_variables.ipynb` → 0 source hits.
- `git diff` confined to cell 3.
- JSON parses.

---

### Task 4 — Migrate `s05_evaluate_resumen_texto.ipynb`

File: [`src/s05_evaluate_resumen_texto.ipynb`](../../../src/s05_evaluate_resumen_texto.ipynb).

**Cell 3** (id `adfd5a47`) — currently:

```python
input_file = '/work/data/intermediate/OBRA CIVIL/OBRA CIVIL.json'
main(input_file)
```

Replace cell source with:

```python
from utils import config

input_file = config.chapter_path("OBRA CIVIL")
main(input_file)
```

**Acceptance**

- `Grep '/work/' src/s05_evaluate_resumen_texto.ipynb` → 0 source hits.
- `git diff` confined to cell 3.
- JSON parses.

---

### Task 5 — Migrate `s06_data_analysis.ipynb`

File: [`src/s06_data_analysis.ipynb`](../../../src/s06_data_analysis.ipynb).

**Cell 2** (id `39432bd0`) — currently:

```python
file_path = '/work/data/intermediate/OBRA CIVIL/OBRA CIVIL_stage5.json'
main(file_path)
```

Replace cell source with:

```python
from utils import config

file_path = config.stage_path("OBRA CIVIL", 5)
main(file_path)
```

**Acceptance**

- `Grep '/work/' src/s06_data_analysis.ipynb` → 0 source hits.
- `git diff` confined to cell 2.
- JSON parses.

---

### Task 6 — Migrate `s07_Filter_duplicates.ipynb`

File: [`src/s07_Filter_duplicates.ipynb`](../../../src/s07_Filter_duplicates.ipynb). This is the heaviest task — 9 source-cell hits
spread across 4 cells. Do all 9 edits in a single `json.load` → patch → write
cycle to keep the JSON pretty-print stable.

**Cell 2** (id `e901816d`) — currently:

```python
marcar_duplicados(
    path_entrada='/work/data/intermediate/OBRA CIVIL/OBRA CIVIL_stage5.json',                   # ← cambia esto
    path_salida='/work/data/intermediate/OBRA CIVIL/OBRA CIVIL_stage6.json'
)
```

Replace cell source with:

```python
from utils import config

marcar_duplicados(
    path_entrada=config.stage_path("OBRA CIVIL", 5),   # ← cambia el chapter aquí
    path_salida=config.stage_path("OBRA CIVIL", 6),
)
```

**Cell 3** (id `11833a3d`) — currently begins:

```python
# This script takes data from the _stage6 pipeline and prints out a sample according to its 'validation' flag
import sys
from pathlib import Path
import json
import random
from collections import Counter, defaultdict
import pandas as pd

project_root = Path('/work')
sys.path.append(str(project_root))

def main(chapter):
    document_path = Path('/work/data/intermediate/' + chapter + '/' + chapter + '_stage6.json')
    ...
```

Apply two surgical edits inside the cell's `source` array:

1. Delete the two-line block

   ```python
   project_root = Path('/work')
   sys.path.append(str(project_root))
   ```

   (it's a `sys.path` bootstrap that becomes redundant once `from utils import config`
   is in scope from cell 1's execution.)

2. Add `from utils import config` to the import block at the top of the cell
   (right after the existing imports).

3. Replace the line

   ```python
       document_path = Path('/work/data/intermediate/' + chapter + '/' + chapter + '_stage6.json')
   ```

   with

   ```python
       document_path = config.stage_path(chapter, 6)
   ```

**Cell 8** (id `8d1aea31`) — currently begins:

```python
# This code finds duplicated items in the _stage6 pipeline and dumps them into a _duplicate_ file

import sys
from pathlib import Path
import json
from collections import Counter, defaultdict

project_root = Path('/work')
sys.path.append(str(project_root))

def main(chapter):
    document_path = Path('/work/data/intermediate/' + chapter + '/' + chapter + '_stage6.json')
    ...
```

Four sites in this cell. Apply:

1. Delete the same two-line `project_root` / `sys.path.append` bootstrap.
2. Add `from utils import config` to the import block.
3. Replace `Path('/work/data/intermediate/' + chapter + '/' + chapter + '_stage6.json')` with `config.stage_path(chapter, 6)`.
4. Replace `Path('/work/data/intermediate/' + chapter + '/' + chapter + '_duplicate_resumen.json')` with `config.INTERMEDIATE_DIR / chapter / f"{chapter}_duplicate_resumen.json"`.
5. Replace `Path('/work/data/intermediate/' + chapter + '/' + chapter + '_duplicate_texto.json')` with `config.INTERMEDIATE_DIR / chapter / f"{chapter}_duplicate_texto.json"`.
6. Replace `Path('/work/data/intermediate/' + chapter + '/' + chapter + '_either_duplicate.json')` with `config.INTERMEDIATE_DIR / chapter / f"{chapter}_either_duplicate.json"`.

(Rationale: the three `_duplicate_*` paths are side-artifact filenames, not
canonical stage outputs, so they shouldn't borrow the `stage_path` helper.
Inlining `INTERMEDIATE_DIR / chapter / f"..."` keeps the config API minimal.
Sprint 04+ can add a `chapter_artifact` helper if a third caller surfaces.)

**Cell 11** (id `949ea377`) — currently contains, inside a function near the end:

```python
    document_path = Path('/work/data/intermediate/' + chapter + '/' + chapter + '_stage6.json')
    ...
    output_path = Path('/work/data/intermediate/' + chapter + '/' + chapter + '_stage7.json')
```

Replace those two lines with:

```python
    document_path = config.stage_path(chapter, 6)
    ...
    output_path = config.stage_path(chapter, 7)
```

Add `from utils import config` to the import block at the top of the cell if
not already present.

**Acceptance**

- `Grep '/work/' src/s07_Filter_duplicates.ipynb` → 0 source hits (output-cell
  hits may remain).
- `git diff src/s07_Filter_duplicates.ipynb` confined to cells 2, 3, 8, 11.
  Specifically: cell 2 fully rewritten (small cell); cells 3, 8, 11 changed
  only inside their respective import blocks and at the named line targets.
- The two `project_root = Path('/work'); sys.path.append(str(project_root))`
  bootstrap pairs are gone (one each from cells 3 and 8 — net **-4 source
  lines** from bootstrap removal).
- JSON parses (`json.load` smoke check).

---

### Task 7 — Add no-`/work/`-in-source regression-guard test

File: `tests/utils/test_notebooks_no_work_literal.py` (new file).

Body:

```python
"""Regression guard: no notebook on the synthetic critical path may carry a
`/work/...` literal in any of its cell `source` arrays.

Output arrays (`outputs`) are exempt — they are regenerated on rerun and
deliberately not migrated by Sprints 02–03.
"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"

# Notebooks Sprints 02–03 are responsible for. Sprint 04 extends this list to
# include s08_Llamaindex_Doc_Creation.ipynb and Generate_OEB_dataset.ipynb.
NOTEBOOKS = [
    "s01_parse_fiebdc.ipynb",
    "s02_split_chapters.ipynb",
    "s03_generate_parametric_combinations.ipynb",
    "s04_evaluate_text_variables.ipynb",
    "s05_evaluate_resumen_texto.ipynb",
    "s06_data_analysis.ipynb",
    "s07_Filter_duplicates.ipynb",
]


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_no_work_literal_in_source_cells(notebook):
    path = SRC_DIR / notebook
    nb = json.loads(path.read_text(encoding="utf-8"))

    offenders = []
    for i, cell in enumerate(nb["cells"]):
        src = "".join(cell.get("source", []))
        if "/work/" in src:
            offenders.append((i, cell.get("id", "?"), src))
    assert not offenders, (
        f"{notebook}: found /work/ literal in cell source arrays at: "
        + ", ".join(f"cell[{i}] id={cid[:8]}" for i, cid, _ in offenders)
    )
```

**Acceptance**

- `pytest tests/utils/test_notebooks_no_work_literal.py -q` exits 0 with 7
  parametrised cases (one per notebook).
- Removing any single Sprint 02 / 03 migration locally re-introduces a failure
  on that notebook (spot-checked manually by the executor on **one** notebook
  before committing — not by reverting and committing).

---

### Task 8 — Verification

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```bash
pytest tests -q
```

Expected: **49 passed** (Sprint 01's 30 + Sprint 02's 12 + 7 new notebook-guard
cases).

Smoke checks (PowerShell-friendly one-liners; substitute `PYTHONPATH=src` for
Bash):

```bash
python -X utf8 -c "import json; [json.load(open(f'src/s0{n}{tail}.ipynb','r',encoding='utf-8')) for n,tail in [(1,'_parse_fiebdc'),(2,'_split_chapters'),(3,'_generate_parametric_combinations'),(4,'_evaluate_text_variables'),(5,'_evaluate_resumen_texto'),(6,'_data_analysis'),(7,'_Filter_duplicates')]]; print('all 7 notebooks parse')"
```

```bash
python -X utf8 -c "
import json
from pathlib import Path
hits = 0
for nb in ['s01_parse_fiebdc','s02_split_chapters','s03_generate_parametric_combinations','s04_evaluate_text_variables','s05_evaluate_resumen_texto','s06_data_analysis','s07_Filter_duplicates']:
    p = Path(f'src/{nb}.ipynb')
    data = json.loads(p.read_text(encoding='utf-8'))
    for c in data['cells']:
        if '/work/' in ''.join(c.get('source', [])): hits += 1
print('source-cell /work/ hits across s01-s07:', hits)
"
```

Expected output: `source-cell /work/ hits across s01-s07: 0`.

End-of-sprint expected `git status`:

```
modified:   src/s02_split_chapters.ipynb
modified:   src/s03_generate_parametric_combinations.ipynb
modified:   src/s04_evaluate_text_variables.ipynb
modified:   src/s05_evaluate_resumen_texto.ipynb
modified:   src/s06_data_analysis.ipynb
modified:   src/s07_Filter_duplicates.ipynb
new file:   tests/utils/test_notebooks_no_work_literal.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_03.md   (this file, already committed)
```

Nothing under `src/synthetic/`, `tests/synthetic/`, `tests/utils/conftest.py`
or `tests/utils/test_config.py`, no other notebook under `src/`, nothing under
`data/` or `configs/` should appear in the diff.

---

### Task 9 — Housekeeping

After Tasks 1–8 pass:

1. Append a Sprint 03 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (newest-first). Cover:
   - 14 source-cell replacements landed across s02–s07.
   - The two `project_root = Path('/work'); sys.path.append(...)` bootstraps
     deleted from `s07_Filter_duplicates.ipynb` cells 3 and 8.
   - pytest count goes from 42 → 49 (one parametrised case per notebook).
   - Decisions confirmed: (a) Path objects passed bare to user functions; no
     `str(...)` wrapping needed (the smoke check + JSON parsing don't exercise
     it, but the same pattern Sprint 02 used in s01 didn't need it either —
     the executor should still note in the retro if `str(...)` was needed
     anywhere). (b) Side-artifact paths in s07 (`_duplicate_*.json`,
     `_either_duplicate.json`) inlined as `config.INTERMEDIATE_DIR / chapter /
     f"..."` instead of a new helper — YAGNI.
   - Next-step recommendation: Sprint 04 — A4 part 3 (s08 +
     `Generate_OEB_dataset` migration). After Sprint 04 lands, the natural
     follow-up is the end-to-end-validation sprint that reruns s01 → s07
     against the existing `data/intermediate/...` and byte-diffs the outputs.

2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Update the "Existing files extended in this branch" block to flip s02–s07
     from "❌ Task A4 part 2" to "✅ Sprint 03". Leave s08 + `Generate_OEB_dataset`
     as the remaining ❌ for Sprint 04.
   - Prepend a new "After Sprint 03 — …" entry to the Sprint History section.

3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). A4
   part 2 closes; A4 part 3 stays open in the backlog for Sprint 04.

---

## Verification runbook

Already inlined in Task 8 above. The two smoke one-liners and the `pytest`
invocation are the gates.

If any notebook fails to round-trip through `json.load`/`json.dumps`, that's a
hard error — check that the executor used `json.dumps(..., indent=1,
ensure_ascii=False)` and wrote with `encoding="utf-8"`. Sprint 02 used exactly
that recipe; Sprint 03 should reuse it.

If the notebook-guard test (Task 7) flags a hit it cannot explain, the
executor should re-run the cell-source dump from the smoke check above to find
the surviving site — typically a `print(f"...{path}...")` debug line that was
overlooked, or a fragment in cell metadata rather than `source`.

---

## References

- [`SPRINT_02.md`](SPRINT_02.md) — predecessor; same template structure, same notebook-edit
  recipe (`json.load` → patch → `json.dumps(..., indent=1)` script).
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file map, design table
  (specifically the "Path-hardcoding" row and the "Existing files extended"
  block).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.5 (what exists vs. what needs building),
  §5 Phase A (A4 task definition).
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 02 retro (closing recommendation pointing here).
- [`../../../src/utils/config.py`](../../../src/utils/config.py) — module the notebooks now consume.

---

## Non-goals reminder

If you find yourself opening `s08_Llamaindex_Doc_Creation.ipynb` or
`Generate_OEB_dataset.ipynb`, **stop**. They each still hardcode `/work/...`;
their migration is Sprint 04's job, and bundling them into Sprint 03 makes the
diff unreviewable. The migration pattern in this sprint is the template.

Similarly, do not edit any `.ipynb_checkpoints/` file. They are Jupyter
auto-saves and will regenerate on next save. Touching them only creates noise.

If you find yourself adding a new helper to `src/utils/config.py`, **stop and
reconsider**. The Sprint 02 surface (`chapter_path` + `stage_path` +
`INTERMEDIATE_DIR`) already covers every site in s02–s07. The three
`_duplicate_*.json` artifacts in s07 are deliberately inlined as
`config.INTERMEDIATE_DIR / chapter / f"..."`; do not add a `chapter_artifact`
helper without a third caller. YAGNI.

If you find yourself running any notebook end-to-end (importing `pandas`,
constructing a `FIEBDCParser`, etc.), **stop**. Static checks only. The
end-to-end validation sprint is a planned follow-up after Sprint 04 lands.
