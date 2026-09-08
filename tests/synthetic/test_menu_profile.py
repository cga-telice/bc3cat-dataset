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


def test_new_param_dedup_is_label_level_not_value_set_level(tmp_path):
    _write(tmp_path / "new_param.jsonl", [
        {"modification_type": "new_param", "skipped_reason": None, "dropped_reasons": [],
         "usages": [{"concept_key": "A$"}],
         "candidates": [
             {"payload": {"new_axis_label": "Acabado superficial", "values": ["liso", "rugoso"]}},
             {"payload": {"new_axis_label": "Acabado superficial", "values": ["pulido", "mate"]}},
         ]},
    ])
    rows = profile_dir(tmp_path)
    assert len(rows) == 1
    r = rows[0]
    # No `original` on new_param payloads, so nothing can be a no-op; the
    # second candidate repeats the first's label and counts as a dup even
    # though the value sets differ.
    assert r.n_noop == 0
    assert r.n_dup == 1


def test_profile_dir_empty_dir_yields_empty_list_and_header_only_table(tmp_path):
    assert profile_dir(tmp_path) == []
    text = format_profile([])
    lines = text.splitlines()
    assert len(lines) == 2
    assert "uniq/tgt" in lines[0]
    assert lines[1] == "-" * len(lines[0])


def test_diversity_columns(tmp_path):
    _write(tmp_path / "template_paraphrase.jsonl", [
        {"modification_type": "template_paraphrase", "skipped_reason": None, "dropped_reasons": [],
         "usages": [{"concept_key": "A$"}],
         "candidates": [
             {"payload": {"original": "a b c d", "new": "a b c d"}},   # dist 0.0 to original
             {"payload": {"original": "a b c d", "new": "e f g h"}},   # dist 1.0
         ]},
    ])
    r = profile_dir(tmp_path)[0]
    # dist_orig: mean over candidates of (1 - Jaccard(new, original)) -> (0.0 + 1.0) / 2
    assert r.dist_orig == 0.5
    # pair_sim: mean pairwise Jaccard among the target's candidates -> 0.0 for disjoint pair
    assert r.pair_sim == 0.0
    text = format_profile([r])
    assert "d_orig" in text and "p_sim" in text


def test_pair_sim_is_mean_of_per_target_means(tmp_path):
    # target 1: two disjoint candidates -> per-target mean 0.0
    # target 2: three identical candidates... use distinct-but-overlapping to avoid dedup concerns:
    # pairs all Jaccard 1.0 -> per-target mean 1.0. Overall = (0.0 + 1.0) / 2 = 0.5,
    # whereas pooled-pairs would give (0*1 + 1*3) / 4 = 0.75.
    _write(tmp_path / "paraphrase.jsonl", [
        {"modification_type": "paraphrase", "skipped_reason": None, "dropped_reasons": [],
         "usages": [{"concept_key": "A$"}],
         "candidates": [
             {"payload": {"original": "o", "new": "a b"}},
             {"payload": {"original": "o", "new": "c d"}},
         ]},
        {"modification_type": "paraphrase", "skipped_reason": None, "dropped_reasons": [],
         "usages": [{"concept_key": "B$"}],
         "candidates": [
             {"payload": {"original": "o", "new": "x y"}},
             {"payload": {"original": "o", "new": "y x"}},
             {"payload": {"original": "o", "new": "x  y"}},
         ]},
    ])
    assert profile_dir(tmp_path)[0].pair_sim == 0.5
