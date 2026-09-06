"""Adapter: render the synthetic seam on bc3param instead of legacy s03-s07.

Maps the frozen variant rule dicts to `bc3param.mutate` edits on a parsed
`Family`, then emits the legacy stage-JSON leaf shape the synthetic pipeline
consumes. Fail-loud: an unmapped rule type or a missing target raises.
"""
from __future__ import annotations

from functools import lru_cache

from bc3param import mutate
from bc3param.fiebdc import Catalog
from utils import config

# Phase 1 pilot source (same file the frozen pilot corpus used).
PILOT_SOURCE = config.RAW_DIR / "BPA_2024_v2_OEB_mod_utf8.txt"

# Rule-type routing (see the discovered schema).
_L2 = {"paraphrase", "compression", "expansion"}
_L1 = {"synonym_label", "num_to_text", "unit_conversion", "unit_expansion",
       "abbrev_expansion", "code_expansion"}
_FIELD = {"reorder", "template_paraphrase", "omission"}


@lru_cache(maxsize=1)
def _catalog() -> Catalog:
    return Catalog.load(PILOT_SOURCE)


def family(concept_key: str):
    """Return the parsed (cached) Family for a concept. Never mutated in place."""
    return _catalog().family(concept_key)


def _concept_meta(concept_key: str) -> tuple[str, str]:
    c = _catalog().concept(concept_key)
    return (c.unit if c else "", c.summary if c else "")


def apply_rules(fam, rules):
    """Return a new Family with every rule applied, in list order (pure)."""
    out = fam
    for rule in rules:
        rtype = rule["type"]
        if rtype in _L2:
            out = mutate.replace_text_fragment(out, rule["var"], rule["condition"], rule["new"])
        elif rtype in _L1:
            out = mutate.replace_option_value(out, rule["param"], rule["value"], rule["new"])
        elif rtype in _FIELD:
            out = mutate.replace_template(out, rule["field"], rule["new"])
        elif rtype == "new_param":
            raise NotImplementedError("new_param is excluded from the pilot corpus (Phase 2)")
        else:
            raise KeyError(f"unmapped rule type {rtype!r}")
    return out


def render_base(concept_key: str) -> dict:
    """Stage-JSON leaves for the unmutated concept (replaces the legacy base call)."""
    ud, concept = _concept_meta(concept_key)
    return mutate.render_family_leaves(family(concept_key), ud=ud, concept=concept)


def run_variant(concept_key: str, rules) -> dict:
    """Apply rules to the concept's Family and return stage-JSON leaves."""
    ud, concept = _concept_meta(concept_key)
    edited = apply_rules(family(concept_key), list(rules))
    return mutate.render_family_leaves(edited, ud=ud, concept=concept)


try:
    from synthetic.taxonomy import Modification, ModificationType, TYPE_TO_LAYER
except ImportError:  # pragma: no cover - fallback for relative-import contexts
    from .taxonomy import Modification, ModificationType, TYPE_TO_LAYER

_CONTEXT_FIELDS = ("param", "var", "condition", "field", "value", "original", "new")


def modification_from_rule(rule: dict) -> Modification:
    """Build the Modification record a rule represents (matches the legacy sidecar).

    Copies the rule's context fields (param/var/condition/field/value/original/new)
    that are present; type+layer are derived from the rule type.
    """
    mtype = ModificationType(rule["type"])
    kwargs = {k: rule[k] for k in _CONTEXT_FIELDS if k in rule}
    return Modification(type=mtype, layer=TYPE_TO_LAYER[mtype], **kwargs)


def modifications_from_rules(rules) -> list:
    return [modification_from_rule(r) for r in rules]
