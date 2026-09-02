"""Sprint 39 — hermetic tests for :mod:`synthetic.corpus_driver`.

Tiny hand-built stage fixture (two concepts in the `tiny_chapter` style) and a
toy pantry/plan built by hand. No real parquet, no LLM, no real menus.
"""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from synthetic import packaging
from synthetic.corpus_driver import CorpusRunStats, run_corpus
from synthetic.corpus_sampler import PlannedVariant
from synthetic.loaders import join, load_items, load_modifications
from synthetic.pantry import ApprovedRewrite, Usage
from synthetic.target_scanner import scan_chapter
from synthetic.taxonomy import ModificationType


C1 = "CTEST010$"
C3 = "CTEST030$"

_STAGE = {
    C1: {
        "ud": "ud",
        "concept": "prueba uno",
        "parameters": {
            "A": {
                "label": "TRABAJO",
                "values": [
                    {"label": "a", "value": "Diurno"},
                    {"label": "b", "value": "Nocturno"},
                ],
            },
            "B": {
                "label": "TIPO",
                "values": [
                    {"label": "a", "value": "Normal"},
                    {"label": "b", "value": "Rocoso"},
                ],
            },
        },
        "text_variables": {
            "K": '"normal" * (%B=="a") + "rocoso" * (%B=="b")',
        },
        "resumen": "Prueba uno $A $K",
        "texto": "Prueba uno con $A en $B",
    },
    C3: {
        "ud": "ud",
        "concept": "prueba tres",
        "parameters": {
            "D": {
                "label": "MATERIAL",
                "values": [
                    {"label": "a", "value": "PVC"},
                    {"label": "b", "value": "HDPE"},
                ],
            },
        },
        "text_variables": {},
        "resumen": "Prueba tres $D",
        "texto": "Prueba tres unitaria $D",
    },
}


def _tiny_stage() -> dict:
    return copy.deepcopy(_STAGE)


def _rewrite(mtype, dedup_key, payload, concepts=(C1, C3), ci=0):
    return ApprovedRewrite(
        mtype=mtype,
        dedup_key=tuple(dedup_key),
        canonical=" / ".join(str(p) for p in dedup_key),
        candidate_index=ci,
        payload=dict(payload),
        usages=tuple(Usage(c, None) for c in concepts),
    )


def _syn_diurno():
    return _rewrite(
        ModificationType.SYNONYM_LABEL,
        ("TRABAJO", "Diurno"),
        {"original": "Diurno", "new": "Turno diurno"},
        concepts=(C1,),
    )


def _syn_pvc():
    return _rewrite(
        ModificationType.SYNONYM_LABEL,
        ("MATERIAL", "PVC"),
        {"original": "PVC", "new": "Cloruro de polivinilo"},
        concepts=(C3,),
    )


def _run(tmp_path, plan, stage=None, workers=1):
    out_dir = tmp_path / "release"
    report_path = tmp_path / "report.md"
    stats = run_corpus(
        stage if stage is not None else _tiny_stage(),
        tuple(plan),
        out_dir=out_dir,
        report_path=report_path,
        workers=workers,
    )
    return stats, out_dir, report_path


# ----- tests --------------------------------------------------------------


def test_run_corpus_produces_valid_release(tmp_path):
    plan = (
        PlannedVariant("single_synonym_label", C1, "CTEST010aa", (_syn_diurno(),)),
        PlannedVariant("single_synonym_label", C3, "CTEST030a", (_syn_pvc(),)),
    )
    stats, out_dir, report_path = _run(tmp_path, plan)
    assert isinstance(stats, CorpusRunStats)

    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    mods = load_modifications(out_dir / packaging.MODIFICATIONS_FILENAME)
    joined = join(items=items, modifications=mods)  # must not raise
    assert len(joined) == len(items) == 2
    assert list(items.columns) == list(packaging.ITEM_COLUMNS)
    # unique traceability triple
    triples = set(
        zip(items["item_key"], items["original_key"], items["variante_id"])
    )
    assert len(triples) == 2

    row = stats.per_condition["single_synonym_label"]
    assert row["planned"] == 2
    assert row["produced"] == 2
    assert row["unique_rewrites"] == 2
    assert row["max_reuse"] == 1
    # compatibility-built plan (each leaf selects its rewritten value):
    # the driver's no-op backstop stays at zero
    assert row["noop_dropped"] == 0
    assert stats.totals["noop_dropped"] == 0
    assert stats.totals["produced"] == 2

    report = report_path.read_text(encoding="utf-8")
    assert "single_synonym_label" in report
    assert "Totals" in report


