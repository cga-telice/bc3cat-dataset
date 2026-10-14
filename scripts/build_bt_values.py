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
import calibrate_characterization as cal  # noqa: E402
from synthetic.back_translation import CachedEngine, MarianEngine  # noqa: E402
from synthetic.bt_masking import MARKER_RE, MaskError, check_masks, mask_surface, unmask_surface  # noqa: E402
from synthetic.bt_values import (  # noqa: E402
    Candidate,
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

    final = []
    for key in sorted(groups):
        pending = [c for c in candidates if (c.concept, c.placeholder) == key and c.status == "pending"]
        final += filter_candidates(groups[key], pending)
        final += [c for c in candidates if (c.concept, c.placeholder) == key and c.status == "rejected"]
    rows = [dict(c.__dict__, uid=c.uid, label=labels[(c.concept, c.placeholder)]) for c in final]
    audit.write_atomic(REPO / cfg["bt_values"]["table"],
                       "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows))
    audit.write_atomic(REPO / cfg["bt_values"]["menu"],
                       menu_markdown(final, "Variantes de valores y fragmentos para la BT (OE)"))
    stats = Counter((c.status, c.reason) for c in final)
    print(stats)
    print("superficies con alguna variante aceptable:",
          len({(c.concept, c.placeholder, c.surface) for c in final if c.status == "ok"}), "/", len(units))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
