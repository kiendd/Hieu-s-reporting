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

---

### Requirement: Multi-Day Analysis Function
`fpt_chat_stats` SHALL expose an `analyze_multiday(parsed_reports, date_from_str, date_to_str) -> dict` function that produces time-aware analytics across a date range. The function groups parsed reports by calendar date (VN timezone UTC+7) and by sender.

The returned dict SHALL contain:
- `total_days` (int): number of calendar days from date_from to date_to inclusive
- `daily_summary` (list): one entry per calendar day — `{date, total_deposits, total_ra_tiem, reporter_count}`, sorted by date ascending
- `asm_summary` (list): one entry per unique sender — `{sender, report_days, report_rate, total_deposits, avg_deposits_per_day, longest_streak, longest_gap}`, sorted by report_rate descending
- `missing_by_day` (list): one entry per calendar day — `{date, missing_senders}` listing senders who appeared at least once in the range but did NOT report on that specific day, sorted by date ascending
- `shop_summary` (list): one entry per unique shop_ref — `{shop_ref, sender, total_deposits, report_days, avg_deposits}`, sorted by total_deposits descending

A sender "reported on a day" if they have at least one parsed report whose VN-time date matches that calendar day (no deadline check).

#### Scenario: Basic weekly analysis
- **WHEN** 7 days of reports are passed with varying reporter activity
- **THEN** `total_days` is 7, `daily_summary` has 7 entries, and `asm_summary` has one entry per unique sender

#### Scenario: Streak calculation
- **WHEN** an ASM reports on days 1, 2, 3, skips day 4, reports on day 5
- **THEN** their `longest_streak` is 3 and `longest_gap` is 1

#### Scenario: Missing senders per day
- **WHEN** sender A reports on all 7 days but sender B only reports on 3 days
- **THEN** `missing_by_day` entries for the 4 days B missed include B's name

#### Scenario: Shop cumulative deposits
- **WHEN** shop X appears in reports on 3 different days with deposits 5, 3, 7
- **THEN** shop X's `total_deposits` is 15, `report_days` is 3, `avg_deposits` is 5.0

### Requirement: Weekly Report Analysis Function
`fpt_chat_stats` SHALL expose an `analyze_weekly(messages, group_members, target_date_vn, deadline)` function that produces a single-day compliance-and-content view, independent of the daily shop-report parser.

A message qualifies as "a weekly report sent" when ALL of the following **hard gates** hold:
- `type == "TEXT"`
- message body (`content` field) is non-empty after whitespace strip
- sender's `displayName` is present in `group_members`
- the message's VN-time date (UTC+7) equals `target_date_vn`

AND the message's body achieves **score ≥ `WEEKLY_SCORE_THRESHOLD`** (default `3`) under the six-feature scoring function defined below. The scoring function distinguishes real weekly reports from casual chat based on structural and lexical features observed across `templates/weekend/1..8`.

**Feature scoring (one point per feature, 0–6):**

| # | Feature            | Matcher (case-insensitive; `\b` = word boundary) |
|---|--------------------|--------------------------------------------------|
| A | Length             | `len(content.strip()) >= WEEKLY_MIN_LENGTH` (default `150`) |
| B | Multi-line         | `"\n" in content` |
| C | Business unit      | matches `\b(tttc\|vx\s\|shop\b\|trung\s*tâm\|chi\s*nhánh\|lc\s+hcm)` |
| D | Numeric metric     | matches `\d+\s*%\|\d+(\.\d+)?\s*(tr\|triệu\|m\b\|k\b\|đ\b\|cọc\|bill\|khách\|lượt\|gói)` |
| E | Report opener/closer | matches `(đánh\s*giá\|báo\s*cáo\|em\s+(xin\s+)?cảm\s*ơn\|dạ\s+em\s+(gửi\|bc))` |
| F | Section label      | matches `(^\|\n)\s*[-–•\d\.]*\s*(kết\s*quả\|tích\s*cực\|vấn\s*đề\|đã\s*làm\|ngày\s*mai\|giải\s*pháp\|hành\s*động\|tổng\s*quan\|phân\s*tích)\s*[:：]` (line-anchored; uses `re.MULTILINE`) |

