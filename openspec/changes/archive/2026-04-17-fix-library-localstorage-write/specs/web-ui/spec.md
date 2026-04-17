## MODIFIED Requirements

### Requirement: Multi-Group Persistence
The web UI SHALL persist the Group Library in browser localStorage under the key `fpt_groups_library`. Any change to the library SHALL immediately write the updated library to `localStorage["fpt_groups_library"]`.

localStorage writes SHALL be performed only from the main Streamlit render body, never from inside a `@st.dialog` or `@st.fragment` context, to guarantee the `st_javascript` component is committed to the browser before any rerun occurs.

#### Scenario: Library persisted after add via dialog
- **WHEN** the user adds a new group entry via the dialog and the page is refreshed
- **THEN** the new entry appears in the library

#### Scenario: Library persisted after edit via dialog
- **WHEN** the user edits a group entry via the dialog and the page is refreshed
- **THEN** the updated entry is shown
