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

# Expected scores per sample: 8 = narrative (5), else 6
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
