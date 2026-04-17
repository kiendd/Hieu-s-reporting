## 1. Refactor app.py layout
- [x] 1.1 Đổi `layout="centered"` (giữ nguyên)
- [x] 1.2 Xoá `with st.sidebar` block
- [x] 1.3 Tạo vùng Kết nối: Token + Group ID trên 2 cột (`st.columns`)
- [x] 1.4 Tạo vùng Thời gian: radio `Hôm nay` / `Chọn khoảng ngày` + date picker inline
- [x] 1.5 Bọc advanced options vào `st.expander("⚙️ Tuỳ chọn nâng cao", expanded=False)`
- [x] 1.6 Đặt nút "Chạy phân tích" ngay sau expander

## 2. Validation
- [x] 2.1 Syntax check pass
- [x] 2.2 App khởi động thành công (HTTP 200)
- [x] 2.3 Date picker chỉ render khi chọn "Chọn khoảng ngày" (conditional block)
- [x] 2.4 Logic fetch/analyze không thay đổi — chỉ layout được refactor
