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
import datetime as _dt
import hashlib
import json
import subprocess
import uuid
import zipfile
from pathlib import Path

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]

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


def load_applicability(path):
    """`{leaf_item_key: {applicable_types, available_types, in_pool}}` from the sidecar.

    The sidecar is keyed by LEAF because applicability is a property of the leaf,
    not of the synthetic item: the same leaf's five rungs share it, so storing it
    once avoids repeating the two lists on every record.

    ``in_pool`` says whether the leaf is in the ladder's common pool. D6 delivers
    the isolated-effects set RESTRICTED to that pool — what was probed outside it
    stays in the release for the report's counts but is not delivered — so the
    isolated records are filtered on this flag.
    """
    table = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        table[row["leaf_item_key"]] = {
            "applicable_types": list(row.get("applicable_types") or []),
            "available_types": list(row.get("available_types") or []),
            "in_pool": bool(row.get("in_pool")),
        }
    return table


def apply_applicability(record, table):
    """Add the two D1 fields to one query record, joined on `gold_item_key`.

    Fails loud: a delivered record whose leaf is absent from the sidecar would
    silently ship an empty population descriptor, which is exactly the "compares
    different populations in silence" failure their §4 asks us to prevent.
    """
    leaf = record["gold_item_key"]
    if leaf not in table:
        raise KeyError(
            f"applicability_missing: leaf {leaf!r} (item {record['item_key']!r}) "
            f"has no sidecar entry"
        )
    entry = table[leaf]
    out = dict(record)
    out["applicable_types"] = entry["applicable_types"]
    out["available_types"] = entry["available_types"]
    return out


def in_pool(record, table):
    """Whether this record's leaf belongs to the ladder's common pool (D6).

    Used to restrict the isolated-effects delivery: the probe release covers
    every candidate leaf that survived, because the corpus report needs those
    counts, but only the pool's leaves are delivered — they are the ones the
    ladder also runs on, which is what makes the isolated effects and the dose
    effects comparable within the same leaf.
    """
    return table[record["gold_item_key"]]["in_pool"]


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_commit(allow_unknown=False):
    """The bc3cat-dataset commit that produced this delivery (their §6).

    Fails loud by default: a provenance stamp reading "unknown" looks like a
    complete delivery while silently dropping the field that makes it
    traceable. `allow_unknown` exists for the one legitimate case — packaging
    from an export with no `.git` — and has to be asked for explicitly, so it
    shows up in the invocation rather than in a default.
    """
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True,
            text=True, check=True,
        ).stdout.strip()
    except Exception as exc:
        if allow_unknown:
            return "unknown"
        raise SystemExit(
            f"provenance_commit_unavailable: could not read HEAD from {REPO} "
            f"({exc}). The delivery would be stamped 'unknown', which is not "
            f"traceable. Pass --allow-unknown-commit if you are packaging from "
            f"an export with no git metadata"
        )


def render_manifest(out_dir, filenames, provenance):
    """The §6 manifest: one SHA-256 per delivered file plus the provenance stamp."""
    lines = [
        "# BC3CAT-Syn — E3 dose delivery manifest",
        "",
        "| clave | valor |",
        "|---|---|",
    ]
    for key in sorted(provenance):
        lines.append(f"| `{key}` | `{provenance[key]}` |")
    lines += ["", "| fichero | bytes | sha256 |", "|---|---|---|"]
    for name in filenames:
        p = Path(out_dir) / name
        lines.append(f"| `{name}` | {p.stat().st_size} | `{_sha256(p)}` |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-json", required=True)
    ap.add_argument("--target-long", default="data/synthetic/processed_OE/OE_target_long.parquet")
    ap.add_argument("--target-short", default="data/synthetic/processed_OE/OE_target_short.parquet")
    ap.add_argument("--stacked", default="data/synthetic/processed_OE_ablation_stacked")
    ap.add_argument("--single", default="data/synthetic/processed_OE_ablation_single")
    ap.add_argument("--out-dir", default="data/synthetic/handoff_OE")
    ap.add_argument("--collection", default="OE")
    ap.add_argument("--dose", default=None, help="dose-ladder release dir")
    ap.add_argument("--probe", default=None, help="isolated-effects release dir")
    ap.add_argument("--applicability", default=None,
                    help="OE_leaf_applicability.jsonl (required with --dose/--probe)")
    ap.add_argument("--run-id", default=None)
    ap.add_argument(
        "--dose-config", default=None,
        help="the dose budgets YAML this run used. Required with --dose/--probe: "
             "provenance records the seed that actually produced the corpus, "
             "not a constant that happens to match today's config.",
    )
    ap.add_argument("--allow-unknown-commit", action="store_true",
                    help="stamp provenance commit as 'unknown' instead of failing "
                         "when HEAD cannot be read (packaging from an export)")
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

    # 3b) E3 dose ladder + isolated-effects releases (optional, additive)
    written = []
    if a.dose or a.probe:
        if not a.applicability:
            raise SystemExit("--applicability is required with --dose/--probe")
        if not a.dose_config:
            raise SystemExit("--dose-config is required with --dose/--probe")
        seed = yaml.safe_load(Path(a.dose_config).read_text(encoding="utf-8"))["seed"]
        table = load_applicability(a.applicability)
        for flag, name in ((a.dose, "dose"), (a.probe, "isolated")):
            if not flag:
                continue
            recs = [apply_applicability(r, table) for r in query_records(flag)]
            if name == "isolated":
                # D6: deliver only the pool's leaves. The probe release keeps
                # every survivor for the report's counts; delivering the rest
                # would break the "same leaves as the ladder" claim the isolated
                # set exists to support.
                before = len(recs)
                recs = [r for r in recs if in_pool(r, table)]
                print(f"isolated restricted to the pool: {len(recs)} of {before}")
            if name == "dose":
                # Every dose leaf is in the pool by construction (task 9 builds
                # the ladder over exactly select_pool's output), so this cannot
                # fail today. It is here because if it ever did — a sidecar
                # generated from a different run than the plan, or an
                # orchestrator edit letting a leaf slip out — the delivery would
                # silently pair dose items with isolated effects on leaves that
                # have none, which is the confound the whole set exists to
                # remove. Filtering would hide that; asserting surfaces it.
                outside = [r["gold_item_key"] for r in recs if not in_pool(r, table)]
                if outside:
                    raise SystemExit(
                        f"dose_leaf_outside_pool: {len(outside)} dose records "
                        f"have leaves the sidecar does not mark in_pool, e.g. "
                        f"{sorted(set(outside))[:3]}. The sidecar and the dose "
                        f"plan disagree about the pool — they must come from "
                        f"the same run"
                    )
            fn = f"{col}_{name}_texto.json"
            (out / fn).write_text(json.dumps(recs, ensure_ascii=False), encoding="utf-8")
            written.append(fn)
            print(f"{fn}: {len(recs)} queries")
        side_name = Path(a.applicability).name
        (out / side_name).write_text(
            Path(a.applicability).read_text(encoding="utf-8"), encoding="utf-8",
        )
        written.append(side_name)
        provenance = {
            "run_id": a.run_id or _dt.datetime.now(_dt.timezone.utc).strftime("e3-%Y%m%dT%H%M%SZ"),
            "seed": seed,
            "dose_config": str(a.dose_config),
            "script": "scripts/build_dose_ladder.py",
            "commit": git_commit(allow_unknown=a.allow_unknown_commit),
            "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        }
        (out / "provenance.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        (out / "MANIFEST.md").write_text(
            render_manifest(out, written, provenance), encoding="utf-8",
        )
        print(f"MANIFEST.md + provenance.json written to {out}")

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
