#!/usr/bin/env python3
"""
REX OS OMNI - Application Ecosystem Manager

Provides application discovery, installation, launching, and management
for Debian APT, Flatpak, and AppImage formats, plus REX Store catalogue APIs.
"""

from omni.app_catalog import AppCatalog, ApplicationInfo, Category
from omni.package_manager import PackageManager, InstallResult, InstallMethod
from omni.app_launcher import AppLauncher, LaunchResult
from omni.omni_core import OMNICore, OMNIStatus
from omni.store import (
    StoreCatalog, StoreListing, StoreSource, StoreSourceKind,
    InstallerArtifact, InstallerFormat, classify_installer, validate_https_url,
)

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
    "StoreCatalog",
    "StoreListing",
    "StoreSource",
    "StoreSourceKind",
    "InstallerArtifact",
    "InstallerFormat",
    "classify_installer",
    "validate_https_url",
]
