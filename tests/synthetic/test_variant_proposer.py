"""Contract tests for `synthetic.variant_proposer` — Sprint 14, Phase C Task C3.

Pins the public surface (`VariantProposal`, `propose_variant`,
`EXPECTED_SLOTS`), per-`ModificationType` schema validation, prompt
rendering with JSON-aware brace escaping, and the two distinguishable
skip-reason prefixes (`malformed_llm_response_after_retry: ` from C2
fallback vs. `schema_validation_failed: ` from C3 validation failure).
"""

from __future__ import annotations

import importlib
import json
from dataclasses import FrozenInstanceError

import pytest

from synthetic.prompts import load_prompt
from synthetic.taxonomy import (
    Layer,
    Modification,
    ModificationType,
    TYPE_TO_LAYER,
)
from synthetic.variant_proposer import (
    EXPECTED_SLOTS,
    VariantProposal,
    propose_variant,
)


_ALL_TYPES = tuple(ModificationType)


class _StubLLMClient:
    """In-test transport: pops queued responses off a list per call."""

    def __init__(self, responses: list[str]):
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


# ---------------------------------------------------------------------------
# Per-type fixtures: templates, slot dicts, and schema-valid payloads.
# ---------------------------------------------------------------------------

_L1_TEMPLATE = (
    "Concepto: {concept}\nEje: {axis_label}\nValores: {value_list}\n"
    'Responde SOLO con un JSON: {"synonyms": [...]}'
)
_L1_SLOTS = {
    "concept": "Canalización",
    "axis_label": "TIPO DE TERRENO",
    "value_list": "Normal, Rocoso",
}
_NUM_TO_TEXT_TEMPLATE = (
    "Concepto: {concept}\nEje: {axis_label}\nValores: {value_list}\n"
    'Responde SOLO con un JSON: {"numerals": [...]}'
)
_L2_TEMPLATE = (
    "Concepto: {concept}\nVariable: {var_key}\nFragmento: {fragment}\n"
    "Condición: {condition}\nSiblings: {sibling_fragments}\n"
    'Responde SOLO con un JSON: {"original": "...", "new": "...", "preserves_meaning": true}'
)
_L2_SLOTS = {
    "concept": "Canalización",
    "var_key": "K",
    "fragment": "normal",
    "condition": "%B=a",
    "sibling_fragments": "%B=b: rocoso",
}
_OMISSION_TEMPLATE = (
    "Concepto: {concept}\nTemplate: {template}\nVar a omitir: {var_to_omit}\n"
    "Eje: {axis_label}\n"
    'Responde SOLO con un JSON: {"original": "...", "new": "...", "omitted_var": "..."}'
)
_OMISSION_SLOTS = {
    "concept": "Canalización",
    "template": "Canalización de $A tubos, incluso $N",
    "var_to_omit": "N",
    "axis_label": "TIPO DE ACABADO",
}
_REORDER_TEMPLATE = (
    "Concepto: {concept}\nTemplate: {template}\nConstituyentes: {constituents}\n"
    'Responde SOLO con un JSON: {"original": "...", "new": "...", "preserves_meaning": true}'
)
_REORDER_SLOTS = {
    "concept": "Canalización",
    "template": "Canalización de $A tubos, incluso $N",
    "constituents": "$A; $N",
}
_NEW_PARAM_TEMPLATE = (
    "Concepto: {concept}\nEjes: {existing_axes_with_labels}\n"
    "Admisibles: {allowlist}\n"
    'Responde SOLO con un JSON: {"new_axis_label": "...", "values": [...], '
    '"var_definition": "...", "template_patch": "..."}'
)
_NEW_PARAM_SLOTS = {
    "concept": "Canalización",
    "existing_axes_with_labels": "B: TIPO DE TERRENO; D: PROFUNDIDAD",
    "allowlist": "[acabado, recubrimiento]",
}
_TEMPLATE_PARAPHRASE_TEMPLATE = (
    "Concepto: {concept}\nCampo: {field}\nPlantilla: {template}\n"
    "Placeholders: {placeholders}\n"
    'Responde SOLO con un JSON: {"original": "...", "new": "...", "preserves_meaning": true}'
)
_TEMPLATE_PARAPHRASE_SLOTS = {
    "concept": "Canalización",
    "field": "RESUMEN",
    "template": "Canalización de $A tubos, incluso $N",
    "placeholders": "$A, $N",
}


