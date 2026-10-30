"""Unit tests for progress parser."""

import pytest
from app.media.progress_parser import ProgressParser


class TestProgressParser:
    """Test yt-dlp output parsing."""

    def test_json_downloading(self):
        parser = ProgressParser(update_interval=0)  # No rate limit for tests
        line = '{"status":"downloading","downloaded_bytes":5242880,"total_bytes":10485760,"speed":2097152.0,"eta":2.5}\n'
        progress = parser.feed(line)
        assert progress is not None
        assert progress.downloaded_bytes == 5242880
        assert progress.total_bytes == 10485760
        assert progress.speed == 2097152.0
        assert progress.eta == 2.5

    def test_json_finished(self):
        parser = ProgressParser(update_interval=0)
        line = '{"status":"finished","downloaded_bytes":10485760,"total_bytes":10485760}\n'
        progress = parser.feed(line)
        assert progress is not None
        assert progress.percent == 100.0

    def test_text_progress(self):
        parser = ProgressParser(update_interval=0)
        line = "[download]  45.2% of 10.50MiB at  2.30MiB/s ETA 00:03\n"
        progress = parser.feed(line)
        assert progress is not None
        assert progress.percent == pytest.approx(45.2)

    def test_text_100_percent(self):
        parser = ProgressParser(update_interval=0)
        line = "[download] 100% of 10.50MiB\n"
        progress = parser.feed(line)
        assert progress is not None
        assert progress.percent == pytest.approx(100.0)

    def test_partial_line_buffered(self):
        parser = ProgressParser(update_interval=0)
        # Send half a line
        result = parser.feed('{"status":"download')
        assert result is None
        # Complete the line
        result = parser.feed('ing","downloaded_bytes":100,"total_bytes":200}\n')
        assert result is not None
        assert result.downloaded_bytes == 100

    def test_unparseable_doesnt_crash(self):
        parser = ProgressParser(update_interval=0)
        result = parser.feed("random garbage output\n")
        # Should not crash, may return None
        # This is fine

    def test_merger_phase_detection(self):
        parser = ProgressParser(update_interval=0)
        result = parser.feed("[Merger] Merging formats into output.mp4\n")
        assert result is not None
        assert "รวมไฟล์" in result.phase

    def test_extract_audio_phase(self):
        parser = ProgressParser(update_interval=0)
        result = parser.feed("[ExtractAudio] Converting to mp3\n")
        assert result is not None
        assert "แปลงเสียง" in result.phase

    def test_destination_phase_tracking(self):
        parser = ProgressParser(update_interval=0)
        parser.feed("[download] Destination: video.mp4\n")
        assert parser._current_phase == "กำลังดาวน์โหลดภาพ"
        parser.feed("[download] Destination: audio.m4a\n")
        assert parser._current_phase == "กำลังดาวน์โหลดเสียง"

    def test_reset(self):
        parser = ProgressParser(update_interval=0)
        parser.feed("[download] Destination: video.mp4\n")
        parser.reset()
        assert parser._current_phase == ""
        assert parser._phase_counter == 0

    def test_rate_limiting(self):
        """With rate limiting, rapid updates should be throttled."""
        parser = ProgressParser(update_interval=1.0)  # 1 second interval
        # First update should pass
        r1 = parser.feed('{"status":"downloading","downloaded_bytes":100,"total_bytes":200}\n')
        assert r1 is not None
        # Immediate second update should be throttled
        r2 = parser.feed('{"status":"downloading","downloaded_bytes":150,"total_bytes":200}\n')
        assert r2 is None  # Throttled
