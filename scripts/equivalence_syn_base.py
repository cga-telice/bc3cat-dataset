"""Base-level equivalence: bc3param render vs the legacy synthetic engine (OEB).

For every OEB parametric concept in the committed intermediate, compare the legacy
`stage_runners.run_stages_3_to_7` output against `bc3param_backend.render_base`,
classifying each resumen/texto difference as exact / whitespace / v2-correction /
unexplained (reusing the dataset reconciliation's `undo_corruption`). Phase-1
equivalence = zero unexplained and identical leaf key sets.

Run: python scripts/equivalence_syn_base.py
Exits non-zero if any unexplained difference or key-set mismatch is found.
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from scripts.reconcile_v1_v2 import collapse, undo_corruption  # noqa: E402
from synthetic import bc3param_backend as bk  # noqa: E402
from synthetic import l2_repr, stage_runners  # noqa: E402

INTERMEDIATE = REPO / "data" / "intermediate" / "OBRA CIVIL" / "OBRA CIVIL.json"


def compare() -> tuple[collections.Counter, int, int, list]:
    inter = json.loads(INTERMEDIATE.read_text(encoding="utf-8"))
    oeb = [k for k in inter if k.startswith("OEB") and k.endswith("$")]
    tally: collections.Counter = collections.Counter()
    only_legacy = only_bc3 = 0
    unexplained: list = []
    for ck in oeb:
        legacy = stage_runners.run_stages_3_to_7(l2_repr.formula_to_list({ck: inter[ck]}))
        got = bk.render_base(ck)
        kl, kb = set(legacy), set(got)
        only_legacy += len(kl - kb)
        only_bc3 += len(kb - kl)
        for leaf in kl & kb:
            for field in ("resumen", "texto"):
                a, b = legacy[leaf].get(field, ""), got[leaf].get(field, "")
                if a == b:
                    tally["exact"] += 1
                elif collapse(a) == collapse(b):
                    tally["whitespace"] += 1
                elif undo_corruption(a) == undo_corruption(b):
                    tally["v2_correction"] += 1
                else:
                    tally["unexplained"] += 1
                    if len(unexplained) < 20:
                        unexplained.append((leaf, field, collapse(a), collapse(b)))
    return tally, only_legacy, only_bc3, unexplained


def main() -> int:
    tally, only_legacy, only_bc3, unexplained = compare()
    print("Base-level equivalence — legacy vs bc3param (OEB chapter)")
    print(f"  field comparisons: {dict(tally)}")
    print(f"  leaves only in legacy (s07 dedup): {only_legacy} | only in bc3param: {only_bc3}")
    for leaf, field, a, b in unexplained:
        print(f"  UNEXPLAINED {leaf} {field}\n    legacy:   {a[:160]}\n    bc3param: {b[:160]}")
    ok = tally["unexplained"] == 0 and only_legacy == 0 and only_bc3 == 0
    print("RESULT:", "EQUIVALENT (up to v2 corrections)" if ok else "DIFFERENCES FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
