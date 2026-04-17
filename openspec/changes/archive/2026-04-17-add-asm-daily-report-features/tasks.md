## 0. Discovery
- [x] 0.1 Verify cấu trúc response của `GET /group-management/group/{groupId}/participant?limit=50&page=1` — field: `id`, `displayName` (đã xác nhận)

## 1. Parser
- [x] 1.1 Viết hàm `detect_asm_reports(messages) -> list[dict]`: lọc tin nhắn TEXT khớp heuristic (có "shop" + `\d+ cọc`)
- [x] 1.2 Viết hàm `parse_asm_report(msg) -> dict`: regex extract `shop_ref`, `coc_count`, `tich_cuc`, `van_de`, `da_lam`, `sender`, `sent_at`
- [x] 1.3 Viết unit test thủ công (offline) với 3 mẫu báo cáo đã cho để xác nhận parse đúng tất cả fields

## 2. Analysis
- [x] 2.1 Viết hàm `analyze_asm_reports(parsed_reports, coc_low, coc_high) -> dict`: trả về `low_coc_shops`, `high_coc_shops`, `ideas`, `highlights`
- [x] 2.2 Viết hàm `fetch_group_members(session, base_url, group_id, limit=50) -> list[dict]`: phân trang qua `GET /group-management/group/{groupId}/participant?limit=50&page=n` cho đến khi hết. Trả về `[]` và in cảnh báo nếu API thất bại.
- [x] 2.3 Viết hàm `check_asm_compliance(parsed_reports, members, target_date, deadline_time) -> list[str]`: so sánh members với báo cáo đã gửi, trả về `displayName` của những người chưa báo cáo
- [x] 2.4 Xử lý edge case: không có báo cáo nào được parse (cảnh báo stderr), members fetch thất bại (bỏ qua compliance), offline mode thiếu token (cảnh báo + bỏ qua)

## 3. CLI
- [x] 3.1 Thêm flag `--asm-report` vào argparse
- [x] 3.2 Thêm flags `--coc-low`, `--coc-high`, `--asm-deadline`, `--date` (chỉ hiệu lực khi `--asm-report` bật)
- [x] 3.3 Cập nhật `main()`: gọi `fetch_group_members`, `analyze_asm_reports`, và `check_asm_compliance` khi flag được bật

## 4. Report Output
- [x] 4.1 Cập nhật `print_text_report()`: thêm 6 section mới khi `asm_report` data có trong stats
- [x] 4.2 Cập nhật `print_json_report()`: thêm key `asm_report` với sub-keys đầy đủ
- [x] 4.3 Xác nhận không có regression: chạy tool không có `--asm-report`, output giống hệt trước

## 5. Validation
- [x] 5.1 Chạy offline với 3 mẫu báo cáo (`--load`) và `--asm-report`, kiểm tra tất cả 4 tính năng hoạt động đúng
- [x] 5.2 Kiểm tra compliance tracking: mock members list gồm ít nhất 1 người có báo cáo và 1 người không có, xác nhận output đúng
