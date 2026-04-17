# Tasks: replace-inline-edit-with-dialog

- [x] 1. Bump `streamlit>=1.32.0` → `>=1.36.0` in `requirements.txt`
- [x] 2. Remove `import pandas as pd` from `app.py`
- [x] 3. Remove `_lib_to_df()` and `_df_to_lib()` helpers from `app.py`
- [x] 4. Add `dialog_idx` to session-state init (replace the data_editor approach)
- [x] 5. Add `@st.dialog("Thêm / Sửa nhóm")` function `_group_dialog(idx)` with all form fields (url, label, deposit_low, deposit_high, deadline, skip) and Save / Huỷ buttons
- [x] 6. Replace the `st.data_editor` block with a `st.columns` header + per-row layout showing: checkbox (selected), label+short_id+config summary, ✏ button, 🗑 button
- [x] 7. Add `+ Thêm nhóm` button above the list that sets `dialog_idx = -1` and calls `st.rerun()`
- [x] 8. Open the dialog at the top of the library section if `dialog_idx is not None`
- [x] 9. Update `openspec/specs/web-ui/spec.md` with MODIFIED Group Library requirement
- [x] 10. Validate with `openspec validate replace-inline-edit-with-dialog --strict --no-interactive`
