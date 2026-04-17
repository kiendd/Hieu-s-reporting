# asm-report-analysis Specification

## Purpose
TBD - created by archiving change update-asm-report-ux. Update Purpose after archive.
## Requirements
### Requirement: Deposit Threshold Configuration
The deposit count thresholds for shop filtering SHALL be configurable via both `config.json` and CLI flags, following the same precedence pattern as other config keys (CLI > config > built-in default).

Config keys:
- `asm_deposit_low` (int, default `2`): lower threshold
- `asm_deposit_high` (int, default `5`): upper threshold

CLI flags (override config):
- `--deposit-low N`: shops with deposit count strictly less than N appear in the low list
- `--deposit-high N`: shops with deposit count strictly greater than N appear in the high list

The old flags `--coc-low`/`--coc-high` are removed. Internal Python field names `coc_count`, `low_coc_shops`, `high_coc_shops` are renamed to `deposit_count`, `low_deposit_shops`, `high_deposit_shops` respectively. The regex patterns that detect "cọc" in raw message text are unchanged.

The JSON output keys SHALL reflect the new names: `low_deposit_shops`, `high_deposit_shops`, and each shop entry's count field SHALL be `deposit_count`.

#### Scenario: Thresholds from config file
- **WHEN** `config.json` contains `"asm_deposit_low": 3, "asm_deposit_high": 8` and no CLI flags override them
- **THEN** shops with deposit count < 3 appear in the low list and shops with count > 8 appear in the high list

#### Scenario: CLI overrides config
- **WHEN** `config.json` has `"asm_deposit_low": 3` and `--deposit-low 1` is passed
- **THEN** the effective threshold is 1 (CLI takes precedence)

#### Scenario: Low deposit shops
- **WHEN** effective `deposit_low` is 2 and a shop has deposit count 1
- **THEN** that shop appears in `low_deposit_shops` in JSON and "SHOP ĐẶT CỌC THẤP" section in text

#### Scenario: High deposit shops
- **WHEN** effective `deposit_high` is 5 and a shop has deposit count 12
- **THEN** that shop appears in `high_deposit_shops` in JSON and "SHOP ĐẶT CỌC CAO" section in text

#### Scenario: Old flags removed
- **WHEN** `--coc-low` or `--coc-high` is passed
- **THEN** argparse reports an unrecognized argument error

---

### Requirement: Skip Reporters
The compliance check SHALL support excluding specific group members from the "chưa báo cáo" list. Excluded members are managers or leads who are not expected to file daily ASM reports.

Members are excluded if their `displayName` contains any entry in the skip list as a **substring (case-insensitive)**.

The skip list is resolved from two sources (merged, no precedence conflict):
1. Config key `asm_skip_reporters`: array of strings in `config.json`
2. CLI flag `--skip-reporters "Name1,Name2"`: comma-separated names provided at runtime

A member matching any entry in the combined skip list is silently omitted from both the missing list and the compliance check entirely.

#### Scenario: Manager excluded via config
- **WHEN** `config.json` contains `"asm_skip_reporters": ["Nguyen Van Manager"]` and that member is in the group
- **THEN** that member does not appear in "ASM CHƯA BÁO CÁO" regardless of whether they reported

#### Scenario: Manager excluded via CLI flag
- **WHEN** `--skip-reporters "Tran Thi Lead"` is passed and that member is in the group
- **THEN** that member does not appear in "ASM CHƯA BÁO CÁO"

#### Scenario: Both sources merged
- **WHEN** config has `["Manager A"]` and `--skip-reporters "Lead B"` is passed
- **THEN** both "Manager A" and "Lead B" are excluded from compliance check

#### Scenario: Substring match
- **WHEN** skip list contains `"Manager"` and a member's `displayName` is `"Nguyen Van Manager HCM"`
- **THEN** that member is excluded (substring match)

#### Scenario: No skip list configured
- **WHEN** neither `asm_skip_reporters` nor `--skip-reporters` is provided
- **THEN** all group members are checked for compliance (existing behaviour)

### Requirement: ASM Report Detection
The tool SHALL identify ASM daily report messages within the fetched message list by applying a heuristic: a TEXT message is classified as an ASM report if it contains the word "shop" (case-insensitive) AND a pattern matching `\d+ cọc`.

