#!/usr/bin/env python3
"""
REX AI Provider Adapters
Provides a unified interface for different AI providers.

Supported providers:
- Ollama (local, no API key required)
- OpenAI (requires OPENAI_API_KEY)
- Anthropic (requires ANTHROPIC_API_KEY)
- Google (requires GOOGLE_API_KEY)
- HuggingFace (requires HUGGING_FACE_API_KEY)
"""

import asyncio
import os
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class ProviderType(Enum):
    """Supported AI providers"""
    OLLAMA = "ollama"
    LLAMA_CPP = "llamacpp"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    HUGGING_FACE = "huggingface"
    NONE = "none"  # Alias for offline mode (backward compatibility)
    OFFLINE = "offline"  # Fallback mode


@dataclass
class ModelInfo:
    """Information about an AI model"""
    name: str
    provider: ProviderType
    capabilities: List[str]
    context_length: int = 4096
    supports_streaming: bool = True


@dataclass
class ProviderConfig:
    """Configuration for a provider"""
    enabled: bool = True
    timeout: float = 30.0
    max_retries: int = 3
    base_url: Optional[str] = None


class AIProvider(ABC):
    """Abstract base class for AI providers"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig()
        self._available = False
        self._last_error: Optional[str] = None

    @property
    def available(self) -> bool:
        """Check if provider is available and ready"""
        return self._available

    @property
    def last_error(self) -> Optional[str]:
        """Get last error message"""
        return self._last_error

    @abstractmethod
    async def check_availability(self) -> bool:
        """Check if the provider is available and configured"""
        pass

    @abstractmethod
    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate a response from the AI"""
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """List available models for this provider"""
        pass

    def shutdown(self):
        """Clean shutdown of provider connections"""
        pass


class OllamaProvider(AIProvider):
    """Ollama local AI provider"""

    def __init__(self, config: Optional[ProviderConfig] = None,
                 base_url: Optional[str] = None):
        super().__init__(config)
        self.base_url = base_url or os.environ.get("OLLAMA_URL", "http://localhost:11434")
        self._models_cache: List[ModelInfo] = []

    async def check_availability(self) -> bool:
        """Check if Ollama server is running"""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status == 200:
                        self._available = True
                        self._last_error = None
                        return True
            self._available = False
            self._last_error = "Ollama server not responding"
            return False
        except Exception as e:
            self._available = False
            self._last_error = str(e)
            return False

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate response from Ollama model"""
        if not self._available:
            await self.check_availability()

        if not self._available:
            raise RuntimeError(f"Ollama not available: {self._last_error}")

        try:
            import aiohttp
            model_name = model or "llama2"

            payload = {
                "model": model_name,
                "prompt": prompt,
                "max_tokens": max_tokens,
                "stream": stream
            }

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("response", "")
                    else:
                        raise RuntimeError(f"Ollama API error: {resp.status}")
        except Exception as e:
            self._last_error = str(e)
            raise

    async def list_models(self) -> List[ModelInfo]:
        """List available Ollama models"""
        if not self._available:
            await self.check_availability()

        if not self._available:
            return []

        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = []
                        for m in data.get("models", []):
                            models.append(ModelInfo(
                                name=m.get("name", "unknown"),
                                provider=ProviderType.OLLAMA,
                                capabilities=["text-generation"],
                                context_length=m.get("detail", {}).get("context_length", 4096)
                            ))
                        return models
        except Exception:
            pass

        return []


class OpenAIProvider(AIProvider):
    """OpenAI API provider"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self._client = None

    async def check_availability(self) -> bool:
        """Check if OpenAI API key is configured"""
        if not self.api_key:
            self._last_error = "OPENAI_API_KEY not set"
            return False
        self._available = True
        return True

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate response from OpenAI model"""
        if not self._available or not self.api_key:
            await self.check_availability()

        if not self._available:
            raise RuntimeError("OpenAI not available: no API key")

        try:
            import aiohttp

            model_name = model or "gpt-3.5-turbo"

            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens
            }

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        error_data = await resp.json()
                        raise RuntimeError(f"OpenAI API error: {error_data}")
        except Exception as e:
            self._last_error = str(e)
            raise

    async def list_models(self) -> List[ModelInfo]:
        """List OpenAI models"""
        return [
            ModelInfo(name="gpt-4", provider=ProviderType.OPENAI, capabilities=["text-generation"], context_length=8192),
            ModelInfo(name="gpt-3.5-turbo", provider=ProviderType.OPENAI, capabilities=["text-generation"], context_length=4096),
            ModelInfo(name="gpt-3.5-turbo-16k", provider=ProviderType.OPENAI, capabilities=["text-generation"], context_length=16384),
        ]

    def shutdown(self):
        """Clean shutdown"""
        self.api_key = None


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")

    async def check_availability(self) -> bool:
        """Check if Anthropic API key is configured"""
        if not self.api_key:
            self._last_error = "ANTHROPIC_API_KEY not set"
            return False
        self._available = True
        return True

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate response from Claude model"""
        if not self._available or not self.api_key:
            await self.check_availability()

        if not self._available:
            raise RuntimeError("Anthropic not available: no API key")

        try:
            import aiohttp

            model_name = model or "claude-3-opus-20240229"

            payload = {
                "model": model_name,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]
            }

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01"
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"]
                    else:
                        error_data = await resp.json()
                        raise RuntimeError(f"Anthropic API error: {error_data}")
        except Exception as e:
            self._last_error = str(e)
            raise

    async def list_models(self) -> List[ModelInfo]:
        """List Anthropic models"""
        return [
            ModelInfo(name="claude-3-opus-20240229", provider=ProviderType.ANTHROPIC, capabilities=["text-generation"], context_length=100000),
            ModelInfo(name="claude-3-sonnet-20240229", provider=ProviderType.ANTHROPIC, capabilities=["text-generation"], context_length=100000),
            ModelInfo(name="claude-3-haiku-20240307", provider=ProviderType.ANTHROPIC, capabilities=["text-generation"], context_length=100000),
        ]

    def shutdown(self):
        """Clean shutdown"""
        self.api_key = None


