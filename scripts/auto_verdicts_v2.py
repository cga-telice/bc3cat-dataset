"""Mechanical rubric-v2 verdicts for the OE synthetic menus.

Rubric v2 (owner's bar, from the OEB pilot): approve by default; reject only on
(a) structural/generation residue in the rewrite, (b) an empty rewrite, or
(c) an explicit preserves_meaning=false from the proposer. Omission over-deletion
and render breakage are caught downstream by the corpus driver's guards.

Reads   data/synthetic/menus_OE/{tipo}.jsonl
Writes  data/synthetic/menus_OE/verdicts/{tipo}.jsonl   (menu_review_parser format)

Usage: python scripts/auto_verdicts_v2.py [menus_dir]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from synthetic.menu_review_parser import CandidateVerdict, MenuVerdict, write_verdicts  # noqa: E402
from synthetic.taxonomy import ModificationType  # noqa: E402

# L3 field rules (reorder/template_paraphrase/omission) rewrite whole templates,
# which legitimately CONTAIN placeholders ($A, $K, %B, $G(%C)); for them residue
# is only an unrestored sentinel. L1/L2 fragments are plain values — a $X/%X there
# is residue.
_FIELD_TYPES = {"reorder", "template_paraphrase", "omission"}
_SENTINEL = re.compile(r"\[\[|\]\]")
_FRAGMENT_RESIDUE = re.compile(r"\[\[|\]\]|[$%][A-Za-z]")


def _approve(payload: dict, mtype: str) -> bool:
    new = str(payload.get("new", ""))
    if not new.strip():
        return False
    if payload.get("preserves_meaning") is False:
        return False
    # No-op rewrite: `new` equals `original` (a "paraphrase" that changed nothing).
    # It would inflate modification_count without altering the item, so reject it.
    original = str(payload.get("original", ""))
    if original and " ".join(new.split()) == " ".join(original.split()):
        return False
    rx = _SENTINEL if mtype in _FIELD_TYPES else _FRAGMENT_RESIDUE
    if rx.search(new):
        return False
    return True


def main(menus_dir: str = "data/synthetic/menus_OE") -> int:
    mdir = REPO / menus_dir if not Path(menus_dir).is_absolute() else Path(menus_dir)
    vdir = mdir / "verdicts"
    totals = {"approved": 0, "rejected": 0}
    for menu_path in sorted(mdir.glob("*.jsonl")):
        verdicts: list[MenuVerdict] = []
        for line in menu_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            cands = []
            for c in rec.get("candidates", []):
                ok = _approve(c.get("payload", {}), rec["modification_type"])
                cands.append(CandidateVerdict(payload=c["payload"], approved=ok))
                totals["approved" if ok else "rejected"] += 1
            verdicts.append(MenuVerdict(
                mtype=ModificationType(rec["modification_type"]),
                dedup_key=tuple(rec["dedup_key"]),
                canonical=str(rec["canonical"]),
                candidates=tuple(cands),
                skipped_reason=rec.get("skipped_reason"),
            ))
        out = vdir / menu_path.name
        write_verdicts(verdicts, out)
        napp = sum(1 for v in verdicts for c in v.candidates if c.approved)
        ncand = sum(len(v.candidates) for v in verdicts)
        print(f"{menu_path.stem:22} {len(verdicts):4} targets  {napp}/{ncand} candidates approved -> {out}")
    print(f"TOTAL approved={totals['approved']} rejected={totals['rejected']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*(sys.argv[1:2])))
