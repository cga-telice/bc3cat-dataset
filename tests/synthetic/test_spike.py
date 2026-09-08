"""Sprint 25 — Phase A Task A3b-build: the model-choice spike harness.

Covers `synthetic.spike` — the harness that composes the unedited
`run_synthetic.run_concept` over one pilot concept across the single-type
conditions, wraps each candidate in a `RecordingClient`, and tallies an
automatable `CandidateScore` off the returned `VariantCatalogEntry`.

Every test is hermetic: a canned in-memory client (the "transcripts") drives the
whole harness, latency rides an injected fake clock, and the recording store is
re-read with a real `ReplayClient`. **No test opens a socket** — the live run is
the manual `python -m synthetic.spike run …` CLI, never a `pytest` case.
"""

import importlib
import json

import pytest

from synthetic import spike
from synthetic.spike import (
    SINGLE_TYPE_CONDITIONS,
    MALFORMED_SKIP_PREFIX,
    SCHEMA_SKIP_PREFIX,
    CandidateScore,
    CandidateSpec,
    format_scorecard,
    run_candidate,
    run_spike,
)
from synthetic.llm_client import LLMConfig, ReplayClient


# ----- canned clients (the "transcripts") -------------------------------

class _ConstClient:
    """Returns the same response on every `complete` call; records prompts."""

    def __init__(self, response):
        self._response = response
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._response


