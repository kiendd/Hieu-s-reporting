## ADDED Requirements

### Requirement: Config File Loading
The tool SHALL load a JSON config file before resolving CLI arguments. Keys present in the config file are used as defaults; explicit CLI arguments take precedence.

Supported config keys:
- `token` — equivalent to `--token`
- `group` — equivalent to `--group`
- `api_url` — equivalent to `--api-url`
- `request_keywords` — list of strings used for keyword-based request detection

The default config file path is `config.json` in the current working directory. This path can be overridden with `--config FILE`.

If the config file is absent, the tool proceeds without error. If the file exists but contains malformed JSON, the tool exits with a descriptive error message.

#### Scenario: Config file present, no CLI token
- **WHEN** `config.json` contains `"token": "abc123"` and `--token` is not passed
- **THEN** the tool uses `"abc123"` as the token and proceeds normally

#### Scenario: CLI token overrides config
- **WHEN** `config.json` contains `"token": "abc123"` and `--token xyz789` is passed
- **THEN** the tool uses `"xyz789"` (CLI takes precedence)

#### Scenario: Config file absent
- **WHEN** no `config.json` exists and `--token`/`--group` are provided on CLI
- **THEN** the tool runs normally with no error about the missing config file

#### Scenario: Malformed config file
- **WHEN** `config.json` exists but contains invalid JSON
- **THEN** the tool prints a clear error to `stderr` and exits with a non-zero code

#### Scenario: Neither config nor CLI provides token
- **WHEN** `config.json` is absent and `--token` is not passed
- **THEN** the tool prints `"Error: --token is required (or set 'token' in config.json)"` and exits

---

### Requirement: Keyword-based Request Detection
The tool SHALL classify a TEXT message as a "request" if its `content` contains any of the configured `request_keywords` (case-insensitive substring match), in addition to the existing link-based detection.

A message is a request if it matches **either** condition:
- Contains one or more entries in `metadata.links`, **OR**
- Its `content` (lowercased) contains at least one configured keyword (also lowercased)

A message that satisfies both conditions is counted as a single request (no double-counting).

When `request_keywords` is empty (default), only link-based detection is used — preserving existing behaviour.

#### Scenario: Keyword match without links
- **WHEN** a TEXT message has content `"Nhờ c down giúp em tài liệu này"` and `"nhờ"` is a configured keyword
- **THEN** the message is classified as a request and the sender's request count increases by 1

#### Scenario: Link match without keyword
- **WHEN** a TEXT message has `metadata.links` with 2 entries but its content does not contain any keyword
- **THEN** the message is still classified as a request (existing link-based behaviour preserved)

#### Scenario: Both keyword and link match
- **WHEN** a TEXT message matches a keyword AND has links
- **THEN** the message is counted as exactly one request (not two)

#### Scenario: No keywords configured
- **WHEN** `request_keywords` is empty or not set
- **THEN** only link-based detection applies; tool behaviour is identical to before this change

#### Scenario: Case-insensitive match
- **WHEN** content is `"NHỜI c @Thu ơi"` and keyword is `"nhờ"`
- **THEN** the message is classified as a request (match is case-insensitive)

---

### Requirement: Request Count by Month
The tool SHALL compute and report a `requests_by_month` statistic: the number of request messages (keyword or link matched) grouped by `YYYY-MM`.

This is separate from `by_month` which counts all messages regardless of type.

#### Scenario: Requests counted per month
- **WHEN** 3 request messages were sent in March 2026 and 5 in April 2026
- **THEN** `requests_by_month` contains `{"2026-03": 3, "2026-04": 5}`

#### Scenario: Non-request messages excluded
- **WHEN** a FILE or ACTIVITY message is processed
- **THEN** it does not increment `requests_by_month`

#### Scenario: Displayed in text report
- **WHEN** `--format text` is used
- **THEN** a "REQUEST THEO THÁNG" section appears in the report showing counts per month

#### Scenario: Included in JSON report
- **WHEN** `--format json` is used
- **THEN** output contains a top-level `"requests_by_month"` key with month-count pairs

---

## MODIFIED Requirements

### Requirement: Authentication
The tool SHALL authenticate against the FPT Chat API using a `fchat_ddtk` token sent as both an `Authorization: Bearer` header and an `fchat_ddtk` cookie on every request.

The token MAY be supplied via:
1. `--token` CLI argument (highest precedence), or
2. `token` key in the config file (see *Config File Loading* requirement)

At least one source MUST provide the token; otherwise the tool exits with an error.

#### Scenario: Token provided via CLI
- **WHEN** the user passes `--token <value>`
- **THEN** every API request includes `Authorization: Bearer <value>` and `Cookie: fchat_ddtk=<value>`

#### Scenario: Token provided via config file
- **WHEN** `config.json` contains `"token": "<value>"` and `--token` is not passed
- **THEN** every API request includes `Authorization: Bearer <value>` and `Cookie: fchat_ddtk=<value>`
