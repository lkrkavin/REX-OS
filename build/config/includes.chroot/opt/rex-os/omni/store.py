#!/usr/bin/env python3
"""REX Store source registry and safe application-catalog primitives.

This module deliberately does not execute downloaded installers. It provides
validated catalogue metadata and installer classification for later,
permission-gated integration with REX Omni's package/compatibility backends.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlsplit
import ipaddress
import re


class StoreSourceKind(str, Enum):
    REX_CATALOG = "rex_catalog"
    APT = "apt"
    FLATPAK = "flatpak"
    SNAP = "snap"
    MICROSOFT_STORE = "microsoft_store"
    WEBSITE = "website"
    GITHUB_RELEASE = "github_release"
    LOCAL_FILE = "local_file"


class InstallerFormat(str, Enum):
    DEB = "deb"
    RPM = "rpm"
    APPIMAGE = "appimage"
    FLATPAK_REF = "flatpakref"
    SNAP = "snap"
    WINDOWS_EXE = "exe"
    WINDOWS_MSI = "msi"
    ANDROID_APK = "apk"
    MACOS_DMG = "dmg"
    MACOS_PKG = "pkg"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class StoreSource:
    source_id: str
    display_name: str
    kind: StoreSourceKind
    description: str
    enabled_by_default: bool = False
    official: bool = False


@dataclass(frozen=True)
class StoreListing:
    app_id: str
    name: str
    description: str
    publisher: str
    version: str = ""
    categories: tuple[str, ...] = ()
    source_id: str = "rex"
    homepage: Optional[str] = None
    download_url: Optional[str] = None
    verified_publisher: bool = False

    def __post_init__(self) -> None:
        for field_name in ("app_id", "name", "description", "publisher", "source_id"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f"Invalid {field_name}")
        if self.homepage:
            validate_https_url(self.homepage)
        if self.download_url:
            validate_https_url(self.download_url)
        if any(not isinstance(c, str) or not c.strip() or len(c) > 64 for c in self.categories):
            raise ValueError("Invalid category")


@dataclass(frozen=True)
class InstallerArtifact:
    path: str
    format: InstallerFormat


SOURCES = (
    StoreSource("rex", "REX Catalogue", StoreSourceKind.REX_CATALOG,
                "Applications curated for REX OS.", True, True),
    StoreSource("apt", "Linux APT repositories", StoreSourceKind.APT,
                "Packages supplied by configured Debian-compatible repositories.", True, True),
    StoreSource("flathub", "Flathub", StoreSourceKind.FLATPAK,
                "Flatpak applications from the configured Flathub remote.", False, True),
    StoreSource("snap", "Snap Store", StoreSourceKind.SNAP,
                "Snap applications where snapd is supported.", False, True),
    StoreSource("microsoft", "Microsoft Store", StoreSourceKind.MICROSOFT_STORE,
                "External Microsoft Store links; direct Linux installation is not assumed.", False, True),
    StoreSource("web", "Developer websites", StoreSourceKind.WEBSITE,
                "Installer downloads from HTTPS developer websites.", True, False),
    StoreSource("github", "GitHub Releases", StoreSourceKind.GITHUB_RELEASE,
                "Release assets published by project maintainers.", False, False),
    StoreSource("local", "Local installer files", StoreSourceKind.LOCAL_FILE,
                "Installer files selected by the user.", True, False),
)


def validate_https_url(url: str) -> str:
    """Accept public HTTPS URLs only; reject credentials and local/private hosts."""
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("Invalid URL")
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise ValueError("Only HTTPS URLs are accepted")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing credentials are not accepted")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("Local hosts are not accepted")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address and (not address.is_global):
        raise ValueError("Non-public IP addresses are not accepted")
    return url


def classify_installer(path: str) -> InstallerArtifact:
    """Classify a user-selected installer by extension; never execute it."""
    if not isinstance(path, str) or not path.strip() or len(path) > 4096:
        raise ValueError("Invalid installer path")
    suffix = Path(path).suffix.lower().lstrip(".")
    formats = {item.value: item for item in InstallerFormat if item is not InstallerFormat.UNKNOWN}
    return InstallerArtifact(path=path, format=formats.get(suffix, InstallerFormat.UNKNOWN))


class StoreCatalog:
    """Small in-memory catalogue with explicit source enablement."""

    def __init__(self, sources: Iterable[StoreSource] = SOURCES):
        source_list = tuple(sources)
        self._sources = {source.source_id: source for source in source_list}
        if len(self._sources) != len(source_list):
            raise ValueError("Duplicate store source ID")
        self._enabled = {s.source_id for s in source_list if s.enabled_by_default}
        self._listings: dict[str, StoreListing] = {}

    def list_sources(self) -> list[StoreSource]:
        return list(self._sources.values())

    def enabled_source_ids(self) -> list[str]:
        return sorted(self._enabled)

    def set_source_enabled(self, source_id: str, enabled: bool) -> None:
        if source_id not in self._sources:
            raise KeyError(source_id)
        if enabled:
            self._enabled.add(source_id)
        else:
            self._enabled.discard(source_id)

    def add_listing(self, listing: StoreListing) -> None:
        if listing.source_id not in self._sources:
            raise ValueError("Unknown catalogue source")
        self._listings[listing.app_id] = listing

    def search(self, query: str = "", category: Optional[str] = None) -> list[StoreListing]:
        if not isinstance(query, str) or len(query) > 256:
            raise ValueError("Invalid search query")
        needle = query.casefold().strip()
        results = []
        for listing in self._listings.values():
            if listing.source_id not in self._enabled:
                continue
            haystack = " ".join((listing.name, listing.description, listing.publisher)).casefold()
            if needle and needle not in haystack:
                continue
            if category and category.casefold() not in {c.casefold() for c in listing.categories}:
                continue
            results.append(listing)
        return sorted(results, key=lambda item: item.name.casefold())
