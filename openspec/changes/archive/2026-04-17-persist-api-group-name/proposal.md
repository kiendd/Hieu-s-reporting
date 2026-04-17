# Proposal: persist-api-group-name

## Why
When a user adds a group using only the ID (no custom label), the library stores the 8-character short ID as the label placeholder. On each run, the app fetches the real group name from the API and uses it as the tab label — but never writes it back to the library. The user sees the correct name during the run, but the library list still shows the ugly short ID, and the next run must fetch the name again.

## What Changes
In the analysis loop, after `fetch_group_info` returns a name and the current label equals the short-ID placeholder, write the real API name back to `st.session_state.library[idx]["label"]` and persist to localStorage via `_lib_save()`.

This is a one-time enrichment: once a real name is saved, future runs won't overwrite it (the label will no longer equal the short ID).

## Approach
Inside the `for entry in selected_groups` loop, after the existing `tab_label` resolution:
1. If `tab_label != entry["label"]` (i.e., the API name was used and differs from the stored label), find the matching library index by group ID and update `library[idx]["label"]`
2. Call `_lib_save()` once after the loop if any labels were updated (a `label_updated` flag)

Since this code runs in the main body (not inside `@st.dialog`), `_lib_save()` can be called directly without the `needs_save` flag workaround.

## Scope
- `app.py`: inside the `if run:` analysis loop
- `openspec/specs/multi-group-reporting/spec.md`: MODIFIED Requirement: Per-Group Tabbed Results — add label write-back behaviour
