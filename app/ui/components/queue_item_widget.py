"""Queue item widget matching the ClipDesk mockup & compatible with ClipDesk-source."""

from __future__ import annotations

import os
import subprocess
from PySide6.QtCore import Signal, Qt, QRectF, QPointF
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QLinearGradient
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget,
)

from app.core.models import DownloadTask, TaskState, DownloadProgress
from app.services.app_paths import asset_path
from app.ui.themes.wave_widgets import AnimatedProgressBar, CircularActionButton


class _RoundedThumbLabel(QWidget):
    """88x50 rounded 16:9 thumbnail for queue items."""

    def __init__(self, pixmap: QPixmap | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(92, 52)
        self._pixmap = pixmap

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event) -> None:
        w = float(self.width())
        h = float(self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        clip = QPainterPath()
        clip.addRoundedRect(QRectF(0, 0, w, h), 8.0, 8.0)
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
            grad.setColorAt(0.0, QColor("#569BE8"))
            grad.setColorAt(1.0, QColor("#235D9F"))
            p.fillRect(QRectF(0, 0, w, h), grad)
        p.end()


class QueueItemWidget(QFrame):
    """
    Widget for one download task in the queue (matches the reference mockup).

    Signals:
        cancel_requested(str): task_id
        retry_requested(str): task_id
        pause_toggled(str, bool): task_id, is_paused
    """

    cancel_requested = Signal(str)
    retry_requested = Signal(str)
    pause_toggled = Signal(str, bool)

    def __init__(self, task: DownloadTask, parent=None) -> None:
        super().__init__(parent)
        self._task = task
        self._paused = False
        self.setObjectName("queueItemCard")
        self._setup_ui()
        self._update_state()

    def _setup_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 12, 8)
        row.setSpacing(14)

        # 1. Left Thumbnail
        self._thumb = _RoundedThumbLabel(self._resolve_thumbnail())
        row.addWidget(self._thumb)

        # 2. Middle Column: Title + Status/Speed/ETA + Progress Bar
        mid_col = QVBoxLayout()
        mid_col.setContentsMargins(0, 1, 0, 1)
        mid_col.setSpacing(4)

        self._title_label = QLabel(self._task.title)
        self._title_label.setStyleSheet("font-weight: 800; font-size: 13.5px; color: #162B4D;")
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        mid_col.addWidget(self._title_label)

        # Combined info line ("กำลังดาวน์โหลด...  45%  •  6.1 MB/s  •  เหลือประมาณ 00:00:12" or "รอคิว...")
        info_row = QHBoxLayout()
        info_row.setContentsMargins(0, 0, 0, 0)
        info_row.setSpacing(6)

        self._status_label = QLabel("รอคิว...")
        self._status_label.setStyleSheet("font-size: 12px; color: #4A6388; font-weight: 600;")
        info_row.addWidget(self._status_label)

        self._phase_label = QLabel()
        self._phase_label.hide()
        self._speed_label = QLabel()
        self._speed_label.hide()
        self._eta_label = QLabel()
        self._eta_label.hide()

        self._error_label = QLabel()
        self._error_label.setObjectName("errorLabel")
        self._error_label.hide()
        info_row.addWidget(self._error_label)

        info_row.addStretch(1)
        mid_col.addLayout(info_row)

        # Smooth animated progress bar
        self._progress_bar = AnimatedProgressBar()
        mid_col.addWidget(self._progress_bar)

        row.addLayout(mid_col, 1)

        # 3. Right Action Buttons: Circular (⏸ / ▶) + Circular (✕)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._pause_play_btn = CircularActionButton("pause", 32)
        self._pause_play_btn.clicked.connect(self._on_toggle_pause)
        btn_row.addWidget(self._pause_play_btn)

        self._cancel_btn = CircularActionButton("cancel", 32)
        self._cancel_btn.clicked.connect(lambda: self.cancel_requested.emit(self._task.task_id))
        btn_row.addWidget(self._cancel_btn)

        # Compatibility buttons for completed/failed states in ClipDesk-source
        self._detail_btn = QPushButton("ดูรายละเอียด")
        self._detail_btn.setObjectName("queueHeaderBtn")
        self._detail_btn.clicked.connect(self._show_error_detail)
        self._detail_btn.hide()
        btn_row.addWidget(self._detail_btn)

        self._open_file_btn = QPushButton("เปิดไฟล์")
        self._open_file_btn.setObjectName("queueHeaderBtn")
        self._open_file_btn.clicked.connect(self._open_file)
        self._open_file_btn.hide()
        btn_row.addWidget(self._open_file_btn)

        self._open_folder_btn = QPushButton("เปิดโฟลเดอร์")
        self._open_folder_btn.setObjectName("queueHeaderBtn")
        self._open_folder_btn.clicked.connect(self._open_folder)
        self._open_folder_btn.hide()
        btn_row.addWidget(self._open_folder_btn)

        self._retry_btn = QPushButton("ลองใหม่")
        self._retry_btn.setObjectName("queueHeaderBtn")
        self._retry_btn.clicked.connect(lambda: self.retry_requested.emit(self._task.task_id))
        self._retry_btn.hide()
        btn_row.addWidget(self._retry_btn)

        row.addLayout(btn_row)

    def _resolve_thumbnail(self) -> QPixmap | None:
        thumb_path = getattr(self._task, "thumbnail_path", None)
        if thumb_path and os.path.isfile(thumb_path):
            return QPixmap(thumb_path)
        media_info = getattr(self._task, "media_info", None)
        thumb_url = getattr(media_info, "thumbnail_url", None) if media_info else None
        if thumb_url:
            if os.path.isfile(thumb_url):
                return QPixmap(thumb_url)
            try:
                from app.services.thumbnail_service import ThumbnailService
                self._thumb_svc = ThumbnailService(parent=self)
                cached = self._thumb_svc.cached(thumb_url)
                if cached is not None:
                    return cached
                self._thumb_svc.thumbnail_ready.connect(
                    lambda u, px: self._thumb.set_pixmap(px) if u == thumb_url else None
                )
                self._thumb_svc.request(thumb_url)
            except Exception:
                pass
        title_low = (self._task.title or "").lower()
        if "cat" in title_low or "แมว" in title_low:
            fallback = asset_path("thumbnails", "queue_cat.png")
        elif "ญี่ปุ่น" in title_low or "japan" in title_low:
            fallback = asset_path("thumbnails", "queue_japan.png")
        else:
            fallback = asset_path("thumbnails", "queue_chill.png")
        if os.path.isfile(fallback):
            return QPixmap(fallback)
        return None

    def _on_toggle_pause(self) -> None:
        if self._task.state == TaskState.FAILED:
            self.retry_requested.emit(self._task.task_id)
            return
        self._paused = not self._paused
        if self._paused:
            self._pause_play_btn.set_mode("play")
            self._status_label.setText("หยุดชั่วคราว...")
        else:
            self._pause_play_btn.set_mode("pause")
            if self._task.progress and self._task.progress.percent:
                self.update_progress(self._task.progress)
            else:
                self._status_label.setText("กำลังดาวน์โหลด...")
        self.pause_toggled.emit(self._task.task_id, self._paused)

    def update_progress(self, progress: DownloadProgress) -> None:
        self._task.progress = progress
        pct = progress.percent if progress.percent is not None else 0.0
        self._progress_bar.setValue(pct, animated=True)

        parts = ["กำลังดาวน์โหลด..."]
        if progress.percent is not None:
            parts.append(f"  {int(round(progress.percent))}%")
        if progress.speed:
            parts.append(f"  •  {_format_speed(progress.speed)}")
        if progress.eta is not None:
            parts.append(f"  •  เหลือประมาณ {_format_eta_clock(progress.eta)}")

        self._status_label.setText("".join(parts))
        self._status_label.setStyleSheet("font-size: 12px; color: #1967D2; font-weight: 600;")

    def update_state(self, state: TaskState) -> None:
        self._task.state = state
        self._update_state()

    def _update_state(self) -> None:
        state = self._task.state
        if state == TaskState.QUEUED:
            self._status_label.setText("รอคิว...")
            self._status_label.setStyleSheet("font-size: 12px; color: #647D9E; font-weight: 600;")
            self._pause_play_btn.set_mode("play")
            self._progress_bar.setValue(0, animated=False)
        elif state == TaskState.DOWNLOADING:
            self._pause_play_btn.set_mode("pause")
            if self._task.progress and self._task.progress.percent is not None:
                self.update_progress(self._task.progress)
            else:
                self._status_label.setText("กำลังดาวน์โหลด...")
                self._status_label.setStyleSheet("font-size: 12px; color: #1967D2; font-weight: 600;")
        elif state in (TaskState.RESOLVING, TaskState.POSTPROCESSING, TaskState.VERIFYING):
            self._pause_play_btn.set_mode("pause")
            labels = {
                TaskState.RESOLVING: "กำลังตรวจสอบลิงก์...",
                TaskState.POSTPROCESSING: "กำลังรวมไฟล์...",
                TaskState.VERIFYING: "กำลังตรวจสอบไฟล์...",
            }
            self._status_label.setText(labels[state])
            self._status_label.setStyleSheet("font-size: 12px; color: #1967D2; font-weight: 600;")
        elif state == TaskState.COMPLETED:
            self._status_label.setText("ดาวน์โหลดสำเร็จ ✓")
            self._status_label.setStyleSheet("font-size: 12px; color: #2E7D32; font-weight: 700;")
            self._progress_bar.setValue(100, animated=True)
        elif state == TaskState.CANCELLED:
            self._status_label.setText("ยกเลิกแล้ว")
            self._status_label.setStyleSheet("font-size: 12px; color: #78909C; font-weight: 600;")
        elif state == TaskState.FAILED:
            msg = f"ล้มเหลว ✗ ({self._task.error_message})" if self._task.error_message else "ล้มเหลว ✗"
            self._status_label.setText(msg)
            self._status_label.setStyleSheet("font-size: 12px; color: #D32F2F; font-weight: 700;")
            self._pause_play_btn.set_mode("play")

        is_done_or_fail = state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)
        self._cancel_btn.setVisible(not is_done_or_fail)
        self._pause_play_btn.setVisible(not is_done_or_fail)
        self._retry_btn.setVisible(state == TaskState.FAILED)
        self._open_file_btn.setVisible(state == TaskState.COMPLETED and bool(self._task.output_path))
        self._open_folder_btn.setVisible(state == TaskState.COMPLETED and bool(self._task.output_path))
        self._detail_btn.setVisible(state == TaskState.FAILED and bool(self._task.error_detail))

    def _show_error_detail(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(self)
        box.setWindowTitle("รายละเอียดข้อผิดพลาด")
        box.setText(self._task.error_message or "")
        box.setDetailedText(self._task.error_detail or "")
        box.exec()

    def _open_file(self) -> None:
        if self._task.output_path and os.path.isfile(self._task.output_path):
            os.startfile(self._task.output_path)

    def _open_folder(self) -> None:
        if self._task.output_path and os.path.isfile(self._task.output_path):
            subprocess.Popen(
                ["explorer", "/select,", self._task.output_path],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

    @property
    def task_id(self) -> str:
        return self._task.task_id


def _format_speed(bps: float) -> str:
    if bps < 1024:
        return f"{bps:.0f} B/s"
    elif bps < 1024 * 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{bps / (1024 * 1024):.1f} MB/s"


def _format_eta_clock(seconds: float) -> str:
    total = max(0, int(seconds))
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
