## 1. Session state & library helpers (app.py)
- [x] 1.1 Định nghĩa hằng `_LIB_KEY = "fpt_groups_library"` và `_LIB_DEFAULTS = {"deposit_low": 2, "deposit_high": 5, "deadline": "20:00", "skip": ""}`
- [x] 1.2 Viết `_migrate_legacy(groups_list, group_configs) -> list[dict]`: tạo library entries từ `fpt_groups` + `fpt_group_configs`
- [x] 1.3 Viết `_lib_to_json(lib) -> str` và `_json_to_lib(s) -> list[dict]` (parse/serialize)
- [x] 1.4 Khởi tạo session_state: `library`, `editing_idx` (None), `adding` (False), `ls_loaded` (False)
- [x] 1.5 Trong đầu script: nếu `ls_loaded=False` → đọc `fpt_groups_library` từ localStorage → migrate nếu cần → ghi vào `session_state.library`, set `ls_loaded=True`

## 2. UI: Danh sách nhóm
- [x] 2.1 Hiển thị header "📋 Nhóm chat" + nút "+ Thêm nhóm" (set `session_state.adding=True`, `editing_idx=None`)
- [x] 2.2 Render từng row: checkbox (`selected`), label + short ID, tóm tắt config (cọc thấp/cao, deadline), nút ✏ (set `editing_idx=i`, `adding=False`), nút 🗑 (xóa entry + ghi localStorage)
- [x] 2.3 Thay đổi checkbox → cập nhật `session_state.library[i].selected` + ghi localStorage
- [x] 2.4 Hiển thị "Chưa có nhóm nào. Nhấn + Thêm nhóm để bắt đầu." khi library rỗng

## 3. UI: Form thêm/sửa nhóm
- [x] 3.1 Form (hiện sau list khi `adding=True` hoặc `editing_idx` không None): fields URL/ID, Tên hiển thị, Cọc thấp, Cọc cao, Deadline, Bỏ qua
- [x] 3.2 Nút "Lưu": validate URL không rỗng → thêm/cập nhật entry → ghi localStorage → reset `adding=False, editing_idx=None`
- [x] 3.3 Nút "Huỷ": reset `adding=False, editing_idx=None` (không lưu)
- [x] 3.4 Form sửa pre-fill từ `session_state.library[editing_idx]`

## 4. Xóa global expander "Tuỳ chọn nâng cao"
- [x] 4.1 Xóa `with st.expander("⚙️ Tuỳ chọn nâng cao")` và các widget bên trong
- [x] 4.2 Xóa `_first_group_cfg`, `_CFG_DEFAULTS`, `_get_group_cfg`, `expander_config` trong run block
- [x] 4.3 Xóa logic đọc `fpt_group_configs` từ localStorage riêng

## 5. Cập nhật run logic
- [x] 5.1 Lấy `selected_groups = [e for e in session_state.library if e["selected"]]`; hiện lỗi nếu rỗng
- [x] 5.2 Mỗi group lấy config từ `entry["config"]` thay vì `_get_group_cfg`
- [x] 5.3 Bỏ lưu `fpt_group_configs` trong localStorage sau khi chạy (không còn cần)
- [x] 5.4 Bỏ `expander_config` fallback

## 6. Xóa expander "Cấu hình đã dùng" trong tabs kết quả
- [x] 6.1 Xóa `with st.expander("⚙️ Cấu hình đã dùng")` trong hàm `_render_result`

## 7. Validation
- [x] 7.1 Syntax check: `python3 -c "import ast; ast.parse(open('app.py').read())"`
- [x] 7.2 Kiểm thử thủ công: thêm 2 nhóm với config khác nhau → reload → library hiện đúng
- [x] 7.3 Kiểm thử thủ công: sửa config nhóm A → chạy → nhóm A dùng config mới
- [x] 7.4 Kiểm thử thủ công: bỏ chọn nhóm B → chạy → chỉ nhóm A được phân tích
- [x] 7.5 Kiểm thử migrate: có `fpt_groups` + `fpt_group_configs` trong localStorage → library được tạo đúng
