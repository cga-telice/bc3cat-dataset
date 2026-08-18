# Sprint 19 — Phase E Tasks E1 (metadata join) + E2 (schema validator)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 19                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | E1, E2 (see [`../RESEARCH_PROTOCOL.md §5 Phase E`](../RESEARCH_PROTOCOL.md))                |
| **Predecessor** | Sprint 18 — `stage_b.py` (D2: apply-and-rerun, raw per-variant items) + `cache_hygiene.py` (D3) (see [`SPRINT_18.md`](SPRINT_18.md)) |
| **Successor**   | Sprint 20 — Phase E (E3–E4: `review.py` — stratified validation sampler + domain-reviewer harness) |

---

## Context

Stage B (Sprint 18) writes one **raw per-variant JSON** per materialised variant
to `data/synthetic/intermediate/{concept_key}/{variant_id}.json`. Each payload is:

```json
{
  "variant_id":  "single_L1_synonym_label_ab12cd34ef",
  "condition":   "single_L1_synonym_label",
  "concept_key": "OEB020$",
  "modification_types": ["synonym_label"],
  "modifications": [ {"type": "synonym_label", "layer": "param_value", "param": "B",
                      "value": "a", "original": "Normal", "new": "Estandar",
                      "status": "applied"} ],
  "items": {
    "OEB020a": {"parent_key": "OEB020$", "ud": "m", "concept": "…",
                "resumen": "…", "texto": "…", "parameters": {…}, "validation": true},
    "OEB020b": {…}
  }
}
```

That payload is **variant-grained** (one record per variant, items nested by leaf
key) and carries the modification log **once per variant**, not per item. The
release schema (proposal [§2.3](../RESEARCH_PROPOSAL.md) / [§6.1]) is the
opposite shape: **one flat record per synthetic item**, each carrying its own
traceability block:

```json
{
  "item_key":   "OEB020a_syn_single_L1_synonym_label_ab12cd34ef",
  "original_key": "OEB020a",
  "params":     {"B": "Estandar"},
  "resumen":    "…",
  "texto":      "…",
  "variante_id": "single_L1_synonym_label_ab12cd34ef",
  "modification_types": ["synonym_label"],
  "modification_count": 1,
  "modifications": [ {…} ]
}
```

**E1 is the join that turns variant-grained Stage-B payloads into item-grained
release records** (proposal Stage C — "Metadata injection"). **E2 is the
fail-loud validator** that asserts every record is well-formed before it can be
packaged. This sprint builds both as a pure library (`metadata.py`); the Parquet
+ sidecar-JSONL serialization is **Phase G (G1)**, not this sprint.

### The load-bearing design decisions (decide up front)

1. **`item_key` uses the mutated leaf key; `original_key` uses the baseline leaf
   key.** A pure L1/L2/L3 mutation does not change the parameter space, so the
   regenerated leaf key **is** an original catalog key → `original_key ==
   leaf_key`. A `new_param` (PD) mutation **appends** an axis; `transform_data`
   builds the key suffix as the labels concatenated in `parameters` insertion
   order, and `apply_new_param` appends the new axis **last**, so each applied
   `new_param` contributes exactly one *trailing* label char. Therefore:

   > `original_key = leaf_key[:-K]` where `K = count of applied `new_param`
   > modifications in the variant` (0 for non-PD variants).

   Verified empirically: a PD variant's leaves `OEB020aa`/`OEB020ba` strip to the
   baseline `OEB020a`/`OEB020b`. `item_key = f"{leaf_key}_syn_{variante_id}"`
   stays globally unique (the *mutated* leaf key disambiguates `new_param` sibling
   items that share an `original_key`).

2. **`variante_id` is Stage B's `variant_id` verbatim.** It is already unique
   per concept (`{condition}_{sha1[:10]}`); no re-derivation. (The proposal's
   illustrative `"v1"` is cosmetic; the real id is the Stage-B one.)

