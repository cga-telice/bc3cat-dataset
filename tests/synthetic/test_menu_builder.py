"""Contract tests for the Sprint 37 menu-builder trio:
:mod:`synthetic.target_scanner`, :mod:`synthetic.menu_proposer`,
:mod:`synthetic.menu_artefacts`.

Fully hermetic — every LLM interaction goes through the canned
:class:`_StubLLMClient` below. One end-to-end integration test scans the
real OBRA CIVIL stage-2 file (committed to the repo) and asserts the
per-family dedup counts from the sprint-37 preflight measurement
(2026-07-08 scratchpad scan): **673 unique targets across all 13
modification types on the 25 OEB concept groups.**
"""

from __future__ import annotations

import copy
import importlib
import inspect
import json
import re
from pathlib import Path

import pytest

from synthetic import (
    menu_artefacts,
    menu_proposer,
    target_scanner,
)
from synthetic.menu_artefacts import WriteReport, write_menu
from synthetic.menu_proposer import (
    _is_prompt_echo,
    _validate_variants,
    DEFAULT_N_CANDIDATES,
    MENU_CAP_BY_TYPE,
    SIMILARITY_THRESHOLD,
    CandidateProposal,
    CandidateSet,
    _cap_candidates,
    _parse_json_list,
    _repair_invalid_escapes,
    _similarity_gate,
    propose_type,
)
from synthetic.target_scanner import (
    ChapterInventory,
    TargetUsage,
    UniqueTarget,
    scan_chapter,
)
from synthetic.taxonomy import ModificationType


_FIXTURES = Path(__file__).parent / "fixtures" / "menu_builder"
_TINY_PATH = _FIXTURES / "tiny_chapter.json"
_OBRA_CIVIL_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "intermediate"
    / "OBRA CIVIL"
    / "OBRA CIVIL.json"
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _StubLLMClient:
    """Pops queued responses; records each prompt received."""

    def __init__(self, responses: list[str]):
        self._queue = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._queue:
            raise AssertionError(
                f"_StubLLMClient: no more responses (received {len(self.calls)} call(s))"
            )
        return self._queue.pop(0)


def _load_tiny() -> dict:
    return json.loads(_TINY_PATH.read_text(encoding="utf-8"))


def _l1_variant(pairs: list[tuple[str, str]], list_key: str = "synonyms") -> dict:
    return {list_key: [{"original": o, "new": n} for o, n in pairs]}


def _l1_list_response(variants: list[list[tuple[str, str]]], list_key: str = "synonyms") -> str:
    return json.dumps([_l1_variant(v, list_key) for v in variants], ensure_ascii=False)


def _l2_list_response(originals_news: list[tuple[str, str]], *, preserves: bool = True) -> str:
    return json.dumps(
        [
            {"original": o, "new": n, "preserves_meaning": preserves}
            for o, n in originals_news
        ],
        ensure_ascii=False,
    )


# ===========================================================================
# target_scanner tests
# ===========================================================================


