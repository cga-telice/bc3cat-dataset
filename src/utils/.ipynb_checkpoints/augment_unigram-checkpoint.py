# /work/src/utils/augment_unigram.py
from __future__ import annotations
import re
from typing import Iterable, List
import numpy as np
import pandas as pd

ALNUM_RE = re.compile(r"^[a-z0-9_]+$", re.UNICODE)
NUM_RE   = re.compile(r"^\d+(?:\.\d+)?(?:x\d+(?:\.\d+)?)*$")  # supports 4x40x2

def as_list(x) -> List[str]:
    """Coerce scalars/arrays/NaN to a clean Python list[str]."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, (tuple, set)):
        return list(x)
    if isinstance(x, (pd.Series, pd.Index, np.ndarray)):
        return [t for t in x.tolist() if t is not None and not (isinstance(t, float) and pd.isna(t))]
    if isinstance(x, float) and pd.isna(x):
        return []
    return [x]

def _safe(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace(" ", "_").replace(".", "_").replace("%", "pct")
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def _is_alpha(tok: str) -> bool:
    # consider it alpha if it has any letter after removing digits/underscores
    t = re.sub(r"[_0-9]+", "", tok or "")
    return bool(t)

def build_aug_tokens(
    tokens_word: Iterable[str],
    param_values_multi_norm: Iterable[str] | None,
) -> List[str]:
    """
    Returns a *set-like* list of pseudo-tokens:
      - param_* from param_values_multi_norm
      - num_*, numprev_*, numnext_* from tokens_word context
    """
    toks = as_list(tokens_word)
    out = set()

    # parameters → param_*
    for p in as_list(param_values_multi_norm):
        sp = _safe(str(p))
        if sp:
            out.add(f"param_{sp}")

    # numbers + context
    n = len(toks)
    for i, t in enumerate(toks):
        if not isinstance(t, str):
            t = "" if t is None else str(t)
        raw = t.lower()
        if not NUM_RE.match(raw):
            continue

        snum = _safe(raw)
        if snum:
            out.add(f"num_{snum}")

        prev_tok = toks[i-1].lower() if i-1 >= 0 else ""
        next_tok = toks[i+1].lower() if i+1 < n else ""

        if prev_tok and _is_alpha(prev_tok):
            out.add(f"numprev_{_safe(prev_tok)}_{snum}")
        if next_tok and _is_alpha(next_tok):
            out.add(f"numnext_{snum}_{_safe(next_tok)}")

    return list(out)

def make_augmented_text_word(
    text_word: str,
    tokens_word: Iterable[str],
    param_values_multi_norm: Iterable[str] | None,
) -> str:
    """
    Append the pseudo-tokens to the existing unigram string.
    """
    base = (text_word or "").strip()
    aug = build_aug_tokens(tokens_word, param_values_multi_norm)
    if not aug:
        return base
    return (base + " " + " ".join(sorted(set(aug)))).strip()
