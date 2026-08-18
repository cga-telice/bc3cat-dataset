"""Concrete `LLMClient` transports — Sprint 24, Phase A Task A3a.

The whole Stage-A generation stack (`llm_proposer` / `variant_proposer` /
`run_synthetic`) takes an injected `LLMClient` — a `Protocol` whose only required
method is `complete(self, prompt: str) -> str`. Until now no concrete
implementation existed; every test injected a hand-rolled fake. This module is
that implementation, and it slots in *underneath* the already-frozen Protocol:
nothing in the seam is edited.

Three transports ship here:

* `HttpLLMClient` — OpenAI-compatible `/chat/completions` POST over stdlib
  `urllib.request` (no `requests`/`httpx`/vendor SDK). One user message at
  `temperature 0.0`; returns `choices[0].message.content`. It owns the
  *network-fault* retry layer (timeouts, connection errors, HTTP 429, 5xx →
  bounded exponential backoff; non-429 4xx and exhausted retries → fail-loud
  `LLMTransportError`). This is a *different* retry from the malformed-JSON
  resend that stays in `llm_proposer.propose` — the two never merge.
* `ReplayClient` — content-addressed (`sha256(prompt)`) read from a JSON store.
  Unknown prompt → fail-loud, so a drifted prompt is caught, never silently
  mis-served. This is what the hermetic suite uses and what makes a generation
  run reproducible offline.
* `RecordingClient` — wraps any `LLMClient`, returns its responses unchanged,
  and persists each `prompt-hash → response` as a side effect. Run a live spike
  once through one of these; replay it forever, free, offline.

Secrets never land on disk: `LLMConfig` stores only the *name* of the
API-key env var, the key value is read live when a request is built, and it is
never written to the store, logged, or placed in an exception message.

Imports `taxonomy` (none needed at runtime) / `utils.config` + stdlib only;
never `stage_b` / `run_synthetic` / `stage_runners` / `review` / `mutator` / any
`layer_*`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Sequence

from utils import config

__all__ = [
    "LLMClientError",
    "LLMTransportError",
    "LLMConfig",
    "HttpLLMClient",
    "ReplayClient",
    "RecordingClient",
    "prompt_hash",
    "main",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class LLMClientError(Exception):
    """Base class for transport-layer failures. Distinct, catchable."""


class LLMTransportError(LLMClientError):
    """A request could not be completed: exhausted network retries, a
    non-retryable HTTP status (e.g. 401 bad key, 400 bad request), an
    unparseable/malformed response envelope, or an unknown replay prompt.

    Fail-loud by design: a network/endpoint/key fault is an operator problem
    (fix the key/endpoint), not a per-variant skip. Never carries the API-key
    value in its message (decision 8 / requirement 5).
    """


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LLMConfig:
    """Transport settings. Holds only the *name* of the API-key env var — never
    the key value (decision 8).

    `temperature` defaults to `0.0` (the `RESEARCH_PROTOCOL.md §8` pin).
    """

    base_url: str
    model: str
    api_key_env: str
    timeout: float = 60.0
    max_retries: int = 3
    backoff_base: float = 0.5
    temperature: float = 0.0

    @classmethod
    def from_config(cls) -> "LLMConfig":
        """Resolve defaults from `utils.config` (import-time env overrides)."""
        return cls(
            base_url=config.LLM_BASE_URL,
            model=config.LLM_MODEL,
            api_key_env=config.LLM_API_KEY_ENV,
            timeout=config.LLM_TIMEOUT,
            max_retries=config.LLM_MAX_RETRIES,
            backoff_base=config.LLM_BACKOFF_BASE,
            temperature=config.LLM_TEMPERATURE,
        )

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Resolve from live `os.environ` (picks up changes made after the
        `utils.config` module was imported — handy for the A3b live spike)."""
        return cls(
            base_url=os.environ.get("BC3CAT_LLM_BASE_URL", config.LLM_BASE_URL),
            model=os.environ.get("BC3CAT_LLM_MODEL", config.LLM_MODEL),
            api_key_env=os.environ.get(
                "BC3CAT_LLM_API_KEY_ENV", config.LLM_API_KEY_ENV
            ),
            timeout=float(os.environ.get("BC3CAT_LLM_TIMEOUT", config.LLM_TIMEOUT)),
            max_retries=int(
                os.environ.get("BC3CAT_LLM_MAX_RETRIES", config.LLM_MAX_RETRIES)
            ),
            backoff_base=float(
                os.environ.get("BC3CAT_LLM_BACKOFF_BASE", config.LLM_BACKOFF_BASE)
            ),
            temperature=float(
                os.environ.get("BC3CAT_LLM_TEMPERATURE", config.LLM_TEMPERATURE)
            ),
        )


# ---------------------------------------------------------------------------
# Prompt hashing (content-addressed record/replay store)
# ---------------------------------------------------------------------------

