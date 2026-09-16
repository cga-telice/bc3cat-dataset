"""E3 — tests del empaquetado: join del sidecar, campos nuevos, procedencia."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_packager():
    """Import the script by path (it lives in scripts/, not a package)."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "package_for_retrieval", ROOT / "scripts" / "package_for_retrieval.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sidecar(tmp_path, rows):
    p = tmp_path / "applicability.jsonl"
    p.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    return p


def test_applicability_fields_are_joined_onto_every_record(tmp_path):
    mod = _load_packager()
    side = _sidecar(tmp_path, [
        {"leaf_item_key": "OEA010aaba",
         "applicable_types": ["paraphrase", "reorder"],
         "available_types": ["reorder"], "in_pool": True},
    ])
    table = mod.load_applicability(side)
    rec = mod.apply_applicability(
        {"item_key": "x", "gold_item_key": "OEA010aaba"}, table,
    )
    assert rec["applicable_types"] == ["paraphrase", "reorder"]
    assert rec["available_types"] == ["reorder"]


def test_isolated_delivery_is_restricted_to_the_pool(tmp_path):
    """D6: the probe release keeps every survivor for the report's counts, but
    only the pool's leaves are delivered — they are the ones the ladder also
    runs on, which is what makes isolated and dose effects comparable within
    the same leaf."""
    mod = _load_packager()
    side = _sidecar(tmp_path, [
        {"leaf_item_key": "IN", "applicable_types": [], "available_types": [],
         "in_pool": True},
        {"leaf_item_key": "OUT", "applicable_types": [], "available_types": [],
         "in_pool": False},
    ])
    table = mod.load_applicability(side)
    assert mod.in_pool({"item_key": "a", "gold_item_key": "IN"}, table) is True
    assert mod.in_pool({"item_key": "b", "gold_item_key": "OUT"}, table) is False


def test_missing_sidecar_entry_fails_loud(tmp_path):
    mod = _load_packager()
    table = mod.load_applicability(_sidecar(tmp_path, []))
    with pytest.raises(KeyError, match="applicability_missing"):
        mod.apply_applicability({"item_key": "x", "gold_item_key": "OEA010aaba"}, table)


def test_manifest_lists_a_sha256_per_file(tmp_path):
    mod = _load_packager()
    (tmp_path / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.jsonl").write_text("{}\n", encoding="utf-8")
    text = mod.render_manifest(
        tmp_path, ["a.json", "b.jsonl"],
        provenance={"run_id": "r1", "seed": 42, "script": "s", "commit": "c"},
    )
    assert "a.json" in text and "b.jsonl" in text
    assert text.count("sha256") >= 1
    # the digest of an empty JSON list, to pin the hashing itself
    import hashlib
    assert hashlib.sha256(b"[]").hexdigest() in text
