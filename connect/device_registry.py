#!/usr/bin/env python3
"""
REX CONNECT - Device Registry

Stores paired-device metadata safely. Long-lived device tokens are hashed at
rest; raw tokens are accepted only during pairing and are never serialized.
"""

import asyncio
import hashlib
import hmac
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from pathlib import Path
import threading


class DeviceType(Enum):
    ANDROID_PHONE = "android_phone"
    ANDROID_TV = "android_tv"
    WINDOWS_PC = "windows_pc"
    LINUX_PC = "linux_pc"
    IOS_DEVICE = "ios_device"
    SMART_TV = "smart_tv"
    UNKNOWN = "unknown"


class ConnectionStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    PAIRING = "pairing"
    ERROR = "error"


@dataclass
class DeviceInfo:
    device_id: str
    name: str
    device_type: DeviceType
    connection_status: ConnectionStatus = ConnectionStatus.OFFLINE
    capabilities: List[str] = field(default_factory=list)
    last_connected: Optional[float] = None
    last_seen_ip: Optional[str] = None
    paired_at: float = field(default_factory=time.time)
    # auth_token is transient input for backwards-compatible pairing only.
    # It is cleared before any registry write.
    auth_token: Optional[str] = field(default=None, repr=False, compare=False)
    token_expires: Optional[float] = None
    is_trusted: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    auth_token_hash: Optional[str] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        raw_token = data.pop("auth_token", None)
        token_hash = data.get("auth_token_hash")
        if not token_hash and raw_token:
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        data["auth_token_hash"] = token_hash
        data["device_type"] = self.device_type.value
        data["connection_status"] = self.connection_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceInfo":
        # Migrate legacy registry entries that stored raw tokens.
        data = dict(data)
        raw_token = data.pop("auth_token", None)
        if raw_token and not data.get("auth_token_hash"):
            data["auth_token_hash"] = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        data["auth_token"] = None
        data["device_type"] = DeviceType(data["device_type"])
        data["connection_status"] = ConnectionStatus(data["connection_status"])
        return cls(**data)


class DeviceRegistry:
    """Thread-safe registry with atomic, owner-only persistence."""

    def __init__(self, storage_path: str = "/var/lib/rex/connect/devices.json"):
        self._storage_path = Path(storage_path)
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[str, DeviceInfo], None]] = []
        self._load()

    def _load(self):
        if not self._storage_path.exists():
            return
        try:
            with open(self._storage_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            migrated = False
            for device_data in data.get("devices", []):
                if "auth_token" in device_data and device_data.get("auth_token"):
                    migrated = True
                device = DeviceInfo.from_dict(device_data)
                self._devices[device.device_id] = device
            # Rewrite legacy plaintext-token records immediately.
            if migrated:
                self._save()
            else:
                try:
                    os.chmod(self._storage_path, 0o600)
                except OSError:
                    pass
        except Exception as exc:
            print(f"Failed to load device registry: {exc}")

    @staticmethod
    def _hash_transient_token(device: DeviceInfo):
        if device.auth_token:
            device.auth_token_hash = hashlib.sha256(device.auth_token.encode("utf-8")).hexdigest()
            device.auth_token = None

    def _save(self):
        self._storage_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        data = {
            "version": 2,
            "devices": [device.to_dict() for device in self._devices.values()]
        }
        fd, temp_path = tempfile.mkstemp(prefix=".devices-", suffix=".tmp", dir=str(self._storage_path.parent))
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self._storage_path)
            try:
                os.chmod(self._storage_path, 0o600)
            except OSError:
                pass
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def register_callback(self, callback: Callable[[str, DeviceInfo], None]):
        with self._lock:
            self._callbacks.append(callback)

    def _notify_change(self, device_id: str, device: Optional[DeviceInfo]):
        for callback in self._callbacks:
            try:
                callback(device_id, device)
            except Exception as exc:
                print(f"Callback error: {exc}")

    def add_device(self, device: DeviceInfo) -> bool:
        with self._lock:
            self._hash_transient_token(device)
            self._devices[device.device_id] = device
            self._save()
            self._notify_change(device.device_id, device)
            return True

    def remove_device(self, device_id: str) -> bool:
        with self._lock:
            if device_id not in self._devices:
                return False
            del self._devices[device_id]
            self._save()
            self._notify_change(device_id, None)
        from .security import get_security_manager
        get_security_manager().revoke_device_permissions(device_id)
        return True

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        with self._lock:
            return self._devices.get(device_id)

    def get_all_devices(self) -> List[DeviceInfo]:
        with self._lock:
            return list(self._devices.values())

    def get_devices_by_type(self, device_type: DeviceType) -> List[DeviceInfo]:
        with self._lock:
            return [device for device in self._devices.values() if device.device_type == device_type]

    def get_online_devices(self) -> List[DeviceInfo]:
        with self._lock:
            return [device for device in self._devices.values()
                    if device.connection_status == ConnectionStatus.ONLINE]

    def update_status(self, device_id: str, status: ConnectionStatus, ip: str = None) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            device.connection_status = status
            if status == ConnectionStatus.ONLINE:
                device.last_connected = time.time()
            if ip:
                device.last_seen_ip = ip
            self._save()
            self._notify_change(device_id, device)
            return True

    def update_token(self, device_id: str, token: str, expires: float = None) -> bool:
        if not isinstance(token, str) or len(token) < 32:
            return False
        with self._lock:
            device = self._devices.get(device_id)
            if not device or not device.is_trusted:
                return False
            device.auth_token = None
            device.auth_token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            device.token_expires = expires if expires is not None else time.time() + 86400 * 30
            self._save()
            return True

    def validate_token(self, device_id: str, token: str) -> bool:
        if not isinstance(token, str) or not token:
            return False
        with self._lock:
            device = self._devices.get(device_id)
            if not device or not device.is_trusted or not device.auth_token_hash:
                return False
            if device.token_expires is None or device.token_expires <= time.time():
                return False
            candidate = hashlib.sha256(token.encode("utf-8")).hexdigest()
            return hmac.compare_digest(device.auth_token_hash, candidate)

    def revoke_device(self, device_id: str) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            device.is_trusted = False
            device.auth_token = None
            device.auth_token_hash = None
            device.token_expires = None
            device.connection_status = ConnectionStatus.OFFLINE
            self._save()
            self._notify_change(device_id, device)
        from .security import get_security_manager
        get_security_manager().revoke_device_permissions(device_id)
        return True

    def trust_device(self, device_id: str) -> bool:
        with self._lock:
            device = self._devices.get(device_id)
            if not device:
                return False
            device.is_trusted = True
            self._save()
            self._notify_change(device_id, device)
            return True

    def generate_device_id(self) -> str:
        return f"dev_{uuid.uuid4().hex[:12]}"

    def clear_all(self):
        with self._lock:
            self._devices.clear()
            self._save()


_global_registry: Optional[DeviceRegistry] = None


def get_device_registry(storage_path: str = None) -> DeviceRegistry:
    global _global_registry
    if _global_registry is None:
        path = storage_path or os.environ.get("REX_CONNECT_DEVICES_PATH", "/var/lib/rex/connect/devices.json")
        _global_registry = DeviceRegistry(path)
    return _global_registry
