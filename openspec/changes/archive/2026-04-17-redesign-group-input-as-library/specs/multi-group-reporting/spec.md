## MODIFIED Requirements

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
