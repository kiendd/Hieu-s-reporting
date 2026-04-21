"""Shared pytest fixtures for llm_extractor tests."""
import pytest


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Isolate llm_extractor cache writes to a temp dir per test."""
    import llm_extractor
    monkeypatch.setattr(llm_extractor, "CACHE_DIR", tmp_path / ".llm_cache")
    (tmp_path / ".llm_cache").mkdir()
    return tmp_path / ".llm_cache"
