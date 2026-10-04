"""BT (opción A), T2 — tests del verificador de caracterización paramétrica.

Sin red: los extractores son falsos e inyectados. El concepto de juguete
``OEX010$`` tiene cuatro ejes:

* ``A`` Nº TUBOS (1, 2) — placeholder ``$A`` en la plantilla TEXTO;
* ``B`` TIPO DE TERRENO (Normal, Rocoso, Cualquiera) — vía la variable
  ``$I``, cuyas condiciones ``%B`` lo indexan. ``Cualquiera`` se renderiza
  igual que ``Normal`` → esas hojas forman grupos D-031 que difieren en B;
* ``C`` TRABAJO (Diurno, Nocturno) — placeholder ``$C``;
* ``D`` VOLUMEN (escaso, relevante) — no aparece en la plantilla TEXTO.
"""
from __future__ import annotations

import itertools
import json

import pytest

from synthetic.characterization import (
    NO_DET,
    CharacterizationContext,
    ExtractionError,
    LLMExtractor,
    build_extraction_prompt,
    invariants,
    lexical_decode,
    parse_extraction,
    survival,
    undo_records,
)

_TEXTO = "Canalización de $A tubos $I, con hormigón HE-20 de 1,60 m. Trabajo: $C"
_I_FORMULA = (
    '"en terreno normal" * (%B=="a") + "en terreno rocoso" * (%B=="b") '
    '+ "en terreno normal" * (%B=="c")'
)
_A = ["1", "2"]
_B = ["Normal", "Rocoso", "Cualquiera"]
_C = ["Diurno", "Nocturno"]
_D = ["Volumen escaso", "Volumen relevante"]
_I = {"a": "en terreno normal", "b": "en terreno rocoso", "c": "en terreno normal"}


def _values(vals):
    return [{"label": chr(97 + i), "value": f" {v} "} for i, v in enumerate(vals)]


def _stage():
    return {
        "OEX010$": {
            "ud": "m",
            "concept": "CANALIZACIÓN DE JUGUETE",
            "text_variables": {"I": _I_FORMULA},
            "resumen": "Canalización $A T, $C",
            "texto": "\\" + _TEXTO,
            "parameters": {
                "A": {"label": " Nº TUBOS ", "values": _values(_A)},
                "B": {"label": "TIPO DE TERRENO", "values": _values(_B)},
                "C": {"label": "TRABAJO", "values": _values(_C)},
                "D": {"label": "VOLUMEN", "values": _values(_D)},
            },
        }
    }


def _render(a, b, c):
    return (
        f"Canalización de {_A[a]} tubos {_I['abc'[b]]}, con hormigón HE-20 "
        f"de 1,60 m. Trabajo: {_C[c]}"
    )


def _corpus():
    rows = []
    for a, b, c, d in itertools.product(range(2), range(3), range(2), range(2)):
        key = "OEX010" + "abcd"[0:0] + "ab"[a] + "abc"[b] + "ab"[c] + "ab"[d]
        rows.append({
            "item_key": key,
            "parent_key": "OEX010$",
            "concept": "CANALIZACIÓN DE JUGUETE",
            "text": _render(a, b, c),
        })
    return rows


def _groups(corpus):
    by_text: dict[str, list[str]] = {}
    for r in corpus:
        by_text.setdefault(r["text"], []).append(r["item_key"])
    groups = {min(v): sorted(v) for v in by_text.values() if len(v) > 1}
    return {"groups": groups}


@pytest.fixture
def ctx():
    corpus = _corpus()
    return CharacterizationContext.load(
        _stage(), corpus, d031_groups=_groups(corpus),
        exclusions=[{"item_keys": ["OEX010aaaa_syn_excluded"]}],
    )


GOLD = "OEX010abaa"  # A=1, B=Rocoso, C=Diurno, D=escaso
GOLD_TEXT = _render(0, 1, 0)


