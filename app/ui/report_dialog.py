"""Report Issue dialog (PySide6 port of the "Clipdesk Report Page" draft).

Layout follows the original design: blue header icon + title, category pills,
optional video-link field, detail box, System Log checkbox, blue send button,
and a status line showing the ntfy.sh/Clipdesk connection state.
"""

from __future__ import annotations

import threading
from typing import Callable

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from app.services import report_service as rs

_SEND_TEXT = "📨  ส่งรายงานปัญหา (Send to Clipdesk)"
_STATUS_READY = "🟢 การเชื่อมต่อแจ้งเตือน: ntfy.sh/Clipdesk (พร้อมส่ง)"

_STYLE = """
QDialog#reportDialog { background: #E3EFFF; }
QLabel { color: #0F172A; background: transparent; }
QLabel#reportTitle { font-size: 19px; font-weight: 700; }
QLabel#reportSubtitle { font-size: 12px; color: #1E293B; }
QLabel#reportIcon {
    background: #1D63EB; color: white; border: 2px solid #60A5FA;
    border-radius: 27px; font-size: 22px;
}
QLabel#cardTitle { font-size: 13px; font-weight: 700; }
QFrame#reportCard {
    background: #F2F7FF; border: 2px solid #FFFFFF; border-radius: 16px;
}
QPushButton#categoryPill {
    background: #F8FAFC; color: #1E293B; border: 1px solid #CBD5E1;
    border-radius: 16px; padding: 7px 20px; font-weight: 700; font-size: 12px;
}
QPushButton#categoryPill:hover { border-color: #60A5FA; }
QPushButton#categoryPill:checked {
    background: #D8E8FF; color: #0F172A; border: 2px solid #60A5FA;
}
QLineEdit#reportUrl, QPlainTextEdit#reportDetail {
    background: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1;
    border-radius: 10px; padding: 8px 10px; font-size: 13px;
}
QLineEdit#reportUrl:focus, QPlainTextEdit#reportDetail:focus { border-color: #3B82F6; }
QCheckBox { color: #1E293B; font-size: 12px; }
QPushButton#sendBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1D63EB, stop:1 #38BDF8);
    color: white; border: none; border-radius: 18px; padding: 10px 22px;
    font-weight: 700; font-size: 13px;
}
QPushButton#sendBtn:disabled { background: #93C5FD; }
QLabel#reportStatus { font-size: 11px; color: #15803D; }
"""


class _Bridge(QObject):
    done = Signal(bool, str)


