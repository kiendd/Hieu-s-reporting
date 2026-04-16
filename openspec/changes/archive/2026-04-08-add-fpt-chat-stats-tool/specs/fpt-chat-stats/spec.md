## ADDED Requirements

### Requirement: Message Fetching
The tool SHALL fetch the complete message history of a FPT Chat group by making repeated paginated requests to the FPT Chat API until all messages have been retrieved.

#### Scenario: Full history retrieved via pagination
- **WHEN** the group contains more messages than the page `limit`
- **THEN** the tool sends subsequent requests using the oldest fetched message ID as the `before` cursor until a page returns fewer messages than `limit`

#### Scenario: Single page group
- **WHEN** the group contains fewer messages than `limit`
- **THEN** the tool makes one request and stops

#### Scenario: API error
- **WHEN** the API returns a non-2xx HTTP status
- **THEN** the tool prints the error to `stderr` and exits with a non-zero code

---

### Requirement: Authentication
The tool SHALL authenticate against the FPT Chat API using a `fchat_ddtk` token sent as both an `Authorization: Bearer` header and an `fchat_ddtk` cookie on every request.

#### Scenario: Token provided via CLI
- **WHEN** the user passes `--token <value>`
- **THEN** every API request includes `Authorization: Bearer <value>` and `Cookie: fchat_ddtk=<value>`

---

### Requirement: Group ID Resolution
The tool SHALL accept a group identifier as either a raw 24-character hex ID or a full FPT Chat URL, and resolve it to the hex ID before making API calls.

#### Scenario: Raw ID passed
- **WHEN** `--group 687d9b9b805279fc03d25365` is given
- **THEN** the tool uses `687d9b9b805279fc03d25365` directly as the group ID

#### Scenario: URL passed
- **WHEN** `--group "https://chat.fpt.com/group/687d9b9b805279fc03d25365"` is given
- **THEN** the tool extracts `687d9b9b805279fc03d25365` via regex and uses it as the group ID

---

### Requirement: Statistical Analysis
The tool SHALL analyze fetched messages and compute the following statistics:

- **Requesters** — users who sent TEXT messages containing one or more links (document requests), ranked by link count.
- **File senders** — users who sent FILE messages, with total file count.
- **Monthly timeline** — message count grouped by `YYYY-MM`.
- **Link detail** — every requested URL with requester name and date.
- **File detail** — every uploaded file with sender name, file name, size, and date.

#### Scenario: User requests multiple documents in one message
- **WHEN** a TEXT message contains 3 links in `metadata.links`
- **THEN** the requester's link count increases by 3 and all 3 URLs appear in the link detail list

#### Scenario: FILE message with multiple attachments
- **WHEN** a FILE message has 2 entries in `metadata.files`
- **THEN** the sender's file count increases by 2 and both files appear in the file detail list

#### Scenario: ACTIVITY message
- **WHEN** a message has type `ACTIVITY`
- **THEN** it is counted in the total and monthly timeline but excluded from requester and file-sender statistics

---

### Requirement: Text Report Output
The tool SHALL produce a human-readable Vietnamese report to `stdout` when `--format text` (default) is used, covering: overview counts, top requesters, file senders, monthly timeline, link detail, and file detail.

#### Scenario: Default output
- **WHEN** the user runs the tool without `--format`
- **THEN** a formatted Vietnamese text report is printed to `stdout`

---

### Requirement: JSON Report Output
The tool SHALL produce a machine-readable JSON report to `stdout` when `--format json` is used, containing: `summary`, `requesters`, `file_senders`, `by_month`, `all_links`, and `all_files` keys.

#### Scenario: JSON selected
- **WHEN** the user passes `--format json`
- **THEN** valid JSON is printed to `stdout` and can be piped to `jq` or saved to a file

---

### Requirement: Raw Message Persistence
The tool SHALL save the fetched raw message list as a JSON file when `--save <path>` is provided, enabling offline re-analysis without repeating API calls.

#### Scenario: Save requested
- **WHEN** the user passes `--save raw.json`
- **THEN** after fetching, the full message list is written to `raw.json` as UTF-8 JSON

---

### Requirement: Offline Analysis Mode
The tool SHALL skip all API calls and load messages from a local JSON file when `--load <path>` is provided.

#### Scenario: Offline load
- **WHEN** the user passes `--load raw.json`
- **THEN** the tool reads messages from `raw.json`, runs analysis, and prints the report — making no network requests