#### Scenario: Valid report detected
- **WHEN** a TEXT message contains "Shop: 80035 173 Hùng Vương" and "12 cọc"
- **THEN** the message is classified as an ASM report and parsed for structured fields

#### Scenario: Non-report message ignored
- **WHEN** a TEXT message contains neither "shop" nor a cọc count
- **THEN** it is not classified as an ASM report and is excluded from ASM report analysis

#### Scenario: Parse failure warning
- **WHEN** a message is classified as an ASM report but a required field (shop name, cọc count) cannot be extracted
- **THEN** the tool prints a warning to `stderr` with the message ID and continues processing remaining messages

---

### Requirement: ASM Report Parsing
The tool SHALL extract the following structured fields from each detected ASM report message using regex-based parsing:

- **shop_ref**: shop code and/or name from the opening line (e.g. `"80035 173 Hùng Vương Tân An"`)
- **coc_count**: integer number of cọc from the "Kết quả" line
- **tich_cuc**: text content of the "Tích cực" section
- **van_de**: text content of the "Vấn đề" section
- **da_lam**: text content of the "Đã làm" section
- **sender**: `displayName` of the message sender (the ASM)
- **sent_at**: ISO-8601 datetime from `createdAt`

Parsing SHALL be tolerant of minor formatting variations (different dash styles `–`/`-`, extra whitespace, mixed capitalisation of section headers).

#### Scenario: All sections present
- **WHEN** a report contains all five sections (Kết quả, Tích cực, Vấn đề, Đã làm, Ngày mai)
- **THEN** all fields are populated correctly

#### Scenario: Missing optional section
- **WHEN** a report omits the "Ngày mai" section
- **THEN** the tool still extracts the other fields and stores `None` for the missing section

#### Scenario: Cọc count extraction
- **WHEN** the Kết quả line contains "2 cọc | 101 KH tiếp | 0 KH ra tiêm"
- **THEN** `coc_count` is set to `2`

#### Scenario: Shop ref with code and name
- **WHEN** the opening line is "Shop: 80931-LC HCM B06 Tổ 2 Ấp Phước Bình"
- **THEN** `shop_ref` is `"80931-LC HCM B06 Tổ 2 Ấp Phước Bình"`

---

### Requirement: Shop Cọc Filtering
When `--asm-report` is active, the tool SHALL produce two filtered shop lists from the parsed reports:

1. **Low-cọc list** (`coc_count < coc_low_threshold`, default `2`): shops needing attention
2. **High-cọc list** (`coc_count > coc_high_threshold`, default `5`): shops performing well

Thresholds SHALL be overridable via `--coc-low N` and `--coc-high N` CLI flags. Each entry in both lists SHALL include: `shop_ref`, `coc_count`, and `sender`.

#### Scenario: Shop below low threshold
- **WHEN** a parsed report has `coc_count = 1` and default thresholds apply
- **THEN** that shop appears in the low-cọc list

#### Scenario: Shop above high threshold
- **WHEN** a parsed report has `coc_count = 12` and default thresholds apply
- **THEN** that shop appears in the high-cọc list

#### Scenario: Shop within normal range
- **WHEN** a parsed report has `coc_count = 3` and default thresholds apply
- **THEN** that shop does not appear in either filtered list

#### Scenario: Custom thresholds
- **WHEN** `--coc-low 3 --coc-high 10` is passed and a shop has `coc_count = 3`
- **THEN** that shop appears in the low-cọc list (boundary is exclusive: `< 3` fails, but `< 3` means the value must be strictly less than 3, so `coc_count = 3` does NOT appear)

#### Scenario: No reports parsed
- **WHEN** no messages match the ASM report heuristic
- **THEN** both filtered lists are empty and the tool prints a warning to `stderr`

---

### Requirement: ASM Idea Extraction
When `--asm-report` is active, the tool SHALL collect the "Đã làm" (done/actions taken) content from each parsed report as a list of ASM implementation ideas, attributed to the sender and their shop.

