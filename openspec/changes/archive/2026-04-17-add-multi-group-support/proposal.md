# Change: Add Multi-Group Support

## Why
Người dùng cần theo dõi nhiều nhóm chat FPT Chat cùng lúc (ví dụ: nhiều tỉnh thành, nhiều vùng), mỗi nhóm có báo cáo ASM độc lập. Hiện tại web UI chỉ hỗ trợ một nhóm mỗi lần chạy.

## What Changes
- **ADDED** UI cho phép nhập nhiều nhóm chat (danh sách có thể thêm/xóa từng dòng)
- **ADDED** khi chạy phân tích, mỗi nhóm được fetch & phân tích độc lập
- **ADDED** kết quả hiển thị dạng tab — mỗi tab tương ứng một nhóm
- **ADDED** mỗi tab có nút "Tải Excel" riêng, tên file mang tên nhóm và ngày
- **MODIFIED** lưu danh sách nhóm vào localStorage thay cho một nhóm duy nhất
- **MODIFIED** `config.json` lưu `groups` (list) thay cho `group` (string) khi chạy local

## Impact
- Affected specs: `fpt-chat-stats` (MODIFIED: group input, localStorage, config key)
- Affected specs: `multi-group-reporting` (ADDED — capability mới)
- Affected code: `app.py` — thay đổi toàn bộ phần input & kết quả
- **BREAKING**: key localStorage `fpt_group` → `fpt_groups` (JSON array); config key `group` → `groups`
