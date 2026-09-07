"""Guard #2 — meaning-drift review aid for approved template_paraphrase rewrites.

A template_paraphrase should REWORD a concept's skeleton, not change what work it
describes. This is inherently semantic, so this guard does not auto-reject — it
RANKS the approved rewrites by how much source content the paraphrase dropped, so
the worst offenders (an action/product word replaced by an unrelated one, e.g.
"destapado" → "extracción") surface first for human review. Pure synonym swaps
(one content word for one) and additive elaborations are ranked low.

Reads the pantry (approved rewrites) via :func:`synthetic.pantry.load_pantry` — it
runs on the ALREADY-paraphrased templates, no rendering or regeneration. Writes an
HTML review report and a JSONL of the flagged (lossy) rewrites.

Run (PYTHONPATH=src):
  python scripts/meaning_drift_flag.py --menus-dir data/synthetic/menus_OE \
    --html <out>.html --jsonl <out>.jsonl
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from synthetic.pantry import load_pantry  # noqa: E402
from synthetic.taxonomy import ModificationType  # noqa: E402

# BC3 placeholders to strip before comparing content words.
_PLACEHOLDER = re.compile(r"\$[A-Za-z]+\([^)]*\)|\$[A-Za-z]+|%[A-Za-z]+")
_STOP = {
    "de", "del", "al", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "en", "para", "con", "y", "o", "u", "e", "a", "por", "su", "sus", "entre",
    "sobre", "tipo", "the", "of", "se", "que", "como", "mm", "cm", "m",
}


def _norm(word: str) -> str:
    w = unicodedata.normalize("NFKD", word.lower())
    w = "".join(c for c in w if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", w)


def _content(text: str) -> list[str]:
    bare = _PLACEHOLDER.sub(" ", text)
    toks = [_norm(t) for t in re.split(r"\s+", bare)]
    return [t for t in toks if t and t not in _STOP and not t.isdigit()]


def analyze(original: str, new: str) -> dict:
    o, n = _content(original), _content(new)
    os_, ns_ = set(o), set(n)
    dropped = sorted(os_ - ns_)
    added = sorted(ns_ - os_)
    net_loss = len(dropped) - len(added)          # >0 = content removed, not replaced
    head_changed = bool(o) and bool(n) and o[0] != n[0]
    return {"dropped": dropped, "added": added,
            "score": round(len(dropped) / max(1, len(os_)), 3),
            "lossy": bool(dropped), "net_loss": net_loss,
            "head_changed": head_changed}


def _mark(text: str, words: set, cls: str) -> str:
    parts = []
    for tok in re.split(r"(\s+)", text):
        parts.append(f'<span class="{cls}">{html.escape(tok)}</span>'
                     if _norm(tok) in words else html.escape(tok))
    return "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--menus-dir", default="data/synthetic/menus_OE")
    ap.add_argument("--html", required=True)
    ap.add_argument("--jsonl", required=True)
    a = ap.parse_args()

    pantry = load_pantry(Path(a.menus_dir))
    rewrites = pantry.by_type.get(ModificationType.TEMPLATE_PARAPHRASE, ())
    rows = []
    seen = set()
    for rw in rewrites:
        field = str(rw.dedup_key[0])
        o, n = rw.payload.get("original", ""), rw.payload.get("new", "")
        key = (field, o, n)
        if key in seen or not o or not n:
            continue
        seen.add(key)
        concept = (re.search(r"\(([^)]+)\)\s*$", rw.canonical) or [None, "?"])[1]
        info = analyze(o, n)
        rows.append({"concept": concept, "field": field, "original": o, "new": n, **info})

    # Two review lenses. A) net content loss: words removed without replacement —
    # the omission-like case (highest concern). B) head-term change with balanced
    # counts: the leading product/action word was swapped (scan for non-synonyms).
    net = sorted((r for r in rows if r["net_loss"] > 0),
                 key=lambda r: (r["net_loss"], r["score"]), reverse=True)
    head = sorted((r for r in rows if r["net_loss"] <= 0 and r["head_changed"] and r["lossy"]),
                  key=lambda r: (len(r["dropped"]), r["score"]), reverse=True)
    flagged = net + head
    other_lossy = [r for r in rows if r["lossy"] and r not in flagged]

    Path(a.jsonl).parent.mkdir(parents=True, exist_ok=True)
    with open(a.jsonl, "w", encoding="utf-8") as f:
        for r in flagged:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    def card(r, i):
        do, ad = set(r["dropped"]), set(r["added"])
        tag = f"net-loss {r['net_loss']}" if r["net_loss"] > 0 else "head-term change"
        return f"""<article>
  <h3>{i}. <code>{html.escape(r['concept'])}</code> <small>{html.escape(r['field'])} · {tag} · dropped {len(r['dropped'])} added {len(r['added'])}</small></h3>
  <div class="o">{_mark(r['original'], do, 'del')}</div>
  <div class="n">{_mark(r['new'], ad, 'ins')}</div>
  <p class="wd">dropped: {html.escape(', '.join(r['dropped']) or '—')} &nbsp;|&nbsp; added: {html.escape(', '.join(r['added']) or '—')}</p>
