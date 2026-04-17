## MODIFIED Requirements

### Requirement: No-Deposit and High-Deposit Shop Lists
The web UI SHALL display two dedicated sections after the summary metrics:

**Nhân viên không phát sinh cọc** — two sub-tables:
- Sub-table A: shops with `deposit_count == 0`, columns: ASM, Shop
- Sub-table B: group members with no report on the target date (deadline `"23:59"`), column: Tên thành viên

**Nhân viên cọc tốt** — shops where `deposit_count > deposit_high`, columns: ASM, Shop, Số cọc, Cọc D-1 (when D-1 data is available)

When D-1 data is available (single-day analysis), the "Nhân viên cọc tốt" table includes a **Cọc D-1** column showing the previous day's deposit count for the same shop_ref. Shops not present in D-1 data show `—`. When D-1 data is unavailable, the column is omitted.

#### Scenario: Shop with 0 deposits appears in sub-table A
- **WHEN** an ASM report contains `0 cọc` for a shop
- **THEN** that shop appears in sub-table A

#### Scenario: Member with no report appears in sub-table B
- **WHEN** a group member has sent no ASM report on the target date
- **THEN** their name appears in sub-table B (subject to skip list)

#### Scenario: Cọc tốt table with D-1 column on single-day analysis
- **WHEN** D-1 data is available and a high-deposit shop also appeared in D-1
- **THEN** the "Nhân viên cọc tốt" table shows that shop's D-1 deposit count in the Cọc D-1 column

#### Scenario: Cọc tốt table — shop absent from D-1
- **WHEN** D-1 data is available but a shop has no entry on D-1
- **THEN** the Cọc D-1 column shows `—` for that shop

#### Scenario: Cọc tốt table on multi-day range
- **WHEN** the analysis covers more than one day (D-1 data not available)
- **THEN** the "Nhân viên cọc tốt" table has no Cọc D-1 column

---

### Requirement: Low-Deposit Shop Table
The web UI SHALL display a dedicated **Shop cọc thấp** section showing all shops where `deposit_count < deposit_low`, with columns: ASM, Shop, Số cọc, and Cọc D-1 (when D-1 data is available).

When D-1 data is available, the Cọc D-1 column shows the previous day's deposit count for the same shop_ref. Shops absent from D-1 show `—`. When D-1 data is unavailable, the column is omitted.

#### Scenario: Low-deposit shops rendered as table
- **WHEN** one or more shops have `deposit_count < deposit_low`
- **THEN** a "Shop cọc thấp" section appears with those shops listed

#### Scenario: Low-deposit table with D-1 column
- **WHEN** D-1 data is available and a low-deposit shop also appeared in D-1
- **THEN** the Cọc D-1 column shows that shop's previous-day deposit count

#### Scenario: Low-deposit table on multi-day range
- **WHEN** the analysis covers more than one day
- **THEN** the "Shop cọc thấp" table has no Cọc D-1 column

---

### Requirement: Unreported-Now Table
The web UI SHALL display a dedicated **Chưa báo cáo đến hiện tại** section listing all group members who have not submitted any report as of the run time (`unreported_now`). The section appears below the summary metric row and shows a table with column: Tên thành viên. When the list is empty, the section shows "Tất cả đã báo cáo". When `unreported_now` is `None` (member list unavailable), the section is hidden.

#### Scenario: Some members have not reported yet
- **WHEN** `unreported_now` contains one or more names
- **THEN** a "Chưa báo cáo đến hiện tại" section appears with those names listed

#### Scenario: All members have reported
- **WHEN** `unreported_now` is an empty list
- **THEN** the section shows "Tất cả đã báo cáo"

#### Scenario: Member list unavailable
- **WHEN** `unreported_now` is None (group members could not be fetched)
- **THEN** the section is not shown

---

### Requirement: Day-over-Day Comparison
The web UI SHALL display `total_deposits` and `total_ra_tiem` as `st.metric` tiles with a delta showing the difference vs. the previous calendar day (D-1).

D-1 data SHALL be fetched as a separate API call for the calendar day immediately before the target date. D-1 comparison is shown only when the analysis covers exactly one calendar day. For multi-day date ranges, the delta is omitted.

The D-1 `all_shops` list SHALL also be used to populate the **Cọc D-1** column in the "Shop đặt cọc", "Shop cọc thấp", and "Nhân viên cọc tốt" tables, matched by `shop_ref`.

#### Scenario: Single-day run with D-1 available
- **WHEN** the user runs analysis for a single day and D-1 messages exist
- **THEN** the Tổng cọc metric tile shows today's total with a +/- delta vs. D-1

#### Scenario: Multi-day range
- **WHEN** the user selects a date range of more than one day
- **THEN** no D-1 delta is shown

#### Scenario: Shop đặt cọc table with D-1 column on single-day analysis
- **WHEN** D-1 data is available and a shop also appeared in D-1
- **THEN** the "Shop đặt cọc" table shows that shop's D-1 deposit count in a Cọc D-1 column

#### Scenario: Shop đặt cọc table on multi-day range
- **WHEN** the analysis covers more than one day
- **THEN** the "Shop đặt cọc" table has no Cọc D-1 column
