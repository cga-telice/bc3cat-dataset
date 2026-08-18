"""Contract tests for `synthetic.slot_extractor`.

Pins the per-type enumerate/extract contract against the
`variant_proposer.EXPECTED_SLOTS` audit and the L1/L2/L3/PD slot
shapes spec'd in Sprint 15.
"""

from __future__ import annotations

import copy
import importlib

import pytest

from synthetic import slot_extractor
from synthetic.slot_extractor import (
    MIN_COMPRESSION_WORDS,
    concept_resumen,
    enumerate_targets,
    extract_slots,
    value_applies,
)
from synthetic.taxonomy import ModificationType
from synthetic.variant_proposer import EXPECTED_SLOTS


_L1_TYPES = (
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
)
_L2_TYPES = (
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
)


_STAGE_JSON_FIXTURE = {
    "OEB020aa": {
        "parent_key": "OEB020$",
        "parameters": {
            # Sprint 31: axis A gives the fixture a numeric axis so num_to_text
            # has at least one applicable target; B carries an abbreviation
            # (PVC) so abbrev/code_expansion apply; D carries a unit (m) so
            # unit_conversion/unit_expansion apply. Nothing about the L2/L3
            # tests depends on axis A.
            "A": {
                "label": "NÚMERO DE TUBOS",
                "values": [
                    {"label": "a", "value": "1"},
                    {"label": "b", "value": "2"},
                ],
            },
            "B": {
                "label": "TIPO DE TERRENO",
                "values": [
                    {"label": "a", "value": "Normal"},
                    {"label": "b", "value": "PVC"},
                ],
            },
            "D": {
                "label": "PROFUNDIDAD",
                "values": [
                    {"label": "a", "value": "Hasta 1 m"},
                    {"label": "b", "value": "Más de 1 m"},
                ],
            },
        },
        "text_variables": {
            "K": '"normal" * (%B=a) + "PVC" * (%B=b)',
            "L": '"hasta 1 m" * (%D=a) + "más de 1 m" * (%D=b)',
            "N": '"por metro lineal" * (%B=a)',
        },
        "resumen": "Canalización para terreno normal hasta 1 m",
        "texto": (
            "Canalización para terreno $K de profundidad $L, incluso $N por metro"
        ),
    },
}


def _fixture() -> dict:
    return copy.deepcopy(_STAGE_JSON_FIXTURE)


# ---- public surface ----------------------------------------------------

def test_module_exposes_public_surface():
    assert callable(slot_extractor.concept_resumen)
    assert callable(slot_extractor.enumerate_targets)
    assert callable(slot_extractor.extract_slots)


# ---- concept_resumen ---------------------------------------------------

def test_concept_resumen_lowercase_key():
    stage = _fixture()
    assert concept_resumen(stage, "OEB020aa") == stage["OEB020aa"]["resumen"]


def test_concept_resumen_uppercase_key():
    stage = {"X": {"RESUMEN": "Algo"}}
    assert concept_resumen(stage, "X") == "Algo"


def test_concept_resumen_missing_raises_keyerror():
    stage = {"X": {"parent_key": "x$"}}
    with pytest.raises(KeyError):
        concept_resumen(stage, "X")


# ---- enumerate_targets -------------------------------------------------

@pytest.mark.parametrize("mtype,expected", [
    (ModificationType.SYNONYM_LABEL, ["B"]),           # textual, digit-free values → B only (D carries "1 m", A is numeric)
    (ModificationType.NUM_TO_TEXT, ["A"]),             # numeric values only on A
    (ModificationType.UNIT_CONVERSION, ["D"]),         # "m" unit token on D
    (ModificationType.UNIT_EXPANSION, ["D"]),
    (ModificationType.ABBREV_EXPANSION, ["B"]),        # "PVC" on B
    (ModificationType.CODE_EXPANSION, ["B"]),
])
def test_enumerate_targets_l1_yields_only_applicable_axes(mtype, expected):
    # Sprint 31: enumerate_targets gates L1 axis emission by applicability.
    # Type-appropriate axes are yielded; inapplicable axes are skipped.
    stage = _fixture()
    assert list(enumerate_targets(stage, "OEB020aa", mtype)) == expected


