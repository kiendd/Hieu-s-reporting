# Design: Fix weekend TTTC coverage in compliance tracking

**Date:** 2026-04-22
**Author:** phudq2
**Status:** Approved (pending spec review)

## Problem

Hieu Hoang Chi (product owner) phàn nàn ngày 2026-04-20 09:14 trong group chat:

> "Form báo cáo 2 ngày cuối tuần thứ 7, CN khác ông à / Nên nó k kéo được báo cáo / Nhờ ông cập nhật thêm form báo cáo của cuối tuần giúp tôi"

Tool không kéo được báo cáo TTTC cuối tuần. Đồng thời `check_asm_compliance` đôi khi list cùng 1 người 2 lần.

## Root cause analysis

Verified bằng 3 tuần data thật (`/tmp/raw_3weeks.json`, 103 messages):

### Bug 1 — Regex pre-filter quá chặt
`detect_asm_reports` (fpt_chat_stats.py line 263-274) yêu cầu **cả hai**:
- substring `shop`
- pattern `\d+\s*c[ọo]c` (vd "5 cọc")

Hệ quả:
- Shop VT canonical: ✅ pass
- Shop VT free-form ("SL cọc:" / "NV đã làm"): ❌ drop
- TTTC reports: ❌ drop 100% (không bao giờ chứa "N cọc")

Recall thực tế: 7/16 ≈ 44% trong sample.

### Bug 2 — Compliance check hardcoded daily_shop_vt
`check_asm_compliance` (line 440) và `check_late_reporters` (line 482) hardcode:
```python
if r.get("report_type") == "daily_shop_vt"
```
→ Dù TTTC report được extract thành công, compliance check vẫn bỏ qua.

### Bug 3 — "Hieu Hoang Chi" listed twice
API `participant` trả 2 entry cho Hieu (cùng `username=hieuhc`, cùng `displayName`, cùng `department`) nhưng khác `id` — 1 active (lastReadMessageId=103, admin) và 1 zombie (lastReadMessageId=0, không avatar). Đây là **2 user record khác nhau trong hệ thống** (data quality issue), không phải 2 người vật lý khác nhau.

`check_asm_compliance` iterate raw `members` → cả 2 entry đều xuất hiện trong missing list khi Hieu chưa nộp.

## Decisions (locked during brainstorming)

| # | Topic | Decision |
|---|---|---|
| 1 | Pre-filter approach | L2 heuristic: length ≥ 80 + ≥ 2 digits + ≥ 1 keyword (diacritic-insensitive). Recall 100% trên sample, precision ~89% (2 false positive sẽ được LLM tag `unknown` → filter downstream) |
| 2 | TTTC reporters | Cùng danh sách ASM với Shop VT — không có team riêng |
| 3 | TTTC deadline | 20:00 cùng ngày, strict (giống Shop VT) |
| 4 | Date bucketing | Theo `createdAt`, không dò ngày trong nội dung. Báo cáo trễ → coi như event ngày sau, ngày trước vẫn missing |
| 5 | Compliance API shape | Thêm param `report_type` required (không default) — caller phải route theo weekday |
| 6 | Dedupe strategy | **Filter zombie members** thay vì dedupe theo username/id. Member với `lastReadMessageId == 0` → drop khỏi compliance check (semantically: không active trong group → không nên tính vào "ai phải báo cáo") |
| 7 | Refactor scope | Approach 1 — patch tối thiểu, giữ shape hiện tại; không gộp 2 hàm compliance |

## Components

### 1. `detect_report_candidates` (replaces `detect_asm_reports`)

**File:** `fpt_chat_stats.py`, replace lines 263-274.

```python
import unicodedata

_REPORT_KEYWORDS = (
    "shop", "tttc", "vx hcm", "coc",
    "doanh thu", "dt %", "hot", "ra tiem",
    "tvv", "tu van", "kh", "bill",
)

def _strip_diacritics(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))

def detect_report_candidates(messages: list) -> list:
    """L2 heuristic pre-filter: length ≥ 80 + ≥ 2 digits + ≥ 1 keyword.
    Cheap signal — LLM extraction phía sau quyết định loại + parse fields."""
    out = []
    digit_re = re.compile(r"\d")
    for msg in messages:
        if msg.get("type") != "TEXT":
            continue
        content = msg.get("content") or ""
        if len(content) < 80:
            continue
        if len(digit_re.findall(content)) < 2:
            continue
        normalized = _strip_diacritics(content)
        if not any(kw in normalized for kw in _REPORT_KEYWORDS):
            continue
        out.append(msg)
    return out
```

Update `extract_all_reports` (line 289):
```python
candidates = detect_report_candidates(messages)
```

### 2. Parametrize compliance functions

**File:** `fpt_chat_stats.py`, update signatures of `check_asm_compliance` (line 435) and `check_late_reporters` (line 476).

```python
ReportType = Literal["daily_shop_vt", "weekend_tttc"]

def check_asm_compliance(
    parsed_reports: list,
    members: list,
    target_date_str: str,
    report_type: ReportType,           # NEW, required
    deadline_hhmm: str = "20:00",
    skip_list: list | None = None,
) -> list:
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == report_type   # was: hardcoded "daily_shop_vt"
                      and r.get("parse_error") is None]
    members = [m for m in members if _is_active_member(m)]     # NEW: zombie filter
    # ... rest unchanged

def check_late_reporters(
    parsed_reports: list,
    target_date_str: str,
    report_type: ReportType,           # NEW, required
    deadline_hhmm: str = "20:00",
) -> list:
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == report_type   # was: hardcoded
                      and r.get("parse_error") is None]
    # ... rest unchanged
```

