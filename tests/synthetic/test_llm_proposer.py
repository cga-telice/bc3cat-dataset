"""Contract tests for `synthetic.llm_proposer` — Sprint 13, Phase C Task C2.

Pins `LLMClient` Protocol surface, `ProposalResult` immutability,
`propose()` parse/retry/fallback semantics, and the
`Modification(status="skipped", reason=...)` fallback shape.
"""

from __future__ import annotations

import importlib
from dataclasses import FrozenInstanceError

import pytest

from synthetic.llm_proposer import (
    LLMClient,
    ProposalResult,
    propose,
)
from synthetic.taxonomy import (
    Layer,
    Modification,
    ModificationType,
    TYPE_TO_LAYER,
)


_ALL_TYPES = tuple(ModificationType)


class _StubLLMClient:
    """In-test transport: pops queued responses off a list per call."""

    def __init__(self, responses: list[str]):
        self._queue = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._queue:
            raise AssertionError(
                f"_StubLLMClient: no more queued responses "
                f"(received {len(self.calls)} call(s))"
            )
        return self._queue.pop(0)


# ---------------------------------------------------------------------------
# 1. Public surface
# ---------------------------------------------------------------------------

def test_module_exposes_public_surface():
    import synthetic.llm_proposer as mod

    assert hasattr(mod, "LLMClient")
    assert hasattr(mod, "ProposalResult")
    assert hasattr(mod, "propose")
    # Sanity: the imports at the top of this file resolved.
    assert LLMClient is mod.LLMClient
    assert ProposalResult is mod.ProposalResult
    assert propose is mod.propose


# ---------------------------------------------------------------------------
# 2. Happy / retry / double-failure paths
# ---------------------------------------------------------------------------

def test_propose_returns_payload_on_first_attempt():
    stub = _StubLLMClient(['{"k": "v"}'])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload == {"k": "v"}
    assert result.raw_responses == ('{"k": "v"}',)
    assert result.fallback is None
    assert len(stub.calls) == 1


def test_propose_retries_once_on_malformed():
    stub = _StubLLMClient(["not json", '{"k": "v"}'])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload == {"k": "v"}
    assert len(result.raw_responses) == 2
    assert result.raw_responses[0] == "not json"
    assert result.raw_responses[1] == '{"k": "v"}'
    assert result.fallback is None
    assert len(stub.calls) == 2


def test_propose_emits_fallback_after_two_failures():
    stub = _StubLLMClient(["junk1", "junk2"])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload is None
    assert len(result.raw_responses) == 2
    assert result.raw_responses == ("junk1", "junk2")
    assert result.fallback is not None
    assert isinstance(result.fallback, Modification)
    assert len(stub.calls) == 2


# ---------------------------------------------------------------------------
# 3. Fallback Modification shape — parametrised over all 12 ModificationType
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_fallback_carries_modification_type(mtype):
    stub = _StubLLMClient(["junk", "junk"])
    result = propose("dummy", stub, mtype)
    assert result.fallback is not None
    assert result.fallback.type == mtype


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_fallback_carries_correct_layer(mtype):
    stub = _StubLLMClient(["junk", "junk"])
    result = propose("dummy", stub, mtype)
    assert result.fallback is not None
    assert result.fallback.layer == TYPE_TO_LAYER[mtype]
    assert isinstance(result.fallback.layer, Layer)


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_fallback_status_is_skipped(mtype):
    stub = _StubLLMClient(["junk", "junk"])
    result = propose("dummy", stub, mtype)
    assert result.fallback is not None
    assert result.fallback.status == "skipped"


def test_fallback_reason_starts_with_known_prefix():
    stub = _StubLLMClient(["junk1", "junk2"])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.fallback is not None
    assert result.fallback.reason is not None
    assert result.fallback.reason.startswith(
        "malformed_llm_response_after_retry: "
    )


def test_fallback_other_fields_are_none():
    stub = _StubLLMClient(["junk1", "junk2"])
    result = propose("dummy", stub, ModificationType.PARAPHRASE)
    fb = result.fallback
    assert fb is not None
    assert fb.param is None
    assert fb.var is None
    assert fb.condition is None
    assert fb.field is None
    assert fb.value is None
    assert fb.original is None
    assert fb.new is None


# ---------------------------------------------------------------------------
# 4. raw_responses capture + immutability
# ---------------------------------------------------------------------------

def test_raw_responses_captured_per_attempt_single_success():
    stub = _StubLLMClient(['{"k": 1}'])
    result = propose("dummy", stub, ModificationType.OMISSION)
    assert len(result.raw_responses) == 1


def test_raw_responses_captured_per_attempt_retry_success():
    stub = _StubLLMClient(["bad", '{"k": 1}'])
    result = propose("dummy", stub, ModificationType.OMISSION)
    assert len(result.raw_responses) == 2


