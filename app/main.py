"""ClipDesk entry point."""

import logging
import os
import sys

# Force lightweight Windows native audio backend (WASAPI/WMF) for QSoundEffect
# so PySide6 does not load its duplicate 19.6 MiB ffmpegmediaplugin + avcodec DLLs.
os.environ.setdefault("QT_MEDIA_BACKEND", "windows")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from app.bootstrap import (
    setup_logging, check_and_warn_dependencies, initialize_storage,
)
from app.core.controller import AppController
from app.ui.main_window import MainWindow
from app.ui.settings_dialog import SettingsDialog


def main():
    """Launch ClipDesk application."""
    from app.version import __version__

    # Bind explicit Windows AppUserModelID before QApplication starts so the
    # taskbar and Start Menu always associate the custom icon with ClipDesk.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                f"ClipDesk.Desktop.App.{__version__}"
            )
        except Exception:
            pass

    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ClipDesk")
    app.setOrganizationName("ClipDesk")
    app.setApplicationVersion(__version__)

    # Set Window & Taskbar Icon
    from PySide6.QtGui import QIcon
    from app.services.app_paths import asset_path
    icon_file = asset_path("icons", "clipdesk.ico")
    if os.path.isfile(icon_file):
        app.setWindowIcon(QIcon(icon_file))

    # Logging
    setup_logging()

    # Crash recovery: clean stale work dirs + flag interrupted downloads
    db, report = initialize_storage(SettingsDialog.get_default_directory())
    if report.did_anything:
        logging.info(
            "Recovery: %d stale dir(s), %.1f MB freed, %d interrupted task(s)",
            report.removed_dirs,
            report.freed_bytes / (1024 * 1024),
            report.interrupted_tasks,
        )

    # Dependency check (non-blocking warning)
    check_and_warn_dependencies()

    # Controller
    controller = AppController(db=db)
    controller.queue.max_concurrent = SettingsDialog.get_max_concurrent()

    # Main window
    window = MainWindow(controller)
    window.show()

    if "--smoke-test" in sys.argv:
        def _finish_smoke_test():
            marker = os.environ.get("CLIPDESK_SMOKE_MARKER")
            if marker:
                try:
                    with open(marker, "w", encoding="utf-8") as fh:
                        fh.write("OK")
                except OSError:
                    pass
            print("SMOKE_OK")
            app.quit()

        QTimer.singleShot(2500, _finish_smoke_test)

    exit_code = app.exec()
    controller.shutdown()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
