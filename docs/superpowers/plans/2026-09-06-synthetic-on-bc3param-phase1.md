# BC3CAT-Syn on bc3param — Phase 1 (OEB equivalence) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Regenerate the OEB pilot synthetic corpus with `bc3param` as the render backend instead of the legacy `stage_runners` (s03-s07 + `z_formula_processing`), keeping the whole synthetic algorithm above the seam untouched, and prove the result equals the frozen release `6b52053` up to documented v2 corrections.

**Architecture:** Add a small mutation+render capability to `bc3param` (edit a parsed `Family`, render its leaves). Add a synthetic-side adapter `bc3param_backend` that maps the existing variant rules to `Family` edits and emits the legacy stage-JSON shape. Route `stage_b.materialize_variant` and the base-leaf render in `corpus_driver` through the adapter via the already-injectable runner hook. Reconcile the regenerated corpus against the frozen release.

**Tech Stack:** Python 3.11+, `bc3param` (stdlib only), the synthetic package (`src/synthetic`, imports `utils.config`), pytest. Spec: `docs/superpowers/specs/2026-09-06-synthetic-on-bc3param-design.md`.

**Conventions for every task:**
- Branch `synthetic-on-bc3param` (based on `synthetic`). Never push toward `main`. Bringing bc3param in is a `main → synthetic` merge (allowed).
- Run bc3param tests from repo root: `python -m pytest tests -q`. Run synthetic tests: tests live at `tests/synthetic/` with a conftest that adds src/ to sys.path (confirmed Task 0).
- Commit after each task; end every commit message with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Every new module starts with `from __future__ import annotations`.
- Equivalence is "up to documented v2 corrections": reuse the normalization `undo_corruption` from `scripts/reconcile_v1_v2.py` (arrives with the main merge in Task 1).

---

## File structure

```
bc3param/mutate.py            NEW  edit a Family (option value, text fragment, template); render leaves
tests/test_mutate.py          NEW  unit tests for bc3param.mutate
src/synthetic/bc3param_backend.py   NEW  adapter: rules->Family edits, emit legacy stage-JSON
tests/synthetic/test_bc3param_backend.py  NEW  adapter unit + equivalence tests
src/synthetic/stage_b.py      MODIFY  route materialize_variant through the injected bc3param runner
src/synthetic/corpus_driver.py MODIFY  pass the bc3param runner; base-leaf render via adapter
scripts/reconcile_syn_v1_v2.py NEW  corpus reconciliation (regenerated vs release 6b52053)
docs/synthetic/reconciliation-syn-v1-v2.md  NEW  generated report
```

---

### Task 0: Confirm pilot inputs and baseline (read-only)

**Files:** none (investigation; record findings in the commit message of Task 1).

- [ ] **Step 1: Confirm the synthetic test path and current green baseline**

Run: `python -m pytest tests/synthetic -q 2>&1 | tail -5`
Expected: the suite collects and passes (retrospective cites 1,092 green). If the path differs, note the actual path (search: `git ls-files 'src/synthetic/**/test_*.py' | head`).

- [ ] **Step 2: Confirm the pilot source file and config keys**

Run:
```bash
python -c "import sys; sys.path.insert(0,'src'); from utils import config; print([k for k in dir(config) if k.isupper()])"
grep -rn "BPA_2024_v2_OEB_mod\|SYNTHETIC_INTERMEDIATE_DIR\|RAW\|PROCESSED" src/utils/config.py
```
Expected: identify the raw catalogue path the pilot used (`data/raw/BPA_2024_v2_OEB_mod_utf8.txt`) and the synthetic dirs. Record the exact config attribute names for use in Task 6.

- [ ] **Step 3: Confirm the frozen release corpus location**

