"""Markdown-tick reader for the menu-first review flow.

Sprint 38 (F3-prep-2-code-B). Translates César's ticked Markdown menu
files (``docs/synthetic/menus/{mtype}.md``, produced by
:mod:`menu_artefacts`) back into structured verdict JSONL under
``data/synthetic/menus/verdicts/{mtype}.jsonl`` for the Sprint 39 sampler
to consume.

Contract
--------

The **machine JSONL** (Sprint 37) is the source of truth for target
order, canonical text, candidate count, and candidate payloads. The
**Markdown** is the human input — it contributes *only* the tick state
per candidate. Any structural drift (heading count mismatch, canonical
string change, tick outside the candidate index range) is a fail-loud
:class:`ParseError`, never a silent verdict.

Approval rule (Sprint 38 non-negotiable): ``- [x]`` (case-insensitive)
approves. Everything else — untouched ``- [ ]``, deleted line, comment
above — rejects. There is no third state.

Does NOT own:

* editing the seam or the Sprint 37 modules;
* writing the Markdown menus (that's :mod:`menu_artefacts`);
* sampling — that's Sprint 39's ``sampler``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from utils import config

from . import menu_runner
from .taxonomy import ModificationType


__all__ = [
    "ParseError",
    "CandidateVerdict",
    "MenuVerdict",
    "ParseReport",
    "TypeParseStat",
    "parse_review_file",
    "parse_all",
    "write_verdicts",
    "read_verdicts",
    "format_parse_report",
    "main",
]


# ---------------------------------------------------------------------------
# Public exceptions + dataclasses
# ---------------------------------------------------------------------------


class ParseError(RuntimeError):
    """Structural mismatch between Markdown and its machine JSONL.

    Distinct + catchable so callers (e.g. an interactive review harness)
    can surface a corrective message rather than treat this as a review
    verdict.
    """


@dataclass(frozen=True)
class CandidateVerdict:
    """One candidate's tick state, joined with its Sprint 37 payload."""

    payload: dict
    approved: bool


@dataclass(frozen=True)
class MenuVerdict:
    """All ticks for one :class:`target_scanner.UniqueTarget`."""

    mtype: ModificationType
    dedup_key: tuple
    canonical: str
    candidates: tuple[CandidateVerdict, ...]
    # ``skipped_reason`` echoes the machine JSONL's ``skipped_reason`` if
    # the target was proposer-skipped (empty candidates, non-null reason).
    # Not review state — provenance carried over for the sampler.
    skipped_reason: Optional[str] = None


@dataclass(frozen=True)
class TypeParseStat:
    """One row of :class:`ParseReport`."""

    mtype: ModificationType
    n_targets: int
    n_targets_with_any_approval: int
    n_total_candidates: int
    n_approved_candidates: int


@dataclass(frozen=True)
class ParseReport:
    """Aggregate across every modification type parsed."""

    per_type: tuple[TypeParseStat, ...]


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------


_HEADING_RE = re.compile(r"^## (.+?)\s*$")
_TICK_RE = re.compile(r"^- \[([ xX])\] (\d+)\. ")


def _parse_markdown_sections(md_text: str) -> list[tuple[str, dict[int, bool]]]:
    """Return ``(canonical, {index: approved})`` in Markdown order.

    Silently ignores non-heading / non-tick lines (usage blurb, sibling
    line, blank spacers, skipped-reason italic). A tick appearing before
    the first ``##`` heading is ignored — the review file's title +
    front-matter block is expected there.
    """
    sections: list[tuple[str, dict[int, bool]]] = []
    canonical: Optional[str] = None
    tick_map: dict[int, bool] = {}
    for line in md_text.splitlines():
        heading = _HEADING_RE.match(line)
        if heading:
            if canonical is not None:
                sections.append((canonical, tick_map))
            canonical = heading.group(1).strip()
            tick_map = {}
            continue
        if canonical is None:
            continue
        tick = _TICK_RE.match(line)
        if tick:
            approved = tick.group(1).lower() == "x"
            idx = int(tick.group(2))
            tick_map[idx] = approved
    if canonical is not None:
        sections.append((canonical, tick_map))
    return sections


