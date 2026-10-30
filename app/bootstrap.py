"""Application bootstrapper — dependency checks and initialization."""

import logging
import os
import sys

from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QSettings

from app.services.dependency_service import check_dependencies

# Log setup
LOG_DIR = os.path.join(os.path.expanduser("~"), ".clipdesk", "logs")


def setup_logging() -> None:
    """Configure rotating file logging."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, "clipdesk.log")

    # Rotate if > 5 MB
    if os.path.isfile(log_file):
        try:
            if os.path.getsize(log_file) > 5 * 1024 * 1024:
                backup = log_file + ".old"
                if os.path.isfile(backup):
                    os.remove(backup)
                os.rename(log_file, backup)
        except OSError:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
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
