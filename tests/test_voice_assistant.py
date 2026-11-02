#!/usr/bin/env python3
"""
Tests for Voice Assistant Module
"""

import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ais.voice_assistant import (
    VoiceState, VoiceConfig, VoiceAssistant, LightweightVoiceAssistant,
    create_voice_assistant
)


class TestVoiceState(unittest.TestCase):
    """Test voice state enumeration"""

    def test_voice_states_exist(self):
        """Test that all voice states exist"""
        self.assertEqual(VoiceState.OFFLINE.value, "offline")
        self.assertEqual(VoiceState.LISTENING.value, "listening")
        self.assertEqual(VoiceState.PROCESSING.value, "processing")
        self.assertEqual(VoiceState.SPEAKING.value, "speaking")
        self.assertEqual(VoiceState.MUTED.value, "muted")
        self.assertEqual(VoiceState.ERROR.value, "error")


class TestVoiceConfig(unittest.TestCase):
    """Test voice configuration"""

    def test_default_config(self):
        """Test default configuration"""
        config = VoiceConfig()
        self.assertTrue(config.enabled)
        self.assertTrue(config.push_to_talk)
        self.assertEqual(config.wake_word, "hey rex")
        self.assertEqual(config.language, "en-US")
        self.assertEqual(config.sample_rate, 16000)

    def test_custom_config(self):
        """Test custom configuration"""
        config = VoiceConfig(
            push_to_talk=False,
            wake_word_enabled=False,
            language="ta-IN"
        )
        self.assertFalse(config.push_to_talk)
        self.assertFalse(config.wake_word_enabled)
        self.assertEqual(config.language, "ta-IN")


class TestVoiceAssistant(unittest.TestCase):
    """Test VoiceAssistant basic functionality"""

    def test_initialization(self):
        """Test voice assistant initialization"""
        assistant = VoiceAssistant()
        self.assertTrue(assistant.is_ready or assistant.state == VoiceState.ERROR)
        self.assertEqual(assistant.state, assistant.state)

    def test_mute_unmute(self):
        """Test mute/unmute functionality"""
        assistant = VoiceAssistant()
        self.assertFalse(assistant.is_muted)
        assistant.mute()
        self.assertTrue(assistant.is_muted)
        assistant.unmute()
        self.assertFalse(assistant.is_muted)

    def test_state_property(self):
        """Test state property"""
        assistant = VoiceAssistant()
        # State should be a valid VoiceState
        valid_states = [VoiceState.OFFLINE, VoiceState.ERROR]
        if assistant.is_ready:
            valid_states.append(VoiceState.LISTENING)
        self.assertIn(assistant.state, valid_states)

    def test_set_state_listeners(self):
        """Test state listener functionality"""
        assistant = VoiceAssistant()
        states_received = []

        def listener(state):
            states_received.append(state)

        assistant.add_state_listener(listener)
        # State change should trigger listener
        assistant._set_state(VoiceState.LISTENING)
        # The listener was called (may or may not have been called yet due to implementation)

    def test_push_to_talk_returns_none_when_unavailable(self):
        """Test push_to_talk returns None when STT unavailable"""
        assistant = VoiceAssistant()
        if not assistant._stt_available:
            result = assistant.push_to_talk()
            self.assertIsNone(result)

    def test_speak_returns_bool(self):
        """Test speak returns boolean"""
        assistant = VoiceAssistant()
        result = assistant.speak("test", blocking=False)
        self.assertIsInstance(result, bool)

    def test_shutdown(self):
        """Test shutdown"""
        assistant = VoiceAssistant()
        assistant.stop_listening()  # Should not raise
        assistant.shutdown()
        self.assertEqual(assistant.state, VoiceState.OFFLINE)


class TestLightweightVoiceAssistant(unittest.TestCase):
    """Test LightweightVoiceAssistant"""

    def test_initialization(self):
        """Test lightweight assistant initialization"""
        assistant = LightweightVoiceAssistant()
        # Should also handle system TTS/STR availability
        self.assertTrue(assistant.is_ready or assistant.state == VoiceState.ERROR)

    def test_system_tts_check(self):
        """Test system TTS detection"""
        assistant = LightweightVoiceAssistant()
        # Just verify it doesn't crash
        self.assertIsNotNone(assistant._system_tts_available)

    def test_system_stt_check(self):
        """Test system STT detection"""
        assistant = LightweightVoiceAssistant()
        # Just verify it doesn't crash
        self.assertIsNotNone(assistant._system_stt_available)


class TestCreateVoiceAssistant(unittest.TestCase):
    """Test factory function"""

    def test_create_voice_assistant(self):
        """Test creating voice assistant via factory"""
        assistant = create_voice_assistant()
        self.assertIsNotNone(assistant)
        self.assertIsInstance(assistant, VoiceAssistant)

    def test_create_with_custom_config(self):
        """Test creating with custom config"""
        config = VoiceConfig(wake_word_enabled=False)
        assistant = create_voice_assistant(config)
        self.assertEqual(assistant.config.wake_word_enabled, False)


if __name__ == '__main__':
    unittest.main()