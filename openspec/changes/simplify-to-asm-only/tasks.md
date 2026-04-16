## 1. Xóa code không dùng
- [ ] 1.1 Xóa hàm `load_keywords()` và toàn bộ logic đọc `keywords.txt`
- [ ] 1.2 Xóa hàm `analyze()` (~90 dòng)
- [ ] 1.3 Xóa hàm `fmt_size()`, `fmt_user()`
- [ ] 1.4 Xóa hàm `print_text_report()` (~130 dòng) và `print_json_report()` (~45 dòng)
- [ ] 1.5 Xóa hàm `write_excel()` (3 sheet cũ, ~120 dòng)

## 2. Đơn giản hóa CLI
- [ ] 2.1 Xóa flag `--asm-report` khỏi argparse
- [ ] 2.2 Xóa flag `--format` khỏi argparse
- [ ] 2.3 Xóa flag `--limit` nếu không còn dùng cho mục đích nào khác (optional, giữ nếu muốn)

## 3. Viết output mới tập trung vào ASM
- [ ] 3.1 Viết hàm `print_asm_report(asm_data, date_from, date_to)`: in summary header + 6 section ASM
- [ ] 3.2 Thay thế call `print_text_report(stats)` trong `main()` bằng `print_asm_report(...)`

## 4. Viết Excel export mới với 4 sheet ASM
- [ ] 4.1 Viết hàm `write_asm_excel(asm_data, path)`: tạo 4 sheet ("Shop Đặt Cọc", "Ý tưởng ASM", "Điểm nổi bật", "ASM chưa báo cáo")
- [ ] 4.2 Thay thế call `write_excel(stats, args.excel)` trong `main()` bằng `write_asm_excel(asm_data, args.excel)`

## 5. Cập nhật main()
- [ ] 5.1 Bỏ `analyze()` call và `stats` dict (hoặc giữ minimal cho `date_from`/`date_to`)
- [ ] 5.2 ASM pipeline luôn chạy: detect → parse → analyze → fetch members → compliance
- [ ] 5.3 Pass `asm_data` trực tiếp vào `print_asm_report()` và `write_asm_excel()`

## 6. Validation
- [ ] 6.1 Syntax check: `python3 -c "import fpt_chat_stats"`
- [ ] 6.2 Test offline với 3 mẫu báo cáo: xác nhận output đủ 6 section
- [ ] 6.3 Test `--excel`: xác nhận 4 sheet được tạo đúng tên và có data
- [ ] 6.4 Test khi không có báo cáo ASM: xác nhận cảnh báo + section trống
