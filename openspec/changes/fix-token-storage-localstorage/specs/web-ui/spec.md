## MODIFIED Requirements

### Requirement: Web UI Token Storage
Token xác thực SHALL được lưu vào **browser localStorage** của từng user — không ghi vào bất kỳ file nào trên server.

- Key: `fpt_token` trong localStorage
- Không hết hạn (tồn tại đến khi user xoá dữ liệu browser)
- Không gửi lên server theo HTTP request

#### Scenario: Lưu token sau khi chạy
- **WHEN** user nhấn Chạy phân tích với token hợp lệ
- **THEN** token được ghi vào `localStorage["fpt_token"]` trong browser của user đó

#### Scenario: Đọc token khi mở app
- **WHEN** user mở lại app trên cùng browser
- **THEN** token được đọc từ localStorage và điền sẵn vào form

#### Scenario: Nhiều user dùng cùng app
- **WHEN** user A và user B cùng dùng app trên cloud
- **THEN** mỗi người thấy token của chính mình — không chia sẻ token giữa các user

### Requirement: Web UI Group ID Storage
Group ID SHALL được lưu vào **browser localStorage** (`fpt_group`). Khi chạy local, cũng đồng bộ vào `config.json` làm fallback cho CLI.

Token SHALL KHÔNG được ghi vào `config.json` trong bất kỳ trường hợp nào.

#### Scenario: config.json có token cũ
- **WHEN** `config.json` tồn tại với key `token` từ phiên bản cũ
- **THEN** key `token` bị xoá khi app khởi động
