"""Calibración del verificador de caracterización (BT, opción A, T2).

Cinco pruebas sobre una muestra estratificada de hojas de ``OE_texto.json``:

* **positivos** — TEXTO original: todos los ejes de R(C) = gold (≥ 99,5 %);
* **discriminación** — TEXTO de una hermana a la menor distancia en tokens
  que difiere en un solo eje renderizado: su propio valor (≥ 99 %);
* **ablación** — TEXTO sin la superficie de un eje renderizado por
  placeholder directo: ``no_determinable`` (≥ 99 %);
* **derivas** — consultas STACKED con una reescritura visible del tipo
  «adosada → empotrada / a ras» o «con topo → topografía / perfilado»:
  rechazo por el verificador completo (100 %);
* **estabilidad** — la reproducción desde caché da lo mismo (100 %).

Los extractores corren por fases, nunca a la vez en GPU:

  PYTHONPATH=src python scripts/calibrate_characterization.py --extract phi4:latest
  PYTHONPATH=src python scripts/calibrate_characterization.py --extract qwen2.5:14b
  PYTHONPATH=src python scripts/calibrate_characterization.py --report

``--extract`` rellena la caché ``data/synthetic/llm_cache/characterization_<modelo>/``
(primero caché, si no, llamada). ``--report`` solo lee la caché
(``ReplayClient``) y escribe ``docs/synthetic/bt/OE_characterization_calibration.md``
más un JSON con todas las respuestas.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import zlib
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import yaml  # noqa: E402

from synthetic.characterization import (  # noqa: E402
    NO_DET,
    CharacterizationContext,
    ExtractionError,
    LLMExtractor,
)

_TOKEN_RE = re.compile(r"\$([A-Za-z]\w*)")
# Derivas conocidas: (lo que desaparece, lo que aparece en su lugar).
_DRIFTS = (
    (re.compile(r"\badosad", re.I), re.compile(r"empotr|incrust|integr|a ras|a nivel", re.I)),
    (re.compile(r"\bcon topo\b", re.I), re.compile(r"topogra|perfil", re.I)),
)


def is_drift(record: Mapping) -> bool:
    """Reescritura no-plantilla que quita «adosada» o «con topo» y mete en
    su lugar «empotrada / a ras…» o «topografía / perfilado»."""
    if record.get("layer") == "template":
        return False
    return any(old.search(record["original"]) and not old.search(record["new"])
               and new.search(record["new"]) for old, new in _DRIFTS)


# ---------------------------------------------------------------------------
# Piezas puras
# ---------------------------------------------------------------------------

def token_distance(a: str, b: str) -> int:
    """Levenshtein sobre tokens separados por espacios."""
    x, y = a.split(), b.split()
    prev = list(range(len(y) + 1))
    for i, tx in enumerate(x, 1):
        cur = [i]
        for j, ty in enumerate(y, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (tx != ty)))
        prev = cur
    return prev[-1]


def _value_re(value: str) -> re.Pattern:
    # palabra completa; "1" no casa dentro de "1,60" ni de "HE-1"
    return re.compile(rf"(?<![\w.,\-]){re.escape(value)}(?!\w|[.,]\d)")


def ablate(text: str, value: str, expected: int) -> Optional[str]:
    """Quita las ``expected`` apariciones de ``value``; ``None`` si no hay
    exactamente esas (el valor también está en otra parte del texto)."""
    pat = _value_re(value)
    if not value or len(pat.findall(text)) != expected:
        return None
    out = pat.sub("", text)
    out = re.sub(r"[ \t]+([.,;:])", r"\1", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out.strip()


@dataclass(frozen=True)
class Case:
    kind: str                    # positive | discrimination | ablation | drift
    text: str
    gold: str
    axis: Optional[str] = None
    base: Optional[str] = None   # discriminación: la hoja muestreada
    distance: Optional[int] = None
    query_key: Optional[str] = None
    records: tuple = field(default=(), compare=False)


def _rng(seed: int, key: str) -> random.Random:
    return random.Random(seed ^ zlib.crc32(key.encode("utf-8")))


def build_cases(ctx: CharacterizationContext, *, seed: int, per_concept: int,
                stacked: Sequence[Mapping], sidecar: Mapping[str, Sequence[Mapping]]) -> list[Case]:
    by_concept: dict[str, list[str]] = {}
    for key, leaf in ctx.leaves.items():
        by_concept.setdefault(leaf.concept, []).append(key)

    cases: list[Case] = []
    for concept_key in sorted(by_concept):
        concept = ctx.concepts[concept_key]
        keys = sorted(by_concept[concept_key])
        rng = _rng(seed, concept_key)
        sample = sorted(rng.sample(keys, min(per_concept, len(keys))))
        rendered = concept.rendered
        tokens = Counter(_TOKEN_RE.findall(concept.texto_template))
        direct = [a for a in rendered if tokens[a]]
        for key in sample:
            leaf = ctx.leaves[key]
            cases.append(Case("positive", leaf.text, key))

            # discriminación: hermana en un solo eje renderizado, la más cercana
            best = None
            for other in keys:
                o = ctx.leaves[other]
                diff = [a for a in leaf.options if leaf.options[a] != o.options[a]]
                if len(diff) != 1 or diff[0] not in rendered or o.text == leaf.text:
                    continue
                d = token_distance(leaf.text, o.text)
                cand = (d, zlib.crc32(f"{seed}|{other}".encode()), other, diff[0])
                best = min(best, cand) if best else cand
            if best:
                d, _, other, axis = best
                cases.append(Case("discrimination", ctx.leaves[other].text, other,
                                  axis=axis, base=key, distance=d))

            # ablación: un eje con placeholder directo, en orden rotado
            if direct:
                start = _rng(seed, key).randrange(len(direct))
                for axis in direct[start:] + direct[:start]:
                    value = concept.axis(axis).values[ord(leaf.options[axis]) - 97]
                    text = ablate(leaf.text, value, tokens[axis])
                    if text is not None:
                        cases.append(Case("ablation", text, key, axis=axis))
                        break

    for q in stacked:
        gold = q["gold_item_key"]
        leaf = ctx.leaves.get(gold)
        if leaf is None:
            continue
        recs = sidecar.get(q["item_key"], ())
        visible = [r for r in recs if ctx.surface.shows_record(r, leaf.concept, gold)]
        if any(is_drift(r) for r in visible):
            cases.append(Case("drift", q["text"], gold, query_key=q["item_key"],
                              records=tuple(recs)))
    return cases


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------

def _gold_idx(ctx, key, axis) -> int:
    return ord(ctx.leaves[key].options[axis]) - 96


def evaluate(ctx, cases: Sequence[Case], extractors: Sequence) -> dict:
    """Aplica los extractores a cada caso y resume por prueba."""
    rows = []
    for c in cases:
        concept = ctx.concepts[ctx.leaves[c.gold].concept]
        row = {"case": {k: v for k, v in asdict(c).items() if k != "records"}}
        if c.kind == "drift":
            r = ctx.check(c.text, c.gold, extractors=extractors,
                          records=list(c.records), query_key=c.query_key)
            row["check"] = {"ok": r.ok, "gate": r.gate, "axis": r.axis, "reason": r.reason}
            rows.append(row)
            continue
        answers = {}
        for ex in extractors:
            try:
                answers[ex.name] = ex.extract(c.text, concept)
            except ExtractionError as err:
                answers[ex.name] = {"error": str(err)}
        row["answers"] = answers
        rows.append(row)
    return {"rows": rows, "summary": summarize(ctx, rows)}


def summarize(ctx, rows) -> dict:
    s = {k: Counter() for k in ("positive", "discrimination", "ablation", "drift")}
    nonr = Counter()
    per_extractor = {k: Counter() for k in ("positive", "ablation")}
    failures: dict[str, list] = {k: [] for k in s}
    for row in rows:
        c = row["case"]
        kind = c["kind"]
        if kind == "drift":
            s[kind]["n"] += 1
            if not row["check"]["ok"]:
                s[kind]["ok"] += 1
            else:
                failures[kind].append(c["query_key"])
            continue
        answers = row["answers"]
        bad = [n for n, a in answers.items() if "error" in a]
        concept = ctx.concepts[ctx.leaves[c["gold"]].concept]
        if kind == "positive":
            for a in concept.rendered:
                allowed = ctx.allowed(c["gold"], a)
                s[kind]["n"] += 1
                ok = not bad and all(ans[a] in allowed for ans in answers.values())
                s[kind]["ok"] += ok
                for name, ans in answers.items():
                    per_extractor[kind][(name, "n")] += 1
                    per_extractor[kind][(name, "ok")] += ("error" not in ans and ans[a] in allowed)
                if not ok:
                    failures[kind].append([c["gold"], a, answers])
            for a in concept.not_rendered:
                nonr["n"] += 1
                nonr["ok"] += not bad and all(ans[a] == NO_DET for ans in answers.values())
        elif kind == "discrimination":
            a = c["axis"]
            allowed = ctx.allowed(c["gold"], a)
            s[kind]["n"] += 1
            ok = not bad and all(ans[a] in allowed for ans in answers.values())
            s[kind]["ok"] += ok
            s[kind][f"d{c['distance']}"] += 1
            if not ok:
                failures[kind].append([c["gold"], a, c["distance"], answers])
        elif kind == "ablation":
            a = c["axis"]
            gold = _gold_idx(ctx, c["gold"], a)
            s[kind]["n"] += 1
            both_zero = not bad and all(ans[a] == NO_DET for ans in answers.values())
            not_accepted = bad or not all(ans[a] == gold for ans in answers.values())
            s[kind]["ok"] += both_zero
            s[kind]["not_accepted"] += not_accepted
            for name, ans in answers.items():
                per_extractor[kind][(name, "n")] += 1
                per_extractor[kind][(name, "ok")] += ("error" not in ans and ans[a] == NO_DET)
            if not both_zero:
                failures[kind].append([c["gold"], a, answers])
    out = {k: dict(v) for k, v in s.items()}
    out["non_rendered_zero"] = dict(nonr)
    out["per_extractor"] = {k: {f"{n}|{m}": v for (n, m), v in d.items()}
                            for k, d in per_extractor.items()}
    out["failures"] = failures
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_context(cfg: dict) -> CharacterizationContext:
    h = REPO / cfg["handoff_dir"]
    return CharacterizationContext.load(
        _load(REPO / cfg["stage_json"]), _load(h / "OE_texto.json"),
        d031_groups=_load(h / "OE_duplicate_texto_groups.json"),
        exclusions=[_load(h / "OE_P7_test_exclusion.json"), _load(h / "OE_P8_test_exclusion.json")],
        concept_schema=_load(h / "OE_concept_schema.json"),
    )


def load_sidecar(path: Path) -> dict:
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        out[r["item_key"]] = r["modifications"]
    return out


def cache_dir(cfg: dict, model: str) -> Path:
    tag = re.sub(r"[^a-z0-9]", "", model.lower())
    return REPO / cfg["cache_root"] / f"characterization_{tag}"


def make_extractor(cfg: dict, model: str, replay: bool):
    from synthetic.llm_client import HttpLLMClient, LLMConfig, ReplayClient
    from synthetic.menu_runner import ResumingRecordingClient

    store = cache_dir(cfg, model)
    if replay:
        client = ReplayClient(store_dir=store)
    else:
        base = LLMConfig.from_env()
        conf = LLMConfig(base_url=cfg["llm_base_url"], model=model,
                         api_key_env=base.api_key_env, timeout=float(cfg.get("llm_timeout", 300)),
                         max_retries=base.max_retries, backoff_base=base.backoff_base,
                         temperature=0.0)
        store.mkdir(parents=True, exist_ok=True)
        client = ResumingRecordingClient(HttpLLMClient(conf), store_dir=store)
    return LLMExtractor(model, client)


def _pct(ok, n):
    return f"{100 * ok / n:.2f} %" if n else "—"


def write_report(cfg, summary, cases, path: Path, stability: bool, digest: str) -> None:
    th = cfg["calibration"]["thresholds"]
    s = summary

    def line(name, key, thr, ok, n):
        rate = ok / n if n else 0.0
        verdict = "cumple" if n and rate >= thr else "**no cumple**"
        return f"| {name} | {n} | {ok} | {_pct(ok, n)} | ≥ {thr * 100:g} % | {verdict} |"

    pos, dis, abl, dri = (s.get(k, {}) for k in ("positive", "discrimination", "ablation", "drift"))
    lines = [
        "# Calibración del verificador de caracterización (OE)",
        "",
        f"Extractores: {', '.join(cfg['extractors'])}, temperatura 0, JSON estricto. "
        f"Semilla {cfg['seed']}, {cfg['calibration']['per_concept']} hojas por concepto. "
        f"sha256 de los casos: `{digest}`.",
        "",
        "| Prueba | Casos | Aciertos | Tasa | Umbral | Resultado |",
        "|---|---:|---:|---:|---:|---|",
        line("Positivos (ejes de R(C))", "positive", th["positives"], pos.get("ok", 0), pos.get("n", 0)),
        line("Discriminación (hermanas)", "discrimination", th["discrimination"], dis.get("ok", 0), dis.get("n", 0)),
        line("Ablación (los dos dan 0)", "ablation", th["ablation"], abl.get("ok", 0), abl.get("n", 0)),
        line("Derivas conocidas (rechazo)", "drift", th["drift"], dri.get("ok", 0), dri.get("n", 0)),
        f"| Estabilidad (reproducción) | {len(cases)} | {len(cases) if stability else 0} | "
        f"{'100 %' if stability else '—'} | 100 % | {'cumple' if stability else '**no cumple**'} |",
        "",
        "Señales secundarias:",
        "",
        f"- Ejes fuera de R(C) a 0 en los positivos (los dos extractores): "
        f"{s['non_rendered_zero'].get('ok', 0)}/{s['non_rendered_zero'].get('n', 0)} "
        f"({_pct(s['non_rendered_zero'].get('ok', 0), s['non_rendered_zero'].get('n', 0))}).",
        f"- Ablación: el par no acepta el valor gold en "
        f"{abl.get('not_accepted', 0)}/{abl.get('n', 0)} ({_pct(abl.get('not_accepted', 0), abl.get('n', 0))}).",
        f"- Discriminación por distancia en tokens: "
        + ", ".join(f"{k[1:]} token(s): {v}" for k, v in sorted(dis.items()) if k.startswith("d")) + ".",
        "",
        "Por extractor:",
        "",
        "| Prueba | Extractor | Aciertos | Tasa |",
        "|---|---|---:|---:|",
    ]
    for kind, d in s["per_extractor"].items():
        for name in cfg["extractors"]:
            n, ok = d.get(f"{name}|n", 0), d.get(f"{name}|ok", 0)
            lines.append(f"| {kind} | {name} | {ok}/{n} | {_pct(ok, n)} |")
    lines += ["", "Fallos por prueba (primeros 15; todos en el JSON):", ""]
    for kind, fails in s["failures"].items():
        lines.append(f"- **{kind}**: {len(fails)}")
        for f in fails[:15]:
            lines.append(f"  - `{json.dumps(f, ensure_ascii=False)}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default="configs/synthetic/bt_OE.yaml")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--extract", metavar="MODELO")
    g.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=None, help="solo los N primeros casos (prueba)")
    a = ap.parse_args(argv)

    cfg = yaml.safe_load((REPO / a.config).read_text(encoding="utf-8"))
    ctx = load_context(cfg)
    h = REPO / cfg["handoff_dir"]
    cases = build_cases(ctx, seed=cfg["seed"], per_concept=cfg["calibration"]["per_concept"],
                        stacked=_load(h / "OE_stacked_texto.json"),
                        sidecar=load_sidecar(REPO / cfg["stacked_sidecar"]))
    if a.limit:
        cases = cases[:a.limit]
    digest = hashlib.sha256(json.dumps(
        [{k: v for k, v in asdict(c).items() if k != "records"} for c in cases],
        ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    print(f"{len(cases)} casos {Counter(c.kind for c in cases)} sha256={digest[:12]}")

    if a.extract:
        ex = make_extractor(cfg, a.extract, replay=False)
        texts = []
        for c in cases:
            texts.append(c.text)
        concept_of = {c.text: ctx.concepts[ctx.leaves[c.gold].concept] for c in cases}
        for i, text in enumerate(dict.fromkeys(texts), 1):
            try:
                ex.extract(text, concept_of[text])
            except ExtractionError:
                pass  # la respuesta queda en caché; el informe la cuenta como error
            if i % 100 == 0:
                print(f"  {i}/{len(concept_of)}", flush=True)
        return 0

    extractors = [make_extractor(cfg, m, replay=True) for m in cfg["extractors"]]
    result = evaluate(ctx, cases, extractors)
    again = evaluate(ctx, cases, [make_extractor(cfg, m, replay=True) for m in cfg["extractors"]])
    stability = json.dumps(result, sort_keys=True) == json.dumps(again, sort_keys=True)
    out_json = REPO / cfg["calibration"]["output_json"]
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(cfg, result["summary"], cases, REPO / cfg["calibration"]["report"], stability, digest)
    print(json.dumps({k: v for k, v in result["summary"].items() if k != "failures"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
