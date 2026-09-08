"""Rule-application equivalence: bc3param vs the legacy synthetic engine.

For every frozen variant in `data/synthetic/variants/*.json`, materialise it both
ways — legacy `stage_b.materialize_variant` (s03-s07 + z_formula) and
`stage_b.materialize_variant_bc3param` (the bc3param adapter) — and compare the
rendered leaves (resumen/texto) and the modification sidecar, classifying each
text difference as exact / whitespace / v2-correction / unexplained. `new_param`
variants are excluded (out of the pilot corpus scope).

Phase-1 acceptance = zero unexplained text differences AND zero modification-log
mismatches AND zero errors. Slow (the legacy path re-runs s03-s07 per variant);
run on demand. `compare(concepts=[...])` limits scope for a fast check.

Run: python scripts/equivalence_syn_rules.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "src"))

from scripts.reconcile_v1_v2 import collapse, undo_corruption  # noqa: E402
from synthetic import l2_repr, stage_b  # noqa: E402
from synthetic.taxonomy import ModificationType  # noqa: E402
from synthetic.variant_catalog import VariantRecord  # noqa: E402

INTERMEDIATE = REPO / "data" / "intermediate" / "OBRA CIVIL" / "OBRA CIVIL.json"
VARIANTS_GLOB = str(REPO / "data" / "synthetic" / "variants" / "*.json")


def compare(concepts: list[str] | None = None, max_variants: int | None = None):
    inter = json.loads(INTERMEDIATE.read_text(encoding="utf-8"))
    tally: collections.Counter = collections.Counter()
    unexplained: list = []
    errors: list = []
    modmismatch = 0
    nvar = 0
    for f in sorted(glob.glob(VARIANTS_GLOB)):
        ck = os.path.basename(f)[:-5]
        if ck not in inter or (concepts is not None and ck not in concepts):
            continue
        slice_ = {ck: inter[ck]}
        variants = json.loads(Path(f).read_text(encoding="utf-8")).get("variants", [])
        for v in variants:
            rules = v.get("rules", [])
            if any(r.get("type") == "new_param" for r in rules):
                continue
            if max_variants is not None and nvar >= max_variants:
                break
            rec = VariantRecord(
                condition=v.get("condition", "c"),
                modification_type=ModificationType(v.get("modification_type", rules[0]["type"])),
                target_id_repr=v.get("target_id_repr", ""),
                rules=tuple(rules),
            )
            try:
                legacy = stage_b.materialize_variant(slice_, ck, rec, pre_rerun=l2_repr.formula_to_list)
                got = stage_b.materialize_variant_bc3param(slice_, ck, rec)
            except Exception as exc:  # noqa: BLE001
                errors.append((ck, v.get("condition"), type(exc).__name__, str(exc)[:120]))
                continue
            nvar += 1
            if [m.to_dict() for m in legacy.modifications] != [m.to_dict() for m in got.modifications]:
                modmismatch += 1
            for leaf in set(legacy.items) & set(got.items):
                for field in ("resumen", "texto"):
                    a, b = legacy.items[leaf].get(field, ""), got.items[leaf].get(field, "")
                    if a == b:
                        tally["exact"] += 1
                    elif collapse(a) == collapse(b):
                        tally["whitespace"] += 1
                    elif undo_corruption(a) == undo_corruption(b):
                        tally["v2_correction"] += 1
                    else:
                        tally["unexplained"] += 1
                        if len(unexplained) < 20:
                            unexplained.append((ck, v.get("condition"), leaf, field, collapse(a), collapse(b)))
    return nvar, tally, errors, modmismatch, unexplained


def main() -> int:
    nvar, tally, errors, modmismatch, unexplained = compare()
    print(f"Rule-application equivalence — legacy vs bc3param ({nvar} variants)")
    print(f"  field comparisons: {dict(tally)}")
    print(f"  errors: {len(errors)} | modification-log mismatches: {modmismatch}")
    for e in errors[:10]:
        print("  ERR", e)
    for ck, cond, leaf, field, a, b in unexplained:
        print(f"  UNEXPLAINED {ck} {cond} {field}\n    legacy:   {a[:150]}\n    bc3param: {b[:150]}")
    ok = tally["unexplained"] == 0 and not errors and modmismatch == 0
    print("RESULT:", "EQUIVALENT (up to v2 corrections)" if ok else "DIFFERENCES FOUND")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
