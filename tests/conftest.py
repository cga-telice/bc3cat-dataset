from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT / "data" / "raw" / "BPA_2024_v2.txt"


@pytest.fixture(scope="session")
def raw_path() -> Path:
    if not RAW_FILE.exists() or RAW_FILE.stat().st_size < 1_000_000:
        pytest.skip("real BC3 file not available")
    return RAW_FILE
