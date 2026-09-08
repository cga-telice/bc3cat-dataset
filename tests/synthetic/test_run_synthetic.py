"""Sprint 16 — Phase D Task D2 (Stage-A half): the synthetic orchestrator.

Covers the condition matrix (`CONDITION_SPECS`), the deterministic seeded
planner (`plan_concept_variants`), the per-variant proposal/emission/
composition loop (`run_variant`), per-concept catalog assembly + write
(`run_concept`), and the order/seed-stable outer loop (`run_catalog`).

No live LLM, no notebook execution, no real stage-JSON IO — inline
fixtures + a queued/const stub `LLMClient`, same as
`test_llm_proposer.py` / `test_variant_proposer.py`.
"""

import copy
import importlib
import json
import random

import pytest

from synthetic import run_synthetic
from synthetic.run_synthetic import (
    ALL_TYPES,
    MAX_MIX_DEPTH,
    Attempt,
    CONDITION_SPECS,
    ConditionSpec,
    VariantPlan,
    plan_concept_variants,
    run_catalog,
    run_concept,
    run_variant,
)
from synthetic import layer_l1
from synthetic.taxonomy import Layer, ModificationType, TYPE_TO_LAYER
from synthetic.variant_catalog import read_catalog_entry


# ----- stubs ------------------------------------------------------------

