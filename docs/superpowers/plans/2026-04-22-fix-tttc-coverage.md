# Fix Weekend TTTC Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 bugs blocking Hieu's weekend TTTC compliance: regex pre-filter drops TTTC reports, `check_asm_compliance` hardcoded to daily, and zombie member entry double-listing.

**Architecture:** Patch in place (Approach 1 from spec) — replace narrow regex pre-filter with L2 heuristic (length+digits+keyword), parametrize compliance functions with required `report_type`, route per weekday at callers, drop zombie members via `lastReadMessageId == 0` filter.

**Tech Stack:** Python 3.11, pytest, existing `fpt_chat_stats.py` + `app.py` + `llm_extractor.py` codebase.

**Spec:** `docs/superpowers/specs/2026-04-22-fix-tttc-coverage-design.md`

---

## File Structure

| File | Action | Purpose |
|---|---|---|
| `fpt_chat_stats.py` | Modify | Replace pre-filter, add helpers (`_strip_diacritics`, `_REPORT_KEYWORDS`, `detect_report_candidates`, `report_type_for_date`, `_is_active_member`, `ReportType` alias), parametrize 2 compliance functions, update 5 callsites |
| `app.py` | Modify | Update 3 callsites with `report_type` arg routed by weekday |
| `tests/test_compliance.py` | Create | ~150 lines pytest covering pre-filter L2 + parametrized compliance + zombie filter + routing |
| `CLAUDE.md` | Modify | 1-paragraph update — Pipeline section mentions L2 + weekday routing |
| `openspec/changes/2026-04-22-fix-tttc-coverage/proposal.md` | Create | OpenSpec proposal (per repo workflow) |
| `openspec/changes/2026-04-22-fix-tttc-coverage/tasks.md` | Create | Task list mirroring this plan |
| `openspec/changes/2026-04-22-fix-tttc-coverage/specs/fpt-chat-stats/spec.md` | Create | Spec delta updating MODIFIED requirements |

---

## Task 1: L2 pre-filter `detect_report_candidates`

**Files:**
- Test: `tests/test_compliance.py` (create)
- Modify: `fpt_chat_stats.py` (replace `detect_asm_reports` lines 263-274; update `extract_all_reports` line 289)

- [ ] **Step 1.1: Write failing tests for L2 pre-filter**

Create `tests/test_compliance.py`:

```python
"""Tests for L2 pre-filter, parametrized compliance, zombie filter, weekday routing."""
import pytest
from fpt_chat_stats import (
    detect_report_candidates,
    _strip_diacritics,
)


def _msg(content, msg_type="TEXT"):
    return {"type": msg_type, "content": content}


class TestDetectReportCandidates:
    def test_keeps_shop_vt_canonical(self):
        text = ("Dạ em xin gửi báo cáo vệ tinh ngày 16/04: "
                "Shop: 223B Cống Quỳnh / Kết quả: 5 cọc | 12 KH tư vấn / "
                "đã làm: tích cực tư vấn / vấn đề: khách ít")
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_keeps_tttc_report(self):
        # Regression: this format used to be dropped by the old "shop + N cọc" regex
        text = ("Dạ em gửi báo cáo TTTC 58149 HCM 406B Trương Công Định / "
                "- Kết quả: DT 95% / HOT 12% / TB bill 2.3tr / "
                "- Vấn đề: khách tiêm lẻ / - Hành động: tăng tư vấn combo")
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_keeps_shop_vt_freeform(self):
        text = ("Em gửi báo cáo ngày 16/04 hỗ trợ tại shop LC HCM 24 Vĩnh Viễn. "
                "- SL cọc: 52 cọc - NV đã làm: gọi 30 KH / "
                "Cần cải thiện: tỷ lệ chốt thấp / Kế hoạch ngày mai: tập trung KH cũ")
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_drops_short_chat(self):
        assert detect_report_candidates([_msg("ok 👍")]) == []
        assert detect_report_candidates([_msg("đến giờ ăn trưa rồi")]) == []

    def test_drops_no_keyword(self):
        # Long text, has digits, but no report keyword
        text = "x" * 100 + " 12 34 nhưng đây là chuyện phiếm về thời tiết"
        assert detect_report_candidates([_msg(text)]) == []

    def test_drops_one_digit_only(self):
        text = "TTTC quận 1 hôm nay khách ít chỉ có 5 người ghé thăm thôi" + "x" * 50
        # Only 1 digit — fails ≥2 digits filter
        assert detect_report_candidates([_msg(text)]) == []

    def test_diacritic_insensitive(self):
        # User typed without diacritics ("coc" instead of "cọc")
        text = ("Dạ em bao cao shop ABC ngay 16/04 - SL coc: 5 - 12 KH tu van - "
                "ra tiem: 3 - kế hoạch ngày mai: tăng tư vấn") + "x" * 20
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_drops_non_text_message_type(self):
        text = "Shop ABC: 5 cọc, 12 KH tư vấn, ra tiêm 3, đã làm tốt" + "x" * 50
        assert detect_report_candidates([_msg(text, msg_type="IMAGE")]) == []

    def test_strip_diacritics(self):
        assert _strip_diacritics("Cọc Việt Nam") == "coc viet nam"
        assert _strip_diacritics("ĐÃ LÀM") == "da lam"
```