Each idea entry SHALL include: `sender`, `shop_ref`, `da_lam` text, and `sent_at`.

#### Scenario: Ideas collected from multiple reports
- **WHEN** 3 ASM reports each have a "Đã làm" section
- **THEN** the idea list contains 3 entries, one per report

#### Scenario: Report with no "Đã làm" section
- **WHEN** a report does not contain a "Đã làm" section
- **THEN** no entry is added to the idea list for that report

---

### Requirement: Highlight Summary
When `--asm-report` is active, the tool SHALL aggregate highlight items across all parsed reports into two lists:

- **Tích cực** (positive highlights): all "Tích cực" section texts, each attributed to sender and shop_ref
- **Hạn chế** (limitations/issues): all "Vấn đề" section texts, each attributed to sender and shop_ref

#### Scenario: Highlights collected from all reports
- **WHEN** 5 reports are parsed and all have both "Tích cực" and "Vấn đề" sections
- **THEN** the tích_cực list has 5 entries and the hạn_chế list has 5 entries

#### Scenario: Text report highlight display
- **WHEN** `--asm-report` and `--format text` are active
- **THEN** the output contains a "ĐIỂM TÍCH CỰC" section and a "ĐIỂM HẠN CHẾ" section, each listing attributed highlights

#### Scenario: JSON report highlight keys
- **WHEN** `--asm-report` and `--format json` are active
- **THEN** the `asm_report` JSON object contains `"highlights": {"tich_cuc": [...], "han_che": [...]}`

---

### Requirement: Group Member Fetching
When `--asm-report` is active and compliance tracking is needed, the tool SHALL fetch the full member list of the target group by calling:

```
GET /group-management/group/{groupId}/participant?limit=50&page=<n>
```

Pagination is page-based (1-indexed). The tool SHALL fetch pages sequentially until a page returns fewer items than `limit`, collecting all members. The same authentication session (Bearer token + `fchat_ddtk` cookie) is reused.

Each member object carries `id` and `displayName` fields.

If the members API call fails (non-2xx) or the group ID is unavailable, the tool SHALL print a warning to `stderr` and skip compliance tracking without exiting.

When `--load` is used for offline analysis, the tool SHALL still attempt to fetch members if `--token` and `--group` are provided; otherwise compliance tracking is skipped with a warning.

#### Scenario: Members fetched in a single page
- **WHEN** `--asm-report` is active and the group has 20 members (fewer than limit=50)
- **THEN** one API call is made and all 20 members are used as the expected reporter list

#### Scenario: Members fetched across multiple pages
- **WHEN** the group has 110 members and limit=50
- **THEN** the tool makes 3 calls (pages 1, 2, 3) and collects all 110 members

#### Scenario: Members API fails
- **WHEN** the `/participant` endpoint returns a non-2xx response
- **THEN** the tool prints a warning to `stderr` and produces the report without the compliance section

#### Scenario: Offline mode without token
- **WHEN** `--load raw.json` is used and `--token`/`--group` are not provided
- **THEN** a warning is printed: "Không thể fetch group members — bỏ qua kiểm tra compliance" and the compliance section is omitted

---

### Requirement: ASM Compliance Tracking
When `--asm-report` is active and group members have been successfully fetched, the tool SHALL identify which members have NOT submitted a report by the deadline (default `20:00` Vietnam time, UTC+7).

The check applies to the date specified by `--date YYYY-MM-DD` (default: today in UTC+7).

A member is considered to have reported if at least one parsed ASM report message was sent by a sender whose `displayName` contains the member's `displayName` as a substring (case-insensitive match), and was sent before the deadline on the target date.

#### Scenario: All ASMs reported on time
- **WHEN** every group member has a matching parsed report before 20:00
- **THEN** the "chưa báo cáo" list is empty and the report shows "Tất cả ASM đã báo cáo"

#### Scenario: Some ASMs did not report
- **WHEN** 2 out of 5 group members have no matching report before 20:00 on the target date
- **THEN** the "chưa báo cáo" list contains the full `displayName` of those 2 members

#### Scenario: Custom deadline
- **WHEN** `--asm-deadline 21:00` is passed
- **THEN** members who reported between 20:00 and 21:00 are considered compliant

