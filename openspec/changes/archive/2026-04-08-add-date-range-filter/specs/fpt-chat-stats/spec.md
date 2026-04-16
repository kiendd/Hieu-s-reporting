## ADDED Requirements

### Requirement: Date Range Filter
The tool SHALL accept optional `--from DATE` and `--to DATE` CLI flags (format `YYYY-MM-DD`) that restrict the analysis to messages whose `createdAt` timestamp falls within the specified range.

- `--from` is an inclusive lower bound interpreted as `DATE 00:00:00 UTC`.
- `--to` is an inclusive upper bound interpreted as `DATE 23:59:59 UTC`.
- Both flags are optional and independent; omitting one leaves that bound open.
- The filter is applied at the analysis stage; fetched raw messages are unaffected and still saved in full when `--save` is used.

#### Scenario: Both bounds provided
- **WHEN** the user passes `--from 2026-03-01 --to 2026-03-31`
- **THEN** only messages with `createdAt` between `2026-03-01T00:00:00Z` and `2026-03-31T23:59:59Z` (inclusive) are counted in all statistics

#### Scenario: Lower bound only
- **WHEN** the user passes `--from 2026-03-01` without `--to`
- **THEN** all messages on or after `2026-03-01T00:00:00Z` are included; no upper bound is applied

#### Scenario: Upper bound only
- **WHEN** the user passes `--to 2026-03-31` without `--from`
- **THEN** all messages on or before `2026-03-31T23:59:59Z` are included; no lower bound is applied

#### Scenario: No filter (default behaviour)
- **WHEN** neither `--from` nor `--to` is provided
- **THEN** all messages are included; output is identical to previous behaviour

#### Scenario: Message outside range is excluded
- **WHEN** a message has `createdAt: "2026-02-15T10:00:00Z"` and `--from 2026-03-01` is active
- **THEN** that message is not counted in any statistic (total, requester, file sender, timeline)

#### Scenario: Save preserves full history
- **WHEN** `--from`/`--to` is active and `--save raw.json` is also specified
- **THEN** `raw.json` contains ALL fetched messages regardless of the date filter

---

## MODIFIED Requirements

### Requirement: Statistical Analysis
The tool SHALL analyze fetched messages and compute the following statistics:

- **Requesters** — users who sent TEXT messages containing one or more links (document requests), ranked by link count.
- **File senders** — users who sent FILE messages, with total file count.
- **Monthly timeline** — message count grouped by `YYYY-MM`.
- **Link detail** — every requested URL with requester name and date.
- **File detail** — every uploaded file with sender name, file name, size, and date.

When a date range filter is active (see *Date Range Filter* requirement), only messages whose `createdAt` falls within the range are included in all of the above.

#### Scenario: User requests multiple documents in one message
- **WHEN** a TEXT message contains 3 links in `metadata.links`
- **THEN** the requester's link count increases by 3 and all 3 URLs appear in the link detail list

#### Scenario: FILE message with multiple attachments
- **WHEN** a FILE message has 2 entries in `metadata.files`
- **THEN** the sender's file count increases by 2 and both files appear in the file detail list

#### Scenario: ACTIVITY message
- **WHEN** a message has type `ACTIVITY`
- **THEN** it is counted in the total and monthly timeline but excluded from requester and file-sender statistics

#### Scenario: Date-filtered analysis
- **WHEN** `--from 2026-03-01 --to 2026-03-31` is active and a message was sent on `2026-02-20`
- **THEN** that message is excluded from all statistics including the total count

---

## ADDED Requirements

### Requirement: Date Range in Report Output
The tool SHALL display the active date range in its output so readers know the scope of the report.

- Text report: a "Khoảng thời gian" line in the overview section showing the resolved bounds (or "Toàn bộ lịch sử" when no filter is active).
- JSON report: a `"date_range"` key inside `"summary"` with `"from"` and `"to"` sub-keys (ISO-8601 strings, or `null` when the bound is open).

#### Scenario: Text report with active filter
- **WHEN** `--from 2026-03-01 --to 2026-03-31` and `--format text`
- **THEN** the overview section contains `Khoảng thời gian: 2026-03-01 → 2026-03-31`

#### Scenario: Text report without filter
- **WHEN** no date flags are passed and `--format text`
- **THEN** the overview section contains `Khoảng thời gian: Toàn bộ lịch sử`

#### Scenario: JSON report with active filter
- **WHEN** `--from 2026-03-01` and `--format json`
- **THEN** output includes `"date_range": {"from": "2026-03-01T00:00:00+00:00", "to": null}`
