# Tasks: add-multiday-analysis

## fpt_chat_stats.py

- [x] 1. New function `analyze_multiday(parsed_reports, date_from_str, date_to_str)` → dict with keys:
  - `total_days`: int — number of calendar days in range
  - `daily_summary`: list of `{date, total_deposits, total_ra_tiem, reporter_count}` sorted by date
  - `asm_summary`: list of `{sender, report_days, report_rate, total_deposits, avg_deposits_per_day, longest_streak, longest_gap}` sorted by report_rate desc
  - `missing_by_day`: list of `{date, missing_count, missing_names}` sorted by date
  - `shop_summary`: list of `{shop_ref, sender, total_deposits, report_days, avg_deposits}` sorted by total_deposits desc

## app.py

- [x] 2. In `if run:` block: when `not _is_single_day`, call `analyze_multiday(parsed, date_from_str, date_to_str)` and store as `"multiday_data"` in result dict (`None` for single-day)
- [x] 3. In `_render_result`: when `multiday_data` is not None, render multi-day sections:
  - **Xu hướng theo ngày**: bar chart of total_deposits + total_ra_tiem by date
  - **Tổng kết ASM**: table with columns Sender, Số ngày báo/Tổng, Tỉ lệ, Chuỗi dài nhất, Vắng dài nhất, Tổng cọc, TB cọc/ngày
  - **Ngày thiếu báo cáo**: table of date + missing_count (expandable names)
  - **Tổng kết shop**: table of shop_ref, sender, total_deposits, report_days, avg_deposits

## Validation

- [x] 4. Update `openspec/specs/asm-report-analysis/spec.md` and `openspec/specs/fpt-chat-stats/spec.md`
- [x] 5. Validate with `openspec validate add-multiday-analysis --strict --no-interactive`
