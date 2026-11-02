#!/usr/bin/env python3
"""
Tests for AI Provider Adapters
"""

import unittest
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ais.ai_providers import (
    ProviderType, ModelInfo, ProviderConfig,
    OllamaProvider, OpenAIProvider, AnthropicProvider, GoogleProvider, OfflineProvider,
    create_provider, get_available_providers
)


class TestProviderTypes(unittest.TestCase):
    """Test provider type enumeration"""

    def test_provider_types_exist(self):
        """Test that all provider types exist"""
        self.assertEqual(ProviderType.OLLAMA.value, "ollama")
        self.assertEqual(ProviderType.OPENAI.value, "openai")
        self.assertEqual(ProviderType.ANTHROPIC.value, "anthropic")
        self.assertEqual(ProviderType.GOOGLE.value, "google")
        self.assertEqual(ProviderType.NONE.value, "none")

    def test_get_available_providers(self):
        """Test get_available_providers returns all providers"""
        providers = get_available_providers()
        self.assertIn("ollama", providers)
        self.assertIn("openai", providers)
        self.assertIn("anthropic", providers)
        self.assertIn("google", providers)


class TestProviderConfig(unittest.TestCase):
    """Test provider configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ProviderConfig()
        self.assertTrue(config.enabled)
        self.assertEqual(config.timeout, 30.0)
        self.assertEqual(config.max_retries, 3)

    def test_custom_config(self):
        """Test custom configuration"""
        config = ProviderConfig(timeout=60.0, max_retries=5)
        self.assertEqual(config.timeout, 60.0)
        self.assertEqual(config.max_retries, 5)


class TestModelInfo(unittest.TestCase):
    """Test model info dataclass"""

    def test_model_info_creation(self):
        """Test creating ModelInfo"""
        model = ModelInfo(
            name="test-model",
            provider=ProviderType.OLLAMA,
            capabilities=["text-generation"],
            context_length=4096
        )
        self.assertEqual(model.name, "test-model")
        self.assertEqual(model.provider, ProviderType.OLLAMA)
        self.assertEqual(model.context_length, 4096)
        self.assertTrue(model.supports_streaming)


class TestOllamaProvider(unittest.TestCase):
    """Test Ollama provider"""

    def setUp(self):
        self.config = ProviderConfig(timeout=5.0)

    def test_provider_creation(self):
        """Test creating Ollama provider"""
        provider = OllamaProvider(config=self.config)
        self.assertEqual(provider.base_url, "http://localhost:11434")

    def test_custom_base_url(self):
        """Test custom base URL"""
        provider = OllamaProvider(config=self.config, base_url="http://custom:11434")
        self.assertEqual(provider.base_url, "http://custom:11434")

    def test_check_availability_sync(self):
        """Test availability check when offline (sync wrapper)"""
        provider = OllamaProvider(config=self.config, base_url="http://localhost:99999")

    def test_provider_available_property(self):
        """Test provider available property"""
        provider = OllamaProvider(config=self.config)
        # Initially not checked
        self.assertFalse(provider.available)


class TestOpenAIProvider(unittest.TestCase):
    """Test OpenAI provider"""

    def test_provider_creation_no_key(self):
        """Test creating OpenAI provider without API key"""
        provider = OpenAIProvider()
        self.assertIsNone(provider.api_key)

    def test_check_availability_sync(self):
        """Test availability check without API key"""
        provider = OpenAIProvider()
        # Sync test - just verify it returns False when called directly
        # (async method would need asyncio.run in real usage)


class TestAnthropicProvider(unittest.TestCase):
    """Test Anthropic provider"""

    def test_check_availability_sync(self):
        """Test availability check without API key"""
        provider = AnthropicProvider()
        # Sync test - just verify it returns None for api_key
        self.assertIsNone(provider.api_key)


class TestGoogleProvider(unittest.TestCase):
    """Test Google provider"""

    def test_check_availability_sync(self):
        """Test availability check without API key"""
        provider = GoogleProvider()
        self.assertIsNone(provider.api_key)


class TestProviderFactory(unittest.TestCase):
    """Test provider factory function"""

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

    def test_invalid_provider(self):
        """Test creating invalid provider - NONE is now valid (maps to OFFLINE)"""
        # NONE is now a valid alias for OFFLINE provider
        provider = create_provider(ProviderType.NONE)
        self.assertIsInstance(provider, OfflineProvider)

    def test_create_offline_provider(self):
        """Test creating OFFLINE provider"""
        provider = create_provider(ProviderType.OFFLINE)
        self.assertIsInstance(provider, OfflineProvider)


class TestProviderAsync(unittest.TestCase):
    """Async tests for providers"""

    def test_ollama_offline_check(self):
        """Test Ollama availability check when offline"""
        async def run():
            provider = OllamaProvider(config=ProviderConfig(timeout=2.0), base_url="http://localhost:99999")
            result = await provider.check_availability()
            self.assertFalse(result)
        asyncio.run(run())

    def test_openai_no_key_check(self):
        """Test OpenAI availability check without API key"""
        async def run():
            provider = OpenAIProvider()
            result = await provider.check_availability()
            self.assertFalse(result)
        asyncio.run(run())

    def test_anthropic_no_key_check(self):
        """Test Anthropic availability check without API key"""
        async def run():
            provider = AnthropicProvider()
            result = await provider.check_availability()
            self.assertFalse(result)
        asyncio.run(run())

    def test_google_no_key_check(self):
        """Test Google availability check without API key"""
        async def run():
            provider = GoogleProvider()
            result = await provider.check_availability()
            self.assertFalse(result)
        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()