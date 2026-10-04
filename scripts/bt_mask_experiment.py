"""Miniexperimento de enmascarado para la BT (opción A, T4; rediseño tras CP2).

100 consultas de STACKED-P (semilla del piloto + 1), pivote EN, condición
``stacked_bt``, con valores de eje y fragmentos L2 enmascarados, × las
estrategias de marcador de ``bt.mask_strategies`` (``sentinel`` ``[[V1]]``,
``xml`` ``<x1/>``). ``none`` ya no aplica: dejaría los valores sin proteger.
Mide, por estrategia: máscara perdida, valores cambiados de orden, rechazos de
la verificación estructural, no-ops y aceptación final. Se elige la de más
aceptación; a igualdad, la que pierde menos máscaras.

  .venv-bt/Scripts/python scripts/bt_mask_experiment.py --translate
  .venv-bt/Scripts/python scripts/bt_mask_experiment.py --report
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import yaml  # noqa: E402

import audit_stacked_characterization as audit  # noqa: E402
import build_bt  # noqa: E402
import calibrate_characterization as cal  # noqa: E402
from synthetic.characterization import norm_text  # noqa: E402


def summarize(rows) -> dict:
    gates = Counter(r["gate"] for r, _, _ in rows if not r["ok"])
    reasons = Counter((r.get("reason") or "").split(":")[0] for r, _, _ in rows if not r["ok"])
    return {
        "n": len(rows),
        "mask_lost": reasons.get("mask_lost", 0),
        "value_order_changed": reasons.get("value_order_changed", 0),
        "no_op": reasons.get("no_op", 0),
        "accepted": sum(r["ok"] for r, _, _ in rows),
        "by_gate": dict(gates),
    }


def choose(summary: dict) -> str:
    """Más aceptación; a igualdad, menos máscaras perdidas; luego por nombre."""
    return min(sorted(summary), key=lambda k: (-summary[k]["accepted"], summary[k]["mask_lost"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--translate", action="store_true")
    g.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    handoff, stacked, corpus, p_keys, digest = build_bt.load_all(cfg)
    keys = build_bt.select(cfg, stacked, p_keys, "experiment")
    jobs = [("stacked_bt", stacked[k]) for k in keys]
    strategies = cfg["bt"]["mask_strategies"]
    stage = cal._load(REPO / cfg["stage_json"])
    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    spans = build_bt.value_spans(jobs, stage, corpus, sidecar)
    print(f"{len(keys)} consultas × {strategies}")

    engine = build_bt.make_engine(cfg, "record" if a.translate else "replay")
    results = {s: build_bt.translate(cfg, jobs, engine, s, spans) for s in strategies}
    if a.translate:
        print({s: Counter(r.reason for r in rs if not r.ok) for s, rs in results.items()})
        return 0

    ctx = cal.load_context(cfg)
    forbidden = audit.forbidden_texts(handoff) | {norm_text(q["text"]) for q in stacked.values()}
    summary, examples = {}, {}
    for s, rs in results.items():
        rows = build_bt.verify(cfg, ctx, jobs, rs, sidecar, forbidden)
        summary[s] = summarize(rows)
        examples[s] = [(r["source_item_key"], r["gate"], r["reason"], b.back_masked)
                       for (r, _, b) in rows if not r["ok"]][:5]
    best = choose(summary)
    lines = ["# Miniexperimento de enmascarado para la BT (OE)", "",
             f"{len(keys)} consultas de STACKED-P, pivote EN, condición `stacked_bt`, valores de "
             "eje y fragmentos L2 enmascarados. Criterio: más aceptación; a igualdad, menos "
             "máscaras perdidas.", "",
             "| Estrategia | Máscara perdida | Valores de orden cambiado | No-ops | Aceptadas | Rechazos por puerta |",
             "|---|---:|---:|---:|---:|---|"]
    for s in strategies:
        x = summary[s]
        lines.append(f"| `{s}` | {x['mask_lost']} | {x['value_order_changed']} | {x['no_op']} | "
                     f"{x['accepted']} | {x['by_gate']} |")
    lines += ["", f"**Elegida: `{best}`.**", "", "## Ejemplos de rechazo (texto enmascarado tras la BT)", ""]
    for s in strategies:
        lines.append(f"- `{s}`:")
        for k, gate, reason, text in examples[s]:
            lines.append(f"  - {gate} `{k}` {reason}: {' '.join((text or '').split())[:300]}")
    audit.write_atomic(REPO / "docs" / "synthetic" / "bt" / "OE_bt_mask_experiment.md",
                       "\n".join(lines) + "\n")
    audit.write_atomic(REPO / cfg["bt"]["out_dir"] / "OE_bt_mask_experiment.json",
                       json.dumps({"keys": keys, "summary": summary, "chosen": best},
                                  ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(summary, indent=1), "\nelegida:", best)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
