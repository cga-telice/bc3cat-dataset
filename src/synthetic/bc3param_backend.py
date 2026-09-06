"""Adapter: render the synthetic seam on bc3param instead of legacy s03-s07.

Maps the frozen variant rule dicts to `bc3param.mutate` edits on a parsed
`Family`, then emits the legacy stage-JSON leaf shape the synthetic pipeline
consumes.

Skip semantics mirror the legacy `stage_b.apply_variant_rules`: a rule whose
target cannot be edited (e.g. an L2 condition-addressed rule aimed at a
lookup-table text variable that has no conditional fragments) is skipped and
logged, exactly as the legacy mutators raise ValueError/KeyError and stage_b
catches it. An *unmapped rule type* or `new_param` still raises loudly — those
are programming/scope errors, not data-driven skips.
"""
from __future__ import annotations

import logging
from pathlib import Path

from bc3param import mutate
from bc3param.fiebdc import Catalog
from utils import config

logger = logging.getLogger(__name__)

# Phase 1 pilot source (same file the frozen pilot corpus used).
SOURCE_DEFAULT = config.RAW_DIR / "BPA_2024_v2_OEB_mod_utf8.txt"
SOURCE = SOURCE_DEFAULT
_CACHE: dict = {}

# Rule-type routing (see the discovered schema).
_L2 = {"paraphrase", "compression", "expansion"}
_L1 = {"synonym_label", "num_to_text", "unit_conversion", "unit_expansion",
       "abbrev_expansion", "code_expansion"}
_FIELD = {"reorder", "template_paraphrase", "omission"}


def set_source(path) -> None:
    """Point the adapter at a different BC3 catalogue (clears the cache).

    A no-op when `path` already names the current source, so repeatedly
    re-asserting the same source (e.g. once per pooled task, to survive a
    `ProcessPoolExecutor` spawn boundary) does not discard the parsed-Family
    cache.
    """
    global SOURCE
    path = Path(path)
    if path == SOURCE:
        return
    SOURCE = path
    _CACHE.clear()


def _catalog() -> Catalog:
    key = str(SOURCE)
    if key not in _CACHE:
        _CACHE[key] = Catalog.load(SOURCE)
    return _CACHE[key]


def family(concept_key: str):
    """Return the parsed (cached) Family for a concept. Never mutated in place."""
    return _catalog().family(concept_key)


def _concept_meta(concept_key: str) -> tuple[str, str]:
    c = _catalog().concept(concept_key)
    return (c.unit if c else "", c.summary if c else "")


def _edit_for_rule(fam, rule):
    """Apply one rule to a Family, returning the new Family. May raise.

    Raises NotImplementedError for `new_param` and KeyError for an unmapped type
    (programming/scope errors). Data-driven failures (target not found, list-form
    text variable) propagate as KeyError/ValueError/TypeError for the caller to
    skip-and-log, matching the legacy mutators + stage_b.
    """
    rtype = rule["type"]
    if rtype == "new_param":
        raise NotImplementedError("new_param is excluded from the pilot corpus (Phase 2)")
    if rtype in _L2:
        return mutate.replace_text_fragment(fam, rule["var"], rule["condition"], rule["new"])
    if rtype in _L1:
        return mutate.replace_option_value(fam, rule["param"], rule["value"], rule["new"])
    if rtype in _FIELD:
        # Substring-splice against `original` (like legacy layer_l3): if `original`
        # isn't in the template the edit raises and the rule is skipped, matching
        # the legacy engine. `original` is always present in the frozen L3 rules.
        return mutate.replace_template_substring(fam, rule["field"], rule["original"], rule["new"])
    raise KeyError(f"unmapped rule type {rtype!r}")


def apply_rules_logged(fam, rules, concept_key: str = "?"):
    """Apply rules, skipping (and logging) those whose target cannot be edited.

    Returns `(edited_family, applied_rules)`. Mirrors legacy
    `stage_b.apply_variant_rules`: KeyError/ValueError/TypeError from an edit are
    caught and the rule is skipped; the applied subset drives the modification
    log so the sidecar matches the legacy corpus.
    """
    out = fam
    applied = []
    for rule in rules:
        try:
            out = _edit_for_rule(out, rule)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("bc3param_backend: skipping %s rule on concept %s: %s",
                           rule.get("type"), concept_key, exc)
            continue
        applied.append(rule)
    return out, applied


def apply_rules(fam, rules):
    """Return a new Family with every rule applied, in list order (pure).

    Strict variant used by unit tests: raises on unmapped type / new_param and
    propagates data-driven failures. Production render uses `apply_rules_logged`.
    """
    out = fam
    for rule in rules:
        out = _edit_for_rule(out, rule)
    return out


def render_base(concept_key: str) -> dict:
    """Stage-JSON leaves for the unmutated concept (replaces the legacy base call)."""
    ud, concept = _concept_meta(concept_key)
    return mutate.render_family_leaves(family(concept_key), ud=ud, concept=concept)


def run_variant_logged(concept_key: str, rules):
    """Apply rules (skip-and-log non-editable ones) and render; return (leaves, applied)."""
    ud, concept = _concept_meta(concept_key)
    edited, applied = apply_rules_logged(family(concept_key), list(rules), concept_key)
    return mutate.render_family_leaves(edited, ud=ud, concept=concept), applied


def run_variant(concept_key: str, rules) -> dict:
    """Apply rules to the concept's Family and return stage-JSON leaves."""
    leaves, _applied = run_variant_logged(concept_key, rules)
    return leaves


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
    # Legacy mutators tag every successfully-applied rule with status="applied";
    # match that so the modification sidecar is byte-identical.
    return Modification(type=mtype, layer=TYPE_TO_LAYER[mtype], status="applied", **kwargs)


def modifications_from_rules(rules) -> list:
    return [modification_from_rule(r) for r in rules]
