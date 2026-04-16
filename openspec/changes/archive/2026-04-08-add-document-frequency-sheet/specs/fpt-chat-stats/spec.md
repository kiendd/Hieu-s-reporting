## MODIFIED Requirements

### Requirement: Excel Report Export
The tool SHALL write a `.xlsx` Excel file when `--excel FILE` is provided. The file contains three sheets: "Tổng hợp", "Chi tiết", and "Tần suất tài liệu". Writing the Excel file does not suppress other output formats — `--format text` and `--excel` may be used together.

#### Scenario: Excel file created with three sheets
- **WHEN** the user passes `--excel report.xlsx`
- **THEN** `report.xlsx` is written containing sheets named "Tổng hợp", "Chi tiết", and "Tần suất tài liệu" in that order

#### Scenario: Combined with text report
- **WHEN** the user passes `--excel report.xlsx --format text`
- **THEN** the text report is printed to `stdout` AND `report.xlsx` is written with all three sheets

#### Scenario: Excel not requested
- **WHEN** `--excel` is not passed
- **THEN** no `.xlsx` file is written; tool behaviour is unchanged

---

## ADDED Requirements

### Requirement: Document Frequency Sheet ("Tần suất tài liệu")
The "Tần suất tài liệu" sheet SHALL display one row per unique URL that appeared in request messages, showing how many times it was requested and by whom.

Columns (in order):
1. **STT** — sequential row number (1, 2, 3…)
2. **URL** — the full URL string
3. **Số lần request** — total number of times this URL appeared across all request messages
4. **Người request** — comma-separated, deduplicated list of display names who requested this URL

Rows are sorted by "Số lần request" descending (most-requested first).
The top row is bold and frozen. The URL column is auto-sized (capped at a readable width).

#### Scenario: URL requested multiple times by different users
- **WHEN** URL "https://gartner.com/doc/123" appears in 2 messages: one from user A and one from user B
- **THEN** the sheet has one row for that URL with count=2 and "Người request" = "User A, User B"

#### Scenario: URL requested multiple times by same user
- **WHEN** URL "https://gartner.com/doc/456" appears in 3 messages all from user A
- **THEN** count=3 but "Người request" = "User A" (deduplicated, name appears once)

#### Scenario: Keyword-only requests excluded
- **WHEN** a request message matched via keyword but contained no links
- **THEN** it contributes no rows to this sheet (it appears in "Chi tiết" only)

#### Scenario: Sheet order
- **WHEN** the Excel file is opened
- **THEN** sheet tab order is: "Tổng hợp" → "Chi tiết" → "Tần suất tài liệu"
