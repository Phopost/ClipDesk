"""Unit tests for data models and state machine."""

import pytest
from app.core.models import (
    DownloadTask, TaskState, VideoFormat, MediaInfo, Platform,
    QualityPolicy, OutputType, VALID_TRANSITIONS,
)


class TestTaskState:
    """Test state transition rules."""

    def test_queued_to_resolving(self):
        task = DownloadTask()
        assert task.state == TaskState.QUEUED
        assert task.transition_to(TaskState.RESOLVING)
        assert task.state == TaskState.RESOLVING

    def test_queued_to_cancelling(self):
        task = DownloadTask()
        assert task.transition_to(TaskState.CANCELLING)
        assert task.state == TaskState.CANCELLING

    def test_cannot_skip_states(self):
        task = DownloadTask()
        assert not task.transition_to(TaskState.DOWNLOADING)
        assert task.state == TaskState.QUEUED

    def test_completed_is_terminal(self):
        task = DownloadTask(state=TaskState.COMPLETED)
        assert not task.transition_to(TaskState.QUEUED)
        assert not task.transition_to(TaskState.DOWNLOADING)
        assert task.state == TaskState.COMPLETED

    def test_cancelled_is_terminal(self):
        task = DownloadTask(state=TaskState.CANCELLED)
        assert not task.transition_to(TaskState.QUEUED)
        assert task.state == TaskState.CANCELLED

    def test_failed_can_retry(self):
        task = DownloadTask(state=TaskState.FAILED)
        assert task.transition_to(TaskState.QUEUED)
        assert task.state == TaskState.QUEUED

    def test_cancelling_to_cancelled(self):
        task = DownloadTask(state=TaskState.CANCELLING)
        assert task.transition_to(TaskState.CANCELLED)
        # Cannot go back from CANCELLED
        assert not task.transition_to(TaskState.COMPLETED)

    def test_downloading_to_postprocessing(self):
        task = DownloadTask(state=TaskState.DOWNLOADING)
        assert task.transition_to(TaskState.POSTPROCESSING)

    def test_full_success_flow(self):
        task = DownloadTask()
        assert task.transition_to(TaskState.RESOLVING)
        assert task.transition_to(TaskState.DOWNLOADING)
        assert task.transition_to(TaskState.POSTPROCESSING)
        assert task.transition_to(TaskState.VERIFYING)
        assert task.transition_to(TaskState.COMPLETED)

    def test_new_attempt_resets_state(self):
        task = DownloadTask(state=TaskState.FAILED)
        old_attempt = task.attempt_id
        task.new_attempt()
        assert task.state == TaskState.QUEUED
        assert task.attempt_id != old_attempt
        assert task.output_path is None
        assert task.error_code is None

    def test_timestamps_set_on_transition(self):
        task = DownloadTask()
        assert task.started_at is None
        task.transition_to(TaskState.RESOLVING)
        assert task.started_at is not None

        task.transition_to(TaskState.DOWNLOADING)
        task.transition_to(TaskState.POSTPROCESSING)
        task.transition_to(TaskState.VERIFYING)
        task.transition_to(TaskState.COMPLETED)
        assert task.completed_at is not None


class TestVideoFormat:
    """Test VideoFormat properties."""

    def test_has_video(self):
        vf = VideoFormat(format_id="1", ext="mp4", vcodec="avc1", acodec=None)
        assert vf.has_video
        assert not vf.has_audio

    def test_has_audio_only(self):
        vf = VideoFormat(format_id="2", ext="m4a", vcodec=None, acodec="mp4a.40.2")
        assert not vf.has_video
        assert vf.has_audio

    def test_vcodec_none_string(self):
        vf = VideoFormat(format_id="3", ext="m4a", vcodec="none", acodec="mp4a")
        assert not vf.has_video

    def test_resolution_label_landscape(self):
        vf = VideoFormat(format_id="1", ext="mp4", width=1920, height=1080,
                         fps=30, vcodec="avc1")
        assert "1920×1080" in vf.resolution_label
        assert "แนวตั้ง" not in vf.resolution_label

    def test_resolution_label_portrait(self):
        vf = VideoFormat(format_id="1", ext="mp4", width=1080, height=1920,
                         fps=30, vcodec="avc1")
        assert "1080×1920" in vf.resolution_label
        assert "แนวตั้ง" in vf.resolution_label

    def test_resolution_label_high_fps(self):
        vf = VideoFormat(format_id="1", ext="mp4", width=1920, height=1080,
                         fps=60, vcodec="avc1")
        assert "60fps" in vf.resolution_label

    def test_resolution_label_audio_only(self):
        vf = VideoFormat(format_id="1", ext="m4a", vcodec=None, acodec="mp4a")
        assert "เสียง" in vf.resolution_label

    def test_size_label_known(self):
        vf = VideoFormat(format_id="1", ext="mp4", filesize=15_000_000)
        assert "14.3 MB" in vf.size_label
        assert "ประมาณ" not in vf.size_label

    def test_size_label_approx(self):
        vf = VideoFormat(format_id="1", ext="mp4", filesize_approx=15_000_000)
        assert "ประมาณ" in vf.size_label

    def test_size_label_unknown(self):
        vf = VideoFormat(format_id="1", ext="mp4")
        assert "ไม่ทราบ" in vf.size_label

    def test_portrait_detection(self):
        vf = VideoFormat(format_id="1", ext="mp4", width=1080, height=1920, vcodec="avc1")
        assert vf.is_portrait
        assert vf.short_height == 1080

    def test_landscape_short_height(self):
        vf = VideoFormat(format_id="1", ext="mp4", width=1920, height=1080, vcodec="avc1")
        assert not vf.is_portrait
        assert vf.short_height == 1080


class TestMediaInfo:
    """Test MediaInfo properties."""

    def test_duration_label_short(self):
        info = MediaInfo(media_id="test", title="Test", platform=Platform.YOUTUBE,
                         duration=65.5)
        assert info.duration_label == "1:05"

    def test_duration_label_long(self):
        info = MediaInfo(media_id="test", title="Test", platform=Platform.YOUTUBE,
                         duration=3723)
        assert info.duration_label == "1:02:03"

    def test_duration_label_unknown(self):
        info = MediaInfo(media_id="test", title="Test", platform=Platform.YOUTUBE)
        assert "ไม่ทราบ" in info.duration_label
