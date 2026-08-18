"""LLM client for Stage-A variant proposing.

Wraps the (TBD per A3) model chosen for Spanish-technical-text
generation. Owns:

  * the pluggable transport contract (`LLMClient` Protocol);
  * structured-JSON parsing of the LLM's response;
  * one-shot retry on malformed output;
  * a `Modification(status="skipped", reason=...)` fallback record
    when both attempts fail.

Does NOT own:

  * prompt rendering (the caller passes an already-formatted prompt;
    `synthetic.prompts.load_prompt` + `str.format_map` is the C3
    variant proposer's responsibility);
  * per-type response schema validation (the C3 variant proposer
    checks the parsed dict against the `Modification` shape);
  * a concrete transport implementation (deferred to A3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional, Protocol

from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER


class LLMClient(Protocol):
    """Single-shot completion transport. A3's concrete client implements this.

    Implementations may wrap an HTTP API (Ollama / Anthropic / OpenAI /
    …) or a local subprocess; Sprint 13 commits only to the surface.
    """

    def complete(self, prompt: str) -> str: ...


@dataclass(frozen=True)
class ProposalResult:
    """Outcome of one `propose()` call.

    Successful parse:
        payload     = parsed JSON object (dict)
        raw_responses = (response_text,)
        fallback    = None

    Retry success (first attempt malformed, second valid):
        payload     = parsed JSON object (dict)
        raw_responses = (first_malformed_text, second_valid_text)
        fallback    = None

    Double failure (both attempts malformed):
        payload     = None
        raw_responses = (first_malformed_text, second_malformed_text)
        fallback    = Modification(type=..., layer=..., status="skipped",
                                   reason="malformed_llm_response_after_retry: ...")
    """

    payload: Optional[dict]
    raw_responses: tuple[str, ...]
    fallback: Optional[Modification]


def propose(
    prompt: str,
    client: LLMClient,
    modification_type: ModificationType,
    *,
    retry_once: bool = True,
) -> ProposalResult:
    """Call `client.complete(prompt)`, parse the response as JSON, retry
    once on malformed output, and return a `ProposalResult`.

    Never raises. All failure modes are encoded in the returned
    `ProposalResult` — either `payload` is set (success) or
    `fallback` is set (skip + log).
    """
    raw: list[str] = []
    last_error_detail: str = ""
    max_attempts = 2 if retry_once else 1
    for _ in range(max_attempts):
        text = client.complete(prompt)
        raw.append(text)
        try:
            payload = _parse_json_object(text)
        except ValueError as err:
            last_error_detail = str(err)
            continue
        return ProposalResult(
            payload=payload,
            raw_responses=tuple(raw),
            fallback=None,
        )
    return ProposalResult(
        payload=None,
        raw_responses=tuple(raw),
        fallback=_build_fallback(modification_type, last_error_detail),
    )


def _parse_json_object(text: str) -> dict:
    """Strict JSON-object parse, tolerant of prose- and fence-wrapped output.

    The first parse target is the raw response; if that fails, we recover the
    JSON object the model buried in chatter (see `_extract_json_object`). Only a
    genuinely unrecoverable response falls through to a malformed skip.
    """
    candidate = _extract_json_object(text)
    if not candidate:
        raise ValueError("empty_response")
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as err:
        raise ValueError(f"malformed_json: {err.msg}") from err
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object: type={type(obj).__name__}")
    return obj


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extract_json_object(text: str) -> str:
    """Recover a single JSON object from a model response.

    Small local models routinely ignore "Responde SOLO con un JSON" and wrap the
    object in prose and/or a Markdown code fence (e.g. *"Aquí te dejo la
    respuesta: ```json {…} ```"*). This recovers the object regardless:

      1. if a ```…``` (optionally ```json) fence appears **anywhere**, take its
         contents (not just a fence at the very start, as before);
      2. then slice from the first `{` to the last `}` so leading/trailing prose
         is dropped.

    Returns the recovered substring (stripped); the caller does the strict parse,
    so genuinely non-JSON input still fails loud as malformed.
    """
    s = text.strip()
    fence = _FENCE_RE.search(s)
    if fence:
        s = fence.group(1).strip()
    if not s.startswith("{"):
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end > start:
            s = s[start : end + 1]
    return s.strip()


def _build_fallback(
    modification_type: ModificationType,
    reason_detail: str,
) -> Modification:
    """Build the skipped-`Modification` fallback record."""
    return Modification(
        type=modification_type,
        layer=TYPE_TO_LAYER[modification_type],
        status="skipped",
        reason=f"malformed_llm_response_after_retry: {reason_detail}",
    )
