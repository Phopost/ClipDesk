"""ClipDesk core data models."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import uuid
import time


class Platform(Enum):
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    UNKNOWN = "unknown"


class OutputType(Enum):
    MP4 = "mp4"
    MP3 = "mp3"


class TaskState(Enum):
    QUEUED = auto()
    RESOLVING = auto()
    DOWNLOADING = auto()
    POSTPROCESSING = auto()
    VERIFYING = auto()
    COMPLETED = auto()
    CANCELLING = auto()
    CANCELLED = auto()
    FAILED = auto()
    PAUSED = auto()


# Valid state transitions — enforced at runtime
VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.QUEUED: {TaskState.RESOLVING, TaskState.CANCELLING},
    TaskState.RESOLVING: {TaskState.DOWNLOADING, TaskState.FAILED, TaskState.CANCELLING},
    TaskState.DOWNLOADING: {
        TaskState.POSTPROCESSING,
        TaskState.COMPLETED,
        TaskState.FAILED,
        TaskState.CANCELLING,
        TaskState.PAUSED,
    },
    TaskState.PAUSED: {TaskState.DOWNLOADING, TaskState.QUEUED, TaskState.CANCELLING},
    TaskState.POSTPROCESSING: {TaskState.VERIFYING, TaskState.FAILED, TaskState.CANCELLING},
    TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLING},
    TaskState.CANCELLING: {TaskState.CANCELLED},
    TaskState.COMPLETED: set(),
    TaskState.CANCELLED: set(),
    TaskState.FAILED: {TaskState.QUEUED},  # retry path
}


@dataclass
class VideoFormat:
    """One downloadable stream/format from yt-dlp."""

    format_id: str
    ext: str
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    vcodec: Optional[str] = None
    acodec: Optional[str] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    tbr: Optional[float] = None
    abr: Optional[float] = None

    @property
    def has_video(self) -> bool:
        return bool(self.vcodec and self.vcodec != "none")

    @property
    def has_audio(self) -> bool:
        return bool(self.acodec and self.acodec != "none")

    @property
    def is_portrait(self) -> bool:
        if self.width and self.height:
            return self.height > self.width
        return False

    @property
    def resolution_label(self) -> str:
        if not self.has_video or not self.width or not self.height:
            return "เสียงอย่างเดียว"
        orient = " · แนวตั้ง" if self.is_portrait else ""
        fps_str = f" {int(self.fps)}fps" if self.fps and self.fps > 30 else ""
        return f"{self.width}×{self.height}{orient}{fps_str}"

    @property
    def effective_size(self) -> Optional[int]:
        return self.filesize or self.filesize_approx

    @property
    def size_label(self) -> str:
        size = self.effective_size
        if size is None:
            return "ยังไม่ทราบขนาด"
        prefix = "" if self.filesize else "ประมาณ "
        if size < 1024 * 1024:
            return f"{prefix}{size / 1024:.0f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{prefix}{size / (1024 * 1024):.1f} MB"
        return f"{prefix}{size / (1024 * 1024 * 1024):.2f} GB"

    @property
    def short_height(self) -> Optional[int]:
        """Effective height for quality comparison (min dimension for portrait)."""
        if self.width and self.height:
            return min(self.width, self.height) if self.is_portrait else self.height
        return self.height


@dataclass
class MediaInfo:
    """Metadata about a video/audio clip."""

    media_id: str
    title: str
    platform: Platform
    duration: Optional[float] = None
    thumbnail_url: Optional[str] = None
    uploader: Optional[str] = None
    formats: list[VideoFormat] = field(default_factory=list)
    webpage_url: str = ""
    has_audio_track: bool = True  # Some clips genuinely have no audio
    view_count_label: Optional[str] = None
    description_subtitle: Optional[str] = None

    @property
    def duration_label(self) -> str:
        if self.duration is None:
            return "ไม่ทราบระยะเวลา"
        total = int(self.duration)
        m, s = divmod(total, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"


@dataclass
class QualityPolicy:
    """User's quality selection — snapshot at task creation time."""

    output_type: OutputType
    # MP4
    preferred_height: Optional[int] = None
    preferred_fps: Optional[float] = None
    prefer_compatible: bool = True  # H.264 + AAC
    selected_video_format_id: Optional[str] = None
    selected_audio_format_id: Optional[str] = None
    # MP3
    preferred_bitrate: int = 192
    # Fallback
    allow_lower_quality: bool = False


@dataclass
class DownloadProgress:
    """Real-time progress from yt-dlp/FFmpeg."""

    phase: str = ""  # "ดาวน์โหลดภาพ", "ดาวน์โหลดเสียง", "รวมไฟล์", "แปลงเสียง"
    downloaded_bytes: int = 0
    total_bytes: Optional[int] = None
    speed: Optional[float] = None  # bytes/sec
    eta: Optional[float] = None  # seconds
    percent: Optional[float] = None


@dataclass
class DownloadTask:
    """One download job in the queue."""

    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attempt_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_url: str = ""
    platform: Platform = Platform.UNKNOWN
    media_id: str = ""
    title: str = ""
    quality_policy: Optional[QualityPolicy] = None
    destination_dir: str = ""
    work_dir: str = ""
    state: TaskState = TaskState.QUEUED
    progress: DownloadProgress = field(default_factory=DownloadProgress)
    output_path: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    error_detail: Optional[str] = None  # raw technical text for "ดูรายละเอียด"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    media_info: Optional[MediaInfo] = None
    thumbnail_path: Optional[str] = None

    def can_transition_to(self, new_state: TaskState) -> bool:
        return new_state in VALID_TRANSITIONS.get(self.state, set())

    def transition_to(self, new_state: TaskState) -> bool:
        if self.can_transition_to(new_state):
            self.state = new_state
            if new_state == TaskState.RESOLVING and self.started_at is None:
                self.started_at = time.time()
            elif new_state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
                self.completed_at = time.time()
            return True
        return False

    def new_attempt(self) -> None:
        """Reset for retry with a fresh attempt_id."""
        self.attempt_id = str(uuid.uuid4())
        self.state = TaskState.QUEUED
        self.progress = DownloadProgress()
        self.output_path = None
        self.error_code = None
        self.error_message = None
        self.started_at = None
        self.completed_at = None