class TestScanChapter:
    def test_returns_chapter_inventory_with_sorted_concept_keys(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        assert isinstance(inv, ChapterInventory)
        assert inv.concept_keys == ("CTEST010$", "CTEST020$", "CTEST030$")
        # Every ModificationType is a key of by_type (even if empty).
        for mtype in ModificationType:
            assert mtype in inv.by_type

    def test_concept_filter_narrows_scope(self):
        stage = _load_tiny()
        inv = scan_chapter(stage, concept_filter=lambda k: k.startswith("CTEST01"))
        assert inv.concept_keys == ("CTEST010$",)

    def test_l1_synonym_label_dedup_across_concepts(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        targets = inv.by_type[ModificationType.SYNONYM_LABEL]
        keys = [t.dedup_key for t in targets]
        # TRABAJO / Diurno + Nocturno appear in CTEST010 and CTEST020 (shared).
        # TIPO / Normal + Rocoso only in CTEST010.
        # MATERIAL / PVC + HDPE only in CTEST030.
        # PROFUNDIDAD has numeric-only values → synonym_label gate rejects.
        assert ("TRABAJO", "Diurno") in keys
        assert ("TRABAJO", "Nocturno") in keys
        assert ("TIPO", "Normal") in keys
        assert ("TIPO", "Rocoso") in keys
        assert ("MATERIAL", "PVC") in keys
        assert ("MATERIAL", "HDPE") in keys
        assert not any(k[0] == "PROFUNDIDAD" for k in keys)

    def test_l1_shared_targets_carry_multiple_usages(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        by_key = {
            t.dedup_key: t for t in inv.by_type[ModificationType.SYNONYM_LABEL]
        }
        diurno = by_key[("TRABAJO", "Diurno")]
        assert tuple(u.concept_key for u in diurno.usages) == (
            "CTEST010$",
            "CTEST020$",
        )
        # Concept-only targets have a single usage.
        pvc = by_key[("MATERIAL", "PVC")]
        assert tuple(u.concept_key for u in pvc.usages) == ("CTEST030$",)

    def test_num_to_text_gate_selects_numeric_axes_only(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        targets = inv.by_type[ModificationType.NUM_TO_TEXT]
        keys = [t.dedup_key for t in targets]
        # PROFUNDIDAD (values "1", "2") is the only numeric axis.
        assert keys == [("PROFUNDIDAD", "1"), ("PROFUNDIDAD", "2")]

    def test_abbrev_expansion_selects_uppercase_abbrev_axes(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        targets = inv.by_type[ModificationType.ABBREV_EXPANSION]
        keys = [t.dedup_key for t in targets]
        # MATERIAL / PVC + HDPE — both contain uppercase abbreviations.
        assert ("MATERIAL", "PVC") in keys
        assert ("MATERIAL", "HDPE") in keys

    def test_l2_paraphrase_dedups_by_fragment_text(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        targets = inv.by_type[ModificationType.PARAPHRASE]
        by_key = {t.dedup_key: t for t in targets}
        # Fragments: "normal" (CTEST010 %B=a, CTEST020 %C=a), "rocoso", "medio".
        assert ("normal",) in by_key
        assert ("rocoso",) in by_key
        assert ("medio",) in by_key
        # "normal" appears in two concepts.
        assert len(by_key[("normal",)].usages) == 2
        assert len(by_key[("rocoso",)].usages) == 1

    def test_l3_omission_targets_per_field_and_var(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        targets = inv.by_type[ModificationType.OMISSION]
        # Fields with var tokens: CTEST010 RESUMEN has $A + $K etc.
        # We don't pin the exact count — just that we get a non-zero number
        # and every dedup_key encodes (field, template_norm, var_token).
        assert len(targets) > 0
        for t in targets:
            assert len(t.dedup_key) == 3
            assert t.dedup_key[0] in ("RESUMEN", "TEXTO")
            assert re.match(r"\$[A-Z]", t.dedup_key[2])

    def test_l3_reorder_one_per_field_per_concept_no_dedup(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        targets = inv.by_type[ModificationType.REORDER]
        # 3 concepts × 2 fields (RESUMEN + TEXTO) = 6 targets (templates unique).
        assert len(targets) == 6

    def test_l3_template_paraphrase_matches_reorder_shape(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        tps = inv.by_type[ModificationType.TEMPLATE_PARAPHRASE]
        assert len(tps) == 6

    def test_new_param_one_per_concept_no_dedup(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        nps = inv.by_type[ModificationType.NEW_PARAM]
        assert tuple(t.dedup_key for t in nps) == (
            ("CTEST010$",), ("CTEST020$",), ("CTEST030$",),
        )

    def test_scan_is_deterministic(self):
        stage = _load_tiny()
        a = scan_chapter(stage)
        b = scan_chapter(stage)
        # Same concept keys, same per-type target order, same usages tuple.
        assert a.concept_keys == b.concept_keys
        for mtype in ModificationType:
            assert a.by_type[mtype] == b.by_type[mtype]

    def test_dataclasses_are_frozen(self):
        with pytest.raises(Exception):
            TargetUsage("k", None, "d").concept_key = "x"  # type: ignore
        u = TargetUsage("k", None, "d")
        t = UniqueTarget(("a",), "c", (u,))
        with pytest.raises(Exception):
            t.canonical = "x"  # type: ignore


# ===========================================================================
# menu_proposer tests
# ===========================================================================


class TestProposeType:
    def _tiny_inventory(self) -> tuple[dict, ChapterInventory]:
        stage = _load_tiny()
        return stage, scan_chapter(stage)

    def test_default_n_is_ten(self):
        assert DEFAULT_N_CANDIDATES == 10

    def test_l1_batched_one_call_per_axis(self):
        """SYNONYM_LABEL on tiny fixture: 3 distinct axes drive 3 calls
        even though there are 6 unique per-value targets."""
        stage, inv = self._tiny_inventory()
        # Batches are enumerated alphabetically by axis label:
        # MATERIAL (CTEST030) → TIPO (CTEST010) → TRABAJO (CTEST010).
        material_response = _l1_list_response(
            [
                [("PVC", "Cloruro de polivinilo"), ("HDPE", "Polietileno de alta densidad")],
            ],
        )
        tipo_response = _l1_list_response(
            [
                [("Normal", "Estándar"), ("Rocoso", "Con roca")],
                [("Normal", "Común"), ("Rocoso", "Rocalloso")],
            ],
        )
        trabajo_response = _l1_list_response(
            [
                [("Diurno", "Turno diurno"), ("Nocturno", "Turno nocturno")],
                [("Diurno", "En horario diurno"), ("Nocturno", "En horario nocturno")],
            ],
        )
        client = _StubLLMClient([material_response, tipo_response, trabajo_response])
        result = propose_type(
            stage, inv, ModificationType.SYNONYM_LABEL, client, n=2,
        )
        # 3 LLM calls, 6 CandidateSets.
        assert len(client.calls) == 3
        assert len(result) == 6
        # Diurno's set has 2 candidates.
        diurno = result[("TRABAJO", "Diurno")]
        assert isinstance(diurno, CandidateSet)
        assert diurno.reason is None
        assert tuple(c.payload["new"] for c in diurno.candidates) == (
            "Turno diurno", "En horario diurno",
        )
        # PVC's set (single-variant response) has 1 candidate.
        pvc = result[("MATERIAL", "PVC")]
        assert tuple(c.payload["new"] for c in pvc.candidates) == (
            "Cloruro de polivinilo",
        )

    def test_l1_inter_candidate_dedup(self):
        stage, inv = self._tiny_inventory()
        # Filter to one axis (TRABAJO) via a stub of inventory.
        trabajo_targets = tuple(
            t for t in inv.by_type[ModificationType.SYNONYM_LABEL]
            if t.dedup_key[0] == "TRABAJO"
        )
        assert len(trabajo_targets) == 2
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.SYNONYM_LABEL: trabajo_targets, **{
                m: () for m in ModificationType if m is not ModificationType.SYNONYM_LABEL
            }},
        )
        # Response: Diurno gets three variants — but the last is a near-duplicate.
        response = _l1_list_response([
            [("Diurno", "Turno diurno"), ("Nocturno", "Turno nocturno")],
            [("Diurno", "Turno de día"), ("Nocturno", "Turno de noche")],
            [("Diurno", "TURNO DIURNO"),  # casefold-matches variant 1
             ("Nocturno", "Nocturnidad")],
        ])
        client = _StubLLMClient([response])
        result = propose_type(
            stage, fake_inv, ModificationType.SYNONYM_LABEL, client, n=3,
        )
        diurno = result[("TRABAJO", "Diurno")]
        # Only two survive — "Turno diurno" and "Turno de día"; the third
        # was a case-insensitive duplicate of the first.
        assert tuple(c.payload["new"] for c in diurno.candidates) == (
            "Turno diurno", "Turno de día",
        )

    def test_l2_one_call_per_fragment(self):
        stage, inv = self._tiny_inventory()
        para_targets = inv.by_type[ModificationType.PARAPHRASE]
        assert len(para_targets) == 3  # medio, normal, rocoso (alphabetical dedup_key)
        # Targets are enumerated in dedup_key order: medio → normal → rocoso.
        r_medio = _l2_list_response([("medio", "intermedio")])
        r_normal = _l2_list_response([("normal", "estándar"), ("normal", "corriente")])
        r_rocoso = _l2_list_response([("rocoso", "pedregoso")])
        client = _StubLLMClient([r_medio, r_normal, r_rocoso])
        result = propose_type(
            stage, inv, ModificationType.PARAPHRASE, client, n=2,
        )
        assert len(client.calls) == 3
        assert len(result) == 3
        assert tuple(c.payload["new"] for c in result[("normal",)].candidates) == (
            "estándar", "corriente",
        )

    def test_partial_schema_fail_drops_only_offender(self):
        stage, inv = self._tiny_inventory()
        # One paraphrase target. Response mixes valid and invalid elements.
        para_targets = inv.by_type[ModificationType.PARAPHRASE]
        normal_target = next(t for t in para_targets if t.dedup_key == ("normal",))
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.PARAPHRASE: (normal_target,), **{
                m: () for m in ModificationType if m is not ModificationType.PARAPHRASE
            }},
        )
        response = json.dumps([
            {"original": "normal", "new": "estándar", "preserves_meaning": True},
            {"original": "normal", "new": "corriente"},  # missing preserves_meaning
            {"original": "normal", "new": "regular", "preserves_meaning": True},
        ], ensure_ascii=False)
        client = _StubLLMClient([response])
        result = propose_type(
            stage, fake_inv, ModificationType.PARAPHRASE, client, n=3,
        )
        set_ = result[("normal",)]
        assert tuple(c.payload["new"] for c in set_.candidates) == (
            "estándar", "regular",
        )
        assert len(set_.dropped_reasons) == 1
        assert "preserves_meaning" in set_.dropped_reasons[0]

    def test_malformed_list_after_retry_marks_target_skipped(self):
        stage, inv = self._tiny_inventory()
        para_targets = inv.by_type[ModificationType.PARAPHRASE]
        normal_target = next(t for t in para_targets if t.dedup_key == ("normal",))
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.PARAPHRASE: (normal_target,), **{
                m: () for m in ModificationType if m is not ModificationType.PARAPHRASE
            }},
        )
        # Two malformed responses → whole-target skip.
        client = _StubLLMClient(["not json at all", "also not json"])
        result = propose_type(
            stage, fake_inv, ModificationType.PARAPHRASE, client, n=3,
        )
        set_ = result[("normal",)]
        assert set_.candidates == ()
        assert set_.reason is not None
        assert set_.reason.startswith("malformed_list_after_retry:")

    def test_empty_list_after_all_dropped_skips_target(self):
        stage, inv = self._tiny_inventory()
        para_targets = inv.by_type[ModificationType.PARAPHRASE]
        normal_target = next(t for t in para_targets if t.dedup_key == ("normal",))
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.PARAPHRASE: (normal_target,), **{
                m: () for m in ModificationType if m is not ModificationType.PARAPHRASE
            }},
        )
        # Both attempts return a valid list of all-invalid elements.
        r = json.dumps([{"original": "x"}, {"new": "y"}], ensure_ascii=False)
        client = _StubLLMClient([r, r])
        result = propose_type(
            stage, fake_inv, ModificationType.PARAPHRASE, client, n=2,
        )
        set_ = result[("normal",)]
        assert set_.candidates == ()
        assert set_.reason is not None
        assert set_.reason.startswith("malformed_list_after_retry:")

    def test_multi_candidate_instruction_appears_in_prompt(self):
        """The runtime f-string is what makes phi4 emit a list. Pin the
        exact instruction text so a silent regression fails loud."""
        stage, inv = self._tiny_inventory()
        para_targets = inv.by_type[ModificationType.PARAPHRASE]
        normal_target = next(t for t in para_targets if t.dedup_key == ("normal",))
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.PARAPHRASE: (normal_target,), **{
                m: () for m in ModificationType if m is not ModificationType.PARAPHRASE
            }},
        )
        client = _StubLLMClient([_l2_list_response([("normal", "estándar")])])
        propose_type(stage, fake_inv, ModificationType.PARAPHRASE, client, n=7)
        prompt = client.calls[0]
        assert "devuelve una lista JSON de 7" in prompt
        assert "No repitas alternativas" in prompt

    def test_empty_inventory_returns_empty_dict(self):
        stage = _load_tiny()
        inv = ChapterInventory(
            concept_keys=(),
            by_type={m: () for m in ModificationType},
        )
        client = _StubLLMClient([])
        result = propose_type(stage, inv, ModificationType.SYNONYM_LABEL, client)
        assert result == {}

    def test_json_fence_wrapped_response_recovered(self):
        stage, inv = self._tiny_inventory()
        para_targets = inv.by_type[ModificationType.PARAPHRASE]
        normal_target = next(t for t in para_targets if t.dedup_key == ("normal",))
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.PARAPHRASE: (normal_target,), **{
                m: () for m in ModificationType if m is not ModificationType.PARAPHRASE
            }},
        )
        fenced = (
            "Aquí tienes:\n```json\n"
            + _l2_list_response([("normal", "estándar")])
            + "\n```\nGracias."
        )
        client = _StubLLMClient([fenced])
        result = propose_type(
            stage, fake_inv, ModificationType.PARAPHRASE, client, n=1,
        )
        assert tuple(c.payload["new"] for c in result[("normal",)].candidates) == (
            "estándar",
        )


