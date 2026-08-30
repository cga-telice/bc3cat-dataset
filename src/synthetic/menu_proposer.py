"""N-candidate proposer for the menu-first Stage-A flow.

Sprint 37 (F3-prep-1-B). A *consumer above the frozen seam* (like
:mod:`spike` and :mod:`f1_pilot`) that batches LLM calls at the same
granularity as the existing prompts (one call per axis for L1, per
fragment for L2, per template for L3, per concept for NEW_PARAM) and
decomposes each response into per-:class:`UniqueTarget`
:class:`CandidateSet` records.

Key ideas
---------

* **Prompt bodies stay byte-identical.** Every one of the 13 prompt
  files is loaded unchanged via :func:`synthetic.prompts.load_prompt`;
  the multi-candidate instruction is a single f-string appended at
  runtime by :func:`_wrap_multi_candidate`. If the flow ever reverts to
  single-candidate mode we delete one f-string.
* **Response shape is uniformly list-wrapped.** For every modification
  type the LLM is asked for a JSON list of ``n`` objects, each following
  the existing per-type schema. The parser strict-validates each element
  against :func:`variant_proposer._validate_payload`; failures drop only
  the offending element.
* **L1 batching.** The existing L1 prompt covers all values on an axis
  in one call, so we call the LLM once per axis and decompose the
  response into per-value :class:`CandidateSet` records. This is the
  cheapest shape that still gives per-value review granularity — one
  LLM call spawns ``len(axis.values)`` review headings.
* **Inter-candidate dedup at parse time.** Near-duplicate candidates
  (whitespace-normalised) get collapsed so phi4 hedging with identical
  strings does not waste review slots.

Skip semantics mirror the existing pipeline:

* Whole-target skip: the LLM returned a non-list top level, an empty
  list, or malformed JSON even after one retry — recorded on the
  :class:`CandidateSet` as ``reason`` starting with
  ``malformed_list_after_retry:`` (distinct from C2's per-item prefix).
* Per-item skip: an individual list element failed
  :func:`variant_proposer._validate_payload` — the element is dropped
  and the failure detail is recorded in ``dropped_reasons``.

Does NOT own:

* the target scan / dedup — that's :mod:`target_scanner`;
* writing the menu artefacts — that's :mod:`menu_artefacts`;
* the review parser or the sampler — Sprint 38 / 39.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from . import slot_extractor
from .llm_proposer import LLMClient, _extract_json_object
from .prompts import load_prompt
from .target_scanner import ChapterInventory, TargetUsage, UniqueTarget
from .taxonomy import ModificationType
from .variant_proposer import EXPECTED_SLOTS, _render_prompt, _validate_payload


DEFAULT_N_CANDIDATES: int = 10

# Sprint 38.5. Low-entropy rewrite types: the model's 10 alternatives are
# near-duplicates (omission differs by a connective, reorder by which clause
# moves, unit/number rewrites have 2-3 legitimate forms). Keep the request at
# ``n`` (prompt text is cache-keyed) but present only the first ``cap`` after
# dedup — candidates are ordered best→worst by the prompt contract.
MENU_CAP_BY_TYPE: dict[ModificationType, int] = {
    ModificationType.OMISSION: 3,
    ModificationType.REORDER: 3,
    ModificationType.NUM_TO_TEXT: 3,
    ModificationType.UNIT_CONVERSION: 3,
    ModificationType.UNIT_EXPANSION: 3,
}


def _cap_candidates(
    candidates: tuple["CandidateProposal", ...],
    mtype: ModificationType,
) -> tuple["CandidateProposal", ...]:
    cap = MENU_CAP_BY_TYPE.get(mtype)
    return candidates if cap is None else candidates[:cap]


# Sprint 38.6. Exact-duplicate dedup misses "same sentence, one word
# swapped" — the dominant dullness mode measured on the Sprint 38 menus
# (template_paraphrase mutual similarity 0.77). Greedy first-kept-wins:
# candidates are ordered best→worst, so the earlier candidate survives.
SIMILARITY_THRESHOLD: float = 0.8


def _token_set(s: str) -> frozenset[str]:
    return frozenset(_normalise(s).split())


def _similarity_gate(
    candidates: tuple["CandidateProposal", ...],
) -> tuple[tuple["CandidateProposal", ...], tuple[str, ...]]:
    """Drop candidates whose token-Jaccard against an already-kept
    candidate exceeds :data:`SIMILARITY_THRESHOLD`. Returns
    ``(kept, drop_reasons)``; reasons use the candidate's index in the
    incoming tuple."""
    kept: list[CandidateProposal] = []
    kept_tokens: list[frozenset[str]] = []
    reasons: list[str] = []
    for i, cand in enumerate(candidates):
        text = cand.payload.get("new") or cand.payload.get("new_axis_label") or ""
        toks = _token_set(str(text))
        is_dup = False
        for kt in kept_tokens:
            union = toks | kt
            if union and len(toks & kt) / len(union) > SIMILARITY_THRESHOLD:
                is_dup = True
                break
        if is_dup:
            reasons.append(f"[{i}] near_duplicate_of_kept")
            continue
        kept.append(cand)
        kept_tokens.append(toks)
    return tuple(kept), tuple(reasons)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CandidateProposal:
    """One reviewable candidate rewrite of a :class:`UniqueTarget`.

    ``payload`` carries the exact fields the sampler will consume later:
    for L1 it is ``{"original": <value>, "new": <alternative>}``; for L2
    and L3 it mirrors the existing per-type variant schema; for
    NEW_PARAM it is the full ``{new_axis_label, var_definition,
    template_patch, values}`` dict.
    """

    payload: dict


@dataclass(frozen=True)
class CandidateSet:
    """The pool of candidate rewrites for one :class:`UniqueTarget`.

    Attributes
    ----------
    target
        The :class:`UniqueTarget` this menu belongs to.
    mtype
        The modification type (same enum value carried by the target's
        family).
    candidates
        Zero-or-more surviving :class:`CandidateProposal` records,
        already deduplicated by normalised text, and, for the types
        listed in :data:`MENU_CAP_BY_TYPE`, truncated to that cap
        (Sprint 38.5) — the tuple can be shorter than the number of
        survivors.
    reason
        Non-``None`` iff the whole target was skipped (malformed list
        after retry / empty list / etc.); prefixed with a stable
        machine-readable slug so downstream reporting can group them.
    dropped_reasons
        Per-element schema-validation errors for elements that were
        parsed but rejected. Ordered as they appeared in the response;
        used by :mod:`menu_artefacts` to note "3 of 10 dropped" in the
        artefact's tally without exposing internals.
    """

    target: UniqueTarget
    mtype: ModificationType
    candidates: tuple[CandidateProposal, ...]
    reason: Optional[str] = None
    dropped_reasons: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def propose_type(
    stage_json: dict,
    inventory: ChapterInventory,
    mtype: ModificationType,
    client: LLMClient,
    *,
    n: int = DEFAULT_N_CANDIDATES,
) -> dict[tuple, CandidateSet]:
    """Populate every :class:`UniqueTarget` in
    ``inventory.by_type[mtype]`` with a :class:`CandidateSet`.

    LLM calls are batched at the existing prompt's natural granularity:

    * L1 — one call per axis (per first-usage concept); the response is
      decomposed into per-value :class:`CandidateSet` records.
    * L2 / L3 / NEW_PARAM — one call per target.

    Returns a ``dict`` keyed by :attr:`UniqueTarget.dedup_key`, one entry
    per target in the inventory (skipped targets have empty
    ``candidates`` and a non-``None`` ``reason``).
    """
    targets = inventory.by_type.get(mtype, ())
    if not targets:
        return {}
    if _is_l1(mtype):
        return _propose_l1(stage_json, targets, mtype, client, n=n)
    return _propose_single_target(stage_json, targets, mtype, client, n=n)


# ---------------------------------------------------------------------------
# L1 batched path
# ---------------------------------------------------------------------------


def _propose_l1(
    stage_json: dict,
    targets: tuple[UniqueTarget, ...],
    mtype: ModificationType,
    client: LLMClient,
    *,
    n: int,
) -> dict[tuple, CandidateSet]:
    """One LLM call per axis; response decomposed to per-value sets."""
    by_axis = _group_l1_targets_by_axis(targets)
    out: dict[tuple, CandidateSet] = {}
    for _batch_key, (representative_usage, axis_targets) in sorted(by_axis.items()):
        variants, reason, dropped = _call_and_validate(
            stage_json, representative_usage, mtype, client, n=n,
        )
        for target in axis_targets:
            _, value_norm = target.dedup_key
            gated, gate_reasons = _similarity_gate(
                _extract_l1_candidates_for_value(variants, value_norm),
            )
            candidates = _cap_candidates(gated, mtype)
            out[target.dedup_key] = CandidateSet(
                target=target,
                mtype=mtype,
                candidates=candidates,
                reason=reason if not variants else None,
                dropped_reasons=dropped + gate_reasons,
            )
    return out


def _group_l1_targets_by_axis(
    targets: tuple[UniqueTarget, ...],
) -> dict[tuple[str, str, object], tuple[TargetUsage, list[UniqueTarget]]]:
    """Group per-value L1 targets into their axis batches.

    Batch key is ``(axis_label, first_usage.concept_key,
    first_usage.slot_extractor_target_id)`` — one call per axis + first
    concept + axis key. All values on the same axis of the same concept
    share the call. ``first`` = ``usages[0]`` after :mod:`target_scanner`
    sorted by ``concept_key`` (deterministic).

    Returns a mapping ``batch_key -> (representative_usage, targets)``.
    """
    out: dict[tuple[str, str, object], tuple[TargetUsage, list[UniqueTarget]]] = {}
    for t in targets:
        axis_label, _value_norm = t.dedup_key
        first = t.usages[0]
        key = (axis_label, first.concept_key, first.slot_extractor_target_id)
        if key not in out:
            out[key] = (first, [])
        out[key][1].append(t)
    # Deterministic per-batch value order.
    for _rep, batch in out.values():
        batch.sort(key=lambda tt: tt.dedup_key)
    return out


def _extract_l1_candidates_for_value(
    variants: tuple[dict, ...],
    value_norm: str,
) -> tuple[CandidateProposal, ...]:
    """From ``n`` validated L1 variants (each a full
    ``{"synonyms": [...]}`` payload), pull the ``new`` field belonging
    to ``value_norm`` and dedupe near-duplicates.

    ``value_norm`` is :func:`target_scanner._norm`-normalised (whitespace
    only, case preserved). Match ``entry["original"]`` with the same
    normaliser so the LLM's exact-echo pins to the same dedup key.
    """
    seen: set[str] = set()
    out: list[CandidateProposal] = []
    for variant in variants:
        entries = None
        # All six L1 types share the same list-of-pairs shape; the dict
        # key varies (``synonyms`` vs ``numerals``) — try both.
        for key in ("synonyms", "numerals"):
            if key in variant and isinstance(variant[key], list):
                entries = variant[key]
                break
        if entries is None:
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if _ws_norm(str(entry.get("original", ""))) != value_norm:
                continue
            new_val = entry.get("new")
            if not isinstance(new_val, str):
                continue
            norm = _normalise(new_val)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            out.append(CandidateProposal(payload={
                "original": entry["original"],
                "new": new_val,
            }))
            break  # one candidate per variant per value
    return tuple(out)


# ---------------------------------------------------------------------------
# Per-target path (L2 / L3 / NEW_PARAM)
# ---------------------------------------------------------------------------


def _propose_single_target(
    stage_json: dict,
    targets: tuple[UniqueTarget, ...],
    mtype: ModificationType,
    client: LLMClient,
    *,
    n: int,
) -> dict[tuple, CandidateSet]:
    out: dict[tuple, CandidateSet] = {}
    for target in targets:
        first = target.usages[0]
        variants, reason, dropped = _call_and_validate(
            stage_json, first, mtype, client, n=n,
        )
        if variants:
            gated, gate_reasons = _similarity_gate(_dedupe_non_l1(variants, mtype))
            candidates = _cap_candidates(gated, mtype)
            out[target.dedup_key] = CandidateSet(
                target=target,
                mtype=mtype,
                candidates=candidates,
                reason=None,
                dropped_reasons=dropped + gate_reasons,
            )
        else:
            out[target.dedup_key] = CandidateSet(
                target=target,
                mtype=mtype,
                candidates=(),
                reason=reason,
                dropped_reasons=dropped,
            )
    return out


def _dedupe_non_l1(
    variants: tuple[dict, ...],
    mtype: ModificationType,
) -> tuple[CandidateProposal, ...]:
    """For L2 / L3 / NEW_PARAM each variant *is* a candidate; dedupe by
    the field(s) that identify uniqueness."""
    seen: set[tuple] = set()
    out: list[CandidateProposal] = []
    for variant in variants:
        key = _candidate_dedup_key(variant, mtype)
        if key is None or key in seen:
            continue
        seen.add(key)
        out.append(CandidateProposal(payload=variant))
    return tuple(out)


def _candidate_dedup_key(payload: dict, mtype: ModificationType) -> Optional[tuple]:
    """Return the near-dup dedup key for one candidate payload, or
    ``None`` if the payload does not expose a usable identifier."""
    if mtype is ModificationType.NEW_PARAM:
        axis = _normalise(str(payload.get("new_axis_label", "")))
        var = _normalise(str(payload.get("var_definition", "")))
        patch = _normalise(str(payload.get("template_patch", "")))
        vals = tuple(
            _normalise(str(v.get("value", "")))
            for v in payload.get("values", []) if isinstance(v, dict)
        )
        if not axis:
            return None
        return ("new_param", axis, var, patch, vals)
    if mtype is ModificationType.OMISSION:
        new = _normalise(str(payload.get("new", "")))
        return ("omission", new) if new else None
    # L2 content + reorder + template_paraphrase all key on `new`.
    new = _normalise(str(payload.get("new", "")))
    return ("original_new", new) if new else None


# ---------------------------------------------------------------------------
# LLM round-trip + validation shared by both paths
# ---------------------------------------------------------------------------


def _call_and_validate(
    stage_json: dict,
    usage: TargetUsage,
    mtype: ModificationType,
    client: LLMClient,
    *,
    n: int,
) -> tuple[tuple[dict, ...], Optional[str], tuple[str, ...]]:
    """Render the prompt for one usage, call the LLM (with a single
    retry on malformed lists), and return the validated variants.

    Returns
    -------
    variants
        Tuple of validated per-variant payload dicts (may be empty).
    reason
        ``None`` on any-variants success; a ``malformed_list_after_retry:
        …`` message on double failure of the list-level parse.
    dropped_reasons
        Per-element schema-validation errors (elements parsed but
        rejected).
    """
    slots = slot_extractor.extract_slots(
        stage_json,
        usage.concept_key,
        mtype,
        usage.slot_extractor_target_id,
    )
    prompt_body = load_prompt(mtype)
    rendered_base = _render_prompt(prompt_body, slots, mtype)
    prompt = _wrap_multi_candidate(rendered_base, n=n)

    last_error = ""
    for _ in range(2):  # one retry mirrors llm_proposer.propose
        response_text = client.complete(prompt)
        try:
            raw_list = _parse_json_list(response_text)
        except ValueError as err:
            last_error = str(err)
            continue
        variants, dropped = _validate_variants(raw_list, mtype)
        if variants:
            return variants, None, dropped
        # Empty after validation — retry once (mirrors llm_proposer).
        last_error = "all_elements_rejected_by_schema"
    return (), f"malformed_list_after_retry: {last_error}", ()


def _wrap_multi_candidate(rendered_prompt: str, *, n: int) -> str:
    """Append the single multi-candidate instruction. Prompts stay
    byte-identical on disk; this f-string is the only per-request
    difference."""
    return (
        rendered_prompt.rstrip()
        + "\n\n"
        + (
            f"IMPORTANTE: en vez de una única respuesta, devuelve una lista "
            f"JSON de {n} respuestas alternativas distintas, ordenadas de "
            "mejor a peor. Cada elemento de la lista debe seguir exactamente "
            "el esquema JSON descrito arriba. No repitas alternativas."
        )
        + "\n"
    )


# Alternation: a *valid* escape pair (\" \\ \/ \b \f \n \r \t \u) is matched
# as a unit and kept; any other lone backslash is matched by the second
# branch and dropped. Consuming valid pairs whole is what keeps "\\" intact.
# Real BC3 text never contains a backslash; the only source is phi4 echoing the
# FIEBDC "\TEXTO\ ... \" field delimiter that s01 leaves on the raw templates.
_ESCAPE_RE = re.compile(r'\\([\\"/bfnrtu])|\\')


def _repair_invalid_escapes(s: str) -> str:
    """Drop backslashes that do not begin a valid JSON escape sequence.

    Sprint 38.5. Applied only *after* a strict ``json.loads`` has failed,
    so well-formed responses are parsed byte-identically to before.
    """
    return _ESCAPE_RE.sub(lambda m: m.group(0) if m.group(1) is not None else "", s)


def _parse_json_list(text: str) -> list:
    """List-level counterpart to :func:`llm_proposer._parse_json_object`.

    Recovers the outermost JSON array from prose/fence-wrapped output;
    tolerates the same shape flexibility (leading commentary, code
    fences). On a decode error, retries once with
    :func:`_repair_invalid_escapes`. Raises ``ValueError`` on
    unrecoverable input.
    """
    s = _recover_json_array(text)
    if not s:
        raise ValueError("empty_response")
    try:
        obj = json.loads(s)
    except json.JSONDecodeError as first_err:
        try:
            obj = json.loads(_repair_invalid_escapes(s))
        except json.JSONDecodeError:
            raise ValueError(f"malformed_json: {first_err.msg}") from first_err
    if not isinstance(obj, list):
        raise ValueError(f"top_level_not_list: type={type(obj).__name__}")
    if not obj:
        raise ValueError("empty_list")
    return obj


def _recover_json_array(text: str) -> str:
    """Same idea as :func:`llm_proposer._extract_json_object`, but
    targets ``[…]`` instead of ``{…}``.

    Falls back to the ``{…}`` recovery so a model that ignored the list
    instruction and returned a single object still produces something —
    the caller strict-parses and fails loud on non-list output.
    """
    from .llm_proposer import _FENCE_RE
    s = text.strip()
    fence = _FENCE_RE.search(s)
    if fence:
        s = fence.group(1).strip()
    if s.startswith("["):
        return s
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end > start:
        return s[start : end + 1].strip()
    # Fall back to the object-level recovery — the caller will reject a
    # non-list top level with a clear error message.
    return _extract_json_object(text)


# Sprint 38.5 addendum. The raw templates' trailing FIEBDC "\" reads like a
# line-continuation, so phi4 occasionally absorbs the prompt scaffold lines
# ("Campo destino: …", "Plantilla actual: …") into its candidate text
# (observed on OEB010$ TEXTO template_paraphrase). Such echoes pass the
# placeholder validator — the echoed original carries every placeholder —
# so they are dropped here by marker. Catalog text never contains these
# phrases; they exist only in the prompt scaffold.
_SCAFFOLD_MARKERS: tuple[str, ...] = ("Campo destino:", "Plantilla actual:")


def _is_prompt_echo(payload: dict) -> bool:
    """True if any string field of ``payload`` contains a prompt-scaffold
    marker — the candidate is a regurgitation of the prompt, not a rewrite."""
    return any(
        isinstance(v, str) and any(marker in v for marker in _SCAFFOLD_MARKERS)
        for v in payload.values()
    )


def _validate_variants(
    raw_list: list,
    mtype: ModificationType,
) -> tuple[tuple[dict, ...], tuple[str, ...]]:
    """Run :func:`variant_proposer._validate_payload` on each element;
    keep the survivors, log the drops."""
    out: list[dict] = []
    dropped: list[str] = []
    for i, elem in enumerate(raw_list):
        if not isinstance(elem, dict):
            dropped.append(f"[{i}] not_a_dict")
            continue
        try:
            _validate_payload(elem, mtype)
        except ValueError as err:
            dropped.append(f"[{i}] {err}")
            continue
        if _is_prompt_echo(elem):
            dropped.append(f"[{i}] prompt_scaffold_echo")
            continue
        out.append(elem)
    return tuple(out), tuple(dropped)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _is_l1(mtype: ModificationType) -> bool:
    return mtype in {
        ModificationType.SYNONYM_LABEL,
        ModificationType.NUM_TO_TEXT,
        ModificationType.UNIT_CONVERSION,
        ModificationType.UNIT_EXPANSION,
        ModificationType.ABBREV_EXPANSION,
        ModificationType.CODE_EXPANSION,
    }


def _normalise(s: str) -> str:
    """Casefold + collapse whitespace. Used ONLY for near-duplicate
    detection — not for storage. Storage keeps the LLM's original
    casing so the human review shows the model's actual output.
    """
    return " ".join(s.split()).casefold()


def _ws_norm(s: str) -> str:
    """Whitespace-collapse only — matches
    :func:`target_scanner._norm` so :func:`_extract_l1_candidates_for_value`
    can compare LLM-echoed ``original`` strings against target dedup
    keys byte-for-byte."""
    return " ".join(s.split())