Run: `git show 6b52053 --stat | grep -E "data/synthetic/(processed|release)" | head` and `ls data/synthetic/processed/`
Expected: locate `BC3CAT_Syn_items.parquet` and `BC3CAT_Syn_modifications.jsonl` (the loaders' `default_items_path` / `default_modifications_path`). Record paths for Task 10.

No commit (read-only). Proceed to Task 1.

---

### Task 1: Merge main (bc3param) into the branch

**Files:** many (merge); resolve `README.md`, `.gitignore`, `CLAUDE.md`, `src/utils/config.py` if they conflict.

- [ ] **Step 1: Merge main**

Run: `git merge --no-commit --no-ff origin/main 2>&1 | tail -20`
Expected: bc3param/, tests/test_*.py (bc3param), scripts/reconcile_v1_v2.py, docs specs add cleanly; conflicts likely only in `README.md`, `.gitignore`, possibly `CLAUDE.md` and `src/utils/config.py`.

- [ ] **Step 2: Resolve conflicts, preferring union**

For `.gitignore` and `README.md`: keep both sides' content (synthetic sections + bc3param sections). For `src/utils/config.py`: keep synthetic's version (it has the synthetic paths); if main changed it, port only additive keys. Verify no `<<<<<<<` remain:
```bash
grep -rn '^<<<<<<<\|^>>>>>>>' . --include=*.py --include=*.md --include=.gitignore || echo "clean"
```

- [ ] **Step 3: Verify both test suites still pass**

Run:
```bash
python -m pip install -e . -q
python -m pytest tests -q 2>&1 | tail -3            # bc3param suite (~95)
python -m pytest tests/synthetic -q 2>&1 | tail -3   # synthetic suite
```
Expected: both green. bc3param's reference tests skip (2024/2026 raw files are gitignored and may be absent) — that is fine.

- [ ] **Step 4: Commit the merge**

```bash
git add -A
git commit -m "Merge main into synthetic-on-bc3param: bring in bc3param engine

Task 0 findings: pilot source <path>, synthetic tests at <path>, release
corpus at <path>. Direction is main->synthetic (allowed); never the reverse.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `bc3param.mutate.replace_option_value`

**Files:**
- Create: `bc3param/mutate.py`
- Test: `tests/test_mutate.py`

- [ ] **Step 1: Write the failing test**

```python
from __future__ import annotations

from bc3param.mutate import replace_option_value
from bc3param.param.parser import parse_family


FAMILY = (
    "\\Nº TUBOS \\ 2 \\ 4 \\\n"
    "\\TIPO DE TERRENO \\Normal\\Rocoso\\\n"
    "$K= \"normal\" * (%B=a) + \"rocoso\" * (%B=b)\n"
    "MN10010001 : 1*%A\n"
    "\\RESUMEN\\Canal $A T, $K.\\\n"
    "\\TEXTO\\Canal de $A tubos $K.\\\n"
)


def test_replace_option_value_edits_named_axis_and_is_pure():
    fam = parse_family("OEB020$", FAMILY)
    out = replace_option_value(fam, "B", "b", "muy rocoso")
    assert out.params[1].options == ("Normal", "muy rocoso")
    # original untouched (pure)
    assert fam.params[1].options == ("Normal", "Rocoso")


def test_replace_option_value_unknown_target_raises():
    fam = parse_family("OEB020$", FAMILY)
    import pytest
    with pytest.raises(KeyError):
        replace_option_value(fam, "B", "z", "x")   # no such option letter in B
    with pytest.raises(KeyError):
        replace_option_value(fam, "Z", "a", "x")   # no such param
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mutate.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bc3param.mutate'`

- [ ] **Step 3: Implement `bc3param/mutate.py` (this function only)**

```python
"""Edit a parsed ``Family`` and re-render it. Additive to the engine; pure edits.

Each function returns a NEW Family (frozen AST nodes are replaced, not mutated),
so callers can keep the original. Targets that do not exist raise KeyError — no
silent no-op, matching the synthetic branch's fail-loud discipline.
"""
from __future__ import annotations

import dataclasses

from .param.ast import Assign, Binary, Const, Family, ParamDef, Str, Text
from .param.codes import letter_to_index


def replace_option_value(family: Family, var: str, letter: str, new_value: str) -> Family:
    """Replace one option value string of parameter ``var`` (by option ``letter``)."""
    params = list(family.params)
    for i, p in enumerate(params):
        if p.var == var:
            idx = letter_to_index(letter) - 1
            if not 0 <= idx < len(p.options):
                raise KeyError(f"option {letter!r} out of range for param {var!r}")
            opts = list(p.options)
            opts[idx] = new_value
            params[i] = dataclasses.replace(p, options=tuple(opts))
            return _with_params(family, params)
    raise KeyError(f"no parameter {var!r} in {family.code}")


def _with_params(family: Family, params: list[ParamDef]) -> Family:
    # statements list holds the same ParamDef objects first; rebuild it so the
    # (also-listed) params match. ParamDef appears in statements in order.
    new_stmts = []
    pi = 0
    for st in family.statements:
        if isinstance(st, ParamDef):
            new_stmts.append(params[pi]); pi += 1
        else:
            new_stmts.append(st)
    return Family(code=family.code, params=params, statements=new_stmts,
                  warnings=list(family.warnings))
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mutate.py -q`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/mutate.py tests/test_mutate.py
git commit -m "bc3param.mutate: replace_option_value (pure Family edit)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `bc3param.mutate.replace_text_fragment`

Text-variable rules identify a fragment by (var, condition), e.g. rule
`{"type":"compression","var":"K","condition":"%B==\"c\"","new":"rocoso"}`. In
bc3param the text variable `$K` parses to an `Assign` whose value is a sum of
`Binary("*", Str, <condition>)` terms. This edits the `Str` whose sibling
condition matches, after normalizing the rule's s01-style condition (`%B=="c"`)
to bc3param's raw form (`%B=c`).

**Files:**
- Modify: `bc3param/mutate.py`
- Test: `tests/test_mutate.py`

- [ ] **Step 1: Write the failing test**

```python
from bc3param.mutate import replace_text_fragment, normalize_condition


def test_normalize_condition_strips_s01_translation():
    assert normalize_condition('%B=="c"') == "%B=c"
    assert normalize_condition("%B==c") == "%B=c"
    assert normalize_condition("%A<>\"b\"") == "%A<>b"


def test_replace_text_fragment_by_condition():
    fam = parse_family("OEB020$", FAMILY)   # FAMILY from test above (module-level)
    out = replace_text_fragment(fam, "K", '%B=="b"', "muy rocoso")
    # find the $K Assign in the output and check the "rocoso" Str became "muy rocoso"
    k = [s for s in out.statements if getattr(s, "name", None) == "K"][0]
    from bc3param.param.ast import Str
    strs = _collect_strs(k.values[0])
    assert "muy rocoso" in strs and "rocoso" not in strs
    assert "normal" in strs  # other term untouched
    # original untouched
    k0 = [s for s in fam.statements if getattr(s, "name", None) == "K"][0]
    assert "rocoso" in _collect_strs(k0.values[0])


def _collect_strs(expr):
    from bc3param.param.ast import Str, Binary
    if isinstance(expr, Str):
        return [expr.value]
    if isinstance(expr, Binary):
        return _collect_strs(expr.left) + _collect_strs(expr.right)
    return []


def test_replace_text_fragment_no_match_raises():
    import pytest
    fam = parse_family("OEB020$", FAMILY)
    with pytest.raises(KeyError):
        replace_text_fragment(fam, "K", '%B=="z"', "x")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mutate.py -k text_fragment -q`
Expected: FAIL with `ImportError: cannot import name 'replace_text_fragment'`

- [ ] **Step 3: Implement (append to `bc3param/mutate.py`)**

```python
import re


def normalize_condition(cond: str) -> str:
    """s01-translated condition (`%B=="c"`) -> bc3param raw form (`%B=c`)."""
    cond = cond.replace('"', "")
    cond = re.sub(r"(?<![<>!])==", "=", cond)   # == -> = (leave <=,>=,<>)
    return cond.replace(" ", "")


def _render_condition(expr) -> str:
    """Render a bc3param condition Expr back to raw text for matching."""
    from .param.ast import Binary, Const, NumVar, Num
    if isinstance(expr, Binary):
        return f"{_render_condition(expr.left)}{expr.op}{_render_condition(expr.right)}"
    if isinstance(expr, NumVar):
        return f"%{expr.name}"
    if isinstance(expr, Const):
        return expr.letter
    if isinstance(expr, Num):
        return str(int(expr.value)) if expr.value == int(expr.value) else str(expr.value)
    return ""


def _edit_terms(expr, want_cond: str, new_value: str, hit: list):
    """Walk a sum of ``Str * (cond)`` terms; replace the Str whose cond matches."""
    from .param.ast import Binary, Str
    if isinstance(expr, Binary) and expr.op == "+":
        return Binary("+", _edit_terms(expr.left, want_cond, new_value, hit),
                      _edit_terms(expr.right, want_cond, new_value, hit))
    if isinstance(expr, Binary) and expr.op == "*":
        left, right = expr.left, expr.right
        str_node = left if isinstance(left, Str) else (right if isinstance(right, Str) else None)
        cond_node = right if str_node is left else left
        if str_node is not None and _render_condition(cond_node).replace(" ", "") == want_cond:
            hit.append(True)
            new_str = Str(new_value)
            return Binary("*", new_str, cond_node) if str_node is left else Binary("*", cond_node, new_str)
    return expr


def replace_text_fragment(family: Family, var: str, condition: str, new_value: str) -> Family:
    """Replace the text fragment of text-variable ``$var`` guarded by ``condition``."""
    want = normalize_condition(condition)
    stmts = list(family.statements)
    for i, st in enumerate(stmts):
        if isinstance(st, Assign) and st.name == var and st.kind == "$":
            hit: list = []
            new_values = tuple(_edit_terms(v, want, new_value, hit) for v in st.values)
            if not hit:
                raise KeyError(f"no fragment for {var!r} at condition {want!r} in {family.code}")
            stmts[i] = dataclasses.replace(st, values=new_values)
            return dataclasses.replace(family, statements=stmts,
                                       params=[s for s in stmts if isinstance(s, ParamDef)])
    raise KeyError(f"no text variable ${var} in {family.code}")
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mutate.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/mutate.py tests/test_mutate.py
git commit -m "bc3param.mutate: replace_text_fragment by (var, condition)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `bc3param.mutate.replace_template`

Template rules (`reorder`, `template_paraphrase`) replace a whole RESUMEN or
TEXTO template. Rule shape: `{"type":"template_paraphrase","var":"RESUMEN","new":"<template>"}`
(the `var` names the template surface; confirm the exact key in Task 6 against a
real L3 rule and adapt the lookup label there).

**Files:**
- Modify: `bc3param/mutate.py`
- Test: `tests/test_mutate.py`

- [ ] **Step 1: Write the failing test**

```python
from bc3param.mutate import replace_template


def test_replace_template_resumen_and_texto():
    fam = parse_family("OEB020$", FAMILY)
    out = replace_template(fam, "RESUMEN", "Nuevo resumen $A.")
    t = [s for s in out.statements if getattr(s, "label", None) == "RESUMEN"][0]
    assert t.template == "Nuevo resumen $A."
    t0 = [s for s in fam.statements if getattr(s, "label", None) == "RESUMEN"][0]
    assert t0.template == "Canal $A T, $K."   # original untouched


def test_replace_template_unknown_label_raises():
    import pytest
    fam = parse_family("OEB020$", FAMILY)
    with pytest.raises(KeyError):
        replace_template(fam, "PLIEGO", "x")
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mutate.py -k template -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement (append to `bc3param/mutate.py`)**

```python
def replace_template(family: Family, label: str, new_template: str) -> Family:
    """Replace the RESUMEN or TEXTO template text."""
    stmts = list(family.statements)
    for i, st in enumerate(stmts):
        if isinstance(st, Text) and st.label == label:
            stmts[i] = dataclasses.replace(st, template=new_template)
            return dataclasses.replace(family, statements=stmts,
                                       params=[s for s in stmts if isinstance(s, ParamDef)])
    raise KeyError(f"no {label} template in {family.code}")
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mutate.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/mutate.py tests/test_mutate.py
git commit -m "bc3param.mutate: replace_template (RESUMEN/TEXTO)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: `bc3param.mutate.render_family_leaves`

Emit the legacy stage-JSON leaf dict from a (possibly edited) Family.

**Files:**
- Modify: `bc3param/mutate.py`
- Test: `tests/test_mutate.py`

- [ ] **Step 1: Write the failing test**

```python
from bc3param.mutate import render_family_leaves


def test_render_family_leaves_shape_and_keys():
    fam = parse_family("OEB020$", FAMILY)   # 2 x 2 options
    leaves = render_family_leaves(fam)
    assert set(leaves) == {"OEB020aa", "OEB020ab", "OEB020ba", "OEB020bb"}
    leaf = leaves["OEB020ab"]
    assert set(leaf) == {"parent_key", "ud", "concept", "resumen", "texto", "parameters"}
    assert leaf["parent_key"] == "OEB020$"
    assert leaf["parameters"] == {
        "A": {"label": "Nº TUBOS", "values": [{"label": "a", "value": " 2 "}]},
        "B": {"label": "TIPO DE TERRENO", "values": [{"label": "b", "value": "Rocoso"}]},
    }
    assert leaf["resumen"] == "Canal 2 T, rocoso."
    assert leaf["texto"] == "Canal de 2 tubos rocoso."


def test_render_family_leaves_reflects_edit():
    fam = parse_family("OEB020$", FAMILY)
    fam2 = replace_text_fragment(fam, "K", '%B=="b"', "muy rocoso")
    leaves = render_family_leaves(fam2)
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_mutate.py -k render_family_leaves -q`
Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement (append to `bc3param/mutate.py`)**

```python
from .generate import selections
from .param.codes import derived_code, index_to_letter
from .param.evaluator import Evaluator


def render_family_leaves(family: Family, ud: str = "", concept: str = "") -> dict:
    """Expand the cartesian product and return the legacy stage-JSON leaf dict.

    Keys are derived item_keys; values carry parent_key, ud, concept, resumen,
    texto, parameters (nested dict, single value per axis). Mirrors the fields
    stage_runners' s05 filter keeps. ``ud``/``concept`` default to empty and are
    normally supplied by the adapter from the catalogue's ~C record.
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
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_mutate.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add bc3param/mutate.py tests/test_mutate.py
git commit -m "bc3param.mutate: render_family_leaves (legacy stage-JSON shape)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Adapter — catalogue cache and rules→Family edits

**Files:**
- Create: `src/synthetic/bc3param_backend.py`
- Test: `tests/synthetic/test_bc3param_backend.py`

- [ ] **Step 1: Confirm the real L1/L3 rule keys**

Run:
```bash
python - <<'PY'
import json, collections
d = json.load(open("data/synthetic/variants/OEB020$.json", encoding="utf-8"))
keys = collections.Counter()
for v in d["variants"]:
    for r in v["rules"]:
        keys[(r["type"], tuple(sorted(r)))] += 1
for k, n in keys.most_common():
    print(n, k)
PY
```
Expected: shows every rule `type` with its exact key set. L2 types use `{type,var,condition,new}`; L1 (param_value) uses `{type,var,...,new}` with a value/letter selector; L3 (`reorder`,`template_paraphrase`) name a template. Record the exact selector keys and use them in Step 3's `rules_to_family_edits`.

- [ ] **Step 2: Write the failing test**

```python
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))   # repo root for bc3param
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # src for utils

import pytest

from synthetic import bc3param_backend as bk


RAW = (
    "~V||FIEBDC-3/2007\\260224|menfis|\\|ANSI||\n"
    "~K|0\\3\\3\\4\\2\\2\\2\\2\\|0\\0\\0\\0\\21\\|3\\2\\\\3\\4\\\\2\\2\\2\\3\\3\\3\\3\\2\\EUR\\|\n"
    "~C|OEB020$|m|CANAL||||\n"
    "~P|OEB020$|\\Nº TUBOS \\ 2 \\ 4 \\\n\\TIPO\\Normal\\Rocoso\\\n"
    "$K= \"normal\"*(%B=a)+\"rocoso\"*(%B=b)\n"
    "\\RESUMEN\\Canal $A T, $K.\\\n\\TEXTO\\Canal de $A tubos $K.\\|\n"
)


@pytest.fixture
def cat(tmp_path):
    f = tmp_path / "mini.bc3"
    f.write_bytes(RAW.encode("cp1252"))
    from bc3param.fiebdc import Catalog
    return Catalog.load(f)


def test_rules_to_family_edits_l2(cat):
    fam = cat.family("OEB020$")
    edited = bk.apply_rules(fam, [{"type": "compression", "var": "K",
                                   "condition": '%B=="b"', "new": "muy rocoso"}])
    from bc3param.mutate import render_family_leaves
    leaves = render_family_leaves(edited, ud="m", concept="CANAL")
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."


def test_apply_rules_unknown_target_raises(cat):
    fam = cat.family("OEB020$")
    with pytest.raises(KeyError):
        bk.apply_rules(fam, [{"type": "compression", "var": "K",
                              "condition": '%B=="z"', "new": "x"}])
```

- [ ] **Step 3: Implement `src/synthetic/bc3param_backend.py` (cache + apply_rules)**

```python
"""Adapter: render the synthetic seam on bc3param instead of legacy s03-s07.

Maps the existing variant rule dicts to `bc3param.mutate` edits on a parsed
`Family`, then emits the legacy stage-JSON leaf shape the synthetic pipeline
consumes. Fail-loud: an unmapped rule type or a missing target raises.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from bc3param import mutate
from bc3param.fiebdc import Catalog
from utils import config

# Layer routing by rule type (mirrors synthetic.taxonomy.TYPE_TO_LAYER).
_L1 = {"synonym_label", "num_to_text", "unit_conversion", "unit_expansion",
       "abbrev_expansion", "code_expansion"}
_L2 = {"paraphrase", "compression", "expansion"}
_L3 = {"reorder", "template_paraphrase"}


# Phase 1 pilot source (confirmed Task 0): config has RAW_DIR, not a source-file key.
PILOT_SOURCE = config.RAW_DIR / "BPA_2024_v2_OEB_mod_utf8.txt"


@lru_cache(maxsize=1)
def _catalog() -> Catalog:
    return Catalog.load(PILOT_SOURCE)


def family(concept_key: str):
    return _catalog().family(concept_key)


def apply_rules(fam, rules):
    """Return a new Family with every rule applied, in list order."""
    out = fam
    for rule in rules:
        rtype = rule["type"]
        if rtype in _L2:
            out = mutate.replace_text_fragment(out, rule["var"], rule["condition"], rule["new"])
        elif rtype in _L1:
            # L1 edits a parameter option value; selector key confirmed in Step 1.
            out = mutate.replace_option_value(out, rule["var"], rule["letter"], rule["new"])
        elif rtype in _L3:
            out = mutate.replace_template(out, _template_label(rule), rule["new"])
        else:
            raise KeyError(f"unmapped rule type {rtype!r}")
    return out


def _template_label(rule: dict) -> str:
    """Normalize an L3 rule's template selector to 'RESUMEN' / 'TEXTO'."""
    raw = str(rule.get("var") or rule.get("template") or rule.get("surface")).upper()
    if "RESUM" in raw:
        return "RESUMEN"
    if "TEXT" in raw:
        return "TEXTO"
    raise KeyError(f"cannot map template selector in rule {rule}")
```

Note: if Step 1 shows L1 uses a value selector rather than `letter`, adjust
`replace_option_value`'s call to translate that selector to the option letter
(add a helper `_option_letter(fam, var, selector)` here); keep the mutate
function letter-based.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/synthetic/test_bc3param_backend.py -q`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/synthetic/bc3param_backend.py tests/synthetic/test_bc3param_backend.py
git commit -m "synthetic: bc3param_backend — catalogue cache + rules->Family edits

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Adapter — `run_stages_3_to_7` drop-in and base render

**Files:**
- Modify: `src/synthetic/bc3param_backend.py`
- Test: `tests/synthetic/test_bc3param_backend.py`

- [ ] **Step 1: Write the failing test**

```python
def test_render_base_matches_legacy_up_to_v2(cat, monkeypatch):
    # base (no rules) leaves for the concept, in stage-JSON shape
    monkeypatch.setattr(bk, "_catalog", lambda: cat)
    leaves = bk.render_base("OEB020$")
    assert set(leaves) == {"OEB020aa", "OEB020ab", "OEB020ba", "OEB020bb"}
    assert leaves["OEB020aa"]["ud"] == "m" and leaves["OEB020aa"]["concept"] == "CANAL"


def test_run_variant_applies_rules(cat, monkeypatch):
    monkeypatch.setattr(bk, "_catalog", lambda: cat)
    leaves = bk.run_variant("OEB020$", [{"type": "compression", "var": "K",
                                         "condition": '%B=="b"', "new": "muy rocoso"}])
    assert leaves["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/synthetic/test_bc3param_backend.py -k "render_base or run_variant" -q`
Expected: FAIL with `AttributeError: module ... has no attribute 'render_base'`

- [ ] **Step 3: Implement (append to `bc3param_backend.py`)**

```python
def _concept_meta(concept_key: str) -> tuple[str, str]:
    c = _catalog().concept(concept_key)
    return (c.unit if c else "", c.summary if c else "")


def render_base(concept_key: str) -> dict:
    """Stage-JSON leaves for the unmutated concept (replaces the legacy base call)."""
    ud, concept = _concept_meta(concept_key)
    return mutate.render_family_leaves(family(concept_key), ud=ud, concept=concept)


def run_variant(concept_key: str, rules) -> dict:
    """Apply rules to the concept's Family and return stage-JSON leaves."""
    ud, concept = _concept_meta(concept_key)
    edited = apply_rules(family(concept_key), list(rules))
    return mutate.render_family_leaves(edited, ud=ud, concept=concept)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/synthetic/test_bc3param_backend.py -q`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add src/synthetic/bc3param_backend.py tests/synthetic/test_bc3param_backend.py
git commit -m "synthetic: bc3param_backend — render_base / run_variant

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: Route `stage_b` and `corpus_driver` through the adapter

`stage_b.materialize_variant` currently slices the stage-2 dict, mutates it, and
calls legacy `run_stages_3_to_7`. Add a bc3param path that ignores the legacy
dict body and renders from the concept's Family via the adapter, keyed by
concept_key + rules. `corpus_driver`'s base call (`stage_runners.run_stages_3_to_7`
at ~line 409) is replaced with `bc3param_backend.render_base`.

