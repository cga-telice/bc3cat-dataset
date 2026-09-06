from __future__ import annotations

import pytest

from bc3param.fiebdc import Catalog
from synthetic import bc3param_backend as bk

RAW = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|OEB020$|m|CANAL||||\n"
    "~P|OEB020$|\\NUM\\ 2 \\ 4 \\\n"
    "\\TIPO\\Normal\\Rocoso\\\n"
    "$K= \"normal\"*(%B=a)+\"rocoso\"*(%B=b)\n"
    "\\RESUMEN\\Canal $A T, $K.\\\n"
    "\\TEXTO\\Canal de $A tubos $K. Terreno: $B.\\|\n"
)


@pytest.fixture
def cat(tmp_path):
    f = tmp_path / "mini.bc3"
    f.write_bytes(RAW.encode("cp1252"))
    return Catalog.load(f)


@pytest.fixture(autouse=True)
def _use_cat(cat, monkeypatch):
    monkeypatch.setattr(bk, "_catalog", lambda: cat)


def test_apply_rules_l2_text_fragment(cat):
    fam = cat.family("OEB020$")
    out = bk.apply_rules(fam, [{"type": "compression", "var": "K",
                                "condition": '%B=="b"', "new": "muy rocoso"}])
    from bc3param import mutate
    leaves = mutate.render_family_leaves(out, ud="m", concept="CANAL")
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."


def test_apply_rules_l1_option_value(cat):
    fam = cat.family("OEB020$")
    out = bk.apply_rules(fam, [{"type": "synonym_label", "param": "B", "value": "b",
                                "original": "Rocoso", "new": "Terreno Rocoso"}])
    from bc3param import mutate
    leaves = mutate.render_family_leaves(out, ud="m", concept="CANAL")
    assert leaves["OEB020ab"]["texto"].endswith("Terreno: Terreno Rocoso.")


def test_apply_rules_field_template(cat):
    fam = cat.family("OEB020$")
    out = bk.apply_rules(fam, [{"type": "template_paraphrase", "field": "RESUMEN",
                                "original": "Canal $A T, $K.", "new": "Zanja de $A tubos, $K."}])
    from bc3param import mutate
    leaves = mutate.render_family_leaves(out, ud="m", concept="CANAL")
    assert leaves["OEB020aa"]["resumen"] == "Zanja de 2 tubos, normal."


def test_apply_rules_new_param_raises(cat):
    fam = cat.family("OEB020$")
    with pytest.raises(NotImplementedError):
        bk.apply_rules(fam, [{"type": "new_param", "param": "E", "label": "X",
                              "values": [], "metadata": {}}])


def test_apply_rules_unmapped_raises(cat):
    fam = cat.family("OEB020$")
    with pytest.raises(KeyError):
        bk.apply_rules(fam, [{"type": "nonsense", "var": "K"}])


def test_render_base(cat):
    leaves = bk.render_base("OEB020$")
    assert set(leaves) == {"OEB020aa", "OEB020ab", "OEB020ba", "OEB020bb"}
    assert leaves["OEB020aa"]["ud"] == "m" and leaves["OEB020aa"]["concept"] == "CANAL"
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, rocoso."


def test_run_variant_applies_rules(cat):
    leaves = bk.run_variant("OEB020$", [{"type": "compression", "var": "K",
                                         "condition": '%B=="b"', "new": "muy rocoso"}])
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."
    # base render is unaffected by the variant edit (purity)
    assert bk.render_base("OEB020$")["OEB020ab"]["resumen"] == "Canal 2 T, rocoso."
