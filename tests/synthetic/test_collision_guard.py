"""Sprint 34 — post-generation collision guard on L1 + L2 mutators.

Rewrite failure surfaced by the F2c-L2 review: phi4's compression of
`Nocturno Excepcional → Nocturno` collides with a sibling value of the
same axis (`%B=b` already reads "Nocturno"). Two leaves that render the
same string are indistinguishable in retrieval evaluation — that
violates the proposal's Stage-D "preservation of parametric meaning"
criterion.

The mutator layers now pre-flight the write:
  * L1 `_replace_value` — if the proposed `new` (normalised) equals any
    OTHER value on the same axis, return `[Modification(status="skipped",
    reason="collision_with_sibling_axis_value")]` and do not apply.
  * L2 `_replace_fragment` — same shape on text-variable fragments.
  * Paired writes — if EITHER primary or pair would collide, skip the
    whole modification (no half-applied state).
"""

from __future__ import annotations

import pytest

from synthetic.layer_l1 import apply_synonym_label
from synthetic.layer_l2 import apply_paraphrase, apply_compression
from synthetic.taxonomy import Layer, ModificationType


def _oeb070():
    return {
        "OEB070$": {
            "concept": "CANALIZACIÓN OEB070",
            "parameters": {
                "A": {"label": "Nº TUBOS", "values": [
                    {"label": "a", "value": "1"},
                    {"label": "b", "value": "2"},
                ]},
                "B": {"label": "TRABAJO", "values": [
                    {"label": "a", "value": "Diurno"},
                    {"label": "b", "value": "Nocturno"},
                    {"label": "c", "value": "Diurno Excepcional"},
                    {"label": "d", "value": "Nocturno Excepcional"},
                ]},
            },
            "text_variables": {
                "L": (
                    '"Diurno" * (%B=a) + "Nocturno" * (%B=b) + '
                    '"Diurno Excepcional" * (%B=c) + '
                    '"Nocturno Excepcional" * (%B=d)'
                ),
            },
            "resumen": "de $A tubo(s) ($L(%B))",
            "texto": "de $A tubo(s). Trabajo: $B",
        }
    }


# ---- L1 collision detection --------------------------------------------

def test_l1_synonym_collision_with_sibling_axis_value_skips():
    stage = _oeb070()
    # Try to rename axis B value "d" ("Nocturno Excepcional") to "Nocturno"
    # — collides with existing sibling %B=b.
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "d", "new": "Nocturno"},
    )
    # No write happened.
    b_d = stage_out["OEB070$"]["parameters"]["B"]["values"][3]["value"]
    assert b_d == "Nocturno Excepcional"
    # Log has one skip record with a descriptive reason.
    assert len(log) == 1
    m = log[0]
    assert m.status == "skipped"
    assert "collision_with_sibling_axis_value" in (m.reason or "")
    assert m.param == "B"
    assert m.value == "d"


def test_l1_synonym_non_colliding_new_value_still_writes():
    stage = _oeb070()
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "d", "new": "Nocturno Especial"},
    )
    assert stage_out["OEB070$"]["parameters"]["B"]["values"][3]["value"] == "Nocturno Especial"
    # Primary applied + paired (twin_var L) — no collisions.
    assert log[0].status == "applied"
    # Verify pair on the twin fragment.
    assert '"Nocturno Especial" * (%B=d)' in stage_out["OEB070$"]["text_variables"]["L"]


def test_l1_collision_normalization_is_whitespace_insensitive():
    stage = _oeb070()
    # "  Nocturno " (extra whitespace) should still collide with %B=b "Nocturno".
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "d", "new": "  Nocturno "},
    )
    assert log[0].status == "skipped"
    assert "collision_with_sibling_axis_value" in (log[0].reason or "")


def test_l1_collision_when_paired_side_would_collide_skips_whole():
    """If primary L1 write is fine but the paired L2 fragment would collide
    with a sibling fragment on the twin var, the whole modification is
    skipped so we never end up in a half-applied state."""
    stage = _oeb070()
    # Manually diverge param B value "d" so primary write "Nocturno" doesn't
    # collide with param values (only "Nocturno Excepcional" is on B=d, and
    # only "Nocturno" is on B=b, no other value equals a candidate). We want
    # to construct a case where the primary side is OK but the pair collides.
    # Concretely: rename axis B value "b" to something that will NOT collide,
    # and rename $L fragment for %B=b to also NOT collide — but leave a
    # sibling fragment "Nocturno" elsewhere that will collide with new pair.
    # Simpler: keep the setup and choose a new value that primary side accepts
    # but pair side rejects.
    # Rewrite %B=d value → "Diurno": collides with %B=a on primary — that's
    # a primary collision. Not what we want here.
    # Rewrite %B=d value → "X": primary OK. Twin $L fragment for %B=d is
    # "Nocturno Excepcional" currently; paired write would set it to "X". No
    # collision. Skip.
    # To force a pair-only collision, we need the twin's fragment set to
    # include "X" already at a different condition. Let's do that:
    stage["OEB070$"]["text_variables"]["L"] = (
        '"Diurno" * (%B=a) + "X" * (%B=b) + '
        '"Diurno Excepcional" * (%B=c) + '
        '"Nocturno Excepcional" * (%B=d)'
    )
    # Now the primary L1 rename of %B=d to "X" does NOT collide with param
    # values (they are Diurno, Nocturno, Diurno Excepcional, Nocturno Excepcional).
    # But paired write into $L(%B=d) with "X" would collide with existing
    # $L(%B=b) = "X".
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "d", "new": "X"},
    )
    assert log[0].status == "skipped"
    assert "collision" in (log[0].reason or "")
    # Primary side NOT applied — no half-state.
    assert stage_out["OEB070$"]["parameters"]["B"]["values"][3]["value"] == "Nocturno Excepcional"


