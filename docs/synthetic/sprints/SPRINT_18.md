# Sprint 18 — Phase D Tasks D2 (Stage-B half) + D3 (cache hygiene)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 18                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | D2 (Stage-B half), D3 (see [`../RESEARCH_PROTOCOL.md §5 Phase D`](../RESEARCH_PROTOCOL.md)) |
| **Predecessor** | Sprint 17 — `stage_runners.py` (D1: in-memory pure stage runners + golden harness) (see [`SPRINT_17.md`](SPRINT_17.md)) |
| **Successor**   | Sprint 19 — Phase E (E1–E2: `metadata.py` — join the per-variant raw items + modification logs into the release schema + schema validator) |

---

## Context

Two halves of the synthetic engine are now built and proven in isolation:

- **Stage A** (Sprint 16, `run_synthetic.py`): loops `(concept, condition)`,
  proposes variants, emits + composes rules, and writes one
  `VariantCatalogEntry` per concept to `data/synthetic/variants/`. The catalog
  records *admissible, ordered* rule sets per variant — but applies nothing.
- **D1 stage hooks** (Sprint 17, `stage_runners.py`): `run_stage3/4/5/7` +
  `run_stages_3_to_7`, pure in-memory dict→dict transforms that reproduce the
  committed golden stage files byte-for-byte. Mutation-blind.

**Stage B is the missing join: read the catalog, apply each variant's rules to
the concept, regenerate the items through the D1 hooks, and emit the mutated
raw items.** This sprint builds it, plus **D3** — the cache-hygiene utility that
matters now that real mutated items land on disk.

### The load-bearing finding: there is ONE injection point, not four

