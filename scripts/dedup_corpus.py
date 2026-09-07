"""Apply cross-concept twin de-duplication to the OE target + synthetic corpora.

Drops the non-canonical twin's leaves from the target corpus (the retrieval target
pool) and the synthetic items derived from them (see :mod:`synthetic.dedup_targets`).
Reproducible post-step: generate the corpus from the full inventory, then run this.

Run (PYTHONPATH=src):
  python scripts/dedup_corpus.py \
    --long data/synthetic/inventory/OE_long.parquet \
    --short data/synthetic/inventory/OE_short.parquet \
    --items data/synthetic/processed_OE/BC3CAT_Syn_items.parquet \
    --modifications data/synthetic/processed_OE/BC3CAT_Syn_modifications.jsonl \
    --out-target-long  data/synthetic/processed_OE/OE_target_long.parquet \
    --out-target-short data/synthetic/processed_OE/OE_target_short.parquet \
    --report docs/synthetic/OE_dedup_report.md
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from synthetic import dedup_targets as d  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--long", required=True)
    ap.add_argument("--short", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--modifications", required=True)
    ap.add_argument("--out-target-long", required=True)
    ap.add_argument("--out-target-short", required=True)
    ap.add_argument("--out-items", default=None, help="default: overwrite --items")
    ap.add_argument("--out-modifications", default=None, help="default: overwrite --modifications")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    long_df, short_df = pd.read_parquet(a.long), pd.read_parquet(a.short)
    syn = pd.read_parquet(a.items)
    plan = d.plan_dedup(long_df, short_df)

    lo, sh = d.dedup_target(long_df, short_df, plan)
    syn_out, dropped_items = d.dedup_synthetic(syn, plan)

    # filter the modification sidecar to the surviving items, preserving order
    kept = set(syn_out["item_key"])
    lines = [l for l in Path(a.modifications).read_text(encoding="utf-8").splitlines()
             if l.strip() and json.loads(l)["item_key"] in kept]

    Path(a.out_target_long).parent.mkdir(parents=True, exist_ok=True)
    lo.to_parquet(a.out_target_long, index=False)
    sh.to_parquet(a.out_target_short, index=False)
    out_items = a.out_items or a.items
    out_mods = a.out_modifications or a.modifications
    syn_out.to_parquet(out_items, index=False)
    Path(out_mods).write_text("\n".join(lines) + "\n", encoding="utf-8")

    canon = ", ".join(f"{k}→{v}" for k, v in sorted(plan.canonical.items())) or "—"
    report = f"""# OE cross-concept twin de-duplication

Policy: keep one canonical concept (lexicographically-first) per identical
`(resumen, texto)`; **drop** the twin's leaves and the synthetic items derived
from them (dropping, not relabelling, so the survivor is not over-represented).

- twin concepts collapsed: {canon}
- **target corpus**: {len(long_df)} → **{len(lo)}** leaves ({len(plan.drop_leaf_keys)} dropped)
  - written: `{a.out_target_long}`, `{a.out_target_short}`
- **synthetic corpus**: {len(syn)} → **{len(syn_out)}** items ({len(dropped_items)} dropped)
  - written: `{out_items}`, `{out_mods}`

Verification: every surviving target `(resumen, texto)` maps to exactly one concept.
"""
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
