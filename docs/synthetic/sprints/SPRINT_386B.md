# Sprint 38.6-B — invariant masking + top-up rounds (addendum) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise candidate survival on long TEXTO templates (OEB010$: 2 → target ≥ 8) by masking the meaning-critical invariants (placeholders + quantities) behind opaque sentinels the LLM cannot corrupt, plus top-up rounds for targets that still finish short — without weakening any gate.

**Architecture:** Approved by César 2026-08-30 (conversation): option 2 (masking) + option 1 (top-up) from the long-template assessment. New single-responsibility module `template_masking.py` (mask/unmask/check, pure functions); `menu_diversity` masks the template slot before rendering, instructs the model to leave `[[..]]` tokens untouched, verifies sentinel integrity on each candidate, restores literals, then runs the FULL existing validator stack on the restored text (belt and braces — gates unchanged). A top-up loop adds R3-style rounds for targets below `MIN_CANDIDATES`. Prompts change → the 60 pilot transcripts in the `menu_OEB_tpar_*` stores go stale (content-addressed; harmless) and the pilot re-runs live (~60 calls).

**Diagnosis being fixed (pilot, 2026-08-30):** 47/180 raw candidates dropped — 23 `placeholders_not_preserved`, 9 `quantities_not_conserved`, concentrated on long templates; all-or-nothing rejection means one corrupt token kills a 150-word rewrite.

**Conventions:** repo root `D:\Users\cesar\Dev\Phd\bc3cat-dataset`, branch `synthetic` (NEVER merge to `main`). Tests: `pytest tests/synthetic -q --basetemp "C:\Users\cesar\AppData\Local\Temp\claude\D--Users-cesar-Dev-Phd-bc3cat-dataset\7bc6b896-cc42-40f9-847f-3e432e8a1b86\scratchpad\ptN"`. Baseline: **1042 passed, 2 skipped**. Commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

## File map

| File | Change |
|---|---|
| `src/synthetic/template_masking.py` | **new** — `mask_invariants`, `unmask`, `check_sentinels` |
| `src/synthetic/menu_diversity.py` | mask slot at render, sentinel instruction in `_wrap_round`, per-candidate unmask+validate, `MIN_CANDIDATES`/top-up loop |
| `tests/synthetic/test_template_masking.py` | **new** |
| `tests/synthetic/test_menu_diversity.py` | wiring + top-up tests (existing scripted-client tests updated for masked prompts) |

---

### Task 1: `template_masking.py`

**Files:**
- Create: `src/synthetic/template_masking.py`
- Test: `tests/synthetic/test_template_masking.py`

- [x] **Step 1: Write the failing tests.** Create `tests/synthetic/test_template_masking.py`:

```python
"""Sprint 38.6-B — hermetic tests for :mod:`synthetic.template_masking`."""
from __future__ import annotations

import pytest

from synthetic.template_masking import check_sentinels, mask_invariants, unmask


_TEMPLATE = (
    "Ejecución de canalización para línea subterránea de doble circuito de "
    "220 ó 400 kV en terreno $A, $B de pavimento, con hormigón HM-20, de "
    "2 m de ancho por 1,60 m de alto, hormigonado a 760 mm, compactado al "
    "95% P.M., 2 ternas de tubos de 250 mm, tetratubos de 4x40 mm. "
    "($L(%C)/$M(%D))"
)


def test_roundtrip_is_identity():
    masked, mapping = mask_invariants(_TEMPLATE)
    assert unmask(masked, mapping) == _TEMPLATE


def test_masked_text_has_no_placeholders_digits_or_units():
    masked, _ = mask_invariants(_TEMPLATE)
    assert "$" not in masked
    # every digit left in the text belongs to a sentinel id [[P3]]/[[Q12]]
    import re
    stripped = re.sub(r"\[\[[PQ]\d+\]\]", "", masked)
    assert not re.search(r"\d", stripped)
    assert " mm" not in stripped and " kV" not in stripped


def test_placeholders_and_quantities_get_distinct_prefixes():
    masked, mapping = mask_invariants("$A de 250 mm ($L(%C))")
    p = [k for k in mapping if k.startswith("P")]
    q = [k for k in mapping if k.startswith("Q")]
    assert len(p) == 2 and len(q) == 1
    assert mapping[q[0]] == "250 mm"


def test_attached_unit_masked_with_its_number():
    masked, mapping = mask_invariants("zanja de 2 m de ancho y 5 At. de presión")
    values = set(mapping.values())
    assert "2 m" in values and "5 At." in values


def test_bare_number_masked_alone():
    _, mapping = mask_invariants("2 ternas de conductos")
    assert "2" in set(mapping.values())
    assert not any("ternas" in v for v in mapping.values())


def test_codes_masked_whole():
    _, mapping = mask_invariants("hormigón HM-20 y tetratubo de 4x40 mm")
    values = set(mapping.values())
    assert "HM-20" in values and "4x40 mm" in values


def test_check_sentinels_passes_on_faithful_text():
    masked, mapping = mask_invariants(_TEMPLATE)
    check_sentinels(masked, mapping)  # no raise


def test_check_sentinels_rejects_dropped_and_duplicated():
    masked, mapping = mask_invariants("$A de 250 mm")
    some = next(iter(mapping))
    with pytest.raises(ValueError, match="sentinels_not_preserved"):
        check_sentinels(masked.replace(f"[[{some}]]", "", 1), mapping)
    with pytest.raises(ValueError, match="sentinels_not_preserved"):
        check_sentinels(masked + f" [[{some}]]", mapping)


def test_check_sentinels_rejects_unknown_sentinel():
    masked, mapping = mask_invariants("$A de 250 mm")
    with pytest.raises(ValueError, match="sentinels_not_preserved"):
        check_sentinels(masked + " [[Q99]]", mapping)
```

