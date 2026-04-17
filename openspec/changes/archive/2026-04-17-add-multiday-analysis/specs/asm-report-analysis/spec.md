## ADDED Requirements

### Requirement: Multi-Day Report Sections
When the selected date range spans more than one calendar day, the web UI SHALL display additional multi-day analysis sections after the standard summary metrics:

**1. Xu hướng theo ngày** — bar chart with one group per calendar day showing `total_deposits` and `total_ra_tiem`. Allows spotting strong/weak days across the group.

**2. Tổng kết ASM** — table with columns: Nhân viên, Số ngày báo / Tổng ngày, Tỉ lệ (%), Chuỗi dài nhất, Vắng dài nhất, Tổng cọc, TB cọc/ngày. Sorted by report rate descending.

**3. Ngày thiếu báo cáo** — table with columns: Ngày, Số ASM vắng, Tên ASM vắng. Lists each calendar day with senders who appeared in the range but did not report on that day. Sorted by date ascending.

**4. Tổng kết shop (nhiều ngày)** — table with columns: Shop, ASM, Tổng cọc, Số ngày báo cáo, TB cọc/ngày. Sorted by total deposits descending.

These sections are hidden when the date range is exactly one day.

#### Scenario: Multi-day sections appear for range > 1 day
- **WHEN** the user selects a 7-day range and runs the analysis
- **THEN** all four multi-day sections appear below the standard metric tiles

#### Scenario: Multi-day sections hidden for single-day
- **WHEN** the user selects a single day (or uses "Hôm nay" mode)
- **THEN** no multi-day sections appear

#### Scenario: Daily trend chart populated
- **WHEN** reports exist on some but not all days in the range
- **THEN** the bar chart shows 0 for days with no reports and actual totals for days with reports

#### Scenario: ASM with perfect attendance
- **WHEN** an ASM reports every day in a 7-day range
- **THEN** their row shows Tỉ lệ = 100%, Chuỗi dài nhất = 7, Vắng dài nhất = 0

#### Scenario: Missing-day table highlights gaps
- **WHEN** a day has 3 out of 5 regular ASMs not reporting
- **THEN** that day appears in the "Ngày thiếu báo cáo" table with count 3 and those names listed
