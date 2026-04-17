# Hướng dẫn sử dụng — FPT Chat ASM Report

Truy cập công cụ tại: **https://hieureport.streamlit.app**

---

## Bước 1 — Lấy token

Token là mã xác thực cá nhân, dùng để công cụ đọc lịch sử chat thay bạn.

![Hướng dẫn lấy token](huong-dan-lay-token.png)

1. Mở **FPT Chat** trên trình duyệt (chat.fpt.com), đăng nhập
2. Nhấn **F12** để mở DevTools → chọn tab **Network**
3. Chọn tiếp thẻ **Fetch/XHR** → nhấn **F5** (hoặc Cmd+R) để tải lại trang
4. Chọn một request bất kỳ trong danh sách, ví dụ **settings**
5. Chọn tab **Headers** → kéo xuống tìm dòng **Authorization**
6. Sao chép toàn bộ phần sau chữ `Bearer ` (đoạn mã dài — **không lấy chữ Bearer**)

> **Lưu ý**: Token có thời hạn. Nếu báo lỗi kết nối, lấy lại token mới theo các bước trên.

---

## Bước 2 — Lấy Group ID

Group ID là mã định danh nhóm chat, tìm trong URL khi mở nhóm trên trình duyệt:

```
https://chat.fpt.com/group/686b517a54ca42cb3c30e1df
                                  ↑ đây là Group ID (24 ký tự)
```

Có thể dán nguyên URL vào ô — công cụ tự trích ID.

---

## Bước 3 — Chạy phân tích

Truy cập **https://hieureport.streamlit.app**, điền vào form:

| Ô nhập | Nội dung |
|--------|----------|
| **Token (Bearer)** | Dán token vừa lấy ở Bước 1 |
| **Group ID hoặc URL** | Dán Group ID hoặc URL nhóm chat |
| **Khoảng thời gian** | Chọn **Hôm nay** hoặc tự chọn ngày |

Nhấn **▶ Chạy phân tích**.

> Token và Group ID được lưu tự động — lần sau chỉ cần nhấn Chạy.

---

## Bước 4 — Đọc kết quả

Sau khi chạy xong, kết quả hiển thị theo 4 bảng:

### 🏪 Shop đặt cọc
Toàn bộ shop được ASM báo cáo, phân loại theo mức đặt cọc:

| Mức | Ý nghĩa |
|-----|---------|
| **Thấp** | Số cọc dưới ngưỡng tối thiểu — cần chú ý |
| **Bình thường** | Trong ngưỡng cho phép |
| **Cao** | Vượt ngưỡng — kết quả tốt |

Click vào tên cột để sắp xếp bảng.

### 💡 Ý tưởng triển khai từ ASM
Tổng hợp nội dung "Đã làm" từ báo cáo của từng ASM — các sáng kiến, cách triển khai mới đáng chú ý.

### ⭐ Điểm nổi bật
Tổng hợp **Tích cực** và **Hạn chế** từ báo cáo của từng ASM.

### ⚠️ ASM chưa báo cáo
Danh sách thành viên chưa gửi báo cáo trước deadline (mặc định 20:00 giờ VN).

---

## Bước 5 — Tải báo cáo Excel

Nhấn nút **⬇️ Tải Excel** ở góc phải phần kết quả để tải file `.xlsx` về máy.

File Excel gồm 4 sheet tương ứng với 4 bảng trên màn hình.

---

## Tuỳ chọn nâng cao

Mở mục **⚙️ Tuỳ chọn nâng cao** để điều chỉnh:

| Tuỳ chọn | Mặc định | Ý nghĩa |
|----------|----------|---------|
| Ngưỡng cọc thấp | 2 | Shop có số cọc < giá trị này bị đánh dấu Thấp |
| Ngưỡng cọc cao | 5 | Shop có số cọc > giá trị này bị đánh dấu Cao |
| Deadline báo cáo | 20:00 | Giờ chốt kiểm tra ASM chưa báo cáo (giờ VN) |
| Bỏ qua compliance | _(trống)_ | Tên quản lý không cần báo cáo, cách nhau dấu phẩy |
