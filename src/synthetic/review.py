"""Phase E (Tasks E3 + E4): stratified validation sampler + reviewer harness.

Full manual review of every synthetic item is unrealistic at scale, so the
protocol's quality gate is **stratified sampling** (proposal Stage D,
`RESEARCH_PROTOCOL.md §5 E3–E4`):

* **E3 — the sampler** (`stratify` / `sample_review_queue`). Stratify the
  `SyntheticItem`s over `(concept_key × ModificationType)` cells, then surface a
  deterministic, seeded review queue hitting a per-cell coverage target — with
  **100 % coverage for `new_param`** (highest semantic-collision risk, proposal
  §4). The queue is de-duplicated by `item_key`: coverage is a per-cell property,
  reviewer effort is a per-item property, reconciled by drawing each item once.

* **E4 — the harness** (`Verdict` / `write_verdicts` / `agreement`). Capture per
  sampled item four verdicts — grammaticality, semantic preservation,
  `new_param` axis distinguishability, metadata accuracy — and, where ≥2
  reviewers score the same item, measure inter-annotator agreement
  (percent + Cohen's κ, hand-rolled stdlib).

This module is a **pure library + thin CLI**. It reviews off the per-item
`modifications` log + synthetic text (decision 5): no baseline re-expansion. It
imports `metadata`, `taxonomy`, `utils.config`, and stdlib only — never
`stage_b` / `run_synthetic` / `stage_runners`. Running a real review pass and
writing `QUALITY_REPORT.md` is F4; Parquet packaging is G1 — neither lives here.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from .metadata import SyntheticItem, join_intermediate
from .taxonomy import Modification, ModificationType
from utils import config

__all__ = [
    "ReviewTask",
    "CellCoverage",
    "CoverageReport",
    "Verdict",
    "AgreementStat",
    "ReviewError",
    "stratify",
    "sample_review_queue",
    "write_queue",
    "read_queue",
    "write_verdicts",
    "read_verdicts",
    "agreement",
    "main",
]

Cell = tuple[str, ModificationType]

_DIMENSIONS = (
    "grammatical",
    "semantic_preserved",
    "axis_distinguishable",
    "metadata_accurate",
)


class ReviewError(ValueError):
    """A review record is malformed or violates a uniqueness invariant.

    Distinct, catchable: raised for a duplicate `(item_key, reviewer)` verdict
    key and for malformed queue/verdict JSONL records.
    """


# --------------------------------------------------------------------------
# E3 — stratified sampler
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ReviewTask:
    """One queued item for a reviewer. `strata` lists every cell it belongs to."""

    item_key: str
    concept_key: str
    modification_types: tuple[ModificationType, ...]
    modification_count: int
    resumen: str
    texto: str
    modifications: tuple[Modification, ...]
    strata: tuple[Cell, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_key": self.item_key,
            "concept_key": self.concept_key,
            "modification_types": [t.value for t in self.modification_types],
            "modification_count": self.modification_count,
            "resumen": self.resumen,
            "texto": self.texto,
            "modifications": [m.to_dict() for m in self.modifications],
            "strata": [[c, t.value] for c, t in self.strata],
        }


@dataclass(frozen=True)
class CellCoverage:
    """Per-cell coverage accounting for one `(concept_key, ModificationType)`."""

    concept_key: str
    modification_type: ModificationType
    size: int
    sampled: int
    target: int
    fraction: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_key": self.concept_key,
            "modification_type": self.modification_type.value,
            "size": self.size,
            "sampled": self.sampled,
            "target": self.target,
            "fraction": self.fraction,
        }


@dataclass(frozen=True)
class CoverageReport:
    """Sampling report: per-cell coverage + total queued + total baselines."""

    cells: tuple[CellCoverage, ...]
    queued: int
    baselines: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cells": [c.to_dict() for c in self.cells],
            "queued": self.queued,
            "baselines": self.baselines,
        }


def _item_cells(item: SyntheticItem) -> list[Cell]:
    """The cells an item belongs to: one per *distinct* modification type."""
    seen: dict[ModificationType, None] = {}
    for t in item.modification_types:
        seen.setdefault(t, None)
    return [(item.concept_key, t) for t in seen]


def stratify(items: Iterable[SyntheticItem]) -> dict[Cell, list[SyntheticItem]]:
    """Group items into `(concept_key, ModificationType)` cells.

    Baselines (`modification_count == 0`) are excluded. A stacked item (several
    modification types) is a member of *each* of its types' cells.
    """
    cells: dict[Cell, list[SyntheticItem]] = {}
    for item in items:
        if item.modification_count == 0:
            continue
        for cell in _item_cells(item):
            cells.setdefault(cell, []).append(item)
    return cells


def sample_review_queue(
    items: Iterable[SyntheticItem],
    *,
    coverage: float = 0.10,
    floor: int = 5,
    full_coverage_types: frozenset[ModificationType] = frozenset(
        {ModificationType.NEW_PARAM}
    ),
    seed: int = 0,
) -> tuple[list[ReviewTask], CoverageReport]:
    """Deterministically sample a de-duplicated review queue + coverage report.

    Per cell: full-coverage types take the whole cell; otherwise
    `n = min(size, max(floor, ceil(coverage * size)))`. Selection is a seeded
    draw over the cell's sorted `item_key`s. The union of per-cell draws is
    de-duplicated by `item_key` (one `ReviewTask` per item, `strata` listing
    every cell it belongs to). Tasks are returned sorted by `item_key`.
    """
    items = list(items)
    baselines = sum(1 for it in items if it.modification_count == 0)
    cells = stratify(items)

    by_key: dict[str, SyntheticItem] = {}
    strata_by_key: dict[str, list[Cell]] = {}
    for cell, members in cells.items():
        for it in members:
            by_key.setdefault(it.item_key, it)
            strata_by_key.setdefault(it.item_key, [])
            if cell not in strata_by_key[it.item_key]:
                strata_by_key[it.item_key].append(cell)

    selected: set[str] = set()
    cell_reports: list[CellCoverage] = []
    for cell in sorted(cells, key=lambda c: (c[0], c[1].value)):
        concept, mtype = cell
        keys = sorted({it.item_key for it in cells[cell]})
        size = len(keys)
        if mtype in full_coverage_types:
            target = size
        else:
            target = min(size, max(floor, math.ceil(coverage * size)))
        rng = random.Random(f"{seed}\x00{concept}\x00{mtype.value}")
        chosen = rng.sample(keys, target) if target else []
        selected.update(chosen)
        cell_reports.append(
            CellCoverage(
                concept_key=concept,
                modification_type=mtype,
                size=size,
                sampled=target,
                target=target,
                fraction=(target / size) if size else 0.0,
            )
        )

    tasks: list[ReviewTask] = []
    for key in sorted(selected):
        it = by_key[key]
        strata = tuple(
            sorted(strata_by_key[key], key=lambda c: (c[0], c[1].value))
        )
        tasks.append(
            ReviewTask(
                item_key=it.item_key,
                concept_key=it.concept_key,
                modification_types=it.modification_types,
                modification_count=it.modification_count,
                resumen=it.resumen,
                texto=it.texto,
                modifications=it.modifications,
                strata=strata,
            )
        )

    report = CoverageReport(
        cells=tuple(cell_reports), queued=len(tasks), baselines=baselines
    )
    return tasks, report


def _task_from_dict(d: dict[str, Any]) -> ReviewTask:
    try:
        return ReviewTask(
            item_key=d["item_key"],
            concept_key=d["concept_key"],
            modification_types=tuple(
                ModificationType(t) for t in d["modification_types"]
            ),
            modification_count=d["modification_count"],
            resumen=d["resumen"],
            texto=d["texto"],
            modifications=tuple(Modification.from_dict(m) for m in d["modifications"]),
            strata=tuple((c, ModificationType(t)) for c, t in d["strata"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ReviewError(f"malformed review task record: {exc}") from exc


def _write_jsonl_atomic(rows: Iterable[dict[str, Any]], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ReviewError(f"malformed JSONL line: {exc}") from exc
    return out


def write_queue(tasks: Iterable[ReviewTask], path: Path) -> None:
    """Write the review queue as JSONL (atomic `.tmp` rename)."""
    _write_jsonl_atomic((t.to_dict() for t in tasks), Path(path))


def read_queue(path: Path) -> list[ReviewTask]:
    """Read a review queue back from JSONL."""
    return [_task_from_dict(d) for d in _read_jsonl(Path(path))]


# --------------------------------------------------------------------------
# E4 — reviewer harness
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Verdict:
    """One reviewer's four-dimension verdict on one sampled item.

    `axis_distinguishable` is `Optional[bool]` — `None` for non-`new_param`
    items, where the question does not apply.
    """

    item_key: str
    reviewer: str
    grammatical: bool
    semantic_preserved: bool
    axis_distinguishable: Optional[bool]
    metadata_accurate: bool
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_key": self.item_key,
            "reviewer": self.reviewer,
            "grammatical": self.grammatical,
            "semantic_preserved": self.semantic_preserved,
            "axis_distinguishable": self.axis_distinguishable,
            "metadata_accurate": self.metadata_accurate,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Verdict":
        try:
            return cls(
                item_key=d["item_key"],
                reviewer=d["reviewer"],
                grammatical=d["grammatical"],
                semantic_preserved=d["semantic_preserved"],
                axis_distinguishable=d["axis_distinguishable"],
                metadata_accurate=d["metadata_accurate"],
                notes=d.get("notes", ""),
            )
        except (KeyError, TypeError) as exc:
            raise ReviewError(f"malformed verdict record: {exc}") from exc


def _check_unique_keys(verdicts: Iterable[Verdict]) -> list[Verdict]:
    out: list[Verdict] = []
    seen: set[tuple[str, str]] = set()
    for v in verdicts:
        key = (v.item_key, v.reviewer)
        if key in seen:
            raise ReviewError(f"duplicate verdict key {key!r}")
        seen.add(key)
        out.append(v)
    return out


def write_verdicts(verdicts: Iterable[Verdict], path: Path) -> None:
    """Write verdicts as JSONL keyed by `(item_key, reviewer)`.

    A duplicate `(item_key, reviewer)` is fail-loud (`ReviewError`) — last-wins
    dedup is intentionally out of scope.
    """
    rows = _check_unique_keys(verdicts)
    _write_jsonl_atomic((v.to_dict() for v in rows), Path(path))


def read_verdicts(path: Path) -> list[Verdict]:
    """Read verdicts back from JSONL; duplicate keys are fail-loud."""
    verdicts = [Verdict.from_dict(d) for d in _read_jsonl(Path(path))]
    return _check_unique_keys(verdicts)


@dataclass(frozen=True)
class AgreementStat:
    """Inter-annotator agreement for one verdict dimension."""

    dimension: str
    n_items: int
    percent_agreement: float
    cohen_kappa: Optional[float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension": self.dimension,
            "n_items": self.n_items,
            "percent_agreement": self.percent_agreement,
            "cohen_kappa": self.cohen_kappa,
        }


def _dimension_pairs(verdicts: Sequence[Verdict], dim: str) -> list[tuple[bool, bool]]:
    """For each item with ≥2 reviewers scoring `dim`, the first two (sorted by
    reviewer) boolean labels. `None` values (axis on non-`new_param`) are skipped,
    so `axis_distinguishable` is measured only over the `new_param` subset."""
    by_item: dict[str, list[tuple[str, bool]]] = {}
    for v in verdicts:
        val = getattr(v, dim)
        if val is None:
            continue
        by_item.setdefault(v.item_key, []).append((v.reviewer, val))
    pairs: list[tuple[bool, bool]] = []
    for rated in by_item.values():
        if len(rated) < 2:
            continue
        rated.sort(key=lambda rv: rv[0])
        pairs.append((rated[0][1], rated[1][1]))
    return pairs


def _cohen_kappa(pairs: Sequence[tuple[bool, bool]]) -> Optional[float]:
    n = len(pairs)
    if n == 0:
        return None
    p_o = sum(1 for a, b in pairs if a == b) / n
    pa = sum(1 for a, _ in pairs if a) / n
    pb = sum(1 for _, b in pairs if b) / n
    p_e = pa * pb + (1 - pa) * (1 - pb)
    if 1 - p_e == 0:
        return None
    return (p_o - p_e) / (1 - p_e)


def agreement(verdicts: Iterable[Verdict]) -> dict[str, AgreementStat]:
    """Percent agreement + Cohen's κ per dimension, over ≥2-reviewer items only.

    `axis_distinguishable` is scored only over the `new_param` subset (items
    where it is non-`None`). κ is `None` when undefined (no ≥2-reviewer items, or
    a zero-expected-disagreement degenerate table).
    """
    verdicts = list(verdicts)
    out: dict[str, AgreementStat] = {}
    for dim in _DIMENSIONS:
        pairs = _dimension_pairs(verdicts, dim)
        n = len(pairs)
        percent = (sum(1 for a, b in pairs if a == b) / n) if n else 0.0
        out[dim] = AgreementStat(dim, n, percent, _cohen_kappa(pairs))
    return out


# --------------------------------------------------------------------------
# CLI — thin wrapper over the library
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.review")
    sub = parser.add_subparsers(dest="cmd")

    build = sub.add_parser("build", help="sample a review queue from joined items")
    build.add_argument("--out", default=None)
    build.add_argument("--intermediate-dir", default=None)
    build.add_argument("--coverage", type=float, default=0.10)
    build.add_argument("--floor", type=int, default=5)
    build.add_argument("--seed", type=int, default=0)

    agree = sub.add_parser("agree", help="report inter-annotator agreement")
    agree.add_argument("--verdicts", required=True)

    args = parser.parse_args(argv)

    if args.cmd == "build":
        idir = Path(args.intermediate_dir) if args.intermediate_dir else None
        items = join_intermediate(idir)
        tasks, report = sample_review_queue(
            items, coverage=args.coverage, floor=args.floor, seed=args.seed
        )
        out = Path(args.out) if args.out else config.SYNTHETIC_REVIEW_DIR / "queue.jsonl"
        write_queue(tasks, out)
        print(json.dumps(report.to_dict(), ensure_ascii=False))
        return 0

    if args.cmd == "agree":
        stats = agreement(read_verdicts(Path(args.verdicts)))
        print(json.dumps({k: v.to_dict() for k, v in stats.items()}, ensure_ascii=False))
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
