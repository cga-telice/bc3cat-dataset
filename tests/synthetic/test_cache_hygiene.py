"""Sprint 18 — Phase D Task D3: cache-hygiene enumeration + opt-in clearing.

All tests run against a `tmp_path` corpus; NONE touch the real `data/` tree.
`stale_cache_paths` is pure (enumerates, deletes nothing); `clear_caches`
defaults to dry-run and only unlinks when `dry_run=False`.
"""

import importlib

from synthetic import cache_hygiene
from synthetic.cache_hygiene import stale_cache_paths, clear_caches


def _plant(root):
    """Plant one of each stale-artefact kind under a tmp data root."""
    (root / "processed").mkdir(parents=True)
    pkl = root / "processed" / "OEB_long.pkl"
    pkl.write_text("x", encoding="utf-8")

    (root / "llamaindex").mkdir(parents=True)
    llama = root / "llamaindex" / "docstore.json"
    llama.write_text("{}", encoding="utf-8")

    chapter = root / "intermediate" / "OBRA CIVIL"
    chapter.mkdir(parents=True)
    chunk = chapter / "chunk_3.json"
    chunk.write_text("{}", encoding="utf-8")

    ckpt = chapter / ".ipynb_checkpoints"
    ckpt.mkdir()

    keep = root / "intermediate" / "OBRA CIVIL" / "OBRA_CIVIL_stage5.json"
    keep.write_text("{}", encoding="utf-8")
    return {"pkl": pkl, "llama": llama, "chunk": chunk, "ckpt": ckpt, "keep": keep}


# --------------------------------------------------------------------------
# Surface + hygiene
# --------------------------------------------------------------------------

def test_module_exposes_public_surface():
    assert set(cache_hygiene.__all__) == {"stale_cache_paths", "clear_caches"}
    assert callable(stale_cache_paths)
    assert callable(clear_caches)


def test_module_has_no_side_effects_at_import():
    reloaded = importlib.reload(cache_hygiene)
    assert callable(reloaded.clear_caches)


# --------------------------------------------------------------------------
# stale_cache_paths
# --------------------------------------------------------------------------

def test_stale_cache_paths_enumerates_expected(tmp_path):
    planted = _plant(tmp_path)
    found = set(stale_cache_paths(data_root=tmp_path))
    assert {planted["pkl"], planted["llama"], planted["chunk"], planted["ckpt"]} <= found
    assert planted["keep"] not in found  # stage5 JSON is a real artefact, not cache


def test_stale_cache_paths_empty_when_clean(tmp_path):
    (tmp_path / "intermediate").mkdir(parents=True)
    assert stale_cache_paths(data_root=tmp_path) == []


def test_stale_cache_paths_is_pure_no_delete(tmp_path):
    planted = _plant(tmp_path)
    stale_cache_paths(data_root=tmp_path)
    assert planted["pkl"].exists()
    assert planted["chunk"].exists()
    assert planted["ckpt"].is_dir()


def test_stale_cache_paths_sorted_and_deduped(tmp_path):
    _plant(tmp_path)
    out = stale_cache_paths(data_root=tmp_path)
    assert out == sorted(set(out))


# --------------------------------------------------------------------------
# clear_caches
# --------------------------------------------------------------------------

def test_clear_caches_dry_run_is_default(tmp_path):
    planted = _plant(tmp_path)
    returned = clear_caches(data_root=tmp_path)
    assert planted["pkl"].exists()
    assert planted["ckpt"].is_dir()
    assert set(returned) == set(stale_cache_paths(data_root=tmp_path))


def test_clear_caches_dry_run_deletes_nothing(tmp_path):
    planted = _plant(tmp_path)
    clear_caches(data_root=tmp_path, dry_run=True)
    assert all(p.exists() for p in planted.values())


def test_clear_caches_removes_planted_files(tmp_path):
    planted = _plant(tmp_path)
    clear_caches(data_root=tmp_path, dry_run=False)
    assert not planted["pkl"].exists()
    assert not planted["llama"].exists()
    assert not planted["chunk"].exists()
    assert planted["keep"].exists()  # untouched


def test_clear_caches_removes_checkpoint_dir(tmp_path):
    planted = _plant(tmp_path)
    clear_caches(data_root=tmp_path, dry_run=False)
    assert not planted["ckpt"].exists()


def test_clear_caches_returns_candidate_list(tmp_path):
    _plant(tmp_path)
    before = set(stale_cache_paths(data_root=tmp_path))
    returned = set(clear_caches(data_root=tmp_path, dry_run=False))
    assert returned == before
