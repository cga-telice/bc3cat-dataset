"""Sprint 20 — Phase E Tasks E3 (validation sampler) + E4 (reviewer harness).

Two tiers:

* **Always-on** — hand-built `SyntheticItem` fixtures (single-type, stacked,
  `new_param`, baseline). Cover stratification (baselines excluded, stacked →
  multi-cell), the floor/fraction + 100 %-`new_param` sampling rule, seeded
  determinism, de-dup-by-`item_key`, the coverage report, queue/verdict JSONL
  round-trips + atomic write, fail-loud duplicate verdict keys, percent + Cohen's
  κ agreement over the ≥2-reviewer subset, the import-hygiene / no-side-effects
  seam guards, and the CLI no-subcommand exit code.

* **Data-gated** — skipped when the committed `data/intermediate/OBRA CIVIL/`
  JSONs are absent; otherwise materialises one real concept through `stage_b`,
  joins it (Sprint 19 `join_intermediate`), samples, and asserts the queue is a
  subset of the joined items with a self-consistent coverage report.
"""

import importlib
import inspect
import json
import types

import pytest

from synthetic import review
from synthetic.review import (
    ReviewTask,
    CoverageReport,
    Verdict,
    AgreementStat,
    ReviewError,
    stratify,
    sample_review_queue,
    write_queue,
    read_queue,
    write_verdicts,
    read_verdicts,
    agreement,
    main,
)
from synthetic.metadata import SyntheticItem, join_intermediate
from synthetic.taxonomy import Modification, ModificationType, TYPE_TO_LAYER
from utils import config


# --------------------------------------------------------------------------
# Inline SyntheticItem fixtures
# --------------------------------------------------------------------------

_CONCEPT = "OEB020$"
_SYN = ModificationType.SYNONYM_LABEL
_PAR = ModificationType.PARAPHRASE
_NEW = ModificationType.NEW_PARAM


def _item(item_key, *, concept=_CONCEPT, types=(_SYN,), resumen="r", texto="t",
          original_key=None):
    mods = tuple(Modification(type=t, layer=TYPE_TO_LAYER[t]) for t in types)
    return SyntheticItem(
        item_key=item_key,
        original_key=original_key or item_key.split("_syn_", 1)[0],
        params={},
        resumen=resumen,
        texto=texto,
        variante_id="v1",
        modification_types=tuple(types),
        modification_count=len(mods),
        modifications=mods,
        concept_key=concept,
    )


def _cell_items(n, *, prefix, types=(_SYN,), concept=_CONCEPT):
    return [_item(f"{prefix}{i:03d}_syn_v1", types=types, concept=concept)
            for i in range(n)]


# --------------------------------------------------------------------------
# Public surface + import hygiene + side effects
# --------------------------------------------------------------------------

def test_module_exposes_public_surface():
    for name in ("ReviewTask", "CoverageReport", "Verdict", "AgreementStat",
                 "ReviewError", "stratify", "sample_review_queue", "write_queue",
                 "read_queue", "write_verdicts", "read_verdicts", "agreement",
                 "main"):
        assert hasattr(review, name)


def test_review_does_not_import_stage_b_run_synthetic_or_stage_runners():
    src = inspect.getsource(review)
    for forbidden in ("import stage_b", "import run_synthetic", "import stage_runners",
                      "synthetic.stage_b", "synthetic.run_synthetic",
                      "synthetic.stage_runners"):
        assert forbidden not in src, forbidden
    for value in vars(review).values():
        if isinstance(value, types.ModuleType):
            for bad in ("stage_b", "run_synthetic", "stage_runners"):
                assert not value.__name__.endswith(bad), value.__name__


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(review)
    assert callable(reloaded.sample_review_queue)


# --------------------------------------------------------------------------
# E3 — stratify
# --------------------------------------------------------------------------

def test_stratify_keys_on_concept_and_type():
    items = [
        _item("OEB020a_syn_v1", types=(_SYN,)),
        _item("OEB030a_syn_v1", types=(_PAR,), concept="OEB030$"),
    ]
    cells = stratify(items)
    assert set(cells) == {(_CONCEPT, _SYN), ("OEB030$", _PAR)}


