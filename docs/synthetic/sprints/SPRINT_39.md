# Sprint 39 — Presupuestos + sampler determinista + driver — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate the pilot synthetic corpus (~9,150 items, 10 conditions, 9 types) from the approved pantry, deterministic and paired, into the frozen release files `BC3CAT_Syn_items.parquet` + `BC3CAT_Syn_modifications.jsonl`, plus the corpus QA report. Spec: [`SPRINT_39_DESIGN.md`](SPRINT_39_DESIGN.md) (binding).

**Architecture:** Three new consumer modules above the frozen seam — `pantry.py` (reads menus+verdicts → applicable approved rewrites per concept), `corpus_sampler.py` (budgets YAML → deterministic per-concept/per-condition plan with reuse caps and composition checks, leaf inventory from the original OEB parquet), `corpus_driver.py` (plan → `rule_emitter.emit_rules` → `stage_b.materialize_variant` with the `l2_repr` pre-rerun hook → leaf extraction → filters → `packaging.write_release` + report). No LLM anywhere; generation is pure CPU.

**Existing seams to reuse (verified 2026-08-31, do not re-implement):**
- `rule_emitter.emit_rules(payload, mtype, *, target_id, stage_json, concept_key) -> EmissionResult` (src/synthetic/rule_emitter.py:32)
- `composition.compose_rules(...)` (src/synthetic/composition.py:85) + canonical order L1→L2→L3
- `stage_b.materialize_variant(stage2_json, concept_key, variant, *, pre_rerun) -> MaterializedVariant` (src/synthetic/stage_b.py:119); `VariantRecord(condition, modification_type, target_id_repr, rules)` (src/synthetic/variant_catalog.py:33)
- `l2_repr.list_to_formula(include_conditional=True)` before rule emission / `formula_to_list` as `pre_rerun` (the F1-pilot discipline — read `f1_pilot.py` for the exact bracket)
- `metadata.SyntheticItem` (src/synthetic/metadata.py:46) and metadata's original_key join — read `metadata.py` before Task 4
- `packaging.write_release(...)` (src/synthetic/packaging.py:172), `loaders.load_items/join`
- Verdicts schema: `data/synthetic/menus/verdicts/{tipo}.jsonl` — one line per target: `{candidates: [{approved: bool, payload: {...}}...], canonical, dedup_key, modification_type, skipped_reason}`; payload order aligns 1:1 with `data/synthetic/menus/{tipo}.jsonl` candidates. `usages` (concept_key + slot_extractor_target_id) live in the MENUS jsonl, not the verdicts — the pantry joins both by line index.
- Leaf inventory: `data/processed/OEB_long_norm.parquet` (item_key + params per leaf; concept = item_key prefix through the parent key rule `parent_key[:-1]`).

**Design constants (from the spec — binding):**

```python
EXCLUDED_TYPES = {ModificationType.OMISSION, ModificationType.NEW_PARAM}
CONDITIONS = [f"single_{t}" for t in NINE_TYPES] + ["all_combined"]
TARGETS = {  # n objetivo por condición
    "single_paraphrase": 1000, "single_expansion": 1000, "single_template_paraphrase": 1000,
    "single_synonym_label": 1000, "single_compression": 1000, "single_reorder": 1000,
    "single_num_to_text": 650, "single_unit_expansion": 650, "single_unit_conversion": 350,
    "all_combined": 1500,
}
REUSE_CAP = {"num_to_text": 20, "unit_expansion": 20, "unit_conversion": 20}  # usos máx por reescritura única
SEED = 39
```

