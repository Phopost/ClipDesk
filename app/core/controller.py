"""Application controller — connects UI events to download logic."""

import os
import time
from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal

from app.core.models import (
    DownloadTask, DownloadProgress, MediaInfo, TaskState,
    QualityPolicy, OutputType, Platform,
)
from app.core.errors import ErrorCode, get_user_message
from app.core.queue_manager import QueueManager
from app.media.ytdlp_adapter import YtDlpAdapter
from app.media.ffprobe_adapter import verify_file
from app.media.format_selector import select_format
from app.services.url_validator import validate_url
from app.services.path_service import (
    sanitize_filename, resolve_destination, create_work_dir,
    cleanup_work_dir, safe_move, check_write_permission, check_disk_space,
)
from app.services.sound_service import SoundService
from app.storage.database import Database


class _VerifyWorker(QThread):
    """Runs FFprobe verification off the GUI thread."""

    result_ready = Signal(object)  # VerificationResult

    def __init__(self, file_path, expected_video, expected_audio,
                 expected_duration, parent=None):
        super().__init__(parent)
        self._file_path = file_path
        self._expected_video = expected_video
        self._expected_audio = expected_audio
        self._expected_duration = expected_duration

    def run(self) -> None:
        try:
            result = verify_file(
                self._file_path,
                expected_video=self._expected_video,
                expected_audio=self._expected_audio,
                expected_duration=self._expected_duration,
            )
        except Exception as exc:  # never let a worker crash the app
            result = type(
                "VerificationResult",
                (),
                {
                    "passed": False,
                    "errors": [f"ตรวจสอบไฟล์ไม่สำเร็จ: {exc}"],
                    "file_size": 0,
                },
            )()
        self.result_ready.emit(result)


