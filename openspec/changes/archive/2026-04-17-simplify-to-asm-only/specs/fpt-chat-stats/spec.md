## REMOVED Requirements

### Requirement: Statistical Analysis
**Reason**: Tool không còn theo dõi document requests. Toàn bộ phân tích requesters, file senders, links, monthly stats bị xóa.
**Migration**: Không cần — chức năng này không còn được dùng.

### Requirement: JSON Report Output
**Reason**: Tool không còn hỗ trợ JSON output format; chỉ dùng text output ASM-focused.
**Migration**: Không cần.

### Requirement: Keyword-based Request Detection
**Reason**: Không còn phân tích document requests.
**Migration**: Không cần — `request_keywords` config key và `keywords.txt` bị bỏ qua.

### Requirement: Request Count by Month
**Reason**: Không còn theo dõi requests.
**Migration**: Không cần.

### Requirement: Username Cache
**Reason**: Chỉ dùng để hiển thị requesters/file senders — không còn cần thiết.
**Migration**: Không cần.

### Requirement: User Display Format
**Reason**: Chỉ dùng cho requesters/file senders.
**Migration**: Không cần.

### Requirement: Summary Sheet ("Tổng hợp")
**Reason**: Thay bằng sheet ASM trong Excel export mới.
**Migration**: Không cần.

### Requirement: Detail Sheet ("Chi tiết")
**Reason**: Thay bằng sheet ASM trong Excel export mới.
**Migration**: Không cần.

### Requirement: Document Frequency Sheet ("Tần suất tài liệu")
**Reason**: Thay bằng sheet ASM trong Excel export mới.
**Migration**: Không cần.

---

## MODIFIED Requirements

### Requirement: Text Report Output
The tool SHALL produce a Vietnamese text report to `stdout` containing only ASM report analysis results:

1. **Summary header**: date range, số báo cáo ASM phát hiện được, số thành viên group (nếu fetch được)
2. **SHOP ĐẶT CỌC THẤP**: shops có deposit count < `deposit_low`
3. **SHOP ĐẶT CỌC CAO**: shops có deposit count > `deposit_high`
4. **Ý TƯỞNG TRIỂN KHAI TỪ ASM**: nội dung "Đã làm" từng ASM
5. **ĐIỂM TÍCH CỰC**: nội dung "Tích cực" từng ASM
6. **ĐIỂM HẠN CHẾ**: nội dung "Vấn đề" từng ASM
7. **ASM CHƯA BÁO CÁO**: tên đầy đủ thành viên chưa báo cáo trước deadline (chỉ hiện khi fetch members thành công)

Khi không phát hiện báo cáo ASM nào, tool in cảnh báo và các section hiển thị "(không có)".

#### Scenario: Reports detected
- **WHEN** messages contain 3 ASM reports and `--today` is active
- **THEN** stdout contains all 7 sections populated with parsed data

#### Scenario: No reports detected
- **WHEN** no messages match the ASM heuristic
- **THEN** a warning is printed to `stderr` and all sections show "(không có)"

---

### Requirement: Excel Report Export
When `--excel FILE` is provided, the tool SHALL write a `.xlsx` file containing **four ASM-focused sheets**:

1. **"Shop Đặt Cọc"**: tất cả shops được phân tích, với cột: STT, Shop, Số đặt cọc, Mức (Thấp/Bình thường/Cao), ASM. Rows sắp xếp theo số đặt cọc giảm dần.
2. **"Ý tưởng ASM"**: cột STT, ASM, Shop, Nội dung "Đã làm", Ngày giờ (UTC+7).
3. **"Điểm nổi bật"**: cột STT, ASM, Shop, Loại (Tích cực/Hạn chế), Nội dung.
4. **"ASM chưa báo cáo"**: cột STT, Tên ASM — chỉ có data khi fetch members thành công; nếu không sheet vẫn tồn tại với header và ghi chú "(Không thể kiểm tra — thiếu token/group)".

#### Scenario: Excel with full ASM data
- **WHEN** `--excel report.xlsx --today` is passed and ASM reports are detected
- **THEN** `report.xlsx` is written with all 4 sheets populated

#### Scenario: Excel when no members fetched
- **WHEN** members API fails or token is absent
- **THEN** sheet "ASM chưa báo cáo" is still created but contains only a note row

#### Scenario: Excel when no ASM reports
- **WHEN** no ASM reports are detected
- **THEN** all 4 sheets are created with headers only (no data rows)

---

## ADDED Requirements

### Requirement: Auto ASM Detection
The tool SHALL always run the ASM detection and analysis pipeline automatically — no explicit flag required. If ASM reports are found, analysis results are included in all outputs. If none are found, output sections are empty and a warning is printed to `stderr`.

The `--asm-report` flag is removed.

#### Scenario: ASM reports present — auto included in output
- **WHEN** the fetched messages contain ASM report messages
- **THEN** all ASM sections appear in text output and Excel without any extra flag

#### Scenario: No ASM reports — clean output with warning
- **WHEN** no ASM report messages are detected
- **THEN** ASM sections show "(không có)" and a warning is printed to `stderr`