</article>"""

    secA = "".join(card(r, i) for i, r in enumerate(net, 1))
    secB = "".join(card(r, i) for i, r in enumerate(head, 1))
    body = (f'<h2>A · Net content loss ({len(net)}) — words removed, not replaced</h2>{secA}'
            f'<h2>B · Head-term changed, balanced ({len(head)}) — leading word swapped; scan for non-synonyms</h2>{secB}')
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Meaning-drift review</title><style>
:root{{color-scheme:light dark}}
body{{font:14px/1.55 system-ui,Segoe UI,sans-serif;margin:0;padding:24px;max-width:1000px;background:#fafafa;color:#111}}
@media(prefers-color-scheme:dark){{body{{background:#161616;color:#e8e8e8}}}}
h1{{font-size:20px;margin:0 0 4px}} p.sub{{color:#777;margin:0 0 20px}}
h2{{font-size:15px;margin:24px 0 12px;padding-bottom:4px;border-bottom:1px solid #ccc}}
@media(prefers-color-scheme:dark){{h2{{border-color:#444}}}}
article{{background:var(--c,#fff);border:1px solid #ddd;border-radius:10px;padding:12px 16px;margin:0 0 14px}}
@media(prefers-color-scheme:dark){{article{{--c:#1f1f1f;border-color:#333}}}}
h3{{font-size:13px;margin:0 0 8px}} h3 small{{color:#999;font-weight:400}}
code{{font:12px ui-monospace,Consolas,monospace;background:#0001;padding:1px 5px;border-radius:4px}}
@media(prefers-color-scheme:dark){{code{{background:#fff1}}}}
.o,.n{{padding:4px 0}} .o{{border-left:3px solid #e5534b;padding-left:8px}} .n{{border-left:3px solid #3fb950;padding-left:8px;margin-top:4px}}
del{{background:#ffd7d5;color:#82071e;text-decoration:none;border-radius:3px;padding:0 2px;font-weight:600}}
ins{{background:#c8f0c8;color:#0a5d1e;text-decoration:none;border-radius:3px;padding:0 2px;font-weight:600}}
@media(prefers-color-scheme:dark){{del{{background:#5a1a1a;color:#ffb3ad}}ins{{background:#183d1a;color:#a9e8ab}}}}
p.wd{{font-size:11.5px;color:#888;margin:6px 0 0}}
</style></head><body>
<h1>Guard #2 — template_paraphrase meaning-drift review</h1>
<p class="sub">{len(rows)} distinct approved template rewrites. This is a REVIEW AID, not an auto-reject: paraphrase legitimately rewords, so most changes are synonyms. The two lenses below isolate the higher-risk shapes — <b>A</b>: content removed without replacement; <b>B</b>: the leading product/action word swapped. {len(other_lossy)} further rewrites reword content in balanced synonym swaps (not shown). red = dropped source word, green = added.</p>
{body}
</body></html>"""
    Path(a.html).parent.mkdir(parents=True, exist_ok=True)
    Path(a.html).write_text(doc, encoding="utf-8")
    print(f"rewrites={len(rows)} | A net-loss={len(net)} | B head-change={len(head)} "
          f"| other balanced synonym swaps={len(other_lossy)} | pure add/reorder={len(rows)-sum(r['lossy'] for r in rows)}")
    print("top net-loss:")
    for r in net[:10]:
        print(f"  [{r['concept']}/{r['field']}] -{r['net_loss']} drop={r['dropped']} add={r['added']}")
    print("top head-term changes:")
    for r in head[:10]:
        print(f"  [{r['concept']}/{r['field']}] drop={r['dropped']} add={r['added']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