def test_synthetic_item_pairs_with_original(tmp_path):
    plan = (
        PlannedVariant("single_synonym_label", C1, "CTEST010aa", (_syn_diurno(),)),
    )
    stats, out_dir, _ = _run(tmp_path, plan)
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    assert len(items) == 1
    row = items.iloc[0]
    # original_key is the planned leaf; keys are stable under L1 mutation
    assert row["original_key"] == "CTEST010aa"
    assert row["item_key"].startswith("CTEST010aa_syn_")
    assert row["concept_key"] == C1
    # the change was really applied — texts differ from the original leaf's
    assert row["resumen"] == "Prueba uno Turno diurno normal"
    assert row["texto"] == "Prueba uno con Turno diurno en Normal"
    assert row["resumen"] != "Prueba uno Diurno normal"
    assert row["texto"] != "Prueba uno con Diurno en Normal"
    assert row["modification_types"][0] == "synonym_label"
    assert row["params"]["A"] == "Turno diurno"


def test_noop_variant_dropped_and_counted(tmp_path):
    noop = _rewrite(
        ModificationType.SYNONYM_LABEL,
        ("TRABAJO", "Diurno"),
        {"original": "Diurno", "new": "Diurno"},  # applies, changes nothing
        concepts=(C1,),
    )
    plan = (
        PlannedVariant("single_synonym_label", C1, "CTEST010aa", (noop,)),
        PlannedVariant("single_synonym_label", C3, "CTEST030a", (_syn_pvc(),)),
    )
    stats, out_dir, _ = _run(tmp_path, plan)
    row = stats.per_condition["single_synonym_label"]
    assert row["noop_dropped"] == 1
    assert row["produced"] == 1
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    assert len(items) == 1
    assert items.iloc[0]["concept_key"] == C3


def test_composition_conflict_skipped_not_raised(tmp_path):
    # two L2 rewrites on the SAME (var, condition) target — paraphrase and
    # expansion of the fragment "normal" — collide on composition's canonical
    # key: the variant is discarded and counted, never raised.
    para = _rewrite(
        ModificationType.PARAPHRASE,
        ("normal",),
        {"original": "normal", "new": "estándar"},
        concepts=(C1,),
    )
    expa = _rewrite(
        ModificationType.EXPANSION,
        ("normal",),
        {"original": "normal", "new": "normal de tipo corriente"},
        concepts=(C1,),
    )
    plan = (
        PlannedVariant("all_combined", C1, "CTEST010aa", (para, expa)),
    )
    stats, out_dir, _ = _run(tmp_path, plan)
    row = stats.per_condition["all_combined"]
    assert row["composition_conflicts"] == 1
    assert row["produced"] == 0
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    assert len(items) == 0


def test_placeholder_residue_raises(tmp_path):
    stage = _tiny_stage()
    inv = scan_chapter(copy.deepcopy(stage))
    target = next(
        t
        for t in inv.by_type[ModificationType.TEMPLATE_PARAPHRASE]
        if t.dedup_key[0] == "RESUMEN" and t.usages[0].concept_key == C3
    )
    residue = _rewrite(
        ModificationType.TEMPLATE_PARAPHRASE,
        target.dedup_key,
        {"original": "Prueba tres $D", "new": "Prueba tres [[X]] $D"},
        concepts=(C3,),
    )
    plan = (
        PlannedVariant("single_template_paraphrase", C3, "CTEST030a", (residue,)),
    )
    with pytest.raises(ValueError, match="residue"):
        run_corpus(
            stage,
            plan,
            out_dir=tmp_path / "release",
            report_path=tmp_path / "report.md",
        )


