"""Menu artefact writer — machine JSONL + human-review Markdown.

Sprint 37 (F3-prep-1-C). Consumes the ``{dedup_key: CandidateSet}`` maps
produced by :mod:`menu_proposer` and emits **two parallel files per
modification type**, each atomically written:

* ``data/synthetic/menus/{mtype}.jsonl`` — one JSON line per unique
  target, carrying every candidate with an ``approved: null`` slot for
  Sprint 38's review parser to flip to ``true`` / ``false``. This is
  what the sampler will consume in Sprint 39.
* ``docs/synthetic/menus/{mtype}.md`` — one section per unique target,
  each candidate rendered as a Markdown checkbox line. The reviewer
  ticks what they accept, saves the file, and Sprint 38's parser reads
  the state back.

Design invariants (all pinned by tests):

* **Deterministic ordering.** Targets are emitted in
  ``UniqueTarget.dedup_key`` order; candidates keep the LLM's
  quality-ranked order (best first). Same input → byte-identical
  output.
* **Skimmable Markdown.** Fixed template: one ``##`` heading per target,
  a ``_Used in N concepts_`` line, an optional sibling-values line
  (L1 only), and up to *n* ``- [ ] i. <candidate>`` lines. If a
  target was fully skipped, the section shows ``_Skipped: <reason>_``
  instead of checkboxes so the reviewer sees the gap.
* **Atomic write.** ``.tmp`` file + ``os.replace``. Never leaves a
  half-written file on disk if a write raises.

Does NOT own:

* the candidate-generation step — that's :mod:`menu_proposer`;
* parsing the reviewer's ticks back into structured verdicts — that's
  Sprint 38's ``menu_review_parser`` (TBD);
* sampling the final variant catalog — that's Sprint 39's sampler.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from .menu_proposer import CandidateSet
from .target_scanner import ChapterInventory, UniqueTarget
from .taxonomy import ModificationType


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WriteReport:
    """One entry per modification type actually written. Returned by
    :func:`write_menu` so the caller can log a scorecard."""

    mtype: ModificationType
    machine_path: Path
    review_path: Path
    n_targets: int
    n_candidates_total: int
    n_skipped_targets: int


def write_menu(
    inventory: ChapterInventory,
    sets_by_type: Mapping[ModificationType, Mapping[tuple, CandidateSet]],
    *,
    machine_dir: Path,
    review_dir: Path,
    chapter_label: str = "menu",
) -> tuple[WriteReport, ...]:
    """Write both artefacts for every modification type that has
    populated :class:`CandidateSet`\\ s.

    Parameters
    ----------
    inventory
        The chapter scan (only used for target ordering + the header
        line that names how many concepts were covered).
    sets_by_type
        Mapping ``{ModificationType: {dedup_key: CandidateSet}}`` —
        typically the concatenation of successive
        :func:`menu_proposer.propose_type` calls.
    machine_dir
        Directory for the ``.jsonl`` files (created if missing).
    review_dir
        Directory for the ``.md`` files (created if missing).
    chapter_label
        Short label used in the Markdown header (e.g. ``"OEB subset"``).

    Returns
    -------
    tuple[WriteReport, ...]
        One entry per modification type written; ordered by
        :class:`ModificationType` enum order.
    """
    machine_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)
    reports: list[WriteReport] = []
    for mtype in ModificationType:
        sets_for_type = sets_by_type.get(mtype)
        if not sets_for_type:
            continue
        targets = inventory.by_type.get(mtype, ())
        if not targets:
            continue
        machine_path = machine_dir / f"{mtype.value}.jsonl"
        review_path = review_dir / f"{mtype.value}.md"
        n_candidates_total, n_skipped_targets = _write_machine(
            machine_path, targets, sets_for_type, mtype,
        )
        _write_review(
            review_path, targets, sets_for_type, mtype,
            chapter_label=chapter_label,
            concept_count=len(inventory.concept_keys),
        )
        reports.append(WriteReport(
            mtype=mtype,
            machine_path=machine_path,
            review_path=review_path,
            n_targets=len(targets),
            n_candidates_total=n_candidates_total,
            n_skipped_targets=n_skipped_targets,
        ))
    return tuple(reports)


# ---------------------------------------------------------------------------
# Machine-readable JSONL
# ---------------------------------------------------------------------------


def _write_machine(
    path: Path,
    targets: Iterable[UniqueTarget],
    sets: Mapping[tuple, CandidateSet],
    mtype: ModificationType,
) -> tuple[int, int]:
    """One JSON line per unique target — ordered by
    :attr:`UniqueTarget.dedup_key`.

    Line shape::

        {
          "modification_type": "synonym_label",
          "dedup_key": ["TRABAJO", "Diurno"],
          "canonical": "TRABAJO / Diurno",
          "usages": [
            {"concept_key": "OEB010$", "display": "TRABAJO / Diurno"},
            ...
          ],
          "candidates": [
            {"payload": {"original": "Diurno", "new": "Turno diurno"},
             "approved": null},
            ...
          ],
          "skipped_reason": null,
          "dropped_reasons": []
        }
    """
    n_candidates_total = 0
    n_skipped_targets = 0
    lines: list[str] = []
    for target in targets:
        set_ = sets.get(target.dedup_key)
        candidates_json: list[dict] = []
        if set_ is not None:
            for cp in set_.candidates:
                candidates_json.append({
                    "payload": cp.payload,
                    "approved": None,
                })
            n_candidates_total += len(set_.candidates)
            if set_.reason is not None:
                n_skipped_targets += 1
        else:
            n_skipped_targets += 1
        line = {
            "modification_type": mtype.value,
            "dedup_key": list(target.dedup_key),
            "canonical": target.canonical,
            "usages": [
                {"concept_key": u.concept_key, "display": u.display}
                for u in target.usages
            ],
            "candidates": candidates_json,
            "skipped_reason": set_.reason if set_ is not None else "not_proposed",
            "dropped_reasons": list(set_.dropped_reasons) if set_ is not None else [],
        }
        lines.append(json.dumps(line, ensure_ascii=False, sort_keys=True))
    payload = "\n".join(lines) + ("\n" if lines else "")
    _atomic_write(path, payload)
    return n_candidates_total, n_skipped_targets


# ---------------------------------------------------------------------------
# Human-review Markdown
# ---------------------------------------------------------------------------


_MARKDOWN_HEADER = (
    "# {mtype} — {chapter_label}\n\n"
    "_{n_targets} unique target(s) across {concept_count} concept(s). "
    "Tick candidates you approve; leave unticked or delete to reject. "
    "Save the file — the Sprint 38 parser reads the ticks back._\n\n"
)


def _write_review(
    path: Path,
    targets: Iterable[UniqueTarget],
    sets: Mapping[tuple, CandidateSet],
    mtype: ModificationType,
    *,
    chapter_label: str,
    concept_count: int,
) -> None:
    """One ``##`` section per unique target, followed by a list of
    ``- [ ] i. <candidate>`` lines. Fixed template so byte-identical
    diffs make reviewer edits obvious in git.
    """
    targets = list(targets)
    body = [
        _MARKDOWN_HEADER.format(
            mtype=mtype.value,
            chapter_label=chapter_label,
            n_targets=len(targets),
            concept_count=concept_count,
        )
    ]
    for target in targets:
        body.append(_render_target_section(target, sets.get(target.dedup_key), mtype))
    _atomic_write(path, "".join(body))


def _render_target_section(
    target: UniqueTarget,
    set_: CandidateSet | None,
    mtype: ModificationType,
) -> str:
    lines: list[str] = []
    lines.append(f"## {target.canonical}\n")
    usages_display = ", ".join(u.concept_key for u in target.usages)
    lines.append(f"_Used in {len(target.usages)} concept(s): {usages_display}_\n")
    if set_ is None:
        lines.append("_Not proposed._\n\n")
        return "".join(lines)
    if set_.reason is not None:
        lines.append(f"_Skipped: {set_.reason}_\n\n")
        return "".join(lines)
    if not set_.candidates:
        lines.append("_No candidates survived validation._\n")
        for drop in set_.dropped_reasons:
            lines.append(f"- ~~{_escape_md(drop)}~~ (dropped)\n")
        lines.append("\n")
        return "".join(lines)
    lines.append("\n")
    for i, cp in enumerate(set_.candidates, start=1):
        text = _render_candidate_line(cp.payload, mtype)
        lines.append(f"- [ ] {i}. {text}\n")
    if set_.dropped_reasons:
        lines.append("\n_Dropped by schema validation (not reviewable):_\n")
        for drop in set_.dropped_reasons:
            lines.append(f"- {_escape_md(drop)}\n")
    lines.append("\n")
    return "".join(lines)


def _render_candidate_line(payload: dict, mtype: ModificationType) -> str:
    """The one line the reviewer actually reads per candidate. Format
    is per-family; kept short so the Markdown stays skimmable."""
    if mtype in _L1_TYPES:
        return _escape_md(str(payload.get("new", "")))
    if mtype is ModificationType.OMISSION:
        return f'"{_escape_md(str(payload.get("new", "")))}"'
    if mtype in _L2_TYPES or mtype in (
        ModificationType.REORDER,
        ModificationType.TEMPLATE_PARAPHRASE,
    ):
        return f'"{_escape_md(str(payload.get("new", "")))}"'
    if mtype is ModificationType.NEW_PARAM:
        label = payload.get("new_axis_label", "?")
        vals = payload.get("values", [])
        val_display = ", ".join(
            _escape_md(str(v.get("value", ""))) for v in vals if isinstance(v, dict)
        )
        return f"axis `{_escape_md(str(label))}` → {{{val_display}}}"
    return _escape_md(json.dumps(payload, ensure_ascii=False, sort_keys=True))


_L1_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})
_L2_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})


def _escape_md(text: str) -> str:
    """Minimal Markdown-safe rendering: strip control chars and collapse
    line breaks. The reviewer sees the LLM's exact wording otherwise."""
    return text.replace("\r", "").replace("\n", " ").strip()


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically. Uses a sibling ``.tmp``
    file + :func:`os.replace` so a raised exception never leaves a
    half-written file behind."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    os.replace(tmp, path)