**Conventions:** repo root `D:\Users\cesar\Dev\Phd\bc3cat-dataset`, branch `synthetic` (NEVER merge to `main`). Tests: `pytest tests/synthetic -q --basetemp "C:\Users\cesar\AppData\Local\Temp\claude\D--Users-cesar-Dev-Phd-bc3cat-dataset\7bc6b896-cc42-40f9-847f-3e432e8a1b86\scratchpad\ptN"` (fresh ptN). Baseline: **1061 passed, 2 skipped** (`tests/synthetic`; full `tests` = 1085). Commits end `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. No live LLM at any point.

---

## File map

| File | Responsibility |
|---|---|
| `src/synthetic/pantry.py` | **new** — approved rewrites, joined menus+verdicts, applicability per concept |
| `configs/synthetic/variant_budgets.yaml` | **new** — TARGETS/REUSE_CAP/SEED (the spec constants, editable sin tocar código) |
| `src/synthetic/corpus_sampler.py` | **new** — deterministic plan: (concept, leaf, condition, rewrites) |
| `src/synthetic/corpus_driver.py` | **new** — plan → materialize → filters → release + report; CLI |
| `tests/synthetic/test_pantry.py`, `test_corpus_sampler.py`, `test_corpus_driver.py` | **new** — hermetic (tiny fixtures, no real parquet/LLM) |
| `data/synthetic/processed/BC3CAT_Syn_items.parquet` + `..._modifications.jsonl` | generated (Task 5) |
| `docs/synthetic/sprints/SPRINT_39_corpus_report.md` | generated QA report |

---

### Task 1: `pantry.py` — la despensa aplicable

**Files:** Create `src/synthetic/pantry.py`; Test `tests/synthetic/test_pantry.py`.

- [x] **Step 1: failing tests.** Create `tests/synthetic/test_pantry.py`:

```python
"""Sprint 39 — hermetic tests for :mod:`synthetic.pantry`."""
from __future__ import annotations

import json

import pytest

from synthetic.pantry import ApprovedRewrite, load_pantry
from synthetic.taxonomy import ModificationType