def test_target_not_found_skipped_and_counted(tmp_path):
    # a pantry rewrite whose target no longer scans (value not in the stage)
    # is skipped and counted, not crashed on (Task-1 approved deviation).
    ghost = _rewrite(
        ModificationType.SYNONYM_LABEL,
        ("TRABAJO", "Vespertino"),
        {"original": "Vespertino", "new": "Turno vespertino"},
        concepts=(C1,),
    )
    plan = (
        PlannedVariant("single_synonym_label", C1, "CTEST010aa", (ghost,)),
        PlannedVariant("single_synonym_label", C3, "CTEST030a", (_syn_pvc(),)),
    )
    stats, out_dir, _ = _run(tmp_path, plan)
    row = stats.per_condition["single_synonym_label"]
    assert row["target_not_found"] == 1
    assert row["produced"] == 1
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    assert len(items) == 1


def test_all_slot_rules_cover_planned_leaf(tmp_path):
    # The same L2 fragment "apto" lives under TWO conditions (%C=="a" and
    # %C=="b") of var L. The planned leaf selects C=b: first-slot-only
    # emission would mutate only the %C=a slot and no-op; all-slot emission
    # must land on the leaf. Conceptually it is still ONE modification.
    stage = {
        "CTEST050$": {
            "ud": "ud",
            "concept": "prueba cinco",
            "parameters": {
                "A": {
                    "label": "TRABAJO",
                    "values": [
                        {"label": "a", "value": "Diurno"},
                        {"label": "b", "value": "Nocturno"},
                    ],
                },
                "C": {
                    "label": "MODO",
                    "values": [
                        {"label": "a", "value": "Alfa"},
                        {"label": "b", "value": "Beta"},
                    ],
                },
            },
            "text_variables": {
                "L": '"apto" * (%C=="a") + "apto" * (%C=="b")',
            },
            "resumen": "Prueba cinco $A $L $C",
            "texto": "Prueba cinco con $A y $L en $C",
        },
    }
    rw = _rewrite(
        ModificationType.PARAPHRASE,
        ("apto",),
        {"original": "apto", "new": "adecuado"},
        concepts=("CTEST050$",),
    )
    plan = (
        PlannedVariant("single_paraphrase", "CTEST050$", "CTEST050ab", (rw,)),
    )
    stats, out_dir, _ = _run(tmp_path, plan, stage=stage)
    row = stats.per_condition["single_paraphrase"]
    assert row["noop_dropped"] == 0
    assert row["produced"] == 1
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    item = items.iloc[0]
    # the rewrite landed on the planned leaf (C=b slot was covered)
    assert item["texto"] == "Prueba cinco con Diurno y adecuado en Beta"
    assert item["texto"] != "Prueba cinco con Diurno y apto en Beta"
    # one distinct rewrite -> ONE conceptual modification, however many slots
    assert item["modification_count"] == 1
    assert list(item["modification_types"]) == ["paraphrase"]
    mods = load_modifications(out_dir / packaging.MODIFICATIONS_FILENAME)
    assert len(mods[item["item_key"]]) == 1


def test_condition_selects_bc3_and_python_styles():
    # The real OEB same-var duplicate-fragment groups (OEB190/OEB200, '20 cm')
    # carry raw BC3-style conditions (`%A=a`, unquoted `=`); Python-style
    # (`%C=="b"`, `or`-chains) must keep working, and garbage stays False.
    from synthetic.corpus_driver import _condition_selects

    labels = {"A": "b", "C": "b"}
    assert _condition_selects("%A=b", labels)
    assert not _condition_selects("%A=a", labels)
    assert _condition_selects('%C=="b"', labels)
    assert not _condition_selects('%C=="a"', labels)
    assert _condition_selects('%C=="a" or %A=b', labels)
    assert not _condition_selects("%Z=b", labels)
    assert not _condition_selects("%A=,", labels)