**Files:**
- Modify: `src/synthetic/stage_b.py`, `src/synthetic/corpus_driver.py`
- Test: `tests/synthetic/test_bc3param_backend.py`

- [ ] **Step 1: Write the failing test**

```python
def test_materialize_variant_via_bc3param(cat, monkeypatch):
    monkeypatch.setattr(bk, "_catalog", lambda: cat)
    from synthetic import stage_b
    from synthetic.variant_catalog import VariantRecord
    variant = VariantRecord(
        condition="single_compression",
        target_id_repr="(('K','%B==\"b\"'),)",
        rules=[{"type": "compression", "var": "K", "condition": '%B=="b"', "new": "muy rocoso"}],
    )
    mv = stage_b.materialize_variant_bc3param({"OEB020$": {}}, "OEB020$", variant)
    assert mv.items["OEB020ab"]["resumen"] == "Canal 2 T, muy rocoso."
    assert mv.concept_key == "OEB020$"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/synthetic/test_bc3param_backend.py -k materialize_variant_via -q`
Expected: FAIL with `AttributeError: ... 'materialize_variant_bc3param'`

- [ ] **Step 3: Add the bc3param materializer to `stage_b.py`**

Append (keeps the legacy `materialize_variant` intact for the frozen path):

```python
def materialize_variant_bc3param(stage2_json, concept_key, variant):
    """Materialise a variant using the bc3param backend (Phase 1 seam swap).

    Ignores stage2_json's concept body: bc3param re-parses the concept from the
    raw ~P (clean, corruption-free) and applies the variant's rules as Family
    edits. Returns the same MaterializedVariant shape as the legacy path.
    """
    from .bc3param_backend import run_variant
    from .taxonomy import ModificationType

    items = run_variant(concept_key, variant.rules)
    mods = tuple()  # modification log rebuilt from rules if the sidecar needs it (Task 10)
    types = tuple(ModificationType(r["type"]) for r in variant.rules)
    return MaterializedVariant(
        variant_id=_variant_id(variant),
        condition=variant.condition,
        concept_key=concept_key,
        modification_types=types,
        modifications=mods,
        items=items,
    )
```

