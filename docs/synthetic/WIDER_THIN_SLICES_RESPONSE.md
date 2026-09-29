# Response to `bc3cat-retrieval` — wider L2 slices

**Answers:** `bc3cat-retrieval/docs/synthetic-oe/requests/WIDER_THIN_SLICES.md` (S4 work item 7), decided as D-043 (option A)
**Delivered:** 2026-09-29 · **Branch:** `synthetic` · generated at `90a318f`
**Status:** **delivered.** 9 / 9 / 8 dev concepts (paraphrase / expansion / compression), the most
the frozen menus reach.

## File

In `bc3cat-dataset/data/synthetic/handoff_OE/`. New files only: `OE_single_texto.json` is untouched
(sha256 still `b6a43961…d839a`).

| file | content | sha256 |
|---|---|---|
| `OE_single_l2_texto.json` | **1 092 queries**, one L2 modification each | `fff7dd3be023125bc5641ccd9632d2761675d7467eace9ab515ac1d299cd73ce` |
| `OE_single_l2_modifications.jsonl` | modifications sidecar, one row per query | `e1e5adbb8824bd34abe08972c8ed9c66ad6fdf4cf8231c67182026efa7a7cc29` |
| `OE_single_l2_provenance.json` | commit, script, selection rule, both digests | — |

Schema: the SINGLE record schema (`id`, `item_key`, `parent_key`, `gold_item_key`, `ud`, `concept`,
`parameters`, `text`, `modification_types`, `modification_count`). `modification_count` is 1 on
every record, and every modification is visible in the TEXTO (generation fails otherwise).

## Coverage

| type | dev concepts | dev queries | test concepts | test queries |
|---|---:|---:|---:|---:|
| `paraphrase` | **9** | 179 | 11 | 203 |
| `expansion` | **9** | 180 | 11 | 203 |
| `compression` | **8** | 159 | 9 | 168 |

- Dev concepts get 19–20 queries each. Some test concepts have fewer eligible leaves: 3 to 20
  per concept.
- These counts are for the new file alone. Together with `OE_single_texto.json`, the concept
  sets overlap: the 5 dev concepts already in SINGLE are among the 9 / 9 / 8.

## Correction to our first answer

Our first answer gave 9 / 9 / 8 as reachable, and then the first build reached only the 5 dev
concepts SINGLE already had. That check tested that a rewrite is visible in the TEXTO, not that the
render engine could apply it:
- 25 concepts render a text variable in their TEXTO: 8 store it as a conditional formula
  (`"frag"*(%B=a)+…`), 17 as a list indexed by one axis (`$T(2)="…","…"` referenced as `$T(%B)`).
- The engine edited only the formula form, so rules on the 17 list-form concepts rendered as
  no-ops.

The fix (D-043, option A) is described below. With it, the frozen menus reach exactly the 9 / 9 / 8
first measured. The 13 dev / 12 test ceiling would need new menus, which D-043 Q3 ruled out.

## D-043 conditions

### (1) Engine change and reorder fix committed, with tests, before the build — **met**

| commit | content |
|---|---|
| `7bff777` | reorder fix: the placeholder check compares whole calls; `load_pantry` withdraws the 28 stale rules (P7) |
| `90a318f` | list-form L2 rules applied |

**The list-form rule.** In `src/synthetic/bc3param_backend.py`, an L2 rule `%B=b` on a list
variable rewrites element *b*, but only when all of these hold:
- the list is one-dimensional and made of strings, with one element per option of `B`;
- every reference to the variable, anywhere in the concept, is exactly `$T(%B)`.

Anything else (a matrix, a list indexed by two axes, a compound condition, an option out of range)
still skips as before.

The change lives in the synthetic backend. `bc3param`, the engine shared with `main`, is not
modified. Tests: `tests/synthetic/test_bc3param_backend_list_l2.py`. The full suite passes:
1 370 passed, 2 skipped.

### (2) Regression: delivered sets re-rendered with the new engine — **byte-identical**

`scripts/regress_render_replay.py` re-renders every delivered query with the engine at `90a318f`.
It replays the modifications recorded in each query's sidecar and compares the TEXTO byte for byte
with the delivered file.

| file | queries | byte-identical | recorded modification no longer applied |
|---|---:|---:|---:|
| `OE_single_texto.json` | 4 439 | 4 439 | 0 |
| `OE_stacked_texto.json` | 4 998 | 4 998 | 0 |
| `OE_dose_texto.json` | 3 000 | 3 000 | 0 |
| `OE_isolated_texto.json` | 5 400 | 5 400 | 0 |

**Scope of this check.** The replay applies the modifications each query *carries*. A planned
L2 rule on a list-form variable that the old engine skipped left no record, so it is not replayed.
The delivered texts therefore stand as they are, but rebuilding STACKED, dose or isolated from
scratch at a later commit would not reproduce them. Such a rebuild draws from the corrected pantry
(P7) and may apply list-form rules that were skipped before. The delivered files stay reproducible
from their stamped commits.

### (3) Frozen menus only — **confirmed: at most 9 / 9 / 8 dev, and reached**

`data/synthetic/menus_OE` as frozen, no new menu pass. 9 / 9 / 8 dev (11 / 11 / 9 test) is the
maximum under the frozen menus, and the build reaches it. 13 dev / 12 test would need new menus.

## Point by point (original request)

1. **Breadth:** 9 / 9 / 8 dev concepts, against your target of ≥ 15. The target is out of reach
   under this grammar; report it as a limitation in S6.
2. **Depth:** ≤ 20 leaves per concept and type (D-043 Q4). Leaves are taken in a fixed crc32
   order per concept, never a sorted prefix, so they spread across axis values. Each takes the
   least-used compatible rewrite.
3. **New file:** `OE_single_l2_texto.json`. It is additive: 0 `item_key`s and 0 texts are shared
   with `OE_single_texto.json`, and one generated query was dropped because its text was already
   there.
4. **Schema, sidecar, reorder fix:** as above.

## Checks on the delivered file

- Every `gold_item_key` resolves against `OE_texto.json`.
- No query equals its gold TEXTO. No query equals any other leaf's TEXTO, on either split.
- No duplicate keys or texts, and no `$`/`%` residue.
- **Deterministic.** A second full build gave identical digests for both files.

## How to reproduce

```bash
PYTHONPATH=src python scripts/build_single_l2.py --source data/raw/BPA_2026.bc3
PYTHONPATH=src python scripts/regress_render_replay.py --source data/raw/BPA_2026.bc3
```
