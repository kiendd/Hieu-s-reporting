# Change: Add ASM Daily Report Analysis Features

## Why
Hệ thống hiện tại chỉ thống kê ai request tài liệu. Ban quản lý cần phân tích nội dung báo cáo hàng ngày của các ASM gửi lên FPT Chat: lọc shop theo hiệu suất cọc, thu thập ý tưởng triển khai, tổng hợp điểm nổi bật, và theo dõi ASM nào chưa báo cáo đúng giờ.

## What Changes
- **ADDED**: Phân tích cú pháp báo cáo ASM từ tin nhắn chat (regex-based extraction)
- **ADDED**: Lọc shop theo ngưỡng cọc — danh sách `cọc < 2` (cảnh báo) và `cọc > 5` (hiệu suất tốt)
- **ADDED**: Thu thập ý tưởng/hành động mới từ mục "Đã làm" trong báo cáo ASM
- **ADDED**: Tổng hợp điểm nổi bật — tích cực và hạn chế từ toàn bộ báo cáo trong ngày
- **ADDED**: Danh sách ASM chưa báo cáo sau 20:00 hàng ngày (so với danh sách kỳ vọng trong config)
- **ADDED**: CLI flag `--asm-report` để kích hoạt chế độ phân tích báo cáo ASM

## Impact
- Affected specs: `fpt-chat-stats` (minor — new CLI flag), new capability `asm-report-analysis`
- Affected code: `fpt_chat_stats.py` (new parsing + reporting functions), `config.json` schema (new key `asm_reporters`)
- No breaking changes to existing flags or output formats

## Interpretation Notes
- "Lọc danh sách shop có số lượng cọc <2 và >5": hiểu là **hai danh sách riêng biệt** trong báo cáo — shops có `cọc < 2` (hiệu suất thấp, cần chú ý) và shops có `cọc > 5` (hiệu suất tốt).
- "Ý tưởng mới từ ASM": lấy từ mục "Đã làm" của mỗi báo cáo — nội dung hành động/triển khai cụ thể mà ASM ghi nhận.
- "ASM chưa báo cáo": so sánh tên người gửi với danh sách `asm_reporters` trong config. Nếu không có config, tool cảnh báo và bỏ qua tính năng này.
