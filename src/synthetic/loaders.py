"""Phase G (Task G2): loader utilities — read API + 1:1 join + long/short views.

G1 (`packaging.py`) shipped the durable release: a flat columnar
`BC3CAT_Syn_items.parquet` (frozen `ITEM_COLUMNS`) and a ragged per-`item_key`
`BC3CAT_Syn_modifications.jsonl` sidecar, joined 1:1 on `item_key`. It shipped
only the minimal read side needed to pin its own round-trip and deferred the
consumer ergonomics to G2.

G2 is the thin, **read-only** consumer layer that turns the two on-disk release
files into the frames a downstream retrieval harness wants:

* `load_items` / `load_modifications` — thin wrappers over `packaging.read_*`
  (default paths resolved at call time under `config.SYNTHETIC_PROCESSED_DIR`).
* `join` — re-attaches the ragged `modifications` log to the flat items frame as
  an in-memory `list[dict]` column. **1:1 on `item_key` and fail-loud**
  (`LoaderError`) on any unmatched key on either side. The flat-Parquet shape is
  not resurrected; the column is an in-memory convenience on a copy.
* `long_view` / `short_view` — the OEB-style target/query projection: the
  retrieval text in a single `text` column (`texto` -> long, `resumen` ->
  short), the key+slice metadata, and a derived `text_norm` lexical column
  (`utils.text_processing.normalize_text`, reused verbatim). No OEB-only
  `id`/`ud`/`concept` columns are fabricated.

G2 **consumes; it neither generates nor packages.** It writes no new on-disk
artifact — every projection is in-memory and re-derivable, so G1's "two files
are the canonical release" invariant holds. It builds *on* `packaging`'s read
functions; it does not re-parse Parquet/JSONL. It imports `packaging`,
`taxonomy`, `utils.config`, `utils.text_processing`, the already-required
`pandas` (lazily, so the stdlib `load_modifications` path stays importable
without it), and stdlib only — never `stage_b` / `run_synthetic` /
`stage_runners` / `review` / `mutator` / any `layer_*`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

from . import packaging
from .taxonomy import Modification
from utils import config
from utils.text_processing import normalize_text

__all__ = [
    "LoaderError",
    "default_items_path",
    "default_modifications_path",
    "load_items",
    "load_modifications",
    "join",
    "long_view",
    "short_view",
    "main",
]

# The key + slice-metadata columns the long/short views carry (decision 3).
# The retrieval text becomes `text`; `text_norm` is derived. No OEB-only
# `id`/`ud`/`concept`, no `modifications`.
_VIEW_KEY_COLUMNS: tuple[str, ...] = (
    "item_key",
    "original_key",
    "concept_key",
    "params",
    "variante_id",
    "modification_types",
    "modification_count",
)
_VIEW_COLUMNS: tuple[str, ...] = _VIEW_KEY_COLUMNS + ("text", "text_norm")


class LoaderError(ValueError):
    """A release cannot be loaded/joined. Distinct, catchable.

    Raised for a join `item_key` mismatch (a partial release that would silently
    drop or duplicate rows) and for malformed loader input.
    """


def default_items_path() -> Path:
    """`config.SYNTHETIC_PROCESSED_DIR / ITEMS_FILENAME`, resolved at call time."""
    return config.SYNTHETIC_PROCESSED_DIR / packaging.ITEMS_FILENAME


def default_modifications_path() -> Path:
    """`config.SYNTHETIC_PROCESSED_DIR / MODIFICATIONS_FILENAME`, at call time."""
    return config.SYNTHETIC_PROCESSED_DIR / packaging.MODIFICATIONS_FILENAME


def load_items(path: Optional[Path] = None):
    """Read the items Parquet (`ITEM_COLUMNS` frame) via `packaging.read_*`."""
    return packaging.read_items_parquet(
        default_items_path() if path is None else Path(path)
    )


def load_modifications(
    path: Optional[Path] = None,
) -> dict[str, list[Modification]]:
    """Read the sidecar as `{item_key: [Modification, ...]}` (baseline -> `[]`).

    Always-on stdlib (the JSONL path needs no Parquet engine).
    """
    return packaging.read_modifications_jsonl(
        default_modifications_path() if path is None else Path(path)
    )


def join(
    items=None,
    modifications: Optional[dict[str, list[Modification]]] = None,
    *,
    items_path: Optional[Path] = None,
    mods_path: Optional[Path] = None,
):
    """Re-attach the `modifications` sidecar to the items frame, 1:1 on `item_key`.

    Loads (or accepts) both sides, asserts a **1:1** `item_key` join (fail-loud
    `LoaderError` on any unmatched key on either side, or a duplicate `item_key`
    in the frame), and returns a **copy** of the items frame — sorted by
    `item_key`, stable — with an added `modifications` column (`list[dict]` per
    row, the `Modification.to_dict` shape). The input frame is not mutated.
    """
    if items is None:
        items = load_items(items_path)
    if modifications is None:
        modifications = load_modifications(mods_path)

    item_keys = list(items["item_key"])
    items_set = set(item_keys)
    if len(items_set) != len(item_keys):
        raise LoaderError("duplicate item_key in items frame")

    mods_set = set(modifications)
    missing_in_mods = items_set - mods_set
    missing_in_items = mods_set - items_set
    if missing_in_mods or missing_in_items:
        raise LoaderError(
            "items/modifications join is not 1:1 on item_key "
            f"(in items only: {sorted(missing_in_mods)}; "
            f"in modifications only: {sorted(missing_in_items)})"
        )

    out = items.sort_values("item_key", kind="stable").reset_index(drop=True)
    out["modifications"] = [
        [m.to_dict() for m in modifications[key]] for key in out["item_key"]
    ]
    return out


def _view(items, text_source: str):
    """Project to the OEB-style view: key/metadata cols + `text` + `text_norm`."""
    import pandas as pd

    out = items.loc[:, list(_VIEW_KEY_COLUMNS)].copy()
    text = list(items[text_source])
    out["text"] = text
    out["text_norm"] = [normalize_text(t) for t in text]
    return out.loc[:, list(_VIEW_COLUMNS)]


def long_view(items):
    """Long/target view: `text == texto`, key+metadata cols, derived `text_norm`."""
    return _view(items, "texto")


def short_view(items):
    """Short/query view: `text == resumen`, key+metadata cols, derived `text_norm`."""
    return _view(items, "resumen")


# --------------------------------------------------------------------------
# CLI — thin wrapper over the library
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.loaders")
    sub = parser.add_subparsers(dest="cmd")

    info = sub.add_parser("info", help="load both release files and report")
    info.add_argument("--items-path", default=None)
    info.add_argument("--mods-path", default=None)

    args = parser.parse_args(argv)

    if args.cmd == "info":
        items = load_items(Path(args.items_path) if args.items_path else None)
        mods = load_modifications(Path(args.mods_path) if args.mods_path else None)
        joined = join(items=items, modifications=mods)
        print(
            json.dumps(
                {
                    "items": len(items),
                    "modifications": len(mods),
                    "columns": list(items.columns),
                    "join_one_to_one": len(joined) == len(items),
                },
                ensure_ascii=False,
            )
        )
        return 0

    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