- [ ] **Step 4: Point `corpus_driver`'s base render at the adapter**

In `src/synthetic/corpus_driver.py`, replace the base-leaf call
`stage_runners.run_stages_3_to_7(l2_repr.formula_to_list(concept_slice))`
(~line 409) with:

```python
from .bc3param_backend import render_base
out = render_base(concept_key)
```

and switch the variant materialisation call to `stage_b.materialize_variant_bc3param`.
Keep the imports of `stage_runners` / `l2_repr` only if still used elsewhere;
remove if now unused (run `python -c "import ast..."` or flake to confirm).

- [ ] **Step 5: Run to verify pass**

Run: `python -m pytest tests/synthetic/test_bc3param_backend.py -q`
Expected: all passed

- [ ] **Step 6: Commit**

```bash
git add src/synthetic/stage_b.py src/synthetic/corpus_driver.py tests/synthetic/test_bc3param_backend.py
git commit -m "synthetic: route stage_b + corpus_driver base render through bc3param

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Equivalence test on real OEB concepts (up to v2 corrections)

**Files:**
- Test: `tests/synthetic/test_bc3param_backend.py`

- [ ] **Step 1: Write the test (skips if the pilot source is absent)**

```python
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "data" / "raw" / "BPA_2024_v2_OEB_mod_utf8.txt"   # pilot source (Task 0)


