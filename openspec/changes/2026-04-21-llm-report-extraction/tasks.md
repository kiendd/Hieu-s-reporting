# Tasks: llm-report-extraction

Implementation plan (with step-by-step TDD and exact code) is at `docs/superpowers/plans/2026-04-21-llm-report-extraction.md`. The 16 in-repo tasks below map 1:1 to the plan's tasks 1–16 (tasks 17–18 are manual live-API smoke and are out of scope for OpenSpec validation).

## Module & tests

- [x] 1. Scaffold pytest: `requirements-dev.txt` (pytest, pytest-mock), `pytest.ini`, `tests/__init__.py`, `tests/conftest.py`, `tests/test_llm_extractor.py`; add `openai>=1.0` to `requirements.txt`; add `.llm_cache/*` + negation + golden-file negation to `.gitignore`; create `.llm_cache/.gitkeep`.
- [x] 2. Create `llm_extractor.py` with module docstring, `PROMPT_VERSION = "v1"`, `DEFAULT_MODEL = "gpt-4o-mini"`, `Report` TypedDict (19 fields — 8 common + 6 daily + 5 weekend).
- [x] 3. Add disk cache primitives: `CACHE_DIR`, `_cache_key`, `_cache_path`, `_load_cache`, `_save_cache` with collision guard (on-disk filename truncated to 16 hex chars; full sha256 stored inside for guard), `ensure_ascii=False` for Vietnamese.
- [x] 4. Add stats counters: `_stats`, `_reset_stats`, `get_stats`, `format_stats` (hit rate = cached / (call + cached), zero-div guarded).
- [x] 5. Add `SYSTEM_PROMPT` (Vietnamese-aware), `LLMParseError`, `_validate_and_coerce` with bool-rejection in `_coerce_int`/`_coerce_float` and strict string-field typing.
- [x] 6. Add OpenAI client wrapper: `_client_cache` keyed by `(api_key, base_url)`, `_RETRY_SLEEP` hook, `LLMConfigError`, `_get_client`, `_reset_client_cache`, `_llm_call` (conn/timeout retry × 1, rate-limit × 3, empty-content guard, `AuthenticationError`/`PermissionDeniedError`/`NotFoundError` → `LLMConfigError`).
- [x] 7. Add `extract_reports(msg) -> list[Report]` orchestrator + `_unparseable_stub` + `_hydrate`. On cache hit: source="cache"; on LLM error: single stub with `parse_error`.
- [x] 8. Add `configure(api_key, base_url, model)` helper; CLI `--llm-base-url` / `--llm-model` in `fpt_chat_stats.py main()` with env > config.json > default precedence.
- [x] 9. Extend `config.example.json` with `llm.base_url` + `llm.model` (no `api_key`).

## Golden corpus & callsite refactor

- [x] 10. Add `tests/test_templates.py` golden-file harness + `templates/daily/1.expected.json`.
- [x] 11. Add `.expected.json` for remaining 14 templates (6 daily + 8 weekend). Total 15 golden tests.
- [x] 12. Delete all regex parsers from `fpt_chat_stats.py`: `_CLASSIFY_RE_COC`, `_CLASSIFY_RE_TTTC`, `classify_report`, `_parse_vnd_amount`, `_extract_sections`, `parse_asm_report`, `_TTTC_*` constants (7), `_first_n_lines`, `_to_pct`, `_tttc_metrics_area`, `parse_tttc_report`.
- [x] 13. Adapt `fpt_chat_stats.py` callsites: add `extract_all_reports`; filter by `report_type` + `parse_error is None` in `analyze_asm_reports`, `analyze_tttc_reports`, `check_asm_compliance`, `check_late_reporters`, `analyze_multiday`; rewire `analyze_weekly` dispatch to call `extract_reports` once and split by `report_type`; rewire `main()` to `extract_all_reports`; map old TTTC field names (`tb_bill`→`tb_bill_vnd`, `hot_ratio`→`hot_ratio_pct`, `venue`→project from `shop_ref`); print `format_stats()` to stderr at end of main.
- [x] 14. Adapt `app.py`: sidebar LLM config inputs (Base URL / Model / API key) persisted in `localStorage` under `fpt_llm_*`, never to `config.json`; replace detect+parse with `extract_all_reports`; render unparseable reports in expander; show stats caption.

## Documentation

- [x] 15. Update `CLAUDE.md` Commands (pytest, install dev deps) + Architecture (LLM pipeline, LLM config section, auth quirk preserved).
- [x] 16. Create this OpenSpec change proposal + updated spec delta; validate with `openspec validate 2026-04-21-llm-report-extraction --strict --no-interactive`.
