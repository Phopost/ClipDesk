"""Settings dialog styled in ClipDesk Sky-Blue theme & compatible with ClipDesk-source."""

from __future__ import annotations

import os
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox,
    QCheckBox, QPushButton, QFrame, QFileDialog, QComboBox,
)

from app.services.sound_service import get_sound_service


class SettingsDialog(QDialog):
    """Application settings dialog (100% compatible with ClipDesk-source)."""

    settings_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = QSettings("ClipDesk", "ClipDesk")
        self.setWindowTitle("ตั้งค่า — ClipDesk")
        self.setMinimumWidth(440)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        title = QLabel("⚙  ตั้งค่าการใช้งาน")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("whiteCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(12)

        # Theme selection
        row_theme = QHBoxLayout()
        row_theme.addWidget(QLabel("ธีมหน้าต่าง:"))
        self._theme_combo = QComboBox()
        self._theme_combo.setObjectName("modernCombo")
        self._theme_combo.addItems(["Sky-Blue Glass (ค่าเริ่มต้น)", "Dark (โหมดมืด)"])
        dark = self.is_dark_theme()
        self._theme_combo.setCurrentIndex(1 if dark else 0)
        row_theme.addWidget(self._theme_combo)
        card_layout.addLayout(row_theme)

        # Concurrent downloads
        row_conc = QHBoxLayout()
        row_conc.addWidget(QLabel("จำนวนดาวน์โหลดพร้อมกันสูงสุด:"))
        self._concurrent_spin = QSpinBox()
        self._concurrent_spin.setRange(1, 5)
        self._concurrent_spin.setValue(self.get_max_concurrent())
        row_conc.addWidget(self._concurrent_spin)
        card_layout.addLayout(row_conc)

        # Default folder
        row_folder = QHBoxLayout()
        row_folder.addWidget(QLabel("โฟลเดอร์เริ่มต้น:"))
        self._folder_label = QLabel(self.get_default_directory())
        self._folder_label.setStyleSheet("color: #2B4266; font-size: 12px;")
        row_folder.addWidget(self._folder_label, 1)
        self._folder_btn = QPushButton("📁 เลือก")
        self._folder_btn.setObjectName("queueHeaderBtn")
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._choose_folder)
        row_folder.addWidget(self._folder_btn)
        card_layout.addLayout(row_folder)

        # Sound toggle
        self._sound_check = QCheckBox("เปิดเสียงเอฟเฟกต์และเสียงแจ้งเตือน (Sound Effects)")
        self._sound_check.setChecked(self.is_sound_enabled())
        card_layout.addWidget(self._sound_check)

        # Reduce motion toggle
        self._motion_check = QCheckBox("ลดการเคลื่อนไหวของอนิเมชั่น (Reduce Motion)")
        self._motion_check.setChecked(self.is_reduce_motion())
        card_layout.addWidget(self._motion_check)

        layout.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        cancel_btn = QPushButton("ยกเลิก")
        cancel_btn.setObjectName("queueHeaderBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("บันทึกการตั้งค่า")
        save_btn.setObjectName("checkUrlBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _choose_folder(self) -> None:
        get_sound_service().play_click()
        current = self._folder_label.text()
        folder = QFileDialog.getExistingDirectory(self, "เลือกโฟลเดอร์เริ่มต้น", current)
        if folder:
            self._folder_label.setText(folder)

    def _on_save(self) -> None:
        self._settings.setValue("theme_dark", self._theme_combo.currentIndex() == 1)
        self._settings.setValue("max_concurrent", self._concurrent_spin.value())
        self._settings.setValue("sound_enabled", self._sound_check.isChecked())
        self._settings.setValue("reduce_motion", self._motion_check.isChecked())
        self._settings.setValue("default_directory", self._folder_label.text())
        get_sound_service().set_enabled(self._sound_check.isChecked())
        get_sound_service().play_click()
        self.settings_changed.emit()
        self.accept()

    @staticmethod
    def is_dark_theme() -> bool:
        return bool(QSettings("ClipDesk", "ClipDesk").value("theme_dark", False, type=bool))

    @staticmethod
    def is_sound_enabled() -> bool:
        return bool(QSettings("ClipDesk", "ClipDesk").value("sound_enabled", True, type=bool))

    @staticmethod
    def get_max_concurrent() -> int:
        return int(QSettings("ClipDesk", "ClipDesk").value("max_concurrent", 3, type=int))

    @staticmethod
    def is_reduce_motion() -> bool:
        return bool(QSettings("ClipDesk", "ClipDesk").value("reduce_motion", False, type=bool))

    @staticmethod
    def get_default_directory() -> str:
        folder = QSettings("ClipDesk", "ClipDesk").value("default_directory", "")
        if not folder or not isinstance(folder, str):
            folder = os.path.join(os.path.expanduser("~"), "Videos")
        return folder
