## REMOVED Requirements

### Requirement: Daily ASM Report Parser
**Reason:** Replaced by LLM-based extraction. Regex-based `parse_asm_report` and its helpers (`_extract_sections`, `_parse_vnd_amount`) are deleted.

**Migration:** Callers now invoke `llm_extractor.extract_reports(msg)` (via the `extract_all_reports(messages)` orchestrator in `fpt_chat_stats.py`). The returned `list[Report]` is filtered downstream by `report_type == "daily_shop_vt"` and `parse_error is None`.

### Requirement: TTTC Report Parser
**Reason:** Replaced by LLM-based extraction. Regex-based `parse_tttc_report` and its 7 supporting regex constants (`_TTTC_VENUE_RE`, `_TTTC_REVENUE_PCT_RE`, `_TTTC_HOT_PCT_RE`, `_TTTC_HOT_RATIO_RE`, `_TTTC_TB_BILL_VALUE_RE`, `_TTTC_CUSTOMER_RE`, `_TTTC_NARRATIVE_BOUNDARY_RE`) plus helpers (`_first_n_lines`, `_to_pct`, `_tttc_metrics_area`) are deleted.

**Migration:** Same as above — callers invoke `extract_all_reports`. TTTC reports have `report_type == "weekend_tttc"`. Field renames: `tb_bill` → `tb_bill_vnd`, `hot_ratio` → `hot_ratio_pct`, `venue` → `shop_ref` (analyze_tttc_reports projects `shop_ref` under the alias `venue` for downstream compatibility).

### Requirement: Report Classifier
**Reason:** No longer needed. Message classification (daily_shop_vt vs weekend_tttc) is performed by the LLM in a single pass that also extracts the structured fields. The `classify_report`, `_CLASSIFY_RE_COC`, and `_CLASSIFY_RE_TTTC` helpers are deleted.

## ADDED Requirements

### Requirement: LLM-based Report Extraction
`llm_extractor.py` SHALL expose `extract_reports(msg: dict) -> list[Report]` that performs all classification and extraction of Vietnamese ASM/TTTC chat reports via a single LLM call per message (with disk caching by content hash + prompt version).

The function SHALL:
- Accept a message dict with at least `content`, `user.displayName`, `user.id`, `createdAt`, `id`.
- Check disk cache first (`.llm_cache/<first-16-hex-of-sha256>_<PROMPT_VERSION>.json`). On hit, return hydrated reports with `source == "cache"` without an LLM call.
- Otherwise call the configured OpenAI-compatible endpoint with JSON mode, `temperature=0`, a module-level `SYSTEM_PROMPT` that instructs extraction into the unified `Report` schema. Validate the response with `_validate_and_coerce`. On success, cache and return hydrated reports with `source == "llm"`.
- On `LLMParseError` (bad JSON, schema violation) or `LLMConfigError` (missing key, auth failure), return a single unparseable stub `Report` with `report_type == "unknown"`, `parse_error == <reason>`, and all extraction fields null. Increment `_stats["llm_error"]`.
- NEVER raise — all failure modes produce a valid `list[Report]` (possibly empty or containing only stubs).

`extract_reports` SHALL support combined messages (one chat message containing multiple reports): the LLM returns `reports: [...]` with length ≥ 1, and `extract_reports` returns one hydrated `Report` per entry.

#### Scenario: Cache hit on second call with same content
- **GIVEN** `extract_reports` was previously called on a message with content C and returned 1 report
- **WHEN** `extract_reports` is called on a different message with the same content C (different `message_id` / `sender`)
- **THEN** the result contains 1 report hydrated with the new message's metadata, `source == "cache"`, no LLM call is made, and `_stats["llm_cached"]` is incremented.

#### Scenario: LLM returns unparseable
- **GIVEN** a chat message that isn't a report (e.g., "Dear Anh Chị")
- **WHEN** the LLM responds with `{"reports": [], "unparseable": true, "reason": "greeting"}`
- **THEN** `extract_reports` returns `[]` (no stub — not an error, just not a report) and `_stats["llm_call"]` is incremented.

#### Scenario: LLM call fails with bad JSON
- **GIVEN** the LLM returns content `"not-json{{{"` after all retries
- **WHEN** `extract_reports` is called
- **THEN** the result contains exactly one report with `report_type == "unknown"`, `parse_error` is a non-null string, `source == "llm"`, and `_stats["llm_error"]` is incremented.

