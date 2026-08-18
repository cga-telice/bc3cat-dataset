"""Sprint 29 — Phase F Task F2: the two F1-findings fixes.

F1-run-generate on `OEB070$` with `llama3.1:8b` exposed two model-driven defects
the frozen seam did not catch:

  1. **JSON reliability** — 8B wraps its JSON in prose + Markdown fences (e.g.
     "Aquí te dejo la respuesta: ```{…}```"), which the old fence-at-start
     stripper missed → 31 `malformed_llm_response_after_retry` skips. Fix:
     `llm_proposer._extract_json_object` recovers the object from prose/fence.
  2. **Placeholder corruption** — omission/reorder rewrote templates but 8B
     mangled placeholders (`$L(%B)` → `$/($B)`), and the string-only validators
     accepted them → broken templates materialized. Fix:
     `variant_proposer` placeholder-preservation checks (reorder: set equality;
     omission: original minus the omitted var's tokens).

All hermetic.
"""

import json

import pytest

from synthetic.llm_proposer import _parse_json_object, propose
from synthetic.variant_proposer import _validate_payload
from synthetic.taxonomy import ModificationType


# ========================================================================
# Fix 1 — JSON extraction robustness
# ========================================================================

_GOOD = '{"original":"a","new":"b","preserves_meaning":true}'


@pytest.mark.parametrize("wrapped", [
    _GOOD,                                                   # bare
    f"```\n{_GOOD}\n```",                                    # fence at start
    f"```json\n{_GOOD}\n```",                                # json-tagged fence
    f"Aquí te dejo la respuesta en formato JSON:\n```\n{_GOOD}\n```",  # prose + fence
    f"Claro, aquí está: ```json {_GOOD} ``` espero te sirva",          # inline prose+fence
    f"La respuesta es {_GOOD} listo",                        # prose + bare object
])
def test_extract_json_recovers_wrapped_object(wrapped):
    assert _parse_json_object(wrapped) == json.loads(_GOOD)


@pytest.mark.parametrize("garbage", ["not json at all {", "", "   ", "Hola, no tengo JSON"])
def test_extract_json_still_rejects_garbage(garbage):
    with pytest.raises(ValueError):
        _parse_json_object(garbage)


class _StubClient:
    def __init__(self, responses):
        self._responses = list(responses)

    def complete(self, prompt: str) -> str:
        return self._responses.pop(0)


def test_propose_recovers_prose_wrapped_json_without_fallback():
    # the exact 8B failure mode: prose + fence around a valid payload
    resp = ('Aquí te dejo la respuesta en formato JSON:\n```json\n'
            '{"synonyms":[{"original":"110 mm","new":"110 milímetros"}]}\n```')
    result = propose("prompt", _StubClient([resp]), ModificationType.UNIT_EXPANSION)
    assert result.fallback is None
    assert result.payload == {"synonyms": [{"original": "110 mm", "new": "110 milímetros"}]}


# ========================================================================
# Fix 2 — placeholder preservation (reorder / omission)
# ========================================================================

_ORIG = ("Suministro y ejecución de canalización de $A tubo(s) de polietileno "
         "110 mm 5 At. con topo bajo vías ($L(%B)/$M(%C)/$N(%D))")


def _reorder(new):
    return {"original": _ORIG, "new": new, "preserves_meaning": True}


def _omission(new, omitted):
    return {"original": _ORIG, "new": new, "omitted_var": omitted}


def test_reorder_clean_placeholders_accepted():
    new = "($N(%D)) primero, luego $A tubo(s) ($L(%B)/$M(%C))"
    assert _validate_payload(_reorder(new), ModificationType.REORDER) is not None


def test_reorder_corrupted_placeholders_rejected():
    new = "Suministro ... ($L/%$B/$M/%$C/$N/%$D)"   # the real 8B corruption
    with pytest.raises(ValueError, match="placeholders_not_preserved"):
        _validate_payload(_reorder(new), ModificationType.REORDER)


def test_reorder_dropped_placeholder_rejected():
    new = "canalización de $A tubo(s) ($L(%B)/$M(%C))"   # lost $N(%D)
    with pytest.raises(ValueError, match="placeholders_not_preserved"):
        _validate_payload(_reorder(new), ModificationType.REORDER)


