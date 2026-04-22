# LLM-based Report Extraction — Design Spec

**Date**: 2026-04-21
**Status**: Draft — awaiting review
**Author**: brainstorming session
**Supersedes parts of**: `openspec/specs/fpt-chat-stats/spec.md` (ASM + TTTC parsing sections)

## Problem

The current pipeline classifies and extracts structured data from ASM / TTTC reports using hand-written regex (`detect_asm_reports`, `parse_asm_report`, `_extract_sections`, `parse_tttc_report`, plus ~7 TTTC-specific metric regexes). This approach has two structural weaknesses:

1. **Template drift**: users compose reports freely. Seven daily variants and eight weekend variants exist in `templates/`, and new shapes appear regularly. Each new shape requires regex patches — recent commit history (`fix: _extract_sections chặn URL không bị bắt làm nhãn section`, `refactor(ui): tách _render_shop_vt_sections`) shows this is ongoing maintenance cost.
2. **Silent failures**: regex can return "successfully parsed" output where field values are garbage because the user's message only *almost* matched the template. The user explicitly flagged that neither the regex output nor the source messages can be fully trusted.

Additionally, combined messages (weekend templates 7 & 8) contain both a Shop VT block and a TTTC block in the same message, which the current one-to-one parser cannot represent.

## Goal

Replace regex-based extraction with an LLM-based extractor, while:

- Keeping the existing cheap regex *detection* pre-filter.
- Remaining cost-effective via disk caching.
- Supporting multi-report messages (1-to-N schema).
- Degrading visibly, not silently, when extraction fails.
- Staying within existing config / deployment conventions (CLI, Streamlit, `config.json`, browser `localStorage` for secrets).

## Non-goals

- Replacing message *fetching*, *analysis aggregation* (`analyze_asm_reports`, `analyze_multiday`), or *report rendering* (Excel / Streamlit). These are unchanged.
- Supporting non-OpenAI-compatible LLM providers. The `openai` SDK with a configurable `base_url` covers OpenAI, Azure OpenAI, Ollama, vLLM, LiteLLM, and similar gateways.
- Batching LLM calls (`asyncio.gather` etc.). One call per fallback message is sufficient given the caching strategy.
- CI integration for the new test suite.

## Design decisions (fixed during brainstorm)

| # | Topic | Decision |
|---|---|---|
| 1 | Scope | LLM always on extraction; regex retained only as cheap pre-filter. All existing regex parsers (`parse_asm_report`, `parse_tttc_report`, `_extract_sections`, TTTC metric regexes) are removed. |
| 2 | Provider | OpenAI Python SDK with config-driven `base_url` + `api_key` + `model`. |
| 3 | Fallback trigger | N/A — no LLM-vs-regex hybrid. The regex pre-filter is a *candidate selector* (cheaply excludes non-report chat messages), not a fallback path. Every candidate goes to the LLM after cache lookup. |
| 4 | Caching | Disk cache keyed by `sha256(content) + PROMPT_VERSION`, one JSON file per entry under `.llm_cache/`. Stats counters for `llm_call / llm_cached / llm_error` logged to stderr / Streamlit sidebar. |
| 5 | Schema | 1-to-N. A message produces `list[Report]`; each `Report` carries a `report_type` discriminator. A single unified `Report` TypedDict with nullable per-type fields. |
| 6 | Failure mode | Unparseable reports are preserved with a `parse_error` field, surfaced in UI/Excel as "Không parse được: {reason}". Missing API key at config time is a hard error. |
| 7 | Testing | Golden-file corpus tests (A) + unit tests for `llm_extractor` internals (B). No live-API integration tests, no CI wiring in v1. |

## Architecture

### New module: `llm_extractor.py`

Top-level file, flat API:

