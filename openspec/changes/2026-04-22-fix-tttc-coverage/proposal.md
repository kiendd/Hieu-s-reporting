# Proposal: fix-tttc-coverage

## Why

Hieu Hoang Chi (product owner) phàn nàn ngày 2026-04-20 09:14 trong group chat:

> "Form báo cáo 2 ngày cuối tuần thứ 7, CN khác ông à / Nên nó k kéo được báo cáo / Nhờ ông cập nhật thêm form báo cáo của cuối tuần giúp tôi"

Tool không kéo được báo cáo TTTC cuối tuần. Đồng thời `check_asm_compliance` đôi khi list cùng 1 người 2 lần.

**Verified bằng 3 tuần data thật** (`/tmp/raw_3weeks.json`, 103 messages):

1. **Pre-filter quá chặt.** `detect_asm_reports` (regex `shop` + `\d+\s*c[ọo]c`) yêu cầu cả hai pattern → drop 100% TTTC reports (TTTC không bao giờ chứa "N cọc") + drop Shop VT free-form variants. Recall thực tế 8/16 ≈ 50% trên sample.

2. **Compliance check hardcoded.** `check_asm_compliance` (line 440) và `check_late_reporters` (line 482) hardcode `r.get("report_type") == "daily_shop_vt"` → dù TTTC report được extract thành công, compliance check vẫn bỏ qua.

3. **Hieu Hoang Chi listed twice.** API `participant` trả 2 entry cho Hieu (cùng username, cùng displayName) — 1 active (lastReadMessageId=103, admin) và 1 zombie (lastReadMessageId=0). `check_asm_compliance` iterate raw `members` → cả 2 entry xuất hiện trong missing list.

## What changes

- **L2 heuristic pre-filter** thay regex chật. `detect_report_candidates` yêu cầu `length ≥ 80` + `≥ 2 digits` + `≥ 1 keyword` (diacritic-insensitive). Recall 100% trên sample 3 tuần (16/16 reports pass), precision ~89% (2 false positive sẽ được LLM tag `unknown` → filter downstream qua `parse_error`).

- **Parametrize compliance functions.** `check_asm_compliance` và `check_late_reporters` thêm param `report_type: ReportType` REQUIRED (không default — silent-bug guard). Caller phải route theo weekday qua helper mới `report_type_for_date(date)` (Mon-Fri → `daily_shop_vt`, Sat-Sun → `weekend_tttc`).

- **Per-day routing trong `analyze_multiday`.** Accept cả 2 report types ở đầu function, filter per-day theo `report_type_for_date(vn_dt.date())` trong bucketing loop. Cùng 1 sender báo cáo Shop VT thứ Sáu + TTTC thứ Bảy → đều count cho ngày tương ứng.

- **Zombie member filter.** Helper mới `_is_active_member(m)` return `(m.get("lastReadMessageId") or 0) > 0`. Apply trong `check_asm_compliance`, `analyze_weekly` (member_names build), `write_weekly_excel` (member_names build). KHÔNG apply cho display/sender lookup (sender metadata phải vẫn thấy raw members).

- **Update 4 callsites:** `fpt_chat_stats.main()`, `app.py × 3` (2× check_asm_compliance, 1× check_late_reporters).

- **Test suite mới** (`tests/test_compliance.py`, ~30 test cases) cover: L2 pre-filter (9), routing helper (4), zombie filter (5), parametrized compliance (8), parametrized late reporters (3), per-day multiday (1).

## Decisions table

| # | Topic | Decision |
|---|---|---|
| 1 | Pre-filter approach | L2 heuristic: length ≥ 80 + ≥ 2 digits + ≥ 1 keyword (diacritic-insensitive). Recall 100% trên sample, precision ~89% |
| 2 | TTTC reporters | Cùng danh sách ASM với Shop VT — không có team riêng |
| 3 | TTTC deadline | 20:00 cùng ngày, strict (giống Shop VT) |
| 4 | Date bucketing | Theo `createdAt`, không dò ngày trong nội dung. Báo cáo trễ → coi như event ngày sau |
| 5 | Compliance API shape | Param `report_type` REQUIRED (không default) — caller phải route theo weekday |
| 6 | Dedupe strategy | Filter zombie members (lastReadMessageId == 0) thay vì dedupe theo username/id |
| 7 | Refactor scope | Approach 1 — patch tối thiểu, giữ shape hiện tại; không gộp 2 hàm compliance |

## Out of scope

- Refactoring `check_asm_compliance` + `check_late_reporters` thành unified engine (Approach 2). Hai functions return shape khác nhau; gộp không sạch.
- Auto-detecting `report_type` từ weekday inside the function (Approach 3). Hides logic, hard to override.
- Date bucketing by content (LLM extracting "báo cáo ngày 18/04"). User chose to keep `createdAt` semantic.
- Disambiguation UI for legitimate same-displayName members. Out of band — should be solved by FPT data quality.
- Adding TTTC compliance check to weekly Excel export. Existing `--weekly` route per-day automatically.

## References

- Design spec: `docs/superpowers/specs/2026-04-22-fix-tttc-coverage-design.md`
- Implementation plan: `docs/superpowers/plans/2026-04-22-fix-tttc-coverage.md`