3. **`modification_count == len(modifications)` and `modification_types ==
   [m.type for m in modifications]`.** Both are derived, never trusted from the
   payload's pre-computed copies — E1 recomputes them from the applied
   `modifications` log so the three fields cannot drift. E2 then asserts the
   payload's own `modification_types` (if present) agrees.

4. **Zero-modification (all-skipped) variants are joined as baselines.** Sprint
   18 emits all-skipped variants with `modifications: []` and baseline `items`.
   E1 produces valid records for them (`modification_count == 0`); E2 accepts
   `modification_count == 0`. Whether to *drop* baseline items from the released
   benchmark is a Phase F budget decision, **not** an E1/E2 concern — keep them,
   flag them via the count.

5. **`metadata.py` does not import `stage_b` or `run_synthetic`.** It reads the
   on-disk per-variant JSON (the payload is the contract) and rebuilds
   `Modification`s via `taxonomy.Modification.from_dict`. Keeping it decoupled
   from the writer means the join can run against any directory of conformant
   payloads (and keeps the Stage-A/Stage-B/Stage-C seams clean). It imports
   `taxonomy` + `utils.config` + stdlib only.

---

## Scope

### In scope

- **E1 — metadata join, new module `src/synthetic/metadata.py`.** Public surface:

  - `@dataclass(frozen=True) SyntheticItem` with exactly the release fields:
    `item_key, original_key, params (dict[str,str]), resumen, texto,
    variante_id, modification_types (tuple[ModificationType,...]),
    modification_count (int), modifications (tuple[Modification,...])`, plus a
    `concept_key` back-pointer and a `to_dict()` matching proposal §2.3 (enum →
    `.value`, `modifications` via `Modification.to_dict`).
  - `join_variant_payload(payload: dict) -> list[SyntheticItem]` — the pure core:
    one `SyntheticItem` per `(leaf_key, item)` in `payload["items"]`. Computes
    `original_key` per decision 1, `params` by flattening each leaf's
    `parameters` to `{axis_id: values[0]["value"]}`, threads
    `variante_id`/`modifications`, recomputes `modification_types`/`_count`
    (decision 3). Drops the stage-7 `validation` flag.
  - `join_variant_file(path: Path) -> list[SyntheticItem]` — read one JSON,
    delegate to `join_variant_payload`.
  - `join_intermediate(intermediate_dir: Path = config.SYNTHETIC_INTERMEDIATE_DIR)
    -> list[SyntheticItem]` — walk `{concept_key}/*.json` (sorted, deterministic
    order), concatenate. Default arg resolved inside (no import-time path read).

- **E2 — schema validator, in `metadata.py`.**
  - `validate_item(item: SyntheticItem) -> None` — fail-loud (`raise
    SchemaError`) on: missing/empty `item_key` / `original_key` / `variante_id`;
    `modification_count != len(modifications)`; `modification_types` disagreeing
    with `[m.type for m in modifications]`; any `Modification` lacking `type`/
    `layer`; `original_key` not a prefix of the `item_key`'s leaf segment;
    non-string `resumen`/`texto`. Accepts `modification_count == 0`.
  - `validate_items(items: Iterable[SyntheticItem]) -> None` — runs
    `validate_item` over all; additionally asserts `item_key` **global
    uniqueness** (fail-loud on collision).
  - `class SchemaError(ValueError)` — distinct, catchable failure type.

- **Tests** — `tests/synthetic/test_metadata.py`. Always-on inline-fixture tier
  (hand-built Stage-B-shaped payloads, no live LLM / no large-file IO) + a
  data-gated tier that runs Stage B on one real `OBRA CIVIL` concept and joins +
  validates the result.

- **Doc + housekeeping**:
  - Add a ✅ `metadata.py` row to the "New Files in This Branch" map in
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); prepend an "After Sprint
    19" Sprint History entry; note the `(item_key, original_key, variante_id)`
    join-key triple and the `original_key = leaf_key[:-K]` rule in the Data
    Structures section.
  - Sprint 19 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).

### Out of scope (explicit)

