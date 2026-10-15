"""Reparación de paráfrasis de plantilla rotas (César, 2026-10-16): los huecos
reasignados y los valores tratados como referencia se corrigen en la plantilla y
las consultas afectadas se vuelven a renderizar con sus mismos valores."""
from __future__ import annotations

import pytest

from synthetic.bt_alignment import Slot
from synthetic.paraphrase_repair import (
    PlaceholderMismatch,
    check_placeholders,
    render,
    repair_text,
    slot_values,
)


def _s(ph, text):
    return Slot(ph, 0, len(text), text)


def test_slot_values_maps_placeholder_to_surface():
    assert slot_values([_s("$A", "2"), _s("$I", "en terreno rocoso")]) == {
        "$A": "2", "$I": "en terreno rocoso"}


def test_slot_values_rejects_inconsistent_duplicates():
    with pytest.raises(ValueError):
        slot_values([_s("$A", "2"), _s("$A", "3")])


def test_render_fills_by_name_not_by_order():
    out = render("Canalización de $A tubos de 110 mm de diámetro $I.",
                 {"$I": "en andén", "$A": "2"})
    assert out == "Canalización de 2 tubos de 110 mm de diámetro en andén."


def test_render_keeps_argument_placeholders():
    assert render("Trabajo: $L(%C).", {"$L(%C)": "Nocturno"}) == "Trabajo: Nocturno."


def test_render_cleans_spaces_left_by_empty_values():
    assert render("incluso $N el relleno , y $P.", {"$N": "", "$P": "x"}) == \
        "incluso el relleno, y x."


def test_render_adds_space_after_colon():
    assert render("Banda:$C.", {"$C": "i >= 5 horas"}) == "Banda: i >= 5 horas."


def test_render_drops_leading_fiebdc_backslash():
    assert render("\\Canaleta $A.", {"$A": "PVC"}) == "Canaleta PVC."


def test_check_placeholders_accepts_same_multiset():
    check_placeholders("de $A con $I y $L(%C)", "con $I, $L(%C) de $A")


@pytest.mark.parametrize("corrected", [
    "de $A con $I",                 # falta uno
    "de $A con $I $I y $L(%C)",     # duplicado
    "de $A con $X y $L(%C)",        # otro hueco
    "de $A con $I y $L(%D)",        # argumento distinto
])
def test_check_placeholders_rejects_mismatch(corrected):
    with pytest.raises(PlaceholderMismatch):
        check_placeholders("de $A con $I y $L(%C)", corrected)


def test_repair_text_rerenders_with_aligned_values():
    broken = "Conducción de $A conductos de 110 mm con un diámetro de $I mm."
    fixed = "Conducción de $A conductos de 110 mm de diámetro, $I."
    query = "Conducción de 2 conductos de 110 mm con un diámetro de en andén mm."
    assert repair_text(broken, fixed, query, {"$A": "2"}) == \
        "Conducción de 2 conductos de 110 mm de diámetro, en andén."
