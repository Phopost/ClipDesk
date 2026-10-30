"""Generate matching artwork thumbnails for ClipDesk UI preview & fallback.

Creates 4 crisp 16:9 thumbnails in app/assets/thumbnails/ matching the mockup:
1. preview_bluesky.png : Mountain lake with blue sky & clouds (Blue Sky - Dreaming Together)
2. queue_chill.png     : Sunset neon city skyline reflection (Chill Vibes - Relaxing Music)
3. queue_cat.png       : Cute orange/white kitten on soft bokeh background (Cute Cat Funny Moments)
4. queue_japan.png     : Spring mountain river with cherry blossoms (เที่ยวญี่ปุ่น ฤดูใบไม้ผลิ)
"""

from __future__ import annotations

import os
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import (
    QImage, QPainter, QLinearGradient, QRadialGradient, QColor,
    QPainterPath, QPen, QBrush,
)


def _draw_bluesky(w: int = 440, h: int = 248) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Sky gradient
    sky = QLinearGradient(0, 0, 0, h * 0.65)
    sky.setColorAt(0.0, QColor("#2B7DE9"))
    sky.setColorAt(0.5, QColor("#67B5F8"))
    sky.setColorAt(1.0, QColor("#C6E8FF"))
    p.fillRect(0, 0, w, h, sky)

    # Fluffy anime clouds
    p.setPen(Qt.PenStyle.NoPen)
    for cx, cy, rx, ry, alpha in [
        (w * 0.72, h * 0.24, 65, 32, 235),
        (w * 0.82, h * 0.30, 55, 28, 220),
        (w * 0.62, h * 0.31, 48, 22, 210),
        (w * 0.22, h * 0.20, 52, 24, 215),
        (w * 0.32, h * 0.25, 42, 20, 200),
    ]:
        p.setBrush(QColor(255, 255, 255, alpha))
        p.drawEllipse(QPointF(cx, cy), rx, ry)

    # Distant snow mountains
    mtn = QPainterPath()
    mtn.moveTo(0, h * 0.62)
    mtn.lineTo(w * 0.18, h * 0.34)
    mtn.lineTo(w * 0.34, h * 0.50)
    mtn.lineTo(w * 0.52, h * 0.28)
    mtn.lineTo(w * 0.70, h * 0.48)
    mtn.lineTo(w * 0.88, h * 0.35)
    mtn.lineTo(w, h * 0.55)
    mtn.lineTo(w, h * 0.62)
    mtn.closeSubpath()
    mtn_grad = QLinearGradient(0, h * 0.28, 0, h * 0.62)
    mtn_grad.setColorAt(0.0, QColor("#E3F2FD"))
    mtn_grad.setColorAt(0.4, QColor("#5C8BC0"))
    mtn_grad.setColorAt(1.0, QColor("#2D5A7B"))
    p.fillPath(mtn, mtn_grad)

    # Pine tree silhouettes along shore
    p.setBrush(QColor("#1E4D3B"))
    p.drawRect(QRectF(0, h * 0.57, w, h * 0.06))

    # Mirror lake reflection
    lake = QLinearGradient(0, h * 0.62, 0, h)
    lake.setColorAt(0.0, QColor("#1D5B8C"))
    lake.setColorAt(0.5, QColor("#4FA3E3"))
    lake.setColorAt(1.0, QColor("#1B4366"))
    p.fillRect(QRectF(0, h * 0.62, w, h * 0.38), lake)

    # Water ripples
    p.setPen(QPen(QColor(255, 255, 255, 95), 1.5))
    for ry in (0.68, 0.74, 0.81, 0.88, 0.94):
        p.drawLine(QPointF(w * 0.15, h * ry), QPointF(w * 0.85, h * ry))

    p.end()
    return img


def _draw_chill(w: int = 240, h: int = 135) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Sunset synthwave sky
    sky = QLinearGradient(0, 0, w, h)
    sky.setColorAt(0.0, QColor("#1A103C"))
    sky.setColorAt(0.45, QColor("#6B2D7B"))
    sky.setColorAt(0.75, QColor("#E85D75"))
    sky.setColorAt(1.0, QColor("#FFB36B"))
    p.fillRect(0, 0, w, h, sky)

    # Glowing sun
    sun = QRadialGradient(QPointF(w * 0.35, h * 0.55), h * 0.35)
    sun.setColorAt(0.0, QColor(255, 235, 160, 240))
    sun.setColorAt(0.5, QColor(255, 140, 105, 140))
    sun.setColorAt(1.0, QColor(255, 100, 120, 0))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(sun)
    p.drawEllipse(QPointF(w * 0.35, h * 0.55), h * 0.35, h * 0.35)

    # City skyline silhouette
    p.setBrush(QColor("#140C2E"))
    buildings = [
        (0.05, 0.55, 0.08), (0.14, 0.42, 0.07), (0.22, 0.48, 0.06),
        (0.52, 0.30, 0.09), (0.62, 0.22, 0.08), (0.71, 0.38, 0.09),
        (0.81, 0.32, 0.08), (0.90, 0.45, 0.08),
    ]
    for bx, top, bw in buildings:
        p.drawRect(QRectF(w * bx, h * top, w * bw, h * (0.72 - top)))

    # Water reflection at bottom
    water = QLinearGradient(0, h * 0.72, 0, h)
    water.setColorAt(0.0, QColor("#2A164D"))
    water.setColorAt(1.0, QColor("#0F0722"))
    p.fillRect(QRectF(0, h * 0.72, w, h * 0.28), water)
    p.end()
    return img


