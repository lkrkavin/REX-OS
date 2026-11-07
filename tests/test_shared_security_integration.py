import unittest
from connect.security import Permission, PermissionLevel, SecurityManager
from connect.remote_input import InputEvent, InputResult, InputType, RemoteInputHandler
from connect.screen_stream import ScreenStreamer
from connect.device_registry import DeviceInfo, DeviceRegistry, DeviceType
from connect.security import get_security_manager
import tempfile
from pathlib import Path


class SharedSecurityIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_input_fails_closed_without_security_manager(self):
        handler = RemoteInputHandler()
        event = InputEvent(InputType.MOUSE_MOVE, {"x": 1, "y": 1}, 1.0, "phone")
        result = await handler.process_input(event, None, "phone")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "PERMISSION_DENIED")

    async def test_remote_input_requires_scoped_permission(self):
        manager = SecurityManager()
        manager.grant_device_permissions("phone", PermissionLevel.READ_ONLY)
        handler = RemoteInputHandler(manager)
        event = InputEvent(InputType.MOUSE_MOVE, {"x": 1, "y": 1}, 1.0, "phone")
        result = await handler.process_input(event, None, "phone")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "PERMISSION_DENIED")

    async def test_remote_input_rejects_device_identity_mismatch(self):
        manager = SecurityManager()
        manager.grant_device_permissions("phone", PermissionLevel.CONTROL)
        handler = RemoteInputHandler(manager)
        event = InputEvent(InputType.MOUSE_MOVE, {"x": 1, "y": 1}, 1.0, "other-device")
        result = await handler.process_input(event, None, "phone")
        self.assertFalse(result.success)

    async def test_mouse_click_dispatches_click_event(self):
        manager = SecurityManager()
        manager.grant_device_permissions("phone", PermissionLevel.CONTROL)
        handler = RemoteInputHandler(manager)
        received = []
        handler.register_handler(lambda event: (received.append(event) or InputResult(True, "ok")))
        result = await handler.mouse_click(10, 20, "phone", manager, button="right")
        self.assertTrue(result.success)
        self.assertEqual(received[0].event_type, InputType.MOUSE_CLICK)
        self.assertEqual(received[0].data["button"], "right")

    async def test_device_registry_revocation_clears_shared_permissions(self):
        manager = get_security_manager()
        device_id = "security-integration-revocation-test"
        manager.grant_device_permissions(device_id, PermissionLevel.CONTROL)
        with tempfile.TemporaryDirectory() as directory:
            registry = DeviceRegistry(str(Path(directory) / "devices.json"))
            registry.add_device(DeviceInfo(device_id, "Test phone", DeviceType.ANDROID_PHONE))
            self.assertTrue(manager.check_permission(device_id, Permission.REMOTE_MOUSE))
            self.assertTrue(registry.revoke_device(device_id))
            self.assertFalse(manager.check_permission(device_id, Permission.REMOTE_MOUSE))

    async def test_screen_stream_requires_permission_and_user_consent(self):
        denied = SecurityManager()
        denied.grant_device_permissions("phone", PermissionLevel.READ_ONLY)
        self.assertFalse(await ScreenStreamer(denied).start_stream("phone", user_confirmed=True))

        allowed = SecurityManager()
        allowed.grant_device_permissions("phone", PermissionLevel.READ_ONLY, permissions={Permission.SCREEN_STREAMING})
        streamer = ScreenStreamer(allowed)
        self.assertFalse(await streamer.start_stream("phone", user_confirmed=False))
        self.assertTrue(await streamer.start_stream("phone", user_confirmed=True))


if __name__ == "__main__":
    unittest.main()
