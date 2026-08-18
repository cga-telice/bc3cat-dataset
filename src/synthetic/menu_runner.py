"""Menu-builder CLI driver — the F3-prep-2-generate half.

Sprint 38 (F3-prep-2-code-A). A *consumer above the frozen seam* (sibling of
:mod:`spike` and :mod:`f1_pilot`) that composes the Sprint 37 menu builder
against a live LLM client and writes both artefacts to disk.

Public surface:

* :class:`MenuRun` — the automatable scorecard returned by :func:`run_menu`;
  per-modification-type counts (unique targets, LLM calls, generated targets,
  skipped targets, total surviving candidates, dropped-by-schema count) plus
  wall-clock.
* :func:`run_menu` — the composition: :func:`target_scanner.scan_chapter` →
  loop every :class:`ModificationType` calling
  :func:`menu_proposer.propose_type` → :func:`menu_artefacts.write_menu` →
  :class:`MenuRun`. Injectable ``client`` seam (:class:`llm_client.LLMClient`
  Protocol); the default is
  ``RecordingClient(HttpLLMClient(LLMConfig.from_env()), store)`` under a
  per-chapter-label store path.
* :func:`format_scorecard` — Markdown-table stringification of a
  :class:`MenuRun` for the :func:`RESEARCH_LOG.md` generation report.
* :func:`main` — ``run`` / ``replay`` subcommands; live is Sprint 38's
  F3-prep-2-generate CLI invocation; replay is offline and free.

Never imported by any seam module (asserted); the hermetic suite exercises
this driver end-to-end through a canned client, opening zero sockets.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from utils import config

from . import l2_repr, menu_artefacts, menu_proposer, target_scanner
from .llm_client import (
    HttpLLMClient,
    LLMConfig,
    RecordingClient,
    ReplayClient,
    prompt_hash,
)
from .taxonomy import ModificationType


__all__ = [
    "MenuRun",
    "TypeStat",
    "ResumingRecordingClient",
    "run_menu",
    "default_client",
    "default_store_dir",
    "default_out_machine_dir",
    "default_out_review_dir",
    "format_scorecard",
    "main",
]


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeStat:
    """Per-:class:`ModificationType` slice of :class:`MenuRun`."""

    mtype: ModificationType
    n_targets: int
    n_llm_calls: int
    n_generated_targets: int      # targets with ≥1 surviving candidate
    n_skipped_targets: int        # targets with reason set (malformed_list_after_retry, etc.)
    n_total_candidates: int       # sum of surviving candidates across targets
    n_dropped_candidates: int     # per-item schema failures across all targets


@dataclass(frozen=True)
class MenuRun:
    """Automatable scorecard for one :func:`run_menu` invocation."""

    chapter_label: str
    concept_count: int
    n_unique_targets_total: int
    n_llm_calls_total: int
    wall_clock_s: float
    per_type: tuple[TypeStat, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------


def default_store_dir(chapter_label: str) -> Path:
    """Recorded-transcript store for one chapter-label run."""
    return Path(config.LLM_CACHE_DIR) / f"menu_{chapter_label}"


def default_out_machine_dir() -> Path:
    return config.SYNTHETIC_DATA_ROOT / "menus"


def default_out_review_dir() -> Path:
    return config.REPO_ROOT / "docs" / "synthetic" / "menus"


# ---------------------------------------------------------------------------
# Client construction
# ---------------------------------------------------------------------------


def default_client(
    chapter_label: str,
    *,
    replay: bool = False,
    store_dir: Optional[Path] = None,
):
    """Live or replay client, wrapped for the F3-prep-2 discipline.

    * ``replay=False`` (default) → :class:`ResumingRecordingClient` around
      ``HttpLLMClient(LLMConfig.from_env())``. Every phi4 response is
      persisted into the content-addressed store, **and** any prompt whose
      hash is already in the store is served from disk without hitting the
      model. This makes a re-run after a transport error resume from the
      last successful prompt rather than redoing everything.
    * ``replay=True`` → ``ReplayClient(store_dir)``; unknown prompt → fail-loud.
    """
    store = store_dir if store_dir is not None else default_store_dir(chapter_label)
    if replay:
        return ReplayClient(store)
    return ResumingRecordingClient(
        HttpLLMClient(LLMConfig.from_env()),
        store_dir=store,
    )


class ResumingRecordingClient:
    """Cache-first wrapper around any :class:`llm_client.LLMClient`.

    Same on-disk format as :class:`llm_client.RecordingClient` (one
    ``{prompt_hash}.json`` file per prompt with ``{"prompt", "response"}``),
    so a store populated by either class is readable by the other and by
    :class:`llm_client.ReplayClient`. The only difference from
    ``RecordingClient`` is that ``complete()`` **checks the cache first** —
    a partial run that crashed mid-way resumes at the first uncached prompt
    instead of re-hitting the live model for every prompt.

    Lives in :mod:`menu_runner` rather than :mod:`llm_client` because
    Sprint 38's scope forbids editing seam modules; if this pattern turns
    out to be broadly useful, a later sprint can hoist it into
    ``llm_client``.
    """

    def __init__(self, inner, store_dir: Path):
        self._inner = inner
        self._store_dir = Path(store_dir)

    def complete(self, prompt: str) -> str:
        path = self._store_dir / f"{prompt_hash(prompt)}.json"
        if path.exists():
            record = json.loads(path.read_text(encoding="utf-8"))
            return record["response"]
        response = self._inner.complete(prompt)
        self._store_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"prompt": prompt, "response": response}, ensure_ascii=False),
            encoding="utf-8",
        )
        return response


# ---------------------------------------------------------------------------
# Counting client wrapper
# ---------------------------------------------------------------------------


class _CountingClient:
    """Wraps any :class:`LLMClient` and counts calls per interval.

    Exists only inside :func:`run_menu` so we can attribute LLM-call totals
    to the modification type that triggered them without changing the client
    interface. Not exported.
    """

    def __init__(self, inner):
        self._inner = inner
        self._count = 0

    def complete(self, prompt: str) -> str:
        self._count += 1
        return self._inner.complete(prompt)

    @property
    def count(self) -> int:
        return self._count

    def reset(self) -> None:
        self._count = 0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_menu(
    stage_json: dict,
    *,
    concept_filter=None,
    n: int = menu_proposer.DEFAULT_N_CANDIDATES,
    client,
    chapter_label: str,
    out_dir_machine: Optional[Path] = None,
    out_dir_review: Optional[Path] = None,
    clock=time.monotonic,
) -> MenuRun:
    """Compose the Sprint 37 menu builder against ``client``, write both
    artefacts to disk, return a :class:`MenuRun`.

    Parameters
    ----------
    stage_json
        Parsed stage-2 chapter JSON.
    concept_filter
        Optional predicate on the concept key (e.g.
        ``lambda k: k.startswith("OEB")``).
    n
        Candidates per unique target (default from
        :data:`menu_proposer.DEFAULT_N_CANDIDATES`).
    client
        A live, recording, or replay :class:`llm_client.LLMClient`. The
        driver never constructs one directly — pass
        :func:`default_client` for the standard live/replay wiring.
    chapter_label
        Short human-readable label for the run (e.g. ``"OEB"``); goes
        into the Markdown header and the default cache-store path.
    out_dir_machine, out_dir_review
        Override the default output paths. ``None`` → the defaults
        under ``data/synthetic/menus/`` and ``docs/synthetic/menus/``.
    clock
        Monotonic clock for wall-clock measurement; injectable for
        deterministic tests.
    """
    out_dir_machine = out_dir_machine or default_out_machine_dir()
    out_dir_review = out_dir_review or default_out_review_dir()

    t0 = clock()
    # Real stage-2 data mixes STR_formula, LIST_plain and LIST_conditional
    # text-variable shapes. `slot_extractor.extract_slots` (called inside
    # `menu_proposer.propose_type`) assumes strings — a bare list crashes with
    # `TypeError: expected string or bytes-like object, got 'list'`. Apply the
    # Sprint 26 adapter here so the downstream stack sees strings uniformly
    # (matches the `f1_pilot.py` pipeline discipline). `target_scanner` gets
    # `apply_l2_conversion=False` because the conversion already ran.
    stage_for_pipeline, _report = l2_repr.list_to_formula(
        stage_json, include_conditional=True,
    )
    inventory = target_scanner.scan_chapter(
        stage_for_pipeline,
        concept_filter=concept_filter,
        apply_l2_conversion=False,
    )
    counter = _CountingClient(client)

    per_type: list[TypeStat] = []
    sets_by_type: dict[ModificationType, dict] = {}
    for mtype in ModificationType:
        counter.reset()
        targets = inventory.by_type.get(mtype, ())
        if not targets:
            per_type.append(TypeStat(
                mtype=mtype,
                n_targets=0,
                n_llm_calls=0,
                n_generated_targets=0,
                n_skipped_targets=0,
                n_total_candidates=0,
                n_dropped_candidates=0,
            ))
            continue
        sets = menu_proposer.propose_type(
            stage_for_pipeline, inventory, mtype, counter, n=n,
        )
        sets_by_type[mtype] = sets
        per_type.append(_tally(mtype, targets, sets, counter.count))

    menu_artefacts.write_menu(
        inventory,
        sets_by_type,
        machine_dir=out_dir_machine,
        review_dir=out_dir_review,
        chapter_label=chapter_label,
    )

    wall = clock() - t0
    total_targets = sum(s.n_targets for s in per_type)
    total_calls = sum(s.n_llm_calls for s in per_type)
    return MenuRun(
        chapter_label=chapter_label,
        concept_count=len(inventory.concept_keys),
        n_unique_targets_total=total_targets,
        n_llm_calls_total=total_calls,
        wall_clock_s=wall,
        per_type=tuple(per_type),
    )


def _tally(
    mtype: ModificationType,
    targets,
    sets: dict,
    llm_calls: int,
) -> TypeStat:
    """One :class:`TypeStat` row from the per-type ``CandidateSet`` map."""
    n_generated = 0
    n_skipped = 0
    n_total_candidates = 0
    n_dropped = 0
    for target in targets:
        set_ = sets.get(target.dedup_key)
        if set_ is None:
            n_skipped += 1
            continue
        n_dropped += len(set_.dropped_reasons)
        if set_.reason is not None:
            n_skipped += 1
        elif set_.candidates:
            n_generated += 1
            n_total_candidates += len(set_.candidates)
        else:
            # No reason but empty candidates — count as skipped.
            n_skipped += 1
    return TypeStat(
        mtype=mtype,
        n_targets=len(targets),
        n_llm_calls=llm_calls,
        n_generated_targets=n_generated,
        n_skipped_targets=n_skipped,
        n_total_candidates=n_total_candidates,
        n_dropped_candidates=n_dropped,
    )


# ---------------------------------------------------------------------------
# Scorecard formatting
# ---------------------------------------------------------------------------


def format_scorecard(run: MenuRun) -> str:
    """Markdown-table stringification suitable for a `RESEARCH_LOG.md`
    generation report.
    """
    lines = [
        f"### Menu-builder scorecard — {run.chapter_label}",
        "",
        f"Concepts: **{run.concept_count}**  ·  "
        f"Unique targets: **{run.n_unique_targets_total}**  ·  "
        f"LLM calls: **{run.n_llm_calls_total}**  ·  "
        f"Wall clock: **{run.wall_clock_s:.1f} s**",
        "",
        "| Rewrite type | Targets | LLM calls | Generated | Skipped | Total candidates | Dropped |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in run.per_type:
        lines.append(
            f"| {row.mtype.value} | {row.n_targets} | {row.n_llm_calls} | "
            f"{row.n_generated_targets} | {row.n_skipped_targets} | "
            f"{row.n_total_candidates} | {row.n_dropped_candidates} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI — thin wrapper (F3-prep-2-generate)
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.menu_runner")
    sub = parser.add_subparsers(dest="cmd")

    for cmd, helptext in (
        ("run", "live menu build against the configured LLM"),
        ("replay", "offline re-run from the recorded transcript store"),
    ):
        p = sub.add_parser(cmd, help=helptext)
        p.add_argument("--stage-json", required=True)
        p.add_argument(
            "--concept-filter",
            default=None,
            help='Prefix filter on concept keys (e.g. "OEB"). Default: no filter.',
        )
        p.add_argument("--n", type=int, default=menu_proposer.DEFAULT_N_CANDIDATES)
        p.add_argument(
            "--chapter-label",
            required=True,
            help="Short label used in Markdown headers and the cache path.",
        )
        p.add_argument("--seed", type=int, default=0, help="Reserved (kept for CLI symmetry with f1_pilot).")
        p.add_argument("--out-machine", default=None)
        p.add_argument("--out-review", default=None)
        p.add_argument("--llm-cache", default=None)

    args = parser.parse_args(argv)
    if args.cmd not in ("run", "replay"):
        parser.print_usage(sys.stderr)
        return 2

    stage = json.loads(Path(args.stage_json).read_text(encoding="utf-8"))
    concept_filter = (
        (lambda k, p=args.concept_filter: k.startswith(p))
        if args.concept_filter is not None
        else None
    )
    store = Path(args.llm_cache) if args.llm_cache else default_store_dir(args.chapter_label)
    client = default_client(
        args.chapter_label, replay=(args.cmd == "replay"), store_dir=store,
    )
    run = run_menu(
        stage,
        concept_filter=concept_filter,
        n=args.n,
        client=client,
        chapter_label=args.chapter_label,
        out_dir_machine=Path(args.out_machine) if args.out_machine else None,
        out_dir_review=Path(args.out_review) if args.out_review else None,
    )
    sys.stdout.write(format_scorecard(run))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
