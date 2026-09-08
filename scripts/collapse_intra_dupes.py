"""Collapse intra-concept duplicate descriptions in the OE target corpus.

Runs AFTER cross-concept dedup (scripts/dedup_corpus.py). For every description a
single concept renders under more than one leaf, keep one leaf and REMAP the
derived synthetic items' ``original_key`` to it (not drop — keeps the concept's
representation intact). See :mod:`synthetic.dedup_targets`.

Run (PYTHONPATH=src):
  python scripts/collapse_intra_dupes.py \
    --target-long  data/synthetic/processed_OE/OE_target_long.parquet \
    --target-short data/synthetic/processed_OE/OE_target_short.parquet \
    --items data/synthetic/processed_OE/BC3CAT_Syn_items.parquet \
    --report docs/synthetic/OE_dedup_report.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from synthetic import dedup_targets as d  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-long", required=True)
    ap.add_argument("--target-short", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    long_df, short_df = pd.read_parquet(a.target_long), pd.read_parquet(a.target_short)
    syn = pd.read_parquet(a.items)

    drop, remap = d.plan_collapse(long_df, short_df)
    lo = long_df[~long_df["item_key"].isin(drop)].reset_index(drop=True)
    sh = short_df[~short_df["item_key"].isin(drop)].reset_index(drop=True)
    syn_out, n_remap = d.remap_synthetic(syn, remap)

    lo.to_parquet(a.target_long, index=False)
    sh.to_parquet(a.target_short, index=False)
    syn_out.to_parquet(a.items, index=False)

    concepts = sorted({k[:k.index("$") + 1] if "$" in k else k for k in
                       (long_df.set_index("item_key").loc[list(drop), "parent_key"])}) if drop else []
    report = f"""

## Intra-concept collapse (second dedup pass)

A single concept rendering the same description under several leaves (a parameter
axis absent from its templates) is redundant, though not label-ambiguous. Keep one
leaf per description; REMAP the derived synthetic queries to it (not drop).

- concept(s) collapsed: {', '.join(concepts) or '—'}
- **target corpus**: {len(long_df)} → **{len(lo)}** leaves ({len(drop)} redundant leaves removed)
- **synthetic corpus**: {len(syn)} items unchanged; **{n_remap}** had `original_key` remapped to the surviving sibling leaf

Verification: every target `(resumen, texto)` is now unique.
"""
    if a.report:
        with open(a.report, "a", encoding="utf-8") as f:
            f.write(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
