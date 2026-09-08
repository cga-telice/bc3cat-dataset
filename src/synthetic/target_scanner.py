"""Chapter-level target enumeration + deduplication.

Sprint 37 (F3-prep-1-A). Walks a stage-2 chapter JSON once and produces
a :class:`ChapterInventory` — for each :class:`ModificationType`, the list
of :class:`UniqueTarget` records deduplicated across concepts, each
carrying a tuple of :class:`TargetUsage` records naming the concept(s)
that share this target.

Dedup keys per family:

* **L1** (per axis-value):
  ``(axis_label_normalised, value_text_normalised)`` — one unique target
  per distinct axis-value pair across the chapter. The axis label anchors
  the semantic role; the value is what the human reviews. Applies to all
  six L1 modification types.
* **L2** (per fragment): ``fragment_text_normalised`` alone. Aggressive
  dedup by textual identity — two concepts using the same Spanish phrase
  share the same review verdict. Applies to the three L2 types.
* **L3** (per template): family-specific.
  ``(field, template_normalised, var_token)`` for OMISSION so different
  variables inside the same template are separate targets;
  ``(field, template_normalised)`` for REORDER and TEMPLATE_PARAPHRASE.
* **NEW_PARAM**: ``(concept_key,)`` — always concept-specific.

The unit of proposal and human review is the ``UniqueTarget``. The unit
of concept-level context (siblings, condition, first-usage concept for
slot extraction) is the ``TargetUsage``. One ``UniqueTarget`` fans out to
``len(usages)`` concepts.

This module does NOT own:

* per-concept slot extraction — that's :func:`slot_extractor.extract_slots`
  (the menu proposer picks the *first* usage's concept for the LLM call);
* the LLM round-trip — :mod:`menu_proposer` handles that;
* writing to disk — :mod:`menu_artefacts` handles that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from . import l2_repr, slot_extractor
from .taxonomy import ModificationType


_L1_TYPES = frozenset({
    ModificationType.SYNONYM_LABEL,
    ModificationType.NUM_TO_TEXT,
    ModificationType.UNIT_CONVERSION,
    ModificationType.UNIT_EXPANSION,
    ModificationType.ABBREV_EXPANSION,
    ModificationType.CODE_EXPANSION,
})
_L2_TYPES = frozenset({
    ModificationType.PARAPHRASE,
    ModificationType.EXPANSION,
    ModificationType.COMPRESSION,
})


_WS_RE = re.compile(r"\s+")


def _norm(s: str) -> str:
    """Whitespace-normalise a string. Preserves case and Spanish accents —
    both are semantically load-bearing for these targets.
    """
    return _WS_RE.sub(" ", s).strip()


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TargetUsage:
    """One concept's use of a shared :class:`UniqueTarget`.

    Attributes
    ----------
    concept_key
        The stage-2 top-level key (e.g. ``"OEB070$"``).
    slot_extractor_target_id
        The opaque ``target_id`` yielded by
        :func:`slot_extractor.enumerate_targets` for this concept +
        modification type. Used later by :mod:`menu_proposer` to feed
        :func:`slot_extractor.extract_slots` for the first usage.
    display
        Short human-readable "axis / value" or "var / condition" label,
        used only in the review artefact's *usages* line.
    """

    concept_key: str
    slot_extractor_target_id: object
    display: str


@dataclass(frozen=True)
class UniqueTarget:
    """A canonicalised target across concepts.

    Attributes
    ----------
    dedup_key
        Family-specific tuple, hashable; sorted lexicographically inside
        each :class:`ChapterInventory` slot for deterministic output.
    canonical
        Human-readable target label for the review artefact heading
        (e.g. ``"TRABAJO / Diurno"``, ``"$L / %B=a: normal"``,
        ``"RESUMEN template"``).
    usages
        Non-empty tuple of :class:`TargetUsage` records — sorted by
        ``concept_key`` for deterministic output.
    """

    dedup_key: tuple
    canonical: str
    usages: tuple[TargetUsage, ...]


@dataclass(frozen=True)
class ChapterInventory:
    """Per-:class:`ModificationType` catalog of unique targets across
    a stage-2 chapter (or a filtered subset like the OEB group).

    ``concept_keys`` is the sorted tuple of concept keys the scan
    covered; ``by_type`` maps each modification type to its tuple of
    unique targets (empty if the type has no targets in this scope).
    """

    concept_keys: tuple[str, ...]
    by_type: dict[ModificationType, tuple[UniqueTarget, ...]]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def scan_chapter(
    stage_json: dict,
    *,
    concept_filter: Optional[Callable[[str], bool]] = None,
    apply_l2_conversion: bool = True,
) -> ChapterInventory:
    """Enumerate every modification-type target across the chapter and
    deduplicate.

    Parameters
    ----------
    stage_json
        Parsed stage-2 chapter JSON (the shape produced by ``s02``).
    concept_filter
        Optional predicate on the top-level key; only ``$``-suffixed
        keys are considered concept groups. Pass e.g.
        ``lambda k: k.startswith("OEB")`` to scan the OEB subset only.
    apply_l2_conversion
        When ``True`` (default), :func:`l2_repr.list_to_formula` is
        applied with ``include_conditional=True`` before the scan.
        This makes every text-variable shape enumerable by the L2 path
        (matches the Sprint 26 pipeline discipline used by
        :mod:`f1_pilot`). Pass ``False`` only in tests that want to
        assert the raw pre-conversion behaviour.

    Returns
    -------
    ChapterInventory
        Fully deterministic: same input + same filter → byte-identical
        output regardless of dict ordering.
    """
    if apply_l2_conversion:
        stage_json, _report = l2_repr.list_to_formula(
            stage_json, include_conditional=True,
        )
    keys = _concept_keys(stage_json, concept_filter)
    by_type: dict[ModificationType, tuple[UniqueTarget, ...]] = {}
    for mtype in ModificationType:
        by_type[mtype] = _scan_type(stage_json, keys, mtype)
    return ChapterInventory(concept_keys=tuple(keys), by_type=by_type)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _concept_keys(
    stage_json: dict,
    concept_filter: Optional[Callable[[str], bool]],
) -> list[str]:
    keys = [k for k in stage_json.keys() if k.endswith("$")]
    if concept_filter is not None:
        keys = [k for k in keys if concept_filter(k)]
    return sorted(keys)


def _scan_type(
    stage_json: dict,
    concept_keys: list[str],
    mtype: ModificationType,
) -> tuple[UniqueTarget, ...]:
    """Walk every ``concept_key`` under one modification type; group
    resulting per-target entries by their dedup key."""
    groups: dict[tuple, list[TargetUsage]] = {}
    canonicals: dict[tuple, str] = {}
    for ck in concept_keys:
        for entry in _emit_entries(stage_json, ck, mtype):
            dk, canonical, usage = entry
            groups.setdefault(dk, []).append(usage)
            canonicals.setdefault(dk, canonical)
    return tuple(
        UniqueTarget(
            dedup_key=dk,
            canonical=canonicals[dk],
            usages=tuple(sorted(usages, key=lambda u: u.concept_key)),
        )
        for dk, usages in sorted(groups.items())
    )


def _emit_entries(
    stage_json: dict,
    concept_key: str,
    mtype: ModificationType,
):
    """Yield ``(dedup_key, canonical, TargetUsage)`` for every target
    of ``mtype`` in ``stage_json[concept_key]``.

    L1 breaks per-axis targets (from :mod:`slot_extractor`) down further
    into per-value entries so the human reviews each value separately.
    Other families pass through :func:`slot_extractor.enumerate_targets`
    directly.
    """
    item = stage_json[concept_key]

    if mtype in _L1_TYPES:
        for axis_key in slot_extractor.enumerate_targets(stage_json, concept_key, mtype):
            block = item["parameters"][axis_key]
            axis_label = _norm(block.get("label", ""))
            for entry in block.get("values", []):
                if not isinstance(entry, dict):
                    continue
                value_text = _norm(str(entry.get("value", "")))
                if not value_text:
                    continue
                if not slot_extractor.value_applies(value_text, mtype):
                    continue  # Sprint 38.5: per-value gate (e.g. digits under SYNONYM_LABEL)
                dedup_key = (axis_label, value_text)
                canonical = f"{axis_label} / {value_text}"
                usage = TargetUsage(
                    concept_key=concept_key,
                    slot_extractor_target_id=axis_key,
                    display=canonical,
                )
                yield dedup_key, canonical, usage

    elif mtype in _L2_TYPES:
        for target_id in slot_extractor.enumerate_targets(stage_json, concept_key, mtype):
            var_key, condition = target_id
            slots = slot_extractor.extract_slots(stage_json, concept_key, mtype, target_id)
            fragment_norm = _norm(slots["fragment"])
            if not fragment_norm:
                continue
            dedup_key = (fragment_norm,)
            canonical = f"${var_key} / {condition}: {fragment_norm}"
            usage = TargetUsage(
                concept_key=concept_key,
                slot_extractor_target_id=target_id,
                display=canonical,
            )
            yield dedup_key, canonical, usage

    elif mtype is ModificationType.OMISSION:
        for target_id in slot_extractor.enumerate_targets(stage_json, concept_key, mtype):
            field, var_token = target_id
            slots = slot_extractor.extract_slots(stage_json, concept_key, mtype, target_id)
            template_norm = _norm(slots["template"])
            dedup_key = (field, template_norm, var_token)
            canonical = f"{field} — omit {var_token} ({concept_key})"
            usage = TargetUsage(
                concept_key=concept_key,
                slot_extractor_target_id=target_id,
                display=canonical,
            )
            yield dedup_key, canonical, usage

    elif mtype in (ModificationType.REORDER, ModificationType.TEMPLATE_PARAPHRASE):
        for target_id in slot_extractor.enumerate_targets(stage_json, concept_key, mtype):
            field = target_id
            slots = slot_extractor.extract_slots(stage_json, concept_key, mtype, target_id)
            template_norm = _norm(slots["template"])
            dedup_key = (field, template_norm)
            canonical = f"{field} template ({concept_key})"
            usage = TargetUsage(
                concept_key=concept_key,
                slot_extractor_target_id=target_id,
                display=canonical,
            )
            yield dedup_key, canonical, usage

    elif mtype is ModificationType.NEW_PARAM:
        # slot_extractor yields exactly one None; new_param never dedups.
        for target_id in slot_extractor.enumerate_targets(stage_json, concept_key, mtype):
            dedup_key = (concept_key,)
            canonical = f"NEW_PARAM on {concept_key}"
            usage = TargetUsage(
                concept_key=concept_key,
                slot_extractor_target_id=target_id,
                display=canonical,
            )
            yield dedup_key, canonical, usage

    else:  # defensive: every enum member must be covered
        raise ValueError(f"no_scanner_for_type: {mtype.value!r}")
