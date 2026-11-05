#!/usr/bin/env python3
"""Detect application compatibility paths without claiming foreign OS binaries run natively."""
import shutil,platform
from dataclasses import dataclass,asdict
@dataclass
class PlatformCapability:
 platform:str
 available:bool
 mode:str
 detail:str
class PlatformSupport:
 def detect(self):
  linux=platform.system()=="Linux";wine=shutil.which("wine") is not None
  flatpak=shutil.which("flatpak") is not None;waydroid=shutil.which("waydroid") is not None
  ssh=shutil.which("ssh") is not None
  return [
   PlatformCapability("Linux",linux,"native","Native Debian/Linux applications." if linux else "Not running on Linux."),
   PlatformCapability("Windows",wine,"compatibility" if wine else "not-installed","Wine compatibility layer detected; per-app compatibility varies." if wine else "Requires Wine/Bottles; compatibility varies by application."),
   PlatformCapability("Android",waydroid,"container" if waydroid else "not-installed","Waydroid detected." if waydroid else "Requires Waydroid and compatible kernel/session support."),
   PlatformCapability("macOS",False,"remote-supported","REX can manage a separately paired Mac over SSH; SSH client "+("is installed" if ssh else "is not installed")+". No Mac device is assumed paired. macOS apps do not run natively on Linux."),
  ]
 def report(self):return [asdict(item) for item in self.detect()]
