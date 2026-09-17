"""Tests for scripts/audit_texto_visibility.py — which recorded modifications a
TEXTO query really shows, and what the corrected count would be."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

STAGE = {"C1$": {
    "ud": "m", "concept": "zanja",
    "parameters": {
        "A": {"label": "TIPO", "values": [{"label": "a", "value": "Normal"},
                                           {"label": "b", "value": "Bajo vías"}]},
        "B": {"label": "BANDA", "values": [{"label": "a", "value": "5 horas"}]},
    },
    "texto": "Zanja $I, banda $B",
    "resumen": "Zanja $K ($A)",
    "text_variables": {},
}}


def _load():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "audit_texto_visibility", ROOT / "scripts" / "audit_texto_visibility.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_item_counts_only_what_the_texto_shows():
    from synthetic.dose_ladder import TextoSurface

    mod = _load()
    surface = TextoSurface.from_stage(STAGE)
    mods = [
        {"type": "template_paraphrase", "layer": "template", "field": "RESUMEN", "new": "Z $K"},
        {"type": "template_paraphrase", "layer": "template", "field": "TEXTO", "new": "Zanja: $I"},
        {"type": "paraphrase", "layer": "text_variable", "var": "K",
         "condition": '%A=="b"', "new": "debajo de las vias"},
        {"type": "compression", "layer": "text_variable", "var": "I",
         "condition": '%A=="b"', "new": "bajo vias"},
        {"type": "unit_expansion", "layer": "param_value", "param": "B", "new": "cinco horas"},
    ]
    texto = "Zanja: bajo vias, banda cinco horas"
    got = mod.audit_item(mods, texto, "C1$", "C1ba", surface)

    assert got["recorded_count"] == 5
    assert got["visible_count"] == 3
    assert got["visible_types"] == ["template_paraphrase", "compression", "unit_expansion"]
    assert got["hidden"] == [("template_paraphrase", "RESUMEN"), ("paraphrase", "text_variable")]
    # structural verdict and the substring check agree on the L1/L2 records
    assert got["disagreements"] == []


def test_audit_item_reports_a_disagreement_with_the_substring_check():
    from synthetic.dose_ladder import TextoSurface

    mod = _load()
    surface = TextoSurface.from_stage(STAGE)
    mods = [{"type": "compression", "layer": "text_variable", "var": "I",
             "condition": '%A=="b"', "new": "bajo vias"}]
    got = mod.audit_item(mods, "Zanja sin el cambio", "C1$", "C1ba", surface)
    assert got["visible_count"] == 1
    assert got["disagreements"] == [("compression", True, False)]


def test_corrected_sidecar_keeps_texts_and_rewrites_only_the_counts(tmp_path):
    mod = _load()
    items = pd.DataFrame({
        "item_key": ["x"], "original_key": ["C1ba"], "concept_key": ["C1$"],
        "texto": ["Zanja: bajo vias"], "resumen": ["r"],
        "modification_types": [["template_paraphrase", "compression"]],
        "modification_count": [2],
    })
    audited = {"x": {"recorded_count": 2, "visible_count": 1,
                     "visible_types": ["compression"], "hidden": [], "disagreements": []}}
    rows = mod.corrected_rows(items, audited)
    assert rows == [{"item_key": "x", "recorded_count": 2, "texto_visible_count": 1,
                     "texto_visible_types": ["compression"]}]
    json.dumps(rows)