- [x] **Step 2: Run to verify failure.** `pytest tests/synthetic/test_template_masking.py -q` → ModuleNotFoundError.

- [x] **Step 3: Implement `src/synthetic/template_masking.py`:**

```python
"""Mask meaning-critical invariants behind opaque sentinels.

Sprint 38.6-B. Long TEXTO templates die in validation because one corrupt
placeholder or digit kills a 150-word rewrite (pilot: 23 placeholder + 9
quantity drops of 47). Instead of asking a 14B model to copy ~15 numbers
and 8 placeholders faithfully at temperature 0.8, we replace them with
sentinels (``[[P1]]``, ``[[Q3]]``) the model is told to leave untouched,
and restore the exact literals afterwards. Quantity and placeholder
preservation become guaranteed by construction; the downstream validators
still run on the restored text as a belt-and-braces check.

Sentinels are ASCII (``[[..]]``) because unicode brackets get normalised
away by some models. ``P`` = placeholder (``$A``, ``$L(%C)``), ``Q`` =
quantity (number, number+unit, or digit-bearing code like ``HM-20``).

Pure functions, stdlib only. Used by :mod:`menu_diversity`.
"""

from __future__ import annotations

import re
from collections import Counter

from .slot_extractor import _UNIT_TOKENS

_PLACEHOLDER_PART = r"\$[A-Za-z0-9]+(?:\(%[A-Z]\))?"
# A whitespace-delimited token containing a digit ("220", "1,60", "HM-20",
# "4x40"), optionally followed by one unit word from the shared unit
# vocabulary ("m", "mm", "kV", "At."), which travels with its number.
_QUANTITY_PART = r"[^\s\[\]]*\d[^\s\[\]]*(?:\s+(?P<unit>[^\s\d\[\]]+?)\.?(?=\s|$|[,;:)]))?"

_MASK_RE = re.compile(rf"(?P<ph>{_PLACEHOLDER_PART})|(?P<qty>{_QUANTITY_PART})")
_SENTINEL_RE = re.compile(r"\[\[([PQ]\d+)\]\]")


def mask_invariants(text: str) -> tuple[str, dict[str, str]]:
    """Replace placeholders and quantities with ``[[Pn]]``/``[[Qn]]``.

    Returns ``(masked_text, mapping)`` where ``mapping`` maps sentinel id
    ("P1", "Q2", …) to the exact literal it replaced. Single combined
    pass so inserted sentinel digits are never re-masked. A trailing unit
    word is included in the quantity literal only if it is in
    :data:`slot_extractor._UNIT_TOKENS` (case-insensitive, optional dot).
    """
    mapping: dict[str, str] = {}
    counters = {"P": 0, "Q": 0}

    def _sub(m: re.Match) -> str:
        if m.group("ph") is not None:
            kind, literal = "P", m.group("ph")
        else:
            kind, literal = "Q", m.group("qty")
            unit = m.group("unit")
            if unit is not None and unit.lower() not in _UNIT_TOKENS:
                # The peeked word is not a unit — put it back.
                literal = literal[: literal.rfind(unit)].rstrip()
                trailing = m.group("qty")[len(literal):]
                counters[kind] += 1
                sid = f"{kind}{counters[kind]}"
                mapping[sid] = literal
                return f"[[{sid}]]{trailing}"
        counters[kind] += 1
        sid = f"{kind}{counters[kind]}"
        mapping[sid] = literal
        return f"[[{sid}]]"

    return _MASK_RE.sub(_sub, text), mapping


def unmask(text: str, mapping: dict[str, str]) -> str:
    """Restore the exact literals. Unknown sentinels are left in place —
    call :func:`check_sentinels` first to fail loud on them."""
    return _SENTINEL_RE.sub(lambda m: mapping.get(m.group(1), m.group(0)), text)


def check_sentinels(text: str, mapping: dict[str, str]) -> None:
    """Every sentinel of ``mapping`` exactly once in ``text``, and no
    sentinel that is not in ``mapping``. Raises ``ValueError`` starting
    with ``sentinels_not_preserved`` otherwise."""
    found = Counter(_SENTINEL_RE.findall(text))
    expected = Counter(mapping.keys())
    if found != expected:
        missing = sorted((expected - found).keys())
        extra = sorted((found - expected).keys())
        raise ValueError(
            f"sentinels_not_preserved: missing={missing} extra_or_dup={extra}"
        )
```

