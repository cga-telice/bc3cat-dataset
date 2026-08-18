# Sprint 24 — Phase A Task A3 (concrete `LLMClient` transport + record/replay harness)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 24                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | A3 (see [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md)) — split A3a (this sprint) / A3b (follow-up) |
| **Predecessor** | Sprint 23 — G3 + G4 release docs (`DATA_CARD.md` + README "Synthetic Variant" + `HANDOFF.md`) (see [`SPRINT_23.md`](SPRINT_23.md)) |
| **Successor**   | Sprint 25 — **A3b** live model-choice spike (≥2 candidates, recorded transcripts) → **F1** single-concept pilot → **F2** pilot retro → **F3** full generation → **F4** validation (`QUALITY_REPORT.md`) → post-F3 `DATA_CARD.md` statistics refresh |

---

## Context

The entire Stage-A generation stack is built and test-pinned, and **every layer
takes an `LLMClient` as an injected dependency** — but the one concrete
implementation of that dependency does not exist. That is the only thing standing
between the orchestrator and a real pilot run.

The seam is already cut:

* [`llm_proposer.py`](../../src/synthetic/llm_proposer.py) defines the transport
  contract — `LLMClient` is a `Protocol` with a single method
  `complete(self, prompt: str) -> str`. `propose()` calls it, parses the response
  as strict JSON, **retries once on malformed output**, and emits a
  `Modification(status="skipped", reason="malformed_llm_response_after_retry: …")`
  on double failure. This is the *response-shape* retry layer.
* [`variant_proposer.py`](../../src/synthetic/variant_proposer.py) (C3) renders
  the prompt, ships it through `propose()`, and validates the payload against the
  per-`ModificationType` schema (its own `schema_validation_failed: …` skip).
* [`run_synthetic.py`](../../src/synthetic/run_synthetic.py) (D2) is the
  concept-loop orchestrator: `run_catalog` / `run_concept` / `run_variant` thread
  a `client: LLMClient` all the way down, plan deterministic per-condition
  variants (`CONDITION_SPECS` covers the §6 conditions), and write the variant
  catalog. It explicitly notes "**a concrete LLM transport (A3) — takes an
  `LLMClient`**" as the one thing it does not own.

Every test to date injects a hand-rolled fake `complete`. **No code path opens a
socket.** What is missing (`RESEARCH_PROTOCOL.md §3.5`: *LLM-assisted variant
proposer — ❌ C1–C3*; §4: *LLM proposer model — TBD, spike in A3*) is a real
transport: something that takes a rendered Spanish prompt and returns a model's
text completion, with timeouts, transport-level retry, and API-key handling — and
a way to make that deterministic and offline for the test suite and for
reproducible re-runs.

### Why A3 now

Sprint 23 closed Phase G documentation and named Sprint 24 = A3. A3 is the
**critical-path unblock**: F1 (single-concept pilot) cannot run without a real
`complete()`, and F1→F2→F3→F4 are the remaining substance of the project. Every
upstream consumer is finished and frozen; A3 is a single, well-isolated new
module behind an already-pinned `Protocol`.

### The honest split: A3a (this sprint) vs A3b (follow-up)

`RESEARCH_PROTOCOL.md §5 A3` bundles two things: (a) **build the transport**, and
(b) **run a live spike across ≥2 candidate models** and record the choice in
`RESEARCH_LOG.md` + §4. These have opposite testability:

* **A3a — the transport + record/replay harness — is code with hermetic tests.**
  Provider-agnostic HTTP client, timeout/retry/backoff, key handling, plus a
  deterministic replay client and a recording wrapper. Every test is network-free
  (injected fake sender / recorded fixtures). This is Sprint 24.
