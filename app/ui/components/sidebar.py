"""Left Sidebar Navigation Widget matching the ClipDesk mockup."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QPen, QFont, QPainterPath
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

from app.services.sound_service import get_sound_service
from app.ui.themes.wave_widgets import ClipDeskLogoWidget


class SidebarNavButton(QPushButton):
    """Custom painted navigation pill button with icon and smooth active highlight."""

    def __init__(self, icon_kind: str, label: str, active: bool = False, parent=None) -> None:
        super().__init__(label, parent)
        self._icon_kind = icon_kind
        self._active = active
        self._hover = False
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        get_sound_service().play_hover()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        get_sound_service().play_tab()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(2.0, 2.0, w - 4.0, h - 4.0)
        if self._active:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0.0, QColor("#C6E0FF"))
            grad.setColorAt(1.0, QColor("#DFEEFF"))
            p.setPen(QPen(QColor("#A8CFFF"), 1.0))
            p.setBrush(grad)
            p.drawRoundedRect(rect, 10.0, 10.0)
        elif self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(205, 228, 255, 115))
            p.drawRoundedRect(rect, 10.0, 10.0)

        # Draw crisp vector icon on left
        icon_col = QColor("#1565D8") if self._active else QColor("#283E5E")
        cx, cy = 24.0, h * 0.5
        p.setPen(QPen(icon_col, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._icon_kind == "home":
            roof = QPainterPath()
            roof.moveTo(cx - 8, cy + 1)
            roof.lineTo(cx, cy - 7)
            roof.lineTo(cx + 8, cy + 1)
            p.drawPath(roof)
            p.setBrush(icon_col if self._active else Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(cx - 5.5, cy - 1, 11.0, 8.0), 1.5, 1.5)
        elif self._icon_kind == "history":
            p.drawEllipse(QPointF(cx, cy), 7.5, 7.5)
            p.drawLine(QPointF(cx, cy - 4), QPointF(cx, cy))
            p.drawLine(QPointF(cx, cy), QPointF(cx + 3, cy + 2))
        elif self._icon_kind == "report":
            tri = QPainterPath()
            tri.moveTo(cx, cy - 7.5)
            tri.lineTo(cx - 8, cy + 6.5)
            tri.lineTo(cx + 8, cy + 6.5)
            tri.closeSubpath()
            p.drawPath(tri)
            p.drawLine(QPointF(cx, cy - 2.5), QPointF(cx, cy + 1.8))
            p.drawPoint(QPointF(cx, cy + 4.3))
        elif self._icon_kind == "settings":
            p.drawEllipse(QPointF(cx, cy), 4.0, 4.0)
            p.drawEllipse(QPointF(cx, cy), 7.2, 7.2)
        elif self._icon_kind == "about":
            p.drawEllipse(QPointF(cx, cy), 7.5, 7.5)
            p.drawLine(QPointF(cx, cy - 1), QPointF(cx, cy + 4))
            p.drawPoint(QPointF(cx, cy - 4))

        # Draw text
        font = QFont("Segoe UI", 11)
        font.setBold(self._active)
        p.setFont(font)
        p.setPen(QColor("#1456B8") if self._active else QColor("#253958"))
        p.drawText(QRectF(44.0, 0, w - 48.0, h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        p.end()


class SidebarWidget(QFrame):
    """Left sidebar panel with ClipDesk branding, menu items, and Ready status bar."""

    home_clicked = Signal()
    history_clicked = Signal()
    report_clicked = Signal()
    settings_clicked = Signal()
    about_clicked = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(222)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 18, 14, 12)
        layout.setSpacing(6)

        # Brand Header: Logo + ClipDesk + Subtitle
        brand_row = QHBoxLayout()
        brand_row.setSpacing(10)
        logo = ClipDeskLogoWidget(44)
        brand_row.addWidget(logo)

        brand_text_col = QVBoxLayout()
        brand_text_col.setSpacing(0)
        title = QLabel(
            '<span style="color:#162F59;font-weight:800;">Clip</span>'
            '<span style="color:#1B66C9;font-weight:800;">Desk</span>'
        )
        title.setStyleSheet("font-size: 23px;")
        sub = QLabel("Download • Enjoy • Anytime")
        sub.setStyleSheet("font-size: 10px; color: #5B7499; font-weight: 600;")
        brand_text_col.addWidget(title)
        brand_text_col.addWidget(sub)
        brand_row.addLayout(brand_text_col, 1)
        layout.addLayout(brand_row)
        layout.addSpacing(16)

        # Top Nav Buttons
        self._btn_home = SidebarNavButton("home", "หน้าหลัก", active=True)
        self._btn_history = SidebarNavButton("history", "ประวัติการดาวน์โหลด")
        self._btn_report = SidebarNavButton("report", "รายงานปัญหา")

        self._nav_group = [self._btn_home, self._btn_history, self._btn_report]
        self._btn_home.clicked.connect(lambda: self._select_nav(self._btn_home, self.home_clicked))
        self._btn_history.clicked.connect(lambda: self._select_nav(self._btn_history, self.history_clicked))
        self._btn_report.clicked.connect(lambda: self._select_nav(self._btn_report, self.report_clicked))

        for btn in self._nav_group:
            layout.addWidget(btn)

        layout.addStretch(1)

        # Bottom Nav Buttons
        self._btn_settings = SidebarNavButton("settings", "ตั้งค่า")
        self._btn_about = SidebarNavButton("about", "เกี่ยวกับโปรแกรม")
        self._btn_settings.clicked.connect(self.settings_clicked.emit)
        self._btn_about.clicked.connect(self.about_clicked.emit)
        layout.addWidget(self._btn_settings)
        layout.addWidget(self._btn_about)

        root.addWidget(content, 1)

        # Bottom Ready Status Strip ("✔ พร้อมใช้งาน")
        status_strip = QFrame()
        status_strip.setFixedHeight(40)
        status_strip.setStyleSheet(
            "background-color: rgba(218, 235, 252, 160); "
            "border-top: 1px solid #CFE2F8;"
        )
        strip_layout = QHBoxLayout(status_strip)
        strip_layout.setContentsMargins(16, 0, 12, 0)
        strip_layout.setSpacing(8)

        dot = QLabel("✔")
        dot.setFixedSize(20, 20)
        dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot.setStyleSheet(
            "background-color: #43A047; color: white; border-radius: 10px; "
            "font-size: 11px; font-weight: bold;"
        )
        self._status_label = QLabel("พร้อมใช้งาน")
        self._status_label.setStyleSheet("color: #264166; font-size: 12px; font-weight: 600;")

        strip_layout.addWidget(dot)
        strip_layout.addWidget(self._status_label, 1)
        root.addWidget(status_strip)

    def _select_nav(self, target: SidebarNavButton, sig: Signal) -> None:
        for b in self._nav_group:
            b.set_active(b is target)
        sig.emit()

    def set_status_text(self, text: str) -> None:
        self._status_label.setText(text)

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor(242, 248, 255, 240))
        grad.setColorAt(0.6, QColor(233, 243, 254, 240))
        grad.setColorAt(1.0, QColor(225, 238, 253, 245))
        p.fillRect(0, 0, int(w), int(h), grad)

        # Right divider line
        p.setPen(QPen(QColor("#D2E4F8"), 1.2))
        p.drawLine(int(w) - 1, 0, int(w) - 1, int(h))
        p.end()
