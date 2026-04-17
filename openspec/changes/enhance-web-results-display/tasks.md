## 1. Thay thế phần hiển thị kết quả trong app.py
- [x] 1.1 Section "Shop đặt cọc": thay 2 markdown list (thấp/cao) bằng một `st.dataframe` tất cả shop, cột: Shop, Số cọc, Mức, ASM — sort mặc định theo Số cọc giảm dần
- [x] 1.2 Section "Ý tưởng ASM": thay expander list bằng `st.dataframe` cột: ASM, Shop, Nội dung
- [x] 1.3 Section "Điểm nổi bật": thay expander list bằng `st.dataframe` cột: ASM, Shop, Loại, Nội dung
- [x] 1.4 Section "ASM chưa báo cáo": thay markdown list bằng `st.dataframe` cột: Tên ASM

## 2. Di chuyển nút download Excel
- [x] 2.1 Đặt nút "⬇️ Tải Excel" vào hàng tiêu đề kết quả (dùng `st.columns` tiêu đề + nút), xoá nút ở cuối trang

## 3. Validation
- [x] 3.1 Syntax check pass
- [x] 3.2 App khởi động HTTP 200
- [x] 3.3 st.dataframe hỗ trợ sort cột khi click header
- [x] 3.4 Nút Excel xuất hiện cùng hàng tiêu đề "Kết quả phân tích"
