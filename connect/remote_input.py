#!/usr/bin/env python3
"""
REX CONNECT - Remote Input Handler

Handles remote mouse, keyboard, and media control input.
Only operates on explicitly confirmed remote sessions.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
import threading


class InputType(Enum):
    """Types of remote input"""
    MOUSE_MOVE = "mouse_move"
    MOUSE_CLICK = "mouse_click"
    MOUSE_SCROLL = "mouse_scroll"
    KEYBOARD_TEXT = "keyboard_text"
    KEYBOARD_KEY = "keyboard_key"
    MEDIA_PLAY = "media_play"
    MEDIA_PAUSE = "media_pause"
    MEDIA_NEXT = "media_next"
    MEDIA_PREVIOUS = "media_previous"
    MEDIA_VOLUME_UP = "media_volume_up"
    MEDIA_VOLUME_DOWN = "media_volume_down"
    LOCK_SCREEN = "lock_screen"


@dataclass
class InputEvent:
    """Remote input event"""
    event_type: InputType
    data: Dict[str, Any]
    timestamp: float
    source_device: str
    session_id: Optional[str] = None


@dataclass
class InputResult:
    """Result of an input operation"""
    success: bool
    message: str
    error: Optional[str] = None


class RemoteInputHandler:
    """
    Handles remote input operations for connected devices.
    Requires permission for each operation type.
    Does not provide hidden control - all actions are visible and auditable.
    """

    def __init__(self, security_manager: 'SecurityManager' = None):
        self._security_manager = security_manager
        self._callbacks: List[Callable[[InputEvent], InputResult]] = []
        self._lock = threading.RLock()
        self._running = False

    def register_handler(self, callback: Callable[[InputEvent], InputResult]):
        """Register an input handler callback"""
        with self._lock:
            self._callbacks.append(callback)

    async def process_input(
        self,
        event: InputEvent,
        security_manager: 'SecurityManager' = None,
        device_id: str = ""
    ) -> InputResult:
        """
        Process a remote input event.
        Requires permission validation through security manager.
        Fails closed if permission denied or handler unavailable.
        """
        # Fail closed: every remote input must be authorized by the shared core.
        from .security import Permission

        manager = security_manager or self._security_manager
        if not isinstance(event, InputEvent) or not isinstance(device_id, str) or not device_id:
            return InputResult(False, "Invalid input request", "INVALID_REQUEST")
        if event.source_device != device_id or manager is None:
            return InputResult(False, "Security context missing or device mismatch", "PERMISSION_DENIED")

        permission_by_type = {
            InputType.MOUSE_MOVE: Permission.REMOTE_MOUSE,
            InputType.MOUSE_CLICK: Permission.REMOTE_MOUSE,
            InputType.MOUSE_SCROLL: Permission.REMOTE_MOUSE,
            InputType.KEYBOARD_TEXT: Permission.REMOTE_KEYBOARD,
            InputType.KEYBOARD_KEY: Permission.REMOTE_KEYBOARD,
            InputType.MEDIA_PLAY: Permission.MEDIA_CONTROL,
            InputType.MEDIA_PAUSE: Permission.MEDIA_CONTROL,
            InputType.MEDIA_NEXT: Permission.MEDIA_CONTROL,
            InputType.MEDIA_PREVIOUS: Permission.MEDIA_CONTROL,
            InputType.MEDIA_VOLUME_UP: Permission.MEDIA_CONTROL,
            InputType.MEDIA_VOLUME_DOWN: Permission.MEDIA_CONTROL,
            InputType.LOCK_SCREEN: Permission.LOCK_SCREEN,
        }
        required_permission = permission_by_type.get(event.event_type)
        if required_permission is None or not manager.check_permission(
            device_id, required_permission, event.session_id
        ):
            return InputResult(
                success=False,
                message="Permission denied for input type",
                error="PERMISSION_DENIED"
            )

        # Execute through callbacks
        result = None
        with self._lock:
            for callback in self._callbacks:
                try:
                    result = callback(event)
                    if result.success:
                        break
                except Exception as e:
                    if result is None or not result.success:
                        result = InputResult(
                            success=False,
                            message=f"Handler error: {e}",
                            error="HANDLER_ERROR"
                        )

        return result if result else InputResult(success=False, message="No handler available")

    # Convenience methods for each input type

    async def mouse_move(self, x: int, y: int, device_id: str, security_manager) -> InputResult:
        """Move mouse to position"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.REMOTE_MOUSE):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        event = InputEvent(
            event_type=InputType.MOUSE_MOVE,
            data={"x": x, "y": y},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)

    async def mouse_click(
        self,
        x: int,
        y: int,
        device_id: str,
        security_manager,
        button: str = "left",
    ) -> InputResult:
        """Move mouse to position"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.REMOTE_MOUSE):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        event = InputEvent(
            event_type=InputType.MOUSE_CLICK,
            data={"x": x, "y": y, "button": button},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)

    async def scroll(
        self,
        amount: int,
        device_id: str,
        security_manager,
        direction: str = "vertical",
    ) -> InputResult:
        """Scroll mouse wheel"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.REMOTE_MOUSE):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        event = InputEvent(
            event_type=InputType.MOUSE_SCROLL,
            data={"amount": amount, "direction": direction},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)

    async def keyboard_text(
        self,
        text: str,
        device_id: str,
        security_manager
    ) -> InputResult:
        """Send keyboard text"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.REMOTE_KEYBOARD):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        event = InputEvent(
            event_type=InputType.KEYBOARD_TEXT,
            data={"text": text},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)

    async def key_press(
        self,
        key: str,
        device_id: str,
        security_manager
    ) -> InputResult:
        """Press a single key"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.REMOTE_KEYBOARD):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        event = InputEvent(
            event_type=InputType.KEYBOARD_KEY,
            data={"key": key},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)

    async def media_control(
        self,
        action: str,
        device_id: str,
        security_manager
    ) -> InputResult:
        """Media control action"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.MEDIA_CONTROL):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        action_map = {
            "play": InputType.MEDIA_PLAY,
            "pause": InputType.MEDIA_PAUSE,
            "next": InputType.MEDIA_NEXT,
            "previous": InputType.MEDIA_PREVIOUS,
            "volume_up": InputType.MEDIA_VOLUME_UP,
            "volume_down": InputType.MEDIA_VOLUME_DOWN,
        }

        event_type = action_map.get(action)
        if not event_type:
            return InputResult(success=False, message="Invalid media action", error="INVALID_ACTION")

        event = InputEvent(
            event_type=event_type,
            data={"action": action},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)

    async def lock_screen(
        self,
        device_id: str,
        security_manager
    ) -> InputResult:
        """Lock the screen"""
        from .security import Permission
        if security_manager and not security_manager.check_permission(device_id, Permission.LOCK_SCREEN):
            return InputResult(success=False, message="Permission denied", error="PERMISSION_DENIED")

        event = InputEvent(
            event_type=InputType.LOCK_SCREEN,
            data={},
            timestamp=time.time(),
            source_device=device_id
        )
        return await self.process_input(event, security_manager, device_id)


# Global input handler instance
_global_input_handler: Optional[RemoteInputHandler] = None


def get_input_handler() -> RemoteInputHandler:
    """Get global input handler instance"""
    global _global_input_handler
    if _global_input_handler is None:
        from .security import get_security_manager
        _global_input_handler = RemoteInputHandler(get_security_manager())
    return _global_input_handler