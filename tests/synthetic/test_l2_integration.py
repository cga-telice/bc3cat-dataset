"""Sprint 26 — Task B6: L2 fires end-to-end on the real list-form shape.

These pin the *bug* and the *fix* at the seam the adapter feeds: before
`list_to_formula`, `enumerate_targets` finds zero L2 targets on the real
list-form concept (the silent no-op); after, it enumerates them and `run_concept`
emits an L2 variant. Hermetic — a tiny inline list-form fixture + a const stub
client; zero network.
"""

import json

from synthetic.l2_repr import list_to_formula
from synthetic.slot_extractor import enumerate_targets
from synthetic.run_synthetic import run_concept
from synthetic.taxonomy import ModificationType


_KEY = "OEB999$"


def _concept():
    return {
        _KEY: {
            "ud": "m",
            "concept": "TEST",
            "parent_key": _KEY,
            "parameters": {
                "B": {"label": "TRABAJO", "values": [
                    {"label": "a", "value": "Diurno"},
                    {"label": "b", "value": "Nocturno"}]},
                "D": {"label": "COND", "values": [
                    {"label": "a", "value": "Rel"},
                    {"label": "b", "value": "Esc"}]},
            },
            "text_variables": {
                "L": ['"Diurno"', '"Nocturno"'],
                "N": ['"Rel"', '"Esc"'],
            },
            "resumen": "Canal ($L(%B)/$N(%D))",
            "texto": "Canal trabajo $L(%B) cond $N(%D) fin",
        }
    }


class _ConstLLMClient:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._response


_PARAPHRASE_OK = json.dumps(
    {"original": "Diurno", "new": "Jornada diurna", "preserves_meaning": True}
)


def test_raw_list_form_enumerates_zero_l2_targets_the_bug():
    raw = _concept()
    for mt in (ModificationType.PARAPHRASE, ModificationType.EXPANSION,
               ModificationType.COMPRESSION):
        assert list(enumerate_targets(raw, _KEY, mt)) == []


def test_converted_form_enumerates_l2_targets_the_fix():
    conv, _ = list_to_formula(_concept())
    targets = list(enumerate_targets(conv, _KEY, ModificationType.PARAPHRASE))
    # 2 vars × 2 conditions
    assert len(targets) == 4
    assert ("L", "%B=a") in targets
    assert ("N", "%D=b") in targets


def test_run_concept_emits_l2_variant_on_converted_concept(tmp_path):
    conv, _ = list_to_formula(_concept())
    client = _ConstLLMClient(_PARAPHRASE_OK)
    entry, _path = run_concept(
        conv, _KEY, ["single_L2_paraphrase"], client,
        out_dir=tmp_path, seed=7,
    )
    assert len(entry.variants) >= 1
    assert all(
        v.modification_type is ModificationType.PARAPHRASE for v in entry.variants
    )


def test_run_concept_emits_nothing_on_raw_list_form(tmp_path):
    # control: without the adapter, the same conditions yield zero L2 variants
    client = _ConstLLMClient(_PARAPHRASE_OK)
    entry, _path = run_concept(
        _concept(), _KEY, ["single_L2_paraphrase"], client,
        out_dir=tmp_path, seed=7,
    )
    assert entry.variants == ()
    assert client.calls == []  # the LLM was never even called


def _mixed():
    """All three shapes on one axis: G plain(indexed) / K str(bare) / P cond(bare)."""
    return {
        _KEY: {
            "ud": "m", "concept": "T", "parent_key": _KEY,
            "parameters": {"B": {"label": "AX", "values": [
                {"label": "a", "value": "AA"}, {"label": "b", "value": "BB"}]}},
            "text_variables": {
                "G": ['"g_a"', '"g_b"'],
                "K": '"k_a" * (%B=="a") + "k_b" * (%B=="b")',
                "P": ['"p_a" * (%B=="a")', '"p_b" * (%B=="b")'],
            },
            "resumen": "R $G(%B) $K $P",
            "texto": "TX $G(%B) $K $P end",
        }
    }


def test_all_three_shapes_become_enumerable_after_adapter():
    raw = _mixed()
    # raw: only the STR_formula K enumerates (it is already a string)
    assert {t[0] for t in enumerate_targets(raw, _KEY, ModificationType.PARAPHRASE)} == {"K"}
    conv, _ = list_to_formula(raw, include_conditional=True)
    vars_after = {t[0] for t in enumerate_targets(conv, _KEY, ModificationType.PARAPHRASE)}
    assert vars_after == {"G", "K", "P"}   # plain + str + conditional all enumerable
