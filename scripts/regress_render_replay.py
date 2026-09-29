"""Regression for the list-form L2 engine change (retrieval D-043, condition 2).

Re-renders every delivered query of SINGLE, STACKED, dose and isolated with the
CURRENT engine, replaying the modifications its sidecar records, and compares
the TEXTO byte for byte with the delivered handoff file. Also checks that every
recorded modification still applies (none newly skipped). Prints counts only.

Usage (PYTHONPATH=src): python scripts/regress_render_replay.py --source data/raw/BPA_2026.bc3
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

SYN = REPO / "data" / "synthetic"
SETS = (
    ("OE_single_texto.json", "processed_OE_ablation_single"),
    ("OE_stacked_texto.json", "processed_OE_ablation_stacked"),
    ("OE_dose_texto.json", "processed_OE_dose"),
    ("OE_isolated_texto.json", "processed_OE_probe"),
)
_DROP = ("layer", "status")


def _replay(task):
    """`(item_key, concept, leaf, rules, source)` -> `(item_key, texto, n_applied)`."""
    from bc3param.param.codes import letter_to_index
    from bc3param.param.evaluator import Evaluator
    from synthetic import bc3param_backend as bk

    item_key, concept, leaf, rules, source = task
    bk.set_source(source)
    edited, applied = bk.apply_rules_logged(bk.family(concept), rules, concept)
    selection = [letter_to_index(ch) for ch in leaf[len(concept) - 1:]]
    return item_key, Evaluator(edited, selection).run().texto or "", len(applied)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()

    import logging
    logging.disable(logging.WARNING)  # skips are counted below, not logged
    failures = 0
    for fname, release in SETS:
        delivered = {r["item_key"]: r for r in json.loads(
            (SYN / "handoff_OE" / fname).read_text(encoding="utf-8"))}
        items = pd.read_parquet(SYN / release / "BC3CAT_Syn_items.parquet",
                                columns=["item_key", "concept_key", "original_key", "texto"])
        items = items[items["item_key"].isin(delivered)]
        mods = {}
        for line in (SYN / release / "BC3CAT_Syn_modifications.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec["item_key"] in delivered:
                mods[rec["item_key"]] = [{k: v for k, v in m.items() if k not in _DROP}
                                         for m in rec["modifications"] if m.get("status") == "applied"]
        tasks = [(r.item_key, r.concept_key, r.original_key, mods[r.item_key], str(Path(a.source)))
                 for r in items.itertuples(index=False)]
        stats = Counter()
        with ProcessPoolExecutor(max_workers=a.workers) as pool:
            for item_key, texto, n_applied in pool.map(_replay, tasks, chunksize=32):
                stats["replayed"] += 1
                stats["identical"] += texto == delivered[item_key]["text"]
                stats["modifications_short"] += n_applied != len(mods[item_key])
        stats["missing_from_release"] = len(delivered) - len(tasks)
        ok = (stats["identical"] == len(delivered) and not stats["modifications_short"])
        failures += not ok
        print(f"{fname}: {len(delivered)} delivered, {stats['replayed']} replayed, "
              f"{stats['identical']} byte-identical, "
              f"{stats['modifications_short']} with a modification no longer applied, "
              f"{stats['missing_from_release']} missing -> {'OK' if ok else 'FAIL'}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