def test_enumerate_targets_l2_yields_sorted_var_condition_pairs():
    stage = _fixture()
    got = list(
        enumerate_targets(stage, "OEB020aa", ModificationType.PARAPHRASE),
    )
    assert got == [
        ("K", "%B=a"),
        ("K", "%B=b"),
        ("L", "%D=a"),
        ("L", "%D=b"),
        ("N", "%B=a"),
    ]


def test_enumerate_targets_l3_omission_yields_field_var_pairs():
    stage = _fixture()
    got = list(
        enumerate_targets(stage, "OEB020aa", ModificationType.OMISSION),
    )
    # RESUMEN has no $X tokens; TEXTO has $K $L $N — sorted.
    assert got == [
        ("TEXTO", "$K"),
        ("TEXTO", "$L"),
        ("TEXTO", "$N"),
    ]


def test_enumerate_targets_l3_reorder_yields_fields_with_text():
    stage = _fixture()
    got = list(
        enumerate_targets(stage, "OEB020aa", ModificationType.REORDER),
    )
    assert got == ["RESUMEN", "TEXTO"]


def test_enumerate_targets_l3_reorder_skips_empty_fields():
    stage = {"X": {"resumen": "", "texto": "hola $A"}}
    got = list(enumerate_targets(stage, "X", ModificationType.REORDER))
    assert got == ["TEXTO"]


def test_enumerate_targets_new_param_yields_single_none():
    stage = _fixture()
    got = list(
        enumerate_targets(stage, "OEB020aa", ModificationType.NEW_PARAM),
    )
    assert got == [None]


# ---- extract_slots: round-trip against EXPECTED_SLOTS ------------------

@pytest.mark.parametrize("mtype", list(ModificationType))
def test_extract_slots_matches_expected_slots_per_type(mtype):
    """For every mtype, the first emitted target produces a slots dict
    whose keys match `EXPECTED_SLOTS[mtype]` exactly. Binding
    round-trip with Sprint 14.
    """
    stage = _fixture()
    targets = list(enumerate_targets(stage, "OEB020aa", mtype))
    assert targets, f"no targets for {mtype!r}"
    slots = extract_slots(stage, "OEB020aa", mtype, targets[0])
    assert set(slots.keys()) == EXPECTED_SLOTS[mtype]


def test_extract_slots_l1_value_list_format():
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.SYNONYM_LABEL, "B",
    )
    assert slots["axis_label"] == "TIPO DE TERRENO"
    assert slots["value_list"] == "a: Normal; b: PVC"


def test_extract_slots_l2_fragment_picks_correct_clause():
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.PARAPHRASE, ("K", "%B=a"),
    )
    assert slots == {
        "concept": stage["OEB020aa"]["resumen"],
        "var_key": "K",
        "fragment": "normal",
        "condition": "%B=a",
        # Sprint 34: sibling_fragments carries the OTHER fragments of the
        # same text-variable so the prompt can enforce no-collision.
        "sibling_fragments": "%B=b: PVC",
    }


def test_extract_slots_l2_sibling_fragments_multi_condition():
    """Sibling list preserves formula order and excludes the target."""
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.COMPRESSION, ("L", "%D=a"),
    )
    assert slots["sibling_fragments"] == "%D=b: más de 1 m"


def test_extract_slots_l2_sibling_fragments_empty_when_single_clause():
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.EXPANSION, ("N", "%B=a"),
    )
    # N has only one clause → no siblings
    assert slots["sibling_fragments"] == "(ninguno)"


def test_extract_slots_omission_axis_label_best_effort_known_binding():
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.OMISSION, ("TEXTO", "$N"),
    )
    # $N's formula references %B=a; B's label is TIPO DE TERRENO.
    assert slots["var_to_omit"] == "N"
    assert slots["axis_label"] == "TIPO DE TERRENO"


def test_extract_slots_omission_axis_label_empty_when_no_formula():
    stage = {
        "X": {
            "parent_key": "X$",
            "resumen": "Algo $Z aqui",
            "texto": "Algo $Z aqui",
            "parameters": {},
            "text_variables": {},
        },
    }
    slots = extract_slots(
        stage, "X", ModificationType.OMISSION, ("TEXTO", "$Z"),
    )
    assert slots["axis_label"] == ""


def test_extract_slots_reorder_constituents_format():
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.REORDER, "TEXTO",
    )
    assert slots["constituents"] == "$K; $L; $N"
    assert slots["template"] == stage["OEB020aa"]["texto"]


