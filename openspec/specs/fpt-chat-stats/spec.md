# fpt-chat-stats Specification

## Purpose
TBD - created by archiving change add-fpt-chat-stats-tool. Update Purpose after archive.
## Requirements
### Requirement: Message Fetching
The tool SHALL fetch the complete message history of a FPT Chat group by making repeated paginated requests to the FPT Chat API until all messages have been retrieved.

#### Scenario: Full history retrieved via pagination
- **WHEN** the group contains more messages than the page `limit`
- **THEN** the tool sends subsequent requests using the oldest fetched message ID as the `before` cursor until a page returns fewer messages than `limit`

#### Scenario: Single page group
- **WHEN** the group contains fewer messages than `limit`
- **THEN** the tool makes one request and stops

#### Scenario: API error
- **WHEN** the API returns a non-2xx HTTP status
- **THEN** the tool prints the error to `stderr` and exits with a non-zero code

---

### Requirement: Authentication
The tool SHALL authenticate against the FPT Chat API using a `fchat_ddtk` token sent as both an `Authorization: Bearer` header and an `fchat_ddtk` cookie on every request.

The token MAY be supplied via:
1. `--token` CLI argument (highest precedence), or
2. `token` key in the config file (see *Config File Loading* requirement)

At least one source MUST provide the token; otherwise the tool exits with an error.

#### Scenario: Token provided via CLI
- **WHEN** the user passes `--token <value>`
- **THEN** every API request includes `Authorization: Bearer <value>` and `Cookie: fchat_ddtk=<value>`

#### Scenario: Token provided via config file
- **WHEN** `config.json` contains `"token": "<value>"` and `--token` is not passed
- **THEN** every API request includes `Authorization: Bearer <value>` and `Cookie: fchat_ddtk=<value>`

### Requirement: Group ID Resolution
The tool SHALL accept a group identifier as either a raw 24-character hex ID or a full FPT Chat URL, and resolve it to the hex ID before making API calls.

#### Scenario: Raw ID passed
- **WHEN** `--group 687d9b9b805279fc03d25365` is given
- **THEN** the tool uses `687d9b9b805279fc03d25365` directly as the group ID

#### Scenario: URL passed
- **WHEN** `--group "https://chat.fpt.com/group/687d9b9b805279fc03d25365"` is given
- **THEN** the tool extracts `687d9b9b805279fc03d25365` via regex and uses it as the group ID

---

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

### Requirement: Text Report Output
The tool SHALL produce a human-readable Vietnamese report to `stdout` when `--format text` (default) is used, covering: overview counts, top requesters, file senders, monthly timeline, link detail, and file detail.

User names in the requester list and file-sender list SHALL use the `"DisplayName (username)"` format when username is available (see *User Display Format* requirement).

#### Scenario: Default output with known usernames
- **WHEN** `--format text` is used and some users have cached usernames
- **THEN** those users appear as `"DisplayName (username)"` in the requester and file-sender sections

#### Scenario: Default output without filter
- **WHEN** no date flags are passed and `--format text`
- **THEN** the overview section contains `Khoảng thời gian: Toàn bộ lịch sử`

---

### Requirement: JSON Report Output
The tool SHALL produce a machine-readable JSON report to `stdout` when `--format json` is used, containing: `summary`, `requesters`, `file_senders`, `by_month`, `all_links`, and `all_files` keys.

#### Scenario: JSON selected
- **WHEN** the user passes `--format json`
- **THEN** valid JSON is printed to `stdout` and can be piped to `jq` or saved to a file

---

### Requirement: Raw Message Persistence
The tool SHALL save the fetched raw message list as a JSON file when `--save <path>` is provided, enabling offline re-analysis without repeating API calls.

#### Scenario: Save requested
- **WHEN** the user passes `--save raw.json`
- **THEN** after fetching, the full message list is written to `raw.json` as UTF-8 JSON

---

### Requirement: Offline Analysis Mode
The tool SHALL skip all API calls and load messages from a local JSON file when `--load <path>` is provided.

#### Scenario: Offline load
- **WHEN** the user passes `--load raw.json`
- **THEN** the tool reads messages from `raw.json`, runs analysis, and prints the report — making no network requests

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

### Requirement: Config File Loading
The tool SHALL load a JSON config file before resolving CLI arguments. Keys present in the config file are used as defaults; explicit CLI arguments take precedence.

Supported config keys:
- `token` — equivalent to `--token`
- `group` — equivalent to `--group`
- `api_url` — equivalent to `--api-url`
- `request_keywords` — list of strings used for keyword-based request detection

The default config file path is `config.json` in the current working directory. This path can be overridden with `--config FILE`.

If the config file is absent, the tool proceeds without error. If the file exists but contains malformed JSON, the tool exits with a descriptive error message.

#### Scenario: Config file present, no CLI token
- **WHEN** `config.json` contains `"token": "abc123"` and `--token` is not passed
- **THEN** the tool uses `"abc123"` as the token and proceeds normally

#### Scenario: CLI token overrides config
- **WHEN** `config.json` contains `"token": "abc123"` and `--token xyz789` is passed
- **THEN** the tool uses `"xyz789"` (CLI takes precedence)

#### Scenario: Config file absent
- **WHEN** no `config.json` exists and `--token`/`--group` are provided on CLI
- **THEN** the tool runs normally with no error about the missing config file

#### Scenario: Malformed config file
- **WHEN** `config.json` exists but contains invalid JSON
- **THEN** the tool prints a clear error to `stderr` and exits with a non-zero code

