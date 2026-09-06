from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
INTERMEDIATE = REPO / "data" / "intermediate" / "OBRA CIVIL" / "OBRA CIVIL.json"
PILOT_SOURCE = REPO / "data" / "raw" / "BPA_2024_v2_OEB_mod_utf8.txt"


@pytest.mark.skipif(
    not INTERMEDIATE.exists() or not PILOT_SOURCE.exists(),
    reason="legacy intermediate or pilot source not present",
)
def test_bc3param_base_render_equivalent_to_legacy_up_to_v2():
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from scripts.equivalence_syn_base import compare

    tally, only_legacy, only_bc3, unexplained = compare()
    assert only_legacy == 0 and only_bc3 == 0, (only_legacy, only_bc3)
    assert tally["unexplained"] == 0, unexplained[:5]
    # sanity: the comparison actually ran over the OEB chapter
    assert tally["exact"] + tally["whitespace"] + tally["v2_correction"] > 10000
