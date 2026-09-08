import json

import pytest

from synthetic.taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER


def test_modification_type_has_13_members():
    # Sprint 36: TEMPLATE_PARAPHRASE joined the taxonomy (13th type).
    assert len(list(ModificationType)) == 13


def test_modification_type_value_roundtrip():
    assert ModificationType("synonym_label") is ModificationType.SYNONYM_LABEL


def test_layer_has_4_members():
    assert len(list(Layer)) == 4


def test_modification_serialisation_roundtrip_via_json():
    original = Modification(
        type=ModificationType.PARAPHRASE,
        layer=Layer.TEXT_VARIABLE,
        var="$I",
        condition="%B=a",
        original="en cualquier clase de terreno, excepto roca",
        new="terreno estándar",
        status="applied",
    )
    payload = json.loads(json.dumps(original.to_dict()))
    restored = Modification.from_dict(payload)
    assert restored == original


def test_modification_skipped_reason_roundtrip():
    skipped = Modification(
        type=ModificationType.UNIT_CONVERSION,
        layer=Layer.PARAM_VALUE,
        param="A",
        status="skipped",
        reason="non-numeric value",
    )
    restored = Modification.from_dict(json.loads(json.dumps(skipped.to_dict())))
    assert restored == skipped


def test_to_dict_uses_string_values_for_enums():
    mod = Modification(type=ModificationType.OMISSION, layer=Layer.TEMPLATE, field="RESUMEN")
    d = mod.to_dict()
    assert d["type"] == "omission"
    assert d["layer"] == "template"
    json.dumps(d)


def test_to_dict_omits_none_fields():
    mod = Modification(type=ModificationType.OMISSION, layer=Layer.TEMPLATE)
    d = mod.to_dict()
    assert set(d) == {"type", "layer"}


def test_type_to_layer_covers_all_types():
    assert set(TYPE_TO_LAYER) == set(ModificationType)


def test_type_to_layer_uses_all_layers():
    assert set(TYPE_TO_LAYER.values()) == set(Layer)
