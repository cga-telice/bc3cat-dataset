"""Tests for `utils.config` — the single-source-of-truth paths module."""
import importlib
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _restore_config_module():
    """After every test, reload `utils.config` against the restored environment.

    Tests in this module use `monkeypatch.setenv(...)` followed by
    `importlib.reload(config)`. monkeypatch's teardown restores the env var,
    but the module still holds the override values until reloaded. This
    autouse fixture has no fixture dependencies, so its teardown runs after
    monkeypatch's — at which point one final reload returns the module to
    its default state for any later test in the session.
    """
    yield
    from utils import config as _cfg
    importlib.reload(_cfg)


# ---------------------------------------------------------------------------
# Bullet 1: every advertised public symbol imports.
# ---------------------------------------------------------------------------
def test_public_surface_imports():
    from utils.config import (  # noqa: F401
        REPO_ROOT,
        DATA_ROOT,
        RAW_DIR,
        INTERMEDIATE_DIR,
        PROCESSED_DIR,
        LLAMAINDEX_DIR,
        SYNTHETIC_DATA_ROOT,
        SYNTHETIC_INTERMEDIATE_DIR,
        SYNTHETIC_PROCESSED_DIR,
        SYNTHETIC_VARIANTS_DIR,
        chapter_path,
        stage_path,
        Config,
    )


# ---------------------------------------------------------------------------
# Bullet 2: all path constants are pathlib.Path instances.
# ---------------------------------------------------------------------------
def test_all_path_constants_are_path_instances(monkeypatch):
    monkeypatch.delenv("BC3CAT_DATA_ROOT", raising=False)
    monkeypatch.delenv("BC3CAT_SYNTHETIC_DATA_ROOT", raising=False)
    from utils import config
    importlib.reload(config)

    for name in (
        "REPO_ROOT",
        "DATA_ROOT",
        "RAW_DIR",
        "INTERMEDIATE_DIR",
        "PROCESSED_DIR",
        "LLAMAINDEX_DIR",
        "SYNTHETIC_DATA_ROOT",
        "SYNTHETIC_INTERMEDIATE_DIR",
        "SYNTHETIC_PROCESSED_DIR",
        "SYNTHETIC_VARIANTS_DIR",
    ):
        assert isinstance(getattr(config, name), Path), name


# ---------------------------------------------------------------------------
# Bullet 3: default DATA_ROOT derives from REPO_ROOT.
# ---------------------------------------------------------------------------
def test_data_root_default(monkeypatch):
    monkeypatch.delenv("BC3CAT_DATA_ROOT", raising=False)
    from utils import config
    importlib.reload(config)

    assert config.DATA_ROOT == config.REPO_ROOT / "data"
    assert config.RAW_DIR == config.DATA_ROOT / "raw"
    assert config.INTERMEDIATE_DIR == config.DATA_ROOT / "intermediate"
    assert config.PROCESSED_DIR == config.DATA_ROOT / "processed"
    assert config.LLAMAINDEX_DIR == config.DATA_ROOT / "llamaindex"


# ---------------------------------------------------------------------------
# Bullet 4: BC3CAT_DATA_ROOT env override is picked up at reload time, and
# all four sub-dirs follow it.
# ---------------------------------------------------------------------------
def test_data_root_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("BC3CAT_DATA_ROOT", str(tmp_path))
    monkeypatch.delenv("BC3CAT_SYNTHETIC_DATA_ROOT", raising=False)
    from utils import config
    importlib.reload(config)

    assert config.DATA_ROOT == tmp_path
    assert config.RAW_DIR == tmp_path / "raw"
    assert config.INTERMEDIATE_DIR == tmp_path / "intermediate"
    assert config.PROCESSED_DIR == tmp_path / "processed"
    assert config.LLAMAINDEX_DIR == tmp_path / "llamaindex"
    # SYNTHETIC_DATA_ROOT defaults under the overridden DATA_ROOT.
    assert config.SYNTHETIC_DATA_ROOT == tmp_path / "synthetic"


