"""Wider L2 slices (retrieval WIDER_THIN_SLICES.md, accepted as D-043): extra
SINGLE queries of `paraphrase`, `expansion` and `compression` from the frozen
OE menus, over the full delivered corpus.

Per type: every concept where an approved rewrite is compatible with a leaf and
visible in its TEXTO (the E3 judgement: `_leaf_candidates` + `TextoSurface`),
up to `--per-concept` leaves per concept in a fixed crc32 order, one variant per
(leaf, type) via `build_probe_plan` (least-used rewrite first). Rendered with
`require_texto_changed`, and every counted modification must show in the TEXTO.

Adds ONLY new files: `OE_single_l2_texto.json`, its modifications sidecar and
its provenance. `OE_single_texto.json` and the rest of the handoff are not
touched (never run `package_for_retrieval.py` for this). Queries already in
SINGLE (same item_key or same text) are dropped, so the file is additive.

Deterministic, no LLM. Run (PYTHONPATH=src):

  python scripts/build_single_l2.py --source data/raw/BPA_2026.bc3
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import pandas as pd  # noqa: E402

from build_dose_ladder import _fail_on_invisible  # noqa: E402
from package_for_retrieval import _jsonable, _sha256, _sid, git_commit  # noqa: E402
from synthetic import bc3param_backend, dose_ladder  # noqa: E402
from synthetic.corpus_driver import run_corpus  # noqa: E402
from synthetic.corpus_sampler import leaf_inventory_from_frames  # noqa: E402
from synthetic.pantry import Pantry, load_pantry  # noqa: E402
from synthetic.taxonomy import ModificationType as MT  # noqa: E402

L2 = (MT.PARAPHRASE, MT.EXPANSION, MT.COMPRESSION)
SYN = REPO / "data" / "synthetic"


def select_leaves(pantry, inventory, surface, mtype, per_concept):
    """{concept: leaves} where `mtype` is visible, at most `per_concept` each,
    taken in crc32 order (never a sorted prefix: a leaf key spells its axis
    values, so a prefix would keep only the first axis's low values)."""
    concept_of = dose_ladder.leaf_concept_map(inventory)
    applicable: dict[str, dict] = {}
    eligible: dict[str, list[str]] = defaultdict(list)
    for leaf, concept in sorted(concept_of.items()):
        if concept not in applicable:
            applicable[concept] = pantry.for_concept(concept)
        cands = dose_ladder._leaf_candidates(applicable[concept], inventory, leaf, concept, surface)
        if mtype in cands:
            eligible[concept].append(leaf)
    order = lambda leaf: (zlib.crc32(leaf.encode("utf-8")), leaf)  # noqa: E731
    return {c: sorted(v, key=order)[:per_concept] for c, v in sorted(eligible.items())}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-json", default=str(SYN / "intermediate" / "OE_2026_stage.json"))
    ap.add_argument("--menus-dir", default=str(SYN / "menus_OE"))
    ap.add_argument("--target-long", default=str(SYN / "processed_OE" / "OE_target_long.parquet"))
    ap.add_argument("--target-short", default=str(SYN / "processed_OE" / "OE_target_short.parquet"))
    ap.add_argument("--per-concept", type=int, default=20)
    ap.add_argument("--out-release", default=str(SYN / "processed_OE_single_l2"))
    ap.add_argument("--handoff", default=str(SYN / "handoff_OE"))
    ap.add_argument("--report", default=str(REPO / "docs" / "synthetic" / "sprints" / "SINGLE_L2_qa.md"))
    ap.add_argument("--source", default=None, help="BC3 catalogue for bc3param")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()

    if a.source:
        bc3param_backend.set_source(a.source)
    stage = json.loads(Path(a.stage_json).read_text(encoding="utf-8"))
    inventory = leaf_inventory_from_frames(
        pd.read_parquet(a.target_long), pd.read_parquet(a.target_short), text_field="texto",
    )
    surface = dose_ladder.TextoSurface.from_stage(stage)
    pantry = load_pantry(Path(a.menus_dir))

    plan = []
    for mtype in L2:
        only = Pantry(by_type={mtype: pantry.by_type[mtype]})
        chosen = select_leaves(only, inventory, surface, mtype, a.per_concept)
        leaves = [leaf for v in chosen.values() for leaf in v]
        part = dose_ladder.build_probe_plan(only, inventory, leaves, surface=surface)
        print(f"[L2] {mtype.value}: {len(chosen)} concepts, {len(part)} planned")
        plan.extend(part)

    stats = run_corpus(
        stage, plan, out_dir=Path(a.out_release), report_path=Path(a.report),
        workers=a.workers, require_texto_changed=True,
    )
    _fail_on_invisible(stats, "single_l2")

    # ----- package: SINGLE schema, additive to OE_single_texto.json ---------
    handoff = Path(a.handoff)
    single = json.loads((handoff / "OE_single_texto.json").read_text(encoding="utf-8"))
    old_keys = {r["item_key"] for r in single}
    old_texts = {r["text"] for r in single}
    gold_keys = set(pd.read_parquet(a.target_long, columns=["item_key"])["item_key"])
    meta = {k: {"ud": v.get("ud", ""), "concept": v.get("concept", "")} for k, v in stage.items()}

    items = pd.read_parquet(stats.items_path)
    records, dropped = [], Counter()
    for r in items.itertuples(index=False):
        mtypes = list(r.modification_types) if not isinstance(r.modification_types, str) \
            else json.loads(r.modification_types)
        if len(mtypes) != 1 or MT(mtypes[0]) not in L2 or int(r.modification_count) != 1:
            raise SystemExit(f"not_single_l2: {r.item_key} {mtypes}")
        if r.original_key not in gold_keys:
            raise SystemExit(f"gold_unresolved: {r.item_key} -> {r.original_key}")
        if r.item_key in old_keys:
            dropped["same_item_key_as_single"] += 1
            continue
        if r.texto in old_texts:
            dropped["same_text_as_single"] += 1
            continue
        m = meta.get(r.concept_key, {"ud": "", "concept": r.concept_key})
        records.append({
            "id": _sid(r.item_key), "item_key": r.item_key,
            "parent_key": r.concept_key, "gold_item_key": r.original_key,
            "ud": m["ud"], "concept": m["concept"],
            "parameters": _jsonable(r.params), "text": r.texto,
            "modification_types": mtypes, "modification_count": 1,
        })
    kept = {r["item_key"] for r in records}

    out_q = handoff / "OE_single_l2_texto.json"
    out_q.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    out_m = handoff / "OE_single_l2_modifications.jsonl"
    lines = [line for line in Path(stats.modifications_path).read_text(encoding="utf-8").splitlines()
             if line.strip() and json.loads(line)["item_key"] in kept]
    out_m.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    provenance = {
        "request": "bc3cat-retrieval WIDER_THIN_SLICES.md (D-043)",
        "script": "scripts/build_single_l2.py",
        "commit": git_commit(),
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "menus": "data/synthetic/menus_OE (frozen)",
        "per_concept": a.per_concept,
        "selection": "crc32 leaf order per concept; least-used rewrite first",
        "queries": len(records),
        "dropped_as_already_in_single": dict(dropped),
        "files": {p.name: _sha256(p) for p in (out_q, out_m)},
    }
    (handoff / "OE_single_l2_provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(json.dumps({k: provenance[k] for k in ("queries", "dropped_as_already_in_single", "files")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
