# Response to `bc3cat-retrieval` — wider L2 slices

**Answers:** `bc3cat-retrieval/docs/synthetic-oe/requests/WIDER_THIN_SLICES.md` (S4 work item 7, needed by S6)
**Answered:** 2026-09-29 · **Branch:** `synthetic` (on top of `f2457fa`)
**Status:** **not built yet.** Measured what is reachable. The ≥ 15 dev-concept target cannot be
met by any menu. The frozen menus can take each L2 type from 5 to 8–9 dev concepts.

## The limit, measured

Script: `scripts/l2_reachability.py`. It uses the E3 probe's judgement: an approved rewrite
counts for a leaf only when it is compatible with the leaf **and visible in its TEXTO**. It runs
over the full delivered corpus (70 242 leaves, 83 concepts), counts only, split by your
`SPLITS.md`.

| type | concepts in SINGLE now (dev / test) | reachable with frozen menus (dev / test) | leaves at ≤ 20 per concept (dev / test) | distinct concept × rewrite pairs (dev / test) |
|---|---|---|---|---|
| `paraphrase` | 5 / 3 | **9 / 11** | 180 / 203 | 376 / 363 |
| `expansion` | 5 / 3 | **9 / 11** | 180 / 203 | 407 / 379 |
| `compression` | 5 / 3 | **8 / 9** | 160 / 168 | 196 / 165 |

**Hard ceiling: 13 dev / 12 test concepts.** An L2 rewrite changes a text variable. It only
reaches the query if the concept's TEXTO template renders a text variable, and only 13 dev and
12 test concepts do. The rest put only axis values into the TEXTO. A rewrite menu cannot change
that, so **≥ 15 dev concepts per type is out of reach** under this grammar. S6 should state it as
a structural limitation.

Between the frozen reach (8–9) and the ceiling (13) lie about 4 dev concepts per type. Their TEXTO
has a text variable, but the menus hold no approved, visible rewrite for it. Reaching them means a
new LLM menu pass plus review. That would be a new menu release, not a recombination.

## Point by point

### 1. Breadth first — **partly achievable: 9 / 9 / 8 dev concepts, not 15**

The 9 / 9 / 8 in the table all come from the frozen menus. The current SINGLE reaches only 5
because it was drawn from the 5 000-leaf shared sample under caps, not from the full corpus. The
extra concepts come from sampling all 70 242 leaves.

### 2. Depth second — **met**

The ≤ 20 leaves per concept and type is not binding for most concepts: every reachable concept has
far more eligible leaves. The totals above are with the cap applied, about 160–180 dev queries per
type. They are more than your current 108 / 130 / 306, except `compression` (160 against 306).
There, breadth rises from 5 to 8 concepts while the query count falls. Tell us if you want
compression's per-concept depth raised to keep n.

Per concept, the leaves would be spread across axis values, as in E3.

### 3. A new file — **agreed**

`OE_single_l2_texto.json`. `OE_single_texto.json` is not touched (sha256 `b6a43961…d839a`).

### 4. Schema, sidecar, reorder fix — **agreed**

The schema is the SINGLE record schema, with its own modifications sidecar. The `reorder` fix
(`REORDER_LOOKUP_RESPONSE.md`) is already in the pantry every builder reads. It does not touch L2.
Every `gold_item_key` will resolve against the delivered corpus, and the build fails if one does
not.

### "If the menus are the limit, tell us how many concepts are reachable"

Frozen menus: **9 / 9 / 8 dev** and **11 / 11 / 9 test**, for paraphrase / expansion /
compression. With new menus: at most **13 dev / 12 test**. The grammar is the limit, then the
menus.

## What we need from you

1. **Go / no-go** on the frozen-menu build (9 / 9 / 8 dev concepts). It is a deterministic
   recombination and fast.
2. Whether a **new menu pass** toward the 13-concept ceiling is worth it for S6. It is slower,
   and the new rewrites need review.
3. For `compression`: keep ≤ 20 per concept (fewer queries, more concepts), or raise depth.
