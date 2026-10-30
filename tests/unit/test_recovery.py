"""Unit tests for crash recovery of stale work directories."""

import os
import time
import uuid

from app.core.models import DownloadTask, TaskState
from app.storage.database import Database
from app.storage.recovery import run_startup_recovery


def _make_stale_tree(root, name, age_seconds):
    path = os.path.join(root, ".clipdesk_tmp", name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "partial.mp4"), "wb") as fh:
        fh.write(b"x" * 1024)
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


def test_removes_only_old_uuid_dirs(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    downloads = tmp_path / "Videos"
    downloads.mkdir()

    old_dir = _make_stale_tree(str(downloads), str(uuid.uuid4()), 48 * 3600)
    fresh_dir = _make_stale_tree(str(downloads), str(uuid.uuid4()), 3600)
    foreign_dir = _make_stale_tree(str(downloads), "my-own-folder", 48 * 3600)

    report = run_startup_recovery(db, default_dir=str(downloads))

    assert not os.path.exists(old_dir)
    assert os.path.exists(fresh_dir)
    assert os.path.exists(foreign_dir)
    assert report.removed_dirs == 1
    assert report.freed_bytes >= 1024
    db.close()


def test_marks_interrupted_tasks(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    task = DownloadTask(title="ค้าง", state=TaskState.DOWNLOADING)
    db.upsert_task(task)

    downloads = tmp_path / "Videos"
    downloads.mkdir()
    report = run_startup_recovery(db, default_dir=str(downloads))

    assert report.interrupted_tasks == 1
    assert db.get_task(task.task_id).state == TaskState.FAILED
    db.close()


def test_missing_directory_is_safe(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    report = run_startup_recovery(db, default_dir=str(tmp_path / "does-not-exist"))
    assert report.removed_dirs == 0
    db.close()
