"""Contract tests for :mod:`synthetic.menu_review_parser` — the Sprint 38
F3-prep-2-code-B reader that translates ticked Markdown menus back into
structured verdict JSONL.

Fully hermetic. Inline Markdown / JSONL fixtures rather than golden files
— easier to eyeball and keeps the read/write contract co-located with the
test that exercises it.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
from pathlib import Path

import pytest

from synthetic import menu_review_parser
from synthetic.menu_review_parser import (
    CandidateVerdict,
    MenuVerdict,
    ParseError,
    ParseReport,
    format_parse_report,
    parse_all,
    parse_review_file,
    read_verdicts,
    write_verdicts,
)
from synthetic.taxonomy import ModificationType


# ---------------------------------------------------------------------------
# Inline fixture helpers
# ---------------------------------------------------------------------------


def _make_machine_jsonl(records: list[dict]) -> str:
    return "\n".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records
    ) + "\n"


def _syn_record(canonical, dedup_key, candidates_new, usages=None, skipped=None):
    """Build a synonym_label JSONL record like the ones :mod:`menu_artefacts`
    writes."""
    return {
        "modification_type": "synonym_label",
        "dedup_key": list(dedup_key),
        "canonical": canonical,
        "usages": usages or [{"concept_key": "CX$", "display": canonical}],
        "candidates": [
            {"payload": {"original": "X", "new": n}, "approved": None}
            for n in candidates_new
        ],
        "skipped_reason": skipped,
        "dropped_reasons": [],
    }


_SIMPLE_MD = """\
# synonym_label — test

_2 unique target(s) across 1 concept(s). Tick candidates you approve._

## AXIS_A / value_alpha
_Used in 1 concept(s): CX$_

- [x] 1. cand_a1
- [ ] 2. cand_a2
- [x] 3. cand_a3

## AXIS_A / value_beta
_Used in 1 concept(s): CX$_

- [ ] 1. cand_b1
- [X] 2. cand_b2

"""

_SIMPLE_JSONL_RECORDS = [
    _syn_record("AXIS_A / value_alpha", ("AXIS_A", "value_alpha"),
                ["cand_a1", "cand_a2", "cand_a3"]),
    _syn_record("AXIS_A / value_beta", ("AXIS_A", "value_beta"),
                ["cand_b1", "cand_b2"]),
]


# ===========================================================================
# parse_review_file — happy paths
# ===========================================================================


class TestParseReviewFileHappy:
    def _write_pair(self, tmp_path: Path, md_body: str, records: list[dict]):
        md = tmp_path / "synonym_label.md"
        jl = tmp_path / "synonym_label.jsonl"
        md.write_text(md_body, encoding="utf-8")
        jl.write_text(_make_machine_jsonl(records), encoding="utf-8")
        return md, jl

    def test_ticks_map_to_approved_flags(self, tmp_path: Path):
        md, jl = self._write_pair(tmp_path, _SIMPLE_MD, _SIMPLE_JSONL_RECORDS)
        verdicts = parse_review_file(md, jl)
        assert len(verdicts) == 2

        alpha = verdicts[0]
        assert alpha.mtype is ModificationType.SYNONYM_LABEL
        assert alpha.dedup_key == ("AXIS_A", "value_alpha")
        assert alpha.canonical == "AXIS_A / value_alpha"
        assert [c.approved for c in alpha.candidates] == [True, False, True]
        assert alpha.candidates[0].payload["new"] == "cand_a1"

        beta = verdicts[1]
        assert [c.approved for c in beta.candidates] == [False, True]

    def test_case_insensitive_ticks(self, tmp_path: Path):
        """`[X]` (upper) and `[x]` (lower) both approve; empty `[ ]`
        rejects."""
        md, jl = self._write_pair(tmp_path, _SIMPLE_MD, _SIMPLE_JSONL_RECORDS)
        verdicts = parse_review_file(md, jl)
        # beta target uses [X]; must be approved.
        assert verdicts[1].candidates[1].approved is True

    def test_no_ticks_at_all_rejects_all(self, tmp_path: Path):
        """Untouched review file → every candidate rejected. This is the
        Sprint 38 reject-by-default contract."""
        md_body = _SIMPLE_MD.replace("[x]", "[ ]").replace("[X]", "[ ]")
        md, jl = self._write_pair(tmp_path, md_body, _SIMPLE_JSONL_RECORDS)
        verdicts = parse_review_file(md, jl)
        for v in verdicts:
            for c in v.candidates:
                assert c.approved is False

    def test_all_ticks_approves_all(self, tmp_path: Path):
        md_body = _SIMPLE_MD.replace("[ ]", "[x]")
        md, jl = self._write_pair(tmp_path, md_body, _SIMPLE_JSONL_RECORDS)
        verdicts = parse_review_file(md, jl)
        for v in verdicts:
            for c in v.candidates:
                assert c.approved is True

    def test_missing_tick_line_defaults_to_reject(self, tmp_path: Path):
        """If a reviewer deletes a candidate line, the JSONL still has it —
        the parser treats the missing line as reject-by-default."""
        # Delete `- [ ] 2. cand_a2` from the Markdown.
        md_body = _SIMPLE_MD.replace("- [ ] 2. cand_a2\n", "")
        md, jl = self._write_pair(tmp_path, md_body, _SIMPLE_JSONL_RECORDS)
        verdicts = parse_review_file(md, jl)
        alpha = verdicts[0]
        # cand_a2 has no tick line → rejected.
        assert alpha.candidates[1].approved is False
        # cand_a1 + cand_a3 stay as they were.
        assert alpha.candidates[0].approved is True
        assert alpha.candidates[2].approved is True

    def test_skipped_target_preserves_reason(self, tmp_path: Path):
        """A proposer-skipped target has empty candidates + non-null
        ``skipped_reason``; the parser emits an empty CandidateVerdict tuple
        and carries the reason through."""
        records = [
            _syn_record("AXIS_A / value_alpha", ("AXIS_A", "value_alpha"),
                        [], skipped="malformed_list_after_retry: not_json"),
        ]
        md_body = """\