`WEEKLY_SCORE_THRESHOLD`, `WEEKLY_MIN_LENGTH`, and the six compiled feature regexes SHALL be module-level constants in `fpt_chat_stats.py` so the thresholds and vocabulary can be tuned in one place. The scoring function SHALL be exposed as `_score_weekly_message(content: str) -> int` and SHALL be a pure function of `content` (no external state). Configurability via CLI or config file is OUT OF SCOPE for this change.

The returned dict SHALL contain:
- `target_date` (str, `YYYY-MM-DD`)
- `deadline` (str, `HH:MM`)
- `reports` (list): one entry per sender who sent at least one qualifying message — `{sender, sent_at_vn, is_late, text, extra_count}` where `sent_at_vn` is the earliest qualifying message's VN time, `text` is that message's body, and `extra_count` is the count of additional qualifying messages from the same sender on the same VN day. Sorted by `sent_at_vn` ascending.
- `late_list` (list of str): senders whose earliest qualifying VN timestamp is at or after `deadline` on `target_date_vn`. Sorted alphabetically.
- `missing_list` (list of str): `displayName`s present in `group_members` with zero qualifying messages on `target_date_vn`. Sorted alphabetically.

The function SHALL NOT invoke `detect_asm_reports`, `parse_asm_report`, or `analyze_asm_reports`. It has no dependency on shop/cọc content heuristics.

#### Scenario: Basic split into three buckets
- **GIVEN** 10 group members and messages where 6 members sent text before deadline, 2 sent after deadline, 2 sent nothing, on `target_date_vn`
- **WHEN** `analyze_weekly` is called with `deadline="20:00"`
- **THEN** `reports` has 8 entries, `late_list` has the 2 late senders, and `missing_list` has the 2 silent senders

#### Scenario: Multiple messages from one sender
- **GIVEN** sender A sends 3 qualifying TEXT messages on the same VN day at 09:00, 10:30, and 14:00
- **WHEN** `analyze_weekly` runs
- **THEN** A's entry in `reports` has `sent_at_vn` equal to 09:00, `text` equal to the 09:00 message body, and `extra_count == 2`

#### Scenario: Non-TEXT messages ignored
- **GIVEN** sender B sends only ACTIVITY or FILE messages on `target_date_vn` and no TEXT message
- **WHEN** `analyze_weekly` runs
- **THEN** B appears in `missing_list`, not in `reports`

#### Scenario: Empty-body TEXT messages ignored
- **GIVEN** sender C sends a TEXT message whose body is whitespace-only on `target_date_vn`
- **WHEN** `analyze_weekly` runs
- **THEN** C appears in `missing_list`, not in `reports`

#### Scenario: Short acknowledgment ignored (score too low)
- **GIVEN** sender E sends one TEXT message "Ok anh" on `target_date_vn` and nothing else
- **WHEN** `analyze_weekly` runs
- **THEN** E's message scores 0 (fails every feature), is below threshold, and E appears in `missing_list`

#### Scenario: Long off-topic message ignored (score too low)
- **GIVEN** sender F sends one TEXT message of 400 characters on `target_date_vn` with multiple lines but no business-unit reference, no metric, no report opener/closer phrase, and no section label
- **WHEN** `analyze_weekly` runs
- **THEN** F's message scores 2 (features A and B only), is below threshold, and F appears in `missing_list`

#### Scenario: All feature matching is case-insensitive with word boundaries
- **GIVEN** sender G sends a message containing `"TTTC"`, `"trung tâm"`, and `"Đánh Giá"` in mixed case
- **WHEN** `analyze_weekly` runs
- **THEN** the business-unit and opener/closer features match regardless of case. A token embedded inside another word (e.g. `"shopping"` inside a narrative) SHALL NOT trigger feature C because the regex uses word boundaries.

