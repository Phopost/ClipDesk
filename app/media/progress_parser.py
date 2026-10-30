"""Parse yt-dlp progress output into structured data."""

import json
import time
from typing import Optional

from app.core.models import DownloadProgress


class ProgressParser:
    """
    Parse yt-dlp structured progress output.

    Uses --progress-template for JSON-based progress (preferred)
    and falls back to line-based parsing for legacy output.

    Rate-limits updates to ~4-5 per second.
    """

    def __init__(self, update_interval: float = 0.22):
        self._buffer = ""
        self._last_update_time: float = 0.0
        self._update_interval = update_interval
        self._current_phase = ""
        self._phase_counter = 0  # Track video vs audio download

    def set_phase(self, phase: str) -> None:
        """Set the current download phase explicitly."""
        self._current_phase = phase

    def feed(self, data: str) -> Optional[DownloadProgress]:
        """
        Feed raw output data. Returns DownloadProgress if a complete
        update is ready and rate-limit allows, else None.
        """
        self._buffer += data
        # Process complete lines only
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.strip()
            if not line:
                continue

            progress = self._parse_line(line)
            if progress is not None:
                now = time.time()
                if now - self._last_update_time >= self._update_interval:
                    self._last_update_time = now
                    return progress

        return None

    def _parse_line(self, line: str) -> Optional[DownloadProgress]:
        """Parse one complete line of output."""
        # Try JSON first (from --progress-template)
        if line.startswith("{"):
            return self._parse_json(line)

        # Fallback: parse yt-dlp default progress lines
        return self._parse_text(line)

    def _parse_json(self, line: str) -> Optional[DownloadProgress]:
        """Parse JSON progress template output."""
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return None

        # yt-dlp progress template fields
        status = data.get("status", "")

        if status == "downloading":
            return DownloadProgress(
                phase=self._current_phase or "กำลังดาวน์โหลด",
                downloaded_bytes=_safe_int(data.get("downloaded_bytes", 0)),
                total_bytes=_safe_int(data.get("total_bytes") or data.get("total_bytes_estimate")),
                speed=_safe_float(data.get("speed")),
                eta=_safe_float(data.get("eta")),
                percent=_safe_float(data.get("_percent_str", "").replace("%", "").strip())
                if "_percent_str" in data
                else _calc_percent(
                    _safe_int(data.get("downloaded_bytes")),
                    _safe_int(data.get("total_bytes") or data.get("total_bytes_estimate")),
                ),
            )
        elif status == "finished":
            return DownloadProgress(
                phase=self._current_phase or "เสร็จสิ้น",
                downloaded_bytes=_safe_int(data.get("downloaded_bytes", 0)),
                total_bytes=_safe_int(data.get("total_bytes", 0)),
                percent=100.0,
            )
        elif status == "error":
            return DownloadProgress(
                phase="เกิดข้อผิดพลาด",
            )

        return None

    def _parse_text(self, line: str) -> Optional[DownloadProgress]:
        """Parse yt-dlp text progress output as fallback."""
        # [download]  45.2% of 10.50MiB at  2.30MiB/s ETA 00:03
        if not line.startswith("[download]"):
            # Detect post-processing phases
            if "[Merger]" in line or "Merging" in line:
                self._current_phase = "กำลังรวมไฟล์"
                return DownloadProgress(phase="กำลังรวมไฟล์")
            if "[ExtractAudio]" in line:
                self._current_phase = "กำลังแปลงเสียง"
                return DownloadProgress(phase="กำลังแปลงเสียง")
            if "Destination:" in line:
                # New stream download starting
                self._phase_counter += 1
                if self._phase_counter == 1:
                    self._current_phase = "กำลังดาวน์โหลดภาพ"
                elif self._phase_counter == 2:
                    self._current_phase = "กำลังดาวน์โหลดเสียง"
            return None

        content = line[len("[download]"):].strip()

        # "100% of 10.50MiB"
        # "45.2% of 10.50MiB at 2.30MiB/s ETA 00:03"
        # "Destination: filename"
        if content.startswith("Destination:"):
            self._phase_counter += 1
            if self._phase_counter == 1:
                self._current_phase = "กำลังดาวน์โหลดภาพ"
            elif self._phase_counter == 2:
                self._current_phase = "กำลังดาวน์โหลดเสียง"
            return None

        # Try to parse percentage
        percent = None
        downloaded = 0
        total = None
        speed = None
        eta = None

        parts = content.split()
        if parts and parts[0].endswith("%"):
            try:
                percent = float(parts[0].replace("%", ""))
            except ValueError:
                pass

        # Parse "of X.XXMiB"
        if "of" in content:
            try:
                of_idx = parts.index("of")
                if of_idx + 1 < len(parts):
                    total_str = parts[of_idx + 1]
                    total = _parse_size(total_str)
                    if total and percent:
                        downloaded = int(total * percent / 100)
            except (ValueError, IndexError):
                pass

        # Parse speed "at X.XXMiB/s"
        if "at" in content:
            try:
                at_idx = parts.index("at")
                if at_idx + 1 < len(parts):
                    speed = _parse_size(parts[at_idx + 1].replace("/s", ""))
            except (ValueError, IndexError):
                pass

        # Parse ETA "ETA HH:MM:SS" or "ETA MM:SS"
        if "ETA" in content:
            try:
                eta_idx = parts.index("ETA")
                if eta_idx + 1 < len(parts):
                    eta = _parse_eta(parts[eta_idx + 1])
            except (ValueError, IndexError):
                pass

        if percent is not None:
            return DownloadProgress(
                phase=self._current_phase or "กำลังดาวน์โหลด",
                downloaded_bytes=downloaded,
                total_bytes=total,
                speed=speed,
                eta=eta,
                percent=percent,
            )

        return None

    def reset(self) -> None:
        """Reset parser state for a new download."""
        self._buffer = ""
        self._last_update_time = 0.0
        self._current_phase = ""
        self._phase_counter = 0


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _calc_percent(downloaded: Optional[int], total: Optional[int]) -> Optional[float]:
    if downloaded and total and total > 0:
        return round(downloaded / total * 100, 1)
    return None


def _parse_size(s: str) -> Optional[int]:
    """Parse size string like '10.50MiB' or '1.20GiB' to bytes."""
    s = s.strip()
    multipliers = {
        "B": 1,
        "KiB": 1024,
        "MiB": 1024 ** 2,
        "GiB": 1024 ** 3,
        "TiB": 1024 ** 4,
        "KB": 1000,
        "MB": 1000 ** 2,
        "GB": 1000 ** 3,
    }
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if s.endswith(suffix):
            try:
                return int(float(s[: -len(suffix)]) * mult)
            except ValueError:
                return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _parse_eta(s: str) -> Optional[float]:
    """Parse ETA string like '00:03' or '1:02:30' to seconds."""
    parts = s.split(":")
    try:
        parts = [int(p) for p in parts]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except ValueError:
        pass
    return None
