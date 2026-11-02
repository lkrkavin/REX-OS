#!/usr/bin/env python3
"""
REX Conversation Manager
Manages conversations, memory, and AI interactions.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    from ai_core import REXAICore, Conversation
    from voice_assistant import VoiceAssistant, VoiceState, VoiceConfig
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class ConversationMode(Enum):
    """How the conversation is initiated"""
    TEXT = "text"
    VOICE = "voice"
    WAKE_WORD = "wake_word"


@dataclass
class AgentStatus:
    """Status of the REX agent"""
    ai_available: bool = False
    current_provider: Optional[str] = None
    voice_ready: bool = False
    voice_state: Optional[str] = None
    memory_available: bool = False


class ConversationManager:
    """
    Manages conversations with the REX AI assistant.
    """

    def __init__(self, ai_core: Optional[REXAICore] = None,
                 voice_assistant: Optional[VoiceAssistant] = None):
        self._ai_core = ai_core
        self._voice_assistant = voice_assistant
        self._current_conversation: Optional[Conversation] = None
        self._conversation_id: Optional[str] = None
        self._on_response: Optional[Callable[[str], None]] = None
        self._on_status_change: Optional[Callable[[AgentStatus], None]] = None

    @property
    def status(self) -> AgentStatus:
        return AgentStatus(
            ai_available=self._ai_core.is_available if self._ai_core else False,
            current_provider=self._ai_core.current_provider if self._ai_core else None,
            voice_ready=self._voice_assistant.is_ready if self._voice_assistant else False,
            voice_state=self._voice_assistant.state.value if self._voice_assistant else None,
        )

    def set_on_response(self, callback: Callable[[str], None]):
        self._on_response = callback

    def set_on_status_change(self, callback: Callable[[AgentStatus], None]):
        self._on_status_change = callback

    async def initialize(self) -> bool:
        if self._ai_core:
            await self._ai_core.initialize()

        if self._voice_assistant and self._voice_assistant.config.enabled:
            self._voice_assistant.start_listening()

        return True

    def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        if not self._ai_core:
            return ""
        return self._ai_core.create_conversation(conversation_id)

    async def send_message(self, message: str, mode: ConversationMode = ConversationMode.TEXT) -> Optional[str]:
        if not self._ai_core:
            return None

        if not self._current_conversation:
            self.create_conversation()

        response = await self._ai_core.add_to_conversation(
            self._conversation_id, "user", message
        )

        if self._on_response:
            self._on_response(response)

        return response

    def speak(self, text: str) -> bool:
        if self._voice_assistant:
            return self._voice_assistant.speak(text)
        return False

    def shutdown(self):
        if self._voice_assistant:
            self._voice_assistant.shutdown()
        if self._ai_core:
            self._ai_core.shutdown()


__all__ = ["ConversationMode", "AgentStatus", "ConversationManager"]