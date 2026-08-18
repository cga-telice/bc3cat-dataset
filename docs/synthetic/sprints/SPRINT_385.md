# Sprint 38.5 — F3-prep-2-fix (menu recovery: parser repair, per-type caps, targeting gates) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

| Field           | Value |
|-----------------|-------|
| **Sprint**      | 38.5 (inserted between 38 and 39; Sprint 39 = sampler stays as planned) |
| **Date**        | 2026-08-18 (drafted) |
| **Branch**      | `synthetic` |
| **Backlog IDs** | **F3-prep-2-fix** (Claude, hermetic + offline replay). Blocks **F3-prep-2-review** (César): do *not* start the 7–9 h manual review until this lands. |
| **Predecessor** | Sprint 38 — F3-prep-2-generate (live phi4 run, 2 918 candidates, 502 recorded transcripts). |
| **Successor**   | F3-prep-2-review (César) → F3-prep-2-parse → Sprint 39 (budgets + sampler + chapter driver). |

**Goal:** Recover the ~127 TEXTO/RESUMEN template targets silently lost to a JSON-escape bug, stop asking for 10 near-identical alternatives on low-entropy rewrite types, and stop `synonym_label` / `compression` from being aimed at values they cannot sensibly rewrite — then regenerate the review menus **entirely offline from the existing transcript cache** (zero GPU time) so the manual review starts from a complete, un-skewed menu.

