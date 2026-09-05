"""Command line interface: bc3param validate | inspect | resolve | generate."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Sequence

from .fiebdc import Bc3Error, Catalog
from .generate import iter_items, resolve_code, select_families, write_json, write_jsonl
from .param.parser import ParseError


def _load(path: str) -> Catalog:
    p = Path(path)
    if not p.is_file():
        raise Bc3Error(f"file not found: {path}")
    return Catalog.load(p)


def cmd_validate(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    codes = [args.family] if args.family else catalog.families
    errors: list[ParseError] = []
    warnings = 0
    for code in codes:
        try:
            family = catalog.family(code)
        except ParseError as exc:
            errors.append(exc)
            continue
        for w in family.warnings:
            warnings += 1
            print(f"warning: {code} {w}")
    for exc in errors:
        print(f"{exc.family} line {exc.line_no}: {exc.message}")
    print(f"{len(codes)} families, {len(errors)} errors, {warnings} warnings")
    return 1 if errors else 0


def cmd_inspect(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    family = catalog.family(args.family if args.family.endswith("$") else args.family + "$")
    concept = catalog.concept(family.code)
    print(f"{family.code}  {concept.unit if concept else ''}  {concept.summary if concept else ''}")
    print("chapters: " + " > ".join(catalog.chapter_path(family.code)))
    for p in family.params:
        print(f"{p.var}  {p.name}")
        for i, opt in enumerate(p.options, 1):
            print(f"    {i}: {opt!r}")
    kinds: dict[str, int] = {}
    for st in family.statements:
        kinds[type(st).__name__] = kinds.get(type(st).__name__, 0) + 1
    print("statements: " + ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    print(f"combinations: {math.prod(family.option_counts())}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    selection = tuple(int(x) for x in args.select.split(",")) if args.select else None
    item = resolve_code(catalog, args.code, selection, with_decomposition=not args.no_decomposition)
    print(json.dumps(item.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    catalog = _load(args.file)
    codes = select_families(catalog, chapter=args.chapter, range_=args.range,
                            families=args.family or None)
    print(f"{len(codes)} families selected", file=sys.stderr)

    def items():
        n = 0
        for code in codes:
            print(f"  {code}", file=sys.stderr)
            for item in iter_items(catalog, [code], include_invalid=args.include_invalid,
                                   with_decomposition=not args.no_decomposition):
                if args.limit is not None and n >= args.limit:
                    return
                n += 1
                yield item

    writer = write_json if args.format == "json" else write_jsonl
    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as fp:
            count = writer(items(), fp)
    else:
        count = writer(items(), sys.stdout)
    print(f"{count} items written", file=sys.stderr)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bc3param", description="Parametric FIEBDC-3 catalogue engine")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="parse every ~P family and report errors")
    p.add_argument("file")
    p.add_argument("--family", help="only this family code")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("inspect", help="show parameters and options of a family")
    p.add_argument("file")
    p.add_argument("family")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("resolve", help="resolve one derived code or family+selection")
    p.add_argument("file")
    p.add_argument("code", help="derived code (OEB020bbbaa) or family code (OEB020$) with -s")
    p.add_argument("-s", "--select", help="1-based option numbers, e.g. 2,2,2,1,1")
    p.add_argument("--no-decomposition", action="store_true")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("generate", help="expand families to JSON/JSONL")
    p.add_argument("file")
    p.add_argument("--chapter", help="chapter code, e.g. OEB# (recursive)")
    p.add_argument("--range", help="START..END on family stems, e.g. OEB010..OEB300")
    p.add_argument("--family", action="append", help="family code (repeatable)")
    p.add_argument("--out", help="output path (default: stdout)")
    p.add_argument("--format", choices=["jsonl", "json"], default="jsonl")
    p.add_argument("--include-invalid", action="store_true")
    p.add_argument("--no-decomposition", action="store_true")
    p.add_argument("--limit", type=int)
    p.set_defaults(func=cmd_generate)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, AttributeError):  # pragma: no cover
                pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (Bc3Error, ParseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
