"""Sprint 19 — Phase E Tasks E1 (metadata join) + E2 (schema validator).

Two tiers:

* **Always-on** — hand-built Stage-B-shaped payloads (no live LLM, no large-file
  IO). Cover the per-item fan-out, the `original_key = leaf_key[:-K]` rule, the
  `_syn_`-marked unique `item_key`, recompute-don't-trust of count/types, the
  zero-modification baseline, params flattening, `to_dict` shape, deterministic
  `join_intermediate`, the fail-loud validator (one case per malformed class),
  global uniqueness, and the import-hygiene / no-side-effects seam guards.

* **Data-gated** — skipped when the committed `data/intermediate/OBRA CIVIL/`
  JSONs are absent; otherwise materialises one real concept through `stage_b`
  into `tmp_path`, joins + validates, and checks `original_key` is a real
  chapter leaf for the (non-PD) baseline variant.
"""

import importlib
import inspect
import json
import types

import pytest

from synthetic import metadata
from synthetic.metadata import (
    SyntheticItem,
    SchemaError,
    join_variant_payload,
    join_variant_file,
    join_intermediate,
    validate_item,
    validate_items,
)
from synthetic.taxonomy import Layer, Modification, ModificationType
from utils import config


# --------------------------------------------------------------------------
# Inline Stage-B-shaped payload fixtures
# --------------------------------------------------------------------------

_CONCEPT_KEY = "OEB020$"
_VID = "single_L1_synonym_label_ab12cd34ef"


def _leaf(value, *, axis="B", axis_label="TERRENO", resumen="r", texto="t", extra=None):
    params = {axis: {"label": axis_label, "values": [{"label": "a", "value": value}]}}
    if extra:
        params.update(extra)
    return {
        "parent_key": _CONCEPT_KEY,
        "ud": "m",
        "concept": "Canalizacion",
        "resumen": resumen,
        "texto": texto,
        "parameters": params,
        "validation": True,
    }


def _l1_payload():
    """Single synonym_label, 2 leaves, K=0 (non-PD)."""
    mod = {"type": "synonym_label", "layer": "param_value", "param": "B",
           "value": "a", "original": "Normal", "new": "Estandar", "status": "applied"}
    return {
        "variant_id": _VID,
        "condition": "single_L1_synonym_label",
        "concept_key": _CONCEPT_KEY,
        "modification_types": ["synonym_label"],
        "modifications": [mod],
        "items": {
            "OEB020a": _leaf("Estandar", resumen="terreno Estandar", texto="t a"),
            "OEB020b": _leaf("Rocoso", resumen="terreno Rocoso", texto="t b"),
        },
    }


def _pd_payload():
    """One new_param, leaves OEB020aa / OEB020ba, K=1 -> original OEB020a / OEB020b."""
    mod = {"type": "new_param", "layer": "param_definition", "param": "Z",
           "status": "applied"}
    z_axis = {"Z": {"label": "EXTRA", "values": [{"label": "a", "value": "zz"}]}}
    return {
        "variant_id": "single_PD_new_param_0011223344",
        "condition": "single_PD_new_param",
        "concept_key": _CONCEPT_KEY,
        "modification_types": ["new_param"],
        "modifications": [mod],
        "items": {
            "OEB020aa": _leaf("Normal", extra=z_axis),
            "OEB020ba": _leaf("Rocoso", extra=z_axis),
        },
    }


def _baseline_payload():
    """All-skipped variant: empty modifications, baseline items."""
    return {
        "variant_id": "single_baseline_deadbeef00",
        "condition": "single_baseline",
        "concept_key": _CONCEPT_KEY,
        "modification_types": [],
        "modifications": [],
        "items": {"OEB020a": _leaf("Normal")},
    }


# --------------------------------------------------------------------------
# Public surface + import hygiene + side effects
# --------------------------------------------------------------------------

def test_module_exposes_public_surface():
    for name in ("SyntheticItem", "SchemaError", "join_variant_payload",
                 "join_variant_file", "join_intermediate",
                 "validate_item", "validate_items"):
        assert hasattr(metadata, name)
    assert set(metadata.__all__) == {
        "SyntheticItem", "SchemaError", "join_variant_payload",
        "join_variant_file", "join_intermediate", "validate_item",
        "validate_items",
    }