#### Scenario: Neither config nor CLI provides token
- **WHEN** `config.json` is absent and `--token` is not passed
- **THEN** the tool prints `"Error: --token is required (or set 'token' in config.json)"` and exits

---

### Requirement: Keyword-based Request Detection
The tool SHALL classify a TEXT message as a "request" if its `content` contains any of the configured `request_keywords` (case-insensitive substring match), in addition to the existing link-based detection.

A message is a request if it matches **either** condition:
- Contains one or more entries in `metadata.links`, **OR**
- Its `content` (lowercased) contains at least one configured keyword (also lowercased)

A message that satisfies both conditions is counted as a single request (no double-counting).

When `request_keywords` is empty (default), only link-based detection is used — preserving existing behaviour.

#### Scenario: Keyword match without links
- **WHEN** a TEXT message has content `"Nhờ c down giúp em tài liệu này"` and `"nhờ"` is a configured keyword
- **THEN** the message is classified as a request and the sender's request count increases by 1

#### Scenario: Link match without keyword
- **WHEN** a TEXT message has `metadata.links` with 2 entries but its content does not contain any keyword
- **THEN** the message is still classified as a request (existing link-based behaviour preserved)

#### Scenario: Both keyword and link match
- **WHEN** a TEXT message matches a keyword AND has links
- **THEN** the message is counted as exactly one request (not two)

#### Scenario: No keywords configured
- **WHEN** `request_keywords` is empty or not set
- **THEN** only link-based detection applies; tool behaviour is identical to before this change

#### Scenario: Case-insensitive match
- **WHEN** content is `"NHỜI c @Thu ơi"` and keyword is `"nhờ"`
- **THEN** the message is classified as a request (match is case-insensitive)

---

### Requirement: Request Count by Month
The tool SHALL compute and report a `requests_by_month` statistic: the number of request messages (keyword or link matched) grouped by `YYYY-MM`.

This is separate from `by_month` which counts all messages regardless of type.

#### Scenario: Requests counted per month
- **WHEN** 3 request messages were sent in March 2026 and 5 in April 2026
- **THEN** `requests_by_month` contains `{"2026-03": 3, "2026-04": 5}`

#### Scenario: Non-request messages excluded
- **WHEN** a FILE or ACTIVITY message is processed
- **THEN** it does not increment `requests_by_month`

#### Scenario: Displayed in text report
- **WHEN** `--format text` is used
- **THEN** a "REQUEST THEO THÁNG" section appears in the report showing counts per month

#### Scenario: Included in JSON report
- **WHEN** `--format json` is used
- **THEN** output contains a top-level `"requests_by_month"` key with month-count pairs

---

### Requirement: Excel Report Export
The tool SHALL write a `.xlsx` Excel file when `--excel FILE` is provided. The file contains three sheets: "Tổng hợp", "Chi tiết", and "Tần suất tài liệu".

The "Tổng hợp" and "Chi tiết" sheets SHALL include a **"Username"** column immediately after the "Người dùng" column, populated from the username cache. The cell is empty when the username is unknown.

#### Scenario: Username column in Tổng hợp
- **WHEN** the Excel file is written and user A has username "kiendt2"
- **THEN** the "Tổng hợp" sheet has a "Username" column showing "kiendt2" in user A's row

#### Scenario: Username column empty when unknown
- **WHEN** a user has no cached username
- **THEN** their "Username" cell in both sheets is empty (not `None`, not `"Unknown"`)

#### Scenario: Excel file created with three sheets
- **WHEN** the user passes `--excel report.xlsx`
- **THEN** `report.xlsx` is written containing sheets named "Tổng hợp", "Chi tiết", and "Tần suất tài liệu" in that order

#### Scenario: Combined with text report
- **WHEN** the user passes `--excel report.xlsx --format text`
- **THEN** the text report is printed to `stdout` AND `report.xlsx` is written with all three sheets

#### Scenario: Excel not requested
- **WHEN** `--excel` is not passed
- **THEN** no `.xlsx` file is written; tool behaviour is unchanged

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

### Requirement: Username Cache
The tool SHALL build a `user_cache` mapping `user_id → {username, department}` during analysis by scanning the `reactions` array of every message. This cache is used by all output surfaces to display usernames alongside display names.

The cache is populated silently; no error is raised if a user has no cached username. Users without a cached username are displayed using their display name only.

#### Scenario: Username extracted from reaction
- **WHEN** a message has a reaction where `user.username = "KienDT2"` and `user.id = "abc123"`
- **THEN** `user_cache["abc123"]["username"] = "KienDT2"`

#### Scenario: Same user appears in multiple reactions
- **WHEN** user `abc123` appears in reactions on 5 different messages
- **THEN** the cache entry for `abc123` is set once; no error or duplication occurs

#### Scenario: User never reacted
- **WHEN** a message sender has no entries in any reaction across the entire message set
- **THEN** their `user_id` is absent from `user_cache`; display name is used as-is in all outputs

---

### Requirement: User Display Format
Wherever a user's name is displayed in any output (text report or Excel), the tool SHALL use the format `"DisplayName (username)"` when the username is known, or `"DisplayName"` when it is not.

#### Scenario: Username known
- **WHEN** `user_cache` contains an entry for the user's ID with `username = "KienDT2"`
- **THEN** the user appears as `"Doan Trung Kien (KienDT2)"` in all outputs

#### Scenario: Username unknown
- **WHEN** `user_cache` has no entry for the user's ID
- **THEN** the user appears as `"Doan Trung Kien"` with no parentheses

---

