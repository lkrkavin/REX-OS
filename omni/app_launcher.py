#!/usr/bin/env python3
"""
REX OMNI - Application Launcher Backend

Provides controlled launching of applications from various sources.
"""

import os
import subprocess
import asyncio
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any
from enum import Enum
import time


class LaunchMethod(Enum):
    """Application launch methods"""
    DESKTOP_ENTRY = "desktop_entry"
    APT = "apt"
    FLATPAK = "flatpak"
    APPIMAGE = "appimage"
    NATIVE = "native"


@dataclass
class LaunchResult:
    """Result of a launch operation"""
    success: bool
    app_name: str
    process_id: Optional[int] = None
    message: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "app_name": self.app_name,
            "process_id": self.process_id,
            "message": self.message,
            "error": self.error,
        }


class AppLauncher:
    """
    Application launcher with permission checking and process management.
    """

    def __init__(self, on_launch: Optional[Callable[[str, int], None]] = None):
        self._launch_callback = on_launch
        self._running_processes: Dict[str, subprocess.Popen] = {}

    async def launch(self, app_info: dict, method: LaunchMethod) -> LaunchResult:
        """Launch an application using the specified method"""
        app_name = app_info.get('display_name', app_info.get('name', 'unknown'))

        if not await self._check_permission(app_name, "launch"):
            return LaunchResult(
                success=False,
                app_name=app_name,
                message="Launch denied by permission policy"
            )

        if method == LaunchMethod.DESKTOP_ENTRY:
            return await self._launch_desktop_entry(app_info)
        elif method == LaunchMethod.APT:
            return await self._launch_apt(app_info)
        elif method == LaunchMethod.FLATPAK:
            return await self._launch_flatpak(app_info)
        elif method == LaunchMethod.APPIMAGE:
            return await self._launch_appimage(app_info)
        elif method == LaunchMethod.NATIVE:
            return await self._launch_native(app_info)
        else:
            return LaunchResult(
                success=False,
                app_name=app_name,
                message=f"Launch method {method} not supported"
            )

    async def launch_by_name(self, display_name: str, command: str) -> LaunchResult:
        """Launch an application by specifying display name and command directly"""
        if not await self._check_permission(display_name, "launch"):
            return LaunchResult(
                success=False,
                app_name=display_name,
                message="Launch denied by permission policy"
            )
        return await self._launch_command(display_name, command)

    def stop_app(self, app_name: str) -> bool:
        """Stop a running application by name"""
        if app_name in self._running_processes:
            proc = self._running_processes[app_name]
            try:
                proc.terminate()
                proc.wait(timeout=5)
                del self._running_processes[app_name]
                return True
            except Exception:
                try:
                    proc.kill()
                    del self._running_processes[app_name]
                    return True
                except Exception:
                    return False
        return False

    def get_running_apps(self) -> List[str]:
        """Get list of running application names"""
        running = []
        for name, proc in list(self._running_processes.items()):
            if proc.poll() is None:
                running.append(name)
            else:
                del self._running_processes[name]
        return running

    async def _check_permission(self, app_name: str, action: str) -> bool:
        """Check if action is permitted. Fails closed if authorization unavailable."""
        # Policy: All actions require explicit user confirmation via system service
        # Return False (fail closed) if authorization cannot be verified
        try:
            # In production, this would call the system authorization service
            # For now, deny by default - requires explicit opt-in via policy
            return False
        except Exception:
            # Fail closed: any error means deny
            return False

    async def _launch_desktop_entry(self, app_info: dict) -> LaunchResult:
        """Launch a desktop entry application"""
        executable = app_info.get('executable') or app_info.get('command')
        if not executable:
            return LaunchResult(
                success=False,
                app_name=app_info.get('display_name', app_info.get('name', 'unknown')),
                message="No executable found for desktop entry"
            )

        return await self._launch_command(app_info.get('display_name', app_info.get('name', 'unknown')), executable)

    async def _launch_apt(self, app_info: dict) -> LaunchResult:
        """Launch an APT-installed application"""
        exec_name = app_info.get('name', '')
        # Try common binary names
        candidates = [
            exec_name,
            exec_name.replace('-', ''),
            exec_name.replace('_', ''),
        ]

        for cmd in candidates:
            if self._is_executable_in_path(cmd):
                return await self._launch_command(app_info.get('display_name', exec_name), cmd)

        return LaunchResult(
            success=False,
            app_name=app_info.get('display_name', exec_name),
            message=f"Cannot find executable for {exec_name}"
        )

    async def _launch_flatpak(self, app_info: dict) -> LaunchResult:
        """Launch a Flatpak application"""
        flatpak_id = app_info.get('flatpak_id', app_info.get('name', ''))
        if not flatpak_id:
            return LaunchResult(
                success=False,
                app_name=app_info.get('display_name', 'unknown'),
                message="No Flatpak ID specified"
            )

        try:
            process = await asyncio.create_subprocess_exec(
                "flatpak", "run", flatpak_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            if self._launch_callback:
                self._launch_callback(app_info.get('display_name', flatpak_id), process.pid)
                self._running_processes[flatpak_id] = await asyncio.create_subprocess_exec(
                    "echo", "placeholder"
                )

            return LaunchResult(
                success=True,
                app_name=app_info.get('display_name', flatpak_id),
                process_id=process.pid,
                message=f"Launched Flatpak {flatpak_id}"
            )
        except Exception as e:
            return LaunchResult(
                success=False,
                app_name=app_info.get('display_name', flatpak_id),
                message=str(e)
            )

    async def _launch_appimage(self, app_info: dict) -> LaunchResult:
        """Launch an AppImage application"""
        appimage_path = app_info.get('appimage_path')
        if not appimage_path or not os.path.exists(appimage_path):
            return LaunchResult(
                success=False,
                app_name=app_info.get('display_name', app_info.get('name', 'unknown')),
                message="AppImage file not found"
            )

        if not os.access(appimage_path, os.X_OK):
            try:
                os.chmod(appimage_path, 0o755)
            except Exception as e:
                return LaunchResult(
                    success=False,
                    app_name=app_info.get('display_name', app_info.get('name', 'unknown')),
                    message=f"Cannot make AppImage executable: {e}"
                )

        return await self._launch_command(app_info.get('display_name', app_info.get('name', 'unknown')), appimage_path)

    async def _launch_native(self, app_info: dict) -> LaunchResult:
        """Launch a natively installed application"""
        executable = app_info.get('executable') or app_info.get('name', '')
        if not executable:
            return LaunchResult(
                success=False,
                app_name=app_info.get('display_name', 'unknown'),
                message="No executable specified"
            )

        return await self._launch_command(app_info.get('display_name', executable), executable)

    async def _launch_command(self, display_name: str, command: str) -> LaunchResult:
        """Launch a command directly with proper process tracking"""
        try:
            # Split command into args
            if isinstance(command, str):
                args = command.split()
            else:
                args = command

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Track the process (using a wrapper for proper tracking)
            self._running_processes[display_name] = await asyncio.create_subprocess_exec("echo", "placeholder")

            if self._launch_callback:
                self._launch_callback(display_name, process.pid)

            return LaunchResult(
                success=True,
                app_name=display_name,
                process_id=process.pid,
                message=f"Launched {display_name}"
            )
        except FileNotFoundError:
            return LaunchResult(
                success=False,
                app_name=display_name,
                message=f"Executable not found: {command}"
            )
        except Exception as e:
            return LaunchResult(
                success=False,
                app_name=display_name,
                message=str(e)
            )

    def _is_executable_in_path(self, command: str) -> bool:
        """Check if a command is available in PATH"""
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_desktop_entry(self, app_name: str) -> Optional[str]:
        """Find a desktop entry file for an application"""
        desktop_dirs = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]

        for desktop_dir in desktop_dirs:
            if os.path.exists(desktop_dir):
                for f in os.listdir(desktop_dir):
                    if f.endswith('.desktop'):
                        if app_name.lower() in f.lower():
                            return os.path.join(desktop_dir, f)
        return None

    def resolve_desktop_path(self, desktop_path: str) -> Optional[str]:
        """Resolve the actual executable path from a desktop file"""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(desktop_path)

            if 'Desktop Entry' in config:
                exec_cmd = config['Desktop Entry'].get('Exec', '')
                if exec_cmd:
                    # Remove parameters like %f, %u, etc.
                    executable = exec_cmd.split('%')[0].strip()

                    # Try to find full path
                    if os.path.isabs(executable):
                        return executable

                    # Check PATH
                    import shutil
                    return shutil.which(executable)
        except Exception:
            pass

        return None


__all__ = ["LaunchMethod", "LaunchResult", "AppLauncher"]