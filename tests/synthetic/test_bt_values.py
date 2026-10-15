"""BT de valores (opción A, vuelta tras CP4) — tests de :mod:`synthetic.bt_values`.

Los valores de eje y los fragmentos L2 son un conjunto cerrado: se traducen
una vez por la cadena ES→EN→X→ES, se filtran contra las hermanas y César
aprueba la tabla. Después cada marcador de valor se rellena con una variante
aprobada (o el original), a veces con la etiqueta del parámetro delante.
"""
from __future__ import annotations

import pytest

from synthetic.bt_values import (
    Candidate,
    filter_candidates,
    fill_values,
    label_present,
    menu_markdown,
    parse_menu,
    source_text,
    split_label,
)


# --- texto de entrada y separación de la etiqueta -------------------------

def test_source_text_puts_label_as_context():
    # en mayúsculas la etiqueta se enmascaraba como sigla y el MT no la veía
    assert source_text("Nocturno", "TRABAJO") == "Trabajo: Nocturno"
    assert source_text("4", "Nº TUBOS") == "Nº tubos: 4"
    assert source_text("en cruce bajo vías", None) == "en cruce bajo vías"


@pytest.mark.parametrize(
    "translated, label, value",
    [
        ("TRABAJO: Noche", "Trabajo", "Noche"),
        ("Horario : turno nocturno", "Horario", "turno nocturno"),
    ],
)
def test_split_label(translated, label, value):
    assert split_label(translated) == (label, value)


def test_split_label_without_colon_fails():
    assert split_label("Trabajo nocturno") is None


# --- filtro automático ----------------------------------------------------

def _c(surface, option, variant, pivot="fr"):
    return Candidate(concept="OEX010$", placeholder="$C", surface=surface, option=option,
                     pivot=pivot, variant=variant, label_variant="Trabajo")


_GROUP = {"Diurno": "a", "Nocturno": "b", "Diurno Excepcional": "c", "Turno de día": "a"}


def test_filter_accepts_new_distinct_variant():
    out = filter_candidates(_GROUP, [_c("Nocturno", "b", "Noche")])
    assert [(c.variant, c.status) for c in out] == [("Noche", "ok")]


@pytest.mark.parametrize(
    "variant, reason",
    [
        ("nocturno", "same_as_original"),        # sin mayúsculas, es el original
        ("Diurno", "collides_with_sibling"),     # es el valor de otra opción
        ("De día", "collides_with_sibling"),     # es la variante de otra opción (abajo)
        ("", "empty"),
    ],
)
def test_filter_rejects(variant, reason):
    other = _c("Diurno", "a", "De día")
    out = filter_candidates(_GROUP, [other, _c("Nocturno", "b", variant)])
    mine = [c for c in out if c.surface == "Nocturno"][0]
    assert (mine.status, mine.reason) == ("rejected", reason)


def test_filter_allows_same_variant_within_same_option():
    # «Diurno» y «Turno de día» son la misma opción: pueden dar la misma variante
    out = filter_candidates(_GROUP, [_c("Diurno", "a", "De día"), _c("Turno de día", "a", "De día")])
    assert {c.status for c in out} == {"ok"}


def test_filter_dedupes_variants_per_surface():
    out = filter_candidates(_GROUP, [_c("Nocturno", "b", "Noche", "fr"),
                                     _c("Nocturno", "b", "noche", "it")])
    assert [c.status for c in out] == ["ok", "rejected"]
    assert out[1].reason == "duplicate"


# --- menú para César ------------------------------------------------------

def test_menu_roundtrip():
    cands = filter_candidates(_GROUP, [_c("Nocturno", "b", "Noche"), _c("Diurno", "a", "Diurno")])
    md = menu_markdown(cands)
    assert md.count("- [ ] ") == 1  # solo las que pasan el filtro
    assert "Nocturno" in md and "Noche" in md
    approved = parse_menu(md.replace("- [ ] ", "- [x] "))
    assert approved == {cands[0].uid}


def test_uid_is_stable():
    assert _c("Nocturno", "b", "Noche").uid == _c("Nocturno", "b", "Noche").uid
    assert _c("Nocturno", "b", "Noche").uid != _c("Nocturno", "b", "Noches").uid


# --- montaje --------------------------------------------------------------

def test_fill_values_replaces_value_markers_only():
    back = "Trabajo [1] con [2] tubos, banda [3]."
    mapping = {"[1]": "Nocturno", "[2]": "4", "[3]": "i < 3 horas"}
    out = fill_values(back, mapping, ["[1]"], {"[1]": "de noche"})
    assert out == "Trabajo de noche con 4 tubos, banda i < 3 horas."