- [ ] **Step 1.2: Run test to verify it fails**

Run: `pytest tests/test_compliance.py::TestDetectReportCandidates -v`
Expected: FAIL with `ImportError: cannot import name 'detect_report_candidates'`

- [ ] **Step 1.3: Implement L2 pre-filter**

Edit `fpt_chat_stats.py` — add `import unicodedata` near top (after `import sys`), then replace lines 263-274:

```python
_REPORT_KEYWORDS = (
    "shop", "tttc", "vx hcm", "coc",
    "doanh thu", "dt %", "hot", "ra tiem",
    "tvv", "tu van", "kh", "bill",
)


def _strip_diacritics(s: str) -> str:
    """Lower + strip Vietnamese diacritics for keyword matching tolerance."""
    nfkd = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def detect_report_candidates(messages: list) -> list:
    """L2 heuristic pre-filter: length ≥ 80 + ≥ 2 digits + ≥ 1 keyword.

    Cheap signal — LLM extraction phía sau quyết định loại + parse fields.
    Diacritic-insensitive keyword match (user gõ thiếu dấu vẫn pass).
    """
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

Then update line 289 in `extract_all_reports`:

```python
candidates = detect_report_candidates(messages)
```

Delete the old `detect_asm_reports` function entirely (lines 263-274 originally).

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `pytest tests/test_compliance.py::TestDetectReportCandidates -v`
Expected: PASS — all 9 tests green.

- [ ] **Step 1.5: Run full test suite to verify no regression**

Run: `pytest -v`
Expected: All existing tests still pass (golden file tests, llm_extractor tests).

- [ ] **Step 1.6: Commit**

```bash
git add tests/test_compliance.py fpt_chat_stats.py
git commit -m "feat: thay regex pre-filter chật bằng L2 heuristic (length+digits+keyword)

Pre-filter cũ yêu cầu 'shop' + 'N cọc' nên drop 100% TTTC report.
L2 heuristic recall 100% trên sample 3 tuần, precision ~89%
(2 false positive sẽ bị LLM tag unknown → filter downstream).
Diacritic-insensitive keyword match.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: `ReportType` alias + `report_type_for_date` helper

**Files:**
- Test: `tests/test_compliance.py` (append)
- Modify: `fpt_chat_stats.py` (add type alias + helper near top of compliance section, ~line 430)

- [ ] **Step 2.1: Write failing tests for routing helper**

Append to `tests/test_compliance.py`:

```python
from datetime import date
from fpt_chat_stats import report_type_for_date


class TestReportTypeForDate:
    def test_monday_returns_daily(self):
        assert report_type_for_date(date(2026, 4, 20)) == "daily_shop_vt"

    def test_friday_returns_daily(self):
        assert report_type_for_date(date(2026, 4, 17)) == "daily_shop_vt"

    def test_saturday_returns_weekend(self):
        assert report_type_for_date(date(2026, 4, 18)) == "weekend_tttc"

    def test_sunday_returns_weekend(self):
        assert report_type_for_date(date(2026, 4, 19)) == "weekend_tttc"
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `pytest tests/test_compliance.py::TestReportTypeForDate -v`
Expected: FAIL with `ImportError: cannot import name 'report_type_for_date'`

- [ ] **Step 2.3: Add type alias + helper**

Edit `fpt_chat_stats.py` — at top of file after `from __future__ import annotations` (around line 14), add:

```python
from typing import Literal

