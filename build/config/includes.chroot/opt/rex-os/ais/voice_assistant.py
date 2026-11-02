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
- Support for English, Tamil, and Tanglish
- No continuous recording by default (push-to-talk only)

Usage:
    voice = VoiceAssistant(VoiceConfig(language="en-US", push_to_talk=True))

    # Enable voice assistant
    voice.start_listening()  # Optional, for continuous listening

    # Push-to-talk mode
    text = voice.push_to_talk()

    # Text-to-speech
    voice.speak("Hello, how can I help you?")
"""

import asyncio
import os
import threading
import time
import shutil
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class VoiceState(Enum):
    """Voice assistant state"""
    OFFLINE = "offline"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    MUTED = "muted"
    ERROR = "error"


class LanguageCode(Enum):
    """Supported language codes for speech recognition"""
    ENGLISH_US = "en-US"
    ENGLISH_GB = "en-GB"
    TAMIL_IN = "ta-IN"
    HINDI_IN = "hi-IN"
    TANGISH = "ta-Latn-IN"  # Tanglish (Tamil in Latin script)


@dataclass
class VoiceConfig:
    """Configuration for voice assistant"""
    enabled: bool = True
    push_to_talk: bool = True  # Default: Push-to-talk mode (no continuous recording)
    wake_word: str = "hey rex"
    wake_word_enabled: bool = True
    sample_rate: int = 16000
    language: str = "en-US"  # Default to English
    tts_voice: str = "en-US"
    tts_rate: int = 150
    tts_volume: float = 1.0
    microphone_device: Optional[str] = None
    max_recording_seconds: int = 30

    # Language-specific configurations
    language_configs: Dict[str, Dict] = field(default_factory=lambda: {
        "en-US": {"tts_voice": "English (US)", "tts_id": "en-us"},
        "ta-IN": {"tts_voice": "Tamil", "tts_id": "ta"},
        "ta-Latn-IN": {"tts_voice": "Tamil (Tanglish)", "tts_id": "ta-latn"},
        "hi-IN": {"tts_voice": "Hindi", "tts_id": "hi"},
    })


class VoiceAssistant:
    """
    REX Voice Assistant with push-to-talk and wake-word support.

    This module provides speech-to-text and text-to-speech capabilities
    with graceful degradation when audio components are unavailable.
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

        # Check available dependencies
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

        # Set initial state based on availability
        if self._stt_available or self._tts_available:
            self._state = VoiceState.OFFLINE
        else:
            self._state = VoiceState.ERROR

    @property
    def state(self) -> VoiceState:
        """Get current voice state"""
        return self._state

    @property
    def is_muted(self) -> bool:
        """Check if microphone is muted"""
        return self._microphone_muted

    @property
    def is_ready(self) -> bool:
        """Check if voice assistant is ready (has at least one capability)"""
        return self._stt_available or self._tts_available

    def add_state_listener(self, callback: Callable[[VoiceState], None]):
        """Add a callback for state changes"""
        self._state_listeners.append(callback)

    def _notify_state_change(self):
        """Notify all listeners of state change"""
        for callback in self._state_listeners:
            try:
                callback(self._state)
            except Exception:
                pass

    def _set_state(self, state: VoiceState):
        """Set state and notify listeners"""
        self._state = state
        self._notify_state_change()

    def set_on_transcription(self, callback: Callable[[str], None]):
        """Set callback for transcription results"""
        self._on_transcription = callback

    def set_on_error(self, callback: Callable[[str], None]):
        """Set callback for errors"""
        self._on_error = callback

    def mute(self):
        """Mute the microphone"""
        self._microphone_muted = True

    def unmute(self):
        """Unmute the microphone"""
        self._microphone_muted = False

    def start_listening(self):
        """Start listening for speech (for continuous mode or push-to-talk)"""
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
                        # Adjust for ambient noise
                        self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

                        # Listen with timeout
                        audio = self._recognizer.listen(source, timeout=1.0, phrase_time_limit=self.config.max_recording_seconds)

                    self._set_state(VoiceState.PROCESSING)

                    # Recognize speech
                    try:
                        text = self._recognizer.recognize_google(
                            audio,
                            language=self.config.language
                        )
                        self._transcription_result = text
                        self._set_state(VoiceState.LISTENING)

                        if self._on_transcription:
                            self._on_transcription(text)

                        # Check for wake word if enabled
                        if self.config.wake_word_enabled:
                            if self.config.wake_word.lower() in text.lower():
                                self._handle_wake_word(text)

                    except sr.UnknownValueError:
                        # Speech not understood - continue listening
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
        """Stop listening"""
        self._stop_event.set()
        if hasattr(self, '_recognition_thread') and self._recognition_thread:
            self._recognition_thread.join(timeout=2.0)
            self._recognition_thread = None

    def push_to_talk(self, duration: float = 5.0) -> Optional[str]:
        """
        Record speech for a short duration (push-to-talk mode).
        Returns transcribed text or None.
        """
        if not self._stt_available:
            return None

        if self._microphone_muted:
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
        """
        Speak text using TTS.
        Returns True if successful.
        """
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
                    import threading
                    t = threading.Thread(target=speak_async, daemon=True)
                    t.start()

                return True

        except Exception as e:
            self._set_state(VoiceState.ERROR)
            if self._on_error:
                self._on_error(str(e))
            return False

        return False

    def _handle_wake_word(self, text: str):
        """Handle wake word detection"""
        if self.config.wake_word.lower() in text.lower():
            # Wake word detected - could trigger assistant
            remaining_text = text.lower().replace(self.config.wake_word.lower(), "").strip()
            if self._on_transcription:
                self._on_transcription(f"[WAKE_WORD] {remaining_text}" if remaining_text else "[WAKE_WORD]")

    def shutdown(self):
        """Clean shutdown"""
        self.stop_listening()
        self._set_state(VoiceState.OFFLINE)


