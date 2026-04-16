# Change: Add User Username / Account ID Display

## Why
Display names in FPT Chat (e.g., "Doan Trung Kien") are not unique and hard to cross-reference with HR/email systems. The username/account ID (e.g., "KienDT2", which is the FPT email prefix) uniquely identifies each person and makes reports usable for follow-up actions.

## What Changes
- **NEW** username cache built during `analyze()` — scan all `reactions[].user` objects (which carry `username` and `department` fields absent from message sender objects) and build a `{user_id → username}` lookup.
- **MODIFIED** every output surface to show username alongside display name:
  - Text report: `Doan Trung Kien (KienDT2)`
  - Excel "Tổng hợp": separate "Username" column next to "Người dùng"
  - Excel "Chi tiết": separate "Username" column next to "Người dùng"
  - Excel "Tần suất tài liệu" (when added): "Người request" shows `DisplayName (username)` format

## Design Decisions
- **Auto-extract from reactions** — no extra API calls, no manual mapping. Reactions embed the full user profile including `username`. This covers the majority of active participants.
- **Limitation**: users who never reacted to any message in the group will have no cached username; they show display name only.
- **Format chosen**: `DisplayName (username)` — keeps the human-readable name primary, username in parentheses for lookup. Applied consistently across all outputs.
- **`department` field also cached** — available in the same reaction user objects; stored in the cache for potential future use but not displayed in this change.

## Impact
- Affected specs: `fpt-chat-stats` (MODIFIED: Statistical Analysis, Text Report Output, Excel Report Export)
- Affected code: `analyze()`, `print_text_report()`, `write_excel()`
- No breaking changes; username is shown only when available, gracefully omitted otherwise.
