"""Unit tests for SQLite persistence."""

import os

from app.core.models import (
    DownloadTask, MediaInfo, OutputType, Platform, QualityPolicy, TaskState,
)
from app.storage.database import Database


def _make_task(title="คลิปทดสอบ", state=TaskState.QUEUED) -> DownloadTask:
    return DownloadTask(
        source_url="https://www.youtube.com/watch?v=abc",
        platform=Platform.YOUTUBE,
        media_id="abc",
        title=title,
        quality_policy=QualityPolicy(output_type=OutputType.MP4),
        destination_dir="C:/Videos",
        state=state,
        media_info=MediaInfo(media_id="abc", title=title, platform=Platform.YOUTUBE,
                             duration=12.5),
    )


def test_upsert_and_fetch(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    task = _make_task()
    db.upsert_task(task)

    rows = db.fetch_history(final_only=False)
    assert len(rows) == 1
    assert rows[0].task_id == task.task_id
    assert rows[0].title == "คลิปทดสอบ"
    assert rows[0].platform == Platform.YOUTUBE
    assert rows[0].destination_dir == "C:/Videos"
    db.close()


def test_completed_task_appears_in_final_history(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    task = _make_task()
    db.upsert_task(task)

    output = tmp_path / "out.mp4"
    output.write_bytes(b"12345")
    db.update_state(task.task_id, TaskState.COMPLETED, output_path=str(output))

    history = db.fetch_history(final_only=True)
    assert len(history) == 1
    assert history[0].state == TaskState.COMPLETED
    assert history[0].output_path == str(output)
    assert history[0].completed_at is not None
    db.close()


def test_mark_interrupted_flags_non_final_tasks(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    running = _make_task("กำลังโหลด")
    done = _make_task("เสร็จแล้ว")
    db.upsert_task(running)
    db.upsert_task(done)
    db.update_state(done.task_id, TaskState.COMPLETED)

    count = db.mark_interrupted("ปิดโปรแกรมกระทันหัน")
    assert count == 1

    flagged = db.get_task(running.task_id)
    assert flagged.state == TaskState.FAILED
    assert "กระทันหัน" in flagged.error_message

    finished = db.get_task(done.task_id)
    assert finished.state == TaskState.COMPLETED
    db.close()


def test_clear_history(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    db.upsert_task(_make_task("a"))
    db.upsert_task(_make_task("b"))
    assert db.count() == 2

    removed = db.clear_history()
    assert removed == 2
    assert db.count() == 0
    db.close()


def test_known_destination_dirs(tmp_path):
    db = Database(str(tmp_path / "test.db"))
    t1 = _make_task("a")
    t1.destination_dir = "C:/Videos"
    t2 = _make_task("b")
    t2.destination_dir = "D:/Clips"
    db.upsert_task(t1)
    db.upsert_task(t2)

    dirs = set(db.get_known_destination_dirs())
    assert dirs == {"C:/Videos", "D:/Clips"}
    db.close()


def test_persistence_across_reopen(tmp_path):
    path = str(tmp_path / "test.db")
    db = Database(path)
    task = _make_task("ถาวร")
    db.upsert_task(task)
    db.close()

    db2 = Database(path)
    rows = db2.fetch_history(final_only=False)
    assert len(rows) == 1
    assert rows[0].title == "ถาวร"
    db2.close()
