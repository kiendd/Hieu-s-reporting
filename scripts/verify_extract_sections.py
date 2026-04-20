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
