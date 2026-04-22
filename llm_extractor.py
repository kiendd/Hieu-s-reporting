"""LLM-based extraction of ASM / TTTC reports from Vietnamese chat messages.

Replaces the regex parsers in fpt_chat_stats.py.  Uses the OpenAI SDK
with a configurable base_url so any OpenAI-compatible provider works
(OpenAI, Azure, Ollama, vLLM, LiteLLM, ...).
"""
from __future__ import annotations

from typing import Literal, TypedDict
import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path


PROMPT_VERSION = "v1"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_STRUCTURED_OUTPUTS = True
DEFAULT_MAX_WORKERS = 4


def _read_max_workers() -> int:
    """Concurrent LLM worker count for extract_all_reports. Env
    `LLM_MAX_WORKERS` overrides default. Clamp to [1, 32] — 1 disables
    parallelism, upper bound protects against runaway config."""
    v = os.environ.get("LLM_MAX_WORKERS")
    if v is None:
        return DEFAULT_MAX_WORKERS
    try:
        n = int(v)
    except ValueError:
        return DEFAULT_MAX_WORKERS
    return max(1, min(32, n))


def _read_structured_outputs_flag() -> bool:
    """Truthy env var `LLM_STRUCTURED_OUTPUTS` enables OpenAI structured
    outputs (response_format=json_schema). Default False for broadest
    provider compatibility."""
    v = os.environ.get("LLM_STRUCTURED_OUTPUTS")
    if v is None:
        return DEFAULT_STRUCTURED_OUTPUTS
    return v.strip().lower() in ("1", "true", "yes", "on")


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


_stats = {"llm_call": 0, "llm_cached": 0, "llm_error": 0}
_STATS_LOCK = threading.Lock()


def _bump_stat(key: str) -> None:
    with _STATS_LOCK:
        _stats[key] += 1


def _reset_stats() -> None:
    with _STATS_LOCK:
        for k in _stats:
            _stats[k] = 0


def get_stats() -> dict[str, int]:
    with _STATS_LOCK:
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


def _build_json_schema() -> dict:
    """JSON Schema for OpenAI structured outputs (strict mode).

    Strict mode requires every property in `required` and
    `additionalProperties: false`; optionality is expressed as a
    null union (`["integer", "null"]`) rather than by omitting the key.
    """
    report_props: dict[str, dict] = {
        "report_type": {"type": "string",
                        "enum": ["daily_shop_vt", "weekend_tttc"]},
    }
    for fld in _STRING_FIELDS:
        report_props[fld] = {"type": ["string", "null"]}
    for fld in _NUMERIC_INT_FIELDS:
        report_props[fld] = {"type": ["integer", "null"]}
    for fld in _NUMERIC_FLOAT_FIELDS:
        report_props[fld] = {"type": ["number", "null"]}

    report_item = {
        "type": "object",
        "properties": report_props,
        "required": list(report_props.keys()),
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {
            "reports": {"type": "array", "items": report_item},
            "unparseable": {"type": "boolean"},
            "reason": {"type": ["string", "null"]},
        },
        "required": ["reports", "unparseable", "reason"],
        "additionalProperties": False,
    }


_JSON_SCHEMA = _build_json_schema()


def _coerce_int(v: object) -> int | None:
    if v is None:
        return None
    if isinstance(v, bool):
        raise LLMParseError(f"cannot coerce int: {v!r}")
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


def _coerce_float(v: object) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        raise LLMParseError(f"cannot coerce float: {v!r}")
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
            if v is not None and not isinstance(v, str):
                raise LLMParseError(
                    f"report[{i}].{fld}: expected string, got {type(v).__name__}"
                )
            cleaned[fld] = v
        for fld in _NUMERIC_INT_FIELDS:
            cleaned[fld] = _coerce_int(r.get(fld))
        for fld in _NUMERIC_FLOAT_FIELDS:
            cleaned[fld] = _coerce_float(r.get(fld))
        out.append(cleaned)
    return out


_client_cache: dict[tuple[str, str], "openai.OpenAI"] = {}
_RETRY_SLEEP = time.sleep  # monkey-patchable in tests


class LLMConfigError(Exception):
    """Raised when API key / base URL is missing at call time."""


def _get_client():
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
    key = (api_key, base_url)
    if key not in _client_cache:
        _client_cache[key] = openai.OpenAI(api_key=api_key, base_url=base_url)
    return _client_cache[key]


def _reset_client_cache() -> None:
    """Used by config-plumbing code after env vars change. Clears all
    cached clients so the next _get_client() call re-reads env."""
    _client_cache.clear()


def _llm_call(content: str) -> list[dict]:
    """Call the LLM, return validated extraction dicts. Raises LLMParseError
    on schema failure; retries transient network/rate errors."""
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    client = _get_client()
    import openai  # safe here — _get_client already confirmed availability

    last_exc = None
    attempts = [
        (openai.APIConnectionError, 1, 2),
        (openai.APITimeoutError,    1, 2),
        (openai.RateLimitError,     3, 4),
    ]
    retriable = tuple(e for e, _, _ in attempts)

    if _read_structured_outputs_flag():
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "reports_extraction",
                "schema": _JSON_SCHEMA,
                "strict": True,
            },
        }
    else:
        response_format = {"type": "json_object"}

    for attempt in range(5):   # max total tries
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0,
                response_format=response_format,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": content},
                ],
            )
            raw_text = resp.choices[0].message.content
            if not raw_text:
                raise LLMParseError("empty response from LLM")
            raw = json.loads(raw_text)
            return _validate_and_coerce(raw)
        except (openai.AuthenticationError,
                openai.PermissionDeniedError,
                openai.NotFoundError) as e:
            # Config-level failures: wrong key / wrong endpoint / wrong model.
            # Surface as LLMConfigError so the UI can prompt for a fix.
            raise LLMConfigError(f"{type(e).__name__}: {e}") from e
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
        "source":      source,
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
        _bump_stat("llm_cached")
        return [_hydrate(r, msg, source="cache") for r in cached]

    try:
        extracted = _llm_call(content)
    except (LLMParseError, LLMConfigError) as e:
        _bump_stat("llm_error")
        return [_unparseable_stub(msg, reason=str(e))]
    except Exception as e:
        _bump_stat("llm_error")
        print(f"[llm] unexpected error on {msg.get('id','?')}: {e!r}",
              file=sys.stderr)
        return [_unparseable_stub(msg, reason=f"unexpected: {type(e).__name__}")]

    _bump_stat("llm_call")
    _save_cache(content, extracted)
    return [_hydrate(r, msg, source="llm") for r in extracted]


def configure(api_key: str | None = None,
              base_url: str | None = None,
              model: str | None = None,
              structured_outputs: bool | None = None,
              max_workers: int | None = None) -> None:
    """Set env vars that _get_client / _llm_call read. Idempotent. Any
    non-None argument overwrites the existing env value; None leaves it
    alone (so env vars from shell still win when CLI/UI don't set them)."""
    if api_key is not None:
        os.environ["OPENAI_API_KEY"] = api_key
    if base_url is not None:
        os.environ["OPENAI_BASE_URL"] = base_url
    if model is not None:
        os.environ["LLM_MODEL"] = model
    if structured_outputs is not None:
        os.environ["LLM_STRUCTURED_OUTPUTS"] = "1" if structured_outputs else "0"
    if max_workers is not None:
        os.environ["LLM_MAX_WORKERS"] = str(max_workers)
    _reset_client_cache()
