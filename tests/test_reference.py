from __future__ import annotations

import math
from decimal import Decimal

import pytest

from bc3param.fiebdc import Catalog
from bc3param.generate import build_item, iter_items, resolve_code, select_families, selections
from bc3param.param.evaluator import Evaluator
from bc3param.param.parser import ParseError
from bc3param.pricing import Pricer


@pytest.fixture(scope="module")
def catalog(raw_path) -> Catalog:
    return Catalog.load(raw_path)


def quantities(item) -> dict[str, float]:
    return {l.code: float(l.quantity) for l in item.decomposition}


def test_catalog_shape(catalog):
    assert len(catalog.families_raw) == 2996
    assert len(catalog.concepts) > 28000
    assert catalog.decimals.DR == 4 and catalog.decimals.DI == 2


def test_every_family_parses(catalog):
    errors = []
    for code in catalog.families:
        try:
            catalog.family(code)
        except ParseError as exc:
            errors.append(str(exc))
    assert errors == []
    # two known leftovers in the source (a bare "0" and a dangling "(%D)*%P(%C)") are tolerated
    tolerated = {code: catalog.family(code).warnings for code in catalog.families if catalog.family(code).warnings}
    assert set(tolerated) == {"ETB090$", "VCD030$"}


def test_au10100001_price_from_decomposition_matches_c_record(catalog):
    pc = Pricer(catalog).concept_price("AU10100001")
    assert pc.price == Decimal("88.39")
    assert [l.code for l in pc.lines][:3] == ["MOC0000100", "MOC0000400", "MOC0000500"]
    assert not any("differs" in w for w in pc.warnings)


def test_oeb010aaa_matches_viewer(catalog):
    item = resolve_code(catalog, "OEB010aaa")
    assert item.valid and item.chapter_path == ["O#", "OE#", "OEB#"]
    q = quantities(item)
    assert q["MOC0000100"] == 0.3667 and q["MOC0000200"] == 1.25 and q["MOC0000500"] == 3.667
    assert q["MQ04020010"] == 0.6667 and q["MQ05000010"] == 0.0833
    assert q["MN10010019"] == 5 and q["MN10010021"] == 2 and q["MN10010020"] == 4
    assert q["MN10010018"] == 6 and q["MN10010022"] == 4 and q["MN01010001"] == 0.076
    assert q["AU10100001"] == 1.35 and q["%CIND"] == 0.06
    assert item.resumen.endswith("(-/-/D)")
    assert item.resumen.startswith("Ejecución de canalización para línea subterranea doble circuito")
    assert "En terreno blando , sin reposición de pavimento." in item.texto
    assert item.texto.endswith("Condiciones de ejecución: Volumen relevante.")
    cind = [l for l in item.decomposition if l.code == "%CIND"][0]
    assert cind.price == item.direct_cost
    assert item.price == item.direct_cost + cind.amount


def test_oeb020bbbaa_matches_viewer_structure(catalog):
    item = resolve_code(catalog, "OEB020bbbaa")
    assert item.valid
    assert [p.letter for p in item.parameters] == ["b", "b", "b", "a", "a"]
    q = quantities(item)
    assert set(q) == {"MOC0000101", "MOC0000601", "MOC0000501", "MQ04000600", "MQ05020300", "MQ04070420",
                      "MQ03000005", "MQ0103D105", "MN10010001", "AU10100001", "%CIND"}
    assert q["MN10010001"] == 4 and q["AU10100001"] == 0.165
    assert q["MOC0000601"] == round(0.372 * 1.1, 4) and q["MQ04000600"] == 0.118
    assert item.resumen == "Canalización hormigonada de 4 T, PVC 110 mm, bajo vías. (N/>5/R)"
    assert item.texto.startswith(
        "Canalización hormigonada de 4 tubos de PVC de 110 mm de diámetro en cruce bajo vías, incluso el "
        "descerne y la entibación de los costados y la posterior reposición del balasto retirado, el relleno"
    )
    assert "Trabajo: Nocturno" in item.texto and "Banda de mantenimiento: i >= 5 horas" in item.texto


def test_oeb020_excluded_combination(catalog):
    item = resolve_code(catalog, "OEB020ahaaa")  # 2 tubos con topo
    assert not item.valid and item.error == "Combinación inexistente en la base de datos"


def test_cla020_one_based_arithmetic(catalog):
    fam = catalog.family("CLA020$")
    assert not Evaluator(fam, (1, 1, 1, 1)).run().valid
    ev = Evaluator(fam, (2, 1, 1, 1)).run()
    assert ev.valid and dict(ev.lines)["MOE0000100"] == pytest.approx(55.857 + 5 * 8.379)


def test_eka100_sequential_redefinition_evaluates_everywhere(catalog):
    fam = catalog.family("EKA100$")
    for sel in selections(fam):
        Evaluator(fam, sel).run()


def test_eib030_text_array_with_literal_index(catalog):
    fam = catalog.family("EIB030$")
    ev = Evaluator(fam, tuple(1 for _ in fam.params)).run()
    assert ev.texto and "interruptor" in ev.texto


def test_all_families_evaluate_first_selection_without_crash(catalog):
    pricer = Pricer(catalog)
    crashes = []
    for code in catalog.families:
        fam = catalog.family(code)
        sel = tuple(1 for _ in fam.params)
        try:
            build_item(catalog, pricer, fam, sel)
        except Exception as exc:  # noqa: BLE001 - we want the full list
            crashes.append(f"{code}: {exc}")
    assert crashes == []


def test_oeb_chapter_expands_to_expected_count(catalog):
    codes = select_families(catalog, chapter="OEB#")
    assert "OEB020$" in codes
    total = sum(math.prod(catalog.family(c).option_counts()) for c in codes)
    assert total == 47508
    n = sum(1 for _ in iter_items(catalog, codes, include_invalid=True, with_decomposition=False))
    assert n == 47508
