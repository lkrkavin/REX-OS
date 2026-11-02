#!/usr/bin/env python3
"""
REX CONNECT - Device Registry

Manages paired devices, their capabilities, and connection state.
"""

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from pathlib import Path
import threading


class DeviceType(Enum):
    """Supported device types"""
    ANDROID_PHONE = "android_phone"
    ANDROID_TV = "android_tv"
    WINDOWS_PC = "windows_pc"
    LINUX_PC = "linux_pc"
    IOS_DEVICE = "ios_device"
    SMART_TV = "smart_tv"
    UNKNOWN = "unknown"


class ConnectionStatus(Enum):
    """Device connection status"""
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    PAIRING = "pairing"
    ERROR = "error"


@dataclass
class DeviceInfo:
    """Information about a paired device"""
    device_id: str
    name: str
    device_type: DeviceType
    connection_status: ConnectionStatus = ConnectionStatus.OFFLINE
    capabilities: List[str] = field(default_factory=list)
    last_connected: Optional[float] = None
    last_seen_ip: Optional[str] = None
    paired_at: float = field(default_factory=time.time)
    auth_token: Optional[str] = None
    token_expires: Optional[float] = None
    is_trusted: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['device_type'] = self.device_type.value
        data['connection_status'] = self.connection_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceInfo':
        """Create from dictionary"""
        data['device_type'] = DeviceType(data['device_type'])
        data['connection_status'] = ConnectionStatus(data['connection_status'])
        return cls(**data)


class DeviceRegistry:
    """
    Registry for managing paired devices.
    Thread-safe operations for device management.
    """

    def __init__(self, storage_path: str = "/var/lib/rex/connect/devices.json"):
        self._storage_path = Path(storage_path)
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[str, DeviceInfo], None]] = []
        self._load()

    def _load(self):
        """Load devices from storage"""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, 'r') as f:
                    data = json.load(f)
                for device_data in data.get('devices', []):
                    device = DeviceInfo.from_dict(device_data)
                    self._devices[device.device_id] = device
            except Exception as e:
                print(f"Failed to load device registry: {e}")

    def _save(self):
        """Save devices to storage"""
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'version': 1,
                'devices': [d.to_dict() for d in self._devices.values()]
            }
            with open(self._storage_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save device registry: {e}")

    def register_callback(self, callback: Callable[[str, DeviceInfo], None]):
        """Register a callback for device changes"""
        with self._lock:
            self._callbacks.append(callback)

    def _notify_change(self, device_id: str, device: DeviceInfo):
        """Notify callbacks of device change"""
        for callback in self._callbacks:
            try:
                callback(device_id, device)
            except Exception as e:
                print(f"Callback error: {e}")

    def add_device(self, device: DeviceInfo) -> bool:
        """Add or update a paired device"""
        with self._lock:
            self._devices[device.device_id] = device
            self._save()
            self._notify_change(device.device_id, device)
            return True

    def remove_device(self, device_id: str) -> bool:
        """Remove a paired device"""
        with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                self._save()
                self._notify_change(device_id, None)
                return True
            return False

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get device by ID"""
        with self._lock:
            return self._devices.get(device_id)

    def get_all_devices(self) -> List[DeviceInfo]:
        """Get all paired devices"""
        with self._lock:
            return list(self._devices.values())

    def get_devices_by_type(self, device_type: DeviceType) -> List[DeviceInfo]:
        """Get devices filtered by type"""
        with self._lock:
            return [d for d in self._devices.values() if d.device_type == device_type]

    def get_online_devices(self) -> List[DeviceInfo]:
        """Get currently online devices"""
        with self._lock:
            return [d for d in self._devices.values() if d.connection_status == ConnectionStatus.ONLINE]

    def update_status(self, device_id: str, status: ConnectionStatus, ip: str = None) -> bool:
        """Update device connection status"""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                device.connection_status = status
                if status == ConnectionStatus.ONLINE:
                    device.last_connected = time.time()
                if ip:
                    device.last_seen_ip = ip
                self._save()
                self._notify_change(device_id, device)
                return True
            return False

    def update_token(self, device_id: str, token: str, expires: float = None) -> bool:
        """Update device authentication token"""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                device.auth_token = token
                if expires:
                    device.token_expires = expires
                else:
                    device.token_expires = time.time() + 86400 * 30  # 30 days default
                self._save()
                return True
            return False

    def validate_token(self, device_id: str, token: str) -> bool:
        """Validate device authentication token"""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                if device.auth_token == token:
                    if device.token_expires and device.token_expires > time.time():
                        return True
            return False

    def revoke_device(self, device_id: str) -> bool:
        """Revoke device trust (mark as untrusted)"""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                device.is_trusted = False
                device.auth_token = None
                device.token_expires = None
                self._save()
                self._notify_change(device_id, device)
                return True
            return False

    def trust_device(self, device_id: str) -> bool:
        """Mark device as trusted"""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                device.is_trusted = True
                self._save()
                self._notify_change(device_id, device)
                return True
            return False

    def generate_device_id(self) -> str:
        """Generate a new unique device ID"""
        return f"dev_{uuid.uuid4().hex[:12]}"

    def clear_all(self):
        """Clear all devices (for testing)"""
        with self._lock:
            self._devices.clear()
            self._save()


# Global registry instance
_global_registry: Optional[DeviceRegistry] = None


def get_device_registry(storage_path: str = None) -> DeviceRegistry:
    """Get global device registry instance"""
    global _global_registry
    if _global_registry is None:
        path = storage_path or os.environ.get("REX_CONNECT_DEVICES_PATH", "/var/lib/rex/connect/devices.json")
        _global_registry = DeviceRegistry(path)
    return _global_registry