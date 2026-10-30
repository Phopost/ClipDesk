"""Unit tests for format selector."""

import pytest
from app.media.format_selector import (
    get_video_quality_options, get_audio_quality_options,
    select_format, AUDIO_BITRATE_MAP,
)
from app.core.models import (
    MediaInfo, VideoFormat, Platform, QualityPolicy, OutputType,
)


def _make_info(formats: list[VideoFormat]) -> MediaInfo:
    return MediaInfo(
        media_id="test123",
        title="Test Video",
        platform=Platform.YOUTUBE,
        duration=120,
        formats=formats,
    )


class TestVideoQualityOptions:
    """Test quality option generation from real format data."""

    def test_empty_formats(self):
        info = _make_info([])
        options = get_video_quality_options(info)
        assert len(options) == 0

    def test_single_muxed_format(self):
        info = _make_info([
            VideoFormat(format_id="18", ext="mp4", width=640, height=360,
                        fps=30, vcodec="avc1.42001E", acodec="mp4a.40.2",
                        filesize=10_000_000),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 1
        assert "640×360" in options[0].label
        assert options[0].needs_merge is False

    def test_separate_video_audio(self):
        info = _make_info([
            VideoFormat(format_id="137", ext="mp4", width=1920, height=1080,
                        fps=30, vcodec="avc1.640028", acodec=None,
                        filesize=50_000_000),
            VideoFormat(format_id="140", ext="m4a", width=None, height=None,
                        vcodec=None, acodec="mp4a.40.2",
                        filesize=3_000_000),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 1
        assert "1920×1080" in options[0].label
        assert options[0].needs_merge is True
        assert options[0].video_format_id == "137"
        assert options[0].audio_format_id == "140"

    def test_portrait_video_label(self):
        info = _make_info([
            VideoFormat(format_id="1", ext="mp4", width=1080, height=1920,
                        fps=30, vcodec="avc1.640028", acodec="mp4a.40.2"),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 1
        assert "แนวตั้ง" in options[0].label

    def test_60fps_shown_separately(self):
        info = _make_info([
            VideoFormat(format_id="1", ext="mp4", width=1920, height=1080,
                        fps=30, vcodec="avc1.640028", acodec=None),
            VideoFormat(format_id="2", ext="mp4", width=1920, height=1080,
                        fps=60, vcodec="avc1.640028", acodec=None),
            VideoFormat(format_id="3", ext="m4a", vcodec=None, acodec="mp4a.40.2"),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 2
        labels = [o.label for o in options]
        assert any("60fps" in l for l in labels)

    def test_only_shows_existing_resolutions(self):
        """Must NOT show 1080p if max is 720p."""
        info = _make_info([
            VideoFormat(format_id="1", ext="mp4", width=1280, height=720,
                        fps=30, vcodec="avc1.4d401f", acodec="mp4a.40.2",
                        filesize=20_000_000),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 1
        assert "720" in options[0].label
        labels_str = " ".join(o.label for o in options)
        assert "1080" not in labels_str
        assert "1920" not in labels_str

    def test_compatible_mode_skips_vp9(self):
        info = _make_info([
            VideoFormat(format_id="1", ext="webm", width=1920, height=1080,
                        fps=30, vcodec="vp9", acodec=None),
            VideoFormat(format_id="2", ext="mp4", width=1280, height=720,
                        fps=30, vcodec="avc1.4d401f", acodec=None),
            VideoFormat(format_id="3", ext="m4a", vcodec=None, acodec="mp4a.40.2"),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 1
        assert "720" in options[0].label

    def test_size_label_combined(self):
        info = _make_info([
            VideoFormat(format_id="1", ext="mp4", width=1920, height=1080,
                        fps=30, vcodec="avc1.640028", acodec=None,
                        filesize=50_000_000),
            VideoFormat(format_id="2", ext="m4a", vcodec=None, acodec="mp4a.40.2",
                        filesize=3_000_000),
        ])
        options = get_video_quality_options(info, prefer_compatible=True)
        assert len(options) == 1
        # Should show combined size ~50.6 MB
        assert "MB" in options[0].size_label


class TestAudioQualityOptions:
    """Test MP3 bitrate options."""

    def test_four_options(self):
        options = get_audio_quality_options()
        assert len(options) == 4

    def test_bitrate_map_values(self):
        assert AUDIO_BITRATE_MAP["128 kbps"] == 128
        assert AUDIO_BITRATE_MAP["192 kbps (แนะนำ)"] == 192
        assert AUDIO_BITRATE_MAP["256 kbps"] == 256
        assert AUDIO_BITRATE_MAP["320 kbps"] == 320


class TestSelectFormat:
    """Test format selection logic."""

    def test_mp3_selection(self):
        info = _make_info([
            VideoFormat(format_id="1", ext="mp4", width=1920, height=1080,
                        vcodec="avc1", acodec="mp4a.40.2"),
            VideoFormat(format_id="2", ext="m4a", vcodec=None, acodec="mp4a.40.2",
                        abr=128),
            VideoFormat(format_id="3", ext="webm", vcodec=None, acodec="opus",
                        abr=160),
        ])
        policy = QualityPolicy(output_type=OutputType.MP3, preferred_bitrate=192)
        sel = select_format(info, policy)
        assert sel.output_ext == "mp3"
        assert sel.audio_format_id is not None

    def test_mp4_with_specific_format(self):
        info = _make_info([
            VideoFormat(format_id="137", ext="mp4", width=1920, height=1080,
                        fps=30, vcodec="avc1.640028", acodec=None),
            VideoFormat(format_id="140", ext="m4a", vcodec=None, acodec="mp4a.40.2"),
        ])
        policy = QualityPolicy(
            output_type=OutputType.MP4,
            selected_video_format_id="137",
            selected_audio_format_id="140",
        )
        sel = select_format(info, policy)
        assert sel.video_format_id == "137"
        assert sel.audio_format_id == "140"
        assert sel.needs_merge

    def test_mp4_auto_select(self):
        info = _make_info([
            VideoFormat(format_id="1", ext="mp4", width=1920, height=1080,
                        fps=30, vcodec="avc1.640028", acodec=None, tbr=5000),
            VideoFormat(format_id="2", ext="mp4", width=1280, height=720,
                        fps=30, vcodec="avc1.4d401f", acodec=None, tbr=2500),
            VideoFormat(format_id="3", ext="m4a", vcodec=None, acodec="mp4a.40.2",
                        abr=128),
        ])
        policy = QualityPolicy(
            output_type=OutputType.MP4,
            preferred_height=720,
            prefer_compatible=True,
        )
        sel = select_format(info, policy)
        assert sel.video_format_id == "2"  # Should pick 720p
