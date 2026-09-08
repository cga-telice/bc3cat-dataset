"""Package the OE synthetic benchmark for the bc3cat-retrieval project.

Emits files in the exact schema that project consumes — a JSON list of records
``{id, item_key, parent_key, ud, concept, parameters, text}`` — for:

* the **document corpus** (original OE leaves, deduplicated target pool):
  ``OE_texto.json`` (retrieval targets) and ``OE_resumen.json`` (baseline queries);
* the **synthetic query sets** ``OE_stacked_texto.json`` and ``OE_single_texto.json``
  (``text`` = the modified TEXTO; gold is embedded as ``parent_key`` = concept and
  ``gold_item_key`` = original leaf; ``item_key`` is the unique synthetic id);

plus ``OE_concept_schema.json`` (per concept: name, axes, item_keys) and a README.
Everything is bundled into ``BC3CAT_Syn_OE_handoff.zip``.

Gold convention (matches the retrieval harness, which reports parent-level Acc@1):
a query is correct if the retrieved item's ``parent_key`` equals the query's
``parent_key``; for item-level scoring use ``gold_item_key``.

Run (PYTHONPATH=src):
  python scripts/package_for_retrieval.py --stage-json <OE_2026_stage.json> --out-dir data/synthetic/handoff_OE
"""
from __future__ import annotations

import argparse
import json
import uuid
import zipfile
from pathlib import Path

import pandas as pd

_NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")  # fixed namespace → stable ids


def _sid(key: str) -> str:
    return str(uuid.uuid5(_NS, key))


