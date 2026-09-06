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


def test_materialize_variant_bc3param_items_and_mods(cat):
    from synthetic import stage_b
    from synthetic.variant_catalog import VariantRecord
    from synthetic.taxonomy import ModificationType
    variant = VariantRecord(
        condition="single_compression",
        modification_type=ModificationType.COMPRESSION,
        target_id_repr="(('K','%B==\"b\"'),)",
        rules=({"type": "compression", "var": "K", "condition": '%B=="b"', "new": "muy rocoso"},),
    )
    mv = stage_b.materialize_variant_bc3param({"OEB020$": {}}, "OEB020$", variant)
    assert mv.concept_key == "OEB020$"
    assert mv.items["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."
    assert [m.to_dict() for m in mv.modifications] == [
        {"type": "compression", "layer": "text_variable", "var": "K",
         "condition": '%B=="b"', "new": "muy rocoso", "status": "applied"}
    ]


def test_apply_rules_logged_skips_unfindable_and_keeps_rest(cat):
    fam = cat.family("OEB020$")
    edited, applied = bk.apply_rules_logged(fam, [
        {"type": "compression", "var": "K", "condition": '%B=="z"', "new": "x"},  # skip
        {"type": "compression", "var": "K", "condition": '%B=="b"', "new": "muy rocoso"},  # applies
    ], "OEB020$")
    assert [r["condition"] for r in applied] == ['%B=="b"']
    from bc3param import mutate
    leaves = mutate.render_family_leaves(edited, ud="m", concept="CANAL")
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."


def test_apply_rules_strict_still_raises_on_unmapped(cat):
    import pytest as _pytest
    fam = cat.family("OEB020$")
    with _pytest.raises(KeyError):
        bk.apply_rules(fam, [{"type": "nope", "var": "K"}])


def test_field_rule_skipped_when_original_absent(cat):
    # reorder whose `original` (accented) is not in the template -> skipped, base kept
    fam = cat.family("OEB020$")
    edited, applied = bk.apply_rules_logged(fam, [
        {"type": "reorder", "field": "RESUMEN",
         "original": "Canal subterránea $A", "new": "X"},
    ], "OEB020$")
    assert applied == []
    from bc3param import mutate
    leaves = mutate.render_family_leaves(edited, ud="m", concept="CANAL")
    assert leaves["OEB020aa"]["resumen"] == "Canal 2 T, normal."
