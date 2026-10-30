"""Unit tests for URL validator."""

import pytest
from app.services.url_validator import validate_url
from app.core.models import Platform


class TestValidateUrl:
    """Test URL validation logic."""

    # ── Valid YouTube URLs ──

    def test_youtube_standard(self):
        r = validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert r.is_valid
        assert r.platform == Platform.YOUTUBE
        assert r.media_id == "dQw4w9WgXcQ"

    def test_youtube_short_link(self):
        r = validate_url("https://youtu.be/dQw4w9WgXcQ")
        assert r.is_valid
        assert r.platform == Platform.YOUTUBE
        assert r.media_id == "dQw4w9WgXcQ"

    def test_youtube_shorts(self):
        r = validate_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        assert r.is_valid
        assert r.platform == Platform.YOUTUBE
        assert r.media_id == "dQw4w9WgXcQ"

    def test_youtube_mobile(self):
        r = validate_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert r.is_valid
        assert r.platform == Platform.YOUTUBE

    def test_youtube_music(self):
        r = validate_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
        assert r.is_valid
        assert r.platform == Platform.YOUTUBE

    def test_youtube_embed(self):
        r = validate_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert r.is_valid
        assert r.media_id == "dQw4w9WgXcQ"

    # ── Valid TikTok URLs ──

    def test_tiktok_standard(self):
        r = validate_url("https://www.tiktok.com/@user/video/1234567890123456789")
        assert r.is_valid
        assert r.platform == Platform.TIKTOK
        assert r.media_id == "1234567890123456789"

    def test_tiktok_vm_shortlink(self):
        r = validate_url("https://vm.tiktok.com/ZMabcdef/")
        assert r.is_valid
        assert r.platform == Platform.TIKTOK

    def test_tiktok_vt_shortlink(self):
        r = validate_url("https://vt.tiktok.com/ZSabcdef/")
        assert r.is_valid
        assert r.platform == Platform.TIKTOK

    # ── Rejected URLs ──

    def test_empty_string(self):
        r = validate_url("")
        assert not r.is_valid

    def test_random_text(self):
        r = validate_url("hello world")
        assert not r.is_valid

    def test_unsupported_site(self):
        r = validate_url("https://www.dailymotion.com/video/abc123")
        assert not r.is_valid
        assert "YouTube" in r.error or "TikTok" in r.error

    def test_file_scheme_rejected(self):
        r = validate_url("file:///C:/secrets.txt")
        assert not r.is_valid

    def test_ftp_rejected(self):
        r = validate_url("ftp://youtube.com/video")
        assert not r.is_valid

    def test_localhost_rejected(self):
        r = validate_url("http://localhost/watch?v=abc12345678")
        assert not r.is_valid

    def test_private_ip_rejected(self):
        r = validate_url("http://192.168.1.1/watch?v=abc12345678")
        assert not r.is_valid

    def test_loopback_rejected(self):
        r = validate_url("http://127.0.0.1/watch?v=abc12345678")
        assert not r.is_valid

    def test_playlist_only_rejected(self):
        r = validate_url("https://www.youtube.com/playlist?list=PLtest12345")
        assert not r.is_valid
        assert "playlist" in r.error.lower() or "เดี่ยว" in r.error

    # ── Auto-add https ──

    def test_auto_add_https(self):
        r = validate_url("youtube.com/watch?v=dQw4w9WgXcQ")
        assert r.is_valid
        assert r.platform == Platform.YOUTUBE

    # ── Clean URL ──

    def test_clean_url_youtube(self):
        r = validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest&index=3")
        assert r.is_valid
        assert r.clean_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_whitespace_stripped(self):
        r = validate_url("  https://youtu.be/dQw4w9WgXcQ  ")
        assert r.is_valid
