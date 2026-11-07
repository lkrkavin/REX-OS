#!/usr/bin/env python3
"""
REX CONNECT - Pairing Manager

Handles device pairing with QR code or pairing code authentication.
Implements secure pairing with confirmation on both devices.
"""

import asyncio
import hashlib
import hmac
import secrets
import time
try:
    import qrcode
except ImportError:  # QR image generation is optional; numeric pairing remains available.
    qrcode = None
import io
import base64
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
import threading
from io import BytesIO

from .device_registry import DeviceRegistry, DeviceInfo, DeviceType, ConnectionStatus, get_device_registry


class PairingMethod(Enum):
    """Pairing authentication methods"""
    QR_CODE = "qr_code"
    PAIRING_CODE = "pairing_code"
    AUTO = "auto"  # For trusted networks/devices


@dataclass
class PairingSession:
    """Active pairing session"""
    session_id: str
    device_type: DeviceType
    device_name: str
    method: PairingMethod
    pairing_code: str
    qr_data: str
    created_at: float
    expires_at: float
    confirmed: bool = False
    failed_attempts: int = 0
    device_info: Optional[Dict[str, Any]] = None
    callback: Optional[Callable] = None


@dataclass
class PairingResult:
    """Result of a pairing operation"""
    success: bool
    device_id: Optional[str] = None
    message: str = ""
    session_id: Optional[str] = None
    error: Optional[str] = None
    auth_token: Optional[str] = field(default=None, repr=False)  # Returned once to the newly paired device.