_TEMPLATES: dict[ModificationType, str] = {
    ModificationType.SYNONYM_LABEL:    _L1_TEMPLATE,
    ModificationType.NUM_TO_TEXT:      _NUM_TO_TEXT_TEMPLATE,
    ModificationType.UNIT_CONVERSION:  _L1_TEMPLATE,
    ModificationType.UNIT_EXPANSION:   _L1_TEMPLATE,
    ModificationType.ABBREV_EXPANSION: _L1_TEMPLATE,
    ModificationType.CODE_EXPANSION:   _L1_TEMPLATE,
    ModificationType.PARAPHRASE:       _L2_TEMPLATE,
    ModificationType.EXPANSION:        _L2_TEMPLATE,
    ModificationType.COMPRESSION:      _L2_TEMPLATE,
    ModificationType.OMISSION:         _OMISSION_TEMPLATE,
    ModificationType.REORDER:          _REORDER_TEMPLATE,
    ModificationType.TEMPLATE_PARAPHRASE: _TEMPLATE_PARAPHRASE_TEMPLATE,
    ModificationType.NEW_PARAM:        _NEW_PARAM_TEMPLATE,
}

_SLOTS: dict[ModificationType, dict[str, str]] = {
    ModificationType.SYNONYM_LABEL:    dict(_L1_SLOTS),
    ModificationType.NUM_TO_TEXT:      dict(_L1_SLOTS),
    ModificationType.UNIT_CONVERSION:  dict(_L1_SLOTS),
    ModificationType.UNIT_EXPANSION:   dict(_L1_SLOTS),
    ModificationType.ABBREV_EXPANSION: dict(_L1_SLOTS),
    ModificationType.CODE_EXPANSION:   dict(_L1_SLOTS),
    ModificationType.PARAPHRASE:       dict(_L2_SLOTS),
    ModificationType.EXPANSION:        dict(_L2_SLOTS),
    ModificationType.COMPRESSION:      dict(_L2_SLOTS),
    ModificationType.OMISSION:         dict(_OMISSION_SLOTS),
    ModificationType.REORDER:          dict(_REORDER_SLOTS),
    ModificationType.TEMPLATE_PARAPHRASE: dict(_TEMPLATE_PARAPHRASE_SLOTS),
    ModificationType.NEW_PARAM:        dict(_NEW_PARAM_SLOTS),
}

_PAYLOADS: dict[ModificationType, dict] = {
    ModificationType.SYNONYM_LABEL: {
        "synonyms": [{"original": "Normal", "new": "Estándar"}],
    },
    ModificationType.NUM_TO_TEXT: {
        "numerals": [{"original": "2", "new": "dos"}],
    },
    ModificationType.UNIT_CONVERSION: {
        "synonyms": [{"original": "m", "new": "metro"}],
    },
    ModificationType.UNIT_EXPANSION: {
        "synonyms": [{"original": "m3", "new": "metro cúbico"}],
    },
    ModificationType.ABBREV_EXPANSION: {
        "synonyms": [{"original": "HM-20", "new": "Hormigón en masa HM-20"}],
    },
    ModificationType.CODE_EXPANSION: {
        "synonyms": [{"original": "OEB020", "new": "OEB020 — canalización"}],
    },
    ModificationType.PARAPHRASE: {
        "original": "Hormigón HM-20",
        "new": "Hormigón en masa HM-20",
        "preserves_meaning": True,
    },
    ModificationType.EXPANSION: {
        "original": "normal",
        "new": "de tipo normal",
        "preserves_meaning": True,
    },
    ModificationType.COMPRESSION: {
        "original": "de tipo normal",
        "new": "normal",
        "preserves_meaning": True,
    },
    ModificationType.OMISSION: {
        "original": "Canalización de $A tubos, incluso $N",
        "new": "Canalización de $A tubos",
        "omitted_var": "N",
    },
    ModificationType.REORDER: {
        "original": "Canalización de $A tubos, incluso $N",
        "new": "Canalización con $N, incluyendo $A tubos",
        "preserves_meaning": True,
    },
    ModificationType.TEMPLATE_PARAPHRASE: {
        # Sprint 36: same shape as reorder; placeholders preserved verbatim.
        "original": "Canalización de $A tubos, incluso $N",
        "new": "Conducción con $A conductos y $N adicional",
        "preserves_meaning": True,
    },
    ModificationType.NEW_PARAM: {
        "new_axis_label": "TIPO DE ACABADO",
        "values": [
            {"label": "a", "value": "rugoso"},
            {"label": "b", "value": "liso"},
        ],
        "var_definition": '$X = "rugoso" * (%G=a) + "liso" * (%G=b)',
        "template_patch": ", con acabado $X",
    },
}