Sprint 17's design note (and the "Stage-Hook Integration Note" in
[`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md)) framed Stage B as *four
interleaved injection points* — "PD/L1 before s03, L2 before s04, L3 before
s05." **Reading the actual mutator implementations contradicts that framing.**
All four mutator families index the **same concept-keyed, parent-level
record**:

| Mutator (`src/synthetic/`) | What it indexes | Record shape it consumes |
|----------------------------|-----------------|--------------------------|
| `layer_l1._replace_value`  | `stage_json[concept_key]["parameters"][param]…` | concept-keyed (stage-2) |
| `layer_l2._replace_fragment` | `stage_json[concept_key]["text_variables"][var]` — matches `"frag" * (cond)` in the **raw formula** | concept-keyed (stage-2) |
| `layer_l3._replace_substring` | `stage_json[concept_key]["resumen"/"texto"]` — the **template** (`$A`, `$L(...)` still present) | concept-keyed (stage-2) |
| `layer_pd.apply_new_param` | `concept["parameters"]` / `["text_variables"]` / `["resumen"/"texto"]` | concept-keyed (stage-2) |

None of them can consume `run_stage3`/`run_stage4` output: after `run_stage3`
the dict is **leaf-keyed** (`OEB020aa`, …) and `concept_key` is no longer a
key, so `stage_json[concept_key]` raises `KeyError`. Worse, by stage-4 the
`text_variables` are resolved `{evaluated: …}` dicts (no raw `"frag"*(cond)`
for L2) and by stage-5 the `resumen`/`texto` are instantiated (no `$`-tokens
for L3). **The mutators can only run before s03**, on the parent record — which
is exactly what CLAUDE_SYNTHETIC.md line 139 already states: *"the variant
catalog mutates the parent-level definition before s03 expansion."* The
layer_l2/layer_l3 docstrings' "stage-3 JSON" / "stage-4 JSON" labels name *the
stage whose content the mutation conceptually targets*, **not** the dict shape
they consume — that shape is the stage-2 concept record in every case.

This is correct *and* simpler. Every mutation is a syntactic edit to the
concept's pre-expansion definition; none depends on any computed intermediate
state. Because `transform_data` copies `text_variables`, `resumen`, `texto`
**identically** to every leaf, mutating the parent and re-expanding is
equivalent to (and cheaper than) mutating leaves post-expansion. So:

> **Stage B applies PD → L1 → L2 → L3 rules to the single-concept stage-2
> record (in the composed order Stage A already pinned), then calls
> `run_stages_3_to_7` once.** No interleaving. The four "injection points" of
> the Sprint 17 narrative collapse to one parent-level injection.

Sprint 18 adopts this and **corrects the docs** (Stage-Hook Integration Note +
the Mutation Architecture framing) to match the implementation.

### The Sprint-16 tripwire is firing on purpose — honour it, don't delete it

Sprint 16 added a test asserting `run_synthetic` **never imports `mutator`** —
explicitly "a scope tripwire that forces the D1/Stage-B conversation the day
someone wires application in." Sprint 18 *is* that day. Sprint 17's "Out of
scope" line said run_synthetic "will gain a Stage-B path in Sprint 18" — **we
supersede that.** Putting apply-and-rerun into `run_synthetic.py` would import
`mutator` there and trip the wire. The cleaner resolution, consistent with the
Stage-A/Stage-B seam the whole design is built on: **Stage B lives in a new
module `src/synthetic/stage_b.py`.** `run_synthetic.py` stays Stage-A-pure and
mutator-free; the tripwire stays green and keeps meaning something.

### Dedup scope changes for synthetic items (decide up front)

The baseline `run_stage7` dedups **chapter-wide** (a leaf is dropped if its
`(resumen, texto)` collides with *any* other leaf in the whole chapter). Stage
B reruns **per concept** (the variant's own leaves only), so its `run_stage7`
dedups **within the variant**. This is the right scope for a synthetic variant
(each variant is a self-contained item set; cross-concept collisions in the
original chapter are an artefact of packaging 25 concepts into one file, not a
property of the variant). Consequence: a per-concept rerun can keep leaves that
the chapter-wide baseline dropped. The golden equivalence we rely on is at
**stage-5 granularity** (pre-dedup, per-item independent) — see the data-gated
test below — not at stage-7.

---

## Scope

### In scope

- **D2 Stage-B: new module `src/synthetic/stage_b.py`.** Public surface:

  - `apply_variant_rules(stage2_concept: dict, concept_key: str, rules: Sequence[dict]) -> tuple[dict, list[Modification]]`
    — partitions `rules` by layer (via `taxonomy.TYPE_TO_LAYER[ModificationType(rule["type"])]`),
    then threads the single-concept dict through, **in PD → L1 → L2 → L3 order**:
    `apply_new_param` once per PD rule, then `apply_l1`(L1 group), then
    `apply_l2`(L2 group), then `apply_l3`(L3 group). Returns the mutated
    concept-keyed dict + the concatenated `Modification` log. Pure
    (`mutator.apply_*` already deep-copy). Rules arrive **pre-composed and
    pre-ordered** from Stage A; partitioning preserves intra-layer order.
  - `materialize_variant(stage2_json: dict, concept_key: str, variant: VariantRecord) -> MaterializedVariant`
    — builds the single-concept slice `{concept_key: stage2_json[concept_key]}`,
    runs `apply_variant_rules`, then `run_stages_3_to_7` on the mutated slice.
    Returns a small frozen dataclass `MaterializedVariant{variant_id, condition,
    concept_key, modification_types, modifications, items}` where `items` is the
    regenerated (mutated, deduped) leaf dict.
  - `materialize_catalog_entry(stage2_json: dict, entry: VariantCatalogEntry, *, out_dir: Path) -> list[Path]`
    — loops `entry.variants`, materialises each, writes one JSON per variant to
    `out_dir / entry.concept_key / {variant_id}.json` (atomic `.tmp` rename, same
    discipline as `variant_catalog.write_catalog_entry`). The written payload
    carries variant metadata + `modifications` log + `items`.
  - `run_stage_b(stage2_json: dict, variants_dir: Path, *, out_dir: Path) -> list[Path]`
    — reads every `VariantCatalogEntry` from `variants_dir` (via
    `variant_catalog.read_catalog_entry`) and materialises each. Default
    `out_dir = config.SYNTHETIC_INTERMEDIATE_DIR`.

  Stage B imports `mutator`, `stage_runners`, `variant_catalog`, `taxonomy`,
  `utils.config` — and **not** `run_synthetic` (no Stage-A coupling).

- **D3 cache hygiene: new module `src/synthetic/cache_hygiene.py`.**
  - `stale_cache_paths(*, data_root=config.DATA_ROOT) -> list[Path]` — the
    enumerated set of derived artefacts that go stale when the corpus changes:
    `PROCESSED_DIR/*.pkl`, `LLAMAINDEX_DIR` contents, stray `chunk_*.json` left
    by the s04/s05 drivers, `**/.ipynb_checkpoints`. Pure (returns paths, deletes
    nothing).
  - `clear_caches(*, data_root=config.DATA_ROOT, dry_run: bool = True) -> list[Path]`
    — returns the would-delete list; only unlinks when `dry_run=False`.
    `dry_run=True` is the default (deletion is opt-in).
  - Document the cleared-path list in [`../../CLAUDE.md`](../../CLAUDE.md) (the
    protocol's D3 wording: "Document the list in `CLAUDE.md`").

- **Tests** — `tests/synthetic/test_stage_b.py` and
  `tests/synthetic/test_cache_hygiene.py`. Always-on inline-fixture tier (no
  live LLM, no large-file IO) + a data-gated equivalence tier.

- **Doc corrections + housekeeping**:
  - Rewrite the "Stage-Hook Integration Note" / Mutation-Architecture framing in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) to the **single
    parent-level injection** model; add ✅ rows for `stage_b.py` and
    `cache_hygiene.py`; flip `data/synthetic/intermediate/` ❌ → ✅; prepend an
    "After Sprint 18" Sprint History entry.
  - Sprint 18 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - A short cache-hygiene section in [`../../CLAUDE.md`](../../CLAUDE.md).

### Out of scope (explicit)

- **The release schema / Parquet + JSONL (`metadata.py`, Phase E / Task G1).**
  Stage B emits **raw** mutated items + their modification logs as per-variant
  JSON under `data/synthetic/intermediate/`. Joining those into the flat
  `BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl` release schema
  (the `Modification`-record shape in CLAUDE_SYNTHETIC.md §Data Structures) is
  Phase E/G — Sprint 19+.
- **Changes to any mutator (`layer_*` / `mutator.py`) or to `stage_runners.py`.**
  Stage B *consumes* them as-is. If a real catalog rule fails to apply, that is
  a Stage-A emission bug or a mutator bug to file separately — Stage B logs the
  skip and moves on, it does not patch the mutator.
- **`run_synthetic.py` changes.** It stays Stage-A-pure; the no-`mutator`-import
  tripwire stays green.
- **A concrete LLM transport (A3).** Irrelevant to Stage B — it reads a catalog
  that already exists; no model calls.
- **Variant budgets / sampling (Phase F).** Stage B materialises *every* variant
  in the catalog; it does not sub-sample.
- **Manual review / quality harness (`review.py`, Phase F, Tasks E3–E4).**
- **Multi-chapter generality of the data-gated test.** Pinned to `OBRA CIVIL`
  (the only chapter with committed intermediate files), as in Sprint 17.

---

## Behavioural requirements

1. **One parent-level injection, composed order.** `apply_variant_rules`
   applies PD then L1 then L2 then L3 to the single-concept stage-2 dict; within
   a layer it preserves the catalog's rule order. Pinned by a stacked-variant
   fixture asserting all layers landed and the modification log lists them in
   PD→L1→L2→L3 order.
2. **Mutation propagates through the rerun.** A `synonym_label` (L1) rule that
   rewrites a parameter value's string makes that new string appear in the
   regenerated `resumen`/`texto` of the affected leaves (the rerun resolves it
   downstream). Pinned on a fixture.
3. **An L2 fragment rewrite and an L3 template edit both survive the rerun.**
   Pinned on fixtures: the L2 `new` fragment shows up post-`run_stage4`; the L3
   `new` substring shows up post-`run_stage5`.
4. **`materialize_variant` is pure.** `stage2_json` is unmutated after the call
   (it slices + the mutators deep-copy). Pinned by an input-unchanged test +
   run-twice-equal.
5. **`materialize_catalog_entry` writes one file per variant** under
   `out_dir/{concept_key}/`, atomically, and the written payload round-trips
   (metadata + `modifications` + `items`). Pinned.
6. **Stage B does not import `run_synthetic`; `run_synthetic` still does not
   import `mutator`.** Both pinned by source/`__dict__` audits (the Sprint-16
   tripwire is *re-asserted*, not removed).
7. **Empty / all-skipped variants are handled.** A variant whose rules all fail
   to apply still produces a materialisation record (baseline items + empty
   modification log) or is skipped-and-logged — decide and pin one behaviour
   (recommend: emit with an empty `modifications` list so the baseline is
   traceable).
8. **`stale_cache_paths` is pure and `clear_caches` defaults to dry-run.**
   `clear_caches()` with no args deletes nothing and returns the candidate list;
   `clear_caches(dry_run=False)` removes a planted temp artefact. Pinned with a
   `tmp_path` fixture — **never** against the real `data/`.
9. **No new runtime dependencies.** Stdlib + in-repo (`utils`, `synthetic`)
   only.
10. **No module-level side effects** in either new module (no on-import IO / path
    resolution / env reads). Pinned by `importlib.reload`.

---

## Acceptance

- `from synthetic.stage_b import (apply_variant_rules, materialize_variant,
  materialize_catalog_entry, run_stage_b)` and
  `from synthetic.cache_hygiene import (stale_cache_paths, clear_caches)`
  succeed.
- On an inline fixture: a single-`synonym_label` variant materialised through
  `materialize_variant` yields items whose `resumen`/`texto` contain the rule's
  `new` string and whose modification log has exactly that one record.
- A stacked PD+L1+L2+L3 variant materialises with all four layers reflected in
  the items and logged in composed order.
- **Data-gated (OBRA CIVIL):** for one real concept, `run_stages_3_to_7` of the
  *unmutated* single-concept stage-2 slice, compared at **stage-5 granularity**
  (i.e. `run_stage5(run_stage4(run_stage3(slice)))`), reproduces exactly the
  chapter `OBRA_CIVIL_stage5.json` items whose `parent_key == concept_key`
  (JSON-normalised per item, as in Sprint 17). Skipped when intermediate data
  is absent.
- `run_synthetic` import-audit test still passes (no `mutator`); a new audit
  confirms `stage_b` does not import `run_synthetic`.
- `pytest tests -q` exits 0 with **≥613 passed** (Sprint 17 baseline 588 +
  ≥25 new always-on functions), **1 skipped** (the Sprint 12 brace audit) in
  César's tree; **zero failures** in any tree (data-gated tests skip, never
  fail, when data is absent).

---

## Tasks

### Task 1 — `src/synthetic/stage_b.py`
1. `apply_variant_rules` — layer partition (`TYPE_TO_LAYER`), PD→L1→L2→L3
   threading over the single-concept dict; concatenate modification logs.
2. `materialize_variant` — slice `{concept_key: …}`, apply, `run_stages_3_to_7`,
   wrap in `MaterializedVariant`.
3. `materialize_catalog_entry` / `run_stage_b` — per-variant atomic writes under
   `SYNTHETIC_INTERMEDIATE_DIR/{concept_key}/`; catalog read loop.
4. Purity + no-`run_synthetic`-import discipline.

### Task 2 — `src/synthetic/cache_hygiene.py`
1. `stale_cache_paths` (pure enumeration) + `clear_caches` (dry-run default).
2. Wire the cleared-path list into a new CLAUDE.md section.

### Task 3 — `tests/synthetic/test_stage_b.py` (+ `test_cache_hygiene.py`)
≥25 always-on functions across both files. Suggested cases:
- `test_apply_variant_rules_orders_pd_l1_l2_l3`
- `test_apply_variant_rules_partitions_by_layer`
- `test_materialize_variant_synonym_label_propagates`
- `test_materialize_variant_l2_fragment_survives_stage4`
- `test_materialize_variant_l3_substring_survives_stage5`
- `test_materialize_variant_stacked_all_layers`
- `test_materialize_variant_is_pure` / `…_deterministic`
- `test_materialize_variant_all_skipped_emits_baseline`
- `test_materialize_catalog_entry_one_file_per_variant` / `…_round_trip`
- `test_run_stage_b_reads_catalog_dir`
- `test_stage_b_does_not_import_run_synthetic`
- `test_run_synthetic_still_does_not_import_mutator` (re-assert the tripwire)
- `test_module_has_no_side_effects_at_import`
- `test_stale_cache_paths_enumerates_expected` (tmp_path fixture)
- `test_clear_caches_dry_run_deletes_nothing`
- `test_clear_caches_removes_planted_artifact`
- **Data-gated:** `test_stage5_slice_matches_chapter_for_concept`

### Task 4 — Housekeeping
1. Append a Sprint 18 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the single-injection finding (with
   the mutator-indexing evidence), the separate-module decision (tripwire kept),
   the dedup-scope decision, the stage-5-granularity equivalence gate, the D3
   utility + CLAUDE.md doc, the test-count delta, and the next step (Sprint 19 —
   Phase E join).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): correct the Stage-Hook
   Integration Note to the single parent-level injection model; add ✅
   `stage_b.py` + `cache_hygiene.py` rows; flip `data/synthetic/intermediate/`
   ❌ → ✅; prepend the "After Sprint 18" history entry.
3. Add a cache-hygiene section to [`../../CLAUDE.md`](../../CLAUDE.md).
4. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) (D2/D3 are §5 backlog
   items; mark them done there only if a reviewer asks).

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥613 passed, 1 skipped** with intermediate data present (0
data-gated skips); **zero failures** in any tree.

Optional end-to-end smoke (manual, with a real catalog present under
`data/synthetic/variants/`):

```powershell
# python -c "from synthetic.stage_b import run_stage_b; from synthetic.stage_runners import *; \
#   import json; from utils import config; \
#   s2=json.load(open(config.chapter_path('OBRA CIVIL'),encoding='utf-8')); \
#   print(run_stage_b(s2, config.SYNTHETIC_VARIANTS_DIR))"
# -> writes data/synthetic/intermediate/{concept}/{variant_id}.json
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/stage_b.py
new file:   src/synthetic/cache_hygiene.py
new file:   tests/synthetic/test_stage_b.py
new file:   tests/synthetic/test_cache_hygiene.py
modified:   CLAUDE.md
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_18.md (this file)
```

No edits to `run_synthetic.py`, `mutator.py`, `stage_runners.py`, or any
`layer_*` module; no new dependencies.

---

## Design notes worth committing to memory

- **One parent-level injection, not four.** Every mutator edits the
  concept-keyed stage-2 record (`stage_json[concept_key][…]`); none can consume
  the leaf-keyed `run_stage3+` output. Stage B applies PD→L1→L2→L3 to that
  record, then `run_stages_3_to_7` once. The Sprint-17 "four injection points"
  narrative is superseded; CLAUDE_SYNTHETIC.md line 139 had it right.
- **Stage A and Stage B stay in separate modules.** `run_synthetic` composes
  and catalogs (no application); `stage_b` applies and reruns (no proposal). The
  Sprint-16 no-`mutator` tripwire is the seam guard — kept, not deleted.
- **Synthetic dedup is per-variant.** `run_stage7` inside Stage B sees only one
  variant's leaves; chapter-wide dedup was a packaging artefact. The faithful
  rerun gate is at stage-5 (pre-dedup, per-item independent).
- **D3 deletes nothing by default.** `clear_caches(dry_run=True)` is the safe
  default; deletion is opt-in and tested only against `tmp_path`.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase D`](../RESEARCH_PROTOCOL.md) — D2 (Stage-B,
  this sprint), D3 (cache hygiene, this sprint).
