"""Sprint 39 corpus driver — materialise the sampling plan into the frozen release.

Consumes the deterministic :mod:`synthetic.corpus_sampler` plan (built from the
approved :mod:`synthetic.pantry`) and drives the frozen generation seam per
:class:`~synthetic.corpus_sampler.PlannedVariant`:

``rule_emitter.emit_rules`` (one call per rewrite per slot) →
``composition.compose_rules`` → ``variant_catalog.VariantRecord`` →
``stage_b.materialize_variant`` → extract the planned leaf → filters →
``packaging.write_release`` + Markdown QA report.

The Sprint-26 ``l2_repr`` bracket is copied verbatim from ``f1_pilot.run_pilot``:

  enum = list_to_formula(stage, include_conditional=True)   # emission + scan
  appl = list_to_formula(stage, include_conditional=False)  # application view
  materialize_variant(appl, ..., pre_rerun=formula_to_list) # restore + rerun

**Target-id re-derivation (Task-1 approved deviation):** the on-disk menu
usages carry ``slot_extractor_target_id=None`` (dropped at serialization), so
this driver re-derives them by scanning the enum view once with
:func:`target_scanner.scan_chapter` and joining pantry rewrites to scanned
targets on ``(modification_type, dedup_key)``. A rewrite whose target no longer
scans is skipped and counted (``target_not_found``), never crashed on.

**All-slot emission:** one ``(mtype, dedup_key)`` can occupy SEVERAL slots in
one concept (the same L2 fragment under different var/conditions, the same L1
value on different axes). The approved rewrite is for the surface TEXT wherever
it appears, so the driver emits one rule per slot and composes them all —
guaranteeing the planned leaf's slot is covered. One exception: when a single
var repeats the same fragment under several conditions, the frozen ``layer_l2``
sibling-collision guard lets only one slot take the new text, so the driver
keeps exactly the slot whose condition selects the planned leaf
(:func:`_select_slots`). Conceptually the variant still
carries ONE modification per distinct rewrite: ``modifications`` holds one
representative record per rewrite (the first applied record of its type from
the materialisation log), so ``modification_count == len(planned.rewrites)``.
(The frozen E2 validator couples ``modification_count`` to
``len(modifications)``, so the full multi-slot log cannot also ride the
sidecar; the representative record is the per-rewrite summary.)

**Leaf correspondence:** the pilot excludes ``new_param``, and L1 mutations
rewrite value *texts*, never value *labels* (``layer_l1._replace_value``), so
``stage_runners.transform_data`` regenerates the mutated leaf under the very
same ``item_key`` — the planned ``leaf_item_key`` indexes the mutated items
directly and becomes ``original_key`` (mirrors ``metadata.join_variant_payload``
with ``k == 0``).

**Grouped, parallel materialisation:** many planned variants share the exact
``(concept_key, composed-ruleset)`` (thin-type rewrites reused across leaves),
so the driver materialises each unique group ONCE and extracts every planned
leaf of the group from that single :class:`~synthetic.stage_b.MaterializedVariant`.
Group (and per-concept baseline) materialisations run on a
``concurrent.futures.ProcessPoolExecutor`` (module-level picklable workers;
``workers=1`` runs inline). Results are keyed by group id and merged in
deterministic sorted order — synthetic items are sorted by
``(condition, concept, leaf)`` before the filter/dedup pass, so output never
depends on completion order.

Filters: a no-op variant (both texts identical to the leaf's originals) and an
exact ``(resumen, texto)`` duplicate within the corpus are dropped + counted —
the no-op filter is a backstop: the sampler's boundary-aware leaf↔rewrite
compatibility should keep its count at ~0, and the report shows it;
unresolved ``$``-placeholder or ``[[`` residue in an output text **raises**
(that would be a bug, not data). No LLM anywhere; generation is pure CPU.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional, Sequence

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
from .stage_b import materialize_variant, materialize_variant_bc3param
from .bc3param_backend import render_base
from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER
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
) -> dict[tuple[ModificationType, tuple], dict[str, tuple]]:
    """`(mtype, dedup_key) -> {concept_key: (slot_id, ...)}` — ALL slots.

    A dedup key can occupy several slots in one concept (same L2 fragment
    under different var/conditions, same L1 value on different axes); every
    slot is kept, in the scanner's deterministic usage order.
    """
    out: dict[tuple[ModificationType, tuple], dict[str, list]] = {}
    for mtype, targets in inventory.by_type.items():
        for target in targets:
            per_concept = out.setdefault((mtype, target.dedup_key), {})
            for usage in target.usages:
                slots = per_concept.setdefault(usage.concept_key, [])
                if usage.slot_extractor_target_id not in slots:
                    slots.append(usage.slot_extractor_target_id)
    return {
        key: {ck: tuple(slots) for ck, slots in per_concept.items()}
        for key, per_concept in out.items()
    }


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


# ----- same-var duplicate-fragment slot selection ---------------------------


def _leaf_labels(
    enum_stage: dict, concept_key: str, leaf_item_key: str,
) -> Optional[dict[str, str]]:
    """`{axis: label}` for the planned leaf, from the repo's own key rule
    (`item_key = parent_key[:-1] + <one label per axis, in axes order>`).
    `None` when the suffix doesn't line up (multi-char labels — fall back)."""
    params = enum_stage[concept_key].get("parameters") or {}
    axes = list(params)
    suffix = leaf_item_key[len(concept_key) - 1:]
    if len(suffix) != len(axes):
        return None
    return dict(zip(axes, suffix))


