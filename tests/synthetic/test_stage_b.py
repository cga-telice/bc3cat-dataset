"""Sprint 18 — Phase D Task D2: Stage-B apply-and-rerun.

Two tiers:

* **Always-on** — tiny inline fixtures, no live LLM, no large-file IO. Cover the
  single parent-level injection (PD->L1->L2->L3 order + partition), mutation
  propagation through the rerun (L1 value, L2 fragment, L3 substring), purity /
  determinism, the all-skipped baseline, the per-variant atomic writes +
  round-trip, the catalog read loop, and the import-hygiene seam guards (Stage B
  does not import `run_synthetic`; `run_synthetic` still does not import
  `mutator`).

* **Data-gated** — skipped when the committed `data/intermediate/OBRA CIVIL/`
  JSONs are absent; otherwise asserts the unmutated single-concept slice
  reproduces the chapter `stage5` items at stage-5 granularity (the faithful
  rerun gate; per-concept dedup means stage-7 is NOT the equivalence point).
"""

import copy
import importlib
import inspect
import json
import types

import pytest

from synthetic import stage_b
from synthetic.stage_b import (
    MaterializedVariant,
    apply_variant_rules,
    materialize_variant,
    materialize_catalog_entry,
    run_stage_b,
)
from synthetic import run_synthetic
from synthetic.taxonomy import ModificationType
from synthetic.variant_catalog import (
    VariantCatalogEntry,
    VariantRecord,
    write_catalog_entry,
)
from utils import config


# --------------------------------------------------------------------------
# Fixtures (inline, tiny) — modelled on the real OBRA CIVIL grammar:
#   conditional fragments use the `(%B=="a")` double-equals/quoted-label form
#   that s04 resolves cleanly, the template references the axis directly ($B)
#   and the variable ($K), and carries a literal substring for L3.
# --------------------------------------------------------------------------

_CONCEPT_KEY = "OEB020$"


def _concept():
    return {
        _CONCEPT_KEY: {
            "ud": "m",
            "concept": "Canalizacion",
            "text_variables": {
                "K": '"normal" * (%B=="a") + "rocoso" * (%B=="b")',
            },
            "resumen": "Canalizacion en terreno $B con tuberia rigida",
            "texto": "Canalizacion terreno $B tipo $K final",
            "parameters": {
                "B": {
                    "label": "TERRENO",
                    "values": [
                        {"label": "a", "value": "Normal"},
                        {"label": "b", "value": "Rocoso"},
                    ],
                },
            },
        }
    }


_R_L1 = {"type": "synonym_label", "param": "B", "value": "a", "new": "Estandar"}
_R_L2 = {"type": "paraphrase", "var": "K", "condition": '%B=="a"', "new": "llano"}
_R_L3 = {"type": "omission", "field": "RESUMEN",
         "original": "tuberia rigida", "new": "conducto"}
_R_PD = {"type": "new_param", "param": "Z", "label": "EXTRA",
         "values": [{"label": "a", "value": "zz"}]}
_R_BAD = {"type": "synonym_label", "param": "NOPE", "value": "a", "new": "x"}


def _variant(rules, condition="single", mtype=ModificationType.SYNONYM_LABEL):
    return VariantRecord(
        condition=condition,
        modification_type=mtype,
        target_id_repr=repr(tuple(r.get("param") or r.get("var") for r in rules)),
        rules=tuple(rules),
    )


def _entry(variants):
    return VariantCatalogEntry(
        concept_key=_CONCEPT_KEY,
        concept_resumen="Canalizacion en terreno",
        parent_key=_CONCEPT_KEY,
        variants=tuple(variants),
        skipped=(),
        provenance=(),
    )


# --------------------------------------------------------------------------
# Public surface + import hygiene + side effects
# --------------------------------------------------------------------------

def test_module_exposes_public_surface():
    for name in ("apply_variant_rules", "materialize_variant",
                 "materialize_catalog_entry", "run_stage_b", "MaterializedVariant"):
        assert hasattr(stage_b, name)
    assert set(stage_b.__all__) == {
        "MaterializedVariant", "apply_variant_rules", "materialize_variant",
        "materialize_catalog_entry", "run_stage_b",
    }


def test_stage_b_does_not_import_run_synthetic():
    src = inspect.getsource(stage_b)
    assert "import run_synthetic" not in src
    assert "synthetic.run_synthetic" not in src
    for value in vars(stage_b).values():
        if isinstance(value, types.ModuleType):
            assert not value.__name__.endswith("run_synthetic"), value.__name__


def test_run_synthetic_still_does_not_import_mutator():
    # Re-assert the Sprint-16 tripwire (NOT removed by Stage B).
    assert "mutator" not in run_synthetic.__dict__


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(stage_b)
    assert callable(reloaded.apply_variant_rules)


