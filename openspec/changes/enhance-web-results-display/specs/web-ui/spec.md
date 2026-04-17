## MODIFIED Requirements

### Requirement: Web UI Results Display
Kết quả phân tích ASM SHALL được hiển thị bằng `st.dataframe` thay vì markdown lists và expanders:

1. **Shop đặt cọc**: bảng gồm cột Shop, Số cọc, Mức (Thấp/Bình thường/Cao), ASM — sort mặc định theo Số cọc giảm dần; các dòng Thấp/Cao được giữ nguyên màu Streamlit mặc định
2. **Ý tưởng ASM**: bảng gồm cột ASM, Shop, Nội dung
3. **Điểm nổi bật**: bảng gồm cột ASM, Shop, Loại, Nội dung
4. **ASM chưa báo cáo**: bảng gồm cột Tên ASM

Khi một section không có dữ liệu, hiển thị text "(không có)" thay vì bảng rỗng.

#### Scenario: Có dữ liệu shop
- **WHEN** `asm_data["all_shops"]` có ít nhất 1 phần tử
- **THEN** `st.dataframe` hiển thị toàn bộ shop, user có thể click header cột để sort

#### Scenario: Không có dữ liệu
- **WHEN** một section không có dữ liệu
- **THEN** hiển thị dòng chữ "(không có)" thay vì bảng rỗng

### Requirement: Web UI Download Button Placement
Nút **⬇️ Tải Excel** SHALL xuất hiện ngay trong hàng tiêu đề kết quả (cùng dòng với "Kết quả phân tích"), không đặt cuối trang.

#### Scenario: Sau khi chạy phân tích
- **WHEN** phân tích hoàn tất (dù có hay không có báo cáo ASM)
- **THEN** nút Tải Excel hiển thị ngay cạnh tiêu đề kết quả, không cần cuộn xuống
