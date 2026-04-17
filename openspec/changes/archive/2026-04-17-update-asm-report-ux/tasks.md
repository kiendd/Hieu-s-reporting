## 1. Today Shortcut
- [x] 1.1 Thêm flag `--today` vào argparse (mutually exclusive với `--from`, `--to`, `--date`)
- [x] 1.2 Trong `main()`: nếu `--today`, tính ngày hôm nay theo UTC+7 và set `date_from`, `date_to`, `args.date` tương ứng trước khi dùng chúng
- [x] 1.3 Xác nhận conflict error khi dùng `--today` kèm `--from`/`--to`/`--date`

## 2. Deposit Terminology Rename
- [x] 2.1 Đổi tên CLI flags: `--coc-low` → `--deposit-low`, `--coc-high` → `--deposit-high` (và `dest` tương ứng); đọc `cfg.get("asm_deposit_low", 2)` và `cfg.get("asm_deposit_high", 5)` làm default trước khi argparse override
- [x] 2.2 Đổi tên tham số hàm `analyze_asm_reports`: `coc_low`/`coc_high` → `deposit_low`/`deposit_high`
- [x] 2.3 Đổi tên field trong `parse_asm_report` output: `coc_count` → `deposit_count`
- [x] 2.4 Đổi tên dict keys trong `analyze_asm_reports` output: `low_coc_shops`/`high_coc_shops` → `low_deposit_shops`/`high_deposit_shops`, và key trong mỗi entry: `coc_count` → `deposit_count`
- [x] 2.5 Cập nhật tất cả tham chiếu đến các keys/attrs đã đổi tên trong `main()`, `print_text_report()`, `print_json_report()`
- [x] 2.6 Đổi tên section header text report: "SHOP CỌC THẤP" → "SHOP ĐẶT CỌC THẤP", "SHOP CỌC CAO" → "SHOP ĐẶT CỌC CAO"

## 3. Skip Reporters
- [x] 3.1 Thêm key `asm_skip_reporters` vào config loading (mảng string, default `[]`)
- [x] 3.2 Thêm CLI flag `--skip-reporters "Name1,Name2"` vào argparse
- [x] 3.3 Trong `main()`: merge `cfg.get("asm_skip_reporters", [])` với `args.skip_reporters.split(",")` thành `skip_list`
- [x] 3.4 Cập nhật `check_asm_compliance()`: nhận thêm tham số `skip_list: list[str]`; lọc members trước khi kiểm tra compliance (substring case-insensitive)

## 4. Validation
- [x] 4.1 Test `--today`: xác nhận `date_from`/`date_to`/`target_date` đều set về hôm nay VN
- [x] 4.2 Test `--today` kèm `--from`: xác nhận báo lỗi và exit non-zero
- [x] 4.3 Test `--deposit-low`/`--deposit-high`: xác nhận flags mới hoạt động, `--coc-low` bị reject
- [x] 4.5 Test config keys `asm_deposit_low`/`asm_deposit_high`: xác nhận config được đọc đúng, CLI override config
- [x] 4.4 Test `--skip-reporters`: xác nhận member bị exclude không xuất hiện trong "ASM CHƯA BÁO CÁO"
