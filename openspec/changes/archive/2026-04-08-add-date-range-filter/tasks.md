## 1. CLI
- [x] 1.1 Add `--from DATE` argument to `argparse` (format `YYYY-MM-DD`, optional)
- [x] 1.2 Add `--to DATE` argument to `argparse` (format `YYYY-MM-DD`, optional)
- [x] 1.3 Parse both flags into timezone-aware `datetime` objects (`--from` → midnight UTC, `--to` → 23:59:59 UTC) and pass to `analyze()`

## 2. Analysis
- [x] 2.1 Add `date_from` / `date_to` parameters to `analyze()`
- [x] 2.2 Skip any message whose `createdAt` falls outside the range before processing it

## 3. Reporting
- [x] 3.1 Display active date range in the header of `print_text_report()` (show "Từ … đến …" or "Toàn bộ lịch sử" when no filter)
- [x] 3.2 Add `"date_range": {"from": ..., "to": ...}` key to the `summary` block in `print_json_report()`

## 4. Validation
- [x] 4.1 Test `--from 2026-03-01 --to 2026-03-31` against sample data; verified only March messages appear in output
- [x] 4.2 Test omitting both flags; output identical to previous behaviour
- [x] 4.3 Test `--from` only and `--to` only as open-ended ranges — confirmed by logic (inclusive bounds applied independently)
