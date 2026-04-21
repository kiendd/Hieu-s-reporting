# Weekly Report Structured Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-04-20-weekly-structured-metrics-design.md`

**Goal:** Make the weekly report surface structured KPIs (Shop VT cọc/ra tiêm + TTTC revenue/bill/%HOT) alongside the existing compliance/raw-text view, via two parsers dispatched by a `classify_report` step.

**Architecture:** Incremental, composable build. Each new unit (helper, parser, analyzer) is landed with its own verifier first, then wired into `analyze_weekly`, then surfaced in CLI print / Excel / Streamlit in that order. Daily page is never touched except for a one-line refactor that extracts a shared render helper. Classifier runs *after* `_score_weekly_message` qualifies the message — the two live side by side without interference.

**Tech Stack:**
- Python 3.11+ single-file `fpt_chat_stats.py` (~900 lines by convention).
- Streamlit for UI (`app.py`).
- openpyxl for Excel.
- Verifiers: standalone scripts under `scripts/`, run via `python scripts/verify_*.py`. Exit 0 = pass, exit 1 = fail. Follow the existing `check() + global FAIL + sys.exit(1 if FAIL else 0)` pattern.
- No pytest, no new dependencies.
- Repo convention: Vietnamese commit messages + `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer. Commits land directly on `main`.

**Verifier invocation convention:** Every verifier script must do `sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))` before importing from `fpt_chat_stats`, and run from repo root (`python scripts/verify_foo.py`). Use `try: p.read_text() except FileNotFoundError: check(..., False); continue` around template file reads so a missing template is a test failure, not a crash.

**Ordering rationale (why this sequence):**
1. Pure helpers first (`_parse_vnd_amount`, relaxed `_extract_sections`) — no dependencies, highest reuse.
2. `classify_report` — trivial, unblocks everything.
3. `parse_tttc_report` — depends on helpers above.
4. `analyze_tttc_reports` — depends on parser output shape.
5. Wire into `analyze_weekly` — the integration point.
6. Then CLI print, then Excel, then Streamlit (ordered cheap → expensive in manual verification cost).

---

## File Map

| File | Role |
|---|---|
| `fpt_chat_stats.py` | add `_parse_vnd_amount`, `classify_report`, `parse_tttc_report`, `analyze_tttc_reports`; relax `_extract_sections`; update `analyze_weekly`, `print_weekly_report`, `write_weekly_excel` |
| `app.py` | extract `_render_shop_vt_sections` helper (shared with daily); add `_render_tttc_sections`; wire into `_render_weekly_result` |
| `scripts/verify_vnd_parsing.py` | new — unit cases for `_parse_vnd_amount` |
| `scripts/verify_extract_sections.py` | new — guards relaxed regex still handles all daily + W7 + numbered TTTC forms |
| `scripts/verify_classify_report.py` | new — 8 weekend + 7 daily + 5 negatives |
| `scripts/verify_parse_tttc.py` | new — per-template expected-field matrix |
| `scripts/verify_analyze_tttc.py` | new — aggregator edge cases |
| `scripts/verify_analyze_weekly.py` | extend — new cases for `asm_data` / `tttc_data` presence |
| `scripts/verify_weekly_excel.py` | extend — assert new Shop VT + TTTC sheets exist with correct headers |

---

## Task 1: `_parse_vnd_amount` helper + verifier

**Files:**
- Modify: `fpt_chat_stats.py` — add helper next to `_extract_sections` (around line 275, before `parse_asm_report` at line 289).
- Create: `scripts/verify_vnd_parsing.py`

**Why first:** Lowest dependency; the TTTC parser's highest-risk surface. Landing it with its own verifier lets Task 4 assume correctness.

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_vnd_parsing.py`:

```python
#!/usr/bin/env python3
"""Verify _parse_vnd_amount handles Vietnamese number conventions.

Run from repo root: python scripts/verify_vnd_parsing.py
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import _parse_vnd_amount

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

CASES = [
    # (raw,         unit_suffix,    expected)
    ("2,2",         "tr",           2_200_000),
    ("2,3",         "M",            2_300_000),
    ("1.625",       "tr",           1_625_000),
    ("0,5",         "triệu",        500_000),
    ("134.927.000", None,           134_927_000),
    ("1.625,000",   None,           1_625_000),
    ("2.248.153",   None,           2_248_153),
    ("500",         None,           500),
    # Unresolvable: fractional without unit
    ("1,5",         None,           None),
    # Garbage
    ("abc",         None,           None),
    ("",            None,           None),
]

print("_parse_vnd_amount cases")
for raw, unit, expected in CASES:
    got = _parse_vnd_amount(raw, unit)
    check(f"_parse_vnd_amount({raw!r}, {unit!r}) = {got!r} (expected {expected!r})",
          got == expected)

print()
if FAIL:
    print(f"FAIL: {FAIL} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
```

- [ ] **Step 2: Run verifier — expect import error**

```bash
python scripts/verify_vnd_parsing.py
```
Expected: `ImportError: cannot import name '_parse_vnd_amount' from 'fpt_chat_stats'`.

- [ ] **Step 3: Implement `_parse_vnd_amount`**

Insert into `fpt_chat_stats.py` directly above `def _extract_sections` (line 275). The function must match the verifier cases above exactly.

```python
def _parse_vnd_amount(raw: str, unit_suffix: str | None) -> int | None:
    """Normalize a Vietnamese-formatted amount string to an integer VND.

    Rules (in order):
      1. If unit_suffix ∈ {"tr", "M", "triệu"}: scale = 1_000_000.
         - `,` or `.` followed by 1-2 digits → decimal part.
         - e.g. "2,2" + "tr" → 2_200_000; "1.625" + "tr" → 1_625_000.
      2. Without a unit suffix: both `,` and `.` are thousand separators.
         - e.g. "134.927.000" → 134_927_000; "1.625,000" → 1_625_000.
      3. If the input is unresolvable (fractional without unit, non-numeric, empty): return None.
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None

    if unit_suffix in ("tr", "M", "triệu"):
        # allow one decimal separator of 1-2 digits
        m = re.fullmatch(r"(\d+)(?:[.,](\d{1,2}))?", s)
        if not m:
            return None
        whole = int(m.group(1))
        frac  = m.group(2)
        if frac is None:
            return whole * 1_000_000
        # "2,2" → 2.2M; "1.625" → 1.625M
        scaled = whole * 1_000_000 + int(frac) * (10 ** (6 - len(frac)))
        return scaled

    # No unit: both . and , are thousand separators
    if not re.fullmatch(r"\d+(?:[.,]\d+)*", s):
        return None
    # Reject if any group after the first has != 3 digits
    digits_only = re.sub(r"[.,]", "", s)
    # Require that removing separators leaves pure digits and that each
    # separated group after the first is exactly 3 digits (thousand grouping).
    groups = re.split(r"[.,]", s)
    if len(groups) > 1 and any(len(g) != 3 for g in groups[1:]):
        return None
    try:
        return int(digits_only)
    except ValueError:
        return None
```

- [ ] **Step 4: Run verifier — expect all PASS**

```bash
python scripts/verify_vnd_parsing.py
```
Expected: `OK: all checks passed`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_vnd_parsing.py
git commit -m "$(cat <<'EOF'
feat: thêm helper _parse_vnd_amount chuẩn hoá số tiền VN

Xử lý "2,2tr", "1.625,000", "134.927.000" theo quy tắc 3 bước
trong spec. Có verifier kiểm tra 11 ca đại diện.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Relax `_extract_sections` + regression verifier

**Files:**
- Modify: `fpt_chat_stats.py:275-286` (replace `_extract_sections` body).
- Create: `scripts/verify_extract_sections.py`

