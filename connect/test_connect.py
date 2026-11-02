#!/usr/bin/env python3
"""
Tests for REX CONNECT modules
"""

import unittest
import asyncio
import tempfile
import os
import sys
import json
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect.device_registry import (
    DeviceRegistry, DeviceInfo, DeviceType, ConnectionStatus,
    get_device_registry
)
from connect.pairing import (
    PairingManager, PairingResult, PairingMethod,
    get_pairing_manager
)
from connect.security import (
    SecurityManager, Permission, PermissionLevel, AccessToken,
    get_security_manager
)
from connect.connection import (
    ConnectionManager, Connection, ConnectionType,
    get_connection_manager
)
from connect.remote_input import (
    RemoteInputHandler, InputEvent, InputType, InputResult,
    get_input_handler
)
from connect.screen_stream import (
    ScreenStreamer, StreamConfig, StreamStatus,
    get_stream_manager
)
from connect.file_transfer import (
    FileTransferManager, TransferInfo, TransferStatus,
    get_transfer_manager
)
from connect.notification import (
    NotificationManager, Notification, NotificationPriority,
    get_notification_manager
)
from connect.device_types import (
    AndroidPhoneAdapter, AndroidTVAdapter, WindowsPCAdapter, LinuxPCAdapter,
    get_adapter, register_adapter
)
from pathlib import Path


class TestDeviceRegistry(unittest.TestCase):
    """Tests for DeviceRegistry"""

    def setUp(self):
        # Use temp directory for test isolation
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "devices.json")
        self.registry = DeviceRegistry(self.storage_path)

    def tearDown(self):
        # Cleanup temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_add_and_get_device(self):
        """Test adding and retrieving a device"""
        device = DeviceInfo(
            device_id="test_123",
            name="Test Device",
            device_type=DeviceType.ANDROID_PHONE,
        )

        self.registry.add_device(device)
        retrieved = self.registry.get_device("test_123")
        self.assertEqual(retrieved.name, "Test Device")

    def test_remove_device(self):
        """Test removing a device"""
        device = DeviceInfo(
            device_id="test_456",
            name="Device to Remove",
            device_type=DeviceType.WINDOWS_PC,
        )

        self.registry.add_device(device)
        self.assertTrue(self.registry.remove_device("test_456"))
        self.assertIsNone(self.registry.get_device("test_456"))

    def test_get_online_devices(self):
        """Test filtering online devices"""
        device1 = DeviceInfo(
            device_id="online_1",
            name="Online Device",
            device_type=DeviceType.ANDROID_PHONE,
            connection_status=ConnectionStatus.ONLINE,
        )
        device2 = DeviceInfo(
            device_id="offline_1",
            name="Offline Device",
            device_type=DeviceType.ANDROID_PHONE,
            connection_status=ConnectionStatus.OFFLINE,
        )

        self.registry.add_device(device1)
        self.registry.add_device(device2)

        online = self.registry.get_online_devices()
        self.assertEqual(len(online), 1)
        self.assertEqual(online[0].device_id, "online_1")

    def test_update_status(self):
        """Test updating device status"""
        device = DeviceInfo(
            device_id="status_test",
            name="Status Test",
            device_type=DeviceType.ANDROID_PHONE,
        )
        self.registry.add_device(device)
        self.assertTrue(self.registry.update_status("status_test", ConnectionStatus.ONLINE, "192.168.1.100"))

        updated = self.registry.get_device("status_test")
        self.assertEqual(updated.connection_status, ConnectionStatus.ONLINE)
        self.assertEqual(updated.last_seen_ip, "192.168.1.100")

    def test_generate_device_id(self):
        """Test device ID generation"""
        id1 = self.registry.generate_device_id()
        id2 = self.registry.generate_device_id()
        self.assertNotEqual(id1, id2)
        self.assertTrue(id1.startswith("dev_"))


class TestPairingManager(unittest.TestCase):
    """Tests for PairingManager"""

    def setUp(self):
        self.pairing = PairingManager()

    def test_generate_pairing_code_format(self):
        """Test pairing code is 6 digits"""
        code = self.pairing._generate_pairing_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_initiate_pairing(self):
        """Test pairing initiation"""
        result = asyncio.run(self.pairing.initiate_pairing(
            DeviceType.ANDROID_PHONE,
            "Test Phone"
        ))
        self.assertTrue(result.success)
        self.assertIsNotNone(result.session_id)

    def test_confirm_pairing_wrong_code(self):
        """Test pairing confirmation with wrong code"""
        result = asyncio.run(self.pairing.initiate_pairing(
            DeviceType.ANDROID_PHONE,
            "Test Phone"
        ))
        confirm_result = asyncio.run(self.pairing.confirm_pairing(result.session_id, "000000"))
        self.assertFalse(confirm_result.success)

    def test_cancel_pairing(self):
        """Test cancelling pairing"""
        result = asyncio.run(self.pairing.initiate_pairing(
            DeviceType.ANDROID_PHONE,
            "Test Phone"
        ))
        self.assertTrue(self.pairing.cancel_pairing(result.session_id))


