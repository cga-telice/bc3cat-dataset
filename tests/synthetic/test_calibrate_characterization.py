"""BT (opción A), T2 — piezas puras de ``scripts/calibrate_characterization.py``."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from synthetic.characterization import CharacterizationContext

from test_characterization import _corpus, _groups, _stage  # noqa: E402

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "calibrate_characterization.py"
_spec = importlib.util.spec_from_file_location("calibrate_characterization", _SCRIPT)
cal = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = cal  # las dataclasses lo necesitan
_spec.loader.exec_module(cal)


@pytest.fixture
def ctx():
    corpus = _corpus()
    return CharacterizationContext.load(_stage(), corpus, d031_groups=_groups(corpus))


@pytest.mark.parametrize(
    "a, b, d",
    [
        ("trabajo Diurno .", "trabajo Nocturno .", 1),
        ("obra normal", "obra normal excepcional", 1),
        ("a b c", "a b c", 0),
        ("1 tubo rocoso", "2 tubos normal", 3),
    ],
)
def test_token_distance(a, b, d):
    assert cal.token_distance(a, b) == d


def test_ablate_removes_every_rendered_occurrence():
    text = "Canalización de 2 tubos en terreno rocoso. Trabajo: Diurno"
    assert cal.ablate(text, "Diurno", 1) == "Canalización de 2 tubos en terreno rocoso. Trabajo:"


def test_ablate_refuses_when_count_does_not_match():
    # "1" aparece también en el literal de la plantilla: no se puede ablacionar
    assert cal.ablate("de 1 tubos de 1,60 m y 1 cm", "1", 1) is None
    assert cal.ablate("sin el valor", "Diurno", 1) is None


def test_cases_are_deterministic_and_cover_all_kinds(ctx):
    a = cal.build_cases(ctx, seed=42, per_concept=4, stacked=[], sidecar={})
    b = cal.build_cases(ctx, seed=42, per_concept=4, stacked=[], sidecar={})
    assert a == b
    kinds = {c.kind for c in a}
    assert kinds == {"positive", "discrimination", "ablation"}


def test_discrimination_sibling_differs_in_one_rendered_axis(ctx):
    cases = cal.build_cases(ctx, seed=42, per_concept=4, stacked=[], sidecar={})
    for c in cases:
        if c.kind != "discrimination":
            continue
        sib, base = ctx.leaves[c.gold], ctx.leaves[c.base]
        diff = [a for a in sib.options if sib.options[a] != base.options[a]]
        assert diff == [c.axis]
        assert c.axis in ctx.concepts[sib.concept].rendered
        assert sib.text != base.text


def test_ablation_only_on_direct_placeholder_axes(ctx):
    cases = cal.build_cases(ctx, seed=42, per_concept=4, stacked=[], sidecar={})
    abl = [c for c in cases if c.kind == "ablation"]
    assert abl and all(c.axis in {"A", "C"} for c in abl)  # B se renderiza vía $I


def test_drift_cases_from_visible_records(ctx):
    stacked = [{"item_key": "q1", "gold_item_key": "OEX010abaa", "text": "t1"},
               {"item_key": "q2", "gold_item_key": "OEX010abaa", "text": "t2"}]
    sidecar = {
        "q1": [{"type": "synonym_label", "layer": "param_value", "param": "C",
                "value": "a", "original": "Adosada", "new": "Empotrada"}],
        "q2": [{"type": "synonym_label", "layer": "param_value", "param": "D",
                "value": "a", "original": "Adosada", "new": "Empotrada"}],  # D no se ve
    }
    cases = cal.build_cases(ctx, seed=42, per_concept=0, stacked=stacked, sidecar=sidecar)
    assert [(c.kind, c.query_key) for c in cases] == [("drift", "q1")]


@pytest.mark.parametrize(
    "original, new, drift",
    [
        ("adosada o superficial", "empotrada o a ras", True),
        ("adosada o superficial", "incrustada o a nivel", True),
        ("en cruce bajo vías ejecutado con topo", "en intersección subvial con topografía", True),
        ("en cruce bajo vías ejecutado con topo", "ejecutado con topo y perfilado", False),
        ("adosada o superficial",
         "instalada adosada o en superficie, permitiendo una integración", False),
    ],
)
def test_is_drift(original, new, drift):
    assert cal.is_drift({"layer": "text_variable", "original": original, "new": new}) is drift
