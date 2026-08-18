# Sprint 6.5 — Cleanup fixes from Sprint 06 findings

| Field          | Value                                                                            |
|----------------|----------------------------------------------------------------------------------|
| **Sprint**     | 6.5 (patch sprint)                                                               |
| **Date**       | 2026-05-19                                                                       |
| **Branch**     | `synthetic`                                                                      |
| **Backlog IDs** | Two low-priority quality-of-life cleanups surfaced by Sprint 06's validation. Logged in [`SPRINT_06_REPORT.md`](SPRINT_06_REPORT.md) and the [Sprint 06 retro](../RESEARCH_LOG.md). Not in the original Phase A or Phase B backlogs. |
| **Predecessor** | [`SPRINT_06.md`](SPRINT_06.md) — end-to-end validation                          |
| **Successor**  | Sprint 07 — Phase B Task B1 (`layer_l1.py` real bodies for the 6 L1 `param_value` mutators) |

---

## Context

Sprint 06 closed Phase A with 24/24 PASS but surfaced two pre-existing bugs that the differ had to hedge around:

1. **`OBRA CIVIL_either_duplicate.json` set-iteration nondeterminism.** [`src/s07_Filter_duplicates.ipynb`](../../../src/s07_Filter_duplicates.ipynb) cell 8 (id `8d1aea31`) iterates `either_duplicate_keys = set()` to build the output dict. Python set iteration order is randomized per-process via PYTHONHASHSEED, so the JSON key order changes run-to-run. Content is identical (15,294 keys, 0 value mismatches). Sprint 06's differ classified the row as JSON content-diff to avoid a false-negative failure.
2. **`Generate_OEB_dataset.ipynb` cell 8 reads `OEB_resumen.pkl` that no in-repo cell writes.** [`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb) cell 3 (id `3348009c`) writes `OEB_texto.pkl` cwd-relative; there is no symmetric writer for resumen. Cell 8 (id `b9f644bb`) reads `config.PROCESSED_DIR / "OEB_resumen.pkl"` and errors with `TypeError: 'NoneType' object is not iterable` because `load_documents` returns `None` on missing file. The in-repo `data/processed/OEB_resumen.pkl` (35 MB) was produced by some prior process outside the in-repo notebook chain.

Sprint 6.5 fixes both before Phase B starts so the foundation is fully clean.

**Coupling check (pre-execution):** [`bc3cat-retrieval`](../../../../bc3cat-retrieval) consumes `OEB_resumen.json`, not `.pkl`. The pickle is dataset-internal — no sibling-repo coupling. Verified by `grep -rn 'OEB_resumen' bc3cat-retrieval/src/` returning only `.json` hits in `cross_encoder.ipynb` and `hybrid.ipynb`.

---

## Scope

### In scope

- **Fix 1 — s07 sorted iteration.** [`src/s07_Filter_duplicates.ipynb`](../../../src/s07_Filter_duplicates.ipynb) cell 8: `for key in either_duplicate_keys:` → `for key in sorted(either_duplicate_keys):`. One-token change inside the cell's source array. Restores byte-determinism across runs. The other two duplicate side-artifacts (`_duplicate_resumen.json`, `_duplicate_texto.json`) are already deterministic (iterate `defaultdict` instances → insertion-ordered).
- **Fix 2 — new `OEB_resumen.pkl` writer cell.** Insert a new cell at index 8 of [`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb), mirroring cell 3's filter-and-pickle pattern but for resumen. Writes to `config.PROCESSED_DIR / "OEB_resumen.pkl"` — matches the read path of cell 9 (the existing cell 8, now shifted by one). Cell count goes 10 → 11.
- **Fix 3 — differ row.** Add `processed/OEB_resumen.pkl` row to `PICKLE_DIFFS` in [`scripts/sprint06_validate_e2e.py`](../../../scripts/sprint06_validate_e2e.py). Total rows go 24 → 25.
- **Validation.** Clear `data_validation/intermediate/*` and `data_validation/processed/*`, rerun s01 → Generate_OEB inside the `bc3cat-sprint06` container, run the updated differ, expect **25/25 PASS** (allowing `_either_duplicate.json` to remain content-diff because the in-repo Jan-12 file predates the sort fix). Capture report at [`SPRINT_065_REPORT.md`](SPRINT_065_REPORT.md). Two-run determinism gate: re-run s07 a second time, byte-diff its `_either_duplicate.json` against the first run — should now be byte-identical.
- **Housekeeping.** Prepend Sprint 6.5 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) and "After Sprint 6.5 — …" to [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md).