**Implementation note (regex subtlety):** the `(?P<unit>…)` group peeks the next word; the callback re-checks it against `_UNIT_TOKENS` and, when it is NOT a unit ("2 ternas"), re-emits it outside the sentinel. If wrangling the lookahead regex proves brittle against the tests, an equivalent two-step tokenizer (split on whitespace, join back) is acceptable — **the tests are the contract, not the regex**; keep the public API identical.

- [x] **Step 4: Run tests.** `pytest tests/synthetic/test_template_masking.py -q` → all pass. Also run a round-trip probe over the real catalog: for every OEB `resumen`/`texto` in `data/intermediate/OBRA CIVIL/OBRA CIVIL.json` (after `_strip_fiebdc`-style edge cleanup), assert `unmask(*mask_invariants(t)) == t`; report the count checked (~50). A single failure → fix before proceeding.

- [x] **Step 5: Commit.**

```bash
git add src/synthetic/template_masking.py tests/synthetic/test_template_masking.py
git commit -m "Sprint 38.6-B: template_masking — sentinel mask/unmask/check for placeholders and quantities

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Wire masking into `menu_diversity`

**Files:**
- Modify: `src/synthetic/menu_diversity.py` (read the CURRENT file first — it has evolved past the SPRINT_386.md listing: `_model_store_tag` is full-string, the parse `try` is narrow, the CLI prints an `empty` count)
- Test: `tests/synthetic/test_menu_diversity.py`

- [x] **Step 1: Failing tests.** Update/extend `tests/synthetic/test_menu_diversity.py`. The scripted clients' queued responses must now echo the MASKED original (the tests can compute it via `mask_invariants` on the sanitized template) and produce `new` texts containing the sentinels. Add:

```python
def test_prompts_carry_masked_template_and_sentinel_instruction():
    # After wiring: the rendered prompt must contain [[P/Q]] sentinels and
    # the leave-untouched instruction, and no raw '$' placeholders.
    ...  # assert on client.prompts[0]: "[[" in p; "$A" not in p; "No modifiques" in p


def test_candidate_with_dropped_sentinel_is_rejected():
    ...  # queue a response whose "new" omits one [[Qn]] -> dropped_reasons contains "sentinels_not_preserved"


def test_surviving_candidate_is_unmasked_and_validated():
    ...  # queue a faithful response -> stored payload["new"] contains the restored literals
         # ("250 mm" etc.), no "[[" anywhere in payload, and payload["original"] equals the
         # sanitized (unmasked) template
```

Write these three tests fully (no `...` in the real file), reusing the file's `_ScriptedClient` and `_STAGE` fixtures; derive expected masked strings by importing `mask_invariants` rather than hardcoding sentinel ids.

- [x] **Step 2: Verify failure.** New tests fail (prompt has `$A`, no sentinel path exists).

- [x] **Step 3: Implement in `menu_diversity.py`.**

1. Import: `from .template_masking import check_sentinels, mask_invariants, unmask`.
2. In `_sanitized_slots` (or a wrapper around it), after stripping FIEBDC: `masked_template, mapping = mask_invariants(slots["template"])`; put `masked_template` into `slots["template"]`, recompute the `placeholders` slot from the masked text as the sentinel list (`", ".join(f"[[{k}]]" for k in mapping)`) so the prompt's own placeholder line refers to what the model actually sees; return `(slots, mapping, true_template)` where `true_template` is the pre-mask sanitized template.
3. In `_wrap_round`, add one constant line to `parts` (after the conservation line):
   `"Los tokens [[P1]], [[Q2]], … son marcadores intocables: no los modifiques, elimines, dupliques ni traduzcas; colócalos donde correspondan en tu reescritura."`
4. Replace the per-candidate validation: after `_parse_json_list`, for each raw element `elem`:
   - shape check: must be a dict with a string `new` (else drop `not_a_dict`/`missing_key: 'new'`);
   - `check_sentinels(elem["new"], mapping)` → on ValueError drop with `f"{model_tag}/{round_.tag} [i] {err}"`;
   - build the restored payload: `restored = {**elem, "original": true_template, "new": unmask(elem["new"], mapping)}` (overwrite the model's echoed `original` with the known true template — echo sloppiness must not matter); default `restored.setdefault("preserves_meaning", True)` is NOT allowed — if the key is missing the schema validator drops it, as before;
   - run `_validate_payload(restored, MTYPE)` (import from `variant_proposer`) → on ValueError drop;
   - `_is_prompt_echo(restored)` (import from `menu_proposer`) → drop `prompt_scaffold_echo`;
   - keep `restored` in `model_keeps`.
   This replaces the previous `_validate_variants` call (which bundled the same checks pre-unmask); `_forbidden_openings` now naturally sees restored text.
5. `propose_diverse` keeps its signature; pooling/dedup/similarity-gate/CandidateSet construction unchanged.

- [x] **Step 4: Run.** `pytest tests/synthetic/test_menu_diversity.py tests/synthetic -q` → all green (existing diversity tests updated in Step 1; nothing else should move).

- [x] **Step 5: Commit** (`src/synthetic/menu_diversity.py`, `tests/synthetic/test_menu_diversity.py`):

```bash
git commit -m "Sprint 38.6-B: mask invariants in template_paraphrase prompts, validate on restored text

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Top-up rounds

