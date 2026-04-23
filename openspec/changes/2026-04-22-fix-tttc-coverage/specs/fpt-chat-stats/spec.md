# Spec Delta: fpt-chat-stats

## MODIFIED Requirements

### Requirement: Late Reporter Detection
`fpt_chat_stats` SHALL expose a `check_late_reporters(parsed_reports, target_date_str, report_type, deadline_hhmm) -> list[dict]` function that returns entries `{sender, sent_at_vn}` for each parsed report whose VN-time timestamp on the target date falls **after** the deadline. Reports on other dates are ignored.

The `report_type` parameter is REQUIRED (no default). Only reports matching `report_type` (one of `"daily_shop_vt"` or `"weekend_tttc"`) are considered. Callers SHALL route by weekday using `report_type_for_date(date)` (Mon-Fri → daily, Sat-Sun → weekend) — the function does NOT auto-detect from the date, so that callers can override for ad-hoc checks.

#### Scenario: Daily report sent after deadline
- **WHEN** a `daily_shop_vt` report's VN-time is 21:05, deadline is "20:00", and the call uses `report_type="daily_shop_vt"`
- **THEN** that sender appears in the returned list with their sent_at_vn time

#### Scenario: TTTC report routed to weekend bucket
- **WHEN** a `weekend_tttc` report is sent at 21:05 VN on Saturday and the call uses `report_type="weekend_tttc"`
- **THEN** that sender appears in the returned list

#### Scenario: Wrong-type reports ignored
- **WHEN** a `weekend_tttc` report is present but the call uses `report_type="daily_shop_vt"`
- **THEN** that report is filtered out and the sender does NOT appear in the returned list

#### Scenario: Report sent before deadline
- **WHEN** a `daily_shop_vt` report's VN-time is 19:45, deadline is "20:00", and `report_type="daily_shop_vt"`
- **THEN** that sender does NOT appear in the returned list

### Requirement: Multi-Day Analysis Function
`fpt_chat_stats` SHALL expose an `analyze_multiday(parsed_reports, date_from_str, date_to_str) -> dict` function that produces time-aware analytics across a date range. The function groups parsed reports by calendar date (VN timezone UTC+7) and by sender.

Per-day report-type routing: each calendar date SHALL accept only the report type expected for its weekday — Mon-Fri (weekday 0-4) → `daily_shop_vt`; Sat-Sun (5-6) → `weekend_tttc`. Reports of the wrong type for their date are dropped from that day's bucket. Both report types pass the initial filter (only `parse_error is not None` and unrecognized `report_type` values are filtered up-front).

This enables a sender who submits a Shop VT report on Friday and a TTTC report on Saturday to be counted on both days.

#### Scenario: Friday Shop VT and Saturday TTTC both counted
- **GIVEN** sender Alice has a `daily_shop_vt` report on 2026-04-17 (Friday) and a `weekend_tttc` report on 2026-04-18 (Saturday)
- **WHEN** `analyze_multiday(reports, "2026-04-17", "2026-04-18")` is called
- **THEN** `daily_summary[2026-04-17].reporter_count == 1` AND `daily_summary[2026-04-18].reporter_count == 1`

#### Scenario: Wrong-type report dropped from day bucket
- **GIVEN** a `daily_shop_vt` report dated 2026-04-18 (Saturday)
- **WHEN** `analyze_multiday` runs
- **THEN** that report is NOT counted in 2026-04-18's bucket (Saturday expects `weekend_tttc`)

## ADDED Requirements

### Requirement: Report Candidate Pre-filter
`fpt_chat_stats.detect_report_candidates(messages: list) -> list` SHALL apply an L2 heuristic to identify chat messages that may contain a report, before delegating to LLM extraction. A message passes the filter when ALL of the following hold:
- `msg["type"] == "TEXT"`
- `len(content) >= 80`
- content contains at least 2 ASCII digits
- after diacritic stripping (lowercase + NFKD strip-combining + explicit `đ→d`), content contains at least one keyword from `_REPORT_KEYWORDS` (`shop`, `tttc`, `vx hcm`, `coc`, `doanh thu`, `dt %`, `hot`, `ra tiem`, `tvv`, `tu van`, `kh`, `bill`)