```
llm_extractor.py
├── PROMPT_VERSION = "v1"                   # bump to invalidate cache
├── class Report (TypedDict)                # unified schema
├── extract_reports(msg) -> list[Report]    # main entry
├── _llm_call(content) -> list[dict]        # OpenAI SDK call
├── _validate_and_coerce(response) -> list[Report]
├── _cache_key(content) / _load_cache / _save_cache
├── _stats: {llm_call, llm_cached, llm_error}
└── get_stats() -> dict
```

### Unified `Report` schema

```python
class Report(TypedDict):
    # Common (all report types)
    report_type: Literal["daily_shop_vt", "weekend_tttc", "unknown"]
    shop_ref: str | None
    sender: str
    sender_id: str
    sent_at: str
    message_id: str
    source: Literal["llm", "cache"]
    parse_error: str | None

    # daily_shop_vt fields (None for other types)
    deposit_count: int | None
    ra_tiem_count: int | None
    kh_tu_van_count: int | None
    tich_cuc: str | None
    van_de: str | None
    da_lam: str | None

    # weekend_tttc fields (None for other types)
    revenue_pct: float | None
    hot_pct: float | None
    hot_ratio_pct: float | None
    tb_bill_vnd: int | None
    customer_count: int | None
```

`report_type == "unknown"` combined with a non-null `parse_error` represents an unparseable stub.

### Changes to `fpt_chat_stats.py`

- **Keep**: `detect_asm_reports` as the cheap regex pre-filter (`shop + N cọc` heuristic).
- **Delete**: `parse_asm_report`, `parse_tttc_report`, `_extract_sections`, `_parse_vnd_amount`, and the TTTC regex constants (`_TTTC_VENUE_RE`, `_TTTC_REVENUE_PCT_RE`, `_TTTC_HOT_PCT_RE`, `_TTTC_HOT_RATIO_RE`, `_TTTC_TB_BILL_VALUE_RE`, `_TTTC_CUSTOMER_RE`, `_TTTC_NARRATIVE_BOUNDARY_RE`, `_tttc_metrics_area`, `_to_pct`, `_first_n_lines`). Net ~300 lines removed.
- **Add**: `extract_all_reports(messages: list) -> list[Report]` orchestrator that calls into `llm_extractor.extract_reports` per candidate message.
- **Adapt**: `analyze_asm_reports`, `analyze_multiday`, `write_asm_excel`, `check_asm_compliance`, and `app.py` UI renderers consume `list[Report]` instead of the old per-type lists. Filtering by type is `[r for r in reports if r["report_type"] == "daily_shop_vt"]`.

### Pipeline

```
messages (from fetch_all_messages / --load)
    │
    ▼
detect_asm_reports(messages)                  # cheap regex pre-filter
    │
    ▼
for each candidate msg:
    extract_reports(msg)
        │
        ├── key = sha256(content) + PROMPT_VERSION
        ├── disk cache lookup → hit: return cached; stats.llm_cached += 1
        ├── _llm_call(content) → validate → write cache → stats.llm_call += 1
        └── on any failure → return [unparseable_stub(msg, reason)]; stats.llm_error += 1
    │
    ▼
flat list[Report]  →  analyze_* / write_*_excel / UI renderers
```

### Prompt design

**Single prompt** handles classification + extraction + combined-message splitting in one call. OpenAI JSON mode (`response_format={"type": "json_object"}`, `temperature=0`) for schema enforcement.

**System prompt** (text stored as module constant, version-tagged):

```
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
      "deposit_count": int | null,     // daily only
      "ra_tiem_count": int | null,
      "kh_tu_van_count": int | null,
      "tich_cuc": string | null,       // preserve original Vietnamese
      "van_de": string | null,
      "da_lam": string | null,
      "revenue_pct": float | null,     // weekend only; 133.0 for "133%"
      "hot_pct": float | null,
      "hot_ratio_pct": float | null,
      "tb_bill_vnd": int | null,       // "2,2tr" → 2200000
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
```

**Response validation pipeline** (defensive — JSON mode is not 100% reliable across providers):

