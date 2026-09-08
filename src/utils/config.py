"""Single-source-of-truth paths for the BC3CAT pipeline and BC3CAT-Syn sub-tree.

REPO_ROOT  -> DATA_ROOT  -> {RAW_DIR, INTERMEDIATE_DIR, PROCESSED_DIR, LLAMAINDEX_DIR,
                            SYNTHETIC_DATA_ROOT}
SYNTHETIC_DATA_ROOT -> {SYNTHETIC_INTERMEDIATE_DIR, SYNTHETIC_PROCESSED_DIR,
                       SYNTHETIC_VARIANTS_DIR}

Env-var overrides (loaded at import time):
  BC3CAT_DATA_ROOT            -> DATA_ROOT
  BC3CAT_SYNTHETIC_DATA_ROOT  -> SYNTHETIC_DATA_ROOT
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_ROOT = Path(os.environ.get("BC3CAT_DATA_ROOT", REPO_ROOT / "data"))
RAW_DIR          = DATA_ROOT / "raw"
INTERMEDIATE_DIR = DATA_ROOT / "intermediate"
PROCESSED_DIR    = DATA_ROOT / "processed"
LLAMAINDEX_DIR   = DATA_ROOT / "llamaindex"

SYNTHETIC_DATA_ROOT = Path(
    os.environ.get("BC3CAT_SYNTHETIC_DATA_ROOT", DATA_ROOT / "synthetic")
)
SYNTHETIC_INTERMEDIATE_DIR = SYNTHETIC_DATA_ROOT / "intermediate"
SYNTHETIC_PROCESSED_DIR    = SYNTHETIC_DATA_ROOT / "processed"
SYNTHETIC_VARIANTS_DIR     = SYNTHETIC_DATA_ROOT / "variants"
SYNTHETIC_REVIEW_DIR       = SYNTHETIC_DATA_ROOT / "review"

# --- LLM transport settings (A3a) -------------------------------------------
# Additive, env-overridable scalars/paths consumed by synthetic.llm_client.
# OpenAI-compatible /chat/completions contract: a single client covers the
# GPT-4-class API and local-Llama candidates by base URL + model id alone.
# LLM_API_KEY_ENV holds only the *name* of the env var carrying the key — the
# key value never lives in config, on disk, or in a log/exception.
LLM_BASE_URL     = os.environ.get("BC3CAT_LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL        = os.environ.get("BC3CAT_LLM_MODEL", "llama3.1:8b")
LLM_API_KEY_ENV  = os.environ.get("BC3CAT_LLM_API_KEY_ENV", "BC3CAT_LLM_API_KEY")
LLM_TIMEOUT      = float(os.environ.get("BC3CAT_LLM_TIMEOUT", "60"))
LLM_MAX_RETRIES  = int(os.environ.get("BC3CAT_LLM_MAX_RETRIES", "3"))
LLM_BACKOFF_BASE = float(os.environ.get("BC3CAT_LLM_BACKOFF_BASE", "0.5"))
LLM_TEMPERATURE  = float(os.environ.get("BC3CAT_LLM_TEMPERATURE", "0.0"))
LLM_CACHE_DIR    = Path(
    os.environ.get("BC3CAT_LLM_CACHE_DIR", SYNTHETIC_DATA_ROOT / "llm_cache")
)


def chapter_path(chapter: str, *, root: Path = INTERMEDIATE_DIR) -> Path:
    """`{root}/{chapter}/{chapter}.json` -- the s02-output flavour."""
    return root / chapter / f"{chapter}.json"


def stage_path(chapter: str, stage_n: int, *, root: Path = INTERMEDIATE_DIR) -> Path:
    """`{root}/{chapter}/{chapter}_stage{n}.json` -- s03+ flavour."""
    return root / chapter / f"{chapter}_stage{stage_n}.json"


class Config:
    """Back-compat shim for the original retrieval-side helpers."""
    DATA_DIR     = LLAMAINDEX_DIR
    TEXTO_PATH   = LLAMAINDEX_DIR / "IISS_plataforma_texto.pkl"
    RESUMEN_PATH = LLAMAINDEX_DIR / "IISS_plataforma_resumen.pkl"

    TOP_K        = 10
    NUM_SAMPLES  = 5

    BM25_K1      = 1.5
    BM25_B       = 0.75