**Why:** Must land before `parse_tttc_report` because that parser depends on the relaxed behaviour. Must not break daily — daily's `parse_asm_report` calls `_extract_sections` directly.

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_extract_sections.py`:

```python
#!/usr/bin/env python3
"""Verify _extract_sections accepts all three label forms.

Run: python scripts/verify_extract_sections.py
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import _extract_sections

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

def has_key(d: dict, needle: str) -> bool:
    return any(needle in k for k in d)

# Form A: bullet-prefixed (daily convention)
A = """
- Kết quả: 12 cọc
- Tích cực: khoẻ
- Vấn đề: chậm
- Đã làm: coaching
"""
sa = _extract_sections(A)
check("form A: has tích cực", has_key(sa, "tích cực"))
check("form A: has vấn đề",   has_key(sa, "vấn đề"))
check("form A: has đã làm",   has_key(sa, "đã làm"))

# Form B: bare Label: (W7 Shop VT weekday template)
B = """
Dạ em bc Đánh giá nhanh Shop: LC HCM 20
Kết quả: 12 cọc | 88 KH tư vấn | 19 KH ra tiêm
Tích cực: bạn chịu khó
Vấn đề: KH cũ từ chối
Đã làm: kèm tư vấn 1-1
Ngày mai: tiếp tục
"""
sb = _extract_sections(B)
check("form B: has tích cực (bare label)", has_key(sb, "tích cực"))
check("form B: has vấn đề (bare label)",   has_key(sb, "vấn đề"))
check("form B: has đã làm (bare label)",   has_key(sb, "đã làm"))

# Form C: numbered "N. Label:" (W1 TTTC template)
C = """
Em xin phép đánh giá nhanh TTTC: 58192
1. Kết quả:
- DT trong ngày: 66,9tr/50tr
- TB Bill: 2,2tr
2. Điểm sáng & Điểm hạn chế các chỉ số MTD:
- Tỉ trọng doanh thu HOT: 58%
3. Giải pháp:
- Kèm TVV ôn luyện kịch bản
"""
sc = _extract_sections(C)
check("form C: has kết quả (numbered)",    has_key(sc, "kết quả"))
check("form C: has giải pháp (numbered)",  has_key(sc, "giải pháp"))

# Regression: all daily templates still parse standard sections
print("\nRegression: daily templates keep tích cực/vấn đề/đã làm")
for i in range(1, 8):
    p = pathlib.Path(f"templates/daily/{i}")
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        check(f"daily/{i}: file missing", False)
        continue
    s = _extract_sections(text)
    check(f"daily/{i}: has tích cực", has_key(s, "tích cực"))
    check(f"daily/{i}: has vấn đề",   has_key(s, "vấn đề"))
    check(f"daily/{i}: has đã làm",   has_key(s, "đã làm"))

print()
if FAIL:
    print(f"FAIL: {FAIL} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
```

- [ ] **Step 2: Run verifier against current code — expect failures on forms B and C**

```bash
python scripts/verify_extract_sections.py
```
Expected: forms A and daily regression PASS; forms B and C FAIL.

- [ ] **Step 3: Replace `_extract_sections`**

Replace lines 275-286 of `fpt_chat_stats.py` with:

```python
def _extract_sections(content: str) -> dict:
    """Trích các mục báo cáo. Hỗ trợ 3 dạng nhãn:
      - '- Label: content' (bullet)
      - 'Label: content' (bare, bắt buộc Label viết hoa chữ cái đầu)
      - 'N. Label:' (numbered heading, nội dung nằm ở các bullet theo sau)
    Trả về dict { label_lower: text } gộp các dòng cho đến nhãn tiếp theo.
    """
    # Normalize: a label-start line is any of:
    #   - optional `[-–•]` or `N.` prefix
    #   - followed by a label (2-40 chars, starts with a letter, no ':')
    #   - followed by ':' or '：'
    label_re = re.compile(
        r"""^[ \t]*                              # leading ws
            (?:[-–•]|\d+\.)?[ \t]*               # optional bullet / number
            (?P<label>[A-ZÀ-Ỵa-zà-ỵ][^\n:：]{1,40}?)
            [ \t]*[:：][ \t]*                    # colon (ascii or fullwidth)
            (?P<rest>.*)$                        # same-line content (may be empty)
        """,
        re.VERBOSE,
    )

    sections: dict[str, str] = {}
    current_label: str | None = None
    current_buf: list[str] = []

    def flush():
        nonlocal current_label, current_buf
        if current_label is not None:
            sections[current_label] = "\n".join(current_buf).strip()
        current_label = None
        current_buf = []

    for line in content.splitlines():
        m = label_re.match(line)
        if m:
            flush()
            current_label = m.group("label").strip().lower()
            rest = m.group("rest").strip()
            current_buf = [rest] if rest else []
        else:
            if current_label is not None:
                current_buf.append(line)
    flush()
    return sections
```

- [ ] **Step 4: Run verifier — expect all PASS**

```bash
python scripts/verify_extract_sections.py
```
Expected: `OK: all checks passed`.

- [ ] **Step 5: Re-run existing regression verifiers**

```bash
python scripts/verify_weekly_classifier.py
python scripts/verify_analyze_weekly.py
python scripts/verify_weekly_excel.py
```
Expected: all three still pass 100%. (None of them depend on section labels from daily templates, but run as a safety net.)

- [ ] **Step 6: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_extract_sections.py
git commit -m "$(cat <<'EOF'
feat: nới _extract_sections nhận 3 dạng nhãn (bullet/bare/numbered)

W7 Shop VT dùng "Tích cực:" không có gạch đầu dòng, W1 TTTC dùng
"1. Kết quả:" dạng đánh số — cả hai trước đây đều rơi về dict rỗng.
Regex mới nhận cả ba dạng, daily templates vẫn parse như cũ (regression
verifier bao 7 template daily + 3 form đặc trưng).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `classify_report` + verifier

**Files:**
- Modify: `fpt_chat_stats.py` — add `classify_report` right after `_score_weekly_message` (around line 256).
- Create: `scripts/verify_classify_report.py`

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_classify_report.py`:

```python
#!/usr/bin/env python3
"""Verify classify_report buckets messages into shop_vt / tttc / unknown.

Run: python scripts/verify_classify_report.py
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import classify_report

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

# Weekend templates: W7 = shop_vt; all others = tttc
WEEKEND_EXPECTED = {1: "tttc", 2: "tttc", 3: "tttc", 4: "tttc",
                    5: "tttc", 6: "tttc", 7: "shop_vt", 8: "tttc"}

print("Weekend templates (templates/weekend/*)")
for i in range(1, 9):
    p = pathlib.Path(f"templates/weekend/{i}")
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        check(f"weekend/{i}: file missing", False)
        continue
    got = classify_report(text)
    exp = WEEKEND_EXPECTED[i]
    check(f"weekend/{i}: got {got!r} (expected {exp!r})", got == exp)

print("\nDaily templates (all should be shop_vt)")
for i in range(1, 8):
    p = pathlib.Path(f"templates/daily/{i}")
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        check(f"daily/{i}: file missing", False)
        continue
    got = classify_report(text)
    check(f"daily/{i}: got {got!r} (expected 'shop_vt')", got == "shop_vt")

print("\nNegatives (no cọc, no TTTC cue → unknown)")
negatives = [
    "Ok anh",
    "Nghỉ trưa nha mọi người",
    "Em đang trên đường tới shop",
    "",
    "Cám ơn mọi người nhé",
]
for s in negatives:
    got = classify_report(s)
    check(f"negative {s[:30]!r}: got {got!r}", got == "unknown")

