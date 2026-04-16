## 1. Project setup
- [x] 1.1 Update `openspec/project.md` with tech stack, conventions, and domain context
- [x] 1.2 Create `requirements.txt` with `requests>=2.31.0`

## 2. Core implementation
- [x] 2.1 Implement `extract_group_id()` — parse 24-char hex ID from URL or pass-through
- [x] 2.2 Implement `build_session()` — create `requests.Session` with Bearer + cookie auth
- [x] 2.3 Implement `fetch_page()` — single paginated GET with optional `before` cursor
- [x] 2.4 Implement `fetch_all_messages()` — loop until fewer than `limit` results returned
- [x] 2.5 Implement `analyze()` — extract requesters (links in TEXT messages), file senders, timeline

## 3. Reporting
- [x] 3.1 Implement `print_text_report()` — human-readable Vietnamese output to stdout
- [x] 3.2 Implement `print_json_report()` — machine-readable JSON output to stdout

## 4. CLI
- [x] 4.1 Wire `argparse` with: `--token`, `--group`, `--api-url`, `--limit`, `--format`, `--save`, `--load`
- [x] 4.2 Implement `--save` to persist raw messages as JSON
- [x] 4.3 Implement `--load` for offline analysis without API calls

## 5. Validation
- [x] 5.1 Test with a real token + group ID; verify pagination fetches >50 messages
- [x] 5.2 Test `--load sample.json` with the provided sample response — text report correct
- [x] 5.3 Test `--format json` output is valid JSON and contains all summary fields
