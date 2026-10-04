"""Auditoría de STACKED → STACKED-P (BT, opción A, T3; rediseño tras CP2).

Determinista, sin LLM (decisión de César en CP2). Parte del fichero STACKED
entregado (sha256 ``c34a…``) y de su sidecar, nunca de una regeneración. Cada
consulta pasa, en orden (la primera que falla la excluye):

* **ALIGN** — la plantilla TEXTO parafraseada casa con el texto y localiza
  cada valor de eje y fragmento L2 (:mod:`bt_alignment`); sin eso no se
  pueden enmascarar en la BT;
* **DRIFT** — lista de exclusión de derivas conocidas: reescrituras visibles
  que quitan «adosada» o «con topo» y meten «empotrada / a ras…» o
  «topografía / perfilado» (``calibrate_characterization.is_drift``). La
  lista concreta se escribe en ``OE_known_drift_rewrites.json``;
* **G0, G1, G3, G6** — verificador en modo estructural (sin extractores): G1
  contra el TEXTO gold con las conversiones registradas en el sidecar; G6
  frente a SINGLE, SINGLE-L2, dose e isolated, y duplicados dentro de STACKED.

  PYTHONPATH=src python scripts/audit_stacked_characterization.py

Salidas en ``data/synthetic/bt_OE/``: ``OE_stacked_characterization.jsonl``,
``OE_stacked_P_keys.json``, ``OE_stacked_P_exclusion.json`` (patrón de
``OE_P7_test_exclusion.json`` más ``gate``/``axis``/``reason``/``cause``) y
``OE_known_drift_rewrites.json``; informe en
``docs/synthetic/bt/OE_stacked_characterization_audit.md``. STACKED-P no se
entrega a retrieval desde aquí (CP3).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import yaml  # noqa: E402

import calibrate_characterization as cal  # noqa: E402
from synthetic.bt_alignment import AlignmentError, stacked_slots  # noqa: E402
from synthetic.characterization import norm_text  # noqa: E402

STACKED_SHA256 = "c34a222ae2af05a0b5335b774cb7fb45f14064cc17234d9d885e809fb29b6f45"
_CALL_RE = re.compile(r"\$([A-Za-z]\w*)(?:\(([^)]*)\))?")
_AXIS_REF_RE = re.compile(r"%([A-Z])")
_OTHER_SETS = ("OE_single_texto.json", "OE_single_l2_texto.json",
               "OE_dose_texto.json", "OE_isolated_texto.json")


# ---------------------------------------------------------------------------
# Piezas puras
# ---------------------------------------------------------------------------

def var_axes(concept: Mapping) -> dict[str, frozenset]:
    """Ejes que indexa cada variable de texto: condiciones ``%X`` de su
    fórmula más argumentos ``%X`` de sus llamadas en la plantilla TEXTO."""
    tv = concept.get("text_variables") or {}
    axes = set(concept.get("parameters") or {})
    out: dict[str, set] = {}
    for name, formula in tv.items():
        f = formula if isinstance(formula, str) else " ".join(map(str, formula))
        out[name] = set(_AXIS_REF_RE.findall(f)) & axes
    texto = concept.get("texto") or ""
    texto = texto if isinstance(texto, str) else " ".join(texto)
    for name, args in _CALL_RE.findall(texto):
        if name in out and args:
            out[name] |= set(_AXIS_REF_RE.findall(args)) & axes
    return {k: frozenset(v) for k, v in out.items()}


def cause(visible: Sequence[Mapping], axis: Optional[str],
          var_axes_: Mapping[str, frozenset]) -> list[str]:
    """Tipos de los registros visibles que tocan ``axis`` (L1 del eje o L2
    de una variable que lo indexa). Si ninguno, la plantilla. Sin eje,
    todos los tipos visibles."""
    if axis is None:
        return sorted({r["type"] for r in visible})
    hits = {r["type"] for r in visible
            if (r.get("layer") == "param_value" and r.get("param") == axis)
            or (r.get("layer") == "text_variable"
                and axis in var_axes_.get(r.get("var"), frozenset()))}
    if not hits:
        hits = {r["type"] for r in visible if r.get("layer") == "template"}
    return sorted(hits)


def drift_list(visible_by_query: Mapping[str, Sequence[Mapping]]) -> list[dict]:
    """Reescrituras de deriva conocidas, agrupadas, con las consultas que las
    llevan. Es la lista de exclusión que revisa César."""
    groups: dict[tuple, list[str]] = {}
    for key in sorted(visible_by_query):
        for r in visible_by_query[key]:
            if cal.is_drift(r):
                k = (r["type"], r["layer"], r["original"].strip(), r["new"].strip())
                groups.setdefault(k, []).append(key)
    return [{"type": t, "layer": l, "original": o, "new": n, "queries": sorted(set(qs))}
            for (t, l, o, n), qs in sorted(groups.items())]


def exclusion_payload(rows: Sequence[Mapping]) -> dict:
    bad = sorted((r for r in rows if not r["ok"]), key=lambda r: r["item_key"])
    return {
        "reason": "BT-A T3: consultas STACKED fuera de STACKED-P (alineación, derivas "
                  "conocidas, G0/G1/G3/G6)",
        "file": "OE_stacked_texto.json",
        "split": "all",
        "item_keys": [r["item_key"] for r in bad],
        "details": {r["item_key"]: {"gate": r["gate"], "axis": r["axis"],
                                    "reason": r["reason"], "cause": r["cause"]}
                    for r in bad},
    }


# ---------------------------------------------------------------------------
# E/S
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def forbidden_texts(handoff: Path) -> frozenset:
    out = set()
    for name in _OTHER_SETS:
        for r in json.loads((handoff / name).read_text(encoding="utf-8")):
            out.add(norm_text(r["text"]))
    return frozenset(out)


def _table(counter: Counter, head: tuple[str, str], top: Optional[int] = None) -> list[str]:
    lines = [f"| {head[0]} | {head[1]} |", "|---|---:|"]
    for k, v in counter.most_common(top):
        lines.append(f"| {k} | {v} |")
    return lines


def write_report(path: Path, rows, drifts, digest_in: str, out_shas: Mapping[str, str]) -> None:
    n = len(rows)
    ok = sum(r["ok"] for r in rows)
    bad = [r for r in rows if not r["ok"]]
    by_gate = Counter(r["gate"] for r in bad)
    by_reason = Counter(f"{r['gate']} · {(r['reason'] or '').split(':')[0]}" for r in bad)
    by_concept = Counter(r["parent_key"] for r in bad)
    by_cause = Counter(t for r in bad for t in r["cause"])
    total_by_concept = Counter(r["parent_key"] for r in rows)
    lines = [
        "# Auditoría de STACKED → STACKED-P (OE)",
        "",
        f"Entrada: `OE_stacked_texto.json` (sha256 `{digest_in}`) y su sidecar. Determinista, "
        "sin LLM (CP2). Filtros en orden: alineación de la plantilla, lista de derivas "
        "conocidas, verificador estructural (G0, G1 contra el gold con las conversiones "
        "registradas, G3, G6) y duplicados dentro de STACKED.",
        "",
        f"- Consultas: {n}.",
        f"- **STACKED-P (aceptadas): {ok} ({100 * ok / n:.1f} %).**",
        f"- Excluidas: {n - ok} ({100 * (n - ok) / n:.1f} %).",
        f"- Derivas conocidas: {len(drifts)} reescrituras distintas en "
        f"{len({q for d in drifts for q in d['queries']})} consultas. La cota inferior del "
        "análisis previo era 323.",
        "",
        "## Exclusiones por filtro",
        "",
        *_table(by_gate, ("Filtro", "Consultas")),
        "",
        "## Por filtro y motivo",
        "",
        *_table(by_reason, ("Filtro · motivo", "Consultas")),
        "",
        "## Por reescritura de origen",
        "",
        *_table(by_cause, ("Tipo", "Consultas")),
        "",
        "## Lista de derivas conocidas (exclusión)",
        "",
        "| Tipo | Original | Nuevo | Consultas |",
        "|---|---|---|---:|",
        *[f"| {d['type']} | {d['original']} | {d['new']} | {len(d['queries'])} |" for d in drifts],
        "",
        "## Por concepto",
        "",
        "| Concepto | Excluidas | Total | % |",
        "|---|---:|---:|---:|",
        *[f"| {k} | {v} | {total_by_concept[k]} | {100 * v / total_by_concept[k]:.1f} % |"
          for k, v in by_concept.most_common()],
        "",
        "## Ficheros",
        "",
        "| Fichero | sha256 |",
        "|---|---|",
        *[f"| `{k}` | `{v}` |" for k, v in out_shas.items()],
    ]
    write_atomic(path, "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    handoff = REPO / cfg["handoff_dir"]
    stacked_path = handoff / "OE_stacked_texto.json"
    digest_in = sha256_file(stacked_path)
    if digest_in != STACKED_SHA256:
        raise SystemExit(f"OE_stacked_texto.json cambió: {digest_in}")
    stacked = sorted(json.loads(stacked_path.read_text(encoding="utf-8")),
                     key=lambda q: q["item_key"])
    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    ctx = cal.load_context(cfg)
    stage = cal._load(REPO / cfg["stage_json"])
    va = {k: var_axes(c) for k, c in stage.items() if k.endswith("$")}
    forbidden = forbidden_texts(handoff)

    visible_by_query = {}
    for q in stacked:
        leaf = ctx.leaves.get(q["gold_item_key"])
        visible_by_query[q["item_key"]] = (
            [x for x in sidecar[q["item_key"]]
             if ctx.surface.shows_record(x, leaf.concept, leaf.key)] if leaf else [])
    drifts = drift_list(visible_by_query)

    rows, seen = [], {}
    for q in stacked:
        key, gold = q["item_key"], q["gold_item_key"]
        recs, visible = sidecar[key], visible_by_query[key]
        leaf = ctx.leaves.get(gold)
        row = {"item_key": key, "gold_item_key": gold, "parent_key": q["parent_key"],
               "texto_modification_types": q.get("texto_modification_types"),
               "ok": False, "gate": None, "axis": None, "reason": None, "cause": [],
               "known_drift": any(cal.is_drift(x) for x in visible)}
        try:
            if leaf is None:
                raise AlignmentError("unknown_gold")
            stacked_slots(stage[q["parent_key"]], gold, leaf.text, q["text"], recs)
        except AlignmentError as err:
            row.update(gate="ALIGN", reason=f"alignment_failed:{err}",
                       cause=cause(visible, None, va.get(q["parent_key"], {})))
            rows.append(row)
            continue
        if row["known_drift"]:
            row.update(gate="DRIFT", reason="known_drift",
                       cause=sorted({x["type"] for x in visible if cal.is_drift(x)}))
            rows.append(row)
            continue
        r = ctx.check(q["text"], gold, extractors=(), records=recs,
                      query_key=key, forbidden=forbidden)
        if r.ok:
            nt = norm_text(q["text"])
            if nt in seen:
                r.ok, r.gate, r.reason = False, "G6", f"duplicate_within_set:{seen[nt]}"
            else:
                seen[nt] = key
        row.update(ok=r.ok, gate=r.gate, axis=r.axis, reason=r.reason,
                   cause=[] if r.ok else cause(visible, r.axis, va.get(q["parent_key"], {})),
                   drift_score=r.drift.get("score"))
        rows.append(row)

    out = REPO / cfg["bt"]["out_dir"]
    files = {
        "OE_stacked_characterization.jsonl":
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
        "OE_stacked_P_keys.json": json.dumps({
            "file": "OE_stacked_texto.json", "source_sha256": digest_in,
            "protocol": "BT-A rediseño CP2: alineación + derivas conocidas + G0/G1/G3/G6",
            "n": sum(r["ok"] for r in rows),
            "item_keys": [r["item_key"] for r in rows if r["ok"]],
        }, ensure_ascii=False, indent=1) + "\n",
        "OE_stacked_P_exclusion.json":
            json.dumps(exclusion_payload(rows), ensure_ascii=False, indent=1) + "\n",
        "OE_known_drift_rewrites.json":
            json.dumps(drifts, ensure_ascii=False, indent=1) + "\n",
    }
    shas = {}
    for name, text in files.items():
        write_atomic(out / name, text)
        shas[name] = sha256_file(out / name)
    write_report(REPO / "docs" / "synthetic" / "bt" / "OE_stacked_characterization_audit.md",
                 rows, drifts, digest_in, shas)
    if sha256_file(stacked_path) != STACKED_SHA256:
        raise SystemExit("OE_stacked_texto.json cambió durante la auditoría")
    print(f"STACKED-P: {sum(r['ok'] for r in rows)}/{len(rows)}")
    print(Counter(r["gate"] for r in rows if not r["ok"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
