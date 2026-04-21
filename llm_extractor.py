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
