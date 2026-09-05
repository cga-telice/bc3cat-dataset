"""Expand parametric families into Items and write them out."""
from __future__ import annotations

import itertools
import json
from typing import IO, Iterable, Iterator, Sequence

from .fiebdc import Bc3Error, Catalog, code_key
from .model import DecompLine, Item, ParameterChoice
from .param.ast import Family
from .param.codes import derived_code, index_to_letter, split_derived_code
from .param.evaluator import EvalError, Evaluation, Evaluator
from .pricing import Pricer


def selections(family: Family) -> Iterator[tuple[int, ...]]:
    """All option tuples, last parameter varying fastest (same order as code letters)."""
    return itertools.product(*(range(1, n + 1) for n in family.option_counts()))


def build_item(catalog: Catalog, pricer: Pricer, family: Family, selection: Sequence[int],
               with_decomposition: bool = True) -> Item:
    concept = catalog.concept(family.code)
    try:
        ev = Evaluator(family, selection).run()
    except EvalError as exc:
        ev = Evaluation(valid=False, error=f"evaluation error: {exc}")
    params = [
        ParameterChoice(p.var, p.name, k, index_to_letter(k), p.options[k - 1] if k <= len(p.options) else "")
        for p, k in zip(family.params, selection)
    ]
    item = Item(
        code=derived_code(family.code, selection),
        family=family.code,
        unit=concept.unit if concept else "",
        family_summary=concept.summary if concept else "",
        chapter_path=catalog.chapter_path(family.code),
        parameters=params,
        resumen=ev.resumen,
        texto=ev.texto,
        valid=ev.valid,
        error=ev.error,
        warnings=list(ev.warnings),
    )
    if not ev.valid:
        return item
    try:
        lines, direct, total = pricer.price_evaluation(ev)
    except Bc3Error as exc:
        item.valid = False
        item.error = f"pricing error: {exc}"
        return item
    item.direct_cost = direct
    item.price = total
    for line in lines:
        if line.warning:
            item.warnings.append(line.warning)
    if with_decomposition:
        item.decomposition = [
            DecompLine(l.code, l.unit, l.summary, l.type, l.price, l.quantity, l.amount) for l in lines
        ]
    return item


def _chapter_families(catalog: Catalog, chapter: str, out: set[str], seen: set[str]) -> None:
    key = code_key(chapter)
    if key in seen:
        return
    seen.add(key)
    for child in catalog.children(chapter):
        if child in catalog.families_raw:
            out.add(child)
        elif code_key(child) in catalog.decompositions:
            _chapter_families(catalog, child, out, seen)


def select_families(catalog: Catalog, chapter: str | None = None, range_: str | None = None,
                    families: Iterable[str] | None = None) -> list[str]:
    codes: set[str] = set()
    if chapter is not None:
        if code_key(chapter) not in catalog.decompositions:
            raise Bc3Error(f"unknown chapter {chapter!r}")
        _chapter_families(catalog, chapter, codes, set())
    if range_ is not None:
        start, sep, end = range_.partition("..")
        if not sep or not start or not end:
            raise Bc3Error("range must be START..END, e.g. OEB010..OEB300")
        start, end = start.rstrip("$"), end.rstrip("$")
        codes.update(f for f in catalog.families_raw if start <= f.rstrip("$") <= end)
    if families is not None:
        for f in families:
            code = f if f.endswith("$") else f + "$"
            if code not in catalog.families_raw:
                raise Bc3Error(f"unknown parametric family {f!r}")
            codes.add(code)
    if chapter is None and range_ is None and families is None:
        raise Bc3Error("nothing selected: give a chapter, a range or family codes")
    return sorted(codes)


def iter_items(catalog: Catalog, family_codes: Iterable[str], include_invalid: bool = False,
               with_decomposition: bool = True, pricer: Pricer | None = None) -> Iterator[Item]:
    pricer = pricer or Pricer(catalog)
    for code in family_codes:
        family = catalog.family(code)
        for sel in selections(family):
            item = build_item(catalog, pricer, family, sel, with_decomposition)
            if item.valid or include_invalid:
                yield item


def resolve_code(catalog: Catalog, code: str, selection: Sequence[int] | None = None,
                 with_decomposition: bool = True) -> Item:
    """Resolve a derived code (``OEB020bbbaa``) or a family code plus selection."""
    if selection is None:
        try:
            family_code, selection = split_derived_code(code, catalog.families_raw)
        except ValueError as exc:
            raise Bc3Error(str(exc)) from None
    else:
        family_code = code if code.endswith("$") else code + "$"
        if family_code not in catalog.families_raw:
            raise Bc3Error(f"unknown parametric family {code!r}")
    family = catalog.family(family_code)
    counts = family.option_counts()
    if len(selection) != len(counts) or any(not 1 <= k <= n for k, n in zip(selection, counts)):
        raise Bc3Error(f"{code}: selection {selection} does not fit parameters with {counts} options")
    return build_item(catalog, Pricer(catalog), family, selection, with_decomposition)


def write_jsonl(items: Iterable[Item], fp: IO[str]) -> int:
    n = 0
    for item in items:
        fp.write(json.dumps(item.to_dict(), ensure_ascii=False) + "\n")
        n += 1
    return n


def write_json(items: Iterable[Item], fp: IO[str]) -> int:
    fp.write("[\n")
    n = 0
    for item in items:
        if n:
            fp.write(",\n")
        fp.write(json.dumps(item.to_dict(), ensure_ascii=False))
        n += 1
    fp.write("\n]\n")
    return n
