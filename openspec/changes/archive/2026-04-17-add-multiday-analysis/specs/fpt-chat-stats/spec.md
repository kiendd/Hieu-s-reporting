## ADDED Requirements

### Requirement: Multi-Day Analysis Function
`fpt_chat_stats` SHALL expose an `analyze_multiday(parsed_reports, date_from_str, date_to_str) -> dict` function that produces time-aware analytics across a date range. The function groups parsed reports by calendar date (VN timezone UTC+7) and by sender.

The returned dict SHALL contain:
- `total_days` (int): number of calendar days from date_from to date_to inclusive
- `daily_summary` (list): one entry per calendar day — `{date, total_deposits, total_ra_tiem, reporter_count}`, sorted by date ascending
- `asm_summary` (list): one entry per unique sender — `{sender, report_days, report_rate, total_deposits, avg_deposits_per_day, longest_streak, longest_gap}`, sorted by report_rate descending
- `missing_by_day` (list): one entry per calendar day — `{date, missing_senders}` listing senders who appeared at least once in the range but did NOT report on that specific day, sorted by date ascending
- `shop_summary` (list): one entry per unique shop_ref — `{shop_ref, sender, total_deposits, report_days, avg_deposits}`, sorted by total_deposits descending

A sender "reported on a day" if they have at least one parsed report whose VN-time date matches that calendar day (no deadline check).

#### Scenario: Basic weekly analysis
- **WHEN** 7 days of reports are passed with varying reporter activity
- **THEN** `total_days` is 7, `daily_summary` has 7 entries, and `asm_summary` has one entry per unique sender

#### Scenario: Streak calculation
- **WHEN** an ASM reports on days 1, 2, 3, skips day 4, reports on day 5
- **THEN** their `longest_streak` is 3 and `longest_gap` is 1

#### Scenario: Missing senders per day
- **WHEN** sender A reports on all 7 days but sender B only reports on 3 days
- **THEN** `missing_by_day` entries for the 4 days B missed include B's name

#### Scenario: Shop cumulative deposits
- **WHEN** shop X appears in reports on 3 different days with deposits 5, 3, 7
- **THEN** shop X's `total_deposits` is 15, `report_days` is 3, `avg_deposits` is 5.0