class FakeExtractor:
    """Devuelve una respuesta fija (o calculada) y guarda los textos vistos."""

    def __init__(self, name, answer):
        self.name = name
        self._answer = answer
        self.seen: list[str] = []

    def extract(self, text, concept):
        self.seen.append(text)
        ans = self._answer(text) if callable(self._answer) else self._answer
        if isinstance(ans, Exception):
            raise ans
        return dict(ans)


def _gold_answer(**over):
    base = {"A": 1, "B": 2, "C": 1, "D": NO_DET}
    base.update(over)
    return base


def _pair(a1, a2=None):
    return [FakeExtractor("x1", a1), FakeExtractor("x2", a2 if a2 is not None else a1)]


_QUERY = "Se ejecuta una canalización de 1 tubos en terreno rocoso, con hormigón HE-20 de 1,60 m, en trabajo Diurno"


# --- contexto -------------------------------------------------------------

def test_rendered_axes_from_texto_template(ctx):
    concept = ctx.concepts["OEX010$"]
    assert concept.rendered == ("A", "B", "C")
    assert concept.not_rendered == ("D",)


def test_axis_values_are_stripped(ctx):
    axis = ctx.concepts["OEX010$"].axis("A")
    assert axis.label == "Nº TUBOS"
    assert axis.values == ("1", "2")


def test_allowed_values_follow_d031_group(ctx):
    # gold B=Normal comparte TEXTO con B=Cualquiera → ambos valen, y 0 también
    assert ctx.allowed("OEX010aaaa", "B") == frozenset({1, 3, NO_DET})
    # gold B=Rocoso no tiene gemela en B
    assert ctx.allowed(GOLD, "B") == frozenset({2})


def test_schema_mismatch_fails_loud():
    corpus = _corpus()
    schema = {"OEX010$": {"axes": {"Nº TUBOS": ["1", "3"]}}}
    with pytest.raises(ValueError, match="concept_schema"):
        CharacterizationContext.load(_stage(), corpus, concept_schema=schema)


# --- G0 -------------------------------------------------------------------

def test_g0_unknown_gold(ctx):
    r = ctx.check(_QUERY, "OEX010zzzz", extractors=_pair(_gold_answer()))
    assert (r.ok, r.gate, r.reason) == (False, "G0", "unknown_gold")


def test_g0_excluded_query(ctx):
    r = ctx.check(_QUERY, GOLD, query_key="OEX010aaaa_syn_excluded",
                  extractors=_pair(_gold_answer()))
    assert (r.gate, r.reason) == ("G0", "excluded_p7_p8")


# --- G1 -------------------------------------------------------------------

def test_invariants_normalisation():
    a = invariants("de 1,60 m y 3x1.5 cm, banda i ≥ 5 horas, tubo PVC")
    b = invariants("de 1.60 m y 3 x 1,5 cm, banda i >= 5 horas, tubo PVC")
    assert a == b


def test_g1_passes_with_source_text(ctx):
    src = "Canalización de 1 tubos en terreno rocoso, con hormigón HE-20 de 1,60 m. Trabajo: Diurno"
    r = ctx.check(_QUERY, GOLD, source_text=src, extractors=_pair(_gold_answer()))
    assert r.ok, r


def test_g1_rejects_lost_quantity(ctx):
    q = _QUERY.replace("de 1,60 m", "de gran altura")
    r = ctx.check(q, GOLD, extractors=_pair(_gold_answer()))
    assert (r.gate, r.reason[:7]) == ("G1", "missing")


def test_g1_allows_recorded_conversion(ctx):
    records = [
        {"type": "template_paraphrase", "layer": "template", "field": "TEXTO",
         "original": _TEXTO, "new": "Tubos ($A) $I; hormigón HE-20 de 1,60 m. Turno: $C"},
        {"type": "num_to_text", "layer": "param_value", "param": "A", "value": "a",
         "original": "1", "new": "Uno"},
    ]
    q = "Tubos (Uno) en terreno rocoso; hormigón HE-20 de 1,60 m. Turno: Diurno"
    r = ctx.check(q, GOLD, records=records, extractors=_pair(_gold_answer()))
    assert r.ok, r
    # sin el registro, el «1» que falta rechaza
    r2 = ctx.check(q, GOLD, records=records[:1], extractors=_pair(_gold_answer()))
    assert r2.gate == "G1"