def test_stratify_excludes_baselines():
    items = [
        _item("OEB020a_syn_v1", types=()),          # baseline, count 0
        _item("OEB020b_syn_v1", types=(_SYN,)),
    ]
    cells = stratify(items)
    assert set(cells) == {(_CONCEPT, _SYN)}
    assert all(it.modification_count > 0 for cell in cells.values() for it in cell)


def test_stratify_stacked_item_in_every_type_cell():
    stacked = _item("OEB020a_syn_v1", types=(_SYN, _PAR))
    cells = stratify([stacked])
    assert set(cells) == {(_CONCEPT, _SYN), (_CONCEPT, _PAR)}
    assert cells[(_CONCEPT, _SYN)] == [stacked]
    assert cells[(_CONCEPT, _PAR)] == [stacked]


# --------------------------------------------------------------------------
# E3 — sample_review_queue
# --------------------------------------------------------------------------

def test_sample_new_param_full_coverage():
    items = _cell_items(8, prefix="NP", types=(_NEW,))
    tasks, report = sample_review_queue(items, coverage=0.10, floor=5)
    assert len(tasks) == 8
    (cell,) = report.cells
    assert cell.size == 8 and cell.sampled == 8


def test_sample_floor_caps_at_cell_size():
    items = _cell_items(3, prefix="S", types=(_SYN,))
    tasks, report = sample_review_queue(items, coverage=0.10, floor=5)
    assert len(tasks) == 3
    assert report.cells[0].sampled == 3


def test_sample_fraction_above_floor():
    items = _cell_items(100, prefix="S", types=(_SYN,))
    tasks, report = sample_review_queue(items, coverage=0.10, floor=5)
    assert len(tasks) == 10
    assert report.cells[0].sampled == 10


def test_sample_floor_dominates_small_cell():
    items = _cell_items(20, prefix="S", types=(_SYN,))
    tasks, report = sample_review_queue(items, coverage=0.10, floor=5)
    assert len(tasks) == 5
    assert report.cells[0].sampled == 5


def test_sample_dedups_stacked_item_to_one_task():
    stacked = _item("OEB020a_syn_v1", types=(_SYN, _PAR))
    tasks, report = sample_review_queue([stacked], coverage=0.10, floor=5)
    assert len(tasks) == 1
    assert tasks[0].item_key == "OEB020a_syn_v1"
    assert report.queued == 1
    assert len(report.cells) == 2  # one per type, both sampled


def test_sample_task_strata_lists_all_cells():
    stacked = _item("OEB020a_syn_v1", types=(_SYN, _PAR))
    tasks, _ = sample_review_queue([stacked])
    # sorted by modification_type.value: "paraphrase" < "synonym_label"
    assert tasks[0].strata == ((_CONCEPT, _PAR), (_CONCEPT, _SYN))


def test_sample_deterministic_same_seed():
    items = _cell_items(50, prefix="S", types=(_SYN,))
    a, ra = sample_review_queue(items, seed=7)
    b, rb = sample_review_queue(items, seed=7)
    assert a == b
    assert ra == rb


def test_sample_seed_changes_selection_not_count():
    items = _cell_items(50, prefix="S", types=(_SYN,))
    a, _ = sample_review_queue(items, seed=0)
    b, _ = sample_review_queue(items, seed=999)
    assert len(a) == len(b) == 5
    assert {t.item_key for t in a} != {t.item_key for t in b}


def test_coverage_report_counts_baselines():
    items = (
        _cell_items(4, prefix="S", types=(_SYN,))
        + [_item("BASE_a_syn_v1", types=()), _item("BASE_b_syn_v1", types=())]
    )
    _, report = sample_review_queue(items)
    assert report.baselines == 2


def test_coverage_report_cell_sums_consistent():
    items = (
        _cell_items(30, prefix="S", types=(_SYN,))
        + _cell_items(6, prefix="NP", types=(_NEW,))
    )
    tasks, report = sample_review_queue(items)
    assert report.queued == len(tasks)
    assert sum(c.sampled for c in report.cells) >= report.queued
    for c in report.cells:
        assert 0 <= c.sampled <= c.size
        assert c.fraction == (c.sampled / c.size if c.size else 0.0)


