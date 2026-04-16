## 1. Analysis — username cache
- [x] 1.1 In `analyze()`, add `"user_cache": {}` to stats dict (`{user_id: {"username": ..., "department": ...}}`)
- [x] 1.2 For every message, scan `msg["reactions"]` and extract `user.id → {username, department}` into cache
- [x] 1.3 Add helper `fmt_user(name, user_id, cache) -> str` returning `"Name (username)"` if username known, else `"Name"`

## 2. Text report
- [x] 2.1 Apply `fmt_user()` in requester list and file-sender list of `print_text_report()`

## 3. Excel — Tổng hợp sheet
- [x] 3.1 Add "Username" column immediately after "Người dùng" column, populated from cache

## 4. Excel — Chi tiết sheet
- [x] 4.1 Add "Username" column immediately after "Người dùng" column, populated from cache per request entry

## 5. Validation
- [x] 5.1 Test with sample data containing reactions; verify username appears in text report for reacting users
- [x] 5.2 Verify users with no reactions show display name only (no crash, no empty parentheses)
- [x] 5.3 Verify Excel columns are correctly ordered and username column is populated
