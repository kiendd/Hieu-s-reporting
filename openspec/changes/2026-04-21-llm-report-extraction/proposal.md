# Proposal: llm-report-extraction

## Why

The ASM/TTTC report parsers are hand-written regex:
- `detect_asm_reports` + `parse_asm_report` + `_extract_sections` + `_parse_vnd_amount` for Shop VT daily reports
- `parse_tttc_report` + 7 specialized regex constants (`_TTTC_VENUE_RE`, `_TTTC_REVENUE_PCT_RE`, `_TTTC_HOT_PCT_RE`, `_TTTC_HOT_RATIO_RE`, `_TTTC_TB_BILL_VALUE_RE`, `_TTTC_CUSTOMER_RE`, `_TTTC_NARRATIVE_BOUNDARY_RE`) for weekend TTTC reports

The regex approach is structurally fragile:

1. **Template drift.** Users compose reports freely. 7 daily + 8 weekend variants already exist in `templates/` and new shapes appear regularly. Each new shape requires regex patches — recent commit history shows this as ongoing maintenance cost (`fix: _extract_sections chặn URL không bị bắt làm nhãn section`, `refactor(ui): tách _render_shop_vt_sections`).

2. **Silent failures.** Regex can return "successfully parsed" output where field values are garbage because the user's message only *almost* matched the template. Neither the regex output nor the source messages can be fully trusted.

3. **Schema limitations.** Combined messages (weekend templates 7 & 8) contain both Shop VT and TTTC blocks; the current one-to-one parser cannot represent them.

## What changes

- Introduce `llm_extractor.py` — a new top-level module owning:
  - `Report` TypedDict (1 unified schema, 19 fields, discriminated by `report_type ∈ {"daily_shop_vt", "weekend_tttc", "unknown"}`).
  - Disk cache keyed by `sha256(content) + PROMPT_VERSION` under `.llm_cache/`.
  - Stats counters (`llm_call`, `llm_cached`, `llm_error`).
  - `SYSTEM_PROMPT` with Vietnamese-aware extraction rules.
  - `_validate_and_coerce` — defensive JSON/schema validator.
  - `_llm_call` — OpenAI SDK wrapper with retry/backoff (conn/timeout × 1, rate-limit × 3) and auth-error classification.
  - `extract_reports(msg) -> list[Report]` — main entry.

- Add `extract_all_reports(messages)` orchestrator to `fpt_chat_stats.py`: applies the regex pre-filter (`detect_asm_reports`), then LLM-extracts each candidate. Returns `list[Report]` (may include unparseable stubs with `parse_error` set).

- Delete regex parsers: `classify_report`, `parse_asm_report`, `_extract_sections`, `_parse_vnd_amount`, `parse_tttc_report`, and the 7 TTTC regex constants + helpers (`_first_n_lines`, `_to_pct`, `_tttc_metrics_area`).

- Adapt `analyze_asm_reports`, `analyze_tttc_reports`, `check_asm_compliance`, `check_late_reporters`, `analyze_multiday`, `write_asm_excel` callsites to filter the flat `list[Report]` by `report_type` and `parse_error is None`.

- CLI: add `--llm-base-url` / `--llm-model` flags + `llm_extractor.configure()` plumbing (env > config.json > default). Print `format_stats()` to stderr at end of `main`.

- Streamlit (`app.py`): add sidebar inputs for LLM URL / model / API key (password), persisted in browser `localStorage` under `fpt_llm_*` keys (never written to `config.json`, same policy as the FPT chat token). Render unparseable reports in a dedicated expander; show stats caption after a run.

- Add `tests/` with pytest (+ `pytest-mock`) — `requirements-dev.txt`. 15 golden-file tests drive `templates/{daily,weekend}/*` through a primed fake OpenAI client, plus unit tests for cache, stats, retry, validation, auth classification.

Design details and brainstorm decisions live in `docs/superpowers/specs/2026-04-21-llm-report-extraction-design.md`; implementation plan in `docs/superpowers/plans/2026-04-21-llm-report-extraction.md`.

## Design decisions (fixed during brainstorm)

| # | Topic | Decision |
|---|---|---|
| 1 | Scope | LLM always on extraction; regex only as cheap pre-filter. |
| 2 | Provider | OpenAI Python SDK, configurable `base_url` + `api_key` + `model`. |
| 3 | Schema | 1-to-N, unified `Report` with per-type nullable fields. |
| 4 | Caching | Disk cache keyed by `sha256(content) + PROMPT_VERSION`. |
| 5 | Failure mode | Unparseable reports preserved with `parse_error`, surfaced in UI/Excel. |
| 6 | Tests | Golden-file corpus + unit tests; no live-API or CI in v1. |

## Out of scope

- Batching LLM calls (asyncio.gather etc.). Per-message calls + disk cache are sufficient.
- Streaming, tool calling, few-shot embedded examples.
- Live-API integration tests; CI wiring.

## Scope of files touched

- `llm_extractor.py`: new module.
- `fpt_chat_stats.py`: delete ~330 lines of regex parsers; add `extract_all_reports`; filter downstream by `report_type`; CLI flags + stats line.
- `app.py`: sidebar LLM config + unparseable rendering + stats caption.
- `requirements.txt` / `requirements-dev.txt` / `pytest.ini` / `tests/{conftest,test_llm_extractor,test_templates}.py`.
- `templates/{daily,weekend}/*.expected.json` × 15.
- `.gitignore`: add `.llm_cache/*` + `!.llm_cache/.gitkeep`; add `!templates/**/*.expected.json` to let golden files escape the `*.json` blanket.
- `config.example.json`: add `llm.base_url` / `llm.model` block (no `api_key`).
- `CLAUDE.md`: updated Commands + Architecture sections.
- `openspec/specs/fpt-chat-stats/spec.md`: updated parsing requirements (in this change's spec delta).