- **Parquet + sidecar JSONL serialization (`G1`).** E1 produces in-memory
  `SyntheticItem` records (and their `to_dict()`); writing
  `BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl` (the columnar
  items table mirroring `OEB_long_norm.parquet` + the `item_key`-keyed
  modifications sidecar) is Phase G. No `pandas`/`pyarrow` dependency added this
  sprint.
- **Validation sampler + reviewer harness (`E3`/`E4`, `review.py`).** Sprint 20.
- **Loader utilities (`loaders.py`, `G2`).**
- **Cross-checking `original_key` against a re-expanded baseline catalog.** E2
  validates `original_key` *structurally* (prefix-of-leaf-segment + derivable by
  the `[:-K]` rule). Asserting it names a row that actually exists in the
  unmutated chapter expansion is a heavier, baseline-dependent check — deferred
  to F4 / G1 (where the baseline is loaded anyway).
- **Changes to `stage_b.py`, `run_synthetic.py`, `stage_runners.py`, or any
  `layer_*` / `mutator` module.** E1 *consumes* the Stage-B payload as-is. If a
  payload is malformed, that is a Stage-B bug to file separately — E2 fails loud,
  it does not paper over it.
- **De-duplicating synthetic items across variants/concepts.** Per-variant dedup
  already happened in Stage B (Sprint 18). E1 is a flatten+annotate, not a dedup.
- **Multi-chapter generality of the data-gated test.** Pinned to `OBRA CIVIL`,
  as in Sprints 17–18.

---

## Behavioural requirements

1. **One record per item, traceability per item.** `join_variant_payload`
   emits exactly `len(payload["items"])` records; each carries the variant's
   `variante_id` + full `modifications` list. Pinned on a 2-leaf fixture.
2. **`original_key` strips applied `new_param` axes.** For a non-PD variant
   `original_key == leaf_key`; for a variant with K applied `new_param` mods
   `original_key == leaf_key[:-K]`. Pinned on an L1-only fixture and a
   PD-stacked fixture (`OEB020aa` → `OEB020a`).
3. **`item_key` is globally unique and `_syn_`-marked.** `item_key ==
   f"{leaf_key}_syn_{variante_id}"`; `validate_items` raises `SchemaError` on a
   planted collision. Pinned.
4. **Derived fields cannot drift.** `modification_count == len(modifications)`
   and `modification_types == [m.type for m in modifications]`, recomputed by
   E1; a fixture whose payload ships a *wrong* pre-computed `modification_types`
   is corrected by E1 (the join recomputes) — pinned.
5. **Zero-modification variants join as valid baselines.** An all-skipped variant
   yields records with `modification_count == 0`, empty `modifications`/types,
   and `original_key == item_key`-leaf; `validate_item` accepts them. Pinned.
6. **`params` flattens to `{axis: value}` strings.** Pinned; the new `new_param`
   axis appears in `params` (it is a real axis post-mutation).
7. **Validator is fail-loud.** `validate_item` raises `SchemaError` (not returns
   a bool, not logs-and-continues) on each malformed-field class. One pinned
   test per class (missing key, count mismatch, types mismatch, malformed
   modification, bad `original_key` prefix).
8. **`join_intermediate` is deterministic and order-stable.** Concept dirs +
   files walked in sorted order; run-twice-equal. Pinned with a `tmp_path`
   two-concept fixture.
9. **`metadata.py` imports neither `stage_b` nor `run_synthetic`.** Pinned by
   source + `__dict__` audits (same shape as the Sprint 17/18 hygiene audits).
10. **No new runtime dependencies; no module-level side effects.** Stdlib +
    in-repo (`taxonomy`, `utils.config`). Pinned by `importlib.reload`.

---

## Acceptance

- `from synthetic.metadata import (SyntheticItem, SchemaError, join_variant_payload,
  join_variant_file, join_intermediate, validate_item, validate_items)` succeeds.
- On an inline single-`synonym_label` payload (2 leaves): `join_variant_payload`
  yields 2 records with `original_key == leaf_key`, `modification_count == 1`,
  and `validate_items` passes.