### Requirement: Report Schema
`llm_extractor.Report` SHALL be a single `TypedDict` with 19 fields. The discriminator `report_type` has literal values `"daily_shop_vt" | "weekend_tttc" | "unknown"`. Per-type numeric fields default to `None` when the report_type doesn't apply. Narrative fields (`tich_cuc`, `van_de`, `da_lam`) SHALL preserve the original Vietnamese text verbatim.

Fields:
- **Common (8):** `report_type`, `shop_ref: str | None`, `sender: str`, `sender_id: str`, `sent_at: str`, `message_id: str`, `source: Literal["llm","cache"]`, `parse_error: str | None`.
- **daily_shop_vt (6):** `deposit_count: int | None`, `ra_tiem_count: int | None`, `kh_tu_van_count: int | None`, `tich_cuc: str | None`, `van_de: str | None`, `da_lam: str | None`.
- **weekend_tttc (5):** `revenue_pct: float | None`, `hot_pct: float | None`, `hot_ratio_pct: float | None`, `tb_bill_vnd: int | None`, `customer_count: int | None`.

VND amounts SHALL be normalized to integer đồng (`"2,2tr"` → `2_200_000`, `"134.927.000"` → `134_927_000`). Percentages SHALL be returned as floats without the `%` sign (`"133%"` → `133.0`). Extraction SHALL NOT invent values — missing data yields `null`.

#### Scenario: Greeting is not shop_ref
- **GIVEN** a message starting `"Dear Anh, Chị\nEm xin phép đánh giá nhanh Shop: 80035 ..."`
- **WHEN** extracted
- **THEN** `shop_ref` is `"80035 ..."` (the actual shop name), NOT `"Dear Anh, Chị"`.

### Requirement: Disk Cache
`llm_extractor` SHALL cache LLM extraction results to disk under `CACHE_DIR` (default `Path(".llm_cache")`) keyed by `sha256(content) + "_" + PROMPT_VERSION`. The on-disk filename SHALL use the first 16 hex chars of the sha256 for readability; each cache file SHALL store the full `_cache_key` field in its JSON body as a collision guard — `_load_cache` SHALL return `None` on mismatch rather than returning stale data. Cache files SHALL use `ensure_ascii=False` so Vietnamese diacritics persist as literals on disk.

The cache SHALL NOT store per-message metadata (`sender`, `sender_id`, `sent_at`, `message_id`, `source`) — only the LLM-derived extraction fields. The orchestrator hydrates metadata from the current `msg` on every cache hit, so different messages with identical content correctly share cache entries.

`PROMPT_VERSION` SHALL be a module-level string constant. Any change to `SYSTEM_PROMPT` or `_validate_and_coerce` semantics SHALL bump `PROMPT_VERSION` to invalidate the cache atomically.

#### Scenario: PROMPT_VERSION bump invalidates cache
- **GIVEN** a cache file keyed by `sha256(C) + "_v1"`
- **WHEN** `PROMPT_VERSION` is changed to `"v2"` and `extract_reports` is called with the same content C
- **THEN** the v1 file is ignored (different filename), and a new LLM call is made producing a v2 cache entry.

### Requirement: Retry and Error Classification in LLM Transport
`_llm_call` SHALL retry transient SDK errors with exponential backoff (via the monkey-patchable `_RETRY_SLEEP` hook):
- `openai.APIConnectionError` and `openai.APITimeoutError`: up to 1 retry with base 2s backoff.
- `openai.RateLimitError`: up to 3 retries with base 4s backoff.
- `openai.AuthenticationError`, `openai.PermissionDeniedError`, `openai.NotFoundError`: NO retry; re-raised as `LLMConfigError` so the Streamlit sidebar / CLI can prompt for a key/model fix.
- `json.JSONDecodeError` or `_validate_and_coerce` failure: NO retry (temperature=0 makes retry pointless); raise `LLMParseError`.
- LLM response with empty `message.content`: treat as `LLMParseError` (refusals / tool-only responses must not silently return `[]`).

The OpenAI client SHALL be cached keyed by `(api_key, base_url)` so config changes via `configure()` invalidate the cache while concurrent callers with different credentials are not cross-contaminated.

#### Scenario: Authentication failure becomes config error
- **GIVEN** the configured API key is invalid
- **WHEN** `_llm_call` is invoked
- **THEN** `openai.AuthenticationError` is raised once (no retry), and `_llm_call` re-raises it as `LLMConfigError`.

