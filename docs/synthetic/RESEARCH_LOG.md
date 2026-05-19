# Research Log — BC3CAT-Syn

**Project:** BC3CAT-Syn — Rule-Modification Synthetic Benchmark
**Branch:** `synthetic`
**Started:** May 2026

---

## How to Use This Log

Append an entry after every sprint. Each entry should capture:
- **What was attempted and what was accomplished** — concrete deliverables, not intentions.
- **Key results** — numbers, observations, acceptance-rate tables, throughput, accuracy on review samples.
- **Decisions made and their rationale** — especially anything that updates the design table in `CLAUDE_SYNTHETIC.md` or §4 of `RESEARCH_PROTOCOL.md`.
- **Problems encountered and how they were resolved (or not)** — including dead-ends; negative results matter.
- **What changed in the plan as a result** — task IDs added, split, or removed from the protocol backlog.

Be concrete. Write numbers, not impressions. This log serves two purposes: (1) context recovery if we lose track of where we are, and (2) source material for the BC3CAT-Syn Data-in-Brief paper's methodology section.

Each entry ends with two housekeeping lines:
- **CLAUDE_SYNTHETIC.md updated:** `yes` / `no` — did the file map, sprint-history block, or design table change?
- **Next step:** the sprint or task that should pick up next.

---

## Log Entries

*Newest entries at the top.*

---

### Sprint 00 — Documentation scaffolding
**Date:** 2026-05-19
**Sprint file:** *(none — pre-sprint scaffolding work)*
**Tasks from backlog:** (precondition for) A1

**What was done:**
- Authored [`RESEARCH_PROPOSAL.md`](RESEARCH_PROPOSAL.md). Adapts the BC3CAT-Syn rule-modification idea into the SEPLN-style proposal template used by `bc3cat-retrieval/docs/RESEARCH_PROPOSAL.md`. Contains motivation, anatomy of a BC3 concept, the 12-type modification taxonomy, the per-item metadata schema, the four-stage generation pipeline, the evaluation plan, and §6/§7 future work + open questions.
- Authored [`RESEARCH_PROTOCOL.md`](RESEARCH_PROTOCOL.md). Implementation roadmap mirroring `bc3cat-retrieval/docs/RESEARCH_PROTOCOL.md`: repo context with the s01…s07 stage contract, three-layer injection interface, design-decisions table, phased task backlog (A → G), generation conditions, new file map, Spanish prompt templates, risk register.
- Authored [`../../CLAUDE.md`](../../CLAUDE.md) at the repo root — generic guidance for the dataset-generation pipeline, with a branch note routing the `synthetic` branch here.
- Authored [`CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md) — the branch-specific Claude Code context file: problem in one paragraph, mutation architecture diagram, design table, data structures, ✅/❌ file map.
- Authored this log.

**Key results:**
- Five documents created, zero source-code changes.
- Cross-links between the four docs resolve (relative paths within `docs/synthetic/`, plus one upward link to the repo-level `CLAUDE.md`).
- File-map in `CLAUDE_SYNTHETIC.md` is internally consistent with `RESEARCH_PROTOCOL.md §3.5` ("What Exists vs. What Needs Building") — every ❌ in the CLAUDE file corresponds to an unbuilt task in the protocol backlog.

**Decisions made:**
- **Injection level:** JSON-intermediate, between stages s02/s03/s04. Rejected raw-BC3 mutation because it would require re-serialising BC3 surface form for L1/L2 changes and would conflate which layer caused each surface-form delta.
- **Scope:** dataset-only. Retrieval evaluation against BC3CAT-Syn gets its own protocol in `bc3cat-retrieval`. Avoids cross-repo coupling.
- **Doc filename convention:** mirror the retrieval repo's split — repo-level `CLAUDE.md` + folder-level `CLAUDE_SYNTHETIC.md`. Confirmed with user when comparing against the structured-retrieval branch's `CLAUDE_STRUCTURED_RETRIEVAL.md`.

**Problems encountered:**
- `s01_parse_fiebdc.ipynb` hardcodes `/work/data/raw/`. Noted as Task A4 in the protocol; will be the first piece of code refactored in Sprint 01.
- The proposal's "modify the BC3 file" phrasing is at slight tension with the JSON-intermediate decision. Resolved by clarifying in `RESEARCH_PROTOCOL.md §3.3` that the mutation operates on the *parsed* representation, not the BC3 surface form, and that this is equivalent for the proposed contributions because the existing parser is bijective on the rule-defining sub-grammar.

**Changes to plan:**
- None — the protocol backlog A1…G4 reflects the agreed design.

**CLAUDE_SYNTHETIC.md updated:** yes (created in this sprint).
**Next step:** Draft `sprints/SPRINT_01.md` covering Phase A — Tasks A2 (`src/synthetic/taxonomy.py`), A4 (path refactor), and A5 (`src/synthetic/mutator.py` injection harness). A3 (LLM proposer spike) and A1 (branch scaffolding sprints/ + CLAUDE update plumbing) can be folded in or split out depending on bandwidth.