# ===========================================================================
# menu_artefacts tests
# ===========================================================================


class TestWriteMenu:
    def _one_l1_run(self, tmp_path: Path) -> tuple[Path, Path, tuple[WriteReport, ...]]:
        stage = _load_tiny()
        inv = scan_chapter(stage)
        # Batches enumerated alphabetically: MATERIAL → TIPO → TRABAJO.
        material_response = _l1_list_response([
            [("PVC", "Cloruro de polivinilo"), ("HDPE", "Polietileno de alta densidad")],
        ])
        tipo_response = _l1_list_response([
            [("Normal", "Estándar"), ("Rocoso", "Con roca")],
        ])
        trabajo_response = _l1_list_response([
            [("Diurno", "Turno diurno"), ("Nocturno", "Turno nocturno")],
        ])
        client = _StubLLMClient([material_response, tipo_response, trabajo_response])
        sets = propose_type(stage, inv, ModificationType.SYNONYM_LABEL, client, n=1)
        machine_dir = tmp_path / "machine"
        review_dir = tmp_path / "review"
        reports = write_menu(
            inv,
            {ModificationType.SYNONYM_LABEL: sets},
            machine_dir=machine_dir,
            review_dir=review_dir,
            chapter_label="tiny fixture",
        )
        return machine_dir, review_dir, reports

    def test_creates_both_files_per_type(self, tmp_path: Path):
        machine_dir, review_dir, reports = self._one_l1_run(tmp_path)
        assert (machine_dir / "synonym_label.jsonl").exists()
        assert (review_dir / "synonym_label.md").exists()
        assert len(reports) == 1
        r = reports[0]
        assert r.mtype is ModificationType.SYNONYM_LABEL
        assert r.n_targets == 6

    def test_jsonl_line_per_target_ordered_by_dedup_key(self, tmp_path: Path):
        machine_dir, _, _ = self._one_l1_run(tmp_path)
        lines = (machine_dir / "synonym_label.jsonl").read_text(
            encoding="utf-8"
        ).splitlines()
        keys = [tuple(json.loads(line)["dedup_key"]) for line in lines]
        assert keys == sorted(keys)
        assert keys[0] == ["MATERIAL", "HDPE"] or keys[0] == ("MATERIAL", "HDPE")

    def test_jsonl_candidate_shape_has_approved_null(self, tmp_path: Path):
        machine_dir, _, _ = self._one_l1_run(tmp_path)
        for line in (machine_dir / "synonym_label.jsonl").read_text(
            encoding="utf-8"
        ).splitlines():
            record = json.loads(line)
            for cand in record["candidates"]:
                assert "payload" in cand
                assert "new" in cand["payload"]
                assert cand["approved"] is None

    def test_markdown_uses_checkbox_format(self, tmp_path: Path):
        _, review_dir, _ = self._one_l1_run(tmp_path)
        md = (review_dir / "synonym_label.md").read_text(encoding="utf-8")
        # Header
        assert md.startswith("# synonym_label — tiny fixture")
        # At least one checkbox
        assert re.search(r"^- \[ \] 1\. ", md, re.MULTILINE)
        # One heading per target (6)
        assert md.count("\n## ") == 6

    def test_markdown_shows_multiple_usages(self, tmp_path: Path):
        _, review_dir, _ = self._one_l1_run(tmp_path)
        md = (review_dir / "synonym_label.md").read_text(encoding="utf-8")
        # Diurno is used in 2 concepts.
        assert re.search(
            r"^## TRABAJO / Diurno\n_Used in 2 concept\(s\): CTEST010\$, CTEST020\$_",
            md,
            re.MULTILINE,
        )

    def test_deterministic_write(self, tmp_path: Path):
        m1, r1, _ = self._one_l1_run(tmp_path / "first")
        m2, r2, _ = self._one_l1_run(tmp_path / "second")
        assert (m1 / "synonym_label.jsonl").read_bytes() == (
            m2 / "synonym_label.jsonl"
        ).read_bytes()
        assert (r1 / "synonym_label.md").read_bytes() == (
            r2 / "synonym_label.md"
        ).read_bytes()

    def test_atomic_write_no_tmp_left_behind(self, tmp_path: Path):
        machine_dir, review_dir, _ = self._one_l1_run(tmp_path)
        # No .tmp files remain after successful write.
        assert list(machine_dir.glob("*.tmp")) == []
        assert list(review_dir.glob("*.tmp")) == []

    def test_skipped_target_shown_in_markdown(self, tmp_path: Path):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        # For SYNONYM_LABEL, feed malformed for all three axis calls.
        client = _StubLLMClient(["not json", "still not json"] * 3)
        sets = propose_type(stage, inv, ModificationType.SYNONYM_LABEL, client, n=2)
        write_menu(
            inv,
            {ModificationType.SYNONYM_LABEL: sets},
            machine_dir=tmp_path / "m",
            review_dir=tmp_path / "r",
        )
        md = (tmp_path / "r" / "synonym_label.md").read_text(encoding="utf-8")
        assert "_Skipped: malformed_list_after_retry:" in md

    def test_write_report_counts(self, tmp_path: Path):
        _, _, reports = self._one_l1_run(tmp_path)
        r = reports[0]
        # 6 targets × 1 candidate each (n=1 in the fixture).
        assert r.n_candidates_total == 6
        assert r.n_skipped_targets == 0


