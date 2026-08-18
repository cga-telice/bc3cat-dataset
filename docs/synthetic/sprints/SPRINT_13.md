# Sprint 13 — Phase C Task C2: LLM client (`llm_proposer.py`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 13                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | C2 — see [`../RESEARCH_PROTOCOL.md §5 Phase C`](../RESEARCH_PROTOCOL.md)                    |
| **Predecessor** | Sprint 12 — `prompts/` library + C1 closes; 12 Spanish prompts + loader (see [`SPRINT_12.md`](SPRINT_12.md)) |
| **Successor**   | Sprint 14 — Phase C Task C3 (`variant_proposer.py` — per-concept slot rendering + per-type schema validation) — TBD |

---

## Context

Sprint 12 froze the 12 Spanish prompt templates and shipped a thin
loader (`load_prompt` + `PROMPT_DIR` + `PROMPT_FILENAMES`) at
[`src/synthetic/prompts/`](../../src/synthetic/prompts). The natural
next concern is **how those templates round-trip through an LLM**:
given an already-rendered prompt string, get a structured JSON
response, validate it parses, retry once on malformed output, and
emit a `Modification(status="skipped", reason=...)` fallback record
when both attempts fail. That is exactly the protocol's [§5 Phase C
C2](../RESEARCH_PROTOCOL.md) row:

> **C2. LLM client.** `src/synthetic/llm_proposer.py` — wraps the
> model chosen in A3. Structured JSON output, malformed-response
> retry (×1), fallback log entry.

Two design tensions to resolve up front:

1. **A3 (LLM proposer choice spike) is still TBD.** The protocol's
   §2 risk table still flags "LLM proposer model: **TBD** — spike
   in A3 across ≥2 candidates". Sprint 13 cannot commit to a
   concrete model (Llama 3.1 70B local vs. GPT-4-class API vs. a
   Spanish-tuned alternative) without A3's results. The plan
   resolves this by shipping a **pluggable transport** — a
   `Protocol`-typed `LLMClient` with a single `complete(prompt) ->
   str` method. Concrete transports (Ollama HTTP, Anthropic API,
   OpenAI API, …) ship in a follow-up sprint once A3 lands.
