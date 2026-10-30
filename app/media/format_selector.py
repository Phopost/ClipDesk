"""Format selection logic — testable without GUI or network."""

from dataclasses import dataclass
from typing import Optional

from app.core.models import MediaInfo, VideoFormat, OutputType, QualityPolicy


@dataclass
class QualityOption:
    """One user-selectable quality option for the UI."""

    label: str  # e.g. "1920×1080 · 60fps"
    height: int  # effective height for sorting
    fps: float
    video_format_id: Optional[str] = None
    audio_format_id: Optional[str] = None
    size_label: str = "ยังไม่ทราบขนาด"
    needs_merge: bool = False  # video+audio separate streams
    needs_remux: bool = False  # container mismatch
    codec_info: str = ""  # e.g. "H.264 + AAC"


@dataclass
class FormatSelection:
    """Result of format selection — what to download and how."""

    video_format_id: Optional[str] = None
    audio_format_id: Optional[str] = None
    needs_merge: bool = False
    needs_remux: bool = False
    needs_transcode: bool = False
    output_ext: str = "mp4"
    codec_info: str = ""
    estimated_size: Optional[int] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def _is_h264(vcodec: Optional[str]) -> bool:
    if not vcodec:
        return False
    v = vcodec.lower()
    return "avc" in v or "h264" in v or "h.264" in v


def _is_aac(acodec: Optional[str]) -> bool:
    if not acodec:
        return False
    return "aac" in acodec.lower() or "mp4a" in acodec.lower()


def _is_mp4_container(ext: Optional[str]) -> bool:
    if not ext:
        return False
    return ext.lower() in ("mp4", "m4a", "m4v")


def get_video_quality_options(
    info: MediaInfo, prefer_compatible: bool = True
) -> list[QualityOption]:
    """
    Build quality options for MP4 download from real format data.

    Groups by resolution + fps. Shows only what actually exists.
    For portrait videos, shows actual dimensions with orientation label.
    """
    if not info.formats:
        return []

    # Separate video-only, audio-only, and muxed formats
    video_formats = [f for f in info.formats if f.has_video]
    audio_formats = [f for f in info.formats if f.has_audio and not f.has_video]
    muxed_formats = [f for f in info.formats if f.has_video and f.has_audio]

    # Find best audio format for merging
    best_audio = _pick_best_audio(audio_formats, prefer_aac=prefer_compatible)

    # Group video formats by (width, height, fps_bucket)
    seen: dict[tuple, QualityOption] = {}

    for vf in video_formats:
        if not vf.width or not vf.height:
            continue

        fps = vf.fps or 30.0
        fps_bucket = 60.0 if fps > 50 else 30.0
        key = (vf.width, vf.height, fps_bucket)

        if prefer_compatible and not _is_h264(vf.vcodec):
            continue  # Skip non-H.264 in compatible mode

        # Check if better than current entry
        current = seen.get(key)
        if current is not None:
            # Prefer higher bitrate within same resolution
            current_tbr = 0
            new_tbr = vf.tbr or 0
            if new_tbr <= current_tbr:
                continue

        # Calculate combined size
        combined_size = None
        vf_size = vf.effective_size
        if vf_size and best_audio and best_audio.effective_size:
            combined_size = vf_size + best_audio.effective_size

        # Build label
        orient = " · แนวตั้ง" if vf.is_portrait else ""
        fps_label = f" {int(fps_bucket)}fps" if fps_bucket > 30 else ""
        codec_label = vf.vcodec or "?"
        if _is_h264(vf.vcodec):
            codec_label = "H.264"
        audio_codec = ""
        if best_audio and _is_aac(best_audio.acodec):
            audio_codec = " + AAC"
        elif best_audio:
            audio_codec = f" + {best_audio.acodec or '?'}"

        option = QualityOption(
            label=f"{vf.width}×{vf.height}{orient}{fps_label}",
            height=vf.short_height or vf.height,
            fps=fps_bucket,
            video_format_id=vf.format_id,
            audio_format_id=best_audio.format_id if best_audio else None,
            size_label=_format_combined_size(vf_size, best_audio.effective_size if best_audio else None),
            needs_merge=best_audio is not None and not vf.has_audio,
            codec_info=f"{codec_label}{audio_codec}",
        )
        seen[key] = option

    # Also include muxed formats (video+audio in one stream)
    for mf in muxed_formats:
        if not mf.width or not mf.height:
            continue
        if prefer_compatible and not _is_h264(mf.vcodec):
            continue

        fps = mf.fps or 30.0
        fps_bucket = 60.0 if fps > 50 else 30.0
        key = (mf.width, mf.height, fps_bucket)

        if key not in seen:
            orient = " · แนวตั้ง" if mf.is_portrait else ""
            fps_label = f" {int(fps_bucket)}fps" if fps_bucket > 30 else ""
            seen[key] = QualityOption(
                label=f"{mf.width}×{mf.height}{orient}{fps_label}",
                height=mf.short_height or mf.height,
                fps=fps_bucket,
                video_format_id=mf.format_id,
                audio_format_id=None,
                size_label=mf.size_label,
                needs_merge=False,
                codec_info=f"{'H.264' if _is_h264(mf.vcodec) else mf.vcodec or '?'} + {'AAC' if _is_aac(mf.acodec) else mf.acodec or '?'}",
            )

    # Sort by height (descending), then fps (descending)
    options = sorted(seen.values(), key=lambda o: (o.height, o.fps), reverse=True)
    return options