**Architecture:** Three surgical changes above the frozen seam, none of which alter any prompt text (so every one of the 502 cached transcripts still hits): (1) `menu_proposer._parse_json_list` retries `json.loads` after dropping invalid JSON escapes — the FIEBDC `\TEXTO\` leading backslash that phi4 echoes; (2) `menu_proposer` truncates each target's deduped candidate list to a per-type cap (`omission`/`reorder`/`num_to_text`/`unit_*` → 3) *after* parsing, so the review shrinks without changing the request; (3) `slot_extractor` targeting gates — `synonym_label` skips digit-bearing values, `compression` skips fragments under 4 words. Then `menu_runner replay` rewrites the 11 menus.

**Tech Stack:** Python 3.11 stdlib (`re`, `json`), `pytest`. `PYTHONPATH=src` is already wired by `tests/conftest`; run tests as `pytest tests/synthetic -q` from the repo root.

---

## Context — what the assessment found (2026-08-18)

Profiling `data/synthetic/menus/*.jsonl` after the Sprint 38 run:

| type | targets | empty | cands | uniq/tgt | verdict |
|---|---|---|---|---|---|
| omission | 212 | **100** | 590 | 5.3 | 97/115 **TEXTO** targets skipped `malformed_json: Invalid \escape`; the 10 survivors per target differ only in a connective (pairwise token-Jaccard 0.86) |
| reorder | 49 | **19** | 215 | 7.2 | 15/24 TEXTO skipped, same cause; 6/215 candidates identical to original |
| template_paraphrase | 49 | **15** | 286 | 8.4 | 15/24 TEXTO skipped, same cause |
| synonym_label | 49 | 6 | 236 | 5.5 | 78/78 digit-bearing labels lost their digits (`3 <= i < 5 horas → Mantenimiento Moderado`, `1,10 m → Profunda`) — meaning-changing |
| compression | 46 | 0 | 291 | 6.3 | 4 no-ops; 2–3-word fragments have no room (`Diurno excepcional → Diurno +E`) |
| unit_conversion / unit_expansion / num_to_text | 14 / 14 / 12 | 7 / 2 / 0 | 21 / 49 / 105 | 3.0 / 4.1 / 8.8 | inherently narrow; 10 alternatives is wasted review |
| paraphrase / expansion / new_param | 46 / 46 / 25 | 0 | 420 / 454 / 251 | 9.1 / 9.9 / 9.8 | healthy |

Root cause of the skips: every OEB `texto` template in `data/intermediate/OBRA CIVIL/OBRA CIVIL.json` begins with `\` and every `resumen` ends with `\` (FIEBDC `\TEXTO\…\` field delimiters that s01 leaves in; the main pipeline drops them later, but the synthetic prompt builder reads the raw field). phi4 echoes the backslash inside its JSON string → `Invalid \escape`. **All 133 cached transcripts with this defect parse cleanly once stray backslashes are dropped** — no re-generation needed.

Because `layer_l3` applies rewrites by *substring* replacement of `original` inside the raw template, an `original` without the backslash still matches (the leading `\` is simply left in place, exactly as the baseline has it). Nothing downstream needs the backslash.

### Decisions taken in this plan (César: veto here if you disagree)

- **D1 — no prompt changes in this sprint.** Cleaning the `\` out of the *prompt* would change ~310 L3 prompt hashes → ~60–80 min live phi4. The parser repair alone recovers the pilot offline. Prompt-side cleaning is queued as a Sprint 40 pre-task (it must land before the full 451-concept run, where everything is generated fresh anyway).
- **D2 — caps are post-parse truncation, not a smaller `n` in the request.** Same reason: `{n}` is inside the prompt f-string; changing it misses the cache. Candidates are already ordered best→worst by the prompt contract, so keeping the first 3 after dedup is the intended semantics.
- **D3 — `expansion` hallucination is left to the reviewer.** The prompt already forbids new facts and phi4 ignores it; a mechanical length cap would kill nearly every candidate. Review guidance instead (Task 6).
- **D4 — `unit_conversion` / `num_to_text` stay LLM-driven for the pilot.** A deterministic implementation is the right long-term answer (`0,80 m → 8000 mm` is an LLM error, not a review question) but is out of scope here; queued as follow-up.

---

## File map

| File | Change |
|---|---|
| `.gitignore` | ignore `__pycache__/`, `data/synthetic/_archive/`, `data/synthetic/intermediate/` |
| `src/synthetic/menu_proposer.py` | `_repair_invalid_escapes` + retry in `_parse_json_list`; `MENU_CAP_BY_TYPE` + `_cap_candidates`, applied in `_propose_l1` and `_propose_single_target` |
| `src/synthetic/slot_extractor.py` | `value_applies` (per-value predicate; `SYNONYM_LABEL` excludes digits), `_axis_applies` delegates to it; `MIN_COMPRESSION_WORDS = 4` gate in `enumerate_targets` L2 branch |
| `src/synthetic/target_scanner.py` | L1 per-value loop skips values failing `slot_extractor.value_applies` |
| `src/synthetic/menu_profile.py` | **new** — read-only per-type scorecard over `data/synthetic/menus/*.jsonl` (the assessment script, made repeatable) |
| `tests/synthetic/test_menu_builder.py` | parser-repair tests, cap tests |
| `tests/synthetic/test_slot_extractor.py` | `value_applies` tests, compression-gate test, one expectation update |
| `tests/synthetic/test_menu_profile.py` | **new** — one hermetic test |
| `data/synthetic/menus/*.jsonl`, `docs/synthetic/menus/*.md` | regenerated by `menu_runner replay` |
| `docs/synthetic/RESEARCH_LOG.md`, `docs/synthetic/STATUS_2026-07-09.md` → `STATUS_2026-08-18.md`, `docs/synthetic/CLAUDE_SYNTHETIC.md` | log entry + status refresh |

---

### Task 0: Housekeeping — commit the Sprint 05–38 working tree

The branch's last commit is `a7d51b9 Sprint 04`. Everything since (20 modified files, ~120 untracked paths incl. the menus and the 4.7 MB transcript cache) is uncommitted. Commit it *before* touching code so this sprint's diff is reviewable on its own.

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Extend `.gitignore`** so the 1.5 GB of derived data and the tracked `.pyc` files stay out:

```gitignore
data_validation/
__pycache__/
data/synthetic/_archive/
data/synthetic/intermediate/
```

- [ ] **Step 2: Untrack the already-committed `.pyc` files**

```bash
git rm --cached -r src/utils/__pycache__
```

- [ ] **Step 3: Stage everything else and inspect**

```bash
git add -A
git status --short | grep -v "^A  \|^M  \|^D  " ; echo "--- sizes of staged blobs > 5 MB:"; git diff --cached --stat | tail -1
```
Expected: no lines from the first grep (everything staged); the `--stat` summary should be a few thousand insertions, and `git count-objects -vH` afterwards should not jump by more than ~30 MB. If `data/synthetic/review/` (6.9 MB) or `data/synthetic/variants/` (0.6 MB) look wrong to keep, add them to `.gitignore` too and re-run — **César's call**; default is to keep them (they are the F1 pilot audit trail).

- [ ] **Step 4: Commit**

```bash
git commit -m "Sprints 05-38: synthetic pipeline, menu builder, phi4 pilot menus + transcript cache

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 1: Tolerant JSON-list parser (`_repair_invalid_escapes`)

**Files:**
- Modify: `src/synthetic/menu_proposer.py:405-423` (`_parse_json_list`)
- Test: `tests/synthetic/test_menu_builder.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/synthetic/test_menu_builder.py` (the file already imports `pytest` and `from synthetic.menu_proposer import (...)`; add `_parse_json_list` and `_repair_invalid_escapes` to that import list):

```python
# ===========================================================================
# Sprint 38.5 — parser repair for the FIEBDC backslash echo
# ===========================================================================


class TestParseJsonListRepair:
    def test_repairs_fiebdc_backslash_echo(self):
        # Raw \TEXTO\ templates start with "\"; phi4 echoes it inside the JSON
        # string, which is an invalid escape. Recover by dropping the backslash.
        text = (
            '[{"original": "\\Canalización de $A tubos", '
            '"new": "Canalización de $A tubos", "omitted_var": "A"}]'
        )
        assert _parse_json_list(text) == [
            {
                "original": "Canalización de $A tubos",
                "new": "Canalización de $A tubos",
                "omitted_var": "A",
            }
        ]

    def test_leaves_valid_escapes_alone(self):
        text = '[{"original": "a\\"b", "new": "línea\\nnueva"}]'
        assert _parse_json_list(text) == [{"original": 'a"b', "new": "línea\nnueva"}]

    def test_still_rejects_unrecoverable_json(self):
        with pytest.raises(ValueError, match="malformed_json"):
            _parse_json_list('[{"original": "x", "new": ]')

    def test_repair_helper_drops_only_invalid_escapes(self):
        assert _repair_invalid_escapes(r'\C \S \" \\ \n \/ end\\') == r'C S \" \\ \n \/ end\\'
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/synthetic/test_menu_builder.py::TestParseJsonListRepair -q
```
Expected: `ImportError: cannot import name '_repair_invalid_escapes'`.

- [ ] **Step 3: Implement** — in `src/synthetic/menu_proposer.py`, add `import re` next to `import json` (line 51), then add the helper and change `_parse_json_list`:

```python
# Alternation: a *valid* escape pair (\" \\ \/ \b \f \n \r \t \u) is matched
# as a unit and kept; any other lone backslash is matched by the second
# branch and dropped. Consuming valid pairs whole is what keeps "\\" intact.
# Real BC3 text never contains a backslash; the only source is phi4 echoing the
# FIEBDC "\TEXTO\ ... \" field delimiter that s01 leaves on the raw templates.
_ESCAPE_RE = re.compile(r'\\([\\"/bfnrtu])|\\')


def _repair_invalid_escapes(s: str) -> str:
    """Drop backslashes that do not begin a valid JSON escape sequence.

    Sprint 38.5. Applied only *after* a strict ``json.loads`` has failed,
    so well-formed responses are parsed byte-identically to before.
    """
    return _ESCAPE_RE.sub(lambda m: m.group(0) if m.group(1) is not None else "", s)


def _parse_json_list(text: str) -> list:
    """List-level counterpart to :func:`llm_proposer._parse_json_object`.

    Recovers the outermost JSON array from prose/fence-wrapped output;
    tolerates the same shape flexibility (leading commentary, code
    fences). On a decode error, retries once with
    :func:`_repair_invalid_escapes`. Raises ``ValueError`` on
    unrecoverable input.
    """
    s = _recover_json_array(text)
    if not s:
        raise ValueError("empty_response")
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as first_err:
        try:
            obj = json.loads(_repair_invalid_escapes(s))
        except json.JSONDecodeError:
            raise ValueError(f"malformed_json: {first_err.msg}") from first_err
    if not isinstance(obj, list):
        raise ValueError(f"top_level_not_list: type={type(obj).__name__}")
    if not obj:
        raise ValueError("empty_list")
    return obj
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/synthetic/test_menu_builder.py -q
```
Expected: all pass (previous count + 4).

- [ ] **Step 5: Verify against the real cache** — this is the whole point; check the recovery number before committing:

```bash
python - <<'EOF'
import json, glob, sys
sys.path.insert(0, "src")
from synthetic.menu_proposer import _parse_json_list
ok = bad = 0
for f in glob.glob("data/synthetic/llm_cache/menu_OEB/*.json"):
    body = json.load(open(f, encoding="utf-8"))["response"]
    try: _parse_json_list(body); ok += 1
    except ValueError: bad += 1
print(f"parseable={ok} unparseable={bad}")
EOF
```
Expected: `parseable=502 unparseable=0` (before this task ≈ 369 / 133 — the 133 transcripts carrying `\C`, `\S`, … escapes). This exact regex was verified against the cache on 2026-08-18: 502/502. Anything less means the regex was transcribed wrongly — stop and compare with the plan. (Run with `$env:PYTHONPATH="src"` if the import fails.)

- [ ] **Step 6: Commit**

```bash
git add src/synthetic/menu_proposer.py tests/synthetic/test_menu_builder.py
git commit -m "Sprint 38.5: repair invalid JSON escapes in menu responses (recovers 127 skipped L3 targets)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Per-type candidate cap (post-parse)

**Files:**
- Modify: `src/synthetic/menu_proposer.py` (`_propose_l1` line ~173, `_propose_single_target` line ~277)
- Test: `tests/synthetic/test_menu_builder.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/synthetic/test_menu_builder.py`; add `MENU_CAP_BY_TYPE`, `_cap_candidates`, `CandidateProposal` to the `menu_proposer` import list if not already there:

```python
# ===========================================================================
# Sprint 38.5 — per-type menu cap
# ===========================================================================


class TestMenuCap:
    def test_cap_table_covers_low_entropy_types_only(self):
        assert MENU_CAP_BY_TYPE == {
            ModificationType.OMISSION: 3,
            ModificationType.REORDER: 3,
            ModificationType.NUM_TO_TEXT: 3,
            ModificationType.UNIT_CONVERSION: 3,
            ModificationType.UNIT_EXPANSION: 3,
        }

    def test_cap_candidates_truncates_only_capped_types(self):
        cands = tuple(CandidateProposal(payload={"new": str(i)}) for i in range(5))
        assert len(_cap_candidates(cands, ModificationType.OMISSION)) == 3
        assert _cap_candidates(cands, ModificationType.PARAPHRASE) == cands
        # Keeps the head — candidates are ordered best→worst by the prompt.
        assert [c.payload["new"] for c in _cap_candidates(cands, ModificationType.REORDER)] == ["0", "1", "2"]

    def test_propose_type_l1_applies_cap(self):
        # tiny_chapter.json: CTEST020$ axis C "PROFUNDIDAD" values 1, 2 → NUM_TO_TEXT.
        stage = _load_tiny()
        inv = scan_chapter(stage)
        five = [[("1", w)] for w in ("uno", "un", "una unidad", "un tubo", "uno solo")]
        client = _StubLLMClient([_l1_list_response(five, list_key="numerals")])
        sets = propose_type(stage, inv, ModificationType.NUM_TO_TEXT, client, n=5)
        assert len(sets[("PROFUNDIDAD", "1")].candidates) == 3
        assert [c.payload["new"] for c in sets[("PROFUNDIDAD", "1")].candidates] == ["uno", "un", "una unidad"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/synthetic/test_menu_builder.py::TestMenuCap -q
```
Expected: `ImportError: cannot import name 'MENU_CAP_BY_TYPE'`.

- [ ] **Step 3: Implement** — in `src/synthetic/menu_proposer.py`, directly under `DEFAULT_N_CANDIDATES: int = 10`:

```python
# Sprint 38.5. Low-entropy rewrite types: the model's 10 alternatives are
# near-duplicates (omission differs by a connective, reorder by which clause
# moves, unit/number rewrites have 2-3 legitimate forms). Keep the request at
# ``n`` (prompt text is cache-keyed) but present only the first ``cap`` after
# dedup — candidates are ordered best→worst by the prompt contract.
MENU_CAP_BY_TYPE: dict[ModificationType, int] = {
    ModificationType.OMISSION: 3,
    ModificationType.REORDER: 3,
    ModificationType.NUM_TO_TEXT: 3,
    ModificationType.UNIT_CONVERSION: 3,
    ModificationType.UNIT_EXPANSION: 3,
}


def _cap_candidates(
    candidates: tuple["CandidateProposal", ...],
    mtype: ModificationType,
) -> tuple["CandidateProposal", ...]:
    cap = MENU_CAP_BY_TYPE.get(mtype)
    return candidates if cap is None else candidates[:cap]
```

Then apply it. In `_propose_l1` replace

```python
            candidates = _extract_l1_candidates_for_value(
                variants, value_norm,
            )
```
with
```python
            candidates = _cap_candidates(
                _extract_l1_candidates_for_value(variants, value_norm), mtype,
            )
```
and in `_propose_single_target` replace
```python
            candidates = _dedupe_non_l1(variants, mtype)
```
with
```python
            candidates = _cap_candidates(_dedupe_non_l1(variants, mtype), mtype)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/synthetic/test_menu_builder.py tests/synthetic/test_menu_runner.py -q
```
Expected: all pass. (`test_menu_runner` exercises SYNONYM_LABEL/PARAPHRASE only — uncapped — so no expectation shifts.)

- [ ] **Step 5: Commit**

```bash
git add src/synthetic/menu_proposer.py tests/synthetic/test_menu_builder.py
git commit -m "Sprint 38.5: cap omission/reorder/unit/num menus at 3 candidates (post-parse, cache-neutral)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Targeting gates — `synonym_label` excludes digit-bearing values; `compression` needs ≥ 4 words

**Files:**
- Modify: `src/synthetic/slot_extractor.py:107-142` (`_axis_applies` and friends), `:165-174` (`enumerate_targets` L2 branch)
- Modify: `src/synthetic/target_scanner.py:239-256` (L1 per-value loop)
- Test: `tests/synthetic/test_slot_extractor.py`, `tests/synthetic/test_menu_builder.py`

- [ ] **Step 1: Write the failing tests** — append to `tests/synthetic/test_slot_extractor.py` (add `value_applies`, `MIN_COMPRESSION_WORDS` to the `from synthetic.slot_extractor import (...)` list):

```python
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


def test_enumerate_targets_compression_skips_short_fragments():
    # Fixture fragments: K "normal"(1) "PVC"(1); L "hasta 1 m"(3) "más de 1 m"(4); N "por metro lineal"(3)
    assert MIN_COMPRESSION_WORDS == 4
    stage = _fixture()
    got = list(enumerate_targets(stage, "OEB020aa", ModificationType.COMPRESSION))
    assert got == [("L", "%D=b")]
```

Also **update** the existing expectation at `tests/synthetic/test_slot_extractor.py:118` — axis D's values (`Hasta 1 m`, `Más de 1 m`) carry digits, so `SYNONYM_LABEL` no longer applies to D:

```python
    (ModificationType.SYNONYM_LABEL, ["B"]),           # textual, digit-free values → B only (D carries "1 m", A is numeric)
```

And append to `tests/synthetic/test_menu_builder.py` (class `TestScanChapter` or module level):

```python
class TestScannerValueGate:
    def test_synonym_label_skips_digit_values_per_value(self):
        # An axis mixing a clean label with a digit-bearing one: only the
        # clean one becomes a review target.
        stage = _load_tiny()
        stage["CTEST010$"]["parameters"]["B"]["values"].append(
            {"label": "c", "value": "Rocoso 2 m"},
        )
        inv = scan_chapter(stage)
        keys = {t.dedup_key for t in inv.by_type[ModificationType.SYNONYM_LABEL]}
        assert ("TIPO", "Rocoso") in keys
        assert ("TIPO", "Rocoso 2 m") not in keys
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/synthetic/test_slot_extractor.py tests/synthetic/test_menu_builder.py::TestScannerValueGate -q
```
Expected: `ImportError: cannot import name 'value_applies'`.

- [ ] **Step 3: Implement in `slot_extractor.py`** — add after `_ABBREV_RE` (line 73):

```python
_HAS_DIGIT_RE = re.compile(r"\d")

# Sprint 38.5. L2 compression needs room to compress: 2-3-word fragments
# produced no-ops and junk ("Diurno excepcional" → "Diurno +E").
MIN_COMPRESSION_WORDS: int = 4
```

Replace `_axis_applies` (lines 128-142) with a per-value predicate plus the axis wrapper:

```python
def value_applies(value: str, mtype: ModificationType) -> bool:
    """Per-value applicability of an L1 rewrite type (Sprint 38.5; the
    Sprint 31 axis gate now delegates here).

    * SYNONYM_LABEL — needs letters and **no digits**: synonymising a
      numeric band (``3 <= i < 5 horas``) or a dimension (``1,10 m``)
      loses the number, which changes meaning; those values are the
      domain of NUM_TO_TEXT / UNIT_* instead.
    * NUM_TO_TEXT — purely numeric.
    * UNIT_CONVERSION / UNIT_EXPANSION — carries a unit token.
    * ABBREV_EXPANSION / CODE_EXPANSION — carries an abbreviation.
    * anything else — always applies (non-L1 types don't gate per value).
    """
    if mtype is ModificationType.SYNONYM_LABEL:
        return _has_letters(value) and not _HAS_DIGIT_RE.search(value)
    if mtype is ModificationType.NUM_TO_TEXT:
        return _is_numeric(value)
    if mtype in (ModificationType.UNIT_CONVERSION, ModificationType.UNIT_EXPANSION):
        return _has_unit(value)
    if mtype in (ModificationType.ABBREV_EXPANSION, ModificationType.CODE_EXPANSION):
        return _has_abbrev(value)
    return True


def _axis_applies(block: dict, mtype: ModificationType) -> bool:
    """Return True if at least one of `block`'s values makes `mtype` a
    semantically sensible modification. Sprint 31 gate — see module
    docstring above; per-value logic lives in :func:`value_applies`."""
    values = _values(block)
    return bool(values) and any(value_applies(v, mtype) for v in values)
```

In `enumerate_targets`, change the L2 branch loop (lines 173-174) to:

```python
            for condition, fragment in pairs:
                if (
                    modification_type is ModificationType.COMPRESSION
                    and len(fragment.split()) < MIN_COMPRESSION_WORDS
                ):
                    continue
                yield (var_key, condition)
```

- [ ] **Step 4: Implement in `target_scanner.py`** — in `_emit_entries`, L1 branch, after `value_text = _norm(str(entry.get("value", "")))` / `if not value_text: continue` (line 247), add:

```python
                if not slot_extractor.value_applies(value_text, mtype):
                    continue  # Sprint 38.5: per-value gate (e.g. digits under SYNONYM_LABEL)
```

- [ ] **Step 5: Run the whole synthetic suite**

```bash
pytest tests/synthetic -q
```
Expected: all pass. The only pre-existing expectation that legitimately changes is the one edited in Step 1 (`SYNONYM_LABEL → ["B"]`). If anything else fails, it is a real regression — investigate, don't edit expectations.

- [ ] **Step 6: Commit**

```bash
git add src/synthetic/slot_extractor.py src/synthetic/target_scanner.py tests/synthetic/test_slot_extractor.py tests/synthetic/test_menu_builder.py
git commit -m "Sprint 38.5: targeting gates — synonym_label skips digit values, compression needs >=4 words

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `menu_profile.py` — repeatable per-type scorecard over the menu JSONL

Makes the assessment measurable before/after (and reusable in Sprint 40 F3 QC).

**Files:**
- Create: `src/synthetic/menu_profile.py`
- Test: `tests/synthetic/test_menu_profile.py`

- [ ] **Step 1: Write the failing test**

```python
"""Sprint 38.5 — hermetic test for :mod:`synthetic.menu_profile`."""
from __future__ import annotations

import json
from pathlib import Path

from synthetic.menu_profile import profile_dir, format_profile


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def test_profile_counts_targets_candidates_noops_and_skips(tmp_path):
    _write(tmp_path / "paraphrase.jsonl", [
        {"modification_type": "paraphrase", "skipped_reason": None, "dropped_reasons": [],
         "usages": [{"concept_key": "A$"}, {"concept_key": "B$"}],
         "candidates": [
             {"payload": {"original": "20 cm", "new": "veinte centímetros"}},
             {"payload": {"original": "20 cm", "new": "20 CM"}},          # no-op after normalisation
             {"payload": {"original": "20 cm", "new": "veinte  centímetros"}},  # dup of #1
         ]},
        {"modification_type": "paraphrase", "skipped_reason": "malformed_list_after_retry: x",
         "dropped_reasons": ["[0] bad"], "usages": [{"concept_key": "C$"}], "candidates": []},
    ])
    rows = profile_dir(tmp_path)
    assert len(rows) == 1
    r = rows[0]
    assert (r.mtype, r.n_targets, r.n_empty, r.n_candidates, r.n_noop, r.n_dup, r.n_skipped, r.n_dropped, r.n_usages) == (
        "paraphrase", 2, 1, 3, 1, 1, 1, 1, 3)
    assert r.uniq_per_target == 2.0  # 2 unique of 3 on the one populated target
    text = format_profile(rows)
    assert "paraphrase" in text and "uniq/tgt" in text
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/synthetic/test_menu_profile.py -q
```
Expected: `ModuleNotFoundError: No module named 'synthetic.menu_profile'`.

- [ ] **Step 3: Implement `src/synthetic/menu_profile.py`**

```python
"""Per-type mechanical scorecard over the menu JSONL artefacts.

Sprint 38.5. Read-only; answers "how many targets, how many were skipped,
how many candidates are no-ops or duplicates" per rewrite type so a
regeneration can be compared against its predecessor without reading
2 900 lines of Spanish. Complements :func:`menu_runner.format_scorecard`
(which reports the *run*) by reporting the *artefacts on disk*.

CLI::

    python -m synthetic.menu_profile [--menus-dir data/synthetic/menus]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return _WS_RE.sub(" ", s).strip()


@dataclass(frozen=True)
class TypeProfile:
    mtype: str
    n_targets: int
    n_empty: int
    n_candidates: int
    n_noop: int          # candidate == original after accent/case/space normalisation
    n_dup: int           # candidate == an earlier candidate on the same target
    uniq_per_target: float
    n_skipped: int
    n_dropped: int
    n_usages: int


def _candidate_text(payload: dict) -> str:
    return str(payload.get("new") or payload.get("new_axis_label") or "")


def profile_file(path: Path) -> TypeProfile:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    n_empty = n_cand = n_noop = n_dup = n_skipped = n_dropped = n_usages = 0
    uniq_counts: list[int] = []
    for r in rows:
        n_usages += len(r.get("usages") or [])
        if r.get("skipped_reason"):
            n_skipped += 1
        n_dropped += len(r.get("dropped_reasons") or [])
        cands = r.get("candidates") or []
        if not cands:
            n_empty += 1
            continue
        seen: set[str] = set()
        for c in cands:
            p = c.get("payload", {})
            new = _norm(_candidate_text(p))
            orig = p.get("original")
            n_cand += 1
            if orig is not None and new == _norm(str(orig)):
                n_noop += 1
            if new in seen:
                n_dup += 1
            seen.add(new)
        uniq_counts.append(len(seen))
    return TypeProfile(
        mtype=path.stem,
        n_targets=len(rows),
        n_empty=n_empty,
        n_candidates=n_cand,
        n_noop=n_noop,
        n_dup=n_dup,
        uniq_per_target=(sum(uniq_counts) / len(uniq_counts)) if uniq_counts else 0.0,
        n_skipped=n_skipped,
        n_dropped=n_dropped,
        n_usages=n_usages,
    )


def profile_dir(menus_dir: Path) -> list[TypeProfile]:
    return [profile_file(p) for p in sorted(menus_dir.glob("*.jsonl"))]


def format_profile(rows: Sequence[TypeProfile]) -> str:
    head = f"{'type':20s} {'tgt':>4s} {'empty':>5s} {'cands':>5s} {'noop':>4s} {'dup':>4s} {'uniq/tgt':>8s} {'skip':>4s} {'drop':>4s} {'usages':>6s}"
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r.mtype:20s} {r.n_targets:4d} {r.n_empty:5d} {r.n_candidates:5d} {r.n_noop:4d} "
            f"{r.n_dup:4d} {r.uniq_per_target:8.1f} {r.n_skipped:4d} {r.n_dropped:4d} {r.n_usages:6d}"
        )
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.menu_profile")
    parser.add_argument("--menus-dir", default="data/synthetic/menus")
    args = parser.parse_args(argv)
    sys.stdout.write(format_profile(profile_dir(Path(args.menus_dir))))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [ ] **Step 4: Run test, then run it for real to capture the BEFORE baseline**

```bash
pytest tests/synthetic/test_menu_profile.py -q
python -m synthetic.menu_profile > docs/synthetic/sprints/SPRINT_385_profile_before.txt
cat docs/synthetic/sprints/SPRINT_385_profile_before.txt
```
Expected test: PASS. Expected profile: matches the Context table above (`omission 212 100 …`, `reorder 49 19 …`, `template_paraphrase 49 15 …`). (Run with `PYTHONPATH=src` if the module isn't found: `set PYTHONPATH=src` in PowerShell → `$env:PYTHONPATH="src"`.)

- [ ] **Step 5: Commit**

```bash
git add src/synthetic/menu_profile.py tests/synthetic/test_menu_profile.py docs/synthetic/sprints/SPRINT_385_profile_before.txt
git commit -m "Sprint 38.5: menu_profile scorecard + pre-fix baseline

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Regenerate the menus offline from the transcript cache

No LLM, no GPU. `replay` fails loud on any cache miss — that is the proof that Tasks 1–3 changed no prompt.

**Files:**
- Regenerated: `data/synthetic/menus/*.jsonl`, `docs/synthetic/menus/*.md`
- Create: `docs/synthetic/sprints/SPRINT_385_profile_after.txt`

- [ ] **Step 1: Replay**

```bash
python -m synthetic.menu_runner replay --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concept-filter OEB --n 10 --seed 7 --chapter-label OEB
```
Expected: completes in well under a minute, prints the scorecard, **no** `LLMTransportError` (a transport error here means a prompt changed → cache miss → stop; do not switch to `run`). Scorecard expectations: `omission` skipped ≈ 3 (was 100; the residual is `all_elements_rejected_by_schema`), `reorder` skipped ≈ 4 (was 19), `template_paraphrase` skipped 0 (was 15), `synonym_label` targets < 49 (every digit-bearing value gone — e.g. no `BANDA DE MANTENIMIENTO / …` or `PROFUNDIDAD / 1,10 m` headings left in `synonym_label.md`), `compression` targets < 46 (no ≤3-word fragments such as `Diurno excepcional` left in `compression.md`).

- [ ] **Step 2: Profile AFTER and diff**

```bash
python -m synthetic.menu_profile > docs/synthetic/sprints/SPRINT_385_profile_after.txt
diff docs/synthetic/sprints/SPRINT_385_profile_before.txt docs/synthetic/sprints/SPRINT_385_profile_after.txt
```
Expected changes: `empty` and `skip` columns drop sharply on the three L3 types; `cands` on omission/reorder/unit_*/num_to_text ≤ 3 × populated targets; `synonym_label`/`compression` target counts down; `paraphrase`, `expansion`, `new_param` **byte-identical** rows (they are untouched — if they moved, something is wrong).

