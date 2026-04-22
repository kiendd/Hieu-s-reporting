# Spec Delta: asm-report-analysis

## MODIFIED Requirements

### Requirement: ASM Compliance Tracking
When ASM analysis is active and group members have been successfully fetched, the tool SHALL identify which members have NOT submitted a report by the deadline (default `20:00` Vietnam time, UTC+7).

The check applies to the date specified by `--date YYYY-MM-DD` (default: today in UTC+7).

`check_asm_compliance` SHALL accept a REQUIRED `report_type: ReportType` keyword argument (`"daily_shop_vt"` or `"weekend_tttc"`). Only reports matching this type are considered when computing the "reported" set. Callers SHALL route by weekday using `report_type_for_date(date)` — Mon-Fri → daily, Sat-Sun → weekend. The function does NOT auto-detect from the target date, so that callers can override for ad-hoc checks.

A member is considered to have reported if at least one parsed report of the matching `report_type` was sent by a sender whose `displayName` contains the member's `displayName` as a substring (case-insensitive match), and was sent before the deadline on the target date.

Members with `lastReadMessageId == 0` (or missing) SHALL be filtered out as zombie accounts (data quality issue: same person occupies two user records). This prevents the same person from appearing twice in the missing-reporters list.

#### Scenario: Daily compliance check filters only Shop VT reports
- **GIVEN** sender Alice has a `daily_shop_vt` report and sender Bob has a `weekend_tttc` report on the same Monday
- **WHEN** `check_asm_compliance(report_type="daily_shop_vt")` is called for that date
- **THEN** Alice is considered reported but Bob is in the missing list (Bob's TTTC report does not satisfy the daily check)

#### Scenario: Weekend compliance check filters only TTTC reports
- **GIVEN** the same setup but on a Saturday
- **WHEN** `check_asm_compliance(report_type="weekend_tttc")` is called
- **THEN** Bob is considered reported but Alice is in the missing list

#### Scenario: Zombie member excluded from missing list
- **GIVEN** a member with `lastReadMessageId == 0` (zombie account) and that member has not submitted any report
- **WHEN** `check_asm_compliance` runs
- **THEN** the zombie member is NOT in the missing list (filtered before iteration)

#### Scenario: Hieu listed once when zombie duplicate exists (regression)
- **GIVEN** the API returns two members both named "Hieu Hoang Chi" with the same username — one with `lastReadMessageId=103` (active) and one with `lastReadMessageId=0` (zombie)
- **WHEN** Hieu has not submitted a report and `check_asm_compliance` runs
- **THEN** "Hieu Hoang Chi" appears exactly once in the missing list (zombie entry filtered)

#### Scenario: Custom deadline
- **WHEN** `--asm-deadline 21:00` is passed
- **THEN** members who reported between 20:00 and 21:00 are considered compliant (deadline_hhmm passed through to the check)

#### Scenario: Text report compliance section
- **WHEN** ASM compliance data is available
- **THEN** the output contains an "ASM CHƯA BÁO CÁO" section listing full `displayName` values, one per line, with no duplicates
