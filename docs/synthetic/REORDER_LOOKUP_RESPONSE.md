# Response to `bc3cat-retrieval` — `reorder` permutes lookup arguments (P7)

**Answers:** `bc3cat-retrieval/docs/synthetic-oe/requests/REORDER_LOOKUP_ARGUMENTS.md` (`DATASET_DEFECTS.md` P7)
**Answered:** 2026-09-29 · **Branch:** `synthetic` · fix committed in `7bff777`. Exclusion list
(D-043 Q1): `handoff_OE/OE_P7_test_exclusion.json`, sha256 `96fe3854…a011`
**Status:** fix and test in place, rules withdrawn for future builds. **No re-delivery.**
`OE_single_texto.json` is untouched: sha256 still `b6a43961…d839a`.

## Summary

Your diagnosis is confirmed. The fixed check also finds a second kind of broken rule that your
test cannot see. It affects **2 test-split SINGLE queries** (§2). No delivered artefact was
rendered from the `$U` permutations (§3).

## Point by point

### §1 Fix the validator, add a test, withdraw the rules — **done**

**Validator.** `src/synthetic/variant_proposer.py`, `_PLACEHOLDER_RE`: a placeholder is now the
**whole call, arguments in order**. Two things changed beyond your suggested regex:
- Arguments may be axes (`%B`) **or literal rows** (`b` in `$L(b,%C)`). The OE menus use both.
  With axes only, `$L(b,%C)` would still reduce to `$L`, and a rule could swap row `b` for row
  `c` unnoticed.
- Whitespace inside the call is dropped before comparing. The menus contain both `$T(%A,%B,%C)`
  and `$T(%A, %B, %C)`, so the old check was not the only thing letting them through.

The same check guards `reorder`, `template_paraphrase` and `omission`, so all three are fixed.

**Tests.**
- `tests/synthetic/test_reorder_lookup_arguments.py`: all three permutations of `$T(%A,%B,%C)`,
  plus the spaced form, rejected for `reorder` and `template_paraphrase`. A permuted literal
  row is rejected. Moving a multi-argument call intact is still a valid reorder.
- `tests/synthetic/test_pantry.py::test_load_pantry_withdraws_stale_lookup_permutations`.

`tests/synthetic`: 1 236 passed, 2 skipped.

**Withdrawal.** The verdict files were approved before this check existed, and nothing re-checked
them. `load_pantry` (`src/synthetic/pantry.py`) is the single entry point every builder uses to
read them. It now re-runs the check on each approved `reorder`/`template_paraphrase` rewrite and
drops any that fail. The verdict files themselves are unchanged, so the audit trail stays intact.

The fixed check rejects **28 approved rules**, more than the six `$T`/`$U` permutations:

| type | rejected | what they do |
|---|---:|---|
| `reorder` | 9 | the 3 `$T` and 3 `$U` permutations you found; the rest change or drop a literal lookup row |
| `template_paraphrase` | 16 | rewrite `$T(%A,%B,%C)` / `$U(%A,%B,%C)` into prose with a bare `$T` and literal `%A`, `%B`, `%C` |
| `omission` | 3 | same kind of damage; `omission` is excluded from every delivered corpus |

Future builds will not sample any of them. They also shift seeded draws for the concepts
that carried them. A rebuild of STACKED, dose or isolated from a later commit is therefore
not byte-identical to the delivered files, which stay reproducible from their stamped commits.

### §2 Test-split check — **2 test queries affected, but not by the test you proposed**

Script: `scripts/audit_lookup_permutations.py`. It prints counts only.

**Your test** (query text equals the TEXTO of a non-gold leaf). D-031 groups are excluded: a leaf
sharing the gold's TEXTO does not count.

| file | dev | test |
|---|---:|---:|
| `OE_single_texto.json` | 1 of 2 206 | **0** of 2 233 |
| `OE_stacked_texto.json` | 0 of 2 521 | 0 of 2 477 |
| `OE_dose_texto.json` | 0 of 1 640 | 0 of 1 360 |
| `OE_isolated_texto.json` | 0 of 2 952 | 0 of 2 448 |

The dev count reproduces your finding exactly.

**Queries built from a withdrawn rule**, from the sidecars:

| sidecar | dev | test |
|---|---:|---:|
| `processed_OE_ablation_single` (SINGLE) | 1 (`reorder`, TEXTO: the one you found) | **2** (`reorder`, TEXTO) |
| `processed_OE_ablation_stacked` (STACKED) | 0 | 0 |
| `processed_OE_dose` (dose) | 0 | 0 |
| `processed_OE_probe` (isolated) | 0 | 0 |

The **2 test queries** use one withdrawn `reorder` rule. It does not permute a call: it replaces
one literal lookup row with another and drops a field. The query therefore matches no leaf's TEXTO
and passes your test. It is still not a referent-preserving rendering: part of it describes a row
the gold leaf does not have. We recommend treating both queries as you treat P7: out of item-level
scoring, kept at parent level.

As asked, this response gives no examples, concepts or keys. To exclude the two at scoring time you
need their `item_key`s. The key-only list is `handoff_OE/OE_P7_test_exclusion.json` (sent on request, D-043 Q1).

### §3 RESUMEN side (`$U`) — **no delivered artefact affected**

Queries are TEXTO only, and `OE_resumen.json` holds original RESUMENs. STACKED is the only
delivered corpus that applies a RESUMEN-field rewrite, and **0** of its records use a `$U`
permutation (table above). The dose and isolated sets are restricted to TEXTO-field rewrites.

One `$U` permutation was applied, on one dev item of the Sprint-39 corpus (`processed_OE`). That
corpus is internal and was never in `handoff_OE`. It also carries one test-split TEXTO item built
from a withdrawn rule. Neither reaches you.

## How to reproduce

```bash
python -m pytest tests/synthetic/test_reorder_lookup_arguments.py tests/synthetic/test_pantry.py
python scripts/audit_lookup_permutations.py ../bc3cat-retrieval/docs/synthetic-oe/SPLITS.md
```