### Requirement: Stats and Observability
`llm_extractor` SHALL maintain process-wide counters `{llm_call, llm_cached, llm_error}` (mutable module-level dict for simplicity). `get_stats()` SHALL return a defensive copy; `format_stats()` SHALL return a human-readable line including cache hit rate = `cached / (call + cached)` with zero-division guard.

`fpt_chat_stats.main()` SHALL print `format_stats()` to stderr after report generation. Streamlit SHALL render it via `st.caption()` in the sidebar after each run.

#### Scenario: Mixed cache and live calls report accurate hit rate
- **GIVEN** 3 fresh LLM calls and 17 cache hits in the same run, no errors
- **WHEN** `format_stats()` is called
- **THEN** the result contains `llm_call=3`, `cached=17`, `error=0`, and `85%` (17 / (17 + 3) = 0.85).

### Requirement: Report Orchestrator in fpt_chat_stats
`fpt_chat_stats` SHALL expose `extract_all_reports(messages: list) -> list[Report]` that:
1. Applies the cheap `detect_asm_reports` regex pre-filter (unchanged from pre-refactor — `shop` + `N cọc`).
2. Delegates extraction of each candidate to `llm_extractor.extract_reports`.
3. Returns a flat list (may be longer than the candidate count due to combined messages).

Existing analysis functions (`analyze_asm_reports`, `analyze_tttc_reports`, `check_asm_compliance`, `check_late_reporters`, `analyze_multiday`) SHALL filter the input by `report_type` and skip reports with non-null `parse_error` at the function top so callers can pass the flat list unfiltered.

`analyze_weekly` SHALL call `llm_extractor.extract_reports` per qualifying message (replacing the old `classify_report` + `parse_asm_report`/`parse_tttc_report` dispatch), split results by `report_type` into `parsed_shop_vt` / `parsed_tttc` lists, and collect stubs with `parse_error` into a new `unparseable` list surfaced in the returned dict.

#### Scenario: Combined weekend message produces both Shop VT and TTTC reports
- **GIVEN** a single chat message whose body contains a Shop VT block AND a TTTC block
- **WHEN** `extract_all_reports([msg])` is called
- **THEN** the result contains TWO `Report` dicts — one with `report_type == "daily_shop_vt"` and one with `report_type == "weekend_tttc"` — both hydrated with the same `message_id` and `sender` from the source message.

#### Scenario: Unparseable stubs do not contaminate analysis
- **GIVEN** a list of 10 reports — 7 valid daily, 2 valid weekend, 1 unparseable stub with `parse_error != None`
- **WHEN** `analyze_asm_reports` is called
- **THEN** the function filters to the 7 valid daily reports only; the stub is not counted in deposit totals, low/high bucket counts, or compliance checks.

### Requirement: LLM Configuration
`llm_extractor.configure(api_key, base_url, model)` SHALL set the corresponding `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `LLM_MODEL` environment variables (when the argument is non-None) and reset the client cache. Precedence (highest first): CLI flag, env var, `config.json` `llm.{base_url,model,api_key}`, built-in default (`https://api.openai.com/v1`, `gpt-4o-mini`).

The API key SHALL NEVER be written to `config.json` or persisted to disk outside `.llm_cache/` by the tool — Streamlit persists it only in the browser's `localStorage` under key `fpt_llm_api_key`, matching the existing `fpt_token` policy.

CLI SHALL expose `--llm-base-url` and `--llm-model` flags; the API key SHALL be read from the `OPENAI_API_KEY` environment variable (no CLI flag to avoid shell-history leakage).

#### Scenario: configure() overwrites stale client cache
- **GIVEN** `_client_cache` holds a client built from key `k1` at base URL `u1`
- **WHEN** `configure(api_key="k2", base_url="u1", model="gpt-foo")` is called
- **THEN** `OPENAI_API_KEY == "k2"`, `OPENAI_BASE_URL == "u1"`, `LLM_MODEL == "gpt-foo"`, and `_client_cache` is cleared so the next `_get_client()` constructs a fresh client with `k2`.

#### Scenario: API key never written to config.json
- **GIVEN** a user types an API key in the Streamlit sidebar
- **WHEN** `_load_config` / `_save_config` are invoked
- **THEN** the `llm.api_key` field is NOT written to `config.json`; the key persists only in browser `localStorage` under `fpt_llm_api_key`.
