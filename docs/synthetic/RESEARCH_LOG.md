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

### Sprint 03 — Path refactor: s02–s07 notebook migration
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_03.md`](sprints/SPRINT_03.md)
**Tasks from backlog:** A4 part 2 (s02–s07 notebook migration). A4 part 3 (s08 + `Generate_OEB_dataset`) remains open for Sprint 04.

**What was done:**
- Fanned the Sprint 02 migration pattern across the six remaining synthetic-critical-path notebooks. **14 source-cell `/work/...` literals** were rewritten in a single `json.load` → patch → `json.dumps(indent=1, ensure_ascii=False)` cycle per notebook, distributed as: s02 cell 2 (1), s03 cell 2 (1), s04 cell 3 (1), s05 cell 3 (1), s06 cell 2 (1), s07 cell 2 (2), s07 cell 3 (1), s07 cell 8 (4), s07 cell 11 (2). Replacements route through `config.INTERMEDIATE_DIR`, `config.chapter_path("OBRA CIVIL")`, and `config.stage_path("OBRA CIVIL", N)`; s07's three `_duplicate_*.json` side-artifacts inline as `config.INTERMEDIATE_DIR / chapter / f"{chapter}_..."`.
- Removed the two `project_root = Path('/work'); sys.path.append(str(project_root))` bootstrap pairs from `s07_Filter_duplicates.ipynb` cells 3 and 8 — **−4 source lines** of dead code. They were redundant because Jupyter's per-notebook kernel cwd is `src/` and `utils` is on the implicit `sys.path` entry (Sprint 02 finding). `from utils import config` was inserted into each touched cell's import block.
- Added [`tests/utils/test_notebooks_no_work_literal.py`](../../tests/utils/test_notebooks_no_work_literal.py) — a parametrised regression-guard test that scans the `source` arrays of s01–s07 and asserts zero `/work/` occurrences. Output arrays (`outputs`) are exempt per the s01 policy. Sprint 04 will extend the notebook list to include s08 + `Generate_OEB_dataset`.

**Key results:**
- `pytest tests -q` → **49 passed in 0.07s** (30 Sprint 01 + 12 Sprint 02 + 7 new notebook-guard cases). No regressions.
- Both smoke checks pass: all 7 notebooks parse via `json.load`, and `source-cell /work/ hits across s01-s07: 0`.
- `git status --short` matches the sprint's expected end-state exactly: 6 modified notebooks (`src/s0{2..7}*.ipynb`), 1 new test file, plus this log + `CLAUDE_SYNTHETIC.md` housekeeping. Nothing under `src/synthetic/`, `tests/synthetic/`, `data/`, or `configs/` in the diff.
- Per-notebook diff scope (`git diff --numstat`): s02 +3 / −1, s03 +3 / −1, s04 +3 / −1, s05 +3 / −1, s06 +3 / −1, s07 +14 / −13. The s07 net is only +1 because the four `project_root` / `sys.path.append` bootstrap lines are deleted while exactly five `from utils import config` insertions and the nine line-by-line path rewrites are added — confirming the bootstrap removal landed.

**Decisions made:**
- **Path objects passed bare.** `marcar_duplicados(path_entrada=config.stage_path(...), ...)` and `main(config.chapter_path(...))` go in without a `str(...)` wrapper. The static-check gate doesn't exercise runtime behaviour, but Sprint 02's s01 edit set the precedent (`os.chdir(config.RAW_DIR)` works because `os.chdir` accepts path-like objects) and the same pattern holds for every callee touched here. End-to-end validation in a future sprint is the gate that would catch a real mismatch.
- **Side-artifact paths inlined, not helper-promoted.** The three `_duplicate_*.json` paths and the `_either_duplicate.json` path in s07 cell 8 deliberately use `config.INTERMEDIATE_DIR / chapter / f"{chapter}_..."` rather than a new `chapter_artifact(chapter, suffix)` helper. YAGNI: only three callers in one cell. If a third site for `_duplicate_*` patterns surfaces in Sprint 04+, the helper can land then.
- **One helper script, one load/write cycle per notebook.** The Sprint 02 recipe (`json.load` → patch `source` arrays → `json.dumps(indent=1, ensure_ascii=False)`) reused unchanged. For s07's nine sites across four cells, a single load/edit/write cycle was used to keep the JSON pretty-printing stable across all the cell edits (avoiding nine re-pretty-prints that would have churned unrelated whitespace).
- **LF line endings preserved.** All six target notebooks use LF in-repo; the patch helper writes via `Path.write_bytes(json_text.encode("utf-8") + b"\n")` (bypassing Windows' universal-newlines text-mode translation). git's `core.autocrlf` produced a soft "LF will be replaced by CRLF" warning on each touched file but the in-repo bytes are LF, matching the existing convention.
- **Cell 11 of s07 import block.** Cell 11 originally imported only `import json` and relied on cells 3/8 to provide `Path` at notebook-execution time. After our rewrite, cell 11 no longer references `Path` (both call sites became `config.stage_path(...)`), so only `from utils import config` was added. No new transitive-import surprise — the cell stays self-sufficient for the columns it actually uses post-edit.

**Problems encountered:**
- None blocking. The atexit `cleanup_dead_symlinks` traceback observed at pytest shutdown is a known Windows-temp-dir-cleanup PermissionError unrelated to test outcomes (49 passed prints before the traceback). Same host as Sprint 02; no action.
- The Sprint 03 plan's expected `git status` does not list a `scripts/` directory. The one-shot migration helper that drove the 14 edits was authored under `scripts/sprint03_migrate_notebooks.py` for traceability, then removed after the patch landed cleanly — the durable artifact is the regression test, not the helper. Sprint 02 followed the same convention implicitly (no `scripts/` in its end-of-sprint diff either).

**Changes to plan:**
- None to the protocol. A4 part 2 closes; A4 part 3 (s08 + `Generate_OEB_dataset`) stays open for Sprint 04.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped s02–s07 from "❌ Task A4 part 2" to "✅ Sprint 03" in the "Existing files extended" block; prepended "After Sprint 03" to the Sprint History section. s08 + `Generate_OEB_dataset` remain ❌ for Sprint 04.
**Next step:** Draft `sprints/SPRINT_04.md` for A4 part 3 — fan the same migration pattern across `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb`. After Sprint 04 lands, the natural follow-up is the end-to-end-validation sprint that reruns s01 → s07 against the existing `data/intermediate/...` and byte-diffs the outputs against the in-repo `OEB_*.parquet` to confirm the path refactor is behaviour-preserving.

---

### Sprint 02 — Path refactor: config core + s01 migration
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_02.md`](sprints/SPRINT_02.md)
**Tasks from backlog:** A4 part 1 (config core + s01). A4 part 2 (s03–s07 notebook migration) remains open for Sprint 03.

