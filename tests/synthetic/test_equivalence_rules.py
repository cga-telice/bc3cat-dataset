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
def test_rule_application_equivalent_to_legacy_up_to_v2_fast():
    """Fast subset: a handful of OEB020$ variants (one per rule family).

    The exhaustive check over all 178 frozen variants is
    `scripts/equivalence_syn_rules.py` (slow: the legacy path re-runs s03-s07).
    """
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from scripts.equivalence_syn_rules import compare

    nvar, tally, errors, modmismatch, unexplained = compare(concepts=["OEB020$"], max_variants=6)
    assert nvar > 0
    assert errors == []
    assert modmismatch == 0
    assert tally["unexplained"] == 0, unexplained[:5]
