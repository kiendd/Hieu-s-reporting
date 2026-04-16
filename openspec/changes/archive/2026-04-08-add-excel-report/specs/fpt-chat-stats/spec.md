## ADDED Requirements

### Requirement: Excel Report Export
The tool SHALL write a `.xlsx` Excel file when `--excel FILE` is provided. The file contains two sheets: "Tổng hợp" and "Chi tiết". Writing the Excel file does not suppress other output formats — `--format text` and `--excel` may be used together.

#### Scenario: Excel file created
- **WHEN** the user passes `--excel report.xlsx`
- **THEN** `report.xlsx` is written to disk and a confirmation line is printed to `stderr`

#### Scenario: Combined with text report
- **WHEN** the user passes `--excel report.xlsx --format text`
- **THEN** the text report is printed to `stdout` AND `report.xlsx` is written; both outputs are produced

#### Scenario: Excel not requested
- **WHEN** `--excel` is not passed
- **THEN** no `.xlsx` file is written; tool behaviour is unchanged

---

### Requirement: Summary Sheet ("Tổng hợp")
The "Tổng hợp" sheet SHALL display a pivot table of request counts with users as rows and calendar months as columns.

Structure:
- **Row 1 (header)**: "Người dùng" | YYYY-MM (one column per month, sorted ascending) | "Tổng"
- **Subsequent rows**: one row per user who made at least one request; cells contain the count for that user-month pair (0 if none); final "Tổng" column is the row sum.
- Header row is bold and the top row is frozen.
- Users are sorted by total request count descending.

#### Scenario: Multiple users across multiple months
- **WHEN** user A made 3 requests in 2026-03 and 1 in 2026-04, user B made 2 in 2026-03
- **THEN** sheet has columns: Người dùng | 2026-03 | 2026-04 | Tổng; user A row: A | 3 | 1 | 4; user B row: B | 2 | 0 | 2

#### Scenario: User with no requests in a month
- **WHEN** a user made requests in some months but not others
- **THEN** the missing month cells contain 0 (not blank)

---

### Requirement: Detail Sheet ("Chi tiết")
The "Chi tiết" sheet SHALL contain one row per request message with full context for audit.

Columns (in order):
1. **STT** — sequential row number (1, 2, 3…)
2. **Ngày giờ** — `createdAt` timestamp converted to Vietnam time (UTC+7), formatted as `YYYY-MM-DD HH:MM:SS`
3. **Người dùng** — `displayName` of the sender
4. **Nội dung** — raw message `content` text
5. **Links** — comma-separated list of URLs from `metadata.links`; empty string if none

Rows are sorted by timestamp ascending (oldest first).
The top row is frozen and columns are auto-sized to fit content.

#### Scenario: Request with links
- **WHEN** a request message has 2 links
- **THEN** the "Links" cell contains both URLs separated by ", "

#### Scenario: Keyword-matched request without links
- **WHEN** a message matched via keyword but has no links
- **THEN** "Links" cell is empty; "Nội dung" contains the full message text

#### Scenario: Row ordering
- **WHEN** the detail sheet is written
- **THEN** rows are ordered by timestamp ascending (earliest request first)

---

## MODIFIED Requirements

### Requirement: Statistical Analysis
The tool SHALL analyze fetched messages and compute the following statistics:

- **Requesters** — users who sent TEXT messages classified as requests (link-based or keyword-based), ranked by request count.
- **File senders** — users who sent FILE messages, with total file count.
- **Monthly timeline** — message count grouped by `YYYY-MM`.
- **Request count by month** — number of request messages grouped by `YYYY-MM`.
- **Link detail** — every requested URL with requester name, date, and message content.
- **File detail** — every uploaded file with sender name, file name, size, and date.

Each request entry SHALL include the `content` field containing the raw message text, in addition to the existing `url`, `user`, `date`, `message_id`, and `messageIdInc` fields. This enables the detail sheet to show what was requested.

When a date range filter is active (see *Date Range Filter* requirement), only messages within the range are included.

#### Scenario: User requests multiple documents in one message
- **WHEN** a TEXT message contains 3 links in `metadata.links`
- **THEN** the requester's link count increases by 3 and all 3 URLs appear in the link detail list, each carrying the same `content` text

#### Scenario: FILE message with multiple attachments
- **WHEN** a FILE message has 2 entries in `metadata.files`
- **THEN** the sender's file count increases by 2 and both files appear in the file detail list

#### Scenario: ACTIVITY message
- **WHEN** a message has type `ACTIVITY`
- **THEN** it is counted in the total and monthly timeline but excluded from requester and file-sender statistics

#### Scenario: Date-filtered analysis
- **WHEN** `--from 2026-03-01 --to 2026-03-31` is active and a message was sent on `2026-02-20`
- **THEN** that message is excluded from all statistics including the total count

#### Scenario: Content stored in request entry
- **WHEN** a request message has content "Nhờ chị download giúp em tài liệu này"
- **THEN** each link entry for that message includes `"content": "Nhờ chị download giúp em tài liệu này"`
