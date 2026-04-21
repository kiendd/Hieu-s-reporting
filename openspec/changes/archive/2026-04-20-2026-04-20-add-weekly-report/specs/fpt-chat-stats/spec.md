## ADDED Requirements

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
