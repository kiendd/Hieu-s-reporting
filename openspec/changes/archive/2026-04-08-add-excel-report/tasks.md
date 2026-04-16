## 1. Dependency
- [x] 1.1 Add `openpyxl>=3.1.0` to `requirements.txt`

## 2. Analysis update
- [x] 2.1 Add `"content"` and `"urls"` fields to each request entry in `analyze()`

## 3. Excel writer
- [x] 3.1 Implement `write_excel(stats, path)` function
- [x] 3.2 Sheet "Tổng hợp": header row = ["Người dùng"] + sorted month list + ["Tổng"]; one row per user with counts per month and row total; bold header + freeze top row
- [x] 3.3 Sheet "Chi tiết": columns = STT, Ngày giờ (UTC+7), Người dùng, Nội dung, Links; one row per request message; freeze top row; auto-width columns

## 4. CLI
- [x] 4.1 Add `--excel FILE` argument to `argparse`
- [x] 4.2 In `main()`, call `write_excel()` when `--excel` is provided; print confirmation to stderr

## 5. Validation
- [x] 5.1 Test `--excel report.xlsx` with sample data; two sheets verified
- [x] 5.2 "Tổng hợp" pivot matches requests_by_month counts
- [x] 5.3 "Chi tiết" content and links columns populated correctly
- [x] 5.4 Combined `--excel --format text` works; text prints to stdout, xlsx written to file
