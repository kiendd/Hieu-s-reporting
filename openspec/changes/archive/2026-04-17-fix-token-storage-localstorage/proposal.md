# Change: Fix Token Storage — Dùng localStorage thay cookie

## Why
Trước đây token được lưu vào `config.json` trên server — nguy hiểm vì mọi người dùng cloud đọc được token của nhau.

Đã sửa sang cookie, nhưng cookie vẫn bị gửi kèm mỗi HTTP request nên server có thể đọc được. localStorage an toàn hơn: chỉ JS trong browser đọc được, không bao giờ tự động gửi lên server.

## What Changes

### localStorage thay cookie
- Dùng `streamlit-javascript` để đọc/ghi localStorage của browser
- Token lưu tại `localStorage["fpt_token"]` — chỉ tồn tại trong browser của user đó
- Group ID lưu tại `localStorage["fpt_group"]` + `config.json` (local fallback cho CLI)
- Bỏ `extra-streamlit-components`

### Token không bao giờ ghi file
- `_load_config()` tự xoá key `token` nếu còn sót trong `config.json`
- `_save_group_local()` chỉ ghi group, không có tham số token

## Impact
- Chỉ ảnh hưởng `app.py` và `requirements.txt`
- Hành vi user không đổi: token/group vẫn được nhớ qua các lần mở app