# ===========================================================================
# Boundary / no-reverse-import tests
# ===========================================================================


class TestBoundaries:
    def _seam_modules(self):
        # Reload from freshly-resolved import strings so this test doesn't
        # accidentally pin unrelated import graphs.
        names = [
            "synthetic.variant_proposer",
            "synthetic.run_synthetic",
            "synthetic.slot_extractor",
            "synthetic.layer_l1",
            "synthetic.layer_l2",
            "synthetic.layer_l3",
            "synthetic.layer_pd",
            "synthetic.mutator",
            "synthetic.stage_b",
            "synthetic.stage_runners",
            "synthetic.metadata",
            "synthetic.review",
            "synthetic.packaging",
            "synthetic.loaders",
            "synthetic.l2_repr",
            "synthetic.llm_client",
            "synthetic.f1_pilot",
            "synthetic.spike",
        ]
        return [importlib.import_module(n) for n in names]

    @staticmethod
    def _imports(mod) -> set[str]:
        """Extract every import target name from ``mod``'s source via AST."""
        import ast
        tree = ast.parse(inspect.getsource(mod))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[-1])
            elif isinstance(node, ast.ImportFrom):
                # from .foo import Bar → capture "foo"; from synthetic.foo … same.
                if node.module:
                    names.add(node.module.split(".")[-1])
        return names

    def test_no_seam_module_imports_menu_builder(self):
        forbidden_here = {"menu_proposer", "menu_artefacts", "target_scanner"}
        for mod in self._seam_modules():
            got = self._imports(mod)
            hits = got & forbidden_here
            assert not hits, f"{mod.__name__} imports {hits}"

    def test_menu_modules_do_not_import_forbidden_seams(self):
        # menu_proposer + target_scanner may import slot_extractor + taxonomy;
        # they may NOT import stage_b / run_synthetic / mutator / layers /
        # metadata / packaging / review / stage_runners.
        forbidden = {
            "stage_b", "run_synthetic", "mutator", "layer_l1", "layer_l2",
            "layer_l3", "layer_pd", "metadata", "packaging", "review",
            "stage_runners",
        }
        for name in ("target_scanner", "menu_proposer", "menu_artefacts"):
            mod = importlib.import_module(f"synthetic.{name}")
            got = self._imports(mod)
            hits = got & forbidden
            assert not hits, f"{name} imports forbidden: {hits}"


