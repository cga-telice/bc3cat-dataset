"""F1 single-concept pilot harness (Sprint 27, Phase F Task F1-build).

The runnable harness for the F1 pilot: it composes the **unedited** frozen stack
(`run_synthetic.run_concept` -> `stage_b.materialize_catalog_entry` ->
`metadata.join_intermediate` -> `review.sample_review_queue`) over **one** concept
across all generation conditions, with the Sprint-26 L2 representation adapter
(`l2_repr`) bracketing the mutation, and returns an automatable scorecard.

Like `spike.py`, this is a *consumer above the orchestrator*: it imports the seam
modules and composes their public surface; nothing in the seam imports it.

The two-mode `l2_repr` flow (see `l2_repr` docstring) is wired here:

  enum = list_to_formula(concept, include_conditional=True)   # Stage-A: enumerate
  entry = run_concept(enum, ...)                               # propose/emit rules
  appl = list_to_formula(concept, include_conditional=False)  # Stage-B: apply
  materialize_catalog_entry(appl, entry, pre_rerun=formula_to_list)   # restore + rerun

The live LLM round-trip goes through a `RecordingClient` so the run is reproducible
and free to replay offline (`replay=True` re-reads the recorded store). The
generated Spanish's fluency is **not** scored here — that is the F1-run manual
review (Sprint 28). This module measures only the mechanical scorecard.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from . import l2_repr
from .llm_client import HttpLLMClient, LLMConfig, RecordingClient, ReplayClient
from .metadata import join_intermediate, validate_items
from .review import sample_review_queue, write_queue
from .run_synthetic import CONDITION_SPECS, run_concept
from .stage_b import materialize_catalog_entry
from utils import config

__all__ = [
    "MALFORMED_SKIP_PREFIX",
    "SCHEMA_SKIP_PREFIX",
    "PilotScore",
    "default_conditions",
    "load_pilot_concept",
    "run_pilot",
    "format_scorecard",
    "main",
]

# Skip-reason prefixes owned by the frozen C2/C3 seam (mirrors spike.py).
MALFORMED_SKIP_PREFIX = "malformed_llm_response_after_retry:"
SCHEMA_SKIP_PREFIX = "schema_validation_failed:"


def default_conditions() -> tuple[str, ...]:
    """All generation conditions (the 12 single-type + the stacked/mix), sorted
    for a deterministic plan."""
    return tuple(sorted(CONDITION_SPECS))


@dataclass(frozen=True)
class PilotScore:
    """Automatable per-pilot scorecard. No fluency field — that is F1-run review."""

    concept_key: str
    conditions: int
    variants_generated: int
    variants_skipped: int
    malformed_skips: int
    schema_skips: int
    l2_targets: int
    materialized_items: int
    reviewable_items: int
    queue_size: int
    coverage_fraction: float

    def to_dict(self) -> dict:
        return {
            "concept_key": self.concept_key,
            "conditions": self.conditions,
            "variants_generated": self.variants_generated,
            "variants_skipped": self.variants_skipped,
            "malformed_skips": self.malformed_skips,
            "schema_skips": self.schema_skips,
            "l2_targets": self.l2_targets,
            "materialized_items": self.materialized_items,
            "reviewable_items": self.reviewable_items,
            "queue_size": self.queue_size,
            "coverage_fraction": self.coverage_fraction,
        }


def load_pilot_concept(stage_json: dict, concept_key: str) -> dict:
    """Slice one concept out of a stage JSON into a single-concept stage_json."""
    if concept_key not in stage_json:
        raise KeyError(f"concept_key {concept_key!r} not in stage JSON")
    return {concept_key: stage_json[concept_key]}


def run_pilot(
    concept: dict,
    concept_key: str,
    *,
    client=None,
    conditions: Optional[Sequence[str]] = None,
    store_root: Optional[Path] = None,
    variants_dir: Optional[Path] = None,
    intermediate_dir: Optional[Path] = None,
    review_dir: Optional[Path] = None,
    seed: int = 0,
    coverage: float = 1.0,
    replay: bool = False,
) -> PilotScore:
    """Run the single-concept pilot end to end and return the mechanical scorecard.

    `concept` is a single-concept stage_json (`{concept_key: item}`). `client` is
    the live `LLMClient` (default `HttpLLMClient(LLMConfig.from_env())`, i.e.
    `llama3.1:8b` via Ollama); it is wrapped in a `RecordingClient`. `replay=True`
    serves from the recorded store instead, with no live call.
    """
    conditions = tuple(conditions) if conditions is not None else default_conditions()
    store_root = Path(store_root) if store_root is not None else Path(config.LLM_CACHE_DIR)
    variants_dir = Path(variants_dir) if variants_dir is not None else Path(config.SYNTHETIC_VARIANTS_DIR)
    intermediate_dir = (
        Path(intermediate_dir) if intermediate_dir is not None
        else Path(config.SYNTHETIC_INTERMEDIATE_DIR)
    )
    review_dir = Path(review_dir) if review_dir is not None else Path(config.SYNTHETIC_REVIEW_DIR)
    store_dir = store_root / concept_key

    # Guard: L2 must be enumerable on this concept (loud warning if it silently isn't).
    l2_targets = l2_repr.assert_l2_targets_or_warn(concept)

    # Stage A — enumerate/propose/emit on the all-formula (enumerable) view.
    enum, _enum_report = l2_repr.list_to_formula(concept, include_conditional=True)
    if replay:
        proposer = ReplayClient(store_dir)
    else:
        inner = client if client is not None else HttpLLMClient(LLMConfig.from_env())
        proposer = RecordingClient(inner, store_dir)
    entry, _ = run_concept(
        enum, concept_key, conditions, proposer, out_dir=variants_dir, seed=seed,
    )

    # Stage B — apply on the native-shape (apply-mode) view, restore before rerun.
    appl, _appl_report = l2_repr.list_to_formula(concept, include_conditional=False)
    materialize_catalog_entry(
        appl, entry, out_dir=intermediate_dir, pre_rerun=l2_repr.formula_to_list,
    )

    # Metadata join + 100 %-coverage review queue (scoped to this concept).
    items = [
        it for it in join_intermediate(intermediate_dir) if it.concept_key == concept_key
    ]
    validate_items(items)
    tasks, _report = sample_review_queue(items, coverage=coverage)
    review_dir.mkdir(parents=True, exist_ok=True)
    write_queue(tasks, review_dir / f"{concept_key}_review_queue.jsonl")

    # Reviewable items carry >=1 applied modification; 0-mod baselines (e.g. a
    # variant whose rules all skipped at Stage-B apply) are correctly excluded
    # from review, so coverage is measured against the reviewable subset.
    reviewable = sum(1 for it in items if it.modification_count > 0)
    return _score(
        concept_key, conditions, entry, l2_targets, len(items), reviewable, len(tasks),
    )


def _score(concept_key, conditions, entry, l2_targets, n_items, reviewable, queue_size) -> PilotScore:
    malformed = sum(
        1 for m in entry.skipped if (m.reason or "").startswith(MALFORMED_SKIP_PREFIX)
    )
    schema = sum(
        1 for m in entry.skipped if (m.reason or "").startswith(SCHEMA_SKIP_PREFIX)
    )
    return PilotScore(
        concept_key=concept_key,
        conditions=len(conditions),
        variants_generated=len(entry.variants),
        variants_skipped=len(entry.skipped),
        malformed_skips=malformed,
        schema_skips=schema,
        l2_targets=l2_targets,
        materialized_items=n_items,
        reviewable_items=reviewable,
        queue_size=queue_size,
        coverage_fraction=(queue_size / reviewable) if reviewable else 0.0,
    )


_SCORECARD_FIELDS: tuple[tuple[str, str], ...] = (
    ("concept_key", "concept_key"),
    ("conditions", "conditions"),
    ("variants_generated", "generated"),
    ("variants_skipped", "skipped"),
    ("malformed_skips", "malformed"),
    ("schema_skips", "schema_fail"),
    ("l2_targets", "l2_targets"),
    ("materialized_items", "items"),
    ("reviewable_items", "reviewable"),
    ("queue_size", "queue"),
    ("coverage_fraction", "coverage"),
)


def format_scorecard(score: PilotScore) -> str:
    d = score.to_dict()
    rows = [f"{label:18s}: {d[key]}" for key, label in _SCORECARD_FIELDS]
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# CLI — thin wrapper (the F1-run live invocation; never a pytest path)
# ---------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.f1_pilot")
    sub = parser.add_subparsers(dest="cmd")

    for name, helptext in (("run", "live pilot run"), ("replay", "offline re-run from the recorded store")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--stage-json", required=True)
        p.add_argument("--concept", required=True)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--store-root", default=None)
        p.add_argument("--variants-dir", default=None)
        p.add_argument("--intermediate-dir", default=None)
        p.add_argument("--review-dir", default=None)

    args = parser.parse_args(argv)
    if args.cmd in ("run", "replay"):
        stage_json = json.loads(Path(args.stage_json).read_text(encoding="utf-8"))
        concept = load_pilot_concept(stage_json, args.concept)
        score = run_pilot(
            concept, args.concept,
            store_root=Path(args.store_root) if args.store_root else None,
            variants_dir=Path(args.variants_dir) if args.variants_dir else None,
            intermediate_dir=Path(args.intermediate_dir) if args.intermediate_dir else None,
            review_dir=Path(args.review_dir) if args.review_dir else None,
            seed=args.seed,
            replay=(args.cmd == "replay"),
        )
        sys.stdout.write(format_scorecard(score) + "\n")
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
