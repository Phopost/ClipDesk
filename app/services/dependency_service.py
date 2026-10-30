"""Dependency checking for ClipDesk — finds and verifies external tools."""

from dataclasses import dataclass, field
from typing import Optional
import os
import subprocess
import threading

from app.services.app_paths import app_root, vendor_dir


@dataclass
class ToolInfo:
    """Info about one external tool."""

    name: str
    path: Optional[str] = None
    version: Optional[str] = None
    available: bool = False
    error: Optional[str] = None


@dataclass
class DependencyStatus:
    """Overall dependency check result."""

    ytdlp: ToolInfo = field(default_factory=lambda: ToolInfo("yt-dlp"))
    ffmpeg: ToolInfo = field(default_factory=lambda: ToolInfo("FFmpeg"))
    ffprobe: ToolInfo = field(default_factory=lambda: ToolInfo("FFprobe"))
    nodejs: ToolInfo = field(default_factory=lambda: ToolInfo("Node.js"))

    @property
    def all_required_available(self) -> bool:
        return self.ytdlp.available and self.ffmpeg.available and self.ffprobe.available

    @property
    def missing_tools(self) -> list[str]:
        missing = []
        if not self.ytdlp.available:
            missing.append("yt-dlp")
        if not self.ffmpeg.available:
            missing.append("FFmpeg")
        if not self.ffprobe.available:
            missing.append("FFprobe")
        return missing

    @property
    def summary(self) -> str:
        if self.all_required_available:
            return "เครื่องมือพร้อมใช้งาน"
        return f"ขาด: {', '.join(self.missing_tools)}"


# Module-level cache
_cached_status: Optional[DependencyStatus] = None
_cache_lock = threading.Lock()


def _find_tool(name: str, vendor_subdir: str = "") -> Optional[str]:
    """Find a tool: check bundled vendor/ first, then system PATH."""
    vendor_path = os.path.join(vendor_dir(), f"{name}.exe")
    if os.path.isfile(vendor_path):
        return vendor_path

    # Check system PATH via where.exe (Windows)
    try:
        result = subprocess.run(
            ["where.exe", name],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            path = result.stdout.strip().split("\n")[0].strip()
            if os.path.isfile(path):
                return path
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return None


def _get_version(path: str, version_arg: str = "--version") -> Optional[str]:
    """Get version string from a tool."""
    try:
        result = subprocess.run(
            [path, version_arg],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0].strip()
        # ffmpeg outputs version to stderr in some builds
        if result.stderr:
            first_line = result.stderr.strip().split("\n")[0].strip()
            if "version" in first_line.lower():
                return first_line
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _check_tool(name: str, version_arg: str = "--version") -> ToolInfo:
    """Find and verify one tool."""
    info = ToolInfo(name=name)
    path = _find_tool(name)
    if path is None:
        info.error = f"ไม่พบ {name} ในระบบ"
        return info

    info.path = path
    version = _get_version(path, version_arg)
    if version:
        info.version = version
        info.available = True
    else:
        info.error = f"พบ {name} แต่ไม่สามารถตรวจเวอร์ชันได้"
        # Still mark as available if the file exists — version check might just be format issue
        info.available = True
    return info


def check_dependencies(force_refresh: bool = False) -> DependencyStatus:
    """Check all required dependencies. Results are cached thread-safely."""
    global _cached_status

    with _cache_lock:
        if _cached_status is not None and not force_refresh:
            return _cached_status

    status = DependencyStatus()
    status.ytdlp = _check_tool("yt-dlp")
    status.ffmpeg = _check_tool("ffmpeg", "-version")
    status.ffprobe = _check_tool("ffprobe", "-version")
    # Prefer bundled QuickJS (qjs.exe, 2.05 MiB) over Node.js (89.2 MiB)
    qjs_info = _check_tool("qjs", "--version")
    if qjs_info.available:
        status.nodejs = qjs_info
    else:
        status.nodejs = _check_tool("node")

    with _cache_lock:
        _cached_status = status

    return status


def get_tool_path(name: str) -> Optional[str]:
    """Get the path for a specific tool from cached dependency status."""
    status = check_dependencies()
    tool_map = {
        "yt-dlp": status.ytdlp,
        "ffmpeg": status.ffmpeg,
        "ffprobe": status.ffprobe,
        "node": status.nodejs,
        "qjs": status.nodejs,
    }
    tool = tool_map.get(name)
    return tool.path if tool and tool.available else None


def get_js_runtime_args() -> list[str]:
    """yt-dlp arguments enabling the bundled JavaScript runtime (QuickJS or Node.js).

    Recent yt-dlp versions require a JS runtime (with yt-dlp-ejs) to solve
    YouTube challenges. Returns an empty list when no runtime is available so
    yt-dlp can still fall back to its own defaults.
    """
    js_path = get_tool_path("qjs")
    if js_path:
        exe_name = os.path.basename(js_path).lower()
        runtime_key = "quickjs" if "qjs" in exe_name else "node"
        return ["--js-runtimes", f"{runtime_key}:{js_path}"]
    return []


def get_vendor_info() -> dict[str, str]:
    """Return resolved paths of bundled tools (for diagnostics/logging)."""
    return {
        "app_root": app_root(),
        "vendor_dir": vendor_dir(),
        "yt-dlp": get_tool_path("yt-dlp") or "",
        "ffmpeg": get_tool_path("ffmpeg") or "",
        "ffprobe": get_tool_path("ffprobe") or "",
        "node": get_tool_path("node") or "",
    }
