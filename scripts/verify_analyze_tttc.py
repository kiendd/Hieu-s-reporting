#!/usr/bin/env python3
"""Verify analyze_tttc_reports aggregates TTTC parser output correctly.

Run from repo root: python scripts/verify_analyze_tttc.py
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
