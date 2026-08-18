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
