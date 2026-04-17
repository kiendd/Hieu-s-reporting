"""
FPT Chat ASM Report — Streamlit Web UI
Chạy: streamlit run app.py
"""

import io
import sys
from datetime import date, datetime, timezone

import streamlit as st

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
        print_asm_report,
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

# ── Sidebar — cấu hình ────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Cấu hình")

    token = st.text_input(
        "Token (Bearer)",
        type="password",
        placeholder="Dán token từ DevTools vào đây",
        help="DevTools → Network → chọn request api-chat.fpt.com → Headers → Authorization: Bearer <token>",
    )
    group = st.text_input(
        "Group ID hoặc URL nhóm chat",
        placeholder="686b517a54ca42cb3c30e1df hoặc URL đầy đủ",
    )

    st.divider()
    st.subheader("📅 Khoảng thời gian")
    use_today = st.checkbox("Hôm nay", value=True)
    if not use_today:
        col1, col2 = st.columns(2)
        with col1:
            date_from_input = st.date_input("Từ ngày", value=date.today())
        with col2:
            date_to_input = st.date_input("Đến ngày", value=date.today())

    st.divider()
    st.subheader("🔧 Tuỳ chọn nâng cao")
    deposit_low  = st.number_input("Ngưỡng đặt cọc thấp (<)", value=2, min_value=0)
    deposit_high = st.number_input("Ngưỡng đặt cọc cao (>)",  value=5, min_value=0)
    deadline     = st.text_input("Deadline báo cáo (giờ VN)", value="20:00")
    skip_str     = st.text_input(
        "Bỏ qua (không check compliance)",
        placeholder="Tên Trưởng phòng, Tên Giám đốc",
        help="Cách nhau bằng dấu phẩy",
    )

# ── Main — nút chạy ───────────────────────────────────────────────────────────
run = st.button("▶ Chạy phân tích", type="primary", use_container_width=True)

if run:
    if not token:
        st.error("Vui lòng nhập Token.")
        st.stop()
    if not group:
        st.error("Vui lòng nhập Group ID hoặc URL.")
        st.stop()

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

        # ── ASM detection ─────────────────────────────────────────────────────
        asm_msgs = detect_asm_reports(messages)
        st.write(f"Phát hiện {len(asm_msgs)} báo cáo ASM")

        # ── Compliance check ──────────────────────────────────────────────────
        try:
            session = build_session(token)
            members = fetch_group_members(session, "https://api-chat.fpt.com", group_id)
            st.write(f"Thành viên nhóm: {len(members)}")
        except Exception:
            members = []
            st.write("Không lấy được danh sách thành viên — bỏ qua compliance check")

        status.update(label="Hoàn tất tải dữ liệu", state="complete")

    # ── Phân tích ─────────────────────────────────────────────────────────────
    parsed  = [parse_asm_report(m) for m in asm_msgs]
    asm_data = analyze_asm_reports(parsed, deposit_low=deposit_low, deposit_high=deposit_high)

    if members:
        asm_data["missing_reporters"] = check_asm_compliance(
            parsed, members, target_date, deadline, skip_list
        )

    if not asm_msgs:
        st.warning("Không tìm thấy báo cáo ASM nào trong khoảng thời gian này.")

    # ── Hiển thị kết quả ──────────────────────────────────────────────────────
    st.divider()

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Báo cáo ASM", len(asm_msgs))
    col_b.metric("Shop cọc thấp", len(asm_data["low_deposit_shops"]))
    col_c.metric("Shop cọc cao",  len(asm_data["high_deposit_shops"]))

    # Shop đặt cọc thấp
    if asm_data["low_deposit_shops"]:
        st.subheader("🔴 Shop đặt cọc thấp")
        for s in sorted(asm_data["low_deposit_shops"], key=lambda x: x["deposit_count"]):
            st.markdown(f"- **{s['shop_ref']}** — {s['deposit_count']} cọc *(ASM: {s['sender']})*")

    # Shop đặt cọc cao
    if asm_data["high_deposit_shops"]:
        st.subheader("🟢 Shop đặt cọc cao")
        for s in sorted(asm_data["high_deposit_shops"], key=lambda x: x["deposit_count"], reverse=True):
            st.markdown(f"- **{s['shop_ref']}** — {s['deposit_count']} cọc *(ASM: {s['sender']})*")

    # Ý tưởng
    if asm_data["ideas"]:
        st.subheader("💡 Ý tưởng triển khai từ ASM")
        for idea in asm_data["ideas"]:
            with st.expander(f"{idea['sender']} — {idea['shop_ref']}"):
                st.markdown(idea["da_lam"])

    # Điểm nổi bật
    tich_cuc = asm_data["highlights"]["tich_cuc"]
    han_che  = asm_data["highlights"]["han_che"]
    if tich_cuc or han_che:
        st.subheader("⭐ Điểm nổi bật")
        if tich_cuc:
            st.markdown("**Tích cực**")
            for h in tich_cuc:
                with st.expander(f"{h['sender']} — {h['shop_ref']}"):
                    st.markdown(h["content"])
        if han_che:
            st.markdown("**Hạn chế**")
            for h in han_che:
                with st.expander(f"{h['sender']} — {h['shop_ref']}"):
                    st.markdown(h["content"])

    # ASM chưa báo cáo
    missing = asm_data.get("missing_reporters")
    if missing is not None:
        st.subheader("⚠️ ASM chưa báo cáo")
        if missing:
            for name in missing:
                st.markdown(f"- {name}")
        else:
            st.success("Tất cả ASM đã báo cáo")

    # ── Xuất Excel ────────────────────────────────────────────────────────────
    st.divider()
    excel_buf = io.BytesIO()
    write_asm_excel(asm_data, excel_buf)
    excel_buf.seek(0)

    filename = f"asm_report_{target_date}.xlsx"
    st.download_button(
        label="⬇️ Tải báo cáo Excel",
        data=excel_buf,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
