# LLM-based Report Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace regex-based ASM/TTTC report parsing with an LLM extractor using the OpenAI SDK, with disk cache and golden-file tests.

**Architecture:** New `llm_extractor.py` owns LLM calls, disk cache, stats. Existing `detect_asm_reports` kept as cheap pre-filter; all regex parsers (`parse_asm_report`, `parse_tttc_report`, `_extract_sections`, `classify_report`, TTTC regex constants) are deleted. Downstream (`analyze_*`, `write_asm_excel`, `check_asm_compliance`, `app.py` UI) adapted to the new 1-to-N `Report` schema discriminated by `report_type`.

**Tech Stack:** Python 3.11+, `openai>=1.0` SDK, OpenAI JSON mode, `pytest` + `pytest-mock` (dev-only), Streamlit 1.36+.

**Spec:** [`docs/superpowers/specs/2026-04-21-llm-report-extraction-design.md`](../specs/2026-04-21-llm-report-extraction-design.md)

---

## File Structure

**New files:**
- `llm_extractor.py` — LLM client, prompt, cache, stats, `Report` schema, `extract_reports()`.
- `requirements-dev.txt` — `pytest`, `pytest-mock` (prod `requirements.txt` gains `openai>=1.0` only).
- `tests/__init__.py` — empty package marker.
- `tests/conftest.py` — shared fixtures (fake OpenAI client, temp cache dir).
- `tests/test_llm_extractor.py` — unit tests for cache / validation / retry / stub.
- `tests/test_templates.py` — golden-file tests driven by `templates/*/N` files.
- `templates/daily/1.expected.json` … `templates/weekend/8.expected.json` — 15 golden files (created iteratively).
- `.llm_cache/.gitkeep` — keep dir in tree but contents ignored.

**Modified files:**
- `fpt_chat_stats.py` — delete regex parsers (~300 lines removed at lines 265, 298, 344, 390, 436–540, plus helpers); add `extract_all_reports()` orchestrator; adapt `analyze_asm_reports`, `analyze_tttc_reports`, `check_asm_compliance`, `analyze_multiday`, `write_asm_excel`, weekly dispatch (lines 980–1002), `main()` to new schema; add `--llm-base-url`, `--llm-model` CLI flags.
- `app.py` — sidebar inputs for LLM URL/model/key; `localStorage` keys `fpt_llm_base_url`, `fpt_llm_model`, `fpt_llm_api_key`; stats `st.caption()` after run; unparseable-report rendering block.
- `requirements.txt` — add `openai>=1.0`.
- `.gitignore` — add `.llm_cache/` and `requirements-dev.txt`? No — `requirements-dev.txt` is checked in. Only `.llm_cache/*` (except `.gitkeep`) ignored.
- `config.example.json` — add `llm.base_url` and `llm.model` examples (never `llm.api_key`).
- `CLAUDE.md` — update Commands (pytest), Architecture (llm_extractor section), replace the regex-pipeline narrative.
- `openspec/specs/fpt-chat-stats/spec.md` — update parsing sections OR proposal a new OpenSpec change under `openspec/changes/<id>/` (decision left to Task 18).

**Deleted from `fpt_chat_stats.py`:**
- `classify_report` (line 265)
- `_parse_vnd_amount` (line 298)
- `_extract_sections` (line 344)
- `parse_asm_report` (line 390)
- TTTC regex constants and helpers (lines 436–540): `_TTTC_VENUE_RE`, `_TTTC_REVENUE_PCT_RE`, `_TTTC_HOT_PCT_RE`, `_TTTC_HOT_RATIO_RE`, `_TTTC_TB_BILL_VALUE_RE`, `_TTTC_CUSTOMER_RE`, `_TTTC_NARRATIVE_BOUNDARY_RE`, `_first_n_lines`, `_to_pct`, `_tttc_metrics_area`.
- `parse_tttc_report` (line 540)

---

## Conventions for this plan

- **TDD**: every task writes a failing test first, then minimal code, then verifies pass.
- **Commit after every task.** Commit message style follows existing repo convention (Vietnamese, lowercase prefix like `feat/`, `fix/`, `refactor/`, `test/`, `docs/`).
- **Run the test command literally as shown.** Expected output is specified; stop and investigate if actual differs.
- **All paths absolute or relative to repo root** (`/Users/phudq/DC5/Hieu-s-reporting/` or CWD = repo root).

---

## Task 1: Add dev tooling and pytest scaffolding

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `pytest.ini`
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Create `requirements-dev.txt`**

```
pytest>=8.0
pytest-mock>=3.12
```

- [ ] **Step 2: Add `openai>=1.0` to `requirements.txt`**

Append a single line:
```
openai>=1.0
```

- [ ] **Step 3: Create `pytest.ini` at repo root**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty file).

- [ ] **Step 5: Create `tests/conftest.py` with a placeholder fixture**

```python
"""Shared pytest fixtures for llm_extractor tests."""
import pytest


@pytest.fixture
def sanity():
    """Placeholder fixture proving pytest is wired."""
    return "ok"
```

- [ ] **Step 6: Add a smoke test in `tests/test_llm_extractor.py`**

```python
"""Smoke test — verifies pytest runs before any real code exists."""


def test_pytest_runs(sanity):
    assert sanity == "ok"
```

- [ ] **Step 7: Modify `.gitignore` — add two lines**

```
.llm_cache/*
!.llm_cache/.gitkeep
```

(`.llm_cache/*` ignores the contents; the negation preserves `.gitkeep` so the empty directory lives in the tree. `.llm_cache/` without the `*` would exclude the directory itself and make the negation a no-op in some git versions.)

- [ ] **Step 8: Create `.llm_cache/.gitkeep`** (empty file).

- [ ] **Step 9: Install dev deps and run the smoke test**

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -v
```
Expected: `tests/test_llm_extractor.py::test_pytest_runs PASSED` (1 passed).

- [ ] **Step 10: Commit**

```bash
git add requirements.txt requirements-dev.txt pytest.ini tests/ .gitignore .llm_cache/.gitkeep
git commit -m "chore: scaffolding pytest + openai dep + .llm_cache dir"
```

---

## Task 2: `Report` TypedDict + skeleton `llm_extractor.py`

**Files:**
- Create: `llm_extractor.py`
- Modify: `tests/test_llm_extractor.py`

- [ ] **Step 1: Write failing test for `Report` shape + `PROMPT_VERSION`**

Append to `tests/test_llm_extractor.py`:
```python
from llm_extractor import Report, PROMPT_VERSION


def test_report_typeddict_fields_present():
    # A well-formed daily report — verifies the structural keys exist.
    r: Report = {
        "report_type": "daily_shop_vt",
        "shop_ref": "80035 173 Hùng Vương",
        "sender": "Alice",
        "sender_id": "u1",
        "sent_at": "2026-04-21T10:00:00Z",
        "message_id": "m1",
        "source": "llm",
        "parse_error": None,
        "deposit_count": 12,
        "ra_tiem_count": 2,
        "kh_tu_van_count": 214,
        "tich_cuc": "ok",
        "van_de": None,
        "da_lam": None,
        "revenue_pct": None,
        "hot_pct": None,
        "hot_ratio_pct": None,
        "tb_bill_vnd": None,
        "customer_count": None,
    }
    assert r["report_type"] == "daily_shop_vt"


