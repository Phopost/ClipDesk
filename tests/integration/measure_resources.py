"""Measure ClipDesk against the resource budgets in the spec.

Budgets (Windows 11 x64, reference machine):
    idle RAM      < 200 MB
    idle CPU      < 1 %
    download RAM  < 600 MB (whole process tree, no re-encode)

Usage:
    python tests/integration/measure_resources.py --mode idle
    python tests/integration/measure_resources.py --mode download
    python tests/integration/measure_resources.py --mode all
"""

import argparse
import os
import subprocess
import sys
import tempfile
import time

import psutil

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

DEFAULT_EXE = os.path.join(ROOT, "dist", "ClipDesk", "ClipDesk.exe")
CC_URL = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"

IDLE_RAM_BUDGET_MB = 200.0
IDLE_CPU_BUDGET_PCT = 1.0
DOWNLOAD_RAM_BUDGET_MB = 600.0


def _tree(proc: psutil.Process) -> list[psutil.Process]:
    try:
        return [proc, *proc.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return [proc]


def _rss_mb(procs: list[psutil.Process]) -> float:
    total = 0
    for p in procs:
        try:
            total += p.memory_info().rss
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total / (1024 * 1024)


def _cpu_times(procs: list[psutil.Process]) -> float:
    total = 0.0
    for p in procs:
        try:
            times = p.cpu_times()
            total += times.user + times.system
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return total


def sample(proc: psutil.Process, seconds: float, pump=None) -> tuple[float, float]:
    """Return (peak RSS MB, average CPU % over the window)."""
    procs = _tree(proc)
    cpu_start = _cpu_times(procs)
    t0 = time.monotonic()
    peak = _rss_mb(procs)

    while time.monotonic() - t0 < seconds:
        if pump is not None:
            pump()
        time.sleep(0.2)
        procs = _tree(proc)
        peak = max(peak, _rss_mb(procs))

    elapsed = time.monotonic() - t0
    cpu_delta = _cpu_times(_tree(proc)) - cpu_start
    return peak, (cpu_delta / elapsed) * 100.0


def run_idle(exe: str, settle: float = 8.0, seconds: float = 5.0) -> tuple[float, float]:
    if not os.path.isfile(exe):
        raise SystemExit(f"exe not found: {exe}\nBuild it with: python packaging/build_windows.py")

    proc = subprocess.Popen([exe])
    try:
        time.sleep(settle)
        root = psutil.Process(proc.pid)
        return sample(root, seconds)
    finally:
        try:
            root = psutil.Process(proc.pid)
            for child in root.children(recursive=True):
                child.kill()
        except psutil.Error:
            pass
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)


def run_download(seconds: float = 15.0) -> tuple[float, float]:
    """Download in-process and sample the whole tree (python + yt-dlp + ffmpeg + node)."""
    from PySide6.QtCore import QCoreApplication

    from app.core.models import OutputType, QualityPolicy
    from app.media.ytdlp_adapter import YtDlpAdapter

    app = QCoreApplication.instance() or QCoreApplication([])
    work_dir = tempfile.mkdtemp(prefix="clipdesk_bench_")
    adapter = YtDlpAdapter()
    policy = QualityPolicy(
        output_type=OutputType.MP4,
        preferred_height=1080,
        prefer_compatible=True,
    )
    adapter.start_download(
        CC_URL, policy, work_dir, os.path.join(work_dir, "%(title)s.%(ext)s")
    )

    me = psutil.Process(os.getpid())
    try:
        return sample(me, seconds, pump=app.processEvents)
    finally:
        adapter.cancel()
        deadline = time.monotonic() + 10
        while adapter.is_running and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["idle", "download", "all"], default="all")
    parser.add_argument("--exe", default=DEFAULT_EXE)
    parser.add_argument("--seconds", type=float, default=None)
    args = parser.parse_args()

    failures = 0

    if args.mode in ("idle", "all"):
        seconds = args.seconds or 5.0
        ram, cpu = run_idle(args.exe, seconds=seconds)
        ok_ram = ram < IDLE_RAM_BUDGET_MB
        ok_cpu = cpu < IDLE_CPU_BUDGET_PCT
        failures += 0 if ok_ram and ok_cpu else 1
        print(f"[idle]     RAM {ram:6.1f} MB (budget < {IDLE_RAM_BUDGET_MB:.0f}) "
              f"{'PASS' if ok_ram else 'FAIL'}")
        print(f"[idle]     CPU {cpu:6.2f} %  (budget < {IDLE_CPU_BUDGET_PCT:.1f}) "
              f"{'PASS' if ok_cpu else 'FAIL'}")

    if args.mode in ("download", "all"):
        seconds = args.seconds or 15.0
        ram, cpu = run_download(seconds=seconds)
        ok_ram = ram < DOWNLOAD_RAM_BUDGET_MB
        failures += 0 if ok_ram else 1
        print(f"[download] RAM {ram:6.1f} MB (budget < {DOWNLOAD_RAM_BUDGET_MB:.0f}) "
              f"{'PASS' if ok_ram else 'FAIL'}  CPU {cpu:.1f}%")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
