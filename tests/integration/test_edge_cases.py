"""Edge-case behaviour: unwritable folders, disk full, dead links, offline."""

import collections
import ctypes
import os

import pytest

from app.core.controller import AppController
from app.core.errors import ErrorCode, classify_ytdlp_error
from app.core.models import MediaInfo, OutputType, Platform, QualityPolicy
from app.services import path_service
from app.storage.database import Database


def _admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


# ── permission denied ──

@pytest.mark.skipif(_admin(), reason="administrators can write to System32")
def test_unwritable_directory_is_rejected():
    target = r"C:\Windows\System32\config"
    if not os.path.isdir(target):
        pytest.skip("System32 config folder not present")
    assert path_service.check_write_permission(target) is False


def test_controller_rejects_unwritable_destination(qapp, qtbot, tmp_path):
    db = Database(str(tmp_path / "edge.db"))
    controller = AppController(db=db)

    info = MediaInfo(
        media_id="abc",
        title="ทดสอบ",
        platform=Platform.YOUTUBE,
        webpage_url="https://www.youtube.com/watch?v=abc",
    )
    policy = QualityPolicy(output_type=OutputType.MP4)

    target = r"C:\Windows\System32\config"
    if _admin() or not os.path.isdir(target):
        pytest.skip("needs a non-admin account")

    with qtbot.waitSignal(controller.info_error, timeout=2000) as blocker:
        task_id = controller.start_download(info, policy, target)

    assert task_id is None
    assert "บันทึก" in blocker.args[0]
    db.close()


# ── disk full ──

def test_disk_full_is_detected(monkeypatch, tmp_path):
    Usage = collections.namedtuple("usage", "total used free")
    monkeypatch.setattr(
        path_service.shutil, "disk_usage",
        lambda _p: Usage(total=10**9, used=10**9, free=10 * 1024 * 1024),
    )
    assert path_service.check_disk_space(str(tmp_path), 1024 * 1024 * 1024) is False


def test_disk_space_ok_when_plenty(monkeypatch, tmp_path):
    Usage = collections.namedtuple("usage", "total used free")
    monkeypatch.setattr(
        path_service.shutil, "disk_usage",
        lambda _p: Usage(total=10**12, used=0, free=500 * 1024**3),
    )
    assert path_service.check_disk_space(str(tmp_path), 100 * 1024 * 1024) is True


# ── dead link / offline classification ──

@pytest.mark.parametrize(
    "stderr,expected",
    [
        ("ERROR: [youtube] xyz: Video unavailable", ErrorCode.CLIP_UNAVAILABLE),
        ("ERROR: [youtube] xyz: Private video", ErrorCode.CLIP_PRIVATE),
        ("ERROR: unable to download webpage: <urlopen error [Errno 11001] getaddrinfo failed>",
         ErrorCode.NETWORK_ERROR),
        ("ERROR: unable to download video data: HTTP Error 429: Too Many Requests",
         ErrorCode.RATE_LIMITED),
        ("ERROR: No space left on device", ErrorCode.DISK_FULL),
        ("ERROR: unable to open for writing: Permission denied", ErrorCode.PERMISSION_DENIED),
        ("ERROR: requested format not available", ErrorCode.FORMAT_UNAVAILABLE),
    ],
)
def test_error_classification(stderr, expected):
    assert classify_ytdlp_error(stderr) == expected


@pytest.mark.skipif(
    os.environ.get("CLIPDESK_LIVE_TESTS") != "1",
    reason="live network test — set CLIPDESK_LIVE_TESTS=1 to run",
)
def test_deleted_video_is_reported_as_unavailable(qapp):
    from PySide6.QtCore import QEventLoop, QTimer
    from app.media.ytdlp_adapter import YtDlpAdapter

    adapter = YtDlpAdapter()
    result: dict = {}
    loop = QEventLoop()
    adapter.error_occurred.connect(
        lambda code, detail: (result.update(code=code, detail=detail), loop.quit())
    )
    adapter.info_ready.connect(lambda info: (result.update(info=info), loop.quit()))

    adapter.extract_info("https://www.youtube.com/watch?v=aaaaaaaaaaa")
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(60000)
    loop.exec()
    timer.stop()

    assert "info" not in result
    assert result.get("code") == ErrorCode.CLIP_UNAVAILABLE.value
