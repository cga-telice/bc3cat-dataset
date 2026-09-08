"""Modification taxonomy — layers, types, and the `Modification` record.

Defines the data contract every Phase-B mutator and the offline LLM proposer
write against. Intentionally has no I/O and no dependencies beyond the
standard library; richer validation lives in E2.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import Enum
from typing import Any, Optional


class Layer(str, Enum):
    PARAM_VALUE = "param_value"
    TEXT_VARIABLE = "text_variable"
    TEMPLATE = "template"
    PARAM_DEFINITION = "param_definition"


class ModificationType(str, Enum):
    SYNONYM_LABEL = "synonym_label"
    NUM_TO_TEXT = "num_to_text"
    UNIT_CONVERSION = "unit_conversion"
    UNIT_EXPANSION = "unit_expansion"
    ABBREV_EXPANSION = "abbrev_expansion"
    CODE_EXPANSION = "code_expansion"
    PARAPHRASE = "paraphrase"
    EXPANSION = "expansion"
    COMPRESSION = "compression"
    OMISSION = "omission"
    REORDER = "reorder"
    # Sprint 36 — full-surface paraphrase of the RESUMEN or TEXTO template.
    # Adds real-world query-drift variability that fragment-level L2 alone
    # cannot produce. See F1_FINDINGS §6.2.1 addendum and Sprint 35 review
    # question ("are we paraphrasing templates?").
    TEMPLATE_PARAPHRASE = "template_paraphrase"
    NEW_PARAM = "new_param"


TYPE_TO_LAYER: dict[ModificationType, Layer] = {
    ModificationType.SYNONYM_LABEL: Layer.PARAM_VALUE,
    ModificationType.NUM_TO_TEXT: Layer.PARAM_VALUE,
    ModificationType.UNIT_CONVERSION: Layer.PARAM_VALUE,
    ModificationType.UNIT_EXPANSION: Layer.PARAM_VALUE,
    ModificationType.ABBREV_EXPANSION: Layer.PARAM_VALUE,
    ModificationType.CODE_EXPANSION: Layer.PARAM_VALUE,
    ModificationType.PARAPHRASE: Layer.TEXT_VARIABLE,
    ModificationType.EXPANSION: Layer.TEXT_VARIABLE,
    ModificationType.COMPRESSION: Layer.TEXT_VARIABLE,
    ModificationType.OMISSION: Layer.TEMPLATE,
    ModificationType.REORDER: Layer.TEMPLATE,
    ModificationType.TEMPLATE_PARAPHRASE: Layer.TEMPLATE,
    ModificationType.NEW_PARAM: Layer.PARAM_DEFINITION,
}


@dataclass(frozen=True)
class Modification:
    """Atomic record of a single applied (or skipped) rule modification.

    Matches the schema in `RESEARCH_PROPOSAL.md §2.3`. Only `type` and `layer`
    are required; everything else is per-type optional context. `status` /
    `reason` carry the protocol's "skip + log" bookkeeping for unstackable
    combinations (see `RESEARCH_PROTOCOL.md §4`).
    """

    type: ModificationType
    layer: Layer
    param: Optional[str] = None
    var: Optional[str] = None
    condition: Optional[str] = None
    field: Optional[str] = None
    value: Optional[str] = None
    original: Optional[str] = None
    new: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type.value, "layer": self.layer.value}
        for f in fields(self):
            if f.name in ("type", "layer"):
                continue
            v = getattr(self, f.name)
            if v is not None:
                out[f.name] = v
        return out

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Modification":
        kwargs = dict(d)
        kwargs["type"] = ModificationType(kwargs["type"])
        kwargs["layer"] = Layer(kwargs["layer"])
        return cls(**kwargs)
