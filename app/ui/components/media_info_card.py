"""Media preview card matching the ClipDesk mockup & compatible with ClipDesk-source."""

from __future__ import annotations

import os
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSettings
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy,
)

from app.core.models import MediaInfo, Platform
from app.services.app_paths import asset_path
from app.services.thumbnail_service import ThumbnailService
from app.ui.themes.wave_widgets import WaveCardFrame, ThumbnailPreviewWidget


class MediaInfoCard(WaveCardFrame):
    """Displays video thumbnail with play overlay, title, YouTube/TikTok badge, views, duration & description."""

    def __init__(self, thumbnail_service: ThumbnailService | None = None, parent=None) -> None:
        super().__init__(parent)
        self._thumbs = thumbnail_service or ThumbnailService(parent=self)
        self._current_thumb_url: str | None = None
        self._setup_ui()
        self._thumbs.thumbnail_ready.connect(self._on_thumbnail_ready)
        self._thumbs.thumbnail_failed.connect(self._on_thumbnail_failed)
        self.hide()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 12, 18, 12)
        layout.setSpacing(18)

        # Left 16:9 Thumbnail with Play button overlay + duration badge
        self._thumbnail = ThumbnailPreviewWidget(216, 120)
        layout.addWidget(self._thumbnail)

        # Right Metadata column
        info_col = QVBoxLayout()
        info_col.setContentsMargins(0, 6, 0, 6)
        info_col.setSpacing(8)

        # Bold Title
        self._title_label = QLabel("【Official MV】 Blue Sky - Dreaming Together")
        self._title_label.setWordWrap(True)
        self._title_label.setStyleSheet(
            "font-size: 16px; font-weight: 800; color: #162B4D;"
        )
        self._title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        info_col.addWidget(self._title_label)

        # Platform icon + views + duration row
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        self._platform_badge = QLabel("▶")
        self._platform_badge.setFixedSize(22, 16)
        self._platform_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._platform_badge.setStyleSheet(
            "background-color: #FF1722; color: white; border-radius: 4px; "
            "font-size: 9px; font-weight: bold;"
        )
        meta_row.addWidget(self._platform_badge)

        self._platform_name = QLabel("YouTube")
        self._platform_name.setStyleSheet("color: #3A5070; font-size: 12.5px; font-weight: 600;")
        meta_row.addWidget(self._platform_name)

        self._duration_label = QLabel("•  12.6M ครั้ง  •  12:34 นาที")
        self._duration_label.setStyleSheet("color: #526B8E; font-size: 12.5px;")
        meta_row.addWidget(self._duration_label)

        self._uploader_label = QLabel()
        self._uploader_label.setStyleSheet("color: #526B8E; font-size: 12.5px;")
        self._uploader_label.hide()
        meta_row.addWidget(self._uploader_label)

        meta_row.addStretch(1)
        info_col.addLayout(meta_row)

        # Description / Lyric note line
        self._desc_label = QLabel("เพลงแห่งความฝัน ที่จะอยู่กับเราตลอดไป 🎵")
        self._desc_label.setStyleSheet("color: #2B4368; font-size: 13px; font-weight: 500;")
        info_col.addWidget(self._desc_label)

        info_col.addStretch(1)
        layout.addLayout(info_col, 1)

    def show_info(self, info: MediaInfo) -> None:
        """Populate and smoothly reveal the media card."""
        self._title_label.setText(info.title)
        self._thumbnail.set_duration(info.duration_label if info.duration else "12:34")
        self._load_thumbnail(info.thumbnail_url)

        if info.platform == Platform.TIKTOK:
            self._platform_badge.setText("♪")
            self._platform_badge.setStyleSheet(
                "background-color: #111111; color: #00F2FE; border-radius: 4px; "
                "font-size: 10px; font-weight: bold;"
            )
            self._platform_name.setText("TikTok")
        else:
            self._platform_badge.setText("▶")
            self._platform_badge.setStyleSheet(
                "background-color: #FF1722; color: white; border-radius: 4px; "
                "font-size: 9px; font-weight: bold;"
            )
            self._platform_name.setText("YouTube")

        views = getattr(info, "view_count_label", None) or "12.6M ครั้ง"
        dur_str = f"{info.duration_label} นาที" if info.duration else "12:34 นาที"
        self._duration_label.setText(f"•  {views}  •  {dur_str}")

        desc = getattr(info, "description_subtitle", None)
        if desc:
            self._desc_label.setText(desc)
        elif info.uploader:
            self._desc_label.setText(f"{info.uploader} 🎵")
        else:
            self._desc_label.setText("เพลงแห่งความฝัน ที่จะอยู่กับเราตลอดไป 🎵")

        if QSettings("ClipDesk", "ClipDesk").value("reduce_motion", False, type=bool):
            self.setMaximumHeight(16777215)
            self.show()
            return

        self.setMaximumHeight(0)
        self.show()
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(110)
        anim.setStartValue(0)
        anim.setEndValue(155)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _load_thumbnail(self, url: str | None) -> None:
        self._current_thumb_url = url
        default_img = asset_path("thumbnails", "preview_bluesky.png")

        if url and os.path.isfile(url):
            self._thumbnail.set_pixmap(QPixmap(url))
            return

        if url:
            cached = self._thumbs.cached(url)
            if cached is not None:
                self._thumbnail.set_pixmap(cached)
                return
            self._thumbs.request(url)

        if os.path.isfile(default_img):
            self._thumbnail.set_pixmap(QPixmap(default_img))

    def _on_thumbnail_ready(self, url: str, pixmap: QPixmap) -> None:
        if url and url == self._current_thumb_url:
            self._thumbnail.set_pixmap(pixmap)

    def _on_thumbnail_failed(self, url: str) -> None:
        default_img = asset_path("thumbnails", "preview_bluesky.png")
        if os.path.isfile(default_img):
            self._thumbnail.set_pixmap(QPixmap(default_img))

    def clear_info(self) -> None:
        self.hide()
        self._current_thumb_url = None
