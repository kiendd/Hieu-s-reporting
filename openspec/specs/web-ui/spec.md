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

### Requirement: Group Library Dialog UI
The web UI SHALL render the Group Library as a read-only display list. Each row shows a checkbox (`selected`), the group label and short ID, a config summary, an ✏ edit button, and a 🗑 delete button. A `+ Thêm nhóm` button appears above the list.

The `selected` checkbox SHALL remain editable inline (no dialog needed for toggling). All other fields SHALL only be editable through a modal dialog.

Clicking `+ Thêm nhóm` or an ✏ button SHALL open a `@st.dialog` modal containing fields: Group ID/URL, display label, Cọc thấp, Cọc cao, Deadline, Bỏ qua. The dialog has "Lưu" and "Huỷ" buttons; submitting saves the entry and closes the dialog.

After any change (checkbox toggle, save from dialog, delete) the app SHALL update `st.session_state.library` and write to `localStorage["fpt_groups_library"]`.

#### Scenario: List rendered on load
- **WHEN** the library contains two entries
- **THEN** two rows appear, each showing label, short ID, config summary, ✏ and 🗑 buttons

#### Scenario: Add group via dialog
- **WHEN** the user clicks `+ Thêm nhóm`, fills the form, and clicks "Lưu"
- **THEN** the dialog closes, a new entry appears in the list, and the library is persisted to localStorage

#### Scenario: Edit group via dialog
- **WHEN** the user clicks ✏ on a row, changes the deadline, and clicks "Lưu"
- **THEN** the dialog closes and that entry's deadline is updated in the list and localStorage

#### Scenario: Cancel closes dialog without saving
- **WHEN** the user clicks ✏, changes a value, then clicks "Huỷ" or the X button
- **THEN** the dialog closes and the entry is unchanged

#### Scenario: Delete group
- **WHEN** the user clicks 🗑 on a row
- **THEN** the entry is removed immediately (no dialog) and localStorage is updated

#### Scenario: Toggle selection inline
- **WHEN** the user checks or unchecks the checkbox on a row
- **THEN** the `selected` flag updates immediately without opening a dialog

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

### Requirement: Help Documentation Link
The web UI SHALL display a "📖 Hướng dẫn sử dụng" hyperlink in the page header, on the same row as the app title, linking to the project documentation page on GitHub.

#### Scenario: Link visible on load
- **WHEN** the user opens the app
- **THEN** a "📖 Hướng dẫn sử dụng" link is visible next to the page title and opens the docs URL when clicked

### Requirement: Weekly Report UI Surface
`app.py` SHALL expose a user-visible section labelled `Báo cáo tuần` alongside the existing daily / multi-day report surfaces. The section SHALL provide:
- A single `st.date_input` control for the target VN-time date.
- A Run button that triggers the weekly pipeline.

The deadline value used for the pipeline SHALL come from the currently selected group's library entry (same source as the daily deadline). The weekly section SHALL NOT introduce a new persistent setting for the deadline; it reuses the per-group `deadline` already stored in `_LIB_KEY`.

When the user clicks Run, the app SHALL:
1. Fetch messages for the target VN day using the existing session/auth flow.
2. Fetch group members.
3. Call `analyze_weekly` from `fpt_chat_stats`.
4. Render the following sections in order, using Vietnamese labels:
   - A summary row with three counters: `Đã báo cáo`, `Muộn`, `Chưa báo cáo`.
   - A `Chưa báo cáo` list (names only).
   - A `Muộn` list (name + VN send time).
   - A `Nội dung` table with columns `Người báo cáo`, `Giờ gửi`, `Trạng thái`, `Nội dung`. The `Nội dung` column SHALL display full raw text (wrap or scroll, never truncate).
5. Provide a download button that serves the weekly Excel output via `st.download_button`, using `write_weekly_excel` against an in-memory buffer.

#### Scenario: Weekly section does not affect daily flow
- **WHEN** the user runs the existing daily or multi-day report
- **THEN** the weekly section is not evaluated and does not alter the daily output in any way

#### Scenario: No reports on target day
- **GIVEN** zero qualifying messages were sent on the target VN day
- **WHEN** the user clicks Run
- **THEN** the summary shows `Đã báo cáo: 0`, `Chưa báo cáo` lists every group member, `Muộn` is empty, and the `Nội dung` table is empty (still rendered with headers)