def test_omission_clean_accepted():
    new = "Suministro ... de tubo(s) ... ($L(%B)/$M(%C)/$N(%D))"   # omit $A
    assert _validate_payload(_omission(new, "A"), ModificationType.OMISSION) is not None


def test_omission_corrupted_placeholder_rejected():
    new = "... de $A tubo(s) ... ($/($B)/$M(%C)/$N(%D))"   # omit L, mangled $L(%B)
    with pytest.raises(ValueError, match="placeholders_not_preserved_after_omission"):
        _validate_payload(_omission(new, "L"), ModificationType.OMISSION)


def test_omission_must_drop_exactly_the_omitted_var():
    # omit M but the model also dropped N → not exactly the omitted set
    new = "... de $A tubo(s) ... ($L(%B))"
    with pytest.raises(ValueError, match="placeholders_not_preserved_after_omission"):
        _validate_payload(_omission(new, "M"), ModificationType.OMISSION)


def test_l2_paraphrase_unaffected_by_placeholder_check():
    # paraphrase operates on placeholder-free fragments; the new check is a no-op
    payload = {"original": "bajo vías", "new": "por debajo de la vía", "preserves_meaning": True}
    assert _validate_payload(payload, ModificationType.PARAPHRASE) is not None


# ========================================================================
# Sprint 31 — L2-content placeholder guard
#
# F1-review found L2 expansions (digest #23, #31, #42) whose `new` fragment
# re-embeds template placeholders such as `($L(%B)/$M(%C)/$N(%D))`. Once
# materialized these leak verbatim into the rendered resumen/texto. The
# structural-only validator missed them because L2 fragments are not
# themselves templates. Guard added: `new` must not contain any $VAR or
# $VAR(%AXIS) token for the three L2 types.
# ========================================================================


def _l2(original, new):
    return {"original": original, "new": new, "preserves_meaning": True}


@pytest.mark.parametrize("mtype", [
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
])
def test_l2_clean_fragment_accepted(mtype):
    # clean rewrite with no template placeholders → passes
    payload = _l2("Nocturno", "Noche")
    assert _validate_payload(payload, mtype) is not None


@pytest.mark.parametrize("mtype", [
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
])
def test_l2_fragment_with_dollar_var_rejected(mtype):
    # digest #42-style bare $A leaked into an L2 fragment
    payload = _l2("Volumen escaso", "Volumen de $A tubos")
    with pytest.raises(ValueError, match="fragment_contains_template_placeholders"):
        _validate_payload(payload, mtype)


def test_l2_expansion_full_template_scaffold_rejected():
    # digest #23: expansion re-embeds the full ($L(%B)/$M(%C)/$N(%D)) scaffold
    leak = ("Volumen de canalización de $A tubo(s) de polietileno 110 mm "
            "($L(%B)/$M(%C)/$N(%D))")
    with pytest.raises(ValueError, match="fragment_contains_template_placeholders"):
        _validate_payload(_l2("Volumen relevante", leak), ModificationType.EXPANSION)


def test_l2_paraphrase_axis_reference_rejected():
    # $L(%B) — variable with axis qualifier
    payload = _l2("Diurno", "durante $L(%B)")
    with pytest.raises(ValueError, match="fragment_contains_template_placeholders"):
        _validate_payload(payload, ModificationType.PARAPHRASE)


def test_l2_dollar_sign_in_prose_not_a_placeholder():
    # a dollar sign followed by non-identifier characters is prose, not a placeholder
    payload = _l2("coste elevado", "coste de $ 100 por tubo")
    # "$ 100" — no identifier after $ → not a placeholder token; must be accepted
    assert _validate_payload(payload, ModificationType.COMPRESSION) is not None


def test_l2_reorder_guard_still_uses_preservation_not_new_content():
    # sanity: reorder is L3 (template), keeps its own placeholders-preserved guard,
    # unaffected by the new L2 content guard.
    orig = "Suministro $A tubo(s) ($L(%B))"
    new = "($L(%B)) primero, luego $A tubo(s)"   # placeholders preserved
    assert _validate_payload(
        {"original": orig, "new": new, "preserves_meaning": True},
        ModificationType.REORDER,
    ) is not None
