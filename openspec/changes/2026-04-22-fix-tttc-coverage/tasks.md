# Tasks

All tasks completed in commits on `feat/llm-parallel-extraction` branch.

- [x] **Task 1:** L2 pre-filter `detect_report_candidates` + `_strip_diacritics` + `_REPORT_KEYWORDS`. Update `extract_all_reports` caller. Delete old `detect_asm_reports`. (commit `6c7b1a8`)
- [x] **Task 2:** `ReportType = Literal["daily_shop_vt", "weekend_tttc"]` alias + `report_type_for_date(date) -> ReportType` helper. (commit `190a537`)
- [x] **Task 3:** `_is_active_member(m) -> bool` zombie filter helper. (commit `df61ce2`)
- [x] **Task 4:** Parametrize `check_asm_compliance` với required `report_type` kwarg + apply zombie filter + update callers (fpt_chat_stats main, app.py × 2). (commit `575e0e3`)
- [x] **Task 5:** Parametrize `check_late_reporters` với required `report_type` kwarg + update app.py caller. (commit `c65bb02`)
- [x] **Task 6:** Per-day routing trong `analyze_multiday` (accept cả 2 types, filter per-day theo weekday inside bucketing loop). (commit `0641f62`)
- [x] **Task 7:** Apply `_is_active_member` filter trong `analyze_weekly` + `write_weekly_excel` (member_names build sites). (commit `5e64c97`)
- [x] **Task 8:** End-to-end smoke test — pre-filter delta 8 → 18 candidates trên `/tmp/raw_3weeks.json` (8 TTTC mới catched, 2 false positive sẽ LLM-tag `unknown`). (commit `77a976c`)
- [x] **Task 9:** Update `CLAUDE.md` — Pipeline section + Compliance routing paragraph. (commit `6ef5ab3`)
- [x] **Task 10:** OpenSpec change proposal — proposal.md + tasks.md + spec deltas + validate. (this commit)

## Test coverage

`tests/test_compliance.py` — 30 test cases, all green:
- `TestDetectReportCandidates` (9): canonical / TTTC / freeform / short / no-keyword / 1-digit / diacritic / non-TEXT / strip helper
- `TestReportTypeForDate` (4): Mon / Fri / Sat / Sun
- `TestIsActiveMember` (5): active / zero / missing / None / low lastread
- `TestCheckAsmCompliance` (8): daily filter / weekend filter / zombie skip / active-keep-low-lastread / **Hieu × 1 regression** / parse_error / late / skip_list
- `TestCheckLateReporters` (3): daily filter / weekend filter / on-time
- `TestAnalyzeMultidayRoutesPerDay` (1): Fri Shop VT + Sat TTTC both count

Full suite: 82 tests pass (existing golden + llm_extractor + new compliance).
