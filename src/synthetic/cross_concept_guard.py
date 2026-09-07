"""Guard #1 — cross-concept collision guard for the synthetic corpus.

A rule modification must not make one concept's item confusable with a
*different* concept: for a retrieval benchmark whose label is the concept, a
synthetic ``resumen``/``texto`` that equals another concept's leaf is an
ambiguous (or mislabelled) example.

Two granularities:

* **corpus-level** (:func:`audit_corpus`) — checks the produced items. A changed
  field that now equals another concept's *base* leaf is an ``introduced``
  collision; a field left *unchanged* that collides only because the source
  catalogue already shares that text across concepts is ``inherited``.
* **template-level** (:func:`audit_pantry_templates`) — the exhaustive guarantee
  for a ``template_paraphrase`` rewrite itself: render it over *every* parameter
  combination of *every* concept it applies to and confirm no rendered leaf
  collides with another concept's base (needs the BC3 catalogue + bc3param).

Baseline note: the BPA catalogue itself contains leaves shared across concepts
(e.g. ``OED020`` == ``OED170``). Those are ``inherited`` and are a property of
the ground truth, not a synthesis defect — only ``introduced`` collisions are a
guard failure, and that count must be zero.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_FIELDS = ("resumen", "texto")


@dataclass(frozen=True)
class Collision:
    kind: str                      # "introduced" | "inherited"
    item_key: str                  # produced item (or rendered leaf) key
    concept: str                   # the item's own concept
    field: str                     # "resumen" | "texto"
    other_concepts: tuple          # colliding concepts (sorted, excludes own)
    text: str


@dataclass(frozen=True)
class BaseIndex:
    """Text -> owning concepts, over every base leaf of the catalogue."""
    #: (field, text) -> frozenset(concept_key)
    _owners: dict
    #: base leaf item_key -> {field: text}
    _self: dict

    def owners(self, field: str, text: str) -> frozenset:
        return self._owners.get((field, text), frozenset())

    def self_text(self, item_key: str, field: str) -> Optional[str]:
        rec = self._self.get(item_key)
        return rec.get(field) if rec else None


def build_base_index(long_df, short_df) -> BaseIndex:
    """Index every base leaf. ``long_df`` = texto (item_key, parent_key, text);
    ``short_df`` = resumen (item_key, text). Concept = the leaf's ``parent_key``.
    """
    parent = dict(zip(long_df["item_key"], long_df["parent_key"]))
    texto = dict(zip(long_df["item_key"], long_df["text"]))
    resumen = dict(zip(short_df["item_key"], short_df["text"]))

    owners: dict = {}
    self_: dict = {}
    for key, cpt in parent.items():
        r, t = resumen.get(key), texto.get(key)
        self_[key] = {"resumen": r, "texto": t}
        if r is not None:
            owners.setdefault(("resumen", r), set()).add(cpt)
        if t is not None:
            owners.setdefault(("texto", t), set()).add(cpt)
    frozen = {k: frozenset(v) for k, v in owners.items()}
    return BaseIndex(_owners=frozen, _self=self_)


def classify(index: BaseIndex, item_key: str, base_key: str, concept: str,
             field: str, val: str) -> Optional[Collision]:
    """Classify one (item, field, value) against the base index.

    Returns a ``Collision`` iff ``val`` is owned by a *different* concept, tagged
    ``inherited`` when ``val`` still equals this leaf's own base (a baseline
    catalogue duplicate that the modification did not touch — e.g. the field a
    ``RESUMEN`` rewrite left alone, or genuinely-twin concepts) and ``introduced``
    when the field was changed and now matches a foreign concept. Returns ``None``
    when there is no cross-concept collision.
    """
    others = index.owners(field, val) - {concept}
    if not others:
        return None
    own_base = index.self_text(base_key, field)
    kind = "inherited" if val == own_base else "introduced"
    return Collision(kind=kind, item_key=item_key, concept=concept, field=field,
                     other_concepts=tuple(sorted(others)), text=val)


def audit_corpus(items_df, index: BaseIndex) -> list[Collision]:
    """Flag every produced item whose ``resumen``/``texto`` equals a *different*
    concept's base leaf (``introduced`` vs ``inherited``, see :func:`classify`).
    """
    out: list[Collision] = []
    for row in items_df.itertuples(index=False):
        for field in _FIELDS:
            c = classify(index, row.item_key, row.original_key,
                         row.concept_key, field, getattr(row, field))
            if c is not None:
                out.append(c)
    return out


def introduced(collisions: list[Collision]) -> list[Collision]:
    return [c for c in collisions if c.kind == "introduced"]


# --------------------------------------------------------------------------- #
# Template-level exhaustive check (needs the catalogue + bc3param).
# --------------------------------------------------------------------------- #
def audit_pantry_templates(pantry, index: BaseIndex, source) -> list[Collision]:
    """Render every ``template_paraphrase`` rewrite over all parameter
    combinations of each concept it applies to, and flag any rendered leaf that
    collides with a *different* concept's base leaf.

    A paraphrased leaf that still equals its *own* concept's base is a no-op, not
    a collision, and is ignored. Every reported collision is ``introduced`` by
    construction (the field was rewritten). Requires the BC3 catalogue at
    ``source``; returns ``[]`` if the pantry has no template rewrites.
    """
    from synthetic import bc3param_backend
    from synthetic.taxonomy import ModificationType

    bc3param_backend.set_source(Path(source))
    rewrites = pantry.by_type.get(ModificationType.TEMPLATE_PARAPHRASE, ())
    out: list[Collision] = []
    for rw in rewrites:
        field = str(rw.dedup_key[0])          # "RESUMEN" | "TEXTO"
        original, new = rw.payload.get("original"), rw.payload.get("new")
        if not original or not new:
            continue
        rule = {"type": "template_paraphrase", "field": field,
                "original": original, "new": new}
        for concept in sorted({u.concept_key for u in rw.usages}):
            leaves, applied = bc3param_backend.run_variant_logged(concept, [rule])
            if not applied or not leaves:
                continue
            for leaf_key, leaf in leaves.items():
                # The rendered leaf_key IS a base item_key, so classify each field
                # against its own base: the field this rewrite did not touch (still
                # equal to the base) collides only with genuine twin concepts and is
                # `inherited`; only the rewritten, now-changed field can be
                # `introduced`.
                for f in _FIELDS:
                    c = classify(index, leaf_key, leaf_key, concept, f, leaf.get(f, ""))
                    if c is not None:
                        out.append(c)
    return out