def get_audio_quality_options() -> list[QualityOption]:
    """Return the fixed MP3 bitrate options."""
    return [
        QualityOption(label="128 kbps", height=0, fps=0),
        QualityOption(label="192 kbps (แนะนำ)", height=0, fps=0),
        QualityOption(label="256 kbps", height=0, fps=0),
        QualityOption(label="320 kbps", height=0, fps=0),
    ]


AUDIO_BITRATE_MAP = {
    "128 kbps": 128,
    "192 kbps (แนะนำ)": 192,
    "256 kbps": 256,
    "320 kbps": 320,
}


def select_format(
    info: MediaInfo, policy: QualityPolicy
) -> FormatSelection:
    """
    Select the best format(s) to download based on user policy.

    This is the core logic — MUST be testable without GUI.
    """
    if policy.output_type == OutputType.MP3:
        return _select_audio_format(info, policy)
    return _select_video_format(info, policy)


def _select_video_format(info: MediaInfo, policy: QualityPolicy) -> FormatSelection:
    """Select format(s) for MP4 download."""
    selection = FormatSelection(output_ext="mp4")

    if not info.formats:
        selection.warnings.append("ไม่พบรูปแบบที่ดาวน์โหลดได้")
        return selection

    # If specific format IDs are already chosen (from UI quality selector)
    if policy.selected_video_format_id:
        selection.video_format_id = policy.selected_video_format_id
        selection.audio_format_id = policy.selected_audio_format_id
        if selection.audio_format_id:
            selection.needs_merge = True

        # Check if remux needed
        vf = _find_format(info, policy.selected_video_format_id)
        if vf and not _is_mp4_container(vf.ext):
            if _is_h264(vf.vcodec):
                selection.needs_remux = True
            else:
                selection.needs_transcode = True
                selection.warnings.append(
                    "codec ต้นทางไม่ใช่ H.264 อาจต้องเข้ารหัสใหม่"
                )

        # Estimate size
        size = 0
        if vf and vf.effective_size:
            size += vf.effective_size
        af = _find_format(info, policy.selected_audio_format_id) if policy.selected_audio_format_id else None
        if af and af.effective_size:
            size += af.effective_size
        if size > 0:
            selection.estimated_size = size

        return selection

    # Auto-select best matching format
    video_formats = [f for f in info.formats if f.has_video]
    audio_formats = [f for f in info.formats if f.has_audio and not f.has_video]

    target_height = policy.preferred_height or 1080
    target_fps = policy.preferred_fps or 30.0

    # Filter by compatible codec if requested
    if policy.prefer_compatible:
        h264_videos = [f for f in video_formats if _is_h264(f.vcodec)]
        if h264_videos:
            video_formats = h264_videos

    # Find best video at or below target height
    best_video = None
    for vf in sorted(video_formats, key=lambda f: (f.short_height or 0, f.fps or 0), reverse=True):
        sh = vf.short_height or 0
        if sh <= target_height:
            if best_video is None or sh > (best_video.short_height or 0):
                best_video = vf
            elif sh == (best_video.short_height or 0):
                # Same height — prefer matching fps
                if abs((vf.fps or 30) - target_fps) < abs((best_video.fps or 30) - target_fps):
                    best_video = vf
    
    if best_video is None and video_formats:
        # No format at or below target — use lowest available
        best_video = min(video_formats, key=lambda f: f.short_height or 9999)

    if best_video:
        selection.video_format_id = best_video.format_id

        if not best_video.has_audio:
            best_audio = _pick_best_audio(audio_formats, prefer_aac=policy.prefer_compatible)
            if best_audio:
                selection.audio_format_id = best_audio.format_id
                selection.needs_merge = True
        
        # Check container compatibility
        if not _is_mp4_container(best_video.ext):
            selection.needs_remux = True

        codec = best_video.vcodec or ""
        acodec = ""
        if selection.audio_format_id:
            af = _find_format(info, selection.audio_format_id)
            acodec = af.acodec if af else ""
        elif best_video.has_audio:
            acodec = best_video.acodec or ""
        
        selection.codec_info = f"{'H.264' if _is_h264(codec) else codec} + {'AAC' if _is_aac(acodec) else acodec}"

    return selection


