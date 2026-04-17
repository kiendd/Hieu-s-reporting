# Tasks: update-group-ui-wide-table

- [x] 1. Change `layout="centered"` → `layout="wide"` in `st.set_page_config` (app.py line 104)
- [x] 2. Remove `editing_idx`, `adding` from session-state init and all references throughout app.py
- [x] 3. Remove the `+ Thêm nhóm` button and `hdr_col/add_col` columns
- [x] 4. Remove the entire for-loop rendering library rows (columns, checkbox, markdown, ✏, 🗑 buttons)
- [x] 5. Remove the `show_form` / `st.form("group_form")` block
- [x] 6. Add `import pandas as pd` (already available as Streamlit dep; no requirements.txt change)
- [x] 7. Add `_lib_to_df()` helper that converts `st.session_state.library` to a flat pandas DataFrame
- [x] 8. Add `_df_to_lib()` helper that reconstructs the library list from an edited DataFrame
- [x] 9. Render `st.data_editor` with appropriate `column_config` (Chọn, Tên nhóm, Group ID/URL, Cọc thấp, Cọc cao, Deadline, Bỏ qua)
- [x] 10. After `st.data_editor`, compare result with current library; if changed, update session state and call `_lib_save()`
- [x] 11. Update `openspec/specs/web-ui/spec.md` with MODIFIED requirement for the Group Library UI
- [x] 12. Validate with `openspec validate update-group-ui-wide-table --strict --no-interactive`
