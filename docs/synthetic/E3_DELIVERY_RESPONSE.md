# Response to `bc3cat-retrieval` — E3 balanced dose set

**Answers:** `bc3cat-retrieval/docs/synthetic-oe/requests/E3_BALANCED_DOSE.md` (D-009)
**Delivered:** 2026-09-17 · `run_id` `e3-20260917T093057Z`
**Branch:** `synthetic` (local; see the note on pushing at the end) · delivery commit `4d10af2`, generated at `e057907`
**Status:** delivered, with two limitations you need before planning S8 (§3 and "Limitations").

## Files

All in `bc3cat-dataset/data/synthetic/handoff_OE/`:

| file | content | sha256 |
|---|---|---|
| `OE_dose_texto.json` | **3 000 queries**: 600 leaves × counts 1–5 | `555fab84d134886f85ece40115ffd485e796fd4e96291e6a9af3129004a80819` |
| `OE_isolated_texto.json` | **5 400 queries**: each of the 9 types alone, on **the same 600 leaves** | `054041ff05349fae79fd5b91ff111f4fe574b37f7f8ee9647cea044503c5e3ce` |
| `OE_leaf_applicability.jsonl` | one row per probed leaf (1 500): `applicable_types`, `available_types`, `in_pool` | `eda12d17c323add48a7d8deac0f93e767188824950357303b497a7ca8d3fbaa3` |
| `MANIFEST.md`, `provenance.json` | digests, seed, commit, config path | — |

Modification sidecars (§6), same format as STACKED/SINGLE:
`data/synthetic/processed_OE_dose/BC3CAT_Syn_modifications.jsonl` (`4e4c3741…d415e`) and
`data/synthetic/processed_OE_probe/BC3CAT_Syn_modifications.jsonl` (`983228e4…47726`).
The probe release covers all 1 500 probed leaves. The isolated set is its restriction to the
600 ladder leaves.

## Point by point

### §1 Dose ladder, composition not fixed — **met, with two exclusive pairs**

Counts 1–5, the nine admitted types (`omission` and `new_param` excluded). Composition is not
fixed. It is chosen per leaf by a deterministic balancing draw: the leaf's own seeded shuffle,
then least-used-first across leaves.

- `reorder` is admitted and co-occurs with the other seven types (in `dose_5`: 173–203
  items each, 84 with `unit_conversion`).
- `template_paraphrase` is not forced: it appears in 300 of 600 items at count 5.

**Two pairs never co-occur, by construction:** `reorder` × `template_paraphrase` (both rewrite
the TEXTO template) and `unit_conversion` × `unit_expansion` (both rewrite the same parameter
value). Every modification in an item sits on a distinct text span, so these two interactions
are **not identifiable** from this set.

### §2 Within-leaf ladder — **met in full**

All 600 leaves carry the complete ladder 1–5. It is **nested**: the types at count *k* are the
types at count *k*−1 plus one. Consecutive counts on the same leaf therefore differ by exactly
one modification, which also supports paired contrasts, not just a within-item slope.

### §3 Balance — **counts met; "across counts" is not achievable as worded**

- Exactly **600 queries per count**, all over the same 600 leaves.
- *Even type rates across counts* cannot hold for any dose ladder: with *k* types drawn from a
  repertoire of *d*, each type's presence rate grows with *k*. That is the dose itself, not a
  bias. What protects the inference is **balance within each count cell**, and that holds for
  eight of the nine types. At count 1, for example, each type appears in 70–71 items.
- **`unit_conversion` is under-represented**: 39 items at count 1 and 160 at count 5, against
  ~300–390 for the others. In these concepts it has only 4 distinct approved rewrites. Each
  rewrite is capped at 40 uses (also for `num_to_text` and `unit_expansion`), so that an effect
  estimated for a type does not come down to one repeated edit. Without caps, one
  `unit_conversion` rewrite would repeat 107 times.

Per-cell presence tables: `docs/synthetic/OE_dose_report.md`.

### §4 Applicability per item — **met, as two fields**

Each record carries:
- `applicable_types`: types the grammar admits for the leaf;
- `available_types`: types with an approved rewrite that actually changes that leaf's TEXTO.

Both are independent of reuse caps, so they describe the population rather than our run.
For the 600 ladder leaves, `available_types` has all 9 types.

### §5 Schema — **identical**, plus the two §4 fields

`item_key`, `parent_key` (present on every record), `gold_item_key`, `ud`, `concept`,
`parameters`, `text`, `modification_types`, `modification_count`, `applicable_types`,
`available_types`. Verified: **all 8 400 `gold_item_key` resolve** against the delivered OE
corpus (70 242 leaves). Gold convention unchanged: query = modified TEXTO, target = original
TEXTO.

### §6 Provenance — **met**

Seed **42**, script `scripts/build_dose_ladder.py`, config
`configs/synthetic/variant_budgets_OE_dose.yaml`. The config's sha256 is
`2c21d69f4343aed5d9a17589180229e91c96310681ac326331a64360e0429fa4` as committed (LF). A
Windows checkout with autocrlf reads it as `3e2b4e7f…9bc2`. Code commit `e057907`. The run is
**reproducible byte for byte**: a second full run gave identical digests for all five output
files.

## Limitations to carry into S8

1. **Concept coverage: 7 of 83 concepts**, all OEB canalizations: `OEB020$` (61 leaves),
   `OEB030$` (87), `OEB040$` (96), `OEB230$` (93), `OEB280$` (87), `OEB290$` (87),
   `OEB300$` (89). Your dev/test split by concept can only partition these seven.

   This is structural. A clean count-5 cell needs leaves with at least 6 available types (so
   that composition at count 5 is still drawn) and 5 of them on distinct spans of the TEXTO.
   Only these families have such leaves. We chose not to relax the criterion: with exactly 5
   types, composition at count 5 is fixed and the confound of §1 of your request comes back in
   the cell that matters most.

   Within each concept, the ladder covers all values of every parameter axis.
2. The two non-identifiable interactions of §1.
3. `unit_conversion` presence (§3).

## Please re-check STACKED counts before relying on them

While building this set we found a defect that also affects the **already delivered STACKED
set**. The compatibility rule matches strings, not text variables. A rewrite of a variable
used only in the RESUMEN was counted whenever the same phrase appears in the TEXTO through
another variable (e.g. `$K` "bajo vías" vs `$I` "en cruce bajo vías"). Such a modification is
applied and counted, but it does not change the query.

A first audit of STACKED finds **~1 800 counted modifications not visible in the TEXTO**,
mostly `paraphrase` and `expansion`. For many items, `modification_count` therefore overstates
the dose seen by the retriever. That bears directly on S2's stacked results and on any H4
regression run on STACKED.

The texts themselves are correct; only the counts and type lists are affected. A precise
audit and a corrected sidecar are being prepared on our side. SINGLE is not expected to be
affected, since each item carries one modification that must change the TEXTO, but that will
be verified too.

The E3 files above are **not** affected: every counted modification was checked against the
TEXTO, and generation fails if any is not visible.
