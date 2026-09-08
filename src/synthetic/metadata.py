"""Phase E (Tasks E1 + E2): variant-grained -> item-grained metadata join.

Stage B (`stage_b.py`) writes one **variant-grained** JSON per materialised
variant: the modification log once, with the regenerated items nested by leaf
key. The release schema (`RESEARCH_PROPOSAL.md §2.3`) is the opposite shape —
**one flat record per synthetic item**, each carrying its own traceability
triple `(item_key, original_key, variante_id)` plus the full modification log.

* **E1 — the join** (`join_variant_payload` / `join_variant_file` /
  `join_intermediate`): fan the variant's modification log out across its leaves,
  producing one `SyntheticItem` per leaf.
* **E2 — the validator** (`validate_item` / `validate_items` / `SchemaError`):
  fail loud on any malformed record before it can be packaged.

This module is a **pure library**. It reads the on-disk per-variant JSON (the
payload is the contract) and rebuilds `Modification`s via
`Modification.from_dict`; it imports neither `stage_b` nor `run_synthetic`
(stdlib + `taxonomy` + `utils.config` only). Parquet / JSONL serialization is
Phase G (G1), not here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional

from .taxonomy import Modification, ModificationType
from utils import config

__all__ = [
    "SyntheticItem",
    "SchemaError",
    "join_variant_payload",
    "join_variant_file",
    "join_intermediate",
    "validate_item",
    "validate_items",
]

_SYN_MARK = "_syn_"


@dataclass(frozen=True)
class SyntheticItem:
    """One flat release record per synthetic item (proposal §2.3 shape).

    `concept_key` is a back-pointer for grouping; it is intentionally absent
    from `to_dict()`, which mirrors the proposal's per-item schema exactly.
    """

    item_key: str
    original_key: str
    params: dict[str, str]
    resumen: str
    texto: str
    variante_id: str
    modification_types: tuple[ModificationType, ...]
    modification_count: int
    modifications: tuple[Modification, ...]
    concept_key: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_key": self.item_key,
            "original_key": self.original_key,
            "params": dict(self.params),
            "resumen": self.resumen,
            "texto": self.texto,
            "variante_id": self.variante_id,
            "modification_types": [t.value for t in self.modification_types],
            "modification_count": self.modification_count,
            "modifications": [m.to_dict() for m in self.modifications],
        }


class SchemaError(ValueError):
    """A `SyntheticItem` violates the release schema. Distinct, catchable."""


# ----- E1: the join -------------------------------------------------------

def join_variant_payload(payload: dict) -> list[SyntheticItem]:
    """Flatten one variant-grained Stage-B payload to item-grained records.

    Emits exactly `len(payload["items"])` records, one per `(leaf_key, item)`.
    `modification_count` / `modification_types` are **recomputed** from the
    applied `modifications` log (decision 3) — the payload's pre-computed copies
    are advisory, never trusted. `original_key = leaf_key[:-K]` where K is the
    count of applied `new_param` modifications (decision 1); the stage-7
    `validation` flag is dropped.
    """
    concept_key = payload["concept_key"]
    variante_id = payload["variant_id"]
    mods = tuple(Modification.from_dict(d) for d in payload["modifications"])
    mod_types = tuple(m.type for m in mods)
    mod_count = len(mods)
    k = sum(
        1 for m in mods
        if m.type is ModificationType.NEW_PARAM and m.status != "skipped"
    )

    out: list[SyntheticItem] = []
    for leaf_key, item in payload["items"].items():
        original_key = leaf_key[:-k] if k else leaf_key
        params = {
            axis_id: axis["values"][0]["value"]
            for axis_id, axis in (item.get("parameters") or {}).items()
        }
        out.append(
            SyntheticItem(
                item_key=f"{leaf_key}{_SYN_MARK}{variante_id}",
                original_key=original_key,
                params=params,
                resumen=item["resumen"],
                texto=item["texto"],
                variante_id=variante_id,
                modification_types=mod_types,
                modification_count=mod_count,
                modifications=mods,
                concept_key=concept_key,
            )
        )
    return out


def join_variant_file(path: Path) -> list[SyntheticItem]:
    """Read one per-variant JSON and join it."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return join_variant_payload(payload)


def join_intermediate(
    intermediate_dir: Optional[Path] = None,
) -> list[SyntheticItem]:
    """Walk `{concept_key}/*.json` (sorted) and concatenate the joins.

    Default `intermediate_dir` is `config.SYNTHETIC_INTERMEDIATE_DIR` (resolved
    here, not at import time). Deterministic: concept dirs and files are walked
    in sorted order.
    """
    root = (
        config.SYNTHETIC_INTERMEDIATE_DIR
        if intermediate_dir is None
        else Path(intermediate_dir)
    )
    if not root.exists():
        return []
    out: list[SyntheticItem] = []
    for concept_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for variant_file in sorted(concept_dir.glob("*.json")):
            out.extend(join_variant_file(variant_file))
    return out


# ----- E2: the validator --------------------------------------------------

def validate_item(item: SyntheticItem) -> None:
    """Fail loud (`raise SchemaError`) on any malformed field.

    Accepts `modification_count == 0` (zero-modification baselines are valid).
    """
    if not item.item_key:
        raise SchemaError("empty item_key")
    if not item.original_key:
        raise SchemaError(f"empty original_key for {item.item_key!r}")
    if not item.variante_id:
        raise SchemaError(f"empty variante_id for {item.item_key!r}")

    if item.modification_count != len(item.modifications):
        raise SchemaError(
            f"modification_count {item.modification_count} != "
            f"len(modifications) {len(item.modifications)} for {item.item_key!r}"
        )
    if tuple(item.modification_types) != tuple(m.type for m in item.modifications):
        raise SchemaError(
            f"modification_types disagree with modifications for {item.item_key!r}"
        )
    for m in item.modifications:
        if getattr(m, "type", None) is None or getattr(m, "layer", None) is None:
            raise SchemaError(
                f"malformed modification (missing type/layer) for {item.item_key!r}"
            )

    leaf_segment = item.item_key.split(_SYN_MARK, 1)[0]
    if not leaf_segment.startswith(item.original_key):
        raise SchemaError(
            f"original_key {item.original_key!r} is not a prefix of leaf segment "
            f"{leaf_segment!r} for {item.item_key!r}"
        )

    if not isinstance(item.resumen, str):
        raise SchemaError(f"non-string resumen for {item.item_key!r}")
    if not isinstance(item.texto, str):
        raise SchemaError(f"non-string texto for {item.item_key!r}")


def validate_items(items: Iterable[SyntheticItem]) -> None:
    """Validate every item; additionally assert global `item_key` uniqueness."""
    seen: set[str] = set()
    for item in items:
        validate_item(item)
        if item.item_key in seen:
            raise SchemaError(f"duplicate item_key {item.item_key!r}")
        seen.add(item.item_key)
