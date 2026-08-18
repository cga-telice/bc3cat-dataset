"""Sprint 27 — Phase F Task F1-build: the pilot harness.

Covers `synthetic.f1_pilot` — the driver that composes the frozen stack
(`run_concept` -> `stage_b` -> `metadata` -> `review`) over one concept with the
`l2_repr` two-mode adapter bracketing the mutation — and the `stage_b` `pre_rerun`
hook that makes the formula->list restore insertable.

All hermetic: a tiny in-memory mixed-shape concept + a canned/Replay client. The
live local generation is the Sprint-28 CLI, never a `pytest` case — no test opens
a socket.
"""

import importlib
import inspect
import json

import pytest

from synthetic import f1_pilot
from synthetic.f1_pilot import (
    PilotScore,
    default_conditions,
    format_scorecard,
    load_pilot_concept,
    run_pilot,
)
from synthetic import l2_repr
from synthetic.llm_client import ReplayClient
from synthetic.run_synthetic import run_concept
from synthetic.stage_b import materialize_variant


_KEY = "OEB999$"


def _concept():
    """One axis B; all three text-variable shapes (plain / str / conditional)."""
    return {
        _KEY: {
            "ud": "m", "concept": "T", "parent_key": _KEY,
            "parameters": {"B": {"label": "AX", "values": [
                {"label": "a", "value": "Diurno"}, {"label": "b", "value": "Nocturno"}]}},
            "text_variables": {
                "L": ['"Diurno"', '"Nocturno"'],
                "K": '"k_a" * (%B=="a") + "k_b" * (%B=="b")',
                "P": ['"p_a" * (%B=="a")', '"p_b" * (%B=="b")'],
            },
            "resumen": "Canal $L(%B) $K $P",
            "texto": "Canal $L(%B) $K $P fin",
        }
    }


class _ConstClient:
    def __init__(self, response):
        self._response = response
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._response


_PARAPHRASE_OK = json.dumps(
    {"original": "Diurno", "new": "Jornada diurna", "preserves_meaning": True}
)
_MALFORMED = "not json at all {"


def _dirs(tmp_path):
    return dict(
        store_root=tmp_path / "store", variants_dir=tmp_path / "variants",
        intermediate_dir=tmp_path / "inter", review_dir=tmp_path / "review",
    )


# ========================================================================
# Public surface / conditions
# ========================================================================

def test_default_conditions_are_all_eighteen_sorted():
    # Sprint 36: TEMPLATE_PARAPHRASE (L3) adds `single_L3_template_paraphrase`
    # to the condition list; 17 → 18.
    cs = default_conditions()
    assert len(cs) == 18
    assert list(cs) == sorted(cs)


def test_load_pilot_concept_slices_one():
    full = _concept()
    full["OEBxxx$"] = {"resumen": "x"}
    sliced = load_pilot_concept(full, _KEY)
    assert set(sliced) == {_KEY}


# ========================================================================
# run_pilot — end-to-end composition (hermetic)
# ========================================================================

def test_run_pilot_l2_fires_and_queue_is_full_coverage(tmp_path):
    score = run_pilot(
        _concept(), _KEY, client=_ConstClient(_PARAPHRASE_OK),
        conditions=["single_L2_paraphrase"], seed=7, **_dirs(tmp_path),
    )
    assert isinstance(score, PilotScore)
    assert score.l2_targets == 6           # L(2) + K(2) + P(2) enumerable
    assert score.variants_generated == 6   # one per L2 target
    assert score.materialized_items == 12  # 6 variants x 2 leaves
    assert score.reviewable_items == 12    # all carry the applied paraphrase
    assert score.queue_size == 12
    assert score.coverage_fraction == 1.0  # 100 % of reviewable items


def test_run_pilot_writes_review_queue_file(tmp_path):
    d = _dirs(tmp_path)
    run_pilot(_concept(), _KEY, client=_ConstClient(_PARAPHRASE_OK),
              conditions=["single_L2_paraphrase"], seed=7, **d)
    assert (d["review_dir"] / f"{_KEY}_review_queue.jsonl").exists()


