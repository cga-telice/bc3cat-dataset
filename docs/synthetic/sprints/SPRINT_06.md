# Sprint 06 — End-to-end validation: rerun s01 → Generate_OEB in Docker, diff against in-repo artifacts

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 06                                                                               |
| **Date**       | 2026-05-19 (drafted)                                                             |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | Phase A closing milestone. The validation gate Sprints 02–05 deferred. Not a new backlog task — it's the runtime check that retires the "static-check-only" hedge attached to every Sprint 02–05 retro. |
| **Predecessor** | [`SPRINT_05.md`](SPRINT_05.md) — import-shape cleanup + `Generate_OEB_dataset` bootstrap retirement |
| **Successor**  | Phase B — Task B1 (`layer_l1.py`, real `param_value` mutator bodies) — if Sprint 06 passes clean. If a real semantic discrepancy surfaces, the successor is a root-cause-and-fix sprint scoped to that finding. |

---

## Context

Sprints 02–05 refactored `src/utils/config.py`, the eight `s01–s08` notebooks, `Generate_OEB_dataset.ipynb`, and the import shape of three `src/utils/*.py` modules. Every retro flagged the same gap: *"static-check gate only; end-to-end pipeline rerun pending"*. Sprint 06 closes that gap by running the full pipeline against an isolated data root and diffing the outputs against the in-repo originals.

The validation is gated by the `BC3CAT_DATA_ROOT` env-var override built in Sprint 02 (Task A4 part 1). Setting it to `/work/data_validation` before launching the kernel reroutes `DATA_ROOT` → `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR` to that tree. The in-repo `data/` stays read-only; the produced artifacts land under `data_validation/`.

**Outcome shape:** every diff returns zero / `equal`. If any diff is non-zero, classify (known nondeterminism vs. real regression) and triage before declaring Phase A closed.

---

## Validation surface (audited 2026-05-19)

### In scope — produced by in-repo notebooks, diffable against in-repo originals

