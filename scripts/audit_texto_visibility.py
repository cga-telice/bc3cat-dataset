"""Audit a delivered synthetic corpus: which recorded modifications the TEXTO
query really shows, and how far `modification_count` overstates it.

The retrieval task uses the MODIFIED TEXTO as query, so a modification that only
touches the RESUMEN — a RESUMEN-field template rewrite, or a text variable or
parameter the TEXTO template never renders — changes nothing the retriever sees.

Each record is judged twice, independently:
* structurally, with `dose_ladder.TextoSurface.shows_record` (template field,
  axis placeholder, text variable + condition against the stage JSON);
* by substring, for L1/L2 records: does the whitespace-normalised `new` text
  occur in the item's TEXTO? Template records carry `$X` placeholders, so they
  are judged structurally only.
Disagreements are reported, not resolved.

Read-only: writes a report and, optionally, a proposed corrected-count sidecar.
It never modifies the corpus.

Run (PYTHONPATH=src):
  python scripts/audit_texto_visibility.py \
    --corpus-dir data/synthetic/processed_OE_ablation_stacked \
    --stage-json data/synthetic/intermediate/OE_2026_stage.json \
    --label STACKED --report docs/synthetic/OE_stacked_texto_visibility_audit.md \
    --sidecar-out <path>.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from synthetic.dose_ladder import TextoSurface  # noqa: E402


def _ws(text) -> str:
    return " ".join(str(text).split())


def audit_item(modifications, texto, concept_key, leaf_key, surface) -> dict:
    """Visibility of one item's recorded modifications in its TEXTO."""
    body = _ws(texto)
    visible_types, hidden, disagreements = [], [], []
    for m in modifications:
        shown = surface.shows_record(m, concept_key, leaf_key)
        if m.get("layer") != "template":
            substring = bool(_ws(m.get("new", ""))) and _ws(m.get("new", "")) in body
            if substring != shown:
                disagreements.append((m["type"], shown, substring))
        if shown:
            visible_types.append(m["type"])
        else:
            hidden.append((m["type"], m.get("field") or m.get("layer")))
    return {
        "recorded_count": len(modifications),
        "visible_count": len(visible_types),
        "visible_types": visible_types,
        "hidden": hidden,
        "disagreements": disagreements,
    }


def corrected_rows(items: pd.DataFrame, audited: dict) -> list[dict]:
    """Proposed sidecar: the recorded count next to the TEXTO-visible one."""
    return [
        {
            "item_key": key,
            "recorded_count": audited[key]["recorded_count"],
            "texto_visible_count": audited[key]["visible_count"],
            "texto_visible_types": audited[key]["visible_types"],
        }
        for key in items["item_key"]
    ]


def render_report(label: str, audited: dict) -> str:
    n = len(audited)
    over = [a for a in audited.values() if a["visible_count"] < a["recorded_count"]]
    diff = Counter(a["recorded_count"] - a["visible_count"] for a in audited.values())
    transitions = Counter((a["recorded_count"], a["visible_count"]) for a in audited.values())
    hidden = Counter(h for a in audited.values() for h in a["hidden"])
    disagreements = Counter(d for a in audited.values() for d in a["disagreements"])
    zero = sum(1 for a in audited.values() if a["visible_count"] == 0)
    recorded_mean = sum(a["recorded_count"] for a in audited.values()) / max(n, 1)
    visible_mean = sum(a["visible_count"] for a in audited.values()) / max(n, 1)

    lines = [
        f"# {label} — auditoría de visibilidad en el TEXTO",
        "",
        "Consulta = TEXTO modificado. Una modificación cuenta como visible solo si",
        "toca algo que la plantilla del TEXTO renderiza (campo TEXTO; marcador del",
        "eje; variable del TEXTO cuya condición se cumple en la hoja).",
        "",
        f"- ítems: **{n}**",
        f"- ítems cuyo `modification_count` sobrecuenta: **{len(over)}** "
        f"({len(over) / max(n, 1):.1%})",
        f"- ítems sin ningún cambio visible en el TEXTO: **{zero}**",
        f"- `modification_count` medio: registrado **{recorded_mean:.2f}**, "
        f"visible **{visible_mean:.2f}**",
        f"- desacuerdos entre el juicio estructural y la comprobación por "
        f"subcadena: **{sum(disagreements.values())}**",
        "",
        "## Sobreconteo por ítem",
        "",
        "| registrado − visible | ítems |",
        "|---|---|",
        *(f"| {k} | {v} |" for k, v in sorted(diff.items())),
        "",
        "## Modificaciones no visibles, por tipo y capa",
        "",
        "| tipo | capa / campo | modificaciones |",
        "|---|---|---|",
        *(f"| {t} | {c} | {v} |" for (t, c), v in hidden.most_common()),
        "",
        "## Transiciones de conteo (registrado → visible)",
        "",
        "| registrado | visible | ítems |",
        "|---|---|---|",
        *(f"| {r} | {vis} | {v} |" for (r, vis), v in sorted(transitions.items())),
    ]
    if disagreements:
        lines += [
            "",
            "## Desacuerdos (tipo, estructural, subcadena)",
            "",
            "| tipo | estructural | subcadena | registros |",
            "|---|---|---|---|",
            *(f"| {t} | {s} | {sub} | {v} |" for (t, s, sub), v in disagreements.most_common()),
        ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus-dir", required=True)
    ap.add_argument("--stage-json", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--report", required=True)
    ap.add_argument("--sidecar-out", default=None)
    a = ap.parse_args()

    corpus = Path(a.corpus_dir)
    items = pd.read_parquet(corpus / "BC3CAT_Syn_items.parquet")
    surface = TextoSurface.from_stage(json.loads(Path(a.stage_json).read_text(encoding="utf-8")))
    rows = items.set_index("item_key")
    audited = {}
    for line in (corpus / "BC3CAT_Syn_modifications.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        row = rows.loc[rec["item_key"]]
        audited[rec["item_key"]] = audit_item(
            rec["modifications"], row.texto, row.concept_key, row.original_key, surface,
        )
    missing = set(items["item_key"]) - set(audited)
    if missing:
        raise SystemExit(f"sidecar_incomplete: {len(missing)} items have no modification record")

    report = render_report(a.label, audited)
    Path(a.report).parent.mkdir(parents=True, exist_ok=True)
    Path(a.report).write_text(report, encoding="utf-8")
    if a.sidecar_out:
        out = Path(a.sidecar_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="\n") as fh:
            for row in corrected_rows(items, audited):
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
