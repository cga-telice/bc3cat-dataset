"""L2 rewrites of LIST-form text variables (retrieval D-043, option A).

`$T(2)="uno","dos"` referenced as `$T(%B)` is a positional list: the leaf with
B = option k shows element k. The L2 menus address it as `%B=<option>` (the
`l2_repr` LIST_plain convention), but `bc3param.mutate` only edits the
`"frag"*(cond)` formula form, so those rules were skipped as no-ops. The backend
now maps `%B=b` to element b, and only when the list is unambiguously indexed
by that one axis.
"""
from __future__ import annotations

import pytest

from bc3param import mutate
from bc3param.fiebdc import Catalog
from synthetic import bc3param_backend as bk

RAW = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|OEX010$|m|LISTA||||\n"
    "~P|OEX010$|\\NUM\\ 2 \\ 4 \\\n"
    "\\TIPO\\Normal\\Rocoso\\\n"
    "$T(2)=\"sobre terreno normal\",\"sobre roca\"\n"
    "$M(2)=\"corto\",\"largo\"\n"
    "$L(2,2)=\"a1\",\"a2\",\"b1\",\"b2\"\n"
    "\\RESUMEN\\Canal $A T ($M(%A)).\\\n"
    "\\TEXTO\\Canal de $A tubos $T(%B). Tramo $M(%A), $M(%B). Fila $L(%A,%B).\\|\n"
)


@pytest.fixture
def cat(tmp_path):
    f = tmp_path / "mini.bc3"
    f.write_bytes(RAW.encode("cp1252"))
    return Catalog.load(f)


@pytest.fixture(autouse=True)
def _use_cat(cat, monkeypatch):
    monkeypatch.setattr(bk, "_catalog", lambda: cat)


def _texto(fam):
    return {k: v["texto"] for k, v in mutate.render_family_leaves(fam).items()}


def test_list_element_rewritten_for_its_option_only(cat):
    fam = cat.family("OEX010$")
    before = _texto(fam)
    out = bk.apply_rules(fam, [{"type": "expansion", "var": "T", "condition": "%B=b",
                                "new": "sobre terreno rocoso"}])
    after = _texto(out)
    for key in before:
        if key.endswith("b"):   # B = b
            assert after[key] == before[key].replace("sobre roca", "sobre terreno rocoso")
            assert after[key] != before[key]
        else:
            assert after[key] == before[key]


@pytest.mark.parametrize("cond", ['%B=="b"', "%B = b"])
def test_legacy_condition_spellings_accepted(cat, cond):
    out = bk.apply_rules(cat.family("OEX010$"), [{"type": "paraphrase", "var": "T",
                                                   "condition": cond, "new": "en roca"}])
    assert "en roca" in _texto(out)["OEX010ab"]


def test_original_recorded_for_list_element(cat):
    _, applied = bk.apply_rules_logged(
        cat.family("OEX010$"),
        [{"type": "compression", "var": "T", "condition": "%B=a", "new": "normal"}],
    )
    assert applied[0]["original"] == "sobre terreno normal"


@pytest.mark.parametrize("rule", [
    # $M is indexed by two different axes: `%A=b` does not name one element's leaves.
    {"type": "paraphrase", "var": "M", "condition": "%A=b", "new": "extenso"},
    # a matrix is not a single-axis list
    {"type": "paraphrase", "var": "L", "condition": "%A=b", "new": "x"},
    # the condition's axis does not index $T
    {"type": "paraphrase", "var": "T", "condition": "%A=b", "new": "x"},
    # option out of range / compound condition
    {"type": "paraphrase", "var": "T", "condition": "%B=c", "new": "x"},
    {"type": "paraphrase", "var": "T", "condition": "%B=a@%B=b", "new": "x"},
])
def test_ambiguous_list_rules_still_skipped(cat, rule):
    fam = cat.family("OEX010$")
    out, applied = bk.apply_rules_logged(fam, [rule])
    assert applied == []
    assert _texto(out) == _texto(fam)


def test_formula_form_unchanged(tmp_path, monkeypatch):
    # the formula path must not route through the list fallback
    raw = RAW.replace('$T(2)="sobre terreno normal","sobre roca"',
                      '$T="sobre terreno normal"*(%B=a)+"sobre roca"*(%B=b)').replace("$T(%B)", "$T")
    f = tmp_path / "f.bc3"
    f.write_bytes(raw.encode("cp1252"))
    c = Catalog.load(f)
    monkeypatch.setattr(bk, "_catalog", lambda: c)
    out = bk.apply_rules(c.family("OEX010$"), [{"type": "expansion", "var": "T",
                                                "condition": "%B=b", "new": "en roca viva"}])
    assert "en roca viva" in _texto(out)["OEX010ab"]
