"""Async thumbnail fetching, disk cache and rounded rendering.

Network access happens through QNetworkAccessManager in the GUI thread but is
fully asynchronous — the UI never blocks waiting for an image.
"""

from __future__ import annotations

import hashlib
import os
from collections import OrderedDict
from typing import Optional

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from app.services.app_paths import user_data_dir

THUMB_WIDTH = 160
THUMB_HEIGHT = 90
THUMB_RADIUS = 6
MAX_CACHE_BYTES = 30 * 1024 * 1024
MAX_CACHE_ITEMS = 50
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
REQUEST_TIMEOUT_MS = 15_000


def default_cache_dir() -> str:
    return os.path.join(user_data_dir(), "cache", "thumbnails")


def render_thumbnail(pixmap: QPixmap) -> QPixmap:
    """Scale/crop to 160x90 (aspect fill) and round the corners."""
    if pixmap.isNull():
        return pixmap

    scaled = pixmap.scaled(
        THUMB_WIDTH,
        THUMB_HEIGHT,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - THUMB_WIDTH) // 2)
    y = max(0, (scaled.height() - THUMB_HEIGHT) // 2)
    cropped = scaled.copy(x, y, THUMB_WIDTH, THUMB_HEIGHT)

    out = QPixmap(THUMB_WIDTH, THUMB_HEIGHT)
    out.fill(Qt.GlobalColor.transparent)

    painter = QPainter(out)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    path = QPainterPath()
    path.addRoundedRect(
        QRectF(0, 0, THUMB_WIDTH, THUMB_HEIGHT), THUMB_RADIUS, THUMB_RADIUS
    )
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return out


class ThumbnailCache:
    """Disk cache bounded by total bytes and item count."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_bytes: int = MAX_CACHE_BYTES,
        max_items: int = MAX_CACHE_ITEMS,
    ) -> None:
        self.cache_dir = cache_dir or default_cache_dir()
        self.max_bytes = max_bytes
        self.max_items = max_items
        os.makedirs(self.cache_dir, exist_ok=True)

    def _path_for(self, url: str) -> str:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, digest + ".img")

    def load(self, url: str) -> Optional[bytes]:
        path = self._path_for(url)
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            # Touch mtime so LRU pruning keeps recently used images
            os.utime(path, None)
            return data
        except OSError:
            return None

    def store(self, url: str, data: bytes) -> None:
        if not data:
            return
        path = self._path_for(url)
        tmp = path + ".part"
        try:
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
        except OSError:
            try:
                if os.path.isfile(tmp):
                    os.remove(tmp)
            except OSError:
                pass
        self.prune()

    def prune(self) -> None:
        """Keep newest max_items files and stay under max_bytes."""
        try:
            entries = []
            for name in os.listdir(self.cache_dir):
                path = os.path.join(self.cache_dir, name)
                if not os.path.isfile(path):
                    continue
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                entries.append((st.st_mtime, st.st_size, path))
        except OSError:
            return

        entries.sort(reverse=True)  # newest first
        total = 0
        kept = 0
        for _mtime, size, path in entries:
            kept += 1
            total += size
            if kept > self.max_items or total > self.max_bytes:
                try:
                    os.remove(path)
                except OSError:
                    pass

    def clear(self) -> None:
        try:
            for name in os.listdir(self.cache_dir):
                path = os.path.join(self.cache_dir, name)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        except OSError:
            pass


class ThumbnailService(QObject):
    """Fetches thumbnails asynchronously and emits ready QPixmaps.

    Signals:
        thumbnail_ready(str, QPixmap): (url, 160x90 rounded pixmap)
        thumbnail_failed(str): url could not be fetched/decoded
    """

    thumbnail_ready = Signal(str, QPixmap)
    thumbnail_failed = Signal(str)

    def __init__(self, cache_dir: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self._cache = ThumbnailCache(cache_dir)
        self._nam = QNetworkAccessManager(self)
        self._pending: dict[str, QNetworkReply] = {}
        self._memory: "OrderedDict[str, QPixmap]" = OrderedDict()
        self._memory_limit = 50

    # ── public API ──

    def cached(self, url: str) -> Optional[QPixmap]:
        """Return a ready pixmap from memory/disk without any network call."""
        if not url:
            return None

        pixmap = self._memory.get(url)
        if pixmap is not None:
            self._memory.move_to_end(url)
            return pixmap

        data = self._cache.load(url)
        if not data:
            return None

        source = QPixmap()
        if not source.loadFromData(data):
            return None

        pixmap = render_thumbnail(source)
        self._remember(url, pixmap)
        return pixmap

    def request(self, url: str) -> Optional[QPixmap]:
        """Request a thumbnail. Returns a cached pixmap immediately if present.

        Otherwise downloads in the background and emits thumbnail_ready.
        """
        if not url:
            self.thumbnail_failed.emit(url or "")
            return None

        pixmap = self.cached(url)
        if pixmap is not None:
            # Emit on the next tick so callers can connect first
            QTimer.singleShot(0, lambda: self.thumbnail_ready.emit(url, pixmap))
            return pixmap

        if url in self._pending:
            return None

        request = QNetworkRequest(QUrl(url))
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        request.setHeader(
            QNetworkRequest.KnownHeaders.UserAgentHeader,
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ClipDesk/1.0",
        )

        reply = self._nam.get(request)
        self._pending[url] = reply

        timer = QTimer(reply)
        timer.setSingleShot(True)
        timer.timeout.connect(reply.abort)
        timer.start(REQUEST_TIMEOUT_MS)

        reply.finished.connect(lambda: self._on_reply_finished(url, reply))
        return None

    def clear_cache(self) -> None:
        self._memory.clear()
        self._cache.clear()

    # ── internals ──

    def _remember(self, url: str, pixmap: QPixmap) -> None:
        self._memory[url] = pixmap
        self._memory.move_to_end(url)
        while len(self._memory) > self._memory_limit:
            self._memory.popitem(last=False)

    def _on_reply_finished(self, url: str, reply: QNetworkReply) -> None:
        self._pending.pop(url, None)
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                self.thumbnail_failed.emit(url)
                return

            data = bytes(reply.readAll())
            if not data or len(data) > MAX_DOWNLOAD_BYTES:
                self.thumbnail_failed.emit(url)
                return

            source = QPixmap()
            if not source.loadFromData(data):
                self.thumbnail_failed.emit(url)
                return

            self._cache.store(url, data)
            pixmap = render_thumbnail(source)
            self._remember(url, pixmap)
            self.thumbnail_ready.emit(url, pixmap)
        finally:
            reply.deleteLater()