class _StubLLMClient:
    """Queued-response client — pops one response per `complete` call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._responses.pop(0)


class _ConstLLMClient:
    """Returns the same response on every call (queue-exhaustion-proof)."""

    def __init__(self, response):
        self._response = response
        self.calls = []

    def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self._response


# ----- fixtures ---------------------------------------------------------

def _stage():
    return {
        "OEB020aa": {
            "parent_key": "OEB020$",
            "parameters": {
                "B": {"label": "TIPO DE TERRENO",
                      "values": [{"label": "a", "value": "Normal"},
                                 {"label": "b", "value": "Rocoso"}]},
            },
            "text_variables": {"K": '"normal" * (%B=a) + "rocoso" * (%B=b)'},
            "resumen": "Canalización para terreno normal",
            "texto": "Canalización para terreno $K, incluso $N",
        },
    }


def _stage_two_axes():
    s = _stage()
    s["OEB020aa"]["parameters"]["C"] = {
        "label": "PROFUNDIDAD",
        "values": [{"label": "a", "value": "Somera"},
                   {"label": "b", "value": "Profunda"}],
    }
    return s


def _stage_no_l2():
    s = _stage()
    del s["OEB020aa"]["text_variables"]
    return s


def _stage_minimal():
    """Only a resumen — reorder (RESUMEN) + template_paraphrase (RESUMEN)
    + new_param (None) are the only eligible attempts on this shape, so
    the full pool yields exactly 3 attempts."""
    return {
        "OEB020aa": {
            "parent_key": "OEB020$",
            "resumen": "Canalización para terreno normal",
        },
    }


_SYNONYM_OK = json.dumps({"synonyms": [{"original": "Normal", "new": "Estándar"}]})
_MALFORMED = "not json at all {"


# ========================================================================
# Condition matrix
# ========================================================================

def test_module_exposes_public_surface():
    for name in (
        "CONDITION_SPECS", "ConditionSpec", "Attempt", "VariantPlan",
        "plan_concept_variants", "run_variant", "run_concept", "run_catalog",
    ):
        assert hasattr(run_synthetic, name), name


def test_condition_specs_key_set():
    expected = {
        "single_L1_synonym_label", "single_L1_num_to_text",
        "single_L1_unit_conversion", "single_L1_unit_expansion",
        "single_L1_abbrev_expansion", "single_L1_code_expansion",
        "single_L2_paraphrase", "single_L2_expansion", "single_L2_compression",
        "single_L3_omission", "single_L3_reorder",
        # Sprint 36: TEMPLATE_PARAPHRASE (L3) joins the single-type conditions.
        "single_L3_template_paraphrase",
        "new_param_only",
        "stacked_2", "stacked_3", "stacked_4", "stacked_5plus",
        "full_random_mix",
    }
    assert set(CONDITION_SPECS) == expected
    assert len(CONDITION_SPECS) == 18


def test_condition_specs_singles_are_singletons_with_matching_layer_tag():
    for label, spec in CONDITION_SPECS.items():
        if not label.startswith("single_"):
            continue
        assert len(spec.pool) == 1, label
        assert spec.stack_depth == 1
        assert spec.sampled is False
        (mtype,) = tuple(spec.pool)
        tag = run_synthetic._layer_tag(mtype)
        assert label == f"single_{tag}_{mtype.value}"


def test_condition_specs_stacked_depths():
    assert CONDITION_SPECS["stacked_2"].stack_depth == 2
    assert CONDITION_SPECS["stacked_3"].stack_depth == 3
    assert CONDITION_SPECS["stacked_4"].stack_depth == 4
    assert CONDITION_SPECS["stacked_5plus"].stack_depth == 5
    assert CONDITION_SPECS["full_random_mix"].stack_depth == 0
    assert CONDITION_SPECS["new_param_only"].stack_depth == 1
    assert CONDITION_SPECS["new_param_only"].sampled is False
    for label in ("stacked_2", "stacked_3", "stacked_4", "stacked_5plus",
                  "full_random_mix"):
        assert CONDITION_SPECS[label].sampled is True


def test_condition_specs_pool_membership():
    for label in ("stacked_2", "stacked_3", "stacked_4", "stacked_5plus",
                  "full_random_mix"):
        assert CONDITION_SPECS[label].pool == ALL_TYPES
    assert CONDITION_SPECS["new_param_only"].pool == frozenset(
        {ModificationType.NEW_PARAM}
    )


# ========================================================================
# Planner
# ========================================================================

def test_plan_single_l1_is_exhaustive_over_axes():
    rng = random.Random(0)
    plans = plan_concept_variants(
        _stage_two_axes(), "OEB020aa", ["single_L1_synonym_label"], rng=rng,
    )
    assert len(plans) == 2
    targets = {p.attempts[0].target_id for p in plans}
    assert targets == {"B", "C"}


def test_plan_single_assigns_one_attempt_each():
    rng = random.Random(0)
    plans = plan_concept_variants(
        _stage_two_axes(), "OEB020aa", ["single_L1_synonym_label"], rng=rng,
    )
    for p in plans:
        assert len(p.attempts) == 1
        assert p.attempts[0].modification_type is ModificationType.SYNONYM_LABEL


def test_plan_condition_with_no_targets_yields_no_plan():
    rng = random.Random(0)
    plans = plan_concept_variants(
        _stage_no_l2(), "OEB020aa", ["single_L2_paraphrase"], rng=rng,
    )
    assert plans == []


def test_plan_variant_ids_are_monotonic_per_concept():
    rng = random.Random(0)
    plans = plan_concept_variants(
        _stage_two_axes(), "OEB020aa",
        ["single_L1_synonym_label", "single_L1_num_to_text"], rng=rng,
    )
    ids = [p.variant_id for p in plans]
    assert ids == [f"OEB020aa_syn_v{i}" for i in range(len(ids))]


def test_plan_is_deterministic_under_same_seed():
    conditions = ["single_L1_synonym_label", "stacked_3", "full_random_mix"]
    a = plan_concept_variants(
        _stage(), "OEB020aa", conditions, rng=random.Random(123),
    )
    b = plan_concept_variants(
        _stage(), "OEB020aa", conditions, rng=random.Random(123),
    )
    assert a == b


def test_plan_stacked_samples_n_distinct_attempts():
    rng = random.Random(5)
    plans = plan_concept_variants(_stage(), "OEB020aa", ["stacked_3"], rng=rng)
    assert len(plans) == 1
    attempts = plans[0].attempts
    assert len(attempts) == 3
    assert len(set(attempts)) == 3  # distinct


def test_plan_stacked_degrades_when_fewer_than_n_available():
    # _stage_minimal yields exactly 3 attempts (reorder RESUMEN +
    # template_paraphrase RESUMEN + new_param); stacked_4 requests 4 ->
    # degrades to 3.
    rng = random.Random(5)
    plans = plan_concept_variants(
        _stage_minimal(), "OEB020aa", ["stacked_4"], rng=rng,
    )
    assert len(plans) == 1
    assert len(plans[0].attempts) == 3


def test_plan_full_random_mix_depth_in_bounds():
    for seed in range(8):
        rng = random.Random(seed)
        plans = plan_concept_variants(
            _stage(), "OEB020aa", ["full_random_mix"], rng=rng,
        )
        assert len(plans) == 1
        depth = len(plans[0].attempts)
        assert 2 <= depth <= MAX_MIX_DEPTH


# ========================================================================
# run_variant
# ========================================================================

def test_run_variant_records_one_provenance_per_attempt():
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="stacked_3",
        attempts=(
            Attempt(ModificationType.SYNONYM_LABEL, "B"),
            Attempt(ModificationType.NUM_TO_TEXT, "B"),
            Attempt(ModificationType.PARAPHRASE, ("K", "%B=a")),
        ),
    )
    client = _StubLLMClient([
        json.dumps({"synonyms": [{"original": "Normal", "new": "Estándar"}]}),
        json.dumps({"numerals": [{"original": "Normal", "new": "uno"}]}),
        json.dumps({"original": "normal", "new": "corriente",
                    "preserves_meaning": True}),
    ])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    assert len(outcome.provenance) == 3


def test_run_variant_success_lands_record_with_rules():
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="single_L1_synonym_label",
        attempts=(Attempt(ModificationType.SYNONYM_LABEL, "B"),),
    )
    client = _StubLLMClient([_SYNONYM_OK])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    assert outcome.record is not None
    assert len(outcome.record.rules) == 1
    assert outcome.record.rules[0]["type"] == "synonym_label"


def test_run_variant_all_skipped_lands_no_record():
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="single_L1_synonym_label",
        attempts=(Attempt(ModificationType.SYNONYM_LABEL, "B"),),
    )
    # malformed twice -> retry exhausted -> proposal skipped
    client = _StubLLMClient([_MALFORMED, _MALFORMED])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    assert outcome.record is None
    assert len(outcome.skipped) >= 1
    assert len(outcome.provenance) == 1


def test_run_variant_unmatched_payload_becomes_skip():
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="single_L1_synonym_label",
        attempts=(Attempt(ModificationType.SYNONYM_LABEL, "B"),),
    )
    # 'Inexistente' is not a value on axis B -> unmatched
    client = _StubLLMClient([
        json.dumps({"synonyms": [{"original": "Inexistente", "new": "X"}]}),
    ])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    assert outcome.record is None
    reasons = [m.reason or "" for m in outcome.skipped]
    assert any(r.startswith("unmatched_payload_entry") for r in reasons)


def test_run_variant_calls_compose_not_apply():
    # two synonym_label attempts on the same (param B, value Normal) collide
    # at compose time -> one rule lands, one same_target skip.
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="stacked_2",
        attempts=(
            Attempt(ModificationType.SYNONYM_LABEL, "B"),
            Attempt(ModificationType.SYNONYM_LABEL, "B"),
        ),
    )
    client = _StubLLMClient([
        json.dumps({"synonyms": [{"original": "Normal", "new": "Estándar"}]}),
        json.dumps({"synonyms": [{"original": "Normal", "new": "Corriente"}]}),
    ])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    assert outcome.record is not None
    assert len(outcome.record.rules) == 1
    reasons = [m.reason or "" for m in outcome.skipped]
    assert any("same_target_conflict" in r for r in reasons)


def test_run_synthetic_does_not_import_mutator():
    # scope tripwire: the orchestrator must not bind `mutator`
    assert "mutator" not in run_synthetic.__dict__


def test_run_variant_provenance_carries_payload_on_success():
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="single_L1_synonym_label",
        attempts=(Attempt(ModificationType.SYNONYM_LABEL, "B"),),
    )
    client = _StubLLMClient([_SYNONYM_OK])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    prov = outcome.provenance[0]
    assert prov.validated_payload is not None
    assert prov.skipped is None


def test_run_variant_provenance_carries_skip_on_failure():
    plan = VariantPlan(
        variant_id="OEB020aa_syn_v0",
        condition="single_L1_synonym_label",
        attempts=(Attempt(ModificationType.SYNONYM_LABEL, "B"),),
    )
    client = _StubLLMClient([_MALFORMED, _MALFORMED])
    outcome = run_variant(_stage(), "OEB020aa", plan, client)
    prov = outcome.provenance[0]
    assert prov.validated_payload is None
    assert prov.skipped is not None


# ========================================================================
# run_concept
# ========================================================================

def test_run_concept_writes_one_catalog_file(tmp_path):
    client = _StubLLMClient([_SYNONYM_OK])
    entry, path = run_concept(
        _stage(), "OEB020aa", ["single_L1_synonym_label"], client,
        out_dir=tmp_path, seed=7,
    )
    assert path.name == "OEB020aa.json"
    assert path.exists()
    assert list(tmp_path.glob("*.json")) == [path]


def test_run_concept_entry_round_trips_via_read(tmp_path):
    client = _StubLLMClient([_SYNONYM_OK])
    entry, path = run_concept(
        _stage(), "OEB020aa", ["single_L1_synonym_label"], client,
        out_dir=tmp_path, seed=7,
    )
    assert read_catalog_entry(path) == entry


def test_run_concept_entry_carries_concept_resumen_and_parent_key(tmp_path):
    client = _StubLLMClient([_SYNONYM_OK])
    entry, _ = run_concept(
        _stage(), "OEB020aa", ["single_L1_synonym_label"], client,
        out_dir=tmp_path, seed=7,
    )
    assert entry.concept_resumen == "Canalización para terreno normal"
    assert entry.parent_key == "OEB020$"


def test_run_concept_emitted_rule_applies_via_layer_l1(tmp_path):
    client = _StubLLMClient([_SYNONYM_OK])
    stage = _stage()
    entry, _ = run_concept(
        stage, "OEB020aa", ["single_L1_synonym_label"], client,
        out_dir=tmp_path, seed=7,
    )
    rule = entry.variants[0].rules[0]
    # end-to-end gate: the emitted rule applies without raising
    layer_l1.apply_synonym_label(copy.deepcopy(stage), "OEB020aa", rule)


def test_run_concept_is_deterministic_under_same_seed(tmp_path):
    d1 = tmp_path / "a"
    d2 = tmp_path / "b"
    conditions = ["single_L1_synonym_label", "stacked_3"]
    c1 = _ConstLLMClient(_SYNONYM_OK)
    c2 = _ConstLLMClient(_SYNONYM_OK)
    e1, _ = run_concept(_stage(), "OEB020aa", conditions, c1,
                        out_dir=d1, seed=99)
    e2, _ = run_concept(_stage(), "OEB020aa", conditions, c2,
                        out_dir=d2, seed=99)
    assert e1 == e2


# ========================================================================
# run_catalog
# ========================================================================

def _multi_stage():
    s = _stage()
    s["OEB030bb"] = copy.deepcopy(s["OEB020aa"])
    s["OEB030bb"]["parent_key"] = "OEB030$"
    s["OEB040cc"] = copy.deepcopy(s["OEB020aa"])
    s["OEB040cc"]["parent_key"] = "OEB040$"
    return s


def test_run_catalog_writes_one_file_per_concept(tmp_path):
    client = _ConstLLMClient(_SYNONYM_OK)
    paths = run_catalog(
        _multi_stage(), ["OEB020aa", "OEB030bb", "OEB040cc"],
        ["single_L1_synonym_label"], client, out_dir=tmp_path, seed=7,
    )
    assert len(paths) == 3
    assert {p.name for p in paths} == {
        "OEB020aa.json", "OEB030bb.json", "OEB040cc.json"
    }


def test_run_catalog_order_stable(tmp_path):
    client = _ConstLLMClient(_SYNONYM_OK)
    keys = ["OEB040cc", "OEB020aa", "OEB030bb"]
    paths = run_catalog(
        _multi_stage(), keys, ["single_L1_synonym_label"],
        client, out_dir=tmp_path, seed=7,
    )
    assert [p.stem for p in paths] == keys


def test_run_catalog_per_concept_seed_stable_across_batch_size(tmp_path):
    conditions = ["stacked_3"]
    d_solo = tmp_path / "solo"
    d_batch = tmp_path / "batch"
    run_catalog(_multi_stage(), ["OEB020aa"], conditions,
                _ConstLLMClient(_SYNONYM_OK), out_dir=d_solo, seed=7)
    run_catalog(_multi_stage(), ["OEB020aa", "OEB030bb", "OEB040cc"],
                conditions, _ConstLLMClient(_SYNONYM_OK),
                out_dir=d_batch, seed=7)
    solo = read_catalog_entry(d_solo / "OEB020aa.json")
    batch = read_catalog_entry(d_batch / "OEB020aa.json")
    assert solo == batch


def test_seed_for_is_stable_across_process():
    # sha256-derived, not the per-process-salted hash() — pinned value.
    assert run_synthetic._seed_for("OEB020aa", 7) == 5357104946266607742


# ========================================================================
# Hygiene
# ========================================================================

def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(run_synthetic)
    assert len(reloaded.CONDITION_SPECS) == 18
