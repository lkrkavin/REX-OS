#!/usr/bin/env python3
"""
REX Voice Assistant Module
Provides speech recognition and text-to-speech capabilities.

Features:
- Push-to-talk support
- Optional wake-word detection ("Hey Rex")
- Microphone mute and listening indicator
- Graceful fallback when audio unavailable
- Lightweight implementation for 4GB RAM systems
"""

import asyncio
import os
import threading
import time
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum


class VoiceState(Enum):
    """Voice assistant state"""
    OFFLINE = "offline"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    MUTED = "muted"
    ERROR = "error"


@dataclass
class VoiceConfig:
    """Configuration for voice assistant"""
    enabled: bool = True
    push_to_talk: bool = True
    wake_word: str = "hey rex"
    wake_word_enabled: bool = True
    sample_rate: int = 16000
    language: str = "en-US"
    tts_voice: str = "en-US"
    tts_rate: int = 150
    tts_volume: float = 1.0
    microphone_device: Optional[str] = None
    max_recording_seconds: int = 30


class VoiceAssistant:
    """
    REX Voice Assistant with push-to-talk and wake-word support.
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self._state = VoiceState.OFFLINE
        self._state_listeners: List[Callable[[VoiceState], None]] = []
        self._transcription_result: Optional[str] = None
        self._on_transcription: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._microphone_muted = False
        self._recognizer = None
        self._tts_engine = None
        self._recognition_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._check_dependencies()

    def _check_dependencies(self):
        """Check if speech recognition libraries are available"""
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._stt_available = True
        except ImportError:
            self._stt_available = False

        try:
            import pyttsx3
            self._tts_engine = pyttsx3.init()
            self._tts_available = True
        except ImportError:
            self._tts_available = False

        if self._stt_available or self._tts_available:
            self._state = VoiceState.OFFLINE
        else:
            self._state = VoiceState.ERROR

    @property
    def state(self) -> VoiceState:
        return self._state

    @property
    def is_muted(self) -> bool:
        return self._microphone_muted

    @property
    def is_ready(self) -> bool:
        return self._stt_available or self._tts_available

    def add_state_listener(self, callback: Callable[[VoiceState], None]):
        self._state_listeners.append(callback)

    def _notify_state_change(self):
        for callback in self._state_listeners:
            try:
                callback(self._state)
            except Exception:
                pass

    def _set_state(self, state: VoiceState):
        self._state = state
        self._notify_state_change()

    def set_on_transcription(self, callback: Callable[[str], None]):
        self._on_transcription = callback

    def set_on_error(self, callback: Callable[[str], None]):
        self._on_error = callback

    def mute(self):
        self._microphone_muted = True

    def unmute(self):
        self._microphone_muted = False

    def start_listening(self):
        if not self._stt_available:
            self._set_state(VoiceState.ERROR)
            if self._on_error:
                self._on_error("Speech recognition not available")
            return

        self._set_state(VoiceState.LISTENING)
        self._stop_event.clear()

        def listen_loop():
            import speech_recognition as sr
            while not self._stop_event.is_set():
                try:
                    with sr.Microphone() as source:
                        self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = self._recognizer.listen(source, timeout=1.0,
                            phrase_time_limit=self.config.max_recording_seconds)

                    self._set_state(VoiceState.PROCESSING)
                    try:
                        text = self._recognizer.recognize_google(
                            audio, language=self.config.language
                        )
                        self._transcription_result = text
                        self._set_state(VoiceState.LISTENING)
                        if self._on_transcription:
                            self._on_transcription(text)
                        if self.config.wake_word_enabled:
                            if self.config.wake_word.lower() in text.lower():
                                remaining = text.lower().replace(self.config.wake_word.lower(), "").strip()
                                if self._on_transcription:
                                    self._on_transcription(f"[WAKE_WORD] {remaining}" if remaining else "[WAKE_WORD]")
                    except sr.UnknownValueError:
                        self._set_state(VoiceState.LISTENING)
                    except sr.RequestError:
                        self._set_state(VoiceState.ERROR)
                        if self._on_error:
                            self._on_error("Speech recognition service unavailable")
                        break
                except Exception as e:
                    self._set_state(VoiceState.ERROR)
                    if self._on_error:
                        self._on_error(str(e))
                    break

        self._recognition_thread = threading.Thread(target=listen_loop, daemon=True)
        self._recognition_thread.start()

    def stop_listening(self):
        self._stop_event.set()
        if hasattr(self, '_recognition_thread') and self._recognition_thread:
            self._recognition_thread.join(timeout=2.0)
            self._recognition_thread = None

    def push_to_talk(self, duration: float = 5.0) -> Optional[str]:
        if not self._stt_available or self._microphone_muted:
            return None

        try:
            import speech_recognition as sr
            self._set_state(VoiceState.LISTENING)
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self._recognizer.listen(source, timeout=1.0, phrase_time_limit=duration)

            self._set_state(VoiceState.PROCESSING)
            text = self._recognizer.recognize_google(audio, language=self.config.language)
            self._transcription_result = text
            self._set_state(VoiceState.OFFLINE)
            return text
        except sr.UnknownValueError:
            self._set_state(VoiceState.OFFLINE)
            return None
        except sr.RequestError:
            self._set_state(VoiceState.ERROR)
            if self._on_error:
                self._on_error("Speech recognition service unavailable")
            return None
        except Exception as e:
            self._set_state(VoiceState.ERROR)
            if self._on_error:
                self._on_error(str(e))
            return None

    def speak(self, text: str, blocking: bool = True) -> bool:
        if not self._tts_available:
            return False

        try:
            if self._tts_engine:
                self._set_state(VoiceState.SPEAKING)

                def speak_async():
                    try:
                        self._tts_engine.say(text)
                        self._tts_engine.runAndWait()
                    except Exception:
                        pass
                    finally:
                        self._set_state(VoiceState.LISTENING if not self._microphone_muted else VoiceState.MUTED)

                if blocking:
                    speak_async()
                else:
                    t = threading.Thread(target=speak_async, daemon=True)
                    t.start()
                return True
        except Exception as e:
            self._set_state(VoiceState.ERROR)
            if self._on_error:
                self._on_error(str(e))
            return False

        return False

    def shutdown(self):
        self.stop_listening()
        self._set_state(VoiceState.OFFLINE)


__all__ = ["VoiceState", "VoiceConfig", "VoiceAssistant"]