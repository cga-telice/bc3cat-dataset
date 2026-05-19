# Sprint 04 — Path refactor: s08 + `Generate_OEB_dataset` notebook migration

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 04                                                                               |
| **Date**       | 2026-05-19 (drafted)                                                             |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | A4 part 3 (s08 + `Generate_OEB_dataset` notebook migration) — see [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md) |
| **Predecessor** | [`SPRINT_03.md`](SPRINT_03.md) — s02–s07 notebook migration                      |
| **Successor**  | End-to-end-validation sprint (s01 → s08 → `Generate_OEB_dataset` rerun + byte-diff), TBD |

---

## Context

Sprint 03 closed A4 part 2 by fanning the s01 migration pattern across `s02_split_chapters.ipynb` → `s07_Filter_duplicates.ipynb`: 14 source-cell `/work/...` literals rewritten to route through `config.INTERMEDIATE_DIR` / `config.chapter_path(...)` / `config.stage_path(...)`, plus the two `project_root = Path('/work'); sys.path.append(...)` bootstraps in s07 cells 3 + 8 deleted as dead code. The notebook-guard test ([`tests/utils/test_notebooks_no_work_literal.py`](../../../tests/utils/test_notebooks_no_work_literal.py)) covers s01–s07 today and pytest is at **49 passed**.

Sprint 04 is **A4 part 3** — the same pattern across the two notebooks that emit the final main-pipeline artifacts but are not on the synthetic critical path:

