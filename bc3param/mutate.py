"""Edit a parsed ``Family`` and re-render it. Additive to the engine; pure edits.

Each function returns a NEW Family (frozen AST nodes are replaced, not mutated),
so callers can keep the original. Targets that do not exist raise KeyError — no
silent no-op, matching the synthetic branch's fail-loud discipline.
"""
from __future__ import annotations

import dataclasses
import re

from .generate import selections
from .param.ast import Assign, Binary, Const, Family, Num, NumVar, ParamDef, Str, Text
from .param.codes import derived_code, index_to_letter, letter_to_index
from .param.evaluator import Evaluator


def _rebuild(family: Family, statements: list) -> Family:
    """Return a new Family whose params list is re-synced to its statements."""
    params = [s for s in statements if isinstance(s, ParamDef)]
    return Family(code=family.code, params=params, statements=statements,
                  warnings=list(family.warnings))


def replace_option_value(family: Family, var: str, letter: str, new_value: str) -> Family:
    """Replace one option value string of parameter ``var`` (by option ``letter``)."""
    idx = letter_to_index(letter) - 1
    statements = list(family.statements)
    for i, st in enumerate(statements):
        if isinstance(st, ParamDef) and st.var == var:
            if not 0 <= idx < len(st.options):
                raise KeyError(f"option {letter!r} out of range for param {var!r}")
            opts = list(st.options)
            opts[idx] = new_value
            statements[i] = dataclasses.replace(st, options=tuple(opts))
            return _rebuild(family, statements)
    raise KeyError(f"no parameter {var!r} in {family.code}")


def normalize_condition(cond: str) -> str:
    """s01-translated condition -> bc3param raw form.

    Legacy conditions (from `utils.z_formula_processing.translate_formula_to_python`)
    use Python syntax: `%B=="c"`, ` or `, ` and `, `!=`. bc3param's raw form uses
    `%B=c`, `@`, `&`, `<>`. Translate the connectives (needing word boundaries)
    before stripping quotes and spaces. Example:
    `'%B=="b"  or  %B=="g"'` -> `'%B=b@%B=g'`.
    """
    cond = cond.replace('"', "")
    cond = re.sub(r"\s+or\s+", "@", cond)
    cond = re.sub(r"\s+and\s+", "&", cond)
    cond = cond.replace("!=", "<>")
    cond = re.sub(r"(?<![<>!])==", "=", cond)  # == -> = ; leave <=,>=,<>,!= alone
    return cond.replace(" ", "")


def _render_condition(expr) -> str:
    """Render a bc3param condition Expr back to raw compact text for matching."""
    if isinstance(expr, Binary):
        return f"{_render_condition(expr.left)}{expr.op}{_render_condition(expr.right)}"
    if isinstance(expr, NumVar):
        return f"%{expr.name}"
    if isinstance(expr, Const):
        return expr.letter
    if isinstance(expr, Num):
        return str(int(expr.value)) if expr.value == int(expr.value) else str(expr.value)
    if isinstance(expr, Str):
        return expr.value
    return ""


def _edit_terms(expr, want_cond: str, new_value: str, hit: list):
    """Walk a sum of ``Str * (cond)`` terms; replace the Str whose cond matches."""
    if isinstance(expr, Binary) and expr.op == "+":
        return Binary("+",
                      _edit_terms(expr.left, want_cond, new_value, hit),
                      _edit_terms(expr.right, want_cond, new_value, hit))
    if isinstance(expr, Binary) and expr.op == "*":
        left, right = expr.left, expr.right
        str_on_left = isinstance(left, Str)
        str_node = left if str_on_left else (right if isinstance(right, Str) else None)
        cond_node = right if str_on_left else left
        if str_node is not None and _render_condition(cond_node).replace(" ", "") == want_cond:
            hit.append(True)
            new_str = Str(new_value)
            return Binary("*", new_str, cond_node) if str_on_left else Binary("*", cond_node, new_str)
    return expr


def replace_text_fragment(family: Family, var: str, condition: str, new_value: str) -> Family:
    """Replace the text fragment of text-variable ``$var`` guarded by ``condition``."""
    want = normalize_condition(condition)
    statements = list(family.statements)
    for i, st in enumerate(statements):
        if isinstance(st, Assign) and st.name == var and st.kind == "$":
            hit: list = []
            new_values = tuple(_edit_terms(v, want, new_value, hit) for v in st.values)
            if not hit:
                raise KeyError(f"no fragment for {var!r} at condition {want!r} in {family.code}")
            statements[i] = dataclasses.replace(st, values=new_values)
            return _rebuild(family, statements)
    raise KeyError(f"no text variable ${var} in {family.code}")


def replace_template(family: Family, label: str, new_template: str) -> Family:
    """Replace the whole RESUMEN or TEXTO template text."""
    statements = list(family.statements)
    for i, st in enumerate(statements):
        if isinstance(st, Text) and st.label == label:
            statements[i] = dataclasses.replace(st, template=new_template)
            return _rebuild(family, statements)
    raise KeyError(f"no {label} template in {family.code}")


def replace_template_substring(family: Family, label: str, original: str, new: str) -> Family:
    """Replace exactly one occurrence of ``original`` within a template.

    Mirrors the legacy ``layer_l3._replace_substring``: raises KeyError when
    ``original`` is absent and ValueError when it is ambiguous (>1 match), so the
    adapter's skip-and-log path drops exactly the L3 rules the legacy engine
    skipped (e.g. a rewrite whose ``original`` doesn't match the template because
    of an accent or wording difference).
    """
    statements = list(family.statements)
    for i, st in enumerate(statements):
        if isinstance(st, Text) and st.label == label:
            count = st.template.count(original)
            if count == 0:
                raise KeyError(f"original {original[:40]!r} not found in {label} of {family.code}")
            if count > 1:
                raise ValueError(f"original {original[:40]!r} ambiguous ({count}) in {label} of {family.code}")
            new_template = st.template.replace(original, new, 1)
            statements[i] = dataclasses.replace(st, template=new_template)
            return _rebuild(family, statements)
    raise KeyError(f"no {label} template in {family.code}")


def render_family_leaves(family: Family, ud: str = "", concept: str = "") -> dict:
    """Expand the cartesian product and return the legacy stage-JSON leaf dict.

    Keys are derived item_keys; values carry parent_key, ud, concept, resumen,
    texto, parameters (nested dict, single value per axis) — the fields the
    synthetic pipeline's s05 filter kept.
    """
    out: dict = {}
    for sel in selections(family):
        ev = Evaluator(family, sel).run()
        params = {
            p.var: {"label": p.name,
                    "values": [{"label": index_to_letter(k), "value": p.options[k - 1]}]}
            for p, k in zip(family.params, sel)
        }
        out[derived_code(family.code, sel)] = {
            "parent_key": family.code,
            "ud": ud,
            "concept": concept,
            "resumen": ev.resumen or "",
            "texto": ev.texto or "",
            "parameters": params,
        }
    return out
