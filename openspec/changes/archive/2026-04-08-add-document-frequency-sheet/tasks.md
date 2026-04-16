## 1. Excel writer update
- [x] 1.1 In `write_excel()`, group `stats["links"]` by `url` → build `{url: {count, requesters set}}`
- [x] 1.2 Create sheet "Tần suất tài liệu" with columns: STT | URL | Số lần request | Người request
- [x] 1.3 Sort rows by count descending; auto-width URL column (capped); freeze top row; bold header

## 2. Validation
- [x] 2.1 Test with sample data; verify URL counts match the number of times each link appears in requests
- [x] 2.2 Verify "Người request" deduplicates names (same person requesting same URL twice → one name)
- [x] 2.3 Verify sheet appears as third sheet after "Tổng hợp" and "Chi tiết"