def test_run_pilot_items_validate_no_exception(tmp_path):
    # run_pilot calls metadata.validate_items internally; a clean run proves the
    # materialized items satisfy the SyntheticItem schema (the integration risk).
    score = run_pilot(_concept(), _KEY, client=_ConstClient(_PARAPHRASE_OK),
                      conditions=["single_L2_paraphrase", "single_L1_synonym_label"],
                      seed=7, **_dirs(tmp_path))
    assert score.materialized_items > 0


def test_run_pilot_malformed_response_lands_in_malformed_bucket(tmp_path):
    score = run_pilot(_concept(), _KEY, client=_ConstClient(_MALFORMED),
                      conditions=["single_L2_paraphrase"], seed=7, **_dirs(tmp_path))
    assert score.variants_generated == 0
    assert score.malformed_skips >= 1
    assert score.schema_skips == 0


def test_run_pilot_replay_reproduces_score_offline(tmp_path):
    d = _dirs(tmp_path)
    live = run_pilot(_concept(), _KEY, client=_ConstClient(_PARAPHRASE_OK),
                     conditions=["single_L2_paraphrase"], seed=7, **d)

    def _exploding(prompt):
        raise AssertionError("replay must not call a live client")

    class _Boom:
        complete = staticmethod(_exploding)

    replayed = run_pilot(_concept(), _KEY, client=_Boom(),
                         conditions=["single_L2_paraphrase"], seed=7, replay=True, **d)
    assert replayed.to_dict() == live.to_dict()


# ========================================================================
# stage_b pre_rerun hook
# ========================================================================

def _one_variant(tmp_path):
    enum, _ = l2_repr.list_to_formula(_concept(), include_conditional=True)
    entry, _ = run_concept(enum, _KEY, ["single_L2_paraphrase"],
                           _ConstClient(_PARAPHRASE_OK),
                           out_dir=tmp_path / "v", seed=7)
    appl, _ = l2_repr.list_to_formula(_concept(), include_conditional=False)
    return appl, entry.variants[0]


def test_materialize_default_pre_rerun_equals_explicit_identity(tmp_path):
    appl, variant = _one_variant(tmp_path)
    default = materialize_variant(appl, _KEY, variant)
    identity = materialize_variant(appl, _KEY, variant, pre_rerun=lambda c: c)
    assert default.items == identity.items   # default is identity (backward-compat)


def test_materialize_pre_rerun_is_invoked_once(tmp_path):
    appl, variant = _one_variant(tmp_path)
    seen = []

    def spy(concept_dict):
        seen.append(concept_dict)
        return concept_dict

    materialize_variant(appl, _KEY, variant, pre_rerun=spy)
    assert len(seen) == 1


def test_pre_rerun_formula_to_list_renders_cleanly(tmp_path):
    # With formula_to_list as the hook, an indexed LIST_plain var mutated in
    # formula form is restored to a positional list → the rerun renders without
    # the mangled `* (%...` artifacts a raw formula would leave.
    appl, variant = _one_variant(tmp_path)
    mv = materialize_variant(appl, _KEY, variant, pre_rerun=l2_repr.formula_to_list)
    blob = json.dumps(mv.items, ensure_ascii=False)
    assert "* (%" not in blob


# ========================================================================
# Scorecard + hygiene
# ========================================================================

def test_format_scorecard_has_no_fluency_field():
    fields = set(PilotScore.__dataclass_fields__)
    assert not any("fluen" in f.lower() for f in fields)


def test_format_scorecard_renders_key_metrics(tmp_path):
    score = run_pilot(_concept(), _KEY, client=_ConstClient(_PARAPHRASE_OK),
                      conditions=["single_L2_paraphrase"], seed=7, **_dirs(tmp_path))
    text = format_scorecard(score)
    assert "generated" in text and "coverage" in text and "l2_targets" in text


def test_f1_pilot_not_imported_by_any_seam_module():
    for mod_name in (
        "synthetic.run_synthetic", "synthetic.stage_b", "synthetic.metadata",
        "synthetic.review", "synthetic.l2_repr",
    ):
        mod = importlib.import_module(mod_name)
        assert "f1_pilot" not in mod.__dict__, mod_name


def test_f1_pilot_adds_no_third_party_dependency():
    src = inspect.getsource(f1_pilot)
    for banned in ("import requests", "import httpx", "import openai", "import anthropic"):
        assert banned not in src