| File                                                              | Producer                  | Size      | Diff method                |
|-------------------------------------------------------------------|---------------------------|-----------|----------------------------|
| `data/intermediate/BPA_2024_v2_OEB_mod_utf8.json`                 | s01                       | 18.5 MB   | byte (`filecmp.cmp`)        |
| `data/intermediate/{11 chapters}/{chapter}.json`                  | s02                       | ~10 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_stage3.json`             | s03                       | 387 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_stage4.json`             | s04                       | 786 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_stage5.json`             | s05                       | 250 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_stage6.json`             | s06                       | 201 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_stage7.json`             | s07                       | 225 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_duplicate_resumen.json`  | s07 (side-artifact)        | 1.8 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_duplicate_texto.json`    | s07 (side-artifact)        | 1.8 MB    | byte                       |
| `data/intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json`   | s07 (side-artifact)        | 8.7 MB    | byte                       |
| `data/processed/OBRA CIVIL_texto.pkl`                             | s08                       | 110 MB    | content (LlamaIndex `Document`s; compare `text` + `metadata`, ignore `id_`) |
| `data/processed/OBRA CIVIL_resumen.pkl`                           | s08                       | 75 MB     | content                    |
| `src/OEB_texto.pkl` *(written to `src/`, cwd-relative)*           | Generate_OEB cell 3       | 53 MB     | content (compared against in-repo `data/processed/OEB_texto.pkl`) |

**14 artifacts total.** Aggregate output size ~2 GB; expected wall-clock for a full rerun on the GPU host: ~30–60 min depending on disk speed.

### Out of scope — produced elsewhere, not validatable by this repo

The following live under `data/processed/` but are NOT produced by any notebook in this repo. They are written by `bc3cat-retrieval` (which also reads `OBRA CIVIL_*.pkl` from `data/processed/` to build them). Sprint 06 cannot validate them; the byte-diff against in-repo copies would always succeed (file untouched) so there's no signal to gain.

```
data/processed/OEB_long_norm.parquet              # bc3cat-retrieval feature extraction
data/processed/OEB_short_norm.parquet             # bc3cat-retrieval feature extraction
data/processed/OEB_long_feats.parquet             # bc3cat-retrieval feature extraction
data/processed/OEB_short_feats.parquet            # bc3cat-retrieval feature extraction
data/processed/OEB_features_meta.json             # bc3cat-retrieval feature extraction
data/processed/OEB_texto.json                     # produced by bc3cat-retrieval (Generate_OEB cell 8 only writes resumen.json)
data/processed/OEB_resumen.pkl                    # no in-repo cell produces this; Generate_OEB writes OEB_texto.pkl only
```

These are tracked in this file for clarity. They are explicitly **not** in Sprint 06's gate; cross-repo validation is a separate concern.

### Pre-existing notebook quirks (logged, not fixed here)

- `Generate_OEB_dataset.ipynb` cell 3 writes `OEB_texto.pkl` via bare relative path → file lands at `src/OEB_texto.pkl`, not `data/processed/`. The in-repo `data/processed/OEB_texto.pkl` was presumably moved by hand. Sprint 06 compares against the in-repo copy regardless of where the new run wrote it.
- `Generate_OEB_dataset.ipynb` writes only `OEB_texto.pkl` (cell 3) and `OEB_resumen.json` (cell 8); there is no cell that writes `OEB_resumen.pkl` or `OEB_texto.json` despite both existing under `data/processed/`. **Out of scope** — Sprint 06 doesn't fix the asymmetry, just doesn't try to validate the missing outputs.
- `OEB_resumen.json` contains the LlamaIndex `doc.id_` field (auto-generated UUID per run). Byte-diff would fail by construction. Excluded from the in-scope table above; Sprint 06 doesn't gate on it. If a future sprint wants to validate it, the comparison must strip `id` before diffing.

---

## Mechanism

### Isolation via env-var override

```bash
export BC3CAT_DATA_ROOT=/work/data_validation
```

Routes `config.DATA_ROOT`, `config.RAW_DIR`, `config.INTERMEDIATE_DIR`, `config.PROCESSED_DIR`, `config.LLAMAINDEX_DIR` to subdirs of `data_validation/`. **Verified by reading [`src/utils/config.py`](../../../src/utils/config.py):** the override is read at import time via `os.environ.get("BC3CAT_DATA_ROOT")`. Any kernel that imports `config` after the env var is set picks up the rerouted root.

The in-repo `data/` is untouched: no notebook ever writes there during a Sprint 06 run.

### Seed the validation root

```bash
mkdir -p data_validation/raw
cp data/raw/BPA_2024_v2_OEB_mod_utf8.txt data_validation/raw/
```

s01 reads exactly this one file. All downstream stages read what their predecessor wrote — so as long as s01's input is byte-identical to the in-repo copy, the whole chain is reproducible.

`data_validation/` is gitignored — see Task 1.

### Notebook execution: `papermill`

Inside the Jupyter container, `papermill` runs a notebook headlessly with the kernel of choice, writing executed cells to a separate output file so the in-repo `.ipynb` stays untouched. Install if missing:

```bash
docker compose exec jupyter-pytorch pip install papermill
```

Per-notebook invocation pattern:

```bash
docker compose exec \
    -e BC3CAT_DATA_ROOT=/work/data_validation \
    -w /work/src \
    jupyter-pytorch \
    papermill s01_parse_fiebdc.ipynb /work/data_validation/executed/s01.ipynb
