#!/usr/bin/env python3
"""
REX AI Core - Central AI service with provider adapters

IMPLEMENTATION STATUS: ENHANCED
This module provides a modular AI provider architecture supporting
local (Ollama) and cloud providers with graceful offline fallback.

Features:
- Provider adapter architecture
- Local-first operation with offline fallback
- Model capability detection
- Conversation context management
- Secure credential handling via environment variables
"""

import asyncio
import json
import os
import time
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Import provider adapters
try:
    from ais.ai_providers import (
        ProviderType, ModelInfo, AIProvider,
        OllamaProvider, OpenAIProvider, AnthropicProvider, GoogleProvider,
        create_provider
    )
    PROVIDERS_AVAILABLE = True
except ImportError:
    PROVIDERS_AVAILABLE = False

try:
    from ais.user_memory import UserMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


@dataclass
class Conversation:
    """Represents a conversation with the AI"""
    messages: List[Dict[str, str]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_message(self, role: str, content: str):
        """Add a message to the conversation"""
        self.messages.append({"role": role, "content": content})
        self.updated_at = datetime.now().isoformat()

    def to_prompt(self) -> str:
        """Convert messages to a single prompt for providers that don't support chat"""
        return "\n".join(
            f"{m['role']}: {m['content']}" for m in self.messages[-10:]  # Last 10 messages
        )


@dataclass
class ProviderStatus:
    """Status of an AI provider"""
    provider_type: ProviderType
    available: bool
    models: List[str] = field(default_factory=list)
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None


class AIProviderConfig:
    """Configuration for AI providers"""

    def __init__(self, config_path: str = "/etc/rex/ai_providers.json"):
        self.config_path = config_path
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load provider configuration"""
        defaults = {
            "preferred_provider": None,  # Auto-select if None
            "providers": {
                "ollama": {"base_url": "http://localhost:11434", "timeout": 30},
                "openai": {"timeout": 30},
                "anthropic": {"timeout": 30},
                "google": {"timeout": 30}
            },
            "offline_fallback": True,
            "max_context_length": 4096,
            "default_model": None
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults
                    for key, value in loaded.items():
                        if key in defaults:
                            defaults[key] = value
            except Exception:
                pass

        return defaults

    @property
    def preferred_provider(self) -> Optional[ProviderType]:
        """Get the preferred provider type"""
        pref = self._config.get("preferred_provider")
        if pref and isinstance(pref, str):
            try:
                return ProviderType(pref)
            except ValueError:
                pass
        return None

    @property
    def providers_config(self) -> Dict[str, Any]:
        return self._config.get("providers", {})

    @property
    def offline_fallback(self) -> bool:
        return self._config.get("offline_fallback", True)


class REXAICore:
    """
    Centralized AI service with provider adapters.

    USAGE:
        ai = REXAICore()
        await ai.initialize()

        if ai.is_available:
            response = await ai.generate("Hello, world!")
        else:
            response = ai.offline_response("Hello, world!")
    """

    def __init__(self, config_path: str = "/etc/rex/ai_providers.json",
                 data_path: str = "/var/lib/rex"):
        self.config_path = config_path
        self.data_path = data_path
        self._initialized = False
        self._provider: Optional[AIProvider] = None
        self._provider_type: Optional[ProviderType] = None
        self._provider_available = False
        self._providers: Dict[ProviderType, AIProvider] = {}
        self._config = AIProviderConfig(config_path)
        self._memory: Optional[UserMemory] = None
        self._conversations: Dict[str, Conversation] = {}

    @property
    def is_available(self) -> bool:
        """Check if any AI provider is available"""
        return self._provider_available and self._provider is not None

    @property
    def current_provider(self) -> Optional[ProviderType]:
        """Get the currently active provider"""
        return self._provider_type

    @property
    def provider_status(self) -> ProviderStatus:
        """Get current provider status"""
        return ProviderStatus(
            provider_type=self._provider_type or ProviderType.NONE,
            available=self._provider_available,
            last_error=self._provider.last_error if self._provider else None
        )

    async def initialize(self) -> bool:
        """
        Initialize the AI core and detect available providers.
        Returns True if at least one provider is available.
        """
        if not PROVIDERS_AVAILABLE:
            self._initialized = True
            return False

        # Initialize user memory if available
        if MEMORY_AVAILABLE:
            try:
                self._memory = UserMemory(1, base_path=self.data_path)
            except Exception:
                self._memory = None

        # Try preferred provider first, then others in order
        preferred = self._config.preferred_provider
        providers_to_try = []

        if preferred:
            providers_to_try.append(preferred)

        # Add other available providers
        all_providers = [ProviderType.OLLAMA, ProviderType.OPENAI,
                        ProviderType.ANTHROPIC, ProviderType.GOOGLE]
        for p in all_providers:
            if p != preferred:
                providers_to_try.append(p)

        for provider_type in providers_to_try:
            provider = create_provider(provider_type)
            self._providers[provider_type] = provider

            if await provider.check_availability():
                self._provider = provider
                self._provider_type = provider_type
                self._provider_available = True
                self._initialized = True
                return True

        # No providers available - run in offline mode
        self._initialized = True
        return False

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False,
                       conversation_id: Optional[str] = None) -> str:
        """
        Generate text from the AI.
        """
        if not self._initialized:
            raise RuntimeError("AI Core not initialized")

        if not self._provider_available:
            return self._offline_response(prompt)

        # Get conversation context if provided
        if conversation_id and conversation_id in self._conversations:
            conv = self._conversations[conversation_id]
            prompt = conv.to_prompt()

        try:
            return await self._provider.generate(prompt, model, max_tokens, stream)
        except Exception as e:
            # Try to use another available provider
            for ptype, provider in self._providers.items():
                if ptype != self._provider_type and provider.available:
                    try:
                        self._provider = provider
                        self._provider_type = ptype
                        return await provider.generate(prompt, model, max_tokens, stream)
                    except Exception:
                        continue
            # All providers failed
            return self._offline_response(prompt)

    async def list_models(self) -> List[ModelInfo]:
        """List models from the current provider"""
        if not self._provider:
            return []
        return await self._provider.list_models()

    def create_conversation(self, conversation_id: Optional[str] = None, initial_messages: Optional[List[Dict]] = None) -> str:
        """Create a new conversation and return the conversation ID"""
        cid = conversation_id or str(uuid.uuid4())
        conv = Conversation()
        if initial_messages:
            for m in initial_messages:
                conv.add_message(m.get("role", "user"), m.get("content", ""))
        self._conversations[cid] = conv
        return cid

    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get an existing conversation"""
        return self._conversations.get(conversation_id)

    async def add_to_conversation(self, conversation_id: str, role: str, content: str) -> str:
        """Add a message to a conversation and get AI response"""
        if conversation_id not in self._conversations:
            self.create_conversation(conversation_id)

        conv = self._conversations[conversation_id]
        conv.add_message(role, content)

        response = await self.generate(
            conv.to_prompt(),
            conversation_id=conversation_id
        )
        conv.add_message("assistant", response)

        return response

    def store_preference(self, key: str, value: Any) -> bool:
        """Store a user preference in memory"""
        if not self._memory:
            return False
        try:
            self._memory.set_preference(key, value)
            return True
        except Exception:
            return False

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference from memory"""
        if not self._memory:
            return default
        try:
            return self._memory.get_preference(key, default)
        except Exception:
            return default

    def _offline_response(self, prompt: str) -> str:
        """Generate a response when no AI provider is available"""
        return f"[Offline Mode] I cannot process your request. No AI provider is available.\n\nCurrently available providers: {[p.value for p in ProviderType if p != ProviderType.NONE]}, none are running or configured."

    def shutdown(self):
        """Clean shutdown of all provider connections"""
        for provider in self._providers.values():
            try:
                provider.shutdown()
            except Exception:
                pass
        self._providers.clear()
        self._provider = None
        self._provider_type = None
        self._provider_available = False
        self._initialized = False


# Placeholder implementations for module imports
__all__ = ["REXAICore", "ProviderType", "ModelInfo", "Conversation", "ProviderStatus", "AIProviderConfig"]