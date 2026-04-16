# Change: Simplify Tool to ASM-Only Reporting

## Why
Tool hiện tại có hai chức năng độc lập: (1) thống kê request tài liệu, (2) phân tích báo cáo ASM. Người dùng chỉ cần chức năng ASM — phần còn lại là dead weight làm phức tạp code và output.

## What Changes

### Xóa bỏ
- **REMOVED** toàn bộ phân tích document-request: `analyze()`, requesters, file senders, links, monthly stats, user cache
- **REMOVED** `print_text_report()`, `print_json_report()`, `write_excel()` (3 sheet cũ) — thay bằng bản ASM-only
- **REMOVED** `load_keywords()`, `fmt_size()`, `fmt_user()` — không còn dùng
- **REMOVED** flag `--asm-report` — ASM analysis luôn chạy (auto-detect)
- **REMOVED** flags `--format json`, keyword config (`request_keywords`)
- **REMOVED** `keywords.txt` support

### Giữ lại
- Fetch messages, auth, group ID resolution, `--load`/`--save`, date range filter, `--today`
- Toàn bộ ASM pipeline: detect → parse → analyze → compliance
- `--deposit-low/high`, `--asm-deadline`, `--date`, `--skip-reporters`
- Config keys: `token`, `group`, `api_url`, `asm_deposit_low`, `asm_deposit_high`, `asm_skip_reporters`

### Thêm mới
- **ADDED** `--excel FILE` xuất 4 sheet ASM: "Shop Đặt Cọc", "Ý tưởng ASM", "Điểm nổi bật", "ASM chưa báo cáo"
- **MODIFIED** text output: chỉ hiển thị summary + 6 section ASM (không có requesters/files/links)

## Impact
- Affected specs: `fpt-chat-stats` (REMOVED nhiều requirements, MODIFIED output requirements)
- Affected code: `fpt_chat_stats.py` — xóa ~400 dòng, đơn giản hóa `main()`
- **BREAKING**: Toàn bộ output format thay đổi; không còn thống kê document request
