"""Tests for TikTok URL parsing, error classification, and format handling."""

import pytest
from app.core.models import (
    Platform, VideoFormat, MediaInfo, OutputType, QualityPolicy,
)
from app.services.url_validator import validate_url
from app.media.format_selector import get_video_quality_options
from app.core.errors import classify_ytdlp_error, ErrorCode, get_user_message


def test_tiktok_urls():
    """Verify various TikTok URL formats."""
    cases = [
        ("https://www.tiktok.com/@creator/video/1234567890123456789", "1234567890123456789"),
        ("https://m.tiktok.com/v/1234567890123456789.html", "1234567890123456789"),
        ("https://vm.tiktok.com/ZMabcdef/", "ZMabcdef"),
        ("https://vt.tiktok.com/ZSabcdef/", "ZSabcdef"),
    ]
    for url, expected_id in cases:
        val = validate_url(url)
        assert val.is_valid, f"Failed on {url}"
        assert val.platform == Platform.TIKTOK
        if expected_id:
            assert val.media_id == expected_id


def test_tiktok_portrait_formats():
    """Verify vertical/portrait TikTok videos get marked correctly in format selector."""
    formats = [
        VideoFormat(
            format_id="h264_1080p",
            ext="mp4",
            width=1080,
            height=1920,
            fps=30,
            vcodec="avc1.640028",
            acodec="mp4a.40.2",
            filesize=15_000_000,
        ),
        VideoFormat(
            format_id="h264_720p",
            ext="mp4",
            width=720,
            height=1280,
            fps=30,
            vcodec="avc1.4d401f",
            acodec="mp4a.40.2",
            filesize=8_000_000,
        )
    ]
    info = MediaInfo(
        media_id="7106594312292453678",
        title="Viral Dance Video",
        platform=Platform.TIKTOK,
        duration=15.0,
        formats=formats,
        webpage_url="https://www.tiktok.com/@tiktok/video/7106594312292453678",
    )

    options = get_video_quality_options(info, prefer_compatible=True)
    assert len(options) == 2
    # Verify portrait label is present
    assert "แนวตั้ง" in options[0].label
    assert "1080×1920" in options[0].label
    assert "720×1280" in options[1].label
    assert options[0].height == 1080  # Short dimension used for sorting portrait


def test_tiktok_error_classification():
    """Verify TikTok specific errors map correctly to friendly messages."""
    blocked_err = "ERROR: [TikTok] 7106594312292453678: Your IP address is blocked from accessing this post"
    code = classify_ytdlp_error(blocked_err)
    assert code == ErrorCode.CLIP_RESTRICTED
    assert "ข้อจำกัด" in get_user_message(code)

    login_err = "ERROR: [TikTok] Sign in to confirm you’re not a bot"
    code2 = classify_ytdlp_error(login_err)
    assert code2 == ErrorCode.CLIP_RESTRICTED

    private_err = "ERROR: [TikTok] This video is private"
    code3 = classify_ytdlp_error(private_err)
    assert code3 == ErrorCode.CLIP_PRIVATE
