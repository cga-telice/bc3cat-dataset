"""Sprint 22 — Phase G Task G2: loader utilities (read API + 1:1 join + views).

Three tiers (the Sprint 21 gating shape):

* **Always-on stdlib** — public-surface pin, import-hygiene / no-side-effects
  seam guards, the default-path call-time resolution, the
  `load_modifications` JSONL round-trip from a hand-written fixture (baseline
  -> `[]`), and the CLI no-subcommand exit. These need neither `pandas` nor
  `pyarrow`. The join-mismatch fail-loud is exercised with only `pandas`
  (a small in-memory frame), never the Parquet engine.

* **`pyarrow`-gated** (`pytest.importorskip`) — `load_items` reads a
  `write_release`-produced Parquet; `join` 1:1 + `modifications`-column shape +
  no-mutation; `long_view` / `short_view` column set + `text`/`text_norm`.

* **Data-gated + `pyarrow`-gated** — skipped when the committed
  `data/intermediate/OBRA CIVIL/` JSONs are absent; otherwise materialises one
  real concept (`stage_b` -> `join_intermediate`), `write_release`s it, then
  `load_items` + `load_modifications` + `join` round-trip to a 1:1 frame and the
  views preserve the `item_key` set.
"""

import importlib
import inspect
import json
import types

import pytest

from synthetic import loaders
from synthetic.loaders import (
    LoaderError,
    load_items,
    load_modifications,
    join,
    long_view,
    short_view,
    main,
)
from synthetic import packaging
from synthetic.metadata import SyntheticItem, join_intermediate
from synthetic.taxonomy import Modification, ModificationType, TYPE_TO_LAYER
from utils import config
from utils.text_processing import normalize_text


# --------------------------------------------------------------------------
# Inline SyntheticItem fixtures (mirror the Sprint 21 packaging fixtures)
# --------------------------------------------------------------------------

_CONCEPT = "OEB020$"
_SYN = ModificationType.SYNONYM_LABEL
_PAR = ModificationType.PARAPHRASE

MODS_NAME = packaging.MODIFICATIONS_FILENAME
ITEMS_NAME = packaging.ITEMS_FILENAME


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
        _item("OEB020b_syn_v1", types=(_SYN, _PAR),
              params={"A": "2"}, resumen="muro de hormigón",
              texto="Canalización de hormigón armado"),
        _item("OEB020a_syn_v1", types=(_SYN,), params={"A": "1"},
              resumen="zanja", texto="Excavación en zanja"),
        _item("OEB020c_syn_v1", types=(), resumen="baseline",
              texto="texto baseline"),
    ]


# --------------------------------------------------------------------------
# Public surface + import hygiene + side effects
# --------------------------------------------------------------------------

def test_module_exposes_public_surface():
    for name in ("LoaderError", "load_items", "load_modifications", "join",
                 "long_view", "short_view", "main"):
        assert hasattr(loaders, name)


def test_loaders_imports_no_generation_or_review_stack():
    src = inspect.getsource(loaders)
    for forbidden in ("import stage_b", "import run_synthetic",
                      "import stage_runners", "import review", "import mutator",
                      "synthetic.stage_b", "synthetic.run_synthetic",
                      "synthetic.stage_runners", "synthetic.review",
                      "synthetic.mutator", "import layer_", "synthetic.layer_"):
        assert forbidden not in src, forbidden
    for value in vars(loaders).values():
        if isinstance(value, types.ModuleType):
            for bad in ("stage_b", "run_synthetic", "stage_runners", "review",
                        "mutator"):
                assert not value.__name__.endswith(bad), value.__name__
            assert ".layer_" not in value.__name__, value.__name__


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(loaders)
    assert callable(reloaded.join)


def test_default_paths_resolve_under_processed_dir():
    assert loaders.default_items_path() == (
        config.SYNTHETIC_PROCESSED_DIR / packaging.ITEMS_FILENAME
    )
    assert loaders.default_modifications_path() == (
        config.SYNTHETIC_PROCESSED_DIR / packaging.MODIFICATIONS_FILENAME
    )


# --------------------------------------------------------------------------
# load_modifications — always-on stdlib
# --------------------------------------------------------------------------

def test_load_modifications_round_trip(tmp_path):
    p = tmp_path / MODS_NAME
    p.write_text(
        '{"item_key": "OEB020a_syn_v1", "modifications": '
        '[{"type": "synonym_label", "layer": "param_value"}]}\n'
        '{"item_key": "OEB020b_syn_v1", "modifications": '
        '[{"type": "synonym_label", "layer": "param_value"}, '
        '{"type": "paraphrase", "layer": "text_variable"}]}\n',
        encoding="utf-8",
    )
    back = load_modifications(p)
    assert set(back) == {"OEB020a_syn_v1", "OEB020b_syn_v1"}
    assert [m.type for m in back["OEB020b_syn_v1"]] == [_SYN, _PAR]
    assert all(isinstance(m, Modification) for m in back["OEB020a_syn_v1"])