def prompt_hash(prompt: str) -> str:
    """`sha256(prompt)` hex digest — stable across processes and PYTHONHASHSEED."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _default_store_dir() -> Path:
    return Path(config.LLM_CACHE_DIR)


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------

# A `sender` is the injectable network seam (decision 6). It POSTs `data` to
# `url` with `headers` under `timeout` and returns `(status_code, body_text)`.
# It signals a *retryable network fault* by raising one of
# `(TimeoutError, ConnectionError, OSError, urllib.error.URLError)`; HTTP-status
# decisions (retry 429/5xx, fail-loud other 4xx) are the client's, not the
# sender's. Tests inject a fake sender so the entire client is exercised without
# opening a socket.
Sender = Callable[[str, bytes, dict, float], "tuple[int, str]"]

_RETRYABLE_NETWORK_ERRORS = (
    TimeoutError,
    ConnectionError,
    OSError,
    urllib.error.URLError,
)


def _urllib_sender(url: str, data: bytes, headers: dict, timeout: float):
    """Default sender: a real `urllib.request` POST.

    Returns `(status, body)` for any HTTP response (including 4xx/5xx, whose
    bodies `urllib` would otherwise raise as `HTTPError`). Connection/timeout
    faults propagate as `URLError`/`OSError` for the client to retry.
    """
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:  # 4xx/5xx — let the client decide
        body = err.read().decode("utf-8", "replace") if err.fp else ""
        return err.code, body


class HttpLLMClient:
    """OpenAI-compatible `/chat/completions` transport (decisions 2–4, 6).

    `complete(prompt)` sends the prompt as a single user-role message at
    `temperature 0.0`, retries network faults / 429 / 5xx with bounded
    exponential backoff, and fails loud (`LLMTransportError`) on a non-retryable
    4xx, exhausted retries, or an unparseable/malformed envelope. Returns
    `choices[0].message.content` verbatim.
    """

    def __init__(self, config_: LLMConfig, *, sender: Optional[Sender] = None):
        self._config = config_
        self._sender: Sender = sender if sender is not None else _urllib_sender

    @property
    def config(self) -> LLMConfig:
        return self._config

    def _url(self) -> str:
        return self._config.base_url.rstrip("/") + "/chat/completions"

    def _build_body(self, prompt: str) -> bytes:
        payload = {
            "model": self._config.model,
            "temperature": self._config.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        return json.dumps(payload).encode("utf-8")

    def _build_headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        key = os.environ.get(self._config.api_key_env)
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return headers

    def complete(self, prompt: str) -> str:
        url = self._url()
        data = self._build_body(prompt)
        headers = self._build_headers()
        last_detail = "no attempt made"
        attempts = self._config.max_retries + 1
        for attempt in range(attempts):
            if attempt > 0:
                time.sleep(self._config.backoff_base * (2 ** (attempt - 1)))
            try:
                status, body = self._sender(url, data, headers, self._config.timeout)
            except _RETRYABLE_NETWORK_ERRORS as err:
                last_detail = f"network_error: {type(err).__name__}: {err}"
                continue
            if 200 <= status < 300:
                return _parse_envelope(body)
            if status == 429 or 500 <= status < 600:
                last_detail = f"retryable_http_status: {status}"
                continue
            raise LLMTransportError(f"non-retryable HTTP status {status}")
        raise LLMTransportError(
            f"exhausted retries ({attempts} attempt(s)): {last_detail}"
        )


def _parse_envelope(body: str) -> str:
    """Extract `choices[0].message.content` from a chat-completions envelope.

    Any deviation (non-JSON body, missing/empty `choices`, missing
    `message.content`, non-string content) is a fail-loud `LLMTransportError`.
    """
    try:
        obj = json.loads(body)
    except json.JSONDecodeError as err:
        raise LLMTransportError(
            f"unparseable response envelope: {err.msg}"
        ) from err
    try:
        content = obj["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as err:
        raise LLMTransportError(
            f"malformed response envelope: {type(err).__name__}: {err}"
        ) from err
    if not isinstance(content, str):
        raise LLMTransportError(
            f"response content is not a string: type={type(content).__name__}"
        )
    return content


# ---------------------------------------------------------------------------
# Record / replay (offline, deterministic) transports
# ---------------------------------------------------------------------------

class ReplayClient:
    """Serves recorded responses from a content-addressed JSON store.

    The store is one `{prompt_hash}.json` file per prompt, each
    `{"prompt": ..., "response": ...}`. A prompt with no recorded response is
    **fail-loud** (`LLMTransportError`) — a drifted prompt is caught, never
    silently mis-served (decision 5).
    """

    def __init__(self, store_dir: Optional[Path] = None):
        self._store_dir = Path(store_dir) if store_dir is not None else _default_store_dir()

    def complete(self, prompt: str) -> str:
        digest = prompt_hash(prompt)
        path = self._store_dir / f"{digest}.json"
        if not path.exists():
            raise LLMTransportError(
                f"no recorded response for prompt hash {digest} "
                f"in {self._store_dir}"
            )
        record = json.loads(path.read_text(encoding="utf-8"))
        return record["response"]


class RecordingClient:
    """Wraps any `LLMClient`, returns its responses unchanged, and writes each
    `prompt-hash → response` into the store as a side effect (decision 5).

    The store holds only prompts and model responses — never an API key.
    """

    def __init__(self, inner, store_dir: Optional[Path] = None):
        self._inner = inner
        self._store_dir = Path(store_dir) if store_dir is not None else _default_store_dir()

    def complete(self, prompt: str) -> str:
        response = self._inner.complete(prompt)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        path = self._store_dir / f"{prompt_hash(prompt)}.json"
        path.write_text(
            json.dumps({"prompt": prompt, "response": response}, ensure_ascii=False),
            encoding="utf-8",
        )
        return response


# ---------------------------------------------------------------------------
# CLI — thin wrapper over the library (handy for the A3b spike)
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.llm_client")
    sub = parser.add_subparsers(dest="cmd")

    comp = sub.add_parser(
        "complete", help="send a prompt and print the completion"
    )
    comp.add_argument(
        "--prompt", default=None, help="prompt text (default: read stdin)"
    )
    comp.add_argument(
        "--replay",
        action="store_true",
        help="serve from the record/replay store instead of the live endpoint",
    )
    comp.add_argument("--store-dir", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "complete":
        prompt = args.prompt if args.prompt is not None else sys.stdin.read()
        store = Path(args.store_dir) if args.store_dir else None
        if args.replay:
            client = ReplayClient(store)
        else:
            client = HttpLLMClient(LLMConfig.from_env())
        sys.stdout.write(client.complete(prompt))
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
