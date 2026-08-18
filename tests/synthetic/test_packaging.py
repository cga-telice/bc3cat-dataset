"""Sprint 21 — Phase G Task G1: release packaging (items Parquet + sidecar JSONL).

Three tiers:

* **Always-on stdlib** — `ITEM_COLUMNS` pin, sidecar shape/round-trip/dedup,
  the `write_release` validate-first no-partial guarantee on the JSONL side, the
  import-hygiene / no-side-effects seam guards, and the CLI no-subcommand exit.
  These need neither `pandas` nor `pyarrow`.

* **`pyarrow`-gated** (`pytest.importorskip`) — `items_to_frame` schema + sort,
  the no-`modifications`-column invariant, the Parquet atomic round-trip, and
  byte-identical determinism. Skipped (never failed) where the dep is absent.

* **Data-gated + `pyarrow`-gated** — skipped when the committed
  `data/intermediate/OBRA CIVIL/` JSONs are absent; otherwise materialises one
  real concept through `stage_b`, joins it (Sprint 19 `join_intermediate`),
  `write_release`s it, rereads both files, and asserts the Parquet `item_key`
  set == the sidecar key set == the joined `item_key` set.
"""

import importlib
import inspect
import json
import types

import pytest

from synthetic import packaging
from synthetic.packaging import (
    PackagingError,
    ITEM_COLUMNS,
    items_to_frame,
    modifications_sidecar,
    write_items_parquet,
    write_modifications_jsonl,
    write_release,
    read_items_parquet,
    read_modifications_jsonl,
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
          params=None, original_key=None):
    mods = tuple(Modification(type=t, layer=TYPE_TO_LAYER[t]) for t in types)
    return SyntheticItem(
        item_key=item_key,
        original_key=original_key or item_key.split("_syn_", 1)[0],
        params=params or {},
        resumen=resumen,
        texto=texto,
        variante_id="v1",
        modification_types=tuple(types),
        modification_count=len(mods),
        modifications=mods,
        concept_key=concept,
    )


def _mixed_fixture():
    """A single-mod, a stacked, and a baseline item (deliberately unsorted)."""
    return [
        _item("OEB020b_syn_v1", types=(_SYN, _PAR), params={"A": "2"}),
        _item("OEB020a_syn_v1", types=(_SYN,), params={"A": "1"}),
        _item("OEB020c_syn_v1", types=()),  # baseline, empty log
    ]


# --------------------------------------------------------------------------
# Public surface + import hygiene + side effects
# --------------------------------------------------------------------------

def test_module_exposes_public_surface():
    for name in ("PackagingError", "ITEM_COLUMNS", "items_to_frame",
                 "modifications_sidecar", "write_items_parquet",
                 "write_modifications_jsonl", "write_release",
                 "read_items_parquet", "read_modifications_jsonl", "main"):
        assert hasattr(packaging, name)


def test_packaging_imports_no_stage_b_run_synthetic_stage_runners_or_review():
    src = inspect.getsource(packaging)
    for forbidden in ("import stage_b", "import run_synthetic",
                      "import stage_runners", "import review",
                      "synthetic.stage_b", "synthetic.run_synthetic",
                      "synthetic.stage_runners", "synthetic.review"):
        assert forbidden not in src, forbidden
    for value in vars(packaging).values():
        if isinstance(value, types.ModuleType):
            for bad in ("stage_b", "run_synthetic", "stage_runners", "review"):
                assert not value.__name__.endswith(bad), value.__name__


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(packaging)
    assert callable(reloaded.write_release)


# --------------------------------------------------------------------------
# ITEM_COLUMNS pin
# --------------------------------------------------------------------------

def test_item_columns_frozen_order():
    assert ITEM_COLUMNS == (
        "item_key", "original_key", "concept_key", "params", "resumen",
        "texto", "variante_id", "modification_types", "modification_count",
    )
    assert "modifications" not in ITEM_COLUMNS


# --------------------------------------------------------------------------
# Sidecar — always-on stdlib
# --------------------------------------------------------------------------

