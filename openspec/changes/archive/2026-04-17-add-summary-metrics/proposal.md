# Proposal: add-summary-metrics

## Why
The current report shows shop-level deposit breakdowns and compliance lists but lacks aggregate summary metrics. Users need quick top-line numbers — total deposits, total vaccinations, late reporter count, not-yet-reported count — and shop-level lists for no-deposit and high-deposit shops, with day-over-day comparison.

## What Changes (6 metrics)

### 1 & 2 — Tổng cọc / tổng ra tiêm hôm nay vs. D-1
**Parse**: Add `ra_tiem_count` to `parse_asm_report` using regex `(\d+)\s*ra\s*tiêm`.  
Messages without a numeric count (e.g. "KH ra tiêm chưa chất lượng" or the "Gói" format) → `None`, excluded from sum.

**D-1 data**: When the analysis date range covers exactly 1 day (including "Hôm nay" mode), the app fetches an additional pass for D-1 (the previous calendar day, VN timezone) and runs the full analysis pipeline on D-1 messages. For multi-day ranges, D-1 comparison is not shown.

**Display**: `st.metric` tiles — `Tổng cọc: X` with delta `+/- vs D-1`, and `Tổng ra tiêm: X` with delta.

### 3 — Nhân viên không phát sinh cọc
Two sub-lists:
- **A** — Shops in parsed reports with `deposit_count == 0`, displayed as `{ASM, Shop}` table.
- **B** — Group members (from `fetch_group_members`) with no ASM report on the target date (regardless of deadline), i.e. `check_asm_compliance` with deadline=`"23:59"`. Displayed as `{Tên thành viên}` table.

### 4 — Nhân viên phát sinh cọc tốt
Reuse existing `high_deposit_shops` (shops where `deposit_count > deposit_high`). Display as a dedicated summary table `{ASM, Shop, Số cọc}`.

### 5 — ASM báo cáo muộn
Count (and list) ASMs whose `sent_at` on the target date falls **after** the configured deadline. New function `check_late_reporters(parsed_reports, target_date_str, deadline_hhmm)` returns `list[{sender, sent_at_vn}]`.

### 6 — ASM chưa báo cáo đến hiện tại
Reuse `check_asm_compliance` with deadline = current VN time at run time. Returns members who have sent zero reports so far today.

## Architecture

```
fpt_chat_stats.py
  parse_asm_report()        + ra_tiem_count field
  analyze_asm_reports()     + total_deposits, total_ra_tiem, no_deposit_shops
  check_late_reporters()    NEW — list of {sender, sent_at_vn} after deadline
  check_asm_compliance()    reuse with deadline="23:59" for "unreported now"

app.py
  if run: block
    D-1 fetch (when single-day)         NEW
    call check_late_reporters()         NEW
    call check_asm_compliance(now)      NEW (for feature 6)
  _render_result()
    NEW summary metrics section at top  (metrics + D-1 delta)
    NEW no-deposit list (A + B)
    MODIFIED high-deposit section       (add dedicated "cọc tốt" table)
```

## Scope
- `fpt_chat_stats.py`: parser + 1 new function + `analyze_asm_reports` additions
- `app.py`: D-1 fetch logic + `_render_result` new sections
- Spec deltas: `asm-report-analysis`, `fpt-chat-stats`