class ReportDialog(QDialog):
    """Modal report form that sends issues to ntfy.sh/Clipdesk."""

    def __init__(
        self,
        parent=None,
        sender: Callable[..., str] | None = None,
        run_async: bool = True,
    ) -> None:
        super().__init__(parent)
        self._sender = sender or rs.send_report
        self._run_async = run_async
        self._bridge = _Bridge()
        self._bridge.done.connect(self._on_send_done)
        self.selected_category = rs.CATEGORIES[0]
        self.category_buttons: dict[str, QPushButton] = {}

        self.setObjectName("reportDialog")
        self.setWindowTitle("แจ้งปัญหาการใช้งาน — ClipDesk")
        self.resize(720, 640)
        self.setStyleSheet(_STYLE)
        self._setup_ui()

    # ── UI ──

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("reportCard")
        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 12, 18, 14)
        lay.setSpacing(8)
        lbl = QLabel(title)
        lbl.setObjectName("cardTitle")
        lay.addWidget(lbl)
        return card, lay

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 14)
        root.setSpacing(12)

        # 1. Header
        header = QHBoxLayout()
        icon = QLabel("🛠")
        icon.setObjectName("reportIcon")
        icon.setFixedSize(54, 54)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(icon)
        header.addSpacing(10)
        titles = QVBoxLayout()
        title = QLabel("แจ้งปัญหาการใช้งาน (Report Issue)")
        title.setObjectName("reportTitle")
        subtitle = QLabel("พบปัญหาหรือมีข้อเสนอแนะ แจ้งทีมงานผ่านระบบแจ้งเตือนทันที")
        subtitle.setObjectName("reportSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles, 1)
        root.addLayout(header)

        # 2. Category pills
        cat_card, cat_lay = self._card("หมวดหมู่ปัญหา")
        pills = QHBoxLayout()
        pills.setSpacing(12)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for cat in rs.CATEGORIES:
            btn = QPushButton(cat)
            btn.setObjectName("categoryPill")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, c=cat: self._select_category(c))
            self._group.addButton(btn)
            self.category_buttons[cat] = btn
            pills.addWidget(btn)
        pills.addStretch(1)
        self.category_buttons[self.selected_category].setChecked(True)
        cat_lay.addLayout(pills)
        root.addWidget(cat_card)

        # 3. Video URL
        url_card, url_lay = self._card("ลิงก์วิดีโอที่พบปัญหา (ถ้ามี)")
        self.url_edit = QLineEdit()
        self.url_edit.setObjectName("reportUrl")
        self.url_edit.setPlaceholderText("🔗  " + rs.URL_PLACEHOLDER)
        self.url_edit.setClearButtonEnabled(True)
        url_lay.addWidget(self.url_edit)
        root.addWidget(url_card)

        # 4. Detail
        detail_card, detail_lay = self._card("รายละเอียดปัญหา")
        self.detail_edit = QPlainTextEdit()
        self.detail_edit.setObjectName("reportDetail")
        self.detail_edit.setPlaceholderText(rs.DETAIL_PLACEHOLDER)
        self.detail_edit.setMinimumHeight(140)
        detail_lay.addWidget(self.detail_edit)
        root.addWidget(detail_card, 1)

        # 5. Checkbox + send button
        action_row = QHBoxLayout()
        self.log_checkbox = QCheckBox("แนบข้อมูลระบบและบันทึกข้อผิดพลาดอัตโนมัติ (System Log)")
        action_row.addWidget(self.log_checkbox)
        action_row.addStretch(1)
        self.send_btn = QPushButton(_SEND_TEXT)
        self.send_btn.setObjectName("sendBtn")
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.clicked.connect(self.submit)
        action_row.addWidget(self.send_btn)
        root.addLayout(action_row)

        # 6. Status line
        self.status_label = QLabel(_STATUS_READY)
        self.status_label.setObjectName("reportStatus")
        root.addWidget(self.status_label)

    # ── Behaviour ──

    def _select_category(self, category: str) -> None:
        self.selected_category = category
        self.category_buttons[category].setChecked(True)

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")

    def submit(self) -> None:
        detail = self.detail_edit.toPlainText().strip()
        if not detail:
            QMessageBox.warning(
                self, "แจ้งเตือน",
                "กรุณากรอกรายละเอียดปัญหาในช่อง 'รายละเอียดปัญหา' ก่อนกดส่งครับ",
            )
            self.detail_edit.setFocus()
            return

        kwargs = {
            "category": self.selected_category,
            "detail": detail,
            "video_url": self.url_edit.text().strip(),
            "attach_sys_log": self.log_checkbox.isChecked(),
        }
        self.send_btn.setEnabled(False)
        self.send_btn.setText("⏳  กำลังส่งไปที่ Clipdesk...")
        self._set_status("🟠 การเชื่อมต่อแจ้งเตือน: กำลังส่งข้อมูลไปที่ ntfy.sh/Clipdesk...", "#D97706")

        def worker() -> None:
            try:
                body = self._sender(**kwargs)
                self._bridge.done.emit(True, body or "")
            except Exception as err:  # noqa: BLE001 - report any failure to the user
                self._bridge.done.emit(False, str(err))

        if self._run_async:
            threading.Thread(target=worker, daemon=True).start()
        else:
            worker()

    def _on_send_done(self, success: bool, info: str) -> None:
        self.send_btn.setEnabled(True)
        self.send_btn.setText(_SEND_TEXT)
        if success:
            self._set_status("✅ การเชื่อมต่อแจ้งเตือน: ntfy.sh/Clipdesk (ส่งสำเร็จแล้ว!)", "#15803D")
            self.url_edit.clear()
            self.detail_edit.clear()
            self._show_sent_preview(info)
        else:
            self._set_status(f"🔴 การเชื่อมต่อแจ้งเตือน: ส่งไม่สำเร็จ ({info})", "#DC2626")
            QMessageBox.critical(
                self, "ส่งไม่สำเร็จ",
                f"ไม่สามารถส่งข้อความไปยัง ntfy.sh/Clipdesk ได้:\n{info}",
            )

    def _show_sent_preview(self, body: str) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("ส่งรายงานสำเร็จ — ClipDesk")
        box.setIcon(QMessageBox.Icon.Information)
        box.setText("✅ ส่งเข้าช่อง ntfy.sh/Clipdesk สำเร็จแล้ว! ขอบคุณที่แจ้งปัญหาครับ")
        box.setDetailedText(body)
        box.exec()
