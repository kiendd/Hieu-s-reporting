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