class TestSecurityManager(unittest.TestCase):
    """Tests for Security Manager"""

    def setUp(self):
        self.security = SecurityManager()
        self.device_id = "test_device_123"

    def test_grant_and_check_permission(self):
        """Test granting and checking permissions"""
        self.security.grant_device_permissions(
            self.device_id,
            PermissionLevel.CONTROL,
            {Permission.REMOTE_MOUSE, Permission.REMOTE_KEYBOARD}
        )
        self.assertTrue(self.security.check_permission(self.device_id, Permission.REMOTE_MOUSE))
        self.assertFalse(self.security.check_permission(self.device_id, Permission.FILE_TRANSFER))

    def test_fail_closed_no_permission(self):
        """Test that permission check fails closed for ungranted devices"""
        # Device not in permissions dict should fail
        self.assertFalse(self.security.check_permission("unknown_device", Permission.REMOTE_MOUSE))

    def test_token_validation(self):
        """Test token creation and validation"""
        self.security.grant_device_permissions(self.device_id, PermissionLevel.FULL_ACCESS)

        token = self.security.create_session_token(self.device_id)
        self.assertTrue(token.is_valid())
        self.assertEqual(token.device_id, self.device_id)

        # Invalid token should fail
        fake_token = AccessToken(
            token_id="fake",
            device_id="other_device",
            created_at=0,
            expires_at=float('inf'),
            permission_level=PermissionLevel.NONE
        )
        self.assertFalse(self.security.validate_token("fake") or self.security.check_permission(self.device_id, Permission.REMOTE_MOUSE, "fake"))

    def test_path_sanitization(self):
        """Test path sanitization for file transfer security"""
        # Valid path within allowed roots (user home)
        valid = self.security.sanitize_path(os.path.expanduser("~/file.txt"))
        self.assertIsNotNone(valid)

        # Path traversal should be blocked
        invalid = self.security.sanitize_path("../../../etc/passwd")
        self.assertIsNone(invalid)


class TestConnectionManager(unittest.TestCase):
    """Tests for ConnectionManager"""

    def setUp(self):
        self.conn_mgr = ConnectionManager()

    def test_add_and_remove_connection(self):
        """Test adding and removing connections"""
        conn = self.conn_mgr.add_connection(
            "conn_123",
            "device_456",
            ConnectionType.WEBSOCKET,
            "192.168.1.100"
        )
        self.assertEqual(conn.connection_id, "conn_123")

        self.assertTrue(self.conn_mgr.remove_connection("conn_123"))
        self.assertIsNone(self.conn_mgr.get_connection("conn_123"))

    def test_authenticate_connection(self):
        """Test connection authentication"""
        from connect.security import PermissionLevel, Permission, get_security_manager

        # Setup security manager
        security = SecurityManager()
        security.grant_device_permissions("device_456", PermissionLevel.CONTROL)
        token = security.create_session_token("device_456")

        # Add connection
        conn = self.conn_mgr.add_connection(
            "conn_789",
            "device_456",
            ConnectionType.WEBSOCKET
        )

        # Authenticate
        self.assertTrue(self.conn_mgr.authenticate_connection("conn_789", token.token_id, security))

        # Check authenticated
        updated = self.conn_mgr.get_connection("conn_789")
        self.assertTrue(updated.is_authenticated)

    def test_device_connection_status(self):
        """Test getting device connection status"""
        conn = self.conn_mgr.add_connection("c1", "d1", ConnectionType.WEBSOCKET)
        conn.is_authenticated = True  # Need authenticated connection
        status = self.conn_mgr.get_connection_status("d1")
        self.assertTrue(status.connected)


class TestRemoteInputHandler(unittest.TestCase):
    """Tests for RemoteInputHandler"""

    def setUp(self):
        self.handler = RemoteInputHandler()

    def test_process_input_fail_closed(self):
        """Test input processing fails without permissions"""
        from connect.security import SecurityManager, PermissionLevel

        security = SecurityManager()
        # No permissions granted - should fail closed

        event = InputEvent(
            event_type=InputType.MOUSE_MOVE,
            data={"x": 100, "y": 100},
            timestamp=0,
            source_device="test"
        )

        result = asyncio.run(self.handler.process_input(event, security, "test"))
        self.assertFalse(result.success)

    def test_register_handler(self):
        """Test registering an input handler"""
        called = []

        def handler(event):
            called.append(event.event_type)
            return InputResult(success=True, message="OK")

        self.handler.register_handler(handler)
        # Handler is registered, can be verified


