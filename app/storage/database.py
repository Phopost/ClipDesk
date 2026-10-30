"""SQLite persistence for download history and crash recovery.

The database lives in ~/.clipdesk/clipdesk.db. All access goes through a
single connection guarded by a lock so the GUI thread and recovery code can
share it safely.
"""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Optional

from app.core.models import (
    DownloadTask, OutputType, Platform, QualityPolicy, TaskState,
)
from app.services.app_paths import user_data_dir

_SCHEMA = """
CREATE TABLE IF NOT EXISTS downloads (
    task_id         TEXT PRIMARY KEY,
    source_url      TEXT NOT NULL DEFAULT '',
    platform        TEXT NOT NULL DEFAULT 'unknown',
    title           TEXT NOT NULL DEFAULT '',
    output_type     TEXT NOT NULL DEFAULT 'mp4',
    destination_dir TEXT NOT NULL DEFAULT '',
    output_path     TEXT,
    state           TEXT NOT NULL DEFAULT 'QUEUED',
    error_message   TEXT,
    file_size       INTEGER,
    duration        REAL,
    created_at      REAL NOT NULL DEFAULT 0,
    completed_at    REAL
);
CREATE INDEX IF NOT EXISTS idx_downloads_created
    ON downloads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_downloads_state
    ON downloads(state);
"""

_FINAL_STATES = ("COMPLETED", "CANCELLED", "FAILED")


def default_db_path() -> str:
    return os.path.join(user_data_dir(), "clipdesk.db")


class Database:
    """Thin, thread-safe repository around SQLite."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or default_db_path()
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.executescript(_SCHEMA)
            self._migrate()
            self._conn.commit()

    # ── schema ──

    def _migrate(self) -> None:
        """Add columns introduced after the first release."""
        existing = {
            row["name"]
            for row in self._conn.execute("PRAGMA table_info(downloads)")
        }
        if "destination_dir" not in existing:
            self._conn.execute(
                "ALTER TABLE downloads ADD COLUMN destination_dir TEXT NOT NULL DEFAULT ''"
            )

    # ── writes ──

    def upsert_task(self, task: DownloadTask) -> None:
        """Insert a task or update its mutable fields."""
        output_type = (
            task.quality_policy.output_type.value
            if task.quality_policy
            else OutputType.MP4.value
        )
        duration = task.media_info.duration if task.media_info else None
        file_size = None
        if task.output_path and os.path.isfile(task.output_path):
            try:
                file_size = os.path.getsize(task.output_path)
            except OSError:
                file_size = None

        with self._lock:
            self._conn.execute(
                """
                INSERT INTO downloads (
                    task_id, source_url, platform, title, output_type,
                    destination_dir, output_path, state, error_message,
                    file_size, duration, created_at, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    source_url      = excluded.source_url,
                    platform        = excluded.platform,
                    title           = excluded.title,
                    output_type     = excluded.output_type,
                    destination_dir = excluded.destination_dir,
                    output_path     = excluded.output_path,
                    state           = excluded.state,
                    error_message   = excluded.error_message,
                    file_size       = excluded.file_size,
                    duration        = excluded.duration,
                    completed_at    = excluded.completed_at
                """,
                (
                    task.task_id,
                    task.source_url,
                    task.platform.value,
                    task.title,
                    output_type,
                    task.destination_dir,
                    task.output_path,
                    task.state.name,
                    task.error_message,
                    file_size,
                    duration,
                    task.created_at,
                    task.completed_at,
                ),
            )
            self._conn.commit()

    def update_state(
        self,
        task_id: str,
        state: TaskState,
        error_message: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> None:
        completed_at = time.time() if state in (
            TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED
        ) else None

        file_size = None
        if output_path and os.path.isfile(output_path):
            try:
                file_size = os.path.getsize(output_path)
            except OSError:
                file_size = None

        with self._lock:
            self._conn.execute(
                """
                UPDATE downloads SET
                    state = ?,
                    error_message = COALESCE(?, error_message),
                    output_path = COALESCE(?, output_path),
                    file_size = COALESCE(?, file_size),
                    completed_at = COALESCE(?, completed_at)
                WHERE task_id = ?
                """,
                (
                    state.name,
                    error_message,
                    output_path,
                    file_size,
                    completed_at,
                    task_id,
                ),
            )
            self._conn.commit()

    def mark_interrupted(self, message: str = "โปรแกรมถูกปิดก่อนงานเสร็จ") -> int:
        """Flag every non-final task as FAILED. Returns affected row count."""
        placeholders = ",".join("?" for _ in _FINAL_STATES)
        with self._lock:
            cur = self._conn.execute(
                f"""
                UPDATE downloads
                   SET state = 'FAILED',
                       error_message = COALESCE(error_message, ?),
                       completed_at = COALESCE(completed_at, ?)
                 WHERE state NOT IN ({placeholders})
                """,
                (message, time.time(), *_FINAL_STATES),
            )
            self._conn.commit()
            return cur.rowcount

    def clear_history(self) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM downloads")
            self._conn.commit()
            return cur.rowcount

    # ── reads ──

    def fetch_history(
        self,
        limit: int = 200,
        offset: int = 0,
        final_only: bool = True,
    ) -> list[DownloadTask]:
        sql = "SELECT * FROM downloads"
        params: list = []
        if final_only:
            placeholders = ",".join("?" for _ in _FINAL_STATES)
            sql += f" WHERE state IN ({placeholders})"
            params.extend(_FINAL_STATES)
        sql += " ORDER BY COALESCE(completed_at, created_at) DESC LIMIT ? OFFSET ?"
        params.extend([max(1, limit), max(0, offset)])

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_task(row) for row in rows]

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM downloads WHERE task_id = ?", (task_id,)
            ).fetchone()
        return _row_to_task(row) if row else None

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS n FROM downloads").fetchone()
        return int(row["n"]) if row else 0

    def get_known_destination_dirs(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT DISTINCT destination_dir FROM downloads "
                "WHERE destination_dir IS NOT NULL AND destination_dir <> ''"
            ).fetchall()
        return [row["destination_dir"] for row in rows]

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass


def _row_to_task(row: sqlite3.Row) -> DownloadTask:
    try:
        platform = Platform(row["platform"])
    except (ValueError, TypeError):
        platform = Platform.UNKNOWN

    state = getattr(TaskState, row["state"], TaskState.FAILED)

    try:
        output_type = OutputType(row["output_type"])
    except (ValueError, TypeError):
        output_type = OutputType.MP4

    return DownloadTask(
        task_id=row["task_id"],
        source_url=row["source_url"] or "",
        platform=platform,
        title=row["title"] or "",
        quality_policy=QualityPolicy(output_type=output_type),
        destination_dir=row["destination_dir"] or "",
        output_path=row["output_path"],
        state=state,
        error_message=row["error_message"],
        created_at=row["created_at"] or 0.0,
        completed_at=row["completed_at"],
    )
