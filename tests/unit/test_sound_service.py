"""Unit tests for the sound service (throttle + settings toggle)."""

import os
import wave

from app.services.app_paths import asset_path
from app.services.sound_service import SoundService


class _CountingEffect:
    def __init__(self):
        self.calls = 0

    def play(self):
        self.calls += 1


def _service_with_counter(enabled=True):
    service = SoundService(enabled=enabled)
    counter = _CountingEffect()
    service._effects = {"success": counter, "error": counter}
    return service, counter


def test_sound_files_exist_and_are_short():
    for name in ("success.wav", "error.wav"):
        path = asset_path("sounds", name)
        assert os.path.isfile(path), f"missing {path}"
        with wave.open(path, "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            assert duration < 1.0
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2


def test_disabled_plays_nothing():
    service, counter = _service_with_counter(enabled=False)
    service.play_success()
    service.play_error()
    assert counter.calls == 0


def test_throttle_limits_to_one_sound_per_second():
    service, counter = _service_with_counter(enabled=True)
    service.play_success()
    service.play_success()
    service.play_error()
    assert counter.calls == 1

    # Simulate one second passing
    service._last_played -= 1.5
    service.play_success()
    assert counter.calls == 2
