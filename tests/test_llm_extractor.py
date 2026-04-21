"""Unit tests for llm_extractor module."""
from pathlib import Path

import pytest

from llm_extractor import (
    Report, PROMPT_VERSION,
    _cache_key, _load_cache, _save_cache, CACHE_DIR,
    SYSTEM_PROMPT, LLMParseError, _validate_and_coerce,
)
import llm_extractor
import llm_extractor as le


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


def test_coerce_int_rejects_bool():
    with pytest.raises(LLMParseError):
        le._coerce_int(True)
    with pytest.raises(LLMParseError):
        le._coerce_int(False)


def test_coerce_float_rejects_bool():
    with pytest.raises(LLMParseError):
        le._coerce_float(True)


def test_validate_rejects_list_in_string_field():
    raw = {
        "reports": [
            {"report_type": "daily_shop_vt", "shop_ref": "S1",
             "van_de": ["a", "b"],  # list, not a string
             "deposit_count": None, "ra_tiem_count": None,
             "kh_tu_van_count": None,
             "tich_cuc": None, "da_lam": None,
             "revenue_pct": None, "hot_pct": None,
             "hot_ratio_pct": None, "tb_bill_vnd": None,
             "customer_count": None}
        ],
        "unparseable": False, "reason": None,
    }
    with pytest.raises(LLMParseError):
        _validate_and_coerce(raw)


def test_validate_rejects_dict_in_string_field():
    raw = {
        "reports": [
            {"report_type": "weekend_tttc", "shop_ref": {"nested": "bad"},
             "deposit_count": None, "ra_tiem_count": None,
             "kh_tu_van_count": None,
             "tich_cuc": None, "van_de": None, "da_lam": None,
             "revenue_pct": None, "hot_pct": None,
             "hot_ratio_pct": None, "tb_bill_vnd": None,
             "customer_count": None}
        ],
        "unparseable": False, "reason": None,
    }
    with pytest.raises(LLMParseError):
        _validate_and_coerce(raw)
