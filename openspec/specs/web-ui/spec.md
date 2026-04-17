# web-ui Specification

## Purpose
TBD - created by archiving change persist-advanced-options. Update Purpose after archive.
## Requirements
### Requirement: Web UI Advanced Options Persistence
The web UI SHALL persist the four advanced-options fields in browser localStorage and restore them on page load.

localStorage keys and defaults:

| Key                | Widget                        | Default  |
|--------------------|-------------------------------|----------|
| `fpt_deposit_low`  | Ngưỡng cọc thấp (<)           | `2`      |
| `fpt_deposit_high` | Ngưỡng cọc cao (>)            | `5`      |
| `fpt_deadline`     | Deadline (giờ VN)             | `20:00`  |
| `fpt_skip`         | Bỏ qua khỏi compliance check  | `""`     |

Values SHALL be written to localStorage when the user clicks "Chạy phân tích". Values SHALL be read and pre-filled into the widgets on page load.

#### Scenario: Restore non-default values on reload
- **WHEN** the user previously set deposit_low=3, deposit_high=8, deadline="18:00", skip="Giám đốc" and reloads the page
- **THEN** all four widgets show those saved values instead of the defaults

#### Scenario: Save on run
- **WHEN** the user changes deadline to "19:30" and clicks "Chạy phân tích"
- **THEN** `localStorage["fpt_deadline"]` is set to `"19:30"`

#### Scenario: Default when localStorage empty
- **WHEN** the user opens the app for the first time with no stored values
- **THEN** deposit_low=2, deposit_high=5, deadline="20:00", skip="" (unchanged from current behaviour)

### Requirement: Per-Group Advanced Config Storage
The web UI SHALL store advanced options (`deposit_low`, `deposit_high`, `deadline`, `skip`) independently per group ID in browser localStorage under the key `fpt_group_configs` as a JSON object mapping group hex IDs to their config objects.

Global hardcoded defaults apply when a group has no stored config: `deposit_low=2`, `deposit_high=5`, `deadline="20:00"`, `skip=""`.

#### Scenario: Config saved on single-group run
- **WHEN** only one group is entered and the user sets deadline="19:00" and clicks "Chạy phân tích"
- **THEN** `localStorage["fpt_group_configs"]["<group_id>"]["deadline"]` is set to `"19:00"`

#### Scenario: Config saved on multi-group run — only new groups updated
- **WHEN** group A already has a saved config and group B does not; user runs both
- **THEN** group B's config is saved from the current expander values; group A's existing config is preserved unchanged

#### Scenario: Config not found — hardcoded defaults used
- **WHEN** a group has no entry in `fpt_group_configs`
- **THEN** the expander shows deposit_low=2, deposit_high=5, deadline="20:00", skip="" for that group

---

### Requirement: Per-Group Advanced Config Restore
On page load, the web UI SHALL pre-fill the advanced options expander with the stored config of the first group listed in the group text area. If the first group has no stored config, hardcoded defaults are used.

#### Scenario: Single group with saved config
- **WHEN** the group text area has one entry with group ID `686b517a...` and that group's config has `deadline="18:30"`
- **THEN** the deadline widget shows `"18:30"` when the expander is opened

#### Scenario: Multiple groups — first group's config shown
- **WHEN** the text area has three groups; the first group has `deposit_low=3` saved
- **THEN** the expander pre-fills with `deposit_low=3` (first group's config)

#### Scenario: No group entered yet
- **WHEN** the text area is empty on page load
- **THEN** expander shows hardcoded defaults

---

### Requirement: Per-Group Config Summary in Results
Each result tab SHALL display a collapsed read-only summary of the advanced config that was used for that group's analysis (deposit thresholds, deadline, skip list).

#### Scenario: Tab shows correct config
- **WHEN** group A was run with `deadline="19:00"` and group B with `deadline="20:00"`
- **THEN** tab A's summary shows `deadline: 19:00` and tab B's summary shows `deadline: 20:00`

#### Scenario: Single group result
- **WHEN** only one group is analyzed
- **THEN** its result area shows the config used in the same collapsed summary format

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

