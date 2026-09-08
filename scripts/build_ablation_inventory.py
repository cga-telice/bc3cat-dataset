"""Select a shared base-leaf sample for the ablation corpora (Design A).

Both the STACKED (all-mods) and SINGLE (one-mod) corpora are generated from this
one restricted inventory, so every item is paired on the same base leaves —
retrieval-degradation differences are attributable to the modifications, not to
which leaves were picked. Selection is leaf-proportional across concepts (with a
per-concept floor for coverage), deterministic.

Run (PYTHONPATH=src):
  python scripts/build_ablation_inventory.py --n 5000 \
    --target-long  data/synthetic/processed_OE/OE_target_long.parquet \
    --target-short data/synthetic/processed_OE/OE_target_short.parquet \
    --out-long  data/synthetic/processed_OE/OE_ablation_inventory_long.parquet \
    --out-short data/synthetic/processed_OE/OE_ablation_inventory_short.parquet
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--floor", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--target-long", required=True)
    ap.add_argument("--target-short", required=True)
    ap.add_argument("--out-long", required=True)
    ap.add_argument("--out-short", required=True)
    a = ap.parse_args()

    lo = pd.read_parquet(a.target_long)
    sh = pd.read_parquet(a.target_short)
    by_concept = {c: sorted(g["item_key"]) for c, g in lo.groupby("parent_key")}
    supply = sum(len(v) for v in by_concept.values())

    # leaf-proportional per-concept quota, floor for coverage, largest-remainder to N
    concepts = sorted(by_concept)
    raw = {c: a.n * len(by_concept[c]) / supply for c in concepts}
    quota = {c: max(a.floor, int(raw[c])) for c in concepts}
    # trim/grow to exactly N by adjusting on the largest fractional parts
    while sum(quota.values()) > a.n:
        # remove from the concept most above its floor with the largest quota
        c = max((c for c in concepts if quota[c] > a.floor),
                key=lambda c: (quota[c], c))
        quota[c] -= 1
    order = sorted(concepts, key=lambda c: (-(raw[c] - int(raw[c])), c))
    i = 0
    while sum(quota.values()) < a.n:
        c = order[i % len(order)]
        if quota[c] < len(by_concept[c]):
            quota[c] += 1
        i += 1

    rng = random.Random(a.seed)
    picked: list[str] = []
    for c in concepts:
        leaves = by_concept[c]
        k = min(quota[c], len(leaves))
        picked.extend(rng.sample(leaves, k))
    picked_set = set(picked)

    out_lo = lo[lo["item_key"].isin(picked_set)].reset_index(drop=True)
    out_sh = sh[sh["item_key"].isin(picked_set)].reset_index(drop=True)
    Path(a.out_long).parent.mkdir(parents=True, exist_ok=True)
    out_lo.to_parquet(a.out_long, index=False)
    out_sh.to_parquet(a.out_short, index=False)
    print(f"shared inventory: {len(out_lo)} leaves across "
          f"{out_lo['parent_key'].nunique()} concepts "
          f"(target N={a.n}); written to {a.out_long}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
