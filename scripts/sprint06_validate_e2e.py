"""Sprint 06 — End-to-end validation differ.

Walks the in-scope artifact table from docs/synthetic/sprints/SPRINT_06.md.
For each row:
  - JSON / text: filecmp.cmp(..., shallow=False) — byte-level
  - Pickle (LlamaIndex Document lists): load, sort by item_key, compare
    (text, metadata) pairwise — ignores Document.id_ (auto-generated UUID)

Designed to run inside the Jupyter container where /work is the repo root
and llama_index is installed. Compares data_validation/ outputs against
in-repo data/ originals.

Exit 0 if every row passes; non-zero with a per-row report otherwise.
The stdout is intended to be tee'd into docs/synthetic/sprints/SPRINT_06_REPORT.md.
"""
from __future__ import annotations

import filecmp
import pickle
import sys
from pathlib import Path

REPO_ROOT = Path("/work")
ORIG_ROOT = REPO_ROOT / "data"
NEW_ROOT = REPO_ROOT / "data_validation"

# Byte-level diffs: relative-to-data-root paths.
BYTE_DIFFS: list[str] = [
    # s01 output
    "intermediate/BPA_2024_v2_OEB_mod_utf8.json",
    # s01 cell-1 encoding conversion side-output (lives under raw/)
    "raw/BPA_2024_v2_OEB_mod_utf8.txt",
    # s02 outputs (11 chapters)
    "intermediate/ARQUITECTURA/ARQUITECTURA.json",
    "intermediate/CONTROL MANDO Y SEÑALIZACIÓN/CONTROL MANDO Y SEÑALIZACIÓN.json",
    "intermediate/CONTROL Y PRUEBAS/CONTROL Y PRUEBAS.json",
    "intermediate/ENERGIA/ENERGIA.json",
    "intermediate/GESTIÓN AMBIENTAL/GESTIÓN AMBIENTAL.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL.json",
    "intermediate/PRECIOS BÁSICOS/PRECIOS BÁSICOS.json",
    "intermediate/PROTECCIÓN Y SEGURIDAD/PROTECCIÓN Y SEGURIDAD.json",
    "intermediate/SEGURIDAD Y SALUD/SEGURIDAD Y SALUD.json",
    "intermediate/TELECOMUNICACIONES/TELECOMUNICACIONES.json",
    "intermediate/VIA/VIA.json",
    # s03–s07 stages on OBRA CIVIL
    "intermediate/OBRA CIVIL/OBRA CIVIL_stage3.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_stage4.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_stage5.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_stage6.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_stage7.json",
    # s07 side-artifacts
    "intermediate/OBRA CIVIL/OBRA CIVIL_duplicate_resumen.json",
    "intermediate/OBRA CIVIL/OBRA CIVIL_duplicate_texto.json",
]

# JSON content-level diffs (load + compare as dicts; bytes may differ when the
# producing notebook iterates a non-deterministic container e.g. a set).
JSON_CONTENT_DIFFS: list[str] = [
    # s07 _either_duplicate.json iterates `either_duplicate_keys` which is a
    # `set` — Python set iteration order is randomized per process via
    # PYTHONHASHSEED, so the resulting dict's key order differs run-to-run
    # while the content is identical. Pre-existing s07 nondeterminism; not a
    # refactor regression. Validated by Sprint 06.
    "intermediate/OBRA CIVIL/OBRA CIVIL_either_duplicate.json",
]

# Pickle diffs: (relative-to-data-root original, absolute path of new copy)
PICKLE_DIFFS: list[tuple[str, Path]] = [
    ("processed/OBRA CIVIL_texto.pkl",   NEW_ROOT / "processed" / "OBRA CIVIL_texto.pkl"),
    ("processed/OBRA CIVIL_resumen.pkl", NEW_ROOT / "processed" / "OBRA CIVIL_resumen.pkl"),
    # Generate_OEB cell 3 writes OEB_texto.pkl cwd-relative → ends up in /work/src/
    ("processed/OEB_texto.pkl",          REPO_ROOT / "src" / "OEB_texto.pkl"),
    # Sprint 6.5: new Generate_OEB cell 8 writes OEB_resumen.pkl to PROCESSED_DIR
    ("processed/OEB_resumen.pkl",        NEW_ROOT / "processed" / "OEB_resumen.pkl"),
]


def byte_diff(rel: str) -> tuple[bool, str]:
    a, b = ORIG_ROOT / rel, NEW_ROOT / rel
    if not a.exists():
        return False, f"missing original artifact: {a}"
    if not b.exists():
        return False, f"missing new artifact: {b}"
    a_size, b_size = a.stat().st_size, b.stat().st_size
    if a_size != b_size:
        return False, f"size mismatch: orig={a_size:,} new={b_size:,}"
    ok = filecmp.cmp(str(a), str(b), shallow=False)
    return ok, f"byte-identical ({a_size:,} bytes)" if ok else "byte-level mismatch"