2. **C2 vs. C3 boundary.** The protocol splits Stage-A work between
   C2 ("LLM client … structured JSON output, retry, fallback log")
   and C3 ("variant proposer … calls the LLM, validates output
   shape against the `Modification` schema, returns a candidate").
   Sprint 13 owns the *model wrapper + JSON-parse + retry + fallback
   log entry*; C3 owns *prompt rendering (filling
   `{concept}`/`{axis_label}`/… slots from per-concept context)*,
   *per-type schema validation* (does this `synonym_label` payload
   carry `{"synonyms": [...]}` with the right shape?), and *candidate
   selection*. Sprint 13's `propose()` takes an *already-rendered*
   prompt string and returns the parsed JSON dict (or a fallback);
   it does not know which `ModificationType`'s schema applies beyond
   what it needs to populate the fallback's `type` and `layer`
   fields.

Sprint 12's verification baseline: **297 passed + 1 skipped.** Sprint
13 adds the new `src/synthetic/llm_proposer.py` module + its contract
test suite (`tests/synthetic/test_llm_proposer.py`). Net pytest
delta target: **≥+22 new cases** = **≥319 passed** total. Zero
failures, zero new skips, zero changes to surviving tests. No
changes to any `layer_*.py`, `mutator.py`, `composition.py`,
`taxonomy.py`, or to `src/synthetic/prompts/`.

---

## Scope

### In scope

- **C2** — `src/synthetic/llm_proposer.py` (new). Public surface:
  - `class LLMClient(Protocol)` — single method
    `complete(self, prompt: str) -> str`. The Stage-A transport
    contract; A3's concrete client implements it.
  - `@dataclass(frozen=True) class ProposalResult` — fields
    `payload: Optional[dict]`, `raw_responses: tuple[str, ...]`,
    `fallback: Optional[Modification]`. Carries either a parsed
    JSON dict + empty fallback, or `payload=None` + a populated
    fallback record. `raw_responses` is the captured client output
    sequence (one or two entries depending on retry path).
  - `def propose(prompt, client, modification_type, *,
    retry_once=True) -> ProposalResult` — the single entry point.
    Calls `client.complete(prompt)`; tries to parse the response
    as a JSON object; on `ValueError` retries once (if
    `retry_once=True`); on second failure builds a fallback
    `Modification` and returns it inside `ProposalResult`. Never
    raises; all failures are encoded in the result.
  - Three private helpers — `_parse_json_object(text) -> dict`
    (strip fence, strict `json.loads`, reject non-dict roots),
    `_strip_code_fence(text) -> str` (handle ` ```json `… `'''` `
    and bare ` ``` `… `'''` wrappers LLMs frequently add despite
    the prompt's "Responde SOLO con un JSON" instruction),
    `_build_fallback(modification_type, reason_detail) ->
    Modification` (populates `type`, `layer` from
    `TYPE_TO_LAYER`, `status="skipped"`,
    `reason=f"malformed_llm_response_after_retry: {detail}"`).
- **Tests** — `tests/synthetic/test_llm_proposer.py` (new, ≥22
  cases). Coverage: happy path (parse on first attempt); retry path
  (malformed → valid); double-failure path (both malformed →
  fallback); fallback record shape (`type`, `layer`, `status`,
  `reason` prefix); raw-response capture; call-count audit; code-fence
  stripping (json-tagged and bare); whitespace tolerance;
  array/string/number root rejection; prompt-passthrough audit;
  `retry_once=False` short-circuit; per-`ModificationType` fallback
  parametrised over all 12 enum members; immutability of
  `ProposalResult`; public-surface import audit.
- **Housekeeping**:
  - Sprint 13 entry in
    [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip ❌ → ✅ for the `llm_proposer.py` row in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)'s "New Files
    in This Branch" section, **partial credit**: "✅ Sprint 13 —
    Task C2 — `LLMClient` Protocol + `propose` + retry/fallback
    contract; concrete transport pending A3". Prepend an "After
    Sprint 13 — …" entry to the Sprint History.

### Out of scope (explicit)

- **A3 (LLM proposer choice spike).** Picking Llama 3.1 70B local
  vs. GPT-4-class API vs. a Spanish-tuned alternative is **not**
  Sprint 13's call. The `LLMClient` Protocol surface is the C2
  deliverable; A3 (a separate sprint or a one-off script) decides
  the concrete implementation. Document the A3 deferral in the
  RESEARCH_LOG entry — Sprint 13's "concrete transport" cell stays
  ❌ in the protocol's risk table until A3 lands.
- **A concrete transport implementation.** No `OllamaClient`, no
  `AnthropicClient`, no `OpenAIClient`, no HTTP code in
  `llm_proposer.py`. The module surface is the Protocol + the
  retry/parse/fallback logic only. Tests use in-test stub clients
  with a queued response sequence. Adding a concrete transport in
  this sprint would (a) commit to A3's outcome prematurely, (b)
  drag in a new runtime dependency (`httpx` / `ollama` /
  `anthropic` / `openai`), and (c) require live-API integration
  tests that this sprint deliberately avoids.
- **Prompt rendering / slot substitution.** `propose()` takes an
  *already-rendered* prompt string. The C3 variant proposer is
  responsible for taking `load_prompt(mtype)` + a per-concept slots
  dict and producing the rendered prompt (likely via
  `str.format_map` with a custom dispatcher that ignores braces
  inside the JSON-contract block). Sprint 12's "loader is dumb"
  contract stays — neither the prompt loader nor the LLM client
  renders.
- **Per-type response schema validation.** Sprint 13's
  `_parse_json_object` checks only that the response is valid JSON
  *and* a top-level object. It does **not** check that a
  `synonym_label` response has the key `synonyms` (a list of
  `{original, new}` objects), nor that a `paraphrase` response has
  `{original, new, preserves_meaning}`. Per-type structural
  validation is C3's call — the response needs to be parsed first
  *(C2)* and then matched against the `Modification` schema *(C3)*.
  The "malformed" detector in C2 is JSON-validity only.
- **Pydantic / jsonschema as runtime dependencies.** Sprint 13 uses
  stdlib `json` only. The C3 variant proposer may introduce
  `pydantic` or `jsonschema` once per-type structural validation is
  on the table — Sprint 13 keeps the dependency surface tight.
  Rationale: adding a heavy dep for a step that's pure-dict-shape
  checking (which `dataclass.__post_init__` can do natively) is
  premature.
- **Live LLM calls in pytest CI.** No network, no real model
  endpoints. The test suite uses an inline `_StubLLMClient` that
  pops queued responses off a list. Real-model smoke tests are A3's
  problem (they should live in a separate script under
  `scripts/spike_a3_*.py` or in a manually-run notebook, not in
  `tests/`).
- **Streaming, chat-format, function-calling, tool-use APIs.** The
  `complete(prompt) -> str` Protocol is intentionally minimal —
  one prompt in, one full response out. A3's concrete client is
  responsible for adapting whatever native API shape the chosen
  vendor exposes (single-shot completion, chat-completion with a
  system message, structured-output JSON mode, etc.) into the
  `complete(prompt) -> str` contract. Sprint 13 doesn't speculate
  on which adaptation will be needed.
- **Token budgeting, cost accounting, rate-limit handling,
  exponential-backoff retry policies.** None of these belong in
  Sprint 13. The protocol's C2 row is explicit — "malformed-response
  retry (×1), fallback log entry". One retry, fixed. Phase F's
  pilot may revisit (e.g., retry on `429 Too Many Requests` in the
  concrete transport), but the *malformed-JSON* retry stays at one.
- **`configs/synthetic/llm_proposer.yaml` or any per-model config
  file.** No external config in Sprint 13. The Protocol surface
  doesn't reference a model name, an endpoint URL, or an API key —
  those are concrete-transport concerns. Configuration is A3's
  follow-up to design once the model is chosen.
- **Anything under `src/synthetic/prompts/`, `data/`, notebooks, or
  `src/utils/`.** Tests instantiate stub clients in-test; no
  fixture files, no on-disk caches, no notebook reruns.
- **Changes to existing `src/synthetic/` modules.** No edits to
  `taxonomy.py` (the existing `Modification`, `ModificationType`,
  `Layer`, `TYPE_TO_LAYER` cover the fallback record's needs as-is),
  `mutator.py`, `composition.py`, any `layer_*.py`, or to
  `prompts/__init__.py`. C2 is purely additive — one new module
  file + one new test file.

---

## Module surface

```python
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

    Parameters
    ----------
    prompt : str
        Already-rendered prompt. The caller (C3 variant proposer) is
        responsible for filling slot placeholders via
        `synthetic.prompts.load_prompt` + a per-concept formatter.
    client : LLMClient
        Pluggable transport. A3 selects the concrete implementation;
        tests pass a stub.
    modification_type : ModificationType
        Used only to populate the fallback record's `type` and
        `layer` fields if both attempts fail. Not used to validate
        the response (that's C3's call).
    retry_once : bool, default True
        Whether to retry on a malformed first response. Tests use
        `retry_once=False` to assert no-retry behaviour.
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
    """Strict JSON-object parse, tolerant of a wrapping code fence."""
    stripped = _strip_code_fence(text).strip()
    if not stripped:
        raise ValueError("empty_response")
    try:
        obj = json.loads(stripped)
    except json.JSONDecodeError as err:
        raise ValueError(f"malformed_json: {err.msg}") from err
    if not isinstance(obj, dict):
        raise ValueError(f"json_not_object: type={type(obj).__name__}")
    return obj


def _strip_code_fence(text: str) -> str:
    """Strip a leading ```json ... ``` (or bare ``` ... ```) fence.

    LLMs frequently emit a fenced code block despite the prompt's
    "Responde SOLO con un JSON" instruction. Stripping the fence
    before parsing is cheaper than retrying on what would be a
    well-formed-content / wrongly-wrapped response.
    """
    s = text.strip()
    if not s.startswith("```"):
        return s
    newline = s.find("\n")
    if newline < 0:
        return s
    body = s[newline + 1:]
    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -3]
    return body.strip()


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
```

### Behavioural requirements

1. **`propose` never raises.** Every failure mode (malformed JSON,
   wrong root type, empty response, retry-after-failure, no-retry
   short-circuit) returns a `ProposalResult` with `fallback` set.
   Pinned by the test suite; the orchestrator should never need a
   `try/except` around the call.
2. **One retry, not exponential, not configurable beyond on/off.**
   The protocol's C2 row is explicit: "malformed-response retry
   (×1)". `retry_once: bool` is a knob for tests (assert no-retry),
   not a production-time tunable. If a future sprint needs richer
   retry semantics (rate-limit-aware, exponential backoff), they
   belong in the concrete transport's `complete` method, not in
   `propose`.
3. **Fallback record matches `Modification` schema exactly.** No
   new fields, no schema extension. `type` and `layer` are
   populated from `TYPE_TO_LAYER`; `status="skipped"`; `reason`
   follows the `"malformed_llm_response_after_retry: <detail>"`
   convention so Phase E1's metadata pipeline can grep for it. All
   other `Modification` fields stay `None` — the fallback has no
   `param` / `var` / `original` / `new` because by definition the
   LLM didn't produce a usable payload.
4. **`raw_responses` is a tuple, not a list.** Pinned by
   `@dataclass(frozen=True)`. Phase E1 may want to log the raw
   responses verbatim for diagnostic purposes; an immutable tuple
   keeps the contract clean.
5. **Code-fence stripping is best-effort, not regex-based.** A
   leading line starting with ` ``` ` and a trailing ` ``` ` are
   stripped if both present; otherwise the response is parsed
   as-is. If the LLM's fence syntax drifts (e.g., uses ` ~~~ `),
   the parse fails and the retry kicks in — that's an acceptable
   degradation path. Don't over-engineer the fence detector.
6. **`_parse_json_object` rejects non-dict roots.** The JSON
   specification permits arrays, strings, numbers, booleans, and
   `null` as top-level values. The prompts all declare an
   object-shaped contract (`Responde SOLO con un JSON: { ... }`),
   so a top-level array or scalar is malformed by C2's definition.
   Pinned by tests #12–#14.
7. **`Protocol`, not `ABC`.** `LLMClient` is a structural type —
   any class with a `complete(self, prompt: str) -> str` method
   satisfies it. No `@runtime_checkable` decorator (we don't need
   `isinstance(x, LLMClient)`); duck typing is sufficient. This
   keeps the test stubs free of inheritance ceremony.

### Acceptance

- `from synthetic.llm_proposer import LLMClient, ProposalResult, propose` succeeds.
- `propose("dummy", _StubLLMClient(['{"k": "v"}']), ModificationType.SYNONYM_LABEL).payload == {"k": "v"}`.
- `propose("dummy", _StubLLMClient(["garbage", '{"k": "v"}']), ModificationType.SYNONYM_LABEL).payload == {"k": "v"}` (retry path).
- `propose("dummy", _StubLLMClient(["junk1", "junk2"]), ModificationType.SYNONYM_LABEL).fallback.status == "skipped"`.
- `ProposalResult.__hash__` is callable (`frozen=True` implies hashable provided all fields are hashable; `raw_responses` as `tuple[str, ...]` and `fallback` as a frozen dataclass cooperate).
- `pytest tests -q` exits 0 with ≥319 passed, exactly 1 skip (the
  Sprint-12 `new_param` brace audit), zero failures.

---

## Tasks

### Task 1 — `src/synthetic/llm_proposer.py`

Create the module as specified in §"Module surface" above.
Implementation notes:

1. **Use `Protocol` from `typing`.** Not `abc.ABC`. The structural
   subtyping is the point — stub clients in tests don't inherit
   from `LLMClient`, they just expose `complete(prompt) -> str`.
2. **`@dataclass(frozen=True)` on `ProposalResult`.** Implies
   `__eq__`, `__hash__`, and frozen-instance enforcement. Tests
   exercise the equality contract on two equal results.
3. **`_parse_json_object` raises only `ValueError`.** Other
   exception types (e.g., `TypeError` from passing a non-string)
   should not be caught — they indicate a programming error in the
   caller, not a malformed LLM response. The catch in `propose` is
   narrow (`except ValueError`) to keep the failure surface
   well-defined.
4. **`_strip_code_fence` handles three common shapes:**
   - ` ```json\n{...}\n``` ` (the most common LLM emission)
   - ` ```\n{...}\n``` ` (bare fence)
   - `{...}` (no fence — pass-through)

   It does *not* handle:
   - mid-text fences (the LLM said `Sure! ```json\n{...}\n``` Hope this helps.`) — these are out of contract
   - `~~~` fences (rare; let the retry handle it)
5. **`_build_fallback`'s reason string format.** Exactly
   `"malformed_llm_response_after_retry: <detail>"`. The prefix is
   the grep handle Phase E1 will use to count fallbacks per type
   in pilot reports.
6. **No logger import.** The module emits no log lines on its own
   — the caller (C3 variant proposer or D2 orchestrator) is
   responsible for logging the `ProposalResult` if it wants to.
   Avoids the "which logger should I use?" decision and keeps the
   module pure-function.
7. **No module-level side effects.** No environment-variable
   reads, no on-import sanity checks, no logger setup. Symbols
   only.

### Task 2 — `tests/synthetic/test_llm_proposer.py`

Create the test file. ≥22 cases. Skeleton:

```python
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
```

Required test cases (≥22):

1. **`test_module_exposes_public_surface`** — `LLMClient`,
   `ProposalResult`, `propose` are importable from
   `synthetic.llm_proposer`.
2. **`test_propose_returns_payload_on_first_attempt`** —
   `_StubLLMClient(['{"k": "v"}'])` produces
   `ProposalResult(payload={"k": "v"}, raw_responses=('{"k": "v"}',), fallback=None)`.
3. **`test_propose_retries_once_on_malformed`** — queue
   `["not json", '{"k": "v"}']`; result has `payload={"k": "v"}`,
   `len(raw_responses) == 2`, `fallback is None`, client received
   2 calls.
4. **`test_propose_emits_fallback_after_two_failures`** — queue
   `["junk1", "junk2"]`; `payload is None`, `fallback is not None`,
   `len(raw_responses) == 2`.
5. **`test_fallback_carries_modification_type`** — fallback's
   `type` field equals the `modification_type` argument.
   Parametrise over all 12 `ModificationType` members.
6. **`test_fallback_carries_correct_layer`** — fallback's `layer`
   field equals `TYPE_TO_LAYER[modification_type]`. Parametrise
   over all 12 members.
7. **`test_fallback_status_is_skipped`** — `fallback.status ==
   "skipped"`. Parametrise over all 12 members (proves the
   convention holds uniformly).
8. **`test_fallback_reason_starts_with_known_prefix`** —
   `fallback.reason.startswith("malformed_llm_response_after_retry: ")`.
   Pins the Phase-E1 grep handle.
9. **`test_fallback_other_fields_are_none`** — `param`, `var`,
   `condition`, `field`, `value`, `original`, `new` are all `None`
   on the fallback record (no LLM payload to populate them with).
10. **`test_raw_responses_captured_per_attempt`** — single-success
    path → `len(raw_responses) == 1`; retry-success path →
    `len(raw_responses) == 2`; double-failure path →
    `len(raw_responses) == 2`. Three sub-cases in one test or split
    into three.
11. **`test_raw_responses_is_tuple_not_list`** —
    `isinstance(result.raw_responses, tuple)`. Pins the immutability
    contract.
12. **`test_retry_once_false_short_circuits`** — with
    `retry_once=False` and a single malformed response queued,
    result has `fallback set` and `len(raw_responses) == 1`;
    client received exactly 1 call.
13. **`test_strips_json_code_fence`** — response wrapped in
    ` ```json\n{"k": "v"}\n``` `; parses to `{"k": "v"}` on first
    attempt.
14. **`test_strips_plain_code_fence`** — response wrapped in
    ` ```\n{"k": "v"}\n``` `; same result.
15. **`test_handles_surrounding_whitespace`** — response
    `'  \n  {"k": "v"}  \n'`; parses to `{"k": "v"}`.
16. **`test_rejects_json_array_root`** — response `'[1, 2, 3]'`;
    triggers retry on first attempt; if retry also returns an
    array, fallback emitted with `reason` containing
    `"json_not_object"`.
17. **`test_rejects_json_string_root`** — response `'"a string"'`;
    same as above but with `type=str` in the error detail.
18. **`test_rejects_json_number_root`** — response `'42'`; same
    pattern with `type=int`.
19. **`test_rejects_empty_response`** — response `''`; retry
    triggered; if both are empty, fallback `reason` contains
    `"empty_response"`.
20. **`test_passes_prompt_through_verbatim`** — `propose("hello {0}",
    stub, mtype)` results in `stub.calls == ["hello {0}"]`. No
    formatting, no escaping, no normalization. Pin Sprint 12's
    "loader returns the raw template" contract by extension.
21. **`test_propose_does_not_raise_on_any_failure_path`** —
    parametrise over malformed inputs `["garbage", "<html>", "{",
    "}", " ", "[unterminated"]`; queue each as a singleton
    against `retry_once=False`; assert `propose(...)` returns a
    `ProposalResult` with `fallback set` (no `pytest.raises`
    blocks).
22. **`test_proposal_result_is_frozen`** —
    `with pytest.raises((FrozenInstanceError, AttributeError)):
    result.payload = {"k": "v2"}`. Pin the immutability contract.
23. **`test_proposal_result_equality`** — two results with
    identical fields compare equal (`@dataclass(frozen=True)`
    implies `__eq__`).
24. **`test_proposal_result_is_hashable`** — `hash(result)` is
    callable (tuple + frozen dataclass + dict… wait, `payload:
    dict` is NOT hashable). **Decision:** if payload is hashable
    only when `None`, restrict the hashability test to the
    fallback-result case where `payload is None`. Document the
    nuance in a code comment if needed. Alternative: drop the
    hashability test if it forces `payload` to be a `MappingProxy`
    or similar — accept that frozen dataclass with a `dict` field
    is non-hashable in practice. **Final decision:** drop this
    test; the immutability test (#22) is the binding contract,
    hashability is an implementation detail of `frozen=True` we
    don't need to assert.
25. **`test_module_has_no_side_effects_at_import`** — re-import
    `synthetic.llm_proposer` via `importlib.reload`; no exceptions,
    no I/O. Sanity check that the module stays cheap to import.
26. **`test_protocol_duck_typing_works`** — define a one-off class
    `class _AdHocClient: def complete(self, prompt): return '{"k": "v"}'`
    (no inheritance from `LLMClient`); pass it to `propose` and
    confirm the call succeeds. Pins the structural-typing decision.

Test count: 24–26 functions (drop #24 per decision above; #5/#6/#7
parametrise ×12 so they expand to 36 individual cases). After
parametrisation expansion the headline is ~60 cases. Binding gate
is "≥22 listed functions, all green".

### Task 3 — Housekeeping

After Tasks 1–2 pass:

1. Append a Sprint 13 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md). Cover: the new
   `llm_proposer.py` module, its public surface (`LLMClient`
   Protocol, `ProposalResult`, `propose`), the four-shape JSON-parse
   contract (success / retry-success / double-failure / no-retry),
   the fallback `Modification` shape (`type` / `layer` /
   `status="skipped"` / `reason="malformed_llm_response_after_retry:
   …"`), the test-count delta (297 → ≥319), the A3 deferral (no
   concrete transport this sprint), the C2/C3 boundary (Sprint 13
   owns the wrapper + parse + retry + fallback; C3 owns rendering
   + per-type schema validation), and a one-line next-step
   recommendation (Sprint 14 — Phase C Task C3, `variant_proposer.py`).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md):
   - Flip the `llm_proposer.py` row from ❌ to ✅ with the
     annotation "✅ Sprint 13 — Task C2 — `LLMClient` Protocol +
     `propose` + retry/fallback contract; concrete transport
     deferred to A3 (Spanish-technical-text model spike)". Keep
     the C3 portion (variant proposer) implicit in the row
     description — the file map's row covers both tasks per its
     "Tasks C2–C3" original wording, but Sprint 13 closes only C2.
     **Decision:** add a follow-up row below `llm_proposer.py`
     reading `(C3 — variant proposer)` as a pending sub-bullet,
     or note "C3 still ❌" in the annotation. Pick the cleaner
     option at execution time; both are honest.
   - Prepend a new "After Sprint 13 — …" entry to the Sprint
     History section.
