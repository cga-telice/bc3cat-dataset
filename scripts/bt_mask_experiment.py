"""Miniexperimento de enmascarado para la BT (opción A, T4).

100 consultas de STACKED-P (semilla del piloto + 1) × {``sentinel``, ``xml``,
``none``}, pivote EN, condición ``stacked_bt``. Mide, por estrategia: pérdida
de máscara, rechazo en G1, aceptación en G2, no-ops y aceptación final. Se
elige la estrategia con más aceptación en G2 **sin** subir los rechazos en G1.

  .venv-bt/Scripts/python scripts/bt_mask_experiment.py --translate
  bash scripts/bt_run_extractors.sh scripts/bt_mask_experiment.py
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
from synthetic.characterization import ExtractionError, norm_text  # noqa: E402

_AFTER_G2 = {"G3", "G4", "G5", "G6", None}


def summarize(rows) -> dict:
    n = len(rows)
    gates = Counter(r["gate"] for r, _, _ in rows if not r["ok"])
    return {
        "n": n,
        "mask_lost": gates.get("BT", 0),
        "g1_rejected": gates.get("G1", 0),
        "passed_g2": sum(r["ok"] or r["gate"] in _AFTER_G2 for r, _, _ in rows),
        "no_op": sum(r.get("reason") == "no_op" for r, _, _ in rows),
        "accepted": sum(r["ok"] for r, _, _ in rows),
        "by_gate": dict(gates),
    }


def choose(summary: dict) -> str:
    """Más aceptación en G2 sin subir los rechazos en G1 respecto al mínimo."""
    g1_min = min(s["g1_rejected"] for s in summary.values())
    eligible = {k: s for k, s in summary.items() if s["g1_rejected"] <= g1_min}
    return max(sorted(eligible), key=lambda k: (eligible[k]["passed_g2"], eligible[k]["accepted"]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--translate", action="store_true")
    g.add_argument("--extract", metavar="MODELO")
    g.add_argument("--report", action="store_true")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    handoff, stacked, corpus, p_keys, digest = build_bt.load_all(cfg)
    keys = build_bt.select(cfg, stacked, p_keys, "experiment")
    jobs = [("stacked_bt", stacked[k]) for k in keys]
    strategies = cfg["bt"]["mask_strategies"]
    print(f"{len(keys)} consultas × {strategies}")

    engine = build_bt.make_engine(cfg, "record" if a.translate else "replay")
    results = {s: build_bt.translate(cfg, jobs, engine, s) for s in strategies}
    if a.translate:
        print({s: sum(not r.ok for r in rs) for s, rs in results.items()})
        return 0

    ctx = cal.load_context(cfg)
    if a.extract:
        ex = cal.make_extractor(cfg, a.extract, replay=False)
        for s, rs in results.items():
            for (_, src), r in zip(jobs, rs):
                if r.ok:
                    try:
                        ex.extract(r.text, ctx.concepts[src["parent_key"]])
                    except ExtractionError:
                        pass
        return 0

    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    forbidden = audit.forbidden_texts(handoff) | {norm_text(q["text"]) for q in stacked.values()}
    summary, examples = {}, {}
    for s, rs in results.items():
        rows = build_bt.verify(cfg, ctx, jobs, rs, sidecar, forbidden)
        summary[s] = summarize(rows)
        examples[s] = [(r["source_item_key"], r["gate"], r["reason"], r["bt_text"] or r["pivot_text"])
                       for r, _, _ in rows if not r["ok"]][:5]
    best = choose(summary)
    lines = ["# Miniexperimento de enmascarado para la BT (OE)", "",
             f"{len(keys)} consultas de STACKED-P, pivote EN, condición `stacked_bt`. "
             f"Criterio: más aceptación en G2 sin subir los rechazos en G1.", "",
             "| Estrategia | Máscara perdida | Rechazo G1 | Pasan G2 | No-ops | Aceptadas |",
             "|---|---:|---:|---:|---:|---:|"]
    for s in strategies:
        x = summary[s]
        lines.append(f"| `{s}` | {x['mask_lost']} | {x['g1_rejected']} | {x['passed_g2']} | "
                     f"{x['no_op']} | {x['accepted']} |")
    lines += ["", f"**Elegida: `{best}`.**", "", "## Ejemplos de rechazo", ""]
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
