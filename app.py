"""
FPT Chat ASM Report — Streamlit Web UI
Chạy: streamlit run app.py
"""

import io
import json
import os
from datetime import date, datetime, time, timedelta, timezone

import pandas as pd
import streamlit as st
from streamlit_javascript import st_javascript

# ── localStorage helpers ──────────────────────────────────────────────────────

def _ls_get(key: str) -> str:
    """Read from localStorage. Returns '' if key missing or JS not yet ready."""
    val = st_javascript(f"localStorage.getItem({json.dumps(key)}) || ''")
    return val if isinstance(val, str) else ""

def _ls_get_nullable(key: str):
    """Returns None on first render (JS not ready); '' if key missing; str if key exists."""
    val = st_javascript(f"localStorage.getItem({json.dumps(key)}) ?? ''")
    return val if isinstance(val, str) else None

def _ls_set(key: str, value: str) -> None:
    st_javascript(f"localStorage.setItem({json.dumps(key)}, {json.dumps(value)}); 'ok'")

# ── Config file (local only, token không bao giờ ghi file) ────────────────────

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def _load_config() -> dict:
    if os.path.isfile(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg.pop("token", None)
            return cfg
        except Exception:
            pass
    return {}

# ── Group Library helpers ─────────────────────────────────────────────────────

_LIB_KEY = "fpt_groups_library"
_LIB_DEFAULTS = {"deposit_low": 2, "deposit_high": 5, "deadline": "20:00", "skip": ""}

def _lib_save(lib: list) -> None:
    _ls_set(_LIB_KEY, json.dumps(lib))

def _make_entry(url: str, label: str = "", selected: bool = True, config: dict | None = None) -> dict:
    from fpt_chat_stats import extract_group_id as _eid
    gid = _eid(url)
    return {
        "url":      url,
        "label":    label or (gid[-8:] if len(gid) >= 8 else gid),
        "selected": selected,
        "config":   {**_LIB_DEFAULTS, **(config or {})},
    }

def _migrate_legacy(groups_list: list, group_configs: dict) -> list:
    """Migrate fpt_groups (string array) + fpt_group_configs → library entries."""
    from fpt_chat_stats import extract_group_id as _eid
    lib = []
    for url in groups_list:
        gid = _eid(url)
        cfg = group_configs.get(gid, {})
        merged_cfg = {**_LIB_DEFAULTS, **cfg}
        lib.append({
            "url":      url,
            "label":    gid[-8:] if len(gid) >= 8 else gid,
            "selected": True,
            "config":   merged_cfg,
        })
    return lib


# ── Import core logic ─────────────────────────────────────────────────────────

try:
    from fpt_chat_stats import (
        analyze_asm_reports,
        analyze_multiday,
        analyze_weekly,
        build_session,
        check_asm_compliance,
        check_late_reporters,
        extract_all_reports,
        extract_group_id,
        fetch_all_messages,
        fetch_group_info,
        fetch_group_members,
        filter_by_date,
        parse_date_arg,
        to_vn_str,
        write_asm_excel,
        write_weekly_excel,
    )
    import llm_extractor
except ImportError as e:
    st.error(f"Không tìm thấy fpt_chat_stats.py: {e}")
    st.stop()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="FPT Chat ASM Report",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
div[data-testid="stElementContainer"]:has(iframe[data-testid="stCustomComponentV1"]) {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────

for _k, _v in [("library", []), ("ls_loaded", False), ("dialog_idx", None), ("needs_save", False)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Load library from localStorage (retry until JS resolves) ─────────────────

if not st.session_state.ls_loaded:
    _raw_lib = _ls_get_nullable(_LIB_KEY)
    if _raw_lib is not None:
        # JS has resolved — parse or migrate
        if _raw_lib:
            try:
                st.session_state.library = json.loads(_raw_lib)
            except Exception:
                st.session_state.library = []
        else:
            # No library yet — try legacy migration
            _cfg_file    = _load_config()
            _raw_groups  = _ls_get_nullable("fpt_groups") or ""
            _raw_cfgs    = _ls_get_nullable("fpt_group_configs") or ""
            _groups_list: list = []
            _group_cfgs:  dict = {}
            if _raw_groups:
                try:
                    _groups_list = json.loads(_raw_groups)
                except Exception:
                    pass
            elif isinstance(_cfg_file.get("groups"), list):
                _groups_list = _cfg_file["groups"]
            elif _cfg_file.get("group"):
                _groups_list = [_cfg_file["group"]]
            if _raw_cfgs:
                try:
                    _group_cfgs = json.loads(_raw_cfgs)
                except Exception:
                    pass
            if _groups_list:
                st.session_state.library = _migrate_legacy(_groups_list, _group_cfgs)
                _lib_save(st.session_state.library)
            else:
                st.session_state.library = []
        st.session_state.ls_loaded = True

# ── Token ─────────────────────────────────────────────────────────────────────

_saved_token = _ls_get("fpt_token")
_saved_llm_key       = _ls_get("fpt_llm_api_key")
_saved_llm_base_url  = _ls_get("fpt_llm_base_url") or "https://api.openai.com/v1"
_saved_llm_model     = _ls_get("fpt_llm_model")    or "gpt-5.4-mini"
_raw_structout = (_ls_get("fpt_llm_structured_outputs") or "").strip().lower()
_saved_llm_structout = True if _raw_structout == "" else _raw_structout in ("1", "true", "yes", "on")

# ── Page header ───────────────────────────────────────────────────────────────

_title_col, _help_col = st.columns([6, 1])
_title_col.title("📊 FPT Chat ASM Report")
_help_col.markdown(
    "<div style='padding-top:1.5rem'>"
    "<a href='https://github.com/kiendd/Hieu-s-reporting/blob/main/docs/huong-dan-su-dung.md'"
    " target='_blank'>📖 Hướng dẫn</a></div>",
    unsafe_allow_html=True,
)

token = st.text_input(
    "Token (Bearer)",
    value=_saved_token,
    type="password",
    placeholder="Dán token từ DevTools vào đây",
    help="DevTools → Network → chọn request api-chat.fpt.com → Headers → Authorization: Bearer <token>",
)

# ── Group Library ─────────────────────────────────────────────────────────────

@st.dialog("Thêm / Sửa nhóm")
def _group_dialog(idx: int) -> None:
    st.session_state.dialog_idx = None  # clear so X-close also resets state
    prefill     = st.session_state.library[idx] if idx >= 0 else None
    prefill_cfg = prefill["config"] if prefill else _LIB_DEFAULTS

    f_url = st.text_input(
        "Group ID hoặc URL nhóm chat *",
        value=prefill["url"] if prefill else "",
        placeholder="686b517a54ca42cb3c30e1df hoặc URL đầy đủ",
    )
    f_label = st.text_input(
        "Tên hiển thị (tab label)",
        value=prefill["label"] if prefill else "",
        placeholder="Nhóm miền Bắc",
    )
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        f_dep_low  = st.number_input("Cọc thấp (<)", value=int(prefill_cfg["deposit_low"]),  min_value=0)
    with fc2:
        f_dep_high = st.number_input("Cọc cao (>)",  value=int(prefill_cfg["deposit_high"]), min_value=0)
    with fc3:
        f_deadline = st.text_input("Deadline (giờ VN)", value=prefill_cfg["deadline"])
    f_skip = st.text_input(
        "Bỏ qua khỏi compliance check",
        value=prefill_cfg["skip"],
        placeholder="Tên Trưởng phòng, Tên Giám đốc",
        help="Cách nhau bằng dấu phẩy",
    )

    c_save, c_cancel = st.columns(2)
    if c_save.button("💾 Lưu", type="primary", use_container_width=True):
        if not f_url.strip():
            st.error("Group ID hoặc URL không được để trống.")
        else:
            gid   = extract_group_id(f_url.strip())
            label = f_label.strip() or (gid[-8:] if len(gid) >= 8 else gid)
            entry = {
                "url":      f_url.strip(),
                "label":    label,
                "selected": True if idx < 0 else st.session_state.library[idx]["selected"],
                "config": {
                    "deposit_low":  int(f_dep_low),
                    "deposit_high": int(f_dep_high),
                    "deadline":     f_deadline,
                    "skip":         f_skip,
                },
            }
            if idx >= 0:
                st.session_state.library[idx] = entry
            else:
                st.session_state.library.append(entry)
            st.session_state.needs_save = True
            st.rerun()

    if c_cancel.button("✕ Huỷ", use_container_width=True):
        st.rerun()


hdr_col, add_col = st.columns([5, 1])
with hdr_col:
    st.markdown("**📋 Nhóm chat**")
with add_col:
    if st.button("+ Thêm nhóm", use_container_width=True):
        st.session_state.dialog_idx = -1
        st.rerun()

if st.session_state.dialog_idx is not None:
    _group_dialog(st.session_state.dialog_idx)

lib = st.session_state.library
if not lib:
    st.caption("Chưa có nhóm nào. Nhấn **+ Thêm nhóm** để bắt đầu.")
else:
    for i, entry in enumerate(lib):
        gid      = extract_group_id(entry["url"])
        short_id = gid[-8:] if len(gid) >= 8 else gid
        cfg      = entry["config"]
        cfg_summary = (
            f"cọc {cfg['deposit_low']}–{cfg['deposit_high']} · {cfg['deadline']}"
            + (f" · bỏ qua: {cfg['skip']}" if cfg["skip"] else "")
        )

        c_chk, c_info, c_edit, c_del = st.columns([0.5, 5.5, 0.7, 0.7])
        with c_chk:
            new_sel = st.checkbox(
                "sel",
                value=entry["selected"],
                key=f"sel_{i}",
                label_visibility="collapsed",
            )
            if new_sel != entry["selected"]:
                st.session_state.library[i]["selected"] = new_sel
                _lib_save(st.session_state.library)
        with c_info:
            st.markdown(
                f"**{entry['label']}** &nbsp;`{short_id}`&nbsp; "
                f"<span style='color:gray;font-size:0.85em'>{cfg_summary}</span>",
                unsafe_allow_html=True,
            )
        with c_edit:
            if st.button("✏", key=f"edit_{i}", use_container_width=True, help="Sửa cấu hình"):
                st.session_state.dialog_idx = i
                st.rerun()
        with c_del:
            if st.button("🗑", key=f"del_{i}", use_container_width=True, help="Xóa nhóm"):
                st.session_state.library.pop(i)
                _lib_save(st.session_state.library)
                st.rerun()

# Flush deferred localStorage write (must happen in main body, not inside @st.dialog)
if st.session_state.needs_save:
    _lib_save(st.session_state.library)
    st.session_state.needs_save = False

# ── Date range ────────────────────────────────────────────────────────────────

st.divider()
date_mode = st.radio(
    "Khoảng thời gian",
    ["Hôm nay", "Chọn khoảng ngày", "Báo cáo tuần"],
    horizontal=True,
    label_visibility="collapsed",
)
use_today = date_mode == "Hôm nay"
use_weekly = date_mode == "Báo cáo tuần"

if use_weekly:
    weekly_date_input = st.date_input("Ngày báo cáo tuần", value=date.today())
elif not use_today:
    col1, col2 = st.columns(2)
    with col1:
        date_from_input = st.date_input("Từ ngày", value=date.today())
    with col2:
        date_to_input = st.date_input("Đến ngày", value=date.today())

# ── Run button ────────────────────────────────────────────────────────────────

selected_groups = [e for e in st.session_state.library if e.get("selected")]
n_sel = len(selected_groups)
run = st.button(
    f"▶ Chạy {n_sel} nhóm đã chọn" if n_sel else "▶ Chạy phân tích",
    type="primary",
    use_container_width=True,
)

def _render_shop_vt_sections(asm_data: dict, d1_shop_map: dict | None = None) -> None:
    """Render the shop-deposit chart + shop-bucket tables + ideas + highlights.

    Shared by daily (_render_result) and weekly (_render_weekly_result).
    d1_shop_map is daily-only (D-1 delta comparison); None for weekly.
    """
    import pandas as pd  # local import keeps helper self-contained

    # Chart: cọc theo shop
    all_shops_raw = sorted(asm_data.get("all_shops", []),
                           key=lambda x: x["deposit_count"], reverse=True)
    if all_shops_raw:
        labels = [s["shop_ref"][:28] for s in all_shops_raw]
        chart_dict = {"Hôm nay": [s["deposit_count"] for s in all_shops_raw]}
        if d1_shop_map is not None:
            chart_dict["D-1"] = [d1_shop_map.get(s["shop_ref"], 0) for s in all_shops_raw]
        st.bar_chart(pd.DataFrame(chart_dict, index=labels), use_container_width=True)

    no_dep = asm_data.get("no_deposit_shops", [])
    if no_dep:
        st.subheader("🚫 Shop báo cáo 0 cọc")
        st.dataframe(
            [{"ASM": s["sender"], "Shop": s["shop_ref"]} for s in no_dep],
            use_container_width=True, hide_index=True,
        )

    low_shops = asm_data.get("low_deposit_shops", [])
    if low_shops:
        st.subheader("📉 Shop cọc thấp")
        def _low_row(s):
            d1 = d1_shop_map.get(s["shop_ref"], "—") if d1_shop_map is not None else None
            row = {"ASM": s["sender"], "Shop": s["shop_ref"], "Số cọc": s["deposit_count"]}
            if d1 is not None:
                row["Cọc D-1"] = d1
            return row
        st.dataframe(
            [_low_row(s) for s in sorted(low_shops, key=lambda x: x["deposit_count"])],
            use_container_width=True, hide_index=True,
        )

    high_shops = asm_data.get("high_deposit_shops", [])
    if high_shops:
        st.subheader("🏆 Nhân viên phát sinh cọc tốt")
        def _high_row(s):
            d1 = d1_shop_map.get(s["shop_ref"], "—") if d1_shop_map is not None else None
            row = {"ASM": s["sender"], "Shop": s["shop_ref"], "Số cọc": s["deposit_count"]}
            if d1 is not None:
                row["Cọc D-1"] = d1
            return row
        st.dataframe(
            [_high_row(s) for s in sorted(high_shops, key=lambda x: x["deposit_count"], reverse=True)],
            use_container_width=True, hide_index=True,
        )

    st.subheader("🏪 Shop đặt cọc")
    all_shops = sorted(asm_data.get("all_shops", []),
                       key=lambda x: x["deposit_count"], reverse=True)
    if all_shops:
        def _shop_row(s):
            d1 = d1_shop_map.get(s["shop_ref"], "—") if d1_shop_map is not None else None
            row = {"Shop": s["shop_ref"], "Số cọc": s["deposit_count"]}
            if d1 is not None:
                row["Cọc D-1"] = d1
            row["Mức"] = s["level"]
            row["ASM"] = s["sender"]
            return row
        st.dataframe(
            [_shop_row(s) for s in all_shops],
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("(không có)")

    st.subheader("💡 Ý tưởng triển khai từ ASM")
    ideas = asm_data.get("ideas", [])
    if ideas:
        st.table(
            [{"ASM": i["sender"], "Shop": i["shop_ref"], "Nội dung": i["da_lam"]}
             for i in ideas]
        )
    else:
        st.caption("(không có)")

    st.subheader("⭐ Điểm nổi bật")
    tich_cuc = asm_data["highlights"]["tich_cuc"]
    han_che  = asm_data["highlights"]["han_che"]
    highlights = (
        [{"ASM": h["sender"], "Shop": h["shop_ref"], "Loại": "Tích cực", "Nội dung": h["content"]}
         for h in tich_cuc]
        + [{"ASM": h["sender"], "Shop": h["shop_ref"], "Loại": "Hạn chế", "Nội dung": h["content"]}
           for h in han_che]
    )
    if highlights:
        st.table(highlights)
    else:
        st.caption("(không có)")


def _render_tttc_sections(tttc_data: dict) -> None:
    """Render TTTC aggregate metrics + top/bottom tables + ideas + highlights."""

    def _fmt_pct(v): return f"{v:.1f}%" if v is not None else "—"
    def _fmt_vnd(v): return f"{v:,}" if v is not None else "—"

    st.subheader("🏥 TTTC — chỉ số trung tâm")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trung tâm báo cáo", tttc_data["total_reports"])
    c2.metric("TB bill TB",        _fmt_vnd(tttc_data["avg_tb_bill"]))
    c3.metric("%HT TB",            _fmt_pct(tttc_data["avg_revenue_pct"]))
    c4.metric("%HOT TB",           _fmt_pct(tttc_data["avg_hot_pct"]))

    def _center_row(c: dict) -> dict:
        return {
            "Trung tâm":     c.get("venue") or "—",
            "%HT":           _fmt_pct(c.get("revenue_pct")),
            "%HOT":          _fmt_pct(c.get("hot_pct")),
            "TB bill":       _fmt_vnd(c.get("tb_bill")),
            "Tỉ trọng HOT":  _fmt_pct(c.get("hot_ratio")),
            "Lượt KH mua":   c.get("customer_count") if c.get("customer_count") is not None else "—",
            "ASM":           c.get("sender") or "—",
        }

    top = tttc_data.get("top_centers", [])
    if top:
        st.subheader("🏆 Top trung tâm (theo %HT)")
        st.dataframe([_center_row(c) for c in top],
                     use_container_width=True, hide_index=True)

    bottom = tttc_data.get("bottom_centers", [])
    if bottom:
        st.subheader("⚠️ Trung tâm cần chú ý")
        st.dataframe([_center_row(c) for c in bottom],
                     use_container_width=True, hide_index=True)

    ideas = tttc_data.get("ideas", [])
    if ideas:
        st.subheader("💡 Ý tưởng từ TTTC")
        st.table([{"ASM": i["sender"], "Trung tâm": i["venue"], "Nội dung": i["da_lam"]}
                  for i in ideas])

    hl = tttc_data.get("highlights", {})
    tich_cuc = hl.get("tich_cuc", [])
    han_che  = hl.get("han_che",  [])
    if tich_cuc or han_che:
        st.subheader("⭐ Điểm nổi bật (TTTC)")
        rows = (
            [{"ASM": h["sender"], "Trung tâm": h["venue"],
              "Loại": "Tích cực", "Nội dung": h["content"]} for h in tich_cuc]
            + [{"ASM": h["sender"], "Trung tâm": h["venue"],
                "Loại": "Hạn chế", "Nội dung": h["content"]} for h in han_che]
        )
        st.table(rows)


def _render_result(r: dict) -> None:
    if r.get("error"):
        st.error(f"Lỗi: {r['error']}")
        return

    asm_data    = r["asm_data"]
    asm_msgs    = r["asm_msgs"]
    excel_buf   = r["excel_buf"]
    target_date = r["target_date"]
    group_id    = r["group_id"]
    short_id    = group_id[-8:] if len(group_id) >= 8 else group_id

    col_hdr, col_dl = st.columns([4, 1])
    with col_hdr:
        st.subheader("Kết quả phân tích")
    with col_dl:
        st.download_button(
            label="⬇️ Tải Excel",
            data=excel_buf,
            file_name=f"asm_report_{short_id}_{target_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    asm_data_d1    = r.get("asm_data_d1")
    late_reporters = asm_data.get("late_reporters", [])
    unreported_now = asm_data.get("unreported_now")

    _d1_deps  = asm_data_d1["total_deposits"] if asm_data_d1 else None
    _d1_tiem  = asm_data_d1["total_ra_tiem"]  if asm_data_d1 else None
    d1_shop_map = (
        {s["shop_ref"]: s["deposit_count"] for s in asm_data_d1["all_shops"]}
        if asm_data_d1 else None
    )

    _unparseable = r.get("unparseable") or []
    if _unparseable:
        with st.expander(f"⚠️ Không parse được ({len(_unparseable)})", expanded=False):
            for u in _unparseable:
                st.caption(f"**{u.get('sender','?')}** — {u.get('sent_at','')}")
                st.code(u.get("parse_error") or "", language=None)

    col_a, col_b, col_c, col_d, col_e, col_f = st.columns(6)
    col_a.metric("Báo cáo ASM",   len(asm_msgs))
    col_b.metric("Tổng cọc",      asm_data["total_deposits"],
                 delta=None if _d1_deps is None else asm_data["total_deposits"] - _d1_deps)
    col_c.metric("Tổng ra tiêm",  asm_data["total_ra_tiem"],
                 delta=None if _d1_tiem is None else asm_data["total_ra_tiem"] - _d1_tiem)
    col_d.metric("Shop cọc thấp", len(asm_data["low_deposit_shops"]))
    col_e.metric("Báo cáo muộn",  len(late_reporters))
    col_f.metric("Chưa báo cáo",  len(unreported_now) if unreported_now is not None else "—")

    if not asm_msgs:
        st.warning("Không tìm thấy báo cáo ASM nào trong khoảng thời gian này.")

    # ── Multi-day analytics (chỉ khi range > 1 ngày) ──────────────────────
    multiday_data = r.get("multiday_data")
    if multiday_data:
        total_days = multiday_data["total_days"]

        # 1. Xu hướng theo ngày
        st.subheader("📈 Xu hướng theo ngày")
        daily = multiday_data["daily_summary"]
        if daily:
            _df_daily = pd.DataFrame(daily).set_index("date")[["total_deposits", "total_ra_tiem"]]
            _df_daily.columns = ["Tổng cọc", "Tổng ra tiêm"]
            st.bar_chart(_df_daily, use_container_width=True)

        # 2. Tổng kết ASM
        st.subheader("👤 Tổng kết ASM")
        asm_sum = multiday_data["asm_summary"]
        if asm_sum:
            st.dataframe(
                [{
                    "Nhân viên":       a["sender"],
                    "Ngày báo/Tổng":   f"{a['report_days']}/{total_days}",
                    "Tỉ lệ (%)":       a["report_rate"],
                    "Chuỗi dài nhất":  a["longest_streak"],
                    "Vắng dài nhất":   a["longest_gap"],
                    "Tổng cọc":        a["total_deposits"],
                    "TB cọc/ngày":     a["avg_deposits_per_day"],
                } for a in asm_sum],
                use_container_width=True, hide_index=True,
            )

        # 3. Ngày thiếu báo cáo
        missing_days = [d for d in multiday_data["missing_by_day"] if d["missing_count"] > 0]
        if missing_days:
            st.subheader("📅 Ngày thiếu báo cáo")
            st.dataframe(
                [{
                    "Ngày":       d["date"],
                    "Số ASM vắng": d["missing_count"],
                    "Tên ASM vắng": ", ".join(d["missing_names"]),
                } for d in missing_days],
                use_container_width=True, hide_index=True,
            )

        # 4. Tổng kết shop
        shop_sum = multiday_data["shop_summary"]
        if shop_sum:
            st.subheader("🏪 Tổng kết shop (nhiều ngày)")
            st.dataframe(
                [{
                    "Shop":            s["shop_ref"],
                    "ASM":             s["sender"],
                    "Tổng cọc":        s["total_deposits"],
                    "Số ngày báo cáo": s["report_days"],
                    "TB cọc/ngày":     s["avg_deposits"],
                } for s in shop_sum],
                use_container_width=True, hide_index=True,
            )
        st.divider()

    if unreported_now is not None:
        st.subheader("⏳ Chưa báo cáo đến hiện tại")
        if unreported_now:
            st.dataframe(
                [{"Tên thành viên": name} for name in unreported_now],
                use_container_width=True, hide_index=True,
            )
        else:
            st.success("Tất cả đã báo cáo")

    if late_reporters:
        st.subheader("🕐 ASM báo cáo muộn")
        st.dataframe(
            [{"ASM": lr["sender"], "Giờ gửi": lr["sent_at_vn"]} for lr in late_reporters],
            use_container_width=True, hide_index=True,
        )

    _render_shop_vt_sections(asm_data, d1_shop_map=d1_shop_map)

    missing = asm_data.get("missing_reporters")
    if missing is not None and r.get("past_deadline"):
        st.subheader("⚠️ ASM chưa báo cáo (sau deadline)")
        if missing:
            st.dataframe(
                [{"Tên ASM": name} for name in missing],
                use_container_width=True, hide_index=True,
            )
        else:
            st.success("Tất cả ASM đã báo cáo đúng hạn")

    # ── Chi tiết theo shop / nhân viên ─────────────────────────────────────
    parsed_reports = r.get("parsed_reports", [])
    if parsed_reports:
        st.subheader("🔍 Xem chi tiết")
        det_col1, det_col2 = st.columns(2)

        def _detail_card(report, d1_val):
            st.markdown(f"**Số cọc:** {report['deposit_count']}  |  **Cọc D-1:** {d1_val}  |  **Ra tiêm:** {report.get('ra_tiem_count', '—')}")
            st.markdown(f"**Giờ gửi:** {to_vn_str(report['sent_at'])}")
            if report.get("tich_cuc"):
                st.markdown("**Tích cực:**")
                st.text(report["tich_cuc"])
            if report.get("van_de"):
                st.markdown("**Vấn đề:**")
                st.text(report["van_de"])
            if report.get("da_lam"):
                st.markdown("**Đã làm:**")
                st.text(report["da_lam"])

        with det_col1:
            shop_list = [p["shop_ref"] for p in parsed_reports if p.get("shop_ref")]
            sel_shop = st.selectbox("Theo shop", [None] + shop_list,
                                    format_func=lambda x: "— chọn shop —" if x is None else x,
                                    key=f"sel_shop_{r['group_id']}")
            if sel_shop:
                report = next((p for p in parsed_reports if p.get("shop_ref") == sel_shop), None)
                if report:
                    st.markdown(f"**ASM:** {report['sender']}")
                    _detail_card(report, d1_shop_map.get(sel_shop, "—") if d1_shop_map else "—")

        with det_col2:
            asm_list = sorted({p["sender"] for p in parsed_reports if p.get("sender")})
            sel_asm = st.selectbox("Theo nhân viên", [None] + asm_list,
                                   format_func=lambda x: "— chọn nhân viên —" if x is None else x,
                                   key=f"sel_asm_{r['group_id']}")
            if sel_asm:
                for report in [p for p in parsed_reports if p.get("sender") == sel_asm]:
                    shop = report.get("shop_ref", "?")
                    st.markdown(f"**Shop:** {shop}")
                    _detail_card(report, d1_shop_map.get(shop, "—") if d1_shop_map else "—")
                    st.divider()


def _render_weekly_result(r: dict) -> None:
    if r.get("error"):
        st.error(f"Lỗi: {r['error']}")
        return

    wd = r["weekly_data"]
    target_date = r["target_date"]
    group_id = r["group_id"]
    short_id = group_id[-8:] if len(group_id) >= 8 else group_id

    reports  = wd["reports"]
    late     = wd["late_list"]
    missing  = wd["missing_list"]
    total_members = len(reports) + len(missing)
    rate = (len(reports) / total_members * 100.0) if total_members else 0.0

    # Avatar lookup keyed by displayName. Try a few common field names since the
    # FPT Chat members endpoint shape isn't fully documented.
    def _avatar_of(member: dict) -> str:
        for key in ("avatarUrl", "avatar", "imageUrl", "photoUrl"):
            v = member.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
        return ""

    avatar_map: dict[str, str] = {
        (m.get("displayName") or "").strip(): _avatar_of(m)
        for m in (r.get("members") or [])
        if (m.get("displayName") or "").strip()
    }

    # ── 1. Compliance header ──────────────────────────────────────────────────
    col_hdr, col_dl = st.columns([4, 1])
    with col_hdr:
        st.subheader(f"Báo cáo tuần — {target_date}")
    with col_dl:
        st.download_button(
            label="⬇️ Tải Excel",
            data=r["excel_buf"],
            file_name=f"bao_cao_tuan_{short_id}_{target_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"dl_weekly_{group_id}",
        )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Đã báo cáo", len(reports), delta=f"{len(reports)}/{total_members}" if total_members else None, delta_color="off")
    m2.metric("Muộn", len(late))
    m3.metric("Chưa báo cáo", len(missing))
    m4.metric("Tỉ lệ báo cáo", f"{rate:.1f}%")

    st.progress(
        rate / 100.0 if total_members else 0.0,
        text=f"{len(reports)}/{total_members} ASM đã gửi (kèm muộn)",
    )

    # ── 2. Action items ───────────────────────────────────────────────────────
    late_map = {rr["sender"]: rr["sent_at_vn"] for rr in reports if rr["is_late"]}
    col_missing, col_late = st.columns(2)
    with col_missing:
        with st.container(border=True):
            st.markdown(f"**🔴 Chưa báo cáo ({len(missing)})**")
            if missing:
                st.code("\n".join(f"🔴 {n}" for n in missing), language=None)
            else:
                st.caption("Không có — toàn bộ ASM đã báo cáo.")
    with col_late:
        with st.container(border=True):
            st.markdown(f"**🟡 Muộn ({len(late)})**")
            if late:
                st.code(
                    "\n".join(f"🟡 {n} ({late_map.get(n, '?')})" for n in late),
                    language=None,
                )
            else:
                st.caption("Không có — tất cả ASM đã báo cáo gửi đúng giờ.")

    # ── 2b. Shop VT + TTTC aggregate sections ────────────────────────────────
    asm_data_w  = wd.get("asm_data")
    tttc_data_w = wd.get("tttc_data")

    if asm_data_w:
        st.markdown("### 🏪 Shop VT")
        _render_shop_vt_sections(asm_data_w, d1_shop_map=None)

    if tttc_data_w:
        _render_tttc_sections(tttc_data_w)

    # ── 3. Nội dung báo cáo (search + tabs + expanders) ───────────────────────
    st.divider()
    st.markdown("**Nội dung báo cáo**")
    query = st.text_input(
        "Tìm ASM…",
        key=f"weekly_search_{group_id}",
        placeholder="Nhập tên ASM để lọc",
        label_visibility="collapsed",
    )
    q = (query or "").strip().lower()

    def _match(rr: dict) -> bool:
        return not q or q in rr["sender"].lower()

    filtered_all      = [rr for rr in reports if _match(rr)]
    filtered_on_time  = [rr for rr in filtered_all if not rr["is_late"]]
    filtered_late     = [rr for rr in filtered_all if rr["is_late"]]

    def _render_list(items: list) -> None:
        if not items:
            st.info("Không có báo cáo khớp.")
            return
        for rr in items:
            badge  = "🟡" if rr["is_late"] else "🟢"
            status = "Muộn" if rr["is_late"] else "Đúng giờ"
            extra  = f" · (+{rr['extra_count']} tin nhắn khác)" if rr["extra_count"] else ""
            header = f"{badge} {rr['sender']} — {rr['sent_at_vn']} ({status}){extra}"
            url = avatar_map.get(rr["sender"], "")
            col_av, col_body = st.columns([1, 12], vertical_alignment="center")
            with col_av:
                if url:
                    st.image(url, width=40)
                else:
                    st.markdown(
                        f"<div style='width:40px;height:40px;border-radius:50%;"
                        f"background:#e3e3e3;display:flex;align-items:center;"
                        f"justify-content:center;font-weight:600;color:#555;'>"
                        f"{(rr['sender'][:1] or '?').upper()}</div>",
                        unsafe_allow_html=True,
                    )
            with col_body:
                with st.expander(header, expanded=False):
                    st.text(rr["text"])

    tab_all, tab_ontime, tab_late = st.tabs([
        f"Tất cả ({len(filtered_all)})",
        f"Đã báo cáo đúng giờ ({len(filtered_on_time)})",
        f"Muộn ({len(filtered_late)})",
    ])
    with tab_all:
        _render_list(filtered_all)
    with tab_ontime:
        _render_list(filtered_on_time)
    with tab_late:
        _render_list(filtered_late)


with st.sidebar:
    st.subheader("Cấu hình LLM")
    _llm_base_url = st.text_input(
        "Base URL", value=_saved_llm_base_url,
        help="OpenAI-compatible endpoint",
    )
    _llm_model = st.text_input("Model", value=_saved_llm_model)
    _llm_api_key = st.text_input(
        "API key", value=_saved_llm_key, type="password",
        help="Lưu trong localStorage trình duyệt — không ghi ra config.json",
    )
    _llm_structout = st.checkbox(
        "Structured outputs",
        value=_saved_llm_structout,
        help="Dùng response_format=json_schema (strict). Chỉ bật khi "
             "provider hỗ trợ (OpenAI gpt-4o-2024-08-06+ / 4.1+ / 5+).",
    )
    if _llm_api_key:
        _ls_set("fpt_llm_api_key", _llm_api_key)
    if _llm_base_url != _saved_llm_base_url:
        _ls_set("fpt_llm_base_url", _llm_base_url)
    if _llm_model != _saved_llm_model:
        _ls_set("fpt_llm_model", _llm_model)
    if _llm_structout != _saved_llm_structout:
        _ls_set("fpt_llm_structured_outputs", "1" if _llm_structout else "0")
    llm_extractor.configure(
        api_key=_llm_api_key or None,
        base_url=_llm_base_url or None,
        model=_llm_model or None,
        structured_outputs=_llm_structout,
    )
    _stats = llm_extractor.get_stats()
    if sum(_stats.values()) > 0:
        st.caption(llm_extractor.format_stats())

if run:
    if not token:
        st.error("Vui lòng nhập Token.")
        st.stop()
    if not _llm_api_key:
        st.error("Vui lòng nhập API key LLM trong sidebar.")
        st.stop()
    if not selected_groups:
        st.error("Vui lòng chọn ít nhất một nhóm.")
        st.stop()

    _ls_set("fpt_token", token)

    if not use_weekly:
        # clear any stale weekly results when running daily/multi-day
        st.session_state["_weekly_results"] = []

    # ── Weekly mode: dispatch cho từng group, render trực tiếp, return sớm ──
    if use_weekly:
        VN_OFFSET = 7 * 3600
        weekly_target_str = weekly_date_input.strftime("%Y-%m-%d")
        weekly_results = []
        for entry in selected_groups:
            group_id = extract_group_id(entry["url"])
            cfg = entry["config"]
            with st.status(f"Đang xử lý {entry['label']}…", expanded=False) as status:
                try:
                    session = build_session(token)
                    group_info = fetch_group_info(session, "https://api-chat.fpt.com", group_id)
                    tab_label = entry["label"]
                    if tab_label == group_id[-8:]:
                        api_name = group_info.get("name") or group_info.get("title") or ""
                        if api_name:
                            tab_label = api_name

                    # Half-open VN-day window [target 00:00+07, target+1 00:00+07)
                    vn_start_utc = datetime.combine(
                        weekly_date_input, time(0, 0), tzinfo=timezone.utc
                    ) - timedelta(hours=7)
                    vn_end_utc = vn_start_utc + timedelta(days=1)

                    messages = fetch_all_messages(
                        token=token, group_id=group_id, date_from=vn_start_utc,
                    )
                    messages = filter_by_date(
                        messages, vn_start_utc, vn_end_utc - timedelta(microseconds=1),
                    )

                    members = fetch_group_members(session, "https://api-chat.fpt.com", group_id)
                    if not members:
                        raise RuntimeError(
                            "fetch_group_members trả rỗng hoặc lỗi — không thể kiểm tra compliance."
                        )

                    weekly_data = analyze_weekly(
                        messages, members, weekly_target_str, deadline=cfg["deadline"],
                    )

                    excel_buf = io.BytesIO()
                    write_weekly_excel(weekly_data, members, excel_buf)
                    excel_buf.seek(0)

                    status.update(label=f"✓ {tab_label}", state="complete")
                    weekly_results.append({
                        "tab_label": tab_label,
                        "group_id": group_id,
                        "target_date": weekly_target_str,
                        "weekly_data": weekly_data,
                        "members": members,
                        "excel_buf": excel_buf,
                        "error": None,
                    })
                except Exception as exc:
                    status.update(label=f"✗ {entry['label']}", state="error")
                    weekly_results.append({
                        "tab_label": entry["label"],
                        "group_id": group_id,
                        "error": str(exc),
                    })

        st.session_state["_weekly_results"] = weekly_results
        st.session_state["_results"] = []  # clear daily results to avoid mixing views
        st.rerun()  # trigger rerun so the render block below picks up the new results

    # Tính date range
    import time as _time
    VN_OFFSET = 7 * 3600
    _vn_now = datetime.fromtimestamp(_time.time() + VN_OFFSET, tz=timezone.utc)
    if use_today:
        _today_str = _vn_now.strftime("%Y-%m-%d")
        date_from_str = date_to_str = target_date = _today_str
    else:
        date_from_str = date_from_input.strftime("%Y-%m-%d")
        date_to_str   = date_to_input.strftime("%Y-%m-%d")
        target_date   = date_to_str

    date_from = parse_date_arg(date_from_str, end_of_day=False)
    date_to   = parse_date_arg(date_to_str,   end_of_day=True)

    # D-1 chỉ khi single-day
    _is_single_day = date_from_str == date_to_str
    if _is_single_day:
        _d1_str   = (datetime.strptime(date_from_str, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        _d1_from  = parse_date_arg(_d1_str, end_of_day=False)
        _d1_to    = parse_date_arg(_d1_str, end_of_day=True)
    else:
        _d1_str = _d1_from = _d1_to = None

    # Thời điểm chạy báo cáo (dùng cho "chưa báo cáo đến hiện tại")
    _now_hhmm = _vn_now.strftime("%H:%M")

    # ── Fetch & analyze từng nhóm ─────────────────────────────────────────────

    results = []
    _label_updated = False
    for entry in selected_groups:
        group_id = extract_group_id(entry["url"])
        short_id = group_id[-8:] if len(group_id) >= 8 else group_id
        cfg      = entry["config"]
        skip_list = [s.strip() for s in cfg["skip"].split(",") if s.strip()]

        with st.status(f"Đang xử lý {entry['label']}…", expanded=False) as status:
            try:
                session = build_session(token)

                # Dùng label đã lưu; chỉ ghi đè nếu label vẫn là short_id placeholder
                group_info = fetch_group_info(session, "https://api-chat.fpt.com", group_id)
                tab_label  = entry["label"]
                if tab_label == short_id:
                    api_name = group_info.get("name") or group_info.get("title") or ""
                    if api_name:
                        tab_label = api_name

                messages = fetch_all_messages(token=token, group_id=group_id, date_from=date_from)
                messages = filter_by_date(messages, date_from, date_to)

                try:
                    members = fetch_group_members(session, "https://api-chat.fpt.com", group_id)
                except Exception:
                    members = []

                parsed   = extract_all_reports(messages)
                asm_data = analyze_asm_reports(
                    parsed,
                    deposit_low=cfg["deposit_low"],
                    deposit_high=cfg["deposit_high"],
                )

                if members:
                    asm_data["missing_reporters"] = check_asm_compliance(
                        parsed, members, target_date, cfg["deadline"], skip_list
                    )
                    asm_data["unreported_now"] = check_asm_compliance(
                        parsed, members, target_date, _now_hhmm, skip_list
                    )
                else:
                    asm_data["unreported_now"] = None

                asm_data["late_reporters"] = check_late_reporters(
                    parsed, target_date, cfg["deadline"]
                )
                asm_data["parsed_reports"] = parsed

                # Multi-day analysis
                multiday_data = None
                if not _is_single_day:
                    try:
                        multiday_data = analyze_multiday(parsed, date_from_str, date_to_str)
                    except Exception:
                        multiday_data = None

                # D-1 analysis
                asm_data_d1 = None
                if _is_single_day and _d1_from:
                    try:
                        msgs_d1   = fetch_all_messages(token=token, group_id=group_id, date_from=_d1_from)
                        msgs_d1   = filter_by_date(msgs_d1, _d1_from, _d1_to)
                        parsed_d1 = extract_all_reports(msgs_d1)
                        asm_data_d1 = analyze_asm_reports(
                            parsed_d1,
                            deposit_low=cfg["deposit_low"],
                            deposit_high=cfg["deposit_high"],
                        )
                    except Exception:
                        asm_data_d1 = None

                # Write-back: cập nhật label về library nếu lấy từ API
                if tab_label != entry["label"]:
                    for _li, _le in enumerate(st.session_state.library):
                        if extract_group_id(_le["url"]) == group_id:
                            st.session_state.library[_li]["label"] = tab_label
                            _label_updated = True
                            break

                excel_buf = io.BytesIO()
                write_asm_excel(asm_data, excel_buf)
                excel_buf.seek(0)

                status.update(label=f"✓ {tab_label}", state="complete")
                results.append({
                    "tab_label":      tab_label,
                    "group_id":       group_id,
                    "asm_data":       asm_data,
                    "asm_data_d1":    asm_data_d1,
                    "multiday_data":  multiday_data,
                    "asm_msgs":       [r for r in parsed if r.get("parse_error") is None],
                    "unparseable":    [r for r in parsed if r.get("parse_error") is not None],
                    "excel_buf":      excel_buf,
                    "target_date":    target_date,
                    "past_deadline":  _now_hhmm >= cfg["deadline"],
                    "parsed_reports": parsed,
                    "error":          None,
                })
            except Exception as exc:
                status.update(label=f"✗ {entry['label']}", state="error")
                results.append({
                    "tab_label": entry["label"],
                    "group_id":  group_id,
                    "error":     str(exc),
                })

    if _label_updated:
        _lib_save(st.session_state.library)

    st.session_state["_results"] = results



# ── Render kết quả (ngoài if run để giữ kết quả qua các rerun) ────────────────
_cached_weekly = st.session_state.get("_weekly_results", [])
if _cached_weekly:
    st.divider()
    if len(_cached_weekly) == 1:
        _render_weekly_result(_cached_weekly[0])
    else:
        _tabs = st.tabs([r["tab_label"] for r in _cached_weekly])
        for tab, result in zip(_tabs, _cached_weekly):
            with tab:
                _render_weekly_result(result)

_cached_results = st.session_state.get("_results", [])
if _cached_results:
    st.divider()

    # ── Chart so sánh giữa các nhóm (chỉ hiện khi có ≥ 2 nhóm) ──────────────
    _ok_results = [r for r in _cached_results if not r.get("error")]
    if len(_ok_results) >= 2:
        st.subheader("📊 So sánh giữa các nhóm")
        _cmp_data = {
            "Tổng cọc":    [r["asm_data"]["total_deposits"]  for r in _ok_results],
            "Tổng ra tiêm": [r["asm_data"]["total_ra_tiem"]  for r in _ok_results],
        }
        _cmp_labels = [r["tab_label"] for r in _ok_results]
        st.bar_chart(pd.DataFrame(_cmp_data, index=_cmp_labels), use_container_width=True)
        st.divider()

    if len(_cached_results) == 1:
        _render_result(_cached_results[0])
    else:
        tabs = st.tabs([r["tab_label"] for r in _cached_results])
        for tab, result in zip(tabs, _cached_results):
            with tab:
                _render_result(result)
