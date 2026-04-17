## MODIFIED Requirements

### Requirement: Web UI Layout
The web UI SHALL use a single-column layout (no sidebar) with inputs grouped in three vertical sections:

1. **Kết nối**: Token (password field) và Group ID trên cùng một hàng
2. **Thời gian**: Radio chọn `Hôm nay` hoặc `Chọn khoảng ngày`; date pickers chỉ hiển thị khi chọn `Chọn khoảng ngày`
3. **Tuỳ chọn nâng cao**: `st.expander` mặc định đóng, chứa deposit-low/high, deadline, skip-reporters

Nút **Chạy phân tích** đặt ngay sau phần tuỳ chọn.

#### Scenario: Default state
- **WHEN** user mở app lần đầu
- **THEN** hiển thị Token input, Group ID input, radio "Hôm nay" được chọn, expander đóng, nút Chạy

#### Scenario: Custom date range
- **WHEN** user chọn "Chọn khoảng ngày"
- **THEN** hai date picker From/To xuất hiện inline ngay bên dưới radio

#### Scenario: Advanced options
- **WHEN** user click vào expander "Tuỳ chọn nâng cao"
- **THEN** deposit-low, deposit-high, deadline, skip-reporters hiển thị trong expander
