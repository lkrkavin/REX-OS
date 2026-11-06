import asyncio
import tempfile
import unittest
from pathlib import Path

from connect.device_registry import DeviceRegistry, DeviceType
from connect.pairing import PairingManager


class TestPairingSecurity(unittest.TestCase):
    def test_success_returns_one_time_token_and_registry_stores_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = DeviceRegistry(str(Path(directory) / "devices.json"))
            manager = PairingManager(registry)
            started = asyncio.run(manager.initiate_pairing(DeviceType.ANDROID_PHONE, "Test Phone"))
            session = manager.get_session(started.session_id)
            asyncio.run(manager.confirm_pairing_local(started.session_id))
            result = asyncio.run(manager.confirm_pairing(started.session_id, session.pairing_code))
            self.assertTrue(result.success)
            self.assertTrue(result.auth_token)
            self.assertTrue(registry.validate_token(result.device_id, result.auth_token))
            persisted = (Path(directory) / "devices.json").read_text(encoding="utf-8")
            self.assertNotIn(result.auth_token, persisted)

    def test_pairing_session_expires_after_five_bad_codes(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = DeviceRegistry(str(Path(directory) / "devices.json"))
            manager = PairingManager(registry)
            started = asyncio.run(manager.initiate_pairing(DeviceType.ANDROID_PHONE, "Test Phone"))
            asyncio.run(manager.confirm_pairing_local(started.session_id))
            for _ in range(manager.MAX_CODE_ATTEMPTS):
                result = asyncio.run(manager.confirm_pairing(started.session_id, "wrong-code"))
            self.assertFalse(result.success)
            self.assertEqual(result.error, "TOO_MANY_ATTEMPTS")
            self.assertIsNone(manager.get_session(started.session_id))


if __name__ == "__main__":
    unittest.main()
