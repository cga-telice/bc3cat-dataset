"""Adapter: render the synthetic seam on bc3param instead of legacy s03-s07.

Maps the frozen variant rule dicts to `bc3param.mutate` edits on a parsed
`Family`, then emits the legacy stage-JSON leaf shape the synthetic pipeline
consumes.

Skip semantics mirror the legacy `stage_b.apply_variant_rules`: a rule whose
target cannot be edited (e.g. an L2 condition-addressed rule aimed at a
lookup-table text variable that is not a one-axis list, see `_list_element`)
is skipped and logged, exactly as the legacy mutators raise ValueError/KeyError and stage_b
catches it. An *unmapped rule type* or `new_param` still raises loudly — those
are programming/scope errors, not data-driven skips.
"""
from __future__ import annotations

import dataclasses
import logging
import re
from pathlib import Path

from bc3param import mutate
from bc3param.fiebdc import Catalog
from bc3param.param.ast import Assign, Decomp, Index, NumVar, Str, Text, TextList, TextVar
from bc3param.param.codes import letter_to_index
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


# L2 rules on a LIST-form text variable (`$T(2)="…","…"`, referenced as `$T(%B)`)
# carry `%B=<option>`, the l2_repr LIST_plain convention. `mutate` only edits the
# `"frag"*(cond)` form, so these fell through as skips (retrieval D-043). They
# are mapped to the list element of that option, but only when the list is a
# plain one-dimensional list of strings, one per option of B, and every
# reference to it anywhere is exactly `$T(%B)`: then `%B=b` selects precisely
# the leaves that show element b. Anything else still skips.
_LIST_CONDITION_RE = re.compile(r"^%([A-Z])=([A-Za-z0-9])$")
_TEXT_REF_RE = re.compile(r"\$([A-Za-z0-9]+)(?:\(([^)]*)\))?")


def _expr_refs(expr, var: str, out: set) -> None:
    """Collect how `expr` references text variable `var` (argument text, '' if bare)."""
    if isinstance(expr, TextVar):
        if expr.name == var:
            out.add("")
        return
    if isinstance(expr, Index):
        if isinstance(expr.var, TextVar) and expr.var.name == var:
            args = expr.args
            out.add(",".join(f"%{a.name}" if isinstance(a, NumVar) else repr(a) for a in args))
        for a in expr.args:
            _expr_refs(a, var, out)
        return
    for child in (getattr(expr, "left", None), getattr(expr, "right", None),
                  getattr(expr, "operand", None)):
        if child is not None:
            _expr_refs(child, var, out)
    for a in getattr(expr, "args", ()) or ():
        _expr_refs(a, var, out)


def _list_element(fam, var: str, condition: str) -> tuple[int, int]:
    """`(statement index, element index)` that `%AXIS=opt` selects in list `$var`.

    Raises KeyError unless the mapping is unambiguous (see the note above).
    """
    m = _LIST_CONDITION_RE.match(mutate.normalize_condition(condition))
    if m is None:
        raise KeyError(f"list form needs a single '%AXIS=option' condition, got {condition!r}")
    axis, letter = m.groups()
    refs: set = set()
    assigns = []
    for i, st in enumerate(fam.statements):
        texts = ()
        if isinstance(st, Text):
            texts = (st.template,)
        elif isinstance(st, TextList):
            texts = st.items
        elif isinstance(st, Decomp):
            texts = (st.code_template,)
        for text in texts:
            for name, args in _TEXT_REF_RE.findall(text):
                if name == var:
                    refs.add(re.sub(r"\s+", "", args))
        if isinstance(st, Assign):
            if st.kind == "$" and st.name == var:
                assigns.append((i, st))
            for v in st.values:
                _expr_refs(v, var, refs)
        elif isinstance(st, Decomp):
            for e in (st.expr, st.factor):
                if e is not None:
                    _expr_refs(e, var, refs)
    if refs != {f"%{axis}"}:
        raise KeyError(f"${var} is not referenced only as ${var}(%{axis}): {sorted(refs)}")
    if len(assigns) != 1:
        raise KeyError(f"${var} is assigned {len(assigns)} times in {fam.code}")
    i, st = assigns[0]
    if (st.dims is not None and len(st.dims) != 1) or not all(isinstance(v, Str) for v in st.values):
        raise KeyError(f"${var} is not a plain list of strings in {fam.code}")
    param = next((p for p in fam.params if p.var == axis), None)
    if param is None or len(param.options) != len(st.values):
        raise KeyError(f"${var} has {len(st.values)} elements, axis {axis} does not match")
    k = letter_to_index(letter) - 1
    if not 0 <= k < len(st.values):
        raise KeyError(f"option {letter!r} out of range for ${var}")
    return i, k


def _list_fragment(fam, var: str, condition: str) -> str:
    i, k = _list_element(fam, var, condition)
    return fam.statements[i].values[k].value


def _replace_list_element(fam, var: str, condition: str, new_value: str):
    i, k = _list_element(fam, var, condition)
    statements = list(fam.statements)
    values = list(statements[i].values)
    values[k] = Str(new_value)
    statements[i] = dataclasses.replace(statements[i], values=tuple(values))
    return mutate._rebuild(fam, statements)


def _text_fragment(fam, var: str, condition: str) -> str:
    try:
        return mutate.text_fragment(fam, var, condition)
    except KeyError as exc:
        try:
            return _list_fragment(fam, var, condition)
        except KeyError:
            raise exc from None


def _replace_text_fragment(fam, var: str, condition: str, new_value: str):
    try:
        return mutate.replace_text_fragment(fam, var, condition, new_value)
    except KeyError as exc:
        try:
            return _replace_list_element(fam, var, condition, new_value)
        except KeyError:
            raise exc from None


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
        return _replace_text_fragment(fam, rule["var"], rule["condition"], rule["new"])
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
        # L2 rules carry only (var, condition, new); the legacy sidecar also records
        # `original` (the replaced fragment). Capture it before editing so the
        # modification record matches. Read from `out` (post earlier edits).
        original = None
        if rule.get("type") in _L2 and "original" not in rule:
            try:
                original = _text_fragment(out, rule["var"], rule["condition"])
            except (KeyError, ValueError, TypeError):
                original = None
        try:
            out = _edit_for_rule(out, rule)
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("bc3param_backend: skipping %s rule on concept %s: %s",
                           rule.get("type"), concept_key, exc)
            continue
        applied.append({**rule, "original": original} if original is not None else rule)
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
    """Apply rules (skip-and-log non-editable ones) and render; return (leaves, applied).

    If the mutated family fails to render (e.g. an LLM template rewrite introduced a
    malformed ``$X(...)`` the evaluator cannot parse), the whole variant is dropped —
    returns empty leaves — so one bad rewrite does not abort the corpus run. The
    driver then materialises nothing for this variant and counts it as a hard fail.
    """
    from bc3param.fiebdc import Bc3Error
    from bc3param.param.evaluator import EvalError
    from bc3param.param.parser import ParseError

    ud, concept = _concept_meta(concept_key)
    edited, applied = apply_rules_logged(family(concept_key), list(rules), concept_key)
    try:
        leaves = mutate.render_family_leaves(edited, ud=ud, concept=concept)
    except (ParseError, EvalError, Bc3Error) as exc:
        logger.warning("bc3param_backend: dropping unrenderable variant on concept %s "
                       "(%d rules): %s", concept_key, len(applied), exc)
        return {}, applied
    return leaves, applied


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
