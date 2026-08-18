# Sprint 26 — Phase B Task B6 (L2 text-variable representation adapter: fix the silent L2 no-op on real data, all shapes)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 26                                                                                          |
| **Date**        | 2026-05-20                                                                                  |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | B6 (new — L2 real-data representation adapter). Surfaced while selecting the F1 pilot concept. |
| **Predecessor** | Sprint 25 — A3b-build spike harness (`spike.py`) + the A3b-run model decision (local `llama3.1:8b`) (see [`SPRINT_25.md`](SPRINT_25.md)) |
| **Successor**   | Sprint 27 — **F1** single-concept pilot, now covering **all 12** modification types (see [`SPRINT_27.md`](SPRINT_27.md)) |

---

## Context

While picking the F1 pilot concept I found the synthetic **L2 layer** (paraphrase
/ expansion / compression) produces **zero** modifications on most real catalog
data — silently. The L2 path (`slot_extractor.enumerate_targets` +
`_parse_l2_formula`, `layer_l2._replace_fragment`) addresses text-variables by a
`"FRAGMENT" * (%AXIS=label)` **formula string**, but `enumerate_targets` skips any
non-string (`if not isinstance(formula, str): continue`).

Real text-variables come in **three shapes** (verified across the OEB chapter),
and the rerun form each needs is decided by **how the template references it**:

| shape | example | template ref | rerun needs | enumerate sees it? |
|---|---|---|---|---|
| `LIST_plain` | `$L = ['"Diurno"', '"Nocturno"', …]` | indexed `$L(%B)` | positional **list** (s05 indexes by axis value) | **no** (it's a list) |
| `STR_formula` | `$K = '"normal" * (%B=="a") + …'` | bare `$K` | **formula string** (s04 evaluates per leaf) | yes |
| `LIST_conditional` | `$P = ['"…prose…" * (%B=="f")', …]` | bare `$P` | **list** of conditional fragments | **no** (it's a list) |

So `LIST_plain` and `LIST_conditional` were silently un-enumerable (and on the OEB
chapter that's ~96 of ~117 L2 vars). The L2 unit tests passed only because their
fixtures used the formula-string form the real pipeline never emits for those.

**The rerun is unforgiving about shape (empirically verified).** Feeding the wrong
form to `stage_runners.run_stages_3_to_7` corrupts output: a `LIST_plain` as a
formula mangles s05's positional index; a `STR_formula` collapsed to a list yields
the first value on every leaf; and a `LIST_conditional` joined into one formula
changes which leaves render — so **baseline faithfulness is lost** (BC3CAT-Syn
must reproduce the original byte-for-byte). Each shape must be restored exactly.

### Why B6 before F1

L2 is 3 of the 12 modification types. Running F1 without it would generate a pilot
that silently looks "L2-complete" while covering 9/12 — exactly the quiet gap the
pilot exists to prevent. Fixing it first (its own sprint) lets F1 exercise all 12.

### The load-bearing design decisions

1. **A reference-style-aware adapter — not a seam edit.** A new pure module
   `src/synthetic/l2_repr.py` makes all three shapes enumerable for Stage A and
   restores each to its rerun-faithful form for Stage B. It imports
   `slot_extractor`/`taxonomy` + stdlib and is **never imported by** any seam
   module; `slot_extractor`/`layer_l2`/`rule_emitter` are untouched.
2. **Two conversion modes, because enumeration and the rerun want different
   things.**
   - `list_to_formula(stage_json, include_conditional=True)` — for **enumeration
     only**: every L2 var becomes a parseable formula string (`LIST_plain` paired
     with its axis values, `LIST_conditional` elements joined **verbatim**,
     `STR_formula` passthrough). Its output feeds `run_concept`; it is never
     rerun.
   - `list_to_formula(…, include_conditional=False)` — for **application**: only
     `LIST_plain` is converted; `STR_formula` and `LIST_conditional` keep their
     native shape so `layer_l2` mutates them **in place** and they stay
     byte-faithful through the rerun.
   - `formula_to_list(stage_json)` — restores **only indexed-referenced**
     (`$VAR(%AXIS)`) formula strings to positional lists. Bare-referenced
     `STR_formula` (mutated as strings) and native `LIST_conditional` lists are
     left exactly as-is. Self-contained (reference style read from the template).
3. **Condition format.** `LIST_plain` → emitted `%AXIS=label`; `LIST_conditional`
   conditions are joined **verbatim** (e.g. `%B=="f"`), so a rule proposed off the
   joined formula round-trips against the native list element unchanged.
4. **Nothing silent.** Every var is recorded with a reason (`converted`,
   `joined_conditional`, `native_conditional`, `already_formula`, `unreferenced`,
   `multi_axis_conflict`, `length_mismatch`, `embedded_quote`, `unsupported_shape`).
   Malformed embedded-quote values (real `$M`) are left native and recorded, not
   half-converted.
5. **A silent-no-op guard.** `assert_l2_targets_or_warn` warns when vars were made
   enumerable but L2 still finds zero targets — this whole bug would have tripped
   it.

---

## Scope

### In scope

- **B6-1 — `src/synthetic/l2_repr.py`:** `derive_var_axis_map`,
  `list_to_formula(stage_json, *, include_conditional=True) -> (converted, report)`,
  `formula_to_list(stage_json)`, `assert_l2_targets_or_warn(stage_json)`. Pure,
  deep-copying, stdlib + `slot_extractor`/`taxonomy` only.
- **B6-2 — tests:** `tests/synthetic/test_l2_repr.py` (20) +
  `tests/synthetic/test_l2_integration.py` (8) — all hermetic, including the
  byte-faithful baseline through `run_stages_3_to_7` and mutated round-trips for
  both `LIST_plain` and `LIST_conditional`.
- **Doc + housekeeping:** this file; `RESEARCH_LOG.md`; `CLAUDE_SYNTHETIC.md`;
  `RESEARCH_PROTOCOL.md` §3.5/§5; renumber the F1 draft → `SPRINT_27.md`.

### Out of scope (explicit)

- **Editing the frozen seam.** No change to `slot_extractor`/`layer_l2`/
  `rule_emitter`/`run_synthetic`/`stage_runners`/`stage_b`/etc. The F1 driver
  composes the public functions.
- **The other silent-failure spots.** Two *error-swallowing* risks (a different
  class) — `stage_runners` s04 `evaluate_formula`'s bare `except`, and
  `stage_b.apply_variant_rules`'s skip-and-log — are a documented follow-up.
- **Running F1.** B6 unblocks L2; the pilot is Sprint 27.
- **Merging `synthetic` to `main`.** Permanently forbidden.

---

## Acceptance (met)

- `src/synthetic/l2_repr.py` + the two test files exist; **no seam file changed**
  (`git diff` clean; the pre-existing `mutator.py` working-tree diff is unrelated
  Phase-B stub-promotion, not this sprint).
- All three shapes become enumerable for Stage A; the bare-referenced
  `STR_formula` is **not** corrupted by `formula_to_list` (the latent bug a list
  conversion would have caused).
- **Byte-faithful baseline:** the unmutated apply-mode round-trip
  (`list_to_formula(include_conditional=False)` → `formula_to_list`) reproduces the
  original `run_stages_3_to_7` output **identically** — verified on real `OEB020$`
  (all three shapes, 4608 leaves, dict-equal).
- On real `OEB020$`: enumerable PARAPHRASE targets **20 → 31** after
  `list_to_formula` (adds the `LIST_plain` and `LIST_conditional` vars; embedded
  -quote `$H`/`$M` left native and recorded). On `OEB070$`: **0 → 9**.
- Mutated round-trips land in the expected leaves for both a `LIST_plain` var
  (`"Diurno"→"DIA_X"`, 24/144 leaves) and a `LIST_conditional` var (applied
  natively).
- `pytest tests -q` → **794 passed, 2 skipped** (Sprint-25 baseline 766 + 28 new
  hermetic), zero failures, **zero network calls**.

---

## Tasks (done)

1. `src/synthetic/l2_repr.py` — the reference-style-aware bidirectional adapter +
   guard, with the `include_conditional` mode flag.
2. `tests/synthetic/test_l2_repr.py` (20) + `tests/synthetic/test_l2_integration.py` (8).
3. Housekeeping: this file; `RESEARCH_LOG.md`; `CLAUDE_SYNTHETIC.md`;
   `RESEARCH_PROTOCOL.md` §3.5/§5; renumber F1 → `SPRINT_27.md`.

---

## Verification runbook

```powershell
$env:PYTHONPATH = "src"
pytest tests -q --basetemp="$env:TEMP\pt_s26"
# → 794 passed, 2 skipped, zero failures, zero network.

# All three shapes enumerable + byte-faithful baseline on OEB020$:
python -c "import json; from synthetic.l2_repr import list_to_formula, formula_to_list; from synthetic.stage_runners import run_stages_3_to_7; d=json.load(open('data/intermediate/OBRA CIVIL/OBRA CIVIL.json',encoding='utf-8')); k='OEB020$'; c={k:d[k]}; appl,_=list_to_formula(c,include_conditional=False); print('faithful:', run_stages_3_to_7(formula_to_list(appl))==run_stages_3_to_7(c))"
# → faithful: True

git diff --stat -- src/synthetic/slot_extractor.py src/synthetic/layer_l2.py `
  src/synthetic/rule_emitter.py src/synthetic/run_synthetic.py `
  src/synthetic/stage_runners.py src/synthetic/stage_b.py   # empty
```

---

## Design notes worth committing to memory

- **Three shapes, not two.** `LIST_plain` (indexed), `STR_formula` (bare),
  `LIST_conditional` (bare). The template **reference style** decides the
  rerun-faithful form; my first cut handled only the first and would have
  corrupted the bare `STR_formula` vars by listifying them.
- **Two conversion modes.** Enumeration wants every var as a string; the rerun
  wants each var in its native form. `include_conditional=True` for `run_concept`,
  `False` for `apply_variant_rules`; `formula_to_list` restores only
  indexed-referenced (`LIST_plain`) vars.
- **Byte-faithfulness is the gate.** BC3CAT-Syn baselines must reproduce the
  original; restoring each shape exactly (verified dict-equal on 4608 leaves) is
  what makes that hold. A joined `LIST_conditional` formula would have silently
  changed which leaves render.
- **A guard makes the next drift loud** (`assert_l2_targets_or_warn`).

---

## References

- [`SPRINT_27.md`](SPRINT_27.md) — F1, now all 12 types; its driver brackets the
  mutation with `list_to_formula`/`formula_to_list`.
- [`../../src/synthetic/l2_repr.py`](../../src/synthetic/l2_repr.py) — the adapter.
- [`../../src/synthetic/slot_extractor.py`](../../src/synthetic/slot_extractor.py)
  / [`layer_l2.py`](../../src/synthetic/layer_l2.py) — the frozen L2 path
  (`_L2_FORMULA_RE` / `_FRAGMENT_PAT`; `layer_l2` natively mutates `STR_formula`
  and `LIST_conditional`, rejects `LIST_plain`).
- [`../../src/synthetic/stage_runners.py`](../../src/synthetic/stage_runners.py) —
  the s04/s05 rerun whose reference-style-dependent handling forces the design.
- [`../../CLAUDE.md`](../../CLAUDE.md) — never-merge-`synthetic`-to-`main`.

---

## Non-goals reminder

If you find yourself editing `slot_extractor`/`layer_l2`/`rule_emitter`/
`stage_runners`/`stage_b` — **stop**. B6 is a *new* adapter the F1 driver composes.

If you find yourself applying the mutation on the `include_conditional=True`
concept — **stop**. That joins `LIST_conditional` into a formula, which the rerun
renders unfaithfully. Apply on the `include_conditional=False` concept so those
vars mutate natively.

If you find yourself fixing the `stage_runners` bare-`except` here — **stop**.
That error-swallowing risk is a documented separate follow-up, not B6.
