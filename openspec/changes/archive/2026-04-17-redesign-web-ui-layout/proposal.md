# Change: Redesign Web UI Layout

## Why
Sidebar hiện tại chứa quá nhiều controls (token, group, date, 4 advanced options) khiến phải cuộn dài. Layout chia đôi sidebar/content lãng phí không gian khi phần content bên phải hầu như trống trước khi chạy phân tích.

## What Changes

### Bỏ sidebar
- Toàn bộ input chuyển vào main area, layout `wide` → `centered`
- Không còn sidebar

### Layout mới — single-page, 3 vùng dọc

**Vùng 1 — Kết nối** (luôn hiển thị):
- Token và Group ID trên cùng một hàng (2 cột)

**Vùng 2 — Thời gian** (luôn hiển thị):
- Radio button: `Hôm nay` / `Chọn khoảng ngày`
- Nếu chọn khoảng ngày: 2 date picker hiện ra inline

**Vùng 3 — Tuỳ chọn nâng cao** (`st.expander`, mặc định đóng):
- Deposit low/high, deadline, skip reporters

**Nút chạy** ngay bên dưới vùng 2/3.

## Impact
- Chỉ ảnh hưởng `app.py` — không thay đổi logic, không thay đổi spec
- Không breaking change với người dùng
