"""Model-choice spike harness — Sprint 25, Phase A Task A3b-build.

The one open Phase-A research question is *which model do we generate
BC3CAT-Syn with?* (`RESEARCH_PROTOCOL.md §4` still reads `LLM proposer model =
TBD`). A3a (`llm_client.py`) shipped the transport — `HttpLLMClient` /
`ReplayClient` / `RecordingClient` — but not the answer. This module is the
runnable half of A3b: a thin harness that drives the **unedited**
`run_synthetic.run_concept` over one pilot concept across the 12 single-type
conditions for each candidate model, wraps every client in a `RecordingClient`,
and tallies an **automatable** scorecard off the returned `VariantCatalogEntry`.

The honest split this module embodies (mirroring A3a → A3b):

* **A3b-build (this module) — code with hermetic tests.** It measures what code
  can verify: how many variants proposed vs. skipped, the per-`ModificationType`
  outcome, the C2/C3 skip split (`malformed_llm_response_after_retry:` vs
  `schema_validation_failed:`), per-call latency, and mean response length.
* **A3b-run — manual, paid, out-of-suite (César).** The live ≥2-model
  comparison, the Spanish-technical-fluency read off the recorded transcripts,
  the decision, and the `§4` `TBD → model` flip. **This module does not pick a
  model, run a paid spike, or flip `§4`.** It *enables* that close-out.

Design invariants (Sprint 25 §"load-bearing design decisions"):

1. **Composes `run_concept`; reimplements nothing.** No new prompt rendering,
   parsing, or schema logic — those are the frozen C2/C3 seam.
2. **Consumer of the orchestrator, never imported by it.** This module imports
   `run_synthetic` / `llm_client` / `taxonomy` / `utils.config` + stdlib; nothing
   in the Stage-A/Stage-B seam imports `spike`.
3. **Code measures the measurable; fluency is human.** No `fluency` field on the
   scorecard — the harness surfaces the recorded transcripts; César reads them.
4. **`RecordingClient` is mandatory.** Each candidate runs through
   `RecordingClient(...)` into a per-candidate store; the chosen candidate's
   store becomes F1's offline replay source.
5. **No secrets, no new dependency.** The key is read by `HttpLLMClient` from the
   `config`-named env var at request time, never written to a store/log/score;
   the harness is stdlib + existing `synthetic` modules only.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Sequence

from .llm_client import HttpLLMClient, LLMConfig, RecordingClient
from .run_synthetic import CONDITION_SPECS, run_concept
from .taxonomy import ModificationType
from .variant_catalog import VariantCatalogEntry
from utils import config

__all__ = [
    "SINGLE_TYPE_CONDITIONS",
    "MALFORMED_SKIP_PREFIX",
    "SCHEMA_SKIP_PREFIX",
    "CandidateSpec",
    "CandidateScore",
    "run_candidate",
    "run_spike",
    "format_scorecard",
    "main",
]


# The 12 single-type generation conditions (`RESEARCH_PROTOCOL.md §6`): the 11
# `single_*` conditions plus `new_param_only`. Pinned in a deterministic order
# (sorted) so the spike — and the recorded store it produces — is reproducible.
SINGLE_TYPE_CONDITIONS: tuple[str, ...] = tuple(
    sorted(c for c in CONDITION_SPECS if c.startswith("single_") or c == "new_param_only")
)

# Skip-reason prefixes owned by the frozen C2/C3 seam (`llm_proposer.propose` /
# `variant_proposer.propose_variant`). The scorecard partitions on these; it does
# not re-derive them.
MALFORMED_SKIP_PREFIX = "malformed_llm_response_after_retry:"
SCHEMA_SKIP_PREFIX = "schema_validation_failed:"


# ---------------------------------------------------------------------------
# Candidate spec + scorecard (automatable fields only — decision 3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CandidateSpec:
    """A spike candidate: a human-readable slug + the transport config.

    Per A3a decision 2, ≥2 candidates differ by `base_url` + `model` (+ key env
    var) alone — one OpenAI-compatible `HttpLLMClient` covers a GPT-4-class API
    and a local Llama by config. `name` is the per-candidate store sub-directory,
    so it must be filesystem-safe.
    """

    name: str
    config: LLMConfig

    @classmethod
    def parse(cls, spec: str) -> "CandidateSpec":
        """Parse a CLI `name:base_url:model[:api_key_env]` spec.

        `base_url` may itself contain a `:` (`https://...`), so the split is
        anchored: first field is the name, last (or last-two) are model and an
        optional key-env name, the middle re-joins as the URL.
        """
        parts = spec.split(":")
        if len(parts) < 3:
            raise ValueError(
                f"candidate spec must be 'name:base_url:model[:api_key_env]', got {spec!r}"
            )
        name = parts[0]
        # Heuristic: a trailing field with no '/' and that looks like an env-var
        # name (UPPER_SNAKE) is the api_key_env; otherwise the key env defaults.
        api_key_env = config.LLM_API_KEY_ENV
        tail = parts[-1]
        if "/" not in tail and tail.isupper() and len(parts) >= 4:
            api_key_env = tail
            model = parts[-2]
            base_url = ":".join(parts[1:-2])
        else:
            model = parts[-1]
            base_url = ":".join(parts[1:-1])
        base = LLMConfig.from_env()
        cfg = LLMConfig(
            base_url=base_url,
            model=model,
            api_key_env=api_key_env,
            timeout=base.timeout,
            max_retries=base.max_retries,
            backoff_base=base.backoff_base,
            temperature=base.temperature,
        )
        return cls(name=name, config=cfg)


@dataclass(frozen=True)
class CandidateScore:
    """The automatable per-candidate scorecard tallied off a `VariantCatalogEntry`.

    **No fluency field** (decision 3): Spanish-technical fluency is the human read
    of the recorded transcripts, not a code-scored column.
    """

    candidate_name: str
    proposed: int
    skipped_total: int
    malformed_skips: int
    schema_skips: int
    llm_calls: int
    total_latency: float
    mean_latency: float
    mean_response_length: float
    per_type: dict[str, dict[str, int]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "candidate_name": self.candidate_name,
            "proposed": self.proposed,
            "skipped_total": self.skipped_total,
            "malformed_skips": self.malformed_skips,
            "schema_skips": self.schema_skips,
            "llm_calls": self.llm_calls,
            "total_latency": self.total_latency,
            "mean_latency": self.mean_latency,
            "mean_response_length": self.mean_response_length,
            "per_type": self.per_type,
        }


# ---------------------------------------------------------------------------
# Measuring wrapper — automatable latency + response-length, deterministic clock
# ---------------------------------------------------------------------------

class _MeasuringClient:
    """Wraps an `LLMClient`, returns its responses unchanged, and records per-call
    latency (via an injectable `clock`) and response length as a side effect.

    Sits *inside* the `RecordingClient` so latency measures the model round-trip,
    not the store write. The injectable clock keeps tests free of wall-clock flake
    (decision 5 / requirement: deterministic latency).
    """

    def __init__(self, inner, clock: Callable[[], float] = time.perf_counter):
        self._inner = inner
        self._clock = clock
        self.latencies: list[float] = []
        self.response_lengths: list[int] = []

    def complete(self, prompt: str) -> str:
        start = self._clock()
        response = self._inner.complete(prompt)
        self.latencies.append(self._clock() - start)
        self.response_lengths.append(len(response))
        return response


# ---------------------------------------------------------------------------
# Client factory (the test/live injection seam)
# ---------------------------------------------------------------------------

ClientFactory = Callable[[LLMConfig], object]


def _http_client_factory(cfg: LLMConfig):
    """Default factory: a live `HttpLLMClient`. Tests inject a canned/replay
    client so the deterministic suite opens zero sockets (requirement 4)."""
    return HttpLLMClient(cfg)


# ---------------------------------------------------------------------------
# The spike
# ---------------------------------------------------------------------------

def run_candidate(
    stage_json: dict,
    concept_key: str,
    candidate: CandidateSpec,
    *,
    store_root: Optional[Path] = None,
    catalog_root: Optional[Path] = None,
    seed: int = 0,
    conditions: Sequence[str] = SINGLE_TYPE_CONDITIONS,
    client_factory: ClientFactory = _http_client_factory,
    clock: Callable[[], float] = time.perf_counter,
    replay: bool = False,
) -> CandidateScore:
    """Run one candidate over `concept_key` across `conditions`, recording every
    transcript, and return the automatable scorecard.

    Composition only (decision 1): builds
    `RecordingClient(_MeasuringClient(client_factory(cfg)))`, calls the **unedited**
    `run_concept`, and tallies the score off the returned `VariantCatalogEntry`.

    `replay=True` swaps the inner transport for a `ReplayClient` over this
    candidate's existing store — re-tally an old spike offline, no live call.
    """
    store_root = Path(store_root) if store_root is not None else Path(config.LLM_CACHE_DIR)
    catalog_root = (
        Path(catalog_root) if catalog_root is not None else store_root / "_catalog"
    )
    store_dir = store_root / candidate.name
    out_dir = catalog_root / candidate.name

    if replay:
        from .llm_client import ReplayClient
        inner = ReplayClient(store_dir)
    else:
        inner = client_factory(candidate.config)
    measuring = _MeasuringClient(inner, clock)
    recording = RecordingClient(measuring, store_dir)

    entry, _ = run_concept(
        stage_json, concept_key, conditions, recording,
        out_dir=out_dir, seed=seed,
    )
    return _score_from_entry(candidate.name, entry, measuring)


def run_spike(
    stage_json: dict,
    concept_key: str,
    candidates: Sequence[CandidateSpec],
    *,
    store_root: Optional[Path] = None,
    catalog_root: Optional[Path] = None,
    seed: int = 0,
    conditions: Sequence[str] = SINGLE_TYPE_CONDITIONS,
    client_factory: ClientFactory = _http_client_factory,
    clock: Callable[[], float] = time.perf_counter,
    replay: bool = False,
) -> list[CandidateScore]:
    """Run each candidate (each into its own per-candidate store) and return the
    scorecards in candidate order."""
    return [
        run_candidate(
            stage_json, concept_key, candidate,
            store_root=store_root, catalog_root=catalog_root, seed=seed,
            conditions=conditions, client_factory=client_factory, clock=clock,
            replay=replay,
        )
        for candidate in candidates
    ]


def _score_from_entry(
    candidate_name: str,
    entry: VariantCatalogEntry,
    measuring: _MeasuringClient,
) -> CandidateScore:
    """Tally the automatable scorecard off a `VariantCatalogEntry` + the measuring
    wrapper. Reads the C2/C3 split off the frozen seam's reason-prefixes."""
    proposed = len(entry.variants)
    skipped_total = len(entry.skipped)
    malformed = sum(
        1 for m in entry.skipped if (m.reason or "").startswith(MALFORMED_SKIP_PREFIX)
    )
    schema = sum(
        1 for m in entry.skipped if (m.reason or "").startswith(SCHEMA_SKIP_PREFIX)
    )

    per_type: dict[str, dict[str, int]] = {}
    for record in entry.variants:
        bucket = per_type.setdefault(
            record.modification_type.value, {"proposed": 0, "skipped": 0}
        )
        bucket["proposed"] += 1
    for m in entry.skipped:
        bucket = per_type.setdefault(m.type.value, {"proposed": 0, "skipped": 0})
        bucket["skipped"] += 1

    llm_calls = len(measuring.latencies)
    total_latency = sum(measuring.latencies)
    mean_latency = total_latency / llm_calls if llm_calls else 0.0
    mean_response_length = (
        sum(measuring.response_lengths) / len(measuring.response_lengths)
        if measuring.response_lengths
        else 0.0
    )
    return CandidateScore(
        candidate_name=candidate_name,
        proposed=proposed,
        skipped_total=skipped_total,
        malformed_skips=malformed,
        schema_skips=schema,
        llm_calls=llm_calls,
        total_latency=total_latency,
        mean_latency=mean_latency,
        mean_response_length=mean_response_length,
        per_type=per_type,
    )


