## MODIFIED Requirements

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
