import asyncio
import tempfile
import unittest
from pathlib import Path

from connect.security import Permission, PermissionLevel, SecurityManager
from connect.file_transfer import FileTransferManager, TransferStatus
from omni.package_manager import PackageManager


class SharedSecurityBoundaryTests(unittest.TestCase):
    def test_remote_file_transfer_requires_shared_permission(self):
        manager = SecurityManager()
        with tempfile.TemporaryDirectory() as directory:
            transfers = FileTransferManager(directory, security_manager=manager)
            self.assertIsNone(transfers.create_transfer_request(
                "report.txt", 12, "phone", "local"
            ))

            manager.grant_device_permissions("phone", PermissionLevel.FULL_ACCESS)
            transfer = transfers.create_transfer_request("report.txt", 12, "phone", "local")
            self.assertIsNotNone(transfer)
            self.assertTrue(transfers.accept_transfer(transfer.transfer_id, confirmed=True))
            self.assertTrue(transfers.start_transfer(transfer.transfer_id))

    def test_revocation_between_accept_and_start_blocks_file_transfer(self):
        manager = SecurityManager()
        manager.grant_device_permissions("phone", PermissionLevel.FULL_ACCESS)
        with tempfile.TemporaryDirectory() as directory:
            transfers = FileTransferManager(directory, security_manager=manager)
            transfer = transfers.create_transfer_request("report.txt", 12, "phone", "local")
            self.assertIsNotNone(transfer)
            self.assertTrue(transfers.accept_transfer(transfer.transfer_id, confirmed=True))
            manager.revoke_device_permissions("phone")
            self.assertFalse(transfers.start_transfer(transfer.transfer_id))
            self.assertEqual(transfer.status, TransferStatus.DENIED)

    def test_omni_uses_shared_permissions_and_explicit_approval(self):
        manager = SecurityManager(approval_callback=lambda _action, _target: True)
        manager.grant_device_permissions(
            "trusted-device", PermissionLevel.FULL_ACCESS,
            permissions={Permission.APP_INSTALL, Permission.APP_REMOVE}
        )
        package_manager = PackageManager(security_manager=manager, actor_id="trusted-device")
        self.assertTrue(asyncio.run(package_manager._check_permission("firefox", "install")))
        self.assertTrue(asyncio.run(package_manager._check_permission("firefox", "uninstall")))
        manager.revoke_device_permissions("trusted-device")
        self.assertFalse(asyncio.run(package_manager._check_permission("firefox", "install")))

    def test_omni_denies_missing_actor_and_invalid_package_id(self):
        manager = SecurityManager(approval_callback=lambda _action, _target: True)
        manager.grant_device_permissions("trusted-device", PermissionLevel.ADMIN)
        without_actor = PackageManager(security_manager=manager)
        with_actor = PackageManager(security_manager=manager, actor_id="trusted-device")
        self.assertFalse(asyncio.run(without_actor._check_permission("firefox", "install")))
        self.assertFalse(asyncio.run(with_actor._check_permission("bad\npackage", "install")))


if __name__ == "__main__":
    unittest.main()