class AppController(QObject):
    """
    Central controller that coordinates between UI, download engine,
    and file management.

    Signals:
        info_fetched(MediaInfo): Metadata ready for display
        info_error(str): Error fetching metadata
        download_progress(str, DownloadProgress): Progress for a task
        task_state_changed(str, TaskState): Task state changed
        status_message(str): Status bar message
    """

    info_fetched = Signal(object)
    info_error = Signal(str)
    download_progress = Signal(str, object)
    task_state_changed = Signal(str, object)
    status_message = Signal(str)

    def __init__(self, db: Optional[Database] = None, parent=None):
        super().__init__(parent)
        self._db = db or Database()
        self._queue = QueueManager(parent=self)
        self._adapters: dict[str, YtDlpAdapter] = {}  # task_id -> adapter
        self._verify_workers: dict[str, QThread] = {}
        self._info_adapter: Optional[YtDlpAdapter] = None
        self._current_info: Optional[MediaInfo] = None
        self._info_timestamp: float = 0.0
        self._sound = SoundService(parent=self)

        # Connect queue signals
        self._queue.slot_available.connect(self._process_next)

    @property
    def queue(self) -> QueueManager:
        return self._queue

    @property
    def current_info(self) -> Optional[MediaInfo]:
        return self._current_info

    def check_url(self, url: str) -> None:
        """Validate URL and fetch metadata."""
        result = validate_url(url)
        if not result.is_valid:
            self.info_error.emit(result.error or "ลิงก์ไม่ถูกต้อง")
            return

        self.status_message.emit("กำลังตรวจสอบลิงก์...")
        self._current_info = None

        # Create info adapter
        if self._info_adapter and self._info_adapter.is_running:
            self._info_adapter.cancel()

        self._info_adapter = YtDlpAdapter(self)
        self._info_adapter.info_ready.connect(self._on_info_ready)
        self._info_adapter.error_occurred.connect(self._on_info_error)
        self._info_adapter.extract_info(result.clean_url)

    def _on_info_ready(self, info: MediaInfo) -> None:
        """Handle metadata extraction success."""
        self._current_info = info
        self._info_timestamp = time.time()
        self.info_fetched.emit(info)
        self.status_message.emit("พร้อมดาวน์โหลด")

    def _on_info_error(self, error_code: str, detail: str) -> None:
        """Handle metadata extraction error."""
        try:
            code = ErrorCode(error_code)
            msg = get_user_message(code)
        except ValueError:
            msg = detail[:200] if detail else "เกิดข้อผิดพลาด"
        self.info_error.emit(msg)
        self.status_message.emit("")

    # ── state / persistence helpers ──

    def _set_state(self, task_id: str, state: TaskState, error_msg: str = "") -> bool:
        """Apply a state transition to the queue, UI and database."""
        if not self._queue.update_task_state(task_id, state, error_msg):
            return False

        self.task_state_changed.emit(task_id, state)
        task = self._queue.get_task(task_id)
        if task is not None:
            self._db.update_state(
                task_id,
                state,
                error_message=task.error_message,
                output_path=task.output_path,
            )
        return True

    def history(self, limit: int = 200) -> list[DownloadTask]:
        """Download history from SQLite (newest first)."""
        return self._db.fetch_history(limit=limit)

    def clear_history(self) -> int:
        return self._db.clear_history()

    def start_download(
        self,
        info: MediaInfo,
        policy: QualityPolicy,
        destination_dir: str,
    ) -> Optional[str]:
        """
        Create a download task and add to queue.
        Returns task_id or None on validation error.
        """
        # Validate destination
        if not os.path.isdir(destination_dir):
            self.info_error.emit("โฟลเดอร์ปลายทางไม่มีอยู่")
            return None

        if not check_write_permission(destination_dir):
            self.info_error.emit("ไม่สามารถบันทึกในโฟลเดอร์นี้ได้")
            return None

        # Create task
        ext = "mp3" if policy.output_type == OutputType.MP3 else "mp4"
        filename = sanitize_filename(info.title, info.media_id, ext)
        dest = resolve_destination(filename, destination_dir)

        task = DownloadTask(
            source_url=info.webpage_url or "",
            platform=info.platform,
            media_id=info.media_id,
            title=info.title,
            quality_policy=policy,
            destination_dir=destination_dir,
            media_info=info,
        )

        # Create work directory
        task.work_dir = create_work_dir(destination_dir, task.task_id)

        # Add to queue and persist immediately
        self._queue.add_task(task)
        self._db.upsert_task(task)
        self.task_state_changed.emit(task.task_id, task.state)

        # Try to start immediately if slot available
        self._process_next()

        return task.task_id

    def cancel_task(self, task_id: str) -> None:
        """Cancel a task."""
        task = self._queue.get_task(task_id)
        if task is None:
            return

        # Move to CANCELLING (or straight to CANCELLED for queued tasks)
        if self._queue.cancel_task(task_id):
            current = self._queue.get_task(task_id)
            if current is not None:
                self.task_state_changed.emit(task_id, current.state)
                self._db.update_state(task_id, current.state)

            # Cancel the adapter if running
            adapter = self._adapters.get(task_id)
            if adapter:
                adapter.cancel()

    def retry_task(self, task_id: str) -> None:
        """Retry a failed task."""
        if self._queue.retry_task(task_id):
            task = self._queue.get_task(task_id)
            if task:
                self.task_state_changed.emit(task_id, task.state)
                self._db.upsert_task(task)
            self._process_next()

    def _process_next(self) -> None:
        """Start the next queued task if a slot is available."""
        task = self._queue.get_next_pending()
        if task is None:
            return

        self._execute_task(task)

    def _execute_task(self, task: DownloadTask) -> None:
        """Execute a download task."""
        # Step 1: RESOLVING — validate or re-read the source.
        if not self._set_state(task.task_id, TaskState.RESOLVING):
            return

        attempt_id = task.attempt_id

        # Fast-path: if metadata was already fetched within the last 180 seconds,
        # skip spawning a duplicate yt-dlp --dump-json process and start downloading immediately!
        if (
            task.media_info is not None
            and (time.time() - self._info_timestamp) < 180.0
            and (task.media_info.formats or (task.quality_policy and task.quality_policy.output_type == OutputType.MP3))
        ):
            self._on_resolved(task, attempt_id, task.media_info)
            return

        resolver = YtDlpAdapter(self)
        self._adapters[task.task_id] = resolver
        resolver.info_ready.connect(
            lambda info: self._on_resolved(task, attempt_id, info))
        resolver.error_occurred.connect(
            lambda code, detail: self._on_download_error(task, attempt_id, code, detail))
        resolver.extract_info(task.source_url, attempt_id)

    def _on_resolved(self, task: DownloadTask, attempt_id: str, info: MediaInfo) -> None:
        """Source re-read OK: confirm chosen quality still exists, then download."""
        if task.attempt_id != attempt_id:
            return
        if task.state == TaskState.CANCELLING:
            self._finish_cancel(task)
            return

        policy = task.quality_policy
        # Never downgrade silently: if the chosen stream vanished, fail clearly.
        if policy and policy.output_type == OutputType.MP4 and policy.selected_video_format_id:
            ids = {f.format_id for f in info.formats}
            wanted = {policy.selected_video_format_id, policy.selected_audio_format_id} - {None}
            if not wanted <= ids:
                self._fail_task(task.task_id, ErrorCode.FORMAT_UNAVAILABLE)
                return
        task.media_info = info

        if policy:
            selection = select_format(info, policy)
            if selection.estimated_size and not check_disk_space(
                    task.destination_dir, selection.estimated_size):
                self._fail_task(task.task_id, ErrorCode.DISK_FULL)
                return

        self._cleanup_adapter(task.task_id)
        self._start_download(task, attempt_id)

    def _start_download(self, task: DownloadTask, attempt_id: str) -> None:
        """Step 2: DOWNLOADING."""
        adapter = YtDlpAdapter(self)
        self._adapters[task.task_id] = adapter

        def on_progress(progress):
            if task.attempt_id == attempt_id:
                task.progress = progress
                self.download_progress.emit(task.task_id, progress)

        def on_finished(output_path):
            if task.attempt_id != attempt_id:
                return
            self._on_download_finished(task, output_path)

        def on_error(error_code, detail):
            self._on_download_error(task, attempt_id, error_code, detail)

        adapter.progress_updated.connect(on_progress)
        adapter.download_finished.connect(on_finished)
        adapter.error_occurred.connect(on_error)

        # Transition to DOWNLOADING
        self._set_state(task.task_id, TaskState.DOWNLOADING)

        # Build output template
        output_template = os.path.join(task.work_dir, "%(title)s.%(ext)s")

        # Start download
        adapter.start_download(
            url=task.source_url,
            policy=task.quality_policy,
            work_dir=task.work_dir,
            output_template=output_template,
            attempt_id=attempt_id,
        )

    def _on_download_finished(self, task: DownloadTask, output_path: str) -> None:
        """Handle download completion — verify and move file."""
        # Check if task was cancelled
        if task.state in (TaskState.CANCELLING, TaskState.CANCELLED):
            self._finish_cancel(task)
            return

        # yt-dlp already merged/converted internally, but the state machine
        # requires DOWNLOADING -> POSTPROCESSING -> VERIFYING.
        self._set_state(task.task_id, TaskState.POSTPROCESSING)
        self._set_state(task.task_id, TaskState.VERIFYING)

        # Verify the file on a worker thread — never block the GUI on FFprobe
        is_mp3 = task.quality_policy and task.quality_policy.output_type == OutputType.MP3
        worker = _VerifyWorker(
            output_path,
            expected_video=not is_mp3,
            expected_audio=bool(is_mp3 or not task.media_info
                                or task.media_info.has_audio_track),
            expected_duration=task.media_info.duration if task.media_info else None,
            parent=self,
        )
        attempt_id = task.attempt_id
        self._verify_workers[task.task_id] = worker
        worker.result_ready.connect(
            lambda result: self._on_verified(task, output_path, result, attempt_id)
        )
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: self._verify_workers.pop(task.task_id, None))
        worker.start()

    def _on_verified(self, task: DownloadTask, output_path: str,
                     result, attempt_id: str) -> None:
        """Continue after FFprobe finished (runs on the GUI thread)."""
        if task.attempt_id != attempt_id:
            return

        if task.state in (TaskState.CANCELLING, TaskState.CANCELLED):
            self._set_state(task.task_id, TaskState.CANCELLED)
            self._cleanup_adapter(task.task_id)
            cleanup_work_dir(task.work_dir)
            return

        if not result.passed:
            errors = "; ".join(getattr(result, "errors", []) or [])
            self._fail_task(task.task_id, ErrorCode.VERIFICATION_FAILED, errors)
            self._cleanup_adapter(task.task_id)
            cleanup_work_dir(task.work_dir)
            return

        # Move to destination
        is_mp3 = task.quality_policy and task.quality_policy.output_type == OutputType.MP3
        ext = "mp3" if is_mp3 else "mp4"
        filename = sanitize_filename(task.title, task.media_id, ext)
        dest = resolve_destination(filename, task.destination_dir)

        if safe_move(output_path, dest.full_path):
            task.output_path = dest.full_path
            self._set_state(task.task_id, TaskState.COMPLETED)
            self.status_message.emit(f"สำเร็จ: {task.title}")
            self._sound.play_success()
        else:
            self._fail_task(task.task_id, ErrorCode.PERMISSION_DENIED,
                            "ไม่สามารถย้ายไฟล์ไปยังโฟลเดอร์ปลายทาง")

        self._cleanup_adapter(task.task_id)

        # Clean up work directory
        cleanup_work_dir(task.work_dir)

    def _on_download_error(self, task: DownloadTask, attempt_id: str,
                           error_code: str, detail: str) -> None:
        """Handle resolve/download error. Events from an old attempt are dropped."""
        if task.attempt_id != attempt_id:
            return
        if task.state == TaskState.CANCELLING:
            self._finish_cancel(task)
            return
        if task.state in (TaskState.FAILED, TaskState.CANCELLED, TaskState.COMPLETED):
            return  # duplicate event after the outcome was already decided
        try:
            code = ErrorCode(error_code)
        except ValueError:
            code = ErrorCode.UNKNOWN
        self._fail_task(task.task_id, code, detail)
        self._cleanup_adapter(task.task_id)

    def _finish_cancel(self, task: DownloadTask) -> None:
        """CANCELLING -> CANCELLED and remove our own partial files."""
        self._set_state(task.task_id, TaskState.CANCELLED)
        self._cleanup_adapter(task.task_id)
        cleanup_work_dir(task.work_dir)

    def _fail_task(self, task_id: str, code: ErrorCode, detail: str = "") -> None:
        """Mark a task as failed.

        The user-facing message is always the readable one; raw tool output is
        kept in error_detail for the "ดูรายละเอียด" view.
        """
        task = self._queue.get_task(task_id)
        message = get_user_message(code)
        if task:
            task.error_code = code.value
            task.error_message = message
            task.error_detail = detail or None

        self._set_state(task_id, TaskState.FAILED, message)
        self._sound.play_error()

    def _cleanup_adapter(self, task_id: str) -> None:
        """Clean up adapter for a task."""
        adapter = self._adapters.pop(task_id, None)
        if adapter:
            if adapter.is_running:
                adapter.cancel()
            adapter.deleteLater()

    def shutdown(self) -> None:
        """Clean shutdown — cancel all active downloads and wait for verifiers."""
        for task_id, adapter in list(self._adapters.items()):
            adapter.cancel()
        self._adapters.clear()

        for worker in list(self._verify_workers.values()):
            worker.wait(3000)
        self._verify_workers.clear()
