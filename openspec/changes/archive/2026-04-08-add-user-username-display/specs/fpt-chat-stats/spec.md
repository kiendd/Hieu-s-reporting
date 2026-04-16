## ADDED Requirements

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

## MODIFIED Requirements

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