def _condition_selects(condition: object, labels: dict[str, str]) -> bool:
    """Whether an L2 slot condition — Python-style (`%C=="b"`,
    `%B=="b" or %B=="g"`) or raw BC3-style (`%A=a`) — selects the leaf with
    these axis labels. Sandboxed eval (no builtins) of the condition with
    every `%X` replaced by the leaf's quoted label, BC3 `=` promoted to
    `==`, and bare label tokens quoted; anything unevaluable is
    conservatively False (caller falls back to the first slot)."""
    expr = re.sub(
        r"%([A-Za-z0-9]+)",
        lambda m: '"' + labels.get(m.group(1), "\x00") + '"',
        str(condition),
    )
    expr = re.sub(r"(?<![=<>!])=(?!=)", "==", expr)
    expr = re.sub(
        r'"[^"]*"|\b[A-Za-z][A-Za-z0-9]*\b',
        lambda m: m.group(0)
        if m.group(0).startswith('"') or m.group(0) in ("and", "or", "not")
        else '"' + m.group(0) + '"',
        expr,
    )
    try:
        return bool(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307
    except Exception:
        return False


def _select_slots(
    slots: tuple, leaf_labels: Optional[dict[str, str]],
) -> tuple:
    """All slots — except same-var duplicates, where the leaf's slot wins.

    When one text-variable carries the SAME fragment under several
    conditions, the frozen `layer_l2` sibling-collision guard lets only one
    of those slots take the new text — so keep exactly the slot whose
    condition selects the planned leaf (first slot as deterministic
    fallback). Slots on distinct vars/axes/fields all stay."""
    by_var: dict[str, list] = {}
    for slot in slots:
        if isinstance(slot, tuple) and len(slot) == 2:
            by_var.setdefault(slot[0], []).append(slot)
    chosen: dict[str, object] = {}
    for var, group in by_var.items():
        if len(group) <= 1:
            continue
        pick = group[0]
        if leaf_labels is not None:
            for slot in group:
                if _condition_selects(slot[1], leaf_labels):
                    pick = slot
                    break
        chosen[var] = pick
    out: list = []
    for slot in slots:
        if isinstance(slot, tuple) and len(slot) == 2 and slot[0] in chosen:
            if slot == chosen[slot[0]]:
                out.append(slot)
            continue
        out.append(slot)
    return tuple(out)


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


def _per_rewrite_modifications(
    rewrites: tuple[ApprovedRewrite, ...],
    materialized_mods: tuple[Modification, ...],
) -> tuple[Modification, ...]:
    """One representative `Modification` per distinct rewrite.

    All-slot emission (and L1↔L2 twin pairing) can log several records per
    rewrite; the release schema (E2) couples `modification_count` to
    `len(modifications)`, and conceptually the variant carries ONE
    modification per rewrite — so pick, per rewrite, the first unclaimed
    record of its type (applied preferred). A rewrite whose rules all
    silently failed to apply gets a synthesized `skipped` record (the item
    is then normally a no-op and filtered anyway).
    """
    claimed: set[int] = set()
    out: list[Modification] = []
    for rewrite in rewrites:
        found: Optional[int] = None
        for prefer_applied in (True, False):
            for i, mod in enumerate(materialized_mods):
                if i in claimed or mod.type is not rewrite.mtype:
                    continue
                if prefer_applied and mod.status != "applied":
                    continue
                found = i
                break
            if found is not None:
                break
        if found is None:
            original = rewrite.payload.get("original")
            new = rewrite.payload.get("new")
            out.append(
                Modification(
                    type=rewrite.mtype,
                    layer=TYPE_TO_LAYER[rewrite.mtype],
                    original=original if isinstance(original, str) else None,
                    new=new if isinstance(new, str) else None,
                    status="skipped",
                    reason="no_apply_record_for_rewrite",
                )
            )
        else:
            claimed.add(found)
            out.append(materialized_mods[found])
    return tuple(out)


# ----- pool workers (module-level: picklable under Windows spawn) -----------


def _materialize_group_task(task: tuple) -> tuple:
    """Materialise one unique (concept, ruleset) group; return needed leaves.

    `task = (group_id, concept_key, concept_slice, condition, mtype_value,
    target_id_repr, rules, needed_leaves)`. Returns
    `(group_id, {leaf: item}, [modification_dict, ...])`.
    """
    (gid, concept_key, concept_slice, condition,
     mtype_value, tid_repr, rules, needed) = task
    record = VariantRecord(
        condition=condition,
        modification_type=ModificationType(mtype_value),
        target_id_repr=tid_repr,
        rules=tuple(rules),
    )
    mv = materialize_variant_bc3param(concept_slice, concept_key, record)
    items = {leaf: mv.items[leaf] for leaf in needed if leaf in mv.items}
    return gid, items, [m.to_dict() for m in mv.modifications]


def _materialize_baseline_task(task: tuple) -> tuple:
    """Regenerate one concept's ORIGINAL items (no rules) for needed leaves.

    `task = (concept_key, concept_slice, needed_leaves)`; returns
    `(concept_key, {leaf: item})`. Same l2_repr bracket as the groups.
    """
    concept_key, concept_slice, needed = task
    out = render_base(concept_key)
    return concept_key, {leaf: out[leaf] for leaf in needed if leaf in out}


def _default_workers() -> int:
    return max(1, (os.cpu_count() or 2) // 2)


# ----- the driver -----------------------------------------------------------


def run_corpus(
    stage2_json: dict,
    plan: Sequence[PlannedVariant],
    *,
    out_dir: Optional[Path] = None,
    report_path: Optional[Path] = None,
    budgets: Optional[Budgets] = None,
    workers: Optional[int] = None,
) -> CorpusRunStats:
    """Materialise `plan` against `stage2_json` into the frozen release + report.

    `out_dir` defaults to `config.SYNTHETIC_PROCESSED_DIR`; `report_path` to
    `docs/synthetic/sprints/SPRINT_39_corpus_report.md`. `budgets`, when given,
    supplies the per-condition targets the report compares against (else the
    planned n doubles as the target). `workers` sizes the materialisation
    process pool (default `os.cpu_count() // 2`; `1` runs inline).
    Deterministic regardless of `workers`: same inputs → byte-identical
    release files.
    """
    report_path = DEFAULT_REPORT_PATH if report_path is None else Path(report_path)
    n_workers = _default_workers() if workers is None else max(1, int(workers))

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

    def _row(condition: str) -> dict:
        if condition not in stats:
            stats[condition] = _new_condition_row()
            uses[condition] = Counter()
            distances[condition] = 0
        return stats[condition]

    # -- phase A (serial, cheap): emission + composition + grouping ----------
    group_ids: dict[tuple[str, str], int] = {}       # (concept, signature) -> gid
    group_specs: list[dict] = []                     # gid -> spec
    baseline_needed: dict[str, set[str]] = {}        # concept -> leaves
    pending: list[tuple[PlannedVariant, int]] = []   # (planned, gid)

    for planned in plan:
        row = _row(planned.condition)
        row["planned"] += 1
        concept_key = planned.concept_key

        # emission: one emit_rules call per rewrite per slot
        rules: list[dict] = []
        target_ids: list[tuple] = []
        skip = None
        leaf_labels = _leaf_labels(enum_stage, concept_key, planned.leaf_item_key)
        for rewrite in planned.rewrites:
            per_concept = lookup.get((rewrite.mtype, rewrite.dedup_key))
            if per_concept is None or concept_key not in per_concept:
                skip = "target_not_found"
                break
            slots = _select_slots(per_concept[concept_key], leaf_labels)
            rewrite_rules: list[dict] = []
            for slot in slots:
                try:
                    emitted = emit_rules(
                        _emission_payload(rewrite, enum_stage, concept_key, slot),
                        rewrite.mtype,
                        target_id=slot,
                        stage_json=enum_stage,
                        concept_key=concept_key,
                    )
                except (KeyError, ValueError, TypeError):
                    continue
                rewrite_rules.extend(emitted.rules)
            if not rewrite_rules:
                skip = "emission_failed"
                break
            rules.extend(rewrite_rules)
            target_ids.append((rewrite.mtype.value, repr(slots)))
        if skip is not None:
            row[skip] += 1
            continue

        # composition: conflict → skip + count, never raise
        composed, comp_skipped = compose_rules(rules)
        if comp_skipped or not composed:
            row["composition_conflicts"] += 1
            continue

        signature = json.dumps(composed, sort_keys=True, ensure_ascii=False)
        group_key = (concept_key, signature)
        gid = group_ids.get(group_key)
        if gid is None:
            gid = len(group_specs)
            group_ids[group_key] = gid
            group_specs.append({
                "concept_key": concept_key,
                "condition": planned.condition,
                "mtype_value": ModificationType(composed[0]["type"]).value,
                "target_id_repr": repr(tuple(target_ids)),
                "rules": tuple(composed),
                "needed": set(),
            })
        group_specs[gid]["needed"].add(planned.leaf_item_key)
        baseline_needed.setdefault(concept_key, set()).add(planned.leaf_item_key)
        pending.append((planned, gid))

    # -- phase B: materialise each unique group + each baseline ONCE ---------
    group_tasks = [
        (
            gid,
            spec["concept_key"],
            {spec["concept_key"]: appl_stage[spec["concept_key"]]},
            spec["condition"],
            spec["mtype_value"],
            spec["target_id_repr"],
            spec["rules"],
            tuple(sorted(spec["needed"])),
        )
        for gid, spec in enumerate(group_specs)
    ]
    baseline_tasks = [
        (ck, {ck: appl_stage[ck]}, tuple(sorted(needed)))
        for ck, needed in sorted(baseline_needed.items())
    ]
    if n_workers <= 1 or len(group_tasks) <= 1:
        group_results = [_materialize_group_task(t) for t in group_tasks]
        baseline_results = [_materialize_baseline_task(t) for t in baseline_tasks]
    else:
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            chunk = max(1, len(group_tasks) // (n_workers * 8))
            group_map = pool.map(_materialize_group_task, group_tasks, chunksize=chunk)
            baseline_map = pool.map(_materialize_baseline_task, baseline_tasks)
            group_results = list(group_map)
            baseline_results = list(baseline_map)
    group_items: dict[int, dict] = {}
    group_mods: dict[int, tuple[Modification, ...]] = {}
    for gid, items_by_leaf, mod_dicts in group_results:
        group_items[gid] = items_by_leaf
        group_mods[gid] = tuple(Modification.from_dict(d) for d in mod_dicts)
    baselines: dict[str, dict] = dict(baseline_results)

    # -- phase C: deterministic sorted merge → filters → items ---------------
    pending.sort(
        key=lambda pair: (
            pair[0].condition, pair[0].concept_key, pair[0].leaf_item_key,
        )
    )
    seen_texts: set[tuple[str, str]] = set()
    items: list[SyntheticItem] = []

    for planned, gid in pending:
        row = stats[planned.condition]
        leaf_key = planned.leaf_item_key
        synthetic = group_items[gid].get(leaf_key)
        original = baselines.get(planned.concept_key, {}).get(leaf_key)
        if synthetic is None or original is None:
            row["leaf_missing"] += 1
            continue
        resumen, texto = synthetic["resumen"], synthetic["texto"]

        # residue is a bug: raise, never filter
        _check_residue(planned, "resumen", resumen)
        _check_residue(planned, "texto", texto)

        # filters: no-op (backstop), then exact corpus-wide dedup
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
        modifications = _per_rewrite_modifications(
            planned.rewrites, group_mods[gid],
        )
        items.append(
            SyntheticItem(
                item_key=f"{leaf_key}{_SYN_MARK}{variante_id}",
                original_key=leaf_key,
                params=params,
                resumen=resumen,
                texto=texto,
                variante_id=variante_id,
                modification_types=tuple(m.type for m in modifications),
                modification_count=len(modifications),
                modifications=modifications,
                concept_key=planned.concept_key,
            )
        )
        row["produced"] += 1
        for rewrite in planned.rewrites:
            uses[planned.condition][rewrite.uid] += 1
            if planned.condition == _ALL_COMBINED:
                key = rewrite.mtype.value
                if (
                    rewrite.mtype is ModificationType.TEMPLATE_PARAPHRASE
                    and rewrite.dedup_key
                ):
                    # split by field so the both-surfaces requirement
                    # (RESUMEN == TEXTO == n) is visible in the QA report
                    key = f"{key} ({rewrite.dedup_key[0]})"
                presence[key] += 1
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
    run.add_argument(
        "--workers", type=int, default=None,
        help="materialisation pool size (default cpu_count // 2; 1 = inline)",
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
        workers=args.workers,
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
