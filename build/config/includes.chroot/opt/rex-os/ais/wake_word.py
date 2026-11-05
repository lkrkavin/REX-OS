#!/usr/bin/env python3
"""Local, offline 'Hey Rex' wake-word listener.

PocketSphinx performs both wake-word detection and command transcription locally.
Audio is processed in memory and is never uploaded or saved.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional


def is_wake_phrase(text: str, wake_word: str = "hey rex") -> bool:
    normalized = " ".join((text or "").lower().replace("-", " ").split())
    target = " ".join((wake_word or "hey rex").lower().replace("-", " ").split())
    return bool(target and target in normalized)


class LocalWakeWordListener:
    def __init__(
        self,
        on_activation: Callable[[Optional[str]], None],
        on_error: Optional[Callable[[str], None]] = None,
        wake_word: str = "hey rex",
        language: str = "en-US",
        microphone_device: Optional[int] = None,
    ):
        self.on_activation = on_activation
        self.on_error = on_error
        self.wake_word = wake_word
        self.language = language
        self.microphone_device = microphone_device
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        try:
            import speech_recognition as sr
            import pocketsphinx  # noqa: F401 - validates local decoder is installed
            self._sr = sr
            self._recognizer = sr.Recognizer()
            self.available = True
        except Exception as exc:
            self._sr = None
            self._recognizer = None
            self.available = False
            self._availability_error = str(exc)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> bool:
        if not self.available:
            if self.on_error:
                self.on_error(
                    "Local wake-word engine unavailable. Install python3-speechrecognition, "
                    "python3-pyaudio and python3-pocketsphinx."
                )
            return False
        if self.running:
            return True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._listen_loop, name="rex-local-wake-word", daemon=True
        )
        self._thread.start()
        return True

    def _listen_loop(self):
        sr = self._sr
        try:
            with sr.Microphone(device_index=self.microphone_device) as source:
                self._recognizer.dynamic_energy_threshold = True
                self._recognizer.pause_threshold = 0.45
                self._recognizer.adjust_for_ambient_noise(source, duration=0.6)
                while not self._stop_event.is_set():
                    try:
                        audio = self._recognizer.listen(
                            source, timeout=1.0, phrase_time_limit=3.0
                        )
                    except sr.WaitTimeoutError:
                        continue
                    try:
                        heard = self._recognizer.recognize_sphinx(
                            audio,
                            language=self.language,
                            keyword_entries=[(self.wake_word, 1e-20)],
                        )
                    except (sr.UnknownValueError, sr.RequestError):
                        continue
                    if not is_wake_phrase(heard, self.wake_word):
                        continue

                    # Wake phrase detected locally. Capture only the next command.
                    command = None
                    try:
                        command_audio = self._recognizer.listen(
                            source, timeout=5.0, phrase_time_limit=10.0
                        )
                    except sr.WaitTimeoutError:
                        pass
                    else:
                        try:
                            # Keep command audio on-device; no cloud transcription.
                            command = self._recognizer.recognize_sphinx(
                                command_audio, language=self.language
                            )
                        except (sr.UnknownValueError, sr.RequestError):
                            command = None
                    if not self._stop_event.is_set():
                        self.on_activation(command.strip() if command else None)
        except Exception as exc:
            if not self._stop_event.is_set() and self.on_error:
                self.on_error("Microphone/wake-word listener error: " + str(exc))

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=4.0)
        self._thread = None


__all__ = ["LocalWakeWordListener", "is_wake_phrase"]
