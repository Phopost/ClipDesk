"""Unit tests for the thumbnail cache and rounded rendering."""

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap

from app.services.thumbnail_service import (
    ThumbnailCache,
    ThumbnailService,
    render_thumbnail,
    THUMB_HEIGHT,
    THUMB_WIDTH,
)


def _make_pixmap(w: int = 320, h: int = 240, color: str = "#ff0000") -> QPixmap:
    pixmap = QPixmap(w, h)
    pixmap.fill(QColor(color))
    return pixmap


def test_render_thumbnail_crops_and_rounds(qapp):
    out = render_thumbnail(_make_pixmap(320, 240))
    assert out.width() == THUMB_WIDTH
    assert out.height() == THUMB_HEIGHT

    image = out.toImage()
    # Corner is transparent (rounded), centre is opaque
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.pixelColor(THUMB_WIDTH // 2, THUMB_HEIGHT // 2).alpha() == 255


def test_render_thumbnail_handles_portrait(qapp):
    out = render_thumbnail(_make_pixmap(90, 160))
    assert out.width() == THUMB_WIDTH
    assert out.height() == THUMB_HEIGHT
    assert not out.isNull()


def test_cache_store_and_load(tmp_path):
    cache = ThumbnailCache(str(tmp_path))
    cache.store("https://example.com/a.jpg", b"abc")
    assert cache.load("https://example.com/a.jpg") == b"abc"
    assert cache.load("https://example.com/missing.jpg") is None


def test_cache_prunes_to_max_items(tmp_path):
    cache = ThumbnailCache(str(tmp_path), max_bytes=10_000_000, max_items=3)
    for i in range(6):
        url = f"https://example.com/{i}.jpg"
        cache.store(url, b"x" * 100)
        path = cache._path_for(url)
        os.utime(path, (1000 + i, 1000 + i))

    files = [f for f in os.listdir(tmp_path) if f.endswith(".img")]
    assert len(files) == 3

    # Newest three survive
    for i in (3, 4, 5):
        assert cache.load(f"https://example.com/{i}.jpg") is not None
    assert cache.load("https://example.com/0.jpg") is None


def test_cache_prunes_to_max_bytes(tmp_path):
    cache = ThumbnailCache(str(tmp_path), max_bytes=250, max_items=50)
    for i in range(4):
        url = f"https://example.com/{i}.jpg"
        cache.store(url, b"x" * 100)
        path = cache._path_for(url)
        os.utime(path, (2000 + i, 2000 + i))

    files = [f for f in os.listdir(tmp_path) if f.endswith(".img")]
    assert len(files) == 2


def test_service_emits_failure_for_empty_url(qtbot):
    service = ThumbnailService()
    with qtbot.waitSignal(service.thumbnail_failed, timeout=1000):
        service.request("")


def test_service_uses_disk_cache(qapp, tmp_path):
    cache = ThumbnailCache(str(tmp_path))
    source = _make_pixmap(320, 240)
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    source.save(buffer, "PNG")
    cache.store("https://example.com/x.png", bytes(buffer.data()))

    service = ThumbnailService(str(tmp_path))
    pixmap = service.cached("https://example.com/x.png")
    assert pixmap is not None
    assert pixmap.size().width() == THUMB_WIDTH
    assert pixmap.size().height() == THUMB_HEIGHT
