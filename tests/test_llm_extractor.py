"""Unit tests for llm_extractor module."""
from pathlib import Path

from llm_extractor import (
    Report, PROMPT_VERSION,
    _cache_key, _load_cache, _save_cache, CACHE_DIR,
)
import llm_extractor


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


def test_cache_key_is_stable():
    k1 = _cache_key("hello world")
    k2 = _cache_key("hello world")
    assert k1 == k2
    assert k1.endswith(f"_{PROMPT_VERSION}")


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