3. Do **not** modify
   [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md). §3.3
   already describes Stage A's LLM-assisted proposal model; the
   pluggable-transport decision doesn't change the proposal's
   framing.
4. Do **not** modify
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §5 Phase C
   C2. The protocol entry already names `src/synthetic/llm_proposer.py`,
   structured JSON, retry, and the fallback log entry — Sprint 13
   ships exactly what the protocol asked for.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥319 passed, 1 skipped** (Sprint 12's `new_param`
brace-audit skip is the only skip in the suite). Zero failures.
The skip count must stay at exactly 1 — any new skip is a
regression.

> ⚠ **Plan-self-consistency cross-check** (continuing the Sprint
> 07–12 convention): the binding gate is "≥22 new test functions,
> all green, no skips, no regressions in the 297-pass +
> 1-skip baseline". The headline pytest number depends on how many
> parametrisations the implementer keeps. Update the RESEARCH_LOG
> entry with the actual count.

Smoke checks (PowerShell-friendly one-liners):

```powershell
python -c "from synthetic.llm_proposer import LLMClient, ProposalResult, propose; from synthetic.taxonomy import ModificationType; print('imports ok'); print('ProposalResult fields:', [f.name for f in __import__('dataclasses').fields(ProposalResult)])"

python -c "
from synthetic.llm_proposer import propose
from synthetic.taxonomy import ModificationType

class _S:
    def __init__(self, q): self._q = list(q)
    def complete(self, p): return self._q.pop(0)

r = propose('dummy', _S(['{\"k\": \"v\"}']), ModificationType.SYNONYM_LABEL)
assert r.payload == {'k': 'v'} and r.fallback is None
print('happy path ok')

r2 = propose('dummy', _S(['junk', 'junk2']), ModificationType.SYNONYM_LABEL)
assert r2.payload is None and r2.fallback.status == 'skipped'
assert r2.fallback.reason.startswith('malformed_llm_response_after_retry: ')
print('fallback path ok -', r2.fallback.reason[:60], '...')
"
```