class TestScreenStreamer(unittest.TestCase):
    """Tests for ScreenStreamer"""

    def setUp(self):
        self.streamer = ScreenStreamer()

    def test_start_stream_requires_consent(self):
        """Test that stream requires explicit user consent"""
        result = asyncio.run(self.streamer.start_stream(
            "device_123",
            user_confirmed=False  # No consent
        ))
        self.assertFalse(result)

    def test_stream_status(self):
        """Test streaming status"""
        status = self.streamer.get_stream_status("nonexistent")
        self.assertIsNone(status)  # Returns None for non-existent stream


class TestFileTransferManager(unittest.TestCase):
    """Tests for FileTransferManager"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.transfer_mgr = FileTransferManager(self.temp_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sanitize_filename(self):
        """Test filename sanitization - rejects traversal, accepts valid names"""
        # Valid name - should pass through
        valid = self.transfer_mgr._sanitize_filename("document.pdf")
        self.assertEqual(valid, "document.pdf")

        # Path traversal with ../ - should be REJECTED (return None)
        invalid = self.transfer_mgr._sanitize_filename("../../../etc/passwd")
        self.assertIsNone(invalid, "Unix traversal path should be rejected")

    def test_create_transfer_request(self):
        """Test creating a transfer request"""
        transfer = self.transfer_mgr.create_transfer_request(
            "test_file.txt",
            1000,
            "device_123",
            "local"
        )
        self.assertIsNotNone(transfer)
        self.assertEqual(transfer.filename, "test_file.txt")
        self.assertTrue(transfer.requires_confirmation)

    def test_validate_transfer_request_unix_traversal_rejected(self):
        """Test that Unix-style path traversal attempts are REJECTED"""
        unix_traversal_attempts = [
            "../../../etc/passwd",
            "../../../../root/.ssh/id_rsa",
            "../../../var/log/auth.log",
        ]

        for attempt in unix_traversal_attempts:
            with self.subTest(path=attempt):
                result = self.transfer_mgr.validate_transfer_request(
                    "test",
                    attempt,
                    1000,
                    "device_123",
                    "local"
                )
                self.assertIsNone(result, f"Unix traversal path {attempt} should be rejected")

    def test_validate_transfer_request_windows_traversal_rejected(self):
        """Test that Windows-style path traversal attempts are REJECTED"""
        windows_traversal_attempts = [
            "..\\..\\..\\windows\\system32\\config\\sam",
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "..\\..\\..\\etc\\passwd",
        ]

        for attempt in windows_traversal_attempts:
            with self.subTest(path=attempt):
                result = self.transfer_mgr.validate_transfer_request(
                    "test",
                    attempt,
                    1000,
                    "device_123",
                    "local"
                )
                self.assertIsNone(result, f"Windows traversal path {attempt} should be rejected")

    def test_validate_transfer_request_absolute_path_rejected(self):
        """Test that absolute paths are REJECTED"""
        absolute_paths = [
            "/etc/passwd",
            "/var/log/auth.log",
            "/root/.ssh/id_rsa",
        ]

        for attempt in absolute_paths:
            with self.subTest(path=attempt):
                result = self.transfer_mgr.validate_transfer_request(
                    "test",
                    attempt,
                    1000,
                    "device_123",
                    "local"
                )
                self.assertIsNone(result, f"Absolute path {attempt} should be rejected")

    def test_validate_transfer_request_encoded_traversal_rejected(self):
        """Test that URL-encoded traversal attempts are REJECTED"""
        encoded_attempts = [
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded ../
            "..%5C..%5C..%5Cwindows%5csystem32",  # URL encoded ..\
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # Fully URL encoded
        ]

        for attempt in encoded_attempts:
            with self.subTest(path=attempt):
                result = self.transfer_mgr.validate_transfer_request(
                    "test",
                    attempt,
                    1000,
                    "device_123",
                    "local"
                )
                self.assertIsNone(result, f"Encoded traversal path {attempt} should be rejected")

    def test_validate_transfer_request_null_byte_rejected(self):
        """Test that null byte injection is blocked"""
        result = self.transfer_mgr.validate_transfer_request(
            "test",
            "file\x00.txt.exe",  # Null byte in filename
            1000,
            "device_123",
            "local"
        )
        self.assertIsNone(result, "Null byte injection should be rejected")

    def test_validate_transfer_request_path_with_separator_rejected(self):
        """Test that paths containing separators are REJECTED"""
        paths_with_separators = [
            "subdir/file.txt",
            "..\\subdir\\file.txt",
            "/etc/passwd",
            "some/path/file.txt",
        ]

        for attempt in paths_with_separators:
            with self.subTest(path=attempt):
                result = self.transfer_mgr.validate_transfer_request(
                    "test",
                    attempt,
                    1000,
                    "device_123",
                    "local"
                )
                self.assertIsNone(result, f"Path with separator {attempt} should be rejected")

    def test_transfer_request_null_byte_injection(self):
        """Test that null byte injection is REJECTED"""
        result = self.transfer_mgr.validate_transfer_request(
            "test",
            "file\x00.txt.exe",  # Null byte in filename
            1000,
            "device_123",
            "local"
        )
        # Null bytes should be rejected (not sanitized)
        self.assertIsNone(result, "Null byte injection should be rejected")


class TestNotificationManager(unittest.TestCase):
    """Tests for NotificationManager"""

    def setUp(self):
        self.notif_mgr = NotificationManager()

    def test_create_notification(self):
        """Test creating a notification"""
        # First enable notifications for device
        self.notif_mgr.set_device_notification_enabled("device_123", True)

        notif = self.notif_mgr.create_notification(
            "device_123",
            "Test Title",
            "Test message"
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.title, "Test Title")

    def test_notification_blocked_when_disabled(self):
        """Test notification is blocked when disabled"""
        # Notifications disabled by default
        notif = self.notif_mgr.create_notification(
            "device_123",
            "Test Title",
            "Test message"
        )
        self.assertIsNone(notif)  # Should be blocked

    def test_unread_count(self):
        """Test unread notification counting"""
        self.notif_mgr.set_device_notification_enabled("device_123", True)

        self.notif_mgr.create_notification("device_123", "Title 1", "Message 1")
        self.notif_mgr.create_notification("device_123", "Title 2", "Message 2")

        count = self.notif_mgr.get_unread_count("device_123")
        self.assertEqual(count, 2)


class TestDeviceTypeAdapters(unittest.TestCase):
    """Tests for device type adapters"""

    def test_android_phone_adapter(self):
        """Test Android phone adapter capabilities"""
        adapter = AndroidPhoneAdapter()
        caps = adapter.capabilities
        self.assertTrue(caps.supports_remote_input)
        self.assertTrue(caps.supports_notifications)
        self.assertTrue(caps.supports_file_transfer)

    def test_android_tv_adapter(self):
        """Test Android TV adapter capabilities"""
        adapter = AndroidTVAdapter()
        caps = adapter.capabilities
        self.assertTrue(caps.supports_remote_input)
        self.assertTrue(caps.supports_media_control)
        self.assertFalse(caps.supports_file_transfer)  # TV doesn't receive files

    def test_windows_pc_adapter(self):
        """Test Windows PC adapter capabilities"""
        adapter = WindowsPCAdapter()
        caps = adapter.capabilities
        self.assertTrue(caps.supports_lock_screen)

    def test_adapter_registration(self):
        """Test adapter lookup"""
        adapter = get_adapter("android phone")
        self.assertIsInstance(adapter, AndroidPhoneAdapter)

        # "windows pc" is the exact key, not "windows"
        adapter = get_adapter("windows pc")
        self.assertIsInstance(adapter, WindowsPCAdapter)


class TestPermissionEnforcement(unittest.TestCase):
    """Tests for permission enforcement (security requirements)"""

    def test_unauthorized_install_denied(self):
        """Test that unauthorized installation is denied"""
        security = SecurityManager()
        # No permissions - fail closed
        self.assertFalse(security.check_permission("device_123", Permission.FILE_TRANSFER))

    def test_token_required_for_remote_control(self):
        """Test that remote control requires valid token"""
        security = SecurityManager()
        security.grant_device_permissions("device_123", PermissionLevel.CONTROL)

        # Token must be created
        token = security.create_session_token("device_123")
        self.assertTrue(token.is_valid())

        # Wrong device ID in token should fail
        fake_token = AccessToken(
            token_id="fake",
            device_id="wrong_device",
            created_at=0,
            expires_at=float('inf'),
            permission_level=PermissionLevel.CONTROL
        )
        self.assertFalse(security.check_permission("device_123", Permission.REMOTE_MOUSE, "fake"))

    def test_path_traversal_protected(self):
        """Test path traversal attack is prevented"""
        security = SecurityManager()

        attack_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/shadow",
            "~/../../etc/passwd",
        ]

        for path in attack_paths:
            result = security.sanitize_path(path)
            # Should either be None or a safe path within allowed roots
            if result:
                self.assertNotIn("..", result)


if __name__ == "__main__":
    unittest.main()