def test_raw_responses_captured_per_attempt_double_failure():
    stub = _StubLLMClient(["bad1", "bad2"])
    result = propose("dummy", stub, ModificationType.OMISSION)
    assert len(result.raw_responses) == 2


def test_raw_responses_is_tuple_not_list():
    stub = _StubLLMClient(['{"k": "v"}'])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert isinstance(result.raw_responses, tuple)
    assert not isinstance(result.raw_responses, list)


# ---------------------------------------------------------------------------
# 5. retry_once knob
# ---------------------------------------------------------------------------

def test_retry_once_false_short_circuits():
    stub = _StubLLMClient(["malformed"])
    result = propose(
        "dummy",
        stub,
        ModificationType.SYNONYM_LABEL,
        retry_once=False,
    )
    assert result.payload is None
    assert result.fallback is not None
    assert len(result.raw_responses) == 1
    assert len(stub.calls) == 1


# ---------------------------------------------------------------------------
# 6. Code-fence stripping
# ---------------------------------------------------------------------------

def test_strips_json_code_fence():
    fenced = '```json\n{"k": "v"}\n```'
    stub = _StubLLMClient([fenced])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload == {"k": "v"}
    assert result.fallback is None


def test_strips_plain_code_fence():
    fenced = '```\n{"k": "v"}\n```'
    stub = _StubLLMClient([fenced])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload == {"k": "v"}
    assert result.fallback is None


def test_handles_surrounding_whitespace():
    text = '  \n  {"k": "v"}  \n'
    stub = _StubLLMClient([text])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload == {"k": "v"}
    assert result.fallback is None


# ---------------------------------------------------------------------------
# 7. Non-dict root rejection
# ---------------------------------------------------------------------------

def test_rejects_json_array_root():
    stub = _StubLLMClient(["[1, 2, 3]", "[4, 5, 6]"])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload is None
    assert result.fallback is not None
    assert "json_not_object" in (result.fallback.reason or "")


def test_rejects_json_string_root():
    stub = _StubLLMClient(['"a string"', '"another string"'])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload is None
    assert result.fallback is not None
    assert "json_not_object" in (result.fallback.reason or "")
    assert "type=str" in (result.fallback.reason or "")


def test_rejects_json_number_root():
    stub = _StubLLMClient(["42", "43"])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload is None
    assert result.fallback is not None
    assert "json_not_object" in (result.fallback.reason or "")
    assert "type=int" in (result.fallback.reason or "")


def test_rejects_empty_response():
    stub = _StubLLMClient(["", ""])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    assert result.payload is None
    assert result.fallback is not None
    assert "empty_response" in (result.fallback.reason or "")


# ---------------------------------------------------------------------------
# 8. Prompt passthrough + never-raises contract
# ---------------------------------------------------------------------------

def test_passes_prompt_through_verbatim():
    stub = _StubLLMClient(['{"k": 1}'])
    prompt = "hello {0}  $K  Responde SOLO con un JSON: { ... }"
    propose(prompt, stub, ModificationType.SYNONYM_LABEL)
    assert stub.calls == [prompt]


@pytest.mark.parametrize(
    "malformed",
    ["garbage", "<html>", "{", "}", " ", "[unterminated"],
)
def test_propose_does_not_raise_on_any_failure_path(malformed):
    stub = _StubLLMClient([malformed])
    result = propose(
        "dummy",
        stub,
        ModificationType.SYNONYM_LABEL,
        retry_once=False,
    )
    assert isinstance(result, ProposalResult)
    assert result.fallback is not None
    assert result.payload is None


# ---------------------------------------------------------------------------
# 9. ProposalResult immutability + equality
# ---------------------------------------------------------------------------

def test_proposal_result_is_frozen():
    stub = _StubLLMClient(['{"k": "v"}'])
    result = propose("dummy", stub, ModificationType.SYNONYM_LABEL)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.payload = {"k": "v2"}  # type: ignore[misc]


def test_proposal_result_equality():
    r1 = ProposalResult(
        payload={"k": "v"},
        raw_responses=('{"k": "v"}',),
        fallback=None,
    )
    r2 = ProposalResult(
        payload={"k": "v"},
        raw_responses=('{"k": "v"}',),
        fallback=None,
    )
    assert r1 == r2


# ---------------------------------------------------------------------------
# 10. Module hygiene + Protocol duck-typing
# ---------------------------------------------------------------------------

def test_module_has_no_side_effects_at_import():
    import synthetic.llm_proposer as mod

    reloaded = importlib.reload(mod)
    assert reloaded.LLMClient is mod.LLMClient
    assert reloaded.propose is mod.propose


def test_protocol_duck_typing_works():
    class _AdHocClient:
        def complete(self, prompt: str) -> str:
            return '{"ok": true}'

    result = propose("dummy", _AdHocClient(), ModificationType.SYNONYM_LABEL)
    assert result.payload == {"ok": True}
    assert result.fallback is None
