# Change: Add Document Frequency Sheet to Excel Report

## Why
The existing Excel report shows *who* requested documents and *when*, but not *which documents* are most in demand. A frequency sheet lets the team see which Gartner/external URLs are requested repeatedly, helping prioritize procurement or identify duplicated effort.

## What Changes
- **NEW** Sheet 3 "Tần suất tài liệu" added to the `.xlsx` output.
  - One row per unique URL found in request messages.
  - Columns: STT, URL, Số lần request, Người request (danh sách tên không trùng).
  - Sorted by request count descending.

## Design Decisions
- **Source data**: `stats["links"]` — each entry is one URL occurrence from a TEXT request message. Grouping by `url` field gives the frequency count.
- **"Người request"**: deduplicated list of display names who requested that URL, joined by ", ".
- **No new CLI flag needed** — sheet is added whenever `--excel` is used.
- **Keyword-only requests** (no links) produce no URL entries and are not represented in this sheet — they appear in "Chi tiết" instead.

## Impact
- Affected specs: `fpt-chat-stats` (MODIFIED: Excel Report Export)
- Affected code: `write_excel()` in `fpt_chat_stats.py`
- No breaking changes.
