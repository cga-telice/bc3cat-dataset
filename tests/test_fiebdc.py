from __future__ import annotations

from decimal import Decimal

import pytest

from bc3param.fiebdc import Bc3Error, Catalog, iter_records

SNIPPET = (
    "~V||FIEBDC-3/2007\\260224|menfis 8.2.117|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|R_A_I_Z##||BASE PRECIOS||||\n"
    "~C|O#||OBRA CIVIL||||\n"
    "~C|OEB#||ZANJAS||||\n"
    "~C|OEB020$|m|CANALIZACIÓN HORMIGONADA||21022019||\n"
    "~C|MOC0000100|h|CAPATAZ|22.66||1|\n"
    "~C|MN01060004|m³|HORMIGÓN|73.88|15111998|3|\n"
    "~C|AU10100001|m³|HORMIGÓN EN MASA|88.39||EA|\n"
    "~C|%CIND|%|Costes indirectos|||%|\n"
    "~D|R_A_I_Z##|O#\\\\\\|\n"
    "~D|O#|OEB#\\\\\\|\n"
    "~D|OEB#|OEB020$\\\\\\OEB060\\\\\\|\n"
    "~D|AU10100001|MOC0000100\\\\0.0080\\MN01060004\\\\1.0500\\|\n"
    "~T|MOC0000100|Capataz de obra|\n"
    "~P|OEB020$|\\Nº TUBOS\\2\\4\\\n"
    "#comentario\n"
    "%%CIND: 0.06\n"
    "\\RESUMEN\\Canal $A\\\n"
    "\\TEXTO\\Texto $A\n"
    "Trabajo: x\\|\n"
    "~C|ZZZ|u|after|1||3|\n"
)


def test_iter_records_splits_and_keeps_p_body():
    recs = list(iter_records(SNIPPET))
    kinds = [r.kind for r in recs]
    assert kinds == ["V", "K"] + ["C"] * 8 + ["D"] * 4 + ["T", "P", "C"]
    p = [r for r in recs if r.kind == "P"][0]
    assert p.fields[0] == "OEB020$"
    assert p.fields[1].startswith("\\Nº TUBOS\\2\\4\\\n#comentario")
    assert p.fields[1].endswith("Trabajo: x\\")  # trailing '|' removed, closing '\' kept
    assert p.line_no == 16
    c = recs[2]
    assert c.fields == ["R_A_I_Z##", "", "BASE PRECIOS", "", "", ""]


def test_catalog_concepts_and_prices():
    cat = Catalog.from_text(SNIPPET)
    assert cat.version == "FIEBDC-3/2007\\260224"
    c = cat.concept("MOC0000100")
    assert c.unit == "h" and c.summary == "CAPATAZ" and c.price == Decimal("22.66") and c.type == "1"
    assert cat.concept("%CIND").price is None
    assert cat.concept("OEB").summary == "ZANJAS"  # '#' is optional in references
    assert cat.concept("nope") is None


def test_catalog_decimals_from_k_record():
    cat = Catalog.from_text(SNIPPET)
    assert (cat.decimals.DR, cat.decimals.DI, cat.decimals.DP, cat.decimals.DC) == (4, 2, 2, 2)


def test_catalog_decompositions():
    cat = Catalog.from_text(SNIPPET)
    refs = cat.decompositions["AU10100001"]
    assert [(r.child, r.factor, r.yield_) for r in refs] == [
        ("MOC0000100", Decimal(1), Decimal("0.0080")),
        ("MN01060004", Decimal(1), Decimal("1.0500")),
    ]
    assert cat.children("OEB#") == ["OEB020$", "OEB060"]


def test_catalog_chapter_path_and_families():
    cat = Catalog.from_text(SNIPPET)
    assert cat.chapter_path("OEB020$") == ["O#", "OEB#"]
    assert cat.chapter_path("MOC0000100") == []
    assert list(cat.families_raw) == ["OEB020$"]
    assert cat.texts["MOC0000100"] == "Capataz de obra"


def test_empty_input_raises():
    with pytest.raises(Bc3Error):
        Catalog.from_text("")
