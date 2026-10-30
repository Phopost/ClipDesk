"""GUI tests for the Report Issue dialog."""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from app.services import report_service as rs
from app.ui.report_dialog import ReportDialog


def test_dialog_defaults(qapp):
    dlg = ReportDialog()
    assert dlg.selected_category == rs.CATEGORIES[0]
    assert len(dlg.category_buttons) == 4
    assert "ntfy.sh/Clipdesk" in dlg.status_label.text()


def test_select_category(qapp):
    dlg = ReportDialog()
    dlg.category_buttons["แอปค้าง/เด้ง"].click()
    assert dlg.selected_category == "แอปค้าง/เด้ง"
    assert dlg.category_buttons["แอปค้าง/เด้ง"].isChecked()
    assert not dlg.category_buttons[rs.CATEGORIES[0]].isChecked()


def test_submit_empty_detail_warns_and_does_not_send(qapp, monkeypatch):
    warned = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warned.append(a))
    sent = []
    dlg = ReportDialog(sender=lambda **kw: sent.append(kw) or "body")
    dlg.submit()
    assert warned and not sent


def test_submit_success_clears_form(qapp, monkeypatch):
    sent = []
    dlg = ReportDialog(sender=lambda **kw: sent.append(kw) or "body", run_async=False)
    dlg.url_edit.setText("https://youtu.be/abc")
    dlg.detail_edit.setPlainText("โหลดไม่ได้")
    dlg.log_checkbox.setChecked(True)
    monkeypatch.setattr(dlg, "_show_sent_preview", lambda body: None)
    dlg.submit()
    assert sent == [{
        "category": rs.CATEGORIES[0],
        "detail": "โหลดไม่ได้",
        "video_url": "https://youtu.be/abc",
        "attach_sys_log": True,
    }]
    assert dlg.detail_edit.toPlainText() == ""
    assert dlg.url_edit.text() == ""
    assert "สำเร็จ" in dlg.status_label.text()


def test_submit_failure_shows_error(qapp, monkeypatch):
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: errors.append(a))

    def boom(**kw):
        raise RuntimeError("offline")

    dlg = ReportDialog(sender=boom, run_async=False)
    dlg.detail_edit.setPlainText("x")
    dlg.submit()
    assert errors
    assert "ไม่สำเร็จ" in dlg.status_label.text()
    assert dlg.detail_edit.toPlainText() == "x"
