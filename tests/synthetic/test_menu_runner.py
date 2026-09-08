"""Contract tests for :mod:`synthetic.menu_runner` — the Sprint 38
F3-prep-2-generate driver.

Fully hermetic. Every LLM interaction goes through the canned
:class:`_StubLLMClient`. No live network, no phi4.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import re
from pathlib import Path

import pytest

from synthetic import menu_proposer, menu_runner
from synthetic.menu_runner import (
    MenuRun,
    ResumingRecordingClient,
    TypeStat,
    format_scorecard,
    run_menu,
)
from synthetic.llm_client import prompt_hash
from synthetic.taxonomy import ModificationType


_FIXTURES = Path(__file__).parent / "fixtures" / "menu_builder"
_TINY_PATH = _FIXTURES / "tiny_chapter.json"


class _StubLLMClient:
    def __init__(self, responses):
        self._queue = list(responses)
        self.calls: list[str] = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        if not self._queue:
            raise AssertionError(
                f"_StubLLMClient: no more queued responses "
                f"(received {len(self.calls)} call(s))"
            )
        return self._queue.pop(0)


def _load_tiny() -> dict:
    return json.loads(_TINY_PATH.read_text(encoding="utf-8"))


def _l1_response(pairs_list, list_key="synonyms"):
    return json.dumps(
        [{list_key: [{"original": o, "new": n} for o, n in pairs]}
         for pairs in pairs_list],
        ensure_ascii=False,
    )


def _l2_response(originals_news):
    return json.dumps(
        [{"original": o, "new": n, "preserves_meaning": True}
         for o, n in originals_news],
        ensure_ascii=False,
    )


def _l3_omission_response(originals_new_omit):
    return json.dumps(
        [{"original": o, "new": n, "omitted_var": v}
         for o, n, v in originals_new_omit],
        ensure_ascii=False,
    )


def _l3_reorder_response(originals_news):
    return json.dumps(
        [{"original": o, "new": n, "preserves_meaning": True}
         for o, n in originals_news],
        ensure_ascii=False,
    )


def _l3_template_paraphrase_response(originals_news):
    return json.dumps(
        [{"original": o, "new": n, "preserves_meaning": True}
         for o, n in originals_news],
        ensure_ascii=False,
    )


def _new_param_response(entries):
    return json.dumps(entries, ensure_ascii=False)


class _FixedClock:
    """Deterministic monotonic clock for wall-clock assertions."""

    def __init__(self, ticks):
        self._ticks = iter(ticks)

    def __call__(self):
        return next(self._ticks)


# ===========================================================================
# run_menu tests
# ===========================================================================


class TestRunMenu:
    def test_runs_end_to_end_over_tiny_fixture(self, tmp_path: Path):
        """A single SYNONYM_LABEL + PARAPHRASE pass writes both artefacts
        and returns a scorecard whose counts tally with the fixture."""
        stage = _load_tiny()
        # Prepare canned responses for every mtype (empty responses for the ones
        # with no targets on the fixture).
        # Order matters — the driver iterates ModificationType in enum order,
        # so we set up per-type queues below.
        responses = self._canned_responses_for_full_run()
        client = _StubLLMClient(responses)
        run = run_menu(
            stage,
            concept_filter=None,
            n=2,
            client=client,
            chapter_label="tiny",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
            clock=_FixedClock([100.0, 101.5]),
        )
        assert isinstance(run, MenuRun)
        assert run.chapter_label == "tiny"
        assert run.concept_count == 3
        assert run.wall_clock_s == pytest.approx(1.5)
        assert run.n_unique_targets_total > 0
        assert run.n_llm_calls_total == len(client.calls)
        # Each per-type TypeStat is non-negative and internally consistent.
        for row in run.per_type:
            assert isinstance(row, TypeStat)
            assert row.n_targets >= 0
            assert row.n_generated_targets + row.n_skipped_targets <= row.n_targets
            assert row.n_total_candidates >= row.n_generated_targets

    def test_writes_both_artefacts_per_populated_type(self, tmp_path: Path):
        stage = _load_tiny()
        client = _StubLLMClient(self._canned_responses_for_full_run())
        run_menu(
            stage,
            concept_filter=None,
            n=2,
            client=client,
            chapter_label="tiny",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
        )
        # synonym_label + paraphrase (and other populated types) exist.
        assert (tmp_path / "m" / "synonym_label.jsonl").exists()
        assert (tmp_path / "r" / "synonym_label.md").exists()
        assert (tmp_path / "m" / "paraphrase.jsonl").exists()
        assert (tmp_path / "r" / "paraphrase.md").exists()
        # abbrev/code_expansion typically empty on tiny — no file written.
        # (Sprint 37 write_menu emits only for types with sets.)

    def test_typestat_counts_generated_vs_skipped(self, tmp_path: Path):
        """A queued malformed response for SYNONYM_LABEL's MATERIAL batch
        results in 2 skipped targets (PVC + HDPE) even though other axes
        succeed."""
        stage = _load_tiny()
        # Mix: MATERIAL malformed × 2 (retry then giveup) → 2 skipped;
        # TIPO OK → 2 targets generated; TRABAJO OK → 2 generated.
        responses = [
            # SYNONYM_LABEL — 3 axes alphabetical: MATERIAL, TIPO, TRABAJO
            "definitely not json",
            "still not json",
            _l1_response([[("Normal", "estándar"), ("Rocoso", "con roca")]]),
            _l1_response([[("Diurno", "turno diurno"), ("Nocturno", "turno nocturno")]]),
        ]
        # Fill remaining types with malformed so they cleanly skip.
        # First figure out how many more calls we'll make. Simpler: use a
        # generous supply of "malformed" for every other type.
        responses += ["not json"] * 200
        client = _StubLLMClient(responses)
        run = run_menu(
            stage,
            concept_filter=None,
            n=1,
            client=client,
            chapter_label="tiny",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
        )
        syn = next(row for row in run.per_type
                   if row.mtype is ModificationType.SYNONYM_LABEL)
        # 6 unique targets on tiny; MATERIAL/PVC + MATERIAL/HDPE skipped;
        # TIPO/Normal + TIPO/Rocoso + TRABAJO/Diurno + TRABAJO/Nocturno generated.
        assert syn.n_targets == 6
        assert syn.n_generated_targets == 4
        assert syn.n_skipped_targets == 2

    def test_records_llm_calls_per_type(self, tmp_path: Path):
        stage = _load_tiny()
        # Enough malformed responses to skip everything cleanly.
        client = _StubLLMClient(["not json"] * 500)
        run = run_menu(
            stage,
            concept_filter=None,
            n=1,
            client=client,
            chapter_label="tiny",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
        )
        # SYNONYM_LABEL: 3 axes × 2 retries each = 6 calls.
        syn = next(row for row in run.per_type
                   if row.mtype is ModificationType.SYNONYM_LABEL)
        assert syn.n_llm_calls == 6
        # Every skipped target contributed to n_skipped, none to n_generated.
        for row in run.per_type:
            if row.n_targets > 0:
                assert row.n_skipped_targets == row.n_targets
                assert row.n_generated_targets == 0

    def test_list_shaped_text_variables_do_not_crash(self, tmp_path: Path):
        """Regression: real OBRA CIVIL data has LIST_plain (indexed refs)
        and LIST_conditional (bare refs) text-variables. `run_menu` must
        apply `l2_repr.list_to_formula(include_conditional=True)` before
        passing the stage_json to `menu_proposer.propose_type`, otherwise
        `slot_extractor.extract_slots` crashes with `TypeError: expected
        string or bytes-like object, got 'list'`.
        """
        stage = {
            "OEB999$": {
                "ud": "m",
                "concept": "TEST",
                "parameters": {
                    "B": {"label": "AX", "values": [
                        {"label": "a", "value": "AA"},
                        {"label": "b", "value": "BB"},
                    ]},
                },
                # Mix all three text-variable shapes exercised in production.
                "text_variables": {
                    "G": ['"g_a"', '"g_b"'],                             # LIST_plain (indexed)
                    "K": '"k_a" * (%B=a) + "k_b" * (%B=b)',              # STR_formula (bare)
                    "P": ['"p_a" * (%B=a)', '"p_b" * (%B=b)'],           # LIST_conditional (bare)
                },
                "resumen": "R $G(%B) $K $P",
                "texto": "T $G(%B) $K $P end",
            }
        }
        # Fill every mtype's queue with malformed responses — we only care
        # that run_menu returns without crashing on the mixed shapes.
        client = _StubLLMClient(["not json"] * 500)
        run = run_menu(
            stage,
            concept_filter=None,
            n=1,
            client=client,
            chapter_label="mixed",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
        )
        # L2 targets are non-zero — all three text-variable shapes should be
        # enumerable after the l2_repr conversion.
        para = next(row for row in run.per_type
                    if row.mtype is ModificationType.PARAPHRASE)
        assert para.n_targets > 0

    def test_empty_type_has_zero_llm_calls(self, tmp_path: Path):
        """unit_conversion / unit_expansion on the tiny fixture have zero
        targets (no axis values carry unit tokens) → no LLM call, no output
        file, no cost."""
        stage = _load_tiny()
        client = _StubLLMClient(["not json"] * 500)
        run = run_menu(
            stage,
            concept_filter=None,
            n=1,
            client=client,
            chapter_label="tiny",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
        )
        unit_conv = next(row for row in run.per_type
                         if row.mtype is ModificationType.UNIT_CONVERSION)
        assert unit_conv.n_targets == 0
        assert unit_conv.n_llm_calls == 0
        assert not (tmp_path / "m" / "unit_conversion.jsonl").exists()

    @staticmethod
    def _canned_responses_for_full_run() -> list[str]:
        """Generous per-type queue: enough calls that every populated type
        gets a valid response; malformed padding for the rest so nothing
        drains the queue past its end."""
        responses: list[str] = []
        # SYNONYM_LABEL: 3 axes alphabetical.
        responses += [
            _l1_response([
                [("PVC", "Cloruro de polivinilo"), ("HDPE", "Polietileno HD")],
                [("PVC", "Plástico PVC"), ("HDPE", "Tubo HDPE")],
            ]),
            _l1_response([
                [("Normal", "Estándar"), ("Rocoso", "Con roca")],
                [("Normal", "Común"), ("Rocoso", "Pedregoso")],
            ]),
            _l1_response([
                [("Diurno", "Turno diurno"), ("Nocturno", "Turno nocturno")],
                [("Diurno", "En horario diurno"), ("Nocturno", "En horario nocturno")],
            ]),
        ]
        # NUM_TO_TEXT: 1 axis (PROFUNDIDAD) with numeric values.
        responses += [
            _l1_response([
                [("1", "uno"), ("2", "dos")],
                [("1", "un"), ("2", "dos unidades")],
            ], list_key="numerals"),
        ]
        # UNIT_CONVERSION / UNIT_EXPANSION: probably empty on tiny (no unit
        # tokens on the axes) — supply malformed as padding, won't be called.
        # ABBREV_EXPANSION / CODE_EXPANSION: MATERIAL has abbreviations (PVC/HDPE).
        for _ in range(4):  # 2 types × 2 attempts fallback if empty
            responses.append(_l1_response([
                [("PVC", "Policloruro de vinilo"), ("HDPE", "Polietileno de alta densidad")],
                [("PVC", "PVC (cloruro de polivinilo)"), ("HDPE", "HDPE (polietileno de alta densidad)")],
            ]))
        # PARAPHRASE / EXPANSION / COMPRESSION: 3 fragments each (medio, normal, rocoso).
        for _ in range(3):
            responses += [
                _l2_response([("medio", "intermedio"), ("medio", "regular")]),
                _l2_response([("normal", "estándar"), ("normal", "común")]),
                _l2_response([("rocoso", "pedregoso"), ("rocoso", "con piedras")]),
            ]
        # OMISSION: 3 concepts × 2 fields = up to 6 targets × N vars each.
        # Pad with several valid responses; extras are unused.
        for _ in range(30):
            responses.append(_l3_omission_response([
                ("original template $A $B", "original template $A", "$B"),
                ("original template $A $B", "template $A only", "$B"),
            ]))
        # REORDER + TEMPLATE_PARAPHRASE: 3 concepts × 2 fields each = 6 targets each.
        for _ in range(12):
            responses.append(_l3_reorder_response([
                ("original template", "template original"),
                ("original template", "the template rewritten"),
            ]))
        for _ in range(12):
            responses.append(_l3_template_paraphrase_response([
                ("original template", "paraphrased template"),
                ("original template", "another paraphrase"),
            ]))
        # NEW_PARAM: 3 concepts.
        for _ in range(3):
            responses.append(_new_param_response([
                {
                    "new_axis_label": "ACABADO",
                    "var_definition": "$Z",
                    "template_patch": " ($Z)",
                    "values": [
                        {"label": "a", "value": "liso"},
                        {"label": "b", "value": "rugoso"},
                    ],
                },
                {
                    "new_axis_label": "COLOR",
                    "var_definition": "$W",
                    "template_patch": " ($W)",
                    "values": [
                        {"label": "a", "value": "blanco"},
                        {"label": "b", "value": "negro"},
                    ],
                },
            ]))
        return responses


# ===========================================================================
# Sprint 38.6 — skip_types guard
# ===========================================================================


class TestSkipTypes:
    def test_run_menu_skips_named_types(self, tmp_path: Path):
        """skip_types leaves the type unproposed and writes no artefact for it."""
        stage = _load_tiny()
        # Junk padding lets every non-skipped type run (and cleanly skip on
        # parse failure); the skipped type must consume none of it — asserted
        # via its per-type n_llm_calls == 0.
        client = _StubLLMClient(["not json"] * 500)
        run = run_menu(
            stage,
            n=2,
            client=client,
            chapter_label="T",
            out_dir_machine=tmp_path / "m",
            out_dir_review=tmp_path / "r",
            skip_types=frozenset({ModificationType.TEMPLATE_PARAPHRASE}),
            concept_filter=None,
        )
        stat = next(s for s in run.per_type if s.mtype is ModificationType.TEMPLATE_PARAPHRASE)
        assert stat.n_llm_calls == 0 and stat.n_generated_targets == 0
        assert not (tmp_path / "m" / "template_paraphrase.jsonl").exists()


# ===========================================================================
# format_scorecard tests
# ===========================================================================


class TestFormatScorecard:
    def test_produces_markdown_table_with_header(self):
        run = MenuRun(
            chapter_label="OEB",
            concept_count=25,
            n_unique_targets_total=562,
            n_llm_calls_total=380,
            wall_clock_s=9000.0,
            per_type=(
                TypeStat(
                    mtype=ModificationType.SYNONYM_LABEL,
                    n_targets=49, n_llm_calls=15,
                    n_generated_targets=48, n_skipped_targets=1,
                    n_total_candidates=478, n_dropped_candidates=2,
                ),
            ),
        )
        s = format_scorecard(run)
        assert "Menu-builder scorecard — OEB" in s
        assert "| Rewrite type | Targets |" in s
        assert "| synonym_label | 49 | 15 | 48 | 1 | 478 | 2 |" in s
        assert "Concepts: **25**" in s
        assert "9000.0 s" in s


# ===========================================================================
# ResumingRecordingClient — cache-first resume across partial runs
# ===========================================================================


class TestResumingRecordingClient:
    def test_cached_prompt_served_from_disk_no_inner_call(self, tmp_path: Path):
        """A prompt whose hash is already in the store is served without
        touching the inner client. This is what makes a re-run after a
        transport-error crash resume instead of redoing everything."""
        prompt = "test prompt"
        digest = prompt_hash(prompt)
        (tmp_path / f"{digest}.json").write_text(
            json.dumps({"prompt": prompt, "response": "cached response"}),
            encoding="utf-8",
        )

        class _FailingInner:
            def complete(self, _prompt):
                raise AssertionError("inner client must not be called")

        client = ResumingRecordingClient(_FailingInner(), tmp_path)
        assert client.complete(prompt) == "cached response"

    def test_uncached_prompt_calls_inner_and_records(self, tmp_path: Path):
        class _Inner:
            def __init__(self):
                self.calls = 0

            def complete(self, _prompt):
                self.calls += 1
                return "fresh response"

        inner = _Inner()
        client = ResumingRecordingClient(inner, tmp_path)
        assert client.complete("new prompt") == "fresh response"
        assert inner.calls == 1
        # Second call to the same prompt: served from cache, inner untouched.
        assert client.complete("new prompt") == "fresh response"
        assert inner.calls == 1

    def test_store_format_matches_recording_client(self, tmp_path: Path):
        """A store populated by ResumingRecordingClient is readable by
        ReplayClient / the existing tooling — same one-file-per-prompt shape."""
        from synthetic.llm_client import ReplayClient

        class _Inner:
            def complete(self, prompt):
                return f"echo:{prompt}"

        client = ResumingRecordingClient(_Inner(), tmp_path)
        client.complete("prompt A")
        client.complete("prompt B")
        # ReplayClient serves them without knowing it wasn't RecordingClient.
        replay = ReplayClient(tmp_path)
        assert replay.complete("prompt A") == "echo:prompt A"
        assert replay.complete("prompt B") == "echo:prompt B"


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

    def test_no_seam_module_imports_menu_runner(self):
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
            assert "menu_runner" not in got, name

    def test_menu_runner_does_not_import_forbidden_seams(self):
        mod = importlib.import_module("synthetic.menu_runner")
        got = self._imports(mod)
        forbidden = {
            "stage_b", "run_synthetic", "mutator", "layer_l1", "layer_l2",
            "layer_l3", "layer_pd", "metadata", "packaging", "review",
            "stage_runners", "variant_proposer", "slot_extractor",
        }
        hits = got & forbidden
        assert not hits, f"menu_runner imports forbidden: {hits}"