# ---------------------------------------------------------------------------
# Scorecard formatting (automatable columns only — no fluency column)
# ---------------------------------------------------------------------------

_SCORECARD_COLUMNS: tuple[str, ...] = (
    "candidate",
    "proposed",
    "skipped",
    "malformed",
    "schema_fail",
    "llm_calls",
    "mean_latency_s",
    "mean_resp_len",
)


def format_scorecard(scores: Sequence[CandidateScore]) -> str:
    """A Markdown comparison table — one row per candidate, the automatable
    columns only. **No fluency column** (decision 3): fluency is the human read of
    the recorded transcripts, surfaced for César, not scored here."""
    header = "| " + " | ".join(_SCORECARD_COLUMNS) + " |"
    sep = "| " + " | ".join("---" for _ in _SCORECARD_COLUMNS) + " |"
    rows = [header, sep]
    for s in scores:
        rows.append(
            "| "
            + " | ".join((
                s.candidate_name,
                str(s.proposed),
                str(s.skipped_total),
                str(s.malformed_skips),
                str(s.schema_skips),
                str(s.llm_calls),
                f"{s.mean_latency:.4f}",
                f"{s.mean_response_length:.1f}",
            ))
            + " |"
        )
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# CLI — thin wrapper (the A3b-run live invocation; never a pytest path)
# ---------------------------------------------------------------------------