**What was done:**
- Rewrote [`src/utils/config.py`](../../src/utils/config.py) into the single-source-of-truth paths module. New public surface: `REPO_ROOT`, `DATA_ROOT`, `RAW_DIR`, `INTERMEDIATE_DIR`, `PROCESSED_DIR`, `LLAMAINDEX_DIR`, `SYNTHETIC_DATA_ROOT`, `SYNTHETIC_INTERMEDIATE_DIR`, `SYNTHETIC_PROCESSED_DIR`, `SYNTHETIC_VARIANTS_DIR`, plus the helpers `chapter_path(chapter, *, root=INTERMEDIATE_DIR)` and `stage_path(chapter, stage_n, *, root=INTERMEDIATE_DIR)`. Env-var overrides `BC3CAT_DATA_ROOT` and `BC3CAT_SYNTHETIC_DATA_ROOT` are read at import time. The legacy `Config` class is preserved; its `DATA_DIR` / `TEXTO_PATH` / `RESUMEN_PATH` now route through `LLAMAINDEX_DIR`, so the `/work/data/llamaindex` literal disappears without touching `Config`'s public surface.
- Refactored [`src/s01_parse_fiebdc.ipynb`](../../src/s01_parse_fiebdc.ipynb): the two `os.chdir('/work/...')` sites (cell 1's `/work/data/raw` and `main()`'s `/work/data`) become `os.chdir(config.RAW_DIR)` / `os.chdir(config.DATA_ROOT)`. Cell 1 now does `from utils import config`. Jupyter's per-notebook kernel cwd is `src/` both inside Docker (`/work/src`) and on the Windows host, so `utils` resolves without a `sys.path` bootstrap. Diff scope: +4 / −2 across two cell `source` arrays, no metadata churn.
- Added [`tests/utils/`](../../tests/utils) with `conftest.py` (clone of `tests/synthetic/conftest.py` — prepends `src/` to `sys.path`) and `test_config.py` — 12 tests covering the eight Task-1 acceptance bullets: import surface, `Path` instance types, default `DATA_ROOT`, env-var override + sub-dir propagation, `SYNTHETIC_DATA_ROOT` default + env override, `chapter_path` / `stage_path` under both default and `SYNTHETIC_INTERMEDIATE_DIR` roots, `Config` back-compat, and the "no `/work/` literal in the module source" check. An autouse fixture with no fixture deps reloads the module after every test so env-var mutations don't bleed across tests in the same session.

