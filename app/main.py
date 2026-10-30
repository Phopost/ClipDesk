"""ClipDesk entry point."""

import logging
import os
import sys

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
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("ClipDesk")
    app.setOrganizationName("ClipDesk")

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
