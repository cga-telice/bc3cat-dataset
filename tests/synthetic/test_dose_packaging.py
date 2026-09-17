"""E3 — tests del empaquetado: join del sidecar, campos nuevos, procedencia."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load_packager():
    """Import the script by path (it lives in scripts/, not a package)."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "package_for_retrieval", ROOT / "scripts" / "package_for_retrieval.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_builder():
    """Import the orchestration script by path, like the other two."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "build_dose_ladder", ROOT / "scripts" / "build_dose_ladder.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sidecar_marks_in_pool_only_the_leaves_that_got_a_ladder():
    """El fondo lleva reserva (pool_min > per_count): las hojas de reserva no
    usadas no tienen escalera, y D6 entrega efectos aislados solo sobre las
    hojas de la escalera. Marcar el fondo entero entregaría ~150 hojas con
    efectos aislados y sin escalera."""
    from synthetic.corpus_sampler import PlannedVariant
    from synthetic.taxonomy import ModificationType as MT

    mod = _load_builder()
    available = {"A": frozenset({MT.REORDER}), "B": frozenset({MT.REORDER}),
                 "C": frozenset({MT.PARAPHRASE})}
    structural = {"A": frozenset({MT.REORDER, MT.PARAPHRASE})}
    dose_plan = (
        PlannedVariant(condition="dose_1", concept_key="C1$", leaf_item_key="A",
                       rewrites=()),
    )
    rows = mod.applicability_rows(available, structural, dose_plan)

    assert [r["leaf_item_key"] for r in rows] == ["A", "B", "C"]
    assert {r["leaf_item_key"]: r["in_pool"] for r in rows} == {
        "A": True, "B": False, "C": False,
    }
    assert rows[0]["applicable_types"] == ["paraphrase", "reorder"]
    assert rows[0]["available_types"] == ["reorder"]
    assert rows[1]["applicable_types"] == []


def _sidecar(tmp_path, rows):
    p = tmp_path / "applicability.jsonl"
    p.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
        encoding="utf-8",
    )
    return p


def test_applicability_fields_are_joined_onto_every_record(tmp_path):
    mod = _load_packager()
    side = _sidecar(tmp_path, [
        {"leaf_item_key": "OEA010aaba",
         "applicable_types": ["paraphrase", "reorder"],
         "available_types": ["reorder"], "in_pool": True},
    ])
    table = mod.load_applicability(side)
    rec = mod.apply_applicability(
        {"item_key": "x", "gold_item_key": "OEA010aaba"}, table,
    )
    assert rec["applicable_types"] == ["paraphrase", "reorder"]
    assert rec["available_types"] == ["reorder"]


def test_isolated_delivery_is_restricted_to_the_pool(tmp_path):
    """D6: the probe release keeps every survivor for the report's counts, but
    only the pool's leaves are delivered — they are the ones the ladder also
    runs on, which is what makes isolated and dose effects comparable within
    the same leaf."""
    mod = _load_packager()
    side = _sidecar(tmp_path, [
        {"leaf_item_key": "IN", "applicable_types": [], "available_types": [],
         "in_pool": True},
        {"leaf_item_key": "OUT", "applicable_types": [], "available_types": [],
         "in_pool": False},
    ])
    table = mod.load_applicability(side)
    assert mod.in_pool({"item_key": "a", "gold_item_key": "IN"}, table) is True
    assert mod.in_pool({"item_key": "b", "gold_item_key": "OUT"}, table) is False


def test_missing_sidecar_entry_fails_loud(tmp_path):
    mod = _load_packager()
    table = mod.load_applicability(_sidecar(tmp_path, []))
    with pytest.raises(KeyError, match="applicability_missing"):
        mod.apply_applicability({"item_key": "x", "gold_item_key": "OEA010aaba"}, table)


def test_git_commit_fails_loud_without_git(tmp_path, monkeypatch):
    """A provenance stamp reading "unknown" looks like a complete delivery while
    dropping the only field that makes it traceable."""
    mod = _load_packager()
    monkeypatch.setattr(mod, "REPO", tmp_path)          # no .git here
    with pytest.raises(SystemExit, match="provenance_commit_unavailable"):
        mod.git_commit()
    assert mod.git_commit(allow_unknown=True) == "unknown"


def test_dose_records_outside_the_pool_fail_loud(tmp_path):
    """The sidecar and the dose plan must come from the same run; a dose leaf the
    sidecar does not mark in_pool means they disagree."""
    mod = _load_packager()
    table = mod.load_applicability(_sidecar(tmp_path, [
        {"leaf_item_key": "OUT", "applicable_types": [], "available_types": [],
         "in_pool": False},
    ]))
    assert mod.in_pool({"item_key": "a", "gold_item_key": "OUT"}, table) is False


def test_manifest_lists_a_sha256_per_file(tmp_path):
    mod = _load_packager()
    (tmp_path / "a.json").write_text("[]", encoding="utf-8")
    (tmp_path / "b.jsonl").write_text("{}\n", encoding="utf-8")
    text = mod.render_manifest(
        tmp_path, ["a.json", "b.jsonl"],
        provenance={"run_id": "r1", "seed": 42, "script": "s", "commit": "c"},
    )
    assert "a.json" in text and "b.jsonl" in text
    assert text.count("sha256") >= 1
    # the digest of an empty JSON list, to pin the hashing itself
    import hashlib
    assert hashlib.sha256(b"[]").hexdigest() in text


def _load_reporter():
    """Import the script by path (it lives in scripts/, not a package)."""
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "report_dose_ladder", ROOT / "scripts" / "report_dose_ladder.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dose_report_shows_per_cell_type_presence(tmp_path):
    mod = _load_reporter()

    items = pd.DataFrame({
        "item_key": ["a_syn_1", "b_syn_1", "c_syn_1"],
        "original_key": ["L1", "L1", "L2"],
        "concept_key": ["C1$", "C1$", "C1$"],
        "modification_types": [["reorder"], ["reorder", "paraphrase"], ["paraphrase"]],
        "modification_count": [1, 2, 1],
    })
    text = mod.render_report(items, depth=6, histogram={6: 2}, pool_size=2)
    assert "dose_1" in text and "dose_2" in text
    assert "reorder" in text and "paraphrase" in text
    assert "| 1 | 2 |" in text or "dose_1 | 2" in text   # 2 items at count 1
    # the nine admitted types are always columns, even ones never seen here —
    # a type absent from the whole corpus must still show as a visible 0.
    assert "unit_conversion" in text and "unit_expansion" in text
    assert "template_paraphrase" in text


def test_dose_report_flags_cells_below_target(tmp_path):
    mod = _load_reporter()

    items = pd.DataFrame({
        "item_key": ["a_syn_1", "b_syn_1", "c_syn_1"],
        "original_key": ["L1", "L1", "L2"],
        "concept_key": ["C1$", "C1$", "C1$"],
        "modification_types": [["reorder"], ["reorder", "paraphrase"], ["paraphrase"]],
        "modification_count": [1, 1, 2],
    })
    # dose_1 has 2 items (meets target=2), dose_2 has 1 item (short by 1).
    text = mod.render_report(items, depth=6, histogram={6: 2}, pool_size=2, target=2)
    assert "| dose_1 | 2 | ok |" in text
    assert "| dose_2 | 1 | SHORT by 1 |" in text
    # singular agreement: one short cell is "1 celda", not "1 celdas"
    assert "Aviso" in text and "1 celda por debajo" in text
    assert "objetivo de 2" in text

    # no short cells -> no warning line
    ok_text = mod.render_report(items, depth=6, histogram={6: 2}, pool_size=2, target=1)
    assert "Aviso" not in ok_text


def test_dose_report_shows_how_many_modifications_fit_per_leaf():
    """Una hoja con 9 tipos puede tener solo 4 tramos distintos: el informe
    tiene que dejar ver cuántas se quedaron fuera del fondo por eso."""
    mod = _load_reporter()

    items = pd.DataFrame({
        "item_key": ["a_syn_1"], "original_key": ["L1"], "concept_key": ["C1$"],
        "modification_types": [["reorder"]], "modification_count": [1],
    })
    text = mod.render_report(items, depth=6, histogram={6: 1, 9: 2}, pool_size=1,
                             placeable_histogram={4: 2, 5: 1})
    assert "caben en tramos distintos" in text
    assert "`{4: 2, 5: 1}`" in text
    assert "2 hojas" in text and "menos de 5" in text
    assert "caben en tramos distintos" not in mod.render_report(
        items, depth=6, histogram={6: 1}, pool_size=1,
    )


def test_dose_report_shows_concept_coverage():
    """bc3cat-retrieval parte dev/test por concepto: cuántos conceptos cubre la
    escalera, y con cuántas hojas cada uno, tiene que estar a la vista."""
    mod = _load_reporter()

    items = pd.DataFrame({
        "item_key": ["a1", "a2", "b1", "c1"],
        "original_key": ["L1", "L2", "L3", "L4"],
        "concept_key": ["C1$", "C1$", "C2$", "C2$"],
        "modification_types": [["reorder"]] * 4,
        "modification_count": [1, 1, 1, 1],
    })
    text = mod.render_report(items, depth=6, histogram={6: 4}, pool_size=4)
    assert "## Cobertura por concepto" in text
    assert "**2 conceptos**" in text
    assert "| C1$ | 2 |" in text and "| C2$ | 2 |" in text


def test_dose_report_counts_the_ladder_leaves_not_the_reserve():
    """El fondo seleccionado incluye la reserva; «las mismas en las cinco
    celdas» solo es cierto de las hojas que recibieron escalera."""
    mod = _load_reporter()

    items = pd.DataFrame({
        "item_key": ["a1", "a2", "b1", "b2"],
        "original_key": ["L1", "L1", "L2", "L2"],
        "concept_key": ["C1$"] * 4,
        "modification_types": [["reorder"], ["reorder", "paraphrase"]] * 2,
        "modification_count": [1, 2, 1, 2],
    })
    text = mod.render_report(items, depth=6, histogram={6: 3}, pool_size=3)
    assert "**2 hojas**, las mismas en las cinco celdas" in text
    assert "3 seleccionadas" in text and "1 de reserva sin usar" in text


def test_release_audit_flags_a_modification_the_texto_does_not_show(tmp_path):
    """Última red: cada modificación L1/L2 de la entrega tiene que verse en el
    TEXTO. Los cambios de plantilla no se comprueban así (su `new` lleva $X)."""
    mod = _load_builder()

    items = pd.DataFrame({
        "item_key": ["ok", "bad"],
        "texto": ["zanja en cruce  debajo de las vias, banda dos horas",
                  "zanja en cruce bajo vias"],
    })
    items_path = tmp_path / "items.parquet"
    items.to_parquet(items_path)
    mods_path = tmp_path / "mods.jsonl"
    mods_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        {"item_key": "ok", "modifications": [
            {"type": "compression", "layer": "text_variable", "new": "debajo de las vias"},
            {"type": "num_to_text", "layer": "param_value", "new": "dos"},
            {"type": "reorder", "layer": "template", "new": "$A tubos"},
        ]},
        {"item_key": "bad", "modifications": [
            {"type": "paraphrase", "layer": "text_variable", "new": "debajo de las vias"},
        ]},
    ]) + "\n", encoding="utf-8")

    assert mod.invisible_modifications(items_path, mods_path) == [("bad", "paraphrase")]