End-to-end smoke (write to `_smoke_proposer.py` then run, then delete):

```python
from synthetic.llm_proposer import propose
from synthetic.taxonomy import ModificationType, TYPE_TO_LAYER

class _StubLLMClient:
    def __init__(self, responses):
        self._q = list(responses)
        self.calls = []
    def complete(self, prompt):
        self.calls.append(prompt)
        return self._q.pop(0)

# Happy path
r = propose('hola', _StubLLMClient(['{"synonyms": []}']), ModificationType.SYNONYM_LABEL)
assert r.payload == {"synonyms": []}
assert r.fallback is None
assert r.raw_responses == ('{"synonyms": []}',)

# Retry path — first call malformed, second valid
r = propose('hola', _StubLLMClient(['garbage', '{"k": "v"}']), ModificationType.PARAPHRASE)
assert r.payload == {"k": "v"}
assert len(r.raw_responses) == 2

# Double failure path — fallback record per-type
for mtype in ModificationType:
    stub = _StubLLMClient(['x', 'y'])
    r = propose('hola', stub, mtype)
    assert r.payload is None
    assert r.fallback is not None
    assert r.fallback.type == mtype
    assert r.fallback.layer == TYPE_TO_LAYER[mtype]
    assert r.fallback.status == "skipped"
    assert r.fallback.reason.startswith("malformed_llm_response_after_retry: ")

# Code-fence stripping
fence = '```json\n{"k": 1}\n```'
r = propose('hola', _StubLLMClient([fence]), ModificationType.OMISSION)
assert r.payload == {"k": 1}, r

print(f"proposer smoke ok — all 12 fallback shapes verified")
```

