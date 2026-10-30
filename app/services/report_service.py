"""Issue reporting via ntfy.sh (topic: Clipdesk).

Ported from the "Clipdesk Report Page" draft: builds a readable report card
and POSTs it to https://ntfy.sh/Clipdesk so the team gets a push notification.
"""

from __future__ import annotations

import datetime
import platform
import urllib.parse
import urllib.request

from app.version import APP_NAME, __version__

NTFY_TOPIC = "Clipdesk"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
NTFY_TIMEOUT = 10

CATEGORIES = ["ดาวน์โหลดไม่ได้", "ลิงก์ผิดพลาด", "แอปค้าง/เด้ง", "ข้อเสนอแนะอื่นๆ"]

URL_PLACEHOLDER = "วางลิงก์วิดีโอที่มีปัญหา..."
DETAIL_PLACEHOLDER = "อธิบายปัญหาที่คุณพบ ขั้นตอนที่ทำให้เกิดปัญหา หรือข้อความแจ้งเตือน..."


def build_report_message(
    category: str,
    detail: str,
    video_url: str = "",
    attach_sys_log: bool = False,
) -> str:
    """Format the report as a readable ntfy notification body."""
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    clean_url = video_url.strip() or "ไม่ได้ระบุ"

    lines = [
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        f"┃  หมวดหมู่ : {category}",
        f"┃  เวลาแจ้ง : {now_str}",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        "🔗 ลิงก์วิดีโอที่พบปัญหา :",
        clean_url,
        "",
        "📝 รายละเอียดปัญหา :",
        detail.strip(),
    ]

    if attach_sys_log:
        os_desc = f"{platform.system()} {platform.release()} ({platform.version()})"
        lines.extend([
            "",
            "────────────────────────────",
            "💻 ข้อมูลระบบ (System Log) :",
            f"• App: {APP_NAME} v{__version__}",
            f"• OS: {os_desc}",
            f"• Runtime: Python {platform.python_version()}",
        ])

    return "\n".join(lines)


def send_report(
    category: str,
    detail: str,
    video_url: str = "",
    attach_sys_log: bool = False,
) -> str:
    """POST the report to ntfy. Returns the sent body; raises on failure."""
    if not detail.strip():
        raise ValueError("detail is required")

    body = build_report_message(category, detail, video_url, attach_sys_log)
    params = urllib.parse.urlencode({
        "title": f"🚨 [ClipDesk] แจ้งปัญหา: {category}",
        "priority": "4",
        "tags": "warning,clipdesk",
    })
    req = urllib.request.Request(
        f"{NTFY_URL}?{params}",
        data=body.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=NTFY_TIMEOUT) as resp:
        if resp.status != 200:
            raise RuntimeError(f"ntfy returned HTTP {resp.status}")
    return body
