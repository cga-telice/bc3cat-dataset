"""Regression guard: no notebook on the synthetic critical path may carry a
`/work` literal in any of its cell `source` arrays.

Output arrays (`outputs`) are exempt — they are regenerated on rerun and
deliberately not migrated by Sprints 02–04.
"""
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"

# Notebooks Sprints 02–04 are responsible for.
NOTEBOOKS = [
    "s01_parse_fiebdc.ipynb",
    "s02_split_chapters.ipynb",
    "s03_generate_parametric_combinations.ipynb",
    "s04_evaluate_text_variables.ipynb",
    "s05_evaluate_resumen_texto.ipynb",
    "s06_data_analysis.ipynb",
    "s07_Filter_duplicates.ipynb",
    "s08_Llamaindex_Doc_Creation.ipynb",
    "Generate_OEB_dataset.ipynb",
]


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_no_work_literal_in_source_cells(notebook):
    path = SRC_DIR / notebook
    nb = json.loads(path.read_text(encoding="utf-8"))

    offenders = []
    for i, cell in enumerate(nb["cells"]):
        src = "".join(cell.get("source", []))
        if "/work" in src:
            offenders.append((i, cell.get("id", "?"), src))
    assert not offenders, (
        f"{notebook}: found /work literal in cell source arrays at: "
        + ", ".join(f"cell[{i}] id={cid[:8]}" for i, cid, _ in offenders)
    )