# ===========================================================================
# Integration test — real OBRA CIVIL stage-2 file
# ===========================================================================


@pytest.mark.skipif(
    not _OBRA_CIVIL_PATH.exists(),
    reason=f"OBRA CIVIL stage-2 file not available at {_OBRA_CIVIL_PATH}",
)
class TestObraCivilDedup:
    """Reproduces the sprint-37 preflight measurement (2026-07-08 scratchpad
    scan). Numbers below are the empirically observed counts on the 25
    OEB concept groups. If the measurement drifts, one of two things
    happened: the source stage-2 JSON changed, or the target scanner's
    enumeration semantics changed. Either is worth a hard fail here.
    """

    @pytest.fixture(scope="class")
    def inventory(self):
        stage = json.loads(_OBRA_CIVIL_PATH.read_text(encoding="utf-8"))
        return scan_chapter(stage, concept_filter=lambda k: k.startswith("OEB"))

    def test_25_oeb_concepts(self, inventory):
        assert len(inventory.concept_keys) == 25

    def test_synonym_label_unique_target_count(self, inventory):
        targets = inventory.by_type[ModificationType.SYNONYM_LABEL]
        # 49 unique (axis_label, value) pairs across the 25 OEB groups,
        # after Sprint 34's applicability gate. All-numeric axes (Nº TUBOS)
        # are gated out for synonym_label; only axes with ≥1 letter-bearing
        # value survive. Preflight scan (2026-07-08) reported 67 which was
        # the pre-gate upper bound.
        # Sprint 38.5: 49 → 34 — 15 digit-bearing values gated out.
        assert len(targets) == 34

    def test_paraphrase_unique_target_count(self, inventory):
        targets = inventory.by_type[ModificationType.PARAPHRASE]
        # 46 unique L2 fragment strings (per fragment_text_normalised dedup)
        # after l2_repr.list_to_formula(include_conditional=True) makes all
        # three text-variable shapes (LIST_plain / STR_formula /
        # LIST_conditional) enumerable — matches the Sprint 26 pipeline
        # discipline used by f1_pilot.
        assert len(targets) == 46

    def test_new_param_target_count_matches_concepts(self, inventory):
        targets = inventory.by_type[ModificationType.NEW_PARAM]
        assert len(targets) == 25

    def test_workhorse_axes_share_across_many_concepts(self, inventory):
        """The insight motivating the whole dedup-first design: axes like
        TRABAJO and BANDA DE MANTENIMIENTO repeat in most OEB concepts."""
        by_key = {
            t.dedup_key: t
            for t in inventory.by_type[ModificationType.SYNONYM_LABEL]
        }
        diurno = by_key.get(("TRABAJO", "Diurno"))
        assert diurno is not None
        # Preflight scan: 20 of 25 OEB concepts use TRABAJO / Diurno.
        assert len(diurno.usages) == 20