# --------------------------------------------------------------------------
# apply_variant_rules — single parent-level injection
# --------------------------------------------------------------------------

def test_apply_variant_rules_orders_pd_l1_l2_l3():
    # rules supplied out of order; the log must come back in PD->L1->L2->L3 order
    _, log = apply_variant_rules(_concept(), _CONCEPT_KEY, [_R_L3, _R_L2, _R_L1, _R_PD])
    assert [m.type.value for m in log] == [
        "new_param", "synonym_label", "paraphrase", "omission",
    ]


def test_apply_variant_rules_partitions_by_layer():
    _, log = apply_variant_rules(_concept(), _CONCEPT_KEY, [_R_L1, _R_L3])
    assert {m.type.value for m in log} == {"synonym_label", "omission"}


def test_apply_variant_rules_preserves_intra_layer_order():
    r1 = {"type": "synonym_label", "param": "B", "value": "a", "new": "Uno"}
    r2 = {"type": "num_to_text", "param": "B", "value": "b", "new": "Dos"}
    _, log = apply_variant_rules(_concept(), _CONCEPT_KEY, [r1, r2])
    assert [m.type.value for m in log] == ["synonym_label", "num_to_text"]


def test_apply_variant_rules_is_pure():
    src = _concept()
    snapshot = copy.deepcopy(src)
    apply_variant_rules(src, _CONCEPT_KEY, [_R_L1, _R_L2, _R_L3, _R_PD])
    assert src == snapshot


def test_apply_variant_rules_empty_rules_is_noop():
    out, log = apply_variant_rules(_concept(), _CONCEPT_KEY, [])
    assert log == []
    assert out == _concept()


def test_apply_variant_rules_skips_failing_rule():
    out, log = apply_variant_rules(_concept(), _CONCEPT_KEY, [_R_BAD])
    assert log == []
    assert out == _concept()  # nothing applied


def test_apply_variant_rules_applies_good_skips_bad():
    _, log = apply_variant_rules(_concept(), _CONCEPT_KEY, [_R_L1, _R_BAD])
    assert [m.type.value for m in log] == ["synonym_label"]


# --------------------------------------------------------------------------
# materialize_variant — mutation propagates through the rerun
# --------------------------------------------------------------------------

def test_materialize_variant_synonym_label_propagates():
    mv = materialize_variant(_concept(), _CONCEPT_KEY, _variant([_R_L1]))
    assert mv.items["OEB020a"]["resumen"] == "Canalizacion en terreno Estandar con tuberia rigida"
    assert [m.type for m in mv.modifications] == [ModificationType.SYNONYM_LABEL]


def test_materialize_variant_l2_fragment_present_after_stage4():
    from synthetic.stage_runners import run_stage3, run_stage4
    mutated, _ = apply_variant_rules(_concept(), _CONCEPT_KEY, [_R_L2])
    s4 = run_stage4(run_stage3(mutated))
    assert "llano" in json.dumps(s4, ensure_ascii=False)


def test_materialize_variant_l2_fragment_survives_to_items():
    mv = materialize_variant(_concept(), _CONCEPT_KEY, _variant([_R_L2]))
    assert "llano" in mv.items["OEB020a"]["texto"]


def test_materialize_variant_l3_substring_survives_stage5():
    mv = materialize_variant(_concept(), _CONCEPT_KEY, _variant([_R_L3]))
    assert "conducto" in mv.items["OEB020a"]["resumen"]
    assert "tuberia rigida" not in mv.items["OEB020a"]["resumen"]


def test_materialize_variant_stacked_all_layers():
    mv = materialize_variant(
        _concept(), _CONCEPT_KEY,
        _variant([_R_PD, _R_L1, _R_L2, _R_L3], condition="stacked_4",
                 mtype=ModificationType.NEW_PARAM),
    )
    assert [m.type.value for m in mv.modifications] == [
        "new_param", "synonym_label", "paraphrase", "omission",
    ]
    # PD adds axis Z (1 value) -> leaf key gains a second suffix char.
    leaf = mv.items["OEB020aa"]
    assert "Estandar" in leaf["resumen"]
    assert "conducto" in leaf["resumen"]
    assert "llano" in leaf["texto"]


def test_materialize_variant_modification_types_match_log():
    mv = materialize_variant(_concept(), _CONCEPT_KEY, _variant([_R_L1, _R_L3]))
    assert mv.modification_types == tuple(m.type for m in mv.modifications)


def test_materialize_variant_is_pure():
    src = _concept()
    snapshot = copy.deepcopy(src)
    materialize_variant(src, _CONCEPT_KEY, _variant([_R_L1, _R_L2, _R_L3]))
    assert src == snapshot


def test_materialize_variant_deterministic():
    v = _variant([_R_L1, _R_L2, _R_L3])
    a = materialize_variant(_concept(), _CONCEPT_KEY, v)
    b = materialize_variant(_concept(), _CONCEPT_KEY, v)
    assert a == b


