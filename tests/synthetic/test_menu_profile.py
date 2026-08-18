"""Sprint 38.5 — hermetic test for :mod:`synthetic.menu_profile`."""
from __future__ import annotations

import json
from pathlib import Path

from synthetic.menu_profile import profile_dir, format_profile


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_profile_counts_targets_candidates_noops_and_skips(tmp_path):
    _write(tmp_path / "paraphrase.jsonl", [
        {"modification_type": "paraphrase", "skipped_reason": None, "dropped_reasons": [],
         "usages": [{"concept_key": "A$"}, {"concept_key": "B$"}],
         "candidates": [
             {"payload": {"original": "20 cm", "new": "veinte centímetros"}},
             {"payload": {"original": "20 cm", "new": "20 CM"}},          # no-op after normalisation
             {"payload": {"original": "20 cm", "new": "veinte  centímetros"}},  # dup of #1
         ]},
        {"modification_type": "paraphrase", "skipped_reason": "malformed_list_after_retry: x",
         "dropped_reasons": ["[0] bad"], "usages": [{"concept_key": "C$"}], "candidates": []},
    ])
    rows = profile_dir(tmp_path)
    assert len(rows) == 1
    r = rows[0]
    assert (r.mtype, r.n_targets, r.n_empty, r.n_candidates, r.n_noop, r.n_dup, r.n_skipped, r.n_dropped, r.n_usages) == (
        "paraphrase", 2, 1, 3, 1, 1, 1, 1, 3)
    assert r.uniq_per_target == 2.0  # 2 unique of 3 on the one populated target
    text = format_profile(rows)
    assert "paraphrase" in text and "uniq/tgt" in text
