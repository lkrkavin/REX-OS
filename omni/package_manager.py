#!/usr/bin/env python3
"""
REX OMNI - Package Manager Backend

Provides controlled installation, removal, and status operations
for multiple package formats.
"""

import os
import subprocess
import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, List
from enum import Enum

from connect.security import get_security_manager


class InstallMethod(Enum):
    """Supported installation methods"""
    APT = "apt"
    FLATPAK = "flatpak"
    APPIMAGE = "appimage"
    NATIVE = "native"


@dataclass
class InstallResult:
    """Result of an installation operation"""
    success: bool
    method: InstallMethod
    package_id: str
    message: str
    output: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "method": self.method.value,
            "package_id": self.package_id,
            "message": self.message,
            "output": self.output,
            "error": self.error,
        }


class PackageManager:
    """
    Controlled package manager for installing and removing applications.
    Uses policy-based permissions and status callbacks.
    """

    def __init__(
        self,
        on_progress: Optional[Callable[[float, str], None]] = None,
        security_manager=None,
        actor_id: Optional[str] = None,
        token_id: Optional[str] = None,
    ):
        self._security = security_manager or get_security_manager()
        self._actor_id = actor_id
        self._token_id = token_id
        self._progress_callback = on_progress
        self._sudo_password: Optional[str] = None
        # Cross-platform check for root/admin
        self._is_root = self._check_is_root()

    def _check_is_root(self) -> bool:
        """Check if running as root (Unix) or admin (Windows)"""
        if hasattr(os, 'geteuid'):
            return os.geteuid() == 0
        # Windows: check for admin privileges
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def _report_progress(self, percent: float, message: str):
        """Report installation progress"""
        if self._progress_callback:
            self._progress_callback(percent, message)

    async def install(self, package_id: str, method: InstallMethod) -> InstallResult:
        """Install an application using the specified method"""
        if not await self._check_permission(package_id, "install"):
            return InstallResult(
                success=False,
                method=method,
                package_id=package_id,
                message="Installation denied by permission policy"
            )

        if method == InstallMethod.APT:
            return await self._install_apt(package_id)
        elif method == InstallMethod.FLATPAK:
            return await self._install_flatpak(package_id)
        elif method == InstallMethod.APPIMAGE:
            return await self._install_appimage(package_id)
        else:
            return InstallResult(
                success=False,
                method=method,
                package_id=package_id,
                message=f"Installation method {method} not supported"
            )

    async def uninstall(self, package_id: str, method: InstallMethod) -> InstallResult:
        """Uninstall an application using the specified method"""
        if not await self._check_permission(package_id, "uninstall"):
            return InstallResult(
                success=False,
                method=method,
                package_id=package_id,
                message="Uninstallation denied by permission policy"
            )

        if method == InstallMethod.APT:
            return await self._uninstall_apt(package_id)
        elif method == InstallMethod.FLATPAK:
            return await self._uninstall_flatpak(package_id)
        else:
            return InstallResult(
                success=False,
                method=method,
                package_id=package_id,
                message=f"Uninstallation method {method} not supported"
            )

    async def _check_permission(self, package_id: str, action: str) -> bool:
        """Authorize package changes through the shared, fail-closed security core."""
        if (not isinstance(package_id, str) or not package_id.strip()
                or len(package_id) > 256 or any(ch in package_id for ch in ("\x00", "\n", "\r"))):
            return False
        if action not in ("install", "uninstall") or not self._actor_id:
            return False
        try:
            shared_action = "install_app" if action == "install" else "remove_app"
            return bool(self._security and self._security.authorize_action(
                self._actor_id, shared_action, package_id, token_id=self._token_id
            ))
        except Exception:
            return False

    async def _install_apt(self, package_id: str) -> InstallResult:
        """Install an APT package"""
        self._report_progress(10, f"Checking package {package_id}...")

        try:
            # Check if package exists
            result = subprocess.run(
                ["apt-cache", "show", package_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return InstallResult(
                    success=False,
                    method=InstallMethod.APT,
                    package_id=package_id,
                    message=f"Package '{package_id}' not found in repositories"
                )

            self._report_progress(30, "Installing package...")

            # Run installation
            cmd = ["apt-get", "install", "-y", package_id]
            if not self._is_root:
                cmd = ["sudo", "-S"] + cmd
                if self._sudo_password:
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdin=asyncio.subprocess.PIPE,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(self._sudo_password.encode() + b'\n'),
                        timeout=300
                    )
                else:
                    return InstallResult(
                        success=False,
                        method=InstallMethod.APT,
                        package_id=package_id,
                        message="Root/sudo access required for package installation"
                    )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=300
                )

            self._report_progress(80, "Verifying installation...")

            # Verify installation
            verify = subprocess.run(
                ["dpkg", "-l", package_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if verify.returncode == 0:
                self._report_progress(100, "Installation complete!")
                return InstallResult(
                    success=True,
                    method=InstallMethod.APT,
                    package_id=package_id,
                    message=f"Successfully installed {package_id}",
                    output=stdout.decode() if stdout else ""
                )
            else:
                return InstallResult(
                    success=False,
                    method=InstallMethod.APT,
                    package_id=package_id,
                    message="Installation completed but verification failed"
                )

        except asyncio.TimeoutError:
            return InstallResult(
                success=False,
                method=InstallMethod.APT,
                package_id=package_id,
                message="Installation timed out"
            )
        except Exception as e:
            return InstallResult(
                success=False,
                method=InstallMethod.APT,
                package_id=package_id,
                message=str(e)
            )

    async def _install_flatpak(self, flatpak_id: str) -> InstallResult:
        """Install a Flatpak package"""
        self._report_progress(30, "Installing Flatpak...")

        try:
            process = await asyncio.create_subprocess_exec(
                "flatpak", "install", "-y", "flathub", flatpak_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=300
            )

            if process.returncode == 0:
                return InstallResult(
                    success=True,
                    method=InstallMethod.FLATPAK,
                    package_id=flatpak_id,
                    message=f"Successfully installed {flatpak_id}",
                    output=stdout.decode() if stdout else ""
                )
            else:
                return InstallResult(
                    success=False,
                    method=InstallMethod.FLATPAK,
                    package_id=flatpak_id,
                    message=stderr.decode() if stderr else "Installation failed"
                )
        except asyncio.TimeoutError:
            return InstallResult(
                success=False,
                method=InstallMethod.FLATPAK,
                package_id=flatpak_id,
                message="Installation timed out"
            )
        except FileNotFoundError:
            return InstallResult(
                success=False,
                method=InstallMethod.FLATPAK,
                package_id=flatpak_id,
                message="Flatpak not installed"
            )

    async def _install_appimage(self, appimage_url: str) -> InstallResult:
        """Install an AppImage (download to ~/Applications)"""
        self._report_progress(50, "Downloading AppImage...")

        app_dir = os.path.expanduser("~/Applications")
        os.makedirs(app_dir, exist_ok=True)

        try:
            import urllib.request
            name = appimage_url.split('/')[-1].split('?')[0]
            dest = os.path.join(app_dir, name)

            urllib.request.urlretrieve(appimage_url, dest)
            os.chmod(dest, 0o755)

            return InstallResult(
                success=True,
                method=InstallMethod.APPIMAGE,
                package_id=name,
                message=f"Downloaded {name} to {app_dir}",
                output=f"File saved to {dest}"
            )
        except Exception as e:
            return InstallResult(
                success=False,
                method=InstallMethod.APPIMAGE,
                package_id=appimage_url,
                message=str(e)
            )

    async def _uninstall_apt(self, package_id: str) -> InstallResult:
        """Uninstall an APT package"""
        try:
            cmd = ["apt-get", "remove", "-y", package_id]
            if not self._is_root:
                cmd = ["sudo", "-S"] + cmd
                # Handle sudo password
            else:
                pass

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120
            )

            return InstallResult(
                success=process.returncode == 0,
                method=InstallMethod.APT,
                package_id=package_id,
                message="Uninstalled" if process.returncode == 0 else f"Failed: {stderr.decode() if stderr else 'Unknown error'}",
                output=stdout.decode() if stdout and stdout != b'' else ""
            )
        except Exception as e:
            return InstallResult(
                success=False,
                method=InstallMethod.APT,
                package_id=package_id,
                message=str(e)
            )

    async def _uninstall_flatpak(self, flatpak_id: str) -> InstallResult:
        """Uninstall a Flatpak package"""
        try:
            process = await asyncio.create_subprocess_exec(
                "flatpak", "uninstall", "-y", flatpak_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )

            return InstallResult(
                success=process.returncode == 0,
                method=InstallMethod.FLATPAK,
                package_id=flatpak_id,
                message="Uninstalled" if process.returncode == 0 else f"Failed: {stderr.decode() if stderr else 'Unknown error'}",
                output=stdout.decode() if stdout and stdout != b'' else ""
            )
        except Exception as e:
            return InstallResult(
                success=False,
                method=InstallMethod.FLATPAK,
                package_id=flatpak_id,
                message=str(e)
            )

    def check_updates_available(self, package_id: str, method: InstallMethod) -> bool:
        """Check if updates are available for a package"""
        if method == InstallMethod.APT:
            try:
                result = subprocess.run(
                    ["apt", "list", "--upgradable", package_id],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0 and package_id in result.stdout
            except Exception:
                return False
        return False

    def get_available_updates(self) -> List[str]:
        """Get list of packages with available updates"""
        try:
            result = subprocess.run(
                ["apt", "list", "--upgradable"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return [line.split('/')[0] for line in result.stdout.strip().split('\n')[1:] if line]
        except Exception:
            pass
        return []


__all__ = ["InstallMethod", "InstallResult", "PackageManager"]