print()
if FAIL:
    print(f"FAIL: {FAIL} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
```

- [ ] **Step 2: Run verifier — expect import error**

```bash
python scripts/verify_classify_report.py
```
Expected: `ImportError: cannot import name 'classify_report'`.

- [ ] **Step 3: Implement `classify_report`**

Insert into `fpt_chat_stats.py` right after `_score_weekly_message` (before `# ---- ASM Report Analysis ----` at line 258):

```python
_CLASSIFY_RE_COC = re.compile(r"\d+\s*cọc|cọc\s*\d+", re.IGNORECASE)
_CLASSIFY_RE_TTTC = re.compile(
    r"\bTTTC\b|TB\s*[Bb]ill|%\s*HT|doanh\s*thu",
    re.IGNORECASE,
)


def classify_report(content: str) -> str:
    """Phân loại loại báo cáo: 'shop_vt' | 'tttc' | 'unknown'.

    Dấu hiệu Shop VT mạnh nhất là "N cọc" — có thì trả shop_vt luôn.
    Nếu không có cọc nhưng có dấu hiệu TTTC (TTTC / TB bill / %HT / doanh thu)
    thì là tttc. Còn lại → unknown.
    """
    if not content:
        return "unknown"
    if _CLASSIFY_RE_COC.search(content):
        return "shop_vt"
    if _CLASSIFY_RE_TTTC.search(content):
        return "tttc"
    return "unknown"
```

- [ ] **Step 4: Run verifier — expect all PASS**

```bash
python scripts/verify_classify_report.py
```
Expected: `OK: all checks passed`.

- [ ] **Step 5: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_classify_report.py
git commit -m "$(cat <<'EOF'
feat: thêm classify_report phân loại shop_vt / tttc / unknown

"N cọc" là cờ Shop VT mạnh nhất (check trước), nếu không có thì tìm
cờ TTTC (TTTC / TB bill / %HT / doanh thu). Verifier bao 8 template
weekend + 7 daily + 5 negative.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `parse_tttc_report` + verifier

**Files:**
- Modify: `fpt_chat_stats.py` — add `parse_tttc_report` after `parse_asm_report` (around line 328).
- Create: `scripts/verify_parse_tttc.py`

**Depends on:** Task 1 (`_parse_vnd_amount`), Task 2 (relaxed `_extract_sections`).

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_parse_tttc.py`. Expected fields per template are taken verbatim from the spec's coverage matrix:

```python
#!/usr/bin/env python3
"""Verify parse_tttc_report extracts the expected field matrix per template.

Run: python scripts/verify_parse_tttc.py
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import parse_tttc_report

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

def load(i: int) -> dict:
    text = pathlib.Path(f"templates/weekend/{i}").read_text(encoding="utf-8")
    return {
        "id": f"w{i}",
        "type": "TEXT",
        "content": text,
        "createdAt": "2026-04-20T02:00:00Z",
        "user": {"id": "u1", "displayName": "Test ASM"},
    }

# (template_id, {field: non-null? bool or expected-numeric})
# bool True  = expect non-None, bool False = expect None
# int value  = expect exactly this value (for the highest-confidence cases)
EXPECTATIONS = {
    # W1: TTTC 58192
    1: {"venue": True, "revenue_pct": True, "hot_pct": True,
        "hot_ratio": True, "tb_bill": True, "customer_count": True},
    # W2: shop VX Dĩ An — narrative, mostly null
    2: {"venue": True, "revenue_pct": False, "hot_pct": False,
        "hot_ratio": False, "tb_bill": True, "customer_count": True},
    # W3: VX Yersin — MTD only
    3: {"venue": True, "revenue_pct": True, "hot_pct": False,
        "hot_ratio": True, "tb_bill": False, "customer_count": False},
    # W4: TTTC 580NDT — narrative
    4: {"venue": True, "revenue_pct": True, "hot_pct": True,
        "hot_ratio": False, "tb_bill": False, "customer_count": False},
    # W5: TTTC 58149
    5: {"venue": True, "revenue_pct": True, "hot_pct": False,
        "hot_ratio": True, "tb_bill": True, "customer_count": True},
    # W6: TTTC 58052
    6: {"venue": True, "revenue_pct": True, "hot_pct": True,
        "hot_ratio": False, "tb_bill": True, "customer_count": False},
    # W8: TTTC 533 Lạc Long Quân
    8: {"venue": True, "revenue_pct": True, "hot_pct": False,
        "hot_ratio": True, "tb_bill": True, "customer_count": True},
}

for tid, expected in EXPECTATIONS.items():
    try:
        msg = load(tid)
    except FileNotFoundError:
        check(f"weekend/{tid}: file missing", False)
        continue
    got = parse_tttc_report(msg)
    print(f"\nTemplate W{tid}: parsed = {{"
          f"venue={got.get('venue')!r}, "
          f"revenue_pct={got.get('revenue_pct')!r}, "
          f"hot_pct={got.get('hot_pct')!r}, "
          f"hot_ratio={got.get('hot_ratio')!r}, "
          f"tb_bill={got.get('tb_bill')!r}, "
          f"customer_count={got.get('customer_count')!r}}}")
    for field, want_present in expected.items():
        actual = got.get(field)
        if want_present:
            check(f"W{tid}.{field}: non-null", actual is not None)
        else:
            check(f"W{tid}.{field}: None", actual is None)

# Structural checks
print("\nStructural")
m = load(7)  # Shop VT template — parse_tttc_report still runs, nulls expected
out = parse_tttc_report(m)
check("parse_tttc_report never raises on Shop VT input",
      isinstance(out, dict))
check("parse_tttc_report sets sender from user.displayName",
      out.get("sender") == "Test ASM")
check("parse_tttc_report sets message_id",
      out.get("message_id") == "w7")

print()
if FAIL:
    print(f"FAIL: {FAIL} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
```

- [ ] **Step 2: Run verifier — expect import error**

```bash
python scripts/verify_parse_tttc.py
```
Expected: `ImportError: cannot import name 'parse_tttc_report'`.

- [ ] **Step 3: Implement `parse_tttc_report`**

Insert into `fpt_chat_stats.py` after `parse_asm_report` (around line 328, before `def analyze_asm_reports`):

```python
# ---------------------------------------------------------------------------
# TTTC Parser (weekly report — weekend shape)
# ---------------------------------------------------------------------------

_TTTC_VENUE_RE = re.compile(
    r"(TTTC|VX|LC|shop)\s*[:\-]?\s*([^\n]+)",
    re.IGNORECASE,
)

# Percent near the word "doanh thu" / "DT" / "DS" / "HT" (excluding HOT)
_TTTC_REVENUE_PCT_RE = re.compile(
    r"(?:doanh\s*thu|DT(?!\s*HOT)|DS(?!\s*Hot)|HT|đạt|về)\s*"
    r"[^%\n]{0,40}?(\d[\d.,]*)\s*%",
    re.IGNORECASE,
)
_TTTC_HOT_PCT_RE = re.compile(
    r"(?:DT\s*HOT|DS\s*Hot|\bHot)\b[^%\n]{0,40}?(\d[\d.,]*)\s*%",
    re.IGNORECASE,
)
_TTTC_HOT_RATIO_RE = re.compile(
    r"[Tt][ỉỷi]\s*trọng\s*(?:doanh\s*thu\s*)?HOT[^%\n]{0,15}?(\d[\d.,]*)\s*%",
    re.IGNORECASE,
)
_TTTC_TB_BILL_RE = re.compile(
    r"TB\s*[Bb]ill|[Gg]iá\s*trị\s*bill",
    re.IGNORECASE,
)
_TTTC_TB_BILL_VALUE_RE = re.compile(
    r"(?:TB\s*[Bb]ill|[Gg]iá\s*trị\s*bill)[^\d]*([\d.,]+)\s*(tr|M|triệu)?",
    re.IGNORECASE,
)
_TTTC_CUSTOMER_RE = re.compile(
    r"(?:[Ll]ượt\s*)?(?:KH|khách)\s*mua[^\d]*(\d+)",
)


def _first_n_lines(content: str, n: int = 3) -> str:
    """Return the first n non-empty lines of content joined by newline."""
    out = []
    for line in content.splitlines():
        if line.strip():
            out.append(line)
            if len(out) >= n:
                break
    return "\n".join(out)


def _to_pct(raw: str) -> float | None:
    """Parse "145" / "128,18" / "133.5" → float percentage, else None."""
    if not raw:
        return None
    s = raw.strip().replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def parse_tttc_report(msg: dict) -> dict:
    """Parse một báo cáo TTTC (weekend). Các field metric đều nullable."""
    content = msg.get("content") or ""
    user = msg.get("user") or {}

    # Venue: restrict to first 3 non-empty lines to avoid body-text mentions
    header = _first_n_lines(content, 3)
    vm = _TTTC_VENUE_RE.search(header)
    venue = None
    if vm:
        venue = (vm.group(1) + " " + vm.group(2)).strip()

    rm = _TTTC_REVENUE_PCT_RE.search(content)
    revenue_pct = _to_pct(rm.group(1)) if rm else None

    hm = _TTTC_HOT_PCT_RE.search(content)
    hot_pct = _to_pct(hm.group(1)) if hm else None

    hrm = _TTTC_HOT_RATIO_RE.search(content)
    hot_ratio = _to_pct(hrm.group(1)) if hrm else None

    tb_bill = None
    tbm = _TTTC_TB_BILL_VALUE_RE.search(content)
    if tbm:
        tb_bill = _parse_vnd_amount(tbm.group(1), tbm.group(2))

    cm = _TTTC_CUSTOMER_RE.search(content)
    customer_count = int(cm.group(1)) if cm else None

    sections = _extract_sections(content)

    def get_section(*needles):
        for needle in needles:
            for key, val in sections.items():
                if needle in key:
                    return val
        return None

    return {
        "venue": venue,
        "revenue_pct":     revenue_pct,
        "hot_pct":         hot_pct,
        "hot_ratio":       hot_ratio,
        "tb_bill":         tb_bill,
        "customer_count":  customer_count,
        "tich_cuc":   get_section("tích cực"),
        "van_de":     get_section("vấn đề"),
        "da_lam":     get_section("đã làm"),
        "giai_phap":  get_section("giải pháp"),
        "sender":     user.get("displayName", "Unknown"),
        "sender_id":  user.get("id", ""),
        "sent_at":    msg.get("createdAt", ""),
        "message_id": msg.get("id", ""),
    }
```

- [ ] **Step 4: Run verifier — iterate regex until all PASS**

```bash
python scripts/verify_parse_tttc.py
```

Some templates will surface regex-tuning needs. **Adjust only the regex inside `parse_tttc_report`**, not the spec's expected matrix — the matrix is the contract. When a check fails, print the parsed dict (the verifier already does this above each template's checks) and tighten the relevant regex.

Expected final state: `OK: all checks passed`.

- [ ] **Step 5: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_parse_tttc.py
git commit -m "$(cat <<'EOF'
feat: thêm parse_tttc_report trích metric TTTC

Xuất venue + revenue_pct / hot_pct / hot_ratio / tb_bill /
customer_count + 4 section (tích cực / vấn đề / đã làm / giải pháp).
Tất cả field metric đều nullable — template TTTC viết rất đa dạng.
Verifier ràng buộc field matrix theo spec cho 7 template weekend.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `analyze_tttc_reports` + verifier

**Files:**
- Modify: `fpt_chat_stats.py` — add `analyze_tttc_reports` after `analyze_asm_reports` (around line 420).
- Create: `scripts/verify_analyze_tttc.py`

- [ ] **Step 1: Write the failing verifier**

Create `scripts/verify_analyze_tttc.py`:

```python
#!/usr/bin/env python3
"""Verify analyze_tttc_reports aggregates TTTC parser output correctly.

Run: python scripts/verify_analyze_tttc.py
"""
from __future__ import annotations
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from fpt_chat_stats import analyze_tttc_reports

FAIL = 0

def check(label: str, cond: bool) -> None:
    global FAIL
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAIL += 1
    print(f"  [{status}] {label}")

def mk(venue, revenue_pct=None, hot_pct=None, hot_ratio=None,
       tb_bill=None, customer_count=None, sender="ASM-X",
       tich_cuc=None, van_de=None, da_lam=None, giai_phap=None):
    return {
        "venue": venue, "revenue_pct": revenue_pct, "hot_pct": hot_pct,
        "hot_ratio": hot_ratio, "tb_bill": tb_bill,
        "customer_count": customer_count,
        "tich_cuc": tich_cuc, "van_de": van_de,
        "da_lam": da_lam, "giai_phap": giai_phap,
        "sender": sender, "sender_id": "uid",
        "sent_at": "2026-04-20T02:00:00Z", "message_id": "mid",
    }

# 1. Empty input
out = analyze_tttc_reports([])
check("empty: total_reports == 0", out["total_reports"] == 0)
check("empty: avg_tb_bill is None", out["avg_tb_bill"] is None)
check("empty: avg_revenue_pct is None", out["avg_revenue_pct"] is None)
check("empty: top_centers is []", out["top_centers"] == [])
check("empty: bottom_centers is []", out["bottom_centers"] == [])
check("empty: ideas is []", out["ideas"] == [])
check("empty: highlights structure", out["highlights"] == {"tich_cuc": [], "han_che": []})

# 2. Single report with all fields
single = [mk("TTTC A", revenue_pct=128.0, hot_pct=150.0, hot_ratio=60.0,
             tb_bill=2_200_000, customer_count=40,
             tich_cuc="tốt", van_de="chậm", da_lam="coaching")]
out = analyze_tttc_reports(single)
check("single: total_reports == 1", out["total_reports"] == 1)
check("single: avg_revenue_pct == 128.0", out["avg_revenue_pct"] == 128.0)
check("single: avg_tb_bill == 2_200_000", out["avg_tb_bill"] == 2_200_000)
check("single: top includes it", len(out["top_centers"]) == 1)
check("single: ideas has one", len(out["ideas"]) == 1)
check("single: highlights tich_cuc", len(out["highlights"]["tich_cuc"]) == 1)
check("single: highlights han_che (from van_de)", len(out["highlights"]["han_che"]) == 1)

# 3. Mixed nulls — avg computed only on non-null
mixed = [
    mk("A", revenue_pct=100.0, tb_bill=2_000_000),
    mk("B", revenue_pct=200.0, tb_bill=None),
    mk("C", revenue_pct=None,  tb_bill=1_000_000),
]
out = analyze_tttc_reports(mixed)
check("mixed: avg_revenue_pct over {100, 200} = 150",
      out["avg_revenue_pct"] == 150.0)
check("mixed: avg_tb_bill over {2_000_000, 1_000_000} = 1_500_000",
      out["avg_tb_bill"] == 1_500_000)

# 4. Top/bottom sorting with nulls-last
out = analyze_tttc_reports(mixed)
tops = [c["venue"] for c in out["top_centers"]]
check("top sorted desc by revenue_pct, nulls last",
      tops == ["B", "A", "C"])
bottoms = [c["venue"] for c in out["bottom_centers"]]
check("bottom sorted asc by revenue_pct, nulls last",
      bottoms == ["A", "B", "C"])

# 5. Top/bottom capped at 5
many = [mk(f"V{i}", revenue_pct=float(i)) for i in range(10)]
out = analyze_tttc_reports(many)
check("top capped at 5", len(out["top_centers"]) == 5)
check("bottom capped at 5", len(out["bottom_centers"]) == 5)
check("top = 9..5 desc",
      [c["venue"] for c in out["top_centers"]] == [f"V{i}" for i in [9, 8, 7, 6, 5]])

# 6. Ideas only for non-null da_lam
out = analyze_tttc_reports([
    mk("A", da_lam="x"),
    mk("B", da_lam=None),
])
check("ideas filter out null da_lam", len(out["ideas"]) == 1)
check("ideas entry shape", out["ideas"][0].keys() >= {"sender", "venue", "da_lam"})

print()
if FAIL:
    print(f"FAIL: {FAIL} check(s) failed")
    sys.exit(1)
print("OK: all checks passed")
```

- [ ] **Step 2: Run verifier — expect import error**

```bash
python scripts/verify_analyze_tttc.py
```
Expected: `ImportError: cannot import name 'analyze_tttc_reports'`.

- [ ] **Step 3: Implement `analyze_tttc_reports`**

Insert into `fpt_chat_stats.py` after `analyze_asm_reports`:

```python
def analyze_tttc_reports(parsed: list) -> dict:
    """Tổng hợp các TTTC report đã parse. Mọi tỉ số chỉ tính trên non-null."""
    def _mean(xs):
        xs = [x for x in xs if x is not None]
        if not xs:
            return None
        return sum(xs) / len(xs)

    avg_tb_bill = _mean([r["tb_bill"] for r in parsed])
    if avg_tb_bill is not None:
        avg_tb_bill = int(round(avg_tb_bill))

    avg_revenue_pct = _mean([r["revenue_pct"] for r in parsed])
    avg_hot_pct     = _mean([r["hot_pct"]     for r in parsed])
    avg_hot_ratio   = _mean([r["hot_ratio"]   for r in parsed])

    # Nulls-last stable sort: key returns (is_null, value)
    def _sort_top(r):
        v = r["revenue_pct"]
        return (v is None, -(v or 0))

    def _sort_bottom(r):
        v = r["revenue_pct"]
        return (v is None, (v or 0))

    top    = sorted(parsed, key=_sort_top)[:5]
    bottom = sorted(parsed, key=_sort_bottom)[:5]

    ideas = [
        {"sender": r["sender"], "venue": r["venue"], "da_lam": r["da_lam"]}
        for r in parsed
        if r.get("da_lam")
    ]
    tich_cuc = [
        {"sender": r["sender"], "venue": r["venue"], "content": r["tich_cuc"]}
        for r in parsed
        if r.get("tich_cuc")
    ]
    han_che = [
        {"sender": r["sender"], "venue": r["venue"], "content": r["van_de"]}
        for r in parsed
        if r.get("van_de")
    ]

    return {
        "total_reports":   len(parsed),
        "avg_tb_bill":     avg_tb_bill,
        "avg_revenue_pct": avg_revenue_pct,
        "avg_hot_pct":     avg_hot_pct,
        "avg_hot_ratio":   avg_hot_ratio,
        "top_centers":     top,
        "bottom_centers":  bottom,
        "ideas":           ideas,
        "highlights": {
            "tich_cuc": tich_cuc,
            "han_che":  han_che,
        },
    }
```

- [ ] **Step 4: Run verifier — expect all PASS**

```bash
python scripts/verify_analyze_tttc.py
```
Expected: `OK: all checks passed`.

- [ ] **Step 5: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_analyze_tttc.py
git commit -m "$(cat <<'EOF'
feat: thêm analyze_tttc_reports tổng hợp metric weekend

Tính avg_tb_bill / avg_revenue_pct / avg_hot_pct / avg_hot_ratio
chỉ trên non-null, top/bottom theo revenue_pct (nulls-last, cap 5),
ideas + highlights shape giống asm_data để dùng chung render helper.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Wire dispatch into `analyze_weekly`

**Files:**
- Modify: `fpt_chat_stats.py:586-649` (extend `analyze_weekly` return).
- Modify: `scripts/verify_analyze_weekly.py` (extend with new cases).

- [ ] **Step 1: Add new verifier cases to `scripts/verify_analyze_weekly.py`**

Append these checks to the existing file (read it first to see the existing test fixtures, then extend). Aim:

1. After existing checks pass, add two new scenarios at the bottom of the file (before the final `sys.exit`):

```python
# --- New: structured dispatch ---
# Use REPORT_BODY (already defined earlier in file) as a TTTC-ish report
# Create a second fixture with real Shop VT text so both branches fire

SHOP_VT_BODY = pathlib.Path("templates/weekend/7").read_text(encoding="utf-8")
TTTC_BODY    = pathlib.Path("templates/weekend/1").read_text(encoding="utf-8")

MIXED_MESSAGES = [
    msg("Nguyễn Văn A", "2026-04-20T02:00:00Z", SHOP_VT_BODY),
    msg("Trần Thị B",   "2026-04-20T03:00:00Z", TTTC_BODY),
]
out = analyze_weekly(MIXED_MESSAGES, GROUP_MEMBERS, "2026-04-20")
print("\n--- Mixed Shop VT + TTTC day ---")
check("reports has 2 entries",         len(out["reports"]) == 2)
check("asm_data present",              out.get("asm_data")  is not None)
check("tttc_data present",             out.get("tttc_data") is not None)
check("parsed_shop_vt has 1",          len(out.get("parsed_shop_vt", [])) == 1)
check("parsed_tttc has 1",             len(out.get("parsed_tttc", [])) == 1)
check("asm_data.total_deposits > 0",
      out["asm_data"]["total_deposits"] > 0)
check("tttc_data.total_reports == 1",
      out["tttc_data"]["total_reports"] == 1)

# Shop-VT-only day
out = analyze_weekly(
    [msg("Nguyễn Văn A", "2026-04-20T02:00:00Z", SHOP_VT_BODY)],
    GROUP_MEMBERS, "2026-04-20",
)
print("\n--- Shop VT only ---")
check("asm_data present",   out.get("asm_data")  is not None)
check("tttc_data is None",  out.get("tttc_data") is None)

# TTTC-only day
out = analyze_weekly(
    [msg("Nguyễn Văn A", "2026-04-20T02:00:00Z", TTTC_BODY)],
    GROUP_MEMBERS, "2026-04-20",
)
print("\n--- TTTC only ---")
check("asm_data is None",   out.get("asm_data")  is None)
check("tttc_data present",  out.get("tttc_data") is not None)

# Zero-reports day
out = analyze_weekly([], GROUP_MEMBERS, "2026-04-20")
print("\n--- Zero reports ---")
check("asm_data is None",   out.get("asm_data")  is None)
check("tttc_data is None",  out.get("tttc_data") is None)
check("parsed_shop_vt is []", out.get("parsed_shop_vt", None) == [])
check("parsed_tttc    is []", out.get("parsed_tttc",    None) == [])
```

- [ ] **Step 2: Run verifier — expect failures on new cases**

```bash
python scripts/verify_analyze_weekly.py
```
Expected: existing checks still pass, new "asm_data present" / "tttc_data present" / "parsed_*" checks FAIL.

- [ ] **Step 3: Extend `analyze_weekly`**

Modify `fpt_chat_stats.py:586-649`. Within the sender loop, also parse each qualifying message via `classify_report` dispatch, accumulating into two lists. After the existing compliance computation, call the analyzers and extend the return dict. Here is the new tail of the function — insert just before `return {…}`:

```python
    # --- Structured dispatch: parse each qualifying message by kind ---
    parsed_shop_vt: list[dict] = []
    parsed_tttc:    list[dict] = []
    for sender, items in by_sender.items():
        for dt, _vn_dt, content in items:
            # Reconstruct a minimal msg dict (parser only reads content + user + createdAt + id).
            # Use the per-message dt so each fake_msg gets a unique id.
            fake_msg = {
                "content":   content,
                "user":      {"displayName": sender, "id": ""},
                "createdAt": dt.isoformat(),
                "id":        f"{sender}-{dt.timestamp()}",
                "type":      "TEXT",
            }
            kind = classify_report(content)
            if kind == "shop_vt":
                parsed_shop_vt.append(parse_asm_report(fake_msg))
            elif kind == "tttc":
                parsed_tttc.append(parse_tttc_report(fake_msg))
            # unknown → dropped from structured pipelines, still in reports[]

    asm_data  = analyze_asm_reports(parsed_shop_vt) if parsed_shop_vt else None
    tttc_data = analyze_tttc_reports(parsed_tttc)   if parsed_tttc    else None
```

Then replace the existing `return {...}` with:

```python
    return {
        "target_date":       target_date_vn,
        "deadline":          deadline,
        "reports":           reports,
        "late_list":         late_list,
        "missing_list":      missing_list,
        "asm_data":          asm_data,
        "tttc_data":         tttc_data,
        "parsed_shop_vt":    parsed_shop_vt,
        "parsed_tttc":       parsed_tttc,
    }
```

**Note:** the `fake_msg` reconstruction is because `parse_asm_report` and `parse_tttc_report` take a message dict, but `analyze_weekly` has already decomposed messages into `(dt, vn_dt, content)` tuples. Do not change the parsers' signatures — reuse them as-is.

- [ ] **Step 4: Run verifier — expect all PASS**

```bash
python scripts/verify_analyze_weekly.py
```
Expected: all existing + new cases PASS.

- [ ] **Step 5: Run full verifier suite as regression check**

```bash
python scripts/verify_vnd_parsing.py
python scripts/verify_extract_sections.py
python scripts/verify_classify_report.py
python scripts/verify_parse_tttc.py
python scripts/verify_analyze_tttc.py
python scripts/verify_analyze_weekly.py
python scripts/verify_weekly_classifier.py
python scripts/verify_weekly_excel.py
```
Expected: all 8 exit 0.

- [ ] **Step 6: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_analyze_weekly.py
git commit -m "$(cat <<'EOF'
feat: analyze_weekly dispatch qua classify_report

Mỗi message đạt ngưỡng được classify → shop_vt ⇒ parse_asm_report,
tttc ⇒ parse_tttc_report, unknown ⇒ chỉ nằm trong reports[]. Trả về
thêm asm_data / tttc_data / parsed_shop_vt / parsed_tttc (None/[] khi
trống). Parser signature không đổi.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Extend `print_weekly_report` with structured blocks

**Files:**
- Modify: `fpt_chat_stats.py:730-768` (`print_weekly_report`).

**No new verifier** — print function has no assertions worth writing, and all data it reads is already verified by Tasks 5 and 6. Smoke-test by running the CLI manually at the end.

- [ ] **Step 1: Add Shop VT + TTTC blocks**

Modify `print_weekly_report` in `fpt_chat_stats.py`. Insert new blocks between the "Muộn" section and the "Nội dung báo cáo" section:

```python
    asm_data  = data.get("asm_data")
    tttc_data = data.get("tttc_data")

    if asm_data:
        print(f"--- Shop VT: tổng cọc {asm_data['total_deposits']}, "
              f"tổng ra tiêm {asm_data['total_ra_tiem']} ---")
        low  = asm_data.get("low_deposit_shops", [])
        high = asm_data.get("high_deposit_shops", [])
        if low:
            print(f"  Shop cọc thấp ({len(low)}):")
            for s in low:
                print(f"    - {s['shop_ref']} — {s['deposit_count']} cọc ({s['sender']})")
        if high:
            print(f"  Shop cọc tốt ({len(high)}):")
            for s in high:
                print(f"    - {s['shop_ref']} — {s['deposit_count']} cọc ({s['sender']})")
        print()

    if tttc_data:
        def _fmt_pct(v): return f"{v:.1f}%" if v is not None else "—"
        def _fmt_vnd(v): return f"{v:,} đ" if v is not None else "—"
        print(f"--- TTTC: {tttc_data['total_reports']} trung tâm ---")
        print(f"  TB bill TB : {_fmt_vnd(tttc_data['avg_tb_bill'])}")
        print(f"  %HT TB     : {_fmt_pct(tttc_data['avg_revenue_pct'])}")
        print(f"  %HOT TB    : {_fmt_pct(tttc_data['avg_hot_pct'])}")
        print(f"  %tr HOT TB : {_fmt_pct(tttc_data['avg_hot_ratio'])}")
        if tttc_data["top_centers"]:
            print(f"  Top trung tâm theo %HT:")
            for c in tttc_data["top_centers"]:
                print(f"    - {c['venue']} — %HT {_fmt_pct(c['revenue_pct'])} "
                      f"({c['sender']})")
        if tttc_data["bottom_centers"]:
            print(f"  Trung tâm cần chú ý:")
            for c in tttc_data["bottom_centers"]:
                print(f"    - {c['venue']} — %HT {_fmt_pct(c['revenue_pct'])} "
                      f"({c['sender']})")
        print()
```

- [ ] **Step 2: Smoke-test with a mixed fixture**

Create a quick one-off invocation:

```bash
python -c "
import pathlib, sys
sys.path.insert(0, '.')
from fpt_chat_stats import analyze_weekly, print_weekly_report
msg = lambda s,t,c: {'id':s,'type':'TEXT','content':c,'createdAt':t,'user':{'id':s,'displayName':s}}
msgs = [
  msg('ASM-A', '2026-04-20T02:00:00Z', pathlib.Path('templates/weekend/7').read_text(encoding='utf-8')),
  msg('ASM-B', '2026-04-20T03:00:00Z', pathlib.Path('templates/weekend/1').read_text(encoding='utf-8')),
]
members = [{'displayName': 'ASM-A'}, {'displayName': 'ASM-B'}, {'displayName': 'ASM-C'}]
data = analyze_weekly(msgs, members, '2026-04-20')
print_weekly_report(data)
"
```
Expected: both `--- Shop VT ---` and `--- TTTC ---` sections print; ASM-C appears under Chưa báo cáo.

- [ ] **Step 3: Re-run all verifiers**

```bash
python scripts/verify_analyze_weekly.py
python scripts/verify_weekly_classifier.py
python scripts/verify_weekly_excel.py
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add fpt_chat_stats.py
git commit -m "$(cat <<'EOF'
feat: print_weekly_report in block Shop VT + TTTC

Giữa phần "Muộn" và "Nội dung báo cáo" giờ có thêm block tóm tắt
cọc (Shop VT) và TB bill / %HT / top / bottom (TTTC). Skip gọn khi
không có dữ liệu tương ứng.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Extend `write_weekly_excel` with Shop VT + TTTC sheets

**Files:**
- Modify: `fpt_chat_stats.py:886-950` (`write_weekly_excel`).
- Modify: `scripts/verify_weekly_excel.py` — add assertions for new sheets.

- [ ] **Step 1: Extend verifier first**

Read `scripts/verify_weekly_excel.py` to see existing structure, then append new checks. Keep existing fixture; add one that covers both Shop VT and TTTC:

```python
# --- New: structured sheets ---
SHOP_VT_BODY = pathlib.Path("templates/weekend/7").read_text(encoding="utf-8")
TTTC_BODY    = pathlib.Path("templates/weekend/1").read_text(encoding="utf-8")
MIXED_MSGS = [
    msg("ASM-A", "2026-04-20T02:00:00Z", SHOP_VT_BODY),
    msg("ASM-B", "2026-04-20T03:00:00Z", TTTC_BODY),
]
mixed_data = analyze_weekly(MIXED_MSGS,
                            [{"displayName": "ASM-A"}, {"displayName": "ASM-B"}],
                            "2026-04-20")
import io
buf = io.BytesIO()
write_weekly_excel(mixed_data,
                   [{"displayName": "ASM-A"}, {"displayName": "ASM-B"}],
                   buf)
buf.seek(0)
from openpyxl import load_workbook
wb = load_workbook(buf)
check("Shop VT sheet exists",  "Shop VT" in wb.sheetnames)
check("TTTC sheet exists",     "TTTC"    in wb.sheetnames)
ws_sv = wb["Shop VT"]
ws_tt = wb["TTTC"]
shop_headers = [c.value for c in ws_sv[1]]
check("Shop VT header Shop",    "Shop"    in shop_headers)
check("Shop VT header Số cọc",  "Số cọc"  in shop_headers)
tt_headers = [c.value for c in ws_tt[1]]
check("TTTC header Trung tâm",   "Trung tâm"   in tt_headers)
check("TTTC header %HT ngày",    "%HT ngày"    in tt_headers)
check("TTTC header TB bill",     "TB bill"     in tt_headers)
# Row content
check("Shop VT has at least one data row",  ws_sv.max_row >= 2)
check("TTTC has at least one data row",     ws_tt.max_row >= 2)

# Edge case: zero reports — sheets still exist but empty
empty_data = analyze_weekly([],
                            [{"displayName": "ASM-A"}],
                            "2026-04-20")
buf2 = io.BytesIO()
write_weekly_excel(empty_data, [{"displayName": "ASM-A"}], buf2)
buf2.seek(0)
wb2 = load_workbook(buf2)
check("zero-day: Shop VT sheet present", "Shop VT" in wb2.sheetnames)
check("zero-day: TTTC sheet present",    "TTTC"    in wb2.sheetnames)
```

- [ ] **Step 2: Run verifier — expect new-sheet checks to FAIL**

```bash
python scripts/verify_weekly_excel.py
```
Expected: existing checks pass, new checks FAIL.

- [ ] **Step 3: Implement the two new sheets**

Modify `write_weekly_excel` in `fpt_chat_stats.py:886`. After the existing "Sheet 2: Nội dung" block (and its column-wrap loop), add:

```python
    # Sheet 3: Shop VT
    ws3 = wb.create_sheet("Shop VT")
    ws3.append(["Shop", "Số cọc", "Ra tiêm", "Mức", "ASM"])
    for cell in ws3[1]:
        cell.font = Font(bold=True)
    asm_data = data.get("asm_data") or {}
    _rt_map = {r["shop_ref"]: r.get("ra_tiem_count")
               for r in data.get("parsed_shop_vt", []) if r.get("shop_ref")}
    for s in sorted(asm_data.get("all_shops", []),
                    key=lambda x: x["deposit_count"], reverse=True):
        ra = _rt_map.get(s["shop_ref"])
        ws3.append([s["shop_ref"], s["deposit_count"],
                    "" if ra is None else ra, s["level"], s["sender"]])
    ws3.column_dimensions["A"].width = 50
    ws3.column_dimensions["B"].width = 12
    ws3.column_dimensions["C"].width = 12
    ws3.column_dimensions["D"].width = 14
    ws3.column_dimensions["E"].width = 28

    # Sheet 4: TTTC
    ws4 = wb.create_sheet("TTTC")
    ws4.append(["Trung tâm", "%HT ngày", "%HOT", "TB bill",
                "Tỉ trọng HOT", "Lượt KH mua", "ASM"])
    for cell in ws4[1]:
        cell.font = Font(bold=True)
    for r in data.get("parsed_tttc", []):
        ws4.append([
            r.get("venue") or "",
            r.get("revenue_pct")    if r.get("revenue_pct")    is not None else "",
            r.get("hot_pct")        if r.get("hot_pct")        is not None else "",
            r.get("tb_bill")        if r.get("tb_bill")        is not None else "",
            r.get("hot_ratio")      if r.get("hot_ratio")      is not None else "",
            r.get("customer_count") if r.get("customer_count") is not None else "",
            r.get("sender") or "",
        ])
    ws4.column_dimensions["A"].width = 40
    for col in ("B", "C", "D", "E", "F"):
        ws4.column_dimensions[col].width = 14
    ws4.column_dimensions["G"].width = 28
```

- [ ] **Step 4: Run verifier — expect all PASS**

```bash
python scripts/verify_weekly_excel.py
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add fpt_chat_stats.py scripts/verify_weekly_excel.py
git commit -m "$(cat <<'EOF'
feat: write_weekly_excel thêm 2 sheet Shop VT + TTTC

Shop VT tận dụng asm_data.all_shops (+ ra_tiem từ parsed_shop_vt),
TTTC in từng trung tâm với 6 cột metric + ASM. Sheet vẫn tạo ngay cả
khi rỗng (chỉ có header) để file Excel có cấu trúc ổn định.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Extract `_render_shop_vt_sections` helper in `app.py`

**Files:**
- Modify: `app.py:338-547` (slice out daily-page sections into a helper; daily page calls helper; identical behavior).

**Purpose:** prepare for Task 10 by making the Shop VT render reusable. No visible behavior change.

- [ ] **Step 1: Add helper function**

In `app.py`, insert this function **above** `_render_result`:

```python
def _render_shop_vt_sections(asm_data: dict, d1_shop_map: dict | None = None) -> None:
    """Render the shop-deposit chart + shop-bucket tables + ideas + highlights.

    Shared by daily (_render_result) and weekly (_render_weekly_result).
    d1_shop_map is daily-only (D-1 delta comparison); None for weekly.
    """
    import pandas as pd  # local import keeps helper self-contained

    # Chart: cọc theo shop
    all_shops_raw = sorted(asm_data.get("all_shops", []),
                           key=lambda x: x["deposit_count"], reverse=True)
    if all_shops_raw:
        labels = [s["shop_ref"][:28] for s in all_shops_raw]
        chart_dict = {"Hôm nay": [s["deposit_count"] for s in all_shops_raw]}
        if d1_shop_map is not None:
            chart_dict["D-1"] = [d1_shop_map.get(s["shop_ref"], 0) for s in all_shops_raw]
        st.bar_chart(pd.DataFrame(chart_dict, index=labels), use_container_width=True)

    no_dep = asm_data.get("no_deposit_shops", [])
    if no_dep:
        st.subheader("🚫 Shop báo cáo 0 cọc")
        st.dataframe(
            [{"ASM": s["sender"], "Shop": s["shop_ref"]} for s in no_dep],
            use_container_width=True, hide_index=True,
        )

    low_shops = asm_data.get("low_deposit_shops", [])
    if low_shops:
        st.subheader("📉 Shop cọc thấp")
        def _low_row(s):
            d1 = d1_shop_map.get(s["shop_ref"], "—") if d1_shop_map is not None else None
            row = {"ASM": s["sender"], "Shop": s["shop_ref"], "Số cọc": s["deposit_count"]}
            if d1 is not None:
                row["Cọc D-1"] = d1
            return row
        st.dataframe(
            [_low_row(s) for s in sorted(low_shops, key=lambda x: x["deposit_count"])],
            use_container_width=True, hide_index=True,
        )

    high_shops = asm_data.get("high_deposit_shops", [])
    if high_shops:
        st.subheader("🏆 Nhân viên phát sinh cọc tốt")
        def _high_row(s):
            d1 = d1_shop_map.get(s["shop_ref"], "—") if d1_shop_map is not None else None
            row = {"ASM": s["sender"], "Shop": s["shop_ref"], "Số cọc": s["deposit_count"]}
            if d1 is not None:
                row["Cọc D-1"] = d1
            return row
        st.dataframe(
            [_high_row(s) for s in sorted(high_shops, key=lambda x: x["deposit_count"], reverse=True)],
            use_container_width=True, hide_index=True,
        )

    st.subheader("🏪 Shop đặt cọc")
    all_shops = sorted(asm_data.get("all_shops", []),
                       key=lambda x: x["deposit_count"], reverse=True)
    if all_shops:
        def _shop_row(s):
            d1 = d1_shop_map.get(s["shop_ref"], "—") if d1_shop_map is not None else None
            row = {"Shop": s["shop_ref"], "Số cọc": s["deposit_count"]}
            if d1 is not None:
                row["Cọc D-1"] = d1
            row["Mức"] = s["level"]
            row["ASM"] = s["sender"]
            return row
        st.dataframe(
            [_shop_row(s) for s in all_shops],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("(không có)")

    st.subheader("💡 Ý tưởng triển khai từ ASM")
    ideas = asm_data.get("ideas", [])
    if ideas:
        st.table(
            [{"ASM": i["sender"], "Shop": i["shop_ref"], "Nội dung": i["da_lam"]}
             for i in ideas]
        )
    else:
        st.caption("(không có)")

    st.subheader("⭐ Điểm nổi bật")
    tich_cuc = asm_data["highlights"]["tich_cuc"]
    han_che  = asm_data["highlights"]["han_che"]
    highlights = (
        [{"ASM": h["sender"], "Shop": h["shop_ref"], "Loại": "Tích cực", "Nội dung": h["content"]}
         for h in tich_cuc]
        + [{"ASM": h["sender"], "Shop": h["shop_ref"], "Loại": "Hạn chế", "Nội dung": h["content"]}
           for h in han_che]
    )
    if highlights:
        st.table(highlights)
    else:
        st.caption("(không có)")
```

- [ ] **Step 2: Replace the duplicate block inside `_render_result`**

In `_render_result` (`app.py:338`), find the block that starts at `# ── Chart: cọc theo shop ──` (around line 445) and runs through the end of the `⭐ Điểm nổi bật` section (ending around line 547). Replace that entire span with a single call:

```python
    _render_shop_vt_sections(asm_data, d1_shop_map=d1_shop_map)
```

Keep everything *after* the `⭐ Điểm nổi bật` block (specifically the `⚠️ ASM chưa báo cáo (sau deadline)` / `🔍 Xem chi tiết` sections at lines 549+).

- [ ] **Step 3: Manual smoke test**

```bash
streamlit run app.py
```
Run a "Hôm nay" report for a group you know. Verify the daily page looks visually identical to before the refactor (same sections, same order, same data).

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "$(cat <<'EOF'
refactor(ui): tách _render_shop_vt_sections để weekly dùng chung

Daily page giữ nguyên hành vi, chỉ gọi helper mới. Tách ra chuẩn bị
cho Task 10 (weekly UI gọi cùng helper này để hiển thị block Shop VT).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Add `_render_tttc_sections` and wire into `_render_weekly_result`

**Files:**
- Modify: `app.py` — add `_render_tttc_sections` next to `_render_shop_vt_sections`, update `_render_weekly_result`.

- [ ] **Step 1: Add `_render_tttc_sections` helper**

Insert below `_render_shop_vt_sections`:

```python
def _render_tttc_sections(tttc_data: dict) -> None:
    """Render TTTC aggregate metrics + top/bottom tables + ideas + highlights."""

    def _fmt_pct(v): return f"{v:.1f}%" if v is not None else "—"
    def _fmt_vnd(v): return f"{v:,}" if v is not None else "—"

    st.subheader("🏥 TTTC — chỉ số trung tâm")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trung tâm báo cáo", tttc_data["total_reports"])
    c2.metric("TB bill TB",        _fmt_vnd(tttc_data["avg_tb_bill"]))
    c3.metric("%HT TB",            _fmt_pct(tttc_data["avg_revenue_pct"]))
    c4.metric("%HOT TB",           _fmt_pct(tttc_data["avg_hot_pct"]))

    def _center_row(c: dict) -> dict:
        return {
            "Trung tâm":     c.get("venue") or "—",
            "%HT":           _fmt_pct(c.get("revenue_pct")),
            "%HOT":          _fmt_pct(c.get("hot_pct")),
            "TB bill":       _fmt_vnd(c.get("tb_bill")),
            "Tỉ trọng HOT":  _fmt_pct(c.get("hot_ratio")),
            "Lượt KH mua":   c.get("customer_count") if c.get("customer_count") is not None else "—",
            "ASM":           c.get("sender") or "—",
        }

    top = tttc_data.get("top_centers", [])
    if top:
        st.subheader("🏆 Top trung tâm (theo %HT)")
        st.dataframe([_center_row(c) for c in top],
                     use_container_width=True, hide_index=True)

    bottom = tttc_data.get("bottom_centers", [])
    if bottom:
        st.subheader("⚠️ Trung tâm cần chú ý")
        st.dataframe([_center_row(c) for c in bottom],
                     use_container_width=True, hide_index=True)

    ideas = tttc_data.get("ideas", [])
    if ideas:
        st.subheader("💡 Ý tưởng từ TTTC")
        st.table([{"ASM": i["sender"], "Trung tâm": i["venue"], "Nội dung": i["da_lam"]}
                  for i in ideas])

    hl = tttc_data.get("highlights", {})
    tich_cuc = hl.get("tich_cuc", [])
    han_che  = hl.get("han_che",  [])
    if tich_cuc or han_che:
        st.subheader("⭐ Điểm nổi bật (TTTC)")
        rows = (
            [{"ASM": h["sender"], "Trung tâm": h["venue"],
              "Loại": "Tích cực", "Nội dung": h["content"]} for h in tich_cuc]
            + [{"ASM": h["sender"], "Trung tâm": h["venue"],
                "Loại": "Hạn chế", "Nội dung": h["content"]} for h in han_che]
        )
        st.table(rows)
```

- [ ] **Step 2: Wire into `_render_weekly_result`**

Locate `_render_weekly_result` (around `app.py:603`). Insert the two conditional blocks **after the Action panels (Chưa báo cáo / Muộn side-by-side)** and **before the Nội dung báo cáo section** (the one with search + tabs + expanders + avatars):

```python
    asm_data_w  = wd.get("asm_data")
    tttc_data_w = wd.get("tttc_data")

    if asm_data_w:
        st.markdown("### 🏪 Shop VT")
        _render_shop_vt_sections(asm_data_w, d1_shop_map=None)

    if tttc_data_w:
        _render_tttc_sections(tttc_data_w)
```

If neither is present, neither block renders and the existing raw-text UI is unchanged.

- [ ] **Step 3: Manual smoke test (multiple scenarios)**

```bash
streamlit run app.py
```
Test each:
1. Daily mode ("Hôm nay") — verify daily page visually identical (Task 9 regression).
2. Weekly mode on a weekday with Shop VT reports — verify Shop VT block renders after the action panels, TTTC block absent.
3. Weekly mode on a weekend day with TTTC reports — verify TTTC block renders (4 metric cards + top/bottom tables), Shop VT block absent.
4. Weekly mode on a day mixing both — verify both blocks render independently.
5. Weekly mode on zero-reports day — verify neither structured block renders; action panels + "Không có báo cáo khớp" state for tabs still works.
6. Typing in the search box — verify search + tabs + expanders still filter (nothing broken).

If you can't access live data, craft a fake `_weekly_results` payload in `st.session_state` and re-run the renderer path — matches how Task 6's verifier constructs fixtures.

- [ ] **Step 4: Run all verifiers one last time**

```bash
python scripts/verify_vnd_parsing.py
python scripts/verify_extract_sections.py
python scripts/verify_classify_report.py
python scripts/verify_parse_tttc.py
python scripts/verify_analyze_tttc.py
python scripts/verify_analyze_weekly.py
python scripts/verify_weekly_classifier.py
python scripts/verify_weekly_excel.py
```
Expected: all 8 exit 0.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "$(cat <<'EOF'
feat(ui): weekly UI render block Shop VT + TTTC độc lập

Sau panel Chưa báo cáo/Muộn, tự động render Shop VT nếu có asm_data
(dùng chung helper với daily), TTTC nếu có tttc_data (4 metric +
top/bottom + ý tưởng + điểm nổi bật). Tabs Nội dung + avatar vẫn giữ
nguyên phía dưới làm fallback cho message "unknown" kind.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: Manual integration test (live API)

**Files:** none modified.

**Purpose:** End-to-end confirmation against real data. No verifier can substitute for this — the TTTC regex was tuned against 7 templates, and real group messages may surface edge cases.

- [ ] **Step 1: Save a live snapshot**

With valid FPT token + group configured:

```bash
python fpt_chat_stats.py --weekly 2026-04-19 --save raw_weekly.json
```

- [ ] **Step 2: Replay from snapshot**

```bash
python fpt_chat_stats.py --load raw_weekly.json --weekly 2026-04-19
```
Expected: terminal output now includes `--- Shop VT ---` and/or `--- TTTC ---` blocks depending on what the group reported. Confirm numbers look right against the raw messages in `raw_weekly.json`.

- [ ] **Step 3: Generate Excel from snapshot**

```bash
python fpt_chat_stats.py --load raw_weekly.json --weekly 2026-04-19 --excel weekly_real.xlsx
```
Open `weekly_real.xlsx` and confirm `Shop VT` + `TTTC` sheets are populated (or empty with headers on a no-reports day).

- [ ] **Step 4: Streamlit end-to-end**

```bash
streamlit run app.py
```
Select Báo cáo tuần → pick 2026-04-19 → Run. Confirm Shop VT + TTTC blocks render with real data; avatars still work; Excel download button still returns a file with the new sheets.

- [ ] **Step 5: If any regex miss**

If a real TTTC report has a metric the parser didn't catch (e.g. an unusual TB bill format), update the relevant regex in `parse_tttc_report` and add a test case to `scripts/verify_parse_tttc.py` with a snippet of that real message content (anonymized if needed). Re-run the full verifier suite. Then commit as a bugfix.

- [ ] **Step 6: Mark the feature done**

No commit required unless regex adjustments were needed. The plan is complete.

---

## Rollback strategy

Each task lands as a single commit. To revert any single task, `git revert <sha>` on that commit. Because every structured-metrics field is additive (nullable, new sheets, new blocks conditional on non-null data), reverting Task 10 alone takes the UI back to the compliance-only view while keeping the CLI/Excel improvements; reverting Tasks 6–10 takes the whole feature back to pre-change state with Tasks 1–5 harmlessly living as unused helpers.

## Files NOT touched

- `fpt_chat_stats.py` daily pipeline (`parse_asm_report`, `analyze_asm_reports`, `detect_asm_reports`, `print_asm_report`, `write_asm_excel`) — only called, never modified.
- CLI `--today` / `--from` / `--to` / `--weekly` flag wiring — unchanged; weekly dispatch still flows through `analyze_weekly`.
- `fetch_all_messages` and auth — unchanged.
- `openspec/` — no proposal needed; this is an additive enhancement on an already-shipped feature that kept its existing spec contract (the existing spec is a superset of the new behaviour once `asm_data` / `tttc_data` are added as optional keys). If that turns out to be wrong during review, follow `openspec/AGENTS.md` to create a change proposal *after* implementation, but do not block Tasks 1–10 on it.