* **A3b — the live model-choice spike — is a manual, out-of-suite, paid activity.**
  It requires real API keys, network, and cost, and produces a *judgement*
  (Spanish-technical fluency, JSON-output reliability, cost) recorded in prose. It
  **cannot** live in the deterministic suite. Sprint 24 *enables* it (the
  `RecordingClient` captures each candidate's transcript so the spike is
  reproducible and the chosen model's responses replay offline forever), but the
  decision itself — and the §4 `LLM proposer model` flip from `TBD` — happens when
  César runs the spike. **That is Sprint 25's opening step, not a Sprint 24
  deliverable.**

This is the same discipline as Sprint 23 (build the runnable contract; never
fabricate the measured result). The suite stays hermetic and green; no live call
runs in `pytest`.

### The load-bearing design decisions (decide up front)

1. **One new module, behind the existing `Protocol`; do not touch the seam.**
   `src/synthetic/llm_client.py` adds concrete classes whose only required public
   method is `complete(self, prompt: str) -> str`. `llm_proposer.LLMClient`,
   `variant_proposer`, and `run_synthetic` are **not edited** — the whole point of
   the Protocol was that A3 slots in underneath. The response-shape retry stays in
   `llm_proposer`; transport adds a *different* retry layer (network faults), and
   the two never merge.

2. **Stdlib transport — no new dependency.** The repo pins no
   `requirements`/`pyproject` and installs deps ad hoc; `packaging`/`loaders`
   import `pyarrow`/`pandas` lazily precisely to stay importable without them. The
   HTTP client therefore uses **stdlib `urllib.request` + `json`** — no `requests`,
   `httpx`, or vendor SDK. It speaks the **OpenAI-compatible `/chat/completions`**
   contract (the de-facto standard exposed by OpenAI, vLLM, LM Studio, and
   Ollama's `/v1` compat endpoint), so a single client covers both the
   "GPT-4-class API" and "local Llama" candidates of §4/§10 **by configuration
   alone** (base URL + model id). (If a native Anthropic Messages-API client is
   wanted for a Claude candidate, it is a thin sibling subclass added later; the
   OpenAI-compat surface already covers an OpenAI-compatible gateway in front of
   any model. Out of scope here.)

3. **Temperature 0.0, single user message — the protocol pin.**
   `RESEARCH_PROTOCOL.md §8` mandates temperature 0.0 and a strict-JSON contract.
   The client sends the rendered prompt as one user-role message at
   `temperature: 0.0` and returns `choices[0].message.content` verbatim (no
   trimming beyond what the transport envelope requires — the code-fence stripping
   already lives in `llm_proposer._strip_code_fence`).

4. **Two retry layers, cleanly separated.** `llm_proposer.propose` already owns
   the *malformed-JSON* retry (one resend, then skip+log). The transport owns a
   *network-fault* retry: timeouts, connection errors, HTTP 429, and 5xx are
   retried with bounded exponential backoff up to a configured cap; a 4xx other
   than 429 (e.g. 401 bad key, 400 bad request) is **fail-loud** (`LLMTransportError`,
   no retry — retrying a bad key is pointless); exhausted retries are fail-loud. A
   transport that exhausts retries raises rather than returning a sentinel string,
   because a network outage is an operator problem (fix the key/endpoint), not a
   per-variant skip.

5. **Determinism + offline reproducibility via record/replay.** Two non-network
   clients ship alongside the HTTP one:
   * `ReplayClient` — given a fixtures store keyed by a **stable hash of the
     prompt**, returns the recorded response; an unknown prompt is **fail-loud**
     (so a drifted prompt is caught, never silently mis-served). This is what the
     hermetic tests use and what makes a generation run reproducible without paying
     for or depending on a live model.
   * `RecordingClient` — wraps any `LLMClient`, returns its responses unchanged,
     and writes each `prompt-hash → response` into the store as a side effect. Run
     a live spike once through a `RecordingClient`; replay it forever.
   The store is plain JSON-per-prompt under a config(env)-resolved directory; the
   prompt hash is `sha256(prompt)` so it is content-addressed and stable across
   processes/`PYTHONHASHSEED`.

6. **Injectable sender seam — zero sockets in `pytest`.** `HttpLLMClient` takes an
   optional `sender` callable (default = the real `urllib` POST). Tests inject a
   fake sender that returns canned envelopes or raises canned transport errors, so
   the entire HTTP client — happy path, retry, backoff schedule, fail-loud
   branches, envelope parsing — is exercised **without opening a socket**. The lone
   live smoke is opt-in and skip-by-default (decision 7).

7. **Live smoke is opt-in and skips-not-fails — the pyarrow/data-gating rule.**
   A single end-to-end "really call the configured endpoint once" test is gated on
   an env var (e.g. `BC3CAT_LLM_LIVE=1`) **and** the key being present; absent
   either, it `pytest.skip`s. In CI and in any bare tree it skips, never fails —
   exactly how the `pyarrow`- and OBRA-CIVIL-data-gated tests behave. The
   deterministic suite never makes a network call.

8. **No secrets in code or fixtures.** The API key is read from an env var named
   in config (default e.g. `BC3CAT_LLM_API_KEY`); it is never written to the
   record/replay store, never logged, never committed. The recorded fixtures
   contain only prompts and model responses.

---

## Scope

### In scope

- **A3a-1 — new module `src/synthetic/llm_client.py`.** Concrete `LLMClient`
  implementations satisfying `llm_proposer.LLMClient` (`complete(prompt) -> str`):
  - `LLMClientError` / `LLMTransportError` — distinct, catchable transport
    exceptions.
  - `LLMConfig` (dataclass) — `base_url`, `model`, `api_key_env`, `timeout`,
    `max_retries`, `backoff_base`, `temperature` (default `0.0`); a
    `from_config()`/`from_env()` builder resolving defaults from `utils.config`
    (decision 8). No key value stored on the dataclass — only the env-var *name*.
  - `HttpLLMClient` — OpenAI-compatible `/chat/completions` POST via stdlib
    `urllib.request`; one user message at `temperature 0.0`; returns
    `choices[0].message.content`; transport retry/backoff (decision 4); injectable
    `sender` (decision 6); fail-loud `LLMTransportError` on exhausted retries /
    non-retryable 4xx / unparseable envelope.
  - `ReplayClient` — content-addressed (`sha256(prompt)`) read from a JSON store;
    unknown prompt → fail-loud (decision 5).
  - `RecordingClient` — wraps an `LLMClient`, persists `prompt-hash → response`
    (decision 5).
  - A thin `main(argv)` CLI (mirroring `packaging`/`loaders`) — e.g. a `complete`
    subcommand that reads a prompt from stdin/file and prints the completion using
    the configured client; useful for the A3b spike. Optional but encouraged for
    parity.

- **A3a-2 — config entries.** Add the LLM transport settings to
  [`src/utils/config.py`](../../src/utils/config.py): default base URL, model id,
  API-key env-var *name*, timeout, retry/backoff caps, and the record/replay store
  directory (default under `SYNTHETIC_DATA_ROOT`, e.g.
  `SYNTHETIC_DATA_ROOT / "llm_cache"`), all env-overridable. Pure path/scalar
  config — no I/O, no key value.

- **A3a-3 — tests `tests/synthetic/test_llm_client.py`.** All hermetic except the
  one gated live smoke:
  - Protocol conformance: `HttpLLMClient` / `ReplayClient` are accepted by
    `llm_proposer.propose` (duck-typed `complete`).
  - `HttpLLMClient` happy path (fake sender): returns the content string; the
    request body carries `model`, `temperature: 0.0`, and the prompt as a single
    user message; the auth header is built from the env key.
  - Transport retry: fake sender raises timeout/connection-error twice then
    succeeds → one returned string, attempt count asserted; 429 and 5xx retried;
    non-429 4xx fail-loud (no retry); exhausted retries fail-loud
    (`LLMTransportError`); backoff schedule is bounded (monkeypatch `sleep` to
    record the delays without waiting).
  - Envelope parse: missing/empty `choices`, non-JSON body → `LLMTransportError`.
  - `ReplayClient`: known prompt → recorded text; unknown prompt → fail-loud.
  - `RecordingClient`: records, and a fresh `ReplayClient` reads it back (round
    trip).
  - End-to-end, still hermetic: `propose(prompt, ReplayClient(store), mtype)`
    returns a payload for a well-formed recorded response; **and a malformed
    recorded response drives the existing C2 `malformed_llm_response_after_retry`
    fallback** — proving the new client composes with the unchanged proposer.
  - Key handling: no API-key value appears in the record/replay store or in any
    exception message (assert the env value is absent from the serialized store +
    the `repr`/`str` of raised errors).
  - **Live smoke** (`BC3CAT_LLM_LIVE=1` + key present, else `skip`): one real
    `complete()` returns a non-empty string. Skip-not-fail otherwise.

- **Doc + housekeeping**:
  - Add an `llm_client.py` row (✅, A3a) to the file map / "New Files in This
    Branch" in [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); record the
    one-module-behind-the-Protocol / stdlib-no-dep / two-retry-layers /
    record-replay / injectable-sender / live-smoke-gated / no-secrets decisions and
    the A3a-vs-A3b split. Prepend an "After Sprint 24" Sprint History entry.
  - Sprint 24 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md): §3.5 — flip the
    transport portion (add/annotate a "Concrete `LLMClient` transport" row ✅ A3a);
    §5 A3 — annotate **A3a ✅ (transport + record/replay)**, **A3b ⏳ (live
    model-choice spike, pending)**; §4 `LLM proposer model` row **stays `TBD`**
    with a note that the transport now exists and the spike (A3b) is the gate.
    Status/annotation only — no design rewrite.

### Out of scope (explicit)

- **A3b — the live model-choice spike and the §4 model decision.** Manual, paid,
  out-of-suite (decision A3a/A3b split). Sprint 25's opening step.
- **F1–F4 (pilot, retro, full generation, validation).** A3 unblocks F1; it is not
  F1. No real catalog is generated, no `QUALITY_REPORT.md`.
- **A native Anthropic Messages-API client / multi-provider abstraction.** One
  OpenAI-compatible HTTP client + record/replay is enough to unblock F1; a second
  provider subclass is added only if the A3b spike picks a model that needs it
  (decision 2).
- **Editing the seam.** No changes to `llm_proposer.py`, `variant_proposer.py`,
  `run_synthetic.py`, `prompts/`, `slot_extractor.py`, `rule_emitter.py`,
  `composition.py`, `variant_catalog.py`, the `layer_*` mutators, `mutator.py`,
  `stage_runners.py`, `stage_b.py`, `metadata.py`, `review.py`, `packaging.py`,
  `loaders.py`. A3 slots in *under* the existing Protocol.
- **Any live network call in the deterministic suite** (decision 7). The replay
  store and the injected sender keep `pytest` hermetic.
- **Variant budgets / Phase-F sampling policy.** `run_synthetic` already plans one
  variant per single-target / per stacked condition; budgets are F2/F3.
- **Merging `synthetic` to `main`.** Permanently forbidden
  ([`CLAUDE.md`](../../CLAUDE.md)).

---

## Content requirements

1. **`src/synthetic/llm_client.py` exists and provides a working
   `complete(prompt) -> str` transport** that satisfies
   `llm_proposer.LLMClient`, plus `ReplayClient` and `RecordingClient`. The
   orchestrator can be handed any of them unchanged.
2. **No new third-party dependency.** Transport is stdlib `urllib.request` + `json`
   (decision 2). The module imports `taxonomy`/`utils.config` + stdlib only; never
   `stage_b`/`run_synthetic`/`stage_runners`/`review`/`mutator`/any `layer_*`.
3. **Two retry layers stay separated** (decision 4): the malformed-JSON retry
   remains in `llm_proposer` (unedited); transport adds a network-fault
   retry/backoff with fail-loud exhaustion and fail-loud non-retryable 4xx.
4. **The deterministic suite makes zero network calls** (decisions 6–7): every
   non-live test uses an injected sender or `ReplayClient`; the single live smoke
   is env-gated and skips-not-fails.
5. **No secret leaks** (decision 8): the API key value never enters the
   record/replay store, logs, or exception text; config holds only the env-var
   name.
6. **The new client composes with the unchanged proposer**: a hermetic
   `propose(...)`-over-`ReplayClient` test shows both a successful payload and the
   existing C2 skip-and-log fallback on a malformed recorded response.

## Acceptance

- `src/synthetic/llm_client.py` and `tests/synthetic/test_llm_client.py` exist;
  no `src/synthetic/*.py` *other than* `llm_client.py` is modified, and
  `utils/config.py` gains only additive LLM settings (a `git diff` shows the seam
  files untouched).
- `HttpLLMClient` satisfies `LLMClient` (accepted by `propose`); with an injected
  fake sender it returns the model content, sends `temperature 0.0` + one user
  message, retries timeouts/429/5xx with bounded backoff, and fails loud on
  non-retryable 4xx / exhausted retries / bad envelope.
- `ReplayClient` round-trips a known prompt and fails loud on an unknown one;
  `RecordingClient` writes a store a fresh `ReplayClient` can read.
- No API-key value appears in the store or in any raised error message
  (asserted).
- `pytest tests -q` makes **no network call** and reports the Sprint 22/23
  baseline **719 passed** still green, **plus** the new hermetic `llm_client`
  tests all passing, **plus** the live smoke **skipped** (→ **2 skipped** total:
  the pre-existing Sprint-12 `new_param` brace-audit skip + the new live smoke).
  Zero failures in any tree, with or without `BC3CAT_LLM_LIVE` / a key / network.
- Housekeeping: `CLAUDE_SYNTHETIC.md` gains the `llm_client.py` ✅ row + decisions
  + "After Sprint 24" history entry; `RESEARCH_LOG.md` Sprint 24 entry prepended;
  `RESEARCH_PROTOCOL.md` §3.5/§5 A3a flipped ✅, A3b annotated pending, §4 model
  row left `TBD` with the transport-now-exists note.

---

## Tasks

### Task 1 — `src/synthetic/llm_client.py` (A3a-1)
Implement `LLMConfig`, `HttpLLMClient` (OpenAI-compatible `/chat/completions` over
stdlib `urllib`, injectable `sender`, two-layer-separated transport retry/backoff,
fail-loud `LLMTransportError`), `ReplayClient`, `RecordingClient`, and the
exceptions. Optional thin `main(argv)` `complete` CLI. Temperature 0.0; return
`choices[0].message.content`. Imports `taxonomy`/`utils.config` + stdlib only.

### Task 2 — config entries (A3a-2)
Add the additive LLM transport settings to `utils/config.py` (base URL, model id,
API-key env-var name, timeout, retry/backoff caps, record/replay store dir under
`SYNTHETIC_DATA_ROOT`), all env-overridable. No key value, no I/O.

### Task 3 — `tests/synthetic/test_llm_client.py` (A3a-3)
Write the hermetic tier per Scope §A3a-3 (Protocol conformance; HTTP happy path +
request-body assertions; retry/backoff/fail-loud branches via injected sender +
monkeypatched `sleep`; envelope-parse failures; `ReplayClient`/`RecordingClient`
round-trips + fail-loud unknown; end-to-end `propose`-over-`ReplayClient` success
and C2 fallback; no-secret-leak assertions) plus the one env-gated live smoke that
skips-not-fails.

### Task 4 — Housekeeping
1. Prepend a Sprint 24 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the A3a-vs-A3b split, the
   one-module-behind-the-Protocol / stdlib-no-dep / two-retry-layers /
   record-replay / injectable-sender / live-smoke-gated / no-secrets decisions, the
   suite math (719 + new hermetic passing, 2 skipped), and the next step (Sprint 25
   — A3b spike then F1).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): add the `llm_client.py` ✅
   file-map row; record the decisions; prepend the "After Sprint 24" history entry.
