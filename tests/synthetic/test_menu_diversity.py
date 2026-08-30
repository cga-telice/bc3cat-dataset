"""Sprint 38.6 — hermetic tests for :mod:`synthetic.menu_diversity`.

Sprint 38.6-B: the diversity flow masks placeholders and quantities behind
``[[Pn]]``/``[[Qn]]`` sentinels before prompting, and restores them after.
Scripted responses therefore echo the MASKED world; expected masked strings
are derived by calling :func:`mask_invariants` on the sanitized template
(never by hardcoding sentinel ids).
"""
from __future__ import annotations

import json

import pytest

from synthetic.menu_diversity import (
    MAX_TOPUP_ROUNDS,
    MIN_CANDIDATES,
    ROUNDS,
    _forbidden_openings,
    _model_store_tag,
    _strip_fiebdc,
    _wrap_round,
    propose_diverse,
)
from synthetic.target_scanner import scan_chapter
from synthetic.taxonomy import ModificationType
from synthetic.template_masking import mask_invariants


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

_TEXTO_SANITIZED = "Prueba de zanja de 2 m de ancho con trabajo $A en modo $K. ($L(%A))"


def _texto_masked():
    """Masked TEXTO template + mapping, exactly as the module computes it."""
    return mask_invariants(_TEXTO_SANITIZED)


def _mask_with(text: str, mapping: dict) -> str:
    """Rewrite a human-readable variant into the masked world by replacing
    each mapped literal with its sentinel (longest literal first, one
    occurrence each — the test templates carry each literal exactly once)."""
    for sid, literal in sorted(mapping.items(), key=lambda kv: -len(kv[1])):
        assert literal in text, f"test variant lost literal {literal!r}: {text!r}"
        text = text.replace(literal, f"[[{sid}]]", 1)
    return text


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


def _resp(*news, original=_TEXTO_SANITIZED):
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
    # Sprint 38.6-B: the constant leave-the-sentinels-alone instruction.
    assert "marcadores intocables" in w
    assert "no los modifiques" in w


def test_forbidden_openings_first_six_words():
    payloads = [{"new": "uno dos tres cuatro cinco seis siete ocho"}]
    assert _forbidden_openings(payloads) == ("uno dos tres cuatro cinco seis",)


def test_model_store_tags_distinguish_sizes():
    assert _model_store_tag("qwen2.5:14b") != _model_store_tag("qwen2.5:32b")


def test_prompts_carry_masked_template_and_sentinel_instruction():
    inv = scan_chapter(_STAGE)
    # Two targets (RESUMEN before TEXTO) x (3 base rounds + 2 top-ups,
    # since junk yields 0 < MIN_CANDIDATES); all responses junk — this
    # test only inspects the prompts.
    client = _ScriptedClient(["no json"] * 10)
    propose_diverse(_STAGE, inv, {"phi4": client}, n_per_round=1)
    assert len(client.prompts) == 10

    first = client.prompts[0]
    assert "[[" in first
    assert "marcadores intocables" in first
    assert "no los modifiques" in first

    masked, mapping = _texto_masked()
    texto_prompt = client.prompts[5]  # TEXTO target's R1
    # The Plantilla line carries the masked template, not the raw one.
    assert masked in texto_prompt
    assert "trabajo $A en modo $K" not in texto_prompt
    # The placeholders slot now lists the sentinels the model actually sees.
    sentinel_list = ", ".join(f"[[{k}]]" for k in mapping)
    assert sentinel_list in texto_prompt


def test_candidate_with_dropped_sentinel_is_rejected():
    inv = scan_chapter(_STAGE)
    masked, mapping = _texto_masked()
    good = "Queda probada la zanja de 2 m de ancho — trabajo $A, modo $K. ($L(%A))"
    good_masked = _mask_with(good, mapping)
    q_sid = next(k for k in mapping if k.startswith("Q"))
    dropped_q = good_masked.replace(f"[[{q_sid}]]", "")
    assert f"[[{q_sid}]]" not in dropped_q
    clients = {
        # RESUMEN: 3 base + 2 top-up rounds of junk; TEXTO: 3 base rounds
        # + 2 top-up rounds (still < MIN_CANDIDATES after the drop).
        "phi4": _ScriptedClient(["no json"] * 5 + [
            _resp(dropped_q, original=masked),
            "no json",
            "no json",
        ] + ["no json"] * 2),
    }
    sets = propose_diverse(_STAGE, inv, clients, n_per_round=1)
    texto = next(v for k, v in sets.items() if k[0] == "TEXTO")
    assert texto.candidates == ()
    assert any("sentinels_not_preserved" in d for d in texto.dropped_reasons)