def test_metadata_does_not_import_stage_b_or_run_synthetic():
    src = inspect.getsource(metadata)
    assert "import stage_b" not in src
    assert "import run_synthetic" not in src
    assert "synthetic.stage_b" not in src
    assert "synthetic.run_synthetic" not in src
    for value in vars(metadata).values():
        if isinstance(value, types.ModuleType):
            assert not value.__name__.endswith("stage_b"), value.__name__
            assert not value.__name__.endswith("run_synthetic"), value.__name__


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(metadata)
    assert callable(reloaded.join_variant_payload)


# --------------------------------------------------------------------------
# E1 — the join
# --------------------------------------------------------------------------

def test_join_one_record_per_item():
    items = join_variant_payload(_l1_payload())
    assert len(items) == 2
    assert all(it.variante_id == _VID for it in items)
    assert all(it.concept_key == _CONCEPT_KEY for it in items)


def test_join_l1_original_key_equals_leaf_key():
    items = join_variant_payload(_l1_payload())
    by_leaf = {it.item_key: it for it in items}
    a = by_leaf[f"OEB020a_syn_{_VID}"]
    assert a.original_key == "OEB020a"


def test_join_new_param_strips_trailing_axis_chars():
    items = join_variant_payload(_pd_payload())
    originals = sorted(it.original_key for it in items)
    assert originals == ["OEB020a", "OEB020b"]


def test_join_item_key_is_syn_marked_and_unique():
    items = join_variant_payload(_l1_payload())
    keys = [it.item_key for it in items]
    assert keys == [f"OEB020a_syn_{_VID}", f"OEB020b_syn_{_VID}"]
    assert len(set(keys)) == len(keys)


def test_join_recomputes_modification_count():
    items = join_variant_payload(_l1_payload())
    assert all(it.modification_count == 1 for it in items)
    assert all(len(it.modifications) == 1 for it in items)


def test_join_recomputes_modification_types_over_payload_copy():
    payload = _l1_payload()
    payload["modification_types"] = ["paraphrase"]  # deliberately wrong
    items = join_variant_payload(payload)
    assert all(it.modification_types == (ModificationType.SYNONYM_LABEL,) for it in items)


def test_join_params_flatten_to_value_strings():
    items = join_variant_payload(_l1_payload())
    by_key = {it.item_key: it for it in items}
    assert by_key[f"OEB020a_syn_{_VID}"].params == {"B": "Estandar"}
    for it in items:
        assert all(isinstance(v, str) for v in it.params.values())


def test_join_new_param_axis_present_in_params():
    items = join_variant_payload(_pd_payload())
    assert all("Z" in it.params and it.params["Z"] == "zz" for it in items)


def test_join_zero_modification_baseline_is_valid():
    items = join_variant_payload(_baseline_payload())
    assert len(items) == 1
    it = items[0]
    assert it.modification_count == 0
    assert it.modifications == ()
    assert it.modification_types == ()
    assert it.original_key == "OEB020a"
    validate_item(it)  # accepted


def test_join_drops_validation_flag():
    it = join_variant_payload(_l1_payload())[0]
    assert "validation" not in it.to_dict()
    assert not hasattr(it, "validation")


def test_to_dict_matches_proposal_shape():
    it = join_variant_payload(_l1_payload())[0]
    d = it.to_dict()
    assert set(d) == {
        "item_key", "original_key", "params", "resumen", "texto",
        "variante_id", "modification_types", "modification_count",
        "modifications",
    }
    assert d["modification_types"] == ["synonym_label"]
    assert d["modification_count"] == 1
    assert d["modifications"][0]["type"] == "synonym_label"
    assert "concept_key" not in d


def test_join_variant_file_round_trips(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps(_l1_payload(), ensure_ascii=False), encoding="utf-8")
    assert join_variant_file(p) == join_variant_payload(_l1_payload())


def test_join_intermediate_deterministic(tmp_path):
    (tmp_path / "OEB020$").mkdir()
    (tmp_path / "OEB030$").mkdir()
    (tmp_path / "OEB020$" / "v1.json").write_text(
        json.dumps(_l1_payload(), ensure_ascii=False), encoding="utf-8")
    pd = _pd_payload()
    (tmp_path / "OEB030$" / "v2.json").write_text(
        json.dumps(pd, ensure_ascii=False), encoding="utf-8")
    a = join_intermediate(tmp_path)
    b = join_intermediate(tmp_path)
    assert [x.item_key for x in a] == [x.item_key for x in b]
    assert len(a) == 4


