"""auto_verdicts_v2._approve — no-op rejection and existing rules."""
from __future__ import annotations

import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "auto_verdicts_v2", REPO / "scripts" / "auto_verdicts_v2.py")
av = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(av)


def test_rejects_noop_rewrite():
    assert av._approve({"new": "foo bar", "original": "foo bar"}, "template_paraphrase") is False
    # whitespace-normalised equality still counts as a no-op
    assert av._approve({"new": " foo   bar ", "original": "foo bar"}, "paraphrase") is False


def test_accepts_real_change():
    assert av._approve({"new": "conducto de hormigón", "original": "canaleta"}, "template_paraphrase") is True


def test_rejects_empty_and_preserves_meaning_false():
    assert av._approve({"new": "  ", "original": "x"}, "paraphrase") is False
    assert av._approve({"new": "y", "original": "x", "preserves_meaning": False}, "paraphrase") is False


def test_rejects_fragment_residue_but_not_field_placeholders():
    # L1/L2 fragment: a $X/%X is residue
    assert av._approve({"new": "$A tubos", "original": "2 tubos"}, "num_to_text") is False
    # L3 field: placeholders are legitimate, only sentinels are residue
    assert av._approve({"new": "Canaleta $A ($L(%B))", "original": "Tubo $A"}, "template_paraphrase") is True
