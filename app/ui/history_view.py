"""History dialog styled in ClipDesk Sky-Blue theme & compatible with ClipDesk-source."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QFrame,
)

from app.core.models import TaskState
from app.services.sound_service import get_sound_service


class HistoryDialog(QDialog):
    """Displays completed/failed download history (supports DownloadTask objects and dicts)."""

    def __init__(self, records: list[Any], parent=None) -> None:
        super().__init__(parent)
        self._records = records or []
        self.was_cleared = False
        self.setWindowTitle("ประวัติการดาวน์โหลด — ClipDesk")
        self.resize(600, 440)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("🕒  ประวัติการดาวน์โหลด")
        title.setObjectName("sectionTitle")
        top.addWidget(title)
        top.addStretch(1)

        clear_btn = QPushButton("🗑  ล้างประวัติ")
        clear_btn.setObjectName("queueHeaderBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear)
        top.addWidget(clear_btn)
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(content)
        self._list_layout.setSpacing(8)

        if not self._records:
            empty = QLabel("ยังไม่มีประวัติการดาวน์โหลด")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet("color: #6B82A6; padding: 36px; font-size: 13px;")
            self._list_layout.addWidget(empty)
        else:
            for rec in self._records:
                card = self._build_record_card(rec)
                self._list_layout.addWidget(card)

        self._list_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_btn = QPushButton("ปิด")
        close_btn.setObjectName("queueHeaderBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def _build_record_card(self, rec: Any) -> QFrame:
        if isinstance(rec, dict):
            title_text = str(rec.get("title") or "ไม่ทราบชื่อ")
            output_path = str(rec.get("output_path") or "")
            is_ok = rec.get("state", TaskState.COMPLETED) == TaskState.COMPLETED
            ts = rec.get("completed_at") or rec.get("created_at")
        else:
            title_text = str(getattr(rec, "title", None) or "ไม่ทราบชื่อ")
            output_path = str(getattr(rec, "output_path", None) or "")
            state = getattr(rec, "state", TaskState.COMPLETED)
            is_ok = state == TaskState.COMPLETED
            ts = getattr(rec, "completed_at", None) or getattr(rec, "created_at", None)

        card = QFrame()
        card.setObjectName("whiteCard")
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        badge = QLabel("✓" if is_ok else "✗")
        badge.setFixedSize(26, 26)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {'#E8F5E9' if is_ok else '#FFEBEE'}; "
            f"color: {'#2E7D32' if is_ok else '#C62828'}; "
            "border-radius: 13px; font-weight: bold; font-size: 13px;"
        )
        row.addWidget(badge)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        lbl = QLabel(title_text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-weight: 700; color: #162B4D; font-size: 13px;")
        info_col.addWidget(lbl)

        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else ""
        status_str = "ดาวน์โหลดสำเร็จ" if is_ok else "ล้มเหลว"
        meta_text = f"{date_str} • {status_str}" if date_str else status_str
        meta_lbl = QLabel(meta_text)
        meta_lbl.setStyleSheet("color: #5C7498; font-size: 11.5px;")
        info_col.addWidget(meta_lbl)

        if output_path:
            path_lbl = QLabel(output_path)
            path_lbl.setWordWrap(True)
            path_lbl.setStyleSheet("color: #7A92B4; font-size: 11px;")
            info_col.addWidget(path_lbl)

        row.addLayout(info_col, 1)

        if output_path and os.path.isfile(output_path):
            open_btn = QPushButton("เปิดไฟล์")
            open_btn.setObjectName("queueHeaderBtn")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda _, p=output_path: os.startfile(p))
            row.addWidget(open_btn)

            folder_btn = QPushButton("เปิดโฟลเดอร์")
            folder_btn.setObjectName("queueHeaderBtn")
            folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            folder_btn.clicked.connect(
                lambda _, p=output_path: subprocess.Popen(
                    ["explorer", "/select,", p],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            )
            row.addWidget(folder_btn)

        return card

    def _on_clear(self) -> None:
        get_sound_service().play_cancel()
        self.was_cleared = True
        self.accept()