class _QueueClient:
    """Pops one response per `complete` call (then sticks on the last)."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


def _fake_clock():
    """Monotonic fake clock: 0,1,2,3,… → every `complete` measures 1.0s elapsed
    (one tick before, one after). Deterministic, no wall-clock flake."""
    counter = {"t": 0}

    def clock():
        counter["t"] += 1
        return float(counter["t"])

    return clock


# ----- fixtures ---------------------------------------------------------

def _stage():
    return {
        "OEB020aa": {
            "parent_key": "OEB020$",
            "parameters": {
                "B": {"label": "TIPO DE TERRENO",
                      "values": [{"label": "a", "value": "Normal"},
                                 {"label": "b", "value": "Rocoso"}]},
            },
            "text_variables": {"K": '"normal" * (%B=a) + "rocoso" * (%B=b)'},
            "resumen": "Canalización para terreno normal",
            "texto": "Canalización para terreno $K, incluso $N",
        },
    }


# A single JSON object that satisfies *every* per-type schema at once (extra keys
# are ignored by each validator), so a const client drives all 12 single-type
# conditions through C3 validation without a schema skip.
_UNIVERSAL_OK = json.dumps({
    "synonyms": [{"original": "Normal", "new": "Estándar"}],
    "numerals": [{"original": "Normal", "new": "uno"}],
    "original": "normal",
    "new": "corriente",
    "preserves_meaning": True,
    "omitted_var": "N",
    "new_axis_label": "EXTRA",
    "var_definition": '$Z = "x" * (%Z=a) + "y" * (%Z=b)',
    "template_patch": "Canalización ... $Z ...",
    "values": [{"label": "a", "value": "x"}, {"label": "b", "value": "y"}],
})

_SYNONYM_OK = json.dumps({"synonyms": [{"original": "Normal", "new": "Estándar"}]})
_MALFORMED = "not json at all {"
# Valid JSON, wrong shape for synonym_label (no 'synonyms' list) → C3 skip.
_SCHEMA_VIOLATION = json.dumps({"wrong_key": [{"a": 1}]})

_SYN_CONDITION = ["single_L1_synonym_label"]


def _candidate(name="cand", model="m"):
    cfg = LLMConfig(base_url="http://x/v1", model=model, api_key_env="UNUSED_KEY_ENV")
    return CandidateSpec(name=name, config=cfg)


def _factory(client):
    return lambda cfg: client


# ========================================================================
# Public surface / constants
# ========================================================================

def test_module_exposes_public_surface():
    for name in (
        "SINGLE_TYPE_CONDITIONS", "CandidateSpec", "CandidateScore",
        "run_candidate", "run_spike", "format_scorecard", "main",
    ):
        assert hasattr(spike, name), name


def test_single_type_conditions_are_the_thirteen():
    # Sprint 36: TEMPLATE_PARAPHRASE brought the taxonomy to 13 members;
    # SINGLE_TYPE_CONDITIONS enumerates one condition per type.
    assert len(SINGLE_TYPE_CONDITIONS) == 13
    assert "new_param_only" in SINGLE_TYPE_CONDITIONS
    assert sum(1 for c in SINGLE_TYPE_CONDITIONS if c.startswith("single_")) == 12
    # deterministic (sorted) order — reproducible store
    assert list(SINGLE_TYPE_CONDITIONS) == sorted(SINGLE_TYPE_CONDITIONS)


# ========================================================================
# run_candidate — scorecard tallies + recording round-trip
# ========================================================================

def test_run_candidate_success_tallies_one_proposed(tmp_path):
    client = _ConstClient(_SYNONYM_OK)
    score = run_candidate(
        _stage(), "OEB020aa", _candidate(),
        store_root=tmp_path / "store", catalog_root=tmp_path / "cat",
        seed=7, conditions=_SYN_CONDITION, client_factory=_factory(client),
        clock=_fake_clock(),
    )
    assert isinstance(score, CandidateScore)
    assert score.proposed == 1
    assert score.skipped_total == 0
    assert score.malformed_skips == 0
    assert score.schema_skips == 0
    assert score.llm_calls == 1


def test_run_candidate_records_store_that_replayclient_round_trips(tmp_path):
    client = _ConstClient(_SYNONYM_OK)
    store_root = tmp_path / "store"
    run_candidate(
        _stage(), "OEB020aa", _candidate(name="alpha"),
        store_root=store_root, catalog_root=tmp_path / "cat",
        seed=7, conditions=_SYN_CONDITION, client_factory=_factory(client),
        clock=_fake_clock(),
    )
    store_dir = store_root / "alpha"
    assert list(store_dir.glob("*.json")), "recording store is empty"
    replay = ReplayClient(store_dir)
    # every prompt the inner client saw is now served from the store unchanged
    for prompt in client.calls:
        assert replay.complete(prompt) == _SYNONYM_OK


def test_run_candidate_replay_mode_retallies_offline(tmp_path):
    """A second pass with replay=True reads the recorded store (no live client)
    and reproduces the same scorecard counts."""
    store_root = tmp_path / "store"
    cat = tmp_path / "cat"
    cand = _candidate(name="beta")
    first = run_candidate(
        _stage(), "OEB020aa", cand,
        store_root=store_root, catalog_root=cat, seed=7,
        conditions=_SYN_CONDITION, client_factory=_factory(_ConstClient(_SYNONYM_OK)),
        clock=_fake_clock(),
    )

    def _exploding_factory(cfg):  # would be used only on a live call
        raise AssertionError("replay must not build a live client")

    second = run_candidate(
        _stage(), "OEB020aa", cand,
        store_root=store_root, catalog_root=cat, seed=7,
        conditions=_SYN_CONDITION, client_factory=_exploding_factory,
        clock=_fake_clock(), replay=True,
    )
    assert second.proposed == first.proposed
    assert second.skipped_total == first.skipped_total
    assert second.llm_calls == first.llm_calls


# ========================================================================
# C2 / C3 skip-reason split (reads the frozen seam, not its own logic)
# ========================================================================

def test_malformed_response_lands_in_malformed_bucket(tmp_path):
    # malformed twice → retry exhausted → C2 fallback skip
    client = _QueueClient([_MALFORMED, _MALFORMED])
    score = run_candidate(
        _stage(), "OEB020aa", _candidate(),
        store_root=tmp_path / "s", catalog_root=tmp_path / "c",
        seed=7, conditions=_SYN_CONDITION, client_factory=_factory(client),
        clock=_fake_clock(),
    )
    assert score.proposed == 0
    assert score.malformed_skips == 1
    assert score.schema_skips == 0


def test_schema_violation_lands_in_schema_bucket(tmp_path):
    client = _ConstClient(_SCHEMA_VIOLATION)
    score = run_candidate(
        _stage(), "OEB020aa", _candidate(),
        store_root=tmp_path / "s", catalog_root=tmp_path / "c",
        seed=7, conditions=_SYN_CONDITION, client_factory=_factory(client),
        clock=_fake_clock(),
    )
    assert score.proposed == 0
    assert score.schema_skips == 1
    assert score.malformed_skips == 0


def test_skip_prefixes_match_the_frozen_seam():
    # tripwire: the buckets partition on the exact reason-prefixes the
    # proposer/llm_proposer emit.
    assert MALFORMED_SKIP_PREFIX == "malformed_llm_response_after_retry:"
    assert SCHEMA_SKIP_PREFIX == "schema_validation_failed:"


# ========================================================================
# Full 12-condition drive (composition over the default conditions)
# ========================================================================

def test_run_candidate_drives_all_twelve_conditions(tmp_path):
    client = _ConstClient(_UNIVERSAL_OK)
    score = run_candidate(
        _stage(), "OEB020aa", _candidate(),
        store_root=tmp_path / "s", catalog_root=tmp_path / "c",
        seed=7, client_factory=_factory(client), clock=_fake_clock(),
    )
    # universal payload passes C3 for every type → no schema/malformed skips
    assert score.malformed_skips == 0
    assert score.schema_skips == 0
    # at least one variant landed and the harness made calls across the 12 types
    assert score.proposed >= 1
    assert score.llm_calls >= 1
    # per_type aggregates back to the headline totals
    total_proposed = sum(v["proposed"] for v in score.per_type.values())
    total_skipped = sum(v["skipped"] for v in score.per_type.values())
    assert total_proposed == score.proposed
    assert total_skipped == score.skipped_total


# ========================================================================
# Latency / response length (deterministic under injected clock)
# ========================================================================

def test_latency_is_deterministic_under_injected_clock(tmp_path):
    client = _ConstClient(_SYNONYM_OK)
    score = run_candidate(
        _stage(), "OEB020aa", _candidate(),
        store_root=tmp_path / "s", catalog_root=tmp_path / "c",
        seed=7, conditions=_SYN_CONDITION, client_factory=_factory(client),
        clock=_fake_clock(),
    )
    # one complete call, fake clock ticks +1 around it → 1.0s exactly
    assert score.llm_calls == 1
    assert score.total_latency == 1.0
    assert score.mean_latency == 1.0
    assert score.mean_response_length == float(len(_SYNONYM_OK))


# ========================================================================
# run_spike — ≥2 candidates, distinct per-candidate stores
# ========================================================================

def test_run_spike_writes_distinct_per_candidate_stores(tmp_path):
    store_root = tmp_path / "store"
    candidates = [_candidate(name="gpt4api"), _candidate(name="llama-local")]
    scores = run_spike(
        _stage(), "OEB020aa", candidates,
        store_root=store_root, catalog_root=tmp_path / "cat",
        seed=7, conditions=_SYN_CONDITION,
        client_factory=_factory(_ConstClient(_SYNONYM_OK)), clock=_fake_clock(),
    )
    assert len(scores) == 2
    assert [s.candidate_name for s in scores] == ["gpt4api", "llama-local"]
    assert (store_root / "gpt4api").is_dir()
    assert (store_root / "llama-local").is_dir()
    assert list((store_root / "gpt4api").glob("*.json"))
    assert list((store_root / "llama-local").glob("*.json"))


# ========================================================================
# format_scorecard — columns + no-fluency guard
# ========================================================================

def test_format_scorecard_has_a_row_per_candidate_and_no_fluency_column(tmp_path):
    candidates = [_candidate(name="alpha"), _candidate(name="bravo")]
    scores = run_spike(
        _stage(), "OEB020aa", candidates,
        store_root=tmp_path / "s", catalog_root=tmp_path / "c",
        seed=7, conditions=_SYN_CONDITION,
        client_factory=_factory(_ConstClient(_SYNONYM_OK)), clock=_fake_clock(),
    )
    table = format_scorecard(scores)
    lines = table.splitlines()
    # header + separator + one row per candidate
    assert len(lines) == 2 + len(candidates)
    assert "alpha" in table and "bravo" in table
    assert "proposed" in lines[0] and "schema_fail" in lines[0]
    # decision 3: no fluency column anywhere
    assert "fluency" not in table.lower()


def test_candidate_score_has_no_fluency_field():
    fields = set(CandidateScore.__dataclass_fields__)
    assert not any("fluen" in f.lower() for f in fields)


# ========================================================================
# No-secret-leak (A3a carry-over)
# ========================================================================

def test_candidate_key_value_never_enters_store_or_scorecard(tmp_path, monkeypatch):
    secret = "sk-SUPER-SECRET-VALUE-123"
    monkeypatch.setenv("SPIKE_TEST_KEY_ENV", secret)
    cfg = LLMConfig(base_url="http://x/v1", model="m", api_key_env="SPIKE_TEST_KEY_ENV")
    cand = CandidateSpec(name="cand", config=cfg)
    store_root = tmp_path / "store"
    scores = run_spike(
        _stage(), "OEB020aa", [cand],
        store_root=store_root, catalog_root=tmp_path / "cat",
        seed=7, conditions=_SYN_CONDITION,
        client_factory=_factory(_ConstClient(_SYNONYM_OK)), clock=_fake_clock(),
    )
    table = format_scorecard(scores)
    assert secret not in table
    assert secret not in json.dumps(scores[0].to_dict())
    for path in (store_root / "cand").glob("*.json"):
        assert secret not in path.read_text(encoding="utf-8")


# ========================================================================
# Scope tripwires
# ========================================================================

def test_spike_is_not_imported_by_any_seam_module():
    # The harness is a *consumer* of the orchestrator, never imported by it
    # (decision 2). Importing each seam module must not bind `spike`.
    for mod_name in (
        "synthetic.run_synthetic", "synthetic.llm_proposer",
        "synthetic.variant_proposer", "synthetic.llm_client",
        "synthetic.variant_catalog", "synthetic.composition",
    ):
        mod = importlib.import_module(mod_name)
        assert "spike" not in mod.__dict__, mod_name


def test_spike_adds_no_third_party_dependency():
    import inspect

    src = inspect.getsource(spike)
    for banned in ("import requests", "import httpx", "import openai", "import anthropic"):
        assert banned not in src


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(spike)
    # Sprint 36: TEMPLATE_PARAPHRASE brought the count to 13.
    assert len(reloaded.SINGLE_TYPE_CONDITIONS) == 13