3. In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md): §3.5 add/flip the
   concrete-transport row ✅ (A3a); §5 annotate A3a ✅ / A3b ⏳; §4 leave the model
   row `TBD` with the "transport exists; spike (A3b) is the gate" note. Status only.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
# Default (hermetic) run — must make NO network call:
pytest tests -q --basetemp="$env:TEMP\pt_s24"
```

Expected: the Sprint 22/23 baseline **719 passed** still green, the new hermetic
`llm_client` tests all passing, and the live smoke **skipped** → **719+N passed,
2 skipped**, zero failures, **zero network calls**.

```powershell
# Confirm the seam is untouched (only llm_client.py added, config.py additive):
git status --short
git diff -- src/synthetic/llm_proposer.py src/synthetic/variant_proposer.py src/synthetic/run_synthetic.py   # empty

# Optional, opt-in live smoke (NOT part of the deterministic suite; costs a call):
$env:BC3CAT_LLM_LIVE = "1"
$env:BC3CAT_LLM_API_KEY = "<key>"      # never committed
pytest tests/synthetic/test_llm_client.py -q -k live
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/llm_client.py
new file:   tests/synthetic/test_llm_client.py
modified:   src/utils/config.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_24.md (this file)
```

No edits to the Stage-A seam (`llm_proposer` / `variant_proposer` /
`run_synthetic` / `prompts` / `slot_extractor` / `rule_emitter` / `composition` /
`variant_catalog` / `layer_*` / `mutator`) nor to `stage_*` / `metadata` /
`review` / `packaging` / `loaders`. No new dependency. No secret committed.

---

## Design notes worth committing to memory

- **A3 splits cleanly: build the transport (code, hermetic) vs. run the spike
  (manual, paid, prose).** Sprint 24 ships A3a — the `complete()` transport plus a
  record/replay harness — and leaves A3b (the live ≥2-model fluency/JSON/cost
  decision and the §4 model flip) to Sprint 25's opening step. Same discipline as
  Sprint 23: build the runnable contract, never fabricate the measured result.
- **A3 slots in under an already-frozen Protocol.** The whole Stage-A stack takes
  `LLMClient`; A3 implements `complete(prompt) -> str` and edits none of it. The
  malformed-JSON retry stays in `llm_proposer`; transport adds a *separate*
  network-fault retry.
- **Stdlib transport, no new dependency.** `urllib.request` + `json` against the
  OpenAI-compatible `/chat/completions` contract covers the API and local-Llama
  candidates by config alone.
- **Record/replay is what keeps generation reproducible and the suite hermetic.**
  Run the spike once through a `RecordingClient`; replay it forever, offline,
  free. The deterministic suite opens zero sockets; the live smoke is env-gated
  skip-not-fail.
- **Next is A3b then F1.** With the transport in hand, Sprint 25 runs the
  model-choice spike, records the decision, then drives the single-concept pilot.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase A`](../RESEARCH_PROTOCOL.md) — A3 (this
  sprint, split A3a/A3b); §4 design table (`LLM proposer model` = TBD); §8 prompt
  templates (temperature 0.0, strict-JSON contract); §3.5 what-exists-vs-builds.