ReportType = Literal["daily_shop_vt", "weekend_tttc"]
```

Then add helper just before `def check_asm_compliance` (around line 434):

```python
def report_type_for_date(target_date: _date) -> ReportType:
    """Mon-Fri (weekday 0-4) → Shop VT daily; Sat-Sun (5-6) → TTTC weekend."""
    return "daily_shop_vt" if target_date.weekday() < 5 else "weekend_tttc"
```

Note: `_date` is the existing alias for `datetime.date` (see line 22 import).

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `pytest tests/test_compliance.py::TestReportTypeForDate -v`
Expected: PASS — 4 green.

- [ ] **Step 2.5: Commit**

```bash
git add tests/test_compliance.py fpt_chat_stats.py
git commit -m "feat: thêm ReportType alias + report_type_for_date helper

Caller sẽ dùng helper này để route theo weekday: T2-T6 → Shop VT,
T7-CN → TTTC. Cần thiết cho việc parametrize compliance functions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Zombie member filter `_is_active_member`

**Files:**
- Test: `tests/test_compliance.py` (append)
- Modify: `fpt_chat_stats.py` (add helper near `check_asm_compliance`, ~line 434)

- [ ] **Step 3.1: Write failing tests**

Append to `tests/test_compliance.py`:

```python
from fpt_chat_stats import _is_active_member


class TestIsActiveMember:
    def test_active_member_with_lastread(self):
        assert _is_active_member({"lastReadMessageId": 103}) is True

    def test_zombie_lastread_zero(self):
        assert _is_active_member({"lastReadMessageId": 0}) is False

    def test_zombie_lastread_missing(self):
        assert _is_active_member({}) is False

    def test_zombie_lastread_none(self):
        assert _is_active_member({"lastReadMessageId": None}) is False

    def test_active_low_lastread(self):
        # Even reading 1 message qualifies as active
        assert _is_active_member({"lastReadMessageId": 1}) is True
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `pytest tests/test_compliance.py::TestIsActiveMember -v`
Expected: FAIL with `ImportError: cannot import name '_is_active_member'`

- [ ] **Step 3.3: Implement `_is_active_member`**

Edit `fpt_chat_stats.py` — add just before `def report_type_for_date` (added in Task 2):

```python
def _is_active_member(m: dict) -> bool:
    """Active = đã từng đọc tin nhắn trong group.

    Loại zombie account (data quality issue: cùng người có 2 user record,
    1 active + 1 zombie với lastReadMessageId=0). Chỉ dùng cho compliance —
    KHÔNG dùng cho display/sender lookup.
    """
    return (m.get("lastReadMessageId") or 0) > 0
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `pytest tests/test_compliance.py::TestIsActiveMember -v`
Expected: PASS — 5 green.

- [ ] **Step 3.5: Commit**

```bash
git add tests/test_compliance.py fpt_chat_stats.py
git commit -m "feat: thêm _is_active_member để filter zombie account

Member với lastReadMessageId=0 = chưa đọc tin nhắn nào trong group.
Đây là zombie account do data quality issue (cùng người có 2 user
record). Sẽ được filter ở compliance check để bug 'Hieu × 2' biến mất.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Parametrize `check_asm_compliance` + apply zombie filter

**Files:**
- Test: `tests/test_compliance.py` (append)
- Modify: `fpt_chat_stats.py:435-473`

- [ ] **Step 4.1: Write failing tests**

Append to `tests/test_compliance.py`:

```python
from fpt_chat_stats import check_asm_compliance


def _report(report_type, sender, sent_at, parse_error=None):
    return {
        "report_type": report_type,
        "sender": sender,
        "sent_at": sent_at,
        "parse_error": parse_error,
    }


def _member(name, username="u", last_read=10):
    return {
        "displayName": name,
        "username": username,
        "lastReadMessageId": last_read,
    }