**Key results:**
- `pytest tests -q` → **42 passed in 0.08s** (Sprint 01's 30 synthetic tests + 12 new utils tests). No regressions.
- All four smoke checks from the verification runbook pass: default paths, synthetic paths, `chapter_path`/`stage_path` helpers (default + synthetic root), `Config` back-compat. `Grep '/work/' src/utils/config.py` returns zero hits.
- Cell-source `/work/` audit on `s01_parse_fiebdc.ipynb` returns zero hits. `git diff` is exactly the two target lines plus the two-line `from utils import config` / blank-line insert in cell 1.

**Decisions made:**
- Env-var names locked: `BC3CAT_DATA_ROOT` and `BC3CAT_SYNTHETIC_DATA_ROOT`. Sprint 03+ will consume these as-is.
- Notebook bootstrap: chose the minimal `from utils import config` form over the `_REPO_ROOT` walker suggested as a fallback in the sprint plan. Verified that Jupyter's per-notebook kernel cwd is `src/` both inside the Docker container (`/work/src`) and on the Windows host (`…\bc3cat-dataset\src`), so `utils` is on the implicit notebook-dir `sys.path` entry without any bootstrap. Sprint 03's downstream-notebook fan-out will reuse this pattern.
- Notebook editing: `Edit` refuses `.ipynb` files, and full-cell `NotebookEdit` replaces would balloon the diff for the 300-line parser cell. Did byte-precise string replacements on the cell `source` arrays via a one-off `json.load` → patch → `json.dumps(..., indent=1)` script — preserves cell 2 verbatim and keeps the diff to +4 / −2.
- Test cleanup strategy: autouse fixture with no fixture dependencies, so its teardown runs after `monkeypatch`'s teardown — at which point one final `importlib.reload(config)` returns the module to defaults for any later test.

**Problems encountered:**
- The `nbformat`-based JSON-validity smoke check from the verification runbook is unavailable on this host's system Python. Substituted `json.load(...)` for the same well-formedness signal (acceptable because the rewriter emits JSON via `json.dumps`, so syntactic invalidity isn't a realistic failure mode).
- Otherwise none. Sprint plan's per-step acceptance criteria were tight enough that no clarifying questions surfaced.

**Changes to plan:**
- None to the protocol. A4 is split into two halves as the sprint plan anticipated; A4 part 2 (s03–s07 notebooks) is Sprint 03's focus.

