"""L1 `param_value` mutators — six pure value-replacement transformers.

Each public function receives a stage-2 JSON dict (already deep-copied by the
upstream `apply_l1` orchestrator in `mutator.py`), the target `concept_key`, and
a single rule dict naming `(param, value_label)` and carrying the proposed `new`
string. The mutator overwrites the matching value entry in place and returns
the dict together with a one-element `[Modification]` log.

All six wrappers share the same `_replace_value` worker — the mechanics are
identical; the semantics live in the `Modification.type` field set by each
wrapper.
"""

from __future__ import annotations

from .axis_twins import (
    axis_twin,
    axis_value_collides,
    fragment_collides,
    pair_l1_into_text_var,
)
from .taxonomy import Layer, Modification, ModificationType


def _replace_value(
    stage_json: dict,
    concept_key: str,
    rule: dict,
    mod_type: ModificationType,
) -> tuple[dict, list[Modification]]:
    """Locate (concept, param, value_label) and rewrite its `value` string."""
    if concept_key not in stage_json:
        raise KeyError(f"concept_key {concept_key!r} not found in stage_json")
    concept = stage_json[concept_key]

    parameters = concept.get("parameters")
    if not isinstance(parameters, dict) or rule["param"] not in parameters:
        raise KeyError(
            f"param {rule['param']!r} not found on concept {concept_key!r}"
        )
    axis = parameters[rule["param"]]

    matches = [
        entry for entry in axis.get("values", [])
        if entry.get("label") == rule["value"]
    ]
    if not matches:
        raise KeyError(
            f"value label {rule['value']!r} not found on param {rule['param']!r}"
        )
    if len(matches) > 1:
        raise ValueError(
            f"value label {rule['value']!r} on param {rule['param']!r} "
            f"matches {len(matches)} entries (catalog corruption)"
        )

    new_value = rule.get("new")
    if not isinstance(new_value, str) or new_value == "":
        raise ValueError(
            f"rule for {mod_type.value} requires a non-empty 'new' field"
        )

    value_entry = matches[0]
    original = value_entry["value"]

    # Sprint 34: pre-flight collision checks (both primary and paired sides).
    # If either side would produce two identical strings on the same
    # (axis, text-var) it makes two leaves render identically, which
    # violates the proposal's Stage-D parameter-preservation contract.
    # Skip cleanly — never leave the mutator in a half-applied state.
    if axis_value_collides(
        concept, param=rule["param"], exclude_value_label=rule["value"],
        candidate=new_value,
    ):
        return stage_json, [
            Modification(
                type=mod_type, layer=Layer.PARAM_VALUE,
                param=rule["param"], value=rule["value"],
                original=original, new=new_value,
                status="skipped",
                reason=(
                    f"collision_with_sibling_axis_value: "
                    f"'{new_value}' already used on axis {rule['param']!r}"
                ),
            )
        ]

    twin_var = axis_twin(concept, rule["param"])
    if twin_var is not None:
        pair_condition = f"%{rule['param']}={rule['value']}"
        if fragment_collides(
            concept, var=twin_var, exclude_condition=pair_condition,
            candidate=new_value,
        ):
            return stage_json, [
                Modification(
                    type=mod_type, layer=Layer.PARAM_VALUE,
                    param=rule["param"], value=rule["value"],
                    original=original, new=new_value,
                    status="skipped",
                    reason=(
                        f"collision_with_sibling_fragment_on_twin_var:"
                        f" '{new_value}' already used on ${twin_var}"
                    ),
                )
            ]

    value_entry["value"] = new_value

    log: list[Modification] = [
        Modification(
            type=mod_type,
            layer=Layer.PARAM_VALUE,
            param=rule["param"],
            value=rule["value"],
            original=original,
            new=new_value,
            status="applied",
        )
    ]

    # Sprint 31: if this axis has a twin text-variable whose fragment still
    # coincides with the pre-mod parameter value, carry the same rewrite into
    # the fragment so `resumen` and `texto` move together. If no twin, or the
    # fragment has already diverged from the value, pairing is silently
    # skipped — single-layer semantics preserved.
    pair = pair_l1_into_text_var(
        concept,
        param=rule["param"],
        value_label=rule["value"],
        original=original,
        new=new_value,
    )
    if pair is not None:
        log.append(
            Modification(
                type=mod_type,
                layer=Layer.TEXT_VARIABLE,
                var=pair["var"],
                condition=pair["condition"],
                original=pair["original"],
                new=pair["new"],
                status="paired",
                reason=f"twin_of_axis:{rule['param']}",
            )
        )

    return stage_json, log


def apply_synonym_label(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_value(stage_json, concept_key, rule, ModificationType.SYNONYM_LABEL)


def apply_num_to_text(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_value(stage_json, concept_key, rule, ModificationType.NUM_TO_TEXT)


def apply_unit_conversion(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_value(stage_json, concept_key, rule, ModificationType.UNIT_CONVERSION)


def apply_unit_expansion(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_value(stage_json, concept_key, rule, ModificationType.UNIT_EXPANSION)


def apply_abbrev_expansion(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_value(stage_json, concept_key, rule, ModificationType.ABBREV_EXPANSION)


def apply_code_expansion(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_value(stage_json, concept_key, rule, ModificationType.CODE_EXPANSION)