def test_all_combined_renders_both_template_fields(tmp_path):
    # an all_combined variant carrying a RESUMEN-template AND a
    # TEXTO-template rewrite: both must compose (the composition canonical
    # key includes the field), both must render, and the frozen E2 schema
    # must accept the duplicated modification type.
    stage = _tiny_stage()
    inv = scan_chapter(copy.deepcopy(stage))
    targets = {
        t.dedup_key[0]: t
        for t in inv.by_type[ModificationType.TEMPLATE_PARAPHRASE]
        if t.usages[0].concept_key == C3
    }
    res_rw = _rewrite(
        ModificationType.TEMPLATE_PARAPHRASE,
        targets["RESUMEN"].dedup_key,
        {"original": "Prueba tres $D", "new": "Ensayo tres $D"},
        concepts=(C3,),
    )
    tex_rw = _rewrite(
        ModificationType.TEMPLATE_PARAPHRASE,
        targets["TEXTO"].dedup_key,
        {"original": "Prueba tres unitaria $D", "new": "Prueba unitaria tres $D"},
        concepts=(C3,),
    )
    plan = (
        PlannedVariant("all_combined", C3, "CTEST030a", (res_rw, tex_rw)),
    )
    stats, out_dir, report_path = _run(tmp_path, plan)
    row = stats.per_condition["all_combined"]
    assert row["composition_conflicts"] == 0
    assert row["produced"] == 1
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    item = items.iloc[0]
    # both surfaces moved, template-structurally
    assert item["resumen"] == "Ensayo tres PVC"
    assert item["texto"] == "Prueba unitaria tres PVC"
    assert list(item["modification_types"]) == [
        "template_paraphrase", "template_paraphrase",
    ]
    assert item["modification_count"] == 2
    # QA report splits the presence by field
    assert row["type_presence"] == {
        "template_paraphrase (RESUMEN)": 1,
        "template_paraphrase (TEXTO)": 1,
    }
    report = report_path.read_text(encoding="utf-8")
    assert "template_paraphrase (RESUMEN): 1" in report
    assert "template_paraphrase (TEXTO): 1" in report


def test_l1_original_aligned_to_raw_whitespace(tmp_path):
    # Real BC3 value texts carry padding (' 12 '); the scanner/menus store the
    # whitespace-normalised form. The driver must align the L1 payload's
    # `original` back to the raw value or emission finds no match.
    stage = {
        "CTEST040$": {
            "ud": "ud",
            "concept": "prueba cuatro",
            "parameters": {
                "A": {
                    "label": "NUMERO",
                    "values": [
                        {"label": "a", "value": " 2 "},
                        {"label": "b", "value": " 4 "},
                    ],
                },
            },
            "text_variables": {},
            "resumen": "Prueba cuatro $A tubos",
            "texto": "Prueba cuatro con $A tubos",
        },
    }
    rw = _rewrite(
        ModificationType.NUM_TO_TEXT,
        ("NUMERO", "2"),  # scanner-normalised dedup key
        {"original": "2", "new": "dos"},  # menu payload, normalised original
        concepts=("CTEST040$",),
    )
    plan = (
        PlannedVariant("single_num_to_text", "CTEST040$", "CTEST040a", (rw,)),
    )
    stats, out_dir, _ = _run(tmp_path, plan, stage=stage)
    row = stats.per_condition["single_num_to_text"]
    assert row["emission_failed"] == 0
    assert row["produced"] == 1
    items = load_items(out_dir / packaging.ITEMS_FILENAME)
    assert items.iloc[0]["texto"] == "Prueba cuatro con dos tubos"
    assert items.iloc[0]["original_key"] == "CTEST040a"


def test_deterministic_output(tmp_path):
    # serial (workers=1) vs parallel (workers=2) must be byte-identical:
    # the merge/dedup order is sorted, never completion-order dependent.
    plan = (
        PlannedVariant("single_synonym_label", C1, "CTEST010aa", (_syn_diurno(),)),
        PlannedVariant("single_synonym_label", C3, "CTEST030a", (_syn_pvc(),)),
    )

    def _sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    hashes = []
    for name, workers in (("first", 1), ("second", 2)):
        out_dir = tmp_path / name
        run_corpus(
            _tiny_stage(),
            plan,
            out_dir=out_dir,
            report_path=tmp_path / f"{name}.md",
            workers=workers,
        )
        hashes.append(
            (
                _sha(out_dir / packaging.ITEMS_FILENAME),
                _sha(out_dir / packaging.MODIFICATIONS_FILENAME),
            )
        )
    assert hashes[0] == hashes[1]
