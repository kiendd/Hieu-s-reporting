"""Unit tests for llm_extractor module."""
import os
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


def test_llm_call_success(fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
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
    fake_openai.chat.completions.errors.append(err)
    fake_openai.chat.completions.queue.append({
        "reports": [], "unparseable": True, "reason": "test",
    })
    out = le._llm_call("content")
    assert out == []
    assert fake_openai.chat.completions.calls == 2  # 1 fail + 1 retry


def test_llm_call_retries_on_rate_limit(fake_openai, tmp_cache, monkeypatch):
    import openai
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(le, "_RETRY_SLEEP", lambda s: None)
    # Queue 3 RateLimitErrors followed by a successful response.
    for _ in range(3):
        err = openai.RateLimitError.__new__(openai.RateLimitError)
        err.args = ("rate limited",)
        fake_openai.chat.completions.errors.append(err)
    fake_openai.chat.completions.queue.append({
        "reports": [], "unparseable": True, "reason": "test",
    })
    out = le._llm_call("content")
    assert out == []
    assert fake_openai.chat.completions.calls == 4   # 3 fails + 1 success


def test_llm_call_auth_error_becomes_config_error(fake_openai, tmp_cache, monkeypatch):
    import openai
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    err = openai.AuthenticationError.__new__(openai.AuthenticationError)
    err.args = ("invalid key",)
    fake_openai.chat.completions.errors.append(err)
    with pytest.raises(le.LLMConfigError):
        le._llm_call("content")


def test_llm_call_empty_response_raises_parse_error(fake_openai, tmp_cache, monkeypatch):
    le._reset_stats()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # Patch the fake's create to return None content directly.
    def _empty_create(**kwargs):
        fake_openai.chat.completions.calls += 1
        class M: content = None
        class C: message = M()
        class R: choices = [C()]
        return R()
    fake_openai.chat.completions.create = _empty_create
    with pytest.raises(le.LLMParseError):
        le._llm_call("content")


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


def test_configure_sets_env_and_clears_client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    le._client_cache[("stale", "url")] = object()
    le.configure(api_key="k1", base_url="https://x/v1", model="gpt-foo")
    assert os.environ["OPENAI_API_KEY"] == "k1"
    assert os.environ["OPENAI_BASE_URL"] == "https://x/v1"
    assert os.environ["LLM_MODEL"] == "gpt-foo"
    assert le._client_cache == {}
