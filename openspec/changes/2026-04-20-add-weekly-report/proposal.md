# Proposal: add-weekly-report

## Why
On designated weekly-reporting days (e.g. weekends), ASMs submit a different class of report than the Mon–Fri shop reports — see `templates/weekend/*` for representative examples. The current tool's detection (`detect_asm_reports`) looks for `shop` + `N cọc` and therefore sees **zero reports on weekend days**, so every ASM is incorrectly flagged as non-compliant on those days.

The client's explicit ask (verbatim):

> Tôi chỉ cần tổng hợp như báo cáo ngày trong tuần ông đang làm cho tôi đấy
> Quan trọng nhất là check người chưa báo cáo, báo cáo muộn
> Nội dung thì chỉ kéo từ text từ các bạn ASM viết
> Cuối tuần cũng vậy chỉ cần text và người báo cáo muộn và k báo cáo

Summarised:
1. Same shape as the existing daily report.
2. Primary value = late and missing detection.
3. Content = raw text, no parsing.
4. Weekend treatment = identical, no special metrics.

## What changes

A new single-day mode, **Báo cáo tuần (Weekly Report)**, that:
- Runs against one user-chosen date.
- Classifies messages as "a report sent" using a length + keyword heuristic (body ≥ 150 chars AND contains at least one of `Đánh giá / báo cáo / shop / TTTC / VX / trung tâm / Kết quả / cọc`, case-insensitive). Short acknowledgments and off-topic chatter do NOT count as reports.
- Produces the same three-bucket view as daily: đúng giờ / muộn / chưa báo cáo.
- Dumps each ASM's raw text verbatim — no section parsing, no metric extraction.

Surfaces:
- CLI: `--weekly YYYY-MM-DD`
- Streamlit: a new tab/section "Báo cáo tuần" with a single date picker and Run button.

## Design notes

- New function `analyze_weekly(messages, group_members, target_date_vn, deadline)` in `fpt_chat_stats.py`. It does NOT call `detect_asm_reports` or `parse_asm_report` — weekly detection is independent of the daily shop-format heuristic.
- "Report sent" = a message where `type == "TEXT"`, body (`content`) has length ≥ `WEEKLY_MIN_LENGTH` (= 150) after strip, body contains at least one substring from `WEEKLY_KEYWORDS` (case-insensitive) — `{Đánh giá, báo cáo, shop, TTTC, VX, trung tâm, Kết quả, cọc}`, sender's `displayName` is in `group_members`, and the VN-time date equals `target_date_vn`.
- Classification constants live as module-level variables in `fpt_chat_stats.py` so the values are tunable in one place. Not exposed via CLI or config for this change.
- If an ASM sends multiple **qualifying** messages on that day, use the **earliest** one as their report. Include a note `(+N tin nhắn khác)` in the content row so the reviewer knows there are more. Non-qualifying messages (short / no keyword) are not counted toward `extra_count`.
- "Late" = the earliest qualifying message's VN-time is ≥ deadline on `target_date_vn`.
- "Missing" = the ASM is in `group_members` but has no qualifying message on `target_date_vn`.
- Deadline default = `20:00` VN, reusing the existing per-group deadline setting (no new config key).
- Output:
  - Print to stdout with three sections (chưa báo cáo, muộn, nội dung) + header line.
  - Excel with two new sheets: `Tổng hợp tuần` (ASM × trạng thái × giờ gửi) and `Nội dung` (ASM × giờ gửi × trạng thái × nội dung).
- No changes to `analyze_multiday`, `analyze_asm_reports`, `parse_asm_report`, or daily compliance logic — weekly is a parallel, independent path.

## Out of scope

- Parsing numeric metrics (doanh thu, TB bill, %HT, tỉ trọng HOT) from weekend/TTTC reports. Client explicitly said content = raw text only.
- Multi-day weekly aggregation (e.g. Mon–Sun rollup). Weekly = one single designated day.
- Distinguishing between shop-format vs TTTC-format weekly submissions. Weekly detection is format-agnostic.
- Auto-selecting the "weekly day" based on day of week. User picks the date explicitly.

## Scope of files touched

- `fpt_chat_stats.py`: new `analyze_weekly()` function, new `print_weekly_report()` helper, new `write_weekly_excel()` helper (or extend `write_asm_excel` with a mode flag — decide during implementation). New `--weekly <date>` CLI argument routed through `main`.
- `app.py`: new "Báo cáo tuần" tab/section with date picker, Run button, and rendering for the three buckets + content table.
- `openspec/specs/fpt-chat-stats/spec.md`: add requirement for `analyze_weekly`.
- `openspec/specs/web-ui/spec.md`: add requirement for the weekly UI surface.
