from __future__ import annotations

import io
import json

import pytest

from bc3param.fiebdc import Bc3Error, Catalog
from bc3param.generate import (
    build_item, iter_items, resolve_code, select_families, selections, write_json, write_jsonl,
)
from bc3param.model import Item
from bc3param.pricing import Pricer

SNIPPET = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|R_A_I_Z##||BASE||||\n"
    "~C|O#||OBRA CIVIL||||\n"
    "~C|OEB#||ZANJAS||||\n"
    "~C|OEC#||ARQUETAS||||\n"
    "~C|OEB020$|m|CANALIZACIÓN HORMIGONADA||21022019||\n"
    "~C|OEB030$|m|OTRA||||\n"
    "~C|OEC010$|ud|ARQUETA||||\n"
    "~C|OEB060|m|SIMPLE|5||3|\n"
    "~C|MOC0000101|h|CAPATAZ NOCTURNO|28.33||1|\n"
    "~C|MN10010001|m|TUBO PVC 110|3.21||3|\n"
    "~C|%CIND|%|Costes indirectos|||%|\n"
    "~D|R_A_I_Z##|O#\\\\\\|\n"
    "~D|O#|OEB#\\\\\\OEC#\\\\\\|\n"
    "~D|OEB#|OEB020$\\\\\\OEB030$\\\\\\OEB060\\\\\\|\n"
    "~D|OEC#|OEC010$\\\\\\|\n"
    "~P|OEB020$|\\Nº TUBOS \\ 2 \\ 4 \\\n"
    "\\TRABAJO\\Diurno\\Nocturno\\\n"
    "$E= \"Combinación inexistente\"\n"
    "%E= (%A=b & %B=b)\n"
    "%L(2)=2,4\n"
    "MOC0000101 : 0.05*(%B=b)\n"
    "MN10010001 : %L(%A)\n"
    "%%CIND: 0.06\n"
    "$G(2)=\"D\",\"N\"\n"
    "\\RESUMEN\\Canalización de $A T. ($G(%B))\\\n"
    "\\TEXTO\\Canalización de $A tubos.\nTrabajo: $B\\|\n"
    "~P|OEB030$|\\X\\a\\\nMN10010001: 1\\|\n"
    "~P|OEC010$|\\X\\a\\\nMN10010001: 2\\|\n"
)


@pytest.fixture
def cat() -> Catalog:
    return Catalog.from_text(SNIPPET)


def test_selections_order_last_parameter_fastest(cat):
    fam = cat.family("OEB020$")
    assert list(selections(fam)) == [(1, 1), (1, 2), (2, 1), (2, 2)]


def test_build_item_valid(cat):
    item = build_item(cat, Pricer(cat), cat.family("OEB020$"), (1, 2))
    assert isinstance(item, Item)
    d = item.to_dict()
    assert d["code"] == "OEB020ab" and d["family"] == "OEB020$" and d["unit"] == "m"
    assert d["family_summary"] == "CANALIZACIÓN HORMIGONADA"
    assert d["chapter_path"] == ["O#", "OEB#"]
    assert d["parameters"] == [
        {"var": "A", "name": "Nº TUBOS", "option": 1, "letter": "a", "label": " 2 "},
        {"var": "B", "name": "TRABAJO", "option": 2, "letter": "b", "label": "Nocturno"},
    ]
    assert d["resumen"] == "Canalización de 2 T. (N)"
    assert d["texto"] == "Canalización de 2 tubos.\nTrabajo: Nocturno"
    assert d["valid"] is True and d["error"] is None
    # 28.33*0.05=1.42 ; 3.21*2=6.42 ; direct 7.84 ; CIND 0.47 ; total 8.31
    assert d["direct_cost"] == 7.84 and d["price"] == 8.31
    assert d["decomposition"] == [
        {"code": "MOC0000101", "unit": "h", "summary": "CAPATAZ NOCTURNO", "type": "1",
         "price": 28.33, "quantity": 0.05, "amount": 1.42},
        {"code": "MN10010001", "unit": "m", "summary": "TUBO PVC 110", "type": "3",
         "price": 3.21, "quantity": 2.0, "amount": 6.42},
        {"code": "%CIND", "unit": "%", "summary": "Costes indirectos", "type": "%",
         "price": 7.84, "quantity": 0.06, "amount": 0.47},
    ]
    assert d["warnings"] == []
    assert list(d) == ["code", "family", "unit", "family_summary", "chapter_path", "parameters", "resumen",
                       "texto", "valid", "error", "direct_cost", "price", "decomposition", "warnings"]


def test_build_item_invalid_and_without_decomposition(cat):
    item = build_item(cat, Pricer(cat), cat.family("OEB020$"), (2, 2))
    d = item.to_dict()
    assert d["valid"] is False and d["error"] == "Combinación inexistente"
    assert d["price"] is None and d["direct_cost"] is None and d["decomposition"] == []
    assert d["resumen"] == "Canalización de 4 T. (N)"
    item = build_item(cat, Pricer(cat), cat.family("OEB020$"), (1, 1), with_decomposition=False)
    assert item.price is not None and item.decomposition == []


def test_select_families(cat):
    assert select_families(cat, chapter="OEB#") == ["OEB020$", "OEB030$"]
    assert select_families(cat, chapter="O#") == ["OEB020$", "OEB030$", "OEC010$"]
    assert select_families(cat, range_="OEB025..OEC010") == ["OEB030$", "OEC010$"]
    assert select_families(cat, families=["OEC010$", "OEB020"]) == ["OEB020$", "OEC010$"]
    with pytest.raises(Bc3Error):
        select_families(cat, families=["NOPE$"])
    with pytest.raises(Bc3Error):
        select_families(cat, chapter="ZZZ#")
    with pytest.raises(Bc3Error):
        select_families(cat)


def test_iter_items_and_writers(cat):
    items = list(iter_items(cat, ["OEB020$"]))
    assert [i.code for i in items] == ["OEB020aa", "OEB020ab", "OEB020ba"]
    items = list(iter_items(cat, ["OEB020$"], include_invalid=True))
    assert [i.code for i in items] == ["OEB020aa", "OEB020ab", "OEB020ba", "OEB020bb"]
    buf = io.StringIO()
    n = write_jsonl(iter_items(cat, ["OEB030$"]), buf)
    assert n == 1 and json.loads(buf.getvalue().strip())["code"] == "OEB030a"
    buf = io.StringIO()
    n = write_json(iter_items(cat, ["OEB030$", "OEC010$"]), buf)
    assert n == 2 and [x["code"] for x in json.loads(buf.getvalue())] == ["OEB030a", "OEC010a"]


def test_resolve_code(cat):
    assert resolve_code(cat, "OEB020ab").code == "OEB020ab"
    assert resolve_code(cat, "OEB020$", (1, 2)).code == "OEB020ab"
    with pytest.raises(Bc3Error):
        resolve_code(cat, "OEB020abc")
    with pytest.raises(Bc3Error):
        resolve_code(cat, "XXXXXXab")
