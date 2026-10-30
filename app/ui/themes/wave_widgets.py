"""Custom QPainter widgets for ClipDesk's Sky-Blue Wave Glass UI & Animations.

Provides:
- WaveBackgroundWidget : Dreamy layered sky-blue wave background (exact mockup match)
- WaveCardFrame        : White card with delicate blue silk waves on the right side
- ClipDeskLogoWidget   : 3D glossy blue play + download arrow logo
- HeaderDownloadBadge  : Large circular glossy blue download icon (↓) in header
- GlossyDownloadButton : 3D glowing cyan/blue pill button ("เริ่มดาวน์โหลด") with pulse & hover animations
- ThumbnailPreviewWidget: Rounded 16:9 thumbnail with animated play overlay & duration badge
- AnimatedProgressBar  : Smooth gradient progress bar with animated shimmer wave
- CircularActionButton : Circular blue (⏸/▶) and soft-red (✕) queue action buttons
"""

from __future__ import annotations

import math
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QTimer, Property, QPropertyAnimation, QEasingCurve, Signal,
)
from PySide6.QtGui import (
    QPainter, QLinearGradient, QRadialGradient, QColor, QPainterPath,
    QPen, QBrush, QPixmap, QFont,
)
from PySide6.QtWidgets import QWidget, QFrame, QPushButton

from app.services.sound_service import get_sound_service


