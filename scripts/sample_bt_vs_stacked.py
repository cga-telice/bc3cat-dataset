"""Muestra para comparar STACKED (v2) y BT sobre las mismas hojas (OE).

12 hojas de 12 conceptos distintos, repartidas por familia (los 5 primeros
caracteres del concepto) con semilla fija. Para cada hoja: TEXTO gold, consulta
STACKED v2 y consulta BT, con sus tipos de modificación.

  python scripts/sample_bt_vs_stacked.py
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
H = REPO / "data" / "synthetic" / "handoff_OE"
OUT = REPO / "docs" / "synthetic" / "bt" / "OE_bt_vs_stacked_sample.md"
SEED, N = 42, 12


def load(name):
    return json.loads((H / name).read_text(encoding="utf-8"))


def main() -> int:
    gold = {r["item_key"]: r for r in load("OE_texto.json")}
    st = {r["gold_item_key"]: r for r in load("OE_stacked_texto_v2.json")}
    bt = {r["gold_item_key"]: r for r in load("OE_bt_texto.json")}
    rng = random.Random(SEED)
    by_concept = defaultdict(list)
    for k in sorted(set(st) & set(bt)):
        by_concept[gold[k]["parent_key"]].append(k)
    by_family = defaultdict(list)
    for c in sorted(by_concept):
        by_family[c[:4]].append(c)
    for cs in by_family.values():
        rng.shuffle(cs)
    concepts = []
    while len(concepts) < N:          # una vuelta por familia hasta llenar
        for fam in sorted(by_family):
            if by_family[fam] and len(concepts) < N:
                concepts.append(by_family[fam].pop())
    rows = []
    for c in sorted(concepts):
        k = rng.choice(by_concept[c])
        rows.append((gold[k], st[k], bt[k]))

    out = ["# STACKED frente a BT: muestra sobre las mismas hojas (OE)", "",
           f"{N} hojas de {N} conceptos distintos, repartidas por familia (semilla {SEED}). "
           "Para cada hoja, el TEXTO gold y las dos consultas que lo tienen como gold: "
           "**STACKED v2** (reescrituras del menú apiladas: paráfrasis de plantilla, sinónimos, "
           "números en letra…) y **BT** (traducción de ida y vuelta por frases, variantes de valor "
           "y sinónimos del glosario). Generado con `scripts/sample_bt_vs_stacked.py`.", ""]
    for i, (g, s, b) in enumerate(rows, 1):
        bs = b["bt_sentences"]
        out += [f"## {i}. {g['parent_key'].rstrip('$')} — {g['concept']}", "",
                f"Hoja `{g['item_key']}`", "",
                f"**Gold:** {g['text']}", "",
                f"**STACKED v2** _({', '.join(s['texto_modification_types'])})_: {s['text']}", "",
                f"**BT** _({', '.join(b['modification_types'])}; {bs['translated']}/{bs['total']} frases "
                f"traducidas)_: {b['text']}", ""]
    OUT.write_text("\n".join(out), encoding="utf-8")
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
