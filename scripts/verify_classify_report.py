#!/usr/bin/env python3
"""Verify classify_report buckets messages into shop_vt / tttc / unknown.

Run from repo root: python scripts/verify_classify_report.py
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
    "Tư vấn đơn cọc 10đ thành công hôm nay",  # multi-digit đ-currency must not match
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