End-of-sprint expected `git status --short` (sprint-scoped subset
only):

```
new file:   src/synthetic/llm_proposer.py
new file:   tests/synthetic/test_llm_proposer.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_13.md   (this file, already committed)
```

Nothing under `src/utils/`, no notebooks, nothing under `data/`,
nothing under `configs/`. **No changes to any `layer_*.py`, to
`mutator.py`, to `composition.py`, to `taxonomy.py`, or to
`src/synthetic/prompts/`** — C2 is additive in one new module
plus its test file.

---

## Design notes worth committing to memory

- **Pluggable transport before model choice.** A3's outcome is
  unknown — we may end up on Llama 3.1 70B (local, reproducible),
  GPT-4-class (managed, fluent), or a Spanish-tuned alternative.
  Committing to a concrete transport in Sprint 13 would force a
  rewrite when A3 lands. The `Protocol` surface is the right
  abstraction: A3 ships *one* concrete `complete(prompt) -> str`
  implementation, Sprint 13 has already shipped the retry/fallback
  scaffold around it.
- **`Protocol`, not `ABC`.** Structural subtyping fits the
  one-method contract. No `@runtime_checkable` (we don't need
  `isinstance` checks; duck typing in tests is sufficient). The
  concrete transport in A3 may inherit from `LLMClient` for
  documentation purposes, but it's not required.
