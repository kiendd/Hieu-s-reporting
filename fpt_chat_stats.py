#!/usr/bin/env python3
"""
FPT Chat ASM Report Tool
Phân tích báo cáo hàng ngày của ASM từ lịch sử chat FPT Chat.

Usage:
    python fpt_chat_stats.py --today
    python fpt_chat_stats.py --today --excel bao_cao.xlsx
    python fpt_chat_stats.py --from 2026-04-01 --to 2026-04-16
    python fpt_chat_stats.py --save raw.json
    python fpt_chat_stats.py --load raw.json --today
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date as _date, datetime, timedelta, time, timezone

try:
    import requests
except ImportError:
    print("Thiếu thư viện 'requests'. Chạy: pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> dict:
    """Đọc config JSON. Trả về {} nếu file không tồn tại."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: config file '{path}' không hợp lệ: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_group_id(value: str) -> str:
    """Trích group ID từ URL hoặc trả về nguyên nếu đã là ID."""
    match = re.search(r'([a-f0-9]{24})', value)
    return match.group(1) if match else value


def parse_dt(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None


def parse_date_arg(value: str, end_of_day: bool = False) -> datetime:
    """Chuyển 'YYYY-MM-DD' thành datetime UTC có timezone."""
    try:
        d = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: định dạng ngày không hợp lệ '{value}'. Dùng YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)
    t = time(23, 59, 59) if end_of_day else time(0, 0, 0)
    return datetime.combine(d, t, tzinfo=timezone.utc)


def to_vn_str(iso: str) -> str:
    """Chuyển ISO datetime thành chuỗi giờ VN (UTC+7)."""
    dt = parse_dt(iso)
    if not dt:
        return iso
    vn = datetime.fromtimestamp(dt.timestamp() + 7 * 3600, tz=timezone.utc)
    return vn.strftime("%Y-%m-%d %H:%M:%S")


def fmt_date_range(date_from: datetime | None, date_to: datetime | None) -> str:
    if not date_from and not date_to:
        return "Toàn bộ lịch sử"
    from_str = date_from.strftime("%Y-%m-%d") if date_from else "..."
    to_str = date_to.strftime("%Y-%m-%d") if date_to else "..."
    return f"{from_str} → {to_str}"


def build_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    session.cookies.set("fchat_ddtk", token, domain="api-chat.fpt.com")
    return session


def filter_by_date(messages: list,
                   date_from: datetime | None,
                   date_to: datetime | None) -> list:
    if not date_from and not date_to:
        return messages
    result = []
    for m in messages:
        dt = parse_dt(m.get("createdAt", ""))
        if dt is None:
            result.append(m)
            continue
        if date_from and dt < date_from:
            continue
        if date_to and dt > date_to:
            continue
        result.append(m)
    return result


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------

def fetch_page(session: requests.Session, base_url: str, group_id: str,
               limit: int, before_inc=None) -> dict:
    url = f"{base_url}/message-query/group/{group_id}/message"
    params: dict = {"limit": limit}
    if before_inc is not None:
        params["messageIdInc"] = before_inc
        params["cursorType"] = "PREVIOUS"
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_group_info(session: requests.Session, base_url: str, group_id: str) -> dict:
    """Lấy thông tin nhóm (name, ...). Trả {} nếu lỗi hoặc endpoint không tồn tại."""
    try:
        resp = session.get(f"{base_url}/group-management/group/{group_id}", timeout=10)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return {}


