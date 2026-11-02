#!/usr/bin/env python3
"""
Tests for REX OMNI modules
"""

import unittest
import asyncio
import tempfile
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omni.app_catalog import AppCatalog, ApplicationInfo, Category
from omni.package_manager import PackageManager, InstallResult, InstallMethod
from omni.app_launcher import AppLauncher, LaunchResult, LaunchMethod
from omni.omni_core import OMNICore, OMNIStatus, OMNIResult


class TestAppCatalog(unittest.TestCase):
    """Tests for AppCatalog"""

    def setUp(self):
        self.catalog = AppCatalog()
        self.catalog.initialize()

    def test_initialize(self):
        """Test catalog initialization"""
        self.assertTrue(self.catalog._initialized)
        self.assertIsInstance(self.catalog._applications, list)

    def test_search_returns_list(self):
        """Test search returns list of ApplicationInfo"""
        results = self.catalog.search("test")
        self.assertIsInstance(results, list)

    def test_get_by_category(self):
        """Test getting applications by category"""
        apps = self.catalog.get_by_category(Category.UTILITIES)
        self.assertIsInstance(apps, list)
        for app in apps:
            self.assertIsInstance(app, ApplicationInfo)

    def test_get_installed(self):
        """Test getting installed applications"""
        installed = self.catalog.get_installed()
        self.assertIsInstance(installed, list)

    def test_available_methods(self):
        """Test getting available installation methods"""
        methods = self.catalog.get_available_methods()
        self.assertIsInstance(methods, list)

    def test_application_info_to_dict(self):
        """Test ApplicationInfo serialization"""
        app = ApplicationInfo(
            name="test-app",
            display_name="Test App",
            description="A test application",
            icon_path="/usr/share/icons/test.png",
            version="1.0.0",
            categories=[Category.UTILITIES],
            install_method="apt",
            package_id="test-app",
            installed=True
        )
        d = app.to_dict()
        self.assertEqual(d['name'], "test-app")
        self.assertEqual(d['display_name'], "Test App")
        self.assertEqual(d['categories'], ["utilities"])


class TestPackageManager(unittest.TestCase):
    """Tests for PackageManager"""

    def setUp(self):
        self.pm = PackageManager()

    def test_install_method_enum(self):
        """Test InstallMethod enum values"""
        self.assertEqual(InstallMethod.APT.value, "apt")
        self.assertEqual(InstallMethod.FLATPAK.value, "flatpak")
        self.assertEqual(InstallMethod.APPIMAGE.value, "appimage")

    def test_install_result_dataclass(self):
        """Test InstallResult dataclass"""
        result = InstallResult(
            success=True,
            method=InstallMethod.APT,
            package_id="test-package",
            message="Success",
            output="Output text",
            error=""
        )
        self.assertTrue(result.success)
        self.assertEqual(result.package_id, "test-package")
        d = result.to_dict()
        self.assertEqual(d['method'], 'apt')

    def test_check_permission_fails_closed(self):
        """Test permission check fails closed by default"""
        result = asyncio.run(self.pm._check_permission("test", "install"))
        self.assertFalse(result)

    def test_check_permission_can_be_overridden(self):
        """Test permission check can be overridden for testing"""
        # Override the permission check for testing
        async def mock_permission(package_id, action):
            return True

        self.pm._check_permission = mock_permission
        result = asyncio.run(self.pm._check_permission("test", "install"))
        self.assertTrue(result)

    def test_not_found_package(self):
        """Test installing a non-existent package with mocked subprocess"""
        import subprocess
        from unittest.mock import patch

        # Override permission check for testing
        async def mock_permission(package_id, action):
            return True
        self.pm._check_permission = mock_permission

        # Mock apt-cache show to return "not found"
        with patch('subprocess.run') as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 100  # apt-cache show returns 100 for not found
            mock_result.stdout = ""
            mock_result.stderr = "Package not found"
            mock_run.return_value = mock_result

            result = asyncio.run(self.pm._install_apt("nonexistent-package-xyz-123"))

        self.assertFalse(result.success)
        self.assertIn("not found", result.message.lower())