This replaces the prior narrow filter that required both `shop` and `\d+\s*c[ọo]c`, which dropped 100% of TTTC reports and Shop VT free-form variants. The L2 filter has 100% recall on the 3-week production sample and ~89% precision (false positives are surfaced to the LLM, which tags them `report_type="unknown"` for downstream `parse_error`-based filtering).

The diacritic-stripping helper `_strip_diacritics(s) -> str` SHALL handle Vietnamese `đ`/`Đ` (U+0111 / U+0110) explicitly via lowercase + replace, because NFKD does not decompose them.

#### Scenario: Canonical Shop VT report passes
- **WHEN** a long Shop VT report message with `shop`, `cọc`, `KH tư vấn` keywords is given
- **THEN** the message is in the returned list

#### Scenario: TTTC report passes (regression)
- **WHEN** a long TTTC report message with `TTTC`, `DT %`, `HOT`, `bill` keywords (no `cọc`) is given
- **THEN** the message is in the returned list (the old filter dropped this case)

#### Scenario: Short chat dropped
- **WHEN** a message of length < 80 is given
- **THEN** the message is NOT in the returned list

#### Scenario: Long chat without keywords dropped
- **WHEN** a message ≥ 80 chars with ≥ 2 digits but no report keyword is given
- **THEN** the message is NOT in the returned list

#### Scenario: Diacritic-insensitive keyword match
- **WHEN** the message contains `coc` (no diacritic) instead of `cọc`
- **THEN** the message still passes the keyword check

### Requirement: Weekday-Routed Report Type
`fpt_chat_stats` SHALL expose a `ReportType` literal alias (`Literal["daily_shop_vt", "weekend_tttc"]`) and a helper `report_type_for_date(target_date: date) -> ReportType` that returns `"daily_shop_vt"` for Monday-Friday (weekday 0-4) and `"weekend_tttc"` for Saturday-Sunday (5-6).

Callers of `check_asm_compliance` and `check_late_reporters` SHALL use this helper to route per-day. The helper is idempotent and pure — no I/O, no caching needed.

#### Scenario: Monday returns daily
- **WHEN** `report_type_for_date(date(2026, 4, 20))` is called (Monday)
- **THEN** the result is `"daily_shop_vt"`

#### Scenario: Friday returns daily
- **WHEN** `report_type_for_date(date(2026, 4, 17))` is called (Friday)
- **THEN** the result is `"daily_shop_vt"`

#### Scenario: Saturday returns weekend
- **WHEN** `report_type_for_date(date(2026, 4, 18))` is called (Saturday)
- **THEN** the result is `"weekend_tttc"`

#### Scenario: Sunday returns weekend
- **WHEN** `report_type_for_date(date(2026, 4, 19))` is called (Sunday)
- **THEN** the result is `"weekend_tttc"`

### Requirement: Active Member Filter
`fpt_chat_stats._is_active_member(m: dict) -> bool` SHALL return `True` iff `m["lastReadMessageId"]` is set and greater than 0. Members with `lastReadMessageId == 0` (or missing / null) are zombie accounts (data quality issue: same person occupies two user records, one active and one never-read) and SHALL be filtered out before compliance computations.

The filter is applied in:
- `check_asm_compliance` (members iteration)
- `analyze_weekly` (member_names build)
- `write_weekly_excel` (member_names build)

The filter is NOT applied to sender-display lookups, because legitimate inactive senders may still need their display name resolved for historical reports.

#### Scenario: Active member kept
- **GIVEN** a member with `lastReadMessageId == 103`
- **WHEN** `_is_active_member` is called
- **THEN** it returns `True`

#### Scenario: Zombie member dropped — lastReadMessageId is 0
- **GIVEN** a member with `lastReadMessageId == 0`
- **WHEN** `_is_active_member` is called
- **THEN** it returns `False`

#### Scenario: Member dropped when lastReadMessageId is missing
- **GIVEN** a member dict without a `lastReadMessageId` key
- **WHEN** `_is_active_member` is called
- **THEN** it returns `False`