def fetch_group_members(session: requests.Session, base_url: str,
                        group_id: str, limit: int = 50) -> list:
    """Lấy toàn bộ thành viên group qua phân trang page-based."""
    members = []
    page = 1
    print("[*] Fetching group members ...", file=sys.stderr)
    while True:
        url = f"{base_url}/group-management/group/{group_id}/participant"
        try:
            resp = session.get(url, params={"limit": limit, "page": page}, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [!] Lỗi fetch group members (page {page}): {e}", file=sys.stderr)
            return []
        data = resp.json()
        items = data if isinstance(data, list) else data.get(
            "data", data.get("members", data.get("participants", data.get("items", [])))
        )
        if not items:
            break
        members.extend(items)
        if len(items) < limit:
            break
        page += 1
    print(f"[✓] {len(members)} thành viên", file=sys.stderr)
    return members


def fetch_all_messages(token: str, group_id: str,
                       base_url: str = "https://api-chat.fpt.com",
                       limit: int = 50,
                       date_from: datetime | None = None) -> list:
    """Lấy toàn bộ tin nhắn bằng cách phân trang ngược (oldest-first)."""
    session = build_session(token)
    all_messages = []
    before_inc = None
    page = 0

    print(f"[*] Fetching messages từ group {group_id} ...", file=sys.stderr)

    while True:
        page += 1
        data = fetch_page(session, base_url, group_id, limit, before_inc)
        regulars = data.get("regulars", [])

        if not regulars:
            break

        all_messages = regulars + all_messages
        fetched = len(regulars)
        oldest_dt = parse_dt(regulars[0].get("createdAt", ""))
        oldest_str = oldest_dt.strftime("%Y-%m-%d") if oldest_dt else "?"
        print(f"  Page {page}: +{fetched} messages (total: {len(all_messages)}, oldest: {oldest_str})",
              file=sys.stderr)

        if fetched < limit:
            break

        if date_from and oldest_dt and oldest_dt < date_from:
            print(f"  [✓] Đã đủ dữ liệu từ {date_from.strftime('%Y-%m-%d')}, dừng fetch.",
                  file=sys.stderr)
            break

        before_inc = regulars[0]["messageIdInc"]

    print(f"[✓] Tổng: {len(all_messages)} messages", file=sys.stderr)
    return all_messages


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


# ---------------------------------------------------------------------------
# ASM Report Analysis
# ---------------------------------------------------------------------------

def detect_asm_reports(messages: list) -> list:
    """Lọc tin nhắn TEXT là báo cáo ASM (heuristic: có 'shop' + số cọc)."""
    result = []
    for msg in messages:
        if msg.get("type") != "TEXT":
            continue
        content = msg.get("content") or ""
        if (re.search(r'shop', content, re.IGNORECASE)
                and re.search(r'\d+\s*cọc|cọc\s*\d+', content, re.IGNORECASE)):
            result.append(msg)
    return result


def _parse_vnd_amount(raw: str, unit_suffix: str | None) -> int | None:
    """Normalize a Vietnamese-formatted amount string to an integer VND.

    Rules (in order):
      1. If unit_suffix ∈ {"tr", "M", "triệu"}: scale = 1_000_000.
         - `,` or `.` followed by 1-3 digits → decimal part.
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
        # allow one decimal separator of 1-3 digits
        m = re.fullmatch(r"(\d+)(?:[.,](\d{1,3}))?", s)
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


def _extract_sections(content: str) -> dict:
    """Trích xuất các mục báo cáo theo pattern '- Label: content'."""
    sections = {}
    pattern = re.compile(
        r'[-–•]\s*([^:\n]+?)\s*[:：]\s*(.*?)(?=\n\s*[-–•]|\Z)',
        re.DOTALL,
    )
    for m in pattern.finditer(content):
        label = m.group(1).strip().lower()
        text = m.group(2).strip()
        sections[label] = text
    return sections


def parse_asm_report(msg: dict) -> dict:
    """Parse một tin nhắn báo cáo ASM, trả về dict các field cấu trúc."""
    content = msg.get("content") or ""
    user = msg.get("user") or {}

    shop_match = re.search(r'shop\s*[:：]?\s*([^\n]+)', content, re.IGNORECASE)
    shop_ref = shop_match.group(1).strip() if shop_match else None

    coc_match = re.search(r'(\d+)\s*cọc|cọc\s*(\d+)', content, re.IGNORECASE)
    deposit_count = None
    if coc_match:
        deposit_count = int(coc_match.group(1) or coc_match.group(2))

    tiem_match = re.search(r'(\d+)\s*ra\s*tiêm', content, re.IGNORECASE)
    ra_tiem_count = int(tiem_match.group(1)) if tiem_match else None

    sections = _extract_sections(content)

    def get_section(*labels):
        for lbl in labels:
            for key in sections:
                if lbl in key:
                    return sections[key]
        return None

    if shop_ref is None or deposit_count is None:
        print(f"  [!] Không parse được shop/cọc từ message {msg.get('id', '?')}", file=sys.stderr)

    return {
        "shop_ref": shop_ref,
        "deposit_count": deposit_count,
        "ra_tiem_count": ra_tiem_count,
        "tich_cuc": get_section("tích cực"),
        "van_de": get_section("vấn đề"),
        "da_lam": get_section("đã làm"),
        "sender": user.get("displayName", "Unknown"),
        "sender_id": user.get("id", ""),
        "sent_at": msg.get("createdAt", ""),
        "message_id": msg.get("id", ""),
    }


def analyze_asm_reports(parsed_reports: list,
                        deposit_low: int = 2, deposit_high: int = 5) -> dict:
    """Phân tích báo cáo ASM: lọc shop theo đặt cọc, thu thập ý tưởng, highlight."""
    all_shops, low_deposit_shops, high_deposit_shops, no_deposit_shops = [], [], [], []
    ideas, tich_cuc_list, han_che_list = [], [], []
    total_deposits = 0
    total_ra_tiem  = 0

    for r in parsed_reports:
        dep = r.get("deposit_count")
        if dep is not None:
            total_deposits += dep
            if dep < deposit_low:
                level = "Thấp"
            elif dep > deposit_high:
                level = "Cao"
            else:
                level = "Bình thường"
            entry = {"shop_ref": r["shop_ref"], "deposit_count": dep,
                     "sender": r["sender"], "level": level}
            all_shops.append(entry)
            if dep == 0:
                no_deposit_shops.append({"sender": r["sender"], "shop_ref": r["shop_ref"]})
            elif level == "Thấp":
                low_deposit_shops.append(entry)
            elif level == "Cao":
                high_deposit_shops.append(entry)

        tiem = r.get("ra_tiem_count")
        if tiem is not None:
            total_ra_tiem += tiem

        if r.get("da_lam"):
            ideas.append({
                "sender": r["sender"], "shop_ref": r["shop_ref"],
                "da_lam": r["da_lam"], "sent_at": r["sent_at"],
            })

        if r.get("tich_cuc"):
            tich_cuc_list.append({
                "sender": r["sender"], "shop_ref": r["shop_ref"], "content": r["tich_cuc"],
            })

        if r.get("van_de"):
            han_che_list.append({
                "sender": r["sender"], "shop_ref": r["shop_ref"], "content": r["van_de"],
            })

    return {
        "total_deposits":    total_deposits,
        "total_ra_tiem":     total_ra_tiem,
        "all_shops":         all_shops,
        "no_deposit_shops":  no_deposit_shops,
        "low_deposit_shops": low_deposit_shops,
        "high_deposit_shops": high_deposit_shops,
        "ideas":             ideas,
        "highlights":        {"tich_cuc": tich_cuc_list, "han_che": han_che_list},
        "missing_reporters": None,  # None = chưa kiểm tra; [] = tất cả đã báo cáo
    }


def check_asm_compliance(parsed_reports: list, members: list,
                         target_date_str: str, deadline_hhmm: str = "20:00",
                         skip_list: list | None = None) -> list:
    """Trả về displayName của thành viên chưa gửi báo cáo trước deadline."""
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


def check_late_reporters(parsed_reports: list,
                         target_date_str: str,
                         deadline_hhmm: str = "20:00") -> list:
    """Trả về list {sender, sent_at_vn} của ASM gửi báo cáo SAU deadline."""
    VN_OFFSET = 7 * 3600
    try:
        deadline_h, deadline_m = map(int, deadline_hhmm.split(":"))
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    except ValueError:
        return []

    late = []
    seen = set()
    for r in parsed_reports:
        dt = parse_dt(r.get("sent_at", ""))
        if not dt:
            continue
        vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
        if vn_dt.date() != target_date:
            continue
        after_deadline = (vn_dt.hour > deadline_h or
                          (vn_dt.hour == deadline_h and vn_dt.minute >= deadline_m))
        if after_deadline and r["sender"] not in seen:
            seen.add(r["sender"])
            late.append({
                "sender":     r["sender"],
                "sent_at_vn": vn_dt.strftime("%H:%M"),
            })
    return late


def analyze_multiday(parsed_reports: list, date_from_str: str, date_to_str: str) -> dict:
    """Phân tích báo cáo ASM theo từng ngày trong khoảng nhiều ngày."""
    VN_OFFSET = 7 * 3600

    d_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()
    d_to   = datetime.strptime(date_to_str,   "%Y-%m-%d").date()
    total_days = (d_to - d_from).days + 1
    all_dates  = [d_from + timedelta(days=i) for i in range(total_days)]

    # Group reports by (date, sender)
    by_date: dict[_date, list] = {d: [] for d in all_dates}
    for r in parsed_reports:
        dt = parse_dt(r.get("sent_at", ""))
        if not dt:
            continue
        vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
        if d_from <= vn_dt.date() <= d_to:
            by_date[vn_dt.date()].append(r)

    # All senders who appeared at least once
    all_senders = sorted({r["sender"] for r in parsed_reports if r.get("sender")})

    # daily_summary
    daily_summary = []
    for d in all_dates:
        reps = by_date[d]
        daily_summary.append({
            "date":           d.strftime("%Y-%m-%d"),
            "total_deposits": sum(r["deposit_count"] for r in reps if r.get("deposit_count") is not None),
            "total_ra_tiem":  sum(r["ra_tiem_count"]  for r in reps if r.get("ra_tiem_count")  is not None),
            "reporter_count": len({r["sender"] for r in reps}),
        })

    # Per-sender reported days set
    sender_dates: dict[str, set] = {s: set() for s in all_senders}
    for d, reps in by_date.items():
        for r in reps:
            if r.get("sender"):
                sender_dates[r["sender"]].add(d)

    # asm_summary with streak calculation
    def _streaks(reported_set: set, all_d: list):
        longest_streak = longest_gap = cur_streak = cur_gap = 0
        for d in all_d:
            if d in reported_set:
                cur_streak += 1
                cur_gap = 0
            else:
                cur_gap += 1
                cur_streak = 0
            longest_streak = max(longest_streak, cur_streak)
            longest_gap    = max(longest_gap,    cur_gap)
        return longest_streak, longest_gap

    asm_summary = []
    for sender in all_senders:
        rep_dates = sender_dates[sender]
        report_days = len(rep_dates)
        report_rate = round(report_days / total_days * 100, 1) if total_days else 0
        sender_reps = [r for r in parsed_reports
                       if r.get("sender") == sender and r.get("deposit_count") is not None]
        total_dep = sum(r["deposit_count"] for r in sender_reps)
        avg_dep   = round(total_dep / report_days, 1) if report_days else 0
        ls, lg    = _streaks(rep_dates, all_dates)
        asm_summary.append({
            "sender":              sender,
            "report_days":         report_days,
            "total_days":          total_days,
            "report_rate":         report_rate,
            "total_deposits":      total_dep,
            "avg_deposits_per_day": avg_dep,
            "longest_streak":      ls,
            "longest_gap":         lg,
        })
    asm_summary.sort(key=lambda x: (-x["report_rate"], -x["total_deposits"]))

    # missing_by_day
    missing_by_day = []
    for d in all_dates:
        reported_today = {r["sender"] for r in by_date[d]}
        missing = sorted(s for s in all_senders if s not in reported_today)
        missing_by_day.append({
            "date":          d.strftime("%Y-%m-%d"),
            "missing_count": len(missing),
            "missing_names": missing,
        })

    # shop_summary
    shop_acc: dict[str, dict] = {}
    for r in parsed_reports:
        shop = r.get("shop_ref")
        if not shop:
            continue
        dt = parse_dt(r.get("sent_at", ""))
        if not dt:
            continue
        vn_dt = datetime.fromtimestamp(dt.timestamp() + VN_OFFSET, tz=timezone.utc)
        if not (d_from <= vn_dt.date() <= d_to):
            continue
        dep = r.get("deposit_count") or 0
        if shop not in shop_acc:
            shop_acc[shop] = {"sender": r.get("sender", ""), "total_deposits": 0, "dates": set()}
        shop_acc[shop]["total_deposits"] += dep
        shop_acc[shop]["dates"].add(vn_dt.date())

    shop_summary = sorted([
        {
            "shop_ref":      shop,
            "sender":        v["sender"],
            "total_deposits": v["total_deposits"],
            "report_days":   len(v["dates"]),
            "avg_deposits":  round(v["total_deposits"] / len(v["dates"]), 1) if v["dates"] else 0,
        }
        for shop, v in shop_acc.items()
    ], key=lambda x: -x["total_deposits"])

    return {
        "total_days":     total_days,
        "daily_summary":  daily_summary,
        "asm_summary":    asm_summary,
        "missing_by_day": missing_by_day,
        "shop_summary":   shop_summary,
    }


def analyze_weekly(messages: list,
                   group_members: list,
                   target_date_vn: str,
                   deadline: str = "20:00") -> dict:
    """Báo cáo tuần một ngày: phân loại tin nhắn, tìm muộn/thiếu, dump text."""
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


# ---------------------------------------------------------------------------
# Report Output
# ---------------------------------------------------------------------------

def print_asm_report(asm_data: dict,
                     date_from: datetime | None = None,
                     date_to: datetime | None = None) -> None:
    sep = "=" * 65
    print(sep)
    print("  FPT CHAT - BÁO CÁO ASM")
    print(sep)

    print(f"\n{'TỔNG QUAN':=<40}")
    print(f"  Khoảng thời gian : {fmt_date_range(date_from, date_to)}")
    print(f"  Báo cáo ASM      : {len(asm_data.get('all_shops', []))}")

    low_shops  = asm_data.get("low_deposit_shops", [])
    high_shops = asm_data.get("high_deposit_shops", [])
    ideas      = asm_data.get("ideas", [])
    tich_cuc   = asm_data.get("highlights", {}).get("tich_cuc", [])
    han_che    = asm_data.get("highlights", {}).get("han_che", [])
    missing    = asm_data.get("missing_reporters")

    print(f"\n{'SHOP ĐẶT CỌC THẤP (< ngưỡng)':=<40}")
    if low_shops:
        for s in sorted(low_shops, key=lambda x: x["deposit_count"]):
            print(f"  [{s['deposit_count']:>3} đặt cọc] {s['shop_ref']}  — {s['sender']}")
    else:
        print("  (không có)")

    print(f"\n{'SHOP ĐẶT CỌC CAO (> ngưỡng)':=<40}")
    if high_shops:
        for s in sorted(high_shops, key=lambda x: x["deposit_count"], reverse=True):
            print(f"  [{s['deposit_count']:>3} đặt cọc] {s['shop_ref']}  — {s['sender']}")
    else:
        print("  (không có)")

    print(f"\n{'Ý TƯỞNG TRIỂN KHAI TỪ ASM':=<40}")
    if ideas:
        for i, idea in enumerate(ideas, 1):
            print(f"  {i}. [{idea['sender']}] Shop: {idea['shop_ref']}")
            for line in idea["da_lam"].splitlines():
                if line.strip():
                    print(f"     {line.strip()}")
    else:
        print("  (không có)")

    print(f"\n{'ĐIỂM TÍCH CỰC':=<40}")
    if tich_cuc:
        for i, h in enumerate(tich_cuc, 1):
            print(f"  {i}. [{h['sender']}] Shop: {h['shop_ref']}")
            for line in h["content"].splitlines():
                if line.strip():
                    print(f"     {line.strip()}")
    else:
        print("  (không có)")

    print(f"\n{'ĐIỂM HẠN CHẾ':=<40}")
    if han_che:
        for i, h in enumerate(han_che, 1):
            print(f"  {i}. [{h['sender']}] Shop: {h['shop_ref']}")
            for line in h["content"].splitlines():
                if line.strip():
                    print(f"     {line.strip()}")
    else:
        print("  (không có)")

    if missing is not None:
        print(f"\n{'ASM CHƯA BÁO CÁO':=<40}")
        if missing:
            for name in missing:
                print(f"  - {name}")
        else:
            print("  Tất cả ASM đã báo cáo")

    print(f"\n{sep}")


def print_weekly_report(data: dict) -> None:
    """In báo cáo tuần một ngày ra stdout."""
    target = data["target_date"]
    deadline = data["deadline"]
    reports = data["reports"]
    late_list = data["late_list"]
    missing_list = data["missing_list"]

    sep = "=" * 65
    print(sep)
    print(f"  BÁO CÁO TUẦN — {target}")
    print(sep)
    print(f"  Deadline: {deadline}")
    print(f"  Đã báo cáo: {len(reports)}")
    print(f"  Muộn: {len(late_list)}")
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


# ---------------------------------------------------------------------------
# Excel Export
# ---------------------------------------------------------------------------

def write_asm_excel(asm_data: dict, path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        print("Thiếu thư viện 'openpyxl'. Chạy: pip install openpyxl", file=sys.stderr)
        sys.exit(1)

    def style_header(ws):
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9E1F2")
            cell.alignment = Alignment(horizontal="center")
        ws.freeze_panes = "A2"

    def set_widths(ws, widths: dict):
        for col_idx, width in widths.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = width

    def wrap_col(ws, col: int):
        for row in ws.iter_rows(min_row=2, min_col=col, max_col=col):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True)

    wb = Workbook()

    # ── Sheet 1: Shop Đặt Cọc ─────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Shop Đặt Cọc"
    ws1.append(["STT", "Shop", "Số đặt cọc", "Ra tiêm", "Mức", "ASM"])
    style_header(ws1)
    all_shops = sorted(asm_data.get("all_shops", []),
                       key=lambda x: x["deposit_count"], reverse=True)
    # Build ra_tiem lookup by shop_ref from parsed_reports if available
    _ra_tiem_map = {r["shop_ref"]: r.get("ra_tiem_count")
                    for r in asm_data.get("parsed_reports", []) if r.get("shop_ref")}
    for i, s in enumerate(all_shops, 1):
        ra = _ra_tiem_map.get(s["shop_ref"], "")
        ws1.append([i, s["shop_ref"], s["deposit_count"],
                    "" if ra is None else ra, s["level"], s["sender"]])
    set_widths(ws1, {1: 6, 2: 50, 3: 14, 4: 12, 5: 14, 6: 35})

    # ── Sheet 2: Ý tưởng ASM ──────────────────────────────────────────────
    ws2 = wb.create_sheet("Ý tưởng ASM")
    ws2.append(["STT", "ASM", "Shop", "Nội dung", "Ngày giờ (UTC+7)"])
    style_header(ws2)
    for i, idea in enumerate(asm_data.get("ideas", []), 1):
        ws2.append([i, idea["sender"], idea["shop_ref"],
                    idea["da_lam"], to_vn_str(idea["sent_at"])])
    set_widths(ws2, {1: 6, 2: 30, 3: 40, 4: 80, 5: 22})
    wrap_col(ws2, 4)

    # ── Sheet 3: Điểm nổi bật ─────────────────────────────────────────────
    ws3 = wb.create_sheet("Điểm nổi bật")
    ws3.append(["STT", "ASM", "Shop", "Loại", "Nội dung"])
    style_header(ws3)
    highlights = (
        [(h["sender"], h["shop_ref"], "Tích cực", h["content"])
         for h in asm_data.get("highlights", {}).get("tich_cuc", [])]
        + [(h["sender"], h["shop_ref"], "Hạn chế", h["content"])
           for h in asm_data.get("highlights", {}).get("han_che", [])]
    )
    for i, (sender, shop, loai, content) in enumerate(highlights, 1):
        ws3.append([i, sender, shop, loai, content])
    set_widths(ws3, {1: 6, 2: 30, 3: 40, 4: 12, 5: 80})
    wrap_col(ws3, 5)

    # ── Sheet 4: Báo cáo muộn ─────────────────────────────────────────────
    ws4 = wb.create_sheet("Báo cáo muộn")
    ws4.append(["STT", "ASM", "Giờ gửi (UTC+7)"])
    style_header(ws4)
    late = asm_data.get("late_reporters", [])
    if late:
        for i, lr in enumerate(late, 1):
            ws4.append([i, lr["sender"], lr["sent_at_vn"]])
    else:
        ws4.append(["", "Không có ASM báo cáo muộn"])
    set_widths(ws4, {1: 6, 2: 45, 3: 18})

    # ── Sheet 5: Chưa báo cáo sau deadline ───────────────────────────────
    ws5 = wb.create_sheet("Chưa báo cáo sau deadline")
    ws5.append(["STT", "Tên ASM"])
    style_header(ws5)
    missing = asm_data.get("missing_reporters")
    if missing is None:
        ws5.append(["", "(Không thể kiểm tra — thiếu token/group)"])
    elif not missing:
        ws5.append(["", "Tất cả ASM đã báo cáo đúng hạn"])
    else:
        for i, name in enumerate(missing, 1):
            ws5.append([i, name])
    set_widths(ws5, {1: 6, 2: 45})

    # ── Sheet 6: Chưa báo cáo tại thời điểm chạy ─────────────────────────
    ws6 = wb.create_sheet("Chưa báo cáo hiện tại")
    ws6.append(["STT", "Tên thành viên"])
    style_header(ws6)
    unreported = asm_data.get("unreported_now")
    if unreported is None:
        ws6.append(["", "(Không thể kiểm tra — thiếu token/group)"])
    elif not unreported:
        ws6.append(["", "Tất cả đã báo cáo"])
    else:
        for i, name in enumerate(unreported, 1):
            ws6.append([i, name])
    set_widths(ws6, {1: 6, 2: 45})

    wb.save(path)


def write_weekly_excel(data: dict, group_members: list, path) -> None:
    """Xuất báo cáo tuần ra .xlsx với 2 sheet: Tổng hợp tuần & Nội dung."""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font
    except ImportError:
        print("Thiếu 'openpyxl'. Chạy: pip install openpyxl", file=sys.stderr)
        sys.exit(1)

    wb = openpyxl.Workbook()

    # Sheet 1: Tổng hợp tuần
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

    for cell in ws1[1]:
        cell.font = Font(bold=True)
    ws1.column_dimensions["A"].width = 28
    ws1.column_dimensions["B"].width = 14
    ws1.column_dimensions["C"].width = 10

    # Sheet 2: Nội dung
    ws2 = wb.create_sheet("Nội dung")
    ws2.append(["Người báo cáo", "Giờ gửi", "Trạng thái", "Nội dung"])
    for cell in ws2[1]:
        cell.font = Font(bold=True)

    for r in sorted(data["reports"], key=lambda r: r["sent_at_vn"]):
        status = "Muộn" if r["is_late"] else "Đúng giờ"
        extra = f"\n\n(+{r['extra_count']} tin nhắn khác)" if r["extra_count"] else ""
        body = r["text"] + extra
        ws2.append([r["sender"], r["sent_at_vn"], status, body])

    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 10
    ws2.column_dimensions["C"].width = 12
    ws2.column_dimensions["D"].width = 100

    for row_idx in range(2, ws2.max_row + 1):
        ws2.cell(row=row_idx, column=4).alignment = Alignment(
            wrap_text=True, vertical="top"
        )

    wb.save(path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--config", default="config.json")
    pre_args, _ = pre.parse_known_args()
    cfg = load_config(pre_args.config)

    parser = argparse.ArgumentParser(
        description="FPT Chat ASM Report Tool — phân tích báo cáo hàng ngày của ASM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ví dụ:
  python fpt_chat_stats.py --today
  python fpt_chat_stats.py --today --excel bao_cao.xlsx
  python fpt_chat_stats.py --from 2026-04-01 --to 2026-04-16
  python fpt_chat_stats.py --save raw.json
  python fpt_chat_stats.py --load raw.json --today
        """,
    )
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--token", default=None,
                        help="Token xác thực (fchat_ddtk). Ưu tiên hơn config file.")
    parser.add_argument("--group", default=None,
                        help="Group ID hoặc URL chat group.")
    parser.add_argument("--api-url", default=None,
                        help="Base URL của API (mặc định: https://api-chat.fpt.com)")
    parser.add_argument("--limit", type=int, default=50,
                        help="Số tin nhắn mỗi trang API (mặc định: 50)")
    parser.add_argument("--from", dest="date_from", default=None, metavar="YYYY-MM-DD",
                        help="Chỉ phân tích từ ngày này (inclusive)")
    parser.add_argument("--to", dest="date_to", default=None, metavar="YYYY-MM-DD",
                        help="Chỉ phân tích đến ngày này (inclusive)")
    parser.add_argument("--today", action="store_true",
                        help="Phân tích hôm nay (giờ VN). Không dùng kèm --from/--to/--date.")
    parser.add_argument("--save", metavar="FILE",
                        help="Lưu raw messages ra file JSON")
    parser.add_argument("--load", metavar="FILE",
                        help="Dùng file JSON đã lưu (offline)")
    parser.add_argument("--excel", metavar="FILE",
                        help="Xuất báo cáo Excel (.xlsx) với 4 sheet ASM")
    parser.add_argument("--deposit-low", dest="deposit_low",
                        type=int, default=cfg.get("asm_deposit_low", 2), metavar="N",
                        help="Ngưỡng đặt cọc thấp — shop có deposit < N (mặc định: 2)")
    parser.add_argument("--deposit-high", dest="deposit_high",
                        type=int, default=cfg.get("asm_deposit_high", 5), metavar="N",
                        help="Ngưỡng đặt cọc cao — shop có deposit > N (mặc định: 5)")
    parser.add_argument("--asm-deadline", default="20:00", metavar="HH:MM",
                        help="Deadline báo cáo hàng ngày (mặc định: 20:00, giờ VN)")
    parser.add_argument("--weekly", default=None, metavar="YYYY-MM-DD",
                        help="Báo cáo tuần một ngày: liệt kê ai đã/muộn/chưa báo cáo + dump text.")
    parser.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                        help="Ngày kiểm tra compliance (mặc định: hôm nay giờ VN)")
    parser.add_argument("--skip-reporters", default="", metavar="NAMES",
                        help="Tên cách nhau bằng dấu phẩy — loại khỏi compliance check")

    args = parser.parse_args()

    if args.weekly and (args.today or args.date_from or args.date_to or args.date):
        print("Error: --weekly không dùng chung với --today / --from / --to / --date.", file=sys.stderr)
        sys.exit(2)

    token   = args.token   or cfg.get("token")
    group   = args.group   or cfg.get("group")
    api_url = args.api_url or cfg.get("api_url", "https://api-chat.fpt.com")

    # ── Validate (chỉ khi cần gọi API; --weekly tự kiểm tra bên trong)
    if not args.load and not args.weekly:
        if not token:
            print("Error: --token là bắt buộc (hoặc set 'token' trong config.json)", file=sys.stderr)
            sys.exit(1)
        if not group:
            print("Error: --group là bắt buộc (hoặc set 'group' trong config.json)", file=sys.stderr)
            sys.exit(1)

    # ── --today shortcut
    if args.today:
        if args.date_from or args.date_to or args.date:
            print("Error: --today không thể dùng kèm --from, --to, hoặc --date", file=sys.stderr)
            sys.exit(1)
        import time as _time
        _vn_today = datetime.fromtimestamp(
            _time.time() + 7 * 3600, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        args.date_from = _vn_today
        args.date_to   = _vn_today
        args.date      = _vn_today

    # ── --weekly shortcut (báo cáo tuần một ngày)
    if args.weekly:
        try:
            target_vn = datetime.strptime(args.weekly, "%Y-%m-%d").date()
        except ValueError:
            print(f"Error: --weekly giá trị không hợp lệ: {args.weekly}", file=sys.stderr)
            sys.exit(2)

        # Half-open VN-day window: [target 00:00+07, target+1 00:00+07)
        vn_start_utc = datetime.combine(target_vn, time(0, 0), tzinfo=timezone.utc) - timedelta(hours=7)
        vn_end_utc   = vn_start_utc + timedelta(days=1)

        # Fetch or load raw messages
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

        # Clip to the half-open window. filter_by_date uses inclusive date_to,
        # so subtract 1 microsecond to emulate half-open [start, end).
        messages = filter_by_date(
            messages, vn_start_utc, vn_end_utc - timedelta(microseconds=1),
        )

        # Members are REQUIRED for the missing list.
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

    # ── Skip reporters: merge config + CLI
    skip_list = list(cfg.get("asm_skip_reporters", []))
    if args.skip_reporters:
        skip_list += [n.strip() for n in args.skip_reporters.split(",") if n.strip()]

    date_from = parse_date_arg(args.date_from, end_of_day=False) if args.date_from else None
    date_to   = parse_date_arg(args.date_to,   end_of_day=True)  if args.date_to   else None

    # ── Fetch messages
    if args.load:
        print(f"[*] Loading từ file: {args.load}", file=sys.stderr)
        with open(args.load, encoding="utf-8") as f:
            messages = json.load(f)
        print(f"[✓] Loaded {len(messages)} messages", file=sys.stderr)
    else:
        group_id = extract_group_id(group)
        messages = fetch_all_messages(token=token, group_id=group_id,
                                      base_url=api_url, limit=args.limit,
                                      date_from=date_from)

    # ── Save raw
    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        print(f"[✓] Đã lưu raw messages → {args.save}", file=sys.stderr)

    # ── Filter by date range
    messages = filter_by_date(messages, date_from, date_to)

    # ── ASM analysis (always)
    asm_msgs = detect_asm_reports(messages)
    print(f"[*] Phát hiện {len(asm_msgs)} báo cáo ASM", file=sys.stderr)
    if not asm_msgs:
        print("  [!] Không tìm thấy báo cáo ASM nào.", file=sys.stderr)

    parsed_reports = [parse_asm_report(m) for m in asm_msgs]
    asm_data = analyze_asm_reports(parsed_reports,
                                   deposit_low=args.deposit_low,
                                   deposit_high=args.deposit_high)

    # ── Compliance check
    if token and group:
        _session = build_session(token)
        members = fetch_group_members(_session, api_url, extract_group_id(group))
    else:
        print("[!] Thiếu --token/--group — bỏ qua kiểm tra compliance", file=sys.stderr)
        members = []

    if members:
        import time as _time
        target_date = args.date or datetime.fromtimestamp(
            _time.time() + 7 * 3600, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        asm_data["missing_reporters"] = check_asm_compliance(
            parsed_reports, members, target_date, args.asm_deadline, skip_list,
        )

    # ── Output
    print_asm_report(asm_data, date_from, date_to)

    if args.excel:
        write_asm_excel(asm_data, args.excel)
        print(f"[✓] Đã xuất Excel → {args.excel}", file=sys.stderr)


if __name__ == "__main__":
    main()
