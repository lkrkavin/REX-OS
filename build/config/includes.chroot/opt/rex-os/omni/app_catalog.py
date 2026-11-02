#!/usr/bin/env python3
"""
REX OMNI - Application Catalog

Provides application discovery, search, and metadata management.
Supports Debian APT repository, Flatpak, and local application detection.
"""

import os
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
from pathlib import Path


class Category(Enum):
    """Application categories"""
    PRODUCTIVITY = "productivity"
    DEVELOPMENT = "development"
    INTERNET = "internet"
    MULTIMEDIA = "multimedia"
    EDUCATION = "education"
    UTILITIES = "utilities"
    SYSTEM = "system"
    GAMES = "games"
    OTHER = "other"


@dataclass
class ApplicationInfo:
    """Information about an application"""
    name: str
    display_name: str
    description: str
    icon_path: Optional[str]
    version: str
    categories: List[Category]
    install_method: str  # 'apt', 'flatpak', 'appimage', 'native'
    package_id: Optional[str] = None
    flatpak_id: Optional[str] = None
    appimage_path: Optional[str] = None
    executable: Optional[str] = None
    installed: bool = False
    last_updated: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "icon_path": self.icon_path,
            "version": self.version,
            "categories": [c.value for c in self.categories],
            "install_method": self.install_method,
            "package_id": self.package_id,
            "flatpak_id": self.flatpak_id,
            "appimage_path": self.appimage_path,
            "executable": self.executable,
            "installed": self.installed,
            "last_updated": self.last_updated,
        }


