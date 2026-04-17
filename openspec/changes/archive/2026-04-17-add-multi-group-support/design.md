## Context
Web UI hiện tại (`app.py`) nhận một `group` text input duy nhất. Token dùng chung cho mọi request. Kết quả hiển thị thẳng trên trang, không phân tab.

Streamlit không có widget "dynamic list of inputs" built-in, nhưng có thể mô phỏng bằng `st.session_state` + nút thêm/xóa.

## Goals / Non-Goals
- Goals:
  - Cho phép nhập N nhóm trước khi chạy
  - Hiển thị kết quả N tab sau khi chạy
  - Mỗi tab có nút Download Excel riêng
  - Persist danh sách nhóm qua localStorage
- Non-Goals:
  - Chạy song song (fetch tuần tự để đơn giản, tránh rate limit)
  - Đặt tên tuỳ chỉnh cho từng nhóm (dùng Group ID làm label)

## Decisions

### Nhập nhóm: text_area "một nhóm một dòng" vs dynamic list
- **Chọn: text_area với một nhóm/dòng** — đơn giản hơn, không cần session_state phức tạp; người dùng dán URL/ID thẳng vào
- Alternatives: dynamic add/remove buttons — UX tốt hơn nhưng phức tạp hơn đáng kể; để dành cho iteration sau nếu được yêu cầu

### Label cho tab
- **Ưu tiên 1 — custom label trong text area:** user có thể thêm ` | Tên tuỳ chỉnh` sau group ID/URL. Ví dụ: `686b517a54ca42cb3c30e1df | Nhóm miền Bắc`
- **Ưu tiên 2 — tên nhóm từ API:** gọi `GET /group-management/group/{group_id}`, lấy trường `name` (hoặc `title`) nếu endpoint tồn tại
- **Fallback — Short ID:** 8 ký tự cuối của hex group ID. Ví dụ `3c30e1df`
- Thêm hàm `fetch_group_info(session, base_url, group_id) -> dict` vào `fpt_chat_stats.py`; trả về `{}` nếu endpoint trả non-2xx hoặc exception

### localStorage key
- Đổi `fpt_group` (string) → `fpt_groups` (JSON array string) để backward-compatible với browser cũ không cần xóa
- Khi đọc: nếu `fpt_groups` chưa có, thử đọc `fpt_group` cũ làm fallback

### config.json
- Thêm key `groups` (list); giữ đọc `group` (string) làm fallback khi `groups` chưa có

## Risks / Trade-offs
- Fetch tuần tự: N nhóm mất N × thời gian — chấp nhận được cho số nhóm nhỏ (<10)
- Nếu một nhóm lỗi, các nhóm khác vẫn hiển thị (lỗi hiện trong tab tương ứng)

## Open Questions
- (Đã giải quyết) Tên tab = custom label nếu có, rồi tên từ API, rồi short ID.
