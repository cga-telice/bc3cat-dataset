"""Regenerate the template_paraphrase menus at high depth (menu_diversity, phi4+qwen).

template_paraphrase is owned by :mod:`synthetic.menu_diversity` (rounds x models,
restore-and-validate). The original OE run yielded ~3.4 candidates/target and left
4 concepts without a valid TEXTO paraphrase. This driver re-runs the diversity
generator for every template_paraphrase target with boosted yield parameters
(``MIN_CANDIDATES`` / ``MAX_TOPUP_ROUNDS`` / ``n_per_round``) and rewrites ONLY the
``template_paraphrase`` menu (write_menu skips every type not passed, so the other
menus are untouched).

Per-model LLM cache (ResumingRecordingClient) lives under a SHORT path
(``data/synthetic/llm_cache/OE_tpar_<model>``) so a multi-hour run resumes from
cache after any interruption and avoids the Windows MAX_PATH limit. The menu file
is written once, only on full success.

Run (PYTHONPATH=src, Ollama up):
  python scripts/regen_template_paraphrase.py --stage-json <OE_stage.json>
Then: auto_verdicts_v2.py, then regenerate the corpora.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from synthetic import l2_repr, menu_artefacts, menu_diversity as MD, target_scanner  # noqa: E402
from synthetic.menu_runner import ResumingRecordingClient  # noqa: E402
from synthetic.llm_client import HttpLLMClient, LLMConfig  # noqa: E402
from utils import config  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-json", required=True)
    ap.add_argument("--concept-filter", default=None, help='e.g. "OEB" (default: all)')
    ap.add_argument("--min-candidates", type=int, default=10)
    ap.add_argument("--max-topup", type=int, default=6)
    ap.add_argument("--n-per-round", type=int, default=4)
    ap.add_argument("--models", default="phi4:latest,qwen2.5:14b")
    ap.add_argument("--machine-dir", default="data/synthetic/menus_OE")
    ap.add_argument("--review-dir", default="data/synthetic/review_OE")
    ap.add_argument("--cache-root", default="data/synthetic/llm_cache")
    ap.add_argument("--chapter-label", default="OE")
    a = ap.parse_args()

    MD.MIN_CANDIDATES = a.min_candidates
    MD.MAX_TOPUP_ROUNDS = a.max_topup

    stage = json.loads(Path(a.stage_json).read_text(encoding="utf-8"))
    stage_p, _ = l2_repr.list_to_formula(stage, include_conditional=True)
    cf = (lambda k, p=a.concept_filter: k.startswith(p)) if a.concept_filter else None
    inv = target_scanner.scan_chapter(stage_p, concept_filter=cf, apply_l2_conversion=False)

    clients = {}
    for tag in [m.strip() for m in a.models.split(",") if m.strip()]:
        cfg = LLMConfig(base_url=config.LLM_BASE_URL, model=tag,
                        api_key_env=config.LLM_API_KEY_ENV, timeout=300.0,
                        max_retries=4, temperature=MD.DEFAULT_TEMPERATURE)
        store = Path(a.cache_root) / ("OE_tpar_" + tag.replace(":", "").replace(".", ""))
        store.mkdir(parents=True, exist_ok=True)
        clients[tag] = ResumingRecordingClient(HttpLLMClient(cfg), store_dir=store)

    ntar = len(inv.by_type.get(MD.MTYPE, ()))
    print(f"template_paraphrase targets: {ntar} | models={list(clients)} | "
          f"MIN={MD.MIN_CANDIDATES} TOPUP={MD.MAX_TOPUP_ROUNDS} "
          f"n_per_round={a.n_per_round}", flush=True)

    res = MD.propose_diverse(stage_p, inv, clients, n_per_round=a.n_per_round)

    reps = menu_artefacts.write_menu(
        inv, {MD.MTYPE: res}, machine_dir=Path(a.machine_dir),
        review_dir=Path(a.review_dir), chapter_label=a.chapter_label)

    counts = sorted(len(cs.candidates) for cs in res.values())
    tot = sum(counts)
    empty = sum(1 for c in counts if c == 0)
    print(f"DONE: {len(res)} targets | {tot} candidates | mean {tot/max(1,len(res)):.1f}/target "
          f"| min {counts[0]} max {counts[-1]} | empty targets {empty}")
    for r in reps:
        print(" wrote", r.machine_path, "->", r.n_candidates_total, "candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