class TestCheckAsmCompliance:
    def test_daily_filters_only_shop_vt(self):
        # Bob nộp TTTC report — không count cho daily check
        reports = [
            _report("daily_shop_vt", "Alice", "2026-04-20T10:00:00Z"),
            _report("weekend_tttc",  "Bob",   "2026-04-20T10:00:00Z"),
        ]
        members = [_member("Alice"), _member("Bob", username="bob")]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
        )
        assert missing == ["Bob"]

    def test_weekend_filters_only_tttc(self):
        reports = [
            _report("daily_shop_vt", "Alice", "2026-04-19T10:00:00Z"),
            _report("weekend_tttc",  "Bob",   "2026-04-19T10:00:00Z"),
        ]
        members = [_member("Alice"), _member("Bob", username="bob")]
        missing = check_asm_compliance(
            reports, members, "2026-04-19",
            report_type="weekend_tttc",
        )
        assert missing == ["Alice"]

    def test_skips_zombie_members(self):
        # Bob is zombie (lastReadMessageId=0) — should not appear in missing
        reports = [_report("daily_shop_vt", "Alice", "2026-04-20T10:00:00Z")]
        members = [
            _member("Alice"),
            _member("Bob", username="bob", last_read=0),
        ]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
        )
        assert missing == []

    def test_keeps_active_member_low_lastread(self):
        reports = [_report("daily_shop_vt", "Alice", "2026-04-20T10:00:00Z")]
        members = [
            _member("Alice"),
            _member("Bob", username="bob", last_read=1),
        ]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
        )
        assert missing == ["Bob"]

    def test_hieu_listed_once_when_zombie_dup(self):
        """Regression: original bug — Hieu xuất hiện 2× trong missing.

        2 entry (active + zombie cùng username). Sau filter zombie chỉ còn 1.
        """
        reports = []  # Hieu chưa nộp gì
        members = [
            _member("Hieu Hoang Chi", username="hieuhc", last_read=103),
            _member("Hieu Hoang Chi", username="hieuhc", last_read=0),
        ]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
        )
        assert missing == ["Hieu Hoang Chi"]

    def test_drops_parse_error_reports(self):
        reports = [
            _report("daily_shop_vt", "Alice", "2026-04-20T10:00:00Z",
                    parse_error="invalid format"),
        ]
        members = [_member("Alice")]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
        )
        assert missing == ["Alice"]  # report bị reject → coi như chưa nộp

    def test_late_report_after_deadline_counts_as_missing(self):
        # Sent at 21:00 VN, deadline 20:00
        reports = [_report("daily_shop_vt", "Alice", "2026-04-20T14:00:00Z")]
        members = [_member("Alice")]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
            deadline_hhmm="20:00",
        )
        assert missing == ["Alice"]

    def test_skip_list_excludes_member(self):
        reports = []
        members = [_member("Alice")]
        missing = check_asm_compliance(
            reports, members, "2026-04-20",
            report_type="daily_shop_vt",
            skip_list=["alice"],
        )
        assert missing == []
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run: `pytest tests/test_compliance.py::TestCheckAsmCompliance -v`
Expected: FAIL — `report_type` is unknown kwarg, OR tests pass weirdly because old signature still works without it. Either way at least `test_weekend_filters_only_tttc` and `test_hieu_listed_once_when_zombie_dup` should fail.

- [ ] **Step 4.3: Update `check_asm_compliance` signature + body**

Edit `fpt_chat_stats.py` lines 435-473. Replace entire function:

```python
def check_asm_compliance(parsed_reports: list, members: list,
                         target_date_str: str,
                         report_type: ReportType,
                         deadline_hhmm: str = "20:00",
                         skip_list: list | None = None) -> list:
    """Trả về displayName của thành viên chưa gửi báo cáo trước deadline.

    `report_type` REQUIRED — caller phải route theo weekday (xem
    `report_type_for_date`). Default sẽ tạo silent bug khi quên route.
    """
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == report_type
                      and r.get("parse_error") is None]
    members = [m for m in members if _is_active_member(m)]
    VN_OFFSET = 7 * 3600
    try:
        deadline_h, deadline_m = map(int, deadline_hhmm.split(":"))
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError as e:
        print(f"  [!] Tham số không hợp lệ: {e}", file=sys.stderr)
        return []

    reported = set()
    for r in parsed_reports:
        dt = parse_dt(r.get("sent_at", ""))
        if not dt:
            continue
        vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
        if vn_dt.date() != target_date:
            continue
        if vn_dt.hour > deadline_h or (vn_dt.hour == deadline_h and vn_dt.minute >= deadline_m):
            continue
        reported.add(r["sender"].strip().lower())

    skip = [s.lower() for s in (skip_list or [])]
    missing = []
    for m in members:
        name = (m.get("displayName") or "").strip()
        if not name:
            continue
        name_lower = name.lower()
        if any(s in name_lower for s in skip):
            continue
        if not any(name_lower in rn or rn in name_lower for rn in reported):
            missing.append(name)
    return missing
```

- [ ] **Step 4.4: Run tests to verify they pass**