class GoogleProvider(AIProvider):
    """Google AI Provider (Gemini)"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self.api_key = os.environ.get("GOOGLE_API_KEY")

    async def check_availability(self) -> bool:
        """Check if Google API key is configured"""
        if not self.api_key:
            self._last_error = "GOOGLE_API_KEY not set"
            return False
        self._available = True
        return True

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate response from Gemini model"""
        if not self._available or not self.api_key:
            await self.check_availability()

        if not self._available:
            raise RuntimeError("Google not available: no API key")

        try:
            import aiohttp

            model_name = model or "gemini-pro"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

            payload = {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens}
            }

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]
                    else:
                        error_data = await resp.json()
                        raise RuntimeError(f"Google API error: {error_data}")
        except Exception as e:
            self._last_error = str(e)
            raise

    async def list_models(self) -> List[ModelInfo]:
        """List Google models"""
        return [
            ModelInfo(name="gemini-pro", provider=ProviderType.GOOGLE, capabilities=["text-generation"], context_length=32768),
            ModelInfo(name="gemini-pro-vision", provider=ProviderType.GOOGLE, capabilities=["text-generation", "vision"], context_length=32768),
        ]

    def shutdown(self):
        """Clean shutdown"""
        self.api_key = None


class LlamaCppProvider(AIProvider):
    """llama.cpp local AI provider"""

    def __init__(self, config: Optional[ProviderConfig] = None,
                 base_url: Optional[str] = None):
        super().__init__(config)
        self.base_url = base_url or os.environ.get("LLAMA_CPP_URL", "http://localhost:8080")
        self._models_cache: List[ModelInfo] = []

    async def check_availability(self) -> bool:
        """Check if llama.cpp server is running"""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/model") as resp:
                    if resp.status == 200:
                        self._available = True
                        self._last_error = None
                        return True
            self._available = False
            self._last_error = "llama.cpp server not responding"
            return False
        except Exception as e:
            self._available = False
            self._last_error = str(e)
            return False

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate response from llama.cpp model"""
        if not self._available:
            await self.check_availability()

        if not self._available:
            raise RuntimeError(f"llama.cpp not available: {self._last_error}")

        try:
            import aiohttp

            # llama.cpp uses /completion endpoint
            payload = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "stream": stream
            }

            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.base_url}/completion",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("content", data.get("response", ""))
                    else:
                        error_text = await resp.text()
                        raise RuntimeError(f"llama.cpp API error: {resp.status} - {error_text}")
        except Exception as e:
            self._last_error = str(e)
            raise

    async def list_models(self) -> List[ModelInfo]:
        """List llama.cpp models"""
        if not self._available:
            await self.check_availability()

        if not self._available:
            return []

        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"{self.base_url}/model") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [ModelInfo(
                            name=data.get("model", "llama.cpp"),
                            provider=ProviderType.LLAMA_CPP,
                            capabilities=["text-generation"],
                            context_length=data.get("context_length", 4096)
                        )]
        except Exception:
            pass

        return [ModelInfo(
            name="llama.cpp",
            provider=ProviderType.LLAMA_CPP,
            capabilities=["text-generation"],
            context_length=4096
        )]

    def shutdown(self):
        """Clean shutdown"""
        pass


class OfflineProvider(AIProvider):
    """Offline fallback provider - provides template responses"""

    def __init__(self, config: Optional[ProviderConfig] = None):
        super().__init__(config)
        self._templates = {
            'greeting': "Hello! I'm REX OS. I'm currently running in offline mode, so my responses will be limited. How can I assist you today?",
            'help': "I'm in offline mode right now. I can help with basic questions, but for AI-powered assistance, you'll need to install an AI provider like Ollama.",
            'default': "I'm currently running in offline mode. I don't have access to AI capabilities right now. Would you like me to help with something else?",
            'error': "I encountered an error processing your request.",
            'acknowledge': "I acknowledge your request. This is a basic offline response."
        }

    async def check_availability(self) -> bool:
        """Offline provider is always available"""
        self._available = True
        self._last_error = None
        return True

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False) -> str:
        """Generate a template response based on prompt content"""
        prompt_lower = prompt.lower() if prompt else ""

        if any(w in prompt_lower for w in ['hello', 'hi', 'hey', 'greetings', 'good']):
            return self._templates['greeting']
        elif 'help' in prompt_lower or 'assist' in prompt_lower:
            return self._templates['help']
        else:
            return self._templates['default']

    async def list_models(self) -> List[ModelInfo]:
        """Return offline model info"""
        return [ModelInfo(
            name="offline",
            provider=ProviderType.OFFLINE,
            capabilities=["text-generation"],
            context_length=4096
        )]

    def shutdown(self):
        """Clean shutdown"""
        pass

    def get_template_response(self, key: str, **kwargs) -> str:
        """Get a template response with optional formatting"""
        template = self._templates.get(key, self._templates['default'])
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


def get_available_providers() -> Dict[str, ProviderType]:
    """Get dictionary of available provider types by name"""
    return {
        "ollama": ProviderType.OLLAMA,
        "llamacpp": ProviderType.LLAMA_CPP,
        "openai": ProviderType.OPENAI,
        "anthropic": ProviderType.ANTHROPIC,
        "google": ProviderType.GOOGLE,
        "huggingface": ProviderType.HUGGING_FACE,
        "offline": ProviderType.OFFLINE,
    }


def create_provider(provider_type: ProviderType, config: Optional[ProviderConfig] = None) -> AIProvider:
    """Factory function to create a provider instance"""
    if provider_type == ProviderType.OLLAMA:
        return OllamaProvider(config=config)
    elif provider_type == ProviderType.LLAMA_CPP:
        return LlamaCppProvider(config=config)
    elif provider_type == ProviderType.OPENAI:
        return OpenAIProvider(config=config)
    elif provider_type == ProviderType.ANTHROPIC:
        return AnthropicProvider(config=config)
    elif provider_type == ProviderType.GOOGLE:
        return GoogleProvider(config=config)
    elif provider_type == ProviderType.OFFLINE or provider_type == ProviderType.NONE:
        return OfflineProvider(config=config)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")


__all__ = [
    "ProviderType", "ModelInfo", "ProviderConfig", "AIProvider",
    "OllamaProvider", "LlamaCppProvider", "OpenAIProvider", "AnthropicProvider", "GoogleProvider", "OfflineProvider",
    "get_available_providers", "create_provider"
]