def test_surviving_candidate_is_unmasked_and_validated():
    inv = scan_chapter(_STAGE)
    masked, mapping = _texto_masked()
    good = "Queda probada la zanja de 2 m de ancho — trabajo $A, modo $K. ($L(%A))"
    good_masked = _mask_with(good, mapping)
    clients = {
        # RESUMEN: 5 junk rounds (3 base + 2 top-up); TEXTO: one keep in
        # R1, junk for R2/R3 and the two top-up rounds (1 < MIN_CANDIDATES).
        "phi4": _ScriptedClient(["no json"] * 5 + [
            _resp(good_masked, original=masked),
            "no json",
            "no json",
        ] + ["no json"] * 2),
    }
    sets = propose_diverse(_STAGE, inv, clients, n_per_round=1)
    texto = next(v for k, v in sets.items() if k[0] == "TEXTO")
    assert len(texto.candidates) == 1
    payload = texto.candidates[0].payload
    # Restored literals, no sentinel residue anywhere in the payload.
    assert payload["new"] == good
    assert "2 m" in payload["new"]
    assert "[[" not in json.dumps(payload, ensure_ascii=False)
    # The echoed original is overwritten with the known true template.
    assert payload["original"] == _TEXTO_SANITIZED
    assert payload["proposer_model"] == "phi4"


def test_propose_diverse_pools_two_models_and_tags_provenance():
    inv = scan_chapter(_STAGE)
    targets = inv.by_type[ModificationType.TEMPLATE_PARAPHRASE]
    texto_target = next(t for t in targets if t.dedup_key[0] == "TEXTO")
    # Two targets (RESUMEN before TEXTO in dedup-key order) x 3 rounds per
    # model: the RESUMEN rounds get junk (parse-skip, no candidates), the
    # TEXTO rounds get the real scripted responses. Responses live in the
    # masked world: each `new` carries every sentinel exactly once.
    masked, mapping = _texto_masked()
    phi4_news = [
        _mask_with(n, mapping) for n in (
            "Se prueba la zanja de 2 m de ancho, trabajo $A, modo $K. ($L(%A))",
            "($L(%A)) En modo $K y con trabajo $A: prueba de zanja de 2 m de ancho.",
            "La zanja, de 2 m de ancho, se somete a prueba con trabajo $A y modo $K. ($L(%A))",
        )
    ]
    qwen_news = [
        _mask_with(n, mapping) for n in (
            "Ensayo de zanja con 2 m de ancho para trabajo $A en modo $K. ($L(%A))",
            "Con trabajo $A y modo $K se ensaya una zanja de 2 m de ancho. ($L(%A))",
            "Zanja de 2 m de ancho: ensayo bajo trabajo $A, modo $K. ($L(%A))",
        )
    ]
    clients = {
        # RESUMEN consumes 5 junk rounds per model (3 base + 2 top-up);
        # TEXTO's 6 pooled survivors reach MIN_CANDIDATES, so no top-up.
        "phi4": _ScriptedClient(
            ["no json"] * 5 + [_resp(n, original=masked) for n in phi4_news]),
        "qwen": _ScriptedClient(
            ["no json"] * 5 + [_resp(n, original=masked) for n in qwen_news]),
    }
    sets = propose_diverse(_STAGE, inv, clients, n_per_round=1)
    cs = sets[texto_target.dedup_key]
    assert len(cs.candidates) == 6
    models = {c.payload["proposer_model"] for c in cs.candidates}
    assert models == {"phi4", "qwen"}
    # Stored payloads are fully unmasked.
    for c in cs.candidates:
        assert "[[" not in json.dumps(c.payload, ensure_ascii=False)
    # every prompt saw the sanitized template (no raw backslash from the stage JSON)
    for client in clients.values():
        for p in client.prompts:
            assert "\\Prueba" not in p
    # TEXTO's prompts are indices 5-7 per client; index 7 is its R3, which
    # carries the forbidden openings harvested from that model's R1/R2 keeps
    # (openings are harvested from RESTORED text, hence the literal "2").
    r3_prompts = [c.prompts[7] for c in clients.values()]
    assert all("R3" in p for p in r3_prompts)
    assert "Se prueba la zanja de 2" in clients["phi4"].prompts[7]
    # 5 RESUMEN + 3 TEXTO prompts per model, nothing more.
    assert all(len(c.prompts) == 8 for c in clients.values())


def test_propose_diverse_applies_validators():
    inv = scan_chapter(_STAGE)
    masked, mapping = _texto_masked()
    good = "Queda probada la zanja de 2 m de ancho — trabajo $A, modo $K. ($L(%A))"
    good_masked = _mask_with(good, mapping)
    # Quantities and placeholders are sentinels now, so the old "3 m" /
    # lost-"$K" corruptions cannot be expressed in text — both failure
    # modes surface as dropped sentinels instead.
    q_sid = next(k for k in mapping if mapping[k] == "2 m")
    p_sid = next(k for k in mapping if mapping[k] == "$K")
    dropped_q_sentinel = good_masked.replace(f"[[{q_sid}]]", "")
    dropped_p_sentinel = good_masked.replace(f"[[{p_sid}]]", "")
    clients = {
        # 5 junk responses for the RESUMEN target's rounds (base + top-up),
        # then the TEXTO base rounds, then its two junk top-up rounds
        # (1 survivor < MIN_CANDIDATES).
        "phi4": _ScriptedClient(["no json"] * 5 + [
            _resp(dropped_q_sentinel, original=masked),
            _resp(dropped_p_sentinel, original=masked),
            _resp(good_masked, original=masked),
        ] + ["no json"] * 2),
    }
    sets = propose_diverse(_STAGE, inv, clients, n_per_round=1)
    texto = next(v for k, v in sets.items() if k[0] == "TEXTO")
    news = [c.payload["new"] for c in texto.candidates]
    assert news == [good]
    n_sentinel_drops = sum(
        1 for d in texto.dropped_reasons if "sentinels_not_preserved" in d
    )
    assert n_sentinel_drops == 2


