"""Tests for the ntfy-based issue report service."""

from __future__ import annotations

import urllib.parse

import pytest

from app.services import report_service as rs


def test_categories_match_spec():
    assert rs.CATEGORIES == ["ดาวน์โหลดไม่ได้", "ลิงก์ผิดพลาด", "แอปค้าง/เด้ง", "ข้อเสนอแนะอื่นๆ"]


def test_build_message_contains_fields():
    msg = rs.build_report_message("ลิงก์ผิดพลาด", "  เปิดไม่ได้  ", "https://youtu.be/x")
    assert "หมวดหมู่ : ลิงก์ผิดพลาด" in msg
    assert "https://youtu.be/x" in msg
    assert "เปิดไม่ได้" in msg
    assert "ข้อมูลระบบ" not in msg


def test_build_message_without_url_says_not_specified():
    msg = rs.build_report_message("ดาวน์โหลดไม่ได้", "detail", "   ")
    assert "ไม่ได้ระบุ" in msg


def test_build_message_with_system_log_includes_version():
    from app.version import __version__

    msg = rs.build_report_message("แอปค้าง/เด้ง", "crash", attach_sys_log=True)
    assert "ข้อมูลระบบ" in msg
    assert __version__ in msg


def test_send_report_rejects_empty_detail():
    with pytest.raises(ValueError):
        rs.send_report("ดาวน์โหลดไม่ได้", "   ")


def test_send_report_posts_to_ntfy(monkeypatch):
    captured = {}

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["data"] = req.data.decode("utf-8")
        captured["method"] = req.get_method()
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr(rs.urllib.request, "urlopen", fake_urlopen)
    body = rs.send_report("ลิงก์ผิดพลาด", "broken link", "https://x")
    assert captured["method"] == "POST"
    assert captured["url"].startswith("https://ntfy.sh/Clipdesk?")
    query = urllib.parse.parse_qs(urllib.parse.urlparse(captured["url"]).query)
    assert "ลิงก์ผิดพลาด" in query["title"][0]
    assert captured["data"] == body
    assert captured["timeout"] <= 15


def test_send_report_raises_on_non_200(monkeypatch):
    class _Resp:
        status = 500

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(rs.urllib.request, "urlopen", lambda req, timeout: _Resp())
    with pytest.raises(RuntimeError):
        rs.send_report("ดาวน์โหลดไม่ได้", "x")