class WaveBackgroundWidget(QWidget):
    """Paints the dreamy sky-blue and white flowing wave background from the mockup."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.025) % (2.0 * math.pi)
        self.update()

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Base soft sky gradient
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor("#DCEBFA"))
        bg.setColorAt(0.35, QColor("#EDF5FD"))
        bg.setColorAt(0.70, QColor("#E3EFFC"))
        bg.setColorAt(1.0, QColor("#D5E7FA"))
        p.fillRect(0, 0, int(w), int(h), bg)

        # Top-right sweeping silk wave 1
        shift = math.sin(self._phase) * 8.0
        wave1 = QPainterPath()
        wave1.moveTo(w * 0.25, 0)
        wave1.cubicTo(
            w * 0.48, h * 0.16 + shift,
            w * 0.72, -h * 0.04 - shift,
            w, h * 0.14,
        )
        wave1.lineTo(w, 0)
        wave1.closeSubpath()
        g1 = QLinearGradient(w * 0.25, 0, w, h * 0.18)
        g1.setColorAt(0.0, QColor(168, 210, 250, 95))
        g1.setColorAt(0.6, QColor(135, 190, 248, 130))
        g1.setColorAt(1.0, QColor(195, 225, 255, 80))
        p.fillPath(wave1, g1)

        # Top sweeping ribbon highlight
        wave2 = QPainterPath()
        wave2.moveTo(w * 0.42, 0)
        wave2.cubicTo(
            w * 0.60, h * 0.12 - shift * 0.7,
            w * 0.82, h * 0.02 + shift * 0.7,
            w, h * 0.22,
        )
        wave2.lineTo(w, 0)
        wave2.closeSubpath()
        g2 = QLinearGradient(w * 0.45, 0, w, h * 0.22)
        g2.setColorAt(0.0, QColor(255, 255, 255, 150))
        g2.setColorAt(1.0, QColor(165, 208, 250, 110))
        p.fillPath(wave2, g2)

        # Bottom-right soft wave
        wave3 = QPainterPath()
        wave3.moveTo(w * 0.35, h)
        wave3.cubicTo(
            w * 0.58, h * 0.86 + shift * 0.5,
            w * 0.82, h * 0.96 - shift * 0.5,
            w, h * 0.78,
        )
        wave3.lineTo(w, h)
        wave3.closeSubpath()
        g3 = QLinearGradient(w * 0.4, h * 0.8, w, h)
        g3.setColorAt(0.0, QColor(180, 216, 252, 85))
        g3.setColorAt(1.0, QColor(145, 196, 248, 125))
        p.fillPath(wave3, g3)
        p.end()


class WaveCardFrame(QFrame):
    """White rounded card with delicate blue wave ribbons on the right side (Media Card)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._hover_progress = 0.0
        self._anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._anim.setDuration(180)

    def getHoverProgress(self) -> float:
        return self._hover_progress

    def setHoverProgress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    hoverProgress = Property(float, getHoverProgress, setHoverProgress)

    def enterEvent(self, event) -> None:
        self._anim.stop()
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._anim.stop()
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1.0, 1.0, w - 2.0, h - 2.0)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 14.0, 14.0)
        p.setClipPath(clip)

        # Card base
        bg = QLinearGradient(0, 0, w, h)
        bg.setColorAt(0.0, QColor(255, 255, 255, 248))
        bg.setColorAt(0.75, QColor(248, 252, 255, 248))
        bg.setColorAt(1.0, QColor(236, 246, 255, 248))
        p.fillPath(clip, bg)

        # Delicate right-side decorative blue waves (matches mockup media preview card)
        w1 = QPainterPath()
        w1.moveTo(w * 0.58, h)
        w1.cubicTo(w * 0.72, h * 0.65, w * 0.86, h * 0.85, w, h * 0.35)
        w1.lineTo(w, h)
        w1.closeSubpath()
        p.fillPath(w1, QColor(200, 228, 254, 110))

        w2 = QPainterPath()
        w2.moveTo(w * 0.70, h)
        w2.cubicTo(w * 0.82, h * 0.72, w * 0.92, h * 0.55, w, h * 0.15)
        w2.lineTo(w, h)
        w2.closeSubpath()
        p.fillPath(w2, QColor(175, 214, 252, 90))

        p.setClipping(False)
        border_col = QColor("#B9D7FA") if self._hover_progress > 0.3 else QColor("#DCE9F9")
        p.setPen(QPen(border_col, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 14.0, 14.0)
        p.end()


class ClipDeskLogoWidget(QWidget):
    """Paints the 3D glossy blue play-triangle with download arrow logo."""

    def __init__(self, size: int = 44, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        s = float(self.width())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded triangle play shape
        path = QPainterPath()
        path.moveTo(s * 0.18, s * 0.10)
        path.quadTo(s * 0.10, s * 0.06, s * 0.10, s * 0.18)
        path.lineTo(s * 0.10, s * 0.82)
        path.quadTo(s * 0.10, s * 0.94, s * 0.20, s * 0.89)
        path.lineTo(s * 0.86, s * 0.56)
        path.quadTo(s * 0.95, s * 0.50, s * 0.86, s * 0.44)
        path.closeSubpath()

        grad = QLinearGradient(0, 0, s, s)
        grad.setColorAt(0.0, QColor("#44B5FF"))
        grad.setColorAt(0.5, QColor("#1E7CF2"))
        grad.setColorAt(1.0, QColor("#0F52BA"))
        p.fillPath(path, grad)

        # Inner cyan highlight
        p.setPen(QPen(QColor(255, 255, 255, 140), 1.4))
        p.drawPath(path)

        # White download arrow inside the triangle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        # Arrow shaft
        p.drawRoundedRect(QRectF(s * 0.34, s * 0.30, s * 0.10, s * 0.22), 2, 2)
        # Arrow head
        head = QPainterPath()
        head.moveTo(s * 0.25, s * 0.48)
        head.lineTo(s * 0.53, s * 0.48)
        head.lineTo(s * 0.39, s * 0.65)
        head.closeSubpath()
        p.fillPath(head, QColor("#FFFFFF"))
        # Bottom tray line
        p.drawRoundedRect(QRectF(s * 0.26, s * 0.68, s * 0.26, s * 0.06), 1.5, 1.5)
        p.end()


class HeaderDownloadBadge(QWidget):
    """Large circular glossy blue download icon (↓) in the main header."""

    def __init__(self, size: int = 52, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:
        s = float(self.width())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Outer soft shadow halo
        halo = QRadialGradient(QPointF(s * 0.5, s * 0.52), s * 0.5)
        halo.setColorAt(0.0, QColor(30, 136, 229, 180))
        halo.setColorAt(0.82, QColor(30, 136, 229, 60))
        halo.setColorAt(1.0, QColor(30, 136, 229, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QRectF(0, 0, s, s))

        # Main glossy blue circle
        circle_rect = QRectF(s * 0.08, s * 0.08, s * 0.84, s * 0.84)
        grad = QLinearGradient(0, s * 0.08, 0, s * 0.92)
        grad.setColorAt(0.0, QColor("#4DA8FF"))
        grad.setColorAt(0.5, QColor("#1E7BF0"))
        grad.setColorAt(1.0, QColor("#1255B8"))
        p.setBrush(grad)
        p.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        p.drawEllipse(circle_rect)

        # White download arrow + tray
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(s * 0.44, s * 0.25, s * 0.12, s * 0.26), 2.5, 2.5)
        arrow = QPainterPath()
        arrow.moveTo(s * 0.31, s * 0.46)
        arrow.lineTo(s * 0.69, s * 0.46)
        arrow.lineTo(s * 0.50, s * 0.66)
        arrow.closeSubpath()
        p.fillPath(arrow, QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(s * 0.32, s * 0.69, s * 0.36, s * 0.07), 2.0, 2.0)
        p.end()


class GlossyDownloadButton(QPushButton):
    """The 3D glowing cyan/blue pill button ('↓ เริ่มดาวน์โหลด') from the mockup."""

    def __init__(self, text: str = "เริ่มดาวน์โหลด", parent=None) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(195, 62)
        self._hover = 0.0
        self._pulse = 0.0

        self._hover_anim = QPropertyAnimation(self, b"hoverLevel", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(40)
        self._pulse_timer.timeout.connect(self._on_pulse)
        self._pulse_timer.start()

    def getHoverLevel(self) -> float:
        return self._hover

    def setHoverLevel(self, val: float) -> None:
        self._hover = val
        self.update()

    hoverLevel = Property(float, getHoverLevel, setHoverLevel)

    def _on_pulse(self) -> None:
        self._pulse = (self._pulse + 0.08) % (2.0 * math.pi)
        self.update()

    def enterEvent(self, event) -> None:
        get_sound_service().play_hover()
        self._hover_anim.stop()
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover_anim.stop()
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        get_sound_service().play_download_start()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        glow_boost = 0.5 * (1.0 + math.sin(self._pulse)) * 0.25 + self._hover * 0.35

        # 1. Outer electric cyan-blue aura glow
        outer_rect = QRectF(3.0, 3.0, w - 6.0, h - 6.0)
        p.setPen(QPen(QColor(80, 195, 255, int(110 + 90 * glow_boost)), 4.0))
        p.setBrush(QColor(225, 245, 255, 210))
        p.drawRoundedRect(outer_rect, (h - 6.0) / 2.0, (h - 6.0) / 2.0)

        # 2. Inner 3D glossy blue pill
        pill_rect = QRectF(8.0, 7.0, w - 16.0, h - 14.0)
        radius = pill_rect.height() / 2.0
        grad = QLinearGradient(0, pill_rect.top(), 0, pill_rect.bottom())
        if self.isDown():
            grad.setColorAt(0.0, QColor("#1565C0"))
            grad.setColorAt(0.5, QColor("#0D47A1"))
            grad.setColorAt(1.0, QColor("#1976D2"))
        elif self._hover > 0.1:
            grad.setColorAt(0.0, QColor("#56B8FF"))
            grad.setColorAt(0.45, QColor("#1E80F0"))
            grad.setColorAt(0.85, QColor("#0F56C8"))
            grad.setColorAt(1.0, QColor("#29B6F6"))
        else:
            grad.setColorAt(0.0, QColor("#42A5F5"))
            grad.setColorAt(0.45, QColor("#1976D2"))
            grad.setColorAt(0.85, QColor("#0D47A1"))
            grad.setColorAt(1.0, QColor("#26C6DA"))

        p.setPen(QPen(QColor(160, 225, 255, 220), 1.5))
        p.setBrush(grad)
        p.drawRoundedRect(pill_rect, radius, radius)

        # 3. Top glass reflection arc
        shine_rect = QRectF(pill_rect.left() + 10, pill_rect.top() + 2, pill_rect.width() - 20, pill_rect.height() * 0.44)
        shine = QLinearGradient(0, shine_rect.top(), 0, shine_rect.bottom())
        shine.setColorAt(0.0, QColor(255, 255, 255, 155))
        shine.setColorAt(1.0, QColor(255, 255, 255, 10))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(shine)
        p.drawRoundedRect(shine_rect, shine_rect.height() / 2.0, shine_rect.height() / 2.0)

        # 4. Download icon (↓) + Text ("เริ่มดาวน์โหลด")
        cx = pill_rect.left() + 34.0
        cy = pill_rect.center().y()
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(cx - 2.2, cy - 10, 4.4, 11), 1.5, 1.5)
        tri = QPainterPath()
        tri.moveTo(cx - 7.5, cy - 1)
        tri.lineTo(cx + 7.5, cy - 1)
        tri.lineTo(cx, cy + 7)
        tri.closeSubpath()
        p.fillPath(tri, QColor("#FFFFFF"))
        p.drawRoundedRect(QRectF(cx - 8, cy + 8.5, 16, 2.8), 1.2, 1.2)

        font = QFont("Segoe UI", 13)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QColor("#FFFFFF"))
        text_rect = QRectF(cx + 12, pill_rect.top(), pill_rect.right() - (cx + 16), pill_rect.height())
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        p.end()


class ThumbnailPreviewWidget(QWidget):
    """16:9 Rounded video thumbnail with centered Play overlay (▶) and duration badge (12:34)."""

    play_clicked = Signal()

    def __init__(self, width: int = 210, height: int = 118, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pixmap: QPixmap | None = None
        self._duration_text = "12:34"
        self._hover = 0.0
        self._anim = QPropertyAnimation(self, b"hoverScale", self)
        self._anim.setDuration(150)

    def getHoverScale(self) -> float:
        return self._hover

    def setHoverScale(self, val: float) -> None:
        self._hover = val
        self.update()

    hoverScale = Property(float, getHoverScale, setHoverScale)

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self.update()

    def set_duration(self, text: str) -> None:
        self._duration_text = text
        self.update()

    def enterEvent(self, event) -> None:
        get_sound_service().play_hover()
        self._anim.stop()
        self._anim.setEndValue(1.0)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._anim.stop()
        self._anim.setEndValue(0.0)
        self._anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        get_sound_service().play_click()
        self.play_clicked.emit()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(0, 0, w, h)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 10.0, 10.0)
        p.setClipPath(clip)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                int(w), int(h),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            sx = (scaled.width() - w) / 2.0
            sy = (scaled.height() - h) / 2.0
            p.drawPixmap(QPointF(-sx, -sy), scaled)
        else:
            grad = QLinearGradient(0, 0, w, h)
            grad.setColorAt(0.0, QColor("#4FA3E3"))
            grad.setColorAt(1.0, QColor("#1D5B8C"))
            p.fillRect(rect, grad)

        # Center dark translucent Play circle
        cx, cy = w * 0.5, h * 0.5
        r = 20.0 + self._hover * 3.0
        p.setPen(QPen(QColor(255, 255, 255, 190), 1.5))
        p.setBrush(QColor(15, 28, 48, int(145 + 35 * self._hover)))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # Play triangle inside circle
        tri = QPainterPath()
        tri.moveTo(cx - 5.0, cy - 7.5)
        tri.lineTo(cx - 5.0, cy + 7.5)
        tri.lineTo(cx + 8.0, cy)
        tri.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#FFFFFF"))
        p.fillPath(tri, QColor("#FFFFFF"))

        # Duration badge at bottom-right ("12:34")
        if self._duration_text:
            badge_w, badge_h = 46.0, 20.0
            badge_rect = QRectF(w - badge_w - 7.0, h - badge_h - 6.0, badge_w, badge_h)
            p.setBrush(QColor(15, 23, 38, 205))
            p.drawRoundedRect(badge_rect, 5.0, 5.0)
            font = QFont("Segoe UI", 9)
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor("#FFFFFF"))
            p.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._duration_text)

        p.end()


