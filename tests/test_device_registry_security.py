import json
import os
import tempfile
import unittest
from pathlib import Path

from connect.device_registry import DeviceRegistry, DeviceInfo, DeviceType, ConnectionStatus


class TestDeviceRegistry(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "devices.json"
        self.registry = DeviceRegistry(str(self.path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_persists_only_token_hash_and_reloads(self):
        raw = "RexTestToken-" + ("x" * 40)
        device = DeviceInfo("phone_1", "Test Phone", DeviceType.ANDROID_PHONE,
                            auth_token=raw, token_expires=4102444800)
        self.registry.add_device(device)
        persisted = self.path.read_text(encoding="utf-8")
        self.assertNotIn(raw, persisted)
        self.assertIsNone(device.auth_token)
        self.assertTrue(self.registry.validate_token("phone_1", raw))
        self.assertFalse(self.registry.validate_token("phone_1", "wrong-token"))
        reloaded = DeviceRegistry(str(self.path))
        self.assertTrue(reloaded.validate_token("phone_1", raw))

    def test_token_update_requires_trusted_device_and_long_token(self):
        self.registry.add_device(DeviceInfo("phone_2", "Phone", DeviceType.ANDROID_PHONE))
        self.assertFalse(self.registry.update_token("phone_2", "short"))
        self.assertTrue(self.registry.update_token("phone_2", "a" * 40))
        self.assertTrue(self.registry.validate_token("phone_2", "a" * 40))
        self.registry.revoke_device("phone_2")
        self.assertFalse(self.registry.validate_token("phone_2", "a" * 40))
        self.assertFalse(self.registry.update_token("phone_2", "b" * 40))

    def test_storage_file_is_owner_only(self):
        self.registry.add_device(DeviceInfo("phone_3", "Phone", DeviceType.ANDROID_PHONE))
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_migrates_legacy_plaintext_token(self):
        raw = "legacy-token-" + ("z" * 40)
        self.path.write_text(json.dumps({"version": 1, "devices": [{
            "device_id": "legacy", "name": "Old Phone", "device_type": "android_phone",
            "connection_status": "offline", "auth_token": raw,
            "token_expires": 4102444800, "is_trusted": True
        }]}), encoding="utf-8")
        migrated = DeviceRegistry(str(self.path))
        persisted = self.path.read_text(encoding="utf-8")
        self.assertNotIn(raw, persisted)
        self.assertTrue(migrated.validate_token("legacy", raw))


if __name__ == "__main__":
    unittest.main()