def test_extract_slots_new_param_allowlist_is_placeholder_for_now():
    stage = _fixture()
    slots = extract_slots(
        stage, "OEB020aa", ModificationType.NEW_PARAM, None,
    )
    assert slots["allowlist"] == "[]"
    assert slots["existing_axes_with_labels"] == (
        "A: NÚMERO DE TUBOS; B: TIPO DE TERRENO; D: PROFUNDIDAD"
    )


def test_extract_slots_l2_unknown_condition_raises():
    stage = _fixture()
    with pytest.raises(KeyError):
        extract_slots(
            stage, "OEB020aa", ModificationType.PARAPHRASE,
            ("K", "%B=zzz"),
        )


# ---- Sprint 31: axis applicability classifier --------------------------

_AXIS_A_NUMERIC = {"values": [{"label": "a", "value": "1"}, {"label": "b", "value": "24"}]}
_AXIS_B_TEXT_LABELS = {"values": [{"label": "a", "value": "Diurno"}, {"label": "b", "value": "Nocturno"}]}
_AXIS_C_TIME_UNIT = {"values": [{"label": "a", "value": "i >= 5 horas"}, {"label": "b", "value": "3 <= i < 5 horas"}]}
_AXIS_D_TEXT_ONLY = {"values": [{"label": "a", "value": "Volumen relevante"}, {"label": "b", "value": "Volumen escaso"}]}
_AXIS_ABBREV = {"values": [{"label": "a", "value": "PVC"}, {"label": "b", "value": "PE"}]}
_AXIS_CODE = {"values": [{"label": "a", "value": "HE-20"}, {"label": "b", "value": "HA-25"}]}


@pytest.mark.parametrize("block,mtype,expected", [
    # OEB070 axis A — pure numeric count
    (_AXIS_A_NUMERIC, ModificationType.NUM_TO_TEXT, True),
    (_AXIS_A_NUMERIC, ModificationType.SYNONYM_LABEL, False),
    (_AXIS_A_NUMERIC, ModificationType.UNIT_EXPANSION, False),
    (_AXIS_A_NUMERIC, ModificationType.ABBREV_EXPANSION, False),
    (_AXIS_A_NUMERIC, ModificationType.CODE_EXPANSION, False),
    # OEB070 axis B — text labels only
    (_AXIS_B_TEXT_LABELS, ModificationType.SYNONYM_LABEL, True),
    (_AXIS_B_TEXT_LABELS, ModificationType.NUM_TO_TEXT, False),
    (_AXIS_B_TEXT_LABELS, ModificationType.UNIT_EXPANSION, False),
    (_AXIS_B_TEXT_LABELS, ModificationType.ABBREV_EXPANSION, False),
    (_AXIS_B_TEXT_LABELS, ModificationType.CODE_EXPANSION, False),
    # OEB070 axis C — time bands with "horas" unit
    (_AXIS_C_TIME_UNIT, ModificationType.SYNONYM_LABEL, False),  # 38.5: digit-bearing bands are not synonym targets
    (_AXIS_C_TIME_UNIT, ModificationType.UNIT_CONVERSION, True),
    (_AXIS_C_TIME_UNIT, ModificationType.UNIT_EXPANSION, True),
    (_AXIS_C_TIME_UNIT, ModificationType.NUM_TO_TEXT, False),
    (_AXIS_C_TIME_UNIT, ModificationType.ABBREV_EXPANSION, False),
    # OEB070 axis D — pure text labels
    (_AXIS_D_TEXT_ONLY, ModificationType.SYNONYM_LABEL, True),
    (_AXIS_D_TEXT_ONLY, ModificationType.UNIT_EXPANSION, False),
    (_AXIS_D_TEXT_ONLY, ModificationType.ABBREV_EXPANSION, False),
    (_AXIS_D_TEXT_ONLY, ModificationType.CODE_EXPANSION, False),
    # material abbreviations
    (_AXIS_ABBREV, ModificationType.ABBREV_EXPANSION, True),
    (_AXIS_ABBREV, ModificationType.CODE_EXPANSION, True),
    (_AXIS_ABBREV, ModificationType.NUM_TO_TEXT, False),
    (_AXIS_ABBREV, ModificationType.UNIT_EXPANSION, False),
    # domain codes like HE-20
    (_AXIS_CODE, ModificationType.CODE_EXPANSION, True),
    (_AXIS_CODE, ModificationType.ABBREV_EXPANSION, True),
])
def test_axis_applies_classifier(block, mtype, expected):
    assert slot_extractor._axis_applies(block, mtype) is expected


