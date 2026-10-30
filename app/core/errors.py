"""ClipDesk error codes and user-facing messages."""

from enum import Enum


class ErrorCode(Enum):
    INVALID_URL = "invalid_url"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    CLIP_UNAVAILABLE = "clip_unavailable"
    CLIP_PRIVATE = "clip_private"
    CLIP_RESTRICTED = "clip_restricted"
    NETWORK_ERROR = "network_error"
    RATE_LIMITED = "rate_limited"
    FORMAT_UNAVAILABLE = "format_unavailable"
    DISK_FULL = "disk_full"
    PERMISSION_DENIED = "permission_denied"
    DRIVE_DISCONNECTED = "drive_disconnected"
    DEPENDENCY_MISSING = "dependency_missing"
    FFMPEG_ERROR = "ffmpeg_error"
    VERIFICATION_FAILED = "verification_failed"
    PROCESS_TIMEOUT = "process_timeout"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.INVALID_URL: "ตรวจสอบรูปแบบลิงก์อีกครั้ง",
    ErrorCode.UNSUPPORTED_PLATFORM: "รองรับเฉพาะ YouTube และ TikTok ในรุ่นนี้",
    ErrorCode.CLIP_UNAVAILABLE: "ไม่สามารถเข้าถึงคลิปนี้ได้ อาจถูกลบหรือไม่มีอยู่",
    ErrorCode.CLIP_PRIVATE: "คลิปนี้เป็นส่วนตัวและไม่สามารถเข้าถึงได้",
    ErrorCode.CLIP_RESTRICTED: "คลิปนี้มีข้อจำกัดการเข้าถึง",
    ErrorCode.NETWORK_ERROR: "การเชื่อมต่อขัดข้อง",
    ErrorCode.RATE_LIMITED: "ต้นทางจำกัดการเชื่อมต่อ กรุณารอสักครู่",
    ErrorCode.FORMAT_UNAVAILABLE: "รูปแบบที่เลือกไม่พร้อมให้ดาวน์โหลดแล้ว",
    ErrorCode.DISK_FULL: "พื้นที่จัดเก็บไม่เพียงพอ",
    ErrorCode.PERMISSION_DENIED: "ไม่สามารถบันทึกในโฟลเดอร์นี้ได้",
    ErrorCode.DRIVE_DISCONNECTED: "โฟลเดอร์ปลายทางไม่พร้อมใช้งาน",
    ErrorCode.DEPENDENCY_MISSING: "ส่วนประกอบที่จำเป็นหายไป",
    ErrorCode.FFMPEG_ERROR: "เกิดข้อผิดพลาดในการประมวลผลไฟล์",
    ErrorCode.VERIFICATION_FAILED: "ไฟล์ที่ได้ยังไม่สมบูรณ์",
    ErrorCode.PROCESS_TIMEOUT: "การดำเนินการใช้เวลานานเกินกำหนด",
    ErrorCode.CANCELLED: "ยกเลิกโดยผู้ใช้",
    ErrorCode.UNKNOWN: "เกิดข้อผิดพลาดที่ไม่คาดคิด",
}


def get_user_message(code: ErrorCode) -> str:
    """Return Thai user-facing error message for a code."""
    return ERROR_MESSAGES.get(code, ERROR_MESSAGES[ErrorCode.UNKNOWN])


def classify_ytdlp_error(stderr: str) -> ErrorCode:
    """Classify yt-dlp stderr output into an ErrorCode."""
    lower = stderr.lower()
    if "video unavailable" in lower or "this video is unavailable" in lower:
        return ErrorCode.CLIP_UNAVAILABLE
    if "private video" in lower or "video is private" in lower or "is a private video" in lower:
        return ErrorCode.CLIP_PRIVATE
    if (
        "sign in" in lower
        or "age-restricted" in lower
        or "age restricted" in lower
        or "confirm your age" in lower
        or "members-only" in lower
        or "restricted" in lower
        or "blocked from accessing" in lower
        or "ip address is blocked" in lower
        or "captcha" in lower
        or "bot detection" in lower
    ):
        return ErrorCode.CLIP_RESTRICTED
    if "unable to download" in lower and "http error 429" in lower:
        return ErrorCode.RATE_LIMITED
    if "unable to download" in lower or "urlopen error" in lower:
        return ErrorCode.NETWORK_ERROR
    if "no video formats" in lower or "requested format" in lower:
        return ErrorCode.FORMAT_UNAVAILABLE
    if "no space left" in lower or "disk full" in lower:
        return ErrorCode.DISK_FULL
    if "permission denied" in lower:
        return ErrorCode.PERMISSION_DENIED
    return ErrorCode.UNKNOWN
