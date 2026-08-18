"""PD `new_param` mutator — adds a parameter axis plus optional
text-variable and template-patch side effects.

Receives a stage-2 JSON dict (already deep-copied by the upstream
`apply_new_param` orchestrator in `mutator.py`), the target `concept_key`,
and a single rule dict. The worker installs the new axis under
`concept["parameters"][rule["param"]]`, optionally registers a new `$VAR`
formula under `concept["text_variables"][rule["text_variable"]["var"]]`,
and optionally applies one or more substring patches to
`concept["resumen"]` / `concept["texto"]`. Returns the dict together with
a one-element `[Modification]` log.

Diverges from L1/L2/L3 in three ways: it `add`s rather than `replace`s
(collisions raise); it may touch multiple blocks of the same concept
within one rule; and there is only one wrapper (no per-type fan-out)
because PD has exactly one `ModificationType`.
"""

from __future__ import annotations

from .taxonomy import Layer, Modification, ModificationType


_ACCEPTED_FIELDS = ("resumen", "texto")


def apply_new_param(
    stage_json: dict,
    concept_key: str,
    rule: dict,
) -> tuple[dict, list[Modification]]:
    if concept_key not in stage_json:
        raise KeyError(f"concept_key {concept_key!r} not found in stage_json")
    concept = stage_json[concept_key]

    parameters = concept.get("parameters")
    if not isinstance(parameters, dict):
        raise KeyError(
            f"concept {concept_key!r} has no parameters block"
        )

    param = rule.get("param")
    if not isinstance(param, str) or param == "":
        raise ValueError(
            "rule for new_param requires a non-empty 'param' (string) field"
        )

    label = rule.get("label")
    if not isinstance(label, str) or label == "":
        raise ValueError(
            "rule for new_param requires a non-empty 'label' (string) field"
        )

    values = rule.get("values")
    if not isinstance(values, list) or len(values) == 0:
        raise ValueError(
            "rule for new_param requires a non-empty 'values' (list) field"
        )
    seen_labels: set[str] = set()
    for entry in values:
        if not isinstance(entry, dict):
            raise ValueError(
                "rule for new_param 'values' entries must be dicts "
                "with 'label' and 'value' string fields"
            )
        entry_label = entry.get("label")
        entry_value = entry.get("value")
        if (
            not isinstance(entry_label, str) or entry_label == ""
            or not isinstance(entry_value, str) or entry_value == ""
        ):
            raise ValueError(
                "rule for new_param 'values' entries must have non-empty "
                "string 'label' and 'value' fields"
            )
        if entry_label in seen_labels:
            raise ValueError(
                f"rule for new_param has duplicated value labels "
                f"({entry_label!r}); value labels must be unique within "
                f"the axis"
            )
        seen_labels.add(entry_label)

    if param in parameters:
        raise ValueError(
            f"param key {param!r} already exists on concept "
            f"{concept_key!r}; new_param cannot replace an existing axis"
        )

    new_var: str | None = None
    if "text_variable" in rule:
        tv = rule["text_variable"]
        if not isinstance(tv, dict):
            raise ValueError(
                "rule for new_param 'text_variable' must be a dict with "
                "'var' and 'formula' string fields"
            )
        var = tv.get("var")
        formula = tv.get("formula")
        if not isinstance(var, str) or var == "":
            raise ValueError(
                "rule for new_param 'text_variable' requires a non-empty "
                "'var' (string) field"
            )
        if not isinstance(formula, str) or formula == "":
            raise ValueError(
                "rule for new_param 'text_variable' requires a non-empty "
                "'formula' (string) field"
            )
        text_variables = concept.get("text_variables")
        if not isinstance(text_variables, dict):
            text_variables = {}
            concept["text_variables"] = text_variables
        if var in text_variables:
            raise ValueError(
                f"var key {var!r} already exists on concept "
                f"{concept_key!r}; new_param cannot overwrite an existing "
                f"text variable"
            )
        new_var = var

    patches = rule.get("template_patches")
    if patches is not None and not isinstance(patches, list):
        raise ValueError(
            "rule for new_param 'template_patches' must be a list of "
            "{'field', 'original', 'new'} dicts"
        )

    if patches:
        for patch in patches:
            if not isinstance(patch, dict):
                raise ValueError(
                    "rule for new_param 'template_patches' entries must "
                    "be dicts with 'field', 'original', 'new' fields"
                )
            raw_field = patch.get("field")
            if not isinstance(raw_field, str):
                raise ValueError(
                    "rule for new_param template_patch requires a string "
                    "'field' naming 'RESUMEN' or 'TEXTO'"
                )
            field_lower = raw_field.lower()
            if field_lower not in _ACCEPTED_FIELDS:
                raise ValueError(
                    f"field {raw_field!r} is not 'RESUMEN' or 'TEXTO'"
                )
            original = patch.get("original")
            new = patch.get("new")
            if (
                not isinstance(original, str) or original == ""
                or not isinstance(new, str)
            ):
                raise ValueError(
                    "rule for new_param template_patch requires non-empty "
                    "'original' and 'new' (string) fields"
                )
            template = concept.get(field_lower)
            if not isinstance(template, str):
                raise KeyError(
                    f"concept {concept_key!r} has no {field_lower!r} template"
                )
            count = template.count(original)
            if count == 0:
                raise KeyError(
                    f"original {original!r} not found in {field_lower!r} "
                    f"of concept {concept_key!r}"
                )
            if count > 1:
                raise ValueError(
                    f"original {original!r} matches {count} substrings in "
                    f"{field_lower!r} of concept {concept_key!r}; rule "
                    f"author must supply a sufficiently-disambiguating "
                    f"substring"
                )
            concept[field_lower] = template.replace(original, new, 1)

    parameters[param] = {"label": label, "values": list(values)}

    if new_var is not None:
        concept["text_variables"][new_var] = rule["text_variable"]["formula"]

    return stage_json, [
        Modification(
            type=ModificationType.NEW_PARAM,
            layer=Layer.PARAM_DEFINITION,
            param=param,
            new=label,
            var=new_var,
            status="applied",
        )
    ]
