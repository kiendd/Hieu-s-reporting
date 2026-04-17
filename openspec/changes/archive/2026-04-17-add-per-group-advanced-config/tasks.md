## 1. Đọc fpt_group_configs từ localStorage
- [x] 1.1 Thêm `_ls_get("fpt_group_configs")` vào khối đọc localStorage đầu trang; parse JSON → dict (default `{}` nếu lỗi)
- [x] 1.2 Lấy group ID đầu tiên từ text area (nếu có) để tra cứu config
- [x] 1.3 Pre-fill expander bằng config của nhóm đầu tiên (fallback hardcoded defaults cho field nào thiếu)

## 2. Ghi fpt_group_configs khi chạy
- [x] 2.1 Khi single-group: lưu đè config từ expander vào `fpt_group_configs[group_id]`
- [x] 2.2 Khi multi-group: với mỗi nhóm CHƯA có config → lưu giá trị expander; nhóm đã có config → giữ nguyên

## 3. Chạy mỗi nhóm với config riêng
- [x] 3.1 Trong `_run_for_group`: đọc config của group_id từ `fpt_group_configs`; fallback về giá trị expander; dùng các giá trị đó cho `deposit_low`, `deposit_high`, `deadline`, `skip_list`
- [x] 3.2 Trả thêm `config_used` trong kết quả của `_run_for_group` (để hiển thị trong tab)

## 4. Config summary trong tab kết quả
- [x] 4.1 Trong mỗi tab kết quả: thêm `st.expander("⚙️ Cấu hình đã dùng", expanded=False)` hiển thị 4 giá trị dạng read-only

## 5. Rút proposal persist-advanced-options
- [x] 5.1 Xác nhận với user rằng `persist-advanced-options` được supersede bởi proposal này trước khi archive

## 6. Validation
- [x] 6.1 Kiểm thử: nhập group A → chạy với deadline "19:00" → reload → expander hiện "19:00"
- [x] 6.2 Kiểm thử: nhập group A + group B → chạy → tab A hiện config A, tab B hiện config B
- [x] 6.3 Kiểm thử: group A đã có config, group B chưa → chạy multi → config A giữ nguyên, config B lưu từ expander
- [x] 6.4 Kiểm thử: lần đầu mở app → expander hiện defaults (2, 5, "20:00", "")
