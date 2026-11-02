#!/usr/bin/env python3
"""
REX Conversation Manager
Manages conversations, memory, and AI interactions.

This module provides the interface between the AI Core and the desktop UI.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    from .ai_core import REXAICore, Conversation, ProviderType
    from .voice_assistant import VoiceAssistant, VoiceState
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
    Coordinates between voice and text input, memory, and providers.
    """

    def __init__(self, ai_core: Optional[REXAICore] = None,
                 voice_assistant: Optional[VoiceAssistant] = None):
        self._ai_core = ai_core
        self._voice_assistant = voice_assistant
        self._current_conversation: Optional[Conversation] = None
        self._conversation_id: Optional[str] = None
        self._on_response: Optional[Callable[[str], None]] = None
        self._on_status_change: Optional[Callable[[AgentStatus], None]] = None
        self._last_provider_status: Optional[str] = None

    @property
    def status(self) -> AgentStatus:
        """Get current agent status"""
        return AgentStatus(
            ai_available=self._ai_core.is_available if self._ai_core else False,
            current_provider=self._ai_core.current_provider.value if self._ai_core and self._ai_core.current_provider else None,
            voice_ready=self._voice_assistant.is_ready if self._voice_assistant else False,
            voice_state=self._voice_assistant.state.value if self._voice_assistant else None,
            memory_available=True  # Memory is assumed available if AI is
        )

    def set_on_response(self, callback: Callable[[str], None]):
        """Set callback for AI responses"""
        self._on_response = callback

    def set_on_status_change(self, callback: Callable[[AgentStatus], None]):
        """Set callback for status changes"""
        self._on_status_change = callback

    def _update_status(self):
        """Update and notify if status changed"""
        status = self.status
        if (self._last_provider_status != status.current_provider or
            status.ai_available != (self._last_provider_status is not None)):
            self._last_provider_status = status.current_provider
            if self._on_status_change:
                self._on_status_change(status)

    async def initialize(self) -> bool:
        """Initialize the conversation manager"""
        if self._ai_core:
            await self._ai_core.initialize()

        if self._voice_assistant:
            self._voice_assistant.add_state_listener(self._handle_voice_state_change)
            # Start voice assistant if configured
            if self._voice_assistant.config.enabled:
                self._voice_assistant.start_listening()

        self._update_status()
        return True

    def _handle_voice_state_change(self, state):
        """Handle voice state changes"""
        self._update_status()

    def create_conversation(self, conversation_id: Optional[str] = None) -> str:
        """Create a new conversation"""
        if not self._ai_core:
            return ""

        self._conversation_id = conversation_id or str(uuid.uuid4())
        self._current_conversation = self._ai_core.create_conversation(self._conversation_id)
        return self._conversation_id

    async def send_message(self, message: str, mode: ConversationMode = ConversationMode.TEXT) -> Optional[str]:
        """
        Send a message and get response.
        Returns the AI response or None if unavailable.
        """
        if not self._ai_core:
            return None

        # Create conversation if needed
        if not self._current_conversation:
            self.create_conversation()

        # Get AI response
        response = await self._ai_core.add_to_conversation(
            self._conversation_id, "user", message
        )

        # Notify response handler
        if self._on_response:
            self._on_response(response)

        return response

    async def speak_and_listen(self) -> Optional[str]:
        """
        Use push-to-talk to capture and process voice input.
        Returns the AI response.
        """
        if not self._voice_assistant:
            return None

        # Capture speech
        text = self._voice_assistant.push_to_talk()
        if text:
            return await self.send_message(text, ConversationMode.VOICE)
        return None

    def set_voice_active(self, active: bool):
        """Start or stop voice assistant listening"""
        if active:
            self._voice_assistant.start_listening()
        else:
            self._voice_assistant.stop_listening()

    def toggle_mute(self) -> bool:
        """Toggle microphone mute state"""
        if self._voice_assistant.is_muted:
            self._voice_assistant.unmute()
            return False
        else:
            self._voice_assistant.mute()
            return True

    def speak(self, text: str) -> bool:
        """Speak text using TTS"""
        if self._voice_assistant:
            return self._voice_assistant.speak(text)
        return False

    def get_provider_status(self) -> Dict[str, Any]:
        """Get detailed status of all providers"""
        if not self._ai_core or not self._ai_core._providers:
            return {"initialized": False}

        status = {
            "initialized": True,
            "available": self._ai_core.is_available,
            "provider": self._ai_core.current_provider.value if self._ai_core.current_provider else None,
            "providers": {}
        }

        for ptype, provider in self._ai_core._providers.items():
            status["providers"][ptype.value] = {
                "available": provider.available,
                "last_error": provider.last_error
            }

        return status

    def shutdown(self):
        """Clean shutdown"""
        if self._voice_assistant:
            self._voice_assistant.shutdown()
        if self._ai_core:
            self._ai_core.shutdown()

        self._current_conversation = None
        self._conversation_id = None


__all__ = ["ConversationMode", "AgentStatus", "ConversationManager"]