- [`src/s08_Llamaindex_Doc_Creation.ipynb`](../../../src/s08_Llamaindex_Doc_Creation.ipynb) — turns the s07 `_stage7.json` into LlamaIndex `Document` pickles (`OBRA CIVIL_texto.pkl`, `OBRA CIVIL_resumen.pkl`). Reads `data/intermediate/{chapter}/{chapter}_stage7.json`, writes `data/processed/{chapter}_{texto,resumen}.pkl`.
- [`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb) — filters the OBRA CIVIL pickles to the OEB subset and emits `OEB_*.pkl` + `OEB_resumen.json`. Depends on `from src.utils.data_utils import load_documents`, which is itself a *repo-rooted* import — see the "Repo-rooted import shape" decision below for how Sprint 04 handles this.

After Sprint 04 the regression-guard test extends to cover all eight pipeline notebooks (s01 → s08) plus `Generate_OEB_dataset.ipynb`, and the `/work/` literal is gone from every `source` array in the codebase. The natural follow-up is the **end-to-end-validation sprint**: rerun s01 → s08 → `Generate_OEB_dataset` against the existing `data/intermediate/...` and `data/processed/...` files and byte-diff against the in-repo `OEB_*.parquet` / `OEB_*.pkl` to confirm the refactor is behaviour-preserving across the full main pipeline.

---

## Site survey (audited 2026-05-19)

Cells listed are 0-indexed against `nb["cells"]`. The "hits" column counts substring occurrences of `/work` (with or without trailing slash) — Sprint 04 widens the gate from Sprint 03's `/work/` to bare `/work` so that the `project_root = Path('/work')` bootstrap in `Generate_OEB_dataset.ipynb` cell 2 is caught (Sprint 03's gate would have missed it).

| Notebook                            | Cell idx | id (8-char) | Hits | Nature of sites                                                                    |
|-------------------------------------|---------:|-------------|-----:|------------------------------------------------------------------------------------|
| `s08_Llamaindex_Doc_Creation.ipynb` | 2        | `78375313`  | 3    | One `_stage7.json` read + two `.pkl` writes inside `main(file)`                    |
| `Generate_OEB_dataset.ipynb`        | 2        | `80529a1b`  | 2    | One `/work` bootstrap (`Path('/work')`) + one stale `# Assuming … /work` comment   |
| `Generate_OEB_dataset.ipynb`        | 3        | `3348009c`  | 1    | One `data/processed/OBRA CIVIL_texto.pkl` read                                     |
| `Generate_OEB_dataset.ipynb`        | 4        | `a64e60f9`  | 1    | One `/work/src/OEB_texto.pkl` read (output of cell 3, currently saved as relative) |
| `Generate_OEB_dataset.ipynb`        | 8        | `b9f644bb`  | 1    | One `data/processed/OEB_resumen.pkl` read                                          |

**Total: 8 source-cell `/work*` occurrences across 5 cells in 2 notebooks.** Six are path literals that need rewriting through `config.*`; one is a bootstrap retarget (`Path('/work')` → `config.REPO_ROOT`); one is a stale comment to delete.

Output-cell (`outputs`) `/work` occurrences are deliberately not counted — they will regenerate on the next notebook rerun, matching the s01–s07 policy from Sprints 02–03.

---

## Scope

### In scope

- **`s08_Llamaindex_Doc_Creation.ipynb` cell 2** — add `from utils import config` to the import block; rewrite the three `Path('/work/data/...')` sites inside `main(file)` to route through `config.stage_path(file, 7)` and `config.PROCESSED_DIR / f"{file}_..."`.
- **`Generate_OEB_dataset.ipynb` cell 2** — add `from utils import config` to the import block; **retarget** the existing `project_root = Path('/work'); sys.path.append(str(project_root))` bootstrap to use `config.REPO_ROOT` instead of the `/work` literal; delete the stale `# Assuming your project root is /work, add it to the system path` comment pair. The bootstrap itself **stays** — it is load-bearing for `from src.utils.data_utils import load_documents`, which is a repo-rooted import chain (see decision below).
- **`Generate_OEB_dataset.ipynb` cells 3, 4, 8** — rewrite the four pickle-path literals:
  - cell 3: `'/work/data/processed/OBRA CIVIL_texto.pkl'` → `config.PROCESSED_DIR / "OBRA CIVIL_texto.pkl"`
  - cell 4: `'/work/src/OEB_texto.pkl'` → `"OEB_texto.pkl"` (bare relative — matches the save side in cell 3, which already writes `"OEB_texto.pkl"` relative to the notebook cwd of `src/`)
  - cell 8: `'/work/data/processed/OEB_resumen.pkl'` → `config.PROCESSED_DIR / "OEB_resumen.pkl"`

  Cells 3 and 8 must also import `config`; the most natural pattern is to add `from utils import config` inside cell 2 (the shared imports cell) where it already needs adding for the bootstrap retarget, so cells 3 + 8 inherit it transitively through notebook globals. **Do not** sprinkle `from utils import config` into cells 3, 4, 8 individually — that's redundant with cell 2's import and would clutter the diff.

- **Regression-guard test extension.** [`tests/utils/test_notebooks_no_work_literal.py`](../../../tests/utils/test_notebooks_no_work_literal.py) is the Sprint 03 deliverable. Sprint 04:
  - Adds `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb` to the `NOTEBOOKS` list (parametrised: 9 cases total).
  - **Widens the literal match** from `"/work/"` to `"/work"` so the bootstrap `Path('/work')` (no trailing slash) is also caught. Verified by hand that s01–s07 stay green under the stricter rule (none of them contains a bare `/work` token after Sprint 03 — the deleted s07 bootstraps were the only such occurrences).

- **Housekeeping.** Append Sprint 04 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md); prepend "After Sprint 04 — …" to [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s Sprint History; flip s08 + `Generate_OEB_dataset` from ❌ to ✅ in the "Existing files extended" block.

### Out of scope (explicit)

- **`src/utils/{data_utils,index_classes,evaluation}.py`'s repo-rooted import shape.** These three modules currently do `from src.utils.{custom_types,text_processing,config}` — *absolute* imports that require `REPO_ROOT` (i.e. the parent of `src/`) to be on `sys.path` rather than `src/` itself. This is why `Generate_OEB_dataset.ipynb` cell 2 keeps a `sys.path.append(REPO_ROOT)` bootstrap after Sprint 04. **Cleaning this up** — switching the four `.py` files to relative imports (`from .custom_types`, etc.) so a notebook with cwd `src/` no longer needs the bootstrap — is a self-contained follow-up that does not affect the `/work`-literal gate. Listed for Sprint 05 (or named "Sprint 04.5"); not touched here. The diff would also span [`src/utils/index_classes.py`](../../../src/utils/index_classes.py) → [`src/utils/data_utils.py`](../../../src/utils/data_utils.py) → [`src/utils/evaluation.py`](../../../src/utils/evaluation.py) and possibly any consumer in `bc3cat-retrieval` (cross-repo coupling check needed before changing).

- **End-to-end pipeline rerun.** Sprint 04 is **static-check only**, same gate as Sprints 02 + 03. The end-to-end-validation sprint that reruns s01 → s08 → `Generate_OEB_dataset` against `data/intermediate/...` and byte-diffs `data/processed/OEB_*.parquet` / `*.pkl` is the natural follow-up after Sprint 04 (or after the import-shape cleanup, whichever lands first). It requires Docker / a configured Python env with `pandas` / `pyarrow` / `llama_index` / etc., which the static gate does not.

- **`.ipynb_checkpoints/`.** Both [`src/.ipynb_checkpoints/`](../../../src/.ipynb_checkpoints) and [`src/utils/.ipynb_checkpoints/`](../../../src/utils/.ipynb_checkpoints) carry stale `/work/` literals (visible in `Grep '/work/' src/utils/.ipynb_checkpoints/`). They are Jupyter auto-saves that regenerate on next save. **Do not touch.** Same rule as Sprints 02 + 03.

- **Output-cell `/work/` strings.** The `outputs` arrays of touched cells (and the untouched cells) still carry `/work/` print-statement remnants. They regenerate on rerun. Editing them is cosmetic-only and matches the s01–s07 policy.

- **Phase B mutator bodies.** Still stubs from Sprint 01. Not this sprint.

- **Renaming `OBRA CIVIL` to something without an internal space.** `config.chapter_path("OBRA CIVIL")` and the in-repo `OBRA CIVIL_texto.pkl` filenames stay as-is (Sprint 02 verified the space round-trips through both helpers).

---

## Tasks

The migration uses the same `json.load` → patch the `source` array → `json.dumps(..., indent=1, ensure_ascii=False)` technique Sprints 02 + 03 adopted. Apply each notebook's edits in **one** load/write cycle so the JSON pretty-print is stable.

### Task 1 — Migrate `s08_Llamaindex_Doc_Creation.ipynb`

File: [`src/s08_Llamaindex_Doc_Creation.ipynb`](../../../src/s08_Llamaindex_Doc_Creation.ipynb).

**Cell 2** (id `78375313`) — currently begins:

```python
from pathlib import Path
import json
import pickle
from llama_index.core import Document

def main(file):

    # Load the JSON data

    json_file_path = Path('/work/data/intermediate/' + file + '/' + file + '_stage7.json')
    save_path_texto = Path('/work/data/processed/' + file + '_texto.pkl')
    save_path_resumen = Path('/work/data/processed/' + file + '_resumen.pkl')
    ...
```

Apply four surgical edits inside the cell's `source` array:

1. Add `from utils import config` to the import block (right after `from llama_index.core import Document`).
2. Replace
   ```python
       json_file_path = Path('/work/data/intermediate/' + file + '/' + file + '_stage7.json')
   ```
   with
   ```python
       json_file_path = config.stage_path(file, 7)
   ```
3. Replace
   ```python
       save_path_texto = Path('/work/data/processed/' + file + '_texto.pkl')
   ```
   with
   ```python
       save_path_texto = config.PROCESSED_DIR / f"{file}_texto.pkl"
   ```
4. Replace
   ```python
       save_path_resumen = Path('/work/data/processed/' + file + '_resumen.pkl')
   ```
   with
   ```python
       save_path_resumen = config.PROCESSED_DIR / f"{file}_resumen.pkl"
   ```

Leave `from pathlib import Path` in the import block — it's now unused inside `main(file)` after the three rewrites, but pruning unused imports is cosmetic-only and out of scope (matches the Sprint 03 policy on s07 cells 3 + 8, which also left `from pathlib import Path` in place).

**Acceptance**

- `Grep '/work' src/s08_Llamaindex_Doc_Creation.ipynb` → 0 source-array hits (output arrays may remain).
- `git diff src/s08_Llamaindex_Doc_Creation.ipynb` confined to cell 2.
- JSON parses (`json.load` smoke check).

---

### Task 2 — Migrate `Generate_OEB_dataset.ipynb`

File: [`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb). Four cells touched in a single load/write cycle.

**Cell 2** (id `80529a1b`) — currently:

```python
import os
import sys
from pathlib import Path
import gc
import json
import pickle
from llama_index.core import Document

# Add parent directory to Python path
# Assuming your project root is `/work`, add it to the system path
project_root = Path('/work')
sys.path.append(str(project_root))

from src.utils.data_utils import load_documents
```

Apply:

1. Add `from utils import config` immediately after `from llama_index.core import Document` (sits beside the other framework imports, before the bootstrap block).
2. Delete the two-line comment block
   ```python
   # Add parent directory to Python path
   # Assuming your project root is `/work`, add it to the system path
   ```
   (the bootstrap retarget is self-explanatory through `config.REPO_ROOT`; the stale comments contain a `/work` literal that the regression test will flag).
3. Replace `project_root = Path('/work')` with `project_root = config.REPO_ROOT`.
4. **Keep** the `sys.path.append(str(project_root))` line. Repo-rooted imports in `src/utils/{data_utils,index_classes,evaluation}.py` mean `REPO_ROOT` (not `src/`) must be on `sys.path` for the `from src.utils.data_utils import load_documents` import on the next line to resolve. The bootstrap's purpose is unchanged — only its target literal is.
5. **Keep** `from src.utils.data_utils import load_documents` exactly as-is. The repo-rooted import shape is the Sprint 05 problem (see "Out of scope" above).

Resulting cell:

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

**Cell 3** (id `3348009c`) — replace the first line

```python
documents_path = '/work/data/processed/OBRA CIVIL_texto.pkl'
```

with

```python
documents_path = config.PROCESSED_DIR / "OBRA CIVIL_texto.pkl"
```

Leave the rest of the cell unchanged. Do **not** add `from utils import config` to this cell — it inherits from cell 2's import via notebook globals.

**Cell 4** (id `a64e60f9`) — replace the single-line cell

```python
doc=load_documents('/work/src/OEB_texto.pkl')
```

with

```python
doc=load_documents("OEB_texto.pkl")
```

Rationale: cell 3 already saves the filtered output as the relative path `"OEB_texto.pkl"` (resolved against the notebook cwd of `src/` on every platform). Loading it back via a bare relative path is the symmetric YAGNI choice — no new `config.SRC_DIR` helper, no `config.REPO_ROOT / "src" / ...` boilerplate, no surprise about which directory the file lives in (it lives where cell 3 just wrote it).

**Cell 8** (id `b9f644bb`) — replace the first line

```python
documents_path = '/work/data/processed/OEB_resumen.pkl'
```

with

```python
documents_path = config.PROCESSED_DIR / "OEB_resumen.pkl"
```

Leave the rest of the cell unchanged.

**Acceptance**

- `Grep '/work' src/Generate_OEB_dataset.ipynb` → 0 source-array hits (output arrays may remain).
- `git diff src/Generate_OEB_dataset.ipynb` confined to cells 2, 3, 4, 8. No metadata churn.
- JSON parses (`json.load` smoke check).
- The bootstrap line `sys.path.append(str(project_root))` is still present in cell 2 (verifies the bootstrap was retargeted, not removed).
- `from src.utils.data_utils import load_documents` still present in cell 2 (verifies the repo-rooted import chain is intact).

---

### Task 3 — Extend the notebook `/work`-literal regression guard

File: [`tests/utils/test_notebooks_no_work_literal.py`](../../../tests/utils/test_notebooks_no_work_literal.py).

Two edits:

1. Append two entries to the `NOTEBOOKS` list:
   ```python
       "s08_Llamaindex_Doc_Creation.ipynb",
       "Generate_OEB_dataset.ipynb",
   ```
2. Tighten the literal check from `/work/` to bare `/work`:
   ```python
   -        if "/work/" in src:
   +        if "/work" in src:
   ```

Update the module docstring's first paragraph to drop the trailing-slash specificity (e.g. "no notebook on the synthetic critical path may carry a `/work` literal in any of its cell `source` arrays").

**Acceptance**

- `pytest tests/utils/test_notebooks_no_work_literal.py -q` exits 0 with **9 parametrised cases** (was 7 after Sprint 03; +2 for s08 + Generate_OEB).
- Spot-check by manually reintroducing `Path('/work')` in one cell of `Generate_OEB_dataset.ipynb` locally (without committing): the corresponding parametrised case fails. Revert before continuing.

---

### Task 4 — Verification

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```bash
pytest tests -q
```

Expected: **51 passed** (Sprint 01's 30 + Sprint 02's 12 + Sprint 03's 7 + 2 new notebook-guard cases for s08 + Generate_OEB).

Smoke checks (PowerShell-friendly one-liners):

```bash
python -X utf8 -c "import json; [json.load(open(f'src/{nb}.ipynb','r',encoding='utf-8')) for nb in ['s01_parse_fiebdc','s02_split_chapters','s03_generate_parametric_combinations','s04_evaluate_text_variables','s05_evaluate_resumen_texto','s06_data_analysis','s07_Filter_duplicates','s08_Llamaindex_Doc_Creation','Generate_OEB_dataset']]; print('all 9 notebooks parse')"
```

```bash
python -X utf8 -c "
import json
from pathlib import Path
hits = 0
for nb in ['s01_parse_fiebdc','s02_split_chapters','s03_generate_parametric_combinations','s04_evaluate_text_variables','s05_evaluate_resumen_texto','s06_data_analysis','s07_Filter_duplicates','s08_Llamaindex_Doc_Creation','Generate_OEB_dataset']:
    p = Path(f'src/{nb}.ipynb')
    data = json.loads(p.read_text(encoding='utf-8'))
    for c in data['cells']:
        if '/work' in ''.join(c.get('source', [])): hits += 1
print('source-cell /work hits across s01-s08 + Generate_OEB:', hits)
"
```

Expected output: `source-cell /work hits across s01-s08 + Generate_OEB: 0`.

End-of-sprint expected `git status`:

```
modified:   src/s08_Llamaindex_Doc_Creation.ipynb
modified:   src/Generate_OEB_dataset.ipynb
modified:   tests/utils/test_notebooks_no_work_literal.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_04.md   (this file, may be bundled with the execution commit per the Sprint 03 precedent)
```

Nothing under `src/synthetic/`, `tests/synthetic/`, `tests/utils/conftest.py`, `tests/utils/test_config.py`, any of s01–s07 under `src/`, anything under `data/` or `configs/`, or anything under `src/utils/*.py` should appear in the diff.

---

### Task 5 — Housekeeping

After Tasks 1–4 pass:

1. Append a Sprint 04 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (newest-first). Cover:
   - 6 source-cell path-literal rewrites + 1 bootstrap retarget + 1 stale-comment deletion across s08 cell 2 and Generate_OEB cells 2/3/4/8.
   - The regression-guard literal widened from `/work/` to `/work` (decision: catches `Path('/work')` while staying green on s01–s07).
   - pytest count goes from 49 → 51 (+2 new notebook-guard cases).
   - Decisions confirmed: (a) Generate_OEB cell 2 bootstrap **retargeted, not deleted** — load-bearing for `from src.utils.data_utils import load_documents` because the repo-rooted import shape inside `src/utils/*.py` is wider than this sprint's scope. (b) Cell 4's `/work/src/OEB_texto.pkl` collapsed to a bare relative `"OEB_texto.pkl"` matching the save side in cell 3 — no `config.SRC_DIR` helper introduced (YAGNI). (c) Single `from utils import config` per notebook in the shared imports cell; cells 3 + 4 + 8 of Generate_OEB inherit transitively, avoiding redundant imports.
   - Next-step recommendation: the "Sprint 05 / 04.5" import-shape cleanup of `src/utils/{data_utils,index_classes,evaluation}.py` (swap `from src.utils.X` → relative `from .X`, then the Generate_OEB cell 2 bootstrap can finally retire). After that, the end-to-end-validation sprint.

2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Update the "Existing files extended in this branch" block to flip `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb` from "❌ Task A4 part 3" to "✅ Sprint 04". A4 part 3 closes; the import-shape cleanup is a new follow-up bullet, not an A-series task.
   - Prepend a new "After Sprint 04 — …" entry to the Sprint History section.

3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Task A4 closes in full with this sprint; the import-shape follow-up is a refinement to the file map, not the backlog.

---

## Verification runbook

Already inlined in Task 4 above. The two smoke one-liners and the `pytest` invocation are the gates.

If any notebook fails to round-trip through `json.load` / `json.dumps`, that is a hard error — confirm the executor used `json.dumps(..., indent=1, ensure_ascii=False)` and wrote bytes (`Path.write_bytes(text.encode("utf-8") + b"\n")`) rather than text-mode (`write_text` would CRLF-corrupt the LF in-repo style on Windows; Sprint 03 confirmed this).

If the regression-guard test (Task 3) flags a hit it cannot explain, dump the surviving site:

```bash
python -X utf8 -c "
import json
for nb in ['s08_Llamaindex_Doc_Creation','Generate_OEB_dataset']:
    data = json.load(open(f'src/{nb}.ipynb','r',encoding='utf-8'))
    for i, c in enumerate(data['cells']):
        for line in c.get('source', []):
            if '/work' in line:
                print(f'{nb} cell[{i}]: {line!r}')
"
```

Typical culprit: a comment that snuck through the deletion in cell 2 of Generate_OEB, or a `print(f'... /work ...')` debug line that was overlooked.

---

## References

- [`SPRINT_03.md`](SPRINT_03.md) — predecessor; same template structure, same notebook-edit recipe.
- [`SPRINT_02.md`](SPRINT_02.md) — sets the migration pattern (one helper script, `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)`).
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context, file map ("Existing files extended" block).
- [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) — §3.5 (what exists vs. what needs building), §5 Phase A (A4 task definition).
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 03 retro (closing recommendation pointing here).
- [`../../../src/utils/config.py`](../../../src/utils/config.py) — module the two notebooks consume.
- [`../../../src/utils/data_utils.py`](../../../src/utils/data_utils.py) — the `load_documents(...)` callee; uses a repo-rooted import. Sprint 05 candidate.

---

## Non-goals reminder

If you find yourself opening any of `s01_parse_fiebdc.ipynb` … `s07_Filter_duplicates.ipynb`, **stop**. They were migrated in Sprints 02 + 03 and are not in scope for Sprint 04. The regression guard (Task 3) already covers them.

If you find yourself opening `src/utils/data_utils.py`, `src/utils/index_classes.py`, or `src/utils/evaluation.py` and rewriting `from src.utils.X` to `from .X`, **stop and reconsider**. That is the Sprint 05 / 04.5 task. Doing it here means the Sprint 04 diff also has to touch the [`bc3cat-retrieval`](../../../../bc3cat-retrieval) repo's consumers of those modules (cross-repo coupling check), and the present sprint loses its narrow A4-part-3 scope.

If you find yourself adding a new helper to `src/utils/config.py` (e.g. `SRC_DIR`, `pickle_path(...)`), **stop**. Sprint 04's site survey covers six file references + one bootstrap target + one comment — the existing surface (`PROCESSED_DIR`, `stage_path`, `REPO_ROOT`) handles all of them. The bare-relative `"OEB_texto.pkl"` in cell 4 is a deliberate symmetric choice, not a place to grow the API.

If you find yourself running any notebook end-to-end (importing `pandas` / `llama_index` / constructing a `Document`, etc.), **stop**. Static checks only. The end-to-end-validation sprint is the planned follow-up after A4 closes and the import-shape cleanup lands.

Similarly, do not edit any `.ipynb_checkpoints/` file. They are Jupyter auto-saves and will regenerate on next save. Touching them only creates noise.
