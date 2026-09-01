"""The approved-rewrite pantry for the Sprint 39 corpus sampler.

Joins ``data/synthetic/menus/{tipo}.jsonl`` (payloads + usages) with
``data/synthetic/menus/verdicts/{tipo}.jsonl`` (approved flags, produced by
``menu_review_parser`` from the reviewed ticks) into per-type tuples of
:class:`ApprovedRewrite`, plus an applicability index per concept.

Sprint 39 design (SPRINT_39_DESIGN.md): ``omission`` and ``new_param`` are
excluded — the benchmark keeps only information-preserving rewrites.
Read-only; fails loud on any misalignment between the two files.

.. note::
   The menus JSONL serializer (:func:`menu_artefacts._write_machine`) writes
   only ``concept_key`` and ``display`` per usage — the in-memory
   ``TargetUsage.slot_extractor_target_id`` was dropped at serialization
   time. :class:`Usage` keeps the attribute (``None`` when absent, as in the
   real Sprint 38 files) so downstream consumers that re-derive the target id
   via :mod:`target_scanner` can fill it in; ``display`` is carried as the
   per-usage datum actually present on disk.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils import config
from .taxonomy import ModificationType

EXCLUDED_TYPES = frozenset({ModificationType.OMISSION, ModificationType.NEW_PARAM})


@dataclass(frozen=True)
class Usage:
    concept_key: str
    slot_extractor_target_id: object
    display: Optional[str] = None


@dataclass(frozen=True)
class ApprovedRewrite:
    mtype: ModificationType
    dedup_key: tuple
    canonical: str
    candidate_index: int
    payload: dict
    usages: tuple[Usage, ...]

    @property
    def uid(self) -> str:
        """Stable id for reuse-cap accounting and provenance."""
        return f"{self.mtype.value}:{self.canonical}:{self.candidate_index}"


@dataclass(frozen=True)
class Pantry:
    by_type: dict[ModificationType, tuple[ApprovedRewrite, ...]]

    def for_concept(self, concept_key: str) -> dict[ModificationType, tuple[ApprovedRewrite, ...]]:
        out: dict[ModificationType, tuple[ApprovedRewrite, ...]] = {}
        for mtype, rewrites in self.by_type.items():
            hits = tuple(r for r in rewrites
                         if any(u.concept_key == concept_key for u in r.usages))
            if hits:
                out[mtype] = hits
        return out


def load_pantry(menus_dir: Optional[Path] = None) -> Pantry:
    menus_dir = Path(menus_dir) if menus_dir else config.SYNTHETIC_DATA_ROOT / "menus"
    verdicts_dir = menus_dir / "verdicts"
    by_type: dict[ModificationType, list[ApprovedRewrite]] = {}
    for vfile in sorted(verdicts_dir.glob("*.jsonl")):
        mtype = ModificationType(vfile.stem)
        if mtype in EXCLUDED_TYPES:
            continue
        menu_rows = [json.loads(l) for l in (menus_dir / vfile.name).read_text(encoding="utf-8").splitlines()]
        verd_rows = [json.loads(l) for l in vfile.read_text(encoding="utf-8").splitlines()]
        if len(menu_rows) != len(verd_rows):
            raise ValueError(f"pantry_misaligned: {vfile.name} rows {len(verd_rows)} != menu {len(menu_rows)}")
        for menu_row, verd_row in zip(menu_rows, verd_rows):
            if len(menu_row["candidates"]) != len(verd_row["candidates"]):
                raise ValueError(
                    f"pantry_misaligned: {vfile.name} target {menu_row['canonical']!r} "
                    f"candidates {len(verd_row['candidates'])} != menu {len(menu_row['candidates'])}"
                )
            usages = tuple(Usage(u["concept_key"], u.get("slot_extractor_target_id"),
                                 u.get("display"))
                           for u in menu_row.get("usages", []))
            for ci, (mc, vc) in enumerate(zip(menu_row["candidates"], verd_row["candidates"])):
                if not vc.get("approved"):
                    continue
                by_type.setdefault(mtype, []).append(ApprovedRewrite(
                    mtype=mtype, dedup_key=tuple(menu_row["dedup_key"]),
                    canonical=menu_row["canonical"], candidate_index=ci,
                    payload=dict(mc["payload"]), usages=usages,
                ))
    return Pantry(by_type={t: tuple(v) for t, v in by_type.items()})
