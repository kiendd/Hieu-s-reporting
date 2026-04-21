"""Shared pytest fixtures for llm_extractor tests."""
import pytest


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Isolate llm_extractor cache writes to a temp dir per test."""
    import llm_extractor
    monkeypatch.setattr(llm_extractor, "CACHE_DIR", tmp_path / ".llm_cache")
    (tmp_path / ".llm_cache").mkdir()
    return tmp_path / ".llm_cache"


@pytest.fixture
def fake_openai(monkeypatch):
    """Build a fake OpenAI client whose chat.completions.create returns
    canned JSON. Tests control the response via `.queue` (list of dicts
    to return in order) or `.error` (exception instance to raise once).
    """
    import json
    import llm_extractor

    class _FakeCompletions:
        def __init__(self):
            self.queue: list = []
            self.error = None
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.error is not None:
                err = self.error
                self.error = None   # raise once, then stop
                raise err
            if not self.queue:
                raise AssertionError("fake_openai: no queued response")
            payload = self.queue.pop(0)

            class _Msg:
                def __init__(self, c): self.content = c
            class _Choice:
                def __init__(self, c): self.message = _Msg(c)
            class _Resp:
                def __init__(self, c): self.choices = [_Choice(c)]
            return _Resp(json.dumps(payload))

    class _FakeChat:
        def __init__(self):
            self.completions = _FakeCompletions()

    class _FakeClient:
        def __init__(self):
            self.chat = _FakeChat()

    fake = _FakeClient()
    monkeypatch.setattr(llm_extractor, "_get_client", lambda: fake)
    return fake
