# Change: Enhance Web Results Display

## Why
Kết quả hiện tại hiển thị dưới dạng danh sách markdown bullet và expander lồng nhau — khó đọc nhanh và không thể sort/filter. Dùng `st.dataframe` cho phép nhìn tổng quan cả bảng, sort cột, và tìm kiếm inline.

Nút download Excel hiện nằm tách biệt ở cuối trang sau khi có kết quả — không trực quan.

## What Changes

### Thay markdown lists bằng bảng (`st.dataframe`)

| Section hiện tại | Thay bằng |
|---|---|
| Shop đặt cọc thấp / cao (markdown list) | Một bảng duy nhất **Tất cả shop** với cột: Shop, Số cọc, Mức, ASM — có thể sort |
| Ý tưởng ASM (expander per row) | Bảng: ASM, Shop, Nội dung |
| Điểm nổi bật (expander per row) | Bảng: ASM, Shop, Loại (Tích cực/Hạn chế), Nội dung |
| ASM chưa báo cáo (markdown list) | Bảng đơn giản: Tên ASM |

### Download Excel
- Nút **⬇️ Tải Excel** đặt ngay bên cạnh tiêu đề kết quả (sau khi có data), không ẩn ở cuối trang
- Giữ nguyên logic `write_asm_excel` — chỉ đổi vị trí nút

## Impact
- Chỉ ảnh hưởng `app.py` — không thay đổi logic phân tích hay spec
