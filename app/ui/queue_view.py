"""Queue view matching the ClipDesk mockup & compatible with ClipDesk-source."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
    QPushButton, QComboBox,
)

from app.core.models import DownloadTask, TaskState, DownloadProgress
from app.services.sound_service import get_sound_service
from app.ui.components.queue_item_widget import QueueItemWidget


class QueueView(QFrame):
    """
    White rounded card housing the download queue header and task cards.
    100% compatible with ClipDesk-source's QueueView methods.
    """

    clear_all_requested = Signal()
    pause_all_requested = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("whiteCard")
        self._items: dict[str, QueueItemWidget] = {}
        self._all_paused = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header Row: [ ☰ คิวดาวน์โหลด (N รายการ) ] ... [ จัดเรียง : ล่าสุดก่อน ⌄ ] [ 🗑 ล้างคิว ] [ ⏸ หยุดทั้งหมด ]
        header_row = QHBoxLayout()
        header_row.setSpacing(10)

        icon_lbl = QLabel("☰")
        icon_lbl.setStyleSheet("color: #1976D2; font-size: 16px; font-weight: bold;")
        header_row.addWidget(icon_lbl)

        self._header_title = QLabel("คิวดาวน์โหลด (0 รายการ)")
        self._header_title.setObjectName("sectionTitle")
        header_row.addWidget(self._header_title)

        header_row.addStretch(1)

        sort_lbl = QLabel("จัดเรียง :")
        sort_lbl.setStyleSheet("color: #5C7498; font-size: 12.5px;")
        header_row.addWidget(sort_lbl)

        self._sort_combo = QComboBox()
        self._sort_combo.setObjectName("sortCombo")
        self._sort_combo.addItems(["ล่าสุดก่อน", "เก่าสุดก่อน", "ชื่อไฟล์"])
        self._sort_combo.currentIndexChanged.connect(lambda _: get_sound_service().play_click())
        header_row.addWidget(self._sort_combo)

        self._clear_btn = QPushButton("🗑  ล้างคิว")
        self._clear_btn.setObjectName("queueHeaderBtn")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        header_row.addWidget(self._clear_btn)

        self._pause_all_btn = QPushButton("⏸  หยุดทั้งหมด")
        self._pause_all_btn.setObjectName("queueHeaderBtn")
        self._pause_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pause_all_btn.clicked.connect(self._on_pause_all_clicked)
        header_row.addWidget(self._pause_all_btn)

        layout.addLayout(header_row)

        # Subtle divider line
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #E3EEFA;")
        layout.addWidget(sep)

        # Scroll Area for Queue Items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scroll_content = QWidget()
        self._scroll_content.setStyleSheet("background: transparent;")
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setContentsMargins(0, 4, 2, 4)
        self._scroll_layout.setSpacing(8)
        self._scroll_layout.addStretch(1)

        scroll.setWidget(self._scroll_content)
        layout.addWidget(scroll, 1)

        # Empty State Label
        self._empty_label = QLabel("ยังไม่มีรายการดาวน์โหลด")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet("color: #7A92B4; padding: 24px; font-size: 13px;")
        self._scroll_layout.insertWidget(0, self._empty_label)

    def _refresh_header_count(self) -> None:
        count = len(self._items)
        self._header_title.setText(f"คิวดาวน์โหลด ({count} รายการ)")

    def _on_clear_clicked(self) -> None:
        get_sound_service().play_cancel()
        self.clear()
        self.clear_all_requested.emit()

    def _on_pause_all_clicked(self) -> None:
        get_sound_service().play_pause()
        self._all_paused = not self._all_paused
        self._pause_all_btn.setText("▶  เริ่มทั้งหมด" if self._all_paused else "⏸  หยุดทั้งหมด")
        for item in self._items.values():
            if item._paused != self._all_paused:
                item._on_toggle_pause()
        self.pause_all_requested.emit(self._all_paused)

    def add_task(self, task: DownloadTask, cancel_callback=None, retry_callback=None) -> QueueItemWidget:
        self._empty_label.hide()

        item = QueueItemWidget(task)
        if cancel_callback:
            item.cancel_requested.connect(cancel_callback)
        else:
            item.cancel_requested.connect(self.remove_task)
        if retry_callback:
            item.retry_requested.connect(retry_callback)

        self._items[task.task_id] = item
        self._scroll_layout.insertWidget(self._scroll_layout.count() - 1, item)
        self._refresh_header_count()
        return item

    def update_progress(self, task_id: str, progress: DownloadProgress) -> None:
        item = self._items.get(task_id)
        if item:
            item.update_progress(progress)

    def update_state(self, task_id: str, state: TaskState) -> None:
        item = self._items.get(task_id)
        if item:
            item.update_state(state)

    def remove_task(self, task_id: str) -> None:
        item = self._items.pop(task_id, None)
        if item:
            item.setParent(None)
            item.deleteLater()
        self._refresh_header_count()
        if not self._items:
            self._empty_label.show()

    def clear(self) -> None:
        for item in list(self._items.values()):
            item.setParent(None)
            item.deleteLater()
        self._items.clear()
        self._refresh_header_count()
        self._empty_label.show()
