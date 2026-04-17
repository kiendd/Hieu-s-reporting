# Proposal: add-docs-link

## Why
Users need a quick reference to usage instructions without having to search the repo manually.

## What Changes
Add a "📖 Hướng dẫn sử dụng" hyperlink in the page header, placed on the same row as the title using `st.columns`, pointing to:
`https://github.com/kiendd/Hieu-s-reporting/blob/main/docs/huong-dan-su-dung.md`

## Scope
- `app.py`: wrap `st.title` in a two-column row; right column renders the link via `st.markdown`
- `openspec/specs/web-ui/spec.md`: ADDED Requirement for the help link
