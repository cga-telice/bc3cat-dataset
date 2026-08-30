"""Sprint 38.6 — hermetic tests for :mod:`synthetic.menu_diversity`."""
from __future__ import annotations

import json

import pytest

from synthetic.menu_diversity import (
    ROUNDS,
    _forbidden_openings,
    _strip_fiebdc,
    _wrap_round,
    propose_diverse,
)
from synthetic.target_scanner import scan_chapter
from synthetic.taxonomy import ModificationType


_STAGE = {
    "CTESTA$": {
        "parent_key": "CTESTA$",
        "parameters": {
            "A": {"label": "TRABAJO", "values": [
                {"label": "a", "value": "Diurno"}, {"label": "b", "value": "Nocturno"}]},
        },
        "text_variables": {"K": '"normal" * (%A=a) + "nocturno" * (%A=b)'},
        "resumen": "Prueba de zanja de 2 m $A $K. ($L(%A))\\",
        "texto": "\\Prueba de zanja de 2 m de ancho con trabajo $A en modo $K. ($L(%A))",
    },
}


class _ScriptedClient:
    """Returns responses in order; records prompts."""

    def __init__(self, responses):
        self._queue = list(responses)
        self.prompts: list[str] = []

    def complete(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self._queue:
            raise AssertionError("no more scripted responses")
        return self._queue.pop(0)


def _resp(*news, original="\\Prueba de zanja de 2 m de ancho con trabajo $A en modo $K. ($L(%A))"):
    return json.dumps(
        [{"original": original, "new": n, "preserves_meaning": True} for n in news],
        ensure_ascii=False,
    )


def test_strip_fiebdc_removes_edge_backslashes_only():
    assert _strip_fiebdc("\\Prueba $A\\") == "Prueba $A"
    assert _strip_fiebdc("  \\ Prueba $A ") == "Prueba $A"
    assert _strip_fiebdc("sin barra") == "sin barra"


def test_rounds_are_three_named_ops():
    assert [r.tag for r in ROUNDS] == ["R1", "R2", "R3"]
    assert "pasiva" in ROUNDS[0].instructions or "voz" in ROUNDS[0].instructions
    assert ROUNDS[2].wants_forbidden_openings is True


def test_wrap_round_embeds_tag_n_and_forbidden_openings():
    w = _wrap_round("BASE", ROUNDS[2], n=3, forbidden_openings=("Prueba de zanja",))
    assert "BASE" in w and "R3" in w and "3" in w and "Prueba de zanja" in w


def test_forbidden_openings_first_six_words():
    payloads = [{"new": "uno dos tres cuatro cinco seis siete ocho"}]
    assert _forbidden_openings(payloads) == ("uno dos tres cuatro cinco seis",)


def test_propose_diverse_pools_two_models_and_tags_provenance():
    inv = scan_chapter(_STAGE)
    targets = inv.by_type[ModificationType.TEMPLATE_PARAPHRASE]
    texto_target = next(t for t in targets if t.dedup_key[0] == "TEXTO")
    # Two targets (RESUMEN before TEXTO in dedup-key order) x 3 rounds per
    # model: the RESUMEN rounds get junk (parse-skip, no candidates), the
    # TEXTO rounds get the real scripted responses; sanitized original (no
    # backslash) in responses.
    orig = "Prueba de zanja de 2 m de ancho con trabajo $A en modo $K. ($L(%A))"
    clients = {
        "phi4": _ScriptedClient(["no json"] * 3 + [
            _resp("Se prueba la zanja de 2 m de ancho, trabajo $A, modo $K. ($L(%A))", original=orig),
            _resp("($L(%A)) En modo $K y con trabajo $A: prueba de zanja de 2 m de ancho.", original=orig),
            _resp("La zanja, de 2 m de ancho, se somete a prueba con trabajo $A y modo $K. ($L(%A))", original=orig),
        ]),
        "qwen": _ScriptedClient(["no json"] * 3 + [
            _resp("Ensayo de zanja con 2 m de ancho para trabajo $A en modo $K. ($L(%A))", original=orig),
            _resp("Con trabajo $A y modo $K se ensaya una zanja de 2 m de ancho. ($L(%A))", original=orig),
            _resp("Zanja de 2 m de ancho: ensayo bajo trabajo $A, modo $K. ($L(%A))", original=orig),
        ]),
    }
    sets = propose_diverse(_STAGE, inv, clients, n_per_round=1)
    cs = sets[texto_target.dedup_key]
    assert len(cs.candidates) == 6
    models = {c.payload["proposer_model"] for c in cs.candidates}
    assert models == {"phi4", "qwen"}
    # every prompt saw the sanitized template (no raw backslash from the stage JSON)
    for client in clients.values():
        for p in client.prompts:
            assert "\\Prueba" not in p
    # TEXTO's prompts are indices 3-5 per client; index 5 is its R3, which
    # carries the forbidden openings harvested from that model's R1/R2 keeps.
    r3_prompts = [c.prompts[5] for c in clients.values()]
    assert all("R3" in p for p in r3_prompts)
    assert "Se prueba la zanja de 2" in clients["phi4"].prompts[5]


def test_propose_diverse_applies_validators():
    inv = scan_chapter(_STAGE)
    orig = "Prueba de zanja de 2 m de ancho con trabajo $A en modo $K. ($L(%A))"
    bad_quantity = "Se prueba la zanja de 3 m de ancho, trabajo $A, modo $K. ($L(%A))"
    lost_placeholder = "Se prueba la zanja de 2 m de ancho, trabajo $A. ($L(%A))"
    good = "Queda probada la zanja de 2 m de ancho — trabajo $A, modo $K. ($L(%A))"
    clients = {
        # 3 junk responses for the RESUMEN target's rounds, then the TEXTO rounds.
        "phi4": _ScriptedClient(["no json"] * 3 + [
            _resp(bad_quantity, original=orig),
            _resp(lost_placeholder, original=orig),
            _resp(good, original=orig),
        ]),
    }
    sets = propose_diverse(_STAGE, inv, clients, n_per_round=1)
    texto = next(v for k, v in sets.items() if k[0] == "TEXTO")
    news = [c.payload["new"] for c in texto.candidates]
    assert news == [good]
    assert any("quantities_not_conserved" in d for d in texto.dropped_reasons)
    assert any("placeholders_not_preserved" in d for d in texto.dropped_reasons)
