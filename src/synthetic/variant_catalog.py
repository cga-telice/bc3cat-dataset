"""Variant catalog writer (Phase C Task C4).

JSON-per-concept artefacts under `data/synthetic/variants/`. Every
emitted variant carries its full audit trail: the rule(s) that landed,
the `Modification`s that skipped, the LLM provenance per attempt.

Atomic write: `.tmp` rename. Round-trip-safe: `read_catalog_entry`
reverses `write_catalog_entry` exactly (modulo the unordered-dict
caveats `json` already imposes).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .taxonomy import Modification, ModificationType


@dataclass(frozen=True)
class ProvenanceRecord:
    modification_type: ModificationType
    rendered_prompt: str
    raw_responses: tuple[str, ...]
    validated_payload: Optional[dict]
    skipped: Optional[Modification]


@dataclass(frozen=True)
class VariantRecord:
    condition: str
    modification_type: ModificationType
    target_id_repr: str
    rules: tuple[dict, ...]


@dataclass(frozen=True)
class VariantCatalogEntry:
    concept_key: str
    concept_resumen: str
    parent_key: str
    variants: tuple[VariantRecord, ...]
    skipped: tuple[Modification, ...]
    provenance: tuple[ProvenanceRecord, ...]


def write_catalog_entry(entry: VariantCatalogEntry, out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    final = out_dir / f"{entry.concept_key}.json"
    tmp = out_dir / f".{entry.concept_key}.json.tmp"
    payload = _entry_to_dict(entry)
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, final)
    return final


def read_catalog_entry(path: Path) -> VariantCatalogEntry:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return _entry_from_dict(raw)


# ----- helpers ----------------------------------------------------------

def _entry_to_dict(entry: VariantCatalogEntry) -> dict:
    return {
        "concept_key": entry.concept_key,
        "concept_resumen": entry.concept_resumen,
        "parent_key": entry.parent_key,
        "variants": [_variant_to_dict(v) for v in entry.variants],
        "skipped": [m.to_dict() for m in entry.skipped],
        "provenance": [_provenance_to_dict(p) for p in entry.provenance],
    }


def _variant_to_dict(v: VariantRecord) -> dict:
    return {
        "condition": v.condition,
        "modification_type": v.modification_type.value,
        "target_id_repr": v.target_id_repr,
        "rules": list(v.rules),
    }


def _provenance_to_dict(p: ProvenanceRecord) -> dict:
    return {
        "modification_type": p.modification_type.value,
        "rendered_prompt": p.rendered_prompt,
        "raw_responses": list(p.raw_responses),
        "validated_payload": p.validated_payload,
        "skipped": p.skipped.to_dict() if p.skipped is not None else None,
    }


def _entry_from_dict(d: dict) -> VariantCatalogEntry:
    return VariantCatalogEntry(
        concept_key=d["concept_key"],
        concept_resumen=d["concept_resumen"],
        parent_key=d["parent_key"],
        variants=tuple(_variant_from_dict(v) for v in d["variants"]),
        skipped=tuple(Modification.from_dict(m) for m in d["skipped"]),
        provenance=tuple(_provenance_from_dict(p) for p in d["provenance"]),
    )


def _variant_from_dict(d: dict) -> VariantRecord:
    return VariantRecord(
        condition=d["condition"],
        modification_type=ModificationType(d["modification_type"]),
        target_id_repr=d["target_id_repr"],
        rules=tuple(d["rules"]),
    )


def _provenance_from_dict(d: dict) -> ProvenanceRecord:
    return ProvenanceRecord(
        modification_type=ModificationType(d["modification_type"]),
        rendered_prompt=d["rendered_prompt"],
        raw_responses=tuple(d["raw_responses"]),
        validated_payload=d.get("validated_payload"),
        skipped=Modification.from_dict(d["skipped"]) if d.get("skipped") else None,
    )
