"""Cache hygiene (Phase D Task D3): enumerate / clear stale derived artefacts.

Now that Stage B writes real mutated items to disk, the derived artefacts that
go stale when the corpus changes need a single place to be enumerated and
(opt-in) cleared:

  * `processed/*.pkl`            — Pickle caches (Generate_OEB_dataset, retrieval)
  * `llamaindex/` contents       — LlamaIndex doc-store caches (s08)
  * stray `chunk_*.json`         — half-merged chunks left by the s04/s05 drivers
  * `**/.ipynb_checkpoints`      — Jupyter checkpoint directories

`stale_cache_paths` is pure (returns paths, deletes nothing). `clear_caches`
defaults to `dry_run=True` — deletion is opt-in. Neither module-level reads,
resolves paths, nor performs IO at import.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from utils import config

__all__ = ["stale_cache_paths", "clear_caches"]


def stale_cache_paths(*, data_root: Optional[Path] = None) -> list[Path]:
    """Enumerate the derived artefacts that go stale when the corpus changes.

    Pure: returns a sorted list of existing paths, deletes nothing. `data_root`
    defaults to `config.DATA_ROOT`; tests inject a `tmp_path`.
    """
    root = config.DATA_ROOT if data_root is None else Path(data_root)
    paths: list[Path] = []

    processed = root / "processed"
    if processed.is_dir():
        paths.extend(processed.glob("*.pkl"))

    llamaindex = root / "llamaindex"
    if llamaindex.is_dir():
        paths.extend(p for p in llamaindex.rglob("*") if p.is_file())

    paths.extend(root.rglob("chunk_*.json"))
    paths.extend(p for p in root.rglob(".ipynb_checkpoints") if p.is_dir())

    return sorted(set(paths))


def clear_caches(
    *, data_root: Optional[Path] = None, dry_run: bool = True,
) -> list[Path]:
    """Return the would-delete list; only unlink when `dry_run=False`.

    `dry_run=True` (the default) deletes nothing. Deletion is opt-in.
    """
    targets = stale_cache_paths(data_root=data_root)
    if not dry_run:
        for path in targets:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
    return targets