Run: `pytest tests/test_compliance.py::TestCheckAsmCompliance -v`
Expected: PASS — 8 green.

- [ ] **Step 4.5: Update callers in `fpt_chat_stats.py:1353`**

Edit `fpt_chat_stats.py` around line 1348-1355. Replace:

```python
if members:
    import time as _time
    target_date = args.date or datetime.fromtimestamp(
        _time.time() + 7 * 3600, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    asm_data["missing_reporters"] = check_asm_compliance(
        parsed_reports, members, target_date, args.asm_deadline, skip_list,
    )
```

With:

```python
if members:
    import time as _time
    target_date = args.date or datetime.fromtimestamp(
        _time.time() + 7 * 3600, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    rtype = report_type_for_date(
        datetime.strptime(target_date, "%Y-%m-%d").date()
    )
    asm_data["missing_reporters"] = check_asm_compliance(
        parsed_reports, members, target_date,
        report_type=rtype,
        deadline_hhmm=args.asm_deadline,
        skip_list=skip_list,
    )
```

- [ ] **Step 4.6: Update callers in `app.py:1026, 1029`**

Edit `app.py` around lines 1025-1031. Replace:

```python
if members:
    asm_data["missing_reporters"] = check_asm_compliance(
        parsed, members, target_date, cfg["deadline"], skip_list
    )
    asm_data["unreported_now"] = check_asm_compliance(
        parsed, members, target_date, _now_hhmm, skip_list
    )
```

With:

```python
if members:
    from datetime import datetime as _dt
    rtype = report_type_for_date(
        _dt.strptime(target_date, "%Y-%m-%d").date()
    )
    asm_data["missing_reporters"] = check_asm_compliance(
        parsed, members, target_date,
        report_type=rtype,
        deadline_hhmm=cfg["deadline"],
        skip_list=skip_list,
    )
    asm_data["unreported_now"] = check_asm_compliance(
        parsed, members, target_date,
        report_type=rtype,
        deadline_hhmm=_now_hhmm,
        skip_list=skip_list,
    )
```

Then add `report_type_for_date` to the import block at line 85-89:

```python
from fpt_chat_stats import (
    ...,
    report_type_for_date,
    ...
)
```

- [ ] **Step 4.7: Run full test suite + smoke-check imports**

Run: `pytest -v`
Expected: all tests pass.

Run: `python -c "import app"` — should not raise.
Run: `python -c "import fpt_chat_stats"` — should not raise.

- [ ] **Step 4.8: Commit**

```bash
git add tests/test_compliance.py fpt_chat_stats.py app.py
git commit -m "feat: parametrize check_asm_compliance với report_type + zombie filter

- Param report_type required (caller phải route theo weekday)
- Filter zombie members (lastReadMessageId=0) trước khi tính missing
- Bug 'Hieu Hoang Chi × 2' biến mất do zombie entry bị drop
- Update 3 callsite (fpt_chat_stats main, app.py × 2)

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Parametrize `check_late_reporters`

**Files:**
- Test: `tests/test_compliance.py` (append)
- Modify: `fpt_chat_stats.py:476-509`, `app.py:1035`

- [ ] **Step 5.1: Write failing tests**

Append to `tests/test_compliance.py`:

```python
from fpt_chat_stats import check_late_reporters


class TestCheckLateReporters:
    def test_daily_filters_only_shop_vt(self):
        # Sent at 21:00 VN (14:00 UTC) — 1h after 20:00 deadline
        reports = [
            _report("daily_shop_vt", "Alice", "2026-04-20T14:00:00Z"),
            _report("weekend_tttc",  "Bob",   "2026-04-20T14:00:00Z"),
        ]
        late = check_late_reporters(
            reports, "2026-04-20", report_type="daily_shop_vt",
        )
        assert [r["sender"] for r in late] == ["Alice"]

    def test_weekend_filters_only_tttc(self):
        reports = [
            _report("daily_shop_vt", "Alice", "2026-04-19T14:00:00Z"),
            _report("weekend_tttc",  "Bob",   "2026-04-19T14:00:00Z"),
        ]
        late = check_late_reporters(
            reports, "2026-04-19", report_type="weekend_tttc",
        )
        assert [r["sender"] for r in late] == ["Bob"]

    def test_on_time_not_listed(self):
        # Sent at 19:00 VN (12:00 UTC) — before 20:00 deadline
        reports = [_report("daily_shop_vt", "Alice", "2026-04-20T12:00:00Z")]
        late = check_late_reporters(
            reports, "2026-04-20", report_type="daily_shop_vt",
        )
        assert late == []
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `pytest tests/test_compliance.py::TestCheckLateReporters -v`
Expected: FAIL with TypeError on `report_type` kwarg.