`report_type` is **required** (no default) — forces caller to think about routing for every new callsite. Default would create silent bugs.

### 3. Day-of-week routing helper

**File:** `fpt_chat_stats.py`, new helper near top of compliance section.

```python
from datetime import date

def report_type_for_date(target_date: date) -> ReportType:
    """Mon-Fri → Shop VT daily; Sat-Sun → TTTC weekend."""
    return "daily_shop_vt" if target_date.weekday() < 5 else "weekend_tttc"
```

Used by:
- `main()` single-day flow (line ~1354): wrap calls to `check_asm_compliance` and `check_late_reporters`
- `app.py` Streamlit single-day flow: same wrap
- `analyze_multiday`: route per-day inside the day-loop (T2-T6 daily, T7-CN weekend)
- `analyze_weekly` / `--weekly`: route per-day inside the week-loop

### 4. Zombie member filter

**File:** `fpt_chat_stats.py`, new helper near `check_asm_compliance`.

```python
def _is_active_member(m: dict) -> bool:
    """Active = đã từng đọc tin nhắn trong group.
    Loại zombie account (data quality issue: cùng người có 2 user record)."""
    return (m.get("lastReadMessageId") or 0) > 0
```

Apply in:
- `check_asm_compliance` (filter `members` at top)
- `analyze_weekly` member_names build (line 648, 1023)
- Any future code iterating `group_members` for "ai chưa làm" purposes

**Do NOT apply for display purposes** — sender metadata lookup must still see raw members so display name resolution works for legacy/inactive senders.

## Data flow

```
Messages
  → detect_report_candidates    (L2 heuristic, ~89% precision, 100% recall)
  → llm_extractor.extract_reports (per-candidate, parallel, cached)
  → parsed_reports (flat list, mixed daily_shop_vt + weekend_tttc + unknown)
  → analyze_asm_reports (filter daily_shop_vt)
  → analyze_tttc_reports (filter weekend_tttc)
  → check_asm_compliance(report_type=...)  ← caller routes by weekday
  → check_late_reporters(report_type=...)  ← caller routes by weekday
       ↑
       members → _is_active_member filter (drop zombies)
```

## Error handling

- **L2 false positives** (non-report messages passing pre-filter): LLM returns `report_type="unknown"` → existing `parse_error` filter drops them downstream. Cost: ~2 extra LLM calls per 100 messages in observed sample. Cache absorbs repeats.
- **Members API returns empty / errors**: existing fallback (line 1346 `members = []`) preserved. Compliance check returns empty missing list.
- **Date in invalid format**: existing `ValueError` handling preserved.

## Testing

**File:** `tests/test_compliance.py` (new, ~150 lines)

```
detect_report_candidates:
  test_l2_keeps_shop_vt_canonical
  test_l2_keeps_tttc_report                    # THE BUG regression
  test_l2_keeps_shop_vt_freeform
  test_l2_drops_short_chat
  test_l2_drops_no_keyword
  test_l2_diacritic_insensitive

check_asm_compliance(report_type=...):
  test_compliance_daily_filters_only_shop_vt
  test_compliance_weekend_filters_only_tttc
  test_compliance_skips_zombie_members
  test_compliance_keeps_active_member_low_lastread
  test_compliance_hieu_listed_once_when_zombie_dup   # regression

check_late_reporters(report_type=...):
  test_late_reporters_daily_only
  test_late_reporters_weekend_only

report_type_for_date:
  test_routing_monday_to_friday_returns_daily
  test_routing_saturday_sunday_returns_weekend

Multiday:
  test_multiday_routes_per_day
```

Test data: dict literals for `members` and `parsed_reports`. No LLM mocking, no fixture files. Pattern follows existing `tests/test_llm_extractor.py`.

Existing golden-file tests (`tests/test_templates.py`) cover LLM extractor regression — untouched.

## Out of scope

- Refactoring `check_asm_compliance` + `check_late_reporters` into a unified engine (Approach 2 from brainstorming). Two functions return different shapes; gộp không sạch.
- Auto-detecting `report_type` from weekday inside the function (Approach 3). Hides logic, hard to override for ad-hoc checks.
- Date bucketing by content (LLM extracting "báo cáo ngày 18/04"). User chose to keep `createdAt` semantic.
- Disambiguation UI for legitimate same-displayName members. Out of band — should be solved by FPT data quality, not by this tool.
- Adding TTTC compliance check to weekly Excel export. Existing `--weekly` flag will route per-day automatically; no schema change needed for v1.

## Migration / backwards compatibility

None needed — internal tool, no API consumers. CLI flags unchanged. Cache files (`.llm_cache/*`) unchanged (keyed by content hash, not affected).

## File touches

- `fpt_chat_stats.py`: ~50 lines diff (replace pre-filter, add helpers, update 2 compliance signatures, update 4 callsites)
- `app.py`: ~10 lines (route by weekday at single-day callsite)
- `tests/test_compliance.py`: ~150 lines new
- `CLAUDE.md`: 1-paragraph update — pipeline section to mention L2 heuristic and weekday-routed compliance
- `openspec/changes/2026-04-22-fix-tttc-coverage/`: proposal + spec delta + tasks
