"""Tabla de variantes de valores de eje y fragmentos L2 (BT, vuelta tras CP4).

Inventario cerrado de superficies (gold de los conceptos de STACKED-P más las
reescrituras de STACKED-P), cadena ES→EN→X→ES por superficie (X ∈
``bt_values.pivots``), entrada «ETIQUETA: valor» en L1, filtro automático
contra las hermanas y menú para que César apruebe.

  .venv-bt/Scripts/python scripts/build_bt_values.py --translate
  .venv-bt/Scripts/python scripts/build_bt_values.py --menu

Salidas: ``bt_values.table`` (todas las candidatas, con estado y motivo) y
``bt_values.menu`` (solo las que pasan el filtro, con casillas).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import zlib
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
from synthetic.back_translation import CachedEngine, MarianEngine  # noqa: E402
from synthetic.bt_masking import MARKER_RE, MaskError, check_masks, mask_surface, unmask_surface  # noqa: E402
from dataclasses import replace  # noqa: E402

from synthetic.bt_values import (  # noqa: E402
    Candidate,
    concept_docs,
    domain_terms,
    lost_domain_terms,
    reverts,
    filter_candidates,
    menu_markdown,
    source_text,
    split_label,
    value_groups,
)


def translatable(text: str) -> bool:
    """Queda alguna palabra fuera de las máscaras (si no, nada que traducir)."""
    masked, _ = mask_surface(text, "bracket")
    return bool(re.search(r"[^\W\d_]{2,}", MARKER_RE.sub(" ", masked)))


def make_engine(cfg, mode: str) -> CachedEngine:
    v = cfg["bt_values"]
    models = {tuple(k.split("-")): tuple(m) for k, m in v["models"].items()}
    d = cfg["bt"]["decoding"]
    eng = MarianEngine(models, num_beams=d["num_beams"], max_new_tokens=d["max_new_tokens"],
                       batch_size=cfg["bt"]["batch_size"], license=json.dumps(v["licenses"]),
                       length_ratio=v["length_ratio"])
    return CachedEngine(eng, REPO / v["cache_dir"], mode=mode)


def chain(engine, texts: list[str], pivot: str) -> list[tuple[str, bool]]:
    """ES→EN→X→ES con cantidades, bandas y siglas enmascaradas."""
    prepared = [mask_surface(t, "bracket") for t in texts]
    masked = [m for m, _ in prepared]
    en = engine.translate(masked, "es", "en")
    x = engine.translate(en, "en", pivot)
    back = engine.translate(x, pivot, "es")
    out = []
    for b, (_, mapping) in zip(back, prepared):
        try:
            check_masks(b, mapping)
            out.append((unmask_surface(b, mapping), True))
        except MaskError:
            out.append((b, False))
    return out


def gold_surface(stage, c: Candidate) -> str:
    """Valor gold de la opción del candidato (L1) o fragmento gold (L2)."""
    params = stage[c.concept].get("parameters") or {}
    axis = c.placeholder[1:]
    if axis in params:
        return params[axis]["values"][ord(c.option) - 97]["value"]
    return c.option


def write_verdicts(cfg, final, menu: str) -> None:
    """Combina los veredictos de auditoría (``bt_values.verdicts``, uno por
    casilla) con el filtro: aprobada = veredicto A y sigue pasando el filtro.
    Escribe el menú marcado, la lista de aprobadas y una muestra para César."""
    v = cfg["bt_values"]
    paths = [REPO / p for p in v["verdicts"]]
    if not all(p.exists() for p in paths):
        return
    verdicts = {}
    for p in paths:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                verdicts[r["uid"]] = r
    ok = {c.uid for c in final if c.status == "ok"}
    approved = sorted(u for u, r in verdicts.items() if r["veredicto"] == "A" and u in ok)
    missing = ok - set(verdicts)
    if missing:
        raise SystemExit(f"{len(missing)} casillas del menú sin veredicto")
    marked = menu
    for u in approved:
        marked = marked.replace(f"- [ ] `{u}`", f"- [x] `{u}`")
    audit.write_atomic(REPO / v["menu_marked"], marked)
    audit.write_atomic(REPO / v["approved"], json.dumps(
        {"source": "auditoría por agentes (L1, L2) + filtros automáticos; muestra pendiente de César",
         "n": len(approved), "uids": approved}, ensure_ascii=False, indent=1) + "\n")

    rng = random.Random(cfg["seed"] ^ zlib.crc32(b"bt_values_sample"))
    a = [verdicts[u] for u in approved]
    r = [x for u, x in verdicts.items() if x["veredicto"] == "R" and u in ok]
    a = rng.sample(a, min(60, len(a)))
    r = rng.sample(r, min(30, len(r)))
    lines = ["# Muestra de la auditoría de variantes (OE)", "",
             f"{len(approved)} aprobadas en total. Abajo, {len(a)} aprobadas y {len(r)} rechazadas al azar "
             "(semilla fija), con el motivo del auditor. Marca las que **no** estés de acuerdo.", ""]
    for title, rows in (("Aprobadas", a), ("Rechazadas", r)):
        lines += [f"## {title}", ""]
        for x in rows:
            label = f"{x['etiqueta']} · " if x.get("etiqueta") else ""
            lines.append(f"- [ ] `{x['uid']}` {label}**{x['original']}** → {x['variante']}  _({x['motivo']})_")
        lines.append("")
    audit.write_atomic(REPO / v["sample"], "\n".join(lines))
    print(f"aprobadas: {len(approved)}; muestra: {len(a)} A + {len(r)} R")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--translate", action="store_true")
    g.add_argument("--menu", action="store_true")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    handoff, stacked, corpus, p_keys, digest = build_bt.load_all(cfg)
    stage = cal._load(REPO / cfg["stage_json"])
    sidecar = cal.load_sidecar(REPO / cfg["stacked_sidecar"])
    groups, labels = value_groups(stage, list(corpus.values()), [stacked[k] for k in p_keys], sidecar)

    units = [(key, s) for key in sorted(groups) for s in sorted(groups[key]) if translatable(s)]
    texts = [source_text(s, labels[key]) for key, s in units]
    print(f"{len(groups)} huecos, {sum(len(v) for v in groups.values())} superficies, "
          f"{len(units)} traducibles")

    engine = make_engine(cfg, "record" if a.translate else "replay")
    candidates = []
    for pivot in cfg["bt_values"]["pivots"]:
        for (key, surface), (out, ok) in zip(units, chain(engine, texts, pivot)):
            option = groups[key][surface]
            if not ok:
                candidates.append(Candidate(*key, surface, option, pivot, out,
                                            label=labels[key], status="rejected", reason="mask_lost"))
                continue
            if labels[key]:
                parts = split_label(out)
                if parts is None:
                    candidates.append(Candidate(*key, surface, option, pivot, out,
                                                label=labels[key], status="rejected", reason="label_lost"))
                    continue
                label_variant, variant = parts
            else:
                label_variant, variant = None, " ".join(out.split())
            candidates.append(Candidate(*key, surface, option, pivot, variant, label_variant,
                                        label=labels[key]))
    if a.translate:
        print(Counter(c.reason for c in candidates if c.status == "rejected"))
        return 0

    # Léxico de dominio: palabras con contenido en <= domain_max_df de los conceptos.
    # Las variantes L2 que pierden alguno se descartan antes del menú (decisión de César).
    max_df = cfg["bt_values"]["domain_max_df"]
    terms = domain_terms(concept_docs(stage), max_df)
    audit.write_atomic(REPO / cfg["bt_values"]["domain_terms"],
                       json.dumps({"max_df": max_df, "n": len(terms), "terms": sorted(terms)},
                                  ensure_ascii=False, indent=1) + "\n")

    final = []
    for key in sorted(groups):
        pending = [c for c in candidates if (c.concept, c.placeholder) == key and c.status == "pending"]
        for c in filter_candidates(groups[key], pending):
            lost = lost_domain_terms(c.surface, c.variant, terms) if c.status == "ok" and not c.label else []
            if lost:
                c = replace(c, status="rejected", reason="domain_term_lost:" + ",".join(lost))
            # reversiones (decisión de César): meter dígitos o volver al valor gold
            rev = reverts(c.surface, c.variant, gold_surface(stage, c)) if c.status == "ok" else None
            final.append(replace(c, status="rejected", reason=f"reverts:{rev}") if rev else c)
        final += [c for c in candidates if (c.concept, c.placeholder) == key and c.status == "rejected"]
    rows = [dict(c.__dict__, uid=c.uid, label=labels[(c.concept, c.placeholder)]) for c in final]
    audit.write_atomic(REPO / cfg["bt_values"]["table"],
                       "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))
    menu = menu_markdown(final, "Variantes de valores y fragmentos para la BT (OE)")
    audit.write_atomic(REPO / cfg["bt_values"]["menu"], menu)
    write_verdicts(cfg, final, menu)
    stats = Counter((c.status, (c.reason or "").split(":")[0]) for c in final)
    print(stats)
    print("superficies con alguna variante aceptable:",
          len({(c.concept, c.placeholder, c.surface) for c in final if c.status == "ok"}), "/", len(units))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
