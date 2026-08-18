"""Tests for `synthetic.llm_client` — Sprint 24, Phase A Task A3a.

Every test is hermetic (injected fake sender or `ReplayClient` over a tmp
store) except the one env-gated live smoke, which skips-not-fails when
`BC3CAT_LLM_LIVE`/the key/network is absent — exactly like the pyarrow- and
data-gated tests. The deterministic suite opens zero sockets.
"""

from __future__ import annotations

import json
import os
import urllib.error

import pytest

from synthetic import llm_client
from synthetic.llm_client import (
    HttpLLMClient,
    LLMClientError,
    LLMConfig,
    LLMTransportError,
    RecordingClient,
    ReplayClient,
    prompt_hash,
)
from synthetic.llm_proposer import propose
from synthetic.taxonomy import ModificationType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cfg(**over) -> LLMConfig:
    base = dict(
        base_url="http://test.local/v1",
        model="test-model",
        api_key_env="BC3CAT_TEST_LLM_KEY",
        timeout=1.0,
        max_retries=3,
        backoff_base=0.5,
        temperature=0.0,
    )
    base.update(over)
    return LLMConfig(**base)


def _envelope(content: str) -> str:
    return json.dumps({"choices": [{"message": {"content": content}}]})


class _SequenceSender:
    """Fake sender driven by a queue of actions: each is either a
    `(status, body)` tuple to return or an Exception instance to raise."""

    def __init__(self, actions):
        self._actions = list(actions)
        self.calls: list[dict] = []

    def __call__(self, url, data, headers, timeout):
        self.calls.append(
            {"url": url, "data": data, "headers": headers, "timeout": timeout}
        )
        if not self._actions:
            raise AssertionError("_SequenceSender: no more queued actions")
        action = self._actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Backoff never actually waits; record the requested delays instead."""
    delays: list[float] = []
    monkeypatch.setattr(llm_client.time, "sleep", lambda s: delays.append(s))
    return delays


# ---------------------------------------------------------------------------
# Public surface / config
# ---------------------------------------------------------------------------

def test_module_public_surface():
    for name in (
        "LLMClientError",
        "LLMTransportError",
        "LLMConfig",
        "HttpLLMClient",
        "ReplayClient",
        "RecordingClient",
        "prompt_hash",
        "main",
    ):
        assert hasattr(llm_client, name), name


def test_transport_error_is_client_error():
    assert issubclass(LLMTransportError, LLMClientError)


def test_config_defaults_temperature_zero():
    cfg = LLMConfig(base_url="u", model="m", api_key_env="E")
    assert cfg.temperature == 0.0


def test_config_from_config_resolves_from_utils_config():
    from utils import config as ucfg

    cfg = LLMConfig.from_config()
    assert cfg.base_url == ucfg.LLM_BASE_URL
    assert cfg.model == ucfg.LLM_MODEL
    assert cfg.api_key_env == ucfg.LLM_API_KEY_ENV
    assert cfg.temperature == 0.0


def test_config_stores_only_env_var_name_not_key(monkeypatch):
    monkeypatch.setenv("BC3CAT_TEST_LLM_KEY", "super-secret")
    cfg = _cfg()
    assert "super-secret" not in repr(cfg)
    assert cfg.api_key_env == "BC3CAT_TEST_LLM_KEY"


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

def test_http_and_replay_are_accepted_by_propose(tmp_path):
    # The LLMClient Protocol is duck-typed (not @runtime_checkable); conformance
    # means `propose` accepts the client via its `complete(prompt) -> str`.
    http = HttpLLMClient(_cfg(), sender=_SequenceSender([(200, _envelope('{"a": 1}'))]))
    http_result = propose("p", http, ModificationType.SYNONYM_LABEL)
    assert http_result.payload == {"a": 1}

    prompt = "replay-conformance"
    (tmp_path / f"{prompt_hash(prompt)}.json").write_text(
        json.dumps({"prompt": prompt, "response": '{"b": 2}'}), encoding="utf-8"
    )
    replay_result = propose(prompt, ReplayClient(tmp_path), ModificationType.SYNONYM_LABEL)
    assert replay_result.payload == {"b": 2}


# ---------------------------------------------------------------------------
# HttpLLMClient — happy path + request body / headers
# ---------------------------------------------------------------------------

def test_http_happy_path_returns_content():
    sender = _SequenceSender([(200, _envelope("hola mundo"))])
    client = HttpLLMClient(_cfg(), sender=sender)
    assert client.complete("prompt") == "hola mundo"
    assert len(sender.calls) == 1


def test_http_request_body_carries_model_temp_and_single_user_message():
    sender = _SequenceSender([(200, _envelope("ok"))])
    client = HttpLLMClient(_cfg(model="m9"), sender=sender)
    client.complete("el prompt")
    body = json.loads(sender.calls[0]["data"].decode("utf-8"))
    assert body["model"] == "m9"
    assert body["temperature"] == 0.0
    assert body["messages"] == [{"role": "user", "content": "el prompt"}]


def test_http_url_appends_chat_completions():
    sender = _SequenceSender([(200, _envelope("ok"))])
    HttpLLMClient(_cfg(base_url="http://h/v1/"), sender=sender).complete("p")
    assert sender.calls[0]["url"] == "http://h/v1/chat/completions"


def test_http_auth_header_built_from_env_key(monkeypatch):
    monkeypatch.setenv("BC3CAT_TEST_LLM_KEY", "k-123")
    sender = _SequenceSender([(200, _envelope("ok"))])
    HttpLLMClient(_cfg(), sender=sender).complete("p")
    assert sender.calls[0]["headers"]["Authorization"] == "Bearer k-123"


def test_http_no_auth_header_when_key_absent(monkeypatch):
    monkeypatch.delenv("BC3CAT_TEST_LLM_KEY", raising=False)
    sender = _SequenceSender([(200, _envelope("ok"))])
    HttpLLMClient(_cfg(), sender=sender).complete("p")
    assert "Authorization" not in sender.calls[0]["headers"]


# ---------------------------------------------------------------------------
# HttpLLMClient — transport retry / backoff / fail-loud
# ---------------------------------------------------------------------------

def test_http_retries_network_faults_then_succeeds(_no_real_sleep):
    sender = _SequenceSender(
        [TimeoutError("t/o"), ConnectionError("refused"), (200, _envelope("ok"))]
    )
    client = HttpLLMClient(_cfg(max_retries=3), sender=sender)
    assert client.complete("p") == "ok"
    assert len(sender.calls) == 3
    assert _no_real_sleep == [0.5, 1.0]  # bounded exponential backoff


def test_http_retries_urlerror(_no_real_sleep):
    sender = _SequenceSender(
        [urllib.error.URLError("down"), (200, _envelope("ok"))]
    )
    assert HttpLLMClient(_cfg(), sender=sender).complete("p") == "ok"
    assert len(sender.calls) == 2


def test_http_retries_429_and_5xx(_no_real_sleep):
    sender = _SequenceSender([(429, ""), (503, ""), (200, _envelope("ok"))])
    assert HttpLLMClient(_cfg(max_retries=3), sender=sender).complete("p") == "ok"
    assert len(sender.calls) == 3


def test_http_non_429_4xx_fails_loud_no_retry():
    sender = _SequenceSender([(401, "bad key")])
    with pytest.raises(LLMTransportError) as exc:
        HttpLLMClient(_cfg(), sender=sender).complete("p")
    assert "401" in str(exc.value)
    assert len(sender.calls) == 1  # not retried


def test_http_400_fails_loud_no_retry():
    sender = _SequenceSender([(400, "bad request")])
    with pytest.raises(LLMTransportError):
        HttpLLMClient(_cfg(), sender=sender).complete("p")
    assert len(sender.calls) == 1


def test_http_exhausted_network_retries_fail_loud(_no_real_sleep):
    sender = _SequenceSender([TimeoutError("t/o")] * 3)
    with pytest.raises(LLMTransportError) as exc:
        HttpLLMClient(_cfg(max_retries=2), sender=sender).complete("p")
    assert len(sender.calls) == 3  # max_retries + 1
    assert "exhausted retries" in str(exc.value)


def test_http_exhausted_retryable_status_fail_loud(_no_real_sleep):
    sender = _SequenceSender([(503, "")] * 3)
    with pytest.raises(LLMTransportError):
        HttpLLMClient(_cfg(max_retries=2), sender=sender).complete("p")
    assert len(sender.calls) == 3


# ---------------------------------------------------------------------------
# HttpLLMClient — envelope parse failures
# ---------------------------------------------------------------------------

def test_http_non_json_body_fails_loud():
    sender = _SequenceSender([(200, "not json {")])
    with pytest.raises(LLMTransportError):
        HttpLLMClient(_cfg(), sender=sender).complete("p")


def test_http_empty_choices_fails_loud():
    sender = _SequenceSender([(200, json.dumps({"choices": []}))])
    with pytest.raises(LLMTransportError):
        HttpLLMClient(_cfg(), sender=sender).complete("p")


def test_http_missing_choices_fails_loud():
    sender = _SequenceSender([(200, json.dumps({"foo": 1}))])
    with pytest.raises(LLMTransportError):
        HttpLLMClient(_cfg(), sender=sender).complete("p")


def test_http_non_string_content_fails_loud():
    sender = _SequenceSender(
        [(200, json.dumps({"choices": [{"message": {"content": 42}}]}))]
    )
    with pytest.raises(LLMTransportError):
        HttpLLMClient(_cfg(), sender=sender).complete("p")


# ---------------------------------------------------------------------------
# ReplayClient / RecordingClient
# ---------------------------------------------------------------------------

def test_replay_known_prompt_returns_recorded(tmp_path):
    prompt = "¿cuál es la respuesta?"
    (tmp_path / f"{prompt_hash(prompt)}.json").write_text(
        json.dumps({"prompt": prompt, "response": "cuarenta y dos"}),
        encoding="utf-8",
    )
    assert ReplayClient(tmp_path).complete(prompt) == "cuarenta y dos"


def test_replay_unknown_prompt_fails_loud(tmp_path):
    with pytest.raises(LLMTransportError) as exc:
        ReplayClient(tmp_path).complete("never recorded")
    assert "no recorded response" in str(exc.value)


def test_recording_round_trip(tmp_path):
    inner = HttpLLMClient(_cfg(), sender=_SequenceSender([(200, _envelope("grabado"))]))
    rec = RecordingClient(inner, tmp_path)
    assert rec.complete("prompt uno") == "grabado"
    # A fresh ReplayClient reads back what was written.
    assert ReplayClient(tmp_path).complete("prompt uno") == "grabado"


def test_recording_returns_inner_response_unchanged(tmp_path):
    class _Echo:
        def complete(self, prompt):
            return f"echo:{prompt}"

    rec = RecordingClient(_Echo(), tmp_path)
    assert rec.complete("abc") == "echo:abc"


# ---------------------------------------------------------------------------
# Composition with the unchanged proposer (C2)
# ---------------------------------------------------------------------------

def test_propose_over_replay_success(tmp_path):
    prompt = "genera variante"
    payload = {"status": "ok", "value": "x"}
    (tmp_path / f"{prompt_hash(prompt)}.json").write_text(
        json.dumps({"prompt": prompt, "response": json.dumps(payload)}),
        encoding="utf-8",
    )
    result = propose(prompt, ReplayClient(tmp_path), ModificationType.SYNONYM_LABEL)
    assert result.payload == payload
    assert result.fallback is None


def test_propose_over_replay_malformed_drives_c2_fallback(tmp_path):
    prompt = "genera variante mala"
    (tmp_path / f"{prompt_hash(prompt)}.json").write_text(
        json.dumps({"prompt": prompt, "response": "no soy json"}),
        encoding="utf-8",
    )
    result = propose(prompt, ReplayClient(tmp_path), ModificationType.SYNONYM_LABEL)
    assert result.payload is None
    assert result.fallback is not None
    assert result.fallback.status == "skipped"
    assert result.fallback.reason.startswith("malformed_llm_response_after_retry:")


# ---------------------------------------------------------------------------
# No secret leaks
# ---------------------------------------------------------------------------

def test_api_key_never_written_to_recording_store(tmp_path, monkeypatch):
    secret = "sk-DO-NOT-LEAK-0001"
    monkeypatch.setenv("BC3CAT_TEST_LLM_KEY", secret)
    sender = _SequenceSender([(200, _envelope("respuesta"))])
    inner = HttpLLMClient(_cfg(), sender=sender)
    RecordingClient(inner, tmp_path).complete("prompt con clave")
    for path in tmp_path.glob("*.json"):
        assert secret not in path.read_text(encoding="utf-8")


def test_api_key_never_in_transport_error_message(tmp_path, monkeypatch):
    secret = "sk-DO-NOT-LEAK-0002"
    monkeypatch.setenv("BC3CAT_TEST_LLM_KEY", secret)
    sender = _SequenceSender([(401, "unauthorized")])
    with pytest.raises(LLMTransportError) as exc:
        HttpLLMClient(_cfg(), sender=sender).complete("p")
    assert secret not in str(exc.value)
    assert secret not in repr(exc.value)


# ---------------------------------------------------------------------------
# Live smoke — opt-in, skips-not-fails (decision 7)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    os.environ.get("BC3CAT_LLM_LIVE") != "1"
    or not os.environ.get(LLMConfig.from_env().api_key_env),
    reason="live smoke disabled (set BC3CAT_LLM_LIVE=1 and the API key env var)",
)
def test_live_smoke_completes():
    client = HttpLLMClient(LLMConfig.from_env())
    out = client.complete("Responde con la palabra: hola")
    assert isinstance(out, str) and out.strip()
