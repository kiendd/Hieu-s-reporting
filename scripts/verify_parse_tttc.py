#!/usr/bin/env python3
"""Verify parse_tttc_report extracts the expected field matrix per template.

Run from repo root: python scripts/verify_parse_tttc.py
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

# (template_id, {field: non-null? bool})
# True = expect non-None, False = expect None
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