#### Scenario: Narrative report without section labels qualifies
- **GIVEN** sender I sends a 900-character multi-line message that references `TTTC`, contains `Doanh thu 133%` and `Em cảm ơn ạ`, but uses only `-` bullet lines with no `Kết quả:` / `Tích cực:` / `Đã làm:` style section labels (shape similar to `templates/weekend/4` and `templates/weekend/6`)
- **WHEN** `analyze_weekly` runs
- **THEN** the message scores 5 (A + B + C + D + E; F fails) which is ≥ threshold, and I appears in `reports`

#### Scenario: Score threshold is exactly met
- **GIVEN** sender J sends a 200-character multi-line message that mentions `TTTC` but has no metric, no opener/closer phrase, and no section label
- **WHEN** `analyze_weekly` runs
- **THEN** the message scores exactly 3 (A + B + C) which meets the threshold, and J appears in `reports`

#### Scenario: Qualifying message among multiple non-qualifying messages
- **GIVEN** sender H sends three TEXT messages on `target_date_vn`: (1) "Ok anh" at 08:00 (score 0), (2) a 400-char off-topic message at 10:00 (score 2), (3) a full 800-char report matching every feature at 14:00 (score 6)
- **WHEN** `analyze_weekly` runs
- **THEN** H's `reports` entry has `sent_at_vn = 14:00`, `text` equal to message (3), and `extra_count = 0` (only message 3 qualifies; 1 and 2 are below threshold and therefore not counted toward `extra_count`)

#### Scenario: Sender not in group_members ignored
- **GIVEN** a TEXT message from an account whose `displayName` is not in `group_members`
- **WHEN** `analyze_weekly` runs
- **THEN** that message is not counted. Non-members never appear in `reports`, `late_list`, or `missing_list`.

#### Scenario: Attachment-only TEXT messages ignored
- **GIVEN** a sender posts an image or file whose API representation is `type == "TEXT"` with an empty or whitespace-only body (the caption is blank)
- **WHEN** `analyze_weekly` runs
- **THEN** that message is treated as an empty-body message and does not qualify; the sender appears in `missing_list` if they have no other qualifying message that day

#### Scenario: Bot and service accounts included if returned by members endpoint
- **GIVEN** `group_members` returned by `fetch_group_members` includes bot/service accounts
- **WHEN** `analyze_weekly` runs
- **THEN** those accounts are treated exactly like any other member — included in `missing_list` if silent, in `reports` if they sent qualifying text. The function SHALL NOT filter members by account type; upstream is responsible for the members list.

#### Scenario: Messages near VN midnight
- **GIVEN** a message sent at `2026-04-20T23:59:30+07:00` and another at `2026-04-21T00:00:15+07:00` with `target_date_vn = 2026-04-20`
- **WHEN** `analyze_weekly` runs
- **THEN** only the first message qualifies (VN-time date equals `2026-04-20`)

#### Scenario: Deadline boundary is inclusive-late
- **GIVEN** sender D's earliest qualifying message has VN time exactly `20:00:00` and `deadline="20:00"`
- **WHEN** `analyze_weekly` runs
- **THEN** D's entry has `is_late == true` and D appears in `late_list`

### Requirement: Weekly Report Print Output
`fpt_chat_stats` SHALL expose `print_weekly_report(data)` that writes the output of `analyze_weekly` to stdout using Vietnamese labels and the following structure:
- A header line with `BÁO CÁO TUẦN — <target_date>`, the deadline, and counts (`Đã báo cáo: N / Muộn: M / Chưa báo cáo: K`).
- A `Chưa báo cáo` section listing `missing_list`, one name per line.
- A `Muộn` section listing each late reporter with their VN send time.
- A `Nội dung báo cáo` section with one block per entry in `reports`: a header line `[<sender> — <HH:MM>]` (plus `— MUỘN` suffix when `is_late`, plus `(+N tin nhắn khác)` when `extra_count > 0`), followed by the raw `text` verbatim.