#### Scenario: Text report compliance section
- **WHEN** `--asm-report` and `--format text` are active and compliance data is available
- **THEN** the output contains an "ASM CHƯA BÁO CÁO" section listing full `displayName` values, one per line

---

### Requirement: ASM Report CLI Flag
The tool SHALL support a new `--asm-report` flag that activates all ASM report analysis features. When this flag is absent, the tool behaves identically to before (no regression).

Additional flags enabled only when `--asm-report` is active:
- `--coc-low N` (int, default 2): low cọc threshold (exclusive upper bound for low list)
- `--coc-high N` (int, default 5): high cọc threshold (exclusive lower bound for high list)
- `--asm-deadline HH:MM` (default `20:00`): daily reporting deadline in Vietnam time
- `--date YYYY-MM-DD` (default: today UTC+7): target date for compliance check

#### Scenario: Flag absent — no regression
- **WHEN** `--asm-report` is not passed
- **THEN** all existing output sections are produced unchanged and no ASM report sections appear

#### Scenario: Flag present — new sections added to text report
- **WHEN** `--asm-report` is passed with `--format text`
- **THEN** the text report includes four additional sections: "SHOP CỌC THẤP", "SHOP CỌC CAO", "Ý TƯỞNG TRIỂN KHAI TỪ ASM", "ĐIỂM TÍCH CỰC", "ĐIỂM HẠN CHẾ", and "ASM CHƯA BÁO CÁO"

#### Scenario: Flag present — new key in JSON report
- **WHEN** `--asm-report` is passed with `--format json`
- **THEN** the JSON output contains an `"asm_report"` top-level key with sub-keys: `"low_coc_shops"`, `"high_coc_shops"`, `"ideas"`, `"highlights"`, `"missing_reporters"`

---

### Requirement: Aggregate Summary Metrics
The analysis SHALL compute and expose the following aggregate fields in the `asm_data` dict:
- `total_deposits`: sum of `deposit_count` across all parsed reports (skipping `None`)
- `total_ra_tiem`: sum of `ra_tiem_count` across all parsed reports (skipping `None`)
- `no_deposit_shops`: list of `{sender, shop_ref}` where `deposit_count == 0`

#### Scenario: Deposits summed
- **WHEN** three ASM reports have deposit_count 5, 3, 0
- **THEN** `total_deposits` is 8 and `no_deposit_shops` contains the shop with 0 deposits

#### Scenario: ra_tiem summed with None
- **WHEN** two reports have ra_tiem_count 1 and None respectively
- **THEN** `total_ra_tiem` is 1 (None entries skipped)

---

### Requirement: Day-over-Day Comparison
The web UI SHALL display `total_deposits` and `total_ra_tiem` as `st.metric` tiles with a delta showing the difference vs. the previous calendar day (D-1).

D-1 data SHALL be fetched as a separate API call for the calendar day immediately before the target date. D-1 comparison is shown only when the analysis covers exactly one calendar day. For multi-day date ranges, the delta is omitted.

The D-1 `all_shops` list SHALL also be used to populate a **Cọc D-1** column in the "Shop đặt cọc", "Shop cọc thấp", and "Nhân viên cọc tốt" tables, matched by `shop_ref`. The column is omitted for multi-day ranges.

#### Scenario: Single-day run with D-1 available
- **WHEN** the user runs analysis for a single day and D-1 messages exist
- **THEN** the Tổng cọc metric tile shows today's total with a +/- delta vs. D-1

#### Scenario: Multi-day range
- **WHEN** the user selects a date range of more than one day
- **THEN** no D-1 delta is shown

#### Scenario: Shop đặt cọc table with D-1 column
- **WHEN** D-1 data is available and a shop also appeared in D-1
- **THEN** the "Shop đặt cọc" table shows that shop's D-1 deposit count in a Cọc D-1 column

#### Scenario: Shop absent from D-1
- **WHEN** D-1 data is available but a shop has no D-1 entry
- **THEN** the Cọc D-1 column shows `—` for that shop

---

### Requirement: No-Deposit and High-Deposit Shop Lists
The web UI SHALL display dedicated sections after the summary metrics:

