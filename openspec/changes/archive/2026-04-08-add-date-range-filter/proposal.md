# Change: Add Date Range Filter for Statistics

## Why
The tool currently analyzes every message ever posted in a group, making it impossible to scope a report to a specific period (e.g., "who requested documents this month?"). Users need `--from` and `--to` flags so they can produce time-bounded reports without manually post-processing output.

## What Changes
- **NEW** `--from DATE` CLI flag — exclude messages created before this date (inclusive lower bound).
- **NEW** `--to DATE` CLI flag — exclude messages created after this date (inclusive upper bound).
- Date format: `YYYY-MM-DD`; dates are interpreted as midnight UTC (start of day for `--from`, end of day for `--to`).
- Filter is applied at the **analysis stage**: all messages are still fetched, but only those within the range are counted and included in the report. This keeps the implementation simple and leaves raw data intact for `--save`.
- The report header (text format) MUST display the active date range so the reader knows the scope.

## Impact
- Affected specs: `fpt-chat-stats` (MODIFIED: Statistical Analysis; ADDED: Date Range Filter)
- Affected code: `fpt_chat_stats.py` — `analyze()`, `print_text_report()`, `print_json_report()`, `main()`
- No breaking changes; both flags are optional and the tool behaves identically when omitted.
