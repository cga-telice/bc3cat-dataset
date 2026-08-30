"""Transformation-slotted, multi-model proposer for TEMPLATE_PARAPHRASE.

Sprint 38.6 (spec: ``docs/synthetic/sprints/SPRINT_386_DESIGN.md``). A
consumer above the frozen seam, like :mod:`menu_runner`. Where the
Sprint 37 flow asks one model for 10 alternatives in one call (and gets
ten variations of one paraphrase), this module asks **each model** for
**three rounds** of ``n_per_round`` candidates, each round pinned to a
named family of meaning-preserving transformations:

* R1 — voice & frame (active ↔ passive/impersonal *se*, nominal ↔ verbal);
* R2 — architecture (clause reorder, split/merge, move the placeholder block);
* R3 — free restructuring, with R1/R2 keeps' openings forbidden.

Slots are sanitized of the FIEBDC ``\\`` delimiters before rendering
(mini-F1, this type only — its cache is invalidated by this sprint
anyway; the trailing ``\\`` is the proven OEB010$ prompt-echo cause).
Sprint 38.6-B: before prompting, the template's placeholders and
quantities are masked behind ``[[Pn]]``/``[[Qn]]`` sentinels
(:mod:`template_masking`); candidates must carry every sentinel exactly
once (``check_sentinels``) and are un-masked before validation, so
placeholder/quantity preservation is guaranteed by construction.
Candidates are pooled across rounds × models, validated on the RESTORED
text by the full Sprint 38.5/38.6 gate stack (schema + placeholders +
quantities + scaffold-echo + exact dedup + similarity gate), and tagged
with ``proposer_model`` *after* validation.

Owns the ``template_paraphrase`` menu artefacts from Sprint 38.6 on —
``menu_runner`` full passes should use ``--skip-types template_paraphrase``.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence

from . import l2_repr, menu_artefacts, slot_extractor, target_scanner
from .llm_client import HttpLLMClient, LLMConfig, ReplayClient
from .menu_proposer import (
    CandidateProposal,
    CandidateSet,
    _dedupe_non_l1,
    _is_prompt_echo,
    _parse_json_list,
    _similarity_gate,
)
from . import menu_runner
from .menu_runner import ResumingRecordingClient
from .prompts import load_prompt
from .target_scanner import ChapterInventory
from .taxonomy import ModificationType
from .template_masking import check_sentinels, mask_invariants, unmask
from .variant_proposer import _render_prompt, _validate_payload
from utils import config


MTYPE = ModificationType.TEMPLATE_PARAPHRASE
DEFAULT_MODELS: tuple[str, ...] = ("phi4:latest", "qwen2.5:14b")
DEFAULT_TEMPERATURE: float = 0.8
DEFAULT_N_PER_ROUND: int = 3
# Sprint 38.6-B top-up rounds: while a target's gated pool is smaller than
# MIN_CANDIDATES, up to MAX_TOPUP_ROUNDS extra free-restructure rounds
# (tags T1, T2) run per model. The decision depends only on validated
# candidate counts, so replay over recorded transcripts reproduces it.
MIN_CANDIDATES: int = 6
MAX_TOPUP_ROUNDS: int = 2

_EDGE_BACKSLASH_RE = re.compile(r"^\s*\\\s*|\s*\\\s*$")


def _strip_fiebdc(s: str) -> str:
    """Remove leading/trailing FIEBDC ``\\`` field delimiters (and the
    whitespace around them). Interior backslashes never occur in the
    catalog (verified 2026-08-18)."""
    return _EDGE_BACKSLASH_RE.sub("", s).strip()


@dataclass(frozen=True)
class Round:
    tag: str
    instructions: str
    wants_forbidden_openings: bool = False


ROUNDS: tuple[Round, ...] = (
    Round(
        tag="R1",
        instructions=(
            "En esta ronda (R1) cambia la VOZ y el MARCO sintáctico: usa voz "
            "pasiva o impersonal con «se» donde el original es activo (o al "
            "revés), y convierte construcciones nominales en verbales o "
            "viceversa (p. ej. «Ejecución de canalización…» → «Se ejecutará "
            "la canalización…» o «Canalización ejecutada mediante…»)."
        ),
    ),
    Round(
        tag="R2",
        instructions=(
            "En esta ronda (R2) cambia la ARQUITECTURA de la frase: reordena "
            "las cláusulas (adelanta la parte de «incluso…» o «incluido…»), "
            "divide una frase larga en dos o fusiona dos en una, y recoloca "
            "el bloque parentético de variables. No cambies palabras más "
            "allá de lo que exija la reestructuración."
        ),
    ),
    Round(
        tag="R3",
        instructions=(
            "En esta ronda (R3) reescribe libremente, como lo haría OTRO "
            "redactor técnico: cambia a la vez el vocabulario y la "
            "estructura de las frases, manteniendo el significado exacto."
        ),
        wants_forbidden_openings=True,
    ),
)


def _wrap_round(
    rendered_prompt: str,
    round_: Round,
    *,
    n: int,
    forbidden_openings: tuple[str, ...] = (),
) -> str:
    parts = [
        rendered_prompt.rstrip(),
        "",
        f"IMPORTANTE ({round_.tag}): en vez de una única respuesta, devuelve "
        f"una lista JSON de {n} respuestas alternativas distintas. Cada "
        "elemento debe seguir exactamente el esquema JSON descrito arriba.",
        round_.instructions,
        "Conserva todas las variables ($X, $X(%Y)) y todas las cantidades y "
        "unidades exactamente como en el original. No añadas información.",
        "Los tokens [[P1]], [[Q2]], … son marcadores intocables: no los "
        "modifiques, elimines, dupliques ni traduzcas; colócalos donde "
        "correspondan en tu reescritura.",
    ]
    if forbidden_openings:
        listed = "; ".join(f"«{o}…»" for o in forbidden_openings)
        parts.append(
            "Ninguna alternativa puede empezar por: " + listed + "."
        )
    return "\n".join(parts) + "\n"


def _forbidden_openings(payloads: Sequence[dict], words: int = 6) -> tuple[str, ...]:
    seen: list[str] = []
    for p in payloads:
        opening = " ".join(str(p.get("new", "")).split()[:words])
        if opening and opening not in seen:
            seen.append(opening)
    return tuple(seen)


def _sanitized_slots(stage_json: dict, usage) -> tuple[dict, dict[str, str], str]:
    """Sanitized + masked slots for one target.

    Sprint 38.6-B: after stripping the FIEBDC delimiters the template's
    placeholders and quantities are replaced by ``[[Pn]]``/``[[Qn]]``
    sentinels (:func:`mask_invariants`), and the ``placeholders`` slot is
    recomputed as the sentinel list so the prompt's preservation line
    refers to what the model actually sees. Returns ``(slots, mapping,
    true_template)`` where ``true_template`` is the sanitized, un-masked
    template (the ground truth restored into every kept payload). The
    ``concept`` slot is NOT masked — it is context, not rewrite material.
    """
    slots = slot_extractor.extract_slots(
        stage_json, usage.concept_key, MTYPE, usage.slot_extractor_target_id,
    )
    slots["concept"] = _strip_fiebdc(slots["concept"])
    true_template = _strip_fiebdc(slots["template"])
    masked, mapping = mask_invariants(true_template)
    slots["template"] = masked
    slots["placeholders"] = (
        ", ".join(f"[[{k}]]" for k in mapping) if mapping else "(ninguna)"
    )
    return slots, mapping, true_template


def _restore_and_validate(
    raw: list,
    mapping: dict[str, str],
    true_template: str,
    prefix: str,
) -> tuple[list[dict], list[str]]:
    """Sentinel-aware per-candidate validation (replaces
    :func:`menu_proposer._validate_variants` in the diversity flow).

    Per raw element: shape check (dict with a string ``new``), then
    :func:`check_sentinels` on the masked text, then restore —
    ``original`` is overwritten with the known ``true_template`` (echo
    sloppiness must not matter) and ``new`` is unmasked — then the full
    schema validator (:func:`variant_proposer._validate_payload`, which
    still requires ``preserves_meaning``; no defaulting) and the
    scaffold-echo check run on the RESTORED payload. Returns
    ``(keeps, dropped)``; drops are ``f"{prefix} [i] reason"``.
    """
    keeps: list[dict] = []
    dropped: list[str] = []
    for i, elem in enumerate(raw):
        if not isinstance(elem, dict):
            dropped.append(f"{prefix} [{i}] not_a_dict")
            continue
        if not isinstance(elem.get("new"), str):
            dropped.append(f"{prefix} [{i}] missing_key: 'new'")
            continue
        try:
            check_sentinels(elem["new"], mapping)
        except ValueError as err:
            dropped.append(f"{prefix} [{i}] {err}")
            continue
        restored = {
            **elem,
            "original": true_template,
            "new": unmask(elem["new"], mapping),
        }
        try:
            _validate_payload(restored, MTYPE)
        except ValueError as err:
            dropped.append(f"{prefix} [{i}] {err}")
            continue
        if _is_prompt_echo(restored):
            dropped.append(f"{prefix} [{i}] prompt_scaffold_echo")
            continue
        keeps.append(restored)
    return keeps, dropped


def _run_round(
    client,
    model_tag: str,
    round_: Round,
    rendered: str,
    mapping: dict[str, str],
    true_template: str,
    *,
    n: int,
    forbidden_openings: tuple[str, ...],
    dropped_all: list[str],
    skip_reasons: list[str],
) -> list[dict]:
    """One prompt → parse → restore-and-validate round for one model.

    Appends drops / parse skips to the shared per-target lists and
    returns the validated (restored) keeps. Shared by the three base
    ROUNDS and the T1/T2 top-up rounds.
    """
    prompt = _wrap_round(
        rendered, round_, n=n, forbidden_openings=forbidden_openings,
    )
    # complete() stays outside the try: a truncated cache record
    # raises json.JSONDecodeError (⊂ ValueError) from the cache-
    # reading client and must fail loud, not file as a parse skip.
    response = client.complete(prompt)
    try:
        raw = _parse_json_list(response)
    except ValueError as err:
        skip_reasons.append(f"{model_tag}/{round_.tag}: {err}")
        return []
    variants, dropped = _restore_and_validate(
        raw, mapping, true_template,
        prefix=f"{model_tag}/{round_.tag}",
    )
    dropped_all.extend(dropped)
    return variants


def propose_diverse(
    stage_json: dict,
    inventory: ChapterInventory,
    clients: Mapping[str, object],
    *,
    n_per_round: int = DEFAULT_N_PER_ROUND,
) -> dict[tuple, CandidateSet]:
    """Rounds × models pooling for every TEMPLATE_PARAPHRASE target.

    ``clients`` maps a short model tag (goes into ``proposer_model``)
    to an ``LLMClient``. Per model the three ROUNDS run in order; R3's
    prompt embeds the forbidden openings harvested from that model's
    R1+R2 validated keeps (deterministic given recorded transcripts).

    Sprint 38.6-B: if the pooled + deduped + similarity-gated survivors
    number fewer than :data:`MIN_CANDIDATES`, up to
    :data:`MAX_TOPUP_ROUNDS` extra free-restructure rounds (tags ``T1``,
    ``T2``; R3-style instructions) run — one per model per top-up — with
    forbidden openings harvested from that model's keeps plus every
    pooled keep so far, then the pool is re-deduped and re-gated.
    """
    targets = inventory.by_type.get(MTYPE, ())
    prompt_body = load_prompt(MTYPE)
    out: dict[tuple, CandidateSet] = {}
    for target in targets:
        usage = target.usages[0]
        slots, mapping, true_template = _sanitized_slots(stage_json, usage)
        rendered = _render_prompt(prompt_body, slots, MTYPE)
        dropped_all: list[str] = []
        skip_reasons: list[str] = []
        keeps_by_model: dict[str, list[dict]] = {}
        for model_tag, client in clients.items():
            model_keeps: list[dict] = []
            for round_ in ROUNDS:
                openings = (
                    _forbidden_openings(model_keeps)
                    if round_.wants_forbidden_openings else ()
                )
                model_keeps.extend(_run_round(
                    client, model_tag, round_, rendered, mapping,
                    true_template, n=n_per_round,
                    forbidden_openings=openings,
                    dropped_all=dropped_all, skip_reasons=skip_reasons,
                ))
            keeps_by_model[model_tag] = model_keeps

        def _pool_and_gate() -> tuple[list[dict], tuple, tuple[str, ...]]:
            pooled = [
                {**v, "proposer_model": tag}
                for tag, keeps in keeps_by_model.items()
                for v in keeps
            ]
            deduped = _dedupe_non_l1(tuple(pooled), MTYPE)
            gated, gate_reasons = _similarity_gate(deduped, MTYPE)
            return pooled, gated, gate_reasons

        pooled, gated, gate_reasons = _pool_and_gate()
        topups_used = 0
        while len(gated) < MIN_CANDIDATES and topups_used < MAX_TOPUP_ROUNDS:
            topups_used += 1
            topup = Round(
                tag=f"T{topups_used}",
                instructions=ROUNDS[2].instructions,
                wants_forbidden_openings=True,
            )
            for model_tag, client in clients.items():
                openings = _forbidden_openings(
                    keeps_by_model[model_tag] + pooled
                )
                keeps_by_model[model_tag].extend(_run_round(
                    client, model_tag, topup, rendered, mapping,
                    true_template, n=n_per_round,
                    forbidden_openings=openings,
                    dropped_all=dropped_all, skip_reasons=skip_reasons,
                ))
            pooled, gated, gate_reasons = _pool_and_gate()
        # Only the final gate's reasons are logged: intermediate gates over
        # the growing pool would duplicate them (same indices re-checked).
        dropped_all.extend(gate_reasons)
        out[target.dedup_key] = CandidateSet(
            target=target,
            mtype=MTYPE,
            candidates=gated,
            reason=(
                "all_rounds_failed: " + "; ".join(skip_reasons)
                if not gated and skip_reasons and not pooled else None
            ),
            dropped_reasons=tuple(dropped_all),
        )
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _model_store_tag(model: str) -> str:
    # Full model string, not just the name before ":" — "qwen2.5:14b" and
    # "qwen2.5:32b" must map to distinct store dirs / provenance tags.
    return re.sub(r"[^a-z0-9]+", "", model.lower())


def default_store_dir(model: str) -> Path:
    return config.SYNTHETIC_DATA_ROOT / "llm_cache" / f"menu_OEB_tpar_{_model_store_tag(model)}"


def build_clients(
    models: Sequence[str],
    *,
    replay: bool,
    temperature: float = DEFAULT_TEMPERATURE,
) -> dict[str, object]:
    clients: dict[str, object] = {}
    for model in models:
        store = default_store_dir(model)
        tag = _model_store_tag(model)
        if replay:
            clients[tag] = ReplayClient(store)
        else:
            cfg = dataclasses.replace(
                LLMConfig.from_env(), model=model, temperature=temperature,
            )
            clients[tag] = ResumingRecordingClient(HttpLLMClient(cfg), store_dir=store)
    if len(clients) != len(models):
        raise ValueError(f"model tag collision: {models}")
    return clients


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="synthetic.menu_diversity")
    sub = parser.add_subparsers(dest="cmd")
    for cmd in ("run", "replay"):
        p = sub.add_parser(cmd)
        p.add_argument("--stage-json", required=True)
        p.add_argument("--concept-filter", default=None)
        p.add_argument("--concepts", default=None,
                       help="Comma-separated concept keys (pilot mode); overrides --concept-filter.")
        p.add_argument(
            "--models",
            default=",".join(DEFAULT_MODELS),
            help="Comma-separated model names. replay must use the same "
                 "--models and --n-per-round as the original run (both are "
                 "baked into the recorded prompts).",
        )
        p.add_argument("--n-per-round", type=int, default=DEFAULT_N_PER_ROUND)
        p.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
        p.add_argument("--out-machine", default=None)
        p.add_argument("--out-review", default=None)
    args = parser.parse_args(argv)
    if args.cmd not in ("run", "replay"):
        parser.print_usage(sys.stderr)
        return 2

    stage = json.loads(Path(args.stage_json).read_text(encoding="utf-8"))
    if args.concepts:
        wanted = {c.strip() for c in args.concepts.split(",")}
        concept_filter = lambda k, w=frozenset(wanted): k in w
    elif args.concept_filter:
        concept_filter = lambda k, p=args.concept_filter: k.startswith(p)
    else:
        concept_filter = None

    stage_conv, _ = l2_repr.list_to_formula(stage, include_conditional=True)
    inventory = target_scanner.scan_chapter(
        stage_conv, concept_filter=concept_filter, apply_l2_conversion=False,
    )
    clients = build_clients(
        [m.strip() for m in args.models.split(",")],
        replay=(args.cmd == "replay"),
        temperature=args.temperature,
    )
    sets = propose_diverse(stage_conv, inventory, clients, n_per_round=args.n_per_round)
    machine_dir = Path(args.out_machine) if args.out_machine else menu_runner.default_out_machine_dir()
    review_dir = Path(args.out_review) if args.out_review else menu_runner.default_out_review_dir()
    menu_artefacts.write_menu(
        inventory, {MTYPE: sets},
        machine_dir=machine_dir, review_dir=review_dir, chapter_label="OEB (diversity)",
    )
    n_c = sum(len(s.candidates) for s in sets.values())
    n_skip = sum(1 for s in sets.values() if s.reason)
    n_empty = sum(1 for s in sets.values() if not s.candidates and not s.reason)
    sys.stdout.write(
        f"template_paraphrase diversity: {len(sets)} targets, {n_c} candidates, "
        f"{n_skip} skipped, {n_empty} empty\n"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
