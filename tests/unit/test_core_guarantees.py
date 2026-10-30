"""Tests for core guarantees from the spec: no overwrite, no silent downgrade,
readable errors, cancel cleanup. No network, no yt-dlp process."""

import os

import pytest

from app.core.errors import ErrorCode, get_user_message
from app.core.models import (
    DownloadTask, MediaInfo, OutputType, Platform, QualityPolicy,
    TaskState, VideoFormat,
)
from app.services.path_service import safe_move


# ── safe_move must never overwrite ──

def test_safe_move_refuses_to_overwrite(tmp_path):
    src = tmp_path / "new.mp4"
    dst = tmp_path / "existing.mp4"
    src.write_bytes(b"NEW")
    dst.write_bytes(b"OLD")
    assert safe_move(str(src), str(dst)) is False
    assert dst.read_bytes() == b"OLD"      # untouched
    assert src.exists()                    # source kept for retry


def test_safe_move_moves_when_free(tmp_path):
    src = tmp_path / "a.mp4"
    dst = tmp_path / "b.mp4"
    src.write_bytes(b"DATA")
    assert safe_move(str(src), str(dst)) is True
    assert dst.read_bytes() == b"DATA"
    assert not src.exists()


# ── controller behaviour (Qt object, but no processes started) ──

@pytest.fixture
def controller(qtbot, tmp_path, monkeypatch):
    from app.core.controller import AppController
    from app.storage.database import Database

    c = AppController(db=Database(str(tmp_path / "t.db")))
    # never launch a real process in these tests
    monkeypatch.setattr(c, "_start_download", lambda *a, **k: None, raising=False)
    return c


def _info(formats):
    return MediaInfo(media_id="vid12345678", title="T", platform=Platform.YOUTUBE,
                     duration=10, formats=formats, webpage_url="https://youtu.be/vid12345678")


def _task(tmp_path, policy):
    t = DownloadTask(source_url="https://youtu.be/vid12345678", title="T",
                     media_id="vid12345678", quality_policy=policy,
                     destination_dir=str(tmp_path), work_dir=str(tmp_path))
    t.state = TaskState.RESOLVING
    return t


def test_missing_selected_quality_fails_instead_of_downgrading(controller, tmp_path):
    controller.queue.add_task(t := _task(tmp_path, QualityPolicy(
        output_type=OutputType.MP4, selected_video_format_id="137",
        selected_audio_format_id="140")))
    # source now only offers 360p
    fresh = _info([VideoFormat(format_id="18", ext="mp4", width=640, height=360,
                               vcodec="avc1", acodec="mp4a")])
    controller._on_resolved(t, t.attempt_id, fresh)
    assert t.state == TaskState.FAILED
    assert t.error_code == ErrorCode.FORMAT_UNAVAILABLE.value


def test_stale_attempt_events_are_ignored(controller, tmp_path):
    controller.queue.add_task(t := _task(tmp_path, QualityPolicy(output_type=OutputType.MP3)))
    old = t.attempt_id
    t.attempt_id = "new-attempt"
    controller._on_download_error(t, old, ErrorCode.NETWORK_ERROR.value, "boom")
    assert t.state == TaskState.RESOLVING   # untouched by the old attempt


def test_user_sees_readable_message_detail_kept_separately(controller, tmp_path):
    controller.queue.add_task(t := _task(tmp_path, QualityPolicy(output_type=OutputType.MP3)))
    t.state = TaskState.DOWNLOADING
    controller._on_download_error(t, t.attempt_id, ErrorCode.NETWORK_ERROR.value,
                                  "ERROR: <urlopen error [Errno 11001] getaddrinfo failed>")
    assert t.state == TaskState.FAILED
    assert t.error_message == get_user_message(ErrorCode.NETWORK_ERROR)
    assert "urlopen" in (t.error_detail or "")
    assert "urlopen" not in t.error_message