# ===========================================================================
# Sprint 38.5 — parser repair for the FIEBDC backslash echo
# ===========================================================================


class TestParseJsonListRepair:
    def test_repairs_fiebdc_backslash_echo(self):
        # Raw \TEXTO\ templates start with "\"; phi4 echoes it inside the JSON
        # string, which is an invalid escape. Recover by dropping the backslash.
        text = (
            '[{"original": "\\Canalización de $A tubos", '
            '"new": "Canalización de $A tubos", "omitted_var": "A"}]'
        )
        assert _parse_json_list(text) == [
            {
                "original": "Canalización de $A tubos",
                "new": "Canalización de $A tubos",
                "omitted_var": "A",
            }
        ]

    def test_leaves_valid_escapes_alone(self):
        text = '[{"original": "a\\"b", "new": "línea\\nnueva"}]'
        assert _parse_json_list(text) == [{"original": 'a"b', "new": "línea\nnueva"}]

    def test_still_rejects_unrecoverable_json(self):
        with pytest.raises(ValueError, match="malformed_json"):
            _parse_json_list('[{"original": "x", "new": ]')

    def test_repair_helper_drops_only_invalid_escapes(self):
        assert _repair_invalid_escapes(r'\C \S \" \\ \n \/ end\\') == r'C S \" \\ \n \/ end\\'