# --------------------------------------------------------------------------
# E3 — JSONL round-trips
# --------------------------------------------------------------------------

def test_review_task_to_dict_shape():
    items = _cell_items(3, prefix="S", types=(_SYN,))
    tasks, _ = sample_review_queue(items, floor=5)
    d = tasks[0].to_dict()
    assert set(d) == {
        "item_key", "concept_key", "modification_types", "modification_count",
        "resumen", "texto", "modifications", "strata",
    }
    assert d["modification_types"] == ["synonym_label"]
    assert d["strata"] == [[_CONCEPT, "synonym_label"]]


def test_queue_jsonl_round_trip(tmp_path):
    items = (
        _cell_items(3, prefix="S", types=(_SYN,))
        + [_item("OEB020z_syn_v1", types=(_SYN, _PAR))]
    )
    tasks, _ = sample_review_queue(items, floor=5)
    p = tmp_path / "queue.jsonl"
    write_queue(tasks, p)
    assert read_queue(p) == tasks


def test_queue_atomic_no_tmp_left(tmp_path):
    sub = tmp_path / "review"
    tasks, _ = sample_review_queue(_cell_items(3, prefix="S", types=(_SYN,)), floor=5)
    write_queue(tasks, sub / "queue.jsonl")
    assert (sub / "queue.jsonl").exists()
    assert list(sub.glob(".*.tmp")) == []


# --------------------------------------------------------------------------
# E4 — verdicts + agreement
# --------------------------------------------------------------------------

# NOTE: `test_module_has_no_side_effects_at_import` reloads `review`, rebinding
# its classes to a fresh generation. Tests sensitive to class identity (==,
# isinstance, pytest.raises) must reference the surface through `review.` so the
# fixtures are co-generation with the reloaded objects (the Sprint 19 pattern).
def _v(item_key, reviewer, *, gram=True, sem=True, axis=None, meta=True, notes=""):
    return review.Verdict(item_key=item_key, reviewer=reviewer, grammatical=gram,
                          semantic_preserved=sem, axis_distinguishable=axis,
                          metadata_accurate=meta, notes=notes)


def test_verdict_round_trip_including_none_axis(tmp_path):
    verdicts = [
        _v("i1", "alice", axis=None, notes="ok"),
        _v("i1", "bob", axis=None),
        _v("i2", "alice", axis=True),
        _v("i2", "bob", axis=False),
    ]
    p = tmp_path / "verdicts.jsonl"
    review.write_verdicts(verdicts, p)
    back = review.read_verdicts(p)
    assert back == verdicts
    assert back[0].axis_distinguishable is None


def test_verdict_duplicate_key_is_fail_loud(tmp_path):
    verdicts = [_v("i1", "alice"), _v("i1", "alice", gram=False)]
    with pytest.raises(review.ReviewError):
        review.write_verdicts(verdicts, tmp_path / "v.jsonl")


def test_agreement_full_agreement_is_one():
    verdicts = []
    for i in range(4):
        verdicts.append(_v(f"i{i}", "alice", gram=True, sem=True, meta=True))
        verdicts.append(_v(f"i{i}", "bob", gram=True, sem=True, meta=True))
    stats = agreement(verdicts)
    assert stats["grammatical"].percent_agreement == 1.0
    assert stats["semantic_preserved"].percent_agreement == 1.0
    assert stats["metadata_accurate"].percent_agreement == 1.0
    assert stats["grammatical"].n_items == 4


def test_agreement_disagreement_below_one():
    verdicts = [
        _v("i0", "alice", gram=True), _v("i0", "bob", gram=True),
        _v("i1", "alice", gram=True), _v("i1", "bob", gram=False),  # planted
    ]
    stats = agreement(verdicts)
    assert stats["grammatical"].percent_agreement < 1.0


