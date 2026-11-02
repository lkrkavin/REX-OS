#!/usr/bin/env python3
"""
REX AI Core - Central AI service with provider adapters

IMPLEMENTATION STATUS: ENHANCED
This module provides a modular AI provider architecture supporting
local (Ollama) and cloud providers with graceful offline fallback.

Features:
- Provider adapter architecture (Ollama, OpenAI, Anthropic, Google)
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
    from ai_providers import (
        ProviderType, ModelInfo, AIProvider,
        OllamaProvider, OpenAIProvider, AnthropicProvider, GoogleProvider,
        create_provider
    )
    PROVIDERS_AVAILABLE = True
except ImportError:
    PROVIDERS_AVAILABLE = False

try:
    from user_memory import UserMemory
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
        """Convert messages to a single prompt for providers"""
        return "\n".join(
            f"{m['role']}: {m['content']}" for m in self.messages[-10:]
        )


@dataclass
class ProviderStatus:
    """Status of an AI provider"""
    provider_type: str
    available: bool = False
    models: List[str] = field(default_factory=list)
    last_error: Optional[str] = None
    response_time_ms: Optional[float] = None


class REXAICore:
    """
    Centralized AI service with provider adapters.

    USAGE:
        ai = REXAICore()
        await ai.initialize()

        if ai.is_available:
            response = await ai.generate("Hello, world!")
        else:
            response = ai._offline_response("Hello, world!")
    """

    def __init__(self, config_path: str = "/etc/rex/ai_providers.json",
                 data_path: str = "/var/lib/rex"):
        self.config_path = config_path
        self.data_path = data_path
        self._initialized = False
        self._provider: Optional[Any] = None
        self._provider_type: Optional[str] = None
        self._provider_available = False
        self._providers: Dict[str, Any] = {}
        self._memory: Optional[Any] = None
        self._conversations: Dict[str, Conversation] = {}

    @property
    def is_available(self) -> bool:
        """Check if any AI provider is available"""
        return self._provider_available and self._provider is not None

    @property
    def current_provider(self) -> Optional[str]:
        """Get the currently active provider"""
        return self._provider_type

    async def initialize(self) -> bool:
        """
        Initialize the AI core and detect available providers.
        Returns True if at least one provider is available.
        """
        if not PROVIDERS_AVAILABLE:
            self._initialized = True
            return False

        # Initialize user memory
        if MEMORY_AVAILABLE:
            try:
                self._memory = UserMemory(1, base_path=self.data_path)
            except Exception:
                self._memory = None

        # Try providers in order
        providers_to_try = ["ollama", "openai", "anthropic", "google"]

        for provider_name in providers_to_try:
            try:
                provider = create_provider(ProviderType(provider_name))
                self._providers[provider_name] = provider

                if await provider.check_availability():
                    self._provider = provider
                    self._provider_type = provider_name
                    self._provider_available = True
                    self._initialized = True
                    return True
            except Exception:
                continue

        self._initialized = True
        return False

    async def generate(self, prompt: str, model: Optional[str] = None,
                       max_tokens: int = 1000, stream: bool = False,
                       conversation_id: Optional[str] = None) -> str:
        """Generate text from the AI."""
        if not self._initialized:
            raise RuntimeError("AI Core not initialized")

        if not self._provider_available:
            return self._offline_response(prompt)

        if conversation_id and conversation_id in self._conversations:
            conv = self._conversations[conversation_id]
            prompt = conv.to_prompt()

        try:
            return await self._provider.generate(prompt, model, max_tokens, stream)
        except Exception as e:
            # Try another provider
            for pname, provider in self._providers.items():
                if pname != self._provider_type and hasattr(provider, 'available') and provider.available:
                    try:
                        self._provider = provider
                        self._provider_type = pname
                        return await provider.generate(prompt, model, max_tokens, stream)
                    except Exception:
                        continue
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

        response = await self.generate(conv.to_prompt(), conversation_id=conversation_id)
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
        providers = [p for p in ["ollama", "openai", "anthropic", "google"]]
        return f"[Offline Mode] I cannot process your request. No AI provider is available.\n\nAvailable providers: {providers}"

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


__all__ = ["REXAICore", "ProviderType", "ModelInfo", "Conversation", "ProviderStatus"]