def test_modifications_sidecar_one_line_per_item():
    rows = modifications_sidecar(_mixed_fixture())
    assert [r["item_key"] for r in rows] == [
        "OEB020a_syn_v1", "OEB020b_syn_v1", "OEB020c_syn_v1",
    ]
    stacked = next(r for r in rows if r["item_key"] == "OEB020b_syn_v1")
    assert [m["type"] for m in stacked["modifications"]] == [
        "synonym_label", "paraphrase",
    ]


def test_baseline_item_sidecar_has_empty_list():
    rows = modifications_sidecar([_item("OEB020c_syn_v1", types=())])
    assert rows == [{"item_key": "OEB020c_syn_v1", "modifications": []}]


def test_sidecar_jsonl_round_trip(tmp_path):
    items = _mixed_fixture()
    p = tmp_path / MODS_NAME
    write_modifications_jsonl(items, p)
    back = read_modifications_jsonl(p)
    assert set(back) == {it.item_key for it in items}
    assert back["OEB020b_syn_v1"] == list(
        next(it for it in items if it.item_key == "OEB020b_syn_v1").modifications
    )
    assert back["OEB020c_syn_v1"] == []


def test_sidecar_atomic_no_tmp_left(tmp_path):
    sub = tmp_path / "processed"
    write_modifications_jsonl(_mixed_fixture(), sub / MODS_NAME)
    assert (sub / MODS_NAME).exists()
    assert list(sub.glob(".*.tmp")) == []


# NOTE: `test_module_has_no_side_effects_at_import` reloads `packaging`,
# rebinding the module dict its functions close over. So a function reached by
# its top-level imported name raises the *reloaded* `PackagingError`, which is a
# different class object than the top-level imported `PackagingError`. Tests that
# assert exception identity (`pytest.raises`) must reach both the function and
# the exception through `packaging.` so they are the same generation (the Sprint
# 19/20 reload pattern).
def test_sidecar_duplicate_item_key_fail_loud(tmp_path):
    dupes = [_item("OEB020a_syn_v1", types=(_SYN,)),
             _item("OEB020a_syn_v1", types=(_PAR,))]
    with pytest.raises(packaging.PackagingError):
        packaging.write_modifications_jsonl(dupes, tmp_path / MODS_NAME)


def test_read_sidecar_duplicate_item_key_fail_loud(tmp_path):
    p = tmp_path / MODS_NAME
    p.write_text(
        '{"item_key": "X", "modifications": []}\n'
        '{"item_key": "X", "modifications": []}\n',
        encoding="utf-8",
    )
    with pytest.raises(packaging.PackagingError):
        packaging.read_modifications_jsonl(p)


# --------------------------------------------------------------------------
# write_release validate-first — always-on (fails before any pyarrow touch)
# --------------------------------------------------------------------------

def test_write_release_validates_first_no_partial(tmp_path):
    bad = SyntheticItem(
        item_key="OEB020a_syn_v1",
        original_key="OEB020a",
        params={},
        resumen="r",
        texto="t",
        variante_id="v1",
        modification_types=(_SYN,),
        modification_count=5,  # mismatch vs. len(modifications) == 1
        modifications=(Modification(type=_SYN, layer=TYPE_TO_LAYER[_SYN]),),
        concept_key=_CONCEPT,
    )
    with pytest.raises(packaging.PackagingError):
        packaging.write_release([bad], out_dir=tmp_path)
    assert list(tmp_path.iterdir()) == []  # nothing written


def test_modifications_sidecar_dedup_independent_of_validation():
    # sidecar is pure: it does not validate, so a baseline + stacked mix is fine
    rows = modifications_sidecar(_mixed_fixture())
    assert len(rows) == 3


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_main_no_subcommand_returns_nonzero():
    assert main([]) != 0


# --------------------------------------------------------------------------
# pyarrow-gated tier — items frame + Parquet round-trip + determinism
# --------------------------------------------------------------------------

MODS_NAME = "BC3CAT_Syn_modifications.jsonl"
ITEMS_NAME = "BC3CAT_Syn_items.parquet"


