from __future__ import annotations

import pytest

from bc3param.mutate import (
    normalize_condition,
    render_family_leaves,
    replace_option_value,
    replace_template,
    replace_template_substring,
    replace_text_fragment,
)
from bc3param.param.ast import Binary, Str
from bc3param.param.parser import parse_family

FAMILY = (
    "\\Nº TUBOS \\ 2 \\ 4 \\\n"
    "\\TIPO DE TERRENO \\Normal\\Rocoso\\\n"
    "$K= \"normal\" * (%B=a) + \"rocoso\" * (%B=b)\n"
    "MN10010001 : 1*%A\n"
    "\\RESUMEN\\Canal $A T, $K.\\\n"
    "\\TEXTO\\Canal de $A tubos $K.\\\n"
)

FAMILY_DISJ = (
    "\\TIPO\\Normal\\Bajo\\Balasto\\\n"
    "$N= \"descerne,\" * (%A=b @ %A=c) + \"otro,\" * (%A=a)\n"
    "\\RESUMEN\\R $N\\\n"
    "\\TEXTO\\T $N\\\n"
)


def _collect_strs(expr):
    if isinstance(expr, Str):
        return [expr.value]
    if isinstance(expr, Binary):
        return _collect_strs(expr.left) + _collect_strs(expr.right)
    return []


def test_replace_option_value_edits_named_axis_and_is_pure():
    fam = parse_family("OEB020$", FAMILY)
    out = replace_option_value(fam, "B", "b", "muy rocoso")
    assert out.params[1].options == ("Normal", "muy rocoso")
    assert fam.params[1].options == ("Normal", "Rocoso")  # original untouched


def test_replace_option_value_unknown_target_raises():
    fam = parse_family("OEB020$", FAMILY)
    with pytest.raises(KeyError):
        replace_option_value(fam, "B", "z", "x")
    with pytest.raises(KeyError):
        replace_option_value(fam, "Z", "a", "x")


def test_normalize_condition_strips_s01_translation():
    assert normalize_condition('%B=="c"') == "%B=c"
    assert normalize_condition("%B==c") == "%B=c"
    assert normalize_condition('%A<>"b"') == "%A<>b"


def test_replace_text_fragment_by_condition():
    fam = parse_family("OEB020$", FAMILY)
    out = replace_text_fragment(fam, "K", '%B=="b"', "muy rocoso")
    k = [s for s in out.statements if getattr(s, "name", None) == "K"][0]
    strs = _collect_strs(k.values[0])
    assert "muy rocoso" in strs and "rocoso" not in strs
    assert "normal" in strs
    k0 = [s for s in fam.statements if getattr(s, "name", None) == "K"][0]
    assert "rocoso" in _collect_strs(k0.values[0])  # original untouched


def test_replace_text_fragment_no_match_raises():
    fam = parse_family("OEB020$", FAMILY)
    with pytest.raises(KeyError):
        replace_text_fragment(fam, "K", '%B=="z"', "x")


def test_replace_template_resumen_and_texto():
    fam = parse_family("OEB020$", FAMILY)
    out = replace_template(fam, "RESUMEN", "Nuevo resumen $A.")
    t = [s for s in out.statements if getattr(s, "label", None) == "RESUMEN"][0]
    assert t.template == "Nuevo resumen $A."
    t0 = [s for s in fam.statements if getattr(s, "label", None) == "RESUMEN"][0]
    assert t0.template == "Canal $A T, $K."


def test_replace_template_unknown_label_raises():
    fam = parse_family("OEB020$", FAMILY)
    with pytest.raises(KeyError):
        replace_template(fam, "PLIEGO", "x")


def test_render_family_leaves_shape_and_keys():
    fam = parse_family("OEB020$", FAMILY)
    leaves = render_family_leaves(fam, ud="m", concept="CANAL")
    assert set(leaves) == {"OEB020aa", "OEB020ab", "OEB020ba", "OEB020bb"}
    leaf = leaves["OEB020ab"]
    assert set(leaf) == {"parent_key", "ud", "concept", "resumen", "texto", "parameters"}
    assert leaf["parent_key"] == "OEB020$"
    assert leaf["parameters"] == {
        "A": {"label": "Nº TUBOS", "values": [{"label": "a", "value": " 2 "}]},
        "B": {"label": "TIPO DE TERRENO", "values": [{"label": "b", "value": "Rocoso"}]},
    }
    assert leaf["resumen"] == "Canal 2 T, rocoso."
    assert leaf["texto"] == "Canal de 2 tubos rocoso."


def test_render_family_leaves_reflects_edit():
    fam = parse_family("OEB020$", FAMILY)
    fam2 = replace_text_fragment(fam, "K", '%B=="b"', "muy rocoso")
    leaves = render_family_leaves(fam2, ud="m", concept="CANAL")
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."


def test_normalize_condition_translates_connectives_and_neq():
    # legacy Python-form conditions -> bc3param raw form
    assert normalize_condition('%B=="b"  or  %B=="g"') == "%B=b@%B=g"
    assert normalize_condition('%C=="a" and %D=="b"') == "%C=a&%D=b"
    assert normalize_condition('%A!="b"') == "%A<>b"
    assert normalize_condition('%A<>"b"') == "%A<>b"


def test_replace_text_fragment_matches_disjunctive_condition():
    fam = parse_family("OEB020$", FAMILY_DISJ)
    out = replace_text_fragment(fam, "N", '%A=="b"  or  %A=="c"', "REEMPLAZO")
    n = [s for s in out.statements if getattr(s, "name", None) == "N"][0]
    strs = _collect_strs(n.values[0])
    assert "REEMPLAZO" in strs and "descerne" not in " ".join(strs)


def test_replace_template_substring_whole_field_guarded():
    fam = parse_family("OEB020$", FAMILY)  # RESUMEN = "Canal $A T, $K."
    # original present (whitespace-insensitive) -> whole field replaced by new
    out = replace_template_substring(fam, "RESUMEN", "Canal  $A T,  $K.", "Zanja de $A tubos, $K.")
    t = [s for s in out.statements if getattr(s, "label", None) == "RESUMEN"][0]
    assert t.template == "Zanja de $A tubos, $K."
    with pytest.raises(KeyError):  # accent mismatch -> not found -> skip signal
        replace_template_substring(fam, "RESUMEN", "Canal subterránea $A T, $K.", "x")
