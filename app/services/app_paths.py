"""Application path helpers — work in source tree and frozen (PyInstaller) builds."""

import os
import sys


def app_root() -> str:
    """Root directory that contains `app/` and `vendor/`.

    In a frozen build this is the PyInstaller extraction dir (_MEIPASS).
    """
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    # app/services/app_paths.py -> app/services -> app -> project root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def user_data_dir() -> str:
    """Per-user writable data directory (~/.clipdesk)."""
    path = os.path.join(os.path.expanduser("~"), ".clipdesk")
    os.makedirs(path, exist_ok=True)
    return path


def asset_path(*parts: str) -> str:
    """Absolute path to a bundled asset (e.g. asset_path('sounds', 'success.wav'))."""
    return os.path.join(app_root(), "app", "assets", *parts)


def vendor_dir() -> str:
    """Directory containing bundled external binaries."""
    return os.path.join(app_root(), "vendor", "windows-x64")
