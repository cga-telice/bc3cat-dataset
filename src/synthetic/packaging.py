"""Phase G (Task G1): release packaging — items Parquet + modifications sidecar.

Everything Phases A–E built lives in-memory (`SyntheticItem` dataclasses) or as
workflow JSONL; nothing on disk is the shape a downstream consumer
(`bc3cat-retrieval`) loads. G1 (`RESEARCH_PROTOCOL.md §5 G1`, §7 file map)
packages the joined `SyntheticItem`s into the durable BC3CAT-Syn release — **two
files, one key**:

* **`BC3CAT_Syn_items.parquet`** — one flat, columnar row per item carrying the
  proposal §2.3 record (`SyntheticItem.to_dict` minus `modifications`) plus the
  `concept_key` grouping back-pointer (`ITEM_COLUMNS`). This is the
  retrieval-/slice-facing table.
* **`BC3CAT_Syn_modifications.jsonl`** — one line per `item_key` carrying the
  ragged `modifications` log (`Modification.to_dict`), kept out of the flat
  Parquet. The two files join 1:1 on `item_key`.

G1 **packages; it does not generate.** The release is a deterministic function
of `metadata.join_intermediate()` output: no LLM, no pipeline rerun. The derived
`_norm`/`_feats` lexical columns are a downstream feature-stage derivation, not
the §2.3 record, and are deferred (G2). Both writes are atomic (`.tmp` rename)
and run-twice byte-identical; `write_release` validates (E2 `validate_items`)
before it writes, so a malformed record fails loud rather than emitting a corrupt
release.

This module imports `metadata`, `taxonomy`, `utils.config`, the already-required
`pandas`/`pyarrow` (lazily, so the stdlib sidecar side stays importable without
them), and stdlib only — never `stage_b` / `run_synthetic` / `stage_runners` /
`review`. The sampler and the generation stack are not in the release path.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from .metadata import SyntheticItem, SchemaError, join_intermediate, validate_items
from .taxonomy import Modification
from utils import config

__all__ = [
    "PackagingError",
    "ITEM_COLUMNS",
    "ITEMS_FILENAME",
    "MODIFICATIONS_FILENAME",
    "items_to_frame",
    "modifications_sidecar",
    "write_items_parquet",
    "write_modifications_jsonl",
    "write_release",
    "read_items_parquet",
    "read_modifications_jsonl",
    "main",
]

# The frozen items-frame column order. The §2.3 per-item record
# (`SyntheticItem.to_dict` minus `modifications`) plus `concept_key`, the one
# grouping back-pointer the record carries. The ragged `modifications` log is
# the sidecar; the derived `_norm`/`_feats` lexical columns are a downstream
# derivation (G2), not part of the release record.
ITEM_COLUMNS: tuple[str, ...] = (
    "item_key",
    "original_key",
    "concept_key",
    "params",
    "resumen",
    "texto",
    "variante_id",
    "modification_types",
    "modification_count",
)

# Protocol §7 release file names.
ITEMS_FILENAME = "BC3CAT_Syn_items.parquet"
MODIFICATIONS_FILENAME = "BC3CAT_Syn_modifications.jsonl"


class PackagingError(ValueError):
    """A release artifact cannot be written. Distinct, catchable.

    Raised for a malformed record on the write path (re-wrapping E2's
    `SchemaError`) and for a duplicate `item_key` on the sidecar.
    """


def _validate(items: list[SyntheticItem]) -> None:
    """Run E2 `validate_items`; re-raise its `SchemaError` as `PackagingError`."""
    try:
        validate_items(items)
    except SchemaError as exc:
        raise PackagingError(f"refusing to package malformed records: {exc}") from exc


def _item_row(item: SyntheticItem) -> dict[str, Any]:
    return {
        "item_key": item.item_key,
        "original_key": item.original_key,
        "concept_key": item.concept_key,
        "params": dict(item.params),
        "resumen": item.resumen,
        "texto": item.texto,
        "variante_id": item.variante_id,
        "modification_types": [t.value for t in item.modification_types],
        "modification_count": item.modification_count,
    }


def items_to_frame(items: Iterable[SyntheticItem]):
    """Validated items -> a `pandas.DataFrame` with exactly `ITEM_COLUMNS`.

    One row per item, sorted by `item_key`; `params` cells are the nested dict,
    `modification_types` cells are `list[str]` of enum `.value`s; there is **no**
    `modifications` column. Validates (E2) first — a malformed record raises
    `PackagingError` before a frame is built.
    """
    import pandas as pd

    items = list(items)
    _validate(items)
    rows = [_item_row(it) for it in sorted(items, key=lambda it: it.item_key)]
    return pd.DataFrame(rows, columns=list(ITEM_COLUMNS))


def modifications_sidecar(items: Iterable[SyntheticItem]) -> list[dict[str, Any]]:
    """One `{"item_key", "modifications"}` dict per item, sorted by `item_key`.

    A baseline item (empty log) still gets a line with `modifications: []`. Pure:
    no validation, no I/O (the duplicate-key gate lives on the write path).
    """
    return [
        {
            "item_key": it.item_key,
            "modifications": [m.to_dict() for m in it.modifications],
        }
        for it in sorted(items, key=lambda it: it.item_key)
    ]


def write_items_parquet(items: Iterable[SyntheticItem], path: Path) -> Path:
    """Atomically write the items Parquet (`.tmp` rename). Validates first."""
    frame = items_to_frame(items)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    frame.to_parquet(tmp, engine="pyarrow", index=False)
    os.replace(tmp, path)
    return path


def write_modifications_jsonl(items: Iterable[SyntheticItem], path: Path) -> Path:
    """Atomically write the sidecar JSONL; fail-loud on a duplicate `item_key`."""
    rows = modifications_sidecar(items)
    seen: set[str] = set()
    for row in rows:
        if row["item_key"] in seen:
            raise PackagingError(f"duplicate item_key {row['item_key']!r}")
        seen.add(row["item_key"])

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(tmp, path)
    return path


def write_release(
    items: Iterable[SyntheticItem],
    *,
    out_dir: Optional[Path] = None,
) -> dict[str, Path]:
    """Validate, then write both release files under `out_dir`.

    Validation runs **before** any write, so a malformed record raises
    `PackagingError` with no partial release on disk. `out_dir` defaults to
    `config.SYNTHETIC_PROCESSED_DIR`. Returns `{"items": ..., "modifications": ...}`.
    """
    items = list(items)
    _validate(items)
    out = config.SYNTHETIC_PROCESSED_DIR if out_dir is None else Path(out_dir)
    items_path = write_items_parquet(items, out / ITEMS_FILENAME)
    mods_path = write_modifications_jsonl(items, out / MODIFICATIONS_FILENAME)
    return {"items": items_path, "modifications": mods_path}


def read_items_parquet(path: Path):
    """Read the items Parquet back (minimal round-trip read; full loader is G2)."""
    import pandas as pd

    return pd.read_parquet(Path(path), engine="pyarrow")


def read_modifications_jsonl(path: Path) -> dict[str, list[Modification]]:
    """Read the sidecar back as `{item_key: [Modification, ...]}`.

    Reconstructs each `Modification` via `Modification.from_dict`. A duplicate
    `item_key` in the file is fail-loud (`PackagingError`).
    """
    out: dict[str, list[Modification]] = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            key = row["item_key"]
            mods = [Modification.from_dict(m) for m in row["modifications"]]
        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            raise PackagingError(f"malformed sidecar line: {exc}") from exc
        if key in out:
            raise PackagingError(f"duplicate item_key {key!r}")
        out[key] = mods
    return out


# --------------------------------------------------------------------------
# CLI — thin wrapper over the library
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.packaging")
    sub = parser.add_subparsers(dest="cmd")

    build = sub.add_parser("build", help="package joined items into the release")
    build.add_argument("--intermediate-dir", default=None)
    build.add_argument("--out-dir", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "build":
        idir = Path(args.intermediate_dir) if args.intermediate_dir else None
        out = Path(args.out_dir) if args.out_dir else None
        items = join_intermediate(idir)
        paths = write_release(items, out_dir=out)
        print(
            json.dumps(
                {"items": len(items), **{k: str(v) for k, v in paths.items()}},
                ensure_ascii=False,
            )
        )
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