# ---------------------------------------------------------------------------
# Bullet 5: SYNTHETIC_DATA_ROOT default + its own env override.
# ---------------------------------------------------------------------------
def test_synthetic_data_root_default(monkeypatch):
    monkeypatch.delenv("BC3CAT_DATA_ROOT", raising=False)
    monkeypatch.delenv("BC3CAT_SYNTHETIC_DATA_ROOT", raising=False)
    from utils import config
    importlib.reload(config)

    assert config.SYNTHETIC_DATA_ROOT == config.DATA_ROOT / "synthetic"
    assert config.SYNTHETIC_INTERMEDIATE_DIR == config.SYNTHETIC_DATA_ROOT / "intermediate"
    assert config.SYNTHETIC_PROCESSED_DIR == config.SYNTHETIC_DATA_ROOT / "processed"
    assert config.SYNTHETIC_VARIANTS_DIR == config.SYNTHETIC_DATA_ROOT / "variants"


def test_synthetic_data_root_env_override(monkeypatch, tmp_path):
    monkeypatch.delenv("BC3CAT_DATA_ROOT", raising=False)
    monkeypatch.setenv("BC3CAT_SYNTHETIC_DATA_ROOT", str(tmp_path))
    from utils import config
    importlib.reload(config)

    assert config.SYNTHETIC_DATA_ROOT == tmp_path
    assert config.SYNTHETIC_INTERMEDIATE_DIR == tmp_path / "intermediate"
    assert config.SYNTHETIC_PROCESSED_DIR == tmp_path / "processed"
    assert config.SYNTHETIC_VARIANTS_DIR == tmp_path / "variants"
    # DATA_ROOT stays on its default.
    assert config.DATA_ROOT == config.REPO_ROOT / "data"


# ---------------------------------------------------------------------------
# Bullet 6: chapter_path helper, default and synthetic roots.
# ---------------------------------------------------------------------------
def test_chapter_path_default_root():
    from utils.config import chapter_path, INTERMEDIATE_DIR

    expected = INTERMEDIATE_DIR / "OBRA CIVIL" / "OBRA CIVIL.json"
    assert chapter_path("OBRA CIVIL") == expected


def test_chapter_path_synthetic_root():
    from utils.config import chapter_path, SYNTHETIC_INTERMEDIATE_DIR

    p = chapter_path("OBRA CIVIL", root=SYNTHETIC_INTERMEDIATE_DIR)
    assert p == SYNTHETIC_INTERMEDIATE_DIR / "OBRA CIVIL" / "OBRA CIVIL.json"
    assert "synthetic" in p.parts


# ---------------------------------------------------------------------------
# Bullet 7: stage_path helper, default and synthetic roots.
# ---------------------------------------------------------------------------
def test_stage_path_default_root():
    from utils.config import stage_path, INTERMEDIATE_DIR

    expected = INTERMEDIATE_DIR / "OBRA CIVIL" / "OBRA CIVIL_stage5.json"
    assert stage_path("OBRA CIVIL", 5) == expected


def test_stage_path_synthetic_root():
    from utils.config import stage_path, SYNTHETIC_INTERMEDIATE_DIR

    p = stage_path("OBRA CIVIL", 3, root=SYNTHETIC_INTERMEDIATE_DIR)
    assert p == SYNTHETIC_INTERMEDIATE_DIR / "OBRA CIVIL" / "OBRA CIVIL_stage3.json"
    assert "synthetic" in p.parts


# ---------------------------------------------------------------------------
# Bullet 8: Config back-compat shim is routed through LLAMAINDEX_DIR.
# No /work/ literal anywhere in the module.
# ---------------------------------------------------------------------------
def test_config_backcompat_shim():
    from utils.config import Config, LLAMAINDEX_DIR

    assert Config.DATA_DIR == LLAMAINDEX_DIR
    assert Config.TEXTO_PATH == LLAMAINDEX_DIR / "IISS_plataforma_texto.pkl"
    assert Config.RESUMEN_PATH == LLAMAINDEX_DIR / "IISS_plataforma_resumen.pkl"
    # Numeric defaults are preserved from the original class.
    assert Config.TOP_K == 10
    assert Config.NUM_SAMPLES == 5
    assert Config.BM25_K1 == 1.5
    assert Config.BM25_B == 0.75


def test_no_work_literal_in_module():
    import utils.config as cfg
    source = Path(cfg.__file__).read_text(encoding="utf-8")
    assert "/work/" not in source, "config.py must not contain the /work/ literal"
