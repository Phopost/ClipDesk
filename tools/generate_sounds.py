"""Synthesize pleasant, soft sky-blue themed UI & notification sound effects (WAV).

Generates 44.1 kHz, 16-bit mono PCM WAV files in app/assets/sounds/:
- click.wav          : Soft airy bubble tap for buttons
- hover.wav          : Ultra-subtle crystalline tick for hover
- tab_switch.wav     : Smooth upward whoosh-chime for sidebar navigation
- check_url.wav      : Bright double-ping when checking a link
- start_download.wav : Warm ascending triad chord for starting a download
- pause_resume.wav   : Gentle two-tone toggle cue
- cancel.wav         : Soft descending muted pop for cancel/clear
- success.wav        : Sparkling major 9th arpeggio for completed download
- error.wav          : Soft low marimba-like double tone for errors
"""

from __future__ import annotations

import math
import os
import struct
import wave

SAMPLE_RATE = 44100


def _adsr_tone(
    freq: float,
    duration: float,
    volume: float = 0.28,
    attack: float = 0.005,
    decay: float = 0.08,
    sustain: float = 0.35,
    harmonics: tuple[tuple[float, float], ...] = ((1.0, 1.0), (2.0, 0.25), (3.0, 0.08)),
    freq_end: float | None = None,
) -> list[float]:
    total = int(SAMPLE_RATE * duration)
    out: list[float] = []
    phase = 0.0
    for i in range(total):
        t = i / SAMPLE_RATE
        # Frequency glide if requested
        f = freq if freq_end is None else freq + (freq_end - freq) * (t / duration)
        phase += 2.0 * math.pi * f / SAMPLE_RATE

        # Envelope
        if t < attack:
            env = t / max(attack, 1e-5)
        else:
            progress = (t - attack) / max(duration - attack, 1e-5)
            env = math.exp(-progress * (duration / max(decay, 0.01))) * (1.0 - sustain * 0.3)
            # Smooth tail fade-out on last 10ms
            remaining = duration - t
            if remaining < 0.012:
                env *= max(0.0, remaining / 0.012)

        val = 0.0
        for mult, amp in harmonics:
            val += amp * math.sin(phase * mult)
        out.append(volume * env * val)
    return out


def _mix(*tracks: list[tuple[float, list[float]]]) -> list[float]:
    """Mix multiple (start_time_sec, samples) tracks into a single buffer."""
    max_len = 0
    for offset, samples in tracks:
        end_idx = int(offset * SAMPLE_RATE) + len(samples)
        if end_idx > max_len:
            max_len = end_idx
    buf = [0.0] * max_len
    for offset, samples in tracks:
        start_idx = int(offset * SAMPLE_RATE)
        for i, s in enumerate(samples):
            buf[start_idx + i] += s
    # Soft clip
    return [math.tanh(x * 1.1) * 0.85 for x in buf]


def _write_wav(path: str, samples: list[float]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        frames = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
            for s in samples
        )
        wav.writeframes(frames)


def generate_all_sounds(sounds_dir: str | None = None) -> dict[str, int]:
    if sounds_dir is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sounds_dir = os.path.join(root, "app", "assets", "sounds")

    sounds: dict[str, list[float]] = {
        # 1. Soft bubble tap
        "click.wav": _adsr_tone(
            580.0, 0.055, volume=0.22, attack=0.002, decay=0.022, freq_end=820.0
        ),
        # 2. Subtle crystalline hover tick
        "hover.wav": _adsr_tone(
            1240.0, 0.025, volume=0.08, attack=0.001, decay=0.009, freq_end=1420.0
        ),
        # 3. Sidebar tab switch chime
        "tab_switch.wav": _mix(
            (0.0, _adsr_tone(523.25, 0.09, volume=0.18, decay=0.04)),
            (0.035, _adsr_tone(659.25, 0.12, volume=0.20, decay=0.05)),
        ),
        # 4. Check URL ping
        "check_url.wav": _mix(
            (0.0, _adsr_tone(783.99, 0.11, volume=0.22, decay=0.05)),
            (0.06, _adsr_tone(1046.50, 0.16, volume=0.24, decay=0.07)),
        ),
        # 5. Start Download glowing chord (C5 - E5 - G5 - B5)
        "start_download.wav": _mix(
            (0.00, _adsr_tone(523.25, 0.22, volume=0.20, decay=0.10)),
            (0.045, _adsr_tone(659.25, 0.22, volume=0.20, decay=0.10)),
            (0.09, _adsr_tone(783.99, 0.25, volume=0.22, decay=0.12)),
            (0.135, _adsr_tone(1046.50, 0.32, volume=0.25, decay=0.16)),
        ),
        # 6. Pause / Resume toggle
        "pause_resume.wav": _mix(
            (0.0, _adsr_tone(659.25, 0.08, volume=0.18, decay=0.035)),
            (0.05, _adsr_tone(587.33, 0.10, volume=0.18, decay=0.04)),
        ),
        # 7. Cancel / Clear queue pop
        "cancel.wav": _mix(
            (0.0, _adsr_tone(440.0, 0.08, volume=0.20, decay=0.03, freq_end=310.0)),
            (0.045, _adsr_tone(310.0, 0.11, volume=0.18, decay=0.04, freq_end=220.0)),
        ),
        # 8. Download completed sparkle
        "success.wav": _mix(
            (0.00, _adsr_tone(587.33, 0.18, volume=0.20, decay=0.08)),
            (0.06, _adsr_tone(739.99, 0.18, volume=0.20, decay=0.08)),
            (0.12, _adsr_tone(880.00, 0.20, volume=0.22, decay=0.10)),
            (0.18, _adsr_tone(1174.66, 0.36, volume=0.26, decay=0.18)),
        ),
        # 9. Error alert
        "error.wav": _mix(
            (0.00, _adsr_tone(349.23, 0.14, volume=0.24, decay=0.06)),
            (0.11, _adsr_tone(261.63, 0.24, volume=0.24, decay=0.10)),
        ),
    }

    sizes: dict[str, int] = {}
    for filename, samples in sounds.items():
        full_path = os.path.join(sounds_dir, filename)
        _write_wav(full_path, samples)
        sizes[filename] = os.path.getsize(full_path)
    return sizes


def main() -> None:
    sizes = generate_all_sounds()
    print(f"OK generated={len(sizes)} files total_bytes={sum(sizes.values())}")


if __name__ == "__main__":
    main()
