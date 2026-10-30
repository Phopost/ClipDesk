"""Full-pipeline test through AppController (live network, CC-licensed clip).

URL check -> metadata -> task -> RESOLVING (re-read) -> DOWNLOADING ->
POSTPROCESSING -> VERIFYING -> COMPLETED -> file published + SQLite history.
Also: cancel mid-download leaves no processes / no partial files.

Run:  $env:CLIPDESK_LIVE_TESTS="1"; python -m pytest tests/integration/test_full_pipeline.py -v -s
"""

import os
import time

import pytest

from app.core.models import OutputType, QualityPolicy, TaskState
from app.media.ffprobe_adapter import verify_file
from app.media.format_selector import get_video_quality_options

pytestmark = pytest.mark.skipif(
    os.environ.get("CLIPDESK_LIVE_TESTS") != "1",
    reason="live network test; set CLIPDESK_LIVE_TESTS=1",
)

CC_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
TERMINAL = (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)


@pytest.fixture
def controller(qapp, tmp_path):
    from app.core.controller import AppController
    from app.storage.database import Database
    c = AppController(db=Database(str(tmp_path / "h.db")))
    yield c
    c.shutdown()


def _fetch_info(controller, qtbot):
    got = {}
    controller.info_fetched.connect(lambda i: got.setdefault("info", i))
    controller.info_error.connect(lambda m: got.setdefault("err", m))
    controller.check_url(CC_URL)
    qtbot.waitUntil(lambda: "info" in got or "err" in got, timeout=60000)
    assert "err" not in got, got.get("err")
    return got["info"]


def _wait_terminal(controller, task, qtbot, timeout=240000):
    qtbot.waitUntil(lambda: task.state in TERMINAL, timeout=timeout)


def test_mp3_full_pipeline(controller, qtbot, tmp_path):
    info = _fetch_info(controller, qtbot)
    dest = tmp_path / "out"
    dest.mkdir()
    states = []
    controller.task_state_changed.connect(lambda tid, s: states.append(s))

    tid = controller.start_download(
        info, QualityPolicy(output_type=OutputType.MP3, preferred_bitrate=128), str(dest))
    assert tid
    task = controller.queue.get_task(tid)
    _wait_terminal(controller, task, qtbot)

    assert task.state == TaskState.COMPLETED, (task.error_message, task.error_detail)
    assert task.output_path and os.path.isfile(task.output_path)
    assert task.output_path.endswith(".mp3")
    assert os.path.dirname(task.output_path) == str(dest)
    assert verify_file(task.output_path, expected_video=False, expected_audio=True).passed
    # state machine order was respected
    order = [s for s in states]
    for a, b in [(TaskState.RESOLVING, TaskState.DOWNLOADING),
                 (TaskState.DOWNLOADING, TaskState.POSTPROCESSING),
                 (TaskState.POSTPROCESSING, TaskState.VERIFYING),
                 (TaskState.VERIFYING, TaskState.COMPLETED)]:
        assert order.index(a) < order.index(b)
    # work dir cleaned, history persisted
    assert not os.path.exists(task.work_dir)
    saved = controller.history()
    assert any(t.task_id == tid and t.state == TaskState.COMPLETED for t in saved)


def test_mp4_full_pipeline_and_no_overwrite(controller, qtbot, tmp_path):
    info = _fetch_info(controller, qtbot)
    options = get_video_quality_options(info, prefer_compatible=True)
    assert options, "source offered no H.264 option"
    opt = options[-1]  # smallest real option
    policy = QualityPolicy(
        output_type=OutputType.MP4, preferred_height=opt.height, prefer_compatible=True,
        selected_video_format_id=opt.video_format_id,
        selected_audio_format_id=opt.audio_format_id)
    dest = tmp_path / "out"
    dest.mkdir()

    paths = []
    for _ in range(2):  # same clip twice into the same folder
        tid = controller.start_download(info, policy, str(dest))
        task = controller.queue.get_task(tid)
        _wait_terminal(controller, task, qtbot)
        assert task.state == TaskState.COMPLETED, (task.error_message, task.error_detail)
        assert verify_file(task.output_path, expected_video=True, expected_audio=True).passed
        paths.append(task.output_path)

    assert paths[0] != paths[1]                      # second got " (2)"
    assert all(os.path.isfile(p) for p in paths)     # first was NOT overwritten
    assert "(2)" in os.path.basename(paths[1])


def test_cancel_mid_download_cleans_up(controller, qtbot, tmp_path):
    import psutil
    info = _fetch_info(controller, qtbot)
    options = get_video_quality_options(info, prefer_compatible=True)
    opt = options[0]  # largest, so there is time to cancel
    dest = tmp_path / "out"
    dest.mkdir()
    tid = controller.start_download(info, QualityPolicy(
        output_type=OutputType.MP4, preferred_height=opt.height,
        selected_video_format_id=opt.video_format_id,
        selected_audio_format_id=opt.audio_format_id), str(dest))
    task = controller.queue.get_task(tid)
    qtbot.waitUntil(lambda: task.state == TaskState.DOWNLOADING, timeout=60000)
    time.sleep(2)
    controller.cancel_task(tid)
    _wait_terminal(controller, task, qtbot, timeout=30000)

    assert task.state == TaskState.CANCELLED
    assert not os.path.exists(task.work_dir)
    assert not [f for f in dest.iterdir() if f.is_file()]    # nothing published
    time.sleep(1)
    left = [p.info["name"] for p in psutil.process_iter(["name"])
            if p.info["name"] and p.info["name"].lower() in ("yt-dlp.exe", "ffmpeg.exe")
            and p.ppid() == os.getpid()]
    assert not left, f"orphan children: {left}"
