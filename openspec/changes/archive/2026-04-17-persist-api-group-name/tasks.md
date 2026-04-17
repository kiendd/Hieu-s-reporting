# Tasks: persist-api-group-name

- [x] 1. In the `for entry in selected_groups` loop, after `tab_label` is resolved from API name, check if it differs from the stored `entry["label"]`
- [x] 2. If so, find the matching index in `st.session_state.library` by group ID and update its `label` field; set a `_label_updated` flag
- [x] 3. After the loop, if `_label_updated`, call `_lib_save(st.session_state.library)` to persist to localStorage
- [x] 4. Update `openspec/specs/multi-group-reporting/spec.md` with MODIFIED requirement
- [x] 5. Validate with `openspec validate persist-api-group-name --strict --no-interactive`
