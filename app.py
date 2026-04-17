"""
FPT Chat ASM Report — Streamlit Web UI
Chạy: streamlit run app.py
"""

import io
import json
import os
from datetime import date, datetime, timezone

import streamlit as st
from streamlit_javascript import st_javascript

# ── localStorage helpers (browser-side, mỗi user riêng, không gửi lên server) ─
def _ls_get(key: str) -> str:
    """Đọc giá trị từ localStorage của browser. Trả '' nếu chưa có."""
    val = st_javascript(f"localStorage.getItem({json.dumps(key)}) || ''")
    return val if isinstance(val, str) else ""

def _ls_set(key: str, value: str) -> None:
    """Ghi giá trị vào localStorage của browser."""
    st_javascript(f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)}); 'ok'")

# ── Config file (local only, group ID only — token không bao giờ ghi file) ───
_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def _load_config() -> dict:
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg.pop("token", None)  # xoá token cũ nếu còn sót
            return cfg
        except Exception:
            pass
    return {}

def _save_group_local(group: str) -> None:
    """Lưu group vào config.json khi chạy local. Token không bao giờ ghi file."""
    if not os.path.isfile(_CONFIG_PATH):
        return
    cfg = _load_config()
    cfg["group"] = group
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ── Import core logic từ fpt_chat_stats ──────────────────────────────────────
try:
    from fpt_chat_stats import (
        analyze_asm_reports,
        check_asm_compliance,
        detect_asm_reports,
        extract_group_id,
        fetch_all_messages,
        fetch_group_members,
        filter_by_date,
        parse_asm_report,
        parse_date_arg,
        build_session,
        write_asm_excel,
    )
except ImportError as e:
    st.error(f"Không tìm thấy fpt_chat_stats.py: {e}")
    st.stop()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FPT Chat ASM Report",
    page_icon="📊",
    layout="centered",
)

st.title("📊 FPT Chat ASM Report")
st.caption("Phân tích báo cáo hàng ngày của ASM từ FPT Chat")