- **`propose` never raises.** Every failure mode is encoded in
  the `ProposalResult`. The caller (C3 variant proposer / D2
  orchestrator) walks a uniform return-value path; no `try/except`
  around the call. Rationale: the protocol's "skip + log via
  `Modification`" convention (§4) treats errors as data, not
  exceptions — the LLM round-trip is just another source of
  `Modification(status="skipped", reason=...)` records, alongside
  the composer's `same_target_conflict` and `layer_dependency_conflict`
  skips.
- **`_parse_json_object` is C2's "malformed" detector — not C3's
  schema validator.** C2 catches *JSON-validity* problems
  (unparseable, wrong root type, empty). C3 catches *structural
  shape* problems (the prompt asked for `{"synonyms": [...]}` but
  the LLM emitted `{"foo": "bar"}`). Mixing the two would couple
  the wrapper to per-prompt schemas — which the wrapper has no
  business knowing. The retry mechanism only fires on *C2-level*
  malformity; *C3-level* shape failures are a separate
  reject-and-log path C3 owns.
- **One retry, fixed.** Protocol §5 Phase C C2 says "malformed-response
  retry (×1)". Not configurable. The `retry_once: bool` knob in
  `propose` is for tests — never for production tuning. If a
  future sprint discovers that two retries materially improve
  acceptance rates, that's a protocol-level decision that updates
  §5 first; this module then changes uniformly.
