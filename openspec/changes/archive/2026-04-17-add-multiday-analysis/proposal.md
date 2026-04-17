# Proposal: add-multiday-analysis

## Why
When a multi-day date range is selected (e.g. 1 week), the current report simply aggregates everything into a single flat list — no sense of trend, consistency, or which days had gaps. Adding time-aware analytics turns a weekly run into a meaningful performance review.

## Proposed Analytics (5 types)

### 1 — Xu hướng theo ngày (Daily trend chart)
A line/bar chart showing, for each calendar day in the range:
- Total deposits for that day
- Total ra tiêm for that day

Allows spotting which days were strong or weak across the group.

### 2 — Tỉ lệ báo cáo per ASM (Report-rate table)
For each ASM (sender), across the date range:
- **Số ngày báo**: distinct calendar days they sent at least one report
- **Tổng ngày**: total calendar days in the range
- **Tỉ lệ**: `report_days / total_days` as a percentage
- **Tổng cọc** accumulated over the period
- **TB cọc/ngày**: average deposit count on days they actually reported

### 3 — Chuỗi ngày liên tục (Streak analysis per ASM)
For each ASM:
- **Chuỗi dài nhất** (longest consecutive reported days)
- **Vắng dài nhất** (longest consecutive missed days)

These two columns are added to the report-rate table (same table, extra columns).

### 4 — Ngày thiếu báo cáo (Missing-day calendar)
A compact table listing each calendar date in the range with the count of ASMs who did NOT report that day (and optionally their names on hover/expand). Highlights days with the most gaps.

### 5 — Tổng kết shop qua nhiều ngày (Multi-day shop summary)
For each shop that appeared in at least one report during the range:
- Total deposits across all days
- Number of days reported
- Average deposits per reported day

## Design notes
- All analyses are computed in a new `fpt_chat_stats.py` function `analyze_multiday(parsed_reports, date_from_str, date_to_str)`.
- The function groups `parsed_reports` by calendar date (VN timezone, UTC+7) and by sender.
- "A day is reported" = the ASM sent at least one valid report on that calendar day (any time, no deadline check — deadlines are for compliance, not presence).
- Total calendar days = all dates from `date_from_str` to `date_to_str` inclusive.
- Multi-day sections are shown **only** when `date_from_str != date_to_str`. Single-day mode is unchanged.
- `analyze_multiday` result is stored in the result dict as `"multiday_data"`.

## Clarification defaults (can be changed post-approval)
- All calendar days counted (not just working days).
- Shop summary uses `shop_ref` as key (same shop across days = same key).

## Scope
- `fpt_chat_stats.py`: new `analyze_multiday()` function
- `app.py`: call `analyze_multiday` when multi-day, store in result dict, render new sections + charts in `_render_result`