# ---- L2 collision detection --------------------------------------------

def test_l2_compression_collision_with_sibling_fragment_skips():
    stage = _oeb070()
    # Compress $L fragment for %B=d "Nocturno Excepcional" to "Nocturno" —
    # collides with existing $L(%B=b) fragment.
    stage_out, log = apply_compression(
        stage, "OEB070$",
        {"var": "L", "condition": "%B=d", "new": "Nocturno"},
    )
    # Text-var untouched.
    assert '"Nocturno Excepcional" * (%B=d)' in stage_out["OEB070$"]["text_variables"]["L"]
    assert log[0].status == "skipped"
    assert "collision_with_sibling_fragment" in (log[0].reason or "")


def test_l2_compression_non_colliding_new_still_writes():
    stage = _oeb070()
    stage_out, log = apply_compression(
        stage, "OEB070$",
        {"var": "L", "condition": "%B=d", "new": "Noche especial"},
    )
    assert '"Noche especial" * (%B=d)' in stage_out["OEB070$"]["text_variables"]["L"]
    assert log[0].status == "applied"


def test_l2_collision_when_paired_side_would_collide_skips_whole():
    """L2 write is OK against fragment siblings but the paired L1 rewrite
    of the twin param value would collide with a sibling axis value.
    Skip both."""
    stage = _oeb070()
    # Compress $L fragment %B=d to "Nocturno". Paired L1 write on axis B
    # value "d" to "Nocturno" WOULD collide with axis B value "b" (Nocturno).
    # But this also collides on the text-var side (Nocturno is at %B=b).
    # So we need a case where fragment side doesn't collide but axis side does.
    # Manually diverge the fragment for %B=b so the L2 write doesn't collide
    # with a fragment sibling, but the pair still collides on param B.
    stage["OEB070$"]["text_variables"]["L"] = (
        '"Diurno" * (%B=a) + "Nocturno Alt" * (%B=b) + '
        '"Diurno Excepcional" * (%B=c) + '
        '"Nocturno Excepcional" * (%B=d)'
    )
    # Now L2 rewrite %B=d → "Nocturno". Fragment siblings are Diurno / Nocturno Alt
    # / Diurno Excepcional → no collision. But paired L1 write into axis B
    # value "d" would set it to "Nocturno" — which collides with axis B value
    # "b" (still "Nocturno" as the axis value).
    stage_out, log = apply_paraphrase(
        stage, "OEB070$",
        {"var": "L", "condition": "%B=d", "new": "Nocturno"},
    )
    assert log[0].status == "skipped"
    assert "collision" in (log[0].reason or "")
    # Neither side applied.
    assert '"Nocturno Excepcional" * (%B=d)' in stage_out["OEB070$"]["text_variables"]["L"]


def test_l2_no_twin_still_checks_own_fragment_siblings():
    """Text-var without a twin axis still needs sibling-fragment collision
    check on its own formula."""
    stage = _oeb070()
    # Add a bare-referenced $K (no twin). Compress one of K's fragments to
    # collide with another K fragment.
    stage["OEB070$"]["text_variables"]["K"] = (
        '"alpha" * (%B=a) + "beta" * (%B=b)'
    )
    stage_out, log = apply_compression(
        stage, "OEB070$",
        {"var": "K", "condition": "%B=a", "new": "beta"},
    )
    assert log[0].status == "skipped"
    assert "collision_with_sibling_fragment" in (log[0].reason or "")


def test_skipped_modification_does_not_propagate_paired_edit():
    """Belt-and-suspenders: when the primary write is skipped, the log MUST
    NOT contain a paired-status Modification. Only the skip record."""
    stage = _oeb070()
    stage_out, log = apply_synonym_label(
        stage, "OEB070$",
        {"param": "B", "value": "d", "new": "Nocturno"},
    )
    assert len(log) == 1
    assert all(m.status != "paired" for m in log)
