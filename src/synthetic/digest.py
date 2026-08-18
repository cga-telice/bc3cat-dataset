"""Review digest generator with condition-binding leaf selection.

F1-review §4.3 found that the hand-built `F1_PILOT_REVIEW_DIGEST.md`
always picked the alphabetically smallest leaf (`OEB070aaaa`) as the
"representative" of each variant. For any modification bound to a
non-`a` parameter value — e.g. a mod on `%C=c`, `%B=b`, or `param D value
"d"` — that leaf does NOT exhibit the change, and the manual reviewer
literally cannot see what the modification did.

The new selector picks a leaf whose parameter labels bind to the
conditions the modifications target. Item-key layout is standard BC3:
`<concept_prefix><axis_labels>_syn_<variant_id>`, where the axis labels
follow the sorted `parameters` keys (A, B, C, D, …).

Public API:

  * `bindings_from_rule(rule)` — pull `(axis, value_label)` bindings out
    of one L1 / L2 rule.
  * `merged_bindings(rules)` — union of the bindings from a rule list.
  * `select_representative_leaf(item_keys, concept_prefix, sorted_axes,
    bindings)` — pick a leaf that matches; fall back to the minimal leaf
    when no match is available.
  * `render_variant_entry(n, variant, materialized, concept_prefix,
    sorted_axes)` — return the markdown block for one variant.
  * `render_digest(concept_key, ...)` — read the artifact layout and
    write the full markdown file.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Mapping, Optional


__all__ = [
    "bindings_from_rule",
    "merged_bindings",
    "select_representative_leaf",
    "render_variant_entry",
    "render_digest",
]


_L1_TYPES = frozenset({
    "synonym_label", "num_to_text", "unit_conversion",
    "unit_expansion", "abbrev_expansion", "code_expansion",
})
_L2_TYPES = frozenset({"paraphrase", "expansion", "compression"})

_CONDITION_PAT = re.compile(r"%([A-Z])\s*=+\s*\"?(?P<label>[A-Za-z0-9]+)\"?")


def bindings_from_rule(rule: Mapping) -> dict[str, str]:
    """Return `{axis: value_label}` this rule pins.

    L1 rules pin via `{"param": "B", "value": "b"}`. L2 rules pin via a
    `condition` string like `%B=a` or `%B="c"`. L3 rules (omission,
    reorder) and `new_param` don't pin any specific value → empty dict.
    """
    mtype = rule.get("type")
    if mtype in _L1_TYPES:
        param = rule.get("param")
        value = rule.get("value")
        if param and value:
            return {param: value}
        return {}
    if mtype in _L2_TYPES:
        cond = rule.get("condition") or ""
        m = _CONDITION_PAT.search(cond)
        if m is not None:
            return {m.group(1): m.group("label")}
    return {}


def merged_bindings(rules: Iterable[Mapping]) -> dict[str, str]:
    """Union of per-rule bindings. Later rules overwrite earlier ones on
    conflicts (this is a display heuristic; downstream chooses one leaf)."""
    out: dict[str, str] = {}
    for r in rules:
        out.update(bindings_from_rule(r))
    return out


def _leaf_stem(item_key: str) -> str:
    """Strip the trailing `_syn_<variant_id>` from an item_key."""
    return item_key.split("_syn_", 1)[0]


def _leaf_matches(
    item_key: str,
    concept_prefix: str,
    sorted_axes: list[str],
    bindings: Mapping[str, str],
) -> bool:
    stem = _leaf_stem(item_key)
    if not stem.startswith(concept_prefix):
        return False
    suffix = stem[len(concept_prefix):]
    for axis, label in bindings.items():
        if axis not in sorted_axes:
            return False
        pos = sorted_axes.index(axis)
        if pos >= len(suffix) or suffix[pos] != label:
            return False
    return True


def select_representative_leaf(
    item_keys: Iterable[str],
    *,
    concept_prefix: str,
    sorted_axes: list[str],
    bindings: Mapping[str, str],
) -> Optional[str]:
    """Pick the alphabetically smallest leaf whose axis assignment matches
    the given bindings. Falls back to the alphabetically smallest leaf when
    no bindings match, so the digest never crashes on odd modifications."""
    keys = sorted(item_keys)
    if not keys:
        return None
    if not bindings:
        return keys[0]
    for k in keys:
        if _leaf_matches(k, concept_prefix, sorted_axes, bindings):
            return k
    return keys[0]


# ---- markdown rendering ------------------------------------------------


def _format_rule_line(rule: Mapping) -> str:
    mtype = rule.get("type", "?")
    original = rule.get("original", "?")
    new = rule.get("new", "?")
    if mtype in _L1_TYPES:
        loc = f"[{rule.get('param', '?')}]"
    elif mtype in _L2_TYPES:
        loc = f"[{rule.get('var', '?')} {rule.get('condition', '?')}]"
    elif mtype in ("omission", "reorder"):
        loc = f"[{rule.get('field', '?')}]"
    else:
        loc = ""
    return f"- {mtype}{loc}: {original!r} → {new!r}"


def render_variant_entry(
    *,
    n: int,
    variant: Mapping,
    materialized: Mapping[str, Mapping],
    concept_prefix: str,
    sorted_axes: list[str],
) -> str:
    """Render one variant's markdown block.

    `variant` carries `{"variant_id", "rules": [...]}`.
    `materialized` maps `item_key -> {"resumen": ..., "texto": ...}`.

    Paired-status entries (`status="paired"`) are suppressed from the rule
    display: they duplicate a primary edit on the twin representation and
    are implementation detail from the reviewer's point of view. The
    displayed modification count reflects the primary edits only.
    """
    variant_id = variant.get("variant_id", "?")
    all_rules = list(variant.get("rules", []))
    primary_rules = [r for r in all_rules if r.get("status") != "paired"]
    bindings = merged_bindings(primary_rules)
    leaf_key = select_representative_leaf(
        materialized.keys(),
        concept_prefix=concept_prefix,
        sorted_axes=sorted_axes,
        bindings=bindings,
    )
    if leaf_key is None:
        return (
            f"## {n}. {variant_id}\n"
            f"- **item_key:** _(no materialized leaves)_  "
            f"(modifications: {len(primary_rules)})\n"
            + "\n".join(_format_rule_line(r) for r in primary_rules)
            + "\n"
        )
    body = materialized.get(leaf_key, {})
    resumen = body.get("resumen") or body.get("RESUMEN") or ""
    texto = body.get("texto") or body.get("TEXTO") or ""
    lines = [
        f"## {n}. {variant_id}",
        f"- **item_key:** `{leaf_key}`  (modifications: {len(primary_rules)})",
    ]
    for r in primary_rules:
        lines.append(_format_rule_line(r))
    lines.append(f"- **resumen:** {resumen}")
    lines.append(f"- **texto:** {texto}")
    return "\n".join(lines) + "\n"


def render_digest(
    *,
    concept_key: str,
    intermediate_dir: Path,
    concept_prefix: str,
    sorted_axes: list[str],
    title_suffix: str = "",
) -> str:
    """Assemble the full markdown digest for `concept_key`.

    Reads every `{variant_id}.json` under `intermediate_dir`. Each file is
    the materializer's output and carries `variant_id`, `modifications`, and
    an `items` map `{item_key -> {resumen, texto, ...}}`.
    """
    files = sorted(Path(intermediate_dir).glob("*.json"))
    header = (
        f"# Review Digest — {concept_key}{title_suffix}\n\n"
        f"{len(files)} distinct variants (representative leaf per variant chosen "
        f"to exhibit each modification's condition).\n\n"
    )
    blocks: list[str] = []
    for i, mat_path in enumerate(files, start=1):
        data = json.loads(mat_path.read_text(encoding="utf-8"))
        variant_id = data.get("variant_id") or mat_path.stem
        modifications = data.get("modifications", [])
        items = data.get("items", {})
        # Some pipelines wrap items under the concept_key.
        if concept_key in items and isinstance(items[concept_key], dict):
            items = items[concept_key]
        blocks.append(
            render_variant_entry(
                n=i,
                variant={"variant_id": variant_id, "rules": modifications},
                materialized=items,
                concept_prefix=concept_prefix,
                sorted_axes=sorted_axes,
            )
        )
    return header + "\n".join(blocks)


# ---- CLI ---------------------------------------------------------------


def _main() -> int:
    import argparse
    p = argparse.ArgumentParser(description="Render a review digest for a concept.")
    p.add_argument("--concept", required=True, help="Concept key, e.g. OEB070$")
    p.add_argument("--intermediate", required=True,
                   help="Path to materialized variant directory")
    p.add_argument("--stage-json", required=True,
                   help="Stage-2 JSON (for parameter/axis discovery)")
    p.add_argument("--out", required=True, help="Output markdown path")
    p.add_argument("--title-suffix", default="", help="Optional suffix for title")
    args = p.parse_args()

    stage = json.loads(Path(args.stage_json).read_text(encoding="utf-8"))
    concept = stage[args.concept]
    sorted_axes = sorted((concept.get("parameters") or {}).keys())
    # Concept prefix is the leading letters of the concept key up to `$`.
    concept_prefix = args.concept.rstrip("$")

    md = render_digest(
        concept_key=args.concept,
        intermediate_dir=Path(args.intermediate),
        concept_prefix=concept_prefix,
        sorted_axes=sorted_axes,
        title_suffix=args.title_suffix,
    )
    Path(args.out).write_text(md, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