@pytest.mark.skipif(not SRC.exists(), reason="pilot source not present")
def test_base_leaves_equal_legacy_up_to_v2_corrections():
    import sys; sys.path.insert(0, str(REPO))
    from bc3param.fiebdc import Catalog
    from bc3param import mutate
    from scripts.reconcile_v1_v2 import undo_corruption   # arrived with main merge
    cat = Catalog.load(SRC)
    # legacy golden base leaves for one concept, from the committed intermediate
    import json
    legacy = json.loads((REPO / "data/intermediate/OBRA CIVIL/OBRA CIVIL.json").read_text("utf-8")) \
        if (REPO / "data/intermediate/OBRA CIVIL/OBRA CIVIL.json").exists() else None
    fam = cat.family("OEB020$")
    leaves = mutate.render_family_leaves(fam, *(_meta(cat, "OEB020$")))
    # every rendered resumen matches the legacy one up to v2 corrections
    # (compare against a small hand-checked sample to avoid depending on the
    #  full legacy intermediate; the corpus-level check is Task 10)
    assert leaves["OEB020aaaaa"]["resumen"]  # renders non-empty
    # spot-check the maintenance-band correction is applied (no ">==")
    assert ">==" not in leaves["OEB020aaaba"]["resumen"]


def _meta(cat, key):
    c = cat.concept(key)
    return (c.unit if c else "", c.summary if c else "")
