"""Format selection panel matching the ClipDesk mockup & compatible with ClipDesk-source."""

from __future__ import annotations

import os
from PySide6.QtCore import Signal, Qt, QSettings
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QFileDialog, QFrame, QLineEdit,
)

from app.core.models import MediaInfo, OutputType, QualityPolicy
from app.media.format_selector import (
    get_video_quality_options, get_audio_quality_options, AUDIO_BITRATE_MAP,
    QualityOption,
)
from app.services.sound_service import get_sound_service
from app.ui.themes.wave_widgets import GlossyDownloadButton


class FormatPanel(QWidget):
    """
    Horizontal row of 3 white cards (รูปแบบไฟล์, คุณภาพ, บันทึกไปที่)
    plus the glowing 3D 'เริ่มดาวน์โหลด' button.

    Signals:
        download_requested(QualityPolicy, str): policy and destination_dir
    """

    download_requested = Signal(object, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._media_info: MediaInfo | None = None
        self._video_options: list[QualityOption] = []
        self._settings = QSettings("ClipDesk", "ClipDesk")
        self._setup_ui()
        self.hide()

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)

        # ── Card 1: รูปแบบไฟล์ (MP4 / MP3) ──
        card_type = QFrame()
        card_type.setObjectName("optionCard")
        ct_layout = QVBoxLayout(card_type)
        ct_layout.setContentsMargins(12, 8, 12, 10)
        ct_layout.setSpacing(5)

        lbl_type = QLabel('<span style="color:#1976D2;">🎬</span>  รูปแบบไฟล์')
        lbl_type.setObjectName("cardFieldTitle")
        ct_layout.addWidget(lbl_type)

        self._type_combo = QComboBox()
        self._type_combo.setObjectName("modernCombo")
        self._type_combo.addItems(["MP4", "MP3 (เสียง)"])
        self._type_combo.setMinimumWidth(125)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        ct_layout.addWidget(self._type_combo)
        row.addWidget(card_type, 2)

        # ── Card 2: คุณภาพ (1080p Full HD) ──
        card_qual = QFrame()
        card_qual.setObjectName("optionCard")
        cq_layout = QVBoxLayout(card_qual)
        cq_layout.setContentsMargins(12, 8, 12, 10)
        cq_layout.setSpacing(5)

        lbl_qual = QLabel('<span style="color:#1976D2;">💎</span>  คุณภาพ')
        lbl_qual.setObjectName("cardFieldTitle")
        cq_layout.addWidget(lbl_qual)

        self._quality_combo = QComboBox()
        self._quality_combo.setObjectName("modernCombo")
        self._quality_combo.setMinimumWidth(155)
        self._quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        cq_layout.addWidget(self._quality_combo)
        row.addWidget(card_qual, 3)

        # ── Card 3: บันทึกไปที่ (D:\Videos\ClipDesk + folder button) ──
        card_folder = QFrame()
        card_folder.setObjectName("optionCard")
        cf_layout = QVBoxLayout(card_folder)
        cf_layout.setContentsMargins(12, 8, 12, 10)
        cf_layout.setSpacing(5)

        lbl_folder = QLabel('<span style="color:#1976D2;">📁</span>  บันทึกไปที่')
        lbl_folder.setObjectName("cardFieldTitle")
        cf_layout.addWidget(lbl_folder)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        self._folder_edit = QLineEdit()
        self._folder_edit.setObjectName("folderEdit")
        saved_dir = self._settings.value("last_directory", "")
        if saved_dir and os.path.isdir(saved_dir):
            self._folder_edit.setText(saved_dir)
        else:
            default_dir = r"D:\Videos\ClipDesk"
            self._folder_edit.setText(default_dir)
        folder_row.addWidget(self._folder_edit, 1)

        self._folder_btn = QPushButton("📁")
        self._folder_btn.setObjectName("folderIconBtn")
        self._folder_btn.setFixedSize(34, 30)
        self._folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._folder_btn.clicked.connect(self._on_choose_folder)
        folder_row.addWidget(self._folder_btn)
        cf_layout.addLayout(folder_row)
        row.addWidget(card_folder, 4)

        # ── Right: Glowing 3D 'เริ่มดาวน์โหลด' Button ──
        self._download_btn = GlossyDownloadButton("เริ่มดาวน์โหลด")
        self._download_btn.clicked.connect(self._on_download)
        row.addWidget(self._download_btn)

        outer.addLayout(row)

        # Hidden compatibility labels (kept for ClipDesk-source test compatibility)
        self._size_label = QLabel()
        self._size_label.hide()
        self._bitrate_note = QLabel(
            "การเลือก bitrate สูงขึ้นไม่ได้ทำให้ต้นฉบับที่คุณภาพต่ำกลายเป็นเสียงคุณภาพสูงขึ้น"
        )
        self._bitrate_note.hide()

        # Populate initial default quality options
        self._populate_default_qualities()

    def _populate_default_qualities(self) -> None:
        self._video_options = [
            QualityOption(label="1080p (Full HD)", height=1080, fps=30.0, codec_info="H.264", size_label="48.5 MB"),
            QualityOption(label="720p (HD)", height=720, fps=30.0, codec_info="H.264", size_label="24.0 MB"),
            QualityOption(label="480p (SD)", height=480, fps=30.0, codec_info="H.264", size_label="12.5 MB"),
        ]
        self._quality_combo.clear()
        for opt in self._video_options:
            self._quality_combo.addItem(opt.label)

    def show_for_media(self, info: MediaInfo) -> None:
        self._media_info = info
        self._on_type_changed(self._type_combo.currentIndex())
        self.show()

    def _on_type_changed(self, index: int) -> None:
        get_sound_service().play_click()
        self._quality_combo.clear()

        if index == 0:  # MP4
            self._bitrate_note.hide()
            if self._media_info:
                self._video_options = get_video_quality_options(
                    self._media_info, prefer_compatible=True
                )
                if not self._video_options:
                    self._video_options = get_video_quality_options(
                        self._media_info, prefer_compatible=False
                    )
                for opt in self._video_options:
                    self._quality_combo.addItem(opt.label)
                if not self._video_options:
                    self._quality_combo.addItem("ไม่พบรูปแบบที่รองรับ")
            else:
                self._populate_default_qualities()
        else:  # MP3
            self._bitrate_note.show()
            for opt in get_audio_quality_options():
                self._quality_combo.addItem(opt.label)
            if self._quality_combo.count() > 1:
                self._quality_combo.setCurrentIndex(1)

        self._update_size_label()

    def _on_quality_changed(self, index: int) -> None:
        self._update_size_label()

    def _update_size_label(self) -> None:
        is_mp4 = self._type_combo.currentIndex() == 0
        if is_mp4 and 0 <= self._quality_combo.currentIndex() < len(self._video_options):
            opt = self._video_options[self._quality_combo.currentIndex()]
            self._size_label.setText(f"ขนาดโดยประมาณ: {opt.size_label}")
        else:
            self._size_label.setText("")

    def _on_choose_folder(self) -> None:
        get_sound_service().play_click()
        current = self._folder_edit.text()
        if not os.path.isdir(current):
            current = os.path.expanduser("~")
        folder = QFileDialog.getExistingDirectory(
            self, "เลือกโฟลเดอร์สำหรับบันทึก", current
        )
        if folder:
            self._folder_edit.setText(folder)
            self._settings.setValue("last_directory", folder)

    def _on_download(self) -> None:
        dest_dir = self._folder_edit.text().strip()
        if not dest_dir:
            return
        # Ensure fallback folder exists if running real download
        if not os.path.isdir(dest_dir):
            fallback = os.path.join(os.path.expanduser("~"), "Videos")
            os.makedirs(fallback, exist_ok=True)
            dest_dir = fallback

        is_mp4 = self._type_combo.currentIndex() == 0
        quality_idx = self._quality_combo.currentIndex()

        if is_mp4:
            if quality_idx < 0 or quality_idx >= len(self._video_options):
                return
            opt = self._video_options[quality_idx]
            policy = QualityPolicy(
                output_type=OutputType.MP4,
                preferred_height=opt.height,
                prefer_compatible=True,
                selected_video_format_id=opt.video_format_id,
                selected_audio_format_id=opt.audio_format_id,
            )
        else:
            label = self._quality_combo.currentText()
            bitrate = AUDIO_BITRATE_MAP.get(label, 192)
            policy = QualityPolicy(
                output_type=OutputType.MP3,
                preferred_bitrate=bitrate,
            )

        self.download_requested.emit(policy, dest_dir)

    def get_destination_dir(self) -> str:
        return self._folder_edit.text()
