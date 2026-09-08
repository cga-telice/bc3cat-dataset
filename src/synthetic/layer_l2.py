"""L2 `text_variable` mutators — three pure fragment-replacement transformers.

Each public function receives a stage-3 JSON dict (already deep-copied by the
upstream `apply_l2` orchestrator in `mutator.py`), the target `concept_key`,
and a single rule dict naming `(var, condition)` and carrying the proposed
`new` fragment string. The mutator finds the matching `"FRAG" * (CONDITION)`
segment inside `stage_json[concept_key]["text_variables"][var]`, overwrites
the quoted fragment, and returns the dict together with a one-element
`[Modification]` log.

All three wrappers share the same `_replace_fragment` worker — the mechanics
are identical; the semantics live in the `Modification.type` field set by
each wrapper.
"""

from __future__ import annotations

import re

from .axis_twins import (
    axis_value_collides,
    fragment_collides,
    pair_l2_into_param,
    var_twin,
)
from .taxonomy import Layer, Modification, ModificationType


_FRAGMENT_PAT = re.compile(r'"(?P<frag>[^"]*)"\s*\*\s*\(\s*(?P<cond>[^)]*)\s*\)')


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _replace_fragment(
    stage_json: dict,
    concept_key: str,
    rule: dict,
    mod_type: ModificationType,
) -> tuple[dict, list[Modification]]:
    """Locate (concept, var, condition) and rewrite the matching fragment."""
    if concept_key not in stage_json:
        raise KeyError(f"concept_key {concept_key!r} not found in stage_json")
    concept = stage_json[concept_key]

    text_variables = concept.get("text_variables")
    if not isinstance(text_variables, dict):
        raise KeyError(f"concept {concept_key!r} has no text_variables block")

    raw_var = rule["var"]
    var_key = raw_var[1:] if raw_var.startswith("$") else raw_var
    if var_key not in text_variables:
        raise KeyError(f"var {var_key!r} not found on concept {concept_key!r}")
    entry = text_variables[var_key]

    if isinstance(entry, str):
        elements = [entry]
        was_str = True
    elif isinstance(entry, list):
        if not any(
            isinstance(el, str) and re.search(r"\*\s*\(", el) for el in entry
        ):
            raise ValueError(
                f"var {var_key!r} on concept {concept_key!r} is a lookup-table list "
                f"(no conditional fragments); L2 condition-addressed mutation "
                f"does not apply"
            )
        elements = list(entry)
        was_str = False
    else:
        raise TypeError(
            f"var {var_key!r} on concept {concept_key!r} has unsupported "
            f"shape {type(entry).__name__}"
        )

    condition = rule.get("condition")
    new_fragment = rule.get("new")
    if (
        not isinstance(condition, str)
        or condition == ""
        or not isinstance(new_fragment, str)
        or new_fragment == ""
    ):
        raise ValueError(
            f"rule for {mod_type.value} requires non-empty 'condition' and "
            f"'new' fields"
        )

    target_norm = _norm(condition)

    hits: list[tuple[int, int, re.Match[str]]] = []
    for idx, element in enumerate(elements):
        if not isinstance(element, str):
            continue
        for m in _FRAGMENT_PAT.finditer(element):
            if _norm(m.group("cond")) == target_norm:
                hits.append((idx, m.start(), m))

    if not hits:
        raise KeyError(
            f"condition {condition!r} not found on var {var_key!r} of concept "
            f"{concept_key!r}"
        )
    if len(hits) > 1:
        locations = ", ".join(
            f"element[{i}]@{start}" for (i, start, _) in hits
        )
        raise ValueError(
            f"condition {condition!r} matches {len(hits)} fragments on var "
            f"{var_key!r} of concept {concept_key!r} (catalog corruption): "
            f"{locations}"
        )

    idx, _start, match = hits[0]
    element = elements[idx]
    original = match.group("frag")
    as_written_cond = match.group("cond")

    # Sprint 34: pre-flight collision checks (primary + paired sides).
    # See layer_l1 for rationale.
    if fragment_collides(
        concept, var=var_key, exclude_condition=as_written_cond,
        candidate=new_fragment,
    ):
        return stage_json, [
            Modification(
                type=mod_type, layer=Layer.TEXT_VARIABLE,
                var=var_key, condition=as_written_cond,
                original=original, new=new_fragment,
                status="skipped",
                reason=(
                    f"collision_with_sibling_fragment: "
                    f"'{new_fragment}' already used on ${var_key}"
                ),
            )
        ]
    twin_axis = var_twin(concept, var_key)
    if twin_axis is not None:
        # Derive the value_label from the condition, e.g. %B=a → "a"
        import re as _re
        cond_m = _re.search(r"%[A-Z]\s*=+\s*\"?([A-Za-z0-9]+)\"?", as_written_cond)
        if cond_m is not None:
            paired_label = cond_m.group(1)
            if axis_value_collides(
                concept, param=twin_axis, exclude_value_label=paired_label,
                candidate=new_fragment,
            ):
                return stage_json, [
                    Modification(
                        type=mod_type, layer=Layer.TEXT_VARIABLE,
                        var=var_key, condition=as_written_cond,
                        original=original, new=new_fragment,
                        status="skipped",
                        reason=(
                            f"collision_with_sibling_axis_value_on_twin:"
                            f" '{new_fragment}' already used on axis {twin_axis!r}"
                        ),
                    )
                ]

    replacement = f'"{new_fragment}" * ({as_written_cond})'
    new_element = element[: match.start()] + replacement + element[match.end():]
    elements[idx] = new_element

    if was_str:
        text_variables[var_key] = elements[0]
    else:
        text_variables[var_key] = elements

    log: list[Modification] = [
        Modification(
            type=mod_type,
            layer=Layer.TEXT_VARIABLE,
            var=var_key,
            condition=as_written_cond,
            original=original,
            new=new_fragment,
            status="applied",
        )
    ]

    # Sprint 31: if this text-variable is indexed-referenced from a template
    # (`$L(%B)`), it has a twin parameter axis whose value entry duplicates
    # the same label. Carry the L2 rewrite into that value so `texto`'s raw
    # `$B` and `resumen`'s `$L(%B)` stay in sync. Silently skipped when the
    # var has no twin or the current value has diverged from the fragment.
    pair = pair_l2_into_param(
        concept,
        var=var_key,
        condition=as_written_cond,
        original=original,
        new=new_fragment,
    )
    if pair is not None:
        log.append(
            Modification(
                type=mod_type,
                layer=Layer.PARAM_VALUE,
                param=pair["param"],
                value=pair["value_label"],
                original=pair["original"],
                new=pair["new"],
                status="paired",
                reason=f"twin_of_var:{var_key}",
            )
        )

    return stage_json, log


def apply_paraphrase(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_fragment(stage_json, concept_key, rule, ModificationType.PARAPHRASE)


def apply_expansion(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_fragment(stage_json, concept_key, rule, ModificationType.EXPANSION)


def apply_compression(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_fragment(stage_json, concept_key, rule, ModificationType.COMPRESSION)
