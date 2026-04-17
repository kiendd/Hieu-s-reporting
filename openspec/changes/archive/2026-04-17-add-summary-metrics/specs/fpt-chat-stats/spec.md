## MODIFIED Requirements

### Requirement: ASM Report Parsing
`parse_asm_report` SHALL extract the following fields from each message:
- `shop_ref`, `deposit_count`, `tich_cuc`, `van_de`, `da_lam`, `sender`, `sender_id`, `sent_at`, `message_id` (existing)
- `ra_tiem_count` (NEW): integer parsed from the pattern `(\d+)\s*ra\s*tiêm` in the message content; `None` when the pattern is absent or has no numeric value

#### Scenario: ra_tiem_count present
- **WHEN** message contains `1 KH ra tiêm`
- **THEN** `parse_asm_report` returns `{"ra_tiem_count": 1, ...}`

#### Scenario: ra_tiem_count absent or non-numeric
- **WHEN** message contains `KH ra tiêm chưa chất lượng` (no number) or no ra tiêm mention
- **THEN** `parse_asm_report` returns `{"ra_tiem_count": None, ...}`

---

## ADDED Requirements

### Requirement: Late Reporter Detection
`fpt_chat_stats` SHALL expose a `check_late_reporters(parsed_reports, target_date_str, deadline_hhmm) -> list[dict]` function that returns entries `{sender, sent_at_vn}` for each parsed report whose VN-time timestamp on the target date falls **after** the deadline. Reports on other dates are ignored.

#### Scenario: Report sent after deadline
- **WHEN** a report's VN-time is 21:05 and deadline is "20:00"
- **THEN** that sender appears in the returned list with their sent_at_vn time

#### Scenario: Report sent before deadline
- **WHEN** a report's VN-time is 19:45 and deadline is "20:00"
- **THEN** that sender does NOT appear in the returned list