# ---------------------------------------------------------------------------
# 1. Public surface
# ---------------------------------------------------------------------------

def test_module_exposes_public_surface():
    import synthetic.variant_proposer as mod

    assert hasattr(mod, "VariantProposal")
    assert hasattr(mod, "propose_variant")
    assert hasattr(mod, "EXPECTED_SLOTS")
    assert VariantProposal is mod.VariantProposal
    assert propose_variant is mod.propose_variant
    assert EXPECTED_SLOTS is mod.EXPECTED_SLOTS


def test_expected_slots_covers_all_modification_types():
    assert set(EXPECTED_SLOTS) == set(ModificationType)
    # Sprint 36: TEMPLATE_PARAPHRASE brought the count to 13.
    assert len(EXPECTED_SLOTS) == 13
    for mtype, slots in EXPECTED_SLOTS.items():
        assert isinstance(slots, frozenset), f"{mtype.value} slots not frozenset"
        assert len(slots) >= 3, f"{mtype.value} slots too few: {slots}"


@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_expected_slots_matches_prompt_audit(mtype):
    """Every declared slot in `EXPECTED_SLOTS[mtype]` must appear as
    `{<name>}` in the corresponding prompt body (before the
    'Responde SOLO con un JSON' marker)."""
    text = load_prompt(mtype)
    marker = "Responde SOLO con un JSON"
    idx = text.find(marker)
    assert idx >= 0, f"{mtype.value} missing '{marker}' marker"
    body = text[:idx]
    for slot in EXPECTED_SLOTS[mtype]:
        token = "{" + slot + "}"
        assert token in body, (
            f"{mtype.value} body missing declared placeholder {token!r}"
        )


# ---------------------------------------------------------------------------
# 2. Per-type happy path (parametrised x12)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_happy_path_per_type(mtype):
    payload = _PAYLOADS[mtype]
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[mtype],
        _SLOTS[mtype],
        stub,
        mtype,
    )
    assert result.payload == payload
    assert result.skipped is None
    assert len(result.raw_responses) == 1
    assert len(stub.calls) == 1


# ---------------------------------------------------------------------------
# 3. Per-type schema-violation path (parametrised x12)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mtype", _ALL_TYPES)
def test_schema_violation_per_type(mtype):
    stub = _StubLLMClient(['{"unrelated": "data"}'])
    result = propose_variant(
        _TEMPLATES[mtype],
        _SLOTS[mtype],
        stub,
        mtype,
    )
    assert result.payload is None
    assert result.skipped is not None
    assert isinstance(result.skipped, Modification)
    assert result.skipped.type == mtype
    assert result.skipped.layer == TYPE_TO_LAYER[mtype]
    assert isinstance(result.skipped.layer, Layer)
    assert result.skipped.status == "skipped"
    assert result.skipped.reason is not None
    assert result.skipped.reason.startswith("schema_validation_failed: ")
    # The C2 round-trip succeeded (one well-formed-but-wrong-shape response):
    assert len(result.raw_responses) == 1


# ---------------------------------------------------------------------------
# 4. C2-fallback propagation + two distinguishable prefixes
# ---------------------------------------------------------------------------

def test_c2_fallback_propagates():
    stub = _StubLLMClient(["junk1", "junk2"])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.payload is None
    assert result.skipped is not None
    assert result.skipped.reason is not None
    assert result.skipped.reason.startswith(
        "malformed_llm_response_after_retry: "
    )
    assert len(result.raw_responses) == 2
    assert result.raw_responses == ("junk1", "junk2")


