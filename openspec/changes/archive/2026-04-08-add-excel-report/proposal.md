# Change: Add Excel Report Export

## Why
The text/JSON output is good for spot-checks but cannot be shared as a formal report or filtered in a spreadsheet. The team needs a ready-to-share `.xlsx` file with two views:
- A **summary pivot** (user × month request counts) for management review.
- A **detail log** (one row per request) for audit and verification.

## What Changes
- **NEW** `--excel FILE` CLI flag — writes an `.xlsx` file alongside (or instead of) the text/JSON report.
- **NEW** Sheet 1 "Tổng hợp": pivot table with users as rows, months as columns, request counts as values, and a "Tổng" (total) column.
- **NEW** Sheet 2 "Chi tiết": one row per request message with columns — STT, Ngày giờ, Người dùng, Nội dung, Links (comma-separated URLs).
- **MODIFIED** `analyze()` — add `content` field to each request entry so the detail sheet can show message text.
- **NEW** dependency: `openpyxl` added to `requirements.txt`.

## Design Decisions
- **`openpyxl` only** — pure Python, no pandas. Keeps the tool dependency-light.
- **One file, two sheets** — single `.xlsx` output is easier to share than two separate files.
- **`--excel` is additive** — combining `--excel report.xlsx` with `--format text` still prints the text report to stdout; Excel is written to file.
- **Vietnamese column headers** — consistent with existing text report style.
- **Timestamps in Vietnam timezone (UTC+7)** displayed in detail sheet for readability.

## Impact
- Affected specs: `fpt-chat-stats` (MODIFIED: Statistical Analysis; ADDED: Excel Report Export)
- Affected code: `fpt_chat_stats.py` — `analyze()`, `main()`; new `write_excel()` function
- `requirements.txt` — add `openpyxl>=3.1.0`
- No breaking changes; `--excel` is opt-in.