def test_undo_records_keeps_template_unit_attached():
    # OEG020: plantilla "$B m", num_to_text " 3 " → "tres m de profundidad"
    rec = {"layer": "param_value", "original": " 3 ", "new": "tres m de profundidad"}
    undone = undo_records("y la profundidad es de tres m de profundidad m, con", [rec])
    assert undone == "y la profundidad es de 3 m, con"
    assert invariants(undone) == invariants("profundidad de 3 m")


def test_undo_records_matches_whole_words_only():
    rec = {"layer": "param_value", "original": "1", "new": "Un"}
    assert undo_records("Un tubo, unido", [rec]) == "1 tubo, unido"


def test_g1_allows_placeholder_repeated_by_paraphrase(ctx):
    # OED110: la paráfrasis repite $A; repetir un valor no añade información
    records = [
        {"type": "template_paraphrase", "layer": "template", "field": "TEXTO",
         "original": _TEXTO,
         "new": "Canalización de $A tubos $I ($A tubos), con hormigón HE-20 de 1,60 m. Trabajo: $C"},
    ]
    q = ("Canalización de 1 tubos en terreno rocoso (1 tubos), con hormigón HE-20 "
         "de 1,60 m. Trabajo: Diurno")
    r = ctx.check(q, GOLD, records=records, extractors=_pair(_gold_answer()))
    assert r.ok, r


def test_g1_with_source_compares_in_original_space(ctx):
    # la BT revierte «Un» → «1»: misma información, G1 no rechaza
    records = [{"type": "num_to_text", "layer": "param_value", "param": "A",
                "value": "a", "original": "1", "new": "Un"}]
    src = "Canalización de Un tubos en terreno rocoso, con hormigón HE-20 de 1,60 m. Trabajo: Diurno"
    q = "Canalización de 1 tubos en terreno rocoso, con hormigón HE-20 de 1,60 m, trabajo Diurno"
    assert ctx.check(q, GOLD, source_text=src, records=records,
                     extractors=_pair(_gold_answer())).ok
    # pero un número nuevo sí rechaza
    q2 = q.replace("Diurno", "Diurno durante 2 horas")
    r = ctx.check(q2, GOLD, source_text=src, records=records,
                  extractors=_pair(_gold_answer()))
    assert r.gate == "G1"


def test_gate_order_g1_before_g2(ctx):
    q = _QUERY.replace("HE-20", "HM-30")
    r = ctx.check(q, GOLD, extractors=_pair(_gold_answer(B=1)))
    assert r.gate == "G1"


# --- G2 -------------------------------------------------------------------

def test_g2_accepts_when_both_extractors_give_gold(ctx):
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer()))
    assert r.ok
    assert r.axes == {"A": "ok", "B": "ok", "C": "ok"}
    assert r.not_rendered == ["D"]


def test_g2_disagreement_rejects(ctx):
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(), _gold_answer(C=2)))
    assert (r.ok, r.gate, r.axis, r.reason) == (False, "G2", "C", "extractor_disagree")


def test_g2_both_wrong_rejects(ctx):
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(B=1)))
    assert (r.gate, r.axis, r.reason) == ("G2", "B", "wrong_value")


def test_g2_not_determinable_rejects(ctx):
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(A=NO_DET)))
    assert (r.gate, r.axis, r.reason) == ("G2", "A", "not_determinable")


def test_g2_group_value_accepted(ctx):
    gold = "OEX010aaaa"  # B=Normal; Cualquiera renderiza igual
    q = _QUERY.replace("rocoso", "normal")
    r = ctx.check(q, gold, extractors=_pair(_gold_answer(B=3)))
    assert r.ok, r
    assert r.axes["B"] == "ok_group"


