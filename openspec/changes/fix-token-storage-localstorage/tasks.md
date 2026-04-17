## 1. Thay cookie bằng localStorage
- [x] 1.1 Bỏ `extra-streamlit-components`, thêm `streamlit-javascript` vào requirements.txt
- [x] 1.2 Viết `_ls_get(key)` và `_ls_set(key, value)` dùng `st_javascript`
- [x] 1.3 Đọc token/group từ localStorage khi load form
- [x] 1.4 Ghi token/group vào localStorage sau khi nhấn Chạy

## 2. Đảm bảo token không ghi file
- [x] 2.1 `_load_config()` tự xoá key `token` nếu còn trong config.json
- [x] 2.2 `_save_group_local()` chỉ nhận `group`, không có tham số token
- [x] 2.3 Xoá token khỏi config.json hiện có trên máy

## 3. Validation
- [x] 3.1 Syntax check pass
- [ ] 3.2 Mở app, xác nhận form đọc được giá trị đã lưu từ localStorage
- [ ] 3.3 Kiểm tra Network tab: token không xuất hiện trong request headers
