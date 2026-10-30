"""Crash recovery — clean stale work directories and flag interrupted tasks."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Iterable, Optional

from app.storage.database import Database

STALE_AGE_SECONDS = 24 * 60 * 60
WORK_DIR_NAME = ".clipdesk_tmp"


@dataclass
class RecoveryReport:
    """What the startup recovery pass did."""

    scanned_roots: list[str] = field(default_factory=list)
    removed_dirs: int = 0
    freed_bytes: int = 0
    interrupted_tasks: int = 0

    @property
    def did_anything(self) -> bool:
        return self.removed_dirs > 0 or self.interrupted_tasks > 0


def _dir_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def _is_task_dir_name(name: str) -> bool:
    """Only delete directories that ClipDesk itself created (UUID names)."""
    try:
        uuid.UUID(name)
        return True
    except (ValueError, AttributeError):
        return False


def _candidate_roots(
    db: Database, default_dir: Optional[str], extra_roots: Iterable[str] = ()
) -> list[str]:
    roots: list[str] = []
    if default_dir:
        roots.append(default_dir)
    try:
        roots.extend(db.get_known_destination_dirs())
    except Exception:
        pass
    roots.extend(extra_roots)

    # Work dirs fall back to %TEMP%\clipdesk\<task_id>
    roots.append(os.path.join(tempfile.gettempdir(), "clipdesk"))

    unique: list[str] = []
    seen = set()
    for root in roots:
        if not root:
            continue
        norm = os.path.normcase(os.path.abspath(root))
        if norm not in seen:
            seen.add(norm)
            unique.append(os.path.abspath(root))
    return unique


def _clean_root(
    root: str,
    max_age_seconds: int,
    now: float,
    report: RecoveryReport,
    protected_task_ids: set[str] | None = None,
) -> None:
    if not os.path.isdir(root):
        return

    tmp_fallback_root = os.path.normcase(
        os.path.abspath(os.path.join(tempfile.gettempdir(), "clipdesk"))
    )
    is_tmp_fallback = os.path.normcase(os.path.abspath(root)) == tmp_fallback_root
    if is_tmp_fallback:
        # %TEMP%\clipdesk — children are task dirs directly
        container = root
    else:
        container = os.path.join(root, WORK_DIR_NAME)

    if not os.path.isdir(container):
        return

    report.scanned_roots.append(container)

    try:
        entries = list(os.scandir(container))
    except OSError:
        return

    for entry in entries:
        try:
            if not entry.is_dir(follow_symlinks=False):
                continue
            if not _is_task_dir_name(entry.name):
                continue
            if protected_task_ids and entry.name in protected_task_ids:
                continue
            age = now - entry.stat().st_mtime
            if age < max_age_seconds:
                continue
            size = _dir_size(entry.path)
            shutil.rmtree(entry.path, ignore_errors=True)
            if not os.path.exists(entry.path):
                report.removed_dirs += 1
                report.freed_bytes += size
        except OSError:
            continue

    # Remove the container itself when empty (best effort)
    if not is_tmp_fallback:
        try:
            if not os.listdir(container):
                os.rmdir(container)
        except OSError:
            pass


def run_startup_recovery(
    db: Database,
    default_dir: Optional[str] = None,
    extra_roots: Iterable[str] = (),
    max_age_seconds: int = STALE_AGE_SECONDS,
    now: Optional[float] = None,
) -> RecoveryReport:
    """Scan for stale work dirs and mark previously-running tasks as failed.

    Never deletes final output files or work dirs belonging to queued tasks.
    """
    report = RecoveryReport()
    current = now if now is not None else time.time()

    protected_ids: set[str] = set()
    try:
        for task in db.fetch_history(limit=500, final_only=False):
            if task.state.name == "QUEUED":
                protected_ids.add(task.task_id)
    except Exception:
        pass

    for root in _candidate_roots(db, default_dir, extra_roots):
        _clean_root(root, max_age_seconds, current, report, protected_ids)

    report.interrupted_tasks = db.mark_interrupted()
    return report
