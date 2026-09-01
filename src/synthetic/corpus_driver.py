"""Sprint 39 corpus driver — materialise the sampling plan into the frozen release.

Consumes the deterministic :mod:`synthetic.corpus_sampler` plan (built from the
approved :mod:`synthetic.pantry`) and drives the frozen generation seam per
:class:`~synthetic.corpus_sampler.PlannedVariant`:

``rule_emitter.emit_rules`` (one call per rewrite) → ``composition.compose_rules``
→ ``variant_catalog.VariantRecord`` → ``stage_b.materialize_variant`` → extract
the planned leaf → filters → ``packaging.write_release`` + Markdown QA report.

The Sprint-26 ``l2_repr`` bracket is copied verbatim from ``f1_pilot.run_pilot``:

  enum = list_to_formula(stage, include_conditional=True)   # emission + scan
  appl = list_to_formula(stage, include_conditional=False)  # application view
  materialize_variant(appl, ..., pre_rerun=formula_to_list) # restore + rerun

**Target-id re-derivation (Task-1 approved deviation):** the on-disk menu
usages carry ``slot_extractor_target_id=None`` (dropped at serialization), so
this driver re-derives them by scanning the enum view once with
:func:`target_scanner.scan_chapter` and joining pantry rewrites to scanned
targets on ``(modification_type, dedup_key)``; the matching usage for the
planned concept supplies the target id. A rewrite whose target no longer scans
is skipped and counted (``target_not_found``), never crashed on.

**Leaf correspondence:** the pilot excludes ``new_param``, and L1 mutations
rewrite value *texts*, never value *labels* (``layer_l1._replace_value``), so
``stage_runners.transform_data`` regenerates the mutated leaf under the very
same ``item_key`` — the planned ``leaf_item_key`` indexes the mutated items
directly and becomes ``original_key`` (mirrors ``metadata.join_variant_payload``
with ``k == 0``).

Filters: a no-op variant (both texts identical to the leaf's originals) and an
exact ``(resumen, texto)`` duplicate within the corpus are dropped + counted —
the no-op filter is a backstop: the sampler's leaf↔rewrite compatibility
(original-text match) should keep its count at ~0, and the report shows it;
unresolved ``$``-placeholder or ``[[`` residue in an output text **raises**
(that would be a bug, not data). No LLM anywhere; generation is pure CPU.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Sequence

import re

from utils import config
from . import l2_repr, stage_runners, target_scanner
from .composition import compose_rules
from .corpus_sampler import (
    CONDITIONS,
    Budgets,
    PlannedVariant,
    build_plan,
    leaf_inventory_from_frames,
    load_budgets,
)
from .metadata import SyntheticItem, _SYN_MARK
from .packaging import write_release
from .pantry import ApprovedRewrite, load_pantry
from .rule_emitter import _L1_LIST_KEY, emit_rules
from .stage_b import materialize_variant
from .taxonomy import ModificationType
from .variant_catalog import VariantRecord

__all__ = [
    "ResidueError",
    "CorpusRunStats",
    "run_corpus",
    "main",
]

DEFAULT_REPORT_PATH = (
    config.REPO_ROOT / "docs" / "synthetic" / "sprints" / "SPRINT_39_corpus_report.md"
)
DEFAULT_INVENTORY_LONG_PARQUET = config.PROCESSED_DIR / "OEB_long_norm.parquet"
DEFAULT_INVENTORY_SHORT_PARQUET = config.PROCESSED_DIR / "OEB_short_norm.parquet"

# Unresolved template/variable residue in a *rendered* output text. `$X`
# survivors and `[[...]]` scaffolding both mean the pipeline mis-rendered.
_RESIDUE_RE = re.compile(r"\$[A-Za-z0-9]|\[\[")

_ALL_COMBINED = "all_combined"

# Per-condition counter keys, in report order.
_COUNTER_KEYS = (
    "planned",
    "produced",
    "noop_dropped",
    "dup_dropped",
    "emission_failed",
    "composition_conflicts",
    "target_not_found",
    "leaf_missing",
)


class ResidueError(ValueError):
    """An output text carries unresolved placeholder residue. A bug, not data."""


@dataclass(frozen=True)
class CorpusRunStats:
    """Per-condition + global accounting of one `run_corpus` invocation."""

    per_condition: dict[str, dict]
    totals: dict[str, int]
    items_path: Path
    modifications_path: Path
    report_path: Path


# ----- target-id re-derivation --------------------------------------------


def _target_lookup(
    inventory: target_scanner.ChapterInventory,
) -> dict[tuple[ModificationType, tuple], dict[str, object]]:
    """`(mtype, dedup_key) -> {concept_key: slot_extractor_target_id}`."""
    out: dict[tuple[ModificationType, tuple], dict[str, object]] = {}
    for mtype, targets in inventory.by_type.items():
        for target in targets:
            per_concept = out.setdefault((mtype, target.dedup_key), {})
            for usage in target.usages:
                per_concept.setdefault(usage.concept_key, usage.slot_extractor_target_id)
    return out


def _emission_payload(
    rewrite: ApprovedRewrite,
    enum_stage: dict,
    concept_key: str,
    target_id: object,
) -> dict:
    """Adapt a pantry payload to the shape `rule_emitter.emit_rules` expects.

    L1 menu candidates are per-value `{"original", "new"}` dicts; the emitter
    consumes them wrapped in the per-type list key (`synonyms` / `numerals`).
    The scanner (and hence the menus) whitespace-normalises value texts
    (`target_scanner._norm`), while the emitter matches the concept's *raw*
    value strings (e.g. `' 12 '`), so each L1 `original` is aligned back to
    the raw value whose normalisation it equals. Every other family's payload
    passes through unchanged.
    """
    list_key = _L1_LIST_KEY.get(rewrite.mtype)
    if list_key is None:
        return dict(rewrite.payload)
    entries = (
        rewrite.payload[list_key]
        if list_key in rewrite.payload
        else [dict(rewrite.payload)]
    )
    values = enum_stage[concept_key]["parameters"][target_id]["values"]
    raw_values = {v.get("value") for v in values}
    by_norm: dict[str, str] = {}
    for v in values:
        by_norm.setdefault(target_scanner._norm(str(v.get("value", ""))), v["value"])
    aligned = []
    for entry in entries:
        entry = dict(entry)
        original = entry.get("original")
        if original not in raw_values:
            raw = by_norm.get(target_scanner._norm(str(original)))
            if raw is not None:
                entry["original"] = raw
        aligned.append(entry)
    return {list_key: aligned}


# ----- helpers -------------------------------------------------------------


def _token_distance(a: str, b: str) -> int:
    """Whitespace-token insert/delete edit distance (deterministic, stdlib)."""
    ta, tb = a.split(), b.split()
    matcher = SequenceMatcher(a=ta, b=tb, autojunk=False)
    matching = sum(block.size for block in matcher.get_matching_blocks())
    return len(ta) + len(tb) - 2 * matching


def _check_residue(planned: PlannedVariant, field: str, text: str) -> None:
    match = _RESIDUE_RE.search(text)
    if match:
        raise ResidueError(
            f"placeholder_residue: {match.group(0)!r} in {field} of leaf "
            f"{planned.leaf_item_key!r} (condition {planned.condition!r}, "
            f"concept {planned.concept_key!r}): {text!r}"
        )


def _variante_id(planned: PlannedVariant) -> str:
    uids = sorted(r.uid for r in planned.rewrites)
    blob = "|".join(
        [planned.condition, planned.concept_key, planned.leaf_item_key, *uids]
    )
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def _new_condition_row() -> dict:
    row: dict = {k: 0 for k in _COUNTER_KEYS}
    row["unique_rewrites"] = 0
    row["max_reuse"] = 0
    row["mean_token_distance"] = 0.0
    return row


# ----- the driver -----------------------------------------------------------


def run_corpus(
    stage2_json: dict,
    plan: Sequence[PlannedVariant],
    *,
    out_dir: Optional[Path] = None,
    report_path: Optional[Path] = None,
    budgets: Optional[Budgets] = None,
) -> CorpusRunStats:
    """Materialise `plan` against `stage2_json` into the frozen release + report.

    `out_dir` defaults to `config.SYNTHETIC_PROCESSED_DIR`; `report_path` to
    `docs/synthetic/sprints/SPRINT_39_corpus_report.md`. `budgets`, when given,
    supplies the per-condition targets the report compares against (else the
    planned n doubles as the target). Deterministic: same inputs → byte-identical
    release files.
    """
    report_path = DEFAULT_REPORT_PATH if report_path is None else Path(report_path)

    # The f1_pilot l2_repr bracket — one enum view for emission + scan, one
    # apply view for materialisation, formula_to_list restored before rerun.
    enum_stage, _enum_report = l2_repr.list_to_formula(
        stage2_json, include_conditional=True,
    )
    appl_stage, _appl_report = l2_repr.list_to_formula(
        stage2_json, include_conditional=False,
    )
    inventory = target_scanner.scan_chapter(enum_stage, apply_l2_conversion=False)
    lookup = _target_lookup(inventory)

    stats: dict[str, dict] = {}
    uses: dict[str, Counter] = {}
    distances: dict[str, int] = {}
    presence: Counter = Counter()
    baselines: dict[str, dict] = {}
    seen_texts: set[tuple[str, str]] = set()
    items: list[SyntheticItem] = []

    def _row(condition: str) -> dict:
        if condition not in stats:
            stats[condition] = _new_condition_row()
            uses[condition] = Counter()
            distances[condition] = 0
        return stats[condition]

    for planned in plan:
        row = _row(planned.condition)
        row["planned"] += 1
        concept_key = planned.concept_key

        # -- emission: one emit_rules call per rewrite -----------------------
        rules: list[dict] = []
        target_ids: list[object] = []
        skip = None
        for rewrite in planned.rewrites:
            per_concept = lookup.get((rewrite.mtype, rewrite.dedup_key))
            if per_concept is None or concept_key not in per_concept:
                skip = "target_not_found"
                break
            target_id = per_concept[concept_key]
            try:
                emitted = emit_rules(
                    _emission_payload(rewrite, enum_stage, concept_key, target_id),
                    rewrite.mtype,
                    target_id=target_id,
                    stage_json=enum_stage,
                    concept_key=concept_key,
                )
            except (KeyError, ValueError, TypeError):
                emitted = None
            if emitted is None or not emitted.rules:
                skip = "emission_failed"
                break
            rules.extend(emitted.rules)
            target_ids.append((rewrite.mtype.value, repr(target_id)))
        if skip is not None:
            row[skip] += 1
            continue

        # -- composition: conflict → skip + count, never raise ---------------
        composed, comp_skipped = compose_rules(rules)
        if comp_skipped or not composed:
            row["composition_conflicts"] += 1
            continue

        record = VariantRecord(
            condition=planned.condition,
            modification_type=ModificationType(composed[0]["type"]),
            target_id_repr=repr(tuple(target_ids)),
            rules=tuple(composed),
        )

        # -- materialise + extract THE planned leaf --------------------------
        materialized = materialize_variant(
            appl_stage, concept_key, record, pre_rerun=l2_repr.formula_to_list,
        )
        if concept_key not in baselines:
            baselines[concept_key] = stage_runners.run_stages_3_to_7(
                l2_repr.formula_to_list({concept_key: appl_stage[concept_key]})
            )
        baseline = baselines[concept_key]
        leaf_key = planned.leaf_item_key
        if leaf_key not in materialized.items or leaf_key not in baseline:
            row["leaf_missing"] += 1
            continue
        synthetic = materialized.items[leaf_key]
        original = baseline[leaf_key]
        resumen, texto = synthetic["resumen"], synthetic["texto"]

        # -- residue is a bug: raise, never filter ---------------------------
        _check_residue(planned, "resumen", resumen)
        _check_residue(planned, "texto", texto)

        # -- filters: no-op, then exact corpus-wide dedup --------------------
        if resumen == original["resumen"] and texto == original["texto"]:
            row["noop_dropped"] += 1
            continue
        if (resumen, texto) in seen_texts:
            row["dup_dropped"] += 1
            continue
        seen_texts.add((resumen, texto))

        variante_id = _variante_id(planned)
        params = {
            axis_id: axis["values"][0]["value"]
            for axis_id, axis in (synthetic.get("parameters") or {}).items()
        }
        items.append(
            SyntheticItem(
                item_key=f"{leaf_key}{_SYN_MARK}{variante_id}",
                original_key=leaf_key,
                params=params,
                resumen=resumen,
                texto=texto,
                variante_id=variante_id,
                modification_types=materialized.modification_types,
                modification_count=len(materialized.modifications),
                modifications=materialized.modifications,
                concept_key=concept_key,
            )
        )
        row["produced"] += 1
        for rewrite in planned.rewrites:
            uses[planned.condition][rewrite.uid] += 1
            if planned.condition == _ALL_COMBINED:
                presence[rewrite.mtype.value] += 1
        distances[planned.condition] += _token_distance(
            original["resumen"], resumen
        ) + _token_distance(original["texto"], texto)

    # -- finalize per-condition stats ---------------------------------------
    for condition, row in stats.items():
        use = uses[condition]
        row["unique_rewrites"] = len(use)
        row["max_reuse"] = max(use.values()) if use else 0
        row["mean_token_distance"] = (
            distances[condition] / row["produced"] if row["produced"] else 0.0
        )
        if budgets is not None:
            row["target"] = budgets.targets.get(condition, row["planned"])
        else:
            row["target"] = row["planned"]
        row["deficit"] = row["target"] - row["produced"]
    if _ALL_COMBINED in stats:
        stats[_ALL_COMBINED]["type_presence"] = dict(sorted(presence.items()))

    totals: dict[str, int] = {k: sum(r[k] for r in stats.values()) for k in _COUNTER_KEYS}

    # -- release + report ----------------------------------------------------
    paths = write_release(items, out_dir=out_dir)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_format_report(stats, totals), encoding="utf-8")

    return CorpusRunStats(
        per_condition=stats,
        totals=totals,
        items_path=paths["items"],
        modifications_path=paths["modifications"],
        report_path=report_path,
    )


# ----- report ---------------------------------------------------------------

_REPORT_COLUMNS = (
    ("condition", "condition"),
    ("produced", "n"),
    ("target", "target"),
    ("deficit", "deficit"),
    ("unique_rewrites", "unique rewrites"),
    ("max_reuse", "max reuse"),
    ("noop_dropped", "no-ops"),
    ("dup_dropped", "dups"),
    ("emission_failed", "emission skips"),
    ("composition_conflicts", "composition skips"),
    ("target_not_found", "target-not-found"),
    ("leaf_missing", "leaf-missing"),
    ("mean_token_distance", "mean tok dist"),
)


def _format_report(stats: dict[str, dict], totals: dict[str, int]) -> str:
    lines = [
        "# Sprint 39 — pilot synthetic corpus QA report",
        "",
        "Generated by `synthetic.corpus_driver` (deterministic, no LLM).",
        "`mean tok dist` = mean whitespace-token insert/delete distance to the",
        "original leaf, summed over (resumen, texto).",
        "",
        "| " + " | ".join(label for _, label in _REPORT_COLUMNS) + " |",
        "|" + "---|" * len(_REPORT_COLUMNS),
    ]
    ordered = [c for c in CONDITIONS if c in stats] + [
        c for c in stats if c not in CONDITIONS
    ]
    for condition in ordered:
        row = stats[condition]
        cells = [condition]
        for key, _label in _REPORT_COLUMNS[1:]:
            value = row.get(key, 0)
            cells.append(f"{value:.2f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    presence = stats.get(_ALL_COMBINED, {}).get("type_presence")
    if presence is not None:
        lines.append("**all_combined type presence** (variants carrying ≥1 rewrite of the type):")
        lines.append("")
        for mtype, count in presence.items():
            lines.append(f"- {mtype}: {count}")
        lines.append("")

    lines.append("## Totals")
    lines.append("")
    for key in _COUNTER_KEYS:
        lines.append(f"- {key}: {totals.get(key, 0)}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI — thin wrapper (Task 5's invocation; no LLM anywhere)
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.corpus_driver")
    sub = parser.add_subparsers(dest="cmd")

    run = sub.add_parser("run", help="materialise the sampling plan into the release")
    run.add_argument("--stage-json", required=True)
    run.add_argument(
        "--concepts", required=True,
        help="comma-separated concept-key prefixes (e.g. OEB)",
    )
    run.add_argument("--budgets", default=None)
    run.add_argument("--out-dir", default=None)
    run.add_argument("--report", default=None)
    run.add_argument("--menus-dir", default=None)
    run.add_argument(
        "--inventory-long-parquet", default=None,
        help="original long (texto) parquet; default OEB_long_norm.parquet",
    )
    run.add_argument(
        "--inventory-short-parquet", default=None,
        help="original short (resumen) parquet; default OEB_short_norm.parquet",
    )

    args = parser.parse_args(argv)
    if args.cmd != "run":
        parser.print_usage(sys.stderr)
        return 2

    import pandas as pd

    stage_json = json.loads(Path(args.stage_json).read_text(encoding="utf-8"))
    prefixes = tuple(p for p in args.concepts.split(",") if p)
    concepts = [
        k for k in stage_json if k.endswith("$") and k.startswith(prefixes)
    ]
    pantry = load_pantry(Path(args.menus_dir) if args.menus_dir else None)
    budgets = load_budgets(Path(args.budgets) if args.budgets else None)
    long_frame = pd.read_parquet(
        Path(args.inventory_long_parquet)
        if args.inventory_long_parquet
        else DEFAULT_INVENTORY_LONG_PARQUET
    )
    short_frame = pd.read_parquet(
        Path(args.inventory_short_parquet)
        if args.inventory_short_parquet
        else DEFAULT_INVENTORY_SHORT_PARQUET
    )
    inventory = leaf_inventory_from_frames(long_frame, short_frame)
    plan = build_plan(pantry, inventory, budgets, concepts)
    stats = run_corpus(
        stage_json,
        plan,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        report_path=Path(args.report) if args.report else None,
        budgets=budgets,
    )
    print(
        json.dumps(
            {
                "planned": stats.totals["planned"],
                "produced": stats.totals["produced"],
                "items": str(stats.items_path),
                "modifications": str(stats.modifications_path),
                "report": str(stats.report_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
