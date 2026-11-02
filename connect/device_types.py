#!/usr/bin/env python3
"""
REX CONNECT - Device Type Adapters

Modular adapters for different device types.
Each adapter implements device-specific functionality.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
import time


@dataclass
class DeviceCapabilities:
    """Capabilities of a device type"""
    supports_remote_input: bool = False
    supports_screen_sharing: bool = False
    supports_file_transfer: bool = False
    supports_notifications: bool = False
    supports_media_control: bool = False
    supports_lock_screen: bool = False
    requires_confirmation_for_input: bool = True
    requires_confirmation_for_stream: bool = True
    max_file_size_mb: int = 100  # Default max file transfer size


class DeviceAdapter(ABC):
    """Abstract base class for device type adapters"""

    @property
    @abstractmethod
    def device_type_name(self) -> str:
        """Human-readable device type name"""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> DeviceCapabilities:
        """Supported capabilities"""
        pass

    @abstractmethod
    def get_pairing_code(self, device_id: str) -> str:
        """Generate pairing code for this device type"""
        pass

    @abstractmethod
    def validate_pairing(self, device_id: str, code: str) -> bool:
        """Validate pairing with provided code"""
        pass

    @abstractmethod
    async def on_device_connected(self, device_id: str) -> Dict[str, Any]:
        """Handle device connection events"""
        pass

    @abstractmethod
    async def on_device_disconnected(self, device_id: str):
        """Handle device disconnection events"""
        pass


class AndroidPhoneAdapter(DeviceAdapter):
    """Adapter for Android phones"""

    @property
    def device_type_name(self) -> str:
        return "Android Phone"

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            supports_remote_input=True,
            supports_screen_sharing=True,
            supports_file_transfer=True,
            supports_notifications=True,
            supports_media_control=True,
            supports_lock_screen=True,
            requires_confirmation_for_input=True,
            requires_confirmation_for_stream=True,
            max_file_size_mb=500
        )

    def get_pairing_code(self, device_id: str) -> str:
        return f"Android-{device_id[-6:]}"

    def validate_pairing(self, device_id: str, code: str) -> bool:
        return len(code) == 23 and code.startswith("Android-")

    async def on_device_connected(self, device_id: str) -> Dict[str, Any]:
        return {
            "type": "android_phone",
            "device_name": "Android Phone",
            "capabilities": ["input", "file_transfer", "notifications", "screen"],
            "status": "connected"
        }

    async def on_device_disconnected(self, device_id: str):
        pass


class AndroidTVAdapter(DeviceAdapter):
    """Adapter for Android TV / Google TV devices"""

    @property
    def device_type_name(self) -> str:
        return "Android TV"

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            supports_remote_input=True,
            supports_screen_sharing=True,  # Receive only (TV shows content)
            supports_file_transfer=False,
            supports_notifications=False,
            supports_media_control=True,
            supports_lock_screen=False,
            requires_confirmation_for_input=True,
            requires_confirmation_for_stream=False,
            max_file_size_mb=0
        )

    def get_pairing_code(self, device_id: str) -> str:
        return f"ATV-{device_id[-6:]}"

    def validate_pairing(self, device_id: str, code: str) -> bool:
        return len(code) >= 4 and code.startswith("ATV-")

    async def on_device_connected(self, device_id: str) -> Dict[str, Any]:
        return {
            "type": "android_tv",
            "device_name": "Android TV",
            "capabilities": ["input", "media_control", "screen_receive"],
            "status": "connected"
        }

    async def on_device_disconnected(self, device_id: str):
        pass


class WindowsPCAdapter(DeviceAdapter):
    """Adapter for Windows PCs"""

    @property
    def device_type_name(self) -> str:
        return "Windows PC"

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            supports_remote_input=True,
            supports_screen_sharing=True,
            supports_file_transfer=True,
            supports_notifications=True,
            supports_media_control=True,
            supports_lock_screen=True,
            requires_confirmation_for_input=True,
            requires_confirmation_for_stream=True,
            max_file_size_mb=1000
        )

    def get_pairing_code(self, device_id: str) -> str:
        return f"WIN-{device_id[-6:]}"

    def validate_pairing(self, device_id: str, code: str) -> bool:
        return len(code) >= 4 and code.startswith("WIN-")

    async def on_device_connected(self, device_id: str) -> Dict[str, Any]:
        return {
            "type": "windows_pc",
            "device_name": "Windows PC",
            "capabilities": ["input", "file_transfer", "notifications", "screen", "lock"],
            "status": "connected"
        }

    async def on_device_disconnected(self, device_id: str):
        pass


class LinuxPCAdapter(DeviceAdapter):
    """Adapter for Linux PCs"""

    @property
    def device_type_name(self) -> str:
        return "Linux PC"

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            supports_remote_input=True,
            supports_screen_sharing=True,
            supports_file_transfer=True,
            supports_notifications=True,
            supports_media_control=True,
            supports_lock_screen=True,
            requires_confirmation_for_input=True,
            requires_confirmation_for_stream=True,
            max_file_size_mb=2000
        )

    def get_pairing_code(self, device_id: str) -> str:
        return f"LINUX-{device_id[-6:]}"

    def validate_pairing(self, device_id: str, code: str) -> bool:
        return len(code) >= 5 and code.startswith("LINUX-")

    async def on_device_connected(self, device_id: str) -> Dict[str, Any]:
        return {
            "type": "linux_pc",
            "device_name": "Linux PC",
            "capabilities": ["input", "file_transfer", "notifications", "screen", "lock"],
            "status": "connected"
        }

    async def on_device_disconnected(self, device_id: str):
        pass


# Adapter registry
_ADAPTERS: Dict[str, DeviceAdapter] = {}


def register_adapter(adapter: DeviceAdapter):
    """Register a device adapter"""
    _ADAPTERS[adapter.device_type_name.lower()] = adapter


def get_adapter(device_type: str) -> Optional[DeviceAdapter]:
    """Get adapter for device type"""
    return _ADAPTERS.get(device_type.lower())


def get_all_adapters() -> List[DeviceAdapter]:
    """Get all registered adapters"""
    return list(_ADAPTERS.values())


# Register default adapters
register_adapter(AndroidPhoneAdapter())
register_adapter(AndroidTVAdapter())
register_adapter(WindowsPCAdapter())
register_adapter(LinuxPCAdapter())