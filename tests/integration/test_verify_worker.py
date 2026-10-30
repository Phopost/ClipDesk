"""The FFprobe verification worker must run off the GUI thread and report."""

import os
import subprocess

import pytest
from PySide6.QtCore import QEventLoop, QTimer

from app.core.controller import _VerifyWorker
from app.services.dependency_service import get_tool_path

pytestmark = [pytest.mark.integration]


def _run_worker(worker, timeout_ms: int = 30000):
    results = []
    loop = QEventLoop()

    worker.result_ready.connect(lambda result: (results.append(result), loop.quit()))
    worker.start()

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout_ms)
    loop.exec()
    timer.stop()
    worker.wait(5000)
    return results


def test_worker_verifies_real_mp4(qapp, tmp_path):
    ffmpeg = get_tool_path("ffmpeg")
    assert ffmpeg, "FFmpeg not found"

    output = tmp_path / "sample.mp4"
    subprocess.run(
        [
            ffmpeg, "-y", "-v", "error",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=440",
            "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(output),
        ],
        check=True,
        capture_output=True,
        timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert os.path.getsize(output) > 0

    worker = _VerifyWorker(str(output), True, True, 1.0)
    results = _run_worker(worker)

    assert results, "worker did not report a result"
    assert results[0].passed, results[0].errors
    assert results[0].video_streams
    assert results[0].audio_streams


def test_worker_rejects_non_media_file(qapp, tmp_path):
    fake = tmp_path / "not_video.mp4"
    fake.write_bytes(b"this is not a video")

    worker = _VerifyWorker(str(fake), True, True, None)
    results = _run_worker(worker)

    assert results
    assert results[0].passed is False
