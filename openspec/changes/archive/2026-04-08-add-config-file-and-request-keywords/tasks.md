## 1. Config file loading
- [x] 1.1 Write `load_config(path: str) -> dict` — reads and parses `config.json`; returns `{}` if file is absent; raises clear error on malformed JSON
- [x] 1.2 Add `--config FILE` CLI argument (default: `"config.json"`)
- [x] 1.3 In `main()`, call `load_config()` before `parse_args()` resolution and merge: CLI args override config keys

## 2. Optional --token and --group
- [x] 2.1 Change `--token` from `required=True` to optional; validate post-merge that a token is available (from CLI or config), else exit with a clear error message
- [x] 2.2 Change `--group` from `required=True` to optional; same post-merge validation

## 3. Keyword-based request detection
- [x] 3.1 Add `request_keywords` parameter to `analyze()` (list of strings, default `[]`)
- [x] 3.2 In `analyze()`, for each TEXT message: check if `content.lower()` contains any keyword (lowercased); if so, mark the message as a request regardless of whether it has links
- [x] 3.3 Ensure a message is not double-counted if it matches both a keyword AND has links (one request entry per message)

## 4. New statistic: requests_by_month
- [x] 4.1 Add `requests_by_month: defaultdict(int)` to the stats dict
- [x] 4.2 Increment `requests_by_month[YYYY-MM]` for every message classified as a request (keyword or link match)

## 5. Reporting
- [x] 5.1 `print_text_report()` — add "REQUEST THEO THÁNG" section showing `requests_by_month`
- [x] 5.2 `print_json_report()` — add `requests_by_month` key to the JSON output

## 6. Config file template
- [x] 6.1 Create `config.example.json` in project root as a reference template (token placeholder, sample keywords)

## 7. Validation
- [x] 7.1 Config.json with real token loaded automatically; tool calls API correctly
- [x] 7.2 `--config /tmp/test_config.json` overrides default path; keywords from that file applied
- [x] 7.3 Keyword "nhờ" matches message bbb (no links) → appears as requester with 0 links but 1 request
- [x] 7.4 requests_by_month: {2026-03: 2, 2026-04: 1} correct with user's keywords configured
- [x] 7.5 --load without --group/--token works when config.json provides them; missing token shows clear error
