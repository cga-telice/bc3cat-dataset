"""Audit for retrieval P8 (D-044): synonym_label candidates that differ from the
original label only in letter case, so the query is its gold TEXTO once
lower-cased.

Prints COUNTS ONLY, per split, never query texts or keys: bc3cat-retrieval does
not read test-split queries before its final evaluation.

1. Approved synonym_label menu candidates equal to their original after
   lower-casing.
2. Per delivered query file: queries whose text equals the gold TEXTO after
   lower-casing, by modification type.

Usage: python scripts/audit_case_only_synonyms.py [path/to/SPLITS.md] [exclusion.json]

With a second argument, also writes the key-only list of the SINGLE test
queries affected (keys are written, never printed).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO))

from audit_lookup_permutations import DEFAULT_SPLITS, HANDOFF, SYN, concept, load_splits  # noqa: E402

QUERY_FILES = ("OE_single_texto.json", "OE_stacked_texto.json", "OE_dose_texto.json",
               "OE_isolated_texto.json", "OE_single_l2_texto.json")


def case_only_rules() -> list[tuple[str, str, str]]:
    """(canonical, original, new) of approved synonym_label case variants."""
    out = []
    path = SYN / "menus_OE" / "verdicts" / "synonym_label.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        for c in row["candidates"]:
            o, n = c["payload"]["original"], c["payload"]["new"]
            if c["approved"] and o != n and o.strip().casefold() == n.strip().casefold():
                out.append((row["canonical"], o, n))
    return out


def main(splits_path: Path = DEFAULT_SPLITS, exclusion_path: Path | None = None) -> int:
    split_of = load_splits(splits_path)

    rules = case_only_rules()
    print(f"1. approved case-only synonym_label candidates: {len(rules)}")
    for canonical, o, n in rules:  # menu labels, not queries
        print(f"  {canonical}: {o!r} -> {n!r}")

    gold = {r["item_key"]: r["text"].casefold()
            for r in json.loads((HANDOFF / "OE_texto.json").read_text(encoding="utf-8"))}

    print("\n2. queries equal to gold TEXTO after lower-casing")
    test_keys: list[str] = []
    for name in QUERY_FILES:
        path = HANDOFF / name
        if not path.exists():
            continue
        hit: Counter = Counter()
        total: Counter = Counter()
        for q in json.loads(path.read_text(encoding="utf-8")):
            s = split_of[concept(q["gold_item_key"])]
            total[s] += 1
            if q["text"].casefold() == gold[q["gold_item_key"]]:
                hit[(s, "+".join(q["modification_types"]))] += 1
                if name == "OE_single_texto.json" and s == "test":
                    test_keys.append(q["item_key"])
        print(f"  {name}: dev {sum(v for (s, _), v in hit.items() if s == 'dev')} of {total['dev']}, "
              f"test {sum(v for (s, _), v in hit.items() if s == 'test')} of {total['test']}")
        for (s, t), v in sorted(hit.items()):
            print(f"    {s} {t}: {v}")

    if exclusion_path is not None:
        exclusion_path.write_text(json.dumps({
            "reason": "P8: SINGLE test synonym_label queries whose synonym is a case variant "
                      "of the label; equal to the gold TEXTO after lower-casing (D-044)",
            "file": "OE_single_texto.json",
            "split": "test",
            "item_keys": sorted(test_keys),
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nexclusion list: {len(test_keys)} keys -> {exclusion_path}")
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    sys.exit(main(Path(args[0]) if args else DEFAULT_SPLITS,
                  Path(args[1]) if len(args) > 1 else None))
