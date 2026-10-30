"""FFprobe adapter — verify downloaded files are valid and complete."""

import json
import os
import subprocess
from dataclasses import dataclass, field
from typing import Optional

from app.services.dependency_service import get_tool_path


@dataclass
class StreamInfo:
    """Info about one stream in a media file."""

    codec_type: str  # "video" or "audio"
    codec_name: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    bit_rate: Optional[int] = None


@dataclass
class VerificationResult:
    """Result of file verification."""

    passed: bool
    file_path: str
    file_size: int = 0
    duration: Optional[float] = None
    video_streams: list[StreamInfo] = field(default_factory=list)
    audio_streams: list[StreamInfo] = field(default_factory=list)
    format_name: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def verify_file(
    file_path: str,
    expected_video: bool = True,
    expected_audio: bool = True,
    expected_duration: Optional[float] = None,
    duration_tolerance: float = 2.0,
) -> VerificationResult:
    """
    Verify a downloaded media file using FFprobe.

    Checks:
    - File exists and size > 0
    - FFprobe can read it
    - Expected streams are present
    - Duration is consistent (within tolerance)
    """
    result = VerificationResult(passed=False, file_path=file_path)

    # Basic file checks
    if not os.path.isfile(file_path):
        result.errors.append("ไฟล์ไม่มีอยู่")
        return result

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        result.errors.append("ไฟล์มีขนาด 0 ไบต์")
        return result
    result.file_size = file_size

    # Run FFprobe
    ffprobe_path = get_tool_path("ffprobe")
    if not ffprobe_path:
        result.errors.append("ไม่พบ FFprobe — ไม่สามารถตรวจสอบไฟล์ได้")
        # Still mark as passed if file exists and has size
        result.passed = True
        result.warnings.append("ไม่ได้ตรวจสอบด้วย FFprobe")
        return result

    try:
        proc = subprocess.run(
            [
                ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except subprocess.TimeoutExpired:
        result.errors.append("FFprobe ใช้เวลานานเกินกำหนด")
        return result
    except (FileNotFoundError, OSError) as e:
        result.errors.append(f"ไม่สามารถเรียก FFprobe: {e}")
        return result

    if proc.returncode != 0:
        result.errors.append("FFprobe ไม่สามารถอ่านไฟล์ได้")
        return result

    # Parse FFprobe output
    try:
        data = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        result.errors.append("ไม่สามารถอ่านผลลัพธ์จาก FFprobe")
        return result

    # Parse format info
    fmt = data.get("format", {})
    result.format_name = fmt.get("format_name", "")
    try:
        result.duration = float(fmt.get("duration", 0))
    except (ValueError, TypeError):
        pass

    # Parse streams
    for stream in data.get("streams", []):
        codec_type = stream.get("codec_type", "")
        si = StreamInfo(
            codec_type=codec_type,
            codec_name=stream.get("codec_name", ""),
            width=stream.get("width"),
            height=stream.get("height"),
            sample_rate=_safe_int(stream.get("sample_rate")),
            channels=stream.get("channels"),
            bit_rate=_safe_int(stream.get("bit_rate")),
        )
        try:
            si.duration = float(stream.get("duration", 0))
        except (ValueError, TypeError):
            pass

        if codec_type == "video":
            result.video_streams.append(si)
        elif codec_type == "audio":
            result.audio_streams.append(si)

    # Validate expected streams
    if expected_video and not result.video_streams:
        result.errors.append("ไม่พบ video stream ในไฟล์")

    if expected_audio and not result.audio_streams:
        result.errors.append("ไม่พบ audio stream ในไฟล์")

    # Duration check
    if expected_duration is not None and result.duration is not None:
        diff = abs(result.duration - expected_duration)
        if diff > duration_tolerance:
            result.warnings.append(
                f"ระยะเวลาไฟล์ ({result.duration:.1f}s) ต่างจากต้นทาง "
                f"({expected_duration:.1f}s) มากกว่า {duration_tolerance}s"
            )

    # Final verdict
    result.passed = len(result.errors) == 0
    return result


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
