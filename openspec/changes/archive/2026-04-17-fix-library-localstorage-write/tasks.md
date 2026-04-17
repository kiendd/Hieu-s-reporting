# Tasks: fix-library-localstorage-write

- [x] 1. Add `needs_save` (default `False`) to session-state init in `app.py`
- [x] 2. In `_group_dialog`: replace `_lib_save(st.session_state.library)` with `st.session_state.needs_save = True`
- [x] 3. In the main body (after the library list, before the date range section): add a block that calls `_lib_save(st.session_state.library)` and resets `needs_save = False` when the flag is set
- [x] 4. Validate with `openspec validate fix-library-localstorage-write --strict --no-interactive`
