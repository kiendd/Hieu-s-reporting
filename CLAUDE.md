# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

## Commands

```bash
pip install -r requirements.txt          # runtime deps (requests, openpyxl, streamlit, streamlit-javascript, openai)
pip install -r requirements-dev.txt      # dev-only: pytest, pytest-mock

# Streamlit web UI (main entry point for end users)
streamlit run app.py                      # serves at http://localhost:8501

# CLI — same analysis pipeline, no browser
OPENAI_API_KEY=sk-... python fpt_chat_stats.py --today
OPENAI_API_KEY=sk-... python fpt_chat_stats.py --from 2026-04-01 --to 2026-04-16 --excel bao_cao.xlsx

# Offline workflow (no chat token needed once saved; LLM key still required unless cached)
python fpt_chat_stats.py --save raw.json                    # snapshot API response
OPENAI_API_KEY=sk-... python fpt_chat_stats.py --load raw.json --today

# Tests
pytest                                    # unit tests + 15-template golden-file suite
pytest -v tests/test_llm_extractor.py     # llm_extractor unit tests only
```

Tests live under `tests/`. The golden-file suite primes a fake OpenAI client with `templates/{daily,weekend}/*.expected.json` canned JSON and asserts extract_reports hydrates correctly — it does NOT exercise LLM quality. Real-LLM validation is manual via `--load raw.json` with a real key against saved snapshots.

## Architecture

This is a two-surface tool (CLI + Streamlit UI) over a shared core library. Both surfaces call into `fpt_chat_stats.py` — the UI imports its functions directly rather than shelling out.

**Pipeline (`fpt_chat_stats.py` + `llm_extractor.py`):** Fetch → Detect → LLM Extract → Analyze → Report.
1. `fetch_all_messages` paginates the FPT Chat API backwards via cursor `messageIdInc` + `cursorType=PREVIOUS`, stopping early if `date_from` is satisfied.
2. `extract_all_reports` applies the cheap regex pre-filter (`detect_asm_reports`: `shop` + `N cọc`) and delegates extraction to `llm_extractor.extract_reports`, which calls the OpenAI API (or OpenAI-compatible endpoint) with JSON mode and caches results on disk under `.llm_cache/` keyed by `sha256(content) + PROMPT_VERSION`.
3. A single LLM call per message returns `list[Report]`. Combined messages (Shop VT + TTTC in one chat message) naturally produce multiple reports. Unparseable messages yield a stub with `parse_error` set — surfaced in UI/Excel as "Không parse được: {reason}" rather than silently dropped.
4. Downstream (`analyze_asm_reports`, `analyze_tttc_reports`, `check_asm_compliance`, `check_late_reporters`, `analyze_multiday`, `write_asm_excel`) filter the flat `list[Report]` by `report_type` (`daily_shop_vt` / `weekend_tttc`) and `parse_error is None`.
5. Output: `print_asm_report` (stdout), `write_asm_excel` (4-sheet xlsx), plus an `llm_extractor.format_stats()` line to stderr (`llm_call=N cached=M error=0 — cache hit rate XX%`).

**LLM config:** `llm_extractor.configure()` reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `LLM_MODEL` from env (defaults: `https://api.openai.com/v1` / `gpt-4o-mini`). CLI flags `--llm-base-url` / `--llm-model` override env. Streamlit stores all three in browser `localStorage` under `fpt_llm_base_url` / `fpt_llm_model` / `fpt_llm_api_key` and NEVER writes the API key to `config.json` — same policy as the FPT chat token.

**Auth quirk:** the FPT chat API requires the token sent in BOTH `Authorization: Bearer <t>` header AND a `fchat_ddtk` cookie on the `api-chat.fpt.com` domain (see `build_session`). Missing the cookie returns 401 even with a valid header.

**Time handling:** API timestamps are UTC ISO-8601; all business logic (deadlines, daily bucketing) uses VN time (UTC+7), computed manually via `datetime.fromtimestamp(dt.timestamp() + 7*3600, tz=timezone.utc)`. Date CLI flags accept `YYYY-MM-DD` and are converted through `parse_date_arg`.

**Streamlit app (`app.py`):**
- Stores the user's group library in browser `localStorage` via `streamlit-javascript` — keys `fpt_groups_library` (current) and `fpt_groups` / `fpt_group_configs` (legacy, migrated on first load by `_migrate_legacy`).
- The token is kept in `localStorage` under `fpt_token` and is deliberately **never written to `config.json`** (`_load_config` strips it).
- Uses `st_javascript` with a nullable-return pattern (`_ls_get_nullable`) to distinguish "JS not ready yet" from "key absent", then reruns until `ls_loaded` flips true. Preserve this pattern when touching localStorage reads.

**Config precedence:** CLI flag > `config.json` (gitignored) > built-in defaults. `config.example.json` is the committed template.

**Domain vocabulary (Vietnamese is first-class in this codebase):** `đặt cọc` = deposits, `ra tiêm` = vaccinations delivered, `đã làm` = tasks done, `tích cực` = positives, `vấn đề` = issues, `ASM` = Area Sales Manager. User-facing strings and section labels are Vietnamese — don't Anglicize.

## Conventions

- Single-file scripts are preferred for the main pipeline (`fpt_chat_stats.py`). Split only when complexity demands it — `llm_extractor.py` is split because its concerns (OpenAI client, prompt engineering, cache, stats) are orthogonal to the fetch/analyze flow.
- Progress/debug logs → `stderr`; report output → `stdout`. Keep this split so `--save`/pipe workflows stay clean.
- Commits are direct to `main`; commit messages in this repo use Vietnamese (see `git log`).
- The tool is **read-only** against the chat API. Do not add endpoints that POST/PUT/DELETE.

## OpenSpec

Specs live under `openspec/specs/{asm-report-analysis,fpt-chat-stats,multi-group-reporting,web-ui}`. For any feature work beyond a bugfix, follow `openspec/AGENTS.md` — proposals go in `openspec/changes/<change-id>/` and must pass `openspec validate <id> --strict --no-interactive` before implementation.
