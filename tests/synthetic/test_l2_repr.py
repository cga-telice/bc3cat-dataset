"""Sprint 26 — Task B6: the L2 text-variable representation adapter.

Covers `synthetic.l2_repr` — the adapter that makes all three real text-variable
shapes enumerable for Stage A and restores each to the rerun-faithful form for
Stage B, without editing the frozen seam. All hermetic: tiny inline fixtures
mirroring the real `OBRA CIVIL` grammar (the three shapes × their reference
styles). Zero network.

The three shapes and their template reference styles (which decide the rerun
form):
  * LIST_plain      — `['"Diurno"', …]`, indexed ref `$L(%B)` → positional list
  * STR_formula     — `'"a"*(%B=="a")+…'`, bare ref `$K`     → formula string
  * LIST_conditional— `['"…"*(%B=="f")', …]`, bare ref `$P`  → list of conds
"""

import copy

import pytest

from synthetic import l2_repr
from synthetic.l2_repr import (
    derive_var_axis_map,
    list_to_formula,
    formula_to_list,
    assert_l2_targets_or_warn,
)
from synthetic import mutator
from synthetic.slot_extractor import enumerate_targets
from synthetic.stage_runners import run_stages_3_to_7
from synthetic.taxonomy import ModificationType


_KEY = "OEB999$"


def _concept():
    """Two LIST_plain vars ($L↔B, $N↔D), positionally aligned, indexed refs."""
    return {
        _KEY: {
            "ud": "m", "concept": "TEST",
            "parameters": {
                "B": {"label": "TRABAJO", "values": [
                    {"label": "a", "value": "Diurno"}, {"label": "b", "value": "Nocturno"}]},
                "D": {"label": "COND", "values": [
                    {"label": "a", "value": "Rel"}, {"label": "b", "value": "Esc"}]},
            },
            "text_variables": {
                "L": ['"Diurno"', '"Nocturno"'],
                "N": ['"Rel"', '"Esc"'],
            },
            "resumen": "Canal ($L(%B)/$N(%D))",
            "texto": "Canal trabajo $L(%B) cond $N(%D) fin",
        }
    }


def _mixed():
    """One axis B; all three shapes: G plain(indexed) / K str(bare) / P cond(bare)."""
    return {
        _KEY: {
            "ud": "m", "concept": "T",
            "parameters": {"B": {"label": "AX", "values": [
                {"label": "a", "value": "AA"}, {"label": "b", "value": "BB"}]}},
            "text_variables": {
                "G": ['"g_a"', '"g_b"'],
                "K": '"k_a" * (%B=="a") + "k_b" * (%B=="b")',
                "P": ['"p_a" * (%B=="a")', '"p_b" * (%B=="b")'],
            },
            "resumen": "R idx=$G(%B) bareK=$K bareP=$P",
            "texto": "TX idx=$G(%B) bareK=$K bareP=$P end",
        }
    }


def _reason(report, var):
    return next(r["reason"] for r in report if r["var"] == var)


# ========================================================================
# derive_var_axis_map — indexed refs only
# ========================================================================

def test_derive_var_axis_map_indexed_refs_only():
    assert derive_var_axis_map(_concept()[_KEY]) == {"L": "B", "N": "D"}


def test_derive_var_axis_map_excludes_bare_refs():
    m = derive_var_axis_map(_mixed()[_KEY])
    assert m == {"G": "B"}            # K and P are bare-referenced → excluded


def test_derive_var_axis_map_excludes_multi_axis_conflict():
    item = _concept()[_KEY]
    item["resumen"] = "Canal ($Q(%B)/$N(%D))"
    item["texto"] = "Canal $Q(%D) $N(%D)"
    assert "Q" not in derive_var_axis_map(item)


# ========================================================================
# list_to_formula — the three shapes
# ========================================================================

def test_list_plain_converts_to_condition_addressed_formula():
    conv, report = list_to_formula(_concept())
    tvs = conv[_KEY]["text_variables"]
    assert tvs["L"] == '"Diurno" * (%B=a) + "Nocturno" * (%B=b)'
    assert tvs["N"] == '"Rel" * (%D=a) + "Esc" * (%D=b)'
    assert _reason(report, "L") == "converted"


def test_str_formula_is_passthrough():
    conv, report = list_to_formula(_mixed())
    assert conv[_KEY]["text_variables"]["K"] == _mixed()[_KEY]["text_variables"]["K"]
    assert _reason(report, "K") == "already_formula"


def test_list_conditional_joins_for_enumeration():
    conv, report = list_to_formula(_mixed(), include_conditional=True)
    assert conv[_KEY]["text_variables"]["P"] == \
        '"p_a" * (%B=="a") + "p_b" * (%B=="b")'   # joined verbatim
    assert _reason(report, "P") == "joined_conditional"


def test_list_conditional_stays_native_when_excluded():
    conv, report = list_to_formula(_mixed(), include_conditional=False)
    assert conv[_KEY]["text_variables"]["P"] == _mixed()[_KEY]["text_variables"]["P"]
    assert _reason(report, "P") == "native_conditional"


def test_list_to_formula_is_pure():
    c = _mixed()
    before = copy.deepcopy(c)
    list_to_formula(c)
    assert c == before


# ========================================================================
# Edge cases (recorded, never silent)
# ========================================================================

def test_edge_unreferenced_plain_list_left_alone():
    c = _concept()
    c[_KEY]["text_variables"]["S"] = ['"x"', '"y"']
    conv, report = list_to_formula(c)
    assert _reason(report, "S") == "unreferenced"
    assert conv[_KEY]["text_variables"]["S"] == ['"x"', '"y"']


