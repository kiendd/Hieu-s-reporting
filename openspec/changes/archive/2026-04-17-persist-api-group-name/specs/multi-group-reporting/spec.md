## MODIFIED Requirements

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
