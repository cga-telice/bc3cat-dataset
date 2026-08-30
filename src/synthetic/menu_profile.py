"""Per-type mechanical scorecard over the menu JSONL artefacts.

Sprint 38.5. Read-only; answers "how many targets, how many were skipped,
how many candidates are no-ops or duplicates" per rewrite type so a
regeneration can be compared against its predecessor without reading
2 900 lines of Spanish. Complements :func:`menu_runner.format_scorecard`
(which reports the *run*) by reporting the *artefacts on disk*.

CLI::

    python -m synthetic.menu_profile [--menus-dir data/synthetic/menus]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from utils import config

_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _WS_RE.sub(" ", s).strip()


@dataclass(frozen=True)
class TypeProfile:
    mtype: str
    n_targets: int
    n_empty: int
    n_candidates: int
    # n_noop and n_dup are NOT mutually exclusive: a candidate that
    # normalises back to `original` can also be a repeat of an earlier
    # candidate on the same target, and is counted in both totals.
    n_noop: int          # candidate == original after accent/case/space normalisation
    # candidate == an earlier candidate on the same target, keyed on the
    # normalised candidate text alone (see _candidate_text). For new_param
    # (no `original`) this text is `new_axis_label`, so dedup is
    # label-level only — two candidates with the same label but different
    # `values` still count as one dup, since the value set is not part of
    # the key.
    n_dup: int
    # Mean of `len(seen)` over populated targets only (targets with zero
    # candidates are excluded from both the sum and the divisor, not
    # counted as 0) — see n_empty for the count of targets skipped here.
    uniq_per_target: float
    n_skipped: int
    n_dropped: int
    n_usages: int
    dist_orig: float     # mean (1 - token-Jaccard(new, original)) over candidates; 0.0 when no original
    pair_sim: float      # mean pairwise token-Jaccard among a target's candidates; averaged over populated targets


def _candidate_text(payload: dict) -> str:
    return str(payload.get("new") or payload.get("new_axis_label") or "")


def _tokens(s: str) -> frozenset[str]:
    return frozenset(_norm(s).split())


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def profile_file(path: Path) -> TypeProfile:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_empty = n_cand = n_noop = n_dup = n_skipped = n_dropped = n_usages = 0
    uniq_counts: list[int] = []
    dists: list[float] = []
    pair_sims: list[float] = []
    for r in rows:
        n_usages += len(r.get("usages") or [])
        if r.get("skipped_reason"):
            n_skipped += 1
        n_dropped += len(r.get("dropped_reasons") or [])
        cands = r.get("candidates") or []
        if not cands:
            n_empty += 1
            continue
        seen: set[str] = set()
        token_sets: list[frozenset[str]] = []
        for c in cands:
            p = c.get("payload", {})
            new = _norm(_candidate_text(p))
            orig = p.get("original")
            n_cand += 1
            if orig is not None and new == _norm(str(orig)):
                n_noop += 1
            if new in seen:
                n_dup += 1
            seen.add(new)
            token_sets.append(_tokens(_candidate_text(p)))
            if orig is not None:
                dists.append(1.0 - _jaccard(token_sets[-1], _tokens(str(orig))))
        uniq_counts.append(len(seen))
        if len(token_sets) >= 2:
            sims = [
                _jaccard(token_sets[i], token_sets[j])
                for i in range(len(token_sets)) for j in range(i + 1, len(token_sets))
            ]
            pair_sims.append(sum(sims) / len(sims))
    return TypeProfile(
        mtype=path.stem,
        n_targets=len(rows),
        n_empty=n_empty,
        n_candidates=n_cand,
        n_noop=n_noop,
        n_dup=n_dup,
        uniq_per_target=(sum(uniq_counts) / len(uniq_counts)) if uniq_counts else 0.0,
        n_skipped=n_skipped,
        n_dropped=n_dropped,
        n_usages=n_usages,
        dist_orig=(sum(dists) / len(dists)) if dists else 0.0,
        pair_sim=(sum(pair_sims) / len(pair_sims)) if pair_sims else 0.0,
    )


def profile_dir(menus_dir: Path) -> list[TypeProfile]:
    return [profile_file(p) for p in sorted(menus_dir.glob("*.jsonl"))]


def format_profile(rows: Sequence[TypeProfile]) -> str:
    head = (
        f"{'type':20s} {'tgt':>4s} {'empty':>5s} {'cands':>5s} {'noop':>4s} {'dup':>4s} "
        f"{'uniq/tgt':>8s} {'skip':>4s} {'drop':>4s} {'usages':>6s} {'d_orig':>6s} {'p_sim':>5s}"
    )
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r.mtype:20s} {r.n_targets:4d} {r.n_empty:5d} {r.n_candidates:5d} {r.n_noop:4d} "
            f"{r.n_dup:4d} {r.uniq_per_target:8.1f} {r.n_skipped:4d} {r.n_dropped:4d} {r.n_usages:6d}"
            f" {r.dist_orig:6.2f} {r.pair_sim:5.2f}"
        )
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    # Same path menu_runner.default_out_machine_dir() derives (config.SYNTHETIC_DATA_ROOT / "menus"),
    # reused directly here rather than via menu_runner to avoid pulling in its
    # LLM-client import chain — menu_runner's docstring asserts it is never
    # imported by a seam module, and this read-only profiler stays consistent
    # with that by importing the config constant instead of the module.
    parser = argparse.ArgumentParser(prog="synthetic.menu_profile")
    parser.add_argument("--menus-dir", default=str(config.SYNTHETIC_DATA_ROOT / "menus"))
    args = parser.parse_args(argv)
    sys.stdout.write(format_profile(profile_dir(Path(args.menus_dir))))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