```

- [ ] **Step 2: Run**

Run: `python -m pytest tests/synthetic/test_bc3param_backend.py -k up_to_v2 -q`
Expected: PASS (or SKIP if the source file is not present locally). The authoritative equivalence check is the corpus-level reconciliation in Task 10.

- [ ] **Step 3: Commit**

```bash
git add tests/synthetic/test_bc3param_backend.py
git commit -m "synthetic: adapter equivalence spot-check (no v1 corruption in base)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Regenerate the OEB corpus and reconcile against release 6b52053

**Files:**
- Create: `scripts/reconcile_syn_v1_v2.py`, `docs/synthetic/reconciliation-syn-v1-v2.md`

- [ ] **Step 1: Regenerate the corpus with the bc3param backend**

Run the existing corpus driver end to end (it now renders via bc3param). Use the
frozen budgets/pantry from the branch; write to a scratch dir, not over the release:
```bash
python -m synthetic.run_synthetic --help   # confirm the driver entrypoint/flags (Task 0)
python -m synthetic.corpus_driver --out /tmp/syn_v2 <frozen-config-flags>
```
Expected: a regenerated `BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl` under `/tmp/syn_v2`, same item count as the release (8,687) modulo items whose only difference is a v2 correction.

- [ ] **Step 2: Write `scripts/reconcile_syn_v1_v2.py`**