def test_load_modifications_baseline_empty_list(tmp_path):
    p = tmp_path / MODS_NAME
    p.write_text('{"item_key": "OEB020c_syn_v1", "modifications": []}\n',
                 encoding="utf-8")
    back = load_modifications(p)
    assert back == {"OEB020c_syn_v1": []}


# --------------------------------------------------------------------------
# join mismatch — fail-loud, exercised with pandas only (no Parquet engine)
# --------------------------------------------------------------------------

def test_join_mismatch_is_fail_loud():
    pd = pytest.importorskip("pandas")
    items = pd.DataFrame(
        {"item_key": ["OEB020a_syn_v1", "OEB020b_syn_v1"]}
    )
    # sidecar is missing OEB020b_syn_v1 -> 1:1 violated
    mods = {"OEB020a_syn_v1": []}
    with pytest.raises(loaders.LoaderError):
        loaders.join(items=items, modifications=mods)


def test_main_no_subcommand_returns_nonzero():
    assert main([]) != 0


# --------------------------------------------------------------------------
# pyarrow-gated tier — load_items / join / views
# --------------------------------------------------------------------------

def test_load_items_round_trip(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df = load_items(paths["items"])
    assert list(df.columns) == list(packaging.ITEM_COLUMNS)
    assert set(df["item_key"]) == {it.item_key for it in items}


def test_join_one_to_one_adds_modifications_column(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df = join(items_path=paths["items"], mods_path=paths["modifications"])
    assert "modifications" in df.columns
    assert len(df) == len(items)
    assert list(df["item_key"]) == [
        "OEB020a_syn_v1", "OEB020b_syn_v1", "OEB020c_syn_v1",
    ]
    stacked = df[df["item_key"] == "OEB020b_syn_v1"].iloc[0]
    assert [m["type"] for m in stacked["modifications"]] == [
        "synonym_label", "paraphrase",
    ]
    baseline = df[df["item_key"] == "OEB020c_syn_v1"].iloc[0]
    assert baseline["modifications"] == []


def test_join_does_not_mutate_input(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df_in = load_items(paths["items"])
    cols_before = list(df_in.columns)
    mods = load_modifications(paths["modifications"])
    out = join(items=df_in, modifications=mods)
    assert "modifications" not in df_in.columns
    assert list(df_in.columns) == cols_before
    assert "modifications" in out.columns


def test_join_frame_mismatch_is_fail_loud(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df = load_items(paths["items"])
    mods = load_modifications(paths["modifications"])
    mods.pop("OEB020c_syn_v1")  # sidecar now missing a key present in items
    with pytest.raises(loaders.LoaderError):
        loaders.join(items=df, modifications=mods)


def test_long_view_text_is_texto_and_norm_matches(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df = load_items(paths["items"])
    lv = long_view(df)
    assert "text" in lv.columns and "text_norm" in lv.columns
    assert list(lv["text"]) == list(df["texto"])
    assert list(lv["text_norm"]) == [normalize_text(t) for t in lv["text"]]
    for col in ("item_key", "original_key", "concept_key", "params",
                "variante_id", "modification_types", "modification_count"):
        assert col in lv.columns


def test_short_view_text_is_resumen_and_norm_matches(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df = load_items(paths["items"])
    sv = short_view(df)
    assert list(sv["text"]) == list(df["resumen"])
    assert list(sv["text_norm"]) == [normalize_text(t) for t in sv["text"]]


def test_views_have_no_modifications_column(tmp_path):
    pytest.importorskip("pyarrow")
    items = _mixed_fixture()
    paths = packaging.write_release(items, out_dir=tmp_path)
    df = load_items(paths["items"])
    assert "modifications" not in long_view(df).columns
    assert "modifications" not in short_view(df).columns
    # no fabricated OEB-only columns
    for forbidden in ("id", "ud", "concept"):
        assert forbidden not in long_view(df).columns
        assert forbidden not in short_view(df).columns


# --------------------------------------------------------------------------
# Data-gated + pyarrow-gated — real OBRA CIVIL concept
# --------------------------------------------------------------------------

_OC = "OBRA CIVIL"
_HAS_DATA = config.chapter_path(_OC).exists() and config.stage_path(_OC, 5).exists()
_skip_no_data = pytest.mark.skipif(
    not _HAS_DATA, reason="OBRA CIVIL intermediate JSONs absent"
)


@_skip_no_data
def test_real_concept_round_trip_load_join_views(tmp_path):
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
    paths = packaging.write_release(items, out_dir=out)

    df = load_items(paths["items"])
    mods = load_modifications(paths["modifications"])
    joined = join(items=df, modifications=mods)

    assert set(joined["item_key"]) == joined_keys
    assert set(load_modifications(paths["modifications"])) == joined_keys
    assert set(long_view(df)["item_key"]) == joined_keys
    assert set(short_view(df)["item_key"]) == joined_keys
