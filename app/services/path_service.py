"""File path management for ClipDesk — safe naming, atomic moves, space checks."""

from dataclasses import dataclass
from typing import Optional
import os
import re
import shutil
import tempfile
import unicodedata


# Characters illegal in Windows filenames
_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Windows reserved device names
_RESERVED_NAMES = frozenset({
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
})

# Max filename length (excluding extension), keeping some room for path
_MAX_FILENAME_LEN = 180


@dataclass
class SafePath:
    """Result of path sanitization."""

    filename: str
    full_path: str
    was_modified: bool  # True if the original title was changed


def sanitize_filename(title: str, media_id: str, ext: str) -> str:
    """
    Create a safe filename from title and media_id.

    Template: "{title} [{media_id}].{ext}"

    Rules:
    - Remove Windows-illegal characters
    - Handle reserved device names
    - Trim trailing dots and spaces
    - Prevent path traversal (../)
    - Preserve Thai and Unicode
    - Limit length while keeping media_id
    """
    # Remove illegal characters but keep Unicode (Thai, emoji, etc.)
    clean = _ILLEGAL_CHARS.sub("", title)

    # Remove path traversal components
    clean = clean.replace("..", "")

    # Normalize Unicode (NFC for consistent representation)
    clean = unicodedata.normalize("NFC", clean)

    # Remove control characters
    clean = "".join(c for c in clean if unicodedata.category(c) != "Cc")

    # Trim whitespace and trailing dots
    clean = clean.strip().rstrip(".")

    # Handle empty result
    if not clean:
        clean = "download"

    # Check for reserved names (case insensitive, without extension)
    name_upper = clean.upper().split(".")[0]
    if name_upper in _RESERVED_NAMES:
        clean = f"_{clean}"

    # Truncate if too long, preserving media_id suffix
    suffix = f" [{media_id}]"
    max_title_len = _MAX_FILENAME_LEN - len(suffix)
    if len(clean) > max_title_len:
        clean = clean[:max_title_len].rstrip()

    # Build final filename
    filename = f"{clean}{suffix}.{ext}"
    return filename


def resolve_destination(
    filename: str,
    destination_dir: str,
    overwrite: bool = False,
) -> SafePath:
    """
    Resolve the final file path, handling duplicates.

    If the file exists and overwrite=False, appends (2), (3), etc.
    NEVER overwrites without explicit consent.
    """
    full_path = os.path.join(destination_dir, filename)
    was_modified = False

    if not overwrite:
        base, ext = os.path.splitext(filename)
        counter = 2
        while os.path.exists(full_path):
            new_filename = f"{base} ({counter}){ext}"
            full_path = os.path.join(destination_dir, new_filename)
            filename = new_filename
            was_modified = True
            counter += 1

    return SafePath(filename=filename, full_path=full_path, was_modified=was_modified)


def create_work_dir(destination_dir: str, task_id: str) -> str:
    """
    Create a temporary work directory for a download task.

    Tries to create in the same filesystem as destination for atomic moves.
    Falls back to system temp if that fails.
    """
    # Try to create .clipdesk_tmp in destination directory
    try:
        work_base = os.path.join(destination_dir, ".clipdesk_tmp")
        os.makedirs(work_base, exist_ok=True)
        work_dir = os.path.join(work_base, task_id)
        os.makedirs(work_dir, exist_ok=True)
        return work_dir
    except OSError:
        pass

    # Fallback to system temp
    work_dir = os.path.join(tempfile.gettempdir(), "clipdesk", task_id)
    os.makedirs(work_dir, exist_ok=True)
    return work_dir


def cleanup_work_dir(work_dir: str) -> None:
    """Remove a work directory. Ignores errors."""
    try:
        if os.path.isdir(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
    except OSError:
        pass


def safe_move(src: str, dst: str) -> bool:
    """
    Move file from src to dst atomically when possible.

    Uses os.replace() on same filesystem, otherwise copy+verify+delete.
    Returns True on success.
    """
    if not os.path.isfile(src):
        return False

    # Never overwrite an existing file (e.g. one created by a concurrent task).
    if os.path.exists(dst):
        return False

    try:
        # os.link fails if dst exists -> atomic "create only if absent"
        os.link(src, dst)
        os.remove(src)
        return True
    except OSError:
        pass

    # Cross-filesystem: copy, verify, then delete source
    try:
        if os.path.exists(dst):
            return False
        shutil.copy2(src, dst)
        # Verify copy succeeded
        if os.path.isfile(dst) and os.path.getsize(dst) == os.path.getsize(src):
            os.remove(src)
            return True
        else:
            # Copy failed, clean up
            if os.path.isfile(dst):
                os.remove(dst)
            return False
    except OSError:
        return False


def check_write_permission(directory: str) -> bool:
    """Check if we can write to a directory."""
    if not os.path.isdir(directory):
        return False
    try:
        test_file = os.path.join(directory, ".clipdesk_write_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        return True
    except OSError:
        return False


def check_disk_space(directory: str, required_bytes: int) -> bool:
    """Check if there's enough free space in the directory's filesystem."""
    try:
        usage = shutil.disk_usage(directory)
        # Require at least required_bytes + 100MB buffer
        buffer = 100 * 1024 * 1024
        return usage.free >= (required_bytes + buffer)
    except OSError:
        return False


def get_free_space_mb(directory: str) -> Optional[float]:
    """Get free space in MB for a directory."""
    try:
        usage = shutil.disk_usage(directory)
        return usage.free / (1024 * 1024)
    except OSError:
        return None
