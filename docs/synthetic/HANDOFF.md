# BC3CAT-Syn → `bc3cat-retrieval` Handoff

A short cross-repo memo for the `bc3cat-retrieval` maintainer. It tells you where
the BC3CAT-Syn release lives, how to load it, and what new evaluation slices it
adds. **It does not modify `bc3cat-retrieval`** — the `import`/index wiring on the
retrieval side is that repo's change.

> **Status: pilot corpus GENERATED (Sprint 39, 2026-09-02).** The release
> **format, schema, and loader API are frozen and test-pinned** (Phase G tasks
> G1/G2), and the files now exist on disk — release commit `6b52053`:
>
> | | |
> |---|---|
> | Items | **8 687** produced (of 8 734 planned) |
> | Conditions | 10 — nine `single_<type>` + `all_combined` |
> | Dropped | 45 no-ops (0.5 %), 2 exact duplicates |
> | Hard failures | 0 (emission / composition / placeholder residue) |
> | Determinism | two full runs byte-identical (items SHA-256 `7A99A754…`, modifications `DA8A140A…`) |
>
> Per-condition detail lives in
> [`sprints/SPRINT_39_corpus_report.md`](sprints/SPRINT_39_corpus_report.md).
> Scale-up to all of OBRA CIVIL is Sprint 40; this pilot covers the 25 OEB
> concept groups.
>
> **Three accepted caveats (César, 2026-09-02)** — documented stress, not bugs;
> all traceable per item through the modifications sidecar:
> 1. `reorder` never appears in `all_combined` (full-template rewrites collide
>    per field, and every `all_combined` item carries a `template_paraphrase`
>    for BOTH fields); `reorder` is measured in `single_reorder` (1 000/1 000).
> 2. Thin-type deficits: `unit_expansion` 373/650, `unit_conversion` 209/350
>    (pantry-limited under the ≤20-uses-per-rewrite cap; worst-case 95 %
>    margins ≈ ±5.1 / ±6.8).
> 3. Pantry artifacts kept as stress: "tubos tubos" (~376 items), "mm mm"
>    (~280), "con topo"→"con topografía" (~245; semantic drift).

---

## 1. The two release files

Under `data/synthetic/processed/` in `bc3cat-dataset` (branch `synthetic`),
joined **1:1 on `item_key`**:

| File                              | Shape          | Carries                                            |
|-----------------------------------|----------------|----------------------------------------------------|
| `BC3CAT_Syn_items.parquet`        | flat columnar  | one row per synthetic item (the 9 `ITEM_COLUMNS`)  |
| `BC3CAT_Syn_modifications.jsonl`  | ragged, 1 / key| the per-item `modifications` log (kept out of Parquet) |

Items columns (frozen order): `item_key, original_key, concept_key, params,
resumen, texto, variante_id, modification_types, modification_count`.

---

## 2. New evaluation slice columns

Beyond the retrieval text, two item-level columns drive slice-aware evaluation:

- **`modification_types`** (`list[str]`) — per-type slicing (the 12 codes); a
  per-layer slice aggregates these via `synthetic.taxonomy.TYPE_TO_LAYER`.
- **`modification_count`** (`int`) — compositionality slicing
  (`{1, 2, 3, 4, ≥5}`; `0` = baseline).

The pilot corpus runs **10 generation conditions** (`RESEARCH_PROTOCOL.md §6`
as amended 2026-09-02): nine `single_<type>` plus `all_combined` (the
`stacked_*` / `new_param_only` conditions were retired from the pilot on
2026-08-31; the schema still supports them).

**Condition is not a column of the frozen schema, but it is derivable
unambiguously:**

```python
condition = (
    f"single_{row.modification_types[0]}" if row.modification_count == 1
    else "all_combined"
)
```

(`modification_count == 1` → that type's single condition; `> 1` →
`all_combined` — in this release every `all_combined` item carries ≥ 3
distinct types, so the rule cannot misclassify.)

The join key back to the original BC3CAT/OEB item is `original_key` (the
`(item_key, original_key, variante_id)` triple is unique) — paired evaluation
compares each synthetic item against its original leaf in
`OEB_{long,short}_norm.parquet`.

---

## 3. Loader API (`synthetic.loaders`)

With `PYTHONPATH=src` in `bc3cat-dataset`:

```python
from synthetic.loaders import (
    load_items, load_modifications, join, long_view, short_view,
)

items  = load_items()          # ITEM_COLUMNS frame
mods   = load_modifications()  # {item_key: [Modification, ...]}, baseline -> []
joined = join(items, mods)     # 1:1 on item_key, fail-loud; + `modifications` list[dict] column

targets = long_view(items)     # text == texto
queries = short_view(items)    # text == resumen
```

`long_view` / `short_view` return the OEB-style projection: the key + slice
columns (`item_key, original_key, concept_key, params, variante_id,
modification_types, modification_count`), the retrieval text in a single `text`
column, and a derived `text_norm`.

**`text_norm` is byte-for-byte consistent with the parent OEB.** It is produced
by `utils.text_processing.normalize_text` — the *same* normalizer behind the
`OEB_long_norm` / `OEB_short_norm` `text_norm` columns this repo already indexes.
So `long_view` maps to `OEB_long_norm` and `short_view` to `OEB_short_norm`:
`text` + `text_norm` in the same shape, plus the synthetic key/slice metadata.
No OEB-only `id`/`ud`/`concept` columns are fabricated.

`join` returns a sorted copy and raises `LoaderError` on any non-1:1 `item_key`
match (a partial release fails loud rather than silently dropping/duplicating
rows).

---

## 4. What this memo is not

- It does **not** add an import or index path in `bc3cat-retrieval` — that is the
  retrieval repo's own change.
- It ships the **pilot** corpus (25 OEB concept groups); the full OBRA CIVIL
  scale-up is Sprint 40 and will regenerate the two files in place (same
  schema, same paths).
- `synthetic` is a permanent parallel branch and is **never merged to `main`**
  (see [`CLAUDE.md`](../../CLAUDE.md)).

See [`DATA_CARD.md`](DATA_CARD.md) for the full schema, taxonomy, slices, and
provenance.