### Out of scope (explicit)

- **Cell 3 cwd-relative path.** Sprint 04 explicitly chose to keep `OEB_texto.pkl` cwd-relative to match cell 4's cwd-relative load. Reversing that decision is out of scope; the new cell at index 8 deliberately writes to `config.PROCESSED_DIR` instead. The asymmetry is preserved on purpose.
- **Regenerating `data/intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json`.** Keep `data/` frozen at the Jan-12 reference state. The differ continues to treat this row as JSON content-diff, with the post-fix bytes-differ message updated to reflect "in-repo Jan-12 reference predates sort fix" rather than "set-iteration order".
- **Mirroring fixes in `bc3cat-retrieval`.** Sibling repo doesn't consume `OEB_resumen.pkl` (only `.json`). No cross-repo work needed.
- **Pytest gate.** Sprint 6.5 is a notebook + script + docs change; validation is the differ rerun. The 54 baseline test count from Sprint 05 stays unchanged.
- **Updating the in-repo `data/processed/OEB_resumen.pkl`.** Leave the existing 35 MB file alone — the differ verifies content-equivalence; if a content diff surfaces, log finding for triage rather than overwriting the reference.
- **Phase B mutator bodies.** Still stubs from Sprint 01. Not this sprint.

---

## Tasks

### Task 1 — Pre-execution coupling check (sibling repo)

```bash
grep -rn 'OEB_resumen' D:/Users/cesar/Dev/Phd/bc3cat-retrieval/ --include='*.py' --include='*.ipynb' | head
```

**Acceptance:** zero `.pkl` hits in the sibling repo (only `.json` references in `cross_encoder.ipynb` / `hybrid.ipynb`). If any `.pkl` hit surfaces, halt and surface it for triage before applying Fix 2.

### Task 2 — Fix 1 (s07 sorted iteration)

[`src/s07_Filter_duplicates.ipynb`](../../../src/s07_Filter_duplicates.ipynb) cell 8 (id `8d1aea31`). Single-token change via `json.load` → patch source array → `json.dumps(indent=1, ensure_ascii=False)` → `Path.write_bytes(text.encode("utf-8") + b"\n")`. Sprint 03/04/05 recipe.

```python
-    for key in either_duplicate_keys:
+    for key in sorted(either_duplicate_keys):
```

**Acceptance:** `git diff --numstat src/s07_Filter_duplicates.ipynb` shows `+1/-1`. The patched cell 8 contains `for key in sorted(either_duplicate_keys):`.

### Task 3 — Fix 2 (Generate_OEB new writer cell)

[`src/Generate_OEB_dataset.ipynb`](../../../src/Generate_OEB_dataset.ipynb), insert new code cell at index 8 between current cell 7 (`f_docs` inspection) and current cell 8 (JSON producer). The new cell:

```python
documents_path = config.PROCESSED_DIR / "OBRA CIVIL_resumen.pkl"
documents = load_documents(documents_path)
# Filter documents where 'item_key' starts with 'OEB'
filtered_docs = [doc for doc in documents if doc.metadata.get("item_key", "").startswith("OEB")]

# Save filtered documents to PROCESSED_DIR (matches the read path in the next cell)
output_path = config.PROCESSED_DIR / "OEB_resumen.pkl"
with open(output_path, "wb") as f:
    pickle.dump(filtered_docs, f)

print(f"Saved {len(filtered_docs)} documents to {output_path}")
```

Cell metadata: `cell_type: "code"`, fresh `id` (UUID4 hex like the existing cells), empty `outputs`, `execution_count: None`. Patched via the same `json.load` → `cells.insert(8, new_cell)` → `json.dumps` cycle.

**Acceptance:** cell count goes 10 → 11. New cell at index 8; existing cell that was at index 8 (id `b9f644bb`) shifts to index 9 with identical content. `git diff --numstat src/Generate_OEB_dataset.ipynb` shows roughly `+13/-1` (new cell added; no other lines changed).

### Task 4 — Fix 3 (differ row)

[`scripts/sprint06_validate_e2e.py`](../../../scripts/sprint06_validate_e2e.py): add `("processed/OEB_resumen.pkl", NEW_ROOT / "processed" / "OEB_resumen.pkl")` to the `PICKLE_DIFFS` list with a one-line comment marking the Sprint 6.5 addition.