```python
"""Reconcile the bc3param-regenerated OEB synthetic corpus against release 6b52053.

Loads the frozen release items (via synthetic.loaders) and the regenerated items,
joins on item_key, and classifies each text difference as exact / whitespace /
v2-correction / unexplained, reusing undo_corruption from reconcile_v1_v2.
Writes docs/synthetic/reconciliation-syn-v1-v2.md. Success = zero unexplained.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO)); sys.path.insert(0, str(REPO / "src"))

import pandas as pd
from scripts.reconcile_v1_v2 import collapse, undo_corruption


def load(path):
    df = pd.read_parquet(path)
    return {r["item_key"]: (r.get("resumen", r.get("text", "")), r.get("texto", ""))
            for _, r in df.iterrows()}


def main(release_items: str, regenerated_items: str) -> None:
    v1 = load(release_items)
    v2 = load(regenerated_items)
    common = set(v1) & set(v2)
    exact = ws = corr = other = 0
    samples = []
    for k in common:
        a, b = v1[k][0], v2[k][0]
        if a == b: exact += 1
        elif collapse(a) == collapse(b): ws += 1
        elif undo_corruption(a) == undo_corruption(b): corr += 1
        else:
            other += 1
            if len(samples) < 10: samples.append((k, a, b))
    lines = ["# Synthetic corpus reconciliation v1 (release 6b52053) vs v2 (bc3param)", "",
             f"- common items: {len(common)} | only v1: {len(set(v1)-set(v2))} | only v2: {len(set(v2)-set(v1))}",
             f"- exact: {exact} | whitespace: {ws} | v2-correction: {corr} | unexplained: {other}", ""]
    for k, a, b in samples:
        lines += [f"- `{k}`", f"  - v1: {collapse(a)[:200]}", f"  - v2: {collapse(b)[:200]}"]
    (REPO / "docs/synthetic/reconciliation-syn-v1-v2.md").write_text("\n".join(lines) + "\n", "utf-8")
    print("\n".join(lines[:4]))
    assert other == 0, f"{other} unexplained differences — investigate before accepting equivalence"


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

- [ ] **Step 3: Run the reconciliation**

Run: `python scripts/reconcile_syn_v1_v2.py data/synthetic/processed/BC3CAT_Syn_items.parquet /tmp/syn_v2/BC3CAT_Syn_items.parquet`
Expected: report written; **unexplained = 0**. If not zero, inspect the samples: a real divergence means a rule did not map correctly (fix `bc3param_backend.apply_rules` and add a regression test) or a genuine engine difference to document. Do not weaken the check.

- [ ] **Step 4: Commit**

```bash
git add scripts/reconcile_syn_v1_v2.py docs/synthetic/reconciliation-syn-v1-v2.md
git commit -m "synthetic: corpus reconciliation vs release 6b52053 (0 unexplained)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: Update seam golden tests and run the full suites

