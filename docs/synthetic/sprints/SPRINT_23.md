# Sprint 23 — Phase G Tasks G3 + G4 (release documentation: `DATA_CARD.md` + README "Synthetic Variant" section + cross-repo `HANDOFF.md`)

| Field           | Value                                                                                       |
|-----------------|---------------------------------------------------------------------------------------------|
| **Sprint**      | 23                                                                                          |
| **Date**        | 2026-05-20 (drafted)                                                                        |
| **Branch**      | `synthetic`                                                                                 |
| **Backlog IDs** | G3 + G4 (see [`../RESEARCH_PROTOCOL.md §5 Phase G`](../RESEARCH_PROTOCOL.md))                |
| **Predecessor** | Sprint 22 — `loaders.py` (G2: read API + 1:1 join + long/short views) (see [`SPRINT_22.md`](SPRINT_22.md)) |
| **Successor**   | Sprint 24 — **A3** (concrete `LLMClient` transport) to unblock the Phase F pilot (F1–F2), then F3 full generation, F4 validation (`QUALITY_REPORT.md`), and a **post-F3 `DATA_CARD.md` statistics refresh** |

---

## Context

Phase G builds the durable BC3CAT-Syn **release**. Sprint 21 (G1,
[`packaging.py`](../../src/synthetic/packaging.py)) froze the on-disk format —
`BC3CAT_Syn_items.parquet` (flat columnar, `ITEM_COLUMNS`) +
`BC3CAT_Syn_modifications.jsonl` (ragged per-`item_key` log), 1:1 on `item_key`.
Sprint 22 (G2, [`loaders.py`](../../src/synthetic/loaders.py)) shipped the
read-only consumer API — `load_items` / `load_modifications` / `join` (1:1,
fail-loud) / `long_view` / `short_view` — that turns those two files into the
frames `bc3cat-retrieval` indexes.

What is *missing* is the human-facing documentation that makes the release
consumable by someone who is not us:

* **G3 — Documentation** (`RESEARCH_PROTOCOL.md §5 G3`): a Data-in-Brief–style
  [`DATA_CARD.md`](../DATA_CARD.md) describing the dataset (provenance, format,
  schema, modification taxonomy, evaluation slices, loader usage, license,
  AI-disclosure, citation) **plus** a "Synthetic Variant" section appended to
  the top-level [`README.md`](../../README.md).
* **G4 — Cross-repo handoff** (`§5 G4`): a short
  [`HANDOFF.md`](../HANDOFF.md) memo pointing `bc3cat-retrieval` at the new
  files, the new slice columns (`modification_types`, `modification_count`), and
  the loader API.

G3/G4 are the natural Phase-G closeout: both are documentation, both are now
**unblocked at the format/schema/API level** (G1 froze the format, G2 froze the
loader contract — both exist and are test-pinned), and both directly continue
the Sprint 21→22 arc. Sprint 20 set the precedent for pairing two closely-related
backlog tasks in one sprint (E3 + E4); G3 + G4 are likewise cohesive — they
describe the *same* release for two audiences (a reader of the dataset, a
maintainer of the downstream repo).

### Why G3 + G4 now, and not A3 — and the one honest caveat

Sprint 22's successor note offered "Sprint 23 — Phase G (G3/G4) **and/or** A3".
G3/G4 are chosen because they finish the phase Sprints 21–22 opened and are
fully unblocked. **A3** (the concrete `LLMClient` transport that unblocks the
Phase F real pilot) is a different track — network transport, retry/timeout,
API-key handling, live-vs-recorded fixtures — and remains its own dedicated
sprint (the planned Sprint 24). G3/G4 first; A3 next.

