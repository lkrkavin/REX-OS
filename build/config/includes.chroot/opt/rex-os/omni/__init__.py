#!/usr/bin/env python3
"""
REX OS OMNI - Application Ecosystem Manager

Provides application discovery, installation, launching, and management
for Debian APT, Flatpak, and AppImage formats.
"""

from omni.app_catalog import AppCatalog, ApplicationInfo, Category
from omni.package_manager import PackageManager, InstallResult, InstallMethod
from omni.app_launcher import AppLauncher, LaunchResult
from omni.omni_core import OMNICore, OMNIStatus

__all__ = [
    "AppCatalog",
    "ApplicationInfo",
    "Category",
    "PackageManager",
    "InstallResult",
    "InstallMethod",
    "AppLauncher",
    "LaunchResult",
    "OMNICore",
    "OMNIStatus",
]