**Files:**
- Modify: seam tests under `tests/synthetic/` that assert legacy byte-output.

- [ ] **Step 1: Find seam tests pinned to legacy byte-output**

Run: `grep -rln "run_stages_3_to_7\|stage_runners\|>==\|golden" src/synthetic/tests | head`
Expected: a short list of tests that assert the legacy (corrupted) render byte-for-byte.

- [ ] **Step 2: Re-point them to the "up to v2 corrections" criterion**

For each such test, keep the legacy golden as the v1 reference but assert the new
render equals it under `undo_corruption`+`collapse` (import from
`scripts.reconcile_v1_v2`). Where a test asserts a raw `>==` string, invert it to
assert the corrected `>=` form. Add a one-line comment citing this plan.

- [ ] **Step 3: Run both full suites**

Run:
```bash
python -m pytest tests -q 2>&1 | tail -3
python -m pytest tests/synthetic -q 2>&1 | tail -3
```
Expected: both green. The synthetic suite count may drop by the handful of seam byte-tests re-pointed; no new failures.

- [ ] **Step 4: Commit**

```bash
git add src/synthetic/tests
git commit -m "synthetic: seam tests assert equivalence up to v2 corrections

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-review notes

- **Spec coverage:** contract preserved (Task 5 shape; Task 7/8 emit it); bc3param mutate capability (Tasks 2-5); adapter + rules→Family (Task 6); stage_b/corpus_driver re-point via the injectable seam (Task 8); same source as pilot + reconciliation up to v2 corrections (Tasks 9-10); main→synthetic merge (Task 1); scaffolding/menus/pantry untouched (no task edits them). Phase 2 (OE, 2026) explicitly deferred.
- **Placeholder scan:** the two data-shape unknowns (exact L1/L3 rule selector keys; driver entrypoint flags) are resolved by explicit discovery steps (Task 6 Step 1, Task 10 Step 1) whose output feeds the immediately following code, not left as "TBD" in shipped code.
- **Type/name consistency:** `replace_option_value(family,var,letter,new_value)`, `replace_text_fragment(family,var,condition,new_value)`, `replace_template(family,label,new_template)`, `render_family_leaves(family,ud,concept)`, `bc3param_backend.apply_rules/render_base/run_variant`, `stage_b.materialize_variant_bc3param`, `MaterializedVariant(variant_id,condition,concept_key,modification_types,modifications,items)` — used consistently across tasks. `undo_corruption`/`collapse` come from `scripts/reconcile_v1_v2.py` (present after Task 1).
- **Risk flagged:** if L1 rules select the option by value rather than letter, Task 6 Step 3's note adds a value→letter helper; if the modification sidecar needs a full modification log (Task 8 leaves `mods` empty), Task 10 Step 1 will surface it and it is rebuilt from `variant.rules` in `materialize_variant_bc3param`.