def test_fill_values_keeps_original_without_choice():
    back = "Trabajo [1]."
    assert fill_values(back, {"[1]": "Nocturno"}, ["[1]"], {}) == "Trabajo Nocturno."


@pytest.mark.parametrize(
    "prefix, label, present",
    [
        ("Condiciones de ejecución: ", "CONDICIONES DE EJECUCIÓN", True),
        ("Se realiza el trabajo ", "TRABAJO", True),
        ("Canalización de ", "Nº TUBOS", False),
    ],
)
def test_label_present_before_marker(prefix, label, present):
    assert label_present(prefix, label) is present


# --- inventario de huecos -------------------------------------------------

from test_characterization import _corpus, _stage  # noqa: E402

from synthetic.bt_values import value_groups  # noqa: E402


def test_value_groups_from_gold_and_stacked():
    stage = _stage()
    corpus = _corpus()
    gold = {r["item_key"]: r for r in corpus}["OEX010abaa"]
    query = {"item_key": "q1", "gold_item_key": "OEX010abaa", "parent_key": "OEX010$",
             "text": gold["text"].replace("Diurno", "Turno de día").replace("en terreno rocoso", "sobre roca")}
    records = [
        {"type": "synonym_label", "layer": "param_value", "param": "C", "value": "a",
         "original": "Diurno", "new": "Turno de día"},
        {"type": "paraphrase", "layer": "text_variable", "var": "I", "condition": '%B=="b"',
         "original": "en terreno rocoso", "new": "sobre roca"},
    ]
    groups, labels = value_groups(stage, corpus, [query], {"q1": records})
    assert groups[("OEX010$", "$C")] == {"Diurno": "a", "Nocturno": "b", "Turno de día": "a"}
    assert groups[("OEX010$", "$I")]["sobre roca"] == "en terreno rocoso"
    assert groups[("OEX010$", "$I")]["en terreno normal"] == "en terreno normal"
    assert labels[("OEX010$", "$C")] == "TRABAJO" and labels[("OEX010$", "$I")] is None


def test_menu_dedupes_across_concepts():
    a = Candidate("OEX010$", "$C", "Nocturno", "b", "fr", "Noche", "Trabajo", label="TRABAJO", status="ok")
    b = Candidate("OEY020$", "$B", "Nocturno", "b", "it", "noche", "Trabajo", label="TRABAJO", status="ok")
    assert a.uid == b.uid  # misma etiqueta, superficie y variante: se aprueba una vez
    md = menu_markdown([a, b])
    assert md.count("- [ ] ") == 1 and "2 conceptos" in md


# --- términos de dominio (descarte automático de L2) ----------------------

from synthetic.bt_values import domain_terms, lost_domain_terms  # noqa: E402

_DOCS = {
    "C1": "Suministro y montaje de canalización con entibación de los costados",
    "C2": "Suministro y montaje de canaleta en zona de balasto",
    "C3": "Suministro y montaje de cimentación con micropilotes",
    "C4": "Suministro y montaje de tubo con topo bajo vías",
}


def test_domain_terms_are_the_rare_content_words():
    terms = domain_terms(_DOCS, max_df=0.5)
    assert {"entibacion", "balasto", "micropilotes", "topo"} <= terms
    assert not {"suministro", "montaje", "de", "con"} & terms


@pytest.mark.parametrize(
    "surface, variant, lost",
    [
        ("entibación de los costados", "intimidación de los lados", ["entibacion", "costados"]),
        ("en zona de balasto", "en zona de lastre", ["balasto"]),
        ("ejecutado con topo", "realizado con topos", []),           # misma raíz
        ("suministro y montaje", "alimentación y montaje", []),      # genérico
    ],
)
def test_lost_domain_terms(surface, variant, lost):
    terms = domain_terms(_DOCS, max_df=0.5)
    assert lost_domain_terms(surface, variant, terms) == lost


def test_concept_docs_join_templates_variables_and_values():
    from synthetic.bt_values import concept_docs

    docs = concept_docs(_stage())
    assert set(docs) == {"OEX010$"}
    text = docs["OEX010$"]
    assert "Canalización" in text and "rocoso" in text and "Volumen escaso" in text


# --- reversiones (decisión de César) --------------------------------------

from synthetic.bt_values import reverts  # noqa: E402


