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
    val = st_javascript(f"localStorage.getItem({json.dumps(key)}) || ''")
    return val if isinstance(val, str) else ""

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

def _save_groups_local(groups: list) -> None:
    """Lưu danh sách groups vào config.json khi chạy local."""
    if not os.path.isfile(_CONFIG_PATH):
        return
    cfg = _load_config()
    cfg["groups"] = groups
    cfg.pop("group", None)
    try:
        with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ── Group input helpers ───────────────────────────────────────────────────────

def _parse_group_line(line: str):
    """Parse 'group_id_or_url | optional label' → (group_str, label_or_None)."""
    if "|" in line:
        parts = line.split("|", 1)
        label = parts[1].strip()
        return parts[0].strip(), label or None
    return line.strip(), None

def _resolve_tab_label(group_id: str, custom_label, group_info: dict) -> str:
    if custom_label:
        return custom_label
    name = group_info.get("name") or group_info.get("title") or ""
    if name:
        return name
    return group_id[-8:] if len(group_id) >= 8 else group_id

# ── Per-group config helpers ──────────────────────────────────────────────────

_CFG_DEFAULTS = {"deposit_low": 2, "deposit_high": 5, "deadline": "20:00", "skip": ""}

def _get_group_cfg(group_configs: dict, group_id: str) -> dict:
    stored = group_configs.get(group_id, {})
    return {k: stored.get(k, v) for k, v in _CFG_DEFAULTS.items()}

# ── Import core logic từ fpt_chat_stats ──────────────────────────────────────

