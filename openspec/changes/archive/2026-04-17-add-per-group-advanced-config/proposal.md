# Change: Per-Group Advanced Config

## Why
Các nhóm chat khác nhau có thể có quy tắc compliance khác nhau (deadline khác giờ, người bỏ qua khác nhau, ngưỡng cọc khác nhau). Hiện tại tuỳ chọn nâng cao chỉ là một bộ settings toàn cục — mỗi lần đổi nhóm phải chỉnh lại thủ công.

## What Changes
- Lưu 4 advanced options (`deposit_low`, `deposit_high`, `deadline`, `skip`) theo từng group ID trong localStorage dưới key `fpt_group_configs` (JSON object)
- **Single group:** expander pre-fill từ config đã lưu của nhóm đó; lưu lại khi chạy
- **Multi-group (phụ thuộc `add-multi-group-support`):** mỗi nhóm chạy với config riêng của nó; expander hiển thị config của nhóm đầu tiên làm starting point cho nhóm chưa có config
- Thay thế/hợp nhất `persist-advanced-options` (cùng mục tiêu nhưng cách lưu tổng quát hơn)

## Impact
- Affected specs: `web-ui` (ADDED requirement — per-group config storage)
- Affected code: `app.py` — thay 4 flat `_ls_get`/`_ls_set` bằng một JSON object keyed by group ID
- Dependency: `add-multi-group-support` (multi-group behavior cần có tabs để hoạt động đúng)
- Supersedes: `persist-advanced-options` — nên rút proposal đó lại sau khi proposal này được duyệt
- Không breaking với user: lần đầu mở app vẫn hiện default, config cũ chưa có → dùng default
