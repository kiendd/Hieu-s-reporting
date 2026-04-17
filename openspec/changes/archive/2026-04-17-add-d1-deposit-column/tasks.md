# Tasks: add-d1-deposit-column

## app.py

- [x] 1. In `_render_result`, build a D-1 shop lookup dict `d1_shop_map: dict[str, int] | None` from `asm_data_d1["all_shops"]` when D-1 data is available; `None` otherwise
- [x] 2. "Shop đặt cọc" table: add `"Cọc D-1"` column using `d1_shop_map` when not None
- [x] 3. Add dedicated "Shop cọc thấp" section (table with columns: ASM, Shop, Số cọc, Cọc D-1 when available) — rendered below the metric tiles, similar to "Nhân viên cọc tốt"
- [x] 4. "Nhân viên cọc tốt" table: add `"Cọc D-1"` column using `d1_shop_map` when not None
- [x] 5. Add dedicated "Chưa báo cáo đến hiện tại" section — render `unreported_now` as a table (column: Tên thành viên) below the metric row; show "Tất cả đã báo cáo" when empty, hide section when `unreported_now is None`

## Validation

- [x] 6. Update `openspec/specs/asm-report-analysis/spec.md` with MODIFIED requirements
- [x] 7. Validate with `openspec validate add-d1-deposit-column --strict --no-interactive`