# ===========================================================================
# Sprint 38.5 — per-type menu cap
# ===========================================================================


class TestMenuCap:
    def test_cap_table_covers_low_entropy_types_only(self):
        assert MENU_CAP_BY_TYPE == {
            ModificationType.OMISSION: 3,
            ModificationType.REORDER: 3,
            ModificationType.NUM_TO_TEXT: 3,
            ModificationType.UNIT_CONVERSION: 3,
            ModificationType.UNIT_EXPANSION: 3,
        }

    def test_cap_candidates_truncates_only_capped_types(self):
        cands = tuple(CandidateProposal(payload={"new": str(i)}) for i in range(5))
        assert len(_cap_candidates(cands, ModificationType.OMISSION)) == 3
        assert _cap_candidates(cands, ModificationType.PARAPHRASE) == cands
        # Keeps the head — candidates are ordered best→worst by the prompt.
        assert [c.payload["new"] for c in _cap_candidates(cands, ModificationType.REORDER)] == ["0", "1", "2"]

    def test_propose_type_l1_applies_cap(self):
        # tiny_chapter.json: CTEST020$ axis C "PROFUNDIDAD" values 1, 2 → NUM_TO_TEXT.
        stage = _load_tiny()
        inv = scan_chapter(stage)
        five = [[("1", w)] for w in ("uno", "un", "una unidad", "un tubo", "uno solo")]
        client = _StubLLMClient([_l1_list_response(five, list_key="numerals")])
        sets = propose_type(stage, inv, ModificationType.NUM_TO_TEXT, client, n=5)
        assert len(sets[("PROFUNDIDAD", "1")].candidates) == 3
        assert [c.payload["new"] for c in sets[("PROFUNDIDAD", "1")].candidates] == ["uno", "un", "una unidad"]


class TestScannerValueGate:
    def test_synonym_label_skips_digit_values_per_value(self):
        # An axis mixing a clean label with a digit-bearing one: only the
        # clean one becomes a review target.
        stage = _load_tiny()
        stage["CTEST010$"]["parameters"]["B"]["values"].append(
            {"label": "c", "value": "Rocoso 2 m"},
        )
        inv = scan_chapter(stage)
        keys = {t.dedup_key for t in inv.by_type[ModificationType.SYNONYM_LABEL]}
        assert ("TIPO", "Rocoso") in keys
        assert ("TIPO", "Rocoso 2 m") not in keys


# ===========================================================================
# Sprint 38.5 (addendum) — prompt-scaffold echo guard
# ===========================================================================


