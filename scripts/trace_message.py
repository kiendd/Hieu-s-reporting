"""Trace one message through every gate of the pipeline.

Usage:
    python scripts/trace_message.py --load raw.json --id <messageId>
    python scripts/trace_message.py --load raw.json --substr "TienDTT12"
    python scripts/trace_message.py --load raw.json --substr "..." --members members.json

Reports per-gate PASS/FAIL so you can pinpoint where a report disappears.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fpt_chat_stats as fcs
import llm_extractor


def _find_message(messages: list, msg_id: str | None, substr: str | None) -> dict | None:
    for m in messages:
        if msg_id and m.get("id") == msg_id:
            return m
        if substr and substr in (m.get("content") or ""):
            return m
    return None


def _vn_date(iso: str):
    dt = fcs.parse_dt(iso)
    if dt is None:
        return None
    return fcs.datetime.fromtimestamp(dt.timestamp() + 7 * 3600, tz=timezone.utc).date()


def trace(msg: dict, members: list | None) -> None:
    content = msg.get("content") or ""
    sender = (msg.get("user") or {}).get("displayName", "?")
    created = msg.get("createdAt", "")

    print(f"id        : {msg.get('id')}")
    print(f"sender    : {sender}")
    print(f"createdAt : {created}  (VN date: {_vn_date(created)})")
    print(f"length    : {len(content)} chars")
    print()

    # Gate 1: type
    mtype = msg.get("type")
    is_accepted = mtype in ("TEXT", "MEDIA")
    print(f"[gate 1] type in (TEXT, MEDIA)    : {'PASS' if is_accepted else 'FAIL'} (got {mtype!r})")

    # Gate 2-4: L2 pre-filter
    digits = re.findall(r"\d", content)
    normalized = fcs._strip_diacritics(content)
    matched_kw = [kw for kw in fcs._REPORT_KEYWORDS if kw in normalized]
    print(f"[gate 2] length >= 80             : {'PASS' if len(content) >= 80 else 'FAIL'} ({len(content)})")
    print(f"[gate 3] digits >= 2              : {'PASS' if len(digits) >= 2 else 'FAIL'} ({len(digits)})")
    print(f"[gate 4] keyword present          : {'PASS' if matched_kw else 'FAIL'} (matched: {matched_kw})")

    pre_pass = is_accepted and len(content) >= 80 and len(digits) >= 2 and bool(matched_kw)
    if not pre_pass:
        print("\n→ Stops at L2 pre-filter. LLM never called.")
        return

    # Gate 5: LLM extract
    print("\n[gate 5] llm_extractor.extract_reports(msg)")
    try:
        reports = llm_extractor.extract_reports(msg)
    except Exception as e:
        print(f"  RAISED: {type(e).__name__}: {e}")
        return
    if not reports:
        print("  returned: [] (no reports)")
        return
    for i, r in enumerate(reports):
        print(f"  report[{i}]: type={r.get('report_type')!r} shop_ref={r.get('shop_ref')!r} parse_error={r.get('parse_error')!r}")

    # Gate 6: weekday routing
    vd = _vn_date(created)
    if vd:
        expected = fcs.report_type_for_date(vd)
        print(f"\n[gate 6] report_type_for_date({vd}) = {expected!r}")
        for i, r in enumerate(reports):
            match = r.get("report_type") == expected
            print(f"  report[{i}] matches routing : {'PASS' if match else 'FAIL'} (LLM: {r.get('report_type')!r}, routed: {expected!r})")

    # Gate 7: member active
    if members is not None:
        sid = (msg.get("user") or {}).get("id", "")
        match = next((m for m in members if m.get("userId") == sid or m.get("id") == sid
                      or (m.get("displayName") or "").strip() == sender.strip()), None)
        print(f"\n[gate 7] sender in member list    : {'YES' if match else 'NO'}")
        if match:
            active = fcs._is_active_member(match)
            print(f"         _is_active_member         : {'PASS' if active else 'FAIL (zombie: lastReadMessageId=0)'}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--load", required=True, help="raw.json snapshot from `fpt_chat_stats.py --save`")
    p.add_argument("--id", default=None, help="message id to trace")
    p.add_argument("--substr", default=None, help="locate first message whose content contains this substring")
    p.add_argument("--members", default=None, help="optional JSON list of group members for gate 7")
    args = p.parse_args()

    if not args.id and not args.substr:
        p.error("provide --id or --substr")

    with open(args.load, encoding="utf-8") as f:
        messages = json.load(f)

    msg = _find_message(messages, args.id, args.substr)
    if msg is None:
        print(f"No message matched (id={args.id!r}, substr={args.substr!r})", file=sys.stderr)
        sys.exit(1)

    members = None
    if args.members:
        with open(args.members, encoding="utf-8") as f:
            members = json.load(f)

    llm_extractor.configure()
    trace(msg, members)


if __name__ == "__main__":
    main()
