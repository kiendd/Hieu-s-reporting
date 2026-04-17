# Proposal: add-d1-deposit-column

## Why
The deposit tables currently show today's deposit count but give no context for whether performance is improving or declining. Adding a "Cọc D-1" column lets the reader immediately compare each shop against the previous day without switching views.

## What Changes

### 1 — "Cọc D-1" column in Shop đặt cọc table
When D-1 data is available (single-day analysis only), the "Shop đặt cọc" (all shops) table gains a **Cọc D-1** column. Looked up by `shop_ref` in D-1 `all_shops`. Shops absent from D-1 show `—`. Column omitted for multi-day ranges.

### 2 — "Cọc D-1" column in Shop cọc thấp table
Same D-1 column added to the "Shop cọc thấp" (`low_deposit_shops`) table. This section will also gain a dedicated rendered table (currently only shown as a count metric tile).

### 3 — "Cọc D-1" column in Nhân viên cọc tốt table
Same D-1 column added to the "Nhân viên cọc tốt" (`high_deposit_shops`) table.

### 4 — Dedicated "Chưa báo cáo đến hiện tại" table
`unreported_now` is currently only shown as a count metric tile. Add a dedicated section below the metric row listing the full names of members who have not reported as of the run time.

## Scope
- `app.py` only: `_render_result` rendering logic
- No changes to `fpt_chat_stats.py` — all data already computed and available in the result dict