class TestAppLauncher(unittest.TestCase):
    """Tests for AppLauncher"""

    def setUp(self):
        self.launcher = AppLauncher()

    def test_launch_result_dataclass(self):
        """Test LaunchResult dataclass"""
        result = LaunchResult(
            success=True,
            app_name="Test App",
            process_id=12345,
            message="Launched successfully"
        )
        self.assertTrue(result.success)
        self.assertEqual(result.process_id, 12345)
        d = result.to_dict()
        self.assertEqual(d['app_name'], "Test App")

    def test_check_permission_fails_closed(self):
        """Test permission check fails closed by default"""
        result = asyncio.run(self.launcher._check_permission("test", "launch"))
        self.assertFalse(result)

    def test_check_permission_can_be_overridden(self):
        """Test permission check can be overridden for testing"""
        async def mock_permission(app_name, action):
            return True
        self.launcher._check_permission = mock_permission
        result = asyncio.run(self.launcher._check_permission("test", "launch"))
        self.assertTrue(result)

    def test_get_running_apps(self):
        """Test getting running apps list"""
        running = self.launcher.get_running_apps()
        self.assertIsInstance(running, list)

    def test_stop_nonexistent_app(self):
        """Test stopping an app that isn't running"""
        result = self.launcher.stop_app("nonexistent-app")
        self.assertFalse(result)


class TestOMNICore(unittest.TestCase):
    """Tests for OMNICore"""

    def setUp(self):
        self.omni = OMNICore()

    def test_initialization(self):
        """Test OMNI initialization"""
        status_callback_calls = []

        def on_status(status: OMNIStatus, message: str):
            status_callback_calls.append((status, message))

        result = self.omni.initialize()
        self.assertTrue(result)

    def test_status_methods(self):
        """Test status getter"""
        self.omni.initialize()
        status = self.omni.get_status()
        self.assertEqual(status, OMNIStatus.READY)

    def test_search_applications(self):
        """Test application search through core"""
        self.omni.initialize()
        results = self.omni.search_applications("test")
        self.assertIsInstance(results, list)

    def test_get_install_methods(self):
        """Test getting available methods through core"""
        self.omni.initialize()
        methods = self.omni.get_available_install_methods()
        self.assertIn("native", methods)

    def test_determine_install_method(self):
        """Test method determination logic"""
        self.omni.initialize()

        apt_app = ApplicationInfo(
            name="vim",
            display_name="Vim",
            description="Text editor",
            icon_path=None,
            version="1.0",
            install_method="apt",
            package_id="vim",
            categories=[Category.DEVELOPMENT],
            installed=True
        )
        self.assertEqual(self.omni._determine_install_method(apt_app), InstallMethod.APT)

        flatpak_app = ApplicationInfo(
            name="org.videolan.VLC",
            display_name="VLC",
            description="Media player",
            icon_path=None,
            version="1.0",
            install_method="flatpak",
            flatpak_id="org.videolan.VLC",
            categories=[Category.MULTIMEDIA],
            installed=True
        )
        self.assertEqual(self.omni._determine_install_method(flatpak_app), InstallMethod.FLATPAK)

    def test_determine_launch_method(self):
        """Test launch method determination logic"""
        native_app = ApplicationInfo(
            name="test",
            display_name="Test",
            description="Test app",
            icon_path=None,
            version="1.0",
            install_method="native",
            executable="/usr/bin/test",
            categories=[Category.UTILITIES],
            installed=True
        )
        self.assertEqual(self.omni._determine_launch_method(native_app), LaunchMethod.NATIVE)

    def test_analyze_intent_install(self):
        """Test intent analysis for install"""
        intent = asyncio.run(self.omni._analyze_intent("install firefox"))
        self.assertEqual(intent, "install")

    def test_analyze_intent_uninstall(self):
        """Test intent analysis for uninstall"""
        intent = asyncio.run(self.omni._analyze_intent("remove firefox"))
        self.assertEqual(intent, "uninstall")

    def test_analyze_intent_launch(self):
        """Test intent analysis for launch"""
        intent = asyncio.run(self.omni._analyze_intent("launch firefox"))
        self.assertEqual(intent, "launch")

    def test_analyze_intent_search(self):
        """Test intent analysis for search"""
        intent = asyncio.run(self.omni._analyze_intent("find firefox"))
        self.assertEqual(intent, "search")

    def test_analyze_intent_unknown(self):
        """Test intent analysis for unknown command"""
        intent = asyncio.run(self.omni._analyze_intent("xyz abc"))
        self.assertEqual(intent, "unknown")


class TestOMNIResult(unittest.TestCase):
    """Tests for OMNIResult"""

    def test_success_result(self):
        """Test successful result"""
        result = OMNIResult(success=True, message="Success", data={"key": "value"})
        d = result.to_dict()
        self.assertTrue(d['success'])
        self.assertEqual(d['message'], "Success")
        self.assertEqual(d['data'], {"key": "value"})

    def test_failure_result(self):
        """Test failure result"""
        result = OMNIResult(success=False, message="Failed")
        d = result.to_dict()
        self.assertFalse(d['success'])
        self.assertEqual(d['message'], "Failed")


if __name__ == "__main__":
    unittest.main()