# Change: Redesign Group Input as Selectable Library

## Why
Text area "một dòng/nhóm" không cho phép người dùng xem hoặc chỉnh advanced settings của từng nhóm trước khi chạy. Muốn đổi config cho nhóm B thì phải chạy đơn lẻ, rồi thêm lại — không trực quan.

## What Changes
- **REPLACED** text area + global expander bằng mô hình "Group Library": danh sách nhóm đã lưu, mỗi nhóm có checkbox chọn, nút sửa/xóa, và form cấu hình inline
- **ADDED** form "Thêm nhóm" / "Sửa nhóm" với đầy đủ label, URL/ID, và 4 advanced settings
- **REMOVED** global "Tuỳ chọn nâng cao" expander — settings nay nằm trong từng entry của library
- **MODIFIED** localStorage key: `fpt_groups` (string array) + `fpt_group_configs` (object keyed by ID) → `fpt_groups_library` (array of objects, mỗi object có url, label, selected, config)
- **ADDED** migration tự động từ `fpt_groups`/`fpt_group_configs` sang schema mới khi load lần đầu
- **BREAKING**: `fpt_groups` và `fpt_group_configs` không còn được ghi — chỉ đọc để migrate

## Impact
- Affected specs: `multi-group-reporting` (MODIFIED: Multi-Group Input, Per-Group Tabbed Results, Multi-Group Persistence)
- Affected specs: `web-ui` (MODIFIED: Per-Group Advanced Config Storage/Restore, REMOVED: Web UI Advanced Options Persistence — global expander không còn)
- Affected code: `app.py` — toàn bộ phần input và state management
- Affected code: `fpt_chat_stats.py` — không thay đổi
