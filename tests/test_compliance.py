"""Tests for L2 pre-filter, parametrized compliance, zombie filter, weekday routing."""
import pytest
from fpt_chat_stats import (
    detect_report_candidates,
    _strip_diacritics,
)


def _msg(content, msg_type="TEXT"):
    return {"type": msg_type, "content": content}


class TestDetectReportCandidates:
    def test_keeps_shop_vt_canonical(self):
        text = ("Dạ em xin gửi báo cáo vệ tinh ngày 16/04: "
                "Shop: 223B Cống Quỳnh / Kết quả: 5 cọc | 12 KH tư vấn / "
                "đã làm: tích cực tư vấn / vấn đề: khách ít")
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_keeps_tttc_report(self):
        # Regression: this format used to be dropped by the old "shop + N cọc" regex
        text = ("Dạ em gửi báo cáo TTTC 58149 HCM 406B Trương Công Định / "
                "- Kết quả: DT 95% / HOT 12% / TB bill 2.3tr / "
                "- Vấn đề: khách tiêm lẻ / - Hành động: tăng tư vấn combo")
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_keeps_shop_vt_freeform(self):
        text = ("Em gửi báo cáo ngày 16/04 hỗ trợ tại shop LC HCM 24 Vĩnh Viễn. "
                "- SL cọc: 52 cọc - NV đã làm: gọi 30 KH / "
                "Cần cải thiện: tỷ lệ chốt thấp / Kế hoạch ngày mai: tập trung KH cũ")
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_drops_short_chat(self):
        assert detect_report_candidates([_msg("ok 👍")]) == []
        assert detect_report_candidates([_msg("đến giờ ăn trưa rồi")]) == []

    def test_drops_no_keyword(self):
        # Long text, has digits, but no report keyword
        text = "x" * 100 + " 12 34 nhưng đây là chuyện phiếm về thời tiết"
        assert detect_report_candidates([_msg(text)]) == []

    def test_drops_one_digit_only(self):
        text = ("TTTC hôm nay khách ít chỉ có năm người ghé thăm shop thôi "
                "lần thứ 2 rồi không có ai đặt cọc cả") + "x" * 40
        # Only 1 digit — fails ≥2 digits filter
        assert detect_report_candidates([_msg(text)]) == []

    def test_diacritic_insensitive(self):
        # User typed without diacritics ("coc" instead of "cọc")
        text = ("Dạ em bao cao shop ABC ngay 16/04 - SL coc: 5 - 12 KH tu van - "
                "ra tiem: 3 - kế hoạch ngày mai: tăng tư vấn") + "x" * 20
        assert detect_report_candidates([_msg(text)]) == [_msg(text)]

    def test_drops_non_text_message_type(self):
        text = "Shop ABC: 5 cọc, 12 KH tư vấn, ra tiêm 3, đã làm tốt" + "x" * 50
        assert detect_report_candidates([_msg(text, msg_type="IMAGE")]) == []

    def test_strip_diacritics(self):
        assert _strip_diacritics("Cọc Việt Nam") == "coc viet nam"
        assert _strip_diacritics("ĐÃ LÀM") == "da lam"


from datetime import date
from fpt_chat_stats import report_type_for_date


class TestReportTypeForDate:
    def test_monday_returns_daily(self):
        assert report_type_for_date(date(2026, 4, 20)) == "daily_shop_vt"

    def test_friday_returns_daily(self):
        assert report_type_for_date(date(2026, 4, 17)) == "daily_shop_vt"

    def test_saturday_returns_weekend(self):
        assert report_type_for_date(date(2026, 4, 18)) == "weekend_tttc"

    def test_sunday_returns_weekend(self):
        assert report_type_for_date(date(2026, 4, 19)) == "weekend_tttc"


from fpt_chat_stats import _is_active_member


class TestIsActiveMember:
    def test_active_member_with_lastread(self):
        assert _is_active_member({"lastReadMessageId": 103}) is True

    def test_zombie_lastread_zero(self):
        assert _is_active_member({"lastReadMessageId": 0}) is False

    def test_zombie_lastread_missing(self):
        assert _is_active_member({}) is False

    def test_zombie_lastread_none(self):
        assert _is_active_member({"lastReadMessageId": None}) is False

    def test_active_low_lastread(self):
        # Even reading 1 message qualifies as active
        assert _is_active_member({"lastReadMessageId": 1}) is True
