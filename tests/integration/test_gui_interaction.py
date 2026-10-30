"""Interactive GUI end-to-end tests using pytest-qt."""

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication

from app.core.controller import AppController
from app.storage.database import Database
from app.ui.main_window import MainWindow
from app.core.models import MediaInfo, Platform, VideoFormat, DownloadTask, TaskState


@pytest.fixture
def main_window(qapp, tmp_path):
    db = Database(str(tmp_path / "gui_test.db"))
    controller = AppController(db=db)
    window = MainWindow(controller)
    window.show()
    yield window
    window.close()
    controller.shutdown()


def test_gui_window_title_and_components(main_window):
    """Verify all top-level components exist and are visible."""
    assert main_window.windowTitle() == "ClipDesk"
    assert main_window._url_input.isVisible()
    assert main_window._queue_view.isVisible()
    assert not main_window._media_card.isVisible()  # hidden initially
    assert not main_window._format_panel.isVisible()  # hidden initially


def test_gui_input_error_flow(main_window, qtbot):
    """Simulate entering an invalid URL and check error display."""
    edit = main_window._url_input._url_edit
    btn = main_window._url_input._check_btn

    edit.setText("http://192.168.1.1/video")
    qtbot.mouseClick(btn, Qt.MouseButton.LeftButton)

    # Error label should become visible
    qtbot.waitUntil(lambda: main_window._url_input._error_label.isVisible(), timeout=2000)
    assert "ตรวจสอบรูปแบบ" in main_window._url_input._error_label.text()


def test_gui_metadata_display_and_format_selection(main_window, qtbot):
    """Simulate info_fetched signal and verify media card & format panel population."""
    formats = [
        VideoFormat(format_id="18", ext="mp4", width=640, height=360, fps=30, vcodec="avc1", acodec="mp4a", filesize=5000000)
    ]
    info = MediaInfo(
        media_id="test12345",
        title="Test Clip Title",
        platform=Platform.YOUTUBE,
        duration=65.0,
        formats=formats,
        uploader="TestChannel"
    )

    # Emit signal directly
    main_window._controller.info_fetched.emit(info)

    qtbot.waitUntil(lambda: main_window._media_card.isVisible(), timeout=2000)
    qtbot.waitUntil(lambda: main_window._format_panel.isVisible(), timeout=2000)

    assert "Test Clip Title" in main_window._media_card._title_label.text()
    assert "1:05" in main_window._media_card._duration_label.text()

    # Format panel should show resolution
    assert main_window._format_panel._quality_combo.count() > 0
    assert "640×360" in main_window._format_panel._quality_combo.currentText()


def test_gui_minimize_throttling(main_window, qtbot):
    """Verify window minimization disables paint updates."""
    assert main_window.updatesEnabled() is True

    # Simulate minimize
    main_window.setWindowState(main_window.windowState() | Qt.WindowState.WindowMinimized)
    # Give event loop a cycle
    qapp = QApplication.instance()
    qapp.processEvents()

    if main_window.isMinimized():
        assert main_window.updatesEnabled() is False

    # Restore window
    main_window.setWindowState(main_window.windowState() & ~Qt.WindowState.WindowMinimized)
    qapp.processEvents()
    assert main_window.updatesEnabled() is True