def test_prompt_version_is_v1():
    assert PROMPT_VERSION == "v1"
```

- [ ] **Step 2: Run test, verify failure**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: `ModuleNotFoundError: No module named 'llm_extractor'`.

- [ ] **Step 3: Create `llm_extractor.py` with the schema**

```python
"""LLM-based extraction of ASM / TTTC reports from Vietnamese chat messages.

Replaces the regex parsers in fpt_chat_stats.py.  Uses the OpenAI SDK
with a configurable base_url so any OpenAI-compatible provider works
(OpenAI, Azure, Ollama, vLLM, LiteLLM, ...).
"""
from __future__ import annotations

from typing import Literal, TypedDict


PROMPT_VERSION = "v1"


class Report(TypedDict):
    # Common
    report_type: Literal["daily_shop_vt", "weekend_tttc", "unknown"]
    shop_ref: str | None
    sender: str
    sender_id: str
    sent_at: str
    message_id: str
    source: Literal["llm", "cache"]
    parse_error: str | None

    # daily_shop_vt fields
    deposit_count: int | None
    ra_tiem_count: int | None
    kh_tu_van_count: int | None
    tich_cuc: str | None
    van_de: str | None
    da_lam: str | None

    # weekend_tttc fields
    revenue_pct: float | None
    hot_pct: float | None
    hot_ratio_pct: float | None
    tb_bill_vnd: int | None
    customer_count: int | None
```

- [ ] **Step 4: Run test, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add llm_extractor.py tests/test_llm_extractor.py
git commit -m "feat(llm): thêm Report TypedDict + PROMPT_VERSION cho llm_extractor"
```

---

## Task 3: Disk cache primitives

**Files:**
- Modify: `llm_extractor.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_llm_extractor.py`

- [ ] **Step 1: Add `tmp_cache` fixture to `tests/conftest.py`**

```python
import pytest


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Isolate llm_extractor cache writes to a temp dir per test."""
    import llm_extractor
    monkeypatch.setattr(llm_extractor, "CACHE_DIR", tmp_path / ".llm_cache")
    (tmp_path / ".llm_cache").mkdir()
    return tmp_path / ".llm_cache"
```

(Remove the old `sanity` fixture and its test; they were scaffolding.)

- [ ] **Step 2: Update `tests/test_llm_extractor.py`**

Remove `test_pytest_runs` and `sanity` fixture references. Append:

```python
from pathlib import Path

from llm_extractor import (
    _cache_key, _load_cache, _save_cache, CACHE_DIR,
)


def test_cache_key_is_stable():
    k1 = _cache_key("hello world")
    k2 = _cache_key("hello world")
    assert k1 == k2
    assert k1.endswith(f"_{__import__('llm_extractor').PROMPT_VERSION}")


def test_cache_key_differs_for_different_content():
    assert _cache_key("a") != _cache_key("b")


def test_save_and_load_cache_roundtrip(tmp_cache):
    payload = [{"report_type": "daily_shop_vt", "shop_ref": "S1"}]
    _save_cache("some content", payload)
    loaded = _load_cache("some content")
    assert loaded == payload


def test_load_cache_miss_returns_none(tmp_cache):
    assert _load_cache("never seen") is None


def test_cache_filename_uses_16_hex_prefix(tmp_cache):
    _save_cache("x", [{"k": 1}])
    files = list(tmp_cache.iterdir())
    assert len(files) == 1
    # <16-hex>_<prompt_version>.json
    name = files[0].name
    assert len(name.split("_")[0]) == 16
    assert name.endswith(".json")
```

- [ ] **Step 3: Run tests, verify failure**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: `ImportError` / `AttributeError` for missing symbols.

- [ ] **Step 4: Implement cache in `llm_extractor.py`**

Append:

```python
import hashlib
import json
from pathlib import Path


CACHE_DIR = Path(".llm_cache")


def _cache_key(content: str) -> str:
    """Full logical key: sha256 hex + prompt version."""
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"{h}_{PROMPT_VERSION}"


def _cache_path(content: str) -> Path:
    """On-disk filename uses truncated (16-hex-char) sha256 for readability."""
    h = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{h[:16]}_{PROMPT_VERSION}.json"


def _load_cache(content: str) -> list[dict] | None:
    path = _cache_path(content)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    # Sanity: collision guard via full hash stored in file header
    full_key = _cache_key(content)
    if data.get("_cache_key") != full_key:
        return None
    return data["reports"]


def _save_cache(content: str, reports: list[dict]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(content)
    payload = {"_cache_key": _cache_key(content), "reports": reports}
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 5: Run tests, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 5 passed (cache tests) + 2 passed (Report + PROMPT_VERSION) = 7 passed.

- [ ] **Step 6: Commit**

```bash
git add llm_extractor.py tests/conftest.py tests/test_llm_extractor.py
git commit -m "feat(llm): disk cache keyed bằng sha256 + prompt_version"
```

---

## Task 4: Stats counters

**Files:**
- Modify: `llm_extractor.py`
- Modify: `tests/test_llm_extractor.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_llm_extractor.py`:

```python
import llm_extractor as le


def test_stats_start_at_zero():
    le._reset_stats()
    assert le.get_stats() == {"llm_call": 0, "llm_cached": 0, "llm_error": 0}


def test_stats_format_string():
    le._reset_stats()
    le._stats["llm_call"] = 3
    le._stats["llm_cached"] = 17
    le._stats["llm_error"] = 0
    msg = le.format_stats()
    assert "llm_call=3" in msg
    assert "cached=17" in msg
    assert "85%" in msg  # 17 / (17+3) = 0.85
```

- [ ] **Step 2: Run tests, verify failure**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: `AttributeError` for `_stats`, `_reset_stats`, `get_stats`, `format_stats`.

- [ ] **Step 3: Implement stats in `llm_extractor.py`**

Append:

```python
_stats = {"llm_call": 0, "llm_cached": 0, "llm_error": 0}


def _reset_stats() -> None:
    for k in _stats:
        _stats[k] = 0


def get_stats() -> dict[str, int]:
    return dict(_stats)


def format_stats() -> str:
    total = _stats["llm_call"] + _stats["llm_cached"]
    if total == 0:
        hit = 0
    else:
        hit = int(round(100 * _stats["llm_cached"] / total))
    return (f"[llm] llm_call={_stats['llm_call']} "
            f"cached={_stats['llm_cached']} "
            f"error={_stats['llm_error']} "
            f"— cache hit rate {hit}%")
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add llm_extractor.py tests/test_llm_extractor.py
git commit -m "feat(llm): stats counter + format cho CLI/UI"
```

---

## Task 5: Prompt constant + response validator

**Files:**
- Modify: `llm_extractor.py`
- Modify: `tests/test_llm_extractor.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_llm_extractor.py`:

```python
import pytest

from llm_extractor import (
    SYSTEM_PROMPT, LLMParseError, _validate_and_coerce,
)


def test_system_prompt_mentions_both_report_types():
    assert "daily_shop_vt" in SYSTEM_PROMPT
    assert "weekend_tttc" in SYSTEM_PROMPT