# Lightweight alternative using system TTS/recognition if available
class LightweightVoiceAssistant(VoiceAssistant):
    """
    Lightweight voice assistant that uses system tools when available.
    Falls back gracefully when Python speech libraries are not installed.
    """

    def __init__(self, config: Optional[VoiceConfig] = None):
        super().__init__(config)
        self._system_tts_available = self._check_system_tts()
        self._system_stt_available = self._check_system_stt()

    def _check_system_tts(self) -> bool:
        """Check if system TTS (espeak, say, etc.) is available"""
        import shutil
        return shutil.which("espeak") is not None or shutil.which("say") is not None

    def _check_system_stt(self) -> bool:
        """Check if system STT is available"""
        import shutil
        return shutil.which("pocketsphinx") is not None

    def speak(self, text: str, blocking: bool = True) -> bool:
        """Speak using system TTS if available"""
        if self._system_tts_available:
            import subprocess
            try:
                if os.name == 'posix':
                    if os.path.exists('/usr/bin/espeak'):
                        subprocess.run(['espeak', '-s', str(self.config.tts_rate), text], timeout=10)
                    elif os.path.exists('/usr/bin/say'):  # macOS
                        subprocess.run(['say', text], timeout=10)
                self._set_state(VoiceState.SPEAKING)
                self._set_state(VoiceState.OFFLINE)
                return True
            except Exception:
                return False
        else:
            return super().speak(text, blocking)

    def push_to_talk(self, duration: float = 5.0) -> Optional[str]:
        """Fallback that returns None if no STT available"""
        if not self._stt_available and not self._system_stt_available:
            return None
        return super().push_to_talk(duration)


def create_voice_assistant(config: Optional[VoiceConfig] = None) -> VoiceAssistant:
    """Factory function to create voice assistant"""
    return VoiceAssistant(config)


__all__ = [
    "VoiceState", "VoiceConfig", "VoiceAssistant", "LightweightVoiceAssistant", "create_voice_assistant"
]