# REX AI Modules
# These modules provide the AI Core and User Memory System placeholders
# for future integration with local and cloud AI providers.

from .ai_core import (
    REXAICore,
    ProviderType,
    ModelInfo,
    Conversation,
    ProviderStatus,
    AIProviderConfig,
)

from .ai_providers import (
    AIProvider,
    OllamaProvider,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    LlamaCppProvider,
    OfflineProvider,
    ProviderConfig,
    create_provider,
    get_available_providers,
)

from .voice_assistant import (
    VoiceAssistant,
    LightweightVoiceAssistant,
    VoiceState,
    VoiceConfig,
    create_voice_assistant,
)

from .user_memory import (
    UserMemory,
)

__all__ = [
    # AI Core
    "REXAICore",
    "ProviderType",
    "ModelInfo",
    "Conversation",
    "ProviderStatus",
    "AIProviderConfig",
    # AI Providers
    "AIProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "LlamaCppProvider",
    "OfflineProvider",
    "ProviderConfig",
    "create_provider",
    "get_available_providers",
    # Voice Assistant
    "VoiceAssistant",
    "LightweightVoiceAssistant",
    "VoiceState",
    "VoiceConfig",
    "create_voice_assistant",
    # User Memory
    "UserMemory",
]