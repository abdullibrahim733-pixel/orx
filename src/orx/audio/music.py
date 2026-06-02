"""Procedural audio generation using pygame.mixer and numpy-like synthesis."""

from __future__ import annotations

import math
import pygame


class AudioManager:
    """Generates and plays procedural sound effects and music."""

    def __init__(self):
        self.enabled = True
        self.music_volume = 0.3
        self.sfx_volume = 0.5
        self._sample_rate = 22050

    def generate_shoot_sfx(self) -> pygame.mixer.Sound:
        samples = int(self._sample_rate * 0.1)
        buf = bytearray(samples * 2)
        for i in range(samples):
            t = i / self._sample_rate
            env = max(0, 1.0 - t / 0.1) ** 2
            val = int(math.sin(t * 800 * 2 * math.pi) * env * 12000 +
                      (255 - i * 255 // samples) * env * 50)
            val = max(-32768, min(32767, val))
            buf[i * 2] = val & 0xFF
            buf[i * 2 + 1] = (val >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    def generate_hit_sfx(self) -> pygame.mixer.Sound:
        samples = int(self._sample_rate * 0.15)
        buf = bytearray(samples * 2)
        for i in range(samples):
            t = i / self._sample_rate
            env = max(0, 1.0 - t / 0.15)
            val = int(math.sin(t * 200 * 2 * math.pi) * env * 8000)
            val = max(-32768, min(32767, val))
            buf[i * 2] = val & 0xFF
            buf[i * 2 + 1] = (val >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    def generate_levelup_sfx(self) -> pygame.mixer.Sound:
        samples = int(self._sample_rate * 0.5)
        buf = bytearray(samples * 2)
        for i in range(samples):
            t = i / self._sample_rate
            freq = 440 + t * 600
            env = min(1.0, t * 4) * max(0, 1.0 - t / 0.5)
            val = int(math.sin(freq * t * 2 * math.pi) * env * 10000)
            val = max(-32768, min(32767, val))
            buf[i * 2] = val & 0xFF
            buf[i * 2 + 1] = (val >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    def generate_death_sfx(self) -> pygame.mixer.Sound:
        samples = int(self._sample_rate * 0.3)
        buf = bytearray(samples * 2)
        for i in range(samples):
            t = i / self._sample_rate
            freq = 300 - t * 200
            env = max(0, 1.0 - t / 0.3)
            val = int(math.sin(freq * t * 2 * math.pi) * env * 9000)
            val = max(-32768, min(32767, val))
            buf[i * 2] = val & 0xFF
            buf[i * 2 + 1] = (val >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))

    def generate_synthwave_loop(self) -> pygame.mixer.Sound:
        duration = 4.0
        samples = int(self._sample_rate * duration)
        buf = bytearray(samples * 2)
        bpm = 120
        beat_len = 60.0 / bpm
        for i in range(samples):
            t = i / self._sample_rate
            beat_pos = t % beat_len
            kick = math.exp(-beat_pos * 15) * math.sin(beat_pos * 80 * 2 * math.pi) * 0.4
            bass_note = int(t / beat_len) % 4
            bass_freq = [55, 55, 73.4, 65.4][bass_note]
            bass = math.sin(t * bass_freq * 2 * math.pi) * 0.2 * (0.8 + 0.2 * math.sin(t * 3))
            pad = math.sin(t * 220 * 2 * math.pi) * 0.05 + math.sin(t * 330 * 2 * math.pi) * 0.03
            val = int((kick + bass + pad) * 15000)
            val = max(-32768, min(32767, val))
            buf[i * 2] = val & 0xFF
            buf[i * 2 + 1] = (val >> 8) & 0xFF
        return pygame.mixer.Sound(buffer=bytes(buf))