```

The `-w /work/src` working-directory flag is critical — it matches the kernel cwd Sprints 02–05 assumed (`src/`), so `from utils import config` resolves the same way it does in interactive Jupyter sessions.

### Comparison

A single Python script — `scripts/sprint06_validate_e2e.py` (new) — walks the in-scope table and produces a per-row report:

```
[PASS] data/intermediate/BPA_2024_v2_OEB_mod_utf8.json — byte-identical (18,478,991 bytes)
[PASS] data/intermediate/OBRA CIVIL/OBRA CIVIL_stage3.json — byte-identical (387,681,258 bytes)
...
[PASS] data/processed/OBRA CIVIL_texto.pkl — 111,234 docs, all (text, metadata) tuples equal (id_ ignored)
[FAIL] data/intermediate/OBRA CIVIL/OBRA CIVIL_stage4.json — first byte diff at offset 12,345,678
```

JSON / text artifacts: `filecmp.cmp(a, b, shallow=False)`.

Pickle artifacts (LlamaIndex `Document` lists):

```python
import pickle
orig = pickle.load(open(orig_path, "rb"))
new  = pickle.load(open(new_path,  "rb"))
assert len(orig) == len(new)
# Sort both by item_key to defeat list-order nondeterminism (if any)
orig.sort(key=lambda d: d.metadata["item_key"])
new.sort(key=lambda d: d.metadata["item_key"])
for o, n in zip(orig, new):
    assert o.text == n.text
    assert o.metadata == n.metadata    # dicts compare by content, not identity