**Shop báo cáo 0 cọc** — shops with `deposit_count == 0`, columns: ASM, Shop

**Shop cọc thấp** — shops with `deposit_count < deposit_low`, columns: ASM, Shop, Số cọc, Cọc D-1 (when D-1 data is available)

**Nhân viên cọc tốt** — shops where `deposit_count > deposit_high`, columns: ASM, Shop, Số cọc, Cọc D-1 (when D-1 data is available)

#### Scenario: Shop with 0 deposits appears in 0-cọc section
- **WHEN** an ASM report contains `0 cọc` for a shop
- **THEN** that shop appears in the "Shop báo cáo 0 cọc" section

#### Scenario: Low-deposit table with D-1 column
- **WHEN** D-1 data is available and a low-deposit shop also appeared in D-1
- **THEN** the Cọc D-1 column shows that shop's previous-day deposit count

#### Scenario: Cọc tốt table with D-1 column
- **WHEN** D-1 data is available and a high-deposit shop also appeared in D-1
- **THEN** the "Nhân viên cọc tốt" table shows that shop's D-1 deposit count

#### Scenario: D-1 column omitted on multi-day range
- **WHEN** the analysis covers more than one day
- **THEN** no Cọc D-1 column appears in any deposit table

---

### Requirement: Unreported-Now Table
The web UI SHALL display a dedicated **Chưa báo cáo đến hiện tại** section listing all group members who have not submitted any report as of the run time. The section appears below the summary metric row. When the list is empty, the section shows "Tất cả đã báo cáo". When `unreported_now` is `None` (member list unavailable), the section is hidden.

#### Scenario: Some members have not reported yet
- **WHEN** `unreported_now` contains one or more names
- **THEN** a "Chưa báo cáo đến hiện tại" section appears with those names listed

#### Scenario: All members have reported
- **WHEN** `unreported_now` is an empty list
- **THEN** the section shows "Tất cả đã báo cáo"

#### Scenario: Member list unavailable
- **WHEN** `unreported_now` is None
- **THEN** the section is not shown

---

### Requirement: Reporter Timing Metrics
The web UI SHALL display two timing metrics in the summary section:

- **Báo cáo muộn**: count of ASMs whose report on the target date was sent after the configured deadline
- **Chưa báo cáo**: count of group members with no report as of the run time (deadline = current VN time at the moment of the run)

#### Scenario: Late reporter counted
- **WHEN** an ASM sends their report at 21:05 and deadline is "20:00"
- **THEN** the "Báo cáo muộn" count includes that ASM

#### Scenario: Unreported as of now
- **WHEN** a member has not sent any report by the time the analysis runs
- **THEN** the "Chưa báo cáo" count includes that member

### Requirement: Report Detail Drill-Down
The web UI SHALL provide a **Xem chi tiết** expander at the bottom of each group's result section. The expander contains two independent selectors:

**Theo shop**: a selectbox listing all `shop_ref` values from parsed reports. When a shop is selected, a detail card is shown containing:
- ASM (sender name), Số cọc, Cọc D-1 (when D-1 data is available), Ra tiêm, Giờ gửi
- Tích cực, Vấn đề, Đã làm (full text from the parsed report)

**Theo nhân viên**: a selectbox listing all unique `sender` values. When an ASM is selected, one detail card per shop that ASM reported is shown (an ASM may report multiple shops).

The two selectors are independent — selecting one does not clear or affect the other.

#### Scenario: User selects a shop
- **WHEN** the user opens the "Xem chi tiết" expander and selects a shop_ref
- **THEN** a detail card appears showing that shop's ASM, deposit count, ra tiêm count, send time, tich_cuc, van_de, and da_lam

#### Scenario: User selects an ASM with multiple shops
- **WHEN** the user selects an ASM who reported two shops
- **THEN** two detail cards appear, one per shop

#### Scenario: Cọc D-1 shown in detail card when available
- **WHEN** D-1 data is available and the selected shop appeared in D-1
- **THEN** the detail card includes the D-1 deposit count

#### Scenario: No selection made
- **WHEN** the expander is open but neither selector has a value chosen
- **THEN** no detail card is shown