try:
    from fpt_chat_stats import (
        analyze_asm_reports,
        build_session,
        check_asm_compliance,
        detect_asm_reports,
        extract_group_id,
        fetch_all_messages,
        fetch_group_info,
        fetch_group_members,
        filter_by_date,
        parse_asm_report,
        parse_date_arg,
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

st.markdown("""
<style>
div[data-testid="stElementContainer"]:has(iframe[data-testid="stCustomComponentV1"]) {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# ── Đọc localStorage ──────────────────────────────────────────────────────────

_cfg = _load_config()
_saved_token = _ls_get("fpt_token")

# Groups: fpt_groups (JSON array) → fpt_group (string cũ) → config.json
_raw_groups_json = _ls_get("fpt_groups")
if _raw_groups_json:
    try:
        _saved_groups_list = json.loads(_raw_groups_json)
    except Exception:
        _saved_groups_list = []
else:
    _legacy = _ls_get("fpt_group") or ""
    if _legacy:
        _saved_groups_list = [_legacy]
    else:
        cfg_groups = _cfg.get("groups")
        if isinstance(cfg_groups, list):
            _saved_groups_list = cfg_groups
        elif _cfg.get("group"):
            _saved_groups_list = [_cfg["group"]]
        else:
            _saved_groups_list = []

_saved_groups_text = "\n".join(_saved_groups_list)

# Per-group configs
_raw_group_configs = _ls_get("fpt_group_configs")
_group_configs: dict = {}
if _raw_group_configs:
    try:
        _group_configs = json.loads(_raw_group_configs)
    except Exception:
        pass

# Pre-fill expander từ config của nhóm đầu tiên
_first_group_cfg = _CFG_DEFAULTS.copy()
if _saved_groups_list:
    _first_str, _ = _parse_group_line(_saved_groups_list[0])
    _first_id = extract_group_id(_first_str)
    _first_group_cfg = _get_group_cfg(_group_configs, _first_id)

# ── UI: Header ────────────────────────────────────────────────────────────────

st.title("📊 FPT Chat ASM Report")
st.caption("Phân tích báo cáo hàng ngày của ASM từ FPT Chat")
st.divider()

# ── Vùng 1: Kết nối ──────────────────────────────────────────────────────────

token = st.text_input(
    "Token (Bearer)",
    value=_saved_token,
    type="password",
    placeholder="Dán token từ DevTools vào đây",
    help="DevTools → Network → chọn request api-chat.fpt.com → Headers → Authorization: Bearer <token>",
)

groups_text = st.text_area(
    "Nhóm chat",
    value=_saved_groups_text,
    height=120,
    placeholder=(
        "Một nhóm mỗi dòng. Tuỳ chọn: thêm | Tên tab sau group ID/URL\n"
        "686b517a54ca42cb3c30e1df\n"
        "https://chat.fpt.com/group/abc123 | Nhóm miền Nam"
    ),
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

# ── Vùng 3: Tuỳ chọn nâng cao (pre-fill từ config nhóm đầu tiên) ─────────────

with st.expander("⚙️ Tuỳ chọn nâng cao"):
    c1, c2, c3 = st.columns(3)
    with c1:
        deposit_low  = st.number_input("Ngưỡng cọc thấp (<)", value=int(_first_group_cfg["deposit_low"]),  min_value=0)
    with c2:
        deposit_high = st.number_input("Ngưỡng cọc cao (>)",  value=int(_first_group_cfg["deposit_high"]), min_value=0)
    with c3:
        deadline = st.text_input("Deadline (giờ VN)", value=_first_group_cfg["deadline"])
    skip_str = st.text_input(
        "Bỏ qua khỏi compliance check",
        value=_first_group_cfg["skip"],
        placeholder="Tên Trưởng phòng, Tên Giám đốc",
        help="Cách nhau bằng dấu phẩy",
    )

# ── Nút chạy ─────────────────────────────────────────────────────────────────

run = st.button("▶ Chạy phân tích", type="primary", use_container_width=True)

if run:
    if not token:
        st.error("Vui lòng nhập Token.")
        st.stop()

    group_lines = [l.strip() for l in groups_text.splitlines() if l.strip()]
    if not group_lines:
        st.error("Vui lòng nhập ít nhất một Group ID hoặc URL.")
        st.stop()

    parsed_groups = [_parse_group_line(l) for l in group_lines]

    # Lưu vào localStorage
    _ls_set("fpt_token", token)
    _ls_set("fpt_groups", json.dumps(group_lines))
    _save_groups_local(group_lines)

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

    # Config từ expander (dùng cho nhóm chưa có config riêng)
    expander_config = {
        "deposit_low":  int(deposit_low),
        "deposit_high": int(deposit_high),
        "deadline":     deadline,
        "skip":         skip_str,
    }

    group_configs = dict(_group_configs)

    # ── Fetch & analyze từng nhóm ─────────────────────────────────────────────
    results = []
    for group_str, custom_label in parsed_groups:
        group_id = extract_group_id(group_str)
        short_id = group_id[-8:] if len(group_id) >= 8 else group_id

        # Dùng config đã lưu; nhóm mới → lưu từ expander
        if group_id in group_configs:
            cfg = _get_group_cfg(group_configs, group_id)
        else:
            cfg = expander_config.copy()
            group_configs[group_id] = cfg

        skip_list = [s.strip() for s in cfg["skip"].split(",") if s.strip()]

        with st.status(f"Đang xử lý {short_id}…", expanded=False) as status:
            try:
                session = build_session(token)

                group_info = fetch_group_info(session, "https://api-chat.fpt.com", group_id)
                tab_label  = _resolve_tab_label(group_id, custom_label, group_info)

                messages = fetch_all_messages(token=token, group_id=group_id, date_from=date_from)
                messages = filter_by_date(messages, date_from, date_to)
                asm_msgs = detect_asm_reports(messages)

                try:
                    members = fetch_group_members(session, "https://api-chat.fpt.com", group_id)
                except Exception:
                    members = []

                parsed = [parse_asm_report(m) for m in asm_msgs]
                asm_data = analyze_asm_reports(
                    parsed,
                    deposit_low=cfg["deposit_low"],
                    deposit_high=cfg["deposit_high"],
                )

                if members:
                    asm_data["missing_reporters"] = check_asm_compliance(
                        parsed, members, target_date, cfg["deadline"], skip_list
                    )

                excel_buf = io.BytesIO()
                write_asm_excel(asm_data, excel_buf)
                excel_buf.seek(0)

                status.update(label=f"✓ {tab_label}", state="complete")
                results.append({
                    "tab_label":   tab_label,
                    "group_id":    group_id,
                    "asm_data":    asm_data,
                    "asm_msgs":    asm_msgs,
                    "excel_buf":   excel_buf,
                    "config":      cfg,
                    "target_date": target_date,
                    "error":       None,
                })
            except Exception as e:
                status.update(label=f"✗ {short_id}", state="error")
                results.append({
                    "tab_label": custom_label or short_id,
                    "group_id":  group_id,
                    "error":     str(e),
                })

    # Lưu config đã cập nhật
    _ls_set("fpt_group_configs", json.dumps(group_configs))

    # ── Render kết quả ────────────────────────────────────────────────────────

    def _render_result(r: dict) -> None:
        if r.get("error"):
            st.error(f"Lỗi: {r['error']}")
            return

        asm_data    = r["asm_data"]
        asm_msgs    = r["asm_msgs"]
        excel_buf   = r["excel_buf"]
        cfg         = r["config"]
        target_date = r["target_date"]
        group_id    = r["group_id"]
        short_id    = group_id[-8:] if len(group_id) >= 8 else group_id

        # Config đã dùng
        with st.expander("⚙️ Cấu hình đã dùng", expanded=False):
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Cọc thấp (<)", cfg["deposit_low"])
            cc2.metric("Cọc cao (>)",  cfg["deposit_high"])
            cc3.metric("Deadline",     cfg["deadline"])
            if cfg["skip"]:
                st.caption(f"Bỏ qua: {cfg['skip']}")

        # Header + Download
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

        # Metrics
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Báo cáo ASM",   len(asm_msgs))
        col_b.metric("Shop cọc thấp", len(asm_data["low_deposit_shops"]))
        col_c.metric("Shop cọc cao",  len(asm_data["high_deposit_shops"]))

        if not asm_msgs:
            st.warning("Không tìm thấy báo cáo ASM nào trong khoảng thời gian này.")

        # Shop đặt cọc
        st.subheader("🏪 Shop đặt cọc")
        all_shops = sorted(asm_data.get("all_shops", []), key=lambda x: x["deposit_count"], reverse=True)
        if all_shops:
            st.dataframe(
                [{"Shop": s["shop_ref"], "Số cọc": s["deposit_count"],
                  "Mức": s["level"], "ASM": s["sender"]} for s in all_shops],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("(không có)")

        # Ý tưởng ASM
        st.subheader("💡 Ý tưởng triển khai từ ASM")
        ideas = asm_data.get("ideas", [])
        if ideas:
            st.dataframe(
                [{"ASM": i["sender"], "Shop": i["shop_ref"], "Nội dung": i["da_lam"]}
                 for i in ideas],
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("(không có)")

        # Điểm nổi bật
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
            st.dataframe(highlights, use_container_width=True, hide_index=True)
        else:
            st.caption("(không có)")

        # ASM chưa báo cáo
        missing = asm_data.get("missing_reporters")
        if missing is not None:
            st.subheader("⚠️ ASM chưa báo cáo")
            if missing:
                st.dataframe(
                    [{"Tên ASM": name} for name in missing],
                    use_container_width=True, hide_index=True,
                )
            else:
                st.success("Tất cả ASM đã báo cáo")

    st.divider()
    if len(results) == 1:
        _render_result(results[0])
    else:
        tabs = st.tabs([r["tab_label"] for r in results])
        for tab, result in zip(tabs, results):
            with tab:
                _render_result(result)
