#!/usr/bin/env python3
"""
REX CONNECT - Device Integration System

Provides secure device pairing, remote control, screen sharing,
file transfer, and notification integration for REX OS.
"""

from .device_registry import DeviceRegistry, DeviceInfo, DeviceType, ConnectionStatus
from .pairing import PairingManager, PairingResult, PairingMethod
from .connection import ConnectionManager, Connection, ConnectionType
from .remote_input import RemoteInputHandler, InputEvent, InputType
from .screen_stream import ScreenStreamer, StreamConfig
from .file_transfer import FileTransferManager, TransferInfo, TransferStatus
from .notification import NotificationManager, Notification, NotificationPriority
from .security import SecurityManager, Permission, PermissionLevel

__all__ = [
    "DeviceRegistry",
    "DeviceInfo",
    "DeviceType",
    "ConnectionStatus",
    "PairingManager",
    "PairingResult",
    "PairingMethod",
    "ConnectionManager",
    "Connection",
    "ConnectionType",
    "RemoteInputHandler",
    "InputEvent",
    "InputType",
    "ScreenStreamer",
    "StreamConfig",
    "FileTransferManager",
    "TransferInfo",
    "TransferStatus",
    "NotificationManager",
    "Notification",
    "NotificationPriority",
    "SecurityManager",
    "Permission",
    "PermissionLevel",
]