- [ ] **Step 5.3: Update `check_late_reporters` signature + body**

Read `fpt_chat_stats.py` lines 476-509 first to see full function. Then update signature to:

```python
def check_late_reporters(parsed_reports: list,
                         target_date_str: str,
                         report_type: ReportType,
                         deadline_hhmm: str = "20:00") -> list:
    """Trả về list {sender, sent_at_vn} của ASM gửi báo cáo SAU deadline."""
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == report_type
                      and r.get("parse_error") is None]
    # ... rest unchanged
```

- [ ] **Step 5.4: Update caller in `app.py:1035`**

Edit `app.py` around line 1035-1037. Replace:

```python
asm_data["late_reporters"] = check_late_reporters(
    parsed, target_date, cfg["deadline"]
)
```

With:

```python
asm_data["late_reporters"] = check_late_reporters(
    parsed, target_date,
    report_type=rtype,                 # rtype computed earlier in same block
    deadline_hhmm=cfg["deadline"],
)
```

(`rtype` is already in scope from the change in Task 4.6.)

- [ ] **Step 5.5: Run full test suite**

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 5.6: Commit**

```bash
git add tests/test_compliance.py fpt_chat_stats.py app.py
git commit -m "feat: parametrize check_late_reporters với report_type

Cùng pattern với check_asm_compliance — param required, không default.
Caller (app.py) tái sử dụng rtype đã compute ở Task 4.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Per-day routing in `analyze_multiday`

**Files:**
- Test: `tests/test_compliance.py` (append)
- Modify: `fpt_chat_stats.py:510-…` (analyze_multiday function)

- [ ] **Step 6.1: Read `analyze_multiday` to understand current shape**

Run: `sed -n '510,640p' fpt_chat_stats.py | head -130` — confirm it currently hardcodes `daily_shop_vt` filter at top. Note that this function returns daily summary stats — it does NOT call check_asm_compliance directly. The "missing reporters per day" logic is via `sender_dates` set diff.

- [ ] **Step 6.2: Write failing test**

Append to `tests/test_compliance.py`:

```python
from fpt_chat_stats import analyze_multiday


class TestAnalyzeMultidayRoutesPerDay:
    def test_picks_daily_for_weekday_and_tttc_for_weekend(self):
        """Across Fri-Sat, daily_shop_vt counts on Fri, weekend_tttc on Sat."""
        reports = [
            # Fri 17/04 — Shop VT
            {"report_type": "daily_shop_vt", "sender": "Alice",
             "sent_at": "2026-04-17T10:00:00Z", "parse_error": None,
             "deposit_count": 5, "ra_tiem_count": 2},
            # Sat 18/04 — TTTC (currently dropped because filter is hardcoded)
            {"report_type": "weekend_tttc", "sender": "Alice",
             "sent_at": "2026-04-18T10:00:00Z", "parse_error": None,
             "deposit_count": None, "ra_tiem_count": None},
        ]
        out = analyze_multiday(reports, "2026-04-17", "2026-04-18")
        # Both days should have a reporter (Alice on Fri via Shop VT, Sat via TTTC)
        days = {d["date"]: d for d in out["daily_summary"]}
        assert days["2026-04-17"]["reporter_count"] == 1
        assert days["2026-04-18"]["reporter_count"] == 1
```

- [ ] **Step 6.3: Run test to verify it fails**

Run: `pytest tests/test_compliance.py::TestAnalyzeMultidayRoutesPerDay -v`
Expected: FAIL — Sat shows reporter_count=0 because TTTC report is filtered out at line 512-514.

- [ ] **Step 6.4: Update `analyze_multiday` to route per day**

Edit `fpt_chat_stats.py` lines 510-514. Replace:

```python
def analyze_multiday(parsed_reports: list, date_from_str: str, date_to_str: str) -> dict:
    """Phân tích báo cáo ASM theo từng ngày trong khoảng nhiều ngày."""
    parsed_reports = [r for r in parsed_reports
                      if r.get("report_type") == "daily_shop_vt"
                      and r.get("parse_error") is None]
