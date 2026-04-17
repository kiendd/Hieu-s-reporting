# Tasks: add-summary-metrics

## fpt_chat_stats.py

- [x] 1. `parse_asm_report`: add `ra_tiem_count` field — regex `(\d+)\s*ra\s*tiêm`; `None` when not found
- [x] 2. `analyze_asm_reports`: add `total_deposits` (sum of deposit_count, skip None), `total_ra_tiem` (sum of ra_tiem_count, skip None), `no_deposit_shops` (list of {sender, shop_ref} where deposit_count == 0)
- [x] 3. New function `check_late_reporters(parsed_reports, target_date_str, deadline_hhmm)` → list of `{sender, sent_at_vn}` whose report on target date is **after** deadline

## app.py

- [x] 4. D-1 fetch logic in `if run:` block: when date range = 1 day, compute D-1 date range, call `fetch_all_messages` + `filter_by_date` + `detect_asm_reports` + `analyze_asm_reports` for D-1; store as `asm_data_d1` (None for multi-day ranges)
- [x] 5. In `if run:` block: call `check_late_reporters()` and store result in each result dict
- [x] 6. In `if run:` block: call `check_asm_compliance` with deadline = current VN time string for "unreported now"; store in each result dict
- [x] 7. `_render_result`: add summary metrics row at top — `st.metric` tiles for Tổng cọc, Tổng ra tiêm (with D-1 delta when available), Báo cáo muộn count, Chưa báo cáo count
- [x] 8. `_render_result`: add "Nhân viên không phát sinh cọc" section — sub-table A (0-deposit shops by ASM) and sub-table B (unreported members, reuse existing missing_reporters with deadline="23:59")
- [x] 9. `_render_result`: add dedicated "Cọc tốt" section showing `high_deposit_shops` as `{ASM, Shop, Số cọc}` table (separate from the combined "Shop đặt cọc" table)

## Validation

- [x] 10. Update `openspec/specs/asm-report-analysis/spec.md` and `openspec/specs/fpt-chat-stats/spec.md`
- [x] 11. Validate with `openspec validate add-summary-metrics --strict --no-interactive`