def test_axis_applies_empty_values_is_false():
    assert slot_extractor._axis_applies({"values": []}, ModificationType.SYNONYM_LABEL) is False
    assert slot_extractor._axis_applies({}, ModificationType.SYNONYM_LABEL) is False


def test_enumerate_targets_gates_l1_on_oeb070_shaped_stage():
    """Sprint 31 targeting gate — OEB070 shape.

    Regression test for F1-review §4.1: enumerating unit_expansion /
    abbrev_expansion / code_expansion on axis A ("Nº TUBOS") produced
    ungrammatical duplications ("de Un tubo tubo(s)…"). The gate must
    block those axes.
    """
    stage = {
        "OEB070aaaa": {
            "parent_key": "OEB070$",
            "parameters": {
                "A": _AXIS_A_NUMERIC,
                "B": _AXIS_B_TEXT_LABELS,
                "C": _AXIS_C_TIME_UNIT,
                "D": _AXIS_D_TEXT_ONLY,
            },
        },
    }
    def targets(mt):
        return list(enumerate_targets(stage, "OEB070aaaa", mt))

    assert targets(ModificationType.NUM_TO_TEXT) == ["A"]
    assert targets(ModificationType.SYNONYM_LABEL) == ["B", "D"]  # 38.5: axis C is the digit-bearing time band
    assert targets(ModificationType.UNIT_CONVERSION) == ["C"]
    assert targets(ModificationType.UNIT_EXPANSION) == ["C"]
    assert targets(ModificationType.ABBREV_EXPANSION) == []
    assert targets(ModificationType.CODE_EXPANSION) == []


# ---- helper edge cases -------------------------------------------------

def test_parse_l2_formula_unparseable_raises():
    with pytest.raises(ValueError):
        slot_extractor._parse_l2_formula("no fragments here")


def test_field_text_handles_lowercase_only():
    item = {"resumen": "lower", "texto": "tex"}
    assert slot_extractor._field_text(item, "RESUMEN") == "lower"
    assert slot_extractor._field_text(item, "TEXTO") == "tex"


def test_field_text_returns_empty_when_missing():
    assert slot_extractor._field_text({}, "RESUMEN") == ""


# ---- import-time safety ------------------------------------------------

def test_module_has_no_side_effects_at_import():
    importlib.reload(slot_extractor)
    assert callable(slot_extractor.enumerate_targets)
    assert callable(slot_extractor.extract_slots)


# ---- Sprint 38.5: per-value gates -------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("Diurno", True),
    ("Cualquier franja horaria", True),
    ("3 <= i < 5 horas", False),   # numeric band — synonymising drops the numbers
    ("1,10 m", False),
    ("PVC 110 mm", False),
    ("1", False),                  # pure numeric (already excluded pre-38.5)
])
def test_value_applies_synonym_label_rejects_digits(value, expected):
    assert value_applies(value, ModificationType.SYNONYM_LABEL) is expected


def test_value_applies_other_l1_types_unchanged():
    assert value_applies("1", ModificationType.NUM_TO_TEXT)
    assert not value_applies("uno", ModificationType.NUM_TO_TEXT)
    assert value_applies("Hasta 1 m", ModificationType.UNIT_CONVERSION)
    assert value_applies("PVC", ModificationType.ABBREV_EXPANSION)
    assert value_applies("anything", ModificationType.PARAPHRASE)
    assert value_applies("36mm", ModificationType.UNIT_EXPANSION)          # digits + unit must survive
    assert value_applies("HE-20", ModificationType.CODE_EXPANSION)          # digit-bearing code stays a code target
    assert not value_applies("HE-20", ModificationType.SYNONYM_LABEL)       # ...but is not a synonym target


def test_enumerate_targets_compression_skips_short_fragments():
    # Fixture fragments: K "normal"(1) "PVC"(1); L "hasta 1 m"(3) "más de 1 m"(4); N "por metro lineal"(3)
    assert MIN_COMPRESSION_WORDS == 4
    stage = _fixture()
    got = list(enumerate_targets(stage, "OEB020aa", ModificationType.COMPRESSION))
    assert got == [("L", "%D=b")]