```

With:

```python
def analyze_multiday(parsed_reports: list, date_from_str: str, date_to_str: str) -> dict:
    """Phân tích báo cáo ASM theo từng ngày trong khoảng nhiều ngày.

    Per-day routing: T2-T6 nhận daily_shop_vt, T7-CN nhận weekend_tttc.
    """
    parsed_reports = [r for r in parsed_reports
                      if r.get("parse_error") is None
                      and r.get("report_type") in ("daily_shop_vt", "weekend_tttc")]
```

Then in the loop that buckets reports by date (around line 524-530), add the per-day type filter. Replace:

```python
by_date: dict[_date, list] = {d: [] for d in all_dates}
for r in parsed_reports:
    dt = parse_dt(r.get("sent_at", ""))
    if not dt:
        continue
    vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
    if d_from <= vn_dt.date() <= d_to:
        by_date[vn_dt.date()].append(r)
```

With:

```python
by_date: dict[_date, list] = {d: [] for d in all_dates}
for r in parsed_reports:
    dt = parse_dt(r.get("sent_at", ""))
    if not dt:
        continue
    vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
    if not (d_from <= vn_dt.date() <= d_to):
        continue
    # Per-day routing: only accept the type expected for that weekday
    if r["report_type"] != report_type_for_date(vn_dt.date()):
        continue
    by_date[vn_dt.date()].append(r)
```

- [ ] **Step 6.5: Run tests to verify they pass**

Run: `pytest tests/test_compliance.py::TestAnalyzeMultidayRoutesPerDay -v`
Expected: PASS.

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 6.6: Commit**

```bash
git add tests/test_compliance.py fpt_chat_stats.py
git commit -m "feat: analyze_multiday route per-day theo weekday

T2-T6 nhận daily_shop_vt, T7-CN nhận weekend_tttc. Cùng 1 sender báo
cáo Shop VT thứ Sáu + TTTC thứ Bảy → đều count cho ngày tương ứng.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Apply zombie filter in `analyze_weekly`

**Files:**
- Modify: `fpt_chat_stats.py:648-652, 1023-1027` (member_names build sites)

- [ ] **Step 7.1: Locate both sites**

Run: `grep -n 'member_names = sorted({' fpt_chat_stats.py`
Expected: two hits — one in `analyze_weekly` (~line 648), one in `write_weekly_excel` (~line 1023).

- [ ] **Step 7.2: Update both sites**

For each occurrence, change:

```python
member_names = sorted({
    (m.get("displayName") or "").strip()
    for m in group_members
    if (m.get("displayName") or "").strip()
})
```

To:

```python
member_names = sorted({
    (m.get("displayName") or "").strip()
    for m in group_members
    if _is_active_member(m) and (m.get("displayName") or "").strip()
})
```

- [ ] **Step 7.3: Smoke check**

Run: `python -c "import fpt_chat_stats"`
Expected: no error.

Run: `pytest -v`
Expected: all tests pass.

- [ ] **Step 7.4: Commit**

```bash
git add fpt_chat_stats.py
git commit -m "feat: filter zombie members trong analyze_weekly + write_weekly_excel

Cùng filter _is_active_member với check_asm_compliance để consistent.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: End-to-end smoke test với data thật

**Files:** none (manual run)

- [ ] **Step 8.1: Run pipeline on saved 3-week sample**

Run:
```bash
OPENAI_API_KEY=$(grep AI_ACCESS_TOKEN .vars | cut -d= -f2) \
  python fpt_chat_stats.py --load /tmp/raw_3weeks.json \
  --from 2026-04-16 --to 2026-04-20 2>&1 | tail -50
```

Expected:
- Log to stderr: pre-filter passes ≥ 16 candidates (was 7 before)
- Reports show both Shop VT (Mon-Fri) and TTTC (Sat-Sun) sections populated
- "ASM CHƯA BÁO CÁO" list does NOT show "Hieu Hoang Chi" twice (assuming members fetched)

- [ ] **Step 8.2: Run pipeline on 2026-04-18 (Saturday) — the original failing case**

Run:
```bash
OPENAI_API_KEY=$(grep AI_ACCESS_TOKEN .vars | cut -d= -f2) \
  python fpt_chat_stats.py --load /tmp/raw_2026-04-18.json \
  --date 2026-04-18 2>&1 | tail -30
```

Expected:
- TTTC reports listed (was 0 before — Hieu's complaint)
- Compliance check uses weekend_tttc (visible in output as "TTTC" header instead of "Shop VT")

- [ ] **Step 8.3: Document smoke-test results in commit message**

If both smoke tests pass as expected, no code change — just record observations:

```bash
git commit --allow-empty -m "chore: smoke-test xác nhận TTTC reports kéo được + Hieu × 1

