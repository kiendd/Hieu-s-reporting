# multi-group-reporting Specification

## Purpose
TBD - created by archiving change add-multi-group-support. Update Purpose after archive.
## Requirements
### Requirement: Multi-Group Input
The web UI SHALL manage groups through a **Group Library** — a persistent, ordered list of group entries. Each entry contains a URL/ID, a display label, a selected flag, and a per-group advanced config.

The library is rendered as a list of rows. Each row shows:
- A checkbox to include/exclude the group from the next run
- The display label and a short form of the group ID
- A summary of the group's config (deposit thresholds and deadline)
- An edit button (✏) and a delete button (🗑)

An "Add group" button above the list opens an inline form to create a new entry. The edit button opens the same form pre-filled with the entry's current data.

At least one group with `selected=True` MUST exist before analysis can start.

#### Scenario: Library shown on load
- **WHEN** the user opens the app and `fpt_groups_library` has two entries
- **THEN** two rows appear, each showing label, short ID, config summary, and action buttons

#### Scenario: Add new group
- **WHEN** the user clicks "+ Thêm nhóm", fills in the form (URL + label + config), and clicks "Lưu"
- **THEN** a new entry appears at the end of the list with the provided settings

#### Scenario: Edit existing group
- **WHEN** the user clicks ✏ on a row, changes the deadline, and clicks "Lưu"
- **THEN** that entry's deadline is updated and the list reflects the change

#### Scenario: Delete group
- **WHEN** the user clicks 🗑 on a row
- **THEN** that entry is removed from the library

#### Scenario: Select/deselect groups
- **WHEN** the user unchecks group B and clicks "Chạy phân tích"
- **THEN** only group A (checked) is analyzed; group B is skipped

#### Scenario: No group selected
- **WHEN** all checkboxes are unchecked and the user clicks "Chạy phân tích"
- **THEN** an error is shown and analysis does not start

---

### Requirement: Per-Group Tabbed Results
After analysis completes, the web UI SHALL display results in a `st.tabs` widget with one tab per analyzed group.

Tab label resolution order (highest priority first):
1. Custom label provided by the user (stored in the library entry, not a short-ID placeholder)
2. Group name fetched from the FPT Chat API (`fetch_group_info`)
3. Last 8 characters of the group hex ID (fallback)

When the API returns a name and the stored label is still the short-ID placeholder, the app SHALL write the API name back to `st.session_state.library` and persist it to localStorage. This enrichment is one-time: once a real name is stored the label is no longer a placeholder and will not be overwritten on subsequent runs.

#### Scenario: Two groups analyzed successfully
- **WHEN** two groups were analyzed and both succeeded
- **THEN** two tabs appear; each tab contains the full analysis result for its group

#### Scenario: One group succeeds, one fails
- **WHEN** group A fetches successfully but group B returns an API error
- **THEN** two tabs appear; tab A shows results normally; tab B shows an error message

#### Scenario: API name written back to library
- **WHEN** a group's label is the short-ID placeholder and `fetch_group_info` returns `{"name": "ASM Hà Nội"}`
- **THEN** `st.session_state.library[idx].label` is updated to `"ASM Hà Nội"` and persisted to localStorage

#### Scenario: Custom label not overwritten
- **WHEN** a group's label was manually set to `"Nhóm miền Bắc"` (not the short-ID placeholder)
- **THEN** the label remains `"Nhóm miền Bắc"` regardless of what the API returns

#### Scenario: Short ID fallback
- **WHEN** no custom label is given and `fetch_group_info` returns `{}` or fails
- **THEN** the tab label is the last 8 characters of the group ID and the library label is not changed

### Requirement: Group Info Fetching
The `fpt_chat_stats` module SHALL expose a `fetch_group_info(session, base_url, group_id) -> dict` function that calls `GET /group-management/group/{group_id}` and returns the response JSON. If the request fails (non-2xx or exception), the function SHALL return `{}` without raising.

#### Scenario: Successful response with name
- **WHEN** the API returns `{"name": "ASM Hà Nội", ...}`
- **THEN** `fetch_group_info` returns a dict containing at least `{"name": "ASM Hà Nội"}`

#### Scenario: API error or timeout
- **WHEN** the endpoint returns 404 or raises a connection error
- **THEN** `fetch_group_info` returns `{}` and does not propagate the exception

---

### Requirement: Per-Group Excel Download
Each result tab SHALL contain a download button for an Excel file scoped to that group only. The file name SHALL follow the pattern `asm_report_<group_short>_<date>.xlsx` where `<group_short>` is the last 8 characters of the group ID and `<date>` is the analysis date or end date of the date range.

#### Scenario: Download button per tab
- **WHEN** three groups are analyzed
- **THEN** three download buttons appear, one in each tab, each producing a distinct `.xlsx` file

#### Scenario: File name includes group identifier
- **WHEN** group ID is `686b517a54ca42cb3c30e1df` and date is `2026-04-17`
- **THEN** the downloaded file is named `asm_report_3c30e1df_2026-04-17.xlsx`

---

### Requirement: Multi-Group Persistence
The web UI SHALL persist the Group Library in browser localStorage under the key `fpt_groups_library` as a JSON-encoded array of objects. Each object contains: `url`, `label`, `selected`, and `config` (with keys `deposit_low`, `deposit_high`, `deadline`, `skip`).

The library SHALL be loaded into `st.session_state` on first page load. Subsequent reruns read from session state, not localStorage, to avoid async timing issues with `st_javascript`.

Any change to the library (add, edit, delete, select/deselect) SHALL immediately write the updated library to `localStorage["fpt_groups_library"]`.

When `fpt_groups_library` is absent, the UI SHALL migrate from the legacy keys `fpt_groups` (string array) and `fpt_group_configs` (object by group ID) if they exist, creating library entries with labels derived from the 8-character group ID suffix.

#### Scenario: Library persisted after add
- **WHEN** the user adds a new group entry and reloads the page
- **THEN** the new entry appears in the library

#### Scenario: Selection persisted across reload
- **WHEN** the user unchecks group B and reloads the page
- **THEN** group B's checkbox is still unchecked

#### Scenario: Migration from legacy schema
- **WHEN** `fpt_groups_library` is absent but `fpt_groups` contains `["686b517a..."]` and `fpt_group_configs` contains config for that ID
- **THEN** a library entry is created with url="686b517a...", label="...7a..." (short ID), selected=true, and the stored config

#### Scenario: No legacy data
- **WHEN** both `fpt_groups_library` and legacy keys are absent
- **THEN** the library starts empty with no rows shown