def _draw_cat(w: int = 240, h: int = 135) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Soft warm bokeh background
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0.0, QColor("#6E9E6E"))
    bg.setColorAt(0.5, QColor("#A8C686"))
    bg.setColorAt(1.0, QColor("#E8D59E"))
    p.fillRect(0, 0, w, h, bg)

    p.setPen(Qt.PenStyle.NoPen)
    # Ears
    p.setBrush(QColor("#E59A52"))
    ear_l = QPainterPath()
    ear_l.moveTo(w * 0.33, h * 0.48)
    ear_l.lineTo(w * 0.37, h * 0.16)
    ear_l.lineTo(w * 0.47, h * 0.38)
    ear_l.closeSubpath()
    p.fillPath(ear_l, QColor("#E59A52"))

    ear_r = QPainterPath()
    ear_r.moveTo(w * 0.67, h * 0.48)
    ear_r.lineTo(w * 0.63, h * 0.16)
    ear_r.lineTo(w * 0.53, h * 0.38)
    ear_r.closeSubpath()
    p.fillPath(ear_r, QColor("#E59A52"))

    # Inner pink ears
    p.setBrush(QColor("#F4B6C2"))
    p.drawEllipse(QPointF(w * 0.39, h * 0.32), 7, 10)
    p.drawEllipse(QPointF(w * 0.61, h * 0.32), 7, 10)

    # Cat head & cheeks
    p.setBrush(QColor("#F3B562"))
    p.drawEllipse(QPointF(w * 0.50, h * 0.64), w * 0.24, h * 0.34)
    p.setBrush(QColor("#FFF8EE"))
    p.drawEllipse(QPointF(w * 0.50, h * 0.72), w * 0.18, h * 0.22)

    # Big glossy eyes
    p.setBrush(QColor("#2C221E"))
    p.drawEllipse(QPointF(w * 0.42, h * 0.58), 7.5, 8.5)
    p.drawEllipse(QPointF(w * 0.58, h * 0.58), 7.5, 8.5)
    p.setBrush(QColor("#FFFFFF"))
    p.drawEllipse(QPointF(w * 0.405, h * 0.555), 2.8, 2.8)
    p.drawEllipse(QPointF(w * 0.565, h * 0.555), 2.8, 2.8)

    # Pink nose
    p.setBrush(QColor("#F08A9B"))
    p.drawEllipse(QPointF(w * 0.50, h * 0.67), 4.5, 3.2)
    p.end()
    return img


def _draw_japan(w: int = 240, h: int = 135) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Blue sky + Fuji mountain + emerald river
    sky = QLinearGradient(0, 0, 0, h * 0.6)
    sky.setColorAt(0.0, QColor("#3A8DDE"))
    sky.setColorAt(1.0, QColor("#B9E2FF"))
    p.fillRect(0, 0, w, h, sky)

    # Mt Fuji peak
    fuji = QPainterPath()
    fuji.moveTo(w * 0.20, h * 0.62)
    fuji.lineTo(w * 0.46, h * 0.25)
    fuji.lineTo(w * 0.54, h * 0.25)
    fuji.lineTo(w * 0.80, h * 0.62)
    fuji.closeSubpath()
    p.fillPath(fuji, QColor("#5A82B8"))

    # Green hills on left/right
    hill_l = QPainterPath()
    hill_l.moveTo(0, h * 0.65)
    hill_l.quadTo(w * 0.22, h * 0.35, w * 0.44, h * 0.65)
    hill_l.closeSubpath()
    p.fillPath(hill_l, QColor("#387D44"))

    hill_r = QPainterPath()
    hill_r.moveTo(w * 0.55, h * 0.65)
    hill_r.quadTo(w * 0.80, h * 0.38, w, h * 0.65)
    hill_r.closeSubpath()
    p.fillPath(hill_r, QColor("#2E6B3A"))

    # Emerald river
    river = QLinearGradient(0, h * 0.62, 0, h)
    river.setColorAt(0.0, QColor("#4EB1D6"))
    river.setColorAt(1.0, QColor("#1D6D8E"))
    p.fillRect(QRectF(0, h * 0.62, w, h * 0.38), river)

    # Cherry blossom pink petals top-right
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(255, 192, 213, 220))
    for px, py, r in [(0.82, 0.18, 12), (0.90, 0.14, 14), (0.94, 0.24, 11), (0.76, 0.12, 9)]:
        p.drawEllipse(QPointF(w * px, h * py), r, r)

    p.end()
    return img


def generate_demo_thumbnails(thumbs_dir: str | None = None) -> dict[str, str]:
    if thumbs_dir is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        thumbs_dir = os.path.join(root, "app", "assets", "thumbnails")
    os.makedirs(thumbs_dir, exist_ok=True)

    builders = {
        "preview_bluesky.png": _draw_bluesky,
        "queue_chill.png": _draw_chill,
        "queue_cat.png": _draw_cat,
        "queue_japan.png": _draw_japan,
    }
    paths: dict[str, str] = {}
    for name, fn in builders.items():
        out_path = os.path.join(thumbs_dir, name)
        img = fn()
        img.save(out_path, "PNG")
        paths[name] = out_path
    return paths


if __name__ == "__main__":
    from PySide6.QtGui import QGuiApplication
    import sys
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    res = generate_demo_thumbnails()
    print(f"OK generated={len(res)} thumbnails")
