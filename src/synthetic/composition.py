"""Composition rules — pre-apply validator for rule batches.

Given a list of rules destined for the same concept, decides which
are mutually compatible, what order they apply in, and which must
be skipped with a logged reason. State-blind: never inspects the
concept's stage JSON. Rule-vs-rule consistency only; rule-vs-data
consistency is enforced at apply-time by the per-layer worker.

The composer is a pure function: same input → same output. It does
not mutate either input or output rule dicts; the returned
``admissible_rules_in_apply_order`` is a fresh ``list`` aliasing the
input rule dicts (shallow copy of the list, the dict elements are
the same objects).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from .layer_l2 import _norm as _norm_cond
from .taxonomy import Layer, Modification, ModificationType, TYPE_TO_LAYER


class CompatibilityVerdict(str, Enum):
    COMPATIBLE = "compatible"
    SAME_TARGET = "same_target_conflict"
    LAYER_DEPENDENCY = "layer_dependency_conflict"
    UNSTACKABLE = "unstackable"


_LAYER_APPLY_ORDER: tuple[Layer, ...] = (
    Layer.PARAM_DEFINITION,
    Layer.PARAM_VALUE,
    Layer.TEXT_VARIABLE,
    Layer.TEMPLATE,
)


COMPATIBILITY_MATRIX: dict[
    tuple[ModificationType, ModificationType],
    CompatibilityVerdict,
] = {
    (ModificationType.NEW_PARAM, ModificationType.SYNONYM_LABEL):    CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.NUM_TO_TEXT):       CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.UNIT_CONVERSION):   CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.UNIT_EXPANSION):    CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.ABBREV_EXPANSION):  CompatibilityVerdict.LAYER_DEPENDENCY,
    (ModificationType.NEW_PARAM, ModificationType.CODE_EXPANSION):    CompatibilityVerdict.LAYER_DEPENDENCY,
}


def _canonical_key(rule: dict[str, Any]) -> tuple:
    """Per-rule addressing tuple used for same-target dedup.

    Two rules with the same canonical key conflict by *same-target*
    (later rule skipped, reason names the duplication). The keys are
    layer-prefixed so cross-layer accidental collisions are impossible.
    """
    mtype = ModificationType(rule["type"])
    layer = TYPE_TO_LAYER[mtype]

    if layer is Layer.PARAM_VALUE:
        return (Layer.PARAM_VALUE, rule["param"], rule["value"])
    if layer is Layer.TEXT_VARIABLE:
        raw_var = rule["var"]
        var_key = raw_var.lstrip("$")
        return (Layer.TEXT_VARIABLE, var_key, _norm_cond(rule["condition"]))
    if layer is Layer.TEMPLATE:
        return (Layer.TEMPLATE, rule["field"].lower(), rule["original"])
    if layer is Layer.PARAM_DEFINITION:
        return (Layer.PARAM_DEFINITION, rule["param"])
    raise AssertionError(f"unhandled layer {layer!r} for type {mtype!r}")


def _resolve(rule: dict[str, Any]) -> tuple[ModificationType, Layer]:
    raw = rule["type"]
    try:
        mtype = ModificationType(raw)
    except ValueError as exc:
        raise ValueError(f"unknown modification type: {raw!r}") from exc
    return mtype, TYPE_TO_LAYER[mtype]


def compose_rules(
    rules: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[Modification]]:
    """Sort ``rules`` into PD→L1→L2→L3 order, deduplicate by canonical
    key, then check pairs against ``COMPATIBILITY_MATRIX``. Returns the
    admissible rules in apply order plus a ``Modification`` log of
    skipped rules.
    """
    if not rules:
        return [], []

    annotated: list[tuple[ModificationType, Layer, dict[str, Any]]] = []
    for rule in rules:
        mtype, layer = _resolve(rule)
        annotated.append((mtype, layer, rule))

    annotated.sort(key=lambda triple: _LAYER_APPLY_ORDER.index(triple[1]))

    skipped: list[Modification] = []
    after_dedup: list[tuple[ModificationType, Layer, dict[str, Any]]] = []
    seen_keys: set[tuple] = set()
    for mtype, layer, rule in annotated:
        key = _canonical_key(rule)
        if key in seen_keys:
            skipped.append(
                Modification(
                    type=mtype,
                    layer=layer,
                    status="skipped",
                    reason=(
                        f"same_target_conflict with earlier rule at "
                        f"canonical key {key!r}"
                    ),
                )
            )
            continue
        seen_keys.add(key)
        after_dedup.append((mtype, layer, rule))

    pd_params: set[str] = {
        rule["param"]
        for mtype, layer, rule in after_dedup
        if layer is Layer.PARAM_DEFINITION
    }

    after_same_axis: list[tuple[ModificationType, Layer, dict[str, Any]]] = []
    for mtype, layer, rule in after_dedup:
        if layer is Layer.PARAM_VALUE and rule["param"] in pd_params:
            skipped.append(
                Modification(
                    type=mtype,
                    layer=layer,
                    status="skipped",
                    reason=(
                        f"layer_dependency_conflict: param "
                        f"{rule['param']!r} introduced by new_param rule "
                        f"in same batch"
                    ),
                )
            )
            continue
        after_same_axis.append((mtype, layer, rule))

    admissible: list[tuple[ModificationType, Layer, dict[str, Any]]] = []
    for i, (later_mtype, later_layer, later_rule) in enumerate(after_same_axis):
        verdict_to_skip: CompatibilityVerdict | None = None
        earlier_for_reason: ModificationType | None = None
        for earlier_mtype, _earlier_layer, _earlier_rule in after_same_axis[:i]:
            verdict = COMPATIBILITY_MATRIX.get(
                (earlier_mtype, later_mtype), CompatibilityVerdict.COMPATIBLE
            )
            if verdict is CompatibilityVerdict.COMPATIBLE:
                continue
            if verdict is CompatibilityVerdict.LAYER_DEPENDENCY:
                # Step 5 (PD-vs-L1 same-axis pass) is the authoritative
                # detector for layer-dependency conflicts. The matrix
                # entry expresses the *type-pair policy*; whether a
                # specific rule pair triggers it is a value-pair check.
                # If step 5 found no conflict, the matrix entry is a
                # no-op here.
                continue
            verdict_to_skip = verdict
            earlier_for_reason = earlier_mtype
            break
        if verdict_to_skip is not None and earlier_for_reason is not None:
            skipped.append(
                Modification(
                    type=later_mtype,
                    layer=later_layer,
                    status="skipped",
                    reason=(
                        f"{verdict_to_skip.value}: {earlier_for_reason.value} "
                        f"stacked with {later_mtype.value}"
                    ),
                )
            )
            continue
        admissible.append((later_mtype, later_layer, later_rule))

    return [rule for _, _, rule in admissible], skipped