def test_two_skip_prefixes_are_distinguishable():
    """The two skip-reason prefixes must be non-overlapping substrings —
    Phase E1's metadata grep relies on this convention."""
    c2_prefix = "malformed_llm_response_after_retry: "
    c3_prefix = "schema_validation_failed: "
    assert c2_prefix not in c3_prefix
    assert c3_prefix not in c2_prefix
    # And neither is a prefix of the other.
    assert not c2_prefix.startswith(c3_prefix)
    assert not c3_prefix.startswith(c2_prefix)


# ---------------------------------------------------------------------------
# 5. Render: slot substitution + JSON-literal preservation
# ---------------------------------------------------------------------------

def test_render_substitutes_slots():
    """The rendered prompt sent to the client contains every slot value
    and a single-brace JSON literal."""
    stub = _StubLLMClient([json.dumps(_PAYLOADS[ModificationType.SYNONYM_LABEL])])
    propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    rendered = stub.calls[0]
    for v in _SLOTS[ModificationType.SYNONYM_LABEL].values():
        assert v in rendered, f"missing slot value {v!r} in rendered output"
    # Single-brace JSON literal, NOT doubled:
    assert 'Responde SOLO con un JSON: {"synonyms": [...]}' in rendered
    assert "{{" not in rendered
    assert "}}" not in rendered


