#!/usr/bin/env python3
"""Local REX settings export/import.

This is a local integrity-checked transfer format, NOT encrypted cloud sync.
Secrets and API credentials are deliberately excluded.
"""
import hashlib
import hmac
import json
import os
import tempfile
from pathlib import Path


class SyncService:
    VERSION = 1
    MAX_BUNDLE_BYTES = 1024 * 1024
    ALLOWED = {"ui_preferences.json", "automation_rules.json", "omni_favorites.json"}

    def __init__(self, base_dir=None):
        self.base = Path(base_dir or Path.home() / ".config/rex")

    @staticmethod
    def _canonical_payload(payload):
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def export_bundle(self, destination):
        files = {}
        for name in sorted(self.ALLOWED):
            path = self.base / name
            if path.is_file():
                try:
                    files[name] = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue

        payload = {"version": self.VERSION, "files": files}
        digest = hashlib.sha256(self._canonical_payload(payload)).hexdigest()
        bundle = {"payload": payload, "sha256": digest}

        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".rex-export-", dir=str(dest.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(bundle, handle, indent=2, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary, 0o600)
            os.replace(temporary, dest)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

        return {"path": str(dest), "files": sorted(files), "sha256": digest}

    def _load_and_validate_bundle(self, source):
        path = Path(source)
        try:
            raw_file = path.read_bytes()
        except OSError as exc:
            raise ValueError("Could not read sync bundle") from exc
        if len(raw_file) > self.MAX_BUNDLE_BYTES:
            raise ValueError("Sync bundle exceeds the size limit")
        try:
            bundle = json.loads(raw_file.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError("Sync bundle is not valid UTF-8 JSON") from exc

        if not isinstance(bundle, dict):
            raise ValueError("Sync bundle must be a JSON object")
        payload = bundle.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Sync bundle payload must be an object")
        if type(payload.get("version")) is not int or payload["version"] != self.VERSION:
            raise ValueError("Unsupported sync bundle version")
        files = payload.get("files")
        if not isinstance(files, dict):
            raise ValueError("Sync bundle files must be an object")
        if any(not isinstance(name, str) for name in files):
            raise ValueError("Sync bundle contains an invalid filename")
        if set(files) - self.ALLOWED:
            raise ValueError("Bundle contains unsupported files")

        supplied_digest = bundle.get("sha256")
        if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
            raise ValueError("Sync bundle checksum is missing or malformed")
        if any(ch not in "0123456789abcdef" for ch in supplied_digest):
            raise ValueError("Sync bundle checksum is malformed")
        expected_digest = hashlib.sha256(self._canonical_payload(payload)).hexdigest()
        if not hmac.compare_digest(expected_digest, supplied_digest):
            raise ValueError("Sync bundle checksum mismatch")
        return files

    def import_bundle(self, source):
        files = self._load_and_validate_bundle(source)
        self.base.mkdir(parents=True, exist_ok=True)
        written = []
        for name, data in files.items():
            target = self.base / name
            fd, temporary = tempfile.mkstemp(prefix=".rex-sync-", dir=str(self.base))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, 0o600)
                os.replace(temporary, target)
                written.append(name)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return written