class AppCatalog:
    """
    Application catalog for discovering, searching, and managing applications.
    """

    APT_CATEGORIES = {
        "apt": {
            "productivity": ["libreoffice", "abiword", "gnumeric", "thunderbird"],
            "development": ["git", "vim", "emacs", "build-essential", "python3-pip"],
            "internet": ["firefox-esr", "chromium", "thunderbird", "transmission"],
            "multimedia": ["vlc", "gimp", "audacity", "kdenlive", "ffmpeg"],
            "education": ["geogebra", "stellarium", "scratch"],
            "utilities": ["bleachbit", "htop", "tree", "rsync", "curl"],
            "system": ["systemd", "udev", "linux-image-amd64"],
            "games": ["games-games", "steam"],
        },
    }

    def __init__(self, cache_path: str = "/var/lib/rex/omni_cache.db"):
        self.cache_path = cache_path
        self._applications: List[ApplicationInfo] = []
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the catalog by detecting available systems"""
        try:
            self._detect_installed_apps()
            self._initialized = True
            return True
        except Exception:
            return False

    def _detect_installed_apps(self) -> List[ApplicationInfo]:
        """Detect installed applications on the system"""
        apps = []

        # Check for APT packages
        apt_result = self._query_apt_packages()
        apps.extend(apt_result)

        # Check for Flatpak
        flatpak_apps = self._query_flatpak_packages()
        apps.extend(flatpak_apps)

        # Check for AppImage
        appimage_apps = self._query_appimage_packages()
        apps.extend(appimage_apps)

        # Check for desktop entries
        desktop_apps = self._query_desktop_entries()
        apps.extend(desktop_apps)

        self._applications = apps
        return apps

    def _query_apt_packages(self) -> List[ApplicationInfo]:
        """Query installed APT packages"""
        apps = []
        try:
            result = subprocess.run(
                ["dpkg", "-l"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n')[5:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 3:
                        pkg_name = parts[1]
                        if pkg_name and not pkg_name.startswith('lib'):
                            # Try to find icon and description
                            icon_path = self._find_package_icon(pkg_name)
                            apps.append(ApplicationInfo(
                                name=pkg_name,
                                display_name=pkg_name.replace('-', ' ').title(),
                                description=f"APT package: {pkg_name}",
                                icon_path=icon_path,
                                version=parts[2] if len(parts) > 2 else "unknown",
                                categories=self._categorize_package(pkg_name),
                                install_method="apt",
                                package_id=pkg_name,
                                installed=True
                            ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return apps

    def _query_flatpak_packages(self) -> List[ApplicationInfo]:
        """Query installed Flatpak packages"""
        apps = []
        try:
            result = subprocess.run(
                ["flatpak", "list", "--app", "--columns=application,name,version"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                for line in result.stdout.strip().split('\n')[1:]:
                    if line.strip():
                        parts = line.split('|')
                        if len(parts) >= 3:
                            flatpak_id = parts[0]
                            name = parts[1]
                            version = parts[2]

                            apps.append(ApplicationInfo(
                                name=flatpak_id,
                                display_name=name,
                                description=f"Flatpak: {name}",
                                icon_path=self._find_flatpak_icon(flatpak_id),
                                version=version,
                                categories=self._categorize_flatpak(flatpak_id),
                                install_method="flatpak",
                                flatpak_id=flatpak_id,
                                installed=True
                            ))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return apps

    def _query_appimage_packages(self) -> List[ApplicationInfo]:
        """Query AppImage applications"""
        apps = []
        appimage_dirs = [
            "/opt/appimages",
            "/Applications",
            os.path.expanduser("~/Applications"),
        ]

        for app_dir in appimage_dirs:
            if os.path.exists(app_dir):
                for f in os.listdir(app_dir):
                    if f.endswith('.AppImage'):
                        app_path = os.path.join(app_dir, f)
                        name = f.replace('.AppImage', '')

                        apps.append(ApplicationInfo(
                            name=name,
                            display_name=name,
                            description=f"AppImage: {name}",
                            icon_path=self._find_appimage_icon(app_path),
                            version="unknown",
                            categories=[Category.UTILITIES],
                            install_method="appimage",
                            appimage_path=app_path,
                            installed=True
                        ))

        return apps

    def _query_desktop_entries(self) -> List[ApplicationInfo]:
        """Query system desktop entries"""
        apps = []
        desktop_dirs = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]

        seen = set()
        for desktop_dir in desktop_dirs:
            if os.path.exists(desktop_dir):
                for f in os.listdir(desktop_dir):
                    if f.endswith('.desktop') and not f.startswith('.'):
                        desktop_path = os.path.join(desktop_dir, f)
                        app_info = self._parse_desktop_entry(desktop_path)
                        if app_info and app_info.name not in seen:
                            apps.append(app_info)
                            seen.add(app_info.name)

        return apps

    def _parse_desktop_entry(self, desktop_path: str) -> Optional[ApplicationInfo]:
        """Parse a .desktop file and create ApplicationInfo"""
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read(desktop_path)

            if 'Desktop Entry' in config:
                entry = config['Desktop Entry']
                name = entry.get('Name', os.path.basename(desktop_path).replace('.desktop', ''))

                if name in [a.name for a in self._applications if a.installed]:
                    return None  # Avoid duplicates

                categories = []
                if 'Categories' in entry:
                    for cat in entry['Categories'].split(';'):
                        cat_lower = cat.lower()
                        if 'utility' in cat_lower or 'tool' in cat_lower:
                            categories.append(Category.UTILITIES)
                        elif 'development' in cat_lower or 'programing' in cat_lower:
                            categories.append(Category.DEVELOPMENT)
                        elif 'education' in cat_lower or 'science' in cat_lower:
                            categories.append(Category.EDUCATION)
                        elif 'game' in cat_lower:
                            categories.append(Category.GAMES)

                if not categories:
                    categories = [Category.OTHER]

                exec_cmd = entry.get('Exec', '')
                executable = exec_cmd.split('%')[0].strip() if exec_cmd else None

                icon = entry.get('Icon', '')
                icon_path = self._resolve_icon(icon)

                return ApplicationInfo(
                    name=name,
                    display_name=name,
                    description=entry.get('Comment', ''),
                    icon_path=icon_path if icon_path else None,
                    version="installed",
                    categories=categories,
                    install_method="native",
                    executable=executable,
                    installed=True
                )
        except Exception:
            pass

        return None

    def _resolve_icon(self, icon_name: str) -> Optional[str]:
        """Resolve an icon name to a file path"""
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            return icon_name

        # Check common icon paths
        icon_paths = [
            f"/usr/share/icons/{icon_name}.png",
            f"/usr/share/icons/{icon_name}.svg",
            f"/usr/share/pixmaps/{icon_name}.png",
        ]

        for path in icon_paths:
            if os.path.exists(path):
                return path

        return None

    def _find_package_icon(self, package_name: str) -> Optional[str]:
        """Find icon for an APT package"""
        # Check for package-specific icons
        icon_paths = [
            f"/usr/share/icons/hicolor/scalable/apps/{package_name}.svg",
            f"/usr/share/icons/hicolor/48x48/apps/{package_name}.png",
            f"/usr/share/pixmaps/{package_name}.png",
        ]

        for path in icon_paths:
            if os.path.exists(path):
                return path

        return None

    def _find_flatpak_icon(self, flatpak_id: str) -> Optional[str]:
        """Find icon for a Flatpak application"""
        icon_name = flatpak_id.split('.')[0]
        return self._resolve_icon(icon_name)

    def _find_appimage_icon(self, appimage_path: str) -> Optional[str]:
        """Try to find AppImage icon using appimagetool or info"""
        return None

    def _categorize_package(self, name: str) -> List[Category]:
        """Categorize a package name"""
        name_lower = name.lower()

        for cat_name, packages in self.APT_CATEGORIES["apt"].items():
            if name_lower in [p.lower() for p in packages]:
                cat_map = {
                    "productivity": Category.PRODUCTIVITY,
                    "development": Category.DEVELOPMENT,
                    "internet": Category.INTERNET,
                    "multimedia": Category.MULTIMEDIA,
                    "education": Category.EDUCATION,
                    "utilities": Category.UTILITIES,
                    "system": Category.SYSTEM,
                    "games": Category.GAMES,
                }
                return [cat_map.get(cat_name, Category.OTHER)]

        return [Category.OTHER]

    def _categorize_flatpak(self, flatpak_id: str) -> List[Category]:
        """Categorize a Flatpak ID"""
        name_lower = flatpak_id.lower()
        if any(k in name_lower for k in ['thunderbird', 'firefox', 'chromium']):
            return [Category.INTERNET]
        if any(k in name_lower for k in ['libreoffice', 'writer', 'calc']):
            return [Category.PRODUCTIVITY]
        if any(k in name_lower for k in ['vlc', 'gimp', 'kdenlive']):
            return [Category.MULTIMEDIA]
        if any(k in name_lower for k in ['code', 'vscode', 'dev']):
            return [Category.DEVELOPMENT]
        return [Category.OTHER]

    def search(self, query: str, categories: Optional[List[Category]] = None) -> List[ApplicationInfo]:
        """Search applications by name or description"""
        query_lower = query.lower()
        results = []

        for app in self._applications:
            if (query_lower in app.name.lower() or
                query_lower in app.display_name.lower() or
                query_lower in app.description.lower()):
                if categories is None or any(c in app.categories for c in categories):
                    results.append(app)

        return results

    def get_by_category(self, category: Category) -> List[ApplicationInfo]:
        """Get applications by category"""
        return [app for app in self._applications if category in app.categories]

    def get_installed(self) -> List[ApplicationInfo]:
        """Get all installed applications"""
        return [app for app in self._applications if app.installed]

    def get_available_methods(self) -> List[str]:
        """Get list of available installation methods"""
        methods = set()

        if self._check_apt_available():
            methods.add("apt")
        if self._check_flatpak_available():
            methods.add("flatpak")
        if os.path.exists("/usr/bin/appimagetool") or True:  # AppImage runtime available
            methods.add("appimage")

        methods.add("native")  # Always available for installed apps
        return sorted(list(methods))

    def _check_apt_available(self) -> bool:
        """Check if APT is available"""
        try:
            subprocess.run(["which", "apt-get"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False

    def _check_flatpak_available(self) -> bool:
        """Check if Flatpak is available"""
        try:
            result = subprocess.run(
                ["which", "flatpak"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False


__all__ = ["Category", "ApplicationInfo", "AppCatalog"]