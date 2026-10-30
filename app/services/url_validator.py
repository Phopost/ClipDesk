"""URL validation for ClipDesk — rejects unsafe URLs, extracts platform & media ID."""

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, parse_qs
import ipaddress
import re

from app.core.models import Platform


# Allowed domains (exact match after lowercasing)
_YOUTUBE_DOMAINS = frozenset({
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "music.youtube.com",
})

_TIKTOK_DOMAINS = frozenset({
    "tiktok.com",
    "www.tiktok.com",
    "m.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
})

_ALLOWED_DOMAINS = _YOUTUBE_DOMAINS | _TIKTOK_DOMAINS

# Windows reserved names
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})


@dataclass(frozen=True)
class ValidatedURL:
    """Result of URL validation."""

    original_url: str
    clean_url: str
    platform: Platform
    media_id: Optional[str]
    is_valid: bool
    error: Optional[str] = None


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname resolves to a private/loopback IP."""
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_loopback or addr.is_reserved
    except ValueError:
        pass
    # Check for localhost variants
    if hostname in ("localhost", "localhost.localdomain"):
        return True
    return False


def _extract_youtube_id(parsed) -> Optional[str]:
    """Extract video ID from a YouTube URL."""
    path = parsed.path.rstrip("/")
    # youtu.be/VIDEO_ID
    if parsed.hostname and parsed.hostname.lower() == "youtu.be":
        vid = path.lstrip("/").split("/")[0] if path.lstrip("/") else None
        if vid and re.match(r"^[A-Za-z0-9_-]{11}$", vid):
            return vid
        return None
    # /shorts/VIDEO_ID
    shorts_match = re.match(r"^/shorts/([A-Za-z0-9_-]{11})", path)
    if shorts_match:
        return shorts_match.group(1)
    # /watch?v=VIDEO_ID
    qs = parse_qs(parsed.query)
    v_param = qs.get("v", [None])[0]
    if v_param and re.match(r"^[A-Za-z0-9_-]{11}$", v_param):
        return v_param
    # /embed/VIDEO_ID or /v/VIDEO_ID
    embed_match = re.match(r"^/(?:embed|v)/([A-Za-z0-9_-]{11})", path)
    if embed_match:
        return embed_match.group(1)
    return None


def _extract_tiktok_id(parsed) -> Optional[str]:
    """Extract video ID from a TikTok URL."""
    path = parsed.path.rstrip("/")
    # /@user/video/VIDEO_ID or /v/VIDEO_ID
    video_match = re.search(r"/(?:video|v)/(\d+)", path)
    if video_match:
        return video_match.group(1)
    # /t/SHORT_CODE (vm.tiktok.com redirect)
    t_match = re.match(r"^/t/([A-Za-z0-9]+)", path)
    if t_match:
        return t_match.group(1)
    # vm.tiktok.com/CODE or vt.tiktok.com/CODE
    if parsed.hostname and any(d in parsed.hostname.lower() for d in ("vm.tiktok", "vt.tiktok")):
        code = path.lstrip("/").split("/")[0] if path.lstrip("/") else None
        if code and re.match(r"^[A-Za-z0-9]+$", code):
            return code
    return None


def validate_url(url: str) -> ValidatedURL:
    """
    Validate and parse a URL for downloading.

    Returns ValidatedURL with is_valid=True if the URL is safe and supported.
    Rejects: non-http(s) schemes, private IPs, unsupported domains,
    playlist URLs (only single video).
    """
    url = url.strip()
    if not url:
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "กรุณาใส่ลิงก์")

    # Reject obvious non-URLs
    if not url.startswith(("http://", "https://")):
        # Try adding https:// if it looks like a domain
        if "." in url and " " not in url:
            url = "https://" + url
        else:
            return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                                "ตรวจสอบรูปแบบลิงก์อีกครั้ง")

    try:
        parsed = urlparse(url)
    except Exception:
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "ตรวจสอบรูปแบบลิงก์อีกครั้ง")

    # Scheme check
    if parsed.scheme not in ("http", "https"):
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "รองรับเฉพาะลิงก์ http และ https")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "ตรวจสอบรูปแบบลิงก์อีกครั้ง")

    # Private IP / localhost rejection
    if _is_private_ip(hostname):
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "ตรวจสอบรูปแบบลิงก์อีกครั้ง")

    # Domain allowlist
    if hostname not in _ALLOWED_DOMAINS:
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "รองรับเฉพาะ YouTube และ TikTok ในรุ่นนี้")

    # Determine platform
    if hostname in _YOUTUBE_DOMAINS:
        platform = Platform.YOUTUBE
        media_id = _extract_youtube_id(parsed)

        # Reject playlist-only URLs (no video ID)
        qs = parse_qs(parsed.query)
        if "list" in qs and not media_id:
            return ValidatedURL(url, "", platform, None, False,
                                "รุ่นนี้รองรับเฉพาะวิดีโอเดี่ยว ไม่รองรับ playlist")

        # Build clean URL
        if media_id:
            clean = f"https://www.youtube.com/watch?v={media_id}"
        else:
            clean = url

    elif hostname in _TIKTOK_DOMAINS:
        platform = Platform.TIKTOK
        media_id = _extract_tiktok_id(parsed)
        clean = url  # TikTok URLs are used as-is for yt-dlp
    else:
        return ValidatedURL(url, "", Platform.UNKNOWN, None, False,
                            "รองรับเฉพาะ YouTube และ TikTok ในรุ่นนี้")

    return ValidatedURL(
        original_url=url,
        clean_url=clean,
        platform=platform,
        media_id=media_id,
        is_valid=True,
    )