- On an inline PD payload (`new_param`, leaves `OEB020aa`/`OEB020ba`): records
  carry `original_key` `OEB020a`/`OEB020b`, the new axis present in `params`, and
  `validate_items` passes.
- On a payload mutated to violate each schema rule, `validate_item` raises
  `SchemaError`.
- **Data-gated (OBRA CIVIL):** materialise one real concept's catalog variant(s)
  through `stage_b` into a `tmp_path`, `join_intermediate` it, and assert every
  produced `SyntheticItem` passes `validate_items` and that each `original_key`
  equals a real chapter leaf key for non-PD variants. Skipped when intermediate
  data is absent.
- `pytest tests -q` exits 0 with **≥646 passed** (Sprint 18 baseline 626 + ≥20
  new always-on functions), **1 skipped** (the Sprint 12 brace audit) in César's
  tree; **zero failures** in any tree (data-gated tests skip, never fail).

---

## Tasks

### Task 1 — `src/synthetic/metadata.py`
1. `SyntheticItem` frozen dataclass + `to_dict()` (proposal §2.3 shape).
2. `join_variant_payload` (pure core: per-item flatten, `original_key` `[:-K]`
   rule, `params` flatten, recompute count/types).
3. `join_variant_file` / `join_intermediate` (sorted, deterministic walk).
4. `SchemaError` + `validate_item` (per-field fail-loud) + `validate_items`
   (per-item + global `item_key` uniqueness).
5. Import-hygiene + no-side-effects discipline.

### Task 2 — `tests/synthetic/test_metadata.py`
≥20 always-on functions + 1 data-gated. Suggested cases:
- `test_module_exposes_public_surface`
- `test_join_one_record_per_item`
- `test_join_l1_original_key_equals_leaf_key`
- `test_join_new_param_strips_trailing_axis_chars`
- `test_join_item_key_is_syn_marked_and_unique`
- `test_join_recomputes_modification_count`
- `test_join_recomputes_modification_types_over_payload_copy`
- `test_join_params_flatten_to_value_strings`
- `test_join_new_param_axis_present_in_params`
- `test_join_zero_modification_baseline_is_valid`
- `test_join_drops_validation_flag`
- `test_to_dict_matches_proposal_shape`
- `test_join_intermediate_deterministic` (tmp_path)
- `test_join_intermediate_sorted_order` (tmp_path)
- `test_validate_item_rejects_missing_item_key`
- `test_validate_item_rejects_count_mismatch`
- `test_validate_item_rejects_types_mismatch`
- `test_validate_item_rejects_malformed_modification`
- `test_validate_item_rejects_bad_original_key_prefix`
- `test_validate_items_rejects_item_key_collision`
- `test_metadata_does_not_import_stage_b_or_run_synthetic`
- `test_module_has_no_side_effects_at_import`
- **Data-gated:** `test_stage_b_to_metadata_roundtrip_for_concept`

### Task 3 — Housekeeping
1. Prepend a Sprint 19 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the variant-grained → item-grained
   join finding, the `original_key = leaf_key[:-K]` decision (with the suffix
   mechanics), the `item_key`/`variante_id` decisions, the recompute-don't-trust
   rule, the baseline-existence cross-check deferral, the test-count delta, and
   the next step (Sprint 20 — E3–E4 `review.py`).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): add the ✅ `metadata.py`
   row; record the join-key triple + `[:-K]` rule near the `Modification`-record
   schema; prepend the "After Sprint 19" history entry.