def test_join_intermediate_sorted_order(tmp_path):
    (tmp_path / "B_concept").mkdir()
    (tmp_path / "A_concept").mkdir()
    (tmp_path / "B_concept" / "v.json").write_text(
        json.dumps(_baseline_payload(), ensure_ascii=False), encoding="utf-8")
    (tmp_path / "A_concept" / "v.json").write_text(
        json.dumps(_l1_payload(), ensure_ascii=False), encoding="utf-8")
    items = join_intermediate(tmp_path)
    # A_concept (2 leaves) sorts before B_concept (1 leaf)
    assert items[0].variante_id == _VID
    assert items[-1].variante_id == "single_baseline_deadbeef00"


def test_join_intermediate_missing_dir_returns_empty(tmp_path):
    assert join_intermediate(tmp_path / "nope") == []


# --------------------------------------------------------------------------
# E2 — the validator (fail-loud, one class per test)
# --------------------------------------------------------------------------

# NOTE: reference the exception-sensitive surface through `metadata.` rather than
# the top-level imports — `test_module_has_no_side_effects_at_import` reloads the
# module, rebinding `SchemaError`/`validate_item` to a fresh generation; going
# through the module keeps these tests co-generation with the reloaded objects.
def _item(**over):
    base = dict(
        item_key="OEB020a_syn_v1",
        original_key="OEB020a",
        params={"B": "Estandar"},
        resumen="r",
        texto="t",
        variante_id="v1",
        modification_types=(ModificationType.SYNONYM_LABEL,),
        modification_count=1,
        modifications=(Modification(type=ModificationType.SYNONYM_LABEL,
                                    layer=Layer.PARAM_VALUE),),
        concept_key=_CONCEPT_KEY,
    )
    base.update(over)
    return metadata.SyntheticItem(**base)


def test_validate_item_accepts_well_formed():
    metadata.validate_item(_item())  # no raise


def test_validate_item_rejects_missing_item_key():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(item_key=""))


def test_validate_item_rejects_missing_variante_id():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(variante_id=""))


def test_validate_item_rejects_count_mismatch():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(modification_count=2))


def test_validate_item_rejects_types_mismatch():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(modification_types=(ModificationType.NUM_TO_TEXT,)))


def test_validate_item_rejects_malformed_modification():
    m = Modification(type=ModificationType.SYNONYM_LABEL, layer=Layer.PARAM_VALUE)
    object.__setattr__(m, "layer", None)  # frozen-bypass to plant the defect
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(modifications=(m,)))


def test_validate_item_rejects_bad_original_key_prefix():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(original_key="XYZ"))


def test_validate_item_rejects_non_string_texto():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_item(_item(texto=123))


def test_validate_items_rejects_item_key_collision():
    with pytest.raises(metadata.SchemaError):
        metadata.validate_items([_item(), _item()])


def test_validate_items_accepts_join_output():
    metadata.validate_items(metadata.join_variant_payload(_l1_payload()))
    metadata.validate_items(metadata.join_variant_payload(_pd_payload()))


# --------------------------------------------------------------------------
# Data-gated tier — real Stage-B materialisation -> join -> validate
# --------------------------------------------------------------------------

_OC = "OBRA CIVIL"
_HAS_DATA = config.chapter_path(_OC).exists() and config.stage_path(_OC, 5).exists()
_skip_no_data = pytest.mark.skipif(not _HAS_DATA, reason="OBRA CIVIL intermediate JSONs absent")


@_skip_no_data
def test_stage_b_to_metadata_roundtrip_for_concept(tmp_path):
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
    gold_keys = {k for k, v in stage5.items() if v.get("parent_key") == target}

    # A single baseline (no-rule) variant: K=0 -> original_key == real chapter leaf.
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
    validate_items(items)
    for it in items:
        assert it.modification_count == 0          # baseline variant
        assert it.original_key == it.item_key.split("_syn_", 1)[0]
        assert it.original_key in gold_keys        # real chapter leaf
