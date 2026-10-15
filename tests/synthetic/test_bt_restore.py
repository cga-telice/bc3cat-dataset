"""BT de prosa por frases (vuelta tras la auditoría de prosas) — restauración
posterior de los términos del glosario (idea de César: no enmascarar antes de
traducir, sino devolver el término original después)."""
from __future__ import annotations

import pytest

from synthetic.bt_restore import restore_terms

_TERMS = ["arqueta", "canaleta", "desmonte", "hastial", "tapa", "poste"]


@pytest.mark.parametrize(
    "source, output, expected",
    [
        ("Tapa para canaleta de hormigón tipo [1].",
         "Parte superior para canaleta de hormigón tipo [1].",
         "Tapa para canaleta de hormigón tipo [1]."),
        ("Cimentación rectangular en desmonte [1] para terreno [2].",
         "Molduras rectangulares no montados [1] para terreno [2].",
         "Molduras rectangulares en desmonte [1] para terreno [2]."),
        ("sobre hastial de túnel o puente",
         "sobre hestial de túnel o puente",
         "sobre hastial de túnel o puente"),
        ("Arqueta de registro [1].", "Arco de registro [1].", "Arqueta de registro [1]."),
    ],
)
def test_restores_mistranslated_terms(source, output, expected):
    r = restore_terms(source, output, _TERMS)
    assert r.ok and r.text == expected


def test_untouched_output_is_ok():
    r = restore_terms("Canaleta [1] con tapa.", "Canaleta [1] con tapa.", _TERMS)
    assert r.ok and r.text == "Canaleta [1] con tapa." and r.restored == []


def test_plural_and_case_count_as_preserved():
    r = restore_terms("Arquetas de registro.", "arquetas del registro.", _TERMS)
    assert r.ok and r.restored == []


def test_large_reordering_is_not_restored():
    # el término desaparece dentro de un bloque reordenado demasiado largo
    src = "Suministro de tapa para canaleta de hormigón tipo [1] incluso montaje."
    out = "Montaje incluido del suministro de la parte superior de hormigón del tipo [1] canal."
    r = restore_terms(src, out, _TERMS)
    assert not r.ok and set(r.missing) >= {"tapa", "canaleta"}


def test_markers_must_survive():
    r = restore_terms("Arqueta [1] y [2].", "Arqueta [1].", _TERMS)
    assert not r.ok and r.reason == "markers_changed"


def test_restoration_only_where_the_source_had_the_term():
    # «arco» legítimo sin «arqueta» en el origen: no se toca
    r = restore_terms("Puente en arco [1].", "Puente de arco [1].", _TERMS)
    assert r.ok and r.text == "Puente de arco [1]."
