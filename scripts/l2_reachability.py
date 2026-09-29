"""How far the frozen OE menus can take the L2 types (retrieval WIDER_THIN_SLICES.md).

For `paraphrase`, `expansion` and `compression`: the concepts and leaves where an
approved rewrite is compatible with the leaf AND visible in its TEXTO (the same
`_leaf_candidates` + `TextoSurface` judgement the E3 probe uses). No renders, no
LLM. Counts only, per split of bc3cat-retrieval's SPLITS.md.

Usage (PYTHONPATH=src): python scripts/l2_reachability.py [path/to/SPLITS.md]
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import pandas as pd  # noqa: E402

from audit_lookup_permutations import DEFAULT_SPLITS, load_splits  # noqa: E402
from synthetic import dose_ladder  # noqa: E402
from synthetic.corpus_sampler import leaf_inventory_from_frames  # noqa: E402
from synthetic.pantry import load_pantry  # noqa: E402
from synthetic.taxonomy import ModificationType as MT  # noqa: E402

L2 = (MT.PARAPHRASE, MT.EXPANSION, MT.COMPRESSION)
SYN = REPO / "data" / "synthetic"


def main(splits_path: Path = DEFAULT_SPLITS) -> int:
    split_of = load_splits(splits_path)
    stage = json.loads((SYN / "intermediate" / "OE_2026_stage.json").read_text(encoding="utf-8"))
    inventory = leaf_inventory_from_frames(
        pd.read_parquet(SYN / "processed_OE" / "OE_target_long.parquet"),
        pd.read_parquet(SYN / "processed_OE" / "OE_target_short.parquet"),
        text_field="texto",
    )
    surface = dose_ladder.TextoSurface.from_stage(stage)
    pantry = load_pantry(SYN / "menus_OE")
    concept_of = dose_ladder.leaf_concept_map(inventory)

    leaves = defaultdict(Counter)      # type -> concept -> reachable leaves
    rewrites = defaultdict(lambda: defaultdict(set))  # type -> concept -> rewrite uids
    applicable_by_concept = {}
    for leaf, concept in sorted(concept_of.items()):
        if concept not in applicable_by_concept:
            applicable_by_concept[concept] = pantry.for_concept(concept)
        cands = dose_ladder._leaf_candidates(
            applicable_by_concept[concept], inventory, leaf, concept, surface)
        for mtype in L2:
            if mtype in cands:
                leaves[mtype][concept] += 1
                rewrites[mtype][concept].update(r.uid for r in cands[mtype])

    print(f"inventory: {len(concept_of)} leaves, {len(set(concept_of.values()))} concepts")
    for mtype in L2:
        by_split = Counter(split_of[c] for c in leaves[mtype])
        leaves_split = Counter()
        capped = Counter()
        for c, n in leaves[mtype].items():
            leaves_split[split_of[c]] += n
            capped[split_of[c]] += min(n, 20)
        n_rw = Counter()
        for c, uids in rewrites[mtype].items():
            n_rw[split_of[c]] += len(uids)
        print(f"{mtype.value}: concepts dev {by_split['dev']} / test {by_split['test']}; "
              f"leaves dev {leaves_split['dev']} / test {leaves_split['test']}; "
              f"<=20 per concept dev {capped['dev']} / test {capped['test']}; "
              f"concept-rewrite pairs dev {n_rw['dev']} / test {n_rw['test']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*(Path(a) for a in sys.argv[1:2])))
