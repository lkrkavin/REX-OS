#!/usr/bin/env python3
"""
REX CONNECT - Security Manager

Handles permission checking, authorization levels, and token verification.
Fails closed on missing or invalid permissions.
"""

import time
import secrets
import hashlib
from enum import Enum
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, field


class PermissionLevel(Enum):
    """Permission access levels"""
    NONE = 0
    READ_ONLY = 1      # Read status, notifications
    CONTROL = 2        # Remote mouse/keyboard, app launch
    FULL_ACCESS = 3    # File transfer, screen sharing, system actions
    ADMIN = 4          # Device pairing, revocation, settings


class Permission(Enum):
    """Specific permission types"""
    REMOTE_MOUSE = "remote_mouse"
    REMOTE_KEYBOARD = "remote_keyboard"
    MEDIA_CONTROL = "media_control"
    SCREEN_STREAMING = "screen_streaming"
    FILE_TRANSFER = "file_transfer"
    NOTIFICATIONS = "notifications"
    SYSTEM_STATUS = "system_status"
    PROCESS_MONITOR = "process_monitor"
    APP_LAUNCH = "app_launch"
    LOCK_SCREEN = "lock_screen"
    PAIRING = "pairing"


@dataclass
class AccessToken:
    """Session access token"""
    token_id: str
    device_id: str
    created_at: float
    expires_at: float
    permission_level: PermissionLevel
    permissions: Set[Permission] = field(default_factory=set)
    is_revoked: bool = False

    def is_valid(self) -> bool:
        """Check if token is valid and not expired"""
        if self.is_revoked:
            return False
        return time.time() < self.expires_at


class SecurityManager:
    """
    Manages security permissions, token validation, and access control.
    Fails closed: Denies access by default unless explicitly granted.
    """

    DEFAULT_TOKEN_LIFETIME = 86400  # 24 hours for session tokens

    def __init__(self):
        self._tokens: Dict[str, AccessToken] = {}
        self._device_permissions: Dict[str, Set[Permission]] = {}
        self._device_levels: Dict[str, PermissionLevel] = {}

    def grant_device_permissions(
        self,
        device_id: str,
        level: PermissionLevel,
        permissions: Optional[Set[Permission]] = None
    ):
        """Grant permissions to a device"""
        self._device_levels[device_id] = level
        if permissions is not None:
            self._device_permissions[device_id] = permissions
        else:
            # Default permissions for level
            self._device_permissions[device_id] = self._get_default_permissions_for_level(level)

    def _get_default_permissions_for_level(self, level: PermissionLevel) -> Set[Permission]:
        """Get default permission set for a level"""
        if level == PermissionLevel.NONE:
            return set()
        elif level == PermissionLevel.READ_ONLY:
            return {Permission.SYSTEM_STATUS, Permission.NOTIFICATIONS, Permission.PROCESS_MONITOR}
        elif level == PermissionLevel.CONTROL:
            return {
                Permission.SYSTEM_STATUS, Permission.NOTIFICATIONS, Permission.PROCESS_MONITOR,
                Permission.REMOTE_MOUSE, Permission.REMOTE_KEYBOARD, Permission.MEDIA_CONTROL,
                Permission.APP_LAUNCH, Permission.LOCK_SCREEN
            }
        elif level == PermissionLevel.FULL_ACCESS:
            return {
                Permission.SYSTEM_STATUS, Permission.NOTIFICATIONS, Permission.PROCESS_MONITOR,
                Permission.REMOTE_MOUSE, Permission.REMOTE_KEYBOARD, Permission.MEDIA_CONTROL,
                Permission.APP_LAUNCH, Permission.LOCK_SCREEN,
                Permission.SCREEN_STREAMING, Permission.FILE_TRANSFER
            }
        elif level == PermissionLevel.ADMIN:
            return set(Permission)  # All permissions
        return set()

    def revoke_device_permissions(self, device_id: str):
        """Revoke all permissions for a device"""
        self._device_levels[device_id] = PermissionLevel.NONE
        self._device_permissions[device_id] = set()

        # Revoke all tokens for this device
        for token in self._tokens.values():
            if token.device_id == device_id:
                token.is_revoked = True

    def create_session_token(
        self,
        device_id: str,
        lifetime: float = DEFAULT_TOKEN_LIFETIME
    ) -> AccessToken:
        """Create a new session access token for a device"""
        token_id = secrets.token_urlsafe(32)
        level = self._device_levels.get(device_id, PermissionLevel.NONE)
        perms = self._device_permissions.get(device_id, set())

        token = AccessToken(
            token_id=token_id,
            device_id=device_id,
            created_at=time.time(),
            expires_at=time.time() + lifetime,
            permission_level=level,
            permissions=perms
        )

        self._tokens[token_id] = token
        return token

    def check_permission(
        self,
        device_id: str,
        permission: Permission,
        token_id: Optional[str] = None
    ) -> bool:
        """
        Check if device has a specific permission.
        Fails closed: returns False if permission is missing, invalid, or error occurs.
        """
        try:
            # Validate token if provided
            if token_id:
                token = self._tokens.get(token_id)
                if not token or not token.is_valid():
                    return False
                if token.device_id != device_id:
                    return False
                return permission in token.permissions

            # Check device direct permissions
            device_level = self._device_levels.get(device_id, PermissionLevel.NONE)
            if device_level == PermissionLevel.NONE:
                return False

            device_perms = self._device_permissions.get(device_id, set())
            return permission in device_perms

        except Exception:
            # Fail closed on any exception
            return False

    def revoke_token(self, token_id: str) -> bool:
        """Revoke a specific session token"""
        token = self._tokens.get(token_id)
        if token:
            token.is_revoked = True
            return True
        return False

    def validate_token(self, token_id: str) -> Optional[AccessToken]:
        """Validate and return token if valid"""
        token = self._tokens.get(token_id)
        if token and token.is_valid():
            return token
        return None

    def sanitize_path(self, path_str: str) -> Optional[str]:
        """
        Sanitize and validate a path to prevent path traversal attacks.
        Returns cleaned path or None if unsafe.
        """
        import os
        from pathlib import Path

        try:
            # Normalization
            normalized = os.path.normpath(path_str)

            # Check for parent directory navigation attempts
            if ".." in normalized.split(os.sep):
                return None

            # Convert to absolute
            abs_path = Path(normalized).resolve()

            # Ensure it stays within allowed root (e.g. user home or downloads)
            allowed_roots = [
                Path.home().resolve(),
                Path("/var/lib/rex/connect/transfers").resolve() if os.name != 'nt' else Path("C:/rex/transfers").resolve()
            ]

            is_safe = False
            for root in allowed_roots:
                try:
                    abs_path.relative_to(root)
                    is_safe = True
                    break
                except ValueError:
                    continue

            if is_safe:
                return str(abs_path)
            return None

        except Exception:
            return None


# Global security manager instance
_global_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """Get global security manager instance"""
    global _global_security_manager
    if _global_security_manager is None:
        _global_security_manager = SecurityManager()
    return _global_security_manager