1. `json.loads` → on fail, raise `LLMParseError`.
2. `reports` must be a list; each item must have `report_type` ∈ valid enum.
3. Coerce obvious type mismatches (e.g. `"133"` → `133.0`) where safe.
4. On any step failure → `LLMParseError`, caught upstream, produces unparseable stub.

**Model**: default `gpt-4o-mini`. Token envelope: typical ~200–600 in, ~150–400 out; worst case combined message ~1500 in, ~800 out.

### Config & secrets

Three settings, following existing precedence (CLI > env > `config.json` > default):

| Setting | CLI flag | Env var | `config.json` key | Default |
|---|---|---|---|---|
| API key | *(none — sensitive)* | `OPENAI_API_KEY` | `llm.api_key` (in gitignored `config.json`) | *required* |
| Base URL | `--llm-base-url` | `OPENAI_BASE_URL` | `llm.base_url` | `https://api.openai.com/v1` |
| Model | `--llm-model` | `LLM_MODEL` | `llm.model` | `gpt-4o-mini` |

**Streamlit UI**: three sidebar inputs (URL, model, API key as `type="password"`), persisted in browser `localStorage` under `fpt_llm_base_url`, `fpt_llm_model`, `fpt_llm_api_key` — identical pattern to the existing `fpt_token` (never written to `config.json`).

**Dependency**: add `openai>=1.0` to `requirements.txt`.

### Disk cache

- Location: `.llm_cache/` at project root. Added to `.gitignore`.
- **Logical cache key**: `sha256(content) + "_" + PROMPT_VERSION` (full 64-char hex).
- **On-disk filename**: `.llm_cache/<first-16-hex-chars-of-sha256>_<prompt_version>.json` — truncated to 16 hex chars (64 bits) for readability. Collision probability for the message volumes here is negligible; the first-line header inside each cache file records the full sha256 so collisions would be detectable if they ever occurred.
- **Contents stored**: only LLM-derived extraction fields (the per-report payload). Message-level metadata (`sender`, `sender_id`, `sent_at`, `message_id`, `source`) is NOT stored in the cache file — `extract_reports(msg)` always reconstructs it from `msg` on both cache-hit and cache-miss paths. This keeps `_load_cache(content_hash)` signature pure-functional on content and means cache files remain valid across re-ingests where the same content reappears with different `message_id`.
- No TTL — content is immutable.
- No locking — CLI and Streamlit (per session) are single-threaded; duplicate writes are idempotent.

### Stats

Module-level counters reset on process start:

```python
{"llm_call": int, "llm_cached": int, "llm_error": int}
```

- CLI: printed to stderr at end of `main()`: `[llm] llm_call=23 cached=142 error=0 — cache hit rate 86%`.
- Streamlit: shown in sidebar after each run via `st.caption()`.

### Error handling

| Failure | Response |
|---|---|
| Missing API key / base URL at extraction time | Raise immediately with message: *"Set OPENAI_API_KEY (env or sidebar). Extraction requires LLM access."* Aborts run. |
| `openai.APIConnectionError` / `APITimeoutError` | Retry once with 2s backoff. On second failure → unparseable stub. |
| `openai.RateLimitError` | Retry up to 3 times with exponential backoff (4s, 8s, 16s). On final failure → unparseable stub. |
| Invalid JSON / schema mismatch | No retry (temperature=0 deterministic). Log to stderr with `message_id` + first 200 chars of content. Return unparseable stub. |
| LLM returns `unparseable: true` | Return `[]` (no reports from this message). Not an error. |

**Unparseable stub**:
```python
{
    "report_type": "unknown",
    "shop_ref": None,
    "sender": msg["user"]["displayName"],
    "sender_id": msg["user"]["id"],
    "sent_at": msg["createdAt"],
    "message_id": msg["id"],
    "source": "llm",
    "parse_error": "<short reason>",
    # all daily/weekend fields: None
}
```