Progress/debug logs SHALL be written to stderr; the report SHALL be written only to stdout, consistent with the project convention.

#### Scenario: Late sender marker
- **GIVEN** one sender is late
- **WHEN** `print_weekly_report` runs
- **THEN** that sender's block header contains the literal substring `MUỘN`

### Requirement: Weekly Report Excel Output
`fpt_chat_stats` SHALL expose a writer that produces an `.xlsx` with exactly two sheets when invoked for weekly-report data:
- Sheet `Tổng hợp tuần`: columns `Người báo cáo`, `Trạng thái`, `Giờ gửi`. One row per group member. Status values are exactly one of the string literals `Đúng giờ`, `Muộn`, `Chưa báo cáo`. Members in `missing_list` have an empty `Giờ gửi`. Rows SHALL be ordered by status (`Đúng giờ` first, then `Muộn`, then `Chưa báo cáo`), then within each status group by `Giờ gửi` ascending (empty last), then by `Người báo cáo` alphabetically.
- Sheet `Nội dung`: columns `Người báo cáo`, `Giờ gửi`, `Trạng thái`, `Nội dung`. One row per entry in `reports`, ordered by `Giờ gửi` ascending. The `Nội dung` column has wrap-text enabled so long text displays without truncation. `Trạng thái` uses the same literal vocabulary (`Đúng giờ`, `Muộn`).

#### Scenario: Every member appears in Tổng hợp tuần
- **GIVEN** a group with 12 members where 7 reported on time, 2 were late, 3 are missing
- **WHEN** the weekly Excel writer runs
- **THEN** `Tổng hợp tuần` has exactly 12 data rows and `Nội dung` has exactly 9 data rows

### Requirement: Weekly Report CLI Flag
`fpt_chat_stats` SHALL accept a `--weekly YYYY-MM-DD` command-line flag that triggers the weekly-report pipeline for the given VN-time date.

When `--weekly` is set:
- The tool SHALL fetch messages whose `sent_at` falls within the half-open UTC window corresponding to VN day `[target_date 00:00+07, target_date+1 00:00+07)`. The cursor-based pagination SHALL stop as soon as messages older than `target_date 00:00+07` are reached, and SHALL have already retrieved any messages up to (and including) `target_date+1 00:00+07 - 1ns`, so that boundary-minute messages near VN midnight are not dropped.
- The tool SHALL fetch group members via the existing `fetch_group_members` path.
- The tool SHALL call `analyze_weekly` using the deadline resolved from: `config.json` `deadline` key, falling back to `"20:00"`. This change introduces no new CLI deadline flag.
- The tool SHALL call `print_weekly_report` on the result.
- If `--excel PATH` is also set, the tool SHALL write the weekly Excel output to `PATH`.
- `--weekly` SHALL be mutually exclusive with `--today`, `--from`, and `--to`. Combining them SHALL produce an error and exit non-zero without fetching.

#### Scenario: Mutually exclusive flags
- **WHEN** the user runs `--weekly 2026-04-20 --today`
- **THEN** the tool exits non-zero with an error message naming the conflicting flags, and performs no API calls

### Requirement: Weekly Report Members-Fetch Failure
If `fetch_group_members` fails (network error, non-2xx response, empty result) during the weekly pipeline, the tool SHALL surface the error on stderr and exit non-zero WITHOUT writing a partial report. The tool SHALL NOT silently substitute an empty members list, because doing so would make every sender look "not-in-group" and hide all missing reporters.

#### Scenario: Members fetch fails
- **GIVEN** `fetch_group_members` raises an exception or returns an empty list
- **WHEN** `--weekly` pipeline runs
- **THEN** the tool writes an error to stderr identifying the members-fetch failure and exits with a non-zero code; no stdout report and no Excel file are produced