**Files:**
- Modify: `src/synthetic/menu_diversity.py`
- Test: `tests/synthetic/test_menu_diversity.py`

- [x] **Step 1: Failing test.**

```python
def test_topup_rounds_fire_until_min_candidates():
    # Scripted: R1-R3 for the one model yield only 1 survivor total; the two
    # top-up rounds (tags T1, T2) each yield 3 more -> stops at >= MIN_CANDIDATES.
    # Assert: client received 5 prompts for the TEXTO target (R1,R2,R3,T1,T2),
    # T-prompts contain "T1"/"T2" tags, final candidates >= MIN_CANDIDATES.


def test_no_topup_when_enough_candidates():
    # R1-R3 already yield >= MIN_CANDIDATES -> exactly 3 prompts per model.
```

(Write fully with the scripted client; MIN_CANDIDATES is importable.)

- [x] **Step 2: Implement.** In `menu_diversity.py`:

```python
MIN_CANDIDATES: int = 6
MAX_TOPUP_ROUNDS: int = 2
```

After the base rounds for a target (all models pooled, deduped, gated), while `len(gated) < MIN_CANDIDATES` and top-ups used `< MAX_TOPUP_ROUNDS`: run one extra round per model with `Round(tag=f"T{k}", instructions=ROUNDS[2].instructions, wants_forbidden_openings=True)` (free-restructure style; forbidden openings from ALL current keeps of that model plus pooled keeps), validate identically, re-pool, re-dedupe, re-gate. Deterministic: the decision depends only on validated counts, which replay reproduces. Structure it so the base-rounds logic is not duplicated (extract a `_run_round(client, model_tag, round_, rendered, mapping, true_template, n)` helper if needed).

- [x] **Step 3: Run full suite, commit** (`Sprint 38.6-B: top-up rounds to MIN_CANDIDATES=6`, same trailer).

---

### Task 4: Re-pilot + comparison  **[CHECKPOINT: report to César before the full run]**

- [x] **Step 1:** Two-phase pilot, same 5 concepts, same commands as the 2026-08-30 pilot (phase 1 `--models phi4:latest`, phase 2 `--models phi4:latest,qwen2.5:14b`), `--out-machine data/synthetic/menus_pilot --out-review docs/synthetic/menus_pilot`. All prompts are new (masked) → fully live (~60+ calls + top-ups; budget 20–35 min).
- [x] **Step 2:** Compare against the pre-masking pilot (the "pilot diversity run (5 concepts, phi4+qwen, two-phase)" commit — its data/synthetic/menus_pilot/template_paraphrase.jsonl; retrieve via `git show <sha>:...` after finding it with `git log --oneline -5`): `menu_profile --menus-dir data/synthetic/menus_pilot` row, drop breakdown by reason, per-target survivor counts — **OEB010$ TEXTO ≥ 8 is the headline number**; `p_sim ≤ 0.55` and `d_orig ≥ 0.45` must still hold on the restored texts; sentinel leak check: `grep -c '\[\[' data/synthetic/menus_pilot/template_paraphrase.jsonl` → 0.
- [x] **Step 3:** Commit pilot artefacts + stores; **STOP and report to César** (survivors before/after per target, metrics, 2–3 samples from OEB010$). The full run and docs (SPRINT_386.md Tasks 6–7) proceed only on his go.

---

## Notes

- The 60 pre-masking pilot transcripts stay in the stores (content-addressed, unused). Do not delete — they document the pre-masking behaviour.
- The quantity gate (`_require_quantities_conserved`) still runs on restored text and should now approach zero drops for this type; if it fires post-masking, that's a masking bug — investigate, don't relax the gate.
- `reorder`/all other types are untouched — masking lives only in the diversity path.
