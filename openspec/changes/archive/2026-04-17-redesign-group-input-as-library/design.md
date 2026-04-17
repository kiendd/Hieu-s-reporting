## Context
Streamlit re-renders toàn bộ script mỗi lần có interaction. Để quản lý danh sách nhóm có thể add/edit/delete, cần dùng `st.session_state` để lưu trạng thái qua các lần rerun.

Vấn đề cốt lõi của text area: người dùng không thể thấy hoặc chỉnh config (deposit thresholds, deadline, skip) của từng nhóm trước khi chạy — và không có cách nào để làm điều đó mà không chạy từng nhóm riêng lẻ trước.

## Goals / Non-Goals
- Goals: thấy và chỉnh config của từng nhóm trước khi chạy; chọn/bỏ chọn nhóm để chạy theo lô
- Non-Goals: sorting/reordering library; import/export library; chia sẻ library giữa users

## Storage Schema

```json
// localStorage["fpt_groups_library"]
[
  {
    "url": "686b517a54ca42cb3c30e1df",
    "label": "Nhóm miền Bắc",
    "selected": true,
    "config": {
      "deposit_low": 2,
      "deposit_high": 5,
      "deadline": "20:00",
      "skip": ""
    }
  }
]
```

Gộp `fpt_groups` và `fpt_group_configs` thành một key duy nhất. "selected" lưu lại trạng thái checkbox qua page reload.

## Session State Design

```
st.session_state.library        # list[dict] — bản sao từ localStorage
st.session_state.editing_idx    # int | None — index đang chỉnh, None = không chỉnh
st.session_state.adding         # bool — đang hiện form thêm nhóm
st.session_state.ls_loaded      # bool — đã load localStorage vào session_state chưa
```

Vì `_ls_get` dùng `st_javascript` (async, trả giá trị sau 1 rerun), cần pattern:
1. Lần đầu: đọc localStorage → lưu vào `session_state.library`, set `ls_loaded = True`
2. Các lần sau: dùng `session_state.library` trực tiếp, không đọc lại localStorage

Mỗi khi library thay đổi → ghi ngay vào localStorage qua `_ls_set`.

## UI Layout

```
Token: [...]

📋 Nhóm chat                              [+ Thêm nhóm]
─────────────────────────────────────────────────────────
[✓]  Nhóm miền Bắc    686b517a...  cọc 2-5  20:00   [✏] [🗑]
[✓]  Nhóm miền Nam    abc12345...  cọc 1-4  19:00   [✏] [🗑]
[ ]  Nhóm miền Trung  def67890...  cọc 2-5  20:00   [✏] [🗑]
─────────────────────────────────────────────────────────
     (form edit/add hiện tại đây khi click ✏ hoặc + Thêm)

Khoảng thời gian: [●Hôm nay] [○Chọn khoảng ngày]

[▶ Chạy 2 nhóm đã chọn]
```

## Decisions

### Inline edit form vs modal
- **Chọn: inline (dưới row hoặc dưới toàn bộ list)** — Streamlit không có modal native; dialog thêm phức tạp với `st.dialog`. Form hiện sau list là đủ.
- Alternatives: `st.popover` (Streamlit 1.31+, cần kiểm tra version) — có thể dùng nếu available

### Edit form placement
- Form add/edit hiện **sau list**, không phải sau từng row — đơn giản hơn, tránh layout shift khi list dài

### Checkbox selection persistence
- `selected` lưu trong library object → persist qua reload
- "Chạy phân tích" chỉ chạy các entry có `selected=True`

### Migration từ schema cũ
- Khi load: nếu `fpt_groups_library` vắng mặt nhưng `fpt_groups` có → tạo library từ `fpt_groups` strings + `fpt_group_configs`
- Label mặc định khi migrate: dùng 8 ký tự cuối group ID
- Sau migrate: ghi `fpt_groups_library`, không xóa key cũ (tránh mất data nếu user dùng version cũ)

## Risks / Trade-offs
- Session state complexity: cần init cẩn thận để không đọc localStorage nhiều lần (vì `st_javascript` là async, trả giá trị delay 1 rerun)
- UX: người dùng quen text area phải học UI mới — mitigated bởi form rõ ràng hơn
