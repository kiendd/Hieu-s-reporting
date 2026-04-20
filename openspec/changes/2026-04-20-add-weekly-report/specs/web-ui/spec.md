## ADDED Requirements

### Requirement: Weekly Report UI Surface
`app.py` SHALL expose a user-visible section labelled `Báo cáo tuần` alongside the existing daily / multi-day report surfaces. The section SHALL provide:
- A single `st.date_input` control for the target VN-time date.
- A Run button that triggers the weekly pipeline.

The deadline value used for the pipeline SHALL come from the currently selected group's library entry (same source as the daily deadline). The weekly section SHALL NOT introduce a new persistent setting for the deadline; it reuses the per-group `deadline` already stored in `_LIB_KEY`.

When the user clicks Run, the app SHALL:
1. Fetch messages for the target VN day using the existing session/auth flow.
2. Fetch group members.
3. Call `analyze_weekly` from `fpt_chat_stats`.
4. Render the following sections in order, using Vietnamese labels:
   - A summary row with three counters: `Đã báo cáo`, `Muộn`, `Chưa báo cáo`.
   - A `Chưa báo cáo` list (names only).
   - A `Muộn` list (name + VN send time).
   - A `Nội dung` table with columns `Người báo cáo`, `Giờ gửi`, `Trạng thái`, `Nội dung`. The `Nội dung` column SHALL display full raw text (wrap or scroll, never truncate).
5. Provide a download button that serves the weekly Excel output via `st.download_button`, using `write_weekly_excel` against an in-memory buffer.

#### Scenario: Weekly section does not affect daily flow
- **WHEN** the user runs the existing daily or multi-day report
- **THEN** the weekly section is not evaluated and does not alter the daily output in any way

#### Scenario: No reports on target day
- **GIVEN** zero qualifying messages were sent on the target VN day
- **WHEN** the user clicks Run
- **THEN** the summary shows `Đã báo cáo: 0`, `Chưa báo cáo` lists every group member, `Muộn` is empty, and the `Nội dung` table is empty (still rendered with headers)
