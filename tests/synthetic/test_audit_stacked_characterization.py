"""BT (opción A), T3 — piezas puras de ``scripts/audit_stacked_characterization.py``."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))
_spec = importlib.util.spec_from_file_location(
    "audit_stacked_characterization", _SCRIPTS / "audit_stacked_characterization.py")
audit = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = audit
_spec.loader.exec_module(audit)

_STAGE = {
    "OEX010$": {
        "texto": "\\Canalización de $A tubos $I. Trabajo: $C",
        "text_variables": {"I": '"normal" * (%B=="a") + "rocoso" * (%B=="b")',
                           "G": ['"D"', '"N"']},
        "parameters": {"A": {}, "B": {}, "C": {}},
    }
}


def test_var_axes_from_formula_and_calls():
    got = audit.var_axes(_STAGE["OEX010$"])
    assert got == {"I": frozenset({"B"}), "G": frozenset()}


def test_cause_by_axis():
    va = audit.var_axes(_STAGE["OEX010$"])
    recs = [
        {"type": "template_paraphrase", "layer": "template", "field": "TEXTO"},
        {"type": "synonym_label", "layer": "param_value", "param": "C"},
        {"type": "paraphrase", "layer": "text_variable", "var": "I"},
    ]
    assert audit.cause(recs, "C", va) == ["synonym_label"]
    assert audit.cause(recs, "B", va) == ["paraphrase"]
    # nadie toca A: la culpa es de la plantilla
    assert audit.cause(recs, "A", va) == ["template_paraphrase"]
    # sin eje (G1/G3/G6): todos los tipos visibles
    assert audit.cause(recs, None, va) == ["paraphrase", "synonym_label", "template_paraphrase"]


def test_exclusion_payload_shape():
    rows = [
        {"item_key": "q2", "ok": False, "gate": "G2", "axis": "B", "reason": "wrong_value",
         "cause": ["paraphrase"]},
        {"item_key": "q1", "ok": True},
        {"item_key": "q0", "ok": False, "gate": "G1", "axis": None, "reason": "extra",
         "cause": ["num_to_text"]},
    ]
    payload = audit.exclusion_payload(rows)
    assert payload["file"] == "OE_stacked_texto.json"
    assert payload["item_keys"] == ["q0", "q2"]
    assert payload["details"]["q2"] == {"gate": "G2", "axis": "B", "reason": "wrong_value",
                                        "cause": ["paraphrase"]}
