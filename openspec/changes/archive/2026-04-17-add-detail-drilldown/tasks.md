# Tasks: add-detail-drilldown

## app.py

- [x] 1. In `if run:` block, add `"parsed_reports": parsed` to each success result dict
- [x] 2. In `_render_result`, add `with st.expander("🔍 Xem chi tiết"):` at the bottom
- [x] 3. Inside expander — "Theo shop": `st.selectbox` of all `shop_ref` values; when selected, display a detail card (ASM, Số cọc, Cọc D-1, Ra tiêm, Giờ gửi, Tích cực, Vấn đề, Đã làm)
- [x] 4. Inside expander — "Theo nhân viên": `st.selectbox` of all unique `sender` values; when selected, display one detail card per shop that ASM reported

## Validation

- [x] 5. Update `openspec/specs/asm-report-analysis/spec.md`
- [x] 6. Validate with `openspec validate add-detail-drilldown --strict --no-interactive`