- **Code-fence stripping is best-effort.** LLMs often emit
  ` ```json\n{...}\n``` ` despite the "Responde SOLO con un JSON"
  instruction. The pre-parse strip handles the three common shapes
  (`json`-tagged, bare, no-fence). Drift to other fence styles
  (e.g., `~~~`) triggers a retry — which is the right degradation.
  Don't over-engineer a regex fence-detector; let retry absorb the
  rare cases.
- **No streaming, no chat-format, no tool-use.** The Protocol is
  intentionally `complete(prompt) -> str`. A3's concrete client is
  responsible for adapting whatever native shape the chosen vendor
  exposes — chat-completion with a system message, single-shot
  completion, structured-output JSON-mode — into this single-method
  contract. Sprint 13 doesn't speculate.
- **No token budgeting, no rate-limit handling, no cost
  accounting.** These are concrete-transport concerns. The
  Protocol surface is too minimal to express any of them; A3's
  follow-up adds whatever instrumentation is needed once the
  vendor / endpoint is fixed.
- **No live LLM calls in pytest.** All tests use `_StubLLMClient`
  with a queued response list. Real-model smoke tests live in
  `scripts/spike_a3_*.py` or in a manually-run notebook, not in
  `tests/`. Rationale: pytest needs to run hermetically in CI; a
  real-model dependency would either flake (network) or balloon
  cost.
- **`raw_responses: tuple[str, ...]`, not `list[str]`.** Pinned by
  `frozen=True`. Phase E1's metadata pipeline may want to log the
  raw response for diagnostic reasons (e.g., to count
  fence-stripping vs. structural-malformity vs. empty-response
  fallbacks separately); a tuple gives an immutable handle to
  attach to the per-item record.
- **`_build_fallback`'s reason prefix is a grep handle.** Phase
  E1 will count fallbacks per type to inform F1 pilot reports:
  "5.2% of `paraphrase` proposals fell back; 11.4% of
  `unit_conversion` did". Standardising the prefix
  (`"malformed_llm_response_after_retry: "`) lets the metadata
  pipeline find them with a substring match instead of a regex.
