# Proposal: add-detail-drilldown

## Why
The current report shows aggregate tables (deposit counts, shop lists) but no way to drill into a single shop's or ASM's full report — tich_cực, vấn_đề, đã_làm, ra tiêm. Users need to be able to quickly pull up the detailed content for any shop or employee without reading raw chat messages.

## What Changes

### 1 — Store parsed_reports in result dict
Currently `parsed` (the list of structured report dicts) is only used locally in the `if run:` block. It needs to be stored in the result dict so `_render_result` can access per-report details.

### 2 — "Chi tiết" drill-down section in _render_result
Add a **🔍 Xem chi tiết** expander at the bottom of each group's result. Inside:

**Theo shop**: a `st.selectbox` listing all `shop_ref` values. When selected, shows the full report card:
- ASM, Số cọc, Cọc D-1 (if available), Ra tiêm, Giờ gửi
- Tích cực, Vấn đề, Đã làm (multi-line text)

**Theo nhân viên (ASM)**: a `st.selectbox` listing all unique `sender` values. When selected, shows a card for each shop that ASM reported (an ASM may cover multiple shops).

The two selectors are independent — selecting one does not affect the other.

## Scope
- `app.py`: add `"parsed_reports"` key to result dict; add drill-down expander to `_render_result`
- No changes to `fpt_chat_stats.py`
