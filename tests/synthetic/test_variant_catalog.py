"""Contract tests for `synthetic.variant_catalog`.

Pins the JSON-per-concept catalog writer's atomic-write contract,
the dataclass immutability invariants, and the
write/read round-trip equality.
"""

from __future__ import annotations

import importlib
import json
import os

import pytest

from synthetic import variant_catalog
from synthetic.taxonomy import Layer, Modification, ModificationType
from synthetic.variant_catalog import (
    ProvenanceRecord,
    VariantCatalogEntry,
    VariantRecord,
    read_catalog_entry,
    write_catalog_entry,
)


def _sample_entry() -> VariantCatalogEntry:
    rule = {
        "type": "synonym_label",
        "param": "B",
        "value": "a",
        "original": "Normal",
        "new": "Estándar",
    }
    skip = Modification(
        type=ModificationType.PARAPHRASE,
        layer=Layer.TEXT_VARIABLE,
        status="skipped",
        reason="schema_validation_failed: missing_key: 'original'",
    )
    return VariantCatalogEntry(
        concept_key="OEB020aa",
        concept_resumen="Canalización para terreno normal hasta 1 m",
        parent_key="OEB020$",
        variants=(
            VariantRecord(
                condition="single_L1_synonym_label",
                modification_type=ModificationType.SYNONYM_LABEL,
                target_id_repr=repr("B"),
                rules=(rule,),
            ),
        ),
        skipped=(skip,),
        provenance=(
            ProvenanceRecord(
                modification_type=ModificationType.SYNONYM_LABEL,
                rendered_prompt="Eres un experto … [prompt]",
                raw_responses=(
                    '{"synonyms": [{"original": "Normal", "new": "Estándar"}]}',
                ),
                validated_payload={
                    "synonyms": [
                        {"original": "Normal", "new": "Estándar"},
                    ],
                },
                skipped=None,
            ),
            ProvenanceRecord(
                modification_type=ModificationType.PARAPHRASE,
                rendered_prompt="Eres un experto … [paraphrase prompt]",
                raw_responses=('{"oops": true}',),
                validated_payload=None,
                skipped=skip,
            ),
        ),
    )


# ---- public surface ----------------------------------------------------

def test_module_exposes_public_surface():
    assert variant_catalog.VariantCatalogEntry is VariantCatalogEntry
    assert variant_catalog.VariantRecord is VariantRecord
    assert variant_catalog.ProvenanceRecord is ProvenanceRecord
    assert callable(variant_catalog.write_catalog_entry)
    assert callable(variant_catalog.read_catalog_entry)


# ---- write_catalog_entry ----------------------------------------------

def test_write_catalog_entry_creates_file_at_expected_path(tmp_path):
    entry = _sample_entry()
    final = write_catalog_entry(entry, tmp_path)
    assert final == tmp_path / "OEB020aa.json"
    assert final.exists()


def test_write_catalog_entry_creates_out_dir_if_missing(tmp_path):
    out = tmp_path / "nested" / "variants"
    assert not out.exists()
    final = write_catalog_entry(_sample_entry(), out)
    assert out.exists()
    assert final.parent == out


def test_write_catalog_entry_round_trips_via_read(tmp_path):
    entry = _sample_entry()
    final = write_catalog_entry(entry, tmp_path)
    back = read_catalog_entry(final)
    assert back == entry


def test_write_catalog_entry_overwrites_existing_file(tmp_path):
    entry = _sample_entry()
    p1 = write_catalog_entry(entry, tmp_path)
    # second write with same concept_key replaces
    entry2 = VariantCatalogEntry(
        concept_key="OEB020aa",
        concept_resumen="otro",
        parent_key="OEB020$",
        variants=(),
        skipped=(),
        provenance=(),
    )
    p2 = write_catalog_entry(entry2, tmp_path)
    assert p1 == p2
    assert read_catalog_entry(p2) == entry2


def test_write_catalog_entry_is_atomic_on_replace_failure(
    tmp_path, monkeypatch,
):
    def boom(src, dst):  # noqa: ARG001
        raise OSError("simulated replace failure")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="simulated"):
        write_catalog_entry(_sample_entry(), tmp_path)
    final = tmp_path / "OEB020aa.json"
    tmp_file = tmp_path / ".OEB020aa.json.tmp"
    # Final path must be absent; tmp may or may not be present per spec.
    assert not final.exists()
    # The tmp file is the only artifact left:
    assert tmp_file.exists()


# ---- JSON-on-disk shape pins ------------------------------------------

def test_catalog_entry_records_modification_type_as_value_string(tmp_path):
    final = write_catalog_entry(_sample_entry(), tmp_path)
    raw = json.loads(final.read_text(encoding="utf-8"))
    assert raw["variants"][0]["modification_type"] == "synonym_label"
    assert raw["provenance"][1]["modification_type"] == "paraphrase"


def test_catalog_entry_on_disk_uses_lists_for_rules_and_raw_responses(
    tmp_path,
):
    final = write_catalog_entry(_sample_entry(), tmp_path)
    raw = json.loads(final.read_text(encoding="utf-8"))
    assert isinstance(raw["variants"][0]["rules"], list)
    assert isinstance(raw["provenance"][0]["raw_responses"], list)


def test_in_memory_records_use_tuples_for_immutability():
    entry = _sample_entry()
    assert isinstance(entry.variants, tuple)
    assert isinstance(entry.variants[0].rules, tuple)
    assert isinstance(entry.provenance[0].raw_responses, tuple)
    assert isinstance(entry.provenance, tuple)
    assert isinstance(entry.skipped, tuple)


# ---- dataclass invariants ---------------------------------------------

def test_dataclasses_are_frozen():
    entry = _sample_entry()
    with pytest.raises(Exception):
        entry.concept_key = "X"  # type: ignore[misc]
    with pytest.raises(Exception):
        entry.variants[0].condition = "X"  # type: ignore[misc]
    with pytest.raises(Exception):
        entry.provenance[0].rendered_prompt = "X"  # type: ignore[misc]


def test_provenance_record_carries_skipped_or_payload_not_both():
    """Structural invariant pin: a successful proposal carries a
    validated_payload (skipped=None); a failed one carries a Modification
    (validated_payload=None). The catalog never observes both populated
    at once.
    """
    entry = _sample_entry()
    for p in entry.provenance:
        # Exactly one of the two slots is populated.
        has_payload = p.validated_payload is not None
        has_skip = p.skipped is not None
        assert has_payload != has_skip


# ---- error paths ------------------------------------------------------

def test_read_catalog_entry_strict_on_malformed_json(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError):
        read_catalog_entry(p)


def test_read_catalog_entry_strict_on_missing_keys(tmp_path):
    p = tmp_path / "incomplete.json"
    p.write_text(
        json.dumps({"concept_key": "X"}), encoding="utf-8",
    )
    with pytest.raises(KeyError):
        read_catalog_entry(p)


def test_skipped_modifications_round_trip(tmp_path):
    entry = _sample_entry()
    final = write_catalog_entry(entry, tmp_path)
    back = read_catalog_entry(final)
    assert back.skipped == entry.skipped
    assert back.skipped[0].reason.startswith("schema_validation_failed: ")


# ---- import-time safety -----------------------------------------------

def test_module_has_no_side_effects_at_import():
    importlib.reload(variant_catalog)
    assert callable(variant_catalog.write_catalog_entry)