3-week sample: pre-filter passes 16 (was 7), TTTC sections populated.
2026-04-18 (Sat): TTTC compliance check active, không còn 'k kéo được
báo cáo' như Hieu phàn nàn.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

If smoke tests fail, debug and create follow-up tasks before continuing to Task 9.

---

## Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (Pipeline section)

- [ ] **Step 9.1: Update Pipeline paragraph**

Find the line in `CLAUDE.md` that describes `detect_asm_reports`:

> 2. `extract_all_reports` applies the cheap regex pre-filter (`detect_asm_reports`: `shop` + `N cọc`) and delegates extraction to `llm_extractor.extract_reports`...

Replace with:

> 2. `extract_all_reports` applies the L2 heuristic pre-filter (`detect_report_candidates`: length ≥ 80 + ≥ 2 digits + ≥ 1 keyword from `_REPORT_KEYWORDS`, diacritic-insensitive) and delegates extraction to `llm_extractor.extract_reports`...

Find the section about compliance (if exists) — add a paragraph after the pipeline description:

> **Compliance routing:** `check_asm_compliance` and `check_late_reporters` require a `report_type` parameter. Callers route by weekday using `report_type_for_date(date)` — Mon-Fri → `daily_shop_vt`, Sat-Sun → `weekend_tttc`. Members with `lastReadMessageId == 0` are filtered out as zombie accounts before compliance check (handles data-quality cases where the same person has 2 user records).

- [ ] **Step 9.2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: cập nhật CLAUDE.md — L2 pre-filter + weekday routing

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Create OpenSpec change proposal

**Files:**
- Create: `openspec/changes/2026-04-22-fix-tttc-coverage/proposal.md`
- Create: `openspec/changes/2026-04-22-fix-tttc-coverage/tasks.md`
- Create: `openspec/changes/2026-04-22-fix-tttc-coverage/specs/fpt-chat-stats/spec.md`

- [ ] **Step 10.1: Read existing OpenSpec template**

Run: `cat openspec/AGENTS.md | head -100`
Then read a recent proposal to follow style:
Run: `cat openspec/changes/archive/2026-04-20-2026-04-20-add-weekly-report/proposal.md`

- [ ] **Step 10.2: Write proposal.md**

Create `openspec/changes/2026-04-22-fix-tttc-coverage/proposal.md` summarizing:
- **Why:** Hieu's complaint quote, regex too narrow, hardcoded compliance, zombie dup
- **What changes:** L2 pre-filter, parametrized compliance, weekday routing helper, zombie filter
- **Decisions table:** copy from spec
- **Out of scope:** copy from spec

- [ ] **Step 10.3: Write tasks.md**

Mirror this plan's tasks 1-9 in tasks.md as a checkbox list.

- [ ] **Step 10.4: Write spec delta**

Create `openspec/changes/2026-04-22-fix-tttc-coverage/specs/fpt-chat-stats/spec.md` — read existing `openspec/specs/fpt-chat-stats/spec.md` first to identify which requirement(s) need MODIFIED markers per OpenSpec conventions.

- [ ] **Step 10.5: Validate with openspec CLI**

Run: `openspec validate 2026-04-22-fix-tttc-coverage --strict --no-interactive`
Expected: `✓ valid`

If validation fails, fix and re-run before committing.

- [ ] **Step 10.6: Commit**

```bash
git add openspec/changes/2026-04-22-fix-tttc-coverage/
git commit -m "docs(openspec): proposal fix-tttc-coverage

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Definition of Done

- All 16 test cases in `tests/test_compliance.py` pass
- Existing test suite (`pytest -v`) passes (15 golden + llm_extractor + new compliance)
- Smoke test on `/tmp/raw_3weeks.json` shows ≥ 16 candidates pass pre-filter (vs 7 before)
- Smoke test on `/tmp/raw_2026-04-18.json` (Saturday) shows TTTC reports extracted and compliance routed to `weekend_tttc`
- "Hieu Hoang Chi" appears at most once in any compliance/missing list
- `openspec validate 2026-04-22-fix-tttc-coverage --strict --no-interactive` returns valid
- `CLAUDE.md` reflects new pipeline + routing semantics
- All changes committed in logical, reviewable commits (one per task)
