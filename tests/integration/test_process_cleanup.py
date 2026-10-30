"""Process-tree cleanup tests (Windows Job Object).

The first test is fully offline and verifies that closing a Job Object kills
both the parent process and a child spawned *after* the assignment.

The second test downloads a real video, cancels mid-flight and verifies that
no yt-dlp/ffmpeg/node process survives.
"""

import os
import subprocess
import sys
import time

import psutil
import pytest
from PySide6.QtCore import QEventLoop, QTimer

from app.core.models import OutputType, QualityPolicy
from app.media.ytdlp_adapter import YtDlpAdapter
from app.services.process_supervisor import JobObject

pytestmark = [pytest.mark.integration]

CC_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"


def _wait_until(predicate, timeout: float, interval: float = 0.1) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def test_job_object_kills_parent_and_child(tmp_path):
    """A child spawned after assignment must die with the job."""
    go_file = tmp_path / "go.txt"
    pid_file = tmp_path / "child.pid"

    spawner = tmp_path / "spawner.py"
    spawner.write_text(
        "import subprocess, sys, time, os\n"
        "while not os.path.exists(sys.argv[1]):\n"
        "    time.sleep(0.05)\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
        "open(sys.argv[2], 'w').write(str(child.pid))\n"
        "time.sleep(120)\n",
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        [sys.executable, str(spawner), str(go_file), str(pid_file)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

    job = JobObject()
    try:
        assert job.is_valid
        assert job.assign(proc.pid)

        go_file.write_text("go", encoding="utf-8")
        assert _wait_until(lambda: pid_file.exists() and pid_file.read_text().strip(), 15)

        child_pid = int(pid_file.read_text().strip())
        assert psutil.pid_exists(child_pid)
        assert psutil.pid_exists(proc.pid)

        job.terminate()
        assert _wait_until(lambda: not psutil.pid_exists(child_pid), 10), "child survived"
        assert _wait_until(lambda: not psutil.pid_exists(proc.pid), 10), "parent survived"
    finally:
        job.close()
        if proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


@pytest.mark.skipif(
    os.environ.get("CLIPDESK_LIVE_TESTS") != "1",
    reason="live network test — set CLIPDESK_LIVE_TESTS=1 to run",
)
def test_cancel_kills_download_process_tree(qapp, tmp_path):
    adapter = YtDlpAdapter()
    policy = QualityPolicy(
        output_type=OutputType.MP4,
        preferred_height=1080,
        prefer_compatible=True,
    )

    started = {"ok": False}
    ended = {"ok": False}
    adapter.process_started.connect(lambda: started.update(ok=True))
    adapter.process_ended.connect(lambda: ended.update(ok=True))

    template = os.path.join(str(tmp_path), "%(title)s.%(ext)s")
    adapter.start_download(CC_URL, policy, str(tmp_path), template)

    assert _wait_until(lambda: started["ok"], 30), "process never started"
    assert adapter._job is not None and adapter._job.is_valid, "job object not assigned"

    # Let yt-dlp spawn its children (node, and possibly ffmpeg)
    time.sleep(4)

    descendants = psutil.Process(os.getpid()).children(recursive=True)
    ytdlp_children = [
        p for p in descendants
        if p.is_running() and any("yt-dlp" in part.lower() for part in p.cmdline())
    ]
    assert ytdlp_children, "expected a running yt-dlp child process"

    adapter.cancel()

    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(15000)
    adapter.process_ended.connect(loop.quit)
    if not ended["ok"]:
        loop.exec()
    timer.stop()

    assert ended["ok"], "adapter never reported process end after cancel"
    assert not adapter.is_running

    time.sleep(1)
    leftovers = [
        p for p in psutil.Process(os.getpid()).children(recursive=True)
        if p.is_running() and any("yt-dlp" in part.lower() for part in p.cmdline())
    ]
    assert not leftovers, f"zombie processes remain: {[p.pid for p in leftovers]}"
