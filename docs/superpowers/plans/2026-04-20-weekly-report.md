# Weekly Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Báo cáo tuần" single-day mode that lists who reported / late / missing on a user-picked date and dumps raw text per ASM, classified with a 6-feature scoring function.

**Architecture:** One new pure classifier (`_score_weekly_message`) + one new pipeline function (`analyze_weekly`) + two new output helpers (`print_weekly_report`, `write_weekly_excel`) + one new CLI flag (`--weekly`) + one new Streamlit section. All new code lives in `fpt_chat_stats.py` and `app.py` — no new files in the main codebase. Classifier operates over raw FPT Chat message dicts; no dependency on the existing daily shop-format parser.

**Tech Stack:** Python 3.11+ stdlib (`re`, `datetime`, `argparse`), `openpyxl` for Excel, `streamlit` + `streamlit-javascript` for UI.

**Authoritative spec:** `openspec/changes/2026-04-20-add-weekly-report/` (proposal, tasks, spec deltas). The spec's "Requirements" and "Scenarios" are the contract; this plan is the implementation roadmap to satisfy them. Re-read the spec if anything below conflicts — spec wins.

**Testing convention:** No pytest in this repo (per `CLAUDE.md`). Instead, add small standalone verification scripts under `scripts/` that run via `python scripts/<name>.py`, print PASS/FAIL per check, and exit non-zero on any failure. These serve the TDD role without adding a framework dependency.

**Commit style:** Vietnamese commit messages following the repo's `git log` pattern (e.g., `feat: thêm ...`, `fix: ...`). Sign commits with the `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer.

---

## File Structure

Files this plan touches (all existing, no new files in the main codebase):

| File | Role | Approx. insertion |
|---|---|---|
| `fpt_chat_stats.py` | Core: constants, classifier, pipeline, output, CLI | Constants+classifier near line 220 (above `detect_asm_reports`); `analyze_weekly` after `analyze_multiday` (line 542); `print_weekly_report` after `print_asm_report` (line 625); `write_weekly_excel` after `write_asm_excel` (line 740); CLI flag in `main` near line 791; dispatch branch in `main`'s `if/elif` flow |
| `app.py` | Streamlit tab "Báo cáo tuần" | New section alongside existing daily / multi-day views |
| `scripts/verify_weekly_classifier.py` | Task-level verifier (new, small) | New file under new `scripts/` dir |
| `scripts/verify_analyze_weekly.py` | Task-level verifier (new, small) | New file |
| `scripts/verify_weekly_excel.py` | Task-level verifier (new, small) | New file |

---

## Task 1: Add scoring classifier and module constants

**Files:**
- Create: `scripts/verify_weekly_classifier.py`
- Modify: `fpt_chat_stats.py` (insert just above `def detect_asm_reports` at line 220)