**Acceptance:** `py_compile.compile(...)` succeeds; `PICKLE_DIFFS` has 4 entries; differ-level total rows = 25.

### Task 5 — Validation rerun

Clear and rerun:

```bash
docker ps --filter name=bc3cat-sprint06   # confirm container is up
rm -rf data_validation/intermediate/* data_validation/processed/* data_validation/executed/*
mkdir -p data_validation/intermediate data_validation/processed data_validation/executed

# Reuse the Sprint 06 run script
/tmp/sprint06_run.sh 2>&1 | tee data_validation/executed/run.log
```

Then the differ:

```bash
MSYS_NO_PATHCONV=1 docker exec -w /work bc3cat-sprint06 \
    python scripts/sprint06_validate_e2e.py \
    | tee docs/synthetic/sprints/SPRINT_065_REPORT.md
```

Then the determinism gate for Fix 1:

```bash
cp "data_validation/intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json" /tmp/either_run1.json
MSYS_NO_PATHCONV=1 docker exec -e BC3CAT_DATA_ROOT=/work/data_validation -w /work/src bc3cat-sprint06 \
    papermill s07_Filter_duplicates.ipynb /work/data_validation/executed/s07_rerun.ipynb
cmp /tmp/either_run1.json "data_validation/intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json" \
    && echo "FIX 1 DETERMINISM GATE: byte-identical across runs"
```

**Acceptance:**
- Differ reports **25/25 PASS, exit 0**.
- `_either_duplicate.json` row reports the same "bytes differ, content identical, 15,294 entries" message (the in-repo Jan-12 reference still predates the sort fix — content-diff bucket continues to handle this honestly).
- Determinism gate: two consecutive s07 runs produce byte-identical `_either_duplicate.json`. This is the proof Fix 1 worked.
- Generate_OEB runs all 11 cells without errors. `data_validation/processed/OEB_resumen.pkl` exists, ~35 MB, 47,514 docs.
- If `OEB_resumen.pkl` content-diff fails (i.e., new file's content differs from the in-repo 35 MB reference), the row FAILs → triage: is the in-repo file from a different filtering rule? Decision in the retro; do not overwrite the in-repo file.

### Task 6 — Housekeeping

After Tasks 1–5 pass:

1. Prepend a Sprint 6.5 entry to [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) (newest-first). Cover the two fixes, the differ update, the validation result, and the next-step recommendation pointing to Sprint 07 (Phase B Task B1).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md), prepend "After Sprint 6.5 — …" Sprint History entry; in "Existing files extended" append parentheticals to the [s07](../../../src/s07_Filter_duplicates.ipynb) and [Generate_OEB](../../../src/Generate_OEB_dataset.ipynb) rows noting Sprint 6.5's contribution.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md). Phase A stays closed; Sprint 6.5 is a patch sprint that doesn't shift backlog items.

---

## Verification runbook

Inlined in Tasks 1–5 above. End-of-sprint gates: differ 25/25 PASS, two-run determinism on `_either_duplicate.json`, no in-repo `data/` writes.

End-of-sprint expected `git status` (excluding pre-existing untracked noise):

```
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   scripts/sprint06_validate_e2e.py
modified:   src/Generate_OEB_dataset.ipynb
modified:   src/s07_Filter_duplicates.ipynb
new file:   docs/synthetic/sprints/SPRINT_065.md                # this file
new file:   docs/synthetic/sprints/SPRINT_065_REPORT.md         # validation report
```

Nothing under `src/utils/`, `tests/`, `data/`, `configs/`, `data_validation/` (gitignored), or `.ipynb_checkpoints/`. Pipeline notebooks s01–s06, s08, and Generate_OEB cells 2/3 stay untouched.

---

## References

- [`SPRINT_06.md`](SPRINT_06.md) — predecessor; surfaced both bugs.
- [`SPRINT_06_REPORT.md`](SPRINT_06_REPORT.md) — 24/24 PASS report where `_either_duplicate.json` is logged as JSON content-diff and `OEB_resumen.pkl` is out of scope.
- [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md) — Sprint 06 retro pointing here.
- [`SPRINT_04.md`](SPRINT_04.md) — established cell 3 cwd-relative policy that Sprint 6.5 preserves.
- [`SPRINT_03.md`](SPRINT_03.md) — notebook `json.load`-cycle recipe + LF discipline reused here.
