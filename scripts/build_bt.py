"""Back-translation sobre STACKED-P (BT, opción A, T5 piloto / T6 corrida completa).

Dos condiciones emparejadas por hoja sobre STACKED-P:

* ``stacked_bt_en`` — BT del TEXTO de la consulta STACKED (rodaja de robustez);
* ``bt_orig_en`` — BT del TEXTO gold de la misma hoja (control).

Rediseño tras CP2: cada valor de eje y cada fragmento L2 se localiza con
:mod:`bt_alignment` y se enmascara entero, así que sale literalmente igual; la
BT solo traduce la prosa de la plantilla. La verificación es estructural, sin
LLM: máscaras preservadas y en el mismo orden, G0, G1, G3, G6 y la señal de
deriva para ordenar la auditoría humana.

Parte del fichero STACKED entregado (sha256 ``c34a…``) y su sidecar, nunca de
una regeneración. Fases:

  .venv-bt/Scripts/python scripts/build_bt.py --pilot --translate
  .venv-bt/Scripts/python scripts/build_bt.py --pilot --report

``--translate`` rellena la caché de traducción (``data/synthetic/bt_OE/cache/``);
``--report`` solo la reproduce (modo replay: falla si falta algo), verifica y
escribe salidas e informes. ``--fresh-check`` traduce de nuevo en GPU sin caché
e informa de cuántos textos coinciden con la caché (la caché manda).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import subprocess
import sys
import uuid
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import yaml  # noqa: E402

import audit_stacked_characterization as audit  # noqa: E402
import calibrate_characterization as cal  # noqa: E402
from synthetic.back_translation import (  # noqa: E402
    CachedEngine,
    MarianEngine,
    back_translate_many,
)
from synthetic.bt_alignment import AlignmentError, gold_slots, stacked_slots  # noqa: E402
from synthetic.characterization import norm_text  # noqa: E402

# mismo namespace que scripts/package_for_retrieval.py
_NS = uuid.UUID("6f9619ff-8b86-d011-b42d-00cf4fc964ff")
CONDITIONS = ("stacked_bt", "bt_orig", "stacked_btv", "bt_origv")
PROTOCOL_VERSION = "bt-masked-1"  # rediseño CP2: valores enmascarados, verificación estructural


def stable_id(key: str) -> str:
    return str(uuid.uuid5(_NS, key))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Muestreo del piloto
# ---------------------------------------------------------------------------

def allocate(sizes: Mapping[str, int], n: int) -> dict[str, int]:
    """Reparto proporcional por resto mayor; nunca más que el estrato."""
    total = sum(sizes.values())
    n = min(n, total)
    raw = {k: n * v / total for k, v in sizes.items()}
    alloc = {k: min(int(r), sizes[k]) for k, r in raw.items()}
    order = sorted(sizes, key=lambda k: (-(raw[k] - int(raw[k])), k))
    i = 0
    while sum(alloc.values()) < n:
        k = order[i % len(order)]
        if alloc[k] < sizes[k]:
            alloc[k] += 1
        i += 1
    return alloc


def sample_pilot(concept_of: Mapping[str, str], n: int, *, seed: int) -> list[str]:
    """``n`` claves estratificadas por concepto, proporcional (las
    canalizaciones OEB quedan limitadas a su proporción). Orden de muestreo
    con ``random.Random(seed ^ zlib.crc32(concepto))``, nunca ``hash()``."""
    by: dict[str, list[str]] = {}
    for k, c in concept_of.items():
        by.setdefault(c, []).append(k)
    alloc = allocate({c: len(v) for c, v in by.items()}, n)
    out = []
    for c in sorted(by):
        keys = sorted(by[c])
        rng = random.Random(seed ^ zlib.crc32(c.encode("utf-8")))
        out.extend(rng.sample(keys, alloc[c]))
    return sorted(out)


# ---------------------------------------------------------------------------
# Registros de salida (contrato §6)
# ---------------------------------------------------------------------------

def _flat_params(params: Mapping) -> dict:
    out = {}
    for k, v in (params or {}).items():
        if isinstance(v, Mapping) and "values" in v:
            vals = v["values"]
            out[k] = " ".join(vals[0]["value"].split()) if vals else None
        else:
            out[k] = v
    return out


_SUFFIX = {"stacked_bt": "bt", "stacked_btv": "btv", "bt_orig": "btorig", "bt_origv": "btorigv"}


def output_record(condition: str, src: Mapping, text: str, res, bt_meta: Mapping,
                  masked_values: int, value_bt: bool = False) -> dict:
    """``condition`` = ``<condición>_<pivote>``; ``value_bt`` = la partida lleva
    algún valor o fragmento sustituido por su variante aprobada."""
    pivot = bt_meta["pivot"]
    base = condition[: -len(pivot) - 1]
    item_key = f"{src['item_key']}_{_SUFFIX[base]}_{pivot}"
    if base.startswith("stacked"):
        gold = src["gold_item_key"]
        mtypes = list(src.get("modification_types") or [])
        ttypes = list(src.get("texto_modification_types") or [])
    else:
        gold = src["item_key"]
        mtypes, ttypes = [], []
    bt_types = ["back_translation"] + (["value_back_translation"] if value_bt else [])
    post = list(res.surviving_types) + bt_types
    return {
        "id": stable_id(item_key),
        "item_key": item_key,
        "parent_key": src["parent_key"],
        "gold_item_key": gold,
        "ud": src.get("ud"),
        "concept": src.get("concept"),
        "parameters": _flat_params(src.get("parameters")),
        "text": text,
        "condition": condition,
        "source_item_key": src["item_key"],
        "source_text_sha256": sha256_text(src["text"]),
        "modification_types": mtypes + bt_types,
        "modification_count": len(mtypes) + len(bt_types),
        "texto_modification_types": ttypes + bt_types,
        "texto_modification_count": len(ttypes) + len(bt_types),
        "texto_modification_types_post_bt": post,
        "texto_modification_count_post_bt": len(post),
        "reverted_types": list(res.reverted_types),
        "bt": dict(bt_meta),
        "characterization_check": {"protocol_version": PROTOCOL_VERSION,
                                   "mode": "structural_masked",
                                   "masked_values": masked_values,
                                   "not_rendered": list(res.not_rendered)},
    }


# ---------------------------------------------------------------------------
# Auditoría humana
# ---------------------------------------------------------------------------

_QUESTION = ("¿Describe exactamente la misma partida, con los mismos valores en todos "
             "los ejes del TEXTO?")


def audit_markdown(title: str, rows: Sequence[Mapping]) -> str:
    """Casillas como los menús, ciego al motor, con el TEXTO gold al lado.
    Ordenado por la señal de deriva (lo dudoso primero). Dudoso cuenta como No."""
    lines = [f"# {title}", "", f"**Pregunta única:** {_QUESTION}", "",
             "Marca una casilla por consulta. *Dudoso* cuenta como *No*. "
             "No uses la rúbrica v2.", ""]
    ordered = sorted(rows, key=lambda r: (-(r.get("drift") or 0), r["item_key"]))
    for i, r in enumerate(ordered, 1):
        lines += [
            f"## {i}. `{r['item_key']}`",
            "",
            f"**Consulta:** {' '.join(r['text'].split())}",
            "",
            f"**TEXTO gold:** {' '.join(r['gold_text'].split())}",
            "",
            "- [ ] Sí",
            "- [ ] No",
            "- [ ] Dudoso",
            "",
        ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# BM25 (sesgo de selección)
# ---------------------------------------------------------------------------

class Bm25Index:
    def __init__(self, corpus: Mapping[str, str]):
        from rank_bm25 import BM25Okapi
        from utils.text_processing import normalize_text

        self._norm = normalize_text
        self.keys = sorted(corpus)
        self._bm25 = BM25Okapi([normalize_text(corpus[k]) for k in self.keys])

    def top1(self, query: str) -> str:
        scores = self._bm25.get_scores(self._norm(query))
        best = max(range(len(scores)), key=lambda i: (scores[i], -i))
        return self.keys[best]


def bm25_acc1(index: Bm25Index, queries: Sequence[tuple[str, str]],
              groups: Mapping[str, frozenset]) -> float:
    if not queries:
        return float("nan")
    hits = 0
    for text, gold in queries:
        hits += index.top1(text) in groups.get(gold, frozenset({gold}))
    return hits / len(queries)


# ---------------------------------------------------------------------------
# Carga y fases
# ---------------------------------------------------------------------------

def load_all(cfg):
    handoff = REPO / cfg["handoff_dir"]
    stacked_path = handoff / "OE_stacked_texto.json"
    digest = audit.sha256_file(stacked_path)
    if digest != audit.STACKED_SHA256:
        raise SystemExit(f"OE_stacked_texto.json cambió: {digest}")
    stacked = {q["item_key"]: q for q in json.loads(stacked_path.read_text(encoding="utf-8"))}
    corpus = {r["item_key"]: r for r in json.loads((handoff / "OE_texto.json").read_text(encoding="utf-8"))}
    p_keys = json.loads((REPO / cfg["bt"]["stacked_p_keys"]).read_text(encoding="utf-8"))
    if p_keys["source_sha256"] != digest:
        raise SystemExit("STACKED-P no corresponde al STACKED entregado")
    return handoff, stacked, corpus, p_keys["item_keys"], digest


def select(cfg, stacked, p_keys, mode: str) -> list[str]:
    if mode == "full":
        return sorted(p_keys)
    n = cfg["bt"]["pilot_size"] if mode == "pilot" else cfg["bt"]["mask_experiment_size"]
    seed = cfg["seed"] if mode == "pilot" else cfg["seed"] + 1
    return sample_pilot({k: stacked[k]["parent_key"] for k in p_keys}, n, seed=seed)


def jobs_for(keys, stacked, corpus) -> list[tuple[str, Mapping]]:
    """(condición, registro de origen); ``bt_orig`` una vez por gold."""
    out, golds = [], []
    for k in keys:
        out.append(("stacked_bt", stacked[k]))
        golds.append(stacked[k]["gold_item_key"])
    for g in sorted(set(golds)):
        out.append(("bt_orig", corpus[g]))
    return out


def make_engine(cfg, mode: str) -> CachedEngine:
    b = cfg["bt"]
    marian = MarianEngine(
        {("es", b["pivot"]): (b["model_es_en"], b["revision_es_en"]),
         (b["pivot"], "es"): (b["model_en_es"], b["revision_en_es"])},
        num_beams=b["decoding"]["num_beams"], max_new_tokens=b["decoding"]["max_new_tokens"],
        batch_size=b["batch_size"], license=b["license"])
    return CachedEngine(marian, REPO / b["cache_dir"], mode=mode)


def value_spans(jobs, stage, corpus, sidecar) -> list[list[tuple[int, int]]]:
    return [[(s.start, s.end) for s in slots] for slots in value_slots(jobs, stage, corpus, sidecar)]


def value_slots(jobs, stage, corpus, sidecar):
    """Huecos no vacíos (valores de eje y fragmentos L2) de cada texto de origen,
    en orden de texto. STACKED-P solo contiene consultas que alinean (T3) y el
    gold alinea siempre: un fallo aquí es un error; nunca se traduce sin
    proteger los valores."""
    out = []
    for cond, src in jobs:
        concept = stage[src["parent_key"]]
        try:
            if cond == "stacked_bt":
                gold = corpus[src["gold_item_key"]]
                slots = stacked_slots(concept, gold["item_key"], gold["text"], src["text"],
                                      sidecar[src["item_key"]])
            else:
                slots = gold_slots(concept, src["item_key"], src["text"])
        except AlignmentError as err:
            raise SystemExit(f"alineación imposible en {src['item_key']}: {err}") from err
        out.append(sorted((s for s in slots if s.end > s.start), key=lambda s: s.start))
    return out


def approved_variants(cfg):
    """(concepto, placeholder, superficie) -> variantes aprobadas (tabla filtrada
    ∩ lista aprobada tras la auditoría)."""
    v = cfg["bt_values"]
    approved = set(json.loads((REPO / v["approved"]).read_text(encoding="utf-8"))["uids"])
    out: dict[tuple, list[str]] = {}
    for line in (REPO / v["table"]).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["status"] == "ok" and r["uid"] in approved:
            out.setdefault((r["concept"], r["placeholder"], r["surface"]), []).append(r["variant"])
    return {k: sorted(set(vs)) for k, vs in out.items()}


def assemble_rows(cfg, ctx, jobs, results, slots, stage, sidecar, forbidden):
    """Condiciones ``stacked_btv`` y ``bt_origv``: la misma BT de prosa de cada
    trabajo con los marcadores de valor rellenos con variantes aprobadas
    (:func:`bt_values.assemble_values`) y la verificación estructural."""
    from synthetic.bt_values import assemble_values

    variants = approved_variants(cfg)
    label_p = cfg["bt_values"]["label_probability"]
    rows, seen = [], {}
    for (cond, src), bt_res, job_slots in zip(jobs, results, slots):
        vcond = cond + "v"
        gold = src.get("gold_item_key", src["item_key"])
        row = {"condition": vcond, "source_item_key": src["item_key"], "gold_item_key": gold,
               "parent_key": src["parent_key"], "source_text": src["text"],
               "bt_text": None, "pivot_text": bt_res.pivot_text, "n_masks": len(bt_res.mapping),
               "subs": []}
        if not bt_res.ok:
            row.update(ok=False, gate="BT", axis=None, reason=bt_res.reason)
            rows.append((row, None, bt_res))
            continue
        concept = src["parent_key"]
        params = stage[concept].get("parameters") or {}
        labels = {f"${ax}": " ".join(b["label"].split()) for ax, b in params.items()}
        marker_slot = {m: (s.placeholder, s.text) for m, s in zip(bt_res.values, job_slots)}
        text, subs = assemble_values(
            bt_res.back_masked, bt_res.mapping, bt_res.values, marker_slot,
            lambda ph, surface: variants.get((concept, ph, surface), []), labels,
            seed=cfg["seed"], key=f"{vcond}|{src['item_key']}", label_p=label_p)
        records = sidecar.get(src["item_key"], []) if cond == "stacked_bt" else None
        r = ctx.check(text, gold, extractors=(), source_text=src["text"],
                      records=records, query_key=src["item_key"], forbidden=forbidden,
                      substitutions=subs)
        if r.ok:
            nt = norm_text(text)
            if nt in seen.setdefault(vcond, {}):
                r.ok, r.gate, r.reason = False, "G6", f"duplicate_within_set:{seen[vcond][nt]}"
            else:
                seen[vcond][nt] = src["item_key"]
        row.update(bt_text=text, subs=subs, ok=r.ok, gate=r.gate, axis=r.axis, reason=r.reason,
                   surviving_types=r.surviving_types, reverted_types=r.reverted_types,
                   drift=r.drift.get("score"))
        rows.append((row, r, bt_res))
    return rows


def translate(cfg, jobs, engine, strategy, spans):
    texts = [src["text"] for _, src in jobs]
    return back_translate_many(texts, cfg["bt"]["pivot"], engine, strategy, spans=spans)


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def verify(cfg, ctx, jobs, results, sidecar, forbidden):
    """Verificación estructural (sin LLM) de cada salida de BT: los fallos de
    máscara u orden ya vienen del motor; aquí G0, G1, G3, G5 (informa) y G6."""
    rows, seen = [], {c: {} for c in CONDITIONS}
    for (cond, src), bt_res in zip(jobs, results):
        gold = src.get("gold_item_key", src["item_key"])
        row = {"condition": cond, "source_item_key": src["item_key"], "gold_item_key": gold,
               "parent_key": src["parent_key"], "source_text": src["text"],
               "bt_text": bt_res.text, "pivot_text": bt_res.pivot_text,
               "n_masks": len(bt_res.mapping)}
        if not bt_res.ok:
            row.update(ok=False, gate="BT", axis=None, reason=bt_res.reason)
            rows.append((row, None, bt_res))
            continue
        records = sidecar.get(src["item_key"], []) if cond == "stacked_bt" else None
        r = ctx.check(bt_res.text, gold, extractors=(), source_text=src["text"],
                      records=records, query_key=src["item_key"], forbidden=forbidden)
        if r.ok:
            nt = norm_text(bt_res.text)
            if nt in seen[cond]:
                r.ok, r.gate, r.reason = False, "G6", f"duplicate_within_set:{seen[cond][nt]}"
            else:
                seen[cond][nt] = src["item_key"]
        row.update(ok=r.ok, gate=r.gate, axis=r.axis, reason=r.reason,
                   surviving_types=r.surviving_types,
                   reverted_types=r.reverted_types, drift=r.drift.get("score"))
        rows.append((row, r, bt_res))
    return rows


# ---------------------------------------------------------------------------
# Informe del piloto / QA
# ---------------------------------------------------------------------------

def _pct(a, b):
    return f"{100 * a / b:.1f} %" if b else "—"


def metrics(cfg, ctx, rows, corpus, groups, stacked_p_keys, stacked, bm25=True) -> dict:
    m = {}
    for cond in CONDITIONS:
        rs = [r for r, _, _ in rows if r["condition"] == cond]
        acc = [r for r in rs if r["ok"]]
        m[cond] = {
            "n": len(rs), "accepted": len(acc),
            "no_op": sum(r.get("reason") == "no_op" for r in rs),
            "mask_lost": sum(r.get("reason") == "mask_lost" for r in rs),
            "value_order_changed": sum(r.get("reason") == "value_order_changed" for r in rs),
            "by_gate": Counter(r["gate"] for r in rs if not r["ok"]),
            "by_gate_axis": Counter(f"{r['gate']} {r['parent_key']} {r['axis'] or ''} "
                                    f"{(r['reason'] or '').split(':')[0]}".strip()
                                    for r in rs if not r["ok"]),
            "reverted": Counter(t for r in acc for t in r.get("reverted_types", [])),
            "surviving": Counter(t for r in acc for t in r.get("surviving_types", [])),
            "dist_before": [cal.token_distance(r["source_text"], corpus[r["gold_item_key"]]["text"]) for r in acc],
            "dist_after": [cal.token_distance(r["bt_text"], corpus[r["gold_item_key"]]["text"]) for r in acc],
            "by_concept": Counter((r["parent_key"], r["ok"]) for r in rs),
        }
    if bm25:
        index = Bm25Index({k: v["text"] for k, v in corpus.items()})
        acc_keys = {r["source_item_key"] for r, _, _ in rows
                    if r["condition"] == "stacked_bt" and r["ok"]}
        sel = [r["source_item_key"] for r, _, _ in rows if r["condition"] == "stacked_bt"]
        q = lambda keys: [(stacked[k]["text"], stacked[k]["gold_item_key"]) for k in keys]  # noqa: E731
        m["bm25"] = {
            "stacked_p_all": bm25_acc1(index, q(sorted(stacked_p_keys)), groups),
            "stacked_selected": bm25_acc1(index, q(sel), groups),
            "stacked_accepted": bm25_acc1(index, q(sorted(acc_keys)), groups),
        }
        for cs in ("stacked_bt", "stacked_btv"):
            m["bm25"][cs + "_accepted_bt"] = bm25_acc1(
                index, [(r["bt_text"], r["gold_item_key"]) for r, _, _ in rows
                        if r["condition"] == cs and r["ok"]], groups)
    return m


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    mid = len(xs) // 2
    return xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2


def report_markdown(title, cfg, m, rows, provenance, pair=("stacked_bt", "bt_orig")) -> str:
    cs, co = pair
    s, o = m[cs], m[co]
    acc_s = s["accepted"] / s["n"] if s["n"] else 0
    noop = s["no_op"] / s["n"] if s["n"] else 0
    lines = [f"# {title}", "",
             f"Pivote EN, MarianMT (`{cfg['bt']['model_es_en']}@{cfg['bt']['revision_es_en'][:7]}`, "
             f"`{cfg['bt']['model_en_es']}@{cfg['bt']['revision_en_es'][:7]}`), beam "
             f"{cfg['bt']['decoding']['num_beams']} sin muestreo, máscara `{cfg['bt']['mask_strategy']}`. "
             "Valores de eje y fragmentos L2 enmascarados; verificación estructural sin LLM. "
             f"Commit `{provenance['commit'][:7]}`.", "",
             "| Métrica | Valor | Umbral |", "|---|---:|---|",
             f"| Aceptación `{cs}_en` | {s['accepted']}/{s['n']} ({_pct(s['accepted'], s['n'])}) | ≥ 80 % → {'cumple' if acc_s >= 0.8 else '**no cumple**'} |",
             f"| Aceptación `{co}_en` | {o['accepted']}/{o['n']} ({_pct(o['accepted'], o['n'])}) | se reporta |",
             f"| No-ops `{cs}_en` | {s['no_op']} ({_pct(s['no_op'], s['n'])}) | ≤ 10 % → {'cumple' if noop <= 0.10 else '**no cumple**'} |",
             f"| Máscara perdida `{cs}_en` / `{co}_en` | {s['mask_lost']} / {o['mask_lost']} | se reporta |",
             f"| Valores cambiados de orden `{cs}_en` / `{co}_en` | {s['value_order_changed']} / {o['value_order_changed']} | se reporta |",
             f"| Mediana de distancia en tokens al gold, antes → después (`{cs}`) | {_median(s['dist_before'])} → {_median(s['dist_after'])} | se reporta |",
             f"| Mediana de distancia en tokens al gold, antes → después (`{co}`) | 0 → {_median(o['dist_after'])} | se reporta |"]
    if "bm25" in m:
        b = m["bm25"]
        diff = 100 * (b["stacked_accepted"] - b["stacked_selected"])
        lines += [f"| BM25 Acc@1 de STACKED: aceptadas / muestra / todo STACKED-P | "
                  f"{100 * b['stacked_accepted']:.1f} / {100 * b['stacked_selected']:.1f} / {100 * b['stacked_p_all']:.1f} % | "
                  f"diferencia ≤ 2 pp → {diff:+.1f} pp, {'cumple' if abs(diff) <= 2 else '**no cumple**'} |",
                  f"| BM25 Acc@1 de las consultas BT aceptadas | {100 * b[cs + '_accepted_bt']:.1f} % | se reporta |"]
    lines += ["", "## Rechazos por puerta", "", f"| Puerta | `{cs}_en` | `{co}_en` |", "|---|---:|---:|"]
    for g in sorted(set(s["by_gate"]) | set(o["by_gate"])):
        lines.append(f"| {g} | {s['by_gate'].get(g, 0)} | {o['by_gate'].get(g, 0)} |")
    lines += ["", f"## Rechazos por puerta, concepto, eje y motivo (`{cs}_en`, 25 primeros)", "",
              "| Clave | Consultas |", "|---|---:|"]
    lines += [f"| {k} | {v} |" for k, v in s["by_gate_axis"].most_common(25)]
    lines += ["", f"## Supervivencia de las modificaciones (G5, aceptadas `{cs}_en`)", "",
              "| Tipo | Sobrevive | Revertido |", "|---|---:|---:|"]
    for t in sorted(set(s["surviving"]) | set(s["reverted"])):
        lines.append(f"| {t} | {s['surviving'].get(t, 0)} | {s['reverted'].get(t, 0)} |")
    lines += ["", f"## Aceptación por concepto (`{cs}_en`)", "", "| Concepto | Aceptadas | Total |", "|---|---:|---:|"]
    concepts = sorted({c for c, _ in s["by_concept"]})
    for c in concepts:
        a, r = s["by_concept"].get((c, True), 0), s["by_concept"].get((c, False), 0)
        lines.append(f"| {c} | {a} | {a + r} |")
    lines += ["", f"## Ejemplos de rechazo (`{cs}_en`)", ""]
    shown = Counter()
    for r, _, _ in rows:
        if r["condition"] != cs or r["ok"] or shown[r["gate"]] >= 3:
            continue
        shown[r["gate"]] += 1
        lines += [f"- **{r['gate']}** `{r['source_item_key']}` eje {r['axis']} · {r['reason']}",
                  f"  - origen: {' '.join(r['source_text'].split())[:400]}",
                  f"  - BT: {' '.join((r['bt_text'] or r.get('pivot_text') or '').split())[:400]}"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument("--pilot", action="store_true")
    scope.add_argument("--full", action="store_true")
    phase = ap.add_mutually_exclusive_group(required=True)
    phase.add_argument("--translate", action="store_true")
    phase.add_argument("--report", action="store_true")
    phase.add_argument("--fresh-check", action="store_true")
    ap.add_argument("--no-bm25", action="store_true",
                    help="sin el diagnóstico BM25 (lento: horas en la corrida completa); los datos no dependen de él")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    mode = "pilot" if a.pilot else "full"
    handoff, stacked, corpus, p_keys, digest = load_all(cfg)
    keys = select(cfg, stacked, p_keys, mode)
    jobs = jobs_for(keys, stacked, corpus)
    strategy = cfg["bt"]["mask_strategy"]
    print(f"{mode}: {len(keys)} consultas STACKED-P, {len(jobs)} trabajos de BT, máscara {strategy}")
    stage = cal._load(REPO / cfg["stage_json"])
    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    spans = value_spans(jobs, stage, corpus, sidecar)

    if a.translate:
        res = translate(cfg, jobs, make_engine(cfg, "record"), strategy, spans)
        print(f"traducidas; fallos de máscara u orden: {Counter(r.reason for r in res if not r.ok)}")
        return 0

    if a.fresh_check:
        cached = make_engine(cfg, "replay")
        fresh = make_engine(cfg, "record")
        fresh._dir = REPO / cfg["bt"]["cache_dir"] / f"fresh-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
        r1 = translate(cfg, jobs, cached, strategy, spans)
        r2 = translate(cfg, jobs, fresh, strategy, spans)
        same = sum(x.back_masked == y.back_masked and x.pivot_text == y.pivot_text for x, y in zip(r1, r2))
        print(json.dumps({"jobs": len(jobs), "identical": same}))
        return 0

    # --report
    results = translate(cfg, jobs, make_engine(cfg, "replay"), strategy, spans)
    ctx = cal.load_context(cfg)
    forbidden = audit.forbidden_texts(handoff) | {norm_text(q["text"]) for q in stacked.values()}
    rows = verify(cfg, ctx, jobs, results, sidecar, forbidden)
    rows += assemble_rows(cfg, ctx, jobs, results, value_slots(jobs, stage, corpus, sidecar),
                          stage, sidecar, forbidden)
    groups = ctx.groups
    m = metrics(cfg, ctx, rows, corpus, groups, p_keys, stacked, bm25=not a.no_bm25)
    out_dir = REPO / cfg["bt"]["out_dir"] / ("pilot" if mode == "pilot" else "")
    pivot = cfg["bt"]["pivot"]
    bt_meta = {"pivot": pivot, "engine": "marian",
               "model_es_en": f"{cfg['bt']['model_es_en']}@{cfg['bt']['revision_es_en']}",
               "model_en_es": f"{cfg['bt']['model_en_es']}@{cfg['bt']['revision_en_es']}",
               "license": cfg["bt"]["license"],
               "decoding": {"num_beams": cfg["bt"]["decoding"]["num_beams"], "do_sample": False},
               "mask_strategy": strategy}

    files: dict[str, str] = {}
    rejected = []
    for cond in CONDITIONS:
        recs, side = [], []
        for row, r, bt_res in rows:
            if row["condition"] != cond:
                continue
            is_stacked = cond.startswith("stacked")
            src = stacked[row["source_item_key"]] if is_stacked else corpus[row["source_item_key"]]
            if not row["ok"]:
                rejected.append({k: row.get(k) for k in ("condition", "source_item_key", "gold_item_key",
                                                         "gate", "axis", "reason", "bt_text")})
                continue
            rec = output_record(f"{cond}_{pivot}", src, row["bt_text"], r, bt_meta, len(bt_res.values),
                                value_bt=bool(row.get("subs")))
            recs.append(rec)
            mods = list(sidecar.get(src["item_key"], [])) if is_stacked else []
            mods.append({"type": "back_translation", "layer": "surface", "pivot": pivot,
                         "engine": "marian", "original_sha256": sha256_text(src["text"]),
                         "new_sha256": sha256_text(row["bt_text"]),
                         "masked": {"strategy": strategy, "n": len(bt_res.mapping),
                                    "literals": list(bt_res.mapping.values())}})
            for sub in row.get("subs") or []:
                mods.append({"type": "value_back_translation", "layer": "surface",
                             "pivot": f"es-{pivot}-x-es", **sub})
            side.append({"item_key": rec["item_key"], "source_item_key": src["item_key"],
                         "modifications": mods})
        recs.sort(key=lambda r: r["item_key"])
        side.sort(key=lambda r: r["item_key"])
        files[f"OE_{cond}_{pivot}_texto.json"] = json.dumps(recs, ensure_ascii=False, indent=1) + "\n"
        files[f"OE_{cond}_{pivot}_modifications.jsonl"] = "".join(
            json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n" for s in side)
    rejected.sort(key=lambda r: (r["condition"], r["source_item_key"]))
    files["OE_bt_rejected.jsonl"] = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
                                           for r in rejected)
    shas = {}
    for name, text in files.items():
        audit.write_atomic(out_dir / name, text)
        shas[name] = audit.sha256_file(out_dir / name)

    inputs = {"OE_stacked_texto.json": digest,
              "OE_texto.json": audit.sha256_file(handoff / "OE_texto.json"),
              "BC3CAT_Syn_modifications.jsonl": audit.sha256_file(REPO / cfg["stacked_sidecar"]),
              "OE_stacked_P_keys.json": audit.sha256_file(REPO / cfg["bt"]["stacked_p_keys"]),
              "OE_2026_stage.json": audit.sha256_file(REPO / cfg["stage_json"])}
    provenance = {"commit": git_commit(), "run_id": f"bt-{mode}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
                  "mode": mode, "seed": cfg["seed"], "bt": bt_meta,
                  "translation_cache": cfg["bt"]["cache_dir"],
                  "verification": "structural_masked", "protocol_version": PROTOCOL_VERSION,
                  "inputs_sha256": inputs, "outputs_sha256": shas,
                  "counts": {c: {"n": m[c]["n"], "accepted": m[c]["accepted"]} for c in CONDITIONS}}
    audit.write_atomic(out_dir / "OE_bt_provenance.json",
                       json.dumps(provenance, ensure_ascii=False, indent=1) + "\n")

    docs = REPO / "docs" / "synthetic" / "bt"
    if mode == "pilot":
        audit.write_atomic(docs / "OE_bt_pilot_report.md",
                           report_markdown("Piloto de BT sobre STACKED-P (OE)", cfg, m, rows, provenance))
        audit.write_atomic(docs / "OE_bt_pilot_report_values.md",
                           report_markdown("Piloto de BT de prosa + valores sobre STACKED-P (OE)",
                                           cfg, m, rows, provenance, pair=("stacked_btv", "bt_origv")))
        for (cs, co), name, title in (
                (("stacked_bt", "bt_orig"), "OE_bt_pilot_audit", "Auditoría humana del piloto de BT (OE)"),
                (("stacked_btv", "bt_origv"), "OE_bt_pilot_audit_values",
                 "Auditoría humana del piloto de BT de prosa + valores (OE)")):
            accepted_s = [{"item_key": r["source_item_key"], "text": r["bt_text"],
                           "gold_text": corpus[r["gold_item_key"]]["text"], "drift": r.get("drift")}
                          for r, _, _ in rows if r["condition"] == cs and r["ok"]]
            orig = [{"item_key": r["source_item_key"], "text": r["bt_text"],
                     "gold_text": corpus[r["gold_item_key"]]["text"], "drift": r.get("drift")}
                    for r, _, _ in rows if r["condition"] == co and r["ok"]]
            # «bt_orig_audit» es la semilla del piloto ya entregado; no cambia
            rng = random.Random(cfg["seed"] ^ zlib.crc32(f"{co}_audit".encode()))
            orig = rng.sample(orig, min(cfg["bt"]["audit_bt_orig"], len(orig)))
            anon = [dict(r, item_key=f"A{i:03d}") for i, r in enumerate(accepted_s + orig, 1)]
            key_map = {a["item_key"]: (r["item_key"], cs if i <= len(accepted_s) else co)
                       for i, (a, r) in enumerate(zip(anon, accepted_s + orig), 1)}
            audit.write_atomic(docs / f"{name}.md", audit_markdown(title, anon))
            audit.write_atomic(out_dir / f"{name}_key.json",
                               json.dumps(key_map, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    else:
        audit.write_atomic(docs / "OE_bt_qa.md",
                           report_markdown("QA de la BT sobre STACKED-P (OE)", cfg, m, rows, provenance))
        audit.write_atomic(docs / "OE_bt_qa_values.md",
                           report_markdown("QA de la BT de prosa + valores sobre STACKED-P (OE)",
                                           cfg, m, rows, provenance, pair=("stacked_btv", "bt_origv")))
    if audit.sha256_file(handoff / "OE_stacked_texto.json") != audit.STACKED_SHA256:
        raise SystemExit("OE_stacked_texto.json cambió durante la corrida")
    print(json.dumps(provenance["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
