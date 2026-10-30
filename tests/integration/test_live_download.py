"""Live end-to-end tests against real YouTube (CC-licensed clip).

These tests hit the network and are skipped unless CLIPDESK_LIVE_TESTS=1.

Run:
    $env:CLIPDESK_LIVE_TESTS="1"
    python -m pytest tests/integration/test_live_download.py -v -s
"""

import os

import pytest
from PySide6.QtCore import QEventLoop, QTimer

from app.core.models import OutputType, QualityPolicy
from app.media.ffprobe_adapter import verify_file
from app.media.ytdlp_adapter import YtDlpAdapter
from app.services.dependency_service import get_js_runtime_args

# Big Buck Bunny — Blender Foundation, CC-BY 3.0
CC_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("CLIPDESK_LIVE_TESTS") != "1",
        reason="live network test — set CLIPDESK_LIVE_TESTS=1 to run",
    ),
]


def _wait(loop: QEventLoop, timeout_sec: int) -> bool:
    """Run an event loop with a hard timeout. Returns True if quit by signal."""
    finished = {"ok": False}

    def _quit():
        finished["ok"] = True
        loop.quit()

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_sec * 1000)
    loop.exec()
    timer.stop()
    return finished["ok"]


def _extract(url: str, timeout: int = 120):
    adapter = YtDlpAdapter()
    result: dict = {}
    loop = QEventLoop()

    adapter.info_ready.connect(lambda info: (result.update(info=info), loop.quit()))
    adapter.error_occurred.connect(
        lambda code, detail: (result.update(error=(code, detail)), loop.quit())
    )

    adapter.extract_info(url)
    _wait(loop, timeout)

    assert "error" not in result, f"metadata error: {result.get('error')}"
    assert "info" in result, "metadata extraction timed out"
    return result["info"]


def _download(url: str, policy: QualityPolicy, work_dir: str, timeout: int = 600):
    adapter = YtDlpAdapter()
    result: dict = {}
    loop = QEventLoop()

    adapter.download_finished.connect(
        lambda path: (result.update(path=path), loop.quit())
    )
    adapter.error_occurred.connect(
        lambda code, detail: (result.update(error=(code, detail)), loop.quit())
    )

    template = os.path.join(work_dir, "%(title)s.%(ext)s")
    adapter.start_download(url, policy, work_dir, template)
    _wait(loop, timeout)

    assert "error" not in result, f"download error: {result.get('error')}"
    assert "path" in result, "download timed out"
    return result["path"]


def test_node_js_runtime_detected(qapp):
    args = get_js_runtime_args()
    assert args, "JS runtime not found — YouTube extraction will be degraded"
    assert args[0] == "--js-runtimes"
    assert args[1].startswith(("quickjs:", "node:"))


def test_live_metadata(qapp):
    info = _extract(CC_URL)
    assert info.title
    assert info.duration and info.duration > 0
    assert info.formats, "no formats returned"
    assert any(f.has_video for f in info.formats)
    assert any(f.has_audio for f in info.formats)
    assert info.thumbnail_url


def test_live_download_mp4(qapp, tmp_path):
    info = _extract(CC_URL)
    policy = QualityPolicy(
        output_type=OutputType.MP4,
        preferred_height=240,
        prefer_compatible=True,
    )
    path = _download(CC_URL, policy, str(tmp_path))

    assert os.path.isfile(path)
    assert path.lower().endswith(".mp4"), f"unexpected container: {path}"

    result = verify_file(
        path,
        expected_video=True,
        expected_audio=True,
        expected_duration=info.duration,
    )
    assert result.passed, f"verification failed: {result.errors}"
    assert result.video_streams
    assert result.audio_streams
    assert result.file_size > 0


def test_live_download_mp3(qapp, tmp_path):
    info = _extract(CC_URL)
    policy = QualityPolicy(
        output_type=OutputType.MP3,
        preferred_bitrate=192,
    )
    path = _download(CC_URL, policy, str(tmp_path))

    assert os.path.isfile(path)
    assert path.lower().endswith(".mp3"), f"unexpected container: {path}"

    result = verify_file(
        path,
        expected_video=False,
        expected_audio=True,
        expected_duration=info.duration,
    )
    assert result.passed, f"verification failed: {result.errors}"
    assert result.audio_streams
    assert result.file_size > 0