# synonym_label — test

## AXIS_A / value_alpha
_Used in 1 concept(s): CX$_
_Skipped: malformed_list_after_retry: not_json_

"""
        md, jl = self._write_pair(tmp_path, md_body, records)
        verdicts = parse_review_file(md, jl)
        assert len(verdicts) == 1
        assert verdicts[0].candidates == ()
        assert verdicts[0].skipped_reason == "malformed_list_after_retry: not_json"


# ===========================================================================
# parse_review_file — fail-loud paths
# ===========================================================================


class TestParseReviewFileErrors:
    def _write_pair(self, tmp_path: Path, md_body: str, records: list[dict]):
        md = tmp_path / "synonym_label.md"
        jl = tmp_path / "synonym_label.jsonl"
        md.write_text(md_body, encoding="utf-8")
        jl.write_text(_make_machine_jsonl(records), encoding="utf-8")
        return md, jl

    def test_heading_count_mismatch(self, tmp_path: Path):
        """Reviewer deleted a heading → structural mismatch → fail-loud."""
        md_body = "# synonym_label — test\n\n## AXIS_A / value_alpha\n\n- [ ] 1. cand_a1\n\n"
        md, jl = self._write_pair(tmp_path, md_body, _SIMPLE_JSONL_RECORDS)
        with pytest.raises(ParseError, match="heading_count_mismatch"):
            parse_review_file(md, jl)

    def test_canonical_string_drift(self, tmp_path: Path):
        """Reviewer typo'd a heading → fail-loud so the true target is not
        silently overwritten by ticks meant for a different value."""
        md_body = _SIMPLE_MD.replace(
            "## AXIS_A / value_alpha", "## AXIS_A / value_ALPHA"
        )
        md, jl = self._write_pair(tmp_path, md_body, _SIMPLE_JSONL_RECORDS)
        with pytest.raises(ParseError, match="canonical_mismatch"):
            parse_review_file(md, jl)

    def test_tick_index_out_of_range(self, tmp_path: Path):
        """Extra checkbox at index 4 when the JSONL only has 3 candidates
        → fail-loud."""
        md_body = _SIMPLE_MD.replace(
            "- [x] 3. cand_a3",
            "- [x] 3. cand_a3\n- [x] 4. extra_line",
        )
        md, jl = self._write_pair(tmp_path, md_body, _SIMPLE_JSONL_RECORDS)
        with pytest.raises(ParseError, match="tick_index_out_of_range"):
            parse_review_file(md, jl)


# ===========================================================================
# write_verdicts / read_verdicts round-trip
# ===========================================================================


class TestVerdictIO:
    def test_round_trip(self, tmp_path: Path):
        verdicts = (
            MenuVerdict(
                mtype=ModificationType.SYNONYM_LABEL,
                dedup_key=("AXIS_A", "value_alpha"),
                canonical="AXIS_A / value_alpha",
                candidates=(
                    CandidateVerdict(payload={"new": "syn1"}, approved=True),
                    CandidateVerdict(payload={"new": "syn2"}, approved=False),
                ),
                skipped_reason=None,
            ),
            MenuVerdict(
                mtype=ModificationType.SYNONYM_LABEL,
                dedup_key=("AXIS_A", "value_beta"),
                canonical="AXIS_A / value_beta",
                candidates=(),
                skipped_reason="malformed_list_after_retry: none",
            ),
        )
        out = tmp_path / "synonym_label.jsonl"
        write_verdicts(verdicts, out)
        read = read_verdicts(out)
        assert read == verdicts

    def test_write_is_atomic_no_tmp_left_behind(self, tmp_path: Path):
        verdicts = (
            MenuVerdict(
                mtype=ModificationType.SYNONYM_LABEL,
                dedup_key=("A", "B"), canonical="A / B",
                candidates=(CandidateVerdict(payload={"new": "x"}, approved=True),),
                skipped_reason=None,
            ),
        )
        out = tmp_path / "sub" / "synonym_label.jsonl"
        write_verdicts(verdicts, out)
        assert out.exists()
        assert list((tmp_path / "sub").glob("*.tmp")) == []


# ===========================================================================
# parse_all directory sweep
# ===========================================================================


class TestParseAll:
    def _seed_paired_type(
        self, machine_dir: Path, review_dir: Path,
        mtype: ModificationType, md_body: str, records: list[dict],
    ):
        (machine_dir / f"{mtype.value}.jsonl").write_text(
            _make_machine_jsonl(records), encoding="utf-8",
        )
        (review_dir / f"{mtype.value}.md").write_text(md_body, encoding="utf-8")

    def test_writes_verdicts_per_paired_type(self, tmp_path: Path):
        m = tmp_path / "m"
        r = tmp_path / "r"
        out = tmp_path / "v"
        m.mkdir()
        r.mkdir()
        self._seed_paired_type(
            m, r, ModificationType.SYNONYM_LABEL,
            _SIMPLE_MD, _SIMPLE_JSONL_RECORDS,
        )
        report = parse_all(m, r, out)
        assert isinstance(report, ParseReport)
        assert (out / "synonym_label.jsonl").exists()
        verdicts = read_verdicts(out / "synonym_label.jsonl")
        assert len(verdicts) == 2

    def test_missing_review_file_falls_back_to_reject_all(self, tmp_path: Path):
        """Reviewer never opened this rewrite type → parser writes verdicts
        with every candidate rejected. No fabricated approvals."""
        m = tmp_path / "m"
        r = tmp_path / "r"
        out = tmp_path / "v"
        m.mkdir()
        r.mkdir()
        (m / "synonym_label.jsonl").write_text(
            _make_machine_jsonl(_SIMPLE_JSONL_RECORDS), encoding="utf-8",
        )
        report = parse_all(m, r, out)
        verdicts = read_verdicts(out / "synonym_label.jsonl")
        assert len(verdicts) == 2
        for v in verdicts:
            for c in v.candidates:
                assert c.approved is False
        stat = next(row for row in report.per_type
                    if row.mtype is ModificationType.SYNONYM_LABEL)
        assert stat.n_approved_candidates == 0
        assert stat.n_targets_with_any_approval == 0

    def test_missing_machine_file_type_skipped(self, tmp_path: Path):
        """A rewrite type with no machine JSONL is silently skipped —
        it just had zero targets on this chapter."""
        m = tmp_path / "m"
        r = tmp_path / "r"
        out = tmp_path / "v"
        m.mkdir()
        r.mkdir()
        # Only omission has files; every other type is silent.
        (m / "omission.jsonl").write_text("", encoding="utf-8")
        report = parse_all(m, r, out)
        # No SYNONYM_LABEL row in the report.
        types_seen = [row.mtype for row in report.per_type]
        assert ModificationType.SYNONYM_LABEL not in types_seen


# ===========================================================================
# Report formatting
# ===========================================================================


class TestFormatParseReport:
    def test_produces_markdown_table(self):
        report = ParseReport(per_type=(
            menu_review_parser.TypeParseStat(
                mtype=ModificationType.SYNONYM_LABEL,
                n_targets=49,
                n_targets_with_any_approval=45,
                n_total_candidates=470,
                n_approved_candidates=88,
            ),
        ))
        s = format_parse_report(report)
        assert "Menu-review parse — coverage summary" in s
        assert "| synonym_label | 49 | 45 | 470 | 88 |" in s


# ===========================================================================
# Boundary
# ===========================================================================


class TestBoundaries:
    @staticmethod
    def _imports(mod) -> set[str]:
        tree = ast.parse(inspect.getsource(mod))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".")[-1])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.add(node.module.split(".")[-1])
        return names

    def test_no_seam_module_imports_menu_review_parser(self):
        seam_names = [
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
            "synthetic.target_scanner",
            "synthetic.menu_proposer",
            "synthetic.menu_artefacts",
        ]
        for name in seam_names:
            mod = importlib.import_module(name)
            got = self._imports(mod)
            assert "menu_review_parser" not in got, name

    def test_parser_does_not_import_forbidden_seams(self):
        mod = importlib.import_module("synthetic.menu_review_parser")
        got = self._imports(mod)
        forbidden = {
            "stage_b", "run_synthetic", "mutator", "layer_l1", "layer_l2",
            "layer_l3", "layer_pd", "metadata", "packaging", "review",
            "stage_runners", "variant_proposer", "slot_extractor",
            "llm_client", "llm_proposer",
        }
        hits = got & forbidden
        assert not hits, f"menu_review_parser imports forbidden: {hits}"