- [`../../src/synthetic/llm_proposer.py`](../../src/synthetic/llm_proposer.py) —
  the `LLMClient` Protocol (`complete(prompt) -> str`) A3 implements, and the
  malformed-JSON retry / skip-and-log layer that stays put.
- [`../../src/synthetic/variant_proposer.py`](../../src/synthetic/variant_proposer.py)
  — C3 schema validation that consumes the proposer payload (unchanged).
- [`../../src/synthetic/run_synthetic.py`](../../src/synthetic/run_synthetic.py) —
  D2 orchestrator that threads `client: LLMClient` and explicitly defers the
  concrete transport to A3.
- [`../../src/utils/config.py`](../../src/utils/config.py) — where the additive
  LLM transport settings (base URL, model, key env-var name, timeout, store dir)
  land.
- [`SPRINT_23.md`](SPRINT_23.md) — the predecessor (G3/G4 docs) and the
  honest-caveat precedent (build the contract; never fabricate the unmeasured).
- [`../../CLAUDE.md`](../../CLAUDE.md) — the never-merge-`synthetic`-to-`main`
  invariant.

---

## Non-goals reminder

If you find yourself editing `llm_proposer.py`, `variant_proposer.py`, or
`run_synthetic.py` — **stop**. A3 implements the `LLMClient` Protocol in a *new*
module; the seam is frozen. The malformed-JSON retry stays in `llm_proposer`;
transport adds its own network-fault retry.

If you find yourself adding `requests`, `httpx`, `openai`, or `anthropic` to the
imports — **stop**. The transport is stdlib `urllib.request` against the
OpenAI-compatible contract; no new dependency.

If you find yourself making a real network call from a non-`live` test, or letting
the live smoke *fail* (rather than skip) when no key/network is present — **stop**.
The deterministic suite is hermetic; the live smoke is env-gated skip-not-fail,
exactly like the `pyarrow`/data-gated tests.

If you find yourself running the live spike, picking a model, or flipping the §4
`LLM proposer model` row from `TBD` — **stop**. That is A3b (Sprint 25), a manual
paid activity, not a Sprint 24 deliverable. Sprint 24 *enables* the spike via
`RecordingClient`; it does not run it.

If you find yourself writing an API key into config, a fixture, a log line, or an
exception message — **stop**. Config holds only the env-var *name*; the key value
never lands on disk or in error text.

If you find yourself generating a real catalog, calling `run_catalog` for output,
or writing `QUALITY_REPORT.md` — **stop**. That is Phase F. A3 builds the
transport that *unblocks* the pilot; it does not run it.
