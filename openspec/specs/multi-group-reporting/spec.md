# multi-group-reporting Specification

## Purpose
TBD - created by archiving change add-multi-group-support. Update Purpose after archive.
## Requirements
### Requirement: Multi-Group Input
The web UI SHALL provide a multi-line text area where users can enter one entry per line. Each line may be:
- A raw group ID or FPT Chat URL (group name resolved automatically from API), or
- A group ID / URL followed by ` | ` and a custom label (e.g. `686b517a... | Nhóm miền Bắc`).

Lines that are blank or whitespace-only SHALL be ignored. At least one valid group entry MUST be present before analysis can start.

#### Scenario: Single group entered
- **WHEN** the text area contains one line with a valid group ID
- **THEN** analysis runs for that group only, same as the previous single-group behaviour

#### Scenario: Multiple groups entered
- **WHEN** the text area contains three lines each with a different group ID or URL
- **THEN** analysis runs sequentially for all three groups

#### Scenario: Custom label provided
- **WHEN** a line is `686b517a54ca42cb3c30e1df | Nhóm miền Bắc`
- **THEN** the group ID `686b517a54ca42cb3c30e1df` is used for API calls and the tab label is `Nhóm miền Bắc`

#### Scenario: Blank lines ignored
- **WHEN** the text area contains a group ID on line 1, a blank line 2, and a group ID on line 3
- **THEN** analysis runs for two groups; the blank line is silently skipped

#### Scenario: No group entered
- **WHEN** the text area is empty or contains only whitespace
- **THEN** clicking "Chạy phân tích" shows an error and does not start analysis

---

### Requirement: Per-Group Tabbed Results
After analysis completes, the web UI SHALL display results in a `st.tabs` widget with one tab per analyzed group.

Tab label resolution order (highest priority first):
1. Custom label provided by the user in the text area (after ` | `)
2. Group name fetched from the FPT Chat API (`fetch_group_info`)
3. Last 8 characters of the group hex ID (fallback)

#### Scenario: Two groups analyzed successfully
- **WHEN** two groups were analyzed and both succeeded
- **THEN** two tabs appear; each tab contains the full analysis result (metrics, tables) for its group

#### Scenario: One group succeeds, one fails
- **WHEN** group A fetches successfully but group B returns an API error
- **THEN** two tabs appear; tab A shows results normally; tab B shows an error message describing the failure

#### Scenario: Custom label used as tab name
- **WHEN** the user entered `686b517a54ca42cb3c30e1df | Nhóm miền Bắc`
- **THEN** the tab label is `Nhóm miền Bắc` regardless of what the API returns

#### Scenario: API group name used when no custom label
- **WHEN** no custom label is given and `fetch_group_info` returns `{"name": "ASM Hà Nội"}`
- **THEN** the tab label is `ASM Hà Nội`

#### Scenario: Short ID fallback
- **WHEN** no custom label is given and `fetch_group_info` returns `{}` or fails
- **THEN** the tab label is the last 8 characters of the group ID (e.g. `3c30e1df`)

---

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
The web UI SHALL persist the list of groups entered by the user in browser localStorage under the key `fpt_groups` as a JSON-encoded array of strings. On page load, the stored value SHALL be restored into the text area.

When `fpt_groups` is absent from localStorage, the UI SHALL fall back to reading the legacy `fpt_group` key (single string) and pre-populate the text area with that single value.

#### Scenario: Groups saved on run
- **WHEN** the user enters two groups and clicks "Chạy phân tích"
- **THEN** `localStorage.fpt_groups` is set to the JSON array of those two group strings

#### Scenario: Groups restored on reload
- **WHEN** the user reloads the page and `fpt_groups` is set in localStorage
- **THEN** the text area is pre-filled with the stored groups (one per line)

#### Scenario: Legacy fallback
- **WHEN** `fpt_groups` is absent but `fpt_group` contains a single group ID
- **THEN** the text area is pre-filled with that single ID

#### Scenario: Config file fallback
- **WHEN** both localStorage keys are absent and `config.json` contains a `groups` array
- **THEN** the text area is pre-filled with those groups (one per line)

