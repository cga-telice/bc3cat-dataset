"""Sinónimos del glosario en la BT (idea de César): los términos del oficio, que
la BT restaura siempre literales, se sustituyen a veces por alternativas
aprobadas para que las consultas se parezcan más a textos reales."""
from __future__ import annotations

from synthetic.bt_glossary import substitute_glossary

_ALTS = {"arqueta": ["caja enterrada", "caja subterránea"],
         "firme": ["pavimento", "afirmado"],
         "poste": ["apoyo"]}


def _sub(text, p=1.0, key="q1"):
    return substitute_glossary(text, _ALTS, seed=42, key=key, p=p)


def test_substitutes_terms_with_approved_alternatives():
    text, subs = _sub("Arqueta [1] junto al poste.")
    assert "arqueta" not in text.lower() and "poste" not in text
    assert text.startswith(("Caja enterrada", "Caja subterránea"))
    assert "apoyo" in text
    assert [s["term"] for s in subs] == ["arqueta", "poste"]


def test_markers_are_untouched():
    text, _ = _sub("Arqueta [1] de [2] mm.")
    assert "[1]" in text and "[2]" in text


def test_probability_zero_changes_nothing():
    assert _sub("Arqueta junto al poste.", p=0.0) == ("Arqueta junto al poste.", [])


def test_deterministic_per_key():
    assert _sub("Arqueta y poste.", p=0.5, key="a") == _sub("Arqueta y poste.", p=0.5, key="a")


def test_alternative_already_in_text_is_not_used():
    # «demolición del firme y del pavimento»: «pavimento» ya está, se usa «afirmado»
    text, subs = _sub("Demolición del firme y del pavimento.")
    assert text == "Demolición del afirmado y del pavimento."


def test_skip_when_every_alternative_is_already_present():
    text, subs = _sub("Poste sobre apoyo.")
    assert text == "Poste sobre apoyo." and subs == []


def test_plural_pluralises_first_word():
    text, _ = substitute_glossary("Postes de electrificación.", {"poste": ["apoyo"]},
                                  seed=1, key="k", p=1.0)
    assert text == "Apoyos de electrificación."


def test_presence_is_checked_on_the_unmasked_text():
    # la sigla PRFV va enmascarada como [2]: no puede elegirse «PRFV» para «composite»
    masked = "Arqueta de composite-[2] tipo [3]."
    text, subs = substitute_glossary(masked, {"composite": ["PRFV"]}, seed=1, key="k", p=1.0,
                                     context="Arqueta de composite-PRFV tipo AFC-1.")
    assert text == masked and subs == []
