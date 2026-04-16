## ADDED Requirements

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