```

The `Document.id_` field (LlamaIndex auto-UUID) is **ignored by construction** — the comparison reads only `.text` and `.metadata`. The script reports per-pickle: `(num_docs, num_text_mismatches, num_metadata_mismatches)`.

---

## Scope

### In scope

- **Task 1.** Add `data_validation/` to `.gitignore`; create `data_validation/raw/`, `data_validation/executed/` skeleton; seed `data_validation/raw/BPA_2024_v2_OEB_mod_utf8.txt`.
- **Task 2.** Smoke test: rerun s01 alone with `BC3CAT_DATA_ROOT=/work/data_validation`. Verify it writes to `data_validation/intermediate/BPA_2024_v2_OEB_mod_utf8.json` (not `data/intermediate/...`). Byte-diff the new output against the in-repo s01 output. **Goes / no-goes the env-var override** before committing to the long run.
- **Task 3.** Run s02 → s07 in order, each with the same env var and `-w /work/src` cwd. Each notebook reads its predecessor's output from `data_validation/intermediate/` and writes the next stage there.
- **Task 4.** Run s08 (produces `data_validation/processed/OBRA CIVIL_{texto,resumen}.pkl`) and `Generate_OEB_dataset.ipynb` (produces `src/OEB_texto.pkl` + `src/OEB_resumen.json` — the cwd-relative quirk, kept as-is).
- **Task 5.** Write [`scripts/sprint06_validate_e2e.py`](../../../scripts/sprint06_validate_e2e.py) — the differ. 14 rows in the in-scope table; 12 byte-diffs + 2 content-diffs + 1 cwd-relative pickle compare. The script exits 0 if all pass, non-zero with a summary if any fail.
- **Task 6.** Run the differ; capture the report; check in the report text under `docs/synthetic/sprints/SPRINT_06_REPORT.md` (new) so the result is durable.
- **Task 7.** Housekeeping: prepend Sprint 06 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (with the full pass/fail table), append "After Sprint 06 — …" to [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) Sprint History, and update its "Existing files extended" block to record that Sprints 02–05 are now runtime-verified.

### Out of scope (explicit)

- **Validating the `bc3cat-retrieval` artifacts** (`OEB_*.parquet`, `OEB_features_meta.json`, `OEB_texto.json`, `OEB_resumen.pkl`). They are not produced by this repo. Mirroring this validation in the retrieval repo is a separate optional task.
- **Fixing `Generate_OEB_dataset.ipynb` cell 3 / 8 cwd-relative output paths.** Sprint 06 validates the current behavior; a fix would be a behavior change masquerading as a validation. Open as a future cosmetic-cleanup candidate.
- **Validating the other 10 chapters' stage3–stage7 JSONs.** Only OBRA CIVIL has stage3–stage7 outputs in the in-repo `data/intermediate/` — the other 10 chapters stop at s02 because OEB lives only in OBRA CIVIL. Sprint 06 validates exactly what the in-repo data supports.
- **Modifying any notebook or `src/utils/*.py` file.** Sprint 06 is read-only on the pipeline surface; the only writes are to `data_validation/`, `.gitignore`, `scripts/sprint06_validate_e2e.py`, and the docs.
- **Running on the host Python env.** The pipeline needs `pandas`, `pyarrow`, `llama_index`, etc. The Jupyter container has them; the host doesn't (per Sprints 02–05). Docker is the gate.
- **Phase B mutator bodies.** Still stubs from Sprint 01. Not this sprint.

---

## Tasks

### Task 1 — Setup `data_validation/`

```bash
# Append to .gitignore (idempotent — guard with grep first)
grep -q '^data_validation/' .gitignore || echo 'data_validation/' >> .gitignore

mkdir -p data_validation/raw data_validation/executed
cp data/raw/BPA_2024_v2_OEB_mod_utf8.txt data_validation/raw/
```

**Acceptance**

- `data_validation/raw/BPA_2024_v2_OEB_mod_utf8.txt` is byte-identical to `data/raw/BPA_2024_v2_OEB_mod_utf8.txt`.
- `git status` does not show `data_validation/` (gitignored).
- `data_validation/executed/` exists and is empty.

---

### Task 2 — Smoke test: s01 alone

```bash
docker compose up -d jupyter-pytorch
docker compose exec jupyter-pytorch pip install -q papermill

docker compose exec \
    -e BC3CAT_DATA_ROOT=/work/data_validation \
    -w /work/src \
    jupyter-pytorch \
    papermill s01_parse_fiebdc.ipynb /work/data_validation/executed/s01.ipynb
```

**Acceptance**

- `data_validation/intermediate/BPA_2024_v2_OEB_mod_utf8.json` exists, 18.5 MB ± epsilon.
- `data/intermediate/BPA_2024_v2_OEB_mod_utf8.json` is **untouched** (mtime unchanged — capture before/after).
- `filecmp.cmp(data_validation/intermediate/BPA_2024_v2_OEB_mod_utf8.json, data/intermediate/BPA_2024_v2_OEB_mod_utf8.json, shallow=False)` returns `True`.
- If False: classify and STOP. Either the path refactor (Sprints 02–05) silently changed behavior, or there's a pre-existing notebook nondeterminism. Triage before running Tasks 3–4.

---

### Task 3 — Run s02 → s07

Sequential, each notebook in its own `papermill` invocation, each with `BC3CAT_DATA_ROOT=/work/data_validation` and `-w /work/src`:

```bash
for nb in s02_split_chapters s03_generate_parametric_combinations s04_evaluate_text_variables s05_evaluate_resumen_texto s06_data_analysis s07_Filter_duplicates; do
    docker compose exec \
        -e BC3CAT_DATA_ROOT=/work/data_validation \
        -w /work/src \
        jupyter-pytorch \
        papermill "${nb}.ipynb" "/work/data_validation/executed/${nb}.ipynb"
done
```

Expect ~25–40 minutes total: s03 (Cartesian expansion) is the longest; s06 (stats only) is the shortest.

**Acceptance**

- `data_validation/intermediate/OBRA CIVIL/` contains all 9 expected files: `OBRA CIVIL.json`, `OBRA CIVIL_stage{3,4,5,6,7}.json`, `OBRA CIVIL_duplicate_{resumen,texto}.json`, `OBRA CIVIL_either_duplicate.json`.
- `data_validation/intermediate/{other 10 chapters}/{chapter}.json` exists for s02 fan-out.
- All sizes within ±1 byte of the in-repo originals (JSON write order is deterministic in CPython 3.11; this is a strong signal).

---

### Task 4 — Run s08 + Generate_OEB

```bash
docker compose exec \
    -e BC3CAT_DATA_ROOT=/work/data_validation \
    -w /work/src \
    jupyter-pytorch \
    papermill s08_Llamaindex_Doc_Creation.ipynb /work/data_validation/executed/s08.ipynb

docker compose exec \
    -e BC3CAT_DATA_ROOT=/work/data_validation \
    -w /work/src \
    jupyter-pytorch \
    papermill Generate_OEB_dataset.ipynb /work/data_validation/executed/Generate_OEB_dataset.ipynb
```

**Acceptance**

- `data_validation/processed/OBRA CIVIL_texto.pkl` exists, ~110 MB.
- `data_validation/processed/OBRA CIVIL_resumen.pkl` exists, ~75 MB.
- `src/OEB_texto.pkl` exists in the container's `/work/src/` (cwd-relative quirk). Sprint 06's comparison reaches into the container to pull this file before the next `docker compose exec` clobbers it; alternatively, the differ runs *inside* the container as one final `docker compose exec` step (preferred — keeps the script in-context).

---

### Task 5 — Write the differ

File: [`scripts/sprint06_validate_e2e.py`](../../../scripts/sprint06_validate_e2e.py) (new). Sketch:

```python
"""Sprint 06 — diff data_validation/ against in-repo data/.

Walks the in-scope table from SPRINT_06.md. For each row:
- JSON / text: filecmp.cmp shallow=False
- Pickle: load both, sort by item_key, compare (text, metadata) per Document

Exit 0 if every row passes; non-zero with a per-row report otherwise.
Designed to run inside the Jupyter container (paths /work/...).
"""
import filecmp
import pickle
import sys
from pathlib import Path

REPO_ROOT = Path("/work")
ORIG = REPO_ROOT / "data"
NEW = REPO_ROOT / "data_validation"

BYTE_DIFFS = [
    "intermediate/BPA_2024_v2_OEB_mod_utf8.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL.json",
    *(f"intermediate/OBRA CIVIL/OBRA CIVIL_stage{n}.json" for n in (3, 4, 5, 6, 7)),
    "intermediate/OBRA CIVIL/OBRA CIVIL_duplicate_resumen.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_duplicate_texto.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json",
    # s02 outputs for the other 10 chapters
    *(f"intermediate/{ch}/{ch}.json" for ch in (
        "ARQUITECTURA", "CONTROL MANDO Y SEÑALIZACIÓN", "CONTROL Y PRUEBAS",
        "ENERGIA", "GESTIÓN AMBIENTAL", "PRECIOS BÁSICOS",
        "PROTECCIÓN Y SEGURIDAD", "SEGURIDAD Y SALUD",
        "TELECOMUNICACIONES", "VIA",
    )),
]

PICKLE_DIFFS = [
    ("processed/OBRA CIVIL_texto.pkl",   "processed/OBRA CIVIL_texto.pkl"),
    ("processed/OBRA CIVIL_resumen.pkl", "processed/OBRA CIVIL_resumen.pkl"),
    # OEB_texto.pkl: new copy lives at src/OEB_texto.pkl (cwd-relative quirk)
    ("processed/OEB_texto.pkl",          REPO_ROOT / "src" / "OEB_texto.pkl"),  # absolute override
]


def byte_diff(rel: str) -> tuple[bool, str]:
    a, b = ORIG / rel, NEW / rel
    if not b.exists():
        return False, f"missing new artifact: {b}"
    ok = filecmp.cmp(a, b, shallow=False)
    return ok, f"{a.stat().st_size} bytes" if ok else "byte-level mismatch"


def pickle_diff(orig_rel: str, new_rel_or_path) -> tuple[bool, str]:
    a = ORIG / orig_rel
    b = new_rel_or_path if isinstance(new_rel_or_path, Path) else NEW / new_rel_or_path
    if not b.exists():
        return False, f"missing new artifact: {b}"
    o, n = pickle.load(a.open("rb")), pickle.load(b.open("rb"))
    if len(o) != len(n):
        return False, f"length mismatch: orig={len(o)} new={len(n)}"
    o.sort(key=lambda d: d.metadata["item_key"])
    n.sort(key=lambda d: d.metadata["item_key"])
    mismatches = sum(1 for x, y in zip(o, n) if x.text != y.text or x.metadata != y.metadata)
    return mismatches == 0, f"{len(o)} docs, {mismatches} content mismatches"


def main() -> int:
    failures = []
    for rel in BYTE_DIFFS:
        ok, msg = byte_diff(rel)
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {rel} — {msg}")
        if not ok:
            failures.append(rel)
    for orig_rel, new_path in PICKLE_DIFFS:
        ok, msg = pickle_diff(orig_rel, new_path)
        tag = "PASS" if ok else "FAIL"
        print(f"[{tag}] {orig_rel} — {msg}")
        if not ok:
            failures.append(orig_rel)
    print()
    print(f"Total: {len(BYTE_DIFFS) + len(PICKLE_DIFFS)} rows, {len(failures)} failures")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
```

**Acceptance**

- File compiles via `py_compile`.
- No new pytest cases added — Sprint 06 is a one-shot validation, not a permanent regression. The differ's output is the artifact.

---

### Task 6 — Run the differ + capture report

```bash
docker compose exec \
    -w /work \
    jupyter-pytorch \
    python scripts/sprint06_validate_e2e.py | tee docs/synthetic/sprints/SPRINT_06_REPORT.md
```

**Acceptance**

- `SPRINT_06_REPORT.md` exists and contains a per-row pass/fail line for all 14 in-scope rows + a summary line.
- Exit status (last line of `docker compose exec`) is 0 if everything passes.
- If any FAIL: do **not** flip Phase A closed in housekeeping. Instead, summarize the failures in the Sprint 06 RESEARCH_LOG entry, and identify the responsible stage.

---

### Task 7 — Housekeeping

After Tasks 1–6:

1. Prepend a Sprint 06 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover:
   - Setup: `data_validation/` tree + raw seed + gitignore.
   - Execution: papermill on 9 notebooks (s01–s08 + Generate_OEB), under `BC3CAT_DATA_ROOT=/work/data_validation`, total wall-clock.
   - Differ results: 14 rows, X passes, Y failures (cite report file).
   - Decisions:
     (a) Scope narrowed to the 14 in-repo-produced artifacts; the 7 `bc3cat-retrieval`–produced files under `data/processed/` are out of scope (provenance: their producer code lives in the sibling repo).
     (b) Pickle comparison ignores `Document.id_` (LlamaIndex auto-UUID) — compares `.text` + `.metadata` only; sorts by `item_key` before pairwise compare.
     (c) `Generate_OEB_dataset.ipynb` cwd-relative output paths preserved as-is; differ pulls `src/OEB_texto.pkl` from the container working dir, not `data_validation/processed/`.
     (d) Validation is one-shot — no new pytest cases. The durable artifact is the report file checked into `docs/synthetic/sprints/SPRINT_06_REPORT.md`.
   - Next-step recommendation:
     - If all 14 pass: **Phase A is closed.** Next is **Task B1 (`layer_l1.py`)** — real bodies for the 6 L1 `param_value` mutators (`synonym_label`, `num_to_text`, `unit_conversion`, `unit_expansion`, `abbrev_expansion`, `code_expansion`), promoting the Sprint 01 stubs.
     - If any fail: open Sprint 07 scoped to that finding. Categorize: (i) pre-existing nondeterminism (e.g., dict-ordering quirk under a different Python build) → narrow the comparison; (ii) refactor-induced regression → root-cause via `git bisect` across Sprints 02–05.

2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Prepend a new "After Sprint 06 — …" Sprint History entry summarizing the validation.
   - In the "Existing files extended" block, append a one-line note to each Sprint 02–05 row stating "runtime-verified in Sprint 06" (or, if any check failed, note which rows are partially verified pending Sprint 07).

3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Phase A is closing per its existing definition.

---

## Verification runbook

Already inlined per task. The end-of-sprint gate is the differ exit code + the `SPRINT_06_REPORT.md` summary line.

End-of-sprint expected `git status`:

```
modified:   .gitignore                                       # data_validation/ entry added
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_06.md              # this file
new file:   docs/synthetic/sprints/SPRINT_06_REPORT.md       # validation report
new file:   scripts/sprint06_validate_e2e.py                 # the differ
```

Nothing under `src/`, `tests/`, `data/`, `configs/`, `data_validation/` (gitignored), or `.ipynb_checkpoints/` should appear in the diff. Notebooks remain untouched.

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Docker Desktop not running on host | Verified at draft time: `docker --version` returned 27.0.3, `docker info` lists desktop-linux context. If down at execution time, start Docker Desktop first. |
| Image (`quay.io/jupyter/pytorch-notebook:cuda12-python-3.11.8`) not pulled | `docker compose up -d` pulls on first run (5–10 min, ~7 GB). Pre-pull if known cold. |
| Papermill not in the image | `pip install -q papermill` as the first `docker compose exec`. Per-session install — not persisted. |
| Pickle comparison fails because LlamaIndex `Document` subclassed something non-trivial across versions | Comparison is field-level (`text` + `metadata`), not object-equality (`==`). Robust to class identity. If `metadata` dict ordering differs (Python 3.7+ preserves insertion order, but s08 source builds the dict via `**metadata, "type": "..."` spread — order should be deterministic), fall back to per-key comparison. |
| Notebook nondeterminism (e.g., dict iteration order in some Python build) | OBRA CIVIL.json is built by s02 grouping over a sorted set; OBRA CIVIL_stage3.json is `itertools.product` (deterministic). If a byte-diff fails on stage3 specifically, that's the canary — investigate before committing to a hot-fix. |
| s04 / s05 take longer than budgeted | Check `papermill --progress-bar`; if the cell-progress is reasonable, just wait. If a cell wedges, kill and investigate; the previous stage's JSON is already on disk so no work is lost. |
| Generate_OEB_dataset.ipynb cell 1 (`!pip install -q llama-index`) reinstalls llama-index inside the container every time | Already-installed → no-op. ~5 second tax. Acceptable. |
| Failure in any single notebook halts the chain | papermill fails fast and propagates non-zero. Re-run only that notebook (and downstream) once fixed; earlier stages' outputs are durable on disk. |

---

## References

- [`SPRINT_05.md`](SPRINT_05.md) — predecessor; closed the import-shape cleanup. Its retro called out the validation gap.
- [`SPRINT_02.md`](SPRINT_02.md) — added the `BC3CAT_DATA_ROOT` env-var override that makes Sprint 06's isolation possible.
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch context.
- [`../../../docker-compose.yml`](../../../docker-compose.yml) — Jupyter service definition.
- [`../../../src/utils/config.py`](../../../src/utils/config.py) — the env-var override sites.

---

## Non-goals reminder

If you find yourself editing any notebook (s01–s08, Generate_OEB), **stop**. Sprint 06 is read-only on the pipeline; the only writes are `.gitignore`, `scripts/sprint06_validate_e2e.py`, the report file, and the docs.

If you find yourself adding `OEB_long_*.parquet` or `OEB_features_meta.json` to the diff list, **stop**. They're not produced by this repo; the diff would compare unchanged files and tell you nothing.

If you find yourself trying to validate the differ output against an existing report, **stop**. SPRINT_06_REPORT.md is a fresh artifact this sprint produces; there is no prior report to diff against.

If you find yourself running the differ outside the container while pickle/llama-index aren't in the host env, **stop**. Run inside the container via `docker compose exec`.

If a single row fails and you're tempted to "just rerun" — **stop**. Capture the failure first (byte offset, mismatch count), log to RESEARCH_LOG, and triage before rerunning. Determinism is the gate; a passing rerun after a failed run hides the signal.
