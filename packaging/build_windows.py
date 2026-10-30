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


def build(clean: bool = True, console: bool = False) -> str:
    if not os.path.isfile(os.path.join(VENDOR, "yt-dlp.exe")):
        raise SystemExit(
            "vendor binaries missing — run: python tools/prepare_vendor.py"
        )

    if clean:
        shutil.rmtree(os.path.join(DIST_DIR, "ClipDesk"), ignore_errors=True)
        shutil.rmtree(os.path.join(BUILD_DIR, "ClipDesk"), ignore_errors=True)

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
        "--add-data",
        f"{VENDOR}{os.pathsep}vendor/windows-x64",
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

    # Ship the license notices next to the executable
    notices = os.path.join(ROOT, "THIRD_PARTY_NOTICES.md")
    if os.path.isfile(notices):
        shutil.copy2(notices, os.path.join(DIST_DIR, "ClipDesk", "THIRD_PARTY_NOTICES.md"))

    return exe


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
