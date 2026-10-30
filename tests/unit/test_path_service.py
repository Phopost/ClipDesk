"""Unit tests for path service."""

import os
import pytest
from app.services.path_service import (
    sanitize_filename, resolve_destination, check_write_permission,
)


class TestSanitizeFilename:
    """Test filename sanitization."""

    def test_basic_filename(self):
        result = sanitize_filename("My Video", "abc123", "mp4")
        assert result == "My Video [abc123].mp4"

    def test_thai_filename(self):
        result = sanitize_filename("วิดีโอทดสอบ", "abc123", "mp4")
        assert result == "วิดีโอทดสอบ [abc123].mp4"
        assert "วิดีโอ" in result

    def test_emoji_filename(self):
        result = sanitize_filename("Fun 🎉 Video", "abc123", "mp4")
        assert "[abc123]" in result

    def test_illegal_chars_removed(self):
        result = sanitize_filename('My <Video>: "Test"', "abc123", "mp4")
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result
        assert '"' not in result
        assert "[abc123]" in result

    def test_path_traversal_blocked(self):
        result = sanitize_filename("../../etc/passwd", "abc123", "mp4")
        assert ".." not in result
        assert "[abc123]" in result

    def test_reserved_name_handled(self):
        result = sanitize_filename("CON", "abc123", "mp4")
        assert result.startswith("_")
        assert "[abc123]" in result

    def test_trailing_dots_stripped(self):
        result = sanitize_filename("test...", "abc123", "mp4")
        assert not result.split("[")[0].rstrip().endswith(".")

    def test_empty_title(self):
        result = sanitize_filename("", "abc123", "mp4")
        assert "download" in result
        assert "[abc123]" in result

    def test_very_long_title_truncated(self):
        long_title = "A" * 300
        result = sanitize_filename(long_title, "abc123", "mp4")
        assert len(result) < 300
        assert "[abc123]" in result  # media_id preserved

    def test_mp3_extension(self):
        result = sanitize_filename("Song", "abc123", "mp3")
        assert result.endswith(".mp3")


class TestResolveDestination:
    """Test destination path resolution with duplicate handling."""

    def test_no_conflict(self, tmp_path):
        result = resolve_destination("test.mp4", str(tmp_path))
        assert result.filename == "test.mp4"
        assert result.was_modified is False

    def test_duplicate_appends_number(self, tmp_path):
        # Create existing file
        (tmp_path / "test.mp4").touch()
        result = resolve_destination("test.mp4", str(tmp_path))
        assert result.filename == "test (2).mp4"
        assert result.was_modified is True

    def test_multiple_duplicates(self, tmp_path):
        (tmp_path / "test.mp4").touch()
        (tmp_path / "test (2).mp4").touch()
        result = resolve_destination("test.mp4", str(tmp_path))
        assert result.filename == "test (3).mp4"

    def test_overwrite_mode(self, tmp_path):
        (tmp_path / "test.mp4").touch()
        result = resolve_destination("test.mp4", str(tmp_path), overwrite=True)
        assert result.filename == "test.mp4"
        assert result.was_modified is False


class TestWritePermission:
    """Test write permission checks."""

    def test_writable_dir(self, tmp_path):
        assert check_write_permission(str(tmp_path))

    def test_nonexistent_dir(self):
        assert not check_write_permission("/nonexistent/path/12345")
