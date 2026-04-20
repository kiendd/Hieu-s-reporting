# Tasks: add-weekly-report

## fpt_chat_stats.py

- [ ] 1. Add `analyze_weekly(messages, group_members, target_date_vn, deadline="20:00") -> dict` returning:
  - `target_date` (str, `YYYY-MM-DD`)
  - `deadline` (str, `HH:MM`)
  - `reports` (list of `{sender, sent_at_vn, is_late, text, extra_count}`, sorted by `sent_at_vn` ascending)
  - `late_list` (list of sender displayNames, sorted alphabetically)
  - `missing_list` (list of sender displayNames, sorted alphabetically)
- [ ] 2. Define module-level constants in `fpt_chat_stats.py`:
  - `WEEKLY_MIN_LENGTH = 150`
  - `WEEKLY_KEYWORDS = ("đánh giá", "báo cáo", "shop", "tttc", "vx", "trung tâm", "kết quả", "cọc")` (store lowercase; apply `content.lower()` when matching)
- [ ] 3. A message qualifies as a weekly report when ALL of: `msg["type"] == "TEXT"`, `len(msg["content"].strip()) >= WEEKLY_MIN_LENGTH`, `content.lower()` contains at least one element of `WEEKLY_KEYWORDS`, sender `displayName` in `group_members`, and VN-time date of `createdAt` equals `target_date_vn`. Do not call `detect_asm_reports` / `parse_asm_report`.
- [ ] 4. Multiple qualifying messages per sender → keep earliest (by `createdAt` UTC), set `extra_count = N_qualifying - 1`. Non-qualifying messages do not increment `extra_count`.
- [ ] 5. `is_late` is true iff `sent_at_vn.time() >= parsed(deadline)` on `target_date_vn`.
- [ ] 6. New `print_weekly_report(data)` writing to stdout with sections: header (date, deadline, counts), Chưa báo cáo, Muộn, Nội dung báo cáo.
- [ ] 7. New `write_weekly_excel(data, group_members, path)` producing two sheets:
  - `Tổng hợp tuần` (one row per member, status ∈ {`Đúng giờ`, `Muộn`, `Chưa báo cáo`} — use these exact Vietnamese literals; ordered by status, then `Giờ gửi` ascending, then name)
  - `Nội dung` (one row per report entry, ordered by `Giờ gửi` ascending; `Nội dung` column wrap-text enabled; `Trạng thái` uses `Đúng giờ` / `Muộn`)
- [ ] 8. Add CLI flag `--weekly YYYY-MM-DD`. When set:
  - Fetch messages for the half-open VN-day window `[target 00:00+07, target+1 00:00+07)`. Pagination SHALL stop only after the oldest fetched message is strictly older than `target 00:00+07`.
  - Fetch group members via `fetch_group_members`. On failure (exception, non-2xx, or empty list), log to stderr and exit non-zero; do NOT continue with an empty members list.
  - Resolve deadline from `config.json` `deadline` key, defaulting to `"20:00"`. Do not add a new CLI flag for deadline.
  - Call `analyze_weekly`, `print_weekly_report`, and (if `--excel PATH`) `write_weekly_excel`.
  - Reject combinations of `--weekly` with `--today` / `--from` / `--to` via argparse mutual-exclusion or an explicit check; error message SHALL name the conflicting flags.
- [ ] 9. Progress/debug → stderr; report output → stdout. (Existing convention.)

## app.py

- [ ] 10. Add a new section/tab "Báo cáo tuần" alongside the existing daily / multi-day views.
- [ ] 11. Controls: a single `st.date_input` for target date, reuse the group's deadline from library config, a Run button.
- [ ] 12. On Run: fetch messages for the VN day, fetch group members, call `analyze_weekly`, render: header metrics (đã báo cáo / muộn / chưa báo cáo counts), chưa báo cáo list, muộn list (name + time), a content table (sender / giờ gửi / trạng thái / nội dung với text wrap).
- [ ] 13. Download button: trigger `write_weekly_excel` to an in-memory buffer and serve via `st.download_button`.

## Validation

- [ ] 14. Update `openspec/specs/fpt-chat-stats/spec.md` and `openspec/specs/web-ui/spec.md` with the ADDED requirements from this change's spec deltas.
- [ ] 15. Validate with `openspec validate 2026-04-20-add-weekly-report --strict --no-interactive`.
- [ ] 16. Manual test: `--save raw.json` on a real weekend day, then `--load raw.json --weekly <that-day>` and verify late/missing lists match expected reality; verify content column shows full raw text; verify short acknowledgments in the group chat are NOT counted as reports.
