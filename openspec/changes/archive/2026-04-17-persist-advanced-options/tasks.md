## 1. Đọc từ localStorage khi load
- [ ] 1.1 Thêm `_ls_get("fpt_deposit_low")`, `_ls_get("fpt_deposit_high")`, `_ls_get("fpt_deadline")`, `_ls_get("fpt_skip")` vào khối đọc localStorage đầu trang (cùng chỗ đọc `fpt_token`, `fpt_group`)
- [ ] 1.2 Convert `fpt_deposit_low` / `fpt_deposit_high` từ string → int (dùng default nếu không parse được)
- [ ] 1.3 Truyền các giá trị đọc được làm `value=` cho 4 widget trong expander

## 2. Ghi vào localStorage khi chạy
- [ ] 2.1 Trong khối `if run:`, thêm 4 lệnh `_ls_set(...)` cho các key tương ứng (ngay sau khi đã lưu token và group)

## 3. Validation
- [ ] 3.1 Kiểm thử thủ công: thay đổi cả 4 field → chạy → reload → kiểm tra form hiển thị đúng giá trị đã lưu
- [ ] 3.2 Kiểm thử: lần đầu mở (localStorage trống) → các field hiển thị đúng default
