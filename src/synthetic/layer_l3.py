"""L3 `template` mutators — two pure substring-rewrite transformers.

Each public function receives a stage-4 JSON dict (already deep-copied by the
upstream `apply_l3` orchestrator in `mutator.py`), the target `concept_key`,
and a single rule dict naming `(field, original)` and carrying the proposed
`new` substring. The mutator finds the unique occurrence of `original`
inside `stage_json[concept_key][field.lower()]`, overwrites the matched span
with `new`, and returns the dict together with a one-element
`[Modification]` log.

Both wrappers share the same `_replace_substring` worker — the mechanics
are identical; the semantics live in the `Modification.type` field set by
each wrapper.
"""

from __future__ import annotations

from .taxonomy import Layer, Modification, ModificationType


_ACCEPTED_FIELDS = ("resumen", "texto")


def _replace_substring(
    stage_json: dict,
    concept_key: str,
    rule: dict,
    mod_type: ModificationType,
) -> tuple[dict, list[Modification]]:
    """Locate (concept, field, original) and rewrite the matching substring."""
    if concept_key not in stage_json:
        raise KeyError(f"concept_key {concept_key!r} not found in stage_json")
    concept = stage_json[concept_key]

    raw_field = rule.get("field")
    if not isinstance(raw_field, str):
        raise ValueError(
            f"rule for {mod_type.value} requires a string 'field' naming "
            f"'RESUMEN' or 'TEXTO'"
        )
    field_lower = raw_field.lower()
    if field_lower not in _ACCEPTED_FIELDS:
        raise ValueError(
            f"field {raw_field!r} is not 'RESUMEN' or 'TEXTO'"
        )

    template = concept.get(field_lower)
    if not isinstance(template, str):
        raise KeyError(
            f"concept {concept_key!r} has no {field_lower!r} template"
        )

    original = rule.get("original")
    new = rule.get("new")
    if (
        not isinstance(original, str)
        or original == ""
        or not isinstance(new, str)
    ):
        raise ValueError(
            f"rule for {mod_type.value} requires non-empty 'original' "
            f"and 'new' (string) fields"
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
            f"{field_lower!r} of concept {concept_key!r}; rule author must "
            f"supply a sufficiently-disambiguating substring"
        )

    concept[field_lower] = template.replace(original, new, 1)

    return stage_json, [
        Modification(
            type=mod_type,
            layer=Layer.TEMPLATE,
            field=raw_field.upper(),
            original=original,
            new=new,
            status="applied",
        )
    ]


def apply_omission(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_substring(stage_json, concept_key, rule, ModificationType.OMISSION)


def apply_reorder(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    return _replace_substring(stage_json, concept_key, rule, ModificationType.REORDER)


def apply_template_paraphrase(
    stage_json: dict, concept_key: str, rule: dict
) -> tuple[dict, list[Modification]]:
    """L3 full-surface paraphrase: rewrite the RESUMEN or TEXTO template's
    literal text while preserving every `$var` / `$var(%axis)` placeholder.

    The rule dict has the same shape as omission/reorder — `field`,
    `original`, `new` — but `original` is expected to be the full template
    string (the paraphrase replaces the whole field, not a substring). The
    variant_proposer runs `_require_placeholders_preserved` on the payload
    before we get here, so the incoming `new` is already guaranteed to
    carry the same placeholder set as `original`.
    """
    return _replace_substring(
        stage_json, concept_key, rule, ModificationType.TEMPLATE_PARAPHRASE,
    )