- [`SPRINT_17.md`](SPRINT_17.md) — the D1 stage hooks Stage B consumes; the
  (now-corrected) four-injection-points note.
- [`SPRINT_16.md`](SPRINT_16.md) — the Stage-A orchestrator + the no-`mutator`
  tripwire that gates this wiring.
- [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md) — Mutation Architecture +
  Stage-Hook Integration Note (to correct) + line 139 (parent-level injection).
- [`../../src/synthetic/mutator.py`](../../src/synthetic/mutator.py) — `apply_l1`
  / `apply_l2` / `apply_l3` (rule lists) + `apply_new_param` (single rule); all
  index `stage_json[concept_key]`.
- [`../../src/synthetic/stage_runners.py`](../../src/synthetic/stage_runners.py)
  — `run_stages_3_to_7`, the regenerate step.
- [`../../src/synthetic/variant_catalog.py`](../../src/synthetic/variant_catalog.py)
  — `read_catalog_entry`, `VariantCatalogEntry`, `VariantRecord{rules}`.
- [`../../src/utils/config.py`](../../src/utils/config.py) —
  `SYNTHETIC_INTERMEDIATE_DIR` (emit target), `SYNTHETIC_VARIANTS_DIR`,
  `DATA_ROOT` / `PROCESSED_DIR` / `LLAMAINDEX_DIR` (D3 targets).

---

## Non-goals reminder

If you find yourself adding apply-and-rerun into `run_synthetic.py` — **stop**.
That trips the Sprint-16 tripwire by design; Stage B is `stage_b.py`.

If you find yourself trying to call `apply_l2` / `apply_l3` on a `run_stage3` or
`run_stage4` output — **stop**. The mutators consume the concept-keyed stage-2
record; that leaf-keyed dict has no `concept_key` and no raw formulas/templates
left to match.

If you find yourself editing a `layer_*` mutator or `stage_runners.py` to make a
rule apply — **stop**. Stage B consumes them as-is; a non-applying rule is a
skip-and-log, or a bug to file separately.

If you find yourself building the Parquet/JSONL release schema — **stop**. Stage
B emits raw per-variant JSON; the join is Phase E (`metadata.py`).

If you find yourself wiring `clear_caches` to delete from the real `data/` tree
in a test — **stop**. Cache deletion is tested only against `tmp_path`.
