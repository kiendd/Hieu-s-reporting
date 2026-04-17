## 1. Input UI
- [x] 1.1 Thay `st.text_input` cho group bằng `st.text_area` (multi-line, placeholder "một nhóm/URL mỗi dòng; tuỳ chọn thêm | Tên tab")
- [x] 1.2 Parse mỗi dòng: tách phần trước và sau ` | ` để lấy `(group_str, custom_label_or_None)`; bỏ qua dòng trống
- [x] 1.3 Validate: hiện lỗi nếu list rỗng khi nhấn Chạy

## 2. localStorage & Config
- [x] 2.1 Đổi `_ls_get("fpt_group")` → đọc `fpt_groups` (JSON array); fallback `fpt_group` cũ
- [x] 2.2 Đổi `_ls_set("fpt_group", ...)` → ghi `fpt_groups` (JSON.stringify của array)
- [x] 2.3 Cập nhật `_load_config()` đọc `groups` (list); fallback `group` (string)
- [x] 2.4 Cập nhật `_save_group_local()` → lưu key `groups` (list) thay `group` (string)

## 3. fetch_group_info (fpt_chat_stats.py)
- [x] 3.1 Thêm hàm `fetch_group_info(session, base_url, group_id) -> dict` gọi `GET /group-management/group/{group_id}`; trả `{}` nếu lỗi

## 4. Fetch & Analyze Loop
- [x] 4.1 Tách toàn bộ logic fetch+analyze+excel hiện tại thành hàm `_run_for_group(group_str, ...)` trả về `(asm_data, excel_bytes, error_msg)`
- [x] 4.2 Trong `_run_for_group`: gọi `fetch_group_info` để lấy tên nhóm, lưu vào kết quả trả về
- [x] 4.3 Trong nút "Chạy phân tích": lặp qua list groups, gọi `_run_for_group` cho từng nhóm, thu thập kết quả

## 5. Tabbed Results
- [x] 5.1 Tính tab label: custom_label → group_info["name"] → short ID (8 ký tự cuối)
- [x] 5.2 Tạo `st.tabs([...labels...])` sau khi có kết quả tất cả nhóm
- [x] 5.3 Trong mỗi tab: hiển thị metrics, dataframes, và nút Download Excel riêng
- [x] 5.4 Nếu nhóm lỗi: tab hiện `st.error(error_msg)` thay vì kết quả

## 6. Excel per group
- [x] 6.1 Tên file: `asm_report_<group_short>_<date>.xlsx`
- [x] 6.2 Mỗi tab có `st.download_button` riêng trỏ đến buffer Excel của nhóm đó

## 7. Validation
- [x] 7.1 Kiểm thử thủ công: nhập 1 nhóm → kết quả như cũ
- [x] 7.2 Kiểm thử thủ công: nhập 2 nhóm (không có label) → tab dùng tên từ API hoặc short ID
- [x] 7.3 Kiểm thử thủ công: nhập `group_id | Nhóm A` → tab label là `Nhóm A`
- [x] 7.4 Kiểm thử thủ công: nhóm lỗi (ID sai) → tab lỗi không làm sập tab còn lại
- [x] 7.5 Reload trang → text area khôi phục danh sách nhóm (kể cả custom label nếu có)