def test_render_preserves_json_literal_braces():
    """A template with a nested JSON literal renders with single braces
    in the output (not the doubled escape form)."""
    template = 'Concepto: {concept}\n... {"k": [1, 2]} ...\n{axis_label}/{value_list}'
    stub = _StubLLMClient([json.dumps(_PAYLOADS[ModificationType.SYNONYM_LABEL])])
    propose_variant(
        template,
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    rendered = stub.calls[0]
    assert '{"k": [1, 2]}' in rendered
    assert "Canalización" in rendered  # {concept} substituted
    assert "TIPO DE TERRENO" in rendered  # {axis_label} substituted


def test_render_handles_nested_json_in_new_param_prompt():
    """The real `new_param` prompt has nested JSON braces — exercise
    the renderer against it directly."""
    real_template = load_prompt(ModificationType.NEW_PARAM)
    stub = _StubLLMClient([json.dumps(_PAYLOADS[ModificationType.NEW_PARAM])])
    result = propose_variant(
        real_template,
        _SLOTS[ModificationType.NEW_PARAM],
        stub,
        ModificationType.NEW_PARAM,
    )
    assert result.payload == _PAYLOADS[ModificationType.NEW_PARAM]
    assert result.skipped is None
    rendered = stub.calls[0]
    # JSON literal block survived intact (single braces):
    assert '"new_axis_label"' in rendered
    assert '"values"' in rendered
    # Slot values were substituted:
    assert _SLOTS[ModificationType.NEW_PARAM]["concept"] in rendered
    assert _SLOTS[ModificationType.NEW_PARAM]["allowlist"] in rendered


# ---------------------------------------------------------------------------
# 6. Render: slot/placeholder mismatch raises (catalog-authoring errors)
# ---------------------------------------------------------------------------

def test_render_missing_slot_raises_keyerror():
    stub = _StubLLMClient([])
    with pytest.raises(KeyError) as excinfo:
        propose_variant(
            _TEMPLATES[ModificationType.SYNONYM_LABEL],
            {},  # empty slots
            stub,
            ModificationType.SYNONYM_LABEL,
        )
    msg = excinfo.value.args[0]
    assert "missing slots" in msg
    assert "synonym_label" in msg
    # All three expected slots flagged as missing:
    for slot in ("concept", "axis_label", "value_list"):
        assert slot in msg
    # No call should have been issued to the LLM:
    assert len(stub.calls) == 0


def test_render_extra_slot_raises_valueerror():
    stub = _StubLLMClient([])
    bad_slots = {**_SLOTS[ModificationType.SYNONYM_LABEL], "extra": "x"}
    with pytest.raises(ValueError) as excinfo:
        propose_variant(
            _TEMPLATES[ModificationType.SYNONYM_LABEL],
            bad_slots,
            stub,
            ModificationType.SYNONYM_LABEL,
        )
    msg = str(excinfo.value)
    assert "unexpected slots" in msg
    assert "extra" in msg
    assert len(stub.calls) == 0


def test_render_rejects_partial_slots():
    """Providing 2 of 3 expected slots flags both missing names."""
    stub = _StubLLMClient([])
    partial = {"concept": "X"}  # missing axis_label and value_list
    with pytest.raises(KeyError) as excinfo:
        propose_variant(
            _TEMPLATES[ModificationType.SYNONYM_LABEL],
            partial,
            stub,
            ModificationType.SYNONYM_LABEL,
        )
    msg = excinfo.value.args[0]
    assert "axis_label" in msg
    assert "value_list" in msg
    assert "concept" not in msg.split("(expected")[0]  # not in the "missing" half


# ---------------------------------------------------------------------------
# 7. Validator: pair-list types (synonyms / numerals)
# ---------------------------------------------------------------------------

def test_validate_pair_list_missing_key():
    stub = _StubLLMClient(['{"unrelated": []}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.skipped is not None
    assert result.skipped.reason is not None
    assert "missing_key: 'synonyms'" in result.skipped.reason


def test_validate_pair_list_wrong_inner_shape():
    stub = _StubLLMClient(['{"synonyms": [{"original": "x"}]}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.skipped is not None
    assert result.skipped.reason is not None
    assert "synonyms[0]_missing_key: 'new'" in result.skipped.reason


def test_validate_pair_list_empty():
    stub = _StubLLMClient(['{"synonyms": []}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.skipped is not None
    assert result.skipped.reason is not None
    assert "synonyms_is_empty" in result.skipped.reason


def test_validate_pair_list_non_str_value():
    stub = _StubLLMClient(['{"synonyms": [{"original": 1, "new": "x"}]}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.skipped is not None
    reason = result.skipped.reason or ""
    assert "original_not_str" in reason
    assert "type=int" in reason


def test_validate_pair_list_not_list():
    stub = _StubLLMClient(['{"synonyms": "not a list"}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.skipped is not None
    assert "synonyms_not_list" in (result.skipped.reason or "")


def test_validate_num_to_text_uses_numerals_key():
    """num_to_text payload uses 'numerals' (not 'synonyms')."""
    stub = _StubLLMClient(['{"synonyms": [{"original": "1", "new": "uno"}]}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.NUM_TO_TEXT],
        _SLOTS[ModificationType.NUM_TO_TEXT],
        stub,
        ModificationType.NUM_TO_TEXT,
    )
    assert result.skipped is not None
    assert "missing_key: 'numerals'" in (result.skipped.reason or "")


# ---------------------------------------------------------------------------
# 8. Validator: original/new/preserves_meaning types
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mtype",
    (
        ModificationType.PARAPHRASE,
        ModificationType.EXPANSION,
        ModificationType.COMPRESSION,
        ModificationType.REORDER,
    ),
)
def test_validate_original_new_preserves_happy(mtype):
    payload = {
        "original": "before",
        "new": "after",
        "preserves_meaning": True,
    }
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(_TEMPLATES[mtype], _SLOTS[mtype], stub, mtype)
    assert result.payload == payload
    assert result.skipped is None


def test_validate_original_new_preserves_rejects_int_bool():
    """`preserves_meaning=1` must be rejected (bool subclasses int, but
    the validator checks bool directly)."""
    stub = _StubLLMClient([
        '{"original": "a", "new": "b", "preserves_meaning": 1}'
    ])
    result = propose_variant(
        _TEMPLATES[ModificationType.PARAPHRASE],
        _SLOTS[ModificationType.PARAPHRASE],
        stub,
        ModificationType.PARAPHRASE,
    )
    assert result.skipped is not None
    reason = result.skipped.reason or ""
    assert "preserves_meaning_not_bool" in reason
    assert "type=int" in reason


def test_validate_original_new_preserves_missing_keys():
    stub = _StubLLMClient(['{"original": "a", "new": "b"}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.PARAPHRASE],
        _SLOTS[ModificationType.PARAPHRASE],
        stub,
        ModificationType.PARAPHRASE,
    )
    assert result.skipped is not None
    assert "missing_key: 'preserves_meaning'" in (result.skipped.reason or "")


# ---------------------------------------------------------------------------
# 9. Validator: omission shape
# ---------------------------------------------------------------------------

def test_validate_omission_happy():
    payload = {"original": "X $A Y $N Z", "new": "X $A Y Z", "omitted_var": "N"}
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[ModificationType.OMISSION],
        _SLOTS[ModificationType.OMISSION],
        stub,
        ModificationType.OMISSION,
    )
    assert result.payload == payload
    assert result.skipped is None


@pytest.mark.parametrize("missing", ["original", "new", "omitted_var"])
def test_validate_omission_rejects_missing_key(missing):
    payload = {"original": "X", "new": "Y", "omitted_var": "N"}
    del payload[missing]
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[ModificationType.OMISSION],
        _SLOTS[ModificationType.OMISSION],
        stub,
        ModificationType.OMISSION,
    )
    assert result.skipped is not None
    assert f"missing_key: {missing!r}" in (result.skipped.reason or "")


# ---------------------------------------------------------------------------
# 10. Validator: new_param shape + length bound
# ---------------------------------------------------------------------------

def test_validate_new_param_happy():
    payload = {
        "new_axis_label": "TIPO DE ACABADO",
        "values": [
            {"label": "a", "value": "rugoso"},
            {"label": "b", "value": "liso"},
        ],
        "var_definition": '$X = "rugoso" * (%G=a) + "liso" * (%G=b)',
        "template_patch": ", con acabado $X",
    }
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[ModificationType.NEW_PARAM],
        _SLOTS[ModificationType.NEW_PARAM],
        stub,
        ModificationType.NEW_PARAM,
    )
    assert result.payload == payload
    assert result.skipped is None


@pytest.mark.parametrize("n", [0, 1, 6, 7])
def test_validate_new_param_rejects_out_of_range_lengths(n):
    payload = {
        "new_axis_label": "X",
        "values": [
            {"label": chr(ord("a") + i), "value": f"v{i}"} for i in range(n)
        ],
        "var_definition": "$X = ...",
        "template_patch": "...",
    }
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[ModificationType.NEW_PARAM],
        _SLOTS[ModificationType.NEW_PARAM],
        stub,
        ModificationType.NEW_PARAM,
    )
    assert result.skipped is not None
    reason = result.skipped.reason or ""
    assert "values_out_of_range" in reason
    assert f"len={n}" in reason


def test_validate_new_param_rejects_wrong_inner_shape():
    payload = {
        "new_axis_label": "X",
        "values": [{"label": "a"}, {"label": "b"}],  # missing 'value'
        "var_definition": "$X = ...",
        "template_patch": "...",
    }
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[ModificationType.NEW_PARAM],
        _SLOTS[ModificationType.NEW_PARAM],
        stub,
        ModificationType.NEW_PARAM,
    )
    assert result.skipped is not None
    assert "values[0]_missing_key: 'value'" in (result.skipped.reason or "")


def test_validate_new_param_rejects_missing_top_keys():
    payload = {
        "new_axis_label": "X",
        "values": [{"label": "a", "value": "v"}, {"label": "b", "value": "v2"}],
        # missing var_definition + template_patch
    }
    stub = _StubLLMClient([json.dumps(payload)])
    result = propose_variant(
        _TEMPLATES[ModificationType.NEW_PARAM],
        _SLOTS[ModificationType.NEW_PARAM],
        stub,
        ModificationType.NEW_PARAM,
    )
    assert result.skipped is not None
    reason = result.skipped.reason or ""
    assert "missing_key:" in reason


# ---------------------------------------------------------------------------
# 11. raw_responses propagation + retry knob
# ---------------------------------------------------------------------------

def test_raw_responses_propagate_from_c2_single_success():
    stub = _StubLLMClient([
        json.dumps(_PAYLOADS[ModificationType.SYNONYM_LABEL])
    ])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert len(result.raw_responses) == 1


def test_raw_responses_propagate_from_c2_retry_success():
    payload_json = json.dumps(_PAYLOADS[ModificationType.SYNONYM_LABEL])
    stub = _StubLLMClient(["bad first response", payload_json])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert result.skipped is None
    assert len(result.raw_responses) == 2
    assert result.raw_responses[0] == "bad first response"
    assert result.raw_responses[1] == payload_json


def test_retry_once_false_short_circuits():
    stub = _StubLLMClient(["malformed"])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
        retry_once=False,
    )
    assert result.payload is None
    assert result.skipped is not None
    assert result.skipped.reason is not None
    assert result.skipped.reason.startswith(
        "malformed_llm_response_after_retry: "
    )
    assert len(result.raw_responses) == 1
    assert len(stub.calls) == 1


# ---------------------------------------------------------------------------
# 12. Never-raises contract on LLM-side failures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "stub_response",
    [
        "garbage",
        "<html>",
        "{",
        "}",
        " ",
        "[unterminated",
        '{"unrelated": "data"}',
        '{"synonyms": []}',
        '{"synonyms": [{"original": 1, "new": "x"}]}',
    ],
)
def test_propose_variant_does_not_raise_on_any_llm_failure(stub_response):
    stub = _StubLLMClient([stub_response, stub_response])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert isinstance(result, VariantProposal)
    assert result.payload is None
    assert result.skipped is not None


# ---------------------------------------------------------------------------
# 13. VariantProposal immutability + equality
# ---------------------------------------------------------------------------

def test_variant_proposal_is_frozen():
    stub = _StubLLMClient([
        json.dumps(_PAYLOADS[ModificationType.SYNONYM_LABEL])
    ])
    result = propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.payload = {"k": "v"}  # type: ignore[misc]


def test_variant_proposal_equality():
    p1 = VariantProposal(
        payload={"k": "v"},
        raw_responses=('{"k": "v"}',),
        skipped=None,
    )
    p2 = VariantProposal(
        payload={"k": "v"},
        raw_responses=('{"k": "v"}',),
        skipped=None,
    )
    assert p1 == p2


# ---------------------------------------------------------------------------
# 14. Module hygiene
# ---------------------------------------------------------------------------

def test_module_has_no_side_effects_at_import():
    import synthetic.variant_proposer as mod

    reloaded = importlib.reload(mod)
    assert reloaded.propose_variant is mod.propose_variant
    assert reloaded.VariantProposal is mod.VariantProposal
    assert reloaded.EXPECTED_SLOTS is mod.EXPECTED_SLOTS


# ---------------------------------------------------------------------------
# 15. Rendered prompt passthrough + skip-record other fields
# ---------------------------------------------------------------------------

def test_rendered_prompt_passed_to_client_verbatim():
    """Whatever the renderer produces is exactly what the client sees."""
    stub = _StubLLMClient([
        json.dumps(_PAYLOADS[ModificationType.SYNONYM_LABEL])
    ])
    propose_variant(
        _TEMPLATES[ModificationType.SYNONYM_LABEL],
        _SLOTS[ModificationType.SYNONYM_LABEL],
        stub,
        ModificationType.SYNONYM_LABEL,
    )
    assert len(stub.calls) == 1
    rendered = stub.calls[0]
    # Every slot value appears exactly once in the rendered output:
    for v in _SLOTS[ModificationType.SYNONYM_LABEL].values():
        assert rendered.count(v) == 1, (
            f"slot value {v!r} appears {rendered.count(v)} times (expected 1)"
        )
    # JSON literal appears exactly once:
    assert rendered.count('Responde SOLO con un JSON:') == 1


def test_skip_record_other_fields_are_none_on_validation_failure():
    stub = _StubLLMClient(['{"unrelated": "data"}'])
    result = propose_variant(
        _TEMPLATES[ModificationType.PARAPHRASE],
        _SLOTS[ModificationType.PARAPHRASE],
        stub,
        ModificationType.PARAPHRASE,
    )
    skip = result.skipped
    assert skip is not None
    assert skip.param is None
    assert skip.var is None
    assert skip.condition is None
    assert skip.field is None
    assert skip.value is None
    assert skip.original is None
    assert skip.new is None