def _write_pair(tmp_path, mtype, rows_menu, rows_verdicts):
    (tmp_path / "menus").mkdir(exist_ok=True)
    (tmp_path / "menus" / "verdicts").mkdir(exist_ok=True)
    (tmp_path / "menus" / f"{mtype}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_menu), encoding="utf-8")
    (tmp_path / "menus" / "verdicts" / f"{mtype}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows_verdicts), encoding="utf-8")


def test_load_pantry_joins_menus_and_verdicts_and_filters_approved(tmp_path):
    menu = [{"canonical": "EJE / Diurno", "dedup_key": ["EJE", "Diurno"],
             "modification_type": "synonym_label", "skipped_reason": None, "dropped_reasons": [],
             "usages": [{"concept_key": "C1$", "slot_extractor_target_id": "A", "display": "x"},
                        {"concept_key": "C2$", "slot_extractor_target_id": "A", "display": "x"}],
             "candidates": [{"approved": None, "payload": {"original": "Diurno", "new": "Turno diurno"}},
                            {"approved": None, "payload": {"original": "Diurno", "new": "De día"}}]}]
    verd = [{"canonical": "EJE / Diurno", "dedup_key": ["EJE", "Diurno"],
             "modification_type": "synonym_label", "skipped_reason": None,
             "candidates": [{"approved": True, "payload": {"original": "Diurno", "new": "Turno diurno"}},
                            {"approved": False, "payload": {"original": "Diurno", "new": "De día"}}]}]
    _write_pair(tmp_path, "synonym_label", menu, verd)
    pantry = load_pantry(menus_dir=tmp_path / "menus")
    rs = pantry.by_type[ModificationType.SYNONYM_LABEL]
    assert len(rs) == 1  # only the approved candidate
    r = rs[0]
    assert isinstance(r, ApprovedRewrite)
    assert r.payload["new"] == "Turno diurno"
    assert [u.concept_key for u in r.usages] == ["C1$", "C2$"]
    # applicability index
    assert pantry.for_concept("C1$")[ModificationType.SYNONYM_LABEL] == (r,)
    assert pantry.for_concept("C9$") == {}


def test_load_pantry_excludes_omission_and_new_param(tmp_path):
    for mtype in ("omission", "new_param"):
        menu = [{"canonical": "x", "dedup_key": ["x"], "modification_type": mtype,
                 "skipped_reason": None, "dropped_reasons": [],
                 "usages": [{"concept_key": "C1$", "slot_extractor_target_id": None, "display": "x"}],
                 "candidates": [{"approved": None, "payload": {"original": "a", "new": "b"}}]}]
        verd = [dict(menu[0], candidates=[{"approved": True, "payload": {"original": "a", "new": "b"}}])]
        _write_pair(tmp_path, mtype, menu, verd)
    pantry = load_pantry(menus_dir=tmp_path / "menus")
    assert ModificationType.OMISSION not in pantry.by_type
    assert ModificationType.NEW_PARAM not in pantry.by_type


def test_load_pantry_fails_loud_on_misaligned_files(tmp_path):
    menu = [{"canonical": "x", "dedup_key": ["x"], "modification_type": "reorder",
             "skipped_reason": None, "dropped_reasons": [], "usages": [],
             "candidates": [{"approved": None, "payload": {"original": "a", "new": "b"}}]}]
    verd = [dict(menu[0], candidates=[])]  # different candidate count
    _write_pair(tmp_path, "reorder", menu, verd)
    with pytest.raises(ValueError, match="pantry_misaligned"):
        load_pantry(menus_dir=tmp_path / "menus")
```

- [x] **Step 2:** run → ModuleNotFoundError.

- [x] **Step 3: implement `src/synthetic/pantry.py`:**

```python
"""The approved-rewrite pantry for the Sprint 39 corpus sampler.

Joins ``data/synthetic/menus/{tipo}.jsonl`` (payloads + usages) with
``data/synthetic/menus/verdicts/{tipo}.jsonl`` (approved flags, produced by
``menu_review_parser`` from the reviewed ticks) into per-type tuples of
:class:`ApprovedRewrite`, plus an applicability index per concept.

Sprint 39 design (SPRINT_39_DESIGN.md): ``omission`` and ``new_param`` are
excluded — the benchmark keeps only information-preserving rewrites.
Read-only; fails loud on any misalignment between the two files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils import config
from .taxonomy import ModificationType

EXCLUDED_TYPES = frozenset({ModificationType.OMISSION, ModificationType.NEW_PARAM})


@dataclass(frozen=True)
class Usage:
    concept_key: str
    slot_extractor_target_id: object


@dataclass(frozen=True)
class ApprovedRewrite:
    mtype: ModificationType
    dedup_key: tuple
    canonical: str
    candidate_index: int
    payload: dict
    usages: tuple[Usage, ...]

    @property
    def uid(self) -> str:
        """Stable id for reuse-cap accounting and provenance."""
        return f"{self.mtype.value}:{self.canonical}:{self.candidate_index}"


@dataclass(frozen=True)
class Pantry:
    by_type: dict[ModificationType, tuple[ApprovedRewrite, ...]]

    def for_concept(self, concept_key: str) -> dict[ModificationType, tuple[ApprovedRewrite, ...]]:
        out: dict[ModificationType, tuple[ApprovedRewrite, ...]] = {}
        for mtype, rewrites in self.by_type.items():
            hits = tuple(r for r in rewrites
                         if any(u.concept_key == concept_key for u in r.usages))
            if hits:
                out[mtype] = hits
        return out


def load_pantry(menus_dir: Optional[Path] = None) -> Pantry:
    menus_dir = Path(menus_dir) if menus_dir else config.SYNTHETIC_DATA_ROOT / "menus"
    verdicts_dir = menus_dir / "verdicts"
    by_type: dict[ModificationType, list[ApprovedRewrite]] = {}
    for vfile in sorted(verdicts_dir.glob("*.jsonl")):
        mtype = ModificationType(vfile.stem)
        if mtype in EXCLUDED_TYPES:
            continue
        menu_rows = [json.loads(l) for l in (menus_dir / vfile.name).read_text(encoding="utf-8").splitlines()]
        verd_rows = [json.loads(l) for l in vfile.read_text(encoding="utf-8").splitlines()]
        if len(menu_rows) != len(verd_rows):
            raise ValueError(f"pantry_misaligned: {vfile.name} rows {len(verd_rows)} != menu {len(menu_rows)}")
        for menu_row, verd_row in zip(menu_rows, verd_rows):
            if len(menu_row["candidates"]) != len(verd_row["candidates"]):
                raise ValueError(
                    f"pantry_misaligned: {vfile.name} target {menu_row['canonical']!r} "
                    f"candidates {len(verd_row['candidates'])} != menu {len(menu_row['candidates'])}"
                )
            usages = tuple(Usage(u["concept_key"], u.get("slot_extractor_target_id"))
                           for u in menu_row.get("usages", []))
            for ci, (mc, vc) in enumerate(zip(menu_row["candidates"], verd_row["candidates"])):
                if not vc.get("approved"):
                    continue
                by_type.setdefault(mtype, []).append(ApprovedRewrite(
                    mtype=mtype, dedup_key=tuple(menu_row["dedup_key"]),
                    canonical=menu_row["canonical"], candidate_index=ci,
                    payload=dict(mc["payload"]), usages=usages,
                ))
    return Pantry(by_type={t: tuple(v) for t, v in by_type.items()})
```

**Verificación importante antes de dar por buena la implementación:** comprobar contra los datos reales que la alineación menús↔verdicts se cumple y que los `usages` de los menús llevan `slot_extractor_target_id` (lo llevan — campo `TargetUsage`; si el JSON lo serializó con otro nombre, adaptar `Usage` y decirlo en el informe). Probe obligatorio:

```bash
PYTHONPATH=src python -c "from synthetic.pantry import load_pantry; p=load_pantry(); print({t.value: len(v) for t,v in p.by_type.items()}); print(sum(len(v) for v in p.by_type.values()))"
```
Esperado: 9 tipos, total **1 931** (157/33/18/33/420/444/107/109/610). Si difiere, STOP e investigar (no ajustar el test al número que salga).

- [x] **Step 4:** full suite green; commit `Sprint 39: pantry — approved rewrites + applicability index` (+ trailer).

---

### Task 2: `variant_budgets.yaml` + carga en el sampler

Pequeña: el YAML con las constantes del spec y su lector (dentro de `corpus_sampler.py`, Task 3, para no crear un módulo de 20 líneas). Aquí solo se crea el YAML:

- [x] **Step 1:** Create `configs/synthetic/variant_budgets.yaml`:

```yaml
# Sprint 39 — presupuestos del corpus sintético piloto (SPRINT_39_DESIGN.md).
# Editable sin tocar código; el sampler valida claves y tipos al cargar.
seed: 39
targets:
  single_paraphrase: 1000
  single_expansion: 1000
  single_template_paraphrase: 1000
  single_synonym_label: 1000
  single_compression: 1000
  single_reorder: 1000
  single_num_to_text: 650
  single_unit_expansion: 650
  single_unit_conversion: 350
  all_combined: 1500
reuse_cap:            # usos máximos por reescritura única (tipos finos)
  num_to_text: 20
  unit_expansion: 20
  unit_conversion: 20
```

(Se commitea junto a Task 3.)

---

### Task 3: `corpus_sampler.py` — el plan determinista

**Files:** Create `src/synthetic/corpus_sampler.py`; Test `tests/synthetic/test_corpus_sampler.py`; incluye el YAML de Task 2.

Contrato (el implementador escribe el código siguiendo esto; los tests de abajo son el criterio):

1. `load_budgets(path=None) -> Budgets` — lee el YAML (default `config.REPO_ROOT / "configs/synthetic/variant_budgets.yaml"`); valida que `targets` cubre exactamente las 10 condiciones y que los valores son int>0; `ValueError("budgets_invalid: ...")` si no. PyYAML ya es dependencia del repo (`pyyaml` en el setup de CLAUDE.md).
2. `LeafInventory`: se construye con `leaf_inventory_from_frame(df)` a partir del parquet original (columnas `item_key`, `params`); agrupa hojas por concepto usando la regla del repo: `concept_key = item_key[:len(parent_prefix)]`… **el implementador debe leer cómo `metadata.py` deriva concepto↔item y reutilizar exactamente esa regla** (no inventar el prefijo). Para tests, el constructor acepta un dict `{concept_key: [item_key, ...]}` directo.
3. `build_plan(pantry, inventory, budgets, concepts) -> tuple[PlannedVariant, ...]` donde `PlannedVariant = (condition, concept_key, leaf_item_key, rewrites: tuple[ApprovedRewrite, ...])`:
   - **Reparto:** para cada condición, n se reparte entre los conceptos donde la condición aplica, proporcional al nº de hojas del concepto (redondeo por resto mayor), mínimo 1 donde aplique.
   - **Hojas sin repetición dentro de una condición** (una hoja puede aparecer en condiciones distintas). Selección con `random.Random(seed ^ hash_estable(condition))` — usar un hash estable (p. ej. `zlib.crc32(condition.encode())`), NUNCA `hash()` (salting por proceso rompería el determinismo).
   - **Singles:** elegir 1 reescritura del tipo aplicable a ese concepto, round-robin ponderado con el `reuse_cap` de los tipos finos (si el cap agota la despensa aplicable, la rebanada se queda corta y se registra el déficit — NO se rellena con otros tipos).
   - **all_combined:** una reescritura de CADA tipo aplicable al concepto (5–9); el driver validará composición — el sampler solo evita dos reescrituras sobre el MISMO objetivo (`dedup_key` repetido).
   - Determinismo total: misma entrada → mismo plan, byte a byte (test con doble llamada).
4. `plan_report(plan) -> dict` — por condición: n, nº de reescrituras únicas, reuso máx, déficit vs target.

- [x] **Step 1: failing tests.** Create `tests/synthetic/test_corpus_sampler.py` con al menos estos casos (código completo, fixtures mínimas construidas a mano con 2 conceptos × 6 hojas y una pantry de juguete de 3 tipos):
  - `test_load_budgets_validates_conditions` (falta una condición → ValueError).
  - `test_plan_is_deterministic` (dos llamadas → planes idénticos).
  - `test_single_condition_uses_one_rewrite_of_its_type` (cada PlannedVariant de `single_X` lleva exactamente 1 rewrite y es del tipo X).
  - `test_all_combined_uses_one_per_applicable_type` (con pantry de 3 tipos aplicables → 3 rewrites, tipos distintos, dedup_keys distintos).
  - `test_leaves_unique_within_condition`.
  - `test_reuse_cap_shortfall_reported` (pantry con 1 reescritura de un tipo fino y cap 2 → n conseguido = 2, déficit registrado en `plan_report`).
  - `test_proportional_allocation` (concepto con 4 hojas recibe el doble que uno con 2, ±1 por redondeo).

- [x] **Step 2:** run → fail. **Step 3:** implementar. **Step 4:** suite verde. **Step 5:** commit `Sprint 39: variant budgets YAML + deterministic corpus sampler` (+ trailer, incluye el YAML).

---

### Task 4: `corpus_driver.py` — materialización + release + informe

**Files:** Create `src/synthetic/corpus_driver.py`; Test `tests/synthetic/test_corpus_driver.py`. **Leer antes:** `f1_pilot.py` (el bracket `l2_repr` exacto), `metadata.py` (SyntheticItem y el join original_key), `stage_b.py`, `packaging.py`, `variant_catalog.py`.

Contrato:

1. `run_corpus(stage2_json, plan, *, out_dir, report_path) -> CorpusRunStats`:
   - Convierte el stage con `l2_repr.list_to_formula(include_conditional=True)` UNA vez para la emisión de reglas, y usa `l2_repr.formula_to_list` como `pre_rerun` en la materialización (calcar la disciplina de `f1_pilot.run_pilot` — misma secuencia, mismos argumentos).
   - Por cada `PlannedVariant`: `rule_emitter.emit_rules(rewrite.payload, rewrite.mtype, target_id=<slot_extractor_target_id del usage de ESTE concepto>, stage_json=..., concept_key=...)` por reescritura → juntar reglas → `composition.compose_rules` (conflicto → variante descartada + contada en stats, no excepción) → `VariantRecord(condition=..., modification_type=<tipo de la primera regla>, target_id_repr=..., rules=...)` → `stage_b.materialize_variant(...)`.
   - Del `MaterializedVariant.items` extraer LA hoja planificada: mapear `leaf_item_key` original → clave mutada usando la misma lógica de correspondencia que usa `metadata.py` (los L1 cambian valores pero no las letras de la clave; verificarlo leyendo metadata y con el test de integración). Construir el `metadata.SyntheticItem` con `original_key=leaf_item_key`, `variante_id` estable (hash corto de condición+concepto+leaf+uids), tipos/count/mods del MaterializedVariant.
   - Filtros: no-op (resumen Y texto idénticos al original de esa hoja → descartar+contar), dedup exacto por (resumen, texto) dentro del corpus (descartar+contar), verificación `$`-placeholder sin resolver o `[[` en el texto → **excepción** (eso sería bug, no dato).
   - `packaging.write_release(items, ...)` a `data/synthetic/processed/`; informe Markdown a `report_path` con la tabla del spec (n vs objetivo, reescrituras únicas, reuso, no-ops, dups, descartes por composición, distancia media de token al original por condición).
2. CLI `python -m synthetic.corpus_driver run --stage-json ... --concepts OEB --budgets ... [--out-dir ...] [--report ...]`.

- [x] **Step 1: failing tests** (código completo en el archivo de test; hermético con un stage de juguete de 1–2 conceptos pequeños estilo `tiny_chapter` y una pantry sintética):
  - `test_run_corpus_produces_valid_release(tmp_path)` — 2 variantes planificadas → parquet+jsonl escritos, `loaders.load_items` los lee, `loaders.join` no falla, columnas == `packaging.ITEM_COLUMNS`, tripleta única.
  - `test_synthetic_item_pairs_with_original` — `original_key` correcto y texto ≠ original (el cambio se aplicó de verdad).
  - `test_noop_variant_dropped_and_counted`.
  - `test_composition_conflict_skipped_not_raised` (dos reescrituras incompatibles en all_combined → variante descartada, stats lo cuentan).
  - `test_placeholder_residue_raises`.
  - `test_deterministic_output` (dos ejecuciones → parquet byte-idéntico; comparar hashes).

- [x] **Step 2-4:** TDD como siempre; suite completa verde. **Step 5:** commit `Sprint 39: corpus driver — materialize plan, filters, frozen release + report` (+ trailer).

---

### Task 5: Generación del corpus piloto  **[CHECKPOINT: informe a César antes de Task 6]**

Sin LLM — solo CPU; estimar minutos, no horas.

- [x] **Step 1:**
```bash
PYTHONPATH=src python -m synthetic.corpus_driver run --stage-json "data/intermediate/OBRA CIVIL/OBRA CIVIL.json" --concepts OEB --budgets configs/synthetic/variant_budgets.yaml
```
- [x] **Step 2: verificaciones** — el informe cumple: total ≈ objetivo (déficits solo en tipos finos y explicados), 0 residuos, tasas de no-op/dup razonables (<5 %; si un tipo pierde >20 % en no-ops, STOP y reportar); `PYTHONPATH=src python -c "from synthetic.loaders import load_items, load_modifications, join; join(load_items(), load_modifications())"` sin errores; segunda ejecución reproduce el parquet (hash).
- [x] **Step 3: muestra ocular** — 10 ítems al azar impresos (original vs sintético, condición) para el checkpoint.
- [x] **Step 4: commit** de release + informe (`Sprint 39: pilot synthetic corpus — <n> items, 10 conditions` + trailer). **STOP: informe a César** (tabla del corpus, déficits, la muestra de 10). Task 6 solo con su OK.

---

### Task 6: Docs y cierre

- [x] `RESEARCH_LOG.md`: entrada Sprint 39 (decisiones de diseño de César — exclusiones, sin stacking, n por significación —, números finales del corpus, determinismo verificado). `RESEARCH_PROTOCOL.md` §6: nota de enmienda (condiciones stacked/new_param_only retiradas del piloto por decisión 2026-08-31; el esquema las sigue soportando). `STATUS_*`: siguiente = Sprint 40 + repo hermano ya puede consumir. `CLAUDE_SYNTHETIC.md`: filas de módulos nuevos. `HANDOFF.md`: cambiar el aviso "not yet generated" por el estado real (piloto generado, stats del corpus).
- [x] `pytest tests -q` verde; commit docs (+ trailer).

---

## Self-check spec↔plan

Exclusiones y 10 condiciones → constantes + pantry (T1) y YAML (T2); n y caps → YAML + sampler (T3); pareado/`original_key`/tripleta única → driver (T4 tests); determinismo → tests T3+T4; informe con reescrituras únicas → `plan_report` + informe T4; déficit-sin-reasignar → T3; esquema congelado → `packaging.write_release` sin tocar; sin stacking → no existe en condiciones; riesgos del spec → filtros y stats del driver.