# Ẩn iframe của streamlit-javascript (height=0 nhưng vẫn chiếm không gian)
st.markdown("""
<style>
div[data-testid="stCustomComponentV1"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# ── Vùng 1: Kết nối ──────────────────────────────────────────────────────────
# Token: localStorage (browser) — không bao giờ đọc/ghi file
# Group: localStorage → config.json (local fallback)
_cfg = _load_config()
_saved_token = _ls_get("fpt_token")
_saved_group = _ls_get("fpt_group") or _cfg.get("group", "")

st.divider()

col_token, col_group = st.columns(2)
with col_token:
    token = st.text_input(
        "Token (Bearer)",
        value=_saved_token,
        type="password",
        placeholder="Dán token từ DevTools vào đây",
        help="DevTools → Network → chọn request api-chat.fpt.com → Headers → Authorization: Bearer <token>",
    )
with col_group:
    group = st.text_input(
        "Group ID hoặc URL nhóm chat",
        value=_saved_group,
        placeholder="686b517a54ca42cb3c30e1df hoặc URL đầy đủ",
    )

# ── Vùng 2: Thời gian ────────────────────────────────────────────────────────
date_mode = st.radio(
    "Khoảng thời gian",
    ["Hôm nay", "Chọn khoảng ngày"],
    horizontal=True,
    label_visibility="collapsed",
)
use_today = date_mode == "Hôm nay"

if not use_today:
    col1, col2 = st.columns(2)
    with col1:
        date_from_input = st.date_input("Từ ngày", value=date.today())
    with col2:
        date_to_input = st.date_input("Đến ngày", value=date.today())

# ── Vùng 3: Tuỳ chọn nâng cao ────────────────────────────────────────────────
with st.expander("⚙️ Tuỳ chọn nâng cao"):
    c1, c2, c3 = st.columns(3)
    with c1:
        deposit_low  = st.number_input("Ngưỡng cọc thấp (<)", value=2, min_value=0)
    with c2:
        deposit_high = st.number_input("Ngưỡng cọc cao (>)",  value=5, min_value=0)
    with c3:
        deadline = st.text_input("Deadline (giờ VN)", value="20:00")
    skip_str = st.text_input(
        "Bỏ qua khỏi compliance check",
        placeholder="Tên Trưởng phòng, Tên Giám đốc",
        help="Cách nhau bằng dấu phẩy",
    )

# ── Nút chạy ─────────────────────────────────────────────────────────────────
run = st.button("▶ Chạy phân tích", type="primary", use_container_width=True)

if run:
    if not token:
        st.error("Vui lòng nhập Token.")
        st.stop()
    if not group:
        st.error("Vui lòng nhập Group ID hoặc URL.")
        st.stop()

    # Lưu vào localStorage (browser, mỗi user riêng, không gửi lên server)
    _ls_set("fpt_token", token)
    _ls_set("fpt_group", group)
    # Lưu group vào config.json khi chạy local (không lưu token)
    _save_group_local(group)

    # Tính date range
    VN_OFFSET = 7 * 3600
    if use_today:
        _today_str = datetime.fromtimestamp(
            __import__("time").time() + VN_OFFSET, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        date_from_str = date_to_str = target_date = _today_str
    else:
        date_from_str = date_from_input.strftime("%Y-%m-%d")
        date_to_str   = date_to_input.strftime("%Y-%m-%d")
        target_date   = date_to_str

    date_from = parse_date_arg(date_from_str, end_of_day=False)
    date_to   = parse_date_arg(date_to_str,   end_of_day=True)

    skip_list = [s.strip() for s in skip_str.split(",") if s.strip()]
    group_id  = extract_group_id(group)

    # ── Fetch messages ────────────────────────────────────────────────────────
    with st.status("Đang tải tin nhắn...", expanded=True) as status:
        try:
            messages = fetch_all_messages(
                token=token,
                group_id=group_id,
                date_from=date_from,
            )
            st.write(f"Tải được {len(messages)} tin nhắn")
        except Exception as e:
            status.update(label="Lỗi khi tải tin nhắn", state="error")
            st.error(f"Lỗi: {e}")
            st.stop()

        messages = filter_by_date(messages, date_from, date_to)
        st.write(f"Sau lọc ngày: {len(messages)} tin nhắn")

        asm_msgs = detect_asm_reports(messages)
        st.write(f"Phát hiện {len(asm_msgs)} báo cáo ASM")

        try:
            session = build_session(token)
            members = fetch_group_members(session, "https://api-chat.fpt.com", group_id)
            st.write(f"Thành viên nhóm: {len(members)}")
        except Exception:
            members = []
            st.write("Không lấy được danh sách thành viên — bỏ qua compliance check")

        status.update(label="Hoàn tất tải dữ liệu", state="complete")

    # ── Phân tích ─────────────────────────────────────────────────────────────
    parsed   = [parse_asm_report(m) for m in asm_msgs]
    asm_data = analyze_asm_reports(parsed, deposit_low=deposit_low, deposit_high=deposit_high)

    if members:
        asm_data["missing_reporters"] = check_asm_compliance(
            parsed, members, target_date, deadline, skip_list
        )

    if not asm_msgs:
        st.warning("Không tìm thấy báo cáo ASM nào trong khoảng thời gian này.")

    # ── Chuẩn bị Excel buffer ─────────────────────────────────────────────────
    excel_buf = io.BytesIO()
    write_asm_excel(asm_data, excel_buf)
    excel_buf.seek(0)

    # ── Header kết quả + nút download ────────────────────────────────────────
    st.divider()
    col_hdr, col_dl = st.columns([4, 1])
    with col_hdr:
        st.subheader("Kết quả phân tích")
    with col_dl:
        st.download_button(
            label="⬇️ Tải Excel",
            data=excel_buf,
            file_name=f"asm_report_{target_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    # Metrics tổng quan
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Báo cáo ASM", len(asm_msgs))
    col_b.metric("Shop cọc thấp", len(asm_data["low_deposit_shops"]))
    col_c.metric("Shop cọc cao",  len(asm_data["high_deposit_shops"]))

    # ── Task 1.1: Shop đặt cọc ────────────────────────────────────────────────
    st.subheader("🏪 Shop đặt cọc")
    all_shops = sorted(asm_data.get("all_shops", []),
                       key=lambda x: x["deposit_count"], reverse=True)
    if all_shops:
        st.dataframe(
            [{"Shop": s["shop_ref"], "Số cọc": s["deposit_count"],
              "Mức": s["level"], "ASM": s["sender"]} for s in all_shops],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("(không có)")

    # ── Task 1.2: Ý tưởng ASM ────────────────────────────────────────────────
    st.subheader("💡 Ý tưởng triển khai từ ASM")
    ideas = asm_data.get("ideas", [])
    if ideas:
        st.dataframe(
            [{"ASM": i["sender"], "Shop": i["shop_ref"], "Nội dung": i["da_lam"]}
             for i in ideas],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("(không có)")

    # ── Task 1.3: Điểm nổi bật ───────────────────────────────────────────────
    st.subheader("⭐ Điểm nổi bật")
    tich_cuc = asm_data["highlights"]["tich_cuc"]
    han_che  = asm_data["highlights"]["han_che"]
    highlights = (
        [{"ASM": h["sender"], "Shop": h["shop_ref"],
          "Loại": "Tích cực", "Nội dung": h["content"]} for h in tich_cuc]
        + [{"ASM": h["sender"], "Shop": h["shop_ref"],
            "Loại": "Hạn chế", "Nội dung": h["content"]} for h in han_che]
    )
    if highlights:
        st.dataframe(highlights, use_container_width=True, hide_index=True)
    else:
        st.caption("(không có)")

    # ── Task 1.4: ASM chưa báo cáo ───────────────────────────────────────────
    missing = asm_data.get("missing_reporters")
    if missing is not None:
        st.subheader("⚠️ ASM chưa báo cáo")
        if missing:
            st.dataframe(
                [{"Tên ASM": name} for name in missing],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("Tất cả ASM đã báo cáo")
