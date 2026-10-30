"""Windows process supervision.

Wraps a Win32 Job Object so that every child process of a download
(yt-dlp -> ffmpeg -> node) is killed together, even if the GUI crashes
or the user cancels mid-post-processing.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import subprocess
from typing import Optional

_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
_JobObjectExtendedLimitInformation = 9
_PROCESS_SET_QUOTA = 0x0100
_PROCESS_TERMINATE = 0x0001


class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.wintypes.LARGE_INTEGER),
        ("PerJobUserTimeLimit", ctypes.wintypes.LARGE_INTEGER),
        ("LimitFlags", ctypes.wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.wintypes.DWORD),
        ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
        ("PriorityClass", ctypes.wintypes.DWORD),
        ("SchedulingClass", ctypes.wintypes.DWORD),
    ]


class _IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", _IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class JobObject:
    """A Win32 job object with KILL_ON_JOB_CLOSE.

    Closing the handle (or the process dying) terminates the whole tree.
    On non-Windows platforms this is a no-op wrapper.
    """

    def __init__(self) -> None:
        self._handle: Optional[int] = None
        if os.name == "nt":
            self._handle = self._create()

    @property
    def is_valid(self) -> bool:
        return bool(self._handle)

    def _create(self) -> Optional[int]:
        try:
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateJobObjectW(None, None)
            if not handle:
                return None
            info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not kernel32.SetInformationJobObject(
                handle,
                _JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            ):
                kernel32.CloseHandle(handle)
                return None
            return handle
        except (AttributeError, OSError):
            return None

    def assign(self, pid: int) -> bool:
        """Assign a running process (and its future children) to the job."""
        if not self._handle or not pid:
            return False
        try:
            kernel32 = ctypes.windll.kernel32
            proc_handle = kernel32.OpenProcess(
                _PROCESS_SET_QUOTA | _PROCESS_TERMINATE, False, int(pid)
            )
            if not proc_handle:
                return False
            try:
                return bool(kernel32.AssignProcessToJobObject(self._handle, proc_handle))
            finally:
                kernel32.CloseHandle(proc_handle)
        except (AttributeError, OSError):
            return False

    def terminate(self, exit_code: int = 1) -> None:
        """Terminate every process currently in the job."""
        if not self._handle:
            return
        try:
            ctypes.windll.kernel32.TerminateJobObject(self._handle, exit_code)
        except (AttributeError, OSError):
            pass

    def close(self) -> None:
        """Close the job handle — kills remaining processes (KILL_ON_JOB_CLOSE)."""
        if self._handle:
            try:
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except (AttributeError, OSError):
                pass
            self._handle = None

    def __enter__(self) -> "JobObject":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def kill_process_tree(pid: int) -> None:
    """Fallback: kill a process and all descendants with taskkill.

    Fire-and-forget: taskkill is not waited on, so this can be called from the
    GUI thread during cancel without freezing the window.
    """
    if not pid:
        return
    try:
        subprocess.Popen(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except (FileNotFoundError, OSError):
        pass
