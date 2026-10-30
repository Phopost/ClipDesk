"""Populate vendor/windows-x64 with the binaries shipped to end users.

Uses:
- Official standalone yt-dlp.exe
- Official BtbN FFmpeg 9.0 GPL Shared build (ffmpeg.exe + ffprobe.exe sharing
  one set of av*/sw* DLLs, excluding unused ffplay.exe — saves ~253.6 MiB vs
  duplicating static builds in both executables)
- Official QuickJS-NG (qjs.exe, 2.05 MiB — saves ~87.2 MiB vs Node.js 89.2 MiB)

Usage (from the project root):
    python tools/prepare_vendor.py
    python tools/prepare_vendor.py --force
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "vendor", "windows-x64")

YTDLP_RELEASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
FFMPEG_SHARED_URL = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
    "ffmpeg-n9.0-latest-win64-gpl-shared-9.0.zip"
)
QJS_RELEASE_URL = (
    "https://github.com/quickjs-ng/quickjs/releases/download/v0.17.0/"
    "qjs-windows-x86_64.exe"
)
MIN_STANDALONE_SIZE = 5 * 1024 * 1024


def _version(path: str, arg: str = "--version") -> str | None:
    try:
        out = subprocess.run(
            [path, arg],
            capture_output=True,
            text=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        text = (out.stdout or out.stderr).strip().splitlines()
        return text[0].strip() if text else None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dst: str) -> None:
    print(f"  download {url}")
    tmp = dst + ".part"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ClipDesk-build/1.2"},
    )
    with urllib.request.urlopen(request, timeout=180) as response, open(tmp, "wb") as fh:
        shutil.copyfileobj(response, fh)
    os.replace(tmp, dst)


def _safe_remove(path: str) -> None:
    """Break hardlink / remove file safely even if read-only."""
    if not os.path.lexists(path):
        return
    try:
        os.chmod(path, 0o666)
    except OSError:
        pass
    try:
        os.unlink(path)
        return
    except PermissionError:
        subprocess.run(
            ["cmd.exe", "/c", "del", "/f", "/q", path],
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def _install_shared_ffmpeg(zip_path: str) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = os.path.basename(info.filename)
            if "/bin/" in info.filename and name.lower() != "ffplay.exe":
                dst = os.path.join(VENDOR, name)
                _safe_remove(dst)
                with zf.open(info) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)
            elif info.filename.endswith("LICENSE.txt"):
                dst = os.path.join(VENDOR, "FFMPEG_LICENSE.txt")
                _safe_remove(dst)
                with zf.open(info) as src, open(dst, "wb") as out:
                    shutil.copyfileobj(src, out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ffmpeg-zip", default="", help="Optional local path to shared FFmpeg zip")
    parser.add_argument("--qjs-exe", default="", help="Optional local path to qjs.exe")
    args = parser.parse_args()

    os.makedirs(VENDOR, exist_ok=True)

    # Remove legacy 89 MiB node.exe or static oversized ffmpeg if switching to shared
    legacy_node = os.path.join(VENDOR, "node.exe")
    if os.path.isfile(legacy_node):
        _safe_remove(legacy_node)
        print("  removed legacy node.exe")

    # ── 1. yt-dlp ──
    print("yt-dlp:")
    ytdlp_dst = os.path.join(VENDOR, "yt-dlp.exe")
    if args.force or not os.path.isfile(ytdlp_dst) or os.path.getsize(ytdlp_dst) < MIN_STANDALONE_SIZE:
        _download(YTDLP_RELEASE_URL, ytdlp_dst)
    else:
        print("  keep  yt-dlp.exe")

    # ── 2. Shared FFmpeg + FFprobe (excluding ffplay.exe) ──
    print("ffmpeg/ffprobe (shared):")
    ffmpeg_dst = os.path.join(VENDOR, "ffmpeg.exe")
    avcodec_dst = os.path.join(VENDOR, "avcodec-63.dll")
    need_ffmpeg = (
        args.force
        or not os.path.isfile(ffmpeg_dst)
        or not os.path.isfile(avcodec_dst)
        or os.path.getsize(ffmpeg_dst) > 10 * 1024 * 1024  # static build > 10 MB
    )
    if need_ffmpeg:
        if args.ffmpeg_zip and os.path.isfile(args.ffmpeg_zip):
            _install_shared_ffmpeg(args.ffmpeg_zip)
        else:
            with tempfile.TemporaryDirectory() as tmp:
                zpath = os.path.join(tmp, "ffmpeg-shared.zip")
                _download(FFMPEG_SHARED_URL, zpath)
                _install_shared_ffmpeg(zpath)
        print("  installed shared ffmpeg + ffprobe + av*/sw* DLLs")
    else:
        print("  keep  shared ffmpeg + ffprobe")

    # ── 3. QuickJS (qjs.exe) ──
    print("qjs:")
    qjs_dst = os.path.join(VENDOR, "qjs.exe")
    if args.force or not os.path.isfile(qjs_dst):
        if args.qjs_exe and os.path.isfile(args.qjs_exe):
            shutil.copy2(args.qjs_exe, qjs_dst)
            print("  copy  qjs.exe")
        else:
            _download(QJS_RELEASE_URL, qjs_dst)
    else:
        print("  keep  qjs.exe")

    # ── 4. Verify + write VERSIONS.json ──
    print("verify:")
    manifest: dict[str, dict] = {}
    for name, exe_name, version_arg in (
        ("yt-dlp", "yt-dlp.exe", "--version"),
        ("ffmpeg", "ffmpeg.exe", "-version"),
        ("ffprobe", "ffprobe.exe", "-version"),
        ("qjs", "qjs.exe", "--version"),
    ):
        path = os.path.join(VENDOR, exe_name)
        version = _version(path, version_arg)
        if not version:
            print(f"  ERROR: {exe_name} does not run")
            return 4
        size = os.path.getsize(path)
        manifest[name] = {
            "file": exe_name,
            "version": version,
            "size": size,
            "sha256": _sha256(path),
        }
        print(f"  OK    {name}: {version} ({size / (1024 * 1024):.2f} MiB)")

    shared_dlls = {}
    for fn in sorted(os.listdir(VENDOR)):
        if fn.lower().endswith(".dll"):
            p = os.path.join(VENDOR, fn)
            shared_dlls[fn] = {
                "size": os.path.getsize(p),
                "sha256": _sha256(p),
            }
    manifest["ffmpeg_shared_dlls"] = shared_dlls

    manifest_path = os.path.join(VENDOR, "VERSIONS.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    total = sum(
        os.path.getsize(os.path.join(VENDOR, f))
        for f in os.listdir(VENDOR)
        if os.path.isfile(os.path.join(VENDOR, f))
    )
    print(f"vendor total: {total / (1024 * 1024):.1f} MiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