# ---------------------------------------------------------------------------
# Join Markdown ticks with machine JSONL
# ---------------------------------------------------------------------------


def parse_review_file(
    md_path: Path, jsonl_path: Path,
) -> tuple[MenuVerdict, ...]:
    """Read a ``(review.md, machine.jsonl)`` pair and produce a tuple of
    :class:`MenuVerdict` records — one per unique target.

    Fail-loud on: heading-count mismatch, canonical-string drift, or a
    tick at an out-of-range index. Missing ticks (unchecked ``[ ]``,
    absent line, section untouched) become ``approved=False`` — the
    reject-by-default contract.
    """
    md_text = md_path.read_text(encoding="utf-8")
    jsonl_records = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    sections = _parse_markdown_sections(md_text)
    if len(sections) != len(jsonl_records):
        raise ParseError(
            f"heading_count_mismatch: markdown={len(sections)} "
            f"jsonl={len(jsonl_records)} (file: {md_path.name})"
        )
    verdicts: list[MenuVerdict] = []
    for (canonical_md, tick_map), record in zip(sections, jsonl_records):
        canonical_jl = str(record["canonical"])
        if canonical_md != canonical_jl:
            raise ParseError(
                f"canonical_mismatch: markdown={canonical_md!r} "
                f"jsonl={canonical_jl!r} (file: {md_path.name})"
            )
        n_candidates = len(record["candidates"])
        extras = sorted(i for i in tick_map if not (1 <= i <= n_candidates))
        if extras:
            raise ParseError(
                f"tick_index_out_of_range: {extras} for {canonical_jl!r} "
                f"(n_candidates={n_candidates}, file: {md_path.name})"
            )
        verdicts.append(MenuVerdict(
            mtype=ModificationType(record["modification_type"]),
            dedup_key=_to_tuple(record["dedup_key"]),
            canonical=canonical_jl,
            candidates=tuple(
                CandidateVerdict(
                    payload=cand["payload"],
                    approved=bool(tick_map.get(i + 1, False)),
                )
                for i, cand in enumerate(record["candidates"])
            ),
            skipped_reason=record.get("skipped_reason") or None,
        ))
    return tuple(verdicts)


def _to_tuple(obj):
    """Round-trip helper: JSON round-trips tuples as lists; canonicalise."""
    if isinstance(obj, list):
        return tuple(_to_tuple(x) for x in obj)
    return obj


# ---------------------------------------------------------------------------
# Writing verdict JSONL
# ---------------------------------------------------------------------------


