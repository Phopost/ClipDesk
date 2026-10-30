"""Enhanced SoundService for ClipDesk UI Pack.

100% backward-compatible with ClipDesk-source's SoundService (`play_success()`,
`play_error()`, `enabled`, `set_enabled()`), plus UI interaction sounds:
- play_click()
- play_hover()
- play_tab()
- play_check()
- play_download_start()
- play_pause()
- play_cancel()
"""

from __future__ import annotations

import os
import time
from typing import Optional

from PySide6.QtCore import QObject, QSettings, QUrl

try:
    from PySide6.QtMultimedia import QSoundEffect
except ImportError:  # pragma: no cover
    QSoundEffect = None  # type: ignore[assignment]

try:
    import winsound
except ImportError:  # pragma: no cover
    winsound = None  # type: ignore[assignment]

MIN_INTERVAL_SEC = 1.0
UI_MIN_INTERVAL_SEC = 0.045
VOLUME = 0.50


def _default_asset_path(*parts: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "assets", *parts)


try:
    from app.services.app_paths import asset_path
except ImportError:
    asset_path = _default_asset_path


class SoundService(QObject):
    """Plays UI and notification cues, respecting the user's sound setting."""

    _SOUND_NAMES = (
        "success",
        "error",
        "click",
        "hover",
        "tab_switch",
        "check_url",
        "start_download",
        "pause_resume",
        "cancel",
    )

    def __init__(self, enabled: Optional[bool] = None, parent=None) -> None:
        super().__init__(parent)
        self._enabled_override = enabled
        self._settings = QSettings("ClipDesk", "ClipDesk")
        self._last_played = 0.0
        self._last_ui_played = 0.0
        self._effects: dict[str, "QSoundEffect"] = {}
        self._paths: dict[str, str] = {}
        self._load_effects()

    @property
    def enabled(self) -> bool:
        if self._enabled_override is not None:
            return self._enabled_override
        return bool(self._settings.value("sound_enabled", True, type=bool))

    def set_enabled(self, enabled: bool) -> None:
        self._enabled_override = enabled
        self._settings.setValue("sound_enabled", enabled)

    # ── Core Notification Cues (Backward-compatible with ClipDesk-source) ──

    def play_success(self) -> None:
        self._play("success", throttle=MIN_INTERVAL_SEC)

    def play_error(self) -> None:
        self._play("error", throttle=MIN_INTERVAL_SEC)

    # ── Rich UI Cues ──

    def play_click(self) -> None:
        self._play("click", throttle=UI_MIN_INTERVAL_SEC)

    def play_hover(self) -> None:
        self._play("hover", throttle=0.06)

    def play_tab(self) -> None:
        self._play("tab_switch", throttle=UI_MIN_INTERVAL_SEC)

    def play_check(self) -> None:
        self._play("check_url", throttle=UI_MIN_INTERVAL_SEC)

    def play_download_start(self) -> None:
        self._play("start_download", throttle=0.1)

    def play_pause(self) -> None:
        self._play("pause_resume", throttle=UI_MIN_INTERVAL_SEC)

    def play_cancel(self) -> None:
        self._play("cancel", throttle=UI_MIN_INTERVAL_SEC)

    # ── Internals ──

    def _load_effects(self) -> None:
        for name in self._SOUND_NAMES:
            path = asset_path("sounds", f"{name}.wav")
            if not os.path.isfile(path):
                continue
            self._paths[name] = path
            if QSoundEffect is not None:
                effect = QSoundEffect(self)
                effect.setSource(QUrl.fromLocalFile(path))
                effect.setVolume(0.25 if name == "hover" else VOLUME)
                self._effects[name] = effect

    def _play(self, name: str, throttle: float = MIN_INTERVAL_SEC) -> None:
        if not self.enabled:
            return

        now = time.monotonic()
        is_notif = name in ("success", "error")
        last = self._last_played if is_notif else self._last_ui_played
        if now - last < throttle:
            return

        if is_notif:
            self._last_played = now
        else:
            self._last_ui_played = now

        effect = self._effects.get(name)
        if effect is not None:
            effect.play()
        elif winsound is not None and name in self._paths:
            winsound.PlaySound(
                self._paths[name],
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )


_GLOBAL_SOUND: Optional[SoundService] = None


def get_sound_service() -> SoundService:
    """Shared singleton for UI widgets."""
    global _GLOBAL_SOUND
    if _GLOBAL_SOUND is None:
        _GLOBAL_SOUND = SoundService()
    return _GLOBAL_SOUND
