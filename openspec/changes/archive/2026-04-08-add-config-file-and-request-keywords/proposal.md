# Change: Add Config File and Keyword-based Request Detection

## Why
Two pain points addressed together:

1. **Token friction** — users must pass `--token` and `--group` on every invocation. A config file lets them set these once and forget.
2. **Incomplete request detection** — the tool currently identifies "requests" only by the presence of `metadata.links`. Messages like _"Nhờ c down giúp em tài liệu này"_ without an embedded link are missed. Configurable keywords enable content-based detection and unlock a new "requests per month" metric.

## What Changes
- **NEW** `config.json` — optional JSON config file (loaded from current directory by default).
  - Stores: `token`, `group`, `api_url`, `request_keywords`.
  - Precedence: CLI args > config file > built-in defaults.
  - `--token` and `--group` become optional when present in the config file.
- **NEW** `--config FILE` CLI flag — override the default `config.json` path.
- **NEW** keyword-based request detection — a TEXT message is classified as a "request" if its content contains **any** of the configured keywords (case-insensitive substring match), in addition to the existing link-based detection.
- **NEW** `requests_by_month` statistic — count of keyword-matched request messages grouped by `YYYY-MM`, displayed in both text and JSON reports.

## Design Decisions
- **JSON over TOML/INI** — Python 3.9 is in use; `tomllib` requires 3.11+. `json` is stdlib, zero new dependencies.
- **Substring match, case-insensitive** — matches real-world messages where keywords like `"nhờ"` appear mid-sentence. Prefix-only matching would miss too many cases.
- **Additive detection** — a message is a request if it matches keywords OR has links (not exclusively one or the other). This avoids losing previously counted requests.
- **Config is optional** — if `config.json` is absent and `--token`/`--group` are provided on the CLI, the tool behaves as before.

## Impact
- Affected specs: `fpt-chat-stats` (MODIFIED: Authentication; ADDED: Config File Loading, Keyword-based Request Detection, Request Count by Month)
- Affected code: `fpt_chat_stats.py` — `main()`, `analyze()`, `print_text_report()`, `print_json_report()`
- New file: `config.json` (created by user, not by the tool)
- No breaking changes; all new flags and config keys are optional.