class TestPromptEchoGuard:
    def test_is_prompt_echo_detects_scaffold_markers(self):
        echo = {
            "original": "x",
            "new": 'Instalación ... Campo destino: TEXTO Plantilla actual: "...',
        }
        clean = {"original": "x", "new": "Instalación de conducción enterrada $A"}
        assert _is_prompt_echo(echo) is True
        assert _is_prompt_echo(clean) is False

    def test_validate_variants_drops_echo_with_reason(self):
        raw = [
            {"original": "t $A", "new": "u $A", "preserves_meaning": True},
            {
                "original": "t $A",
                "new": 'v $A Campo destino: TEXTO Plantilla actual: "t $A"',
                "preserves_meaning": True,
            },
        ]
        variants, dropped = _validate_variants(
            raw, ModificationType.TEMPLATE_PARAPHRASE,
        )
        assert len(variants) == 1 and variants[0]["new"] == "u $A"
        assert dropped == ("[1] prompt_scaffold_echo",)


# ===========================================================================
# Sprint 38.6 — near-duplicate similarity gate
# ===========================================================================


class TestSimilarityGate:
    def test_near_duplicate_dropped_with_reason(self):
        cands = (
            CandidateProposal(payload={"new": "canalización hormigonada de tubos de PVC en zanja"}),
            CandidateProposal(payload={"new": "canalización hormigonada de tubos de PVC en la zanja"}),  # 7/8 shared
            CandidateProposal(payload={"new": "conducción embebida en hormigón para conductos plásticos"}),
        )
        kept, reasons = _similarity_gate(cands, ModificationType.TEMPLATE_PARAPHRASE)
        assert [c.payload["new"] for c in kept] == [cands[0].payload["new"], cands[2].payload["new"]]
        assert reasons == ("[1] near_duplicate_of_kept",)

    def test_threshold_is_08_and_short_strings_survive(self):
        assert SIMILARITY_THRESHOLD == 0.8
        # 1/3 Jaccard — distinct L1-style short candidates stay
        cands = (
            CandidateProposal(payload={"new": "con reposición"}),
            CandidateProposal(payload={"new": "con reemplazo"}),
        )
        kept, reasons = _similarity_gate(cands, ModificationType.TEMPLATE_PARAPHRASE)
        assert len(kept) == 2 and reasons == ()

    def test_reorder_exempt_pure_permutations_kept(self):
        cands = (
            CandidateProposal(payload={"new": "$K. Canalización hormigonada $A T"}),
            CandidateProposal(payload={"new": "Canalización hormigonada $A T $K."}),
        )
        kept, reasons = _similarity_gate(cands, ModificationType.REORDER)
        assert len(kept) == 2 and reasons == ()

    def test_new_param_gate_text_includes_values(self):
        a = CandidateProposal(payload={"new_axis_label": "TIPO", "values": [{"value": "Horizontal"}, {"value": "Vertical"}]})
        b = CandidateProposal(payload={"new_axis_label": "TIPO", "values": [{"value": "Fija"}, {"value": "Móvil"}]})
        kept, reasons = _similarity_gate((a, b), ModificationType.NEW_PARAM)
        assert len(kept) == 2 and reasons == ()

    def test_propose_single_target_applies_gate(self):
        stage = _load_tiny()
        inv = scan_chapter(stage)
        # CTEST010$ RESUMEN "Prueba uno $A $K" -> a template_paraphrase target.
        # The tiny fixture has 6 TEMPLATE_PARAPHRASE targets (RESUMEN/TEXTO x
        # 3 concepts); isolate this one so a single stub response suffices
        # (same fake_inv pattern used elsewhere in this file).
        all_targets = inv.by_type[ModificationType.TEMPLATE_PARAPHRASE]
        rst_target = next(
            t for t in all_targets
            if t.usages[0].concept_key == "CTEST010$" and t.dedup_key[0] == "RESUMEN"
        )
        fake_inv = ChapterInventory(
            concept_keys=inv.concept_keys,
            by_type={ModificationType.TEMPLATE_PARAPHRASE: (rst_target,), **{
                m: () for m in ModificationType if m is not ModificationType.TEMPLATE_PARAPHRASE
            }},
        )
        resp = _l2_list_response([
            ("Prueba uno $A $K", "Ensayo uno $A $K"),
            ("Prueba uno $A $K", "Ensayo  uno $A $K"),   # normalises to dup (exact dedup)
            ("Prueba uno $A $K", "Ensayo uno $A $K bis"),  # Jaccard 4/5 = 0.8 > threshold? no: 0.8 is not > 0.8 — keep
            ("Prueba uno $A $K", "Primera comprobación $A $K"),
        ])
        client = _StubLLMClient([resp])
        sets = propose_type(stage, fake_inv, ModificationType.TEMPLATE_PARAPHRASE, client, n=4)
        target = next(s for s in sets.values()
                      if s.target.usages[0].concept_key == "CTEST010$"
                      and s.target.dedup_key[0] == "RESUMEN")
        news = [c.payload["new"] for c in target.candidates]
        assert "Ensayo uno $A $K" in news and "Primera comprobación $A $K" in news