def _load_stage_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.spike")
    sub = parser.add_subparsers(dest="cmd")

    run = sub.add_parser(
        "run", help="run the live model-choice spike and print the scorecard"
    )
    run.add_argument("--stage-json", required=True, help="pilot concept stage JSON")
    run.add_argument("--concept", required=True, help="pilot concept_key")
    run.add_argument(
        "--candidate", action="append", default=[],
        metavar="name:base_url:model[:API_KEY_ENV]",
        help="a candidate (repeatable); ≥2 for a comparison",
    )
    run.add_argument("--store-root", default=None)
    run.add_argument("--catalog-root", default=None)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument(
        "--replay", action="store_true",
        help="re-tally from existing per-candidate stores (no live call)",
    )

    args = parser.parse_args(argv)

    if args.cmd == "run":
        if not args.candidate:
            parser.error("at least one --candidate is required")
        stage_json = _load_stage_json(Path(args.stage_json))
        candidates = [CandidateSpec.parse(c) for c in args.candidate]
        store_root = Path(args.store_root) if args.store_root else None
        catalog_root = Path(args.catalog_root) if args.catalog_root else None
        scores = run_spike(
            stage_json, args.concept, candidates,
            store_root=store_root, catalog_root=catalog_root, seed=args.seed,
            replay=args.replay,
        )
        sys.stdout.write(format_scorecard(scores) + "\n")
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