def test_g2_extractor_error_rejects(ctx):
    bad = ExtractionError("no_json")
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(), bad))
    assert (r.gate, r.reason) == ("G2", "extractor_output_invalid:x2")


def test_extractors_never_see_the_gold(ctx):
    pair = _pair(_gold_answer())
    ctx.check(_QUERY, GOLD, extractors=pair)
    assert pair[0].seen == [_QUERY]
    concept = ctx.concepts["OEX010$"]
    prompt = build_extraction_prompt(_QUERY, concept)
    assert GOLD not in prompt and "abaa" not in prompt


# --- G3 -------------------------------------------------------------------

def test_g3_query_equal_to_sibling_rejects(ctx):
    sibling = _render(0, 1, 1)  # Nocturno
    r = ctx.check(sibling, GOLD, extractors=_pair(_gold_answer()))
    assert (r.gate, r.reason) == ("G3", "confusable_with_leaf")


def test_g3_equality_is_case_and_space_insensitive(ctx):
    sibling = "  " + _render(0, 1, 1).upper()
    r = ctx.check(sibling, GOLD, extractors=_pair(_gold_answer()))
    assert r.gate in {"G1", "G3"}  # las siglas cambian; nunca se acepta
    assert not r.ok


# --- G4 -------------------------------------------------------------------

def test_g4_unrendered_axis_accepts_group_value(ctx):
    # D no se renderiza: las hojas que solo difieren en D comparten TEXTO
    # (grupo D-031), así que cualquier valor del grupo no añade información
    assert ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(D=2))).ok


def test_g4_value_outside_gold_group_rejects():
    ctx = CharacterizationContext.load(_stage(), _corpus())  # sin grupos D-031
    assert ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(D=1))).ok  # = gold
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer(D=2)))
    assert (r.gate, r.axis, r.reason) == ("G4", "D", "added_axis_value")


def test_g4_drift_signal_is_reported(ctx):
    r = ctx.check(_QUERY, GOLD, extractors=_pair(_gold_answer()))
    assert "score" in r.drift


# --- G5 -------------------------------------------------------------------

@pytest.mark.parametrize(
    "original, new, query, expected",
    [
        ("12", "Doce", "con 12 tubos", "reverted"),
        ("30x15 mm", "30x15 milímetros", "canaleta de 30x15 mm", "reverted"),
        ("Volumen relevante", "Alto Volumen", "con alto volumen", "survived"),
        ("Volumen relevante", "Alto Volumen", "con mucho volumen", "transformed"),
    ],
)
def test_survival(original, new, query, expected):
    assert survival(original, new, query) == expected


def test_g5_survival_types_on_stacked_source(ctx):
    records = [
        {"type": "template_paraphrase", "layer": "template", "field": "RESUMEN",
         "original": "x", "new": "y"},
        {"type": "synonym_label", "layer": "param_value", "param": "C", "value": "a",
         "original": "Diurno", "new": "Turno de día"},
        {"type": "num_to_text", "layer": "param_value", "param": "A", "value": "a",
         "original": "1", "new": "Un"},
        {"type": "synonym_label", "layer": "param_value", "param": "D", "value": "a",
         "original": "Volumen escaso", "new": "Poco volumen"},  # D no se ve
    ]
    src = "Canalización de Un tubos en terreno rocoso, con hormigón HE-20 de 1,60 m. Trabajo: Turno de día"
    q = "Canalización de 1 tubos en terreno rocoso, con hormigón HE-20 de 1,60 m. Trabajo: Turno de día"
    r = ctx.check(q, GOLD, source_text=src, records=records,
                  extractors=_pair(_gold_answer()))
    assert r.gate != "G5"
    assert r.surviving_types == ["synonym_label"]
    assert r.reverted_types == ["num_to_text"]


# --- G6 -------------------------------------------------------------------

def test_g6_no_op_rejects(ctx):
    r = ctx.check(_QUERY, GOLD, source_text=_QUERY, extractors=_pair(_gold_answer()))
    assert (r.gate, r.reason) == ("G6", "no_op")


