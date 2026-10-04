"""BT (opción A, rediseño tras CP2) — tests de :mod:`synthetic.bt_alignment`.

La alineación localiza en un TEXTO renderizado la superficie de cada
placeholder de su plantilla (valores L1 y fragmentos de variables L2), para
enmascararlos durante la BT.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from synthetic.bt_alignment import (
    AlignmentError,
    align,
    gold_slots,
    leaf_values,
    stacked_slots,
)

from test_characterization import _render, _stage  # noqa: E402

_REPO = Path(__file__).resolve().parents[2]
_STAGE = _stage()["OEX010$"]
_TPL = "Canalización de $A tubos $I, con hormigón HE-20 de 1,60 m. Trabajo: $C"
GOLD = "OEX010abaa"
GOLD_TEXT = _render(0, 1, 0)  # 1 tubos, rocoso, Diurno


def _surfaces(slots):
    return {s.placeholder: s.text for s in slots}


def test_leaf_values_by_axis():
    assert leaf_values(_STAGE, GOLD) == {"A": " 1 ", "B": " Rocoso ", "C": " Diurno ", "D": " Volumen escaso "}


def test_gold_slots_cover_every_placeholder():
    slots = gold_slots(_STAGE, GOLD, GOLD_TEXT)
    assert _surfaces(slots) == {"$A": "1", "$I": "en terreno rocoso", "$C": "Diurno"}
    for s in slots:
        assert GOLD_TEXT[s.start:s.end] == s.text


def test_align_with_free_group():
    slots = align(_TPL, GOLD_TEXT, {"$A": "1", "$C": "Diurno"})
    assert _surfaces(slots)["$I"] == "en terreno rocoso"


def test_align_tolerates_whitespace_differences():
    text = GOLD_TEXT.replace(". Trabajo", ".\nTrabajo")
    assert _surfaces(align(_TPL, text, {}))["$C"] == "Diurno"


def test_align_no_match_fails_loud():
    with pytest.raises(AlignmentError, match="no_match"):
        align(_TPL, "otro texto distinto", {})


def test_align_ambiguous_fails_loud():
    # dos grupos libres contiguos: «1 tubos en terreno» admite varios cortes
    with pytest.raises(AlignmentError, match="ambiguous"):
        align("de $A $B fin", "de x y z fin", {})


def test_empty_rendering_gives_empty_slot():
    slots = align("Inicio $N fin", "Inicio fin", {"$N": ""})
    assert slots[0].text == "" and slots[0].start == slots[0].end


def test_stacked_slots_apply_sidecar_records():
    records = [
        {"type": "template_paraphrase", "layer": "template", "field": "TEXTO",
         "original": _TPL, "new": "Trabajo: $C. Se tiende $A tubos $I con HE-20 de 1,60 m"},
        {"type": "synonym_label", "layer": "param_value", "param": "C",
         "value": "a", "original": "Diurno", "new": "Turno de día"},
        {"type": "paraphrase", "layer": "text_variable", "var": "I",
         "condition": '%B=="b"', "original": "en terreno rocoso", "new": "sobre roca"},
    ]
    query = "Trabajo: Turno de día. Se tiende 1 tubos sobre roca con HE-20 de 1,60 m"
    slots = stacked_slots(_STAGE, GOLD, GOLD_TEXT, query, records)
    assert _surfaces(slots) == {"$C": "Turno de día", "$A": "1", "$I": "sobre roca"}
    assert [s.placeholder for s in slots] == ["$C", "$A", "$I"]


def test_stacked_slots_fall_back_when_l2_fragment_unknown():
    records = [
        {"type": "template_paraphrase", "layer": "template", "field": "TEXTO",
         "original": _TPL, "new": _TPL},
        {"type": "compression", "layer": "text_variable", "var": "I",
         "condition": '%B=="b"', "original": "texto que no está", "new": "roca"},
    ]
    query = GOLD_TEXT.replace("en terreno rocoso", "roca")
    assert _surfaces(stacked_slots(_STAGE, GOLD, GOLD_TEXT, query, records))["$I"] == "roca"


# --- datos reales (se saltan si no están) ---------------------------------

def _load(rel):
    p = _REPO / rel
    if not p.exists():
        pytest.skip(f"{rel} no está en disco")
    return json.loads(p.read_text(encoding="utf-8"))


def test_every_gold_leaf_aligns():
    stage = _load("data/synthetic/intermediate/OE_2026_stage.json")
    corpus = _load("data/synthetic/handoff_OE/OE_texto.json")
    for r in corpus:
        slots = gold_slots(stage[r["parent_key"]], r["item_key"], r["text"])
        con = stage[r["parent_key"]]
        vals = leaf_values(con, r["item_key"])
        for s in slots:
            if s.placeholder[1:] in vals:
                assert s.text == " ".join(vals[s.placeholder[1:]].split()) or s.text in vals[s.placeholder[1:]], (r["item_key"], s)
