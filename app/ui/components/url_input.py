"""URL input widget matching the ClipDesk mockup & compatible with ClipDesk-source."""

from __future__ import annotations

from PySide6.QtCore import Signal, Qt, QPointF, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QFrame, QApplication,
)

from app.services.sound_service import get_sound_service
from app.services.url_validator import validate_url


class _LinkBadgeIcon(QWidget):
    """Soft blue circular badge with chain-link icon on the left of URL input."""

    clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(32, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        s = float(self.width())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#C2DDFB"), 1.0))
        p.setBrush(QColor("#EBF4FF"))
        p.drawEllipse(QRectF(1.0, 1.0, s - 2.0, s - 2.0))

        # Chain link icon
        p.setPen(QPen(QColor("#1976D2"), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.translate(s * 0.5, s * 0.5)
        p.rotate(-40)
        p.drawRoundedRect(QRectF(-7.5, -3.5, 8.5, 7.0), 3.5, 3.5)
        p.drawRoundedRect(QRectF(-1.0, -3.5, 8.5, 7.0), 3.5, 3.5)
        p.end()


class UrlInput(QWidget):
    """
    URL input area with link icon, clear '✕' button, and '🔍 ตรวจสอบลิงก์' button.

    Signals:
        check_requested(str): URL to check (100% compatible with ClipDesk-source)
    """

    check_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._is_loading = False
        self._last_auto_checked_url = ""
        self._auto_check_timer = QTimer(self)
        self._auto_check_timer.setSingleShot(True)
        self._auto_check_timer.setInterval(120)
        self._auto_check_timer.timeout.connect(self._on_auto_check_timeout)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(10)

        # White pill input container
        self._input_card = QFrame()
        self._input_card.setObjectName("whiteCard")
        self._input_card.setFixedHeight(48)
        card_layout = QHBoxLayout(self._input_card)
        card_layout.setContentsMargins(10, 4, 10, 4)
        card_layout.setSpacing(8)

        # Left chain-link badge (clicking pastes from clipboard if empty)
        self._link_badge = _LinkBadgeIcon()
        self._link_badge.clicked.connect(self._on_paste)
        card_layout.addWidget(self._link_badge)

        # LineEdit
        self._url_edit = QLineEdit()
        self._url_edit.setObjectName("urlEdit")
        self._url_edit.setPlaceholderText("วางลิงก์ YouTube หรือ TikTok ที่นี่... (ตรวจสอบอัตโนมัติทันทีที่วาง)")
        self._url_edit.returnPressed.connect(self._on_check)
        self._url_edit.textEdited.connect(self._on_text_edited)
        card_layout.addWidget(self._url_edit, 1)

        # Hidden paste button kept for test/source compatibility
        self._paste_btn = QPushButton("วาง")
        self._paste_btn.hide()
        self._paste_btn.clicked.connect(self._on_paste)

        # Clear '✕' button inside input box
        self._clear_btn = QPushButton("✕")
        self._clear_btn.setFixedSize(28, 28)
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #6B82A6; "
            "font-size: 14px; font-weight: bold; border-radius: 14px; }"
            "QPushButton:hover { background-color: #EBF4FF; color: #1E2F4D; }"
        )
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        card_layout.addWidget(self._clear_btn)

        row.addWidget(self._input_card, 1)

        # Blue "🔍 ตรวจสอบลิงก์" button
        self._check_btn = QPushButton("🔍  ตรวจสอบลิงก์")
        self._check_btn.setObjectName("checkUrlBtn")
        self._check_btn.setFixedHeight(48)
        self._check_btn.setMinimumWidth(155)
        self._check_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._check_btn.clicked.connect(self._on_check)
        row.addWidget(self._check_btn)

        layout.addLayout(row)

        # Error label below input
        self._error_label = QLabel()
        self._error_label.setObjectName("errorLabel")
        self._error_label.setWordWrap(True)
        self._error_label.hide()
        layout.addWidget(self._error_label)

    def _on_clear_clicked(self) -> None:
        get_sound_service().play_click()
        self.clear()

    def _on_paste(self) -> None:
        get_sound_service().play_click()
        clipboard = QApplication.clipboard()
        text = clipboard.text().strip()
        if text:
            self._url_edit.setText(text)
            self._url_edit.setFocus()
            self._on_text_edited(text)

    def _on_text_edited(self, text: str) -> None:
        clean = text.strip()
        if not clean:
            self._auto_check_timer.stop()
            self.hide_error()
            return
        res = validate_url(clean)
        if res.is_valid and res.media_id and clean != self._last_auto_checked_url:
            self._auto_check_timer.start()

    def _on_auto_check_timeout(self) -> None:
        if self._is_loading:
            return
        url = self._url_edit.text().strip()
        res = validate_url(url)
        if res.is_valid and res.media_id and url != self._last_auto_checked_url:
            self._last_auto_checked_url = url
            self._on_check()

    def _on_check(self) -> None:
        if self._is_loading:
            return
        self._auto_check_timer.stop()
        get_sound_service().play_check()
        url = self._url_edit.text().strip()
        if url:
            self._last_auto_checked_url = url
            self.hide_error()
            self.check_requested.emit(url)

    def set_loading(self, loading: bool) -> None:
        self._is_loading = loading
        self._url_edit.setEnabled(not loading)
        self._paste_btn.setEnabled(not loading)
        self._check_btn.setEnabled(not loading)
        self._check_btn.setText("⏳ กำลังตรวจสอบ..." if loading else "🔍  ตรวจสอบลิงก์")

    def show_error(self, message: str) -> None:
        get_sound_service().play_error()
        self._error_label.setText(message)
        self._error_label.show()

    def hide_error(self) -> None:
        self._error_label.hide()

    def clear(self) -> None:
        self._auto_check_timer.stop()
        self._last_auto_checked_url = ""
        self._url_edit.clear()
        self.hide_error()

    def get_url(self) -> str:
        return self._url_edit.text().strip()

    def set_url(self, url: str) -> None:
        self._url_edit.setText(url)