def test_g6_equal_to_gold_rejects(ctx):
    r = ctx.check(GOLD_TEXT, GOLD, extractors=_pair(_gold_answer()))
    assert (r.gate, r.reason) == ("G6", "equals_gold")


def test_g6_duplicate_of_delivered_rejects(ctx):
    forbidden = frozenset({" ".join(_QUERY.casefold().split())})
    r = ctx.check(_QUERY, GOLD, forbidden=forbidden, extractors=_pair(_gold_answer()))
    assert (r.gate, r.reason) == ("G6", "duplicate_of_delivered")


# --- extractor LLM, prompt y parseo ---------------------------------------

def test_prompt_lists_every_axis_with_lettered_options(ctx):
    prompt = build_extraction_prompt(_QUERY, ctx.concepts["OEX010$"])
    assert _QUERY in prompt
    assert "B — TIPO DE TERRENO\n  a) Normal\n  b) Rocoso\n  c) Cualquiera" in prompt
    assert "D — VOLUMEN\n  a) Volumen escaso\n  b) Volumen relevante" in prompt


@pytest.mark.parametrize(
    "raw",
    [
        '{"A": "a", "B": "b", "C": "a", "D": null}',
        'Respuesta:\n```json\n{"A": "A", "B": "b", "C": "a", "D": null}\n```',
        '{"A": "a", "B": "b", "C": "a", "D": "0"}',
        '{"A": "a)", "B": "b", "C": "a", "D": ""}',
    ],
)
def test_parse_extraction_ok(ctx, raw):
    got = parse_extraction(raw, ctx.concepts["OEX010$"])
    assert got == {"A": 1, "B": 2, "C": 1, "D": NO_DET}


@pytest.mark.parametrize(
    "raw",
    [
        "no sé",
        '{"A": "a", "B": "b", "C": "a"}',              # falta un eje
        '{"A": "a", "B": "z", "C": "a", "D": null}',   # fuera de rango
        '{"A": "a", "B": 2, "C": "a", "D": null}',     # número en vez de letra
        '{"A": "a", "B": "Rocoso", "C": "a", "D": null}',  # valor en vez de letra
    ],
)
def test_parse_extraction_rejects(ctx, raw):
    with pytest.raises(ExtractionError):
        parse_extraction(raw, ctx.concepts["OEX010$"])


class _Client:
    def __init__(self, response):
        self.response = response
        self.prompts: list[str] = []

    def complete(self, prompt):
        self.prompts.append(prompt)
        return self.response


def test_llm_extractor_roundtrip(ctx):
    client = _Client(json.dumps({"A": "a", "B": "b", "C": "a", "D": None}))
    ex = LLMExtractor("phi4:latest", client)
    got = ex.extract(_QUERY, ctx.concepts["OEX010$"])
    assert got == {"A": 1, "B": 2, "C": 1, "D": 0}
    assert client.prompts == [build_extraction_prompt(_QUERY, ctx.concepts["OEX010$"])]


# --- decodificador léxico (tercera señal, no decide) ----------------------

def test_lexical_decode_uses_extra_surfaces(ctx):
    concept = ctx.concepts["OEX010$"]
    extra = {("OEX010$", "C", 1): ("turno de día",)}
    got = lexical_decode("trabajo en turno de día, 2 tubos", concept, extra)
    assert got["C"] == (1,)
    assert got["A"] == (2,)
    assert got["D"] == ()


def test_json_mode_client_body():
    from synthetic.characterization import JsonModeClient
    from synthetic.llm_client import LLMConfig

    conf = LLMConfig(base_url="http://x/v1", model="phi4:latest", api_key_env="NOPE")
    body = json.loads(JsonModeClient(conf, max_tokens=96)._build_body("hola"))
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 96
    assert body["temperature"] == 0.0
    assert body["messages"] == [{"role": "user", "content": "hola"}]
