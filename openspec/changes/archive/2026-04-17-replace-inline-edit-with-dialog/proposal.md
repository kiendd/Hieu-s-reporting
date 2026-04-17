# Proposal: replace-inline-edit-with-dialog

## Why
Inline cell editing in `st.data_editor` is error-prone: users can accidentally modify values while scrolling, there is no explicit confirm step, and the table renders all editable fields at once making the UI cluttered. A modal dialog provides a dedicated, intentional editing surface.

## What Changes
Replace the `st.data_editor` group library table with:

1. **Read-only display table** — `st.data_editor` with `disabled=True` keeping only the `selected` checkbox editable inline (for quick include/exclude toggling without a dialog).
2. **Row-level action buttons** — an ✏ (edit) and 🗑 (delete) button per row, rendered in columns alongside the table or as a separate column.
3. **`@st.dialog` add/edit form** — a Streamlit modal dialog (`@st.dialog` decorator, stable since 1.36.0) that opens when the user clicks `+ Thêm nhóm` or ✏. Contains the same fields as the previous `st.form`: URL/ID, display label, deposit_low, deposit_high, deadline, skip.

Session state changes:
- Remove `dialog_idx` placeholder (add new `dialog_idx` key: `None` = closed, `-1` = add new, `≥0` = edit row at index).
- Remove `_lib_to_df`, `_df_to_lib` helpers and `pandas` import (no longer needed).

`requirements.txt`: bump `streamlit>=1.32.0` → `>=1.36.0` to formally declare the `@st.dialog` dependency.

## Scope
- `app.py`: remove data_editor block, add column-row list + `@st.dialog` function
- `requirements.txt`: version bump
- `openspec/specs/web-ui/spec.md`: MODIFIED Requirement: Group Library Table UI → Group Library Dialog UI