3. Do **not** modify [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) or
   [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) (E1/E2 are §5 backlog
   items; mark them done there only if a reviewer asks).

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
pytest tests -q
```

Expected: **≥646 passed, 1 skipped** with intermediate data present (0
data-gated skips); **zero failures** in any tree.

Optional end-to-end smoke (manual, with a real catalog under
`data/synthetic/variants/` and a chapter stage-2 JSON):

```powershell
# python -c "from synthetic.stage_b import run_stage_b; from synthetic.metadata import join_intermediate, validate_items; \
#   import json, tempfile; from pathlib import Path; from utils import config; \
#   s2=json.load(open(config.chapter_path('OBRA CIVIL'),encoding='utf-8')); \
#   out=Path(tempfile.mkdtemp()); run_stage_b(s2, config.SYNTHETIC_VARIANTS_DIR, out_dir=out); \
#   items=join_intermediate(out); validate_items(items); print(len(items),'items joined + validated')"
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   src/synthetic/metadata.py
new file:   tests/synthetic/test_metadata.py
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
new file:   docs/synthetic/sprints/SPRINT_19.md (this file)
```

No edits to `stage_b.py`, `run_synthetic.py`, `stage_runners.py`, `mutator.py`,
any `layer_*` module, or `cache_hygiene.py`; no new dependencies.

---

## Design notes worth committing to memory

- **Variant-grained → item-grained is the whole job.** Stage B writes the
  modification log once per variant with items nested; the release schema needs
  it once per item, flat. E1 fans the log out across the variant's leaves and
  attaches the per-item traceability triple `(item_key, original_key,
  variante_id)`.
- **`original_key = leaf_key[:-K]`.** `new_param` appends axes; their labels are
  the trailing key-suffix chars (insertion-order suffix construction in
  `transform_data`). Strip K of them (K = applied `new_param` count) to recover
  the baseline catalog key. Non-PD variants: K=0, `original_key == leaf_key`.
- **Recompute, don't trust.** `modification_count` / `modification_types` are
  derived from the applied `modifications` log inside E1; the payload's copies
  are advisory and cross-checked, never authoritative.
- **E1 is a pure library; G1 packages.** `metadata.py` returns `SyntheticItem`s
  and validates them; Parquet + JSONL serialization (and the `pyarrow`
  dependency) belong to Phase G.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase E`](../RESEARCH_PROTOCOL.md) — E1 (metadata
  join, this sprint), E2 (schema validator, this sprint), E3–E4 (Sprint 20).
- [`../RESEARCH_PROPOSAL.md §2.3`](../RESEARCH_PROPOSAL.md) — the per-item
  metadata schema this sprint targets; the join-key triple.
- [`SPRINT_18.md`](SPRINT_18.md) — Stage B; the per-variant payload E1 consumes;
  the `variant_id = {condition}_{sha1[:10]}` derivation reused as `variante_id`.
- [`../../src/synthetic/stage_b.py`](../../src/synthetic/stage_b.py) —
  `_materialized_to_dict` (the payload contract) + the `new_param` key-suffix
  behaviour that the `[:-K]` rule inverts.
- [`../../src/synthetic/stage_runners.py`](../../src/synthetic/stage_runners.py)
  — `transform_data` (insertion-order key-suffix construction, the basis of the
  `original_key` rule).
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) —
  `Modification` / `ModificationType` / `Modification.from_dict` / `.to_dict`.
- [`../../src/utils/config.py`](../../src/utils/config.py) —
  `SYNTHETIC_INTERMEDIATE_DIR` (join input), `SYNTHETIC_PROCESSED_DIR` (G1
  output target, next sprint).

---

## Non-goals reminder

If you find yourself adding `pandas` / `pyarrow` or writing
`BC3CAT_Syn_items.parquet` / `BC3CAT_Syn_modifications.jsonl` — **stop**. That is
Phase G (G1); E1 returns `SyntheticItem` records and `to_dict()`s.

If you find yourself importing `stage_b` or `run_synthetic` into `metadata.py` —
**stop**. The on-disk per-variant JSON payload is the contract; read it directly
and rebuild via `Modification.from_dict`.

If you find yourself making `validate_item` return a bool or log-and-continue —
**stop**. E2 is fail-loud: raise `SchemaError`.

If you find yourself editing a `layer_*` mutator, `stage_b`, or `stage_runners`
to make a record validate — **stop**. A malformed payload is a Stage-B/Stage-A
bug to file separately; E2 surfaces it, it does not patch upstream.

If you find yourself building the stratified validation sampler or the reviewer
CLI — **stop**. That is E3–E4 (`review.py`), Sprint 20.