def write_verdicts(verdicts: Sequence[MenuVerdict], out_path: Path) -> None:
    """Atomic write of the verdict JSONL. One line per unique target.

    Line shape mirrors the input JSONL (Sprint 37) plus the per-candidate
    ``approved`` boolean, so downstream (Sprint 39 sampler) can consume
    either flavor without an extra join.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload_lines = []
    for v in verdicts:
        payload_lines.append(json.dumps({
            "modification_type": v.mtype.value,
            "dedup_key": list(v.dedup_key),
            "canonical": v.canonical,
            "candidates": [
                {"payload": c.payload, "approved": c.approved}
                for c in v.candidates
            ],
            "skipped_reason": v.skipped_reason,
        }, ensure_ascii=False, sort_keys=True))
    body = "\n".join(payload_lines) + ("\n" if payload_lines else "")
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8", newline="\n")
    os.replace(tmp, out_path)


def read_verdicts(path: Path) -> tuple[MenuVerdict, ...]:
    """Symmetric read for tests + downstream consumers."""
    out: list[MenuVerdict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out.append(MenuVerdict(
            mtype=ModificationType(record["modification_type"]),
            dedup_key=_to_tuple(record["dedup_key"]),
            canonical=str(record["canonical"]),
            candidates=tuple(
                CandidateVerdict(payload=c["payload"], approved=bool(c["approved"]))
                for c in record["candidates"]
            ),
            skipped_reason=record.get("skipped_reason") or None,
        ))
    return tuple(out)


# ---------------------------------------------------------------------------
# Directory sweep
# ---------------------------------------------------------------------------


def parse_all(
    machine_dir: Path,
    review_dir: Path,
    out_dir: Path,
) -> ParseReport:
    """For every ``machine_dir/{mtype}.jsonl`` with a matching
    ``review_dir/{mtype}.md``, parse and write
    ``out_dir/{mtype}.jsonl``.

    Missing pairs are silently skipped (a rewrite type may have zero
    unique targets on this chapter). A pair with the machine side present
    but the review side missing is treated as *unreviewed* → all
    candidates rejected (still emitted, so the sampler sees a consistent
    contract). Log-worthy but not fatal.
    """
    stats: list[TypeParseStat] = []
    for mtype in ModificationType:
        machine_path = machine_dir / f"{mtype.value}.jsonl"
        review_path = review_dir / f"{mtype.value}.md"
        if not machine_path.exists():
            continue
        if review_path.exists():
            verdicts = parse_review_file(review_path, machine_path)
        else:
            verdicts = _reject_all(machine_path, mtype)
        write_verdicts(verdicts, out_dir / f"{mtype.value}.jsonl")
        stats.append(_tally(mtype, verdicts))
    return ParseReport(per_type=tuple(stats))


def _reject_all(jsonl_path: Path, mtype: ModificationType) -> tuple[MenuVerdict, ...]:
    """Fallback when the reviewer never opened this rewrite type — build
    a verdict tuple with every candidate rejected. Never fabricates
    approvals."""
    out: list[MenuVerdict] = []
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        out.append(MenuVerdict(
            mtype=mtype,
            dedup_key=_to_tuple(record["dedup_key"]),
            canonical=str(record["canonical"]),
            candidates=tuple(
                CandidateVerdict(payload=c["payload"], approved=False)
                for c in record["candidates"]
            ),
            skipped_reason=record.get("skipped_reason") or None,
        ))
    return tuple(out)


def _tally(
    mtype: ModificationType, verdicts: Sequence[MenuVerdict],
) -> TypeParseStat:
    n_total = 0
    n_approved = 0
    n_targets_any = 0
    for v in verdicts:
        approved_here = sum(1 for c in v.candidates if c.approved)
        n_total += len(v.candidates)
        n_approved += approved_here
        if approved_here > 0:
            n_targets_any += 1
    return TypeParseStat(
        mtype=mtype,
        n_targets=len(verdicts),
        n_targets_with_any_approval=n_targets_any,
        n_total_candidates=n_total,
        n_approved_candidates=n_approved,
    )


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def format_parse_report(report: ParseReport) -> str:
    lines = [
        "### Menu-review parse — coverage summary",
        "",
        "| Rewrite type | Targets | Targets with ≥1 approval | Total candidates | Approved |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report.per_type:
        lines.append(
            f"| {row.mtype.value} | {row.n_targets} | "
            f"{row.n_targets_with_any_approval} | "
            f"{row.n_total_candidates} | {row.n_approved_candidates} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.menu_review_parser")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser(
        "parse",
        help="translate ticked Markdown menus into verdict JSONL",
    )
    p.add_argument(
        "--machine-dir",
        default=None,
        help=f"default: {menu_runner.default_out_machine_dir()}",
    )
    p.add_argument(
        "--review-dir",
        default=None,
        help=f"default: {menu_runner.default_out_review_dir()}",
    )
    p.add_argument(
        "--out-dir",
        default=None,
        help=f"default: {config.SYNTHETIC_DATA_ROOT / 'menus' / 'verdicts'}",
    )

    args = parser.parse_args(argv)
    if args.cmd != "parse":
        parser.print_usage(sys.stderr)
        return 2

    machine_dir = Path(args.machine_dir) if args.machine_dir else menu_runner.default_out_machine_dir()
    review_dir = Path(args.review_dir) if args.review_dir else menu_runner.default_out_review_dir()
    out_dir = Path(args.out_dir) if args.out_dir else config.SYNTHETIC_DATA_ROOT / "menus" / "verdicts"

    report = parse_all(machine_dir, review_dir, out_dir)
    sys.stdout.write(format_parse_report(report))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