**The honest caveat (decision 1, below):** the BC3CAT-Syn corpus has **not been
generated** — F3 (full generation) is blocked on A3, so there is no real release
on disk, only test fixtures and the manual G1/G2 smokes. A Data-in-Brief data
card normally leads with corpus statistics (item counts, per-type distributions,
acceptance rates). Those numbers **do not exist yet** and must **not** be
fabricated. So Sprint 23 writes the **format/schema/provenance/usage card against
the now-frozen G1/G2 contract**, with every corpus-scale statistic carried as an
explicit, clearly-marked `TBD (pending F3 full generation)` placeholder. A
**post-F3 statistics refresh** of `DATA_CARD.md` is an explicit follow-up
(noted in the Successor row), not a Sprint 23 deliverable. This is the standard
"data card written at format-freeze, numbers filled at corpus-freeze" split, and
it lets the documentation track proceed without waiting on A3 while staying
truthful about what is and isn't measured.

### The load-bearing design decisions (decide up front)

1. **Document the frozen contract; never fabricate corpus statistics.** Every
   schema/format/taxonomy/slice/loader fact the card states is derivable from
   the *code that already exists* (`packaging.ITEM_COLUMNS`,
   `taxonomy.ModificationType` / `Layer` / `TYPE_TO_LAYER`, `loaders` view
   columns, `RESEARCH_PROPOSAL.md §2.3`, `§6` generation conditions). Every
   corpus-scale number (total items, per-concept / per-type counts, acceptance
   rates, throughput) is an explicit `TBD (pending F3)` placeholder. No invented
   figures, no copied-from-OEB figures presented as synthetic figures.

2. **Sprint 23 is documentation-only — no code module, no new tests, suite
   stays at 719.** Unlike Sprints 19–22 (each a code module + a pytest tier),
   G3/G4 produce Markdown only. There is nothing executable to pin; the schema
   the card documents is *already* test-pinned (`test_packaging.py
   ::test_item_columns_frozen_order` froze `ITEM_COLUMNS`; `test_loaders.py`
   froze the view columns). `pytest tests -q` must still report the Sprint 22
   baseline **719 passed, 1 skipped**, unchanged. (A Markdown-parsing
   "docs-don't-drift-from-`ITEM_COLUMNS`" guard is deliberately **out of scope**
   — it would be brittle and the underlying contract is already pinned in code;
   see Out of scope.)