**What you're building:** Six compiled regexes + `_score_weekly_message(content) -> int` that returns an integer in `[0, 6]`.

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_weekly_classifier.py`:

```python
#!/usr/bin/env python3
"""Sanity-check the weekly-report classifier against real samples and negatives.

Run: python scripts/verify_weekly_classifier.py
Exits 0 on all-pass, 1 on any failure.
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import _score_weekly_message, WEEKLY_SCORE_THRESHOLD

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

# Expected minimum scores per sample (from plan; samples 4 and 6 are narrative = 5, rest = 6)
EXPECTED_MIN = {1: 6, 2: 6, 3: 6, 4: 5, 5: 6, 6: 5, 7: 6, 8: 6}

print("Positive samples (templates/weekend/*)")
for i in range(1, 9):
    p = pathlib.Path(f"templates/weekend/{i}")
    s = _score_weekly_message(p.read_text(encoding="utf-8"))
    check(f"sample {i}: score={s} (expected {EXPECTED_MIN[i]})", s == EXPECTED_MIN[i])

print("\nNegative samples (casual chat must score < threshold)")
negatives = [
    "Ok anh",
    "Shop mình nghỉ trưa nha mọi người",
    "Dạ em gửi anh file nhé",
    "Anh ơi hôm qua trung tâm mình làm 133% rất tốt",
    "a" * 400,  # long single-line, no features except length
]
for msg in negatives:
    s = _score_weekly_message(msg)
    check(f"score={s} for {msg[:50]!r}", s < WEEKLY_SCORE_THRESHOLD)

print(f"\n{FAIL} failure(s)" if FAIL else "\nAll checks passed.")
sys.exit(1 if FAIL else 0)
```

- [ ] **Step 2: Run verifier to confirm it fails**

Run: `python scripts/verify_weekly_classifier.py`
Expected: `ImportError: cannot import name '_score_weekly_message' from 'fpt_chat_stats'`

- [ ] **Step 3: Add constants + classifier to `fpt_chat_stats.py`**

Insert this block immediately above `def detect_asm_reports` (line 220):

```python
# ---------------------------------------------------------------------------
# Weekly Report Classifier
# ---------------------------------------------------------------------------

WEEKLY_SCORE_THRESHOLD = 3
WEEKLY_MIN_LENGTH = 150

_WEEKLY_RE_UNIT = re.compile(
    r"\b(tttc|vx\s|shop\b|trung\s*tâm|chi\s*nhánh|lc\s+hcm)",
    re.IGNORECASE,
)
_WEEKLY_RE_METRIC = re.compile(
    r"\d+\s*%|\d+(?:\.\d+)?\s*(tr|triệu|m\b|k\b|đ\b|cọc|bill|khách|lượt|gói)",
    re.IGNORECASE,
)
_WEEKLY_RE_OPEN_CLOSE = re.compile(
    r"(đánh\s*giá|báo\s*cáo|em\s+(?:xin\s+)?cảm\s*ơn|dạ\s+em\s+(?:gửi|bc))",
    re.IGNORECASE,
)
_WEEKLY_RE_SECTION = re.compile(
    r"(?m)^\s*[-–•\d\.]*\s*(kết\s*quả|tích\s*cực|vấn\s*đề|đã\s*làm|ngày\s*mai"
    r"|giải\s*pháp|hành\s*động|tổng\s*quan|phân\s*tích)\s*[:：]",
    re.IGNORECASE,
)


def _score_weekly_message(content: str) -> int:
    """Tính điểm phân loại báo cáo tuần (0..6) cho một đoạn text."""
    if not content:
        return 0
    flags = (
        len(content.strip()) >= WEEKLY_MIN_LENGTH,
        "\n" in content,
        bool(_WEEKLY_RE_UNIT.search(content)),
        bool(_WEEKLY_RE_METRIC.search(content)),
        bool(_WEEKLY_RE_OPEN_CLOSE.search(content)),
        bool(_WEEKLY_RE_SECTION.search(content)),
    )
    return sum(1 for f in flags if f)
```

- [ ] **Step 4: Run verifier to confirm it passes**

Run: `python scripts/verify_weekly_classifier.py`
Expected:
```
Positive samples (templates/weekend/*)
  [PASS] sample 1: score=6 (expected 6)
  ... (all 8 PASS)
Negative samples (casual chat must score < threshold)
  ... (all 5 PASS)
All checks passed.
```
Exit code 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_weekly_classifier.py fpt_chat_stats.py
git commit -m "$(cat <<'EOF'
feat: thêm classifier 6-feature cho báo cáo tuần

Thêm hằng số module (WEEKLY_SCORE_THRESHOLD, WEEKLY_MIN_LENGTH, 4
regex feature) và hàm _score_weekly_message(content) -> int trong
fpt_chat_stats.py. Thêm scripts/verify_weekly_classifier.py kiểm tra
8 template weekend (score 5-6) và 5 case casual chat (score < 3).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add `analyze_weekly` pipeline function

**Files:**
- Create: `scripts/verify_analyze_weekly.py`
- Modify: `fpt_chat_stats.py` (insert after `analyze_multiday`, around line 542)

**What you're building:** The main pipeline function that takes raw messages + group members + target date + deadline, classifies messages, groups by sender, and produces the `{target_date, deadline, reports, late_list, missing_list}` dict described in the spec at `openspec/changes/2026-04-20-add-weekly-report/specs/fpt-chat-stats/spec.md`.

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_analyze_weekly.py`:

```python
#!/usr/bin/env python3
"""Unit-style verification of analyze_weekly against synthetic fixtures."""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import analyze_weekly

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

# --- Fixture: a qualifying report body (score 6). ---
REPORT_BODY = (
    "Dạ em gửi báo cáo đánh giá TTTC 58149\n"
    "- Kết quả: Doanh thu 133% HT, TB bill 2.2M, lượt khách 45\n"
    "- Tích cực: TVV upsale tốt\n"
    "- Vấn đề: HPV kèm HOT còn thấp\n"
    "- Đã làm: hướng dẫn kịch bản\n"
    "Em cảm ơn ạ."
)

GROUP_MEMBERS = [
    {"displayName": n}
    for n in ["Nguyễn Văn A", "Trần Thị B", "Lê C", "Phạm D", "Hoàng E"]
]

# UTC timestamps that, when +7h offset, give VN date 2026-04-20
def msg(sender, utc_ts, text="ok anh", typ="TEXT"):
    return {
        "id": f"id-{sender}-{utc_ts}",
        "type": typ,
        "content": text,
        "createdAt": utc_ts,
        "user": {"id": f"u-{sender}", "displayName": sender},
    }

MESSAGES = [
    msg("Nguyễn Văn A", "2026-04-20T02:00:00Z", REPORT_BODY),          # VN 09:00, on-time
    msg("Trần Thị B",   "2026-04-20T14:30:00Z", REPORT_BODY),          # VN 21:30, late
    msg("Lê C",         "2026-04-20T10:00:00Z", "Ok anh"),             # VN 17:00, below threshold
    msg("Phạm D",       "2026-04-20T03:00:00Z", REPORT_BODY, "FILE"),  # Not TEXT
    # Hoàng E sends nothing
]

result = analyze_weekly(MESSAGES, GROUP_MEMBERS, "2026-04-20", deadline="20:00")

check("target_date == '2026-04-20'", result["target_date"] == "2026-04-20")
check("deadline == '20:00'", result["deadline"] == "20:00")
check("len(reports) == 2 (A on-time, B late)", len(result["reports"]) == 2)
check("late_list == ['Trần Thị B']", result["late_list"] == ["Trần Thị B"])
check(
    "missing_list == sorted(['Hoàng E','Lê C','Phạm D'])",
    result["missing_list"] == sorted(["Hoàng E", "Lê C", "Phạm D"]),
)
# Order of reports
check(
    "reports sorted by sent_at_vn asc: A at 09:00 first, B at 21:30 second",
    [r["sender"] for r in result["reports"]] == ["Nguyễn Văn A", "Trần Thị B"],
)
check(
    "A.is_late == False, B.is_late == True",
    result["reports"][0]["is_late"] is False and result["reports"][1]["is_late"] is True,
)
check("A.extra_count == 0", result["reports"][0]["extra_count"] == 0)
check("A.text == REPORT_BODY", result["reports"][0]["text"] == REPORT_BODY)

# Multiple qualifying messages from one sender: earliest wins, extra_count = N-1
MESSAGES_2 = [
    msg("Nguyễn Văn A", "2026-04-20T01:00:00Z", REPORT_BODY + "\nfirst"),   # VN 08:00
    msg("Nguyễn Văn A", "2026-04-20T03:30:00Z", REPORT_BODY + "\nsecond"),  # VN 10:30
    msg("Nguyễn Văn A", "2026-04-20T07:00:00Z", REPORT_BODY + "\nthird"),   # VN 14:00
]
r2 = analyze_weekly(MESSAGES_2, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Multi-message: 1 entry", len(r2["reports"]) == 1)
check("Multi-message: earliest by UTC wins", r2["reports"][0]["text"].endswith("first"))
check("Multi-message: extra_count == 2", r2["reports"][0]["extra_count"] == 2)

# Midnight boundary: VN 23:59 on target day, VN 00:00 next day
MESSAGES_MID = [
    msg("Nguyễn Văn A", "2026-04-20T16:59:30Z", REPORT_BODY),  # VN 23:59:30, same day
    msg("Nguyễn Văn A", "2026-04-20T17:00:15Z", REPORT_BODY),  # VN 00:00:15, NEXT day
]
r3 = analyze_weekly(MESSAGES_MID, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Midnight: only first message counted", r3["reports"][0]["extra_count"] == 0)

# Non-member sender is ignored (must not appear in missing_list)
MESSAGES_NONMEMBER = [msg("Stranger", "2026-04-20T02:00:00Z", REPORT_BODY)]
r4 = analyze_weekly(MESSAGES_NONMEMBER, GROUP_MEMBERS, "2026-04-20", deadline="20:00")
check("Non-member: not in reports", not any(r["sender"] == "Stranger" for r in r4["reports"]))
check("Non-member: not in missing_list", "Stranger" not in r4["missing_list"])
check(
    "Non-member: all group_members in missing_list",
    set(r4["missing_list"]) == set(GROUP_MEMBERS),
)

# Deadline boundary inclusive-late: VN exactly 20:00:00
MESSAGES_BOUNDARY = [msg("Nguyễn Văn A", "2026-04-20T13:00:00Z", REPORT_BODY)]  # VN 20:00:00
r5 = analyze_weekly(MESSAGES_BOUNDARY, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Boundary 20:00 is late", r5["reports"][0]["is_late"] is True)
check("Boundary: in late_list", r5["late_list"] == ["Nguyễn Văn A"])

# Bot/service account: treated like any member if in members list
MESSAGES_BOT = [msg("FPT Chat Bot", "2026-04-20T02:00:00Z", REPORT_BODY)]
r6 = analyze_weekly(
    MESSAGES_BOT,
    [{"displayName": "FPT Chat Bot"}, {"displayName": "Real User"}],
    "2026-04-20",
    deadline="20:00",
)
check("Bot reporter: appears in reports", any(r["sender"] == "FPT Chat Bot" for r in r6["reports"]))
check("Bot reporter: Real User is in missing_list", "Real User" in r6["missing_list"])

# Attachment-only TEXT (empty caption): ignored
MESSAGES_ATTACH = [msg("Nguyễn Văn A", "2026-04-20T02:00:00Z", "   \n\t  ")]  # whitespace-only
r7 = analyze_weekly(MESSAGES_ATTACH, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Attachment-only / empty body: not in reports", r7["reports"] == [])
check("Attachment-only / empty body: sender in missing_list", r7["missing_list"] == ["Nguyễn Văn A"])

print(f"\n{FAIL} failure(s)" if FAIL else "\nAll checks passed.")
sys.exit(1 if FAIL else 0)
```

- [ ] **Step 2: Run verifier — should fail**

Run: `python scripts/verify_analyze_weekly.py`
Expected: `ImportError: cannot import name 'analyze_weekly' from 'fpt_chat_stats'`

- [ ] **Step 3: Implement `analyze_weekly` in `fpt_chat_stats.py`**

Insert after `def analyze_multiday(...)` block (around line 542, before the `# Report Output` divider):

```python
def analyze_weekly(messages: list,
                   group_members: list,
                   target_date_vn: str,
                   deadline: str = "20:00") -> dict:
    """Báo cáo tuần một ngày: phân loại tin nhắn, tìm muộn/thiếu, dump text.

    - messages: list of raw FPT Chat message dicts (as returned by fetch_all_messages)
    - group_members: list of member dicts (as returned by fetch_group_members),
      each with a 'displayName' key
    - target_date_vn: 'YYYY-MM-DD' (VN-time date; UTC+7)
    - deadline: 'HH:MM' VN time, inclusive (20:00:00 counts as late)
    """
    VN_OFFSET = 7 * 3600
    target = datetime.strptime(target_date_vn, "%Y-%m-%d").date()
    dl_h, dl_m = [int(x) for x in deadline.split(":", 1)]
    deadline_time = time(hour=dl_h, minute=dl_m)

    member_names = sorted({
        (m.get("displayName") or "").strip()
        for m in group_members
        if (m.get("displayName") or "").strip()
    })
    member_set = set(member_names)

    # Group qualifying messages by sender
    by_sender: dict[str, list] = {}
    for msg in messages:
        if msg.get("type") != "TEXT":
            continue
        content = msg.get("content") or ""
        if not content.strip():
            continue
        user = msg.get("user") or {}
        sender = (user.get("displayName") or "").strip()
        if sender not in member_set:
            continue
        dt = parse_dt(msg.get("createdAt", ""))
        if not dt:
            continue
        vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
        if vn_dt.date() != target:
            continue
        if _score_weekly_message(content) < WEEKLY_SCORE_THRESHOLD:
            continue
        by_sender.setdefault(sender, []).append((dt, vn_dt, content))

    # Build reports (earliest qualifying per sender)
    reports = []
    for sender, items in by_sender.items():
        items.sort(key=lambda t: t[0])
        _, vn_dt, content = items[0]
        is_late = vn_dt.time() >= deadline_time
        reports.append({
            "sender": sender,
            "sent_at_vn": vn_dt.strftime("%H:%M"),
            "is_late": is_late,
            "text": content,
            "extra_count": len(items) - 1,
        })
    reports.sort(key=lambda r: r["sent_at_vn"])

    late_list = sorted(r["sender"] for r in reports if r["is_late"])
    reporters = {r["sender"] for r in reports}
    missing_list = sorted(n for n in member_names if n not in reporters)

    return {
        "target_date":  target_date_vn,
        "deadline":     deadline,
        "reports":      reports,
        "late_list":    late_list,
        "missing_list": missing_list,
    }
```

`group_members` is a list of dicts matching what `fetch_group_members` returns — each dict has a `displayName` key. The implementation extracts `displayName` and ignores everything else (no filtering by account type — the spec explicitly says upstream is responsible for the members list, including bots/service accounts).

- [ ] **Step 4: Run verifier — should pass**

Run: `python scripts/verify_analyze_weekly.py`
Expected: all checks PASS, exit 0.

Also re-run Task 1's verifier to confirm no regression: `python scripts/verify_weekly_classifier.py`.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_analyze_weekly.py fpt_chat_stats.py
git commit -m "$(cat <<'EOF'
feat: thêm analyze_weekly — pipeline báo cáo tuần một ngày

Hàm nhận messages + group_members + target_date + deadline, phân
loại bằng _score_weekly_message, trả về dict {reports, late_list,
missing_list}. Đã verify: basic buckets, multi-message dedup, ranh
giới nửa đêm VN, deadline boundary, non-member filter.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Add `print_weekly_report` stdout helper

**Files:**
- Modify: `fpt_chat_stats.py` (insert after `print_asm_report`, around line 625)

**What you're building:** A pure-output helper that writes the Vietnamese-labeled structured text described in the spec's `Weekly Report Print Output` requirement.

- [ ] **Step 1: Write the failing check**

Append this block at the bottom of `scripts/verify_analyze_weekly.py` (before the final `sys.exit`):

```python
# --- print_weekly_report smoke ---
import io, contextlib
from fpt_chat_stats import print_weekly_report

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print_weekly_report(result)  # use `result` from earlier basic fixture
out = buf.getvalue()

check("header has 'BÁO CÁO TUẦN'", "BÁO CÁO TUẦN" in out)
check("header has target_date", "2026-04-20" in out)
check("header has 'Đã báo cáo: 2'", "Đã báo cáo: 2" in out)
check("header has 'Muộn: 1'", "Muộn: 1" in out)
check("header has 'Chưa báo cáo: 3'", "Chưa báo cáo: 3" in out)
check("missing section lists Hoàng E", "Hoàng E" in out)
check("late marker MUỘN appears for Trần Thị B", "MUỘN" in out and "Trần Thị B" in out)
check("content section includes report body substring",
      "Doanh thu 133% HT" in out)
```

- [ ] **Step 2: Run verifier — should fail at the print_weekly_report import**

Run: `python scripts/verify_analyze_weekly.py`
Expected: `ImportError: cannot import name 'print_weekly_report'`.

- [ ] **Step 3: Implement `print_weekly_report`**

Insert after `def print_asm_report(...)` (around line 625):

```python
def print_weekly_report(data: dict) -> None:
    """In báo cáo tuần một ngày ra stdout."""
    target = data["target_date"]
    deadline = data["deadline"]
    reports = data["reports"]
    late_list = data["late_list"]
    missing_list = data["missing_list"]
    on_time = len(reports) - len(late_list)

    sep = "=" * 65
    print(sep)
    print(f"  BÁO CÁO TUẦN — {target}")
    print(sep)
    print(f"  Deadline   : {deadline}")
    print(f"  Đã báo cáo : {len(reports)}")
    print(f"  Muộn       : {len(late_list)}")
    print(f"  Chưa báo cáo: {len(missing_list)}")
    print()

    if missing_list:
        print(f"--- Chưa báo cáo ({len(missing_list)}) ---")
        for name in missing_list:
            print(f"  - {name}")
        print()

    if late_list:
        print(f"--- Muộn ({len(late_list)}) ---")
        late_map = {r["sender"]: r["sent_at_vn"] for r in reports if r["is_late"]}
        for name in late_list:
            print(f"  - {name} ({late_map.get(name, '?')})")
        print()

    if reports:
        print(f"--- Nội dung báo cáo ({len(reports)}) ---")
        for r in reports:
            suffix = " — MUỘN" if r["is_late"] else ""
            extra  = f" (+{r['extra_count']} tin nhắn khác)" if r["extra_count"] else ""
            print(f"[{r['sender']} — {r['sent_at_vn']}{suffix}{extra}]")
            print(r["text"])
            print()
```

- [ ] **Step 4: Run verifier — should pass**

Run: `python scripts/verify_analyze_weekly.py`
Expected: all checks PASS including the print block.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_analyze_weekly.py fpt_chat_stats.py
git commit -m "$(cat <<'EOF'
feat: thêm print_weekly_report — xuất báo cáo tuần ra stdout

Header + 3 section (Chưa báo cáo, Muộn, Nội dung), gắn MUỘN suffix
cho người gửi muộn, ghi chú (+N tin nhắn khác) khi extra_count > 0.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add `write_weekly_excel` writer

**Files:**
- Create: `scripts/verify_weekly_excel.py`
- Modify: `fpt_chat_stats.py` (insert after `write_asm_excel`, around line 740)

**What you're building:** An `openpyxl`-based writer that produces an `.xlsx` with exactly two sheets (`Tổng hợp tuần`, `Nội dung`) matching the spec's `Weekly Report Excel Output` requirement — including row ordering rules and wrap-text on content.

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_weekly_excel.py`:

```python
#!/usr/bin/env python3
"""Verify the weekly Excel writer output shape."""
from __future__ import annotations
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import analyze_weekly, write_weekly_excel

FAIL = 0
def check(label, cond):
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

REPORT = (
    "Dạ em gửi báo cáo đánh giá TTTC 58149\n"
    "- Kết quả: Doanh thu 133% HT, TB bill 2.2M\n"
    "- Tích cực: TVV upsale tốt\n"
    "- Đã làm: hướng dẫn kịch bản\n"
    "Em cảm ơn ạ."
)

def msg(sender, utc_ts, text):
    return {
        "id": f"id-{sender}-{utc_ts}",
        "type": "TEXT",
        "content": text,
        "createdAt": utc_ts,
        "user": {"displayName": sender},
    }

members = [{"displayName": n} for n in ["A", "B", "C", "D", "E"]]
messages = [
    msg("A", "2026-04-20T02:00:00Z", REPORT),   # VN 09:00 on-time
    msg("B", "2026-04-20T14:30:00Z", REPORT),   # VN 21:30 late
    # C, D, E silent
]
data = analyze_weekly(messages, members, "2026-04-20", deadline="20:00")

with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
    path = tmp.name

write_weekly_excel(data, members, path)

import openpyxl
wb = openpyxl.load_workbook(path)
check("sheet 'Tổng hợp tuần' exists", "Tổng hợp tuần" in wb.sheetnames)
check("sheet 'Nội dung' exists", "Nội dung" in wb.sheetnames)
check("exactly 2 sheets", len(wb.sheetnames) == 2)

ws1 = wb["Tổng hợp tuần"]
header1 = [c.value for c in ws1[1]]
check("Tổng hợp tuần headers", header1 == ["Người báo cáo", "Trạng thái", "Giờ gửi"])
rows1 = [[c.value for c in row] for row in ws1.iter_rows(min_row=2, values_only=False)]
check("5 data rows (one per member)", len(rows1) == 5)

# Ordering: Đúng giờ first, then Muộn, then Chưa báo cáo
statuses = [r[1] for r in rows1]
check(
    "status order: Đúng giờ → Muộn → Chưa báo cáo",
    statuses == ["Đúng giờ", "Muộn", "Chưa báo cáo", "Chưa báo cáo", "Chưa báo cáo"],
)
# Missing rows have empty Giờ gửi
missing_hours = [r[2] for r in rows1 if r[1] == "Chưa báo cáo"]
check("missing Giờ gửi is empty/None", all(h in (None, "") for h in missing_hours))

ws2 = wb["Nội dung"]
header2 = [c.value for c in ws2[1]]
check("Nội dung headers", header2 == ["Người báo cáo", "Giờ gửi", "Trạng thái", "Nội dung"])
rows2 = [[c.value for c in row] for row in ws2.iter_rows(min_row=2, values_only=False)]
check("Nội dung has 2 data rows (2 reporters)", len(rows2) == 2)
check("Nội dung ordered by Giờ gửi asc", rows2[0][1] < rows2[1][1])
# Wrap text check
content_cell = ws2.cell(row=2, column=4)
check("Nội dung column has wrap_text enabled",
      content_cell.alignment is not None and content_cell.alignment.wrap_text is True)

print(f"\n{FAIL} failure(s)" if FAIL else "\nAll checks passed.")
pathlib.Path(path).unlink(missing_ok=True)
sys.exit(1 if FAIL else 0)
```

- [ ] **Step 2: Run verifier — should fail**

Run: `python scripts/verify_weekly_excel.py`
Expected: `ImportError: cannot import name 'write_weekly_excel'`.

- [ ] **Step 3: Implement `write_weekly_excel`**

First, look at `write_asm_excel` for the openpyxl idioms used in this repo (around line 627 onwards) and match them (fill colors, header row style, column widths). Then insert after it (around line 740):

```python
def write_weekly_excel(data: dict, group_members: list, path) -> None:
    """Xuất báo cáo tuần ra .xlsx với 2 sheet: Tổng hợp tuần & Nội dung."""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        print("Thiếu 'openpyxl'. Chạy: pip install openpyxl", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.Workbook()

    # --- Sheet 1: Tổng hợp tuần ---
    ws1 = wb.active
    ws1.title = "Tổng hợp tuần"
    ws1.append(["Người báo cáo", "Trạng thái", "Giờ gửi"])

    reports_by_sender = {r["sender"]: r for r in data["reports"]}
    member_names = sorted({
        (m.get("displayName") or "").strip()
        for m in group_members
        if (m.get("displayName") or "").strip()
    })

    def _row_for(name: str):
        r = reports_by_sender.get(name)
        if r is None:
            return (name, "Chưa báo cáo", "")
        return (name, "Muộn" if r["is_late"] else "Đúng giờ", r["sent_at_vn"])

    rows = [_row_for(n) for n in member_names]
    status_order = {"Đúng giờ": 0, "Muộn": 1, "Chưa báo cáo": 2}
    rows.sort(key=lambda r: (status_order[r[1]], r[2] or "ZZ", r[0]))
    for row in rows:
        ws1.append(list(row))

    # Header style
    for cell in ws1[1]:
        cell.font = Font(bold=True)
    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 14
    ws1.column_dimensions["C"].width = 10

    # --- Sheet 2: Nội dung ---
    ws2 = wb.create_sheet("Nội dung")
    ws2.append(["Người báo cáo", "Giờ gửi", "Trạng thái", "Nội dung"])
    for cell in ws2[1]:
        cell.font = Font(bold=True)

    for r in sorted(data["reports"], key=lambda r: r["sent_at_vn"]):
        status = "Muộn" if r["is_late"] else "Đúng giờ"
        extra = f" (+{r['extra_count']} tin nhắn khác)" if r["extra_count"] else ""
        body = r["text"] + (f"\n\n{extra.strip()}" if extra else "")
        ws2.append([r["sender"], r["sent_at_vn"], status, body])

    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 10
    ws2.column_dimensions["C"].width = 12
    ws2.column_dimensions["D"].width = 100

    # Wrap text on Nội dung column for all data rows
    for row_idx in range(2, ws2.max_row + 1):
        ws2.cell(row=row_idx, column=4).alignment = Alignment(
            wrap_text=True, vertical="top"
        )

    wb.save(path)
```

- [ ] **Step 4: Run verifier — should pass**

Run: `python scripts/verify_weekly_excel.py`
Expected: all checks PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/verify_weekly_excel.py fpt_chat_stats.py
git commit -m "$(cat <<'EOF'
feat: thêm write_weekly_excel — xuất 2 sheet (Tổng hợp / Nội dung)

Row order: Đúng giờ → Muộn → Chưa báo cáo, rồi theo Giờ gửi asc,
rồi theo tên. Cột Nội dung bật wrap-text để hiển thị text dài.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Wire up `--weekly` CLI flag

**Files:**
- Modify: `fpt_chat_stats.py` — argparse block around line 791, dispatch in `main()` below that

**What you're building:** The `--weekly YYYY-MM-DD` flag with mutual exclusion against `--today` / `--from` / `--to` / `--date`, plus the pipeline wiring in `main()`.

- [ ] **Step 1: Read existing `main()` layout — know before you code**

Read `fpt_chat_stats.py:742-889` in full. Critical facts the plan relies on:
- **`fetch_all_messages` signature** is `(token, group_id, base_url, limit, date_from)` — it accepts only a `date_from` lower bound. It stops pagination when the oldest fetched page predates `date_from`. There is NO `date_to` parameter. Upper-bound clipping is done client-side via `filter_by_date(messages, date_from, date_to)` (line 102).
- **`fetch_group_members` signature** is `(session, base_url, group_id, limit=50)`. It returns `[]` on error (it already swallows exceptions and logs to stderr). So the failure check is `if not members:` — no try/except needed.
- **Session construction**: use `build_session(token)` (line 91) — this is what the existing compliance path does at line 864.
- **`--date`, `--today`, `--from`, `--to`** all already exist and `--today` already enforces mutual exclusion against `--from/--to/--date` (line 812). The plan adds `--weekly` with the same exclusion pattern.
- **Config read pattern**: the existing code reads config via `cfg = load_config(args.config)` early in `main`; deadline value lives at `cfg.get("deadline", "20:00")`. Reuse.
- **Message fetch + filter pattern** (lines 830-849): fetch, save raw, then `filter_by_date(messages, date_from, date_to)`. The weekly branch must replicate this pattern so snapshots captured via `--save` replay identically.

You'll slot `--weekly` into `main` as an **early-return branch** (before the existing daily dispatch at line ~851), not a restructure.

- [ ] **Step 2: Add the argparse flag**

In the `add_argument` section (near line 791), add:

```python
parser.add_argument(
    "--weekly",
    default=None,
    metavar="YYYY-MM-DD",
    help="Báo cáo tuần một ngày: liệt kê ai đã/muộn/chưa báo cáo + dump text.",
)
```

- [ ] **Step 3: Add mutual-exclusion check**

Right after `args = parser.parse_args()` in `main`, before any fetch happens:

```python
if args.weekly and (args.today or args.date_from or args.date_to or args.date):
    print(
        "Error: --weekly không dùng chung với --today / --from / --to / --date.",
        file=sys.stderr,
    )
    sys.exit(2)
```

- [ ] **Step 4: Add dispatch branch in `main`**

Insert this block right after the existing `--today` shortcut block (around line 821, after `args.date = _vn_today`) so it runs before any of the daily-flow computation. Replace the placeholder variable names if yours differ — the outer scope already has `token`, `group`, `api_url`, `args`, `cfg`.

```python
# ── --weekly shortcut (báo cáo tuần một ngày)
if args.weekly:
    try:
        target_vn = datetime.strptime(args.weekly, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: --weekly giá trị không hợp lệ: {args.weekly}", file=sys.stderr)
        sys.exit(2)

    # Half-open VN-day window: [target 00:00+07, target+1 00:00+07)
    # In UTC: [target 00:00+07 - 7h, target 00:00+07 - 7h + 24h) == [target-1 17:00Z, target 17:00Z)
    vn_start_utc = datetime.combine(target_vn, time(0, 0), tzinfo=timezone.utc) - timedelta(hours=7)
    vn_end_utc   = vn_start_utc + timedelta(days=1)

    # Fetch or load raw messages (same save/load pattern as daily path)
    if args.load:
        print(f"[*] Loading từ file: {args.load}", file=sys.stderr)
        with open(args.load, encoding="utf-8") as f:
            messages = json.load(f)
        print(f"[✓] Loaded {len(messages)} messages", file=sys.stderr)
    else:
        if not token:
            print("Error: --weekly cần --token (hoặc config.json).", file=sys.stderr)
            sys.exit(1)
        if not group:
            print("Error: --weekly cần --group (hoặc config.json).", file=sys.stderr)
            sys.exit(1)
        group_id = extract_group_id(group)
        messages = fetch_all_messages(
            token=token, group_id=group_id, base_url=api_url,
            limit=args.limit, date_from=vn_start_utc,
        )

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"[✓] Đã lưu raw messages → {args.save}", file=sys.stderr)

    # Clip to the half-open window. filter_by_date uses inclusive date_to, so subtract
    # 1 microsecond to emulate half-open [start, end).
    messages = filter_by_date(
        messages, vn_start_utc, vn_end_utc - timedelta(microseconds=1),
    )

    # Members are required for the missing-list — weekly cannot run without them.
    if not token or not group:
        print(
            "Error: --weekly cần token+group để lấy thành viên group cho compliance check.",
            file=sys.stderr,
        )
        sys.exit(3)
    _session = build_session(token)
    members = fetch_group_members(_session, api_url, extract_group_id(group))
    if not members:
        print(
            "Error: fetch_group_members trả rỗng hoặc lỗi — hủy báo cáo tuần.",
            file=sys.stderr,
        )
        sys.exit(3)

    deadline = cfg.get("deadline", "20:00")
    data = analyze_weekly(messages, members, args.weekly, deadline=deadline)
    print_weekly_report(data)
    if args.excel:
        write_weekly_excel(data, members, args.excel)
        print(f"[✓] Đã xuất Excel → {args.excel}", file=sys.stderr)
    return
```

Key points to double-check while you write this:
- Imports at the top of `fpt_chat_stats.py` already include `timedelta`, `time`, `timezone` (line 21) — no new imports needed.
- The branch calls `return` so the daily-flow code below never runs when `--weekly` is set.
- Members fetch is REQUIRED even in `--load` mode. This means offline replay of weekly requires live token+group for members. Document this limitation in Task 6.

- [ ] **Step 5: Smoke-test CLI parsing**

Run:
```bash
python fpt_chat_stats.py --weekly 2026-04-20 --today 2>&1
```
Expected: exits non-zero with the mutual-exclusion error.

Run:
```bash
python fpt_chat_stats.py --weekly bad-date 2>&1
```
Expected: exits non-zero with "giá trị không hợp lệ".

Run:
```bash
python fpt_chat_stats.py --weekly 2026-04-20 --help 2>&1 | head -20
```
Expected: `--weekly` listed in help text.

- [ ] **Step 6: Commit**

```bash
git add fpt_chat_stats.py
git commit -m "$(cat <<'EOF'
feat: thêm CLI flag --weekly YYYY-MM-DD

Loại trừ --today/--from/--to/--date. Fetch window VN-day half-open
[target 00:00+07, target+1 00:00+07). Lỗi lấy members → exit non-zero,
không ghi báo cáo một phần.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Manual integration test with real snapshot

**Files:** none modified; this is a manual verification step.

**What you're verifying:** The full end-to-end path works against realistic data.

**Prerequisite:** This task requires live API access (token + group in `config.json` or via `--token`/`--group`). Members are fetched live in both `--save` and `--load` modes because the weekly pipeline hard-requires a members list for the missing check.

- [ ] **Step 1: Capture a snapshot of a real weekend day**

Pick a recent Saturday or Sunday when you know ASMs submitted weekly reports. Run:

```bash
python fpt_chat_stats.py --weekly 2026-04-19 --save raw_2026-04-19.json
```

Expected: produces `raw_2026-04-19.json` and prints the weekly report.

- [ ] **Step 2: Re-run from the snapshot (still needs live credentials for members)**

```bash
python fpt_chat_stats.py --weekly 2026-04-19 --load raw_2026-04-19.json
```

Expected: messages loaded from file, members fetched live. Output is effectively identical to Step 1 (messages are identical; member list may drift slightly over time if people join/leave the group).

- [ ] **Step 3: Spot-check results manually**

Against what you know about that day:
- [ ] Names in `Chưa báo cáo` really did not post on that VN day.
- [ ] Names in `Muộn` posted after 20:00 VN time.
- [ ] Content dumps show each ASM's actual weekly report text verbatim.
- [ ] Any short "Ok anh" / "Nhận rồi ạ" acknowledgments are NOT listed as reports.
- [ ] Any `(+N tin nhắn khác)` notes make sense (ASM sent multiple qualifying messages).

- [ ] **Step 4: Generate Excel**

```bash
python fpt_chat_stats.py --weekly 2026-04-19 --load raw_2026-04-19.json --excel test_weekly.xlsx
```

Open `test_weekly.xlsx` and confirm:
- [ ] Two sheets: `Tổng hợp tuần`, `Nội dung`.
- [ ] `Tổng hợp tuần` has one row per group member in the correct status order.
- [ ] `Nội dung` column wraps long text (no clipping).

- [ ] **Step 5: DO NOT commit the snapshot or test xlsx**

These contain real chat content. Add to gitignore if not already present, or just delete:

```bash
rm raw_2026-04-19.json test_weekly.xlsx
```

---

## Task 7: Streamlit UI — "Báo cáo tuần" section

**Files:**
- Modify: `app.py`

**What you're building:** A new section/tab alongside the existing daily / multi-day views, with a date picker, deadline re-used from the group's library entry, a Run button, rendering of the three buckets + a content table, and a download button for Excel.

- [ ] **Step 1: Read the existing UI layout in `app.py`**

Identify:
- How the current tabs/sections are laid out (`st.tabs`, `st.radio`, or separate sections).
- How group config (deadline) is read from `_LIB_KEY` / library state.
- How messages and members are currently fetched in the run handler.
- How the existing Excel download button is wired (`st.download_button` with `io.BytesIO`).

You will reuse all of these — no new auth/fetch/localStorage plumbing.

- [ ] **Step 2: Add a new section**

Near the existing daily/multi-day section, add a new one. The exact UI pattern depends on what app.py already uses (tabs vs radio), but the content is:

```python
# --- Báo cáo tuần ---
st.subheader("Báo cáo tuần")
target_date = st.date_input("Ngày báo cáo tuần", value=date.today())
run_weekly = st.button("Chạy báo cáo tuần")

if run_weekly:
    with st.spinner("Đang fetch tin nhắn..."):
        # Fetch messages for the VN day using the existing auth/session
        vn_start_utc = datetime.combine(target_date, time(0, 0), tzinfo=timezone.utc) - timedelta(hours=7)
        vn_end_utc = vn_start_utc + timedelta(days=1)
        messages = fetch_all_messages(
            token=token, group_id=group_id, base_url=api_url,
            date_from=vn_start_utc, date_to=vn_end_utc, limit=50,
        )
        try:
            members = fetch_group_members(session, api_url, group_id)
        except Exception as e:
            st.error(f"Lỗi lấy thành viên group: {e}")
            st.stop()
        if not members:
            st.error("Danh sách thành viên group rỗng. Hủy báo cáo tuần.")
            st.stop()

    deadline = group_config.get("deadline", "20:00")  # name matches existing code
    data = analyze_weekly(messages, members, target_date.strftime("%Y-%m-%d"), deadline=deadline)

    c1, c2, c3 = st.columns(3)
    c1.metric("Đã báo cáo", len(data["reports"]))
    c2.metric("Muộn", len(data["late_list"]))
    c3.metric("Chưa báo cáo", len(data["missing_list"]))

    if data["missing_list"]:
        st.markdown(f"**Chưa báo cáo ({len(data['missing_list'])}):**")
        for n in data["missing_list"]:
            st.markdown(f"- {n}")

    if data["late_list"]:
        st.markdown(f"**Muộn ({len(data['late_list'])}):**")
        late_map = {r["sender"]: r["sent_at_vn"] for r in data["reports"] if r["is_late"]}
        for n in data["late_list"]:
            st.markdown(f"- {n} ({late_map.get(n, '?')})")

    if data["reports"]:
        st.markdown("**Nội dung báo cáo:**")
        rows = [{
            "Người báo cáo": r["sender"],
            "Giờ gửi": r["sent_at_vn"],
            "Trạng thái": "Muộn" if r["is_late"] else "Đúng giờ",
            "Nội dung": r["text"] + (f"\n\n(+{r['extra_count']} tin nhắn khác)" if r["extra_count"] else ""),
        } for r in data["reports"]]
        st.dataframe(rows, use_container_width=True, height=400)

    # Download Excel
    import io as _io
    buf = _io.BytesIO()
    write_weekly_excel(data, members, buf)
    buf.seek(0)
    st.download_button(
        "Tải Excel báo cáo tuần",
        data=buf.read(),
        file_name=f"bao_cao_tuan_{target_date.strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
```

Note: `write_weekly_excel` calls `wb.save(path)` which accepts a file path OR a file-like object. The `BytesIO` pattern above works because openpyxl treats both the same.

- [ ] **Step 3: Import additions at top of `app.py`**

Ensure these are imported from `fpt_chat_stats`:

```python
from fpt_chat_stats import (
    # ... existing ...
    analyze_weekly,
    write_weekly_excel,
)
from datetime import date, datetime, time, timedelta, timezone
```

- [ ] **Step 4: Manual UI validation**

Start the app:

```bash
streamlit run app.py
```

In the browser:
- [ ] Navigate to the "Báo cáo tuần" section.
- [ ] Pick yesterday's date. Click Run.
- [ ] Verify the three metric boxes display sensible counts.
- [ ] Verify `Chưa báo cáo` list contains names.
- [ ] Verify the content table renders with wrapped text (no truncation of long reports).
- [ ] Click "Tải Excel báo cáo tuần" and open the file: verify both sheets are correct.
- [ ] Change the date to a day with no reports (e.g. a weekday if weekly is Sun). Verify it still renders with empty tables and correct zero counts (no crash).

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "$(cat <<'EOF'
feat(ui): thêm section "Báo cáo tuần" trong Streamlit

Date picker + Run → 3 metric + danh sách Chưa/Muộn + dataframe nội
dung + nút tải Excel. Dùng lại auth/fetch/members existing, không
plumbing mới.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Update canonical specs and finalize change

**Files:**
- Modify: `openspec/specs/fpt-chat-stats/spec.md`
- Modify: `openspec/specs/web-ui/spec.md`

**What you're doing:** After implementation passes all verifiers, fold the change's `ADDED Requirements` deltas into the canonical spec files. This is an OpenSpec housekeeping step.

- [ ] **Step 1: Re-run `openspec validate` on the change**

```bash
openspec validate 2026-04-20-add-weekly-report --strict --no-interactive
```

Expected: `valid`.

- [ ] **Step 2: Apply the change**

Follow the repo's OpenSpec workflow (see `openspec/AGENTS.md`). Typically this means copying the `ADDED Requirements` blocks from `openspec/changes/2026-04-20-add-weekly-report/specs/*/spec.md` into the corresponding canonical `openspec/specs/*/spec.md` files.

If the repo has an `openspec apply <id>` command, run it; otherwise do the merge manually by hand.

- [ ] **Step 3: Archive the change directory**

Move `openspec/changes/2026-04-20-add-weekly-report/` into `openspec/changes/archive/`:

```bash
mv openspec/changes/2026-04-20-add-weekly-report openspec/changes/archive/
```

- [ ] **Step 4: Run all verifiers one more time**

```bash
python scripts/verify_weekly_classifier.py
python scripts/verify_analyze_weekly.py
python scripts/verify_weekly_excel.py
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add openspec/
git commit -m "$(cat <<'EOF'
chore(openspec): áp requirement báo cáo tuần + archive change

Fold ADDED Requirements từ 2026-04-20-add-weekly-report vào specs
gốc, move change sang archive.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Verification Summary

At the end of all tasks you should be able to run, in order:

```bash
python scripts/verify_weekly_classifier.py    # Task 1 — pure classifier
python scripts/verify_analyze_weekly.py       # Tasks 2 & 3 — pipeline + print
python scripts/verify_weekly_excel.py         # Task 4 — Excel writer
python fpt_chat_stats.py --weekly 2026-04-19 --load raw_2026-04-19.json        # Task 5 — CLI e2e
python fpt_chat_stats.py --weekly 2026-04-19 --load raw_2026-04-19.json --excel out.xlsx  # full path
streamlit run app.py                                                            # Task 7 — UI
openspec validate 2026-04-20-add-weekly-report --strict --no-interactive       # Task 8 — spec applied
```

All three verifier scripts must exit 0. The CLI runs must produce sensible output for a real weekend snapshot. The UI must render without errors.

## Non-goals in this plan

- No new test framework (pytest/unittest). The verifier scripts under `scripts/` are the testing story.
- No refactor of `fpt_chat_stats.py` beyond adding the new functions. Single-file convention stays.
- No extraction of the classifier into its own module. Constants + scoring function live alongside `detect_asm_reports`.
- No metric parsing of TTTC content. Raw text only, per client's explicit ask.
- No changes to daily / multi-day flows.