**CLAUDE_SYNTHETIC.md updated:** yes — flipped the s01 line in the "Top-level scaffolding" block to ✅ (part 1); noted the new `src/utils/config.py` surface; prepended "After Sprint 02" to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_03.md` for A4 part 2 — fan the same migration pattern across `s02_split_chapters.ipynb` → `s07_Filter_duplicates.ipynb`. Defer `s08_Llamaindex_Doc_Creation.ipynb` and `Generate_OEB_dataset.ipynb` to Sprint 04 since they only emit the final main-pipeline artifacts and are not on the synthetic critical path.

---

### Sprint 01 — Taxonomy module + injection harness skeleton
**Date:** 2026-05-19
**Sprint file:** [`sprints/SPRINT_01.md`](sprints/SPRINT_01.md)
**Tasks from backlog:** A2 (taxonomy), A5 (injection harness). A4 (path refactor) and A3 (LLM proposer spike) were deliberately deferred per the sprint's "Out of scope" block.

**What was done:**
- Created [`src/synthetic/__init__.py`](../../src/synthetic/__init__.py) — package scaffold with `__version__ = "0.1.0"`.
- Created [`src/synthetic/taxonomy.py`](../../src/synthetic/taxonomy.py) — `Layer` (4 members) and `ModificationType` (12 members) as `str, Enum`; `Modification` `@dataclass(frozen=True)` with the proposal §2.3 schema (`type`, `layer`, plus `param`, `var`, `condition`, `field`, `value`, `original`, `new`, `status`, `reason`); `to_dict()` / `from_dict()` JSON-friendly helpers; `TYPE_TO_LAYER` map covering all 12 → all 4 layers.
- Created [`src/synthetic/mutator.py`](../../src/synthetic/mutator.py) — `apply_l1` / `apply_l2` / `apply_l3` / `apply_new_param` public API with the signatures fixed by [`../CLAUDE_SYNTHETIC.md`](CLAUDE_SYNTHETIC.md) "Stage-Hook Integration Note". Internal `_DISPATCH` registers exactly 12 stubs (`_stub_synonym_label` … `_stub_new_param`), each raising `NotImplementedError(f"Phase B: {type_code} mutator not yet implemented")`. Wrong-layer rules and unknown type codes raise `ValueError`; all four entry points deep-copy their input before any mutation.
- Created [`tests/synthetic/`](../../tests/synthetic) with `conftest.py` (prepends `src/` to `sys.path`), `test_taxonomy.py`, and `test_mutator.py` — 30 tests in total covering every acceptance bullet from Tasks 2–3.

**Key results:**
- `pytest tests/synthetic -q` → **30 passed in 0.10s**.
- All three smoke checks from the verification runbook (taxonomy invariants, four `inspect.signature` checks, `_DISPATCH` shape) pass.
- Round-trip via `json.dumps`/`json.loads` of `Modification.to_dict()` preserves all set fields; `None` fields are omitted from the serialised form.
- Stub-raise message uses the type-code string verbatim (e.g. `"Phase B: synonym_label mutator not yet implemented"`), so the parameterised 12-type test matches by substring.
- Deep-copy purity verified: snapshot-before / snapshot-after of the input JSON inside a `pytest.raises(NotImplementedError)` block compares byte-identical.

**Decisions made:**
- `to_dict()` omits `None` fields rather than emitting nulls. Cleaner JSON and round-trips fine because `from_dict()` defaults missing optional fields to `None` via the dataclass.
- Spelled out all 12 stubs as explicit named functions rather than generating them through a factory — the sprint pinned the names (`_stub_synonym_label` … `_stub_new_param`) and Phase B will physically relocate the bodies; named functions make that move mechanical.
- Routed the per-layer entry points through a single internal `_apply_rules(stage_json, concept_key, rules, expected_layer)` helper so the layer gate + deepcopy logic is in one place; `apply_new_param` has its own variant because it takes a single `rule` not a `list[dict]`.
- Test file skips optional `__init__.py` markers under `tests/` and `tests/synthetic/`. `conftest.py` alone is enough for pytest to discover and add `src/` to `sys.path`.

**Problems encountered:**
- None blocking. The sprint's signature and acceptance criteria were precise enough that no clarifying questions surfaced during implementation.

**Changes to plan:**
- None. Backlog A2 + A5 close cleanly; A4 (path refactor) remains the natural Sprint 02 candidate as suggested at the bottom of Sprint 00.

**CLAUDE_SYNTHETIC.md updated:** yes — three ❌ → ✅ flips for the new `src/synthetic/` files; new "After Sprint 01" entry prepended to the Sprint History section.
**Next step:** Draft `sprints/SPRINT_02.md` for Task A4 — un-hardcode `/work/data/raw/` in `s01_parse_fiebdc.ipynb` and route through [`src/utils/config.py`](../../src/utils/config.py). This is the precondition for pipeline reruns from `data/synthetic/intermediate/`.

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
