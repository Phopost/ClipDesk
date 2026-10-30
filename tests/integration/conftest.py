"""Shared Qt application fixture for integration tests.

A single QApplication instance must exist for the whole session: creating a
QCoreApplication first makes a later QApplication (needed by pytest-qt and
QPixmap) fail hard on Windows.
"""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
