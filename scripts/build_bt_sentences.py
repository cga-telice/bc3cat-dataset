"""BT de prosa por frases con candidatas y respaldo (vuelta tras la auditoría de prosas).

Para ``bt_origv`` (BT sobre el TEXTO gold, valores enmascarados):

1. la prosa se parte en frases; las frases se agrupan por su forma con huecos
   genéricos (119 en OE);
2. cada frase representativa se traduce por varias cadenas (``bt_sentences.chains``:
   ES→EN→ES y ES→EN→X→ES), **sin** enmascarar el glosario;
3. los términos del glosario que se pierden se restauran después
   (:func:`bt_restore.restore_terms`, idea de César); si no se puede con
   seguridad, la candidata se descarta;
4. ``--candidates`` escribe la auditoría por frase (gold frente a cada candidata);
5. ``--assemble`` lee los veredictos: por frase, la primera candidata aprobada en el
   orden de ``chains``; si ninguna, la frase original. Una partida cuenta como BT si
   al menos una de sus frases está traducida (decisión de César). Los valores se
   rellenan como en ``bt_origv`` (:func:`bt_values.assemble_values`).

  .venv-bt/Scripts/python scripts/build_bt_sentences.py --candidates
  .venv-bt/Scripts/python scripts/build_bt_sentences.py --assemble
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

import yaml  # noqa: E402

import audit_stacked_characterization as audit  # noqa: E402
import build_bt  # noqa: E402
import build_bt_values  # noqa: E402
import calibrate_characterization as cal  # noqa: E402
from synthetic.back_translation import reassemble, segment  # noqa: E402
from synthetic.bt_masking import MARKER_RE, check_masks, mask_with_values, unmask_surface  # noqa: E402
from synthetic.bt_restore import renumber, restore_terms  # noqa: E402
from synthetic.bt_values import assemble_values  # noqa: E402
from synthetic.characterization import norm_text  # noqa: E402


def shape(sentence: str) -> str:
    return MARKER_RE.sub("[·]", sentence)


def prepare(cfg):
    handoff, stacked, corpus, p_keys, digest = build_bt.load_all(cfg)
    keys = build_bt.select(cfg, stacked, p_keys, "full")
    jobs = [j for j in build_bt.jobs_for(keys, stacked, corpus) if j[0] == "bt_orig"]
    stage = cal._load(REPO / cfg["stage_json"])
    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    slots = build_bt.value_slots(jobs, stage, corpus, sidecar)
    masked = []
    for (_, src), sl in zip(jobs, slots):
        m, mapping, values = mask_with_values(src["text"], cfg["bt"]["mask_strategy"],
                                              [(s.start, s.end) for s in sl])
        masked.append((m, mapping, values, segment(m)))
    reps: dict[str, str] = {}  # forma -> frase representativa (primera en orden)
    rep_values: dict[str, list] = {}  # forma -> marcadores de valor de la representativa, en orden
    for m, mapping, values, pieces in masked:
        for p in pieces:
            if p.translate and shape(p.text) not in reps:
                reps[shape(p.text)] = p.text
                rep_values[shape(p.text)] = [mk for mk in MARKER_RE.findall(p.text) if mk in values]
    cfg["_rep_values"] = rep_values
    return handoff, stacked, corpus, stage, sidecar, jobs, slots, masked, reps


def candidates(cfg, reps, mode):
    """{forma: [(cadena, texto restaurado | None, motivo)]} en el orden de ``chains``."""
    prose = build_bt.make_engine(cfg, mode)
    values = build_bt_values.make_engine(cfg, mode)
    terms = list(cfg["bt"]["glossary"]) + list(cfg["bt_sentences"]["extra_glossary"])
    shapes = sorted(reps)
    texts = [reps[s] for s in shapes]
    out = {s: [] for s in shapes}
    for chain in cfg["bt_sentences"]["chains"]:
        if chain == "en":
            back = prose.translate(prose.translate(texts, "es", "en"), "en", "es")
        else:
            x = chain.split("-")[1]
            back = values.translate(values.translate(values.translate(texts, "es", "en"), "en", x), x, "es")
        for s, src, b in zip(shapes, texts, back):
            r = restore_terms(src, b, terms)
            vals = cfg["_rep_values"][s]
            if r.ok and [mk for mk in MARKER_RE.findall(r.text) if mk in vals] != vals:
                out[s].append((chain, None, "value_order_changed"))
            elif not r.ok:
                out[s].append((chain, None, r.reason))
            elif shape(r.text) == s:
                out[s].append((chain, None, "no_op"))
            else:
                out[s].append((chain, r.text, None))
    return out


def audit_md(cands) -> tuple[str, dict]:
    lines = ["# Frases traducidas de bt_origv (auditoría por frase)", "",
             "Cada entrada: una frase del TEXTO gold con los valores y cantidades como [·] y "
             "una traducción de ida y vuelta candidata. Los [·] no se juzgan.", ""]
    index = {}
    n = 0
    for s in sorted(cands):
        for chain, text, _ in cands[s]:
            if text is None:
                continue
            n += 1
            fid = f"F{n:03d}"
            index[fid] = {"shape": s, "chain": chain}
            lines += [f"## {fid}", "", f"**Frase gold:** {' '.join(s.split())}", "",
                      f"**Frase traducida:** {' '.join(shape(text).split())}", ""]
    return "\n".join(lines) + "\n", index


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--candidates", action="store_true")
    g.add_argument("--assemble", action="store_true")
    a = ap.parse_args(argv)
    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    bs = cfg["bt_sentences"]
    handoff, stacked, corpus, stage, sidecar, jobs, slots, masked, reps = prepare(cfg)
    cands = candidates(cfg, reps, "record" if a.candidates else "replay")
    print(f"{len(jobs)} textos, {len(reps)} frases distintas; candidatas por cadena:",
          {c: sum(1 for s in cands if any(ch == c and t for ch, t, _ in cands[s]))
           for c in bs["chains"]})

    if a.candidates:
        md, index = audit_md(cands)
        audit.write_atomic(REPO / bs["audit"], md)
        audit.write_atomic(REPO / bs["index"], json.dumps(index, ensure_ascii=False, indent=1) + "\n")
        print(f"{len(index)} pares frase/candidata para auditar;",
              Counter(r for s in cands for _, t, r in cands[s] if t is None))
        return 0

    # --assemble
    index = json.loads((REPO / bs["index"]).read_text(encoding="utf-8"))
    ok_pairs = set()
    for line in (REPO / bs["verdicts"]).read_text(encoding="utf-8").splitlines():
        if line.strip():
            v = json.loads(line)
            if v["veredicto"] == "Sí":
                ok_pairs.add((index[v["id"]]["shape"], index[v["id"]]["chain"]))
    chosen = {}
    for s, lst in cands.items():
        for chain, text, _ in lst:
            if text is not None and (s, chain) in ok_pairs:
                chosen[s] = (chain, text)
                break

    ctx = cal.load_context(cfg)
    forbidden = audit.forbidden_texts(handoff) | {norm_text(q["text"]) for q in stacked.values()}
    variants = build_bt.approved_variants(cfg)
    label_p = cfg["bt_values"]["label_probability"]
    recs, rejected, seen = [], [], {}
    bt_meta = {"pivot": "en", "engine": "marian", "unit": "sentence",
               "chains": bs["chains"], "mask_strategy": cfg["bt"]["mask_strategy"],
               "glossary_restoration": "post"}
    for (_, src), sl, (m, mapping, values, pieces) in zip(jobs, slots, masked):
        out_pieces, n_bt, n_all, used = [], 0, 0, []
        for p in pieces:
            if not p.translate:
                continue
            n_all += 1
            c = chosen.get(shape(p.text))
            if c:
                out_pieces.append(renumber(c[1], reps[shape(p.text)], p.text))
                n_bt += 1
                used.append(c[0])
            else:
                out_pieces.append(p.text)
        if n_bt == 0:
            rejected.append({"source_item_key": src["item_key"], "reason": "no_sentence_translated"})
            continue
        back_masked = reassemble(pieces, out_pieces)
        check_masks(back_masked, mapping)
        concept = src["parent_key"]
        params = stage[concept].get("parameters") or {}
        labels = {f"${ax}": " ".join(b["label"].split()) for ax, b in params.items()}
        marker_slot = {mk: (s.placeholder, s.text) for mk, s in zip(values, sl)}
        text, subs = assemble_values(back_masked, mapping, values, marker_slot,
                                     lambda ph, surface: variants.get((concept, ph, surface), []),
                                     labels, seed=cfg["seed"], key=f"bt_origv|{src['item_key']}",
                                     label_p=label_p)
        r = ctx.check(text, src["item_key"], extractors=(), source_text=src["text"],
                      query_key=src["item_key"], forbidden=forbidden, substitutions=subs)
        if r.ok and norm_text(text) in seen:
            r.ok, r.gate, r.reason = False, "G6", "duplicate_within_set"
        if not r.ok:
            rejected.append({"source_item_key": src["item_key"], "gate": r.gate, "reason": r.reason})
            continue
        seen[norm_text(text)] = src["item_key"]
        rec = build_bt.output_record("bt_origv_en", src, text, r, bt_meta, len(values), value_bt=bool(subs))
        rec["bt_sentences"] = {"translated": n_bt, "total": n_all, "fraction": round(n_bt / n_all, 3),
                               "chains": dict(Counter(used))}
        rec["characterization_check"]["mode"] = "structural_masked+sentence_audit"
        recs.append(rec)
    recs.sort(key=lambda r: r["item_key"])
    audit.write_atomic(REPO / bs["output"], json.dumps(recs, ensure_ascii=False, indent=1) + "\n")
    audit.write_atomic(REPO / bs["rejected"], "".join(
        json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n" for x in sorted(rejected, key=lambda x: x["source_item_key"])))
    frac = [r["bt_sentences"]["fraction"] for r in recs]
    print(json.dumps({
        "partidas": len(recs), "descartadas": len(rejected),
        "conceptos": len({r["parent_key"] for r in recs}),
        "frases_con_bt": len(chosen), "frases": len(reps),
        "partidas_100pct_bt": sum(f == 1 for f in frac),
        "fraccion_media": round(sum(frac) / max(len(frac), 1), 3),
        "rechazos": dict(Counter(x.get("gate") or x["reason"] for x in rejected)),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
