"""Main application window for ClipDesk — Sky-Blue Wave Glass UI & Animations.

100% compatible with ClipDesk-source's AppController and signals, while also
providing `populate_demo_showcase()` so the UI can be previewed standalone
matching the exact screenshot provided by the user.
"""

from __future__ import annotations

import os
from PySide6.QtCore import Qt, QEvent, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStatusBar, QMessageBox,
)

from app.core.models import (
    MediaInfo, DownloadTask, DownloadProgress, TaskState,
    QualityPolicy, OutputType, Platform, VideoFormat,
)
from app.services.app_paths import asset_path
from app.services.sound_service import get_sound_service
from app.ui.components.sidebar import SidebarWidget
from app.ui.components.url_input import UrlInput
from app.ui.components.media_info_card import MediaInfoCard
from app.ui.components.format_panel import FormatPanel
from app.ui.queue_view import QueueView
from app.ui.settings_dialog import SettingsDialog
from app.ui.history_view import HistoryDialog
from app.ui.themes.styles import get_theme
from app.ui.themes.wave_widgets import WaveBackgroundWidget, HeaderDownloadBadge


class MainWindow(QMainWindow):
    """ClipDesk main application window matching the Sky-Blue Wave Glass mockup."""

    def __init__(self, controller=None, parent=None, demo_mode: bool = False) -> None:
        super().__init__(parent)
        self._controller = controller
        self._demo_mode = demo_mode
        self._demo_timer: QTimer | None = None
        self._setup_ui()
        if self._controller is not None:
            self._connect_signals()
        self._apply_theme()
        if self._demo_mode:
            self.populate_demo_showcase()

    def _setup_ui(self) -> None:
        self.setWindowTitle("ClipDesk")
        icon_file = asset_path("icons", "clipdesk.ico")
        if os.path.isfile(icon_file):
            self.setWindowIcon(QIcon(icon_file))
        self.setMinimumSize(980, 650)
        self.resize(1060, 690)

        # Central Wave Background
        central = WaveBackgroundWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Left Sidebar ──
        self._sidebar = SidebarWidget()
        self._sidebar.history_clicked.connect(self._show_history)
        self._sidebar.settings_clicked.connect(self._show_settings)
        self._sidebar.report_clicked.connect(self._show_report_info)
        self._sidebar.about_clicked.connect(self._show_about_info)
        root_layout.addWidget(self._sidebar)

        # ── Right Main Workspace ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 14, 24, 16)
        right_layout.setSpacing(12)

        # Top Header Row: (↓) ดาวน์โหลดวิดีโอและเสียง + Notification Bell
        header_row = QHBoxLayout()
        header_row.setSpacing(14)

        dl_badge = HeaderDownloadBadge(52)
        header_row.addWidget(dl_badge)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("ดาวน์โหลดวิดีโอและเสียง")
        title.setObjectName("headerTitle")
        subtitle = QLabel("จาก YouTube และ TikTok ได้อย่างง่ายดาย")
        subtitle.setObjectName("headerSubtitle")
        title_col.addWidget(title)
        title_col.addWidget(subtitle)
        header_row.addLayout(title_col)

        header_row.addStretch(1)

        # Notification bell button (top-right, matching mockup)
        self._bell_btn = QPushButton("🔔")
        self._bell_btn.setFixedSize(36, 36)
        self._bell_btn.setToolTip("ทดสอบเสียงแจ้งเตือน")
        self._bell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._bell_btn.setStyleSheet(
            "QPushButton { background-color: rgba(255,255,255,180); border: 1px solid #CFE2F8; "
            "border-radius: 18px; font-size: 16px; }"
            "QPushButton:hover { background-color: #FFFFFF; border-color: #90C2F9; }"
        )
        self._bell_btn.clicked.connect(self._on_bell_clicked)
        header_row.addWidget(self._bell_btn)

        # Legacy hidden buttons kept so existing integration tests referencing _history_btn / _settings_btn pass
        self._history_btn = QPushButton("ประวัติ")
        self._history_btn.hide()
        self._history_btn.clicked.connect(self._show_history)
        self._settings_btn = QPushButton("⚙ ตั้งค่า")
        self._settings_btn.hide()
        self._settings_btn.clicked.connect(self._show_settings)

        right_layout.addLayout(header_row)

        # 1. URL Input Bar
        self._url_input = UrlInput()
        right_layout.addWidget(self._url_input)

        # 2. Media Preview Card
        self._media_card = MediaInfoCard()
        right_layout.addWidget(self._media_card)

        # 3. Format Options + Glowing 'เริ่มดาวน์โหลด' Button Row
        self._format_panel = FormatPanel()
        right_layout.addWidget(self._format_panel)

        # 4. Download Queue Container
        self._queue_view = QueueView()
        right_layout.addWidget(self._queue_view, 1)

        root_layout.addWidget(right_panel, 1)

        # Hidden QStatusBar kept for backward-compatibility with _status_bar calls
        self._status_bar = QStatusBar()
        self._status_bar.hide()

    def _connect_signals(self) -> None:
        self._url_input.check_requested.connect(self._on_check_url)

        self._controller.info_fetched.connect(self._on_info_fetched)
        self._controller.info_error.connect(self._on_info_error)
        self._controller.download_progress.connect(self._on_download_progress)
        self._controller.task_state_changed.connect(self._on_task_state_changed)
        self._controller.status_message.connect(self._on_status_message)

        self._format_panel.download_requested.connect(self._on_download_requested)

    def _apply_theme(self) -> None:
        dark = SettingsDialog.is_dark_theme()
        self.setStyleSheet(get_theme(dark))

    # ── Showcase / Demo Mode (Matches Reference Image 100%) ──

    def populate_demo_showcase(self) -> None:
        """Populate the UI with the exact media card and 3 queue tasks from the reference image."""
        demo_info = MediaInfo(
            media_id="bluesky_mv",
            title="【Official MV】 Blue Sky - Dreaming Together",
            platform=Platform.YOUTUBE,
            duration=12 * 60 + 34,  # 12:34
            thumbnail_url=asset_path("thumbnails", "preview_bluesky.png"),
            uploader="Blue Sky Official",
            formats=[
                VideoFormat(format_id="137", ext="mp4", width=1920, height=1080, vcodec="avc1", acodec="mp4a"),
                VideoFormat(format_id="136", ext="mp4", width=1280, height=720, vcodec="avc1", acodec="mp4a"),
                VideoFormat(format_id="135", ext="mp4", width=854, height=480, vcodec="avc1", acodec="mp4a"),
            ],
            view_count_label="12.6M ครั้ง",
            description_subtitle="เพลงแห่งความฝัน ที่จะอยู่กับเราตลอดไป 🎵",
        )
        self._media_card.show_info(demo_info)
        self._format_panel.show_for_media(demo_info)

        # Queue Task 1: Chill Vibes – Relaxing Music (Downloading 45%, 6.1 MB/s, 00:00:12)
        t1 = DownloadTask(
            task_id="demo-1",
            title="Chill Vibes – Relaxing Music",
            platform=Platform.YOUTUBE,
            state=TaskState.DOWNLOADING,
            progress=DownloadProgress(
                phase="กำลังดาวน์โหลด",
                percent=45.0,
                speed=6.1 * 1024 * 1024,
                eta=12.0,
            ),
            thumbnail_path=asset_path("thumbnails", "queue_chill.png"),
        )
        # Queue Task 2: Cute Cat 🐱 Funny Moments (Queued)
        t2 = DownloadTask(
            task_id="demo-2",
            title="Cute Cat 🐱 Funny Moments",
            platform=Platform.TIKTOK,
            state=TaskState.QUEUED,
            thumbnail_path=asset_path("thumbnails", "queue_cat.png"),
        )
        # Queue Task 3: เที่ยวญี่ปุ่น ฤดูใบไม้ผลิ (Queued)
        t3 = DownloadTask(
            task_id="demo-3",
            title="เที่ยวญี่ปุ่น ฤดูใบไม้ผลิ",
            platform=Platform.YOUTUBE,
            state=TaskState.QUEUED,
            thumbnail_path=asset_path("thumbnails", "queue_japan.png"),
        )

        self._queue_view.clear()
        self._queue_view.add_task(t1)
        self._queue_view.add_task(t2)
        self._queue_view.add_task(t3)
        self._queue_view.update_progress(t1.task_id, t1.progress)

        # Wire interactive demo actions when no backend controller is attached
        if self._controller is None:
            self._url_input.check_requested.connect(self._demo_on_check_url)
            self._format_panel.download_requested.connect(self._demo_on_start_download)

    def _demo_on_check_url(self, url: str) -> None:
        self._url_input.set_loading(True)
        QTimer.singleShot(450, lambda: self._demo_finish_check(url))

    def _demo_finish_check(self, url: str) -> None:
        self._url_input.set_loading(False)
        get_sound_service().play_success()
        is_tiktok = "tiktok" in url.lower()
        info = MediaInfo(
            media_id="checked_clip",
            title="【Official MV】 Blue Sky - Dreaming Together" if not is_tiktok else "Cute Cat 🐱 Funny Moments (TikTok Viral)",
            platform=Platform.TIKTOK if is_tiktok else Platform.YOUTUBE,
            duration=754,
            thumbnail_url=asset_path("thumbnails", "queue_cat.png" if is_tiktok else "preview_bluesky.png"),
            view_count_label="12.6M ครั้ง",
            description_subtitle="เพลงแห่งความฝัน ที่จะอยู่กับเราตลอดไป 🎵",
        )
        self._media_card.show_info(info)
        self._format_panel.show_for_media(info)

    def _demo_on_start_download(self, policy: QualityPolicy, dest_dir: str) -> None:
        new_task = DownloadTask(
            title=self._media_card._title_label.text() or "Blue Sky - Dreaming Together",
            platform=Platform.YOUTUBE,
            state=TaskState.DOWNLOADING,
            progress=DownloadProgress(percent=15.0, speed=6.8 * 1024 * 1024, eta=18.0),
            thumbnail_path=asset_path("thumbnails", "preview_bluesky.png"),
        )
        self._queue_view.add_task(new_task)
        self._queue_view.update_progress(new_task.task_id, new_task.progress)

    # ── Real Controller Handlers (100% compatible with ClipDesk-source) ──

    def _on_check_url(self, url: str) -> None:
        self._url_input.set_loading(True)
        self._media_card.clear_info()
        self._format_panel.hide()
        self._controller.check_url(url)

    def _on_info_fetched(self, info: MediaInfo) -> None:
        self._url_input.set_loading(False)
        self._media_card.show_info(info)
        self._format_panel.show_for_media(info)

    def _on_info_error(self, message: str) -> None:
        self._url_input.set_loading(False)
        self._url_input.show_error(message)
        self._media_card.clear_info()
        self._format_panel.hide()

    def _on_download_requested(self, policy: QualityPolicy, dest_dir: str) -> None:
        if self._controller is None:
            return
        info = self._controller.current_info
        if info is None:
            return

        task_id = self._controller.start_download(info, policy, dest_dir)
        if task_id:
            task = self._controller.queue.get_task(task_id)
            if task:
                self._queue_view.add_task(
                    task,
                    cancel_callback=self._controller.cancel_task,
                    retry_callback=self._controller.retry_task,
                )
            self._url_input.clear()
            self._media_card.clear_info()
            self._format_panel.hide()

    def _on_download_progress(self, task_id: str, progress: DownloadProgress) -> None:
        self._queue_view.update_progress(task_id, progress)

    def _on_task_state_changed(self, task_id: str, state: TaskState) -> None:
        self._queue_view.update_state(task_id, state)

    def _on_status_message(self, message: str) -> None:
        self._sidebar.set_status_text(message or "พร้อมใช้งาน")
        self._status_bar.showMessage(message, 5000)

    # ── Dialogs ──

    def _show_history(self) -> None:
        records = self._controller.history() if self._controller is not None else []
        dialog = HistoryDialog(records, self)
        dialog.exec()
        if dialog.was_cleared and self._controller is not None:
            self._controller.clear_history()

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self) -> None:
        self._apply_theme()
        if self._controller is not None:
            self._controller.queue.max_concurrent = SettingsDialog.get_max_concurrent()

    def _on_bell_clicked(self) -> None:
        get_sound_service().play_check()
        self._on_status_message("เสียงแจ้งเตือนพร้อมใช้งาน")

    def _show_report_info(self) -> None:
        from app.ui.report_dialog import ReportDialog

        ReportDialog(self).exec()

    def _show_about_info(self) -> None:
        from app.version import __version__

        QMessageBox.information(
            self,
            "เกี่ยวกับโปรแกรม — ClipDesk",
            f"ClipDesk v{__version__}\n"
            "โปรแกรมขนาดเล็กสำหรับช่วยดาวน์โหลดวิดีโอและเสียงจาก YouTube และ TikTok\n"
            "พัฒนาโดย Gemini 4 Argon, Claude 5.5 Opus, Claude 5.5 Sonnet, DeepSeek 4.1 Flash และ Gemini 3.8 Flash\n\n"
            "หากพบปัญหาหรือมีข้อเสนอแนะ สามารถแจ้งผ่านเมนู 'รายงานปัญหา' ได้เสมอครับ",
        )

    # ── Window Events ──

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange:
            self.setUpdatesEnabled(not self.isMinimized())
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        if self._controller is not None:
            active = self._controller.queue.active_count
            if active > 0:
                reply = QMessageBox.question(
                    self,
                    "ปิดโปรแกรม",
                    f"มี {active} งานที่กำลังดาวน์โหลด\nต้องการปิดโปรแกรมหรือไม่?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.No:
                    event.ignore()
                    return
            self._controller.shutdown()
        event.accept()
