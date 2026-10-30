"""Live integration test: metadata extraction + format selector on real data.

Skipped unless CLIPDESK_LIVE_TESTS=1.
"""

import json
import os
import subprocess

import pytest

from app.core.models import MediaInfo, Platform, VideoFormat
from app.media.format_selector import get_video_quality_options
from app.services.dependency_service import get_js_runtime_args, get_tool_path

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("CLIPDESK_LIVE_TESTS") != "1",
        reason="live network test — set CLIPDESK_LIVE_TESTS=1 to run",
    ),
]

# Big Buck Bunny — Blender Foundation, CC-BY 3.0
TEST_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"


def _fetch_json(url: str) -> dict:
    ytdlp = get_tool_path("yt-dlp")
    assert ytdlp, "yt-dlp not found"
    result = subprocess.run(
        [ytdlp, "--ignore-config", "--no-playlist", "--dump-json", "--no-download",
         *get_js_runtime_args(), url],
        capture_output=True,
        text=True,
        timeout=120,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    assert result.returncode == 0, result.stderr[:300]
    return json.loads(result.stdout)


def _to_media_info(data: dict) -> MediaInfo:
    formats = []
    for fmt in data.get("formats", []):
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")
        formats.append(
            VideoFormat(
                format_id=str(fmt.get("format_id", "")),
                ext=fmt.get("ext", ""),
                width=fmt.get("width"),
                height=fmt.get("height"),
                fps=fmt.get("fps"),
                vcodec=vcodec if vcodec != "none" else None,
                acodec=acodec if acodec != "none" else None,
                filesize=fmt.get("filesize"),
                filesize_approx=fmt.get("filesize_approx"),
                tbr=fmt.get("tbr"),
                abr=fmt.get("abr"),
            )
        )
    return MediaInfo(
        media_id=data.get("id", ""),
        title=data.get("title", ""),
        platform=Platform.YOUTUBE,
        duration=data.get("duration"),
        formats=formats,
    )


def test_live_metadata_and_format_options():
    data = _fetch_json(TEST_URL)
    assert data.get("title")
    assert data.get("formats")

    info = _to_media_info(data)
    assert info.formats

    compatible = get_video_quality_options(info, prefer_compatible=True)
    all_codecs = get_video_quality_options(info, prefer_compatible=False)
    assert compatible, "no MP4 quality options generated"
    assert all_codecs, "no codec options generated"
    # H.264-first list can never contain more options than the full list
    assert len(compatible) <= len(all_codecs)

    for option in compatible:
        assert option.label
        assert option.video_format_id or option.audio_format_id