def json_content_diff(rel: str) -> tuple[bool, str]:
    import json
    a, b = ORIG_ROOT / rel, NEW_ROOT / rel
    if not a.exists():
        return False, f"missing original artifact: {a}"
    if not b.exists():
        return False, f"missing new artifact: {b}"
    with a.open(encoding="utf-8") as f:
        orig = json.load(f)
    with b.open(encoding="utf-8") as f:
        new = json.load(f)
    a_size, b_size = a.stat().st_size, b.stat().st_size
    bytes_equal = filecmp.cmp(str(a), str(b), shallow=False)
    bytes_note = "bytes equal" if bytes_equal else "bytes differ (set-iteration order)"
    if isinstance(orig, dict) and isinstance(new, dict):
        if set(orig.keys()) != set(new.keys()):
            return False, f"key sets differ (orig={len(orig)} new={len(new)})"
        mismatches = sum(1 for k in orig if orig[k] != new[k])
        if mismatches == 0:
            return True, f"{len(orig):,} entries, content identical, {bytes_note} ({a_size:,} vs {b_size:,} bytes)"
        return False, f"{mismatches} per-key value mismatches"
    if orig == new:
        return True, f"content identical, {bytes_note}"
    return False, "content differs (non-dict comparison)"


def pickle_diff(orig_rel: str, new_path: Path) -> tuple[bool, str]:
    a = ORIG_ROOT / orig_rel
    if not a.exists():
        return False, f"missing original artifact: {a}"
    if not new_path.exists():
        return False, f"missing new artifact: {new_path}"
    with a.open("rb") as f:
        orig = pickle.load(f)
    with new_path.open("rb") as f:
        new = pickle.load(f)
    if len(orig) != len(new):
        return False, f"length mismatch: orig={len(orig):,} new={len(new):,}"
    orig.sort(key=lambda d: d.metadata["item_key"])
    new.sort(key=lambda d: d.metadata["item_key"])
    text_mismatch = 0
    meta_mismatch = 0
    for o, n in zip(orig, new):
        if o.text != n.text:
            text_mismatch += 1
        if o.metadata != n.metadata:
            meta_mismatch += 1
    if text_mismatch == 0 and meta_mismatch == 0:
        return True, f"{len(orig):,} docs, text+metadata identical (id_ ignored)"
    return False, (
        f"{len(orig):,} docs, {text_mismatch} text mismatches, "
        f"{meta_mismatch} metadata mismatches"
    )


def main() -> int:
    print(f"# Sprint 06 — End-to-End Validation Report")
    print()
    print(f"Generated by `scripts/sprint06_validate_e2e.py`.")
    print(f"Original tree: `{ORIG_ROOT}`")
    print(f"New tree:      `{NEW_ROOT}`")
    print()
    print(f"## Byte-level diffs ({len(BYTE_DIFFS)} rows)")
    print()
    failures: list[str] = []
    for rel in BYTE_DIFFS:
        ok, msg = byte_diff(rel)
        tag = "PASS" if ok else "FAIL"
        print(f"- [{tag}] `{rel}` — {msg}")
        if not ok:
            failures.append(rel)
    print()
    print(f"## JSON content-level diffs ({len(JSON_CONTENT_DIFFS)} rows — bytes may differ; content must match)")
    print()
    for rel in JSON_CONTENT_DIFFS:
        ok, msg = json_content_diff(rel)
        tag = "PASS" if ok else "FAIL"
        print(f"- [{tag}] `{rel}` — {msg}")
        if not ok:
            failures.append(rel)
    print()
    print(f"## Pickle content-level diffs ({len(PICKLE_DIFFS)} rows)")
    print()
    for orig_rel, new_path in PICKLE_DIFFS:
        ok, msg = pickle_diff(orig_rel, new_path)
        tag = "PASS" if ok else "FAIL"
        print(f"- [{tag}] `{orig_rel}` (vs `{new_path}`) — {msg}")
        if not ok:
            failures.append(orig_rel)
    total = len(BYTE_DIFFS) + len(JSON_CONTENT_DIFFS) + len(PICKLE_DIFFS)
    print()
    print(f"## Summary")
    print()
    print(f"Total rows: {total} — passed: {total - len(failures)}, failed: {len(failures)}")
    if failures:
        print()
        print("Failures:")
        for f in failures:
            print(f"  - `{f}`")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
