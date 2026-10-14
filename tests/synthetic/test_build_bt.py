"""BT (opción A), T5/T6 — piezas puras de ``scripts/build_bt.py``."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location("build_bt", _SCRIPTS / "build_bt.py")
bt = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bt
_spec.loader.exec_module(bt)


# --- muestreo del piloto --------------------------------------------------

def test_allocate_is_proportional_and_exact():
    sizes = {"OEB020$": 600, "OEB030$": 300, "OEA010$": 90, "OEZ$": 10}
    alloc = bt.allocate(sizes, 100)
    assert sum(alloc.values()) == 100
    assert alloc == {"OEB020$": 60, "OEB030$": 30, "OEA010$": 9, "OEZ$": 1}


def test_allocate_never_exceeds_stratum():
    alloc = bt.allocate({"a": 2, "b": 1000}, 500)
    assert alloc["a"] <= 2 and sum(alloc.values()) == 500


def test_sample_pilot_is_deterministic_and_stratified():
    keys = {f"{c}_{i}": c for c in ("A$", "B$", "C$") for i in range(50)}
    s1 = bt.sample_pilot(keys, 30, seed=42)
    s2 = bt.sample_pilot(dict(reversed(list(keys.items()))), 30, seed=42)
    assert s1 == s2 and len(s1) == 30
    assert {keys[k] for k in s1} == {"A$", "B$", "C$"}
    assert s1 != bt.sample_pilot(keys, 30, seed=7)


# --- registro de salida (contrato §6) -------------------------------------

_SRC = {
    "id": "x", "item_key": "OEB030jcaaa_syn_7460ba334a18", "parent_key": "OEB030$",
    "gold_item_key": "OEB030jcaaa", "ud": "m", "concept": "CANALIZACIÓN",
    "parameters": {"A": "Doce"}, "text": "texto stacked",
    "modification_types": ["template_paraphrase", "template_paraphrase", "num_to_text"],
    "modification_count": 3,
    "texto_modification_types": ["template_paraphrase", "num_to_text"],
    "texto_modification_count": 2,
}


class _Res:
    surviving_types = ["template_paraphrase"]
    reverted_types = ["num_to_text"]
    axes = {"A": "ok", "B": "ok"}
    not_rendered = ["F"]


_BT_META = {"pivot": "en", "engine": "marian", "mask_strategy": "xml"}


def test_stacked_bt_record():
    rec = bt.output_record("stacked_bt_en", _SRC, "nuevo texto", _Res(), _BT_META, 6)
    assert rec["item_key"] == "OEB030jcaaa_syn_7460ba334a18_bt_en"
    assert rec["source_item_key"] == _SRC["item_key"]
    assert rec["gold_item_key"] == "OEB030jcaaa"
    assert rec["condition"] == "stacked_bt_en"
    assert rec["text"] == "nuevo texto"
    assert rec["modification_types"][-1] == "back_translation"
    assert rec["modification_count"] == 4
    assert rec["texto_modification_types"] == ["template_paraphrase", "num_to_text",
                                               "back_translation"]
    assert rec["texto_modification_count"] == 3
    assert rec["texto_modification_types_post_bt"] == ["template_paraphrase",
                                                       "back_translation"]
    assert rec["texto_modification_count_post_bt"] == 2
    assert rec["reverted_types"] == ["num_to_text"]
    assert rec["characterization_check"] == {
        "protocol_version": bt.PROTOCOL_VERSION, "mode": "structural_masked",
        "masked_values": 6, "not_rendered": ["F"]}
    assert rec["id"] == bt.stable_id(rec["item_key"])
    assert len(rec["source_text_sha256"]) == 64


def test_bt_orig_record():
    gold = {"item_key": "OEB030jcaaa", "parent_key": "OEB030$", "ud": "m",
            "concept": "CANALIZACIÓN", "text": "texto gold",
            "parameters": {"A": {"label": "Nº", "values": [{"label": "a", "value": " 12 "}]}}}

    class R(_Res):
        surviving_types, reverted_types = [], []

    rec = bt.output_record("bt_orig_en", gold, "gold traducido", R(), _BT_META, 5)
    assert rec["item_key"] == "OEB030jcaaa_btorig_en"
    assert rec["source_item_key"] == rec["gold_item_key"] == "OEB030jcaaa"
    assert rec["parameters"] == {"A": "12"}
    assert rec["modification_types"] == ["back_translation"]
    assert rec["texto_modification_types_post_bt"] == ["back_translation"]
    assert rec["texto_modification_count_post_bt"] == 1


def test_stable_id_matches_package_for_retrieval():
    pytest.importorskip("pandas")
    spec = importlib.util.spec_from_file_location("pfr", _SCRIPTS / "package_for_retrieval.py")
    pfr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pfr)
    assert bt.stable_id("OEB030jcaaa_bt_en") == pfr._sid("OEB030jcaaa_bt_en")


# --- auditoría humana -----------------------------------------------------

def test_audit_markdown_is_blind_and_sorted_by_drift():
    rows = [
        {"item_key": "k1", "text": "consulta uno", "gold_text": "gold uno", "drift": 0.1},
        {"item_key": "k2", "text": "consulta dos", "gold_text": "gold dos", "drift": 0.6},
    ]
    md = bt.audit_markdown("Piloto", rows)
    assert md.index("k2") < md.index("k1")
    assert "¿Describe exactamente la misma partida" in md
    assert md.count("- [ ] Sí") == 2 and md.count("- [ ] Dudoso") == 2
    assert "marian" not in md.lower() and "phi4" not in md.lower()
    assert "gold uno" in md


# --- BM25 -----------------------------------------------------------------

def test_bm25_acc1_counts_group_members_as_hits():
    pytest.importorskip("rank_bm25")
    corpus = {"d1": "canaleta pvc diurno", "d2": "canaleta pvc nocturno",
              "d3": "tubo acero rocoso", "d4": "canaleta pvc diurno"}
    index = bt.Bm25Index(corpus)
    groups = {"d1": frozenset({"d1", "d4"}), "d4": frozenset({"d1", "d4"})}
    queries = [("canaleta diurno", "d4"), ("tubo rocoso", "d3"), ("canaleta nocturno", "d1")]
    assert bt.bm25_acc1(index, queries, groups) == pytest.approx(2 / 3)


def _mx():
    spec = importlib.util.spec_from_file_location("bt_mask_experiment", _SCRIPTS / "bt_mask_experiment.py")
    mx = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mx
    spec.loader.exec_module(mx)
    return mx


def test_mask_experiment_chooses_most_accepted():
    summary = {"sentinel": {"accepted": 38, "mask_lost": 50},
               "xml": {"accepted": 75, "mask_lost": 10}}
    assert _mx().choose(summary) == "xml"


def test_mask_experiment_tie_breaks_on_fewer_lost_masks():
    summary = {"sentinel": {"accepted": 70, "mask_lost": 5},
               "xml": {"accepted": 70, "mask_lost": 9}}
    assert _mx().choose(summary) == "sentinel"


# --- condiciones con BT de valores ----------------------------------------

def test_stacked_btv_record_suffix_and_types():
    rec = bt.output_record("stacked_btv_en", _SRC, "texto", _Res(), _BT_META, 6, value_bt=True)
    assert rec["item_key"] == "OEB030jcaaa_syn_7460ba334a18_btv_en"
    assert rec["modification_types"][-2:] == ["back_translation", "value_back_translation"]
    assert rec["texto_modification_types_post_bt"][-2:] == ["back_translation", "value_back_translation"]


def test_bt_origv_record_suffix():
    gold = {"item_key": "OEB030jcaaa", "parent_key": "OEB030$", "text": "t", "parameters": {}}

    class R(_Res):
        surviving_types, reverted_types = [], []

    rec = bt.output_record("bt_origv_en", gold, "x", R(), _BT_META, 3, value_bt=False)
    assert rec["item_key"] == "OEB030jcaaa_btorigv_en"
    assert rec["modification_types"] == ["back_translation"]  # sin sustituciones de valor


def test_condition_names():
    assert bt.CONDITIONS == ("stacked_bt", "bt_orig", "stacked_btv", "bt_origv")
