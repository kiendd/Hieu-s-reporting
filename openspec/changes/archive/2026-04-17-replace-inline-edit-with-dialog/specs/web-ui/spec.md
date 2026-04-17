## MODIFIED Requirements

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
