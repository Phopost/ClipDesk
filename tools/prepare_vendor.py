"""Populate vendor/windows-x64 with the binaries shipped to end users.

Usage (from the project root):
    python tools/prepare_vendor.py            # copy/download what is missing
    python tools/prepare_vendor.py --force    # re-copy everything
    python tools/prepare_vendor.py --skip-ytdlp-download

The pip-installed yt-dlp.exe is only a 100 KB launcher that needs Python, so
this script downloads the official standalone build when it detects a shim.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join(ROOT, "vendor", "windows-x64")

YTDLP_RELEASE_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
MIN_STANDALONE_SIZE = 5 * 1024 * 1024  # a real standalone build is > 5 MB


def _where(name: str) -> str | None:
    try:
        out = subprocess.run(
            ["where.exe", name],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if out.returncode == 0:
            return out.stdout.strip().splitlines()[0].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


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


def _place(src: str, dst: str, force: bool = False) -> None:
    """Hardlink when possible (same volume), otherwise copy."""
    if os.path.isfile(dst) and not force:
        print(f"  keep  {os.path.basename(dst)}")
        return

    if os.path.isfile(dst):
        os.remove(dst)

    try:
        os.link(src, dst)
        print(f"  link  {os.path.basename(dst)}")
        return
    except OSError:
        pass

    shutil.copy2(src, dst)
    print(f"  copy  {os.path.basename(dst)}")


def _download_ytdlp(dst: str) -> None:
    print(f"  download {YTDLP_RELEASE_URL}")
    tmp = dst + ".part"
    request = urllib.request.Request(
        YTDLP_RELEASE_URL,
        headers={"User-Agent": "ClipDesk-build/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response, open(tmp, "wb") as fh:
        shutil.copyfileobj(response, fh)
    os.replace(tmp, dst)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-ytdlp-download", action="store_true")
    args = parser.parse_args()

    os.makedirs(VENDOR, exist_ok=True)
    manifest: dict[str, dict] = {}

    # ── yt-dlp ──
    print("yt-dlp:")
    ytdlp_dst = os.path.join(VENDOR, "yt-dlp.exe")
    local = _where("yt-dlp")
    local_is_standalone = bool(local and os.path.getsize(local) > MIN_STANDALONE_SIZE)

    if args.force and local_is_standalone:
        _place(local, ytdlp_dst, force=True)
    elif not os.path.isfile(ytdlp_dst) or os.path.getsize(ytdlp_dst) < MIN_STANDALONE_SIZE:
        if local_is_standalone:
            _place(local, ytdlp_dst, force=args.force)
        elif args.skip_ytdlp_download:
            print("  ERROR: local yt-dlp is a pip shim and download is disabled")
            return 2
        else:
            _download_ytdlp(ytdlp_dst)
    else:
        print("  keep  yt-dlp.exe")

    # ── ffmpeg / ffprobe / node ──
    for name, version_arg in (
        ("ffmpeg", "-version"),
        ("ffprobe", "-version"),
        ("node", "--version"),
    ):
        print(f"{name}:")
        src = _where(name)
        if not src:
            print(f"  ERROR: {name} not found on PATH")
            return 3
        _place(src, os.path.join(VENDOR, f"{name}.exe"), force=args.force)

    # ── verify + manifest ──
    print("verify:")
    for name, version_arg in (
        ("yt-dlp", "--version"),
        ("ffmpeg", "-version"),
        ("ffprobe", "-version"),
        ("node", "--version"),
    ):
        path = os.path.join(VENDOR, f"{name}.exe")
        version = _version(path, version_arg)
        if not version:
            print(f"  ERROR: {name}.exe does not run")
            return 4
        size = os.path.getsize(path)
        manifest[name] = {
            "file": os.path.basename(path),
            "version": version,
            "size": size,
            "sha256": _sha256(path),
        }
        print(f"  OK    {name}: {version} ({size / (1024 * 1024):.1f} MB)")

    manifest_path = os.path.join(VENDOR, "VERSIONS.json")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)

    total = sum(item["size"] for item in manifest.values())
    print(f"total: {total / (1024 * 1024):.1f} MB")
    print(f"manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
