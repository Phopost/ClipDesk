"""Queue manager — manages ordered list of download tasks with concurrency control."""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.core.models import DownloadTask, TaskState


class QueueManager(QObject):
    """
    Manages the download queue with concurrency limits.

    Signals:
        task_added(DownloadTask): New task added to queue
        task_started(str): Task started (task_id)
        task_completed(str): Task completed (task_id)
        task_failed(str, str): Task failed (task_id, error_message)
        task_cancelled(str): Task cancelled (task_id)
        task_progress(str, object): Progress update (task_id, DownloadProgress)
        queue_changed(): Queue order or count changed
        slot_available(): A download slot became available
    """

    task_added = Signal(object)
    task_started = Signal(str)
    task_completed = Signal(str)
    task_failed = Signal(str, str)
    task_cancelled = Signal(str)
    task_progress = Signal(str, object)
    queue_changed = Signal()
    slot_available = Signal()

    def __init__(self, max_concurrent: int = 3, parent=None):
        super().__init__(parent)
        self._tasks: list[DownloadTask] = []
        self._max_concurrent = max_concurrent
        self._active_count = 0

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        self._max_concurrent = max(1, min(value, 5))

    @property
    def active_count(self) -> int:
        return sum(
            1 for t in self._tasks
            if t.state in (TaskState.RESOLVING, TaskState.DOWNLOADING,
                           TaskState.POSTPROCESSING, TaskState.VERIFYING)
        )

    @property
    def has_available_slot(self) -> bool:
        return self.active_count < self._max_concurrent

    @property
    def pending_tasks(self) -> list[DownloadTask]:
        return [t for t in self._tasks if t.state == TaskState.QUEUED]

    @property
    def all_tasks(self) -> list[DownloadTask]:
        return list(self._tasks)

    def add_task(self, task: DownloadTask) -> None:
        """Add a new task to the queue."""
        self._tasks.append(task)
        self.task_added.emit(task)
        self.queue_changed.emit()

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """Get a task by ID."""
        for t in self._tasks:
            if t.task_id == task_id:
                return t
        return None

    def get_next_pending(self) -> Optional[DownloadTask]:
        """Get the next QUEUED task if a slot is available."""
        if not self.has_available_slot:
            return None
        for t in self._tasks:
            if t.state == TaskState.QUEUED:
                return t
        return None

    def update_task_state(self, task_id: str, new_state: TaskState,
                          error_msg: str = "") -> bool:
        """Update a task's state with transition validation."""
        task = self.get_task(task_id)
        if task is None:
            return False

        if not task.transition_to(new_state):
            return False

        if new_state == TaskState.COMPLETED:
            self.task_completed.emit(task_id)
            self.slot_available.emit()
        elif new_state == TaskState.FAILED:
            task.error_message = error_msg
            self.task_failed.emit(task_id, error_msg)
            self.slot_available.emit()
        elif new_state == TaskState.CANCELLED:
            self.task_cancelled.emit(task_id)
            self.slot_available.emit()
        elif new_state in (TaskState.RESOLVING, TaskState.DOWNLOADING):
            self.task_started.emit(task_id)

        self.queue_changed.emit()
        return True

    def retry_task(self, task_id: str) -> bool:
        """Retry a failed task."""
        task = self.get_task(task_id)
        if task is None or task.state != TaskState.FAILED:
            return False

        task.new_attempt()
        self.queue_changed.emit()
        self.slot_available.emit()
        return True

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a task."""
        task = self.get_task(task_id)
        if task is None:
            return False

        if task.state in (TaskState.COMPLETED, TaskState.CANCELLED):
            return False

        if task.state == TaskState.QUEUED:
            # Can cancel directly
            task.transition_to(TaskState.CANCELLING)
            task.transition_to(TaskState.CANCELLED)
            self.task_cancelled.emit(task_id)
            self.queue_changed.emit()
            return True

        # For active tasks, move to CANCELLING (controller handles actual cancellation)
        return task.transition_to(TaskState.CANCELLING)

    def remove_completed(self) -> int:
        """Remove completed and cancelled tasks. Returns count removed."""
        before = len(self._tasks)
        self._tasks = [
            t for t in self._tasks
            if t.state not in (TaskState.COMPLETED, TaskState.CANCELLED)
        ]
        removed = before - len(self._tasks)
        if removed > 0:
            self.queue_changed.emit()
        return removed

    def clear_all(self) -> None:
        """Remove all non-active tasks."""
        self._tasks = [
            t for t in self._tasks
            if t.state in (TaskState.RESOLVING, TaskState.DOWNLOADING,
                           TaskState.POSTPROCESSING, TaskState.VERIFYING,
                           TaskState.CANCELLING)
        ]
        self.queue_changed.emit()