def _jsonable(v):
    """Coerce parquet/numpy cells to JSON-serialisable Python."""
    if hasattr(v, "tolist"):
        return v.tolist()
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-json", required=True)
    ap.add_argument("--target-long", default="data/synthetic/processed_OE/OE_target_long.parquet")
    ap.add_argument("--target-short", default="data/synthetic/processed_OE/OE_target_short.parquet")
    ap.add_argument("--stacked", default="data/synthetic/processed_OE_ablation_stacked")
    ap.add_argument("--single", default="data/synthetic/processed_OE_ablation_single")
    ap.add_argument("--out-dir", default="data/synthetic/handoff_OE")
    ap.add_argument("--collection", default="OE")
    a = ap.parse_args()

    stage = json.loads(Path(a.stage_json).read_text(encoding="utf-8"))
    meta = {k: {"ud": v.get("ud", ""), "concept": v.get("concept", "")} for k, v in stage.items()}
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    col = a.collection

    lo = pd.read_parquet(a.target_long)
    sh = pd.read_parquet(a.target_short).set_index("item_key")["text"].to_dict()
    params_by_leaf = {r.item_key: _jsonable(r.parameters) for r in lo.itertuples(index=False)}

    def doc_record(item_key, parent_key, text):
        m = meta.get(parent_key, {"ud": "", "concept": parent_key})
        return {"id": _sid(item_key), "item_key": item_key, "parent_key": parent_key,
                "ud": m["ud"], "concept": m["concept"],
                "parameters": params_by_leaf.get(item_key, {}), "text": text}

    # 1) document corpus (original OE leaves): texto (targets) + resumen (baseline queries)
    texto_docs = [doc_record(r.item_key, r.parent_key, r.text) for r in lo.itertuples(index=False)]
    resumen_docs = [doc_record(r.item_key, r.parent_key, sh.get(r.item_key, "")) for r in lo.itertuples(index=False)]
    (out / f"{col}_texto.json").write_text(json.dumps(texto_docs, ensure_ascii=False), encoding="utf-8")
    (out / f"{col}_resumen.json").write_text(json.dumps(resumen_docs, ensure_ascii=False), encoding="utf-8")

    # 2) concept schema (per concept: name, axes label->values, item_keys, num_items)
    schema = {}
    leaves_by_concept: dict[str, list[str]] = {}
    for r in lo.itertuples(index=False):
        leaves_by_concept.setdefault(r.parent_key, []).append(r.item_key)
    for ck, ikeys in sorted(leaves_by_concept.items()):
        params = stage.get(ck, {}).get("parameters", {}) or {}
        axes = {ax.get("label", aid): [v.get("value") for v in ax.get("values", [])]
                for aid, ax in params.items()}
        schema[ck] = {"concept": meta.get(ck, {}).get("concept", ck),
                      "axes": axes, "item_keys": sorted(ikeys), "num_items": len(ikeys)}
    (out / f"{col}_concept_schema.json").write_text(json.dumps(schema, ensure_ascii=False), encoding="utf-8")

    # 3) synthetic query sets
    def load_mods(d):
        m = {}
        for line in (Path(d) / "BC3CAT_Syn_modifications.jsonl").read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            m[r["item_key"]] = [x for x in r["modifications"] if x.get("status") == "applied"]
        return m

    def query_records(d):
        items = pd.read_parquet(Path(d) / "BC3CAT_Syn_items.parquet")
        mods = load_mods(d)
        recs = []
        for r in items.itertuples(index=False):
            mtypes = list(r.modification_types) if not isinstance(r.modification_types, str) else json.loads(r.modification_types)
            m = meta.get(r.concept_key, {"ud": "", "concept": r.concept_key})
            recs.append({
                "id": _sid(r.item_key), "item_key": r.item_key,           # unique per query
                "parent_key": r.concept_key,                               # GOLD (concept level)
                "gold_item_key": r.original_key,                           # GOLD (item level)
                "ud": m["ud"], "concept": m["concept"],
                "parameters": _jsonable(r.params), "text": r.texto,        # the MODIFIED TEXTO
                "modification_types": mtypes, "modification_count": int(r.modification_count),
            })
        return recs

    stk = query_records(a.stacked)
    sgl = query_records(a.single)
    (out / f"{col}_stacked_texto.json").write_text(json.dumps(stk, ensure_ascii=False), encoding="utf-8")
    (out / f"{col}_single_texto.json").write_text(json.dumps(sgl, ensure_ascii=False), encoding="utf-8")

    # 4) README
    readme = f"""# BC3CAT-Syn — OE synthetic benchmark (handoff for bc3cat-retrieval)

Query = a MODIFIED `text` (TEXTO); target = the ORIGINAL TEXTO of the same concept.
All files are JSON lists of records with the project's schema:
`{{id, item_key, parent_key, ud, concept, parameters, text}}` (query files add
`gold_item_key`, `modification_types`, `modification_count`).

## Files
- `{col}_texto.json` — document corpus: original OE TEXTOs (retrieval **targets**). {len(texto_docs)} docs.
- `{col}_resumen.json` — same leaves, original RESUMEN (for the resumen→texto **baseline**). {len(resumen_docs)} docs.
- `{col}_stacked_texto.json` — **STACKED** queries: every applicable modification stacked. {len(stk)} queries.
- `{col}_single_texto.json` — **SINGLE** queries: one modification each (stratify by `modification_types[0]`). {len(sgl)} queries.
- `{col}_concept_schema.json` — per concept: name, axes, item_keys, num_items. {len(schema)} concepts.

## Gold / scoring
The harness reports parent-level Acc@1: a query is correct if the retrieved item's
`parent_key` == the query's `parent_key`. For item-level, use `gold_item_key`.
Every synthetic query modifies the TEXTO, so no query equals its target verbatim.

## Notes
- Corpus deduplicated: every target `(resumen, texto)` maps to one concept
  (cross-concept twins dropped, intra-concept duplicates collapsed).
- Deterministic; LLM used only to author the rewrite menus (frozen), corpora built
  by recombination. `id` = uuid5 of `item_key` (stable).
"""
    (out / "README.md").write_text(readme, encoding="utf-8")

    # 5) zip
    zip_path = out.parent / "BC3CAT_Syn_OE_handoff.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(out.glob("*")):
            z.write(f, arcname=f"BC3CAT_Syn_OE_handoff/{f.name}")

    print(f"docs texto/resumen: {len(texto_docs)} | stacked Q: {len(stk)} | single Q: {len(sgl)} | concepts: {len(schema)}")
    print(f"handoff dir: {out}")
    print(f"zip: {zip_path} ({zip_path.stat().st_size/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
