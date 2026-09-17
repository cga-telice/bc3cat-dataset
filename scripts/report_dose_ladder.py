"""E3 — corpus report for the dose ladder (spec E3_DOSE_DESIGN.md §7).

Reads the dose release and writes docs/synthetic/OE_dose_report.md: cells per
count, per-type presence WITHIN each cell (their §3, achievable half), the
admitted-depth histogram, the chosen depth and any deficits.

Run (PYTHONPATH=src):
  python scripts/report_dose_ladder.py \
    --items data/synthetic/processed_OE_dose/BC3CAT_Syn_items.parquet \
    --depth 6 --pool-size 600 \
    --out docs/synthetic/OE_dose_report.md
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

from synthetic.corpus_sampler import NINE_TYPES  # noqa: E402


def _types(value):
    return list(value) if not isinstance(value, str) else json.loads(value)


def _placeable_lines(placeable_histogram: dict | None) -> list[str]:
    if placeable_histogram is None:
        return []
    placeable_histogram = {int(k): v for k, v in placeable_histogram.items()}
    short = sum(n for k, n in placeable_histogram.items() if k < 5)
    return [
        f"- histograma de modificaciones que caben en tramos distintos: "
        f"`{dict(sorted(placeable_histogram.items()))}` — "
        f"{short} hojas sondeadas admiten menos de 5 y no entran al fondo",
    ]


def render_report(items: pd.DataFrame, *, depth: int, histogram: dict,
                  pool_size: int, target: int = 600,
                  placeable_histogram: dict | None = None) -> str:
    counts = Counter(int(c) for c in items["modification_count"])
    lines = [
        "# E3 — informe del corpus de dosis (escalera anidada)",
        "",
        "Consulta = TEXTO modificado; objetivo = TEXTO original de la misma hoja.",
        "`modification_count` cuenta modificaciones APLICADAS y es exacto por",
        "construcción (D2): el sondeo verificó la disponibilidad antes de sortear.",
        "",
        f"- profundidad elegida **d = {depth}**",
        f"- fondo común: **{items['original_key'].nunique()} hojas**, las mismas "
        f"en las cinco celdas ({pool_size} seleccionadas, "
        f"{pool_size - items['original_key'].nunique()} de reserva sin usar)",
        f"- histograma de profundidad admitida: `{histogram}`",
        *_placeable_lines(placeable_histogram),
        f"- ítems: **{len(items)}**, hojas distintas: **{items['original_key'].nunique()}**",
        "",
        "## Celdas por dosis",
        "",
        f"El plan construye exactamente `per_count` escaleras completas o levanta",
        f"(`pool_too_small`/`DoseLadderError`); una celda por debajo de **{target}**",
        "aquí solo puede venir del emisor filtrando ítems ya planificados —",
        "duplicado exacto de `(resumen, texto)` en el corpus.",
        "",
        "| dosis | ítems | estado |",
        "|---|---|---|",
    ]
    short_cells: list[tuple[int, int]] = []
    for k in sorted(counts):
        n = counts[k]
        if n >= target:
            estado = "ok"
        else:
            deficit = target - n
            estado = f"SHORT by {deficit}"
            short_cells.append((k, deficit))
        lines.append(f"| dose_{k} | {n} | {estado} |")

    if short_cells:
        lines += [
            "",
            f"**Aviso: {len(short_cells)} "
            f"{'celda' if len(short_cells) == 1 else 'celdas'} por debajo del "
            f"objetivo de {target}.**"
            " El plan construye exactamente `per_count` escaleras o levanta, así que "
            "un déficit aquí viene del emisor: ítems descartados después de "
            "planificarse, por duplicado exacto de `(resumen, texto)` en el corpus. "
            "Revisa el informe QA de la pasada de dosis.",
        ]

    # The nine admitted types (E3_DOSE_DESIGN.md §3), always the columns — a
    # type that never fired anywhere in the corpus must still show as a zero,
    # not disappear from the table, so a hollowed-out thin type (small pantry,
    # e.g. unit_conversion/unit_expansion) cannot go unnoticed.
    all_types = [t.value for t in NINE_TYPES]
    lines += [
        "",
        "## Presencia por tipo dentro de cada celda",
        "",
        "Lo alcanzable de su §3: dentro de una celda ningún tipo debe estar",
        "sistemáticamente sobre-representado. La tasa de un tipo CRECE con la",
        "dosis por construcción (k tipos de un repertorio de d), y eso es una",
        "propiedad de la dosis, no un sesgo.",
        "",
        "Las columnas son los nueve tipos admitidos (fijos); un 0 significa que",
        "el tipo nunca disparó en esa celda, no que quedó sin tabular.",
        "",
        "| dosis | " + " | ".join(all_types) + " |",
        "|" + "---|" * (len(all_types) + 1),
    ]
    for k in sorted(counts):
        rows = items[items["modification_count"] == k]
        presence = Counter(t for v in rows["modification_types"] for t in _types(v))
        lines.append(
            f"| dose_{k} | " + " | ".join(str(presence.get(t, 0)) for t in all_types) + " |"
        )

    leaves_per_concept = items.groupby("concept_key")["original_key"].nunique()
    lines += [
        "",
        "## Cobertura por concepto",
        "",
        f"La escalera cubre **{len(leaves_per_concept)} conceptos**. Una partición",
        "dev/test por concepto solo puede repartir estos.",
        "",
        "| concepto | hojas con escalera |",
        "|---|---|",
    ]
    for concept, n in leaves_per_concept.sort_values(ascending=False).items():
        lines.append(f"| {concept} | {n} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--depth", type=int, required=True)
    ap.add_argument("--pool-size", type=int, required=True)
    ap.add_argument("--histogram", default="{}",
                    help="JSON dict from build_dose_ladder.py's output")
    ap.add_argument("--placeable-histogram", default=None,
                    help="JSON dict `placeable_histogram` from build_dose_ladder.py")
    ap.add_argument("--target", type=int, default=600,
                    help="minimum items expected per dose cell (§3); default 600")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    items = pd.read_parquet(a.items)
    text = render_report(
        items, depth=a.depth, histogram=json.loads(a.histogram),
        pool_size=a.pool_size, target=a.target,
        placeable_histogram=(json.loads(a.placeable_histogram)
                             if a.placeable_histogram else None),
    )
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(text, encoding="utf-8")
    print(f"informe escrito en {a.out} ({len(items)} ítems)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
