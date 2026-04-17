## Context
App có một `st.expander("⚙️ Tuỳ chọn nâng cao")` duy nhất ở đầu trang — nằm trước nút Chạy, tức là TRƯỚC khi có kết quả/tab. Tuỳ chọn nâng cao phải được đặt trước khi chạy nên không thể di chuyển vào trong tab kết quả.

## Goals / Non-Goals
- Goals: mỗi group ID nhớ config riêng; đổi nhóm → expander tự điền config phù hợp
- Non-Goals: giao diện đồng thời chỉnh config của nhiều nhóm khác nhau trong cùng một màn hình; không cần "lưu mà không cần chạy"

## Storage Schema
```json
// localStorage["fpt_group_configs"]
{
  "686b517a54ca42cb3c30e1df": {
    "deposit_low": 3,
    "deposit_high": 8,
    "deadline": "19:00",
    "skip": "Giám đốc, Trưởng phòng"
  },
  "abc123def456abc123def456": {
    "deposit_low": 2,
    "deposit_high": 5,
    "deadline": "20:00",
    "skip": ""
  }
}
```

## Decisions

### Multi-group: dùng config của nhóm nào trong expander?
- **Quyết định: nhóm đầu tiên trong text area** — expander pre-fill config của nhóm đầu tiên (hoặc global default nếu chưa có config). Khi chạy, mỗi nhóm dùng config riêng của nó; nhóm chưa có config dùng giá trị đang hiển thị trong expander.
- Alternatives: hiện config của tất cả nhóm cùng lúc (quá phức tạp); chỉ dùng global defaults cho multi-group (không đáp ứng yêu cầu).

### Khi nào lưu config?
- **Quyết định: khi nhấn "Chạy phân tích"** — lưu giá trị expander làm config của TẤT CẢ nhóm đang chạy, trừ những nhóm đã có config riêng (giữ nguyên config cũ của chúng).
- **Exception:** nếu chỉ có 1 nhóm → luôn lưu đè từ expander (user đang chỉnh config cho nhóm đó).

Rationale: với multi-group, expander reflect config của nhóm 1 — không nên tự động ghi đè config của nhóm 2, 3 bằng config của nhóm 1.

### Không lưu global defaults riêng
- Chỉ có `fpt_group_configs` (per-group). Không có key global riêng.
- Global defaults (2, 5, "20:00", "") là hardcoded — dùng khi group chưa có config.

## Risks / Trade-offs
- Multi-group UX hơi counterintuitive: expander hiện config nhóm 1, nhóm 2 và 3 chạy với config riêng của chúng (có thể khác nhau). Người dùng cần biết điều này.
- Mitigation: hiển thị config thực tế đã dùng trong mỗi tab kết quả (read-only summary).

## Open Questions
- (Answered) Single group: lưu đè từ expander khi chạy → ✓
- (Answered) Multi-group: nhóm đã có config → không bị ghi đè bởi nhóm khác → ✓