- **No module-level state.** `propose` is a pure function (modulo
  the side effect of calling `client.complete`); no
  module-singleton client, no global retry counter, no caching.
  Sprint 13's module is import-cheap and unit-test-friendly.
- **No `llm_proposer.py` config file.** The protocol's file-tree
  listing doesn't reserve a `configs/synthetic/llm_proposer.yaml`
  path. A3's follow-up decides whether the concrete transport
  needs a config file (probably yes — endpoint URL, model name,
  API key env-var) and how to surface it. Sprint 13's surface
  doesn't reference any of those.
- **No new runtime dependency.** Sprint 13 imports only
  `dataclasses`, `json`, and `typing` from stdlib (plus
  `synthetic.taxonomy` from the in-repo package). No `httpx`, no
  `pydantic`, no `tenacity`, no `ollama`. The dependency surface
  stays minimal until A3 forces a vendor SDK in.

---

## References

- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — branch
  context, file map (the `llm_proposer.py` row flips ❌ → ✅ for
  C2; C3 stays ❌).
- [`../RESEARCH_PROPOSAL.md §3.3`](../RESEARCH_PROPOSAL.md) — Stage
  A pipeline framing (LLM-assisted variant proposal + human
  review). §7 open-questions #2 is the source of the "model
  choice is TBD per A3" deferral.
- [`../RESEARCH_PROTOCOL.md §5 Phase C`](../RESEARCH_PROTOCOL.md) —
  C2 task definition (one paragraph; the scope is exactly
  "structured JSON output, malformed-response retry (×1), fallback
  log entry"). §2 risk table row "LLM proposer model: TBD" is the
  pin for the A3 deferral.
- [`SPRINT_12.md`](SPRINT_12.md) — the immediate predecessor;
  closed Phase C Task C1 (the prompt library). Sprint 13 begins
  the LLM round-trip side of Phase C.
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py)
  — `Modification`, `ModificationType`, `Layer`, `TYPE_TO_LAYER`.
  Sprint 13 imports the first three for the fallback record's
  shape and the fourth for `type → layer` lookup.
- [`../../src/synthetic/prompts/__init__.py`](../../src/synthetic/prompts/__init__.py)
  — `load_prompt` + `PROMPT_DIR` + `PROMPT_FILENAMES`. Sprint 13
  does **not** import these; the C3 variant proposer is the
  consumer of both the prompt loader and the `propose` function
  in this sprint.

---

## Non-goals reminder

If you find yourself opening `src/synthetic/prompts/` to render a
slot, `src/synthetic/composition.py`, any `layer_*.py`,
`mutator.py`, or `taxonomy.py` — **stop**. C2 is additive in
exactly one new module file (`llm_proposer.py`) plus its test
file. Slot rendering belongs to C3.

If you find yourself adding a concrete HTTP transport (Ollama /
Anthropic / OpenAI / urllib-based) inside `llm_proposer.py` —
**stop**. A3 picks the model; the concrete transport is a separate
sprint. Sprint 13 ships the Protocol and the retry/fallback logic
only.

If you find yourself adding `pydantic` / `jsonschema` /
`langchain` / `httpx` / `tenacity` / `requests` to `requirements.txt`
or `pyproject.toml` — **stop**. Sprint 13 imports stdlib only.
New runtime deps are A3's call.

If you find yourself validating that a `synonym_label` response
has a `{"synonyms": [...]}` shape inside `_parse_json_object` —
**stop**. That is C3's per-type schema validation, not C2's
"malformed" detector. C2 only checks JSON validity + dict-root.

If you find yourself making `propose` raise on the
double-failure path — **stop**. The contract is "never raises;
all failures encoded in `ProposalResult.fallback`". A
caller-friendly uniform return type is the binding decision.

If you find yourself making the retry count configurable past
the `retry_once: bool` on/off knob — **stop**. The protocol
specifies one retry, fixed. Production-time tuning of the retry
budget is a §5 Phase C protocol-level decision, not a per-sprint
implementation knob.

If you find yourself running a real LLM endpoint inside the
pytest suite — **stop**. All tests use `_StubLLMClient` with
queued responses. Real-model smoke tests live in `scripts/` (A3's
problem) or in a manually-run notebook (a Phase F1 pilot
problem). Pytest stays hermetic.

If you find yourself adding logging, telemetry, or metric
emission inside `llm_proposer.py` — **stop**. The module is pure
data-flow; instrumentation is the orchestrator's (D2's) call.

If you find yourself extending the `Modification` dataclass to
carry the raw LLM response text alongside the fallback record —
**stop**. `ProposalResult.raw_responses` already exposes the
captured response sequence to the caller; embedding it in
`Modification` would change the taxonomy.py schema for a
diagnostic concern. Phase E1 may join the raw response back in via
the metadata pipeline if needed.
