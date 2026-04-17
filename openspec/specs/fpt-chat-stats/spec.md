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

### Requirement: Text Report Output
The tool SHALL produce a Vietnamese text report to `stdout` containing only ASM report analysis results:

1. **Summary header**: date range, số báo cáo ASM phát hiện được, số thành viên group (nếu fetch được)
2. **SHOP ĐẶT CỌC THẤP**: shops có deposit count < `deposit_low`
3. **SHOP ĐẶT CỌC CAO**: shops có deposit count > `deposit_high`
4. **Ý TƯỞNG TRIỂN KHAI TỪ ASM**: nội dung "Đã làm" từng ASM
5. **ĐIỂM TÍCH CỰC**: nội dung "Tích cực" từng ASM
6. **ĐIỂM HẠN CHẾ**: nội dung "Vấn đề" từng ASM
7. **ASM CHƯA BÁO CÁO**: tên đầy đủ thành viên chưa báo cáo trước deadline (chỉ hiện khi fetch members thành công)

Khi không phát hiện báo cáo ASM nào, tool in cảnh báo và các section hiển thị "(không có)".

#### Scenario: Reports detected
- **WHEN** messages contain 3 ASM reports and `--today` is active
- **THEN** stdout contains all 7 sections populated with parsed data

#### Scenario: No reports detected
- **WHEN** no messages match the ASM heuristic
- **THEN** a warning is printed to `stderr` and all sections show "(không có)"

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

### Requirement: Excel Report Export
When `--excel FILE` is provided, the tool SHALL write a `.xlsx` file containing **four ASM-focused sheets**:

1. **"Shop Đặt Cọc"**: tất cả shops được phân tích, với cột: STT, Shop, Số đặt cọc, Mức (Thấp/Bình thường/Cao), ASM. Rows sắp xếp theo số đặt cọc giảm dần.
2. **"Ý tưởng ASM"**: cột STT, ASM, Shop, Nội dung "Đã làm", Ngày giờ (UTC+7).
3. **"Điểm nổi bật"**: cột STT, ASM, Shop, Loại (Tích cực/Hạn chế), Nội dung.
4. **"ASM chưa báo cáo"**: cột STT, Tên ASM — chỉ có data khi fetch members thành công; nếu không sheet vẫn tồn tại với header và ghi chú "(Không thể kiểm tra — thiếu token/group)".

#### Scenario: Excel with full ASM data
- **WHEN** `--excel report.xlsx --today` is passed and ASM reports are detected
- **THEN** `report.xlsx` is written with all 4 sheets populated

#### Scenario: Excel when no members fetched
- **WHEN** members API fails or token is absent
- **THEN** sheet "ASM chưa báo cáo" is still created but contains only a note row

#### Scenario: Excel when no ASM reports
- **WHEN** no ASM reports are detected
- **THEN** all 4 sheets are created with headers only (no data rows)

---

### Requirement: Auto ASM Detection
The tool SHALL always run the ASM detection and analysis pipeline automatically — no explicit flag required. If ASM reports are found, analysis results are included in all outputs. If none are found, output sections are empty and a warning is printed to `stderr`.

The `--asm-report` flag is removed.

#### Scenario: ASM reports present — auto included in output
- **WHEN** the fetched messages contain ASM report messages
- **THEN** all ASM sections appear in text output and Excel without any extra flag

#### Scenario: No ASM reports — clean output with warning
- **WHEN** no ASM report messages are detected
- **THEN** ASM sections show "(không có)" and a warning is printed to `stderr`

### Requirement: Today Shortcut
The tool SHALL support a `--today` flag that automatically sets the date range and compliance date to the current date in Vietnam time (UTC+7), eliminating the need to type the date manually.

When `--today` is passed:
- `--from` is set to today's date (start of day, UTC)
- `--to` is set to today's date (end of day, UTC)
- `--date` is set to today's date (for ASM compliance check)

`--today` MUST NOT be combined with `--from`, `--to`, or `--date`; if any of these are also provided, the tool SHALL exit with an error.

#### Scenario: Today shortcut sets date range
- **WHEN** `--today` is passed
- **THEN** messages are filtered to today (VN time) and the compliance check uses today as the target date

#### Scenario: Conflict with explicit date flags
- **WHEN** `--today --from 2026-04-01` are both passed
- **THEN** the tool prints an error to `stderr` and exits with a non-zero code

---

### Requirement: ASM Report Parsing — ra_tiem_count
`parse_asm_report` SHALL extract a `ra_tiem_count` field from each message using the regex pattern `(\d+)\s*ra\s*tiêm`. The field is an integer when the pattern matches with a leading number; `None` when the pattern is absent or has no numeric value.

#### Scenario: ra_tiem_count present
- **WHEN** message contains `1 KH ra tiêm`
- **THEN** `parse_asm_report` returns `{"ra_tiem_count": 1, ...}`

#### Scenario: ra_tiem_count absent or non-numeric
- **WHEN** message contains `KH ra tiêm chưa chất lượng` (no number) or no ra tiêm mention
- **THEN** `parse_asm_report` returns `{"ra_tiem_count": None, ...}`

---

### Requirement: Late Reporter Detection
`fpt_chat_stats` SHALL expose a `check_late_reporters(parsed_reports, target_date_str, deadline_hhmm) -> list[dict]` function that returns entries `{sender, sent_at_vn}` for each parsed report whose VN-time timestamp on the target date falls **after** the deadline. Reports on other dates are ignored.

#### Scenario: Report sent after deadline
- **WHEN** a report's VN-time is 21:05 and deadline is "20:00"
- **THEN** that sender appears in the returned list with their sent_at_vn time

#### Scenario: Report sent before deadline
- **WHEN** a report's VN-time is 19:45 and deadline is "20:00"
- **THEN** that sender does NOT appear in the returned list

#### Scenario: Today shortcut without ASM report
- **WHEN** `--today` is passed without `--asm-report`
- **THEN** only messages from today (VN time) are analyzed; `--from`/`--to` are auto-set and the date range label shows today's date

#### Scenario: Today shortcut with ASM report
- **WHEN** `--today --asm-report` are both passed
- **THEN** messages are filtered to today, AND the compliance check uses today as the target date

#### Scenario: Conflict with explicit date flags
- **WHEN** `--today --from 2026-04-01` are both passed
- **THEN** the tool prints an error to `stderr` and exits with a non-zero code

