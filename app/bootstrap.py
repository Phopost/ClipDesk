"""Application bootstrapper — dependency checks and initialization."""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QSettings

from app.services.dependency_service import check_dependencies

# Log setup (bounded to 2 MiB x 3 files max = 6 MiB total)
LOG_DIR = os.path.join(os.path.expanduser("~"), ".clipdesk", "logs")
LOG_MAX_BYTES = 2 * 1024 * 1024
LOG_BACKUP_COUNT = 2


def setup_logging() -> None:
    """Configure bounded rotating file logging."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "clipdesk.log")

    # Remove legacy .old file if present from older versions
    legacy_old = log_file + ".old"
    if os.path.isfile(legacy_old):
        try:
            os.remove(legacy_old)
        except OSError:
            pass

    handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler],
    )
    # Don't log sensitive data
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def check_and_warn_dependencies(parent=None) -> bool:
    """
    Check dependencies and show warning if tools are missing.
    Returns True if all required tools are available.
    """
    status = check_dependencies(force_refresh=True)

    if status.all_required_available:
        logging.info(
            "Dependencies OK: yt-dlp=%s ffmpeg=%s ffprobe=%s node=%s",
            status.ytdlp.version, status.ffmpeg.version,
            status.ffprobe.version, status.nodejs.version or "not found",
        )
        return True

    missing = status.missing_tools
    msg = (
        f"ขาดเครื่องมือที่จำเป็น: {', '.join(missing)}\n\n"
        "โปรแกรมต้องการ:\n"
        "• yt-dlp — ดาวน์โหลดวิดีโอ\n"
        "• FFmpeg — ประมวลผลสื่อ\n"
        "• FFprobe — ตรวจสอบไฟล์\n\n"
        "กรุณาติดตั้งเครื่องมือที่ขาดก่อนใช้งาน"
    )

    logging.warning("Missing dependencies: %s", ", ".join(missing))

    if parent:
        QMessageBox.warning(parent, "ขาดเครื่องมือ", msg)
    else:
        # No parent widget yet — print to console
        print(f"[WARNING] {msg}")

    return False


def get_app_settings() -> QSettings:
    """Get the application QSettings instance."""
    return QSettings("ClipDesk", "ClipDesk")


def initialize_storage(default_dir=None):
    """Open the SQLite database and run crash recovery at startup.

    Returns:
        (Database, RecoveryReport)
    """
    from app.storage.database import Database
    from app.storage.recovery import run_startup_recovery

    db = Database()
    report = run_startup_recovery(db, default_dir=default_dir)
    return db, report
