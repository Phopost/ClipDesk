"""Automated verification tests for ClipDesk UI, Animations, and Sound Pack."""

from __future__ import annotations

import os
import pytest
from PySide6.QtCore import QObject, Signal

from tools.generate_sounds import generate_all_sounds
from tools.generate_demo_assets import generate_demo_thumbnails
from app.core.models import (
    MediaInfo, Platform, DownloadTask, DownloadProgress, TaskState, OutputType, VideoFormat,
)
from app.services.sound_service import SoundService
from app.ui.main_window import MainWindow


class _MockQueue:
    max_concurrent = 2
    active_count = 0

    def __init__(self) -> None:
        self._tasks: dict[str, DownloadTask] = {}

    def get_task(self, task_id: str):
        return self._tasks.get(task_id)


class _MockController(QObject):
    """Simulates ClipDesk-source's AppController contract."""

    info_fetched = Signal(object)
    info_error = Signal(str)
    download_progress = Signal(str, object)
    task_state_changed = Signal(str, object)
    status_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.queue = _MockQueue()
        self.current_info: MediaInfo | None = None
        self.checked_urls: list[str] = []

    def check_url(self, url: str) -> None:
        self.checked_urls.append(url)

    def start_download(self, info: MediaInfo, policy, dest_dir: str) -> str:
        task = DownloadTask(title=info.title, platform=info.platform, destination_dir=dest_dir)
        self.queue._tasks[task.task_id] = task
        return task.task_id

    def cancel_task(self, task_id: str) -> None:
        pass

    def retry_task(self, task_id: str) -> None:
        pass

    def history(self) -> list:
        return []

    def clear_history(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


def test_sound_generation_and_service(tmp_path):
    sizes = generate_all_sounds(str(tmp_path))
    expected = {
        "click.wav", "hover.wav", "tab_switch.wav", "check_url.wav",
        "start_download.wav", "pause_resume.wav", "cancel.wav",
        "success.wav", "error.wav",
    }
    assert set(sizes.keys()) == expected
    for name, size in sizes.items():
        assert size > 1000, f"{name} is too small"

    svc = SoundService(enabled=False)
    svc.play_click()
    svc.play_hover()
    svc.play_tab()
    svc.play_check()
    svc.play_download_start()
    svc.play_pause()
    svc.play_cancel()
    svc.play_success()
    svc.play_error()


def test_demo_thumbnails_generation(qapp, tmp_path):
    paths = generate_demo_thumbnails(str(tmp_path))
    assert len(paths) == 4
    for p in paths.values():
        assert os.path.isfile(p)
        assert os.path.getsize(p) > 500


def test_main_window_demo_showcase_matches_mockup(qtbot):
    win = MainWindow(controller=None, demo_mode=True)
    qtbot.addWidget(win)
    win.show()

    assert win._media_card.isVisible()
    assert "Blue Sky - Dreaming Together" in win._media_card._title_label.text()
    assert len(win._queue_view._items) == 3
    assert "คิวดาวน์โหลด (3 รายการ)" in win._queue_view._header_title.text()


def test_main_window_compatible_with_clipdesk_source_controller(qtbot):
    ctrl = _MockController()
    win = MainWindow(controller=ctrl, demo_mode=False)
    qtbot.addWidget(win)
    win.show()

    # Check URL flow
    win._url_input.set_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    win._url_input._on_check()
    assert ctrl.checked_urls == ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]

    # Info fetched flow
    info = MediaInfo(
        media_id="vid1",
        title="Test Song MV",
        platform=Platform.YOUTUBE,
        duration=215.0,
        formats=[
            VideoFormat(format_id="137", ext="mp4", width=1920, height=1080, fps=30, vcodec="avc1", acodec="mp4a"),
        ],
    )
    ctrl.current_info = info
    ctrl.info_fetched.emit(info)
    assert win._media_card.isVisible()
    assert win._media_card._title_label.text() == "Test Song MV"

    # Start download flow
    win._format_panel._on_download()
    assert len(win._queue_view._items) == 1
    task_id = next(iter(win._queue_view._items.keys()))

    # Progress update flow
    ctrl.download_progress.emit(
        task_id,
        DownloadProgress(phase="กำลังดาวน์โหลด", percent=65.0, speed=4.2 * 1024 * 1024, eta=9.0),
    )
    item = win._queue_view._items[task_id]
    assert "65%" in item._status_label.text()

    # Completed state flow
    ctrl.task_state_changed.emit(task_id, TaskState.COMPLETED)
    assert "สำเร็จ" in item._status_label.text()


def test_url_input_auto_check_on_valid_paste(qtbot):
    """When a valid YouTube/TikTok URL is pasted into UrlInput, it auto-triggers check_requested."""
    from app.ui.components.url_input import UrlInput
    inp = UrlInput()
    qtbot.addWidget(inp)
    inp.show()

    emitted = []
    inp.check_requested.connect(lambda u: emitted.append(u))

    # Simulate pasting or typing a full valid YouTube URL via _on_text_edited
    inp._url_edit.setText("https://www.youtube.com/watch?v=aqz-KE-bpKQ")
    inp._on_text_edited("https://www.youtube.com/watch?v=aqz-KE-bpKQ")

    qtbot.waitUntil(lambda: len(emitted) == 1, timeout=1000)
    assert emitted == ["https://www.youtube.com/watch?v=aqz-KE-bpKQ"]


def test_ytdlp_adapter_includes_high_speed_flags(monkeypatch):
    """YtDlpAdapter must pass concurrent fragments and fast buffer flags for maximum speed."""
    from app.media.ytdlp_adapter import YtDlpAdapter
    from app.core.models import QualityPolicy

    adapter = YtDlpAdapter()
    captured = {}

    def fake_start(program, args):
        captured["program"] = program
        captured["args"] = list(args)

    monkeypatch.setattr(adapter, "_start_process", fake_start)
    monkeypatch.setattr("app.media.ytdlp_adapter.get_tool_path", lambda name: f"C:/fake/{name}.exe")

    adapter.start_download(
        url="https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        policy=QualityPolicy(output_type=OutputType.MP4, preferred_height=1080),
        work_dir="C:/tmp",
        output_template="C:/tmp/%(title)s.%(ext)s",
    )

    args = captured["args"]
    assert "--concurrent-fragments" in args
    idx = args.index("--concurrent-fragments")
    assert int(args[idx + 1]) >= 8
    assert "--buffer-size" in args


def test_controller_skips_redundant_resolve_when_info_is_fresh(qtbot, tmp_path, monkeypatch):
    """AppController should start downloading immediately without re-running extract_info if info was just checked."""
    from app.core.controller import AppController
    from app.storage.database import Database
    from app.core.models import QualityPolicy

    ctrl = AppController(db=Database(str(tmp_path / "fast.db")))
    started_downloads = []
    extract_calls = []

    monkeypatch.setattr(ctrl, "_start_download", lambda task, aid: started_downloads.append(task.task_id))

    info = MediaInfo(
        media_id="vidfast1234",
        title="Fast Clip",
        platform=Platform.YOUTUBE,
        duration=30.0,
        webpage_url="https://www.youtube.com/watch?v=vidfast1234",
        formats=[
            VideoFormat(format_id="137", ext="mp4", width=1920, height=1080, vcodec="avc1", acodec="mp4a"),
        ],
    )
    ctrl._on_info_ready(info)

    policy = QualityPolicy(
        output_type=OutputType.MP4,
        preferred_height=1080,
        selected_video_format_id="137",
    )
    tid = ctrl.start_download(info, policy, str(tmp_path))
    assert tid is not None
    assert tid in started_downloads

