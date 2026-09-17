"""E3 — build the balanced dose ladder + isolated-effects set (spec: E3_DOSE_DESIGN.md).

Two passes over the SAME shared base-leaf sample the OE ablation corpora use, so
every dose item is paired on the same leaf as its stacked/single counterparts:

1. PROBE — one single-modification variant per (leaf, available type), TEXTO
   only, over the structurally pre-filtered candidates. Its surviving items give
   `available_types` per leaf and, restricted to the pool, the isolated-effects
   deliverable (D6).
2. DOSE — dose_1..dose_5 over the common pool, nested composition (D4/D5).

Deterministic, no LLM. Run (PYTHONPATH=src):

  python scripts/build_dose_ladder.py \
    --stage-json   data/synthetic/intermediate/OE_2026_stage.json \
    --menus-dir    data/synthetic/menus_OE \
    --inventory-long  data/synthetic/processed_OE/OE_ablation_inventory_long.parquet \
    --inventory-short data/synthetic/processed_OE/OE_ablation_inventory_short.parquet \
    --probe-budgets configs/synthetic/variant_budgets_OE_probe.yaml \
    --dose-budgets  configs/synthetic/variant_budgets_OE_dose.yaml \
    --concepts OE \
    --out-probe data/synthetic/processed_OE_probe \
    --out-dose  data/synthetic/processed_OE_dose \
    --applicability data/synthetic/handoff_OE/OE_leaf_applicability.jsonl \
    --report-probe docs/synthetic/sprints/E3_probe_qa.md \
    --report-dose  docs/synthetic/sprints/E3_dose_qa.md \
    --source data/raw/BPA_2026.bc3
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from synthetic import bc3param_backend, dose_ladder  # noqa: E402
from synthetic.corpus_driver import run_corpus  # noqa: E402
from synthetic.corpus_sampler import leaf_inventory_from_frames  # noqa: E402
from synthetic.pantry import Pantry, load_pantry  # noqa: E402
from synthetic.target_scanner import scan_chapter  # noqa: E402
from synthetic.taxonomy import ModificationType  # noqa: E402

#: L3 types whose rewrites must be restricted to their TEXTO-field variant, so
#: one modification always moves the TEXTO and counts once, not twice (D3).
_TEXTO_FIELD_TYPES = (
    ModificationType.TEMPLATE_PARAPHRASE,
    ModificationType.REORDER,
)


def _texto_only_pantry(pantry: Pantry) -> Pantry:
    """Keep only the TEXTO-field rewrites of the L3 types (D3).

    Same transform the OE SINGLE corpus applied via `--texto-fields-only`; here
    it is unconditional, because every E3 item must change the TEXTO.
    """
    keep = set(_TEXTO_FIELD_TYPES)
    by_type = {
        mt: (tuple(r for r in rws if str(r.dedup_key[0]) == "TEXTO")
             if mt in keep else rws)
        for mt, rws in pantry.by_type.items()
    }
    return Pantry(by_type={mt: rws for mt, rws in by_type.items() if rws})


def _surviving_types(items_path: Path) -> dict[str, frozenset]:
    """`{leaf: types whose probe item survived}` — read back from the probe
    release. A type survives when its single-modification item was emitted,
    which (with --require-texto-changed) means it really changed the TEXTO."""
    frame = pd.read_parquet(items_path)
    out: dict[str, set] = {}
    for original_key, mtypes in zip(frame["original_key"], frame["modification_types"]):
        types = list(mtypes) if not isinstance(mtypes, str) else json.loads(mtypes)
        out.setdefault(original_key, set()).update(
            ModificationType(t) for t in types
        )
    return {k: frozenset(v) for k, v in out.items()}


def applicability_rows(available, structural, dose_plan) -> list[dict]:
    """One sidecar row per probed leaf, sorted by leaf.

    ``in_pool`` marks the leaves that got a ladder, not every leaf
    `select_pool` returned: the pool carries a reserve (``pool_min >
    per_count``) and an unused reserve leaf has no ladder, so delivering its
    isolated effects (D6) would pair them with dose effects that do not exist.
    """
    ladder_leaves = {p.leaf_item_key for p in dose_plan}
    return [
        {
            "leaf_item_key": leaf,
            "applicable_types": sorted(t.value for t in structural.get(leaf, ())),
            "available_types": sorted(t.value for t in available[leaf]),
            "in_pool": leaf in ladder_leaves,
        }
        for leaf in sorted(available)
    ]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-json", required=True)
    ap.add_argument("--menus-dir", required=True)
    ap.add_argument("--inventory-long", required=True)
    ap.add_argument("--inventory-short", required=True)
    ap.add_argument("--probe-budgets", required=True)
    ap.add_argument("--dose-budgets", required=True)
    ap.add_argument("--concepts", default="OE")
    ap.add_argument("--out-probe", required=True)
    ap.add_argument("--out-dose", required=True)
    ap.add_argument("--applicability", required=True)
    ap.add_argument(
        "--report-probe", required=True,
        help="QA report path for the probe pass. Required on purpose: "
             "run_corpus falls back to the Sprint-39 pilot report, which "
             "belongs to an already-delivered corpus.",
    )
    ap.add_argument(
        "--report-dose", required=True,
        help="QA report path for the dose pass. Required for the same reason, "
             "and it must differ from --report-probe or the second pass "
             "overwrites the first.",
    )
    ap.add_argument("--source", default=None, help="BC3 catalogue for bc3param")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()

    if Path(a.report_probe) == Path(a.report_dose):
        raise SystemExit(
            "report_paths_collide: --report-probe and --report-dose must differ; "
            "the second pass would overwrite the first pass's report"
        )

    if a.source:
        bc3param_backend.set_source(a.source)

    stage_json = json.loads(Path(a.stage_json).read_text(encoding="utf-8"))
    prefixes = tuple(p for p in a.concepts.split(",") if p)
    concepts = [k for k in stage_json if k.endswith("$") and k.startswith(prefixes)]
    if not concepts:
        raise SystemExit(f"no concepts match prefixes {prefixes!r}")

    pantry = _texto_only_pantry(load_pantry(Path(a.menus_dir)))
    probe_budgets = dose_ladder.load_dose_budgets(Path(a.probe_budgets))
    dose_budgets = dose_ladder.load_dose_budgets(Path(a.dose_budgets))

    # Cross-config invariant, enforceable only here: `load_dose_budgets` sees one
    # file at a time, but the probe's structural_threshold/candidate_cap decide
    # which leaves ever reach the pool, and the dose config carries descriptive
    # copies of both. A drift — someone tuning the probe and forgetting the dose
    # file — would silently mean the pool was selected under different terms than
    # the config documents, so fail loud instead.
    for field in ("structural_threshold", "candidate_cap"):
        pv, dv = getattr(probe_budgets, field), getattr(dose_budgets, field)
        if pv != dv:
            raise SystemExit(
                f"config_drift: {field} is {pv} in {a.probe_budgets} but {dv} in "
                f"{a.dose_budgets}. The probe's value is what actually governs "
                f"which leaves reach the pool; the dose copy is descriptive. "
                f"Make them agree."
            )

    long_df = pd.read_parquet(a.inventory_long)
    short_df = pd.read_parquet(a.inventory_short)
    # compatibility is judged against the TEXTO alone: a rewrite surfacing only
    # in the resumen must not count (refinement 1 of the plan)
    inventory = leaf_inventory_from_frames(long_df, short_df, text_field="texto")

    chapter = scan_chapter(stage_json, concept_filter=lambda k: k.startswith(prefixes))

    # ----- structural pre-filter (no renders) -----------------------------
    candidates = dose_ladder.candidate_leaves(
        chapter, inventory,
        threshold=probe_budgets.structural_threshold,
        cap=probe_budgets.candidate_cap,
    )
    print(f"[E3] candidatas tras el pre-filtro estructural: {len(candidates)}")

    # ----- pass 1: probe --------------------------------------------------
    probe_plan = dose_ladder.build_probe_plan(pantry, inventory, candidates)
    print(f"[E3] sondeo planificado: {len(probe_plan)} items")
    probe_stats = run_corpus(
        stage_json, probe_plan,
        out_dir=Path(a.out_probe),
        report_path=Path(a.report_probe),
        budgets=probe_budgets.to_driver_budgets(),
        workers=a.workers,
        require_texto_changed=True,
    )
    available = _surviving_types(Path(probe_stats.items_path))
    print(f"[E3] sondeo producido: {probe_stats.totals['produced']} items; "
          f"hojas con >=1 tipo disponible: {len(available)}")

    # ----- pool ------------------------------------------------------------
    # Types of one family compete for the same span, so a leaf can have more
    # available types than modifications that fit together. Only leaves where
    # a full ladder fits may enter the pool; D5's depth still counts types.
    rewrites = dose_ladder.leaf_rewrites(pantry, inventory, available)
    placeable = {
        leaf: dose_ladder.placeable_depth(
            {t: frozenset(r.dedup_key for r in rws) for t, rws in by_type.items()}
        )
        for leaf, by_type in rewrites.items()
    }
    placeable_histogram = dict(sorted(Counter(placeable.values()).items()))
    fits = {
        leaf: types for leaf, types in available.items()
        if placeable[leaf] >= dose_ladder.LADDER_MAX
    }
    histogram = dose_ladder.depth_histogram(available)
    concept_of = dose_ladder.leaf_concept_map(inventory)
    depth, pool = dose_ladder.select_pool(
        fits,
        concept_of,
        pool_min=dose_budgets.effective_pool_min,
        min_depth=dose_budgets.structural_threshold,
    )
    print(f"[E3] profundidad elegida d={depth}; fondo={len(pool)} hojas; "
          f"histograma={histogram}; caben en tramos distintos={placeable_histogram}")

    # ----- pass 2: dose ladder --------------------------------------------
    order = dose_ladder.nested_order(
        {leaf: available[leaf] for leaf in pool}, seed=dose_budgets.seed,
        rewrites=rewrites, reuse_cap=dose_budgets.reuse_cap,
    )
    dose_plan = dose_ladder.build_dose_plan(
        pantry, inventory, order, pool,
        reuse_cap=dose_budgets.reuse_cap, per_count=dose_budgets.per_count,
    )
    print(f"[E3] escalera planificada: {len(dose_plan)} items")
    dose_stats = run_corpus(
        stage_json, dose_plan,
        out_dir=Path(a.out_dose),
        report_path=Path(a.report_dose),
        budgets=dose_budgets.to_driver_budgets(),
        workers=a.workers,
        require_texto_changed=True,
    )

    # ----- applicability sidecar ------------------------------------------
    structural = {
        leaf: dose_ladder.structural_types(
            chapter, concept, inventory.text(leaf), inventory.axis_values(leaf),
        )
        for concept in inventory.concepts()
        for leaf in inventory.leaves(concept)
        if leaf in available
    }
    out_side = Path(a.applicability)
    out_side.parent.mkdir(parents=True, exist_ok=True)
    rows = applicability_rows(available, structural, dose_plan)
    with out_side.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(json.dumps({
        "candidates": len(candidates),
        "probe_produced": probe_stats.totals["produced"],
        "depth": depth,
        "pool": len(pool),
        "pool_leaves": sum(row["in_pool"] for row in rows),
        "dose_produced": dose_stats.totals["produced"],
        "depth_histogram": histogram,
        "placeable_histogram": placeable_histogram,
        "probe_items": str(probe_stats.items_path),
        "dose_items": str(dose_stats.items_path),
        "applicability": str(out_side),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
