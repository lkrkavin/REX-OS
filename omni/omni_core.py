#!/usr/bin/env python3
"""
REX OMNI - Core Integration Module

Main integration point connecting catalog, package manager, launcher, and AI Core.
"""

import os
import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

from .app_catalog import AppCatalog, ApplicationInfo, Category
from .package_manager import PackageManager, InstallResult, InstallMethod
from .app_launcher import AppLauncher, LaunchResult, LaunchMethod


class OMNIStatus(Enum):
    """OMNI system status"""
    INITIALIZING = "initializing"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class OMNIResult:
    """Generic OMNI operation result"""
    success: bool
    message: str
    data: Any = None

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
        }


class OMNICore:
    """
    Main OMNI core - central coordinator for all OMNI operations.
    """

    def __init__(self, on_status_change: Optional[Callable[[OMNIStatus, str], None]] = None):
        self._status = OMNIStatus.INITIALIZING
        self._status_callback = on_status_change
        self._logger = logging.getLogger("rex.omni")

        # Core components
        self._catalog = AppCatalog()
        self._package_manager = PackageManager()
        self._app_launcher = AppLauncher()

        # AI Core integration (optional)
        self._ai_core = None
        self._conversation_manager = None

    def set_ai_core(self, ai_core):
        """Set AI Core reference for integration"""
        self._ai_core = ai_core

    def set_conversation_manager(self, manager):
        """Set conversation manager for voice/text integration"""
        self._conversation_manager = manager

    def initialize(self) -> bool:
        """Initialize OMNI and all subsystems"""
        self._set_status(OMNIStatus.INITIALIZING, "Initializing OMNI...")

        try:
            # Initialize catalog
            if not self._catalog.initialize():
                self._set_status(OMNIStatus.ERROR, "Failed to initialize application catalog")
                return False

            self._set_status(OMNIStatus.READY, "OMNI ready")
            return True
        except Exception as e:
            self._set_status(OMNIStatus.ERROR, f"Initialization error: {e}")
            return False

    def _set_status(self, status: OMNIStatus, message: str):
        """Update status and notify callback"""
        self._status = status
        if self._status_callback:
            self._status_callback(status, message)

    # ============================================================
    # Application Discovery
    # ============================================================

    def search_applications(self, query: str, categories: Optional[List[Category]] = None) -> List[ApplicationInfo]:
        """Search for applications by name/description"""
        return self._catalog.search(query, categories)

    def get_applications_by_category(self, category: Category) -> List[ApplicationInfo]:
        """Get applications by category"""
        return self._catalog.get_by_category(category)

    def get_installed_applications(self) -> List[ApplicationInfo]:
        """Get all installed applications"""
        return self._catalog.get_installed()

    def get_application(self, name: str) -> Optional[ApplicationInfo]:
        """Get a specific application by name"""
        for app in self._catalog._applications:
            if app.name == name or app.display_name == name:
                return app
        return None

    def get_available_install_methods(self) -> List[str]:
        """Get list of available installation methods"""
        return self._catalog.get_available_methods()

    # ============================================================
    # Package Management
    # ============================================================

    async def install_application(self, app_info: ApplicationInfo, on_progress: Optional[Callable[[float, str], None]] = None) -> InstallResult:
        """Install an application"""
        self._set_status(OMNIStatus.BUSY, f"Installing {app_info.display_name}...")

        if on_progress:
            self._package_manager._progress_callback = on_progress

        method = self._determine_install_method(app_info)
        result = await self._package_manager.install(app_info.package_id or app_info.name, method)

        if result.success:
            self._set_status(OMNIStatus.READY, f"Installed {app_info.display_name}")
            # Refresh catalog
            self._catalog.initialize()
        else:
            self._set_status(OMNIStatus.ERROR, f"Install failed: {result.message}")

        return result

    async def uninstall_application(self, app_info: ApplicationInfo, on_progress: Optional[Callable[[float, str], None]] = None) -> InstallResult:
        """Uninstall an application"""
        self._set_status(OMNIStatus.BUSY, f"Uninstalling {app_info.display_name}...")

        if on_progress:
            self._package_manager._progress_callback = on_progress

        method = self._determine_install_method(app_info)
        result = await self._package_manager.uninstall(app_info.package_id or app_info.flatpak_id or app_info.name, method)

        if result.success:
            self._set_status(OMNIStatus.READY, f"Uninstalled {app_info.display_name}")
            self._catalog.initialize()
        else:
            self._set_status(OMNIStatus.ERROR, f"Uninstall failed: {result.message}")

        return result

    def check_updates(self, app_info: ApplicationInfo) -> bool:
        """Check if updates are available for an application"""
        method = self._determine_install_method(app_info)
        return self._package_manager.check_updates_available(app_info.package_id or app_info.name, method)

    def get_available_updates(self) -> List[str]:
        """Get all packages with available updates"""
        return self._package_manager.get_available_updates()

    # ============================================================
    # Application Launching
    # ============================================================

    async def launch_application(self, app_info: ApplicationInfo) -> LaunchResult:
        """Launch an application"""
        self._set_status(OMNIStatus.BUSY, f"Launching {app_info.display_name}...")

        method = self._determine_launch_method(app_info)
        result = await self._app_launcher.launch(app_info.to_dict(), method)

        if result.success:
            self._set_status(OMNIStatus.READY, f"Launched {app_info.display_name}")
        else:
            self._set_status(OMNIStatus.ERROR, f"Launch failed: {result.message}")

        return result

    def get_running_applications(self) -> List[str]:
        """Get list of running application names"""
        return self._app_launcher.get_running_apps()

    def stop_application(self, app_name: str) -> bool:
        """Stop a running application"""
        return self._app_launcher.stop_app(app_name)

    # ============================================================
    # AI Integration (for voice commands, etc.)
    # ============================================================

    async def handle_ai_command(self, command: str) -> OMNIResult:
        """Handle a natural language command from AI"""
        if not self._ai_core:
            return OMNIResult(success=False, message="AI Core not available")

        try:
            # Analyze intent
            intent = await self._analyze_intent(command)

            if intent == "install":
                app_name = await self._extract_app_name(command)
                apps = self.search_applications(app_name)
                if apps:
                    result = await self.install_application(apps[0])
                    return OMNIResult(
                        success=result.success,
                        message=result.message,
                        data=result.to_dict()
                    )
            elif intent == "uninstall":
                app_name = await self._extract_app_name(command)
                apps = self.search_applications(app_name)
                if apps:
                    result = await self.uninstall_application(apps[0])
                    return OMNIResult(
                        success=result.success,
                        message=result.message,
                        data=result.to_dict()
                    )
            elif intent == "launch":
                app_name = await self._extract_app_name(command)
                apps = self.search_applications(app_name)
                if apps:
                    result = await self.launch_application(apps[0])
                    return OMNIResult(
                        success=result.success,
                        message=result.message,
                        data=result.to_dict()
                    )
            elif intent == "search":
                query = command
                apps = self.search_applications(query)
                return OMNIResult(
                    success=True,
                    message=f"Found {len(apps)} applications",
                    data=[a.to_dict() for a in apps]
                )

            return OMNIResult(success=False, message="Could not understand command")
        except Exception as e:
            return OMNIResult(success=False, message=f"Error handling command: {e}")

    async def _analyze_intent(self, command: str) -> str:
        """Analyze intent from natural language"""
        cmd_lower = command.lower()
        if any(w in cmd_lower for w in ["install", "add", "download", "get"]):
            return "install"
        if any(w in cmd_lower for w in ["uninstall", "remove", "delete", "delete"]):
            return "uninstall"
        if any(w in cmd_lower for w in ["launch", "start", "open", "run"]):
            return "launch"
        if any(w in cmd_lower for w in ["find", "search", "look for", "list"]):
            return "search"
        return "unknown"

    async def _extract_app_name(self, command: str) -> str:
        """Extract application name from command"""
        # Simple extraction - in production, use NLP
        words = command.lower().split()
        # Remove common intent words
        stop_words = {"install", "uninstall", "remove", "delete", "launch", "start", "open", "run", "find", "search", "the", "a", "an", "app", "application", "please"}
        return " ".join([w for w in words if w not in stop_words])

    # ============================================================
    # Helper Methods
    # ============================================================

    def _determine_install_method(self, app_info: ApplicationInfo) -> InstallMethod:
        """Determine the best installation method for an app"""
        if app_info.install_method == "flatpak" or app_info.flatpak_id:
            return InstallMethod.FLATPAK
        elif app_info.install_method == "appimage" or app_info.appimage_path:
            return InstallMethod.APPIMAGE
        else:
            return InstallMethod.APT

    def _determine_launch_method(self, app_info: ApplicationInfo) -> LaunchMethod:
        """Determine the best launch method for an app"""
        if app_info.install_method == "flatpak":
            return LaunchMethod.FLATPAK
        elif app_info.install_method == "appimage":
            return LaunchMethod.APPIMAGE
        elif app_info.executable or app_info.install_method == "native":
            return LaunchMethod.NATIVE
        elif app_info.install_method == "apt":
            return LaunchMethod.APT
        else:
            return LaunchMethod.DESKTOP_ENTRY

    def get_status(self) -> OMNIStatus:
        """Get current OMNI status"""
        return self._status


__all__ = ["OMNIStatus", "OMNIResult", "OMNICore"]