Downstream callsites (`analyze_*`, `write_*_excel`, UI) treat `parse_error is not None` as a signal to render the raw message in a dedicated "Không parse được" section, not drop it silently.

### Testing

Two complementary test suites (pytest):

**A. Golden-file corpus tests (`tests/test_templates.py`)**
- For each file in `templates/daily/*` and `templates/weekend/*`: load file, wrap in a synthetic `msg` dict, run through `extract_reports` with a mocked OpenAI client returning canned JSON, assert exact equality against `templates/<name>.expected.json`.
- Catches prompt-drift, schema-drift, and callsite breakages.
- Growing the corpus is low-friction: drop a file in → add its `.expected.json` → done.

**B. Unit tests (`tests/test_llm_extractor.py`)**
- Cache read/write.
- Prompt version invalidation (changing `PROMPT_VERSION` must bypass old cache entries).
- JSON validation + schema coercion edge cases.
- Unparseable stub shape.
- Retry/backoff behavior (mock `openai.RateLimitError`, `APITimeoutError`).

**Fixtures**: a single pytest fixture builds a fake OpenAI client whose `.chat.completions.create` returns canned JSON keyed by content hash. All tests are offline.

**Tooling**: new `requirements-dev.txt` with `pytest`, `pytest-mock`. Production `requirements.txt` gains only `openai>=1.0`. `CLAUDE.md` Commands section gains a `pytest` entry.

### Out of scope for v1

- Batching LLM calls (if fallback volume justifies it later, revisit with `asyncio.gather`).
- Streaming responses.
- Tool/function calling.
- Few-shot examples in the prompt (add only if empirical accuracy is insufficient).
- Live-API integration tests.
- CI automation (GitHub Actions).

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| OpenAI-compatible provider doesn't support JSON mode → malformed output. | `_validate_and_coerce` is defensive; malformed → unparseable stub, not crash. The `reason` field makes the failure visible. |
| Prompt drift between LLM vendors → `gpt-4o-mini` prompt works differently on a local Ollama model. | `LLM_MODEL` is config-driven; golden tests protect the default (`gpt-4o-mini`). Swapping model is the user's call and may require prompt tuning. |
| Cost spike if cache is wiped (Streamlit Cloud redeploy). | Worst case = one-time re-extraction; still bounded by the number of unique messages in the window. Documented as known tradeoff. |
| LLM hallucinates numeric values (e.g. invents a `deposit_count` not in the message). | Rule in system prompt: *"Never invent values. Missing → null."* Golden tests catch regressions against known templates. Manual verification via `scripts/verify_llm_extract.py` on new production snapshots. |
| Combined messages (weekend 7/8) split incorrectly. | Golden tests cover both templates 7 and 8. Schema is 1-to-N by design — no structural blocker. |
| Callsite breakage (`analyze_*`, `write_*_excel`, `app.py`). | Refactoring is in-scope; golden tests driven by real template files exercise downstream flow once adapters are added. |

## Implementation order (for writing-plans skill)

1. New module `llm_extractor.py` with `Report` schema, cache, stats, stub `_llm_call` returning `NotImplementedError`.
2. Wire OpenAI SDK + prompt into `_llm_call`; config plumbing (env vars, `config.json`, CLI flags).
3. Refactor `fpt_chat_stats.py`: delete old parsers, add `extract_all_reports` orchestrator, adapt `analyze_*`, `write_*_excel`, `check_asm_compliance`.
4. Adapt `app.py`: sidebar inputs, `localStorage` plumbing, stats display, unparseable rendering.
5. Testing: `requirements-dev.txt`, fixtures, golden files for all 15 templates, unit tests.
6. Documentation: update `CLAUDE.md` (commands, architecture section), update `openspec/specs/fpt-chat-stats/spec.md` or supersede with an OpenSpec change proposal (`openspec/changes/<id>/`).

## Open questions

None remaining — all brainstorm questions resolved.
