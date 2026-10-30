"""Build the standalone Windows distribution of ClipDesk.

Produces a PyInstaller *onedir* build:

    dist/ClipDesk/ClipDesk.exe
    dist/ClipDesk/_internal/...   (Qt, Python, app assets, vendor binaries)

Usage (from the project root):
    python packaging/build_windows.py
    python packaging/build_windows.py --skip-test
    python packaging/build_windows.py --console   # keep a console for debugging
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTRY = os.path.join(ROOT, "app", "main.py")
DIST_DIR = os.path.join(ROOT, "dist")
BUILD_DIR = os.path.join(ROOT, "build")
VENDOR = os.path.join(ROOT, "vendor", "windows-x64")
ASSETS = os.path.join(ROOT, "app", "assets")
ICON = os.path.join(ASSETS, "icons", "clipdesk.ico")


def _clean_dir(path: str) -> None:
    shutil.rmtree(path, ignore_errors=True)
    if os.path.exists(path):
        stash = os.path.join(
            tempfile.gettempdir(),
            f"clipdesk_old_build_{os.getpid()}_{os.path.basename(path)}",
        )
        try:
            os.rename(path, stash)
            shutil.rmtree(stash, ignore_errors=True)
        except OSError:
            pass


def build(clean: bool = True, console: bool = False) -> str:
    if not os.path.isfile(os.path.join(VENDOR, "yt-dlp.exe")):
        raise SystemExit(
            "vendor binaries missing — run: python tools/prepare_vendor.py"
        )

    if clean:
        _clean_dir(os.path.join(DIST_DIR, "ClipDesk"))
        _clean_dir(os.path.join(BUILD_DIR, "ClipDesk"))

    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(BUILD_DIR, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name",
        "ClipDesk",
        "--distpath",
        DIST_DIR,
        "--workpath",
        BUILD_DIR,
        "--specpath",
        BUILD_DIR,
        "--paths",
        ROOT,
        "--add-data",
        f"{ASSETS}{os.pathsep}app/assets",
        "--hidden-import",
        "PySide6.QtMultimedia",
        "--hidden-import",
        "PySide6.QtNetwork",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "pytest",
        "--exclude-module",
        "_pytest",
        "--exclude-module",
        "PySide6.QtQml",
        "--exclude-module",
        "PySide6.QtQuick",
        "--exclude-module",
        "PySide6.QtOpenGL",
        "--exclude-module",
        "PySide6.QtPdf",
        "--exclude-module",
        "PySide6.QtSvg",
        "--exclude-module",
        "PySide6.QtMultimediaWidgets",
        "--exclude-module",
        "PySide6.QtVirtualKeyboard",
    ]
    cmd.append("--console" if console else "--windowed")

    if os.path.isfile(ICON):
        cmd += ["--icon", ICON]

    cmd.append(ENTRY)

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)

    exe = os.path.join(DIST_DIR, "ClipDesk", "ClipDesk.exe")
    if not os.path.isfile(exe):
        raise SystemExit("build finished but ClipDesk.exe is missing")

    _prune_unused_qt_files(os.path.join(DIST_DIR, "ClipDesk", "_internal", "PySide6"))

    # Copy vendor/windows-x64 directly into _internal/vendor/windows-x64 after
    # COLLECT so PyInstaller's binary dependency scanner does not duplicate
    # 179.9 MiB of shared FFmpeg av*/sw* DLLs into _internal/.
    vendor_dst = os.path.join(DIST_DIR, "ClipDesk", "_internal", "vendor", "windows-x64")
    shutil.rmtree(vendor_dst, ignore_errors=True)
    shutil.copytree(VENDOR, vendor_dst)

    # Ship the license notices next to the executable
    notices = os.path.join(ROOT, "THIRD_PARTY_NOTICES.md")
    if os.path.isfile(notices):
        shutil.copy2(notices, os.path.join(DIST_DIR, "ClipDesk", "THIRD_PARTY_NOTICES.md"))

    return exe


# Proven-unused PySide6 binaries & plugins (verified via PE import graph and
# runtime memory-map trace). ClipDesk uses QWidget 2D raster UI + Windows
# native audio backend (QT_MEDIA_BACKEND=windows) and never uses QML, Quick,
# OpenGL software rasterizer, PDF, SVG, VirtualKeyboard, or Qt's duplicate
# FFmpeg multimedia plugin.
_UNUSED_PYSIDE6_FILES = (
    "opengl32sw.dll",
    # Duplicate FFmpeg DLLs from Qt Multimedia (we use windowsmediaplugin.dll)
    "avcodec-63.dll",
    "avformat-63.dll",
    "avutil-61.dll",
    "swresample-7.dll",
    "swscale-10.dll",
    os.path.join("plugins", "multimedia", "ffmpegmediaplugin.dll"),
    # QML / Quick / VirtualKeyboard / OpenGL / PDF / SVG / MultimediaWidgets
    "Qt6Quick.dll",
    "Qt6Qml.dll",
    "Qt6QmlMeta.dll",
    "Qt6QmlModels.dll",
    "Qt6QmlWorkerScript.dll",
    "Qt6OpenGL.dll",
    "Qt6VirtualKeyboard.dll",
    "Qt6Pdf.dll",
    "Qt6Svg.dll",
    "Qt6MultimediaWidgets.dll",
    "QtMultimediaWidgets.pyd",
    os.path.join("plugins", "platforminputcontexts", "qtvirtualkeyboardplugin.dll"),
    os.path.join("plugins", "imageformats", "qpdf.dll"),
    os.path.join("plugins", "imageformats", "qsvg.dll"),
    os.path.join("plugins", "iconengines", "qsvgicon.dll"),
    # Unused experimental platform / imageformat / touch plugins
    os.path.join("plugins", "platforms", "qdirect2d.dll"),
    os.path.join("plugins", "imageformats", "qtiff.dll"),
    os.path.join("plugins", "imageformats", "qicns.dll"),
    os.path.join("plugins", "imageformats", "qtga.dll"),
    os.path.join("plugins", "imageformats", "qwbmp.dll"),
    os.path.join("plugins", "generic", "qtuiotouchplugin.dll"),
)

_UNUSED_PYSIDE6_DIRS = (
    "translations",
    "iconengines",
    "platforminputcontexts",
    "generic",
)


def _prune_unused_qt_files(pyside_dir: str) -> None:
    """Deterministically remove unused Qt binaries/translations after COLLECT."""
    if not os.path.isdir(pyside_dir):
        return

    removed_bytes = 0
    removed_count = 0

    for rel in _UNUSED_PYSIDE6_FILES:
        target = os.path.join(pyside_dir, rel)
        if os.path.isfile(target):
            removed_bytes += os.path.getsize(target)
            os.remove(target)
            removed_count += 1

    for dirname in _UNUSED_PYSIDE6_DIRS:
        for base in (pyside_dir, os.path.join(pyside_dir, "plugins")):
            dpath = os.path.join(base, dirname)
            if os.path.isdir(dpath):
                for dp, _dn, fn in os.walk(dpath):
                    for f in fn:
                        removed_bytes += os.path.getsize(os.path.join(dp, f))
                        removed_count += 1
                shutil.rmtree(dpath)

    print(
        f"Pruned {removed_count} unused PySide6 files "
        f"({removed_bytes / (1024 * 1024):.1f} MiB saved)"
    )


def smoke_test(exe: str, timeout: int = 120) -> bool:
    """Launch the built exe with --smoke-test and wait for the marker file."""
    marker = os.path.join(tempfile.gettempdir(), "clipdesk_smoke_ok.txt")
    try:
        os.remove(marker)
    except OSError:
        pass

    env = os.environ.copy()
    env["CLIPDESK_SMOKE_MARKER"] = marker
    print(f"Smoke test: {exe}")
    proc = subprocess.Popen([exe, "--smoke-test"], env=env)

    try:
        code = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        print("FAILED: app did not exit within timeout")
        return False

    ok = code == 0 and os.path.isfile(marker)
    print("PASSED" if ok else f"FAILED: exit={code}, marker={os.path.isfile(marker)}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-test", action="store_true")
    parser.add_argument("--console", action="store_true")
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    exe = build(clean=not args.no_clean, console=args.console)

    size = 0
    for root, _dirs, files in os.walk(os.path.join(DIST_DIR, "ClipDesk")):
        for name in files:
            try:
                size += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass

    print(f"Built: {exe}")
    print(f"Size:  {size / (1024 * 1024):.1f} MB")

    if args.skip_test:
        return 0

    return 0 if smoke_test(exe) else 1


if __name__ == "__main__":
    sys.exit(main())
