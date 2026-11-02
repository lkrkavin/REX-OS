#!/usr/bin/env python3
"""
REX CONNECT - Notification Manager

Handles notification forwarding between REX OS and connected devices.
Requires explicit user permission for each notification forwarded.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
import threading


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Notification:
    """A notification to be forwarded"""
    notification_id: str
    device_id: str
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    icon: Optional[str] = None  # base64 icon data
    actions: List[str] = field(default_factory=list)  # Action buttons
    is_read: bool = False
    requires_confirmation: bool = False


class NotificationManager:
    """
    Manages notification forwarding between devices.
    - Requires user permission to enable forwarding
    - Does not collect content without authorization
    - Allows users to disable notification forwarding
    """

    def __init__(self):
        self._notifications: Dict[str, Notification] = {}
        self._device_settings: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[str, Notification], None]] = []

    def register_callback(self, callback: Callable[[str, Notification], None]):
        """Register callback for notification changes"""
        with self._lock:
            self._callbacks.append(callback)

    def set_device_notification_enabled(self, device_id: str, enabled: bool):
        """Enable or disable notifications for a device"""
        with self._lock:
            if device_id not in self._device_settings:
                self._device_settings[device_id] = {"notifications_enabled": False}
            self._device_settings[device_id]["notifications_enabled"] = enabled

    def is_device_notifications_enabled(self, device_id: str) -> bool:
        """Check if notifications are enabled for a device"""
        with self._lock:
            if device_id not in self._device_settings:
                return False
            return self._device_settings[device_id].get("notifications_enabled", False)

    def create_notification(
        self,
        device_id: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        icon: Optional[str] = None,
        actions: List[str] = None,
        requires_confirmation: bool = False
    ) -> Optional[Notification]:
        """
        Create a new notification for forwarding.
        Returns None if notifications disabled for device.
        """
        if not self.is_device_notifications_enabled(device_id):
            return None

        notification_id = f"notif_{uuid.uuid4().hex[:10]}"

        notification = Notification(
            notification_id=notification_id,
            device_id=device_id,
            title=title,
            message=message,
            priority=priority,
            icon=icon,
            actions=actions or [],
            requires_confirmation=requires_confirmation
        )

        with self._lock:
            self._notifications[notification_id] = notification

        self._notify_change(notification_id, notification)
        return notification

    def get_device_notifications(self, device_id: str, limit: int = 100) -> List[Notification]:
        """Get notifications for a device"""
        with self._lock:
            device_notifs = [
                n for n in self._notifications.values()
                if n.device_id == device_id
            ]
            device_notifs.sort(key=lambda n: n.timestamp, reverse=True)
            return device_notifs[:limit]

    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read"""
        with self._lock:
            if notification_id in self._notifications:
                self._notifications[notification_id].is_read = True
                self._notify_change(notification_id, self._notifications[notification_id])
                return True
        return False

    def dismiss_notification(self, notification_id: str) -> bool:
        """Remove a notification"""
        with self._lock:
            if notification_id in self._notifications:
                del self._notifications[notification_id]
                return True
        return False

    def clear_device_notifications(self, device_id: str):
        """Clear all notifications for a device"""
        with self._lock:
            to_remove = [
                nid for nid, n in self._notifications.items()
                if n.device_id == device_id
            ]
            for nid in to_remove:
                del self._notifications[nid]

    def get_unread_count(self, device_id: str) -> int:
        """Get count of unread notifications for a device"""
        with self._lock:
            return len([
                n for n in self._notifications.values()
                if n.device_id == device_id and not n.is_read
            ])

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get a specific notification"""
        with self._lock:
            return self._notifications.get(notification_id)

    def _notify_change(self, notification_id: str, notification: Notification):
        """Notify callbacks of notification change"""
        for callback in self._callbacks:
            try:
                callback(notification_id, notification)
            except Exception:
                pass

    def clear_all(self):
        """Clear all notifications (for testing)"""
        with self._lock:
            self._notifications.clear()
            self._device_settings.clear()


# Global notification manager instance
_global_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get global notification manager instance"""
    global _global_notification_manager
    if _global_notification_manager is None:
        _global_notification_manager = NotificationManager()
    return _global_notification_manager