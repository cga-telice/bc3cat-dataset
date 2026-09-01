"""Sprint 39 — hermetic tests for :mod:`synthetic.pantry`."""
from __future__ import annotations

import json

import pytest

from synthetic.pantry import ApprovedRewrite, load_pantry
from synthetic.taxonomy import ModificationType


def _write_pair(tmp_path, mtype, rows_menu, rows_verdicts):
    (tmp_path / "menus").mkdir(exist_ok=True)
    (tmp_path / "menus" / "verdicts").mkdir(exist_ok=True)
    (tmp_path / "menus" / f"{mtype}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_menu), encoding="utf-8")
    (tmp_path / "menus" / "verdicts" / f"{mtype}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_verdicts), encoding="utf-8")


def test_load_pantry_joins_menus_and_verdicts_and_filters_approved(tmp_path):
    menu = [{"canonical": "EJE / Diurno", "dedup_key": ["EJE", "Diurno"],
             "modification_type": "synonym_label", "skipped_reason": None, "dropped_reasons": [],
             "usages": [{"concept_key": "C1$", "slot_extractor_target_id": "A", "display": "x"},
                        {"concept_key": "C2$", "slot_extractor_target_id": "A", "display": "x"}],
             "candidates": [{"approved": None, "payload": {"original": "Diurno", "new": "Turno diurno"}},
                            {"approved": None, "payload": {"original": "Diurno", "new": "De día"}}]}]
    verd = [{"canonical": "EJE / Diurno", "dedup_key": ["EJE", "Diurno"],
             "modification_type": "synonym_label", "skipped_reason": None,
             "candidates": [{"approved": True, "payload": {"original": "Diurno", "new": "Turno diurno"}},
                            {"approved": False, "payload": {"original": "Diurno", "new": "De día"}}]}]
    _write_pair(tmp_path, "synonym_label", menu, verd)
    pantry = load_pantry(menus_dir=tmp_path / "menus")
    rs = pantry.by_type[ModificationType.SYNONYM_LABEL]
    assert len(rs) == 1  # only the approved candidate
    r = rs[0]
    assert isinstance(r, ApprovedRewrite)
    assert r.payload["new"] == "Turno diurno"
    assert [u.concept_key for u in r.usages] == ["C1$", "C2$"]
    # applicability index
    assert pantry.for_concept("C1$")[ModificationType.SYNONYM_LABEL] == (r,)
    assert pantry.for_concept("C9$") == {}


def test_load_pantry_excludes_omission_and_new_param(tmp_path):
    for mtype in ("omission", "new_param"):
        menu = [{"canonical": "x", "dedup_key": ["x"], "modification_type": mtype,
                 "skipped_reason": None, "dropped_reasons": [],
                 "usages": [{"concept_key": "C1$", "slot_extractor_target_id": None, "display": "x"}],
                 "candidates": [{"approved": None, "payload": {"original": "a", "new": "b"}}]}]
        verd = [dict(menu[0], candidates=[{"approved": True, "payload": {"original": "a", "new": "b"}}])]
        _write_pair(tmp_path, mtype, menu, verd)
    pantry = load_pantry(menus_dir=tmp_path / "menus")
    assert ModificationType.OMISSION not in pantry.by_type
    assert ModificationType.NEW_PARAM not in pantry.by_type


def test_load_pantry_fails_loud_on_misaligned_files(tmp_path):
    menu = [{"canonical": "x", "dedup_key": ["x"], "modification_type": "reorder",
             "skipped_reason": None, "dropped_reasons": [], "usages": [],
             "candidates": [{"approved": None, "payload": {"original": "a", "new": "b"}}]}]
    verd = [dict(menu[0], candidates=[])]  # different candidate count
    _write_pair(tmp_path, "reorder", menu, verd)
    with pytest.raises(ValueError, match="pantry_misaligned"):
        load_pantry(menus_dir=tmp_path / "menus")