def test_validate_accepts_well_formed_response():
    raw = {
        "reports": [
            {"report_type": "daily_shop_vt", "shop_ref": "S1",
             "deposit_count": 12, "ra_tiem_count": 2,
             "kh_tu_van_count": 214,
             "tich_cuc": "ok", "van_de": None, "da_lam": None,
             "revenue_pct": None, "hot_pct": None, "hot_ratio_pct": None,
             "tb_bill_vnd": None, "customer_count": None},
        ],
        "unparseable": False,
        "reason": None,
    }
    out = _validate_and_coerce(raw)
    assert len(out) == 1
    assert out[0]["report_type"] == "daily_shop_vt"


def test_validate_returns_empty_for_unparseable():
    raw = {"reports": [], "unparseable": True, "reason": "greeting"}
    assert _validate_and_coerce(raw) == []


def test_validate_coerces_string_numeric():
    raw = {
        "reports": [
            {"report_type": "weekend_tttc", "shop_ref": "T1",
             "revenue_pct": "133", "hot_pct": None, "hot_ratio_pct": None,
             "tb_bill_vnd": None, "customer_count": None,
             "deposit_count": None, "ra_tiem_count": None,
             "kh_tu_van_count": None, "tich_cuc": None,
             "van_de": None, "da_lam": None},
        ],
        "unparseable": False, "reason": None,
    }
    out = _validate_and_coerce(raw)
    assert out[0]["revenue_pct"] == 133.0


def test_validate_rejects_bad_report_type():
    raw = {
        "reports": [{"report_type": "garbage", "shop_ref": None}],
        "unparseable": False, "reason": None,
    }
    with pytest.raises(LLMParseError):
        _validate_and_coerce(raw)


def test_validate_rejects_missing_reports_field():
    with pytest.raises(LLMParseError):
        _validate_and_coerce({"unparseable": False})
```

- [ ] **Step 2: Run tests, verify failure**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: import errors for `SYSTEM_PROMPT`, `LLMParseError`, `_validate_and_coerce`.

- [ ] **Step 3: Implement prompt + validator in `llm_extractor.py`**

Append:

```python
SYSTEM_PROMPT = """\
You extract structured data from Vietnamese chat messages reporting
ASM (Area Sales Manager) activity at FPT Long Chau vaccine shops.

A single message may contain one OR more reports. Two report types:
  - daily_shop_vt: Shop vệ tinh daily report (Mon-Fri).
    Key signals: "Shop:", cọc count, KH tư vấn, ra tiêm, sections
    "đã làm / tích cực / vấn đề".
  - weekend_tttc: TTTC center weekend report (Sat-Sun).
    Key signals: "TTTC:" or "VX HCM", DT/Doanh thu %, HOT %, TB bill,
    "điểm sáng / giải pháp".

Return ONLY valid JSON matching this schema:
{
  "reports": [
    {
      "report_type": "daily_shop_vt" | "weekend_tttc",
      "shop_ref": string | null,
      "deposit_count": int | null,
      "ra_tiem_count": int | null,
      "kh_tu_van_count": int | null,
      "tich_cuc": string | null,
      "van_de": string | null,
      "da_lam": string | null,
      "revenue_pct": float | null,
      "hot_pct": float | null,
      "hot_ratio_pct": float | null,
      "tb_bill_vnd": int | null,
      "customer_count": int | null
    }
  ],
  "unparseable": boolean,
  "reason": string | null
}

Rules:
- Preserve Vietnamese text in narrative fields.
- VND: "2,2tr" or "2.2M" → 2200000; "134.927.000" → 134927000.
- Percentages: drop "%" sign, numeric only ("133%" → 133.0).
- Never invent values. Missing → null.
- Greetings ("Dear Anh, Chị") are NOT shop_ref.
"""


class LLMParseError(Exception):
    """Raised when LLM response cannot be validated against the schema."""


_VALID_TYPES = {"daily_shop_vt", "weekend_tttc"}
_NUMERIC_INT_FIELDS = (
    "deposit_count", "ra_tiem_count", "kh_tu_van_count",
    "tb_bill_vnd", "customer_count",
)
_NUMERIC_FLOAT_FIELDS = ("revenue_pct", "hot_pct", "hot_ratio_pct")
_STRING_FIELDS = ("shop_ref", "tich_cuc", "van_de", "da_lam")


def _coerce_int(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and v.strip():
        try:
            return int(float(v.replace(",", ".")))
        except ValueError:
            raise LLMParseError(f"cannot coerce int: {v!r}")
    raise LLMParseError(f"cannot coerce int: {v!r}")


def _coerce_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str) and v.strip():
        try:
            return float(v.replace(",", "."))
        except ValueError:
            raise LLMParseError(f"cannot coerce float: {v!r}")
    raise LLMParseError(f"cannot coerce float: {v!r}")


def _validate_and_coerce(raw: dict) -> list[dict]:
    """Validate LLM JSON response, coerce types, return list of extraction
    dicts (without per-message metadata; caller rehydrates)."""
    if not isinstance(raw, dict) or "reports" not in raw:
        raise LLMParseError("missing 'reports' field")
    if raw.get("unparseable") is True:
        return []
    reports = raw["reports"]
    if not isinstance(reports, list):
        raise LLMParseError("'reports' is not a list")

    out: list[dict] = []
    for i, r in enumerate(reports):
        if not isinstance(r, dict):
            raise LLMParseError(f"report[{i}] is not a dict")
        rtype = r.get("report_type")
        if rtype not in _VALID_TYPES:
            raise LLMParseError(f"report[{i}] bad report_type: {rtype!r}")
        cleaned = {"report_type": rtype}
        for fld in _STRING_FIELDS:
            v = r.get(fld)
            cleaned[fld] = v if (v is None or isinstance(v, str)) else str(v)
        for fld in _NUMERIC_INT_FIELDS:
            cleaned[fld] = _coerce_int(r.get(fld))
        for fld in _NUMERIC_FLOAT_FIELDS:
            cleaned[fld] = _coerce_float(r.get(fld))
        out.append(cleaned)
    return out
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add llm_extractor.py tests/test_llm_extractor.py
git commit -m "feat(llm): SYSTEM_PROMPT v1 + response validator/coercer"
```

---

## Task 6: OpenAI client wrapper with retry/backoff

**Files:**
- Modify: `llm_extractor.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_llm_extractor.py`

- [ ] **Step 1: Add `fake_openai` fixture to `tests/conftest.py`**

Append:

```python
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
```

- [ ] **Step 2: Add failing tests**

Append to `tests/test_llm_extractor.py`:

```python
def test_llm_call_success(fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_openai.chat.completions.create  # ensure monkeypatch landed
    fake_openai.chat.completions.queue.append({
        "reports": [{
            "report_type": "daily_shop_vt", "shop_ref": "S1",
            "deposit_count": 12, "ra_tiem_count": 2,
            "kh_tu_van_count": 214,
            "tich_cuc": None, "van_de": None, "da_lam": None,
            "revenue_pct": None, "hot_pct": None, "hot_ratio_pct": None,
            "tb_bill_vnd": None, "customer_count": None,
        }],
        "unparseable": False, "reason": None,
    })
    out = le._llm_call("some report content")
    assert len(out) == 1
    assert out[0]["shop_ref"] == "S1"


def test_llm_call_retries_on_connection_error(fake_openai, monkeypatch):
    import openai
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(le, "_RETRY_SLEEP", lambda s: None)  # skip backoff
    # openai.APIConnectionError's __init__ signature varies across SDK versions.
    # Bypass it via __new__ + manual attribute setup so the test is version-safe.
    err = openai.APIConnectionError.__new__(openai.APIConnectionError)
    err.args = ("connection refused",)
    fake_openai.chat.completions.error = err
    fake_openai.chat.completions.queue.append({
        "reports": [], "unparseable": True, "reason": "test",
    })
    out = le._llm_call("content")
    assert out == []
    assert fake_openai.chat.completions.calls == 2  # 1 fail + 1 retry
```

- [ ] **Step 3: Run tests, verify failure**

```bash
pytest tests/test_llm_extractor.py -v -k "llm_call"
```
Expected: `AttributeError` for `_llm_call`, `_get_client`, `_RETRY_SLEEP`.

- [ ] **Step 4: Implement client + retry**

Append to `llm_extractor.py`:

```python
import os
import sys
import time

_client_cache = None
_RETRY_SLEEP = time.sleep  # monkey-patchable in tests


class LLMConfigError(Exception):
    """Raised when API key / base URL is missing at call time."""


def _get_client():
    global _client_cache
    if _client_cache is not None:
        return _client_cache
    try:
        import openai
    except ImportError as e:
        raise LLMConfigError("openai package not installed") from e
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMConfigError(
            "Set OPENAI_API_KEY (env or Streamlit sidebar). "
            "Extraction requires LLM access."
        )
    base_url = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    _client_cache = openai.OpenAI(api_key=api_key, base_url=base_url)
    return _client_cache


def _reset_client_cache() -> None:
    """Used by config-plumbing code after env vars change."""
    global _client_cache
    _client_cache = None


def _llm_call(content: str) -> list[dict]:
    """Call the LLM, return validated extraction dicts. Raises LLMParseError
    on schema failure; retries transient network/rate errors."""
    import openai
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    client = _get_client()

    last_exc = None
    attempts = [
        (openai.APIConnectionError, 1, 2),
        (openai.APITimeoutError,    1, 2),
        (openai.RateLimitError,     3, 4),
    ]
    retriable = tuple(e for e, _, _ in attempts)

    for attempt in range(5):   # max total tries
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": content},
                ],
            )
            raw_text = resp.choices[0].message.content
            raw = json.loads(raw_text)
            return _validate_and_coerce(raw)
        except retriable as e:
            last_exc = e
            # connection/timeout: 1 retry; rate limit: up to 3 retries
            max_retries = 3 if isinstance(e, openai.RateLimitError) else 1
            if attempt >= max_retries:
                break
            base = 4 if isinstance(e, openai.RateLimitError) else 2
            _RETRY_SLEEP(base * (2 ** attempt))
            continue
        except json.JSONDecodeError as e:
            raise LLMParseError(f"invalid JSON: {e}") from e
    raise LLMParseError(f"LLM call failed after retries: {last_exc!r}")
