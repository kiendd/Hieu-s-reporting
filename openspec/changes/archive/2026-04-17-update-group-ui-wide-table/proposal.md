# Proposal: update-group-ui-wide-table

## Summary
Two cosmetic/UX improvements to the web UI:
1. Switch page layout from `"centered"` to `"wide"` so users can see more content horizontally.
2. Replace the custom column-based group library list (with separate add/edit form) with a `st.data_editor` table — eliminating oversized emoji buttons and simplifying session-state management.

## Motivation
- The centered layout wastes space on wide monitors; the group list, results tables, and Excel data all benefit from wider rendering.
- The current ✏ / 🗑 buttons are disproportionately large because Streamlit renders icon-only buttons at full row height in a narrow column. A `st.data_editor` replaces them with native inline cell editing and row-level deletion.

## Approach

### 1. Wide layout
`st.set_page_config(layout="wide")` — one-line change.

### 2. Group library as `st.data_editor`
Flatten each library entry into a row:

| Column | Type | Notes |
|--------|------|-------|
| Chọn | bool | `selected` |
| Tên nhóm | str | `label` |
| Group ID / URL | str | `url` |
| Cọc thấp | int | `config.deposit_low` |
| Cọc cao | int | `config.deposit_high` |
| Deadline | str | `config.deadline` |
| Bỏ qua | str | `config.skip` |

Use `num_rows="dynamic"` so users can add rows at the bottom and delete rows via the row-selector checkbox. After each render, compare the returned DataFrame with current session state; if changed, update `st.session_state.library` and write to localStorage.

**Session state simplification**: `editing_idx`, `adding`, `show_form`, and the entire `st.form("group_form")` block are removed. The header `+ Thêm nhóm` button is also removed.

**New entries**: When a row is added via the table, `selected` defaults to `True` and config fields use `_LIB_DEFAULTS`.

## Scope
- `app.py`: layout flag, remove old list+form code, add data_editor block
- `openspec/specs/web-ui/spec.md`: update Group Library UI requirement

## Out of Scope
- No changes to `fpt_chat_stats.py`, `requirements.txt`, or any other spec