@pytest.mark.parametrize(
    "surface, variant, gold, reason",
    [
        ("Trescientos milímetros", "300 mm", "300 mm", "introduces_digits"),
        ("cuarenta elementos", "40 elementos", "40", "introduces_digits"),
        ("concreto", "hormigón", "Hormigón", "back_to_gold"),
        ("Nocturno", "Noche", "Nocturno", None),          # superficie gold: no hay nada que revertir
        ("Turno de noche", "Noche cerrada", "Nocturno", None),
        ("300 mm", "300 milímetros", "300 mm", None),     # ya tenía dígitos
    ],
)
def test_reverts(surface, variant, gold, reason):
    assert reverts(surface, variant, gold) == reason


# --- montaje de una partida (BT de prosa + valores) ------------------------

from synthetic.bt_values import assemble_values  # noqa: E402

_BACK = "Trabajo [1], terreno [2] con [3] tubos de [4] mm."
_MAP = {"[1]": "Nocturno", "[2]": "rocoso", "[3]": "4", "[4]": "110"}
_VALUES = ["[1]", "[2]", "[3]"]
_SLOTS = {"[1]": ("$C", "Nocturno"), "[2]": ("$B", "rocoso"), "[3]": ("$A", "4")}
_LABELS = {"$C": "TRABAJO", "$B": "TIPO DE TERRENO", "$A": "Nº TUBOS"}
_APPROVED = {"$C": {"Nocturno": ["De noche", "Turno de noche"]}, "$B": {"rocoso": ["de roca"]},
             "$A": {"4": ["cuatro"]}}


def _assemble(key="q1", label_p=0.0):
    return assemble_values(_BACK, _MAP, _VALUES, _SLOTS,
                           lambda ph, s: _APPROVED.get(ph, {}).get(s, []),
                           _LABELS, seed=42, key=key, label_p=label_p)


def test_assemble_always_substitutes_approved_variants():
    text, subs = _assemble()
    assert "Nocturno" not in text and "rocoso" not in text
    assert text.endswith("tubos de 110 mm.")  # el resto de marcadores, literales
    assert {s["placeholder"] for s in subs} == {"$C", "$B", "$A"}


def test_assemble_is_deterministic_per_key():
    assert _assemble("q1") == _assemble("q1")


def test_assemble_keeps_original_without_variants():
    text, subs = assemble_values("Trabajo [1].", {"[1]": "Diurno"}, ["[1]"], {"[1]": ("$C", "Diurno")},
                                 lambda ph, s: [], _LABELS, seed=42, key="q", label_p=1.0)
    assert text == "Trabajo Diurno." and subs == []


def test_label_added_only_without_digits_and_when_absent():
    back = "Se ejecuta en [2] con [3] tubos."
    text, subs = assemble_values(back, _MAP, ["[2]", "[3]"], _SLOTS,
                                 lambda ph, s: _APPROVED.get(ph, {}).get(s, []),
                                 _LABELS, seed=42, key="q", label_p=1.0)
    assert "Tipo de terreno: de roca" in text       # sin dígitos y la prosa no la dice
    assert "Nº tubos" not in text                   # valor numérico: sin etiqueta
    # «Trabajo [1]»: la prosa ya nombra el parámetro, no se repite
    text2, _ = _assemble(label_p=1.0)
    assert "Trabajo: " not in text2 and text2.startswith("Trabajo ")


def test_variant_takes_the_initial_case_of_the_original():
    back = "de diámetro [1], que comprende"
    text, _ = assemble_values(back, {"[1]": "en todo terreno, salvo roca"}, ["[1]"],
                              {"[1]": ("$I", "en todo terreno, salvo roca")},
                              lambda ph, s: ["En todos los terrenos excepto rocas"], {},
                              seed=42, key="q", label_p=0.0)
    assert text == "de diámetro en todos los terrenos excepto rocas, que comprende"
    text2, _ = assemble_values("Trabajo: [1].", {"[1]": "Nocturno"}, ["[1]"], {"[1]": ("$C", "Nocturno")},
                               lambda ph, s: ["de noche"], {}, seed=42, key="q", label_p=0.0)
    assert text2 == "Trabajo: De noche."


def test_label_present_tolerates_plural_and_inflection():
    # la BT tradujo la etiqueta «Trabajo:» como «Trabajos:»; no hay que repetirla
    assert label_present("Completamente terminado. Trabajos: ", "TRABAJO")
    assert label_present("las condiciones de la ejecución ", "CONDICIONES DE EJECUCIÓN")
