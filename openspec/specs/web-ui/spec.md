# web-ui Specification

## Purpose
TBD - created by archiving change persist-advanced-options. Update Purpose after archive.
## Requirements
### Requirement: Wide Page Layout
The web UI SHALL use `layout="wide"` in `st.set_page_config` to maximise horizontal space on wide monitors.

#### Scenario: Wide layout rendered
- **WHEN** the user opens the app on a wide monitor
- **THEN** content spans the full browser width instead of being constrained to a centred column

---

### Requirement: Group Library Table UI
The web UI SHALL render the Group Library as an editable table using `st.data_editor` with `num_rows="dynamic"`. The table SHALL have the following columns: Chọn (bool), Tên nhóm (str), Group ID/URL (str), Cọc thấp (int), Cọc cao (int), Deadline (str), Bỏ qua (str).

Users add groups by filling in the empty row at the bottom of the table; users delete groups by selecting the row checkbox and pressing the delete key or the trash icon. There is no separate add/edit form or dedicated ✏/🗑 buttons.

After each render the app SHALL compare the returned DataFrame with the current session state. If there are differences it SHALL update `st.session_state.library` and write the updated library to `localStorage["fpt_groups_library"]`.

#### Scenario: Library rendered as table
- **WHEN** the library contains two entries
- **THEN** two rows appear in the `st.data_editor` table with all columns populated

#### Scenario: Add group via table
- **WHEN** the user fills in the empty bottom row and clicks away
- **THEN** a new library entry appears and is persisted to localStorage

#### Scenario: Delete group via table
- **WHEN** the user selects a row and deletes it via the table UI
- **THEN** the entry is removed from the library and localStorage is updated

#### Scenario: Edit group via table
- **WHEN** the user double-clicks a cell, changes the value, and confirms
- **THEN** the library entry is updated and localStorage is updated

### Requirement: Per-Group Advanced Config Storage
The web UI SHALL store advanced options (`deposit_low`, `deposit_high`, `deadline`, `skip`) for each group as part of the Group Library entry under `fpt_groups_library` in localStorage. Config is no longer stored separately in `fpt_group_configs`.

Advanced options are set per group directly in the table row.

Global hardcoded defaults apply when a new group is created without explicit values: `deposit_low=2`, `deposit_high=5`, `deadline="20:00"`, `skip=""`.

#### Scenario: Config saved when group is added
- **WHEN** the user adds a row with deadline="19:00" and clicks away
- **THEN** `fpt_groups_library[n].config.deadline` is `"19:00"`

#### Scenario: Config updated when group is edited
- **WHEN** the user edits group A's deposit_low from 2 to 3 in the table
- **THEN** `fpt_groups_library[n].config.deposit_low` is `3` and other groups are unchanged

#### Scenario: Default config for new group
- **WHEN** the user adds a group without changing the config fields
- **THEN** the entry is created with deposit_low=2, deposit_high=5, deadline="20:00", skip=""

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