def test_materialize_variant_all_skipped_emits_baseline():
    baseline = materialize_variant(_concept(), _CONCEPT_KEY, _variant([]))
    skipped = materialize_variant(_concept(), _CONCEPT_KEY, _variant([_R_BAD]))
    assert skipped.modifications == ()
    assert skipped.items == baseline.items  # baseline is traceable


def test_materialize_variant_id_is_deterministic():
    v = _variant([_R_L1], condition="single_L1_synonym_label")
    a = materialize_variant(_concept(), _CONCEPT_KEY, v)
    b = materialize_variant(_concept(), _CONCEPT_KEY, v)
    assert a.variant_id == b.variant_id
    assert a.variant_id.startswith("single_L1_synonym_label_")


# --------------------------------------------------------------------------
# materialize_catalog_entry / run_stage_b — disk emission
# --------------------------------------------------------------------------

def test_materialize_catalog_entry_one_file_per_variant(tmp_path):
    entry = _entry([
        _variant([_R_L1], condition="c1"),
        _variant([_R_L3], condition="c2"),
    ])
    paths = materialize_catalog_entry(_concept(), entry, out_dir=tmp_path)
    assert len(paths) == 2
    concept_dir = tmp_path / _CONCEPT_KEY
    assert {p.parent for p in paths} == {concept_dir}
    assert sorted(p.name for p in concept_dir.glob("*.json")) == sorted(p.name for p in paths)


def test_materialize_catalog_entry_round_trip(tmp_path):
    v = _variant([_R_L1, _R_L3], condition="c1")
    entry = _entry([v])
    (path,) = materialize_catalog_entry(_concept(), entry, out_dir=tmp_path)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    mv = materialize_variant(_concept(), _CONCEPT_KEY, v)
    assert loaded == {
        "variant_id": mv.variant_id,
        "condition": "c1",
        "concept_key": _CONCEPT_KEY,
        "modification_types": [t.value for t in mv.modification_types],
        "modifications": [m.to_dict() for m in mv.modifications],
        "items": mv.items,
    }


def test_materialize_catalog_entry_atomic_no_tmp_left(tmp_path):
    entry = _entry([_variant([_R_L1])])
    materialize_catalog_entry(_concept(), entry, out_dir=tmp_path)
    assert list((tmp_path / _CONCEPT_KEY).glob(".*tmp")) == []


def test_run_stage_b_reads_catalog_dir(tmp_path):
    variants_dir = tmp_path / "variants"
    out_dir = tmp_path / "intermediate"
    write_catalog_entry(_entry([_variant([_R_L1])]), variants_dir)
    paths = run_stage_b(_concept(), variants_dir, out_dir=out_dir)
    assert len(paths) == 1
    assert paths[0].parent == out_dir / _CONCEPT_KEY
    assert paths[0].exists()


def test_run_stage_b_empty_dir_yields_no_paths(tmp_path):
    variants_dir = tmp_path / "variants"
    variants_dir.mkdir()
    assert run_stage_b(_concept(), variants_dir, out_dir=tmp_path / "out") == []


# --------------------------------------------------------------------------
# Data-gated tier — stage-5 granularity slice equivalence
# --------------------------------------------------------------------------

_OC = "OBRA CIVIL"
_HAS_DATA = (
    config.chapter_path(_OC).exists()
    and config.stage_path(_OC, 5).exists()
)
_skip_no_data = pytest.mark.skipif(not _HAS_DATA, reason="OBRA CIVIL intermediate JSONs absent")


def _norm(obj):
    return json.loads(json.dumps(obj, ensure_ascii=False))


@_skip_no_data
def test_stage5_slice_matches_chapter_for_concept():
    from math import prod
    from synthetic.stage_runners import run_stage3, run_stage4, run_stage5

    with open(config.chapter_path(_OC), encoding="utf-8") as f:
        stage2 = json.load(f)
    with open(config.stage_path(_OC, 5), encoding="utf-8") as f:
        stage5 = json.load(f)

    # smallest concept with >=2 leaves whose leaves are present in stage5
    present = {v.get("parent_key") for v in stage5.values()}

    def _leaves(v):
        params = v.get("parameters") or {}
        return prod([len(p["values"]) for p in params.values()]) if params else 1

    target = min(
        (k for k in stage2 if k in present and _leaves(stage2[k]) >= 2),
        key=lambda k: _leaves(stage2[k]),
    )

    got = run_stage5(run_stage4(run_stage3({target: stage2[target]})))
    gold = {k: v for k, v in stage5.items() if v.get("parent_key") == target}

    assert list(got.keys()) == list(gold.keys())
    for k in got:
        assert _norm(got[k]) == gold[k], f"item {k} diverges from chapter golden"
