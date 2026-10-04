"""BT (opción A), T1 — tests de :mod:`synthetic.bt_masking`.

Enmascarado de superficie para la back-translation: expresiones de banda
completas, tokens con dígito (con su unidad), códigos con dígito y siglas
(decisión de César en CP1: las siglas se protegen, no solo se avisan).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from synthetic.bt_masking import (
    MARKER_RE,
    MaskError,
    check_masks,
    mask_surface,
    unmask_surface,
)

_REPO = Path(__file__).resolve().parents[2]
_HANDOFF = _REPO / "data" / "synthetic" / "handoff_OE"

_STRATEGIES = ("sentinel", "xml", "none")


def _literals(text: str, strategy: str = "sentinel") -> list[str]:
    _, mapping = mask_surface(text, strategy)
    return list(mapping.values())


# --- bandas ---------------------------------------------------------------

@pytest.mark.parametrize("band", ["i >= 5 horas", "3 <= i < 5 horas", "i < 3 horas"])
def test_band_is_masked_whole(band):
    text = f"Banda de mantenimiento: {band} Condiciones de ejecución: Normal."
    assert _literals(text) == [band]


def test_band_with_leading_space_value():
    # los valores del corpus llevan espacio inicial (" i >= 5 horas")
    text = "Banda de mantenimiento:  i >= 5 horas."
    masked, mapping = mask_surface(text, "sentinel")
    assert list(mapping.values()) == ["i >= 5 horas"]
    assert "<" not in masked and ">" not in masked


def test_band_glued_to_colon():
    # 108 TEXTOS del corpus: "mantenimiento:3 <= i < 5 horas"
    masked, mapping = mask_surface("Banda de mantenimiento:3 <= i < 5 horas.", "sentinel")
    assert list(mapping.values()) == ["3 <= i < 5 horas"]
    assert masked == "Banda de mantenimiento:[[B1]]."


def test_stray_operator_is_masked():
    # 1 consulta STACKED degenerada: "Área de  <= ."
    assert _literals("Área de  <= . Circunstancias") == ["<="]


@pytest.mark.parametrize("band", ["i ≥ 5 horas", "3 ≤ i < 5 horas"])
def test_band_unicode_operators(band):
    assert _literals(f"Banda: {band}.") == [band]


# --- cantidades y códigos -------------------------------------------------

@pytest.mark.parametrize(
    "text, literal",
    [
        ("con hormigón HE-20, vertido", "HE-20"),
        ("canaleta de 30x15 mm con tapa", "30x15 mm"),
        ("canaleta de 3x1.5 cm con tapa", "3x1.5 cm"),
        ("de 1,60 m de alto", "1,60 m"),
        ("altura de 1,60 sobre rasante", "1,60"),
        ("de 220 ó 400 kV en terreno", "220"),
    ],
)
def test_quantities_and_codes_are_protected(text, literal):
    assert literal in _literals(text)


@pytest.mark.parametrize("text", ["hasta 1 m. , desde", "hasta 1 m.. Profundidad"])
def test_unit_followed_by_periods(text):
    # OED180: "hasta 1 m. ." en el gold, "hasta 1 m.." tras deshacer la expansión
    assert _literals(text) == ["1 m"]


def test_non_unit_word_after_number_is_not_swallowed():
    assert _literals("2 ternas de tubos") == ["2"]


def test_placeholder_after_number_is_not_swallowed():
    # en superficie no hay placeholders, pero si aparece uno pegado a un
    # número no puede tragarse como pseudo-unidad
    masked, mapping = mask_surface("clase 5.6 $L(%C) de acero", "sentinel")
    assert list(mapping.values()) == ["5.6"]
    assert "$L(%C)" in masked


# --- siglas ---------------------------------------------------------------

@pytest.mark.parametrize("sigla", ["PVC", "PRFV", "ADIF", "CA", "II", "PE"])
def test_acronym_is_masked(sigla):
    assert _literals(f"tubo de {sigla} reforzado") == [sigla]


@pytest.mark.parametrize("sigla", ["E.T.", "P.M."])
def test_dotted_acronym_keeps_its_dots(sigla):
    assert _literals(f"compactado al 95% {sigla} y regado") == ["95%", sigla]


def test_acronym_at_sentence_end_leaves_the_period():
    masked, mapping = mask_surface("Instalación en CA. Incluso pruebas.", "sentinel")
    assert list(mapping.values()) == ["CA"]
    assert masked.startswith("Instalación en [[S1]]. Incluso")


def test_single_capital_and_titlecase_are_not_acronyms():
    assert _literals("Normal y Bajo vías. A pie de obra") == []


# --- estrategias ----------------------------------------------------------

def test_sentinel_markers_by_kind():
    masked, mapping = mask_surface("PVC de 30x15 mm, banda i < 3 horas", "sentinel")
    assert masked == "[[S1]] de [[Q1]], banda [[B1]]"
    assert mapping == {"[[S1]]": "PVC", "[[Q1]]": "30x15 mm", "[[B1]]": "i < 3 horas"}


def test_xml_markers_are_numbered_in_order():
    masked, mapping = mask_surface("PVC de 30x15 mm, banda i < 3 horas", "xml")
    assert masked == "<x1/> de <x2/>, banda <x3/>"
    assert mapping == {"<x1/>": "PVC", "<x2/>": "30x15 mm", "<x3/>": "i < 3 horas"}


def test_none_strategy_masks_nothing():
    text = "PVC de 30x15 mm, banda i < 3 horas"
    assert mask_surface(text, "none") == (text, {})


def test_unknown_strategy_fails():
    with pytest.raises(ValueError):
        mask_surface("x", "brackets")


# --- comprobación y desenmascarado ----------------------------------------

def test_check_masks_passes_when_every_marker_once():
    masked, mapping = mask_surface("PVC de 30x15 mm", "sentinel")
    check_masks("The [[Q1]] made of [[S1]]", mapping)  # el orden puede cambiar


@pytest.mark.parametrize(
    "translated, needle",
    [
        ("[[S1]] de 30x15 mm", "missing"),          # máscara perdida
        ("[[S1]] [[S1]] de [[Q1]]", "extra_or_dup"),  # duplicada
        ("[[S1]] de [[Q1]] [[Q9]]", "extra_or_dup"),  # inventada
    ],
)
def test_check_masks_fails_loud(translated, needle):
    _, mapping = mask_surface("PVC de 30x15 mm", "sentinel")
    with pytest.raises(MaskError, match=needle):
        check_masks(translated, mapping)


def test_check_masks_none_strategy_rejects_stray_markers():
    with pytest.raises(MaskError):
        check_masks("texto con [[Q1]]", {})


def test_unmask_restores_literals():
    masked, mapping = mask_surface("PVC de 30x15 mm", "xml")
    assert unmask_surface("The <x2/> of <x1/>", mapping) == "The 30x15 mm of PVC"


def test_marker_re_matches_both_strategies():
    assert MARKER_RE.findall("[[B1]] y <x12/>") == ["[[B1]]", "<x12/>"]


# --- corpus completos (se saltan si los ficheros no están) ----------------

def _load_texts(name: str) -> list[str]:
    path = _HANDOFF / name
    if not path.exists():
        pytest.skip(f"{name} no está en disco")
    return [r["text"] for r in json.loads(path.read_text(encoding="utf-8"))]


_RESIDUE = re.compile(r"\d|<=|>=|[<>≤≥]")


@pytest.mark.parametrize("name", ["OE_texto.json", "OE_stacked_texto.json"])
@pytest.mark.parametrize("strategy", _STRATEGIES)
def test_roundtrip_identity_on_corpus(name, strategy):
    texts = _load_texts(name)
    for text in texts:
        masked, mapping = mask_surface(text, strategy)
        check_masks(masked, mapping)
        assert unmask_surface(masked, mapping) == text


@pytest.mark.parametrize("name", ["OE_texto.json", "OE_stacked_texto.json"])
def test_no_digit_or_operator_survives_masking(name):
    for text in _load_texts(name):
        masked, _ = mask_surface(text, "sentinel")
        residue = MARKER_RE.sub("", masked)
        assert not _RESIDUE.search(residue), (text, residue)


# --- valores de eje protegidos (rediseño tras CP2) ------------------------

from synthetic.bt_masking import check_value_order, mask_with_values  # noqa: E402

_VTEXT = "Canaleta PVC de 30x15 mm. Trabajo: Turno de día 2. Banda: i < 3 horas."


def _span(text, sub):
    i = text.index(sub)
    return (i, i + len(sub))


def test_value_spans_become_v_markers():
    spans = [_span(_VTEXT, "Turno de día 2"), _span(_VTEXT, "i < 3 horas")]
    masked, mapping, values = mask_with_values(_VTEXT, "sentinel", spans)
    assert masked == "Canaleta [[S1]] de [[Q1]]. Trabajo: [[V1]]. Banda: [[V2]]."
    assert values == ["[[V1]]", "[[V2]]"]
    assert mapping["[[V1]]"] == "Turno de día 2"  # el dígito va dentro del valor


def test_value_markers_xml_numbering_in_text_order():
    spans = [_span(_VTEXT, "Turno de día 2")]
    masked, mapping, values = mask_with_values(_VTEXT, "xml", spans)
    assert masked == "Canaleta <x1/> de <x2/>. Trabajo: <x3/>. Banda: <x4/>."
    assert values == ["<x3/>"]


def test_empty_spans_are_ignored():
    masked, mapping, values = mask_with_values("A B", "sentinel", [(1, 1)])
    assert values == [] and masked == "A B"


@pytest.mark.parametrize("strategy", ["sentinel", "xml"])
def test_value_roundtrip_identity(strategy):
    spans = [_span(_VTEXT, "Turno de día 2"), _span(_VTEXT, "i < 3 horas")]
    masked, mapping, _ = mask_with_values(_VTEXT, strategy, spans)
    check_masks(masked, mapping)
    assert unmask_surface(masked, mapping) == _VTEXT


def test_value_order_check():
    values = ["[[V1]]", "[[V2]]"]
    check_value_order("x [[Q1]] [[V1]] y [[S1]] [[V2]]", values)
    check_value_order("[[S1]] [[V1]] [[Q1]] [[V2]]", values)  # otros marcadores pueden moverse
    with pytest.raises(MaskError, match="value_order_changed"):
        check_value_order("[[V2]] y [[V1]]", values)
