"""yt-dlp adapter — runs yt-dlp as external process via QProcess."""

import json
import os
from typing import Optional

from PySide6.QtCore import QObject, Signal, QProcess, QTimer

from app.core.models import (
    MediaInfo, VideoFormat, Platform, DownloadProgress,
    QualityPolicy, OutputType,
)
from app.core.errors import classify_ytdlp_error, ErrorCode
from app.media.progress_parser import ProgressParser
from app.services.dependency_service import get_tool_path, get_js_runtime_args
from app.services.process_supervisor import JobObject, kill_process_tree


class YtDlpAdapter(QObject):
    """
    Manages yt-dlp as an external process for metadata extraction and downloading.

    Signals:
        info_ready(MediaInfo): Metadata successfully extracted
        progress_updated(DownloadProgress): Download progress update
        download_finished(str): Download completed, path to output file
        error_occurred(str, str): (error_code, error_message)
        process_started(): Process has started
        process_ended(): Process has ended (success, error, or cancel)
    """

    info_ready = Signal(object)  # MediaInfo
    progress_updated = Signal(object)  # DownloadProgress
    download_finished = Signal(str)  # output path
    error_occurred = Signal(str, str)  # error_code, detail
    process_started = Signal()
    process_ended = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._job: Optional[JobObject] = None
        self._stderr_buffer = ""
        self._stdout_buffer = ""
        self._progress_parser = ProgressParser()
        self._mode = ""  # "info" or "download"
        self._work_dir = ""
        self._output_template = ""
        self._kill_timer: Optional[QTimer] = None
        self._current_attempt_id = ""

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def extract_info(self, url: str, attempt_id: str = "") -> None:
        """Extract metadata from URL without downloading."""
        if self.is_running:
            return

        self._mode = "info"
        self._current_attempt_id = attempt_id
        self._stdout_buffer = ""
        self._stderr_buffer = ""

        ytdlp_path = get_tool_path("yt-dlp")
        if not ytdlp_path:
            self.error_occurred.emit(
                ErrorCode.DEPENDENCY_MISSING.value,
                "ไม่พบ yt-dlp"
            )
            return

        args = [
            "--ignore-config",
            "--no-playlist",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            "--socket-timeout", "12",
            "--retries", "2",
        ]
        args.extend(get_js_runtime_args())
        args.append(url)

        self._start_process(ytdlp_path, args)

    def start_download(
        self,
        url: str,
        policy: QualityPolicy,
        work_dir: str,
        output_template: str,
        attempt_id: str = "",
    ) -> None:
        """Start downloading with the given quality policy."""
        if self.is_running:
            return

        self._mode = "download"
        self._current_attempt_id = attempt_id
        self._work_dir = work_dir
        self._output_template = output_template
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._progress_parser.reset()

        ytdlp_path = get_tool_path("yt-dlp")
        ffmpeg_path = get_tool_path("ffmpeg")

        if not ytdlp_path:
            self.error_occurred.emit(
                ErrorCode.DEPENDENCY_MISSING.value,
                "ไม่พบ yt-dlp"
            )
            return

        args = [
            "--ignore-config",
            "--no-playlist",
            "--newline",
            "--progress-template", "download:%(progress)j",
            "--concurrent-fragments", "16",
            "--buffer-size", "64K",
            "--http-chunk-size", "10M",
            "--socket-timeout", "15",
            "--retries", "5",
            "--fragment-retries", "5",
            "-o", output_template,
        ]

        # YouTube extraction needs a JS runtime (Node.js) on recent yt-dlp
        args.extend(get_js_runtime_args())

        if ffmpeg_path:
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            args.extend(["--ffmpeg-location", ffmpeg_dir])

        # Format selection based on policy
        if policy.output_type == OutputType.MP3:
            args.extend(self._build_audio_args(policy))
        else:
            args.extend(self._build_video_args(policy))

        args.append(url)
        self._start_process(ytdlp_path, args)

    def _build_video_args(self, policy: QualityPolicy) -> list[str]:
        """Build yt-dlp arguments for video download."""
        args = []

        if policy.selected_video_format_id:
            if policy.selected_audio_format_id:
                fmt = f"{policy.selected_video_format_id}+{policy.selected_audio_format_id}"
            else:
                fmt = policy.selected_video_format_id
            args.extend(["-f", fmt])
        else:
            # Auto-select
            height = policy.preferred_height or 1080
            if policy.prefer_compatible:
                fmt = (
                    f"bestvideo[ext=mp4][vcodec~='^(avc|h264)'][height<={height}]"
                    f"+bestaudio[ext=m4a]"
                    f"/best[ext=mp4][height<={height}]"
                    f"/bestvideo[height<={height}]+bestaudio"
                    f"/best[height<={height}]"
                )
            else:
                fmt = (
                    f"bestvideo[height<={height}]+bestaudio"
                    f"/best[height<={height}]"
                )
            args.extend(["-f", fmt])

        # Merge output format
        args.extend(["--merge-output-format", "mp4"])

        return args

    def _build_audio_args(self, policy: QualityPolicy) -> list[str]:
        """Build yt-dlp arguments for audio extraction."""
        args = [
            "-f", "bestaudio/best",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", f"{policy.preferred_bitrate}k",
        ]
        return args

    def _start_process(self, program: str, args: list[str]) -> None:
        """Start a QProcess with Job Object for process tree management."""
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)

        # Connect signals
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._process.started.connect(self._on_process_started)

        # Create Job Object for process tree cleanup. The process is assigned
        # in _on_process_started() because processId() is still 0 right after
        # start() returns (QProcess starts asynchronously).
        self._job = JobObject()

        self._process.start(program, args)

    def _on_process_started(self) -> None:
        """Assign the freshly started process (and its children) to the job."""
        if self._job and self._process:
            pid = int(self._process.processId())
            if pid:
                self._job.assign(pid)
        self.process_started.emit()

    def _on_stdout(self) -> None:
        """Handle stdout data from yt-dlp."""
        if self._process is None:
            return

        raw = self._process.readAllStandardOutput()
        try:
            text = bytes(raw).decode("utf-8", errors="replace")
        except Exception:
            return

        if self._mode == "info":
            self._stdout_buffer += text
        elif self._mode == "download":
            progress = self._progress_parser.feed(text)
            if progress:
                self.progress_updated.emit(progress)

    def _on_stderr(self) -> None:
        """Handle stderr data from yt-dlp."""
        if self._process is None:
            return

        raw = self._process.readAllStandardError()
        try:
            text = bytes(raw).decode("utf-8", errors="replace")
        except Exception:
            return

        self._stderr_buffer += text

        # Also feed stderr to progress parser (yt-dlp outputs some progress there)
        if self._mode == "download":
            progress = self._progress_parser.feed(text)
            if progress:
                self.progress_updated.emit(progress)

    def _on_finished(self, exit_code: int, exit_status) -> None:
        """Handle process completion."""
        if self._mode == "info":
            self._handle_info_finished(exit_code)
        elif self._mode == "download":
            self._handle_download_finished(exit_code)

        self._cleanup_job()
        self.process_ended.emit()

    def _on_error(self, error) -> None:
        """Handle process error (crash, not found, etc.)."""
        error_map = {
            QProcess.ProcessError.FailedToStart: "ไม่สามารถเริ่ม yt-dlp ได้",
            QProcess.ProcessError.Crashed: "yt-dlp หยุดทำงานผิดปกติ",
            QProcess.ProcessError.Timedout: "yt-dlp ใช้เวลานานเกินกำหนด",
        }
        msg = error_map.get(error, "เกิดข้อผิดพลาดที่ไม่คาดคิด")
        self.error_occurred.emit(ErrorCode.UNKNOWN.value, msg)
        self._cleanup_job()
        self.process_ended.emit()

    def _handle_info_finished(self, exit_code: int) -> None:
        """Process metadata extraction result."""
        if exit_code != 0:
            error_code = classify_ytdlp_error(self._stderr_buffer)
            self.error_occurred.emit(error_code.value, self._stderr_buffer[:500])
            return

        try:
            data = json.loads(self._stdout_buffer)
            info = self._parse_media_info(data)
            self.info_ready.emit(info)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.error_occurred.emit(
                ErrorCode.UNKNOWN.value,
                f"ไม่สามารถอ่านข้อมูลคลิปได้: {e}"
            )

    def _handle_download_finished(self, exit_code: int) -> None:
        """Process download completion."""
        if exit_code != 0:
            error_code = classify_ytdlp_error(self._stderr_buffer)
            self.error_occurred.emit(error_code.value, self._stderr_buffer[:500])
            return

        # Find the output file
        output_path = self._find_output_file()
        if output_path:
            self.download_finished.emit(output_path)
        else:
            self.error_occurred.emit(
                ErrorCode.VERIFICATION_FAILED.value,
                "ไม่พบไฟล์ผลลัพธ์หลังดาวน์โหลด"
            )

    def _find_output_file(self) -> Optional[str]:
        """Find the downloaded file in work directory."""
        if not self._work_dir or not os.path.isdir(self._work_dir):
            return None

        # Look for the most recently modified media file
        candidates = []
        for fname in os.listdir(self._work_dir):
            fpath = os.path.join(self._work_dir, fname)
            if os.path.isfile(fpath):
                ext = os.path.splitext(fname)[1].lower()
                if ext in (".mp4", ".mp3", ".m4a", ".webm", ".mkv"):
                    candidates.append((os.path.getmtime(fpath), fpath))

        if candidates:
            candidates.sort(reverse=True)
            return candidates[0][1]
        return None

    def _parse_media_info(self, data: dict) -> MediaInfo:
        """Parse yt-dlp JSON output into MediaInfo."""
        # Determine platform
        extractor = (data.get("extractor", "") or "").lower()
        if "youtube" in extractor:
            platform = Platform.YOUTUBE
        elif "tiktok" in extractor:
            platform = Platform.TIKTOK
        else:
            platform = Platform.UNKNOWN

        # Parse formats
        formats = []
        for fmt in data.get("formats", []):
            vcodec = fmt.get("vcodec", "none")
            acodec = fmt.get("acodec", "none")

            vf = VideoFormat(
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
            formats.append(vf)

        # Check if any format has audio
        has_audio = any(f.has_audio for f in formats)

        # Format view count label if present
        vc = data.get("view_count")
        vc_label = None
        if isinstance(vc, (int, float)) and vc >= 0:
            if vc >= 1_000_000:
                vc_label = f"{vc / 1_000_000:.1f}M ครั้ง"
            elif vc >= 1_000:
                vc_label = f"{vc / 1_000:.1f}K ครั้ง"
            else:
                vc_label = f"{int(vc)} ครั้ง"

        uploader = data.get("uploader") or data.get("channel")
        raw_desc = (data.get("description") or "").strip().splitlines()
        first_line = raw_desc[0].strip() if raw_desc else ""
        if len(first_line) > 70:
            first_line = first_line[:67] + "..."
        desc_sub = first_line or (f"ช่อง: {uploader} 🎵" if uploader else None)

        return MediaInfo(
            media_id=data.get("id", ""),
            title=data.get("title", "ไม่ทราบชื่อ"),
            platform=platform,
            duration=data.get("duration"),
            thumbnail_url=data.get("thumbnail"),
            uploader=uploader,
            formats=formats,
            webpage_url=data.get("webpage_url", ""),
            has_audio_track=has_audio,
            view_count_label=vc_label,
            description_subtitle=desc_sub,
        )

    def cancel(self) -> None:
        """Cancel the current operation — graceful then force kill."""
        if not self.is_running:
            return

        # Try graceful termination first (WM_CLOSE / polite signal)
        self._process.terminate()

        # Force-kill the whole tree if the process ignores us
        self._kill_timer = QTimer(self)
        self._kill_timer.setSingleShot(True)
        self._kill_timer.timeout.connect(self._force_kill)
        self._kill_timer.start(4000)

    def _force_kill(self) -> None:
        """Force kill the process tree if still running."""
        pid = int(self._process.processId()) if self._process else 0
        if self._job and self._job.is_valid:
            # KILL_ON_JOB_CLOSE terminates yt-dlp + ffmpeg + node at once
            self._job.terminate()
        if self.is_running:
            self._process.kill()
        if pid:
            # Belt and braces: taskkill /T in case the job was not assigned
            kill_process_tree(pid)
        self._cleanup_job()

    def _cleanup_job(self) -> None:
        """Close the Job Object handle (kills any lingering children)."""
        if self._kill_timer:
            self._kill_timer.stop()
            self._kill_timer = None

        if self._job:
            self._job.close()
            self._job = None

        self._process = None