def test_items_frame_columns_and_sort():
    pytest.importorskip("pyarrow")
    df = items_to_frame(_mixed_fixture())
    assert list(df.columns) == list(ITEM_COLUMNS)
    assert list(df["item_key"]) == [
        "OEB020a_syn_v1", "OEB020b_syn_v1", "OEB020c_syn_v1",
    ]
    stacked = df[df["item_key"] == "OEB020b_syn_v1"].iloc[0]
    assert stacked["modification_types"] == ["synonym_label", "paraphrase"]
    assert stacked["params"] == {"A": "2"}
    assert int(stacked["modification_count"]) == 2
    baseline = df[df["item_key"] == "OEB020c_syn_v1"].iloc[0]
    assert baseline["modification_types"] == []
    assert int(baseline["modification_count"]) == 0


def test_items_frame_has_no_modifications_column():
    pytest.importorskip("pyarrow")
    df = items_to_frame(_mixed_fixture())
    assert "modifications" not in df.columns


def test_items_to_frame_validates_first():
    pytest.importorskip("pyarrow")
    bad = SyntheticItem(
        item_key="OEB020a_syn_v1", original_key="OEB020a", params={},
        resumen="r", texto="t", variante_id="v1",
        modification_types=(_PAR,),  # disagrees with modifications below
        modification_count=1,
        modifications=(Modification(type=_SYN, layer=TYPE_TO_LAYER[_SYN]),),
        concept_key=_CONCEPT,
    )
    with pytest.raises(packaging.PackagingError):
        packaging.items_to_frame([bad])


def test_items_parquet_round_trip(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    p = tmp_path / ITEMS_NAME
    write_items_parquet(items, p)
    assert p.exists()
    assert list(tmp_path.glob(".*.tmp")) == []
    df = read_items_parquet(p)
    assert set(df["item_key"]) == {it.item_key for it in items}
    assert list(df.columns) == list(ITEM_COLUMNS)
    a = df[df["item_key"] == "OEB020a_syn_v1"].iloc[0]
    assert a["resumen"] == "r" and a["texto"] == "t"
    assert a["concept_key"] == _CONCEPT and a["variante_id"] == "v1"


def test_release_deterministic_byte_identical(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    d1, d2 = tmp_path / "r1", tmp_path / "r2"
    write_release(items, out_dir=d1)
    write_release(items, out_dir=d2)
    for name in (ITEMS_NAME, MODS_NAME):
        assert (d1 / name).read_bytes() == (d2 / name).read_bytes()


def test_write_release_files_join_one_to_one(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = write_release(items, out_dir=tmp_path)
    assert paths["items"].name == ITEMS_NAME
    assert paths["modifications"].name == MODS_NAME
    df = read_items_parquet(paths["items"])
    sidecar = read_modifications_jsonl(paths["modifications"])
    assert set(df["item_key"]) == set(sidecar) == {it.item_key for it in items}


# --------------------------------------------------------------------------
# Data-gated + pyarrow-gated — real OBRA CIVIL concept
# --------------------------------------------------------------------------

_OC = "OBRA CIVIL"
_HAS_DATA = config.chapter_path(_OC).exists() and config.stage_path(_OC, 5).exists()
_skip_no_data = pytest.mark.skipif(
    not _HAS_DATA, reason="OBRA CIVIL intermediate JSONs absent"
)


@_skip_no_data
def test_write_release_real_concept_joins_one_to_one(tmp_path):
    pytest.importorskip("pyarrow")
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
    intermediate = tmp_path / "intermediate"
    materialize_catalog_entry({target: stage2[target]}, entry, out_dir=intermediate)

    items = join_intermediate(intermediate)
    assert items
    joined_keys = {it.item_key for it in items}

    out = tmp_path / "processed"
    paths = write_release(items, out_dir=out)
    df = read_items_parquet(paths["items"])
    sidecar = read_modifications_jsonl(paths["modifications"])

    assert set(df["item_key"]) == joined_keys
    assert set(sidecar) == joined_keys
    assert list(df.columns) == list(ITEM_COLUMNS)