class AnimatedProgressBar(QWidget):
    """Smooth rounded progress bar with animated sky-blue shimmer."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(7)
        self._value = 0.0  # 0..100
        self._shimmer = 0.0
        self._anim = QPropertyAnimation(self, b"progressValue", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        if 0 < self._value < 100:
            self._shimmer = (self._shimmer + 0.04) % 1.0
            self.update()

    def getProgressValue(self) -> float:
        return self._value

    def setProgressValue(self, val: float) -> None:
        self._value = max(0.0, min(100.0, val))
        self.update()

    progressValue = Property(float, getProgressValue, setProgressValue)

    def setValue(self, val: float, animated: bool = True) -> None:
        target = max(0.0, min(100.0, float(val)))
        if animated:
            self._anim.stop()
            self._anim.setStartValue(self._value)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self.setProgressValue(target)

    def setMaximum(self, _max: int) -> None:
        pass

    def value(self) -> int:
        return int(round(self._value))

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        r = h / 2.0
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#DCE8F6"))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Fill chunk
        if self._value > 0.5:
            fill_w = max(h, w * (self._value / 100.0))
            grad = QLinearGradient(0, 0, fill_w, 0)
            grad.setColorAt(0.0, QColor("#1976D2"))
            grad.setColorAt(0.6, QColor("#2998FF"))
            grad.setColorAt(1.0, QColor("#00BCD4"))
            p.setBrush(grad)
            p.drawRoundedRect(QRectF(0, 0, fill_w, h), r, r)

            # Moving shimmer highlight
            if self._value < 100.0:
                sx = fill_w * self._shimmer
                shimmer = QLinearGradient(sx - 25, 0, sx + 25, 0)
                shimmer.setColorAt(0.0, QColor(255, 255, 255, 0))
                shimmer.setColorAt(0.5, QColor(255, 255, 255, 130))
                shimmer.setColorAt(1.0, QColor(255, 255, 255, 0))
                p.setBrush(shimmer)
                p.drawRoundedRect(QRectF(0, 0, fill_w, h), r, r)
        p.end()


class CircularActionButton(QPushButton):
    """Circular icon button for queue rows: 'pause' (⏸), 'play' (▶), or 'cancel' (✕)."""

    def __init__(self, mode: str = "pause", size: int = 32, parent=None) -> None:
        super().__init__(parent)
        self._mode = mode  # "pause", "play", "cancel"
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        self.update()

    def mode(self) -> str:
        return self._mode

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
        if self._mode == "cancel":
            get_sound_service().play_cancel()
        else:
            get_sound_service().play_pause()
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        s = float(self.width())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(1.5, 1.5, s - 3.0, s - 3.0)
        if self._mode == "cancel":
            bg = QColor("#FFD8DF") if self._hover else QColor("#FFECEF")
            border = QColor("#F06277") if self._hover else QColor("#F8BBD0")
            fg = QColor("#D32F2F")
        else:
            bg = QColor("#D2E7FF") if self._hover else QColor("#EBF4FF")
            border = QColor("#64B5F6") if self._hover else QColor("#BBDEFB")
            fg = QColor("#1565C0")

        p.setPen(QPen(border, 1.3))
        p.setBrush(bg)
        p.drawEllipse(rect)

        cx, cy = s * 0.5, s * 0.5
        if self._mode == "pause":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fg)
            p.drawRoundedRect(QRectF(cx - 4.5, cy - 5.5, 3.0, 11.0), 1.0, 1.0)
            p.drawRoundedRect(QRectF(cx + 1.5, cy - 5.5, 3.0, 11.0), 1.0, 1.0)
        elif self._mode == "play":
            tri = QPainterPath()
            tri.moveTo(cx - 3.5, cy - 6.0)
            tri.lineTo(cx - 3.5, cy + 6.0)
            tri.lineTo(cx + 5.5, cy)
            tri.closeSubpath()
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(fg)
            p.fillPath(tri, fg)
        elif self._mode == "cancel":
            p.setPen(QPen(fg, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(cx - 4.2, cy - 4.2), QPointF(cx + 4.2, cy + 4.2))
            p.drawLine(QPointF(cx + 4.2, cy - 4.2), QPointF(cx - 4.2, cy + 4.2))
        p.end()
