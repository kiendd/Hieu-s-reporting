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

# Fixture: a qualifying report body (should score 6)
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
    msg("Lê C",         "2026-04-20T10:00:00Z", "Ok anh"),             # below threshold
    msg("Phạm D",       "2026-04-20T03:00:00Z", REPORT_BODY, "FILE"),  # not TEXT
    # Hoàng E sends nothing
]

result = analyze_weekly(MESSAGES, GROUP_MEMBERS, "2026-04-20", deadline="20:00")

check("target_date == '2026-04-20'", result["target_date"] == "2026-04-20")
check("deadline == '20:00'", result["deadline"] == "20:00")
check("len(reports) == 2", len(result["reports"]) == 2)
check("late_list == ['Trần Thị B']", result["late_list"] == ["Trần Thị B"])
check(
    "missing_list == sorted(['Hoàng E','Lê C','Phạm D'])",
    result["missing_list"] == sorted(["Hoàng E", "Lê C", "Phạm D"]),
)
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
    msg("Nguyễn Văn A", "2026-04-20T01:00:00Z", REPORT_BODY + "\nfirst"),
    msg("Nguyễn Văn A", "2026-04-20T03:30:00Z", REPORT_BODY + "\nsecond"),
    msg("Nguyễn Văn A", "2026-04-20T07:00:00Z", REPORT_BODY + "\nthird"),
]
r2 = analyze_weekly(MESSAGES_2, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Multi-message: 1 entry", len(r2["reports"]) == 1)
check("Multi-message: earliest by UTC wins", r2["reports"][0]["text"].endswith("first"))
check("Multi-message: extra_count == 2", r2["reports"][0]["extra_count"] == 2)

# Midnight boundary
MESSAGES_MID = [
    msg("Nguyễn Văn A", "2026-04-20T16:59:30Z", REPORT_BODY),  # VN 23:59:30, same day
    msg("Nguyễn Văn A", "2026-04-20T17:00:15Z", REPORT_BODY),  # VN 00:00:15 next day
]
r3 = analyze_weekly(MESSAGES_MID, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Midnight: only first message counted", r3["reports"][0]["extra_count"] == 0)

# Non-member
MESSAGES_NONMEMBER = [msg("Stranger", "2026-04-20T02:00:00Z", REPORT_BODY)]
r4 = analyze_weekly(MESSAGES_NONMEMBER, GROUP_MEMBERS, "2026-04-20", deadline="20:00")
check("Non-member: not in reports", not any(r["sender"] == "Stranger" for r in r4["reports"]))
check("Non-member: not in missing_list", "Stranger" not in r4["missing_list"])
check(
    "Non-member: all group_members in missing_list",
    set(r4["missing_list"]) == {m["displayName"] for m in GROUP_MEMBERS},
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
MESSAGES_ATTACH = [msg("Nguyễn Văn A", "2026-04-20T02:00:00Z", "   \n\t  ")]
r7 = analyze_weekly(MESSAGES_ATTACH, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Attachment-only / empty body: not in reports", r7["reports"] == [])
check("Attachment-only / empty body: sender in missing_list", r7["missing_list"] == ["Nguyễn Văn A"])

# Qualifying among non-qualifying: below-threshold messages must NOT inflate extra_count
MESSAGES_MIX = [
    msg("Nguyễn Văn A", "2026-04-20T01:00:00Z", "Ok anh"),                       # VN 08:00, score 0
    msg("Nguyễn Văn A", "2026-04-20T03:00:00Z", "a" * 400),                      # VN 10:00, score 1
    msg("Nguyễn Văn A", "2026-04-20T07:00:00Z", REPORT_BODY),                    # VN 14:00, score 6
]
r_mix = analyze_weekly(MESSAGES_MIX, [{"displayName": "Nguyễn Văn A"}], "2026-04-20", deadline="20:00")
check("Mix: 1 qualifying entry", len(r_mix["reports"]) == 1)
check("Mix: sent_at_vn == '14:00' (only qualifying kept)", r_mix["reports"][0]["sent_at_vn"] == "14:00")
check("Mix: text is REPORT_BODY (not 'Ok anh' or 400-char spam)", r_mix["reports"][0]["text"] == REPORT_BODY)
check("Mix: extra_count == 0 (below-threshold filtered BEFORE counting)", r_mix["reports"][0]["extra_count"] == 0)

# --- print_weekly_report smoke ---
import io, contextlib
from fpt_chat_stats import print_weekly_report

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    print_weekly_report(result)
out = buf.getvalue()

check("header has 'BÁO CÁO TUẦN'", "BÁO CÁO TUẦN" in out)
check("header has target_date", "2026-04-20" in out)
check("header has 'Đã báo cáo: 2'", "Đã báo cáo: 2" in out)
check("header has 'Muộn: 1'", "Muộn: 1" in out)
check("header has 'Chưa báo cáo: 3'", "Chưa báo cáo: 3" in out)
check("missing section lists Hoàng E", "Hoàng E" in out)
check("late marker 'MUỘN' and 'Trần Thị B' both appear", "MUỘN" in out and "Trần Thị B" in out)
check("content section includes report body substring", "Doanh thu 133% HT" in out)

# --- New: structured dispatch ---
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

print(f"\n{FAIL} failure(s)" if FAIL else "\nAll checks passed.")
sys.exit(1 if FAIL else 0)
