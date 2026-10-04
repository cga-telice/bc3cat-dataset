"""BT (opción A), T4 — tests del motor de back-translation con motores falsos."""
from __future__ import annotations

import re

import pytest

from synthetic.back_translation import (
    CacheMiss,
    CachedEngine,
    back_translate,
    back_translate_many,
    reassemble,
    segment,
)

_TEXT = (
    "Canaleta PVC de 30x15 mm con tapa.\nTrabajo: Diurno. "
    "Banda de mantenimiento: 3 <= i < 5 horas. Compactado al 95% P.M. y regado."
)


class Identity:
    signature = {"engine": "identity"}

    def __init__(self):
        self.calls: list[tuple] = []

    def translate(self, segments, src, tgt):
        self.calls.append((tuple(segments), src, tgt))
        return list(segments)


class ReverseWords(Identity):
    """Cambia el orden de las palabras (los marcadores sobreviven)."""
    signature = {"engine": "reverse"}

    def translate(self, segments, src, tgt):
        self.calls.append((tuple(segments), src, tgt))
        return [" ".join(reversed(s.split())) for s in segments]


class DropMarkers(Identity):
    signature = {"engine": "drop"}

    def translate(self, segments, src, tgt):
        return [re.sub(r"\[\[[BQS]\d+\]\]|<x\d+/>", "", s) for s in segments]


# --- segmentación ---------------------------------------------------------

def test_segment_and_reassemble_identity():
    pieces = segment(_TEXT)
    assert reassemble(pieces, [p.text for p in pieces if p.translate]) == _TEXT


def test_segment_splits_lines_then_sentences():
    pieces = segment("Uno. Dos.\nTres")
    assert [p.text for p in pieces if p.translate] == ["Uno.", "Dos.", "Tres"]


def test_blank_pieces_are_not_translated():
    pieces = segment("Uno.\n\n  \nDos.")
    assert [p.text for p in pieces if p.translate] == ["Uno.", "Dos."]


# --- back_translate -------------------------------------------------------

@pytest.mark.parametrize("strategy", ["sentinel", "xml", "none"])
def test_identity_engine_is_a_noop(strategy):
    r = back_translate(_TEXT, "en", Identity(), strategy)
    assert r.ok and r.text == _TEXT


def test_masks_are_restored_after_reordering():
    r = back_translate("Canaleta PVC de 30x15 mm.", "en", ReverseWords(), "sentinel")
    assert r.ok
    assert r.text == "Canaleta PVC de 30x15 mm."  # dos inversiones = identidad
    assert sorted(r.mapping.values()) == ["30x15 mm", "PVC"]


def test_translator_sees_masked_text_only():
    eng = Identity()
    back_translate(_TEXT, "en", eng, "sentinel")
    sent = " ".join(s for call in eng.calls for s in call[0])
    assert "30x15" not in sent and "PVC" not in sent and "<=" not in sent
    assert [c[1:] for c in eng.calls] == [("es", "en"), ("en", "es")]


def test_lost_mask_fails_loud():
    r = back_translate(_TEXT, "en", DropMarkers(), "sentinel")
    assert (r.ok, r.reason, r.text) == (False, "mask_lost", None)


def test_many_batches_one_call_per_direction():
    eng = Identity()
    out = back_translate_many([_TEXT, "Otra frase. Y otra."], "en", eng, "xml")
    assert [r.text for r in out] == [_TEXT, "Otra frase. Y otra."]
    assert len(eng.calls) == 2


# --- caché ----------------------------------------------------------------

def test_cache_records_and_serves(tmp_path):
    inner = Identity()
    eng = CachedEngine(inner, tmp_path, mode="record")
    eng.translate(["Uno.", "Dos.", "Uno."], "es", "en")
    eng.translate(["Uno.", "Tres."], "es", "en")
    sent = [s for call in inner.calls for s in call[0]]
    assert sent == ["Uno.", "Dos.", "Tres."]  # cada segmento único una vez


def test_cache_persists_and_replays(tmp_path):
    CachedEngine(ReverseWords(), tmp_path, mode="record").translate(["a b"], "es", "en")
    replay = CachedEngine(ReverseWords(), tmp_path, mode="replay")
    assert replay.translate(["a b"], "es", "en") == ["b a"]
    with pytest.raises(CacheMiss):
        replay.translate(["c d"], "es", "en")


def test_cache_key_depends_on_signature_and_direction(tmp_path):
    CachedEngine(Identity(), tmp_path, mode="record").translate(["a"], "es", "en")
    other = ReverseWords()
    other.signature = {"engine": "identity", "num_beams": 5}
    with pytest.raises(CacheMiss):
        CachedEngine(other, tmp_path, mode="replay").translate(["a"], "es", "en")
    with pytest.raises(CacheMiss):
        CachedEngine(Identity(), tmp_path, mode="replay").translate(["a"], "en", "es")


def test_cache_unknown_mode(tmp_path):
    with pytest.raises(ValueError):
        CachedEngine(Identity(), tmp_path, mode="fresh")


# --- valores de eje enmascarados (rediseño tras CP2) ----------------------

_VT = "Trabajo: Turno de día. Banda: i < 3 horas. Condiciones: Volumen escaso."


def _spans(text, *subs):
    return [(text.index(s), text.index(s) + len(s)) for s in subs]


class SwapValues(Identity):
    """En la vuelta al español intercambia los dos primeros valores."""
    signature = {"engine": "swap"}

    def translate(self, segments, src, tgt):
        joined = "\x00".join(segments)
        if tgt == "es":
            joined = joined.replace("[[V1]]", "@@").replace("[[V2]]", "[[V1]]").replace("@@", "[[V2]]")
        return joined.split("\x00")


def test_values_are_hidden_from_the_translator():
    eng = Identity()
    spans = _spans(_VT, "Turno de día", "Volumen escaso")
    r = back_translate_many([_VT], "en", eng, "sentinel", spans=[spans])[0]
    assert r.ok and r.text == _VT
    sent = " ".join(s for call in eng.calls for s in call[0])
    assert "Turno" not in sent and "escaso" not in sent
    assert r.values == ["[[V1]]", "[[V2]]"]


def test_swapped_values_are_rejected():
    spans = _spans(_VT, "Turno de día", "Volumen escaso")
    r = back_translate_many([_VT], "en", SwapValues(), "sentinel", spans=[spans])[0]
    assert (r.ok, r.reason) == (False, "value_order_changed")


def test_spans_are_optional_per_text():
    out = back_translate_many([_VT, _VT], "en", Identity(), "xml",
                              spans=[_spans(_VT, "Volumen escaso"), None])
    assert [r.ok for r in out] == [True, True]
    assert len(out[0].values) == 1 and out[1].values == []