def test_topup_rounds_fire_until_min_candidates():
    assert MIN_CANDIDATES == 6 and MAX_TOPUP_ROUNDS == 2
    inv = scan_chapter(_STAGE)
    masked, mapping = _texto_masked()
    base_good = "Se prueba la zanja de 2 m de ancho, trabajo $A, modo $K. ($L(%A))"
    t1_news = [
        "($L(%A)) En modo $K y con trabajo $A: prueba de zanja de 2 m de ancho.",
        "La zanja, de 2 m de ancho, se somete a prueba con trabajo $A y modo $K. ($L(%A))",
        "Ensayo de zanja con 2 m de ancho para trabajo $A en modo $K. ($L(%A))",
    ]
    t2_news = [
        "Con trabajo $A y modo $K se ensaya una zanja de 2 m de ancho. ($L(%A))",
        "Zanja de 2 m de ancho: ensayo bajo trabajo $A, modo $K. ($L(%A))",
        "Queda probada la zanja de 2 m de ancho — trabajo $A, modo $K. ($L(%A))",
    ]
    client = _ScriptedClient(
        ["no json"] * 5  # RESUMEN: 3 base + 2 top-up rounds, all junk
        + [
            _resp(_mask_with(base_good, mapping), original=masked),  # R1 -> 1 keep
            "no json",  # R2
            "no json",  # R3
            _resp(*[_mask_with(n, mapping) for n in t1_news], original=masked),  # T1
            _resp(*[_mask_with(n, mapping) for n in t2_news], original=masked),  # T2
        ]
    )
    sets = propose_diverse(_STAGE, inv, {"phi4": client}, n_per_round=1)
    texto = next(v for k, v in sets.items() if k[0] == "TEXTO")
    # 1 keep after base rounds (< 6) -> T1 (4 keeps, still < 6) -> T2 (7).
    assert len(texto.candidates) >= MIN_CANDIDATES
    # RESUMEN got 5 prompts; TEXTO got R1,R2,R3,T1,T2 = 5 more.
    assert len(client.prompts) == 10
    texto_prompts = client.prompts[5:]
    assert "IMPORTANTE (T1)" in texto_prompts[3]
    assert "IMPORTANTE (T2)" in texto_prompts[4]
    # Top-up rounds forbid the openings of the keeps pooled so far
    # (restored text: the base R1 keep's first words).
    assert "Se prueba la zanja de 2" in texto_prompts[3]


def test_no_topup_when_enough_candidates():
    inv = scan_chapter(_STAGE)
    masked, mapping = _texto_masked()
    news = [
        "Se prueba la zanja de 2 m de ancho, trabajo $A, modo $K. ($L(%A))",
        "($L(%A)) En modo $K y con trabajo $A: prueba de zanja de 2 m de ancho.",
        "La zanja, de 2 m de ancho, se somete a prueba con trabajo $A y modo $K. ($L(%A))",
        "Ensayo de zanja con 2 m de ancho para trabajo $A en modo $K. ($L(%A))",
        "Con trabajo $A y modo $K se ensaya una zanja de 2 m de ancho. ($L(%A))",
        "Zanja de 2 m de ancho: ensayo bajo trabajo $A, modo $K. ($L(%A))",
    ]
    masked_news = [_mask_with(n, mapping) for n in news]
    client = _ScriptedClient(
        ["no json"] * 5  # RESUMEN: 3 base + 2 top-up rounds, all junk
        + [
            _resp(*masked_news[0:2], original=masked),  # R1
            _resp(*masked_news[2:4], original=masked),  # R2
            _resp(*masked_news[4:6], original=masked),  # R3
        ]
    )
    sets = propose_diverse(_STAGE, inv, {"phi4": client}, n_per_round=2)
    texto = next(v for k, v in sets.items() if k[0] == "TEXTO")
    assert len(texto.candidates) >= MIN_CANDIDATES
    # Base rounds already reach MIN_CANDIDATES: exactly 3 TEXTO prompts,
    # none of them a top-up.
    assert len(client.prompts) == 8
    assert not any("IMPORTANTE (T" in p for p in client.prompts[5:])
