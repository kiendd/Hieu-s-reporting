# Change: Persist Advanced Options in localStorage

## Why
Phần "Tuỳ chọn nâng cao" (ngưỡng cọc, deadline, danh sách bỏ qua) hiện tại reset về giá trị mặc định mỗi lần tải lại trang. Người dùng phải nhập lại mỗi phiên, gây bất tiện.

## What Changes
- Đọc 4 giá trị từ localStorage khi mở app: `fpt_deposit_low`, `fpt_deposit_high`, `fpt_deadline`, `fpt_skip`
- Ghi 4 giá trị vào localStorage khi nhấn "Chạy phân tích"
- Giá trị mặc định dùng khi localStorage chưa có: `2`, `5`, `"20:00"`, `""`

## Impact
- Affected specs: `web-ui` (ADDED requirement — lưu tuỳ chọn nâng cao)
- Affected code: `app.py` — thêm `_ls_get`/`_ls_set` cho 4 key mới
- Không breaking
