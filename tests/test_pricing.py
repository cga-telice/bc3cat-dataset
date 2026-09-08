from __future__ import annotations

from decimal import Decimal

import pytest

from bc3param.fiebdc import Bc3Error, Catalog
from bc3param.param.evaluator import Evaluation
from bc3param.pricing import Pricer, is_percentage, percentage_prefix, quantize

SNIPPET = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|MOC0000100|h|CAPATAZ|22.66||1|\n"
    "~C|MOC0000400|h|PEÓN ESPECIALISTA|21.00||1|\n"
    "~C|MOC0000500|h|PEÓN|20.66||1|\n"
    "~C|MN01060004|m³|HORMIGÓN|73.88||3|\n"
    "~C|AU10100001|m³|HORMIGÓN EN MASA HM-20|80.00||EA|\n"
    "~C|AU10100002|m³|AUX SIN LINEAS|||EA|\n"
    "~C|%CIND|%|Costes indirectos|||%|\n"
    "~C|%VOL|%|Sobrecoste por volumen escaso|||%|\n"
    "~C|MO%X|%|Sólo mano de obra|||%|\n"
    "~D|AU10100001|MOC0000100\\\\0.0080\\MOC0000400\\\\0.0800\\MOC0000500\\\\0.0400\\MN01060004\\\\1.0500\\|\n"
    "~D|CYC1|CYC2\\\\1\\|\n"
    "~D|CYC2|CYC1\\\\1\\|\n"
)


@pytest.fixture
def pricer() -> Pricer:
    return Pricer(Catalog.from_text(SNIPPET))


def test_quantize_half_up():
    assert quantize(Decimal("0.05115"), 4) == Decimal("0.0512")
    assert quantize(Decimal("0.08333"), 4) == Decimal("0.0833")
    assert quantize(Decimal("35.0778"), 2) == Decimal("35.08")


def test_percentage_helpers():
    assert is_percentage("%CIND") and is_percentage("MO%X") and not is_percentage("MOC0000100")
    assert percentage_prefix("%CIND") == "" and percentage_prefix("MO%X") == "MO"


def test_composite_price_from_decomposition_prevails_over_c_price(pricer):
    pc = pricer.concept_price("AU10100001")
    # 22.66*0.008=0.18 ; 21*0.08=1.68 ; 20.66*0.04=0.83 ; 73.88*1.05=77.57  -> 80.26
    assert [(l.code, l.quantity, l.amount) for l in pc.lines] == [
        ("MOC0000100", Decimal("0.0080"), Decimal("0.18")),
        ("MOC0000400", Decimal("0.0800"), Decimal("1.68")),
        ("MOC0000500", Decimal("0.0400"), Decimal("0.83")),
        ("MN01060004", Decimal("1.0500"), Decimal("77.57")),
    ]
    assert pc.price == Decimal("80.26")
    assert pc.unit == "m³" and pc.type == "EA"
    assert any("differs" in w for w in pc.warnings)
    assert pricer.concept_price("AU10100001") is pc  # cached


def test_simple_and_unknown_concepts(pricer):
    assert pricer.concept_price("MOC0000100").price == Decimal("22.66")
    unknown = pricer.concept_price("NOPE")
    assert unknown.price == 0 and unknown.warnings == ["unknown concept NOPE"]
    nolines = pricer.concept_price("AU10100002")
    assert nolines.price == 0 and nolines.warnings == ["AU10100002 has no price"]


def test_cycle_raises(pricer):
    with pytest.raises(Bc3Error):
        pricer.concept_price("CYC1")


def test_price_lines_with_percentages_and_masks(pricer):
    lines, total = pricer.price_lines([
        ("MOC0000100", 0.0558), ("MN01060004", 0.0), ("AU10100001", 0.165),
        ("MO%X", 0.10), ("%VOL", 0.20), ("%CIND", 0.06),
    ])
    assert [l.code for l in lines] == ["MOC0000100", "AU10100001", "MO%X", "%VOL", "%CIND"]
    assert lines[0].amount == Decimal("1.26")           # 22.66*0.0558=1.264
    assert lines[1].amount == Decimal("13.24")          # 80.26*0.165=13.243
    assert lines[2].price == Decimal("1.26") and lines[2].amount == Decimal("0.13")  # mask MO
    assert lines[3].price == Decimal("14.63") and lines[3].amount == Decimal("2.93")  # 20% of all previous incl. %
    assert lines[4].price == Decimal("17.56") and lines[4].amount == Decimal("1.05")
    assert lines[4].summary == "Costes indirectos" and lines[4].unit == "%"
    assert total == Decimal("18.61")


def test_price_evaluation(pricer):
    ev = Evaluation(lines=[("MOC0000100", 1.0), ("%CIND", 0.06)])
    lines, direct, total = pricer.price_evaluation(ev)
    assert direct == Decimal("22.66") and total == Decimal("24.02") and len(lines) == 2
    ev = Evaluation(direct_price=12.345)
    assert pricer.price_evaluation(ev) == ([], None, Decimal("12.35"))
    ev = Evaluation(lines=[("MOC0000100", 1.0)], aux_percent=0.03)
    lines, direct, total = pricer.price_evaluation(ev)
    assert lines[-1].code == "%" and lines[-1].summary == "Medios auxiliares" and total == Decimal("23.34")