- [ ] **Step 3: Eyeball one recovered TEXTO omission menu**

```bash
grep -n "TEXTO" docs/synthetic/menus/omission.md | head -5
```
Expected: TEXTO headings now followed by `- [ ] 1.` candidate lines whose text starts `Canalización…` (no leading `\`).

- [ ] **Step 4: Confirm nothing but the menus + profile changed**

```bash
git status --short
```
Expected: only `data/synthetic/menus/*.jsonl`, `docs/synthetic/menus/*.md`, and the new `SPRINT_385_profile_after.txt`. The `llm_cache/` directory must be untouched (replay never writes).

- [ ] **Step 5: Commit**

```bash
git add data/synthetic/menus docs/synthetic/menus docs/synthetic/sprints/SPRINT_385_profile_after.txt
git commit -m "Sprint 38.5: regenerate OEB menus offline (recovered L3 TEXTO targets, capped low-entropy types)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Documentation — research log, status, review guidance

**Files:**
- Modify: `docs/synthetic/RESEARCH_LOG.md` (append entry)
- Create: `docs/synthetic/STATUS_2026-08-18.md` (supersedes `STATUS_2026-07-09.md`; leave the old one in place)
- Modify: `docs/synthetic/CLAUDE_SYNTHETIC.md` — the "Known issues / next" line (~line 378) and the module table (add `menu_profile.py`)

- [ ] **Step 1: RESEARCH_LOG entry** — append under the Sprint 38 entries:

```markdown
### 2026-08-18 — Sprint 38.5, F3-prep-2-fix (assessment + offline recovery)

**Assessment of the Sprint 38 menus** (`python -m synthetic.menu_profile`, baseline in
`sprints/SPRINT_385_profile_before.txt`): 127 targets skipped as `malformed_json: Invalid \escape`,
concentrated on TEXTO templates (omission 97/115, reorder 15/24, template_paraphrase 15/24).
Root cause: raw OEB `texto` templates in the stage-2 JSON begin with `\` and `resumen` end with `\`
(FIEBDC field delimiters left by s01); phi4 echoes the backslash inside its JSON string.
127 of the 133 affected cached transcripts parse once stray backslashes are dropped.
Secondary findings: `synonym_label` on digit-bearing values loses the digits (78/78 candidates,
meaning-changing); `compression` on ≤3-word fragments yields no-ops/junk; omission/reorder/unit_*/
num_to_text menus are near-duplicate 10-lists (pairwise token-Jaccard 0.86 on omission).

**Fixes (all cache-neutral, no prompt text changed):** `_parse_json_list` retries after
`_repair_invalid_escapes`; `MENU_CAP_BY_TYPE` post-parse truncation (3 for omission/reorder/
num_to_text/unit_conversion/unit_expansion); `slot_extractor.value_applies` (SYNONYM_LABEL excludes
digits) + `MIN_COMPRESSION_WORDS = 4`. Menus regenerated with `menu_runner replay` — zero GPU.
Before/after: `sprints/SPRINT_385_profile_{before,after}.txt`.

**Deferred (Sprint 40 pre-tasks):** strip the FIEBDC `\` at prompt-build time (changes L3 prompt
hashes → do it when the full chapter is generated fresh); deterministic `unit_conversion` /
`num_to_text` (LLM produced `0,80 m → 8000 mm`); consider scaling `n` with usage count for
high-fan-out targets (e.g. `BANDA DE MANTENIMIENTO / i >= 5 horas`, 21 concepts, 1 candidate).
```

- [ ] **Step 2: `STATUS_2026-08-18.md`** — copy `STATUS_2026-07-09.md`, update the date, replace the "Progress" section's counts with the AFTER profile totals, and replace "Next actions" item 1 with:

```markdown
1. **Manual review of the regenerated menus** (César). Reject-by-default: tick `[x]` to approve.
   Review guidance from the 2026-08-18 assessment:
   - `expansion`: reject candidates that *add facts* ("ideal para áreas urbanas", "asegurando una
     instalación duradera") — the prompt forbids it, phi4 ignores it, the tick is the gate.
   - `synonym_label`: watch domain terms (`Con topo` → `Topográfico` is wrong; a *topo* is a
     tunnelling machine).
   - `unit_conversion`: verify arithmetic (`8000 mm` for `0,80 m` appeared once).
   - `num_to_text`: prefer forms that keep the noun (`Seis tubos`), reject bare `Número seis`.
   Start with `unit_conversion.md` (~2 min) as a warm-up.
```
Keep items 2–6 unchanged.

- [ ] **Step 3: `CLAUDE_SYNTHETIC.md`** — replace the "Known issues / next" line so it points at F3-prep-2-review on the regenerated menus, and add one row to the module table:

```markdown
  menu_profile.py                                 ✅ Sprint 38.5 — read-only per-type scorecard over `data/synthetic/menus/*.jsonl` (targets / empty / candidates / no-ops / dups / skips). `python -m synthetic.menu_profile`. Stdlib only.
```

- [ ] **Step 4: Full suite, then commit**

```bash
pytest tests -q
git add docs/synthetic/RESEARCH_LOG.md docs/synthetic/STATUS_2026-08-18.md docs/synthetic/CLAUDE_SYNTHETIC.md docs/synthetic/sprints/SPRINT_385.md
git commit -m "Sprint 38.5: research log, status refresh, review guidance

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
Expected pytest: previous total (1 018) + ~12 new, 0 failures.

---

## Out of scope / follow-ups (recorded, not done here)

| # | Item | Why deferred | Where it lands |
|---|---|---|---|
| F1 | Strip FIEBDC `\` from `template`/`concept` slots at prompt-build (`slot_extractor._field_text`, `concept_resumen`) | Changes every prompt hash → full live re-run; only worth it when generating fresh | Sprint 40 pre-task |
| F2 | Deterministic `unit_conversion` (m/cm/mm, h/min) and `num_to_text` (`num2words`-style) instead of LLM | Architecture change in `layer_l1` / prompts | Sprint 39 or 40 |
| F3 | Scale `n` with `len(usages)` for high-fan-out targets | Prompt change; small gain | Sprint 40 |
| F4 | Mechanical `expansion` fact-injection guard | No good heuristic; reviewer gate suffices for the pilot | revisit after review acceptance rates |
