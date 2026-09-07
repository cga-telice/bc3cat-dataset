"""Guard #1 runner — audit a synthetic corpus + pantry for cross-concept collisions.

Corpus-level (always): does any produced item's resumen/texto equal a *different*
concept's base leaf, and was that field changed by us (``introduced``) or is it a
baseline catalogue duplicate (``inherited``)?

Template-level (``--template-level``, needs the BC3 catalogue at ``--source``):
render every ``template_paraphrase`` rewrite over *all* parameter combinations of
each concept it applies to — the exhaustive guarantee for the rewrite itself.

Acceptance = zero ``introduced`` collisions at both levels. Exit code is the
introduced count (0 = clean).

Run (PYTHONPATH=src):
  python scripts/cross_concept_audit.py \
    --items data/synthetic/processed_OE/BC3CAT_Syn_items.parquet \
    --long  data/synthetic/inventory/OE_long.parquet \
    --short data/synthetic/inventory/OE_short.parquet \
    --menus-dir data/synthetic/menus_OE --source data/raw/BPA_2026.bc3 \
    --template-level --report docs/synthetic/OE_cross_concept_audit.md
"""
from __future__ import annotations

import argparse
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import pandas as pd  # noqa: E402

from synthetic import cross_concept_guard as g  # noqa: E402


def _fmt(cols, level):
    intro = g.introduced(cols)
    inh = [c for c in cols if c.kind == "inherited"]
    lines = [f"## {level}", "",
             f"- introduced collisions (guard failures): **{len(intro)}**",
             f"- inherited collisions (baseline catalogue duplicates): {len(inh)}"]
    if inh:
        pair = collections.Counter(
            tuple(sorted((c.concept, *c.other_concepts))) for c in inh)
        top = ", ".join(f"{'≡'.join(p)} ({n})" for p, n in pair.most_common(6))
        lines.append(f"- inherited concept pairs (top): {top}")
    for c in intro[:50]:
        lines.append(f"  - INTRODUCED {c.item_key} [{c.concept}] {c.field} "
                     f"→ {c.other_concepts}: {c.text[:80]!r}")
    lines.append("")
    return "\n".join(lines), len(intro)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True)
    ap.add_argument("--long", required=True)
    ap.add_argument("--short", required=True)
    ap.add_argument("--menus-dir", default=None)
    ap.add_argument("--source", default=None)
    ap.add_argument("--template-level", action="store_true")
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    index = g.build_base_index(pd.read_parquet(a.long), pd.read_parquet(a.short))
    items = pd.read_parquet(a.items)
    corpus_cols = g.audit_corpus(items, index)
    body, n_intro = _fmt(corpus_cols, f"Corpus-level ({len(items)} items)")

    parts = ["# Cross-concept collision audit (Guard #1)", "",
             "Zero *introduced* collisions = pass. *Inherited* collisions are "
             "leaves the source catalogue already shares across concepts "
             "(a ground-truth property, not a synthesis defect).", "", body]
    total_intro = n_intro

    if a.template_level:
        if not a.menus_dir or not a.source or not Path(a.source).exists():
            parts.append("## Template-level\n\n- SKIPPED (need --menus-dir and an "
                         "existing --source catalogue)\n")
        else:
            from synthetic.pantry import load_pantry
            pantry = load_pantry(Path(a.menus_dir))
            tcols = g.audit_pantry_templates(pantry, index, a.source)
            tbody, tintro = _fmt(tcols, "Template-level (exhaustive over all leaves)")
            parts.append(tbody)
            total_intro += tintro

    report = "\n".join(parts)
    if a.report:
        Path(a.report).parent.mkdir(parents=True, exist_ok=True)
        Path(a.report).write_text(report, encoding="utf-8")
    print(report)
    print(f"\nRESULT: {'PASS' if total_intro == 0 else 'FAIL'} "
          f"({total_intro} introduced collisions)")
    return total_intro


if __name__ == "__main__":
    raise SystemExit(main())