3. **The README edit is purely additive and preserves the original BC3CAT
   description verbatim.** A new top-level section — `## Synthetic Variant
   (BC3CAT-Syn)` — is **appended** (placed after the existing dataset content,
   before `## Citation`/`## License`, at the drafter's judgement), pointing at
   `docs/synthetic/`, the two release files, and the loader API. The existing
   sections (Overview, Pipeline, Quick Start, Data Formats, Citation, License,
   Contact) are **not reworded**. (`README.md` is shared with `main` in spirit,
   but this work lives only on `synthetic` and **must never be merged to
   `main`** — see [`CLAUDE.md`](../../CLAUDE.md); the section documents the
   synthetic branch's artifacts, which `main` does not have.)

4. **`HANDOFF.md` is a short cross-repo memo — it does NOT modify
   `bc3cat-retrieval`.** It tells the downstream maintainer: where the two files
   live, the 1:1 `item_key` join, the new evaluation slice columns
   (`modification_types`, `modification_count`) and the generation-conditions
   slices (§6), the `synthetic.loaders` import surface and the
   `long_view`/`short_view` shape (which mirrors the OEB `OEB_long_norm` /
   `OEB_short_norm` `text` + `text_norm` layout the retrieval repo already
   indexes), and the current **"not yet generated — pending A3 + F3"** status.
   The actual `import`/index wiring on the `bc3cat-retrieval` side is that repo's
   change, not this sprint's.

5. **The card mirrors the §2.3 *record*, not the OEB LlamaIndex column list**
   (the Sprint 22 decision-3 invariant, restated for the reader): the items
   schema is the §2.3 per-item record + `concept_key`; the long/short views add
   a single `text` + derived `text_norm`; no OEB-only `id`/`ud`/`concept` is
   claimed. License mirrors the parent BC3CAT dataset license (**CC-BY 4.0**, per
   the existing `README.md` "Dataset" license block); code remains MIT.

6. **AI-disclosure is mandatory and prominent.** The synthetic modifications are
   **LLM-proposed** (Phase C, temperature 0.0, strict-JSON contract, one retry
   then `fallback: skipped`) and rule-applied (Phase B), with a domain-reviewer
   validation protocol (Phase E `review.py`; F4 quality pass). The card states
   this plainly under an "AI Disclosure / Provenance" heading, consistent with
   the existing `README.md` `### AI Disclosure` block.

---

## Scope

### In scope

- **G3a — new file `docs/synthetic/DATA_CARD.md`** (Data-in-Brief style).
  Sections (suggested, drafter may reorder):
  1. **Title / version / one-line description / license (CC-BY 4.0)** and the
     relationship to the parent BC3CAT release.
  2. **Provenance** — derived from the BC3CAT OEB subset via the
     rule-modification synthetic pipeline on branch `synthetic`; the three-layer
     BC3 grammar (L1/L2/L3 + param-definition); LLM-proposed + rule-applied +
     reviewer-validated. Cross-link `RESEARCH_PROPOSAL.md` / `RESEARCH_PROTOCOL.md`.
  3. **Release files** — `BC3CAT_Syn_items.parquet` (flat columnar) +
     `BC3CAT_Syn_modifications.jsonl` (ragged per-`item_key` log), 1:1 on
     `item_key`; both under `data/synthetic/processed/`.
  4. **Items schema table** — the frozen `ITEM_COLUMNS` (`item_key`,
     `original_key`, `concept_key`, `params`, `resumen`, `texto`, `variante_id`,
     `modification_types`, `modification_count`) with type + semantics per column;
     the `modifications` sidecar payload shape (`Modification.to_dict`).
  5. **Modification taxonomy** — the 12 `ModificationType`s mapped to their 4
     `Layer`s (`TYPE_TO_LAYER`); the skip-and-log convention for unstackable
     combinations.
  6. **Evaluation slices** — `modification_types` / `modification_count` +
     the §6 generation-conditions table (`single_L*`, `new_param_only`,
     `stacked_2…5+`, `full_random_mix`) and their diagnostic interpretation.
  7. **Loader quickstart** — `from synthetic.loaders import load_items,
     load_modifications, join, long_view, short_view`; the long/short view
     `text` + `text_norm` shape and its OEB-`_norm` consistency.
  8. **Statistics** — total items, per-concept / per-type counts, acceptance
     rate per type, throughput — **all `TBD (pending F3 full generation)`**.
  9. **AI disclosure / known limitations / ethical considerations.**
  10. **Citation** (aligned with the existing README citation) + license.

- **G3b — README "Synthetic Variant" section.** Append `## Synthetic Variant
  (BC3CAT-Syn)` to [`README.md`](../../README.md): 1–3 short paragraphs +
  pointers to `docs/synthetic/DATA_CARD.md`, the two release files, and the
  loader API. Additive only; existing sections untouched.

- **G4 — new file `docs/synthetic/HANDOFF.md`** (short memo, decision 4): file
  locations + 1:1 join, the new slice columns + §6 condition slices, the
  `synthetic.loaders` surface + `long_view`/`short_view` ↔ OEB `_norm` mapping,
  and the "not yet generated — pending A3 + F3" status line.

- **Doc + housekeeping**:
  - Flip the ❌ `DATA_CARD.md` (line ~204) and `HANDOFF.md` (line ~206) rows ✅
    in the "Branch Documentation" / file map of
    [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md); note the README
    "Synthetic Variant" section; record the documentation-only / no-fabricated-
    stats / additive-README / handoff-only-memo decisions. Prepend an
    "After Sprint 23" Sprint History entry.
  - Sprint 23 entry in [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md).
  - Flip the `G3` / `G4` portion of the relevant §3 status row in
    [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) (the "Documentation /
    release docs" line, if present; otherwise annotate the Phase-G status).
    Status flip only — no design edit.

### Out of scope (explicit)

- **A3 (concrete `LLMClient` transport) and the Phase F pilot (F1–F4).** A3 is
  Sprint 24; F1–F2 are blocked on it; F3 full generation and F4
  (`QUALITY_REPORT.md`) follow. Sprint 23 documents the *format*, not a generated
  corpus.
- **Any corpus statistics in `DATA_CARD.md`.** No real numbers exist (no F3).
  Statistics are `TBD` placeholders; a post-F3 refresh fills them (decision 1).
- **Any new code module or test.** G3/G4 are Markdown. The suite stays at the
  Sprint 22 baseline (719 passed, 1 skipped). No Markdown-parsing doc-drift
  test (the schema is already pinned in `test_packaging.py` / `test_loaders.py`)
  (decision 2).
- **`QUALITY_REPORT.md` (F4).** That is the validation-pass report, written after
  a real review pass — Phase F, not G3.
- **Changes to `bc3cat-retrieval`.** `HANDOFF.md` *points* the downstream repo at
  the release; the `import`/index integration is a `bc3cat-retrieval` change,
  not this sprint (decision 4).
- **Rewording the existing `README.md` BC3CAT content.** The README edit is a
  pure append (decision 3).
- **Changes to `packaging.py` / `loaders.py` / `metadata.py` / `review.py` / any
  `layer_*` / `mutator` / `run_synthetic` / `stage_runners`.** Sprint 23 is
  documentation; it consumes the frozen G1/G2 contract and changes no code.
- **Merging `synthetic` to `main`.** Permanently forbidden
  ([`CLAUDE.md`](../../CLAUDE.md)).

---

## Content requirements

1. **`DATA_CARD.md` exists and documents the frozen contract.** Its items-schema
   section lists **exactly** the nine `ITEM_COLUMNS` (in order) and the sidecar
   `modifications` payload; its taxonomy section lists all 12
   `ModificationType`s with their `Layer`. No column or type the code does not
   have; none omitted.
2. **Every corpus-scale figure is a marked `TBD` placeholder.** No fabricated or
   OEB-borrowed counts/rates presented as BC3CAT-Syn measurements. A reader can
   tell at a glance which facts are format (final) and which are statistics
   (pending F3).
3. **`README.md` gains an additive "Synthetic Variant (BC3CAT-Syn)" section.**
   The existing sections are byte-unchanged except for the inserted section; the
   new section links `docs/synthetic/DATA_CARD.md`, the two release files, and
   the loader API.
4. **`HANDOFF.md` exists and is a self-contained cross-repo memo.** It names the
   two files + 1:1 `item_key` join, the slice columns + §6 conditions, the
   `synthetic.loaders` surface + the `long_view`/`short_view` ↔ OEB `_norm`
   mapping, and the "pending A3 + F3" status — without modifying
   `bc3cat-retrieval`.
5. **License + AI-disclosure are stated.** CC-BY 4.0 for the dataset (mirroring
   the parent), MIT for code; the LLM-proposed / rule-applied / reviewer-validated
   provenance is prominent (decisions 5–6).
6. **No code, no test, no statistics fabrication; the suite is unchanged.**
   `pytest tests -q` still reports 719 passed, 1 skipped (decision 2).

---

## Acceptance

- `docs/synthetic/DATA_CARD.md`, `docs/synthetic/HANDOFF.md` exist; `README.md`
  has a `## Synthetic Variant (BC3CAT-Syn)` section.
- `DATA_CARD.md`'s items-schema section enumerates exactly `ITEM_COLUMNS`
  (9 columns, correct order) and its taxonomy section lists all 12
  `ModificationType`s with the right `Layer`; spot-check against
  `src/synthetic/packaging.py` and `src/synthetic/taxonomy.py`.
- Every corpus statistic in `DATA_CARD.md` is an explicit `TBD (pending F3)`
  placeholder; no invented numbers.
- `README.md`'s pre-existing sections are unchanged (a `git diff` shows only the
  inserted Synthetic-Variant section); the section links the data card, the two
  files, and the loader API.
- `HANDOFF.md` is self-contained and names the files, join, slice columns,
  loader surface, and pending-A3/F3 status.
- `pytest tests -q` exits 0 with **719 passed, 1 skipped** (unchanged from
  Sprint 22 — Sprint 23 adds no tests).
- Housekeeping: `CLAUDE_SYNTHETIC.md` `DATA_CARD.md` + `HANDOFF.md` rows flipped
  ✅ with the README note + decisions recorded and an "After Sprint 23" history
  entry; `RESEARCH_LOG.md` Sprint 23 entry prepended; the §3 G3/G4 status
  flipped.

---

## Tasks

### Task 1 — `docs/synthetic/DATA_CARD.md` (G3a)
Write the Data-in-Brief card per the Scope §G3a section list. Pull the schema
from `packaging.ITEM_COLUMNS`, the taxonomy from `taxonomy.ModificationType` /
`TYPE_TO_LAYER`, the slices from `RESEARCH_PROTOCOL.md §6`, the loader usage from
`loaders.py`, the per-item record from `RESEARCH_PROPOSAL.md §2.3`. **All
corpus statistics → `TBD (pending F3)`.** License CC-BY 4.0; prominent AI
disclosure.

### Task 2 — README "Synthetic Variant" section (G3b)
Append `## Synthetic Variant (BC3CAT-Syn)` to `README.md` (additive; existing
content verbatim). Link the data card, the two release files, the loader API.

### Task 3 — `docs/synthetic/HANDOFF.md` (G4)
Write the short cross-repo memo per decision 4 / requirement 4. No
`bc3cat-retrieval` edits.

### Task 4 — Housekeeping
1. Prepend a Sprint 23 entry (newest-first) to
   [`../RESEARCH_LOG.md`](../RESEARCH_LOG.md): the G3+G4-over-A3 sequencing, the
   document-the-frozen-contract / no-fabricated-statistics decision (and the
   post-F3 refresh follow-up), the documentation-only / suite-unchanged note,
   the additive-README and handoff-only-memo decisions, and the next step
   (Sprint 24 — A3).
2. In [`../CLAUDE_SYNTHETIC.md`](../CLAUDE_SYNTHETIC.md): flip the ✅
   `DATA_CARD.md` + `HANDOFF.md` rows; note the README section; record the
   decisions; prepend the "After Sprint 23" history entry.
3. In [`../RESEARCH_PROTOCOL.md`](../RESEARCH_PROTOCOL.md) §3: flip the G3/G4
   documentation status — status only, no design edit.

---

## Verification runbook

Run from repo root (`D:\Users\cesar\Dev\Phd\bc3cat-dataset`):

```powershell
$env:PYTHONPATH = "src"
# A stale %TEMP%\pytest-of-cesar\pytest-current symlink can raise WinError 5
# during pytest's tmp-cleanup; route to a fresh basetemp to sidestep it.
pytest tests -q --basetemp="$env:TEMP\pt_s23"
```

Expected: **719 passed, 1 skipped**, unchanged from Sprint 22 (Sprint 23 adds no
tests — it is documentation-only). Zero failures in any tree.

Manual doc checks (no automation):

```powershell
# Schema enumerated in the card matches the frozen code contract:
python -c "from synthetic.packaging import ITEM_COLUMNS; print(ITEM_COLUMNS)"
python -c "from synthetic.taxonomy import TYPE_TO_LAYER; [print(t.value, l.value) for t,l in TYPE_TO_LAYER.items()]"
# README edit is purely additive:
git diff -- README.md   # only the inserted Synthetic-Variant section
```

End-of-sprint expected `git status --short` (sprint-scoped subset):

```
new file:   docs/synthetic/DATA_CARD.md
new file:   docs/synthetic/HANDOFF.md
modified:   README.md
modified:   docs/synthetic/CLAUDE_SYNTHETIC.md
modified:   docs/synthetic/RESEARCH_LOG.md
modified:   docs/synthetic/RESEARCH_PROTOCOL.md
new file:   docs/synthetic/sprints/SPRINT_23.md (this file)
```

No edits to any `src/synthetic/*.py` / `tests/synthetic/*.py`; no new
dependency; no statistics fabricated.

---

## Design notes worth committing to memory

- **Document the contract, not a corpus that doesn't exist yet.** The format,
  schema, taxonomy, slices, and loader API are frozen and real (G1/G2); the
  corpus is not generated (F3 blocked on A3). The card states the former as
  final and the latter as `TBD (pending F3)` — never fabricating numbers. A
  post-F3 statistics refresh is the follow-up.
- **G3/G4 are documentation-only — the suite is unchanged.** No code module, no
  new test; 719 passed, 1 skipped stands. The schema the card documents is
  already pinned in `test_packaging.py` / `test_loaders.py`.
- **The README edit is additive; the BC3CAT description stays verbatim.** And
  `synthetic` still never merges to `main`.
- **`HANDOFF.md` points; it does not wire.** The downstream `bc3cat-retrieval`
  `import`/index integration is that repo's change.
- **Next is A3.** Sprint 24 builds the concrete `LLMClient` transport, unblocking
  the Phase F pilot (F1–F2), then F3 full generation, F4 validation, and the
  `DATA_CARD.md` statistics refresh.

---

## References

- [`../RESEARCH_PROTOCOL.md §5 Phase G`](../RESEARCH_PROTOCOL.md) — G3 (docs,
  this sprint), G4 (handoff, this sprint); §6 generation conditions (the slice
  table for the card); §7 file map (`DATA_CARD.md`, `HANDOFF.md`,
  `QUALITY_REPORT.md` locations).
- [`SPRINT_22.md`](SPRINT_22.md) / [`../../src/synthetic/loaders.py`](../../src/synthetic/loaders.py)
  — the G2 loader API the card documents (`load_items`/`load_modifications`/
  `join`/`long_view`/`short_view`, the `text` + `text_norm` view shape).
- [`SPRINT_21.md`](SPRINT_21.md) / [`../../src/synthetic/packaging.py`](../../src/synthetic/packaging.py)
  — the G1 release format the card documents (`ITEM_COLUMNS`, the two filenames,
  the 1:1 `item_key` join, the sidecar payload).
- [`../../src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) —
  `ModificationType` (12) × `Layer` (4) via `TYPE_TO_LAYER` (the card's taxonomy
  section); `Modification.to_dict` (the sidecar payload shape).
- [`../RESEARCH_PROPOSAL.md`](../RESEARCH_PROPOSAL.md) — §2.3 per-item record
  (the items-schema source); §5 release-format note; §2 the three-layer grammar
  (provenance section).
- [`../../README.md`](../../README.md) — the existing dataset README (the
  "Synthetic Variant" section is appended here; the `### AI Disclosure` and
  CC-BY-4.0 "Dataset" license blocks are the precedent the card mirrors).
- [`../../CLAUDE.md`](../../CLAUDE.md) — the never-merge-`synthetic`-to-`main`
  invariant (the README edit lives only on `synthetic`).

---

## Non-goals reminder

If you find yourself writing a concrete `LLMClient`, calling a model, or running
`run_synthetic` / `stage_b` to *generate* items — **stop**. That is A3 (Sprint
24) + Phase F. G3/G4 document the frozen format; they generate nothing.

If you find yourself writing a real item count, per-type acceptance rate, or any
corpus-scale number in `DATA_CARD.md` — **stop**. No F3 has run; there is no
corpus to count. Write `TBD (pending F3)`. Fabricated or OEB-borrowed numbers
presented as BC3CAT-Syn measurements are a correctness bug.

If you find yourself adding a code module, a pytest file, or a Markdown-parsing
doc-drift test — **stop**. Sprint 23 is documentation-only; the suite stays at
719 passed, 1 skipped. The schema is already pinned in `test_packaging.py` /
`test_loaders.py`.

If you find yourself rewording the existing `README.md` BC3CAT sections, or
editing `bc3cat-retrieval`, or proposing a merge of `synthetic` into `main` —
**stop**. The README edit is a pure append; the handoff is a memo, not a wiring;
`synthetic` never merges to `main`.

If you find yourself listing a column `ITEM_COLUMNS` does not have (e.g. an
OEB-only `id`/`ud`/`concept`, or a `parent_key`) or omitting one it does —
**stop**. The card mirrors the frozen §2.3 record + `concept_key`, exactly
(decision 5).