def test_edge_length_mismatch_left_alone():
    c = _concept()
    c[_KEY]["text_variables"]["L"] = ['"only-one"']
    conv, report = list_to_formula(c)
    assert _reason(report, "L") == "length_mismatch"


def test_edge_embedded_quote_plain_list_left_alone():
    c = _concept()
    c[_KEY]["text_variables"]["L"] = ['"clean"', '"3 > "5" h"']
    conv, report = list_to_formula(c)
    assert _reason(report, "L") == "embedded_quote"
    assert isinstance(conv[_KEY]["text_variables"]["L"], list)


def test_edge_unsupported_shape_left_alone():
    c = _concept()
    c[_KEY]["text_variables"]["L"] = 123
    conv, report = list_to_formula(c)
    assert _reason(report, "L") == "unsupported_shape"


# ========================================================================
# formula_to_list — restores ONLY indexed-referenced vars
# ========================================================================

def test_formula_to_list_restores_indexed_plain_to_list():
    conv, _ = list_to_formula(_concept())
    back = formula_to_list(conv)
    assert back[_KEY]["text_variables"]["L"] == ['"Diurno"', '"Nocturno"']
    assert back[_KEY]["text_variables"]["N"] == ['"Rel"', '"Esc"']


def test_formula_to_list_does_not_corrupt_bare_str_formula():
    # the latent bug: a bare-referenced STR_formula must NOT be turned into a list
    conv, _ = list_to_formula(_mixed(), include_conditional=False)
    back = formula_to_list(conv)
    assert back[_KEY]["text_variables"]["K"] == _mixed()[_KEY]["text_variables"]["K"]
    assert isinstance(back[_KEY]["text_variables"]["K"], str)


def test_formula_to_list_leaves_native_conditional_list():
    conv, _ = list_to_formula(_mixed(), include_conditional=False)
    back = formula_to_list(conv)
    assert back[_KEY]["text_variables"]["P"] == _mixed()[_KEY]["text_variables"]["P"]


def test_apply_mode_round_trip_is_byte_identity_all_shapes():
    c = _mixed()
    appl, _ = list_to_formula(c, include_conditional=False)
    back = formula_to_list(appl)
    assert back[_KEY]["text_variables"] == c[_KEY]["text_variables"]


def test_formula_to_list_handles_pd_added_indexed_axis():
    c = _concept()
    c[_KEY]["parameters"]["Z"] = {"label": "EXTRA", "values": [
        {"label": "a", "value": "zz"}, {"label": "b", "value": "yy"}]}
    c[_KEY]["text_variables"]["Z"] = '"alpha" * (%Z=a) + "beta" * (%Z=b)'
    c[_KEY]["texto"] += " extra $Z(%Z)"   # PD injects an indexed reference
    back = formula_to_list(c)
    assert back[_KEY]["text_variables"]["Z"] == ['"alpha"', '"beta"']


# ========================================================================
# Byte-faithful baseline + mutated round-trip through the real rerun
# ========================================================================

def test_unmutated_round_trip_reproduces_baseline_rerun_exactly():
    c = _mixed()
    appl, _ = list_to_formula(c, include_conditional=False)
    restored = formula_to_list(appl)
    assert run_stages_3_to_7(restored) == run_stages_3_to_7(c)


def test_mutated_plain_var_lands_in_expected_leaves():
    c = _concept()
    appl, _ = list_to_formula(c, include_conditional=False)
    mutated, log = mutator.apply_l2(
        appl, _KEY, [{"type": "paraphrase", "var": "L", "condition": "%B=a", "new": "DIA_X"}])
    # Sprint 31: $L is indexed-referenced (`$L(%B)`) so it has a twin axis B.
    # The paraphrase now also carries into param B value "a" (which was "Diurno")
    # → status "paired". Both resumen ($L(%B)) and texto ($L(%B) here too, but
    # the paired L1 also updates param B for callers that render `$B`) move
    # together.
    assert [m.status for m in log] == ["applied", "paired"]
    items = run_stages_3_to_7(formula_to_list(mutated))
    import json
    hits = [k for k, v in items.items() if "DIA_X" in json.dumps(v, ensure_ascii=False)]
    assert len(items) == 4 and len(hits) == 2


def test_mutated_conditional_var_applies_natively_and_renders():
    c = _mixed()
    appl, _ = list_to_formula(c, include_conditional=False)   # P stays a native list
    mutated, log = mutator.apply_l2(
        appl, _KEY, [{"type": "paraphrase", "var": "P", "condition": '%B=="a"', "new": "P_X"}])
    assert [m.status for m in log] == ["applied"]
    items = run_stages_3_to_7(formula_to_list(mutated))
    rendered = " ".join(v.get("resumen", "") for v in items.values())
    assert "P_X" in rendered


# ========================================================================
# Guard
# ========================================================================

def test_guard_counts_targets_across_all_shapes():
    # _mixed (axis B has 2 values): G(plain→2) + K(str→2) + P(joined→2) = 6
    assert assert_l2_targets_or_warn(_mixed()) == 6


def test_guard_warns_when_enumerable_but_zero_targets(monkeypatch, caplog):
    monkeypatch.setattr(l2_repr, "enumerate_targets", lambda *a, **k: iter([]))
    with caplog.at_level("WARNING"):
        n = assert_l2_targets_or_warn(_concept())
    assert n == 0
    assert any("silent-no-op" in rec.message for rec in caplog.records)


def test_guard_silent_when_nothing_made_enumerable(caplog):
    c = _concept()
    c[_KEY]["text_variables"] = {"K": '"x" * (%B=="a")'}  # already a formula
    with caplog.at_level("WARNING"):
        assert_l2_targets_or_warn(c)
    assert not any("silent-no-op" in rec.message for rec in caplog.records)