```

- [ ] **Step 5: Run tests, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 17 passed.

- [ ] **Step 6: Commit**

```bash
git add llm_extractor.py tests/conftest.py tests/test_llm_extractor.py
git commit -m "feat(llm): _llm_call wrapper với retry/backoff + fake_openai fixture"
```

---

## Task 7: `extract_reports` orchestrator

**Files:**
- Modify: `llm_extractor.py`
- Modify: `tests/test_llm_extractor.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_llm_extractor.py`:

```python
def _fake_msg(content: str, sender: str = "Alice", mid: str = "m1") -> dict:
    return {
        "content":   content,
        "user":      {"displayName": sender, "id": f"u-{sender}"},
        "createdAt": "2026-04-21T10:00:00Z",
        "id":        mid,
        "type":      "TEXT",
    }


def test_extract_reports_caches_second_call(fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_openai.chat.completions.queue.append({
        "reports": [{"report_type": "daily_shop_vt", "shop_ref": "S1",
                     "deposit_count": 12, "ra_tiem_count": None,
                     "kh_tu_van_count": None,
                     "tich_cuc": None, "van_de": None, "da_lam": None,
                     "revenue_pct": None, "hot_pct": None,
                     "hot_ratio_pct": None, "tb_bill_vnd": None,
                     "customer_count": None}],
        "unparseable": False, "reason": None,
    })
    msg = _fake_msg("12 cọc shop X")
    out1 = le.extract_reports(msg)
    out2 = le.extract_reports(msg)
    assert len(out1) == 1 and len(out2) == 1
    assert le.get_stats() == {"llm_call": 1, "llm_cached": 1, "llm_error": 0}
    assert out1[0]["source"] == "llm"
    assert out2[0]["source"] == "cache"
    assert out1[0]["message_id"] == "m1"
    assert out1[0]["sender"] == "Alice"


def test_extract_reports_unparseable_returns_stub(fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(le, "_RETRY_SLEEP", lambda s: None)
    # Force JSONDecodeError by returning a bare string, unrecoverable.
    def _bad(**kw):
        class M: content = "not-json{{{"
        class C: message = M()
        class R: choices = [C()]
        return R()
    fake_openai.chat.completions.create = _bad  # type: ignore
    msg = _fake_msg("something weird")
    out = le.extract_reports(msg)
    assert len(out) == 1
    assert out[0]["report_type"] == "unknown"
    assert out[0]["parse_error"] is not None
    assert le.get_stats()["llm_error"] == 1


def test_extract_reports_returns_empty_for_non_report(fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    fake_openai.chat.completions.queue.append({
        "reports": [], "unparseable": True, "reason": "greeting only",
    })
    out = le.extract_reports(_fake_msg("Dear Anh Chi"))
    assert out == []
```

- [ ] **Step 2: Run tests, verify failure**

```bash
pytest tests/test_llm_extractor.py -v -k "extract_reports"
```
Expected: `AttributeError: extract_reports`.

- [ ] **Step 3: Implement orchestrator**

Append to `llm_extractor.py`:

```python
def _unparseable_stub(msg: dict, reason: str) -> Report:
    u = msg.get("user") or {}
    return {   # type: ignore[return-value]
        "report_type": "unknown",
        "shop_ref": None,
        "sender": u.get("displayName", "Unknown"),
        "sender_id": u.get("id", ""),
        "sent_at": msg.get("createdAt", ""),
        "message_id": msg.get("id", ""),
        "source": "llm",
        "parse_error": reason,
        "deposit_count": None, "ra_tiem_count": None,
        "kh_tu_van_count": None, "tich_cuc": None, "van_de": None,
        "da_lam": None, "revenue_pct": None, "hot_pct": None,
        "hot_ratio_pct": None, "tb_bill_vnd": None, "customer_count": None,
    }


def _hydrate(extracted: dict, msg: dict, source: str) -> Report:
    """Merge per-report LLM fields with per-message metadata."""
    u = msg.get("user") or {}
    report: Report = {   # type: ignore[assignment]
        "report_type": extracted["report_type"],
        "shop_ref":    extracted.get("shop_ref"),
        "sender":      u.get("displayName", "Unknown"),
        "sender_id":   u.get("id", ""),
        "sent_at":     msg.get("createdAt", ""),
        "message_id":  msg.get("id", ""),
        "source":      source,   # "llm" or "cache"
        "parse_error": None,
        "deposit_count":   extracted.get("deposit_count"),
        "ra_tiem_count":   extracted.get("ra_tiem_count"),
        "kh_tu_van_count": extracted.get("kh_tu_van_count"),
        "tich_cuc":        extracted.get("tich_cuc"),
        "van_de":          extracted.get("van_de"),
        "da_lam":          extracted.get("da_lam"),
        "revenue_pct":     extracted.get("revenue_pct"),
        "hot_pct":         extracted.get("hot_pct"),
        "hot_ratio_pct":   extracted.get("hot_ratio_pct"),
        "tb_bill_vnd":     extracted.get("tb_bill_vnd"),
        "customer_count":  extracted.get("customer_count"),
    }
    return report


def extract_reports(msg: dict) -> list[Report]:
    """Main entry: extract zero-or-more reports from a single message."""
    content = msg.get("content") or ""

    cached = _load_cache(content)
    if cached is not None:
        _stats["llm_cached"] += 1
        return [_hydrate(r, msg, source="cache") for r in cached]

    try:
        extracted = _llm_call(content)
    except (LLMParseError, LLMConfigError) as e:
        _stats["llm_error"] += 1
        return [_unparseable_stub(msg, reason=str(e))]
    except Exception as e:   # transport bug, unexpected
        _stats["llm_error"] += 1
        print(f"[llm] unexpected error on {msg.get('id','?')}: {e!r}",
              file=sys.stderr)
        return [_unparseable_stub(msg, reason=f"unexpected: {type(e).__name__}")]

    _stats["llm_call"] += 1
    _save_cache(content, extracted)
    return [_hydrate(r, msg, source="llm") for r in extracted]
```

- [ ] **Step 4: Run tests, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 20 passed.

- [ ] **Step 5: Commit**

```bash
git add llm_extractor.py tests/test_llm_extractor.py
git commit -m "feat(llm): extract_reports orchestrator với cache → LLM → stub"
```

---

## Task 8: Config plumbing — CLI flags + env propagation

**Files:**
- Modify: `fpt_chat_stats.py` (argparse block ~lines 1399–1452; add --llm-base-url, --llm-model after existing flags)
- Modify: `llm_extractor.py`

- [ ] **Step 1: Add failing test for `configure_from_args` helper**

Append to `tests/test_llm_extractor.py`:

```python
def test_configure_sets_env_and_clears_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    le._client_cache = object()   # prove it gets cleared
    le.configure(api_key="k1", base_url="https://x/v1", model="gpt-foo")
    assert os.environ["OPENAI_API_KEY"] == "k1"
    assert os.environ["OPENAI_BASE_URL"] == "https://x/v1"
    assert os.environ["LLM_MODEL"] == "gpt-foo"
    assert le._client_cache is None
```

(Add `import os` at the top of `test_llm_extractor.py` if not already present.)

- [ ] **Step 2: Run, verify failure**

```bash
pytest tests/test_llm_extractor.py -v -k "configure"
```
Expected: `AttributeError: configure`.

- [ ] **Step 3: Implement `configure` in `llm_extractor.py`**

Append:

```python
def configure(api_key: str | None = None,
              base_url: str | None = None,
              model: str | None = None) -> None:
    """Set env vars that `_get_client` / `_llm_call` read. Idempotent. Any
    non-None argument overwrites the existing env value; None leaves it
    alone (so env vars from shell still win when CLI/UI don't set them)."""
    if api_key is not None:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url is not None:
        os.environ["OPENAI_BASE_URL"] = base_url
    if model is not None:
        os.environ["LLM_MODEL"] = model
    _reset_client_cache()
```

- [ ] **Step 4: Run, verify pass**

```bash
pytest tests/test_llm_extractor.py -v
```
Expected: 21 passed.

- [ ] **Step 5: Add CLI flags to `fpt_chat_stats.py` `main()`**

In `fpt_chat_stats.py` around line 1452 (after `--skip-reporters`), insert:

```python
    parser.add_argument("--llm-base-url", dest="llm_base_url", default=None,
                        help="OpenAI-compatible base URL (default: https://api.openai.com/v1)")
    parser.add_argument("--llm-model", dest="llm_model", default=None,
                        help="LLM model name (default: gpt-4o-mini)")
```

After `args = parser.parse_args()` (currently line 1453), resolve LLM config from precedence CLI > cfg > env > default and call `llm_extractor.configure`:

```python
    import llm_extractor
    llm_extractor.configure(
        api_key = (cfg.get("llm") or {}).get("api_key"),  # only from gitignored config.json
        base_url= args.llm_base_url or (cfg.get("llm") or {}).get("base_url"),
        model   = args.llm_model    or (cfg.get("llm") or {}).get("model"),
    )
```

- [ ] **Step 6: Commit**

```bash
git add llm_extractor.py fpt_chat_stats.py tests/test_llm_extractor.py
git commit -m "feat(llm): CLI flags --llm-base-url/--llm-model + configure() helper"
```

---

## Task 9: Update `config.example.json`

**Files:**
- Modify: `config.example.json`

- [ ] **Step 1: Read current file**

```bash
cat config.example.json
```

- [ ] **Step 2: Add `llm` block (before closing brace)**

Add these keys (do NOT add `api_key` — it stays out of the example to reinforce "never check in"):

```json
  "llm": {
    "base_url": "https://api.openai.com/v1",
    "model":    "gpt-4o-mini"
  },
```

- [ ] **Step 3: Validate JSON**

```bash
python -c "import json; json.load(open('config.example.json'))"
```
Expected: no output (valid JSON).

- [ ] **Step 4: Commit**

```bash
git add config.example.json
git commit -m "docs: thêm llm block (base_url, model) vào config.example.json"
```

---

## Task 10: Golden-file test scaffolding (single template to prove the pattern)

**Files:**
- Create: `tests/test_templates.py`
- Create: `templates/daily/1.expected.json`

- [ ] **Step 0: Read the template file first** — the example JSON below is a structural guide, but the strings (`shop_ref`, `tich_cuc`, `van_de`, `da_lam`) must mirror the exact text in `templates/daily/1`, including Vietnamese diacritics and punctuation. Always open the template, don't trust the plan's example wholesale:

```bash
cat templates/daily/1
```

- [ ] **Step 1: Create expected file for `templates/daily/1`**

Write `templates/daily/1.expected.json` based on what you just read — the following is a *shape reference*, adjust the string values to match the actual file content:

```json
{
  "reports": [
    {
      "report_type": "daily_shop_vt",
      "shop_ref": "80035 173 Hùng Vương Tân An",
      "deposit_count": 12,
      "ra_tiem_count": 2,
      "kh_tu_van_count": 214,
      "tich_cuc": "Vệ tinh khai thác tốt NMC, khách nhi sau các đợt đào tạo offline.",
      "van_de": "Shop còn 2 bạn chưa đạt doanh thu còn chậm hơn các bạn.",
      "da_lam": "ASM đã họp trao đổi riêng  và hướng dẫn thêm cách care data và theo đuổi đến cùng.",
      "revenue_pct": null,
      "hot_pct": null,
      "hot_ratio_pct": null,
      "tb_bill_vnd": null,
      "customer_count": null
    }
  ]
}
```

- [ ] **Step 2: Create `tests/test_templates.py`**

```python
"""Golden-file regression tests driven by real chat-message templates
under templates/{daily,weekend}/.  The fake OpenAI client is primed
from the matching .expected.json file, so these tests verify the
extract_reports → hydrate → downstream contract, NOT LLM accuracy.
(LLM accuracy is validated manually via scripts/verify_llm_extract.py
against live snapshots.)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import llm_extractor as le


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _discover():
    for sub in ("daily", "weekend"):
        d = TEMPLATES_DIR / sub
        if not d.exists():
            continue
        for p in sorted(d.iterdir()):
            if p.is_file() and not p.name.endswith(".expected.json"):
                exp = p.with_suffix(".expected.json")
                if exp.exists():
                    yield pytest.param(p, exp, id=f"{sub}/{p.name}")


@pytest.mark.parametrize("template_path, expected_path", list(_discover()))
def test_template_extraction(template_path, expected_path,
                             fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    content = template_path.read_text(encoding="utf-8")
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    # Prime the fake LLM with the expected reports wrapped in the
    # top-level LLM response shape (no unparseable, no reason).
    reports_only = expected["reports"]
    fake_openai.chat.completions.queue.append({
        "reports": reports_only, "unparseable": False, "reason": None,
    })

    msg = {"content": content,
           "user": {"displayName": "T", "id": "u-t"},
           "createdAt": "2026-04-21T10:00:00Z",
           "id": f"m-{template_path.name}",
           "type": "TEXT"}
    out = le.extract_reports(msg)

    assert len(out) == len(reports_only)
    for actual, exp in zip(out, reports_only):
        for k, v in exp.items():
            assert actual[k] == v, (
                f"{template_path.name}: field {k!r} differs "
                f"(got {actual[k]!r}, want {v!r})"
            )
```

- [ ] **Step 3: Run golden tests**

```bash
pytest tests/test_templates.py -v
```
Expected: 1 passed (only `daily/1` has an expected file yet).

- [ ] **Step 4: Commit**

```bash
git add tests/test_templates.py templates/daily/1.expected.json
git commit -m "test: golden-file harness + templates/daily/1 expected"
```

---

## Task 11: Add expected files for remaining 14 templates

**Files:**
- Create: `templates/daily/{2,3,4,5,6,7}.expected.json`
- Create: `templates/weekend/{1,2,3,4,5,6,7,8}.expected.json`

For each template file, produce the expected JSON manually by reading the template and extracting the same shape as `daily/1.expected.json`. Key reminders:

- `tich_cuc` / `van_de` / `da_lam`: preserve original Vietnamese, including trailing punctuation; `null` if absent.
- Weekend template 7 and 8 are combined-message templates (Shop VT block + TTTC block) — their `reports` array has **length 2**, one of each type.
- Percentages: `133` not `"133%"`; `null` if not present.
- VND amounts: `2200000` for "2,2tr", `134927000` for "134.927.000".

- [ ] **Step 1: Create `templates/daily/2.expected.json` through `templates/daily/7.expected.json`** (6 files).

Run after each:
```bash
pytest tests/test_templates.py::test_template_extraction -v -k "daily"
```

- [ ] **Step 2: Create `templates/weekend/1.expected.json` through `templates/weekend/8.expected.json`** (8 files).

For templates 7 and 8 (combined), example for `templates/weekend/7.expected.json`:
```json
{
  "reports": [
    {"report_type": "daily_shop_vt", "shop_ref": "LC HCM 20 PHẠM THẾ HIỂN",
     "deposit_count": 12, "ra_tiem_count": 19, "kh_tu_van_count": 88,
     "tich_cuc": null, "van_de": null, "da_lam": null,
     "revenue_pct": null, "hot_pct": null, "hot_ratio_pct": null,
     "tb_bill_vnd": null, "customer_count": null},
    {"report_type": "weekend_tttc", "shop_ref": "<from file>",
     "deposit_count": null, "ra_tiem_count": null, "kh_tu_van_count": null,
     "tich_cuc": null, "van_de": null, "da_lam": null,
     "revenue_pct": null, "hot_pct": null, "hot_ratio_pct": null,
     "tb_bill_vnd": null, "customer_count": null}
  ]
}
```

Fill in actual values from each template — the scaffolding proves the harness, but each file must match real content.

- [ ] **Step 3: Full run**

```bash
pytest tests/test_templates.py -v
```
Expected: 15 passed.

- [ ] **Step 4: Commit per-directory (two commits)**

```bash
git add templates/daily/*.expected.json
git commit -m "test: golden files cho 7 template daily"

git add templates/weekend/*.expected.json
git commit -m "test: golden files cho 8 template weekend (gồm combined 7/8)"
```

---

## Task 12: Rip out regex parsers from `fpt_chat_stats.py`

This task ONLY deletes; adaptation of callsites is Task 13. After this task the file will be temporarily broken at runtime — that's intentional, Task 13 restores it.

**Files:**
- Modify: `fpt_chat_stats.py` (delete lines around 265, 298, 344, 390, 436–540)

- [ ] **Step 1: Delete the named symbols** (use exact `Grep`/`Edit` — search the function signature text, delete from that line through the end of the function/constant block):

- `classify_report` (line ~265) — delete the whole function.
- `_parse_vnd_amount` (line ~298) — delete the whole function.
- `_extract_sections` (line ~344) — delete the whole function.
- `parse_asm_report` (line ~390) — delete the whole function (through end of its return block).
- All TTTC regex constants and helpers: `_TTTC_VENUE_RE`, `_TTTC_REVENUE_PCT_RE`, `_TTTC_HOT_PCT_RE`, `_TTTC_HOT_RATIO_RE`, `_TTTC_TB_BILL_VALUE_RE`, `_TTTC_CUSTOMER_RE`, `_TTTC_NARRATIVE_BOUNDARY_RE`, `_first_n_lines`, `_to_pct`, `_tttc_metrics_area` (lines ~436–540).
- `parse_tttc_report` (line ~540) — delete the whole function.

Keep: `detect_asm_reports` at line 285.

- [ ] **Step 2: Verify import-ability (file still parses)**

```bash
python -c "import fpt_chat_stats"
```
Expected: **will fail** — `analyze_asm_reports`, `write_asm_excel`, the weekly dispatch code, and `main()` still reference deleted symbols. This is the intentional broken state.

- [ ] **Step 3: Commit (broken state acknowledged)**

```bash
git add fpt_chat_stats.py
git commit -m "refactor(parse): xoá toàn bộ regex parser (ASM/TTTC) — callsites sẽ adapt ở commit sau"
```

---

## Task 13: Adapt `fpt_chat_stats.py` callsites to the `Report` schema

**Files:**
- Modify: `fpt_chat_stats.py` (lines 606, 667, 729, 798, 980-1002, 1178, 1399+)

- [ ] **Step 1: Add orchestrator at the top of the "Analysis" section**

Insert (just after the `detect_asm_reports` function) a new function:

```python
def extract_all_reports(messages: list) -> list:
    """Pre-filter with detect_asm_reports, then LLM-extract each candidate.

    Returns a flat list of Report dicts (may be longer than candidates
    because combined messages produce multiple reports).
    """
    import llm_extractor
    out = []
    for msg in detect_asm_reports(messages):
        out.extend(llm_extractor.extract_reports(msg))
    return out
```

- [ ] **Step 2: Adapt `analyze_asm_reports`** (currently expects pre-parsed ASM dicts at line 606)

The function already reads `r.get("deposit_count")`, `r.get("shop_ref")` etc. — those keys still exist in the `Report` TypedDict, so the body itself needs only one change: **filter inputs by `report_type`** at the top:

```python
def analyze_asm_reports(parsed_reports: list,
                        deposit_low: int = 2, deposit_high: int = 5) -> dict:
    """Phân tích báo cáo ASM (daily_shop_vt only)."""
    # Accept a mixed list: filter to daily reports.
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == "daily_shop_vt"
                      and r.get("parse_error") is None]
    # ... rest unchanged ...
```

- [ ] **Step 3: Adapt `analyze_tttc_reports`** (line 667) — same filter, but `report_type == "weekend_tttc"`. Also skip `parse_error is not None`.

- [ ] **Step 4: Adapt `check_asm_compliance`** (line 729) AND `check_late_reporters` (line 767)

Both functions iterate `parsed_reports` against `members` and read `r["sender"]` / `r.get("sent_at")`. With the new schema, TTTC reports and unparseable stubs will share those fields too — without a filter they'd be counted as daily-report compliance data, which is wrong. Add the filter at the top of **both** functions:

```python
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == "daily_shop_vt"
                      and r.get("parse_error") is None]
```

- [ ] **Step 5: Adapt `analyze_multiday`** (line 798)

Same filter at the top — take only `daily_shop_vt` with `parse_error is None`.

- [ ] **Step 6: Adapt the weekly flow** (lines 980–1002)

Replace the current `classify_report` + `parse_asm_report`/`parse_tttc_report` dispatch with a single extraction pass:

```python
    import llm_extractor
    parsed_shop_vt: list = []
    parsed_tttc:    list = []
    unparseable:    list = []
    for sender, items in by_sender.items():
        for dt, _vn_dt, content in items:
            fake_msg = {
                "content":   content,
                "user":      {"displayName": sender, "id": ""},
                "createdAt": dt.isoformat(),
                "id":        f"{sender}-{dt.timestamp()}",
                "type":      "TEXT",
            }
            for r in llm_extractor.extract_reports(fake_msg):
                if r["parse_error"] is not None:
                    unparseable.append(r)
                elif r["report_type"] == "daily_shop_vt":
                    parsed_shop_vt.append(r)
                elif r["report_type"] == "weekend_tttc":
                    parsed_tttc.append(r)

    asm_data  = analyze_asm_reports(parsed_shop_vt) if parsed_shop_vt else None
    tttc_data = analyze_tttc_reports(parsed_tttc)   if parsed_tttc    else None
```

Add `"unparseable": unparseable,` to the returned dict (around line 1004+).

- [ ] **Step 7: Adapt `main()`** (line ~1581)

Replace:
```python
    asm_msgs = detect_asm_reports(messages)
    ...
    parsed_reports = [parse_asm_report(m) for m in asm_msgs]
```
with:
```python
    parsed_reports = extract_all_reports(messages)
```

- [ ] **Step 8: Adapt `write_asm_excel`** (line 1178)

Skim the function body: it iterates `asm_data["reports"]` / related lists that come from `analyze_asm_reports`. Since `analyze_asm_reports` now filters by `report_type`, `write_asm_excel` itself needs no logic change UNLESS it reads field names that existed on the old ASM dict but not the new `Report` — in which case rename reads to match the `Report` schema (e.g. `tich_cuc`, `van_de`, `da_lam` — all preserved). Verify with:

```bash
grep -n "r\[\|r\.get\|\.get(" fpt_chat_stats.py | grep -E "tich_cuc|van_de|da_lam|deposit_count|ra_tiem_count|shop_ref" | head
```

If any access uses a field **not** in the `Report` TypedDict (e.g. `kh_tu_van` — old singular), rename to the new canonical name (`kh_tu_van_count`).

- [ ] **Step 9: Run CLI smoke (no network — print-only path)**

```bash
python -c "import fpt_chat_stats; print('ok')"
```
Expected: `ok` (file parses cleanly).

- [ ] **Step 10: Run all tests**

```bash
pytest -v
```
Expected: 21 unit tests + 15 template tests = 36 passed.

- [ ] **Step 11: Print-report smoke against a saved snapshot (offline, no real API)**

If `raw.json` exists in the repo root, run with a deliberately-unreachable base URL so `_llm_call` enters the `APIConnectionError` retry path and degrades to unparseable stubs — no real API hit, no auth error, just pipeline execution:
```bash
OPENAI_API_KEY=sk-test \
OPENAI_BASE_URL=http://127.0.0.1:1/v1 \
python fpt_chat_stats.py --load raw.json --today 2>&1 | tail -40
```
Expected: the CLI completes without a Python traceback; the stderr tail shows the stats line and a count of `llm_error=N` matching the number of detected candidates. The "Không parse được" section in the printed report (or the equivalent stub entries) should list every candidate with a `parse_error`.

Skip this step if no `raw.json` exists.

- [ ] **Step 12: Commit**

```bash
git add fpt_chat_stats.py
git commit -m "refactor: adapt analyze/compliance/weekly/main sang Report schema mới"
```

---

## Task 14: Adapt Streamlit UI (`app.py`)

**Files:**
- Modify: `app.py` (imports ~line 84-99; sidebar; analysis callsites ~line 949-1011)

- [ ] **Step 1: Remove deleted imports**

On lines 84–99, remove `parse_asm_report` from the imports. Keep `detect_asm_reports`, `analyze_asm_reports`, `write_asm_excel`, `analyze_tttc_reports`, `check_asm_compliance`, `analyze_multiday`. Add:

```python
from fpt_chat_stats import extract_all_reports
import llm_extractor
```

- [ ] **Step 2: Add LLM config sidebar block**

Inside the existing sidebar (find the block that handles `fpt_token` / `fpt_groups_library`), add three inputs. Use the same `st_javascript` nullable-return pattern. Keys: `fpt_llm_base_url`, `fpt_llm_model`, `fpt_llm_api_key`.

Pseudocode (adapt to the file's style):

```python
llm_base_url = st.sidebar.text_input(
    "LLM base URL",
    value=st.session_state.get("llm_base_url", "https://api.openai.com/v1"),
    key="llm_base_url_input",
)
llm_model = st.sidebar.text_input(
    "LLM model",
    value=st.session_state.get("llm_model", "gpt-4o-mini"),
    key="llm_model_input",
)
llm_api_key = st.sidebar.text_input(
    "OpenAI API key",
    value=st.session_state.get("llm_api_key", ""),
    type="password",
    key="llm_api_key_input",
)
llm_extractor.configure(
    api_key=llm_api_key or None,
    base_url=llm_base_url or None,
    model=llm_model or None,
)
```

Persist the three values in `localStorage` using the same pattern as `fpt_token` (see CLAUDE.md note: tokens/keys never go to `config.json`).

- [ ] **Step 3: Replace detect+parse call pair with `extract_all_reports`**

At lines 949 and 956:
```python
asm_msgs = detect_asm_reports(messages)
...
parsed   = [parse_asm_report(m) for m in asm_msgs]
```
becomes:
```python
parsed   = extract_all_reports(messages)
```

Same replacement at line 992–993 (`asm_d1`/`parsed_d1` block).

- [ ] **Step 4: Render unparseable reports**

Near the end of the main analysis section, after the existing report-rendering blocks, add:

```python
unparseable = [r for r in parsed if r.get("parse_error")]
if unparseable:
    st.subheader("Không parse được")
    for r in unparseable:
        with st.expander(f"{r['sender']} — {r['sent_at']}"):
            st.caption(f"Lý do: {r['parse_error']}")
            # Look up the raw message by message_id to show original text.
            raw = next((m for m in messages if m.get("id") == r["message_id"]), None)
            if raw:
                st.code(raw.get("content") or "", language=None)
```

- [ ] **Step 5: Show stats in sidebar after run**

At the end of the sidebar block (after analysis triggers), add:

```python
_stats_line = llm_extractor.format_stats()
st.sidebar.caption(_stats_line)
```

- [ ] **Step 6: Smoke the app**

```bash
streamlit run app.py --server.headless true --server.port 8501 &
sleep 3
curl -sSf http://localhost:8501/ > /dev/null && echo OK
kill %1
```
Expected: `OK` (app boots without import errors).

- [ ] **Step 7: Commit**

```bash
git add app.py
git commit -m "feat(ui): sidebar LLM config + unparseable rendering + stats caption"
```

---

## Task 15: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the Commands section** — add `pytest` row:

```
pytest                                    # unit tests + golden-file tests (15 templates)
pytest -v tests/test_llm_extractor.py     # llm_extractor unit tests only
```

- [ ] **Step 2: Replace the Pipeline description**

In the "Architecture" → "Pipeline (`fpt_chat_stats.py`)" block, replace the regex-parser bullets with:

```
2. `extract_all_reports` applies the cheap regex pre-filter (`detect_asm_reports`)
   and delegates extraction to `llm_extractor.extract_reports`, which calls the
   OpenAI API (or compatible endpoint) with JSON mode and caches results on
   disk under `.llm_cache/` keyed by sha256(content) + PROMPT_VERSION.
3. A single LLM call per message returns a `list[Report]`; combined messages
   (e.g. weekend 7/8 — Shop VT + TTTC in one chat message) produce two
   reports. Unparseable messages yield a stub with `parse_error` surfaced
   in UI/Excel.
4. Downstream (`analyze_asm_reports`, `analyze_tttc_reports`,
   `check_asm_compliance`, `analyze_multiday`, `write_asm_excel`) filter the
   flat report list by `report_type` and `parse_error is None`.
```

Update the "Auth quirk" block to also mention: `llm_extractor.configure()` reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `LLM_MODEL` from env; Streamlit stores these in `localStorage` (keys `fpt_llm_*`) and never writes them to `config.json`.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: cập nhật CLAUDE.md — llm_extractor pipeline + pytest command"
```

---

## Task 16: OpenSpec change proposal

Per `CLAUDE.md`: *"For any feature work beyond a bugfix, follow `openspec/AGENTS.md` — proposals go in `openspec/changes/<change-id>/` and must pass `openspec validate <id> --strict --no-interactive` before implementation."*

This refactor replaces a whole extraction subsystem, so the default is a **change proposal**, not an in-place spec edit.

**Files:**
- Create: `openspec/changes/2026-04-21-llm-report-extraction/proposal.md`
- Create: `openspec/changes/2026-04-21-llm-report-extraction/tasks.md`
- Create: `openspec/changes/2026-04-21-llm-report-extraction/specs/fpt-chat-stats/spec.md` (the updated spec delta)

- [ ] **Step 1: Read `openspec/AGENTS.md` to confirm current proposal format and required files.**

```bash
cat openspec/AGENTS.md
```

- [ ] **Step 2: Scaffold the change directory**

```bash
mkdir -p openspec/changes/2026-04-21-llm-report-extraction/specs/fpt-chat-stats
```

- [ ] **Step 3: Write `proposal.md`** — short rationale mirroring the spec's Problem / Goal / Non-goals sections, with a link to `docs/superpowers/specs/2026-04-21-llm-report-extraction-design.md`.

- [ ] **Step 4: Write `tasks.md`** — the 17 in-repo tasks from this plan (Task 17 and 18 are validation-only, exclude).

- [ ] **Step 5: Write `specs/fpt-chat-stats/spec.md`** — the updated parsing section matching the new architecture (LLM extractor, 1-to-N schema, cache, stats, unparseable stub).

- [ ] **Step 6: Validate**

```bash
openspec validate 2026-04-21-llm-report-extraction --strict --no-interactive
```
Expected: validation passes.

- [ ] **Step 7: Commit**

```bash
git add openspec/changes/2026-04-21-llm-report-extraction/
git commit -m "docs(openspec): đề xuất đổi parser regex sang LLM extractor"
```

(The change stays in `openspec/changes/` until implementation is complete and an archive commit moves it to `openspec/changes/archive/` per project convention — out of scope for this plan.)

---

## Task 17: Manual live-API smoke (off-plan, document in commit)

Not enforced by tests. Run this once with a real API key and a saved snapshot to verify end-to-end behavior.

- [ ] **Step 1: Save a fresh snapshot**

```bash
python fpt_chat_stats.py --save raw.json --today
```

- [ ] **Step 2: Run with real LLM**

```bash
export OPENAI_API_KEY=sk-...
python fpt_chat_stats.py --load raw.json --today --excel smoke.xlsx 2>&1 | tail -20
```

Expected: `[llm] llm_call=N cached=0 error=0 — cache hit rate 0%` printed to stderr, no crashes.

- [ ] **Step 3: Run again (should hit cache)**

```bash
python fpt_chat_stats.py --load raw.json --today --excel smoke2.xlsx 2>&1 | tail -5
```

Expected: `llm_call=0 cached=N`, cache hit rate 100%.

- [ ] **Step 4: Inspect `smoke.xlsx` manually** — compare shops count, deposit totals, and presence of an "Unparseable" block against the pre-refactor Excel (if you still have one).

- [ ] **Step 5 (no commit — this task is validation only)** — if everything checks out, record observations in a note; if anything regresses, cut follow-up tasks.

---

## Task 18: Streamlit live smoke

- [ ] **Step 1: Run locally**

```bash
export OPENAI_API_KEY=sk-...
streamlit run app.py
```

- [ ] **Step 2: In browser** — paste a real token, select a group, run "today" analysis. Verify:
  - Report renders
  - No regex-parse errors in stderr
  - Sidebar shows `[llm] llm_call=N cached=M error=0 — ...`
  - Unparseable block shows up only when there are genuinely weird messages

- [ ] **Step 3: No code commit** — follow-up bugs become their own tasks.

---

## Post-plan checklist

- [ ] All tests pass: `pytest -v` → 36 passed.
- [ ] `git status` clean.
- [ ] `fpt_chat_stats.py` line count dropped by ~300.
- [ ] `.llm_cache/` tracked via `.gitkeep` but contents ignored.
- [ ] `CLAUDE.md` Commands section mentions `pytest`.
- [ ] `requirements.txt` has `openai>=1.0`; `requirements-dev.txt` has `pytest`, `pytest-mock`.
- [ ] `templates/*.expected.json` present for all 15 templates.
- [ ] No references to deleted symbols (`parse_asm_report`, `parse_tttc_report`, `classify_report`, `_extract_sections`) remain:

```bash
grep -rn "parse_asm_report\|parse_tttc_report\|classify_report\|_extract_sections\|_parse_vnd_amount" \
    --include="*.py" .
```
Expected: no matches (other than the test corpus which shouldn't reference them anyway).

- [ ] OpenSpec updated or change proposal created.
- [ ] Manual smoke passed (Task 17 + 18).