def _select_audio_format(info: MediaInfo, policy: QualityPolicy) -> FormatSelection:
    """Select format for MP3 download."""
    selection = FormatSelection(output_ext="mp3")

    # yt-dlp handles audio extraction — we just need to specify format
    # Use best audio-only format, or best format with audio
    audio_formats = [f for f in info.formats if f.has_audio and not f.has_video]

    if audio_formats:
        best = _pick_best_audio(audio_formats, prefer_aac=False)
        if best:
            selection.audio_format_id = best.format_id
            if best.effective_size:
                selection.estimated_size = best.effective_size
    else:
        # Fall back to muxed format with audio
        muxed = [f for f in info.formats if f.has_audio]
        if muxed:
            best = max(muxed, key=lambda f: f.abr or 0)
            selection.audio_format_id = best.format_id

    selection.codec_info = f"MP3 {policy.preferred_bitrate}kbps"
    return selection


def _pick_best_audio(
    audio_formats: list[VideoFormat], prefer_aac: bool = True
) -> Optional[VideoFormat]:
    """Pick the best audio-only format."""
    if not audio_formats:
        return None

    if prefer_aac:
        aac_formats = [f for f in audio_formats if _is_aac(f.acodec)]
        if aac_formats:
            return max(aac_formats, key=lambda f: f.abr or f.tbr or 0)

    return max(audio_formats, key=lambda f: f.abr or f.tbr or 0)


def _find_format(info: MediaInfo, format_id: Optional[str]) -> Optional[VideoFormat]:
    """Find a format by ID."""
    if not format_id:
        return None
    for f in info.formats:
        if f.format_id == format_id:
            return f
    return None


def _format_combined_size(
    video_size: Optional[int], audio_size: Optional[int]
) -> str:
    """Format combined file size label."""
    if video_size is None and audio_size is None:
        return "ยังไม่ทราบขนาด"

    total = (video_size or 0) + (audio_size or 0)
    is_approx = video_size is None or audio_size is None
    prefix = "ประมาณ " if is_approx else ""

    if total < 1024 * 1024:
        return f"{prefix}{total / 1024:.0f} KB"
    elif total < 1024 * 1024 * 1024:
        return f"{prefix}{total / (1024 * 1024):.1f} MB"
    return f"{prefix}{total / (1024 * 1024 * 1024):.2f} GB"
