"""Auditoría de STACKED → STACKED-P (BT, opción A, T3).

Aplica el verificador de caracterización (G0–G4 y G6; sin ``source_text``,
así G1 compara con el TEXTO gold admitiendo las conversiones registradas en
el sidecar) a las 4 998 consultas de ``OE_stacked_texto.json``. Parte del
fichero entregado y de su sidecar, nunca de una regeneración.

Extractores por fases, como la calibración:

  PYTHONPATH=src python scripts/audit_stacked_characterization.py --extract phi4:latest
  PYTHONPATH=src python scripts/audit_stacked_characterization.py --extract qwen2.5:14b
  PYTHONPATH=src python scripts/audit_stacked_characterization.py --report

Salidas en ``data/synthetic/bt_OE/``:

* ``OE_stacked_characterization.jsonl`` — una fila por consulta, con el
  resultado por eje;
* ``OE_stacked_P_keys.json`` — claves aceptadas (STACKED-P);
* ``OE_stacked_P_exclusion.json`` — patrón de ``OE_P7_test_exclusion.json``
  más ``gate``/``axis``/``reason``/``cause`` por clave;

e informe en ``docs/synthetic/bt/OE_stacked_characterization_audit.md``.
STACKED-P no se entrega a retrieval desde aquí (CP3).
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
from synthetic.characterization import ExtractionError, norm_text  # noqa: E402

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


def exclusion_payload(rows: Sequence[Mapping]) -> dict:
    bad = sorted((r for r in rows if not r["ok"]), key=lambda r: r["item_key"])
    return {
        "reason": "BT-A T3: consultas STACKED que no preservan su caracterización "
                  "paramétrica (verificador G0–G4, G6); fuera de STACKED-P",
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


def write_report(path: Path, rows, stage, digest_in: str, out_shas: Mapping[str, str]) -> None:
    n = len(rows)
    ok = sum(r["ok"] for r in rows)
    bad = [r for r in rows if not r["ok"]]
    by_gate = Counter(r["gate"] for r in bad)
    by_reason = Counter(f"{r['gate']} · {r['reason'].split(':')[0]}" for r in bad)
    by_concept = Counter(r["parent_key"] for r in bad)
    by_axis = Counter(f"{r['parent_key']} {r['axis']} ({r['axis_label']})"
                      for r in bad if r["axis"])
    by_cause = Counter(t for r in bad for t in r["cause"])
    drift = [r for r in rows if r["known_drift"]]
    drift_out = sum(not r["ok"] for r in drift)
    total_by_concept = Counter(r["parent_key"] for r in rows)
    lines = [
        "# Auditoría de caracterización de STACKED → STACKED-P (OE)",
        "",
        f"Entrada: `OE_stacked_texto.json` (sha256 `{digest_in}`) y su sidecar. "
        "Verificador G0–G4 y G6 (sin `source_text`: G1 contra el TEXTO gold con las "
        "conversiones registradas). Extractores: phi4:latest y qwen2.5:14b, temperatura 0.",
        "",
        f"- Consultas: {n}.",
        f"- **STACKED-P (aceptadas): {ok} ({100 * ok / n:.1f} %).**",
        f"- Excluidas: {n - ok} ({100 * (n - ok) / n:.1f} %).",
        f"- Derivas conocidas («adosada» → «empotrada / a ras», «con topo» → «topografía»), "
        f"visibles en el TEXTO: {len(drift)}; excluidas {drift_out}. "
        f"La cota inferior del análisis era 323.",
        f"- Exclusiones fuera de esas derivas: {len(bad) - drift_out}.",
        "",
        "## Exclusiones por puerta",
        "",
        *_table(by_gate, ("Puerta", "Consultas")),
        "",
        "## Por puerta y motivo",
        "",
        *_table(by_reason, ("Puerta · motivo", "Consultas")),
        "",
        "## Por reescritura de origen (tipo del sidecar que toca el eje que falla)",
        "",
        *_table(by_cause, ("Tipo", "Consultas")),
        "",
        "## Por concepto",
        "",
        "| Concepto | Excluidas | Total | % |",
        "|---|---:|---:|---:|",
        *[f"| {k} | {v} | {total_by_concept[k]} | {100 * v / total_by_concept[k]:.1f} % |"
          for k, v in by_concept.most_common()],
        "",
        "## Por eje (20 más frecuentes)",
        "",
        *_table(by_axis, ("Concepto, eje", "Consultas"), top=20),
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
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--extract", metavar="MODELO")
    g.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    handoff = REPO / cfg["handoff_dir"]
    stacked_path = handoff / "OE_stacked_texto.json"
    digest_in = sha256_file(stacked_path)
    if digest_in != STACKED_SHA256:
        raise SystemExit(f"OE_stacked_texto.json cambió: {digest_in}")
    stacked = sorted(json.loads(stacked_path.read_text(encoding="utf-8")),
                     key=lambda q: q["item_key"])
    if a.limit:
        stacked = stacked[:a.limit]
    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    ctx = cal.load_context(cfg)

    if a.extract:
        ex = cal.make_extractor(cfg, a.extract, replay=False)
        for i, q in enumerate(stacked, 1):
            concept = ctx.concepts[q["parent_key"]]
            try:
                ex.extract(q["text"], concept)
            except ExtractionError:
                pass
            if i % 100 == 0:
                print(f"  {i}/{len(stacked)}", flush=True)
        return 0

    stage = cal._load(REPO / cfg["stage_json"])
    va = {k: var_axes(c) for k, c in stage.items() if k.endswith("$")}
    forbidden = forbidden_texts(handoff)
    extractors = [cal.make_extractor(cfg, m, replay=True) for m in cfg["extractors"]]
    rows, seen = [], {}
    for q in stacked:
        key, gold = q["item_key"], q["gold_item_key"]
        recs = sidecar[key]
        r = ctx.check(q["text"], gold, extractors=extractors, records=recs,
                      query_key=key, forbidden=forbidden)
        if r.ok:
            nt = norm_text(q["text"])
            if nt in seen:
                r.ok, r.gate, r.reason = False, "G6", f"duplicate_within_set:{seen[nt]}"
            else:
                seen[nt] = key
        leaf = ctx.leaves.get(gold)
        visible = ([x for x in recs if ctx.surface.shows_record(x, leaf.concept, gold)]
                   if leaf else [])
        concept = ctx.concepts.get(q["parent_key"])
        rows.append({
            "item_key": key, "gold_item_key": gold, "parent_key": q["parent_key"],
            "ok": r.ok, "gate": r.gate, "axis": r.axis, "reason": r.reason,
            "axis_label": concept.axis(r.axis).label if (r.axis and concept) else None,
            "cause": [] if r.ok else cause(visible, r.axis, va.get(q["parent_key"], {})),
            "known_drift": any(cal.is_drift(x) for x in visible),
            "axes": r.axes, "not_rendered": r.not_rendered,
            "extractions": r.extractions,
            "decoder": {k: list(v) for k, v in r.decoder.items()},
            "drift_score": r.drift.get("score"),
            "texto_modification_types": q.get("texto_modification_types"),
        })

    out = REPO / "data" / "synthetic" / "bt_OE"
    files = {
        "OE_stacked_characterization.jsonl":
            "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows),
        "OE_stacked_P_keys.json": json.dumps({
            "file": "OE_stacked_texto.json", "source_sha256": digest_in,
            "protocol_version": "1", "extractors": cfg["extractors"],
            "n": sum(r["ok"] for r in rows),
            "item_keys": [r["item_key"] for r in rows if r["ok"]],
        }, ensure_ascii=False, indent=1) + "\n",
        "OE_stacked_P_exclusion.json":
            json.dumps(exclusion_payload(rows), ensure_ascii=False, indent=1) + "\n",
    }
    shas = {}
    for name, text in files.items():
        write_atomic(out / name, text)
        shas[name] = sha256_file(out / name)
    write_report(REPO / "docs" / "synthetic" / "bt" / "OE_stacked_characterization_audit.md",
                 rows, stage, digest_in, shas)
    if sha256_file(stacked_path) != STACKED_SHA256:
        raise SystemExit("OE_stacked_texto.json cambió durante la auditoría")
    print(f"STACKED-P: {sum(r['ok'] for r in rows)}/{len(rows)}")
    print(Counter(r["gate"] for r in rows if not r["ok"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
