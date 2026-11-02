#!/usr/bin/env python3
"""
REX CONNECT - Connection Manager

Manages device connections using secure sockets.
Supports WebSocket connections for real-time control.
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
import threading
import hashlib
import hmac


class ConnectionType(Enum):
    """Connection transport types"""
    WEBSOCKET = "websocket"
    TCP = "tcp"
    TCP_TLS = "tcp_tls"
    LOCAL = "local"  # For testing


@dataclass
class Connection:
    """Active device connection"""
    connection_id: str
    device_id: str
    connection_type: ConnectionType
    connected_at: float
    last_activity: float
    is_authenticated: bool = False
    token_id: Optional[str] = None
    remote_address: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class ConnectionStatus:
    """Status of a connection"""
    connected: bool
    latency_ms: Optional[float] = None
    last_message: Optional[float] = None
    active_sessions: List[str] = field(default_factory=list)


class ConnectionManager:
    """
    Manages device connections with authentication and lifecycle management.
    Uses authenticated connections only - no unauthenticated public ports.
    """

    HEARTBEAT_INTERVAL = 30
    MAX_INACTIVITY = 300  # 5 minutes

    def __init__(self):
        self._connections: Dict[str, Connection] = {}
        self._device_connections: Dict[str, List[str]] = {}  # device_id -> [connection_ids]
        self._lock = threading.RLock()

    def add_connection(
        self,
        connection_id: str,
        device_id: str,
        connection_type: ConnectionType,
        remote_address: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Connection:
        """Add a new connection"""
        now = time.time()
        conn = Connection(
            connection_id=connection_id,
            device_id=device_id,
            connection_type=connection_type,
            connected_at=now,
            last_activity=now,
            remote_address=remote_address,
            session_id=session_id
        )

        with self._lock:
            self._connections[connection_id] = conn
            if device_id not in self._device_connections:
                self._device_connections[device_id] = []
            self._device_connections[device_id].append(connection_id)

        return conn

    def remove_connection(self, connection_id: str) -> bool:
        """Remove a connection"""
        with self._lock:
            if connection_id in self._connections:
                conn = self._connections[connection_id]
                device_id = conn.device_id
                del self._connections[connection_id]
                if device_id in self._device_connections:
                    self._device_connections[device_id] = [
                        c for c in self._device_connections[device_id] if c != connection_id
                    ]
                return True
            return False

    def get_connection(self, connection_id: str) -> Optional[Connection]:
        """Get connection by ID"""
        with self._lock:
            return self._connections.get(connection_id)

    def get_device_connections(self, device_id: str) -> List[Connection]:
        """Get all connections for a device"""
        with self._lock:
            if device_id not in self._device_connections:
                return []
            return [
                self._connections[cid]
                for cid in self._device_connections[device_id]
                if cid in self._connections
            ]

    def get_all_connections(self) -> List[Connection]:
        """Get all active connections"""
        with self._lock:
            return list(self._connections.values())

    def authenticate_connection(
        self,
        connection_id: str,
        token_id: str,
        security_manager: 'SecurityManager'
    ) -> bool:
        """
        Authenticate a connection using a session token.
        Returns True if authentication successful, False if denied (fail closed).
        """
        if not security_manager:
            return False

        token = security_manager.validate_token(token_id)
        if not token or token.device_id != self._get_device_id(connection_id):
            return False

        with self._lock:
            if connection_id in self._connections:
                conn = self._connections[connection_id]
                conn.is_authenticated = True
                conn.token_id = token_id
                conn.last_activity = time.time()
                return True

        return False

    def _get_device_id(self, connection_id: str) -> Optional[str]:
        """Get device ID for a connection"""
        with self._lock:
            conn = self._connections.get(connection_id)
            return conn.device_id if conn else None

    def update_activity(self, connection_id: str):
        """Update last activity timestamp for a connection"""
        with self._lock:
            if connection_id in self._connections:
                self._connections[connection_id].last_activity = time.time()

    def get_connection_status(self, device_id: str) -> ConnectionStatus:
        """Get connection status for a device"""
        connections = self.get_device_connections(device_id)

        if not connections:
            return ConnectionStatus(connected=False)

        # Check for authenticated connections
        auth_connections = [c for c in connections if c.is_authenticated]
        if not auth_connections:
            return ConnectionStatus(connected=False)

        # Get latest activity
        latest_activity = max(c.last_activity for c in auth_connections)
        latency = time.time() - latest_activity

        return ConnectionStatus(
            connected=True,
            latency_ms=latency * 1000,
            last_message=latest_activity,
            active_sessions=[c.session_id for c in auth_connections if c.session_id]
        )

    def is_connection_active(self, connection_id: str, timeout: float = None) -> bool:
        """Check if a connection is still active"""
        timeout = timeout or self.MAX_INACTIVITY
        with self._lock:
            conn = self._connections.get(connection_id)
            if not conn:
                return False
            if not conn.is_authenticated:
                return False
            return (time.time() - conn.last_activity) < timeout

    def close_connection(self, connection_id: str):
        """Close a connection"""
        self.remove_connection(connection_id)

    def close_all_device_connections(self, device_id: str):
        """Close all connections for a device"""
        with self._lock:
            if device_id in self._device_connections:
                for conn_id in self._device_connections[device_id]:
                    if conn_id in self._connections:
                        del self._connections[conn_id]
                del self._device_connections[device_id]

    def generate_handshake_token(self, device_id: str, secret: str) -> str:
        """Generate a handshake token for initial connection"""
        timestamp = str(int(time.time()))
        message = f"{device_id}:{timestamp}"
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{device_id}:{timestamp}:{signature}"

    def verify_handshake_token(self, token: str, secret: str, max_age: float = 60) -> Optional[str]:
        """Verify a handshake token and return device ID if valid"""
        try:
            parts = token.split(':')
            if len(parts) != 3:
                return None

            device_id, timestamp, signature = parts
            token_time = float(timestamp)

            if time.time() - token_time > max_age:
                return None

            message = f"{device_id}:{timestamp}"
            expected_sig = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(signature, expected_sig):
                return device_id
            return None

        except Exception:
            return None


# Global connection manager instance
_global_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get global connection manager instance"""
    global _global_connection_manager
    if _global_connection_manager is None:
        _global_connection_manager = ConnectionManager()
    return _global_connection_manager