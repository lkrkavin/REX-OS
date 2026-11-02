#!/usr/bin/env python3
"""
Phase 4 Enhanced Tests
Tests for AI Core and Voice Assistant enhancements
"""

import unittest
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ais.ai_core import REXAICore, ProviderType, Conversation, ProviderStatus
from ais.ai_providers import (
    OllamaProvider, OpenAIProvider, AnthropicProvider, GoogleProvider,
    ProviderConfig, create_provider
)
from ais.voice_assistant import (
    VoiceState, VoiceConfig, VoiceAssistant, LightweightVoiceAssistant
)


class TestConversationIntegration(unittest.TestCase):
    """Integration tests for AI Core and conversations"""

    def test_ai_core_conversation_creation(self):
        """Test AI Core conversation creation"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        cid = ai.create_conversation("test-id")
        self.assertIn("test-id", ai._conversations)

    def test_ai_core_conversation_messages(self):
        """Test AI Core conversation message handling"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        ai.create_conversation("test-id")
        conv = ai.get_conversation("test-id")
        self.assertIsNotNone(conv)

    def test_ai_core_offline_mode(self):
        """Test AI Core in offline mode"""
        ai = REXAICore(data_path=tempfile.mkdtemp())
        # Should not be initialized until initialize() is called
        self.assertFalse(ai._initialized)
        self.assertFalse(ai.is_available)
        # Initialize first
        asyncio.run(ai.initialize())
        # Should be initialized but no provider available
        self.assertTrue(ai._initialized)
        self.assertFalse(ai.is_available)
        # Should have offline response
        response = ai._offline_response("test")
        self.assertIn("Offline Mode", response)


class TestProviderFactory(unittest.TestCase):
    """Tests for provider factory function"""

    def test_create_ollama_provider(self):
        """Test creating Ollama provider via factory"""
        provider = create_provider(ProviderType.OLLAMA)
        self.assertIsInstance(provider, OllamaProvider)

    def test_create_openai_provider(self):
        """Test creating OpenAI provider via factory"""
        provider = create_provider(ProviderType.OPENAI)
        self.assertIsInstance(provider, OpenAIProvider)

    def test_create_anthropic_provider(self):
        """Test creating Anthropic provider via factory"""
        provider = create_provider(ProviderType.ANTHROPIC)
        self.assertIsInstance(provider, AnthropicProvider)

    def test_create_google_provider(self):
        """Test creating Google provider via factory"""
        provider = create_provider(ProviderType.GOOGLE)
        self.assertIsInstance(provider, GoogleProvider)


class TestMemoryIntegration(unittest.TestCase):
    """Tests for memory system integration"""

    def test_ai_core_with_memory(self):
        """Test AI Core can use UserMemory"""
        from ais.user_memory import UserMemory

        ai = REXAICore(data_path=tempfile.mkdtemp())

        # Create memory instance
        ai._memory = UserMemory(1, base_path=tempfile.mkdtemp())

        # Test storing preference
        result = ai.store_preference("test_key", "test_value")
        self.assertTrue(result)

        # Test getting preference
        value = ai.get_preference("test_key", "default")
        self.assertEqual(value, "test_value")

        # Test getting non-existent preference
        value = ai.get_preference("nonexistent", "default")
        self.assertEqual(value, "default")


class TestProviderConfiguration(unittest.TestCase):
    """Tests for provider configuration"""

    def test_provider_config_timeout(self):
        """Test provider configuration timeout values"""
        config = ProviderConfig(timeout=60.0)
        self.assertEqual(config.timeout, 60.0)

        config2 = ProviderConfig()
        self.assertEqual(config2.timeout, 30.0)

    def test_ollama_provider_base_url(self):
        """Test Ollama provider base URL"""
        provider = OllamaProvider()
        self.assertEqual(provider.base_url, "http://localhost:11434")

    def test_ollama_custom_base_url(self):
        """Test Ollama provider custom base URL"""
        provider = OllamaProvider(base_url="http://custom:11434")
        self.assertEqual(provider.base_url, "http://custom:11434")

    def test_openai_provider_no_key(self):
        """Test OpenAI provider without API key"""
        provider = OpenAIProvider()
        self.assertIsNone(provider.api_key)


class TestVoiceAssistantEnhancements(unittest.TestCase):
    """Enhanced tests for voice assistant"""

    def test_voice_config_defaults(self):
        """Test voice config default values"""
        config = VoiceConfig()
        self.assertTrue(config.enabled)
        self.assertTrue(config.push_to_talk)
        self.assertEqual(config.language, "en-US")

    def test_voice_config_custom(self):
        """Test custom voice config"""
        config = VoiceConfig(wake_word="hey rex os", language="ta-IN")
        self.assertEqual(config.wake_word, "hey rex os")
        self.assertEqual(config.language, "ta-IN")

    def test_lightweight_voice_init(self):
        """Test LightweightVoiceAssistant initialization"""
        assistant = LightweightVoiceAssistant()
        self.assertTrue(assistant.is_ready or assistant.state == VoiceState.ERROR)


if __name__ == '__main__':
    unittest.main()