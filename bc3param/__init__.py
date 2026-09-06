"""bc3param: parametric FIEBDC-3 catalogue engine."""
from __future__ import annotations

from .fiebdc import Bc3Error, Catalog
from .generate import build_item, iter_items, resolve_code, select_families, write_json, write_jsonl
from .model import DecompLine, Item, ParameterChoice
from .param.evaluator import EvalError, Evaluator
from .param.parser import ParseError
from .pricing import Pricer

__version__ = "0.1.0"
__all__ = [
    "Bc3Error", "Catalog", "DecompLine", "EvalError", "Evaluator", "Item", "ParameterChoice",
    "ParseError", "Pricer", "build_item", "iter_items", "resolve_code", "select_families",
    "write_json", "write_jsonl",
]
