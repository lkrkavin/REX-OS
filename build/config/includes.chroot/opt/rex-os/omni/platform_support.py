#!/usr/bin/env python3
"""Detect application compatibility paths without claiming foreign OS binaries run natively."""
import os
import shutil
import platform
from dataclasses import dataclass, asdict

@dataclass
class PlatformCapability:
    platform: str
    available: bool
    mode: str
    detail: str

class PlatformSupport:
    def detect(self):
        linux = platform.system() == "Linux"
        wine = shutil.which("wine") is not None
        flatpak = shutil.which("flatpak") is not None
        waydroid = shutil.which("waydroid") is not None
        ssh = shutil.which("ssh") is not None
        return [
            PlatformCapability("Linux", linux, "native", "Native Debian/Linux applications." if linux else "Not running on Linux."),
            PlatformCapability("Windows", wine, "compatibility" if wine else "not-installed", "Wine compatibility layer detected." if wine else "Requires Wine/Bottles; compatibility varies by application."),
            PlatformCapability("Android", waydroid, "container" if waydroid else "not-installed", "Waydroid detected." if waydroid else "Requires Waydroid and compatible kernel/session support."),
            PlatformCapability("macOS", ssh, "remote-device" if ssh else "unavailable", "Can connect to a separately owned Mac over SSH after explicit pairing; macOS apps do not run natively on Linux."),
        ]
    def report(self):
        return [asdict(item) for item in self.detect()]
