# Proposal: fix-library-localstorage-write

## Why
`_lib_save()` is called inside `@st.dialog` immediately before `st.rerun()`. `_lib_save()` works by rendering a `st_javascript(localStorage.setItem(...))` component. However, `@st.dialog` is implemented as a Streamlit fragment — when `st.rerun()` is raised inside a fragment, the fragment's current render is discarded before it reaches the browser. The `st_javascript` component therefore never executes, `localStorage` is never updated, and the library is lost on every page refresh.

## What Changes
Introduce a `needs_save` boolean in session state. Inside `_group_dialog`, replace `_lib_save(...)` with `st.session_state.needs_save = True`. In the main script body (outside any dialog/fragment), check `needs_save` and call `_lib_save()` there — the main render is always committed to the frontend before any rerun, so `localStorage.setItem` is guaranteed to execute.

No changes needed for the delete or checkbox handlers (they already run in the main body where the render is committed before the rerun).

## Scope
- `app.py` only: add `needs_save` to session-state init, replace `_lib_save` call in dialog with flag, add save block in main body
- No spec delta needed: the persistence requirement already exists and this restores intended behaviour