def test_agreement_kappa_matches_hand_value():
    # grammatical 2x2 over 10 items, raters alice(a)/bob(b):
    #   4 (T,T), 4 (F,F), 1 (T,F), 1 (F,T)
    #   p_o = 8/10 = 0.8 ; p(a=T)=p(b=T)=5/10=0.5 ; p_e = 0.5 ; kappa = 0.6
    verdicts = []
    plan = [("T", "T")] * 4 + [("F", "F")] * 4 + [("T", "F"), ("F", "T")]
    for i, (a, b) in enumerate(plan):
        verdicts.append(_v(f"i{i}", "alice", gram=(a == "T")))
        verdicts.append(_v(f"i{i}", "bob", gram=(b == "T")))
    stats = agreement(verdicts)
    assert stats["grammatical"].n_items == 10
    assert stats["grammatical"].percent_agreement == pytest.approx(0.8)
    assert stats["grammatical"].cohen_kappa == pytest.approx(0.6)


def test_agreement_axis_only_over_new_param():
    verdicts = [
        _v("i0", "alice", axis=None), _v("i0", "bob", axis=None),   # non-new_param
        _v("i1", "alice", axis=None), _v("i1", "bob", axis=None),
        _v("i2", "alice", axis=True), _v("i2", "bob", axis=True),   # new_param
        _v("i3", "alice", axis=False), _v("i3", "bob", axis=False),
    ]
    stats = agreement(verdicts)
    assert stats["axis_distinguishable"].n_items == 2


def test_agreement_ignores_single_reviewer_items():
    verdicts = [
        _v("solo", "alice", gram=True),                      # only one reviewer
        _v("pair", "alice", gram=True), _v("pair", "bob", gram=True),
    ]
    stats = agreement(verdicts)
    assert stats["grammatical"].n_items == 1


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_main_no_subcommand_returns_nonzero():
    assert main([]) != 0


# --------------------------------------------------------------------------
# Data-gated tier — real concept join -> sample
# --------------------------------------------------------------------------

_OC = "OBRA CIVIL"
_HAS_DATA = config.chapter_path(_OC).exists() and config.stage_path(_OC, 5).exists()
_skip_no_data = pytest.mark.skipif(not _HAS_DATA, reason="OBRA CIVIL intermediate JSONs absent")


@_skip_no_data
def test_sample_real_concept_queue_subset_of_items(tmp_path):
    from math import prod
    from synthetic.stage_b import materialize_catalog_entry
    from synthetic.variant_catalog import VariantCatalogEntry, VariantRecord

    with open(config.chapter_path(_OC), encoding="utf-8") as f:
        stage2 = json.load(f)
    with open(config.stage_path(_OC, 5), encoding="utf-8") as f:
        stage5 = json.load(f)

    present = {v.get("parent_key") for v in stage5.values()}

    def _leaves(v):
        params = v.get("parameters") or {}
        return prod([len(p["values"]) for p in params.values()]) if params else 1

    target = min(
        (k for k in stage2 if k in present and _leaves(stage2[k]) >= 2),
        key=lambda k: _leaves(stage2[k]),
    )

    variant = VariantRecord(
        condition="baseline",
        modification_type=ModificationType.SYNONYM_LABEL,
        target_id_repr="()",
        rules=(),
    )
    entry = VariantCatalogEntry(
        concept_key=target,
        concept_resumen=stage2[target].get("resumen", ""),
        parent_key=target,
        variants=(variant,),
        skipped=(),
        provenance=(),
    )
    materialize_catalog_entry({target: stage2[target]}, entry, out_dir=tmp_path)

    items = join_intermediate(tmp_path)
    assert items
    item_keys = {it.item_key for it in items}

    tasks, report = sample_review_queue(items)
    assert all(t.item_key in item_keys for t in tasks)
    assert report.queued == len(tasks)
    assert sum(c.sampled for c in report.cells) >= report.queued
    assert all(0 <= c.sampled <= c.size for c in report.cells)
    for t in tasks:
        assert isinstance(t.resumen, str) and isinstance(t.texto, str)
        assert t.strata
    # the baseline variant carries no modifications -> every item is a baseline
    assert report.baselines == len(items)
