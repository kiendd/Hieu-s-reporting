"""LLM-based extraction of ASM / TTTC reports from Vietnamese chat messages.

Replaces the regex parsers in fpt_chat_stats.py.  Uses the OpenAI SDK
with a configurable base_url so any OpenAI-compatible provider works
(OpenAI, Azure, Ollama, vLLM, LiteLLM, ...).
"""
from __future__ import annotations

from typing import Literal, TypedDict
import hashlib
import json
from pathlib import Path


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