class PairingManager:
    """
    Manages device pairing with secure authentication.
    Supports QR code and numeric pairing code methods.
    """

    PAIRING_TIMEOUT = 300  # 5 minutes
    PAIRING_CODE_LENGTH = 6
    MAX_CODE_ATTEMPTS = 5
    SESSION_CLEANUP_INTERVAL = 60

    def __init__(self, registry: DeviceRegistry = None):
        self._registry = registry or get_device_registry()
        self._active_sessions: Dict[str, PairingSession] = {}
        self._lock = threading.RLock()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the pairing manager"""
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_sessions())

    async def stop(self):
        """Stop the pairing manager"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_sessions(self):
        """Periodically clean up expired sessions"""
        while self._running:
            try:
                await asyncio.sleep(self.SESSION_CLEANUP_INTERVAL)
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Pairing cleanup error: {e}")

    async def _cleanup_expired(self):
        """Remove expired pairing sessions"""
        now = time.time()
        with self._lock:
            expired = [sid for sid, s in self._active_sessions.items() if s.expires_at < now]
            for sid in expired:
                del self._active_sessions[sid]

    def _generate_pairing_code(self) -> str:
        """Generate a 6-digit pairing code"""
        return ''.join(secrets.choice('0123456789') for _ in range(self.PAIRING_CODE_LENGTH))

    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return f"pair_{secrets.token_hex(8)}"

    def _create_qr_data(self, session_id: str, pairing_code: str, device_type: DeviceType) -> str:
        """Create QR code data payload"""
        import json
        payload = {
            "type": "rex_connect_pairing",
            "version": 1,
            "session_id": session_id,
            "pairing_code": pairing_code,
            "device_type": device_type.value,
            "timestamp": time.time()
        }
        return json.dumps(payload)

    def generate_qr_code(self, qr_data: str) -> str:
        """Generate QR code as base64 PNG"""
        if qrcode is None:
            return ""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"QR code generation failed: {e}")
            return ""

    async def initiate_pairing(
        self,
        device_type: DeviceType,
        device_name: str,
        method: PairingMethod = PairingMethod.QR_CODE,
        device_info: Dict[str, Any] = None
    ) -> PairingResult:
        """
        Initiate a new pairing session.
        Returns pairing code and QR code for user confirmation.
        """
        session_id = self._generate_session_id()
        pairing_code = self._generate_pairing_code()
        qr_data = self._create_qr_data(session_id, pairing_code, device_type)

        session = PairingSession(
            session_id=session_id,
            device_type=device_type,
            device_name=device_name,
            method=method,
            pairing_code=pairing_code,
            qr_data=qr_data,
            created_at=time.time(),
            expires_at=time.time() + self.PAIRING_TIMEOUT,
            device_info=device_info or {}
        )

        with self._lock:
            self._active_sessions[session_id] = session

        qr_code_b64 = self.generate_qr_code(qr_data)

        return PairingResult(
            success=True,
            session_id=session_id,
            message="Pairing initiated. Please confirm on the other device.",
            device_id=None
        )

    async def confirm_pairing(
        self,
        session_id: str,
        pairing_code: str,
        device_info: Dict[str, Any] = None
    ) -> PairingResult:
        """
        Confirm a pairing session with the provided pairing code.
        Called by the device being paired.
        """
        with self._lock:
            session = self._active_sessions.get(session_id)

        if not session:
            return PairingResult(
                success=False,
                message="Invalid or expired pairing session",
                error="SESSION_NOT_FOUND"
            )

        if session.expires_at < time.time():
            with self._lock:
                del self._active_sessions[session_id]
            return PairingResult(
                success=False,
                message="Pairing session has expired",
                error="SESSION_EXPIRED"
            )

        if not session.confirmed:
            return PairingResult(
                success=False,
                message="Confirm this pairing request on the REX computer first.",
                error="LOCAL_CONFIRMATION_REQUIRED"
            )

        if not isinstance(pairing_code, str) or not hmac.compare_digest(session.pairing_code, pairing_code):
            with self._lock:
                session.failed_attempts += 1
                exhausted = session.failed_attempts >= self.MAX_CODE_ATTEMPTS
                if exhausted:
                    self._active_sessions.pop(session_id, None)
            return PairingResult(
                success=False,
                message="Pairing code attempt limit reached; start a new pairing session." if exhausted else "Invalid pairing code",
                error="TOO_MANY_ATTEMPTS" if exhausted else "INVALID_CODE"
            )

        # Create device entry
        device_id = self._registry.generate_device_id()
        auth_token = secrets.token_urlsafe(32)

        device = DeviceInfo(
            device_id=device_id,
            name=session.device_name,
            device_type=session.device_type,
            connection_status=ConnectionStatus.ONLINE,
            capabilities=device_info.get('capabilities', []) if device_info else [],
            auth_token=auth_token,
            token_expires=time.time() + 86400 * 30,  # 30 days
            is_trusted=True,
            metadata=device_info or {}
        )

        # Add to registry, then grant only the least-privilege default permissions.
        self._registry.add_device(device)
        from .security import PermissionLevel, get_security_manager
        if not get_security_manager().grant_device_permissions(device_id, PermissionLevel.READ_ONLY):
            self._registry.remove_device(device_id)
            return PairingResult(
                success=False,
                message="Could not initialize device security permissions",
                error="SECURITY_GRANT_FAILED"
            )

        # Mark session as confirmed
        with self._lock:
            session.confirmed = True
            session.device_info = device_info
            del self._active_sessions[session_id]

        return PairingResult(
            success=True,
            device_id=device_id,
            message=f"Successfully paired with {session.device_name}",
            session_id=session_id,
            auth_token=auth_token
        )

    async def confirm_pairing_local(self, session_id: str) -> PairingResult:
        """
        Confirm pairing locally (user clicked "Accept" on this device).
        """
        with self._lock:
            session = self._active_sessions.get(session_id)

        if not session:
            return PairingResult(
                success=False,
                message="Invalid or expired pairing session",
                error="SESSION_NOT_FOUND"
            )

        if session.expires_at < time.time():
            with self._lock:
                del self._active_sessions[session_id]
            return PairingResult(
                success=False,
                message="Pairing session has expired",
                error="SESSION_EXPIRED"
            )

        # The local confirmation means we wait for the remote device to provide the code
        # This is just a local acknowledgment - the actual pairing completes when
        # confirm_pairing is called with the correct code
        session.confirmed = True
        return PairingResult(
            success=True,
            session_id=session_id,
            message="Waiting for remote device to enter pairing code..."
        )

    def get_session(self, session_id: str) -> Optional[PairingSession]:
        """Get active pairing session"""
        with self._lock:
            return self._active_sessions.get(session_id)

    def get_qr_code(self, session_id: str) -> Optional[str]:
        """Get QR code for a session as base64 PNG"""
        with self._lock:
            session = self._active_sessions.get(session_id)
        if session:
            return self.generate_qr_code(session.qr_data)
        return None

    def cancel_pairing(self, session_id: str) -> bool:
        """Cancel an active pairing session"""
        with self._lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
                return True
        return False

    def get_active_sessions(self) -> List[PairingSession]:
        """Get all active pairing sessions"""
        with self._lock:
            return list(self._active_sessions.values())

    def verify_pairing_code(self, session_id: str, code: str) -> bool:
        """Verify a pairing code without completing pairing"""
        with self._lock:
            session = self._active_sessions.get(session_id)
        if not session:
            return False
        return session.pairing_code == code


# Global pairing manager instance
_global_pairing_manager: Optional[PairingManager] = None


def get_pairing_manager(registry: DeviceRegistry = None) -> PairingManager:
    """Get global pairing manager instance"""
    global _global_pairing_manager
    if _global_pairing_manager is None:
        _global_pairing_manager = PairingManager(registry)
    return _global_pairing_manager