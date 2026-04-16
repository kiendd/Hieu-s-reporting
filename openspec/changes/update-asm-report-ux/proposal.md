# Change: Update ASM Report UX — Today Shortcut, Deposit Terminology, Skip Reporters

## Why
Ba cải tiến nhỏ về UX và convention sau khi dùng thực tế:
1. Phải gõ `--from YYYY-MM-DD --to YYYY-MM-DD --date YYYY-MM-DD` mỗi ngày là thừa — cần shortcut `--today`.
2. CLI flags `--coc-low`/`--coc-high` dùng từ tiếng Việt không chuẩn — "cọc" = đặt cọc = "deposit".
3. Group có manager/lead không cần báo cáo hàng ngày — compliance check sai khi liệt kê họ là "chưa báo cáo".

## What Changes
- **ADDED**: Flag `--today` đặt `--from`, `--to`, và `--date` đồng thời về ngày hiện tại (giờ VN UTC+7)
- **BREAKING**: Đổi tên CLI flags `--coc-low`/`--coc-high` → `--deposit-low`/`--deposit-high`; thêm config keys `asm_deposit_low`/`asm_deposit_high` (CLI > config > default)
- **BREAKING**: Đổi tên JSON output keys `low_coc_shops`/`high_coc_shops`/`coc_count` → `low_deposit_shops`/`high_deposit_shops`/`deposit_count`
- **ADDED**: Config key `asm_skip_reporters` — danh sách `displayName` (substring, case-insensitive) bị loại khỏi compliance check
- **ADDED**: CLI flag `--skip-reporters "Name1,Name2"` — override/bổ sung cho config key

## Impact
- Affected specs: `fpt-chat-stats` (ADDED: Today Shortcut), `asm-report-analysis` (deposit rename + skip reporters)
- Affected code: `fpt_chat_stats.py` — CLI args, `analyze_asm_reports()`, `check_asm_compliance()`, output sections, `config.json` schema
- Dependency: `add-asm-daily-report-features` nên được archive trước change này để tránh xung đột spec

## Notes
- `asm-report-analysis` chưa tồn tại trong `specs/` (chưa archive) → tất cả delta dùng `ADDED`
- Regex detection trong source text ("cọc") **không thay đổi** — chỉ đổi tên API/CLI/JSON facing
