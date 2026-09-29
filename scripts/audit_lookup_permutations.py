"""Audit for retrieval P7 (REORDER_LOOKUP_ARGUMENTS.md): template rewrites that
permute a lookup's arguments and render a sibling leaf's text.

Prints COUNTS ONLY, per split, never query texts or keys: bc3cat-retrieval does
not read test-split queries before its final evaluation.

1. Approved menu rules that the fixed placeholder check now rejects.
2. Per delivered query file: queries whose text equals the TEXTO of a leaf other
   than the gold, where that TEXTO differs from the gold's (so D-031 duplicate
   groups are not counted).
3. Per modifications sidecar: applied records that use a rule from (1), by field.

Usage: python scripts/audit_lookup_permutations.py [path/to/SPLITS.md] [exclusion.json]

With a second argument, also writes the key-only exclusion list of the SINGLE
test queries built from a rejected rule (keys are written, never printed).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from synthetic.taxonomy import ModificationType  # noqa: E402
from synthetic.variant_proposer import _validate_payload  # noqa: E402

SYN = REPO / "data" / "synthetic"
HANDOFF = SYN / "handoff_OE"
QUERY_FILES = ("OE_single_texto.json", "OE_stacked_texto.json",
               "OE_dose_texto.json", "OE_isolated_texto.json")
SIDECARS = ("processed_OE", "processed_OE_ablation_single", "processed_OE_ablation_stacked",
            "processed_OE_dose", "processed_OE_probe")
TEMPLATE_TYPES = ("reorder", "template_paraphrase", "omission")
DEFAULT_SPLITS = REPO.parent / "bc3cat-retrieval" / "docs" / "synthetic-oe" / "SPLITS.md"


def load_splits(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    split_of: dict[str, str] = {}
    for name in ("dev", "test"):
        m = re.search(rf"^## {name} .*?```\n(.*?)```", text, re.S | re.M)
        for key in m.group(1).split():
            split_of[key] = name
    return split_of


def withdrawn_rules() -> set[tuple[str, str, str]]:
    """(type, original, new) of approved candidates the fixed check rejects."""
    out = set()
    for mtype in TEMPLATE_TYPES:
        for line in (SYN / "menus_OE" / "verdicts" / f"{mtype}.jsonl").read_text(encoding="utf-8").splitlines():
            for c in json.loads(line)["candidates"]:
                if not c["approved"]:
                    continue
                try:
                    _validate_payload(c["payload"], ModificationType(mtype))
                except ValueError as e:
                    if "placeholders_not_preserved" in str(e):
                        out.add((mtype, c["payload"]["original"], c["payload"]["new"]))
    return out


def concept(item_key: str) -> str:
    return item_key[:6] + "$"


def main(splits_path: Path = DEFAULT_SPLITS, exclusion_path: Path | None = None) -> int:
    split_of = load_splits(splits_path)

    rules = withdrawn_rules()
    # Counts only: a rule's template names its concept, and so its split.
    print(f"## 1. Approved rules rejected by the fixed check: {len(rules)}")
    for mtype, n in sorted(Counter(r[0] for r in rules).items()):
        print(f"  {mtype}: {n}")

    corpus = json.loads((HANDOFF / "OE_texto.json").read_text(encoding="utf-8"))
    text_of = {d["item_key"]: d["text"] for d in corpus}
    leaves_by_text: dict[str, set[str]] = {}
    for k, t in text_of.items():
        leaves_by_text.setdefault(t, set()).add(k)

    print("\n## 2. Queries equal to a non-gold leaf's (different) TEXTO")
    for name in QUERY_FILES:
        queries = json.loads((HANDOFF / name).read_text(encoding="utf-8"))
        total, hit = Counter(), Counter()
        for q in queries:
            s = split_of[q["parent_key"]]
            total[s] += 1
            gold_text = text_of[q["gold_item_key"]]
            if q["text"] != gold_text and q["text"] in leaves_by_text:
                hit[s] += 1
        print(f"  {name}: dev {hit['dev']} of {total['dev']}, test {hit['test']} of {total['test']}")

    print("\n## 3. Applied sidecar records using a rejected rule")
    delivered_test_keys = set()
    for d in SIDECARS:
        hit = Counter()
        for line in (SYN / d / "BC3CAT_Syn_modifications.jsonl").read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            for m in rec["modifications"]:
                if m.get("status") == "applied" and (m["type"], m.get("original"), m.get("new")) in rules:
                    s = split_of[concept(rec["item_key"])]
                    hit[(s, m.get("field"))] += 1
                    if d == "processed_OE_ablation_single" and s == "test":
                        delivered_test_keys.add(rec["item_key"])
        summary = ", ".join(f"{s}/{f}: {n}" for (s, f), n in sorted(hit.items())) or "0"
        print(f"  {d}: {summary}")

    if exclusion_path is not None:
        # Keys only, never printed: retrieval applies them blind at the final
        # test evaluation (D-043 Q1).
        exclusion_path.write_text(json.dumps({
            "reason": "P7: SINGLE test queries rendered from a withdrawn reorder rule "
                      "(not referent-preserving); exclude from item-level scoring, "
                      "keep at parent level",
            "file": "OE_single_texto.json",
            "split": "test",
            "item_keys": sorted(delivered_test_keys),
        }, indent=2) + "\n", encoding="utf-8")
        print(f"\nexclusion list: {len(delivered_test_keys)} keys -> {exclusion_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*(Path(a) for a in sys.argv[1:3])))
