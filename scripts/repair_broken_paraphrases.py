"""v2 de STACKED, SINGLE, dose e isolated con las paráfrasis rotas corregidas.

César (2026-10-16): se corrigen las paráfrasis de plantilla con un hueco en un
papel que no es el suyo (``reasignacion``) o con un valor tratado como
referencia (``referencia``); las demás categorías de la auditoría se dejan.

Por cada consulta cuya paráfrasis TEXTO está en
``data/synthetic/broken_OE/OE_template_paraphrase_repairs.json``: alineación con
la paráfrasis rota (mismos anclajes que la auditoría de STACKED) y nuevo
renderizado con la corregida. El resto de consultas queda byte a byte igual.

Salidas (solo en ``data/synthetic/broken_OE/``; ``handoff_OE`` no se toca):
* ``OE_{stacked,single,dose,isolated}_texto_v2.json``;
* ``OE_paraphrase_repair_changes.jsonl`` — una línea por consulta cambiada;
* ``OE_paraphrase_repair_report.md``.

  PYTHONPATH=src python scripts/repair_broken_paraphrases.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from synthetic.bt_alignment import stacked_slots  # noqa: E402
from synthetic.paraphrase_repair import check_placeholders, render, slot_values  # noqa: E402

HANDOFF = REPO / "data" / "synthetic" / "handoff_OE"
OUT = REPO / "data" / "synthetic" / "broken_OE"
STAGE = REPO / "data" / "synthetic" / "intermediate" / "OE_2026_stage.json"
SETS = {"stacked": "OE_stacked_texto.json", "single": "OE_single_texto.json",
        "dose": "OE_dose_texto.json", "isolated": "OE_isolated_texto.json"}
SIDECARS = sorted((REPO / "data" / "synthetic").glob("processed_OE*/BC3CAT_Syn_modifications.jsonl"))


def uid(original: str, new: str) -> str:
    return hashlib.sha1("\x1f".join((original, new)).encode()).hexdigest()[:12]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    repairs = load_json(OUT / "OE_template_paraphrase_repairs.json")
    for r in repairs.values():
        check_placeholders(r["original"], r["corrected"])
    stage = load_json(STAGE)
    gold = {r["item_key"]: r["text"] for r in load_json(HANDOFF / "OE_texto.json")}
    gold_texts = frozenset(gold.values())
    side = {}
    for f in SIDECARS:
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            side.setdefault(r["item_key"], r["modifications"])

    before = {name: sha256(HANDOFF / fn) for name, fn in SETS.items()}
    changes, stats = [], {}
    for name, fn in SETS.items():
        queries = load_json(HANDOFF / fn)
        texts = Counter(q["text"] for q in queries)
        n = 0
        for q in queries:
            recs = side[q["item_key"]]
            tp = [x for x in recs if x["type"] == "template_paraphrase" and x["field"] == "TEXTO"]
            k = uid(tp[-1]["original"], tp[-1]["new"]) if tp else None
            if k not in repairs:
                continue
            slots = stacked_slots(stage[q["parent_key"]], q["gold_item_key"],
                                  gold[q["gold_item_key"]], q["text"], recs)
            new = render(repairs[k]["corrected"], slot_values(slots))
            if "$" in new or "[[" in new:
                raise SystemExit(f"{q['item_key']}: residuo de plantilla")
            if new in gold_texts:
                raise SystemExit(f"{q['item_key']}: igual a un TEXTO gold")
            texts[q["text"]] -= 1
            texts[new] += 1
            changes.append({"set": name, "item_key": q["item_key"], "paraphrase_id": k,
                            "old": q["text"], "new": new})
            q["text"] = new
            n += 1
        dups = sum(c - 1 for c in texts.values() if c > 1)
        out = OUT / fn.replace(".json", "_v2.json")
        # mismo formato que el entregado (compacto, sin salto final): las
        # consultas no cambiadas quedan byte a byte iguales
        out.write_text(json.dumps(queries, ensure_ascii=False), encoding="utf-8")
        stats[name] = {"queries": len(queries), "changed": n, "duplicate_texts": dups, "sha256": sha256(out)}

    if before != {name: sha256(HANDOFF / fn) for name, fn in SETS.items()}:
        raise SystemExit("handoff_OE cambió")
    with (OUT / "OE_paraphrase_repair_changes.jsonl").open("w", encoding="utf-8") as f:
        for c in changes:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    lines = ["# Reparación de paráfrasis rotas (OE, v2)", "",
             f"{len(repairs)} paráfrasis corregidas (reasignación de hueco y valor como referencia).", "",
             "| Conjunto | Consultas | Cambiadas | Textos duplicados | sha256 v2 |", "|---|---:|---:|---:|---|"]
    for name, s in stats.items():
        lines.append(f"| {name} | {s['queries']} | {s['changed']} | {s['duplicate_texts']} | `{s['sha256'][:16]}…` |")
    (OUT / "OE_paraphrase_repair_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
