# Design: ASM Daily Report Analysis

## Context
Báo cáo ASM là tin nhắn TEXT trong FPT Chat group theo format bán cấu trúc (semi-structured). Mỗi báo cáo gồm phần mở đầu (tên shop) và các mục có tiêu đề cố định: "Kết quả", "Tích cực", "Vấn đề", "Đã làm", "Ngày mai". Format không hoàn toàn đồng nhất (dấu câu, ký tự đặc biệt, ký tự xuống dòng có thể thay đổi) nên cần regex tolerant.

## Goals / Non-Goals
- **Goals**:
  - Parse chính xác: shop ID/tên, số cọc, các mục nội dung
  - Lọc shop theo ngưỡng cọc và xuất hai danh sách
  - Thu thập "Đã làm" làm nguồn ý tưởng triển khai
  - Tổng hợp tích cực / vấn đề
  - Phát hiện ASM chưa báo cáo so với danh sách kỳ vọng
- **Non-Goals**:
  - Phân tích NLP/AI trên nội dung tự do
  - Ghi dữ liệu ngược lại FPT Chat
  - Phân loại tự động loại ý tưởng

## Decisions

### 1. Parse bằng regex trên toàn text tin nhắn
- **Quyết định**: Dùng regex multi-line để nhận dạng từng mục. Pattern ví dụ:
  - Shop: `r'[Ss]hop[:\s]+([^\n]+)'` 
  - Cọc: `r'(\d+)\s*cọc'` trong dòng Kết quả
  - Mục nội dung: `r'[-–]\s*Tích cực\s*:(.*?)(?=[-–]\s*\w|$)'` (DOTALL)
- **Lý do**: Đơn giản, không cần thư viện ngoài, phù hợp quy ước single-file script.
- **Alternatives**: Dùng LLM để parse → quá phức tạp, cần API key, không offline được.

### 2. Nhận dạng báo cáo ASM qua heuristic
- **Quyết định**: Một tin nhắn TEXT được coi là báo cáo ASM nếu khớp **cả hai** điều kiện:
  1. Chứa từ "shop" (case-insensitive)
  2. Chứa pattern `\d+\s*cọc`
- **Lý do**: Tránh false positive với các tin nhắn chat thông thường.

### 3. Danh sách ASM kỳ vọng từ API group members
- **Quyết định**: Fetch danh sách thành viên group từ FPT Chat API thay vì cấu hình thủ công. Endpoint: `GET /group-management/group/{groupId}/participant?limit=50&page=1`. API phân trang theo `page` (1-based). Tool fetch tuần tự cho đến khi trang trả về ít hơn `limit` items. Response trả về mảng object user với các field `id`, `displayName`, `username`.
- **Lý do**: Danh sách ASM chính là thành viên của group báo cáo; lấy trực tiếp từ API loại bỏ việc phải maintain config thủ công và tránh sai sót khi thành viên group thay đổi.
- **Fallback**: Nếu API members thất bại (non-2xx), tool in cảnh báo stderr và bỏ qua compliance check thay vì crash.
- **Offline mode (`--load`)**: Khi dùng `--load`, không thể gọi API members. Tool yêu cầu `--token` + `--group` vẫn được cung cấp để fetch members riêng, hoặc bỏ qua compliance check nếu thiếu.

### 4. Thời điểm kiểm tra compliance
- **Quyết định**: Flag `--asm-deadline HH:MM` (mặc định `20:00`). Tool lọc tin nhắn trong ngày được chỉ định (default: hôm nay theo UTC+7), chỉ tính báo cáo gửi trước deadline.
- **Lý do**: Hạn mềm 20:00 có thể thay đổi, cần cấu hình được.

### 5. Output mode mới
- **Quyết định**: Flag `--asm-report` kết hợp với `--format text|json`. Text output thêm 4 section mới; JSON thêm key `asm_report`.
- **Lý do**: Tái sử dụng pipeline fetch → analyze → report hiện tại.

## Risks / Trade-offs
- **Regex fragility**: Format báo cáo do người viết, có thể sai chính tả hoặc dùng ký tự thay thế (gạch ngang, dấu chấm đầu dòng). Mitigation: Pattern tolerant, log cảnh báo khi không parse được mục nào.
- **Tên ASM không khớp**: `displayName` trên FPT Chat có thể có dấu cách/hoa/thường khác nhau. Mitigation: So khớp substring case-insensitive.

## Open Questions
- Báo cáo ASM có thể gửi theo nhiều tin nhắn liên tiếp (multi-message) không, hay luôn là một tin nhắn duy nhất? → Giả định: một tin nhắn = một báo cáo.
- Ngưỡng cọc `< 2` và `> 5` có cần cấu hình qua CLI/config không? → Đề xuất: hardcode mặc định nhưng cho phép override qua `--coc-low N --coc-high N`.
- Cấu trúc response của `/group-management/group/{groupId}/participant`: field tên là `displayName`, field ID là `id`. Đã xác nhận.
