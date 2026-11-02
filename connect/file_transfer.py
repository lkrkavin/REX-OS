#!/usr/bin/env python3
"""
REX CONNECT - File Transfer Manager

Secure file transfer between paired devices.
Validates paths, prevents traversal attacks, requires confirmation.
"""

import asyncio
import os
import time
import uuid
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from pathlib import Path
import threading


class TransferStatus(Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DENIED = "denied"


@dataclass
class TransferInfo:
    """Information about a file transfer"""
    transfer_id: str
    direction: str  # "upload" (from device) or "download" (to device)
    source_device: str
    target_device: str
    filename: str
    filepath: str
    filesize: int
    status: TransferStatus = TransferStatus.PENDING
    progress: int = 0  # bytes transferred
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    requires_confirmation: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class FileTransferManager:
    """
    Manages secure file transfers between paired devices.
    - Validates paths to prevent traversal attacks
    - Never overwrites files silently
    - Requires user confirmation
    - Shows transfer progress
    """

    DEFAULT_TRANSFER_ROOT = "transfers"

    def __init__(self, base_path: str = None):
        self._base_path = Path(base_path or os.path.expanduser("~/REX-Transfers"))
        self._transfers: Dict[str, TransferInfo] = {}
        self._lock = threading.RLock()
        self._callbacks: List[Callable[[str, TransferInfo], None]] = []

        # Create base transfer directory
        self._base_path.mkdir(parents=True, exist_ok=True)

    def register_callback(self, callback: Callable[[str, TransferInfo], None]):
        """Register callback for transfer status changes"""
        with self._lock:
            self._callbacks.append(callback)

    def _sanitize_filename(self, filename: str) -> Optional[str]:
        """
        Sanitize and validate filename to prevent path traversal.
        Returns sanitized filename or None if invalid.
        Rejects any path that attempts traversal - does not sanitize.
        """
        if not filename:
            return None

        # Reject if path contains any directory separators
        if '/' in filename or '\\' in filename:
            return None

        # Reject if path contains parent directory navigation
        if '..' in filename:
            return None

        # Check for null bytes
        if '\x00' in filename:
            return None

        # Check for other suspicious patterns
        suspicious = ['~', '$', '|', '`', ';', '&', '\n', '\r']
        if any(s in filename for s in suspicious):
            return None

        # Check for URL-encoded traversal attempts
        if '%' in filename:
            return None

        # Limit length
        clean_name = filename[:255] if len(filename) > 255 else filename

        return clean_name if clean_name else None

    def _is_safe_path(self, filepath: str) -> bool:
        """Check if path is safe (within allowed directory)"""
        try:
            resolved = Path(filepath).resolve()
            base = self._base_path.resolve()
            resolved.relative_to(base)
            return True
        except (ValueError, OSError):
            return False

    def validate_transfer_request(
        self,
        transfer_id: str,
        filename: str,
        filesize: int,
        source_device: str,
        target_device: str,
        requires_confirmation: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a file transfer request.
        Returns validated info dict or None if invalid.
        """
        clean_name = self._sanitize_filename(filename)
        if not clean_name:
            return None

        # Create safe filepath
        filepath = self._base_path / clean_name

        # Handle name conflicts - don't overwrite silently
        if filepath.exists():
            base = filepath.stem
            ext = filepath.suffix
            counter = 1
            while filepath.exists():
                new_name = f"{base}_{counter}{ext}"
                filepath = self._base_path / new_name
                counter += 1
            clean_name = filepath.name

        if not self._is_safe_path(str(filepath)):
            return None

        return {
            "transfer_id": transfer_id,
            "filename": clean_name,
            "filepath": str(filepath),
            "filesize": filesize,
            "source_device": source_device,
            "target_device": target_device,
            "requires_confirmation": requires_confirmation
        }

    def create_transfer_request(
        self,
        filename: str,
        filesize: int,
        source_device: str,
        target_device: str,
        requires_confirmation: bool = True
    ) -> Optional[TransferInfo]:
        """
        Create a new transfer request.
        Returns TransferInfo or None if request is invalid.
        """
        transfer_id = f"xf_{uuid.uuid4().hex[:12]}"

        validated = self.validate_transfer_request(
            transfer_id, filename, filesize, source_device, target_device, requires_confirmation
        )

        if not validated:
            return None

        transfer = TransferInfo(
            transfer_id=transfer_id,
            direction="upload" if source_device != "local" else "download",
            source_device=source_device,
            target_device=target_device,
            filename=validated["filename"],
            filepath=validated["filepath"],
            filesize=filesize,
            requires_confirmation=requires_confirmation
        )

        with self._lock:
            self._transfers[transfer_id] = transfer

        return transfer

    def accept_transfer(self, transfer_id: str, confirmed: bool = True) -> bool:
        """Accept or reject a pending transfer"""
        with self._lock:
            if transfer_id not in self._transfers:
                return False

            transfer = self._transfers[transfer_id]
            if not transfer.requires_confirmation and not confirmed:
                return False  # Can't override auto-reject

            transfer.status = TransferStatus.DENIED if not confirmed else TransferStatus.PREPARING
            transfer.completed_at = time.time()

            self._notify_change(transfer_id, transfer)
            return True

    def start_transfer(self, transfer_id: str) -> bool:
        """Start the actual transfer"""
        with self._lock:
            if transfer_id not in self._transfers:
                return False

            transfer = self._transfers[transfer_id]
            if transfer.status != TransferStatus.PREPARING:
                return False

            transfer.status = TransferStatus.TRANSFERRING
            transfer.started_at = time.time()
            transfer.progress = 0

            self._notify_change(transfer_id, transfer)
            return True

    def update_progress(self, transfer_id: str, bytes_transferred: int):
        """Update transfer progress"""
        with self._lock:
            if transfer_id in self._transfers:
                transfer = self._transfers[transfer_id]
                transfer.progress = bytes_transferred

                if transfer.progress >= transfer.filesize:
                    transfer.status = TransferStatus.COMPLETED
                    transfer.completed_at = time.time()

                self._notify_change(transfer_id, transfer)

    def cancel_transfer(self, transfer_id: str) -> bool:
        """Cancel an active transfer"""
        with self._lock:
            if transfer_id in self._transfers:
                transfer = self._transfers[transfer_id]
                transfer.status = TransferStatus.CANCELLED
                transfer.completed_at = time.time()

                self._notify_change(transfer_id, transfer)
                return True
            return False

    def get_transfer(self, transfer_id: str) -> Optional[TransferInfo]:
        """Get transfer info by ID"""
        with self._lock:
            return self._transfers.get(transfer_id)

    def get_pending_transfers(self) -> List[TransferInfo]:
        """Get all pending transfers awaiting confirmation"""
        with self._lock:
            return [t for t in self._transfers.values() if t.status == TransferStatus.PENDING]

    def get_active_transfers(self) -> List[TransferInfo]:
        """Get all actively transferring files"""
        with self._lock:
            return [t for t in self._transfers.values() if t.status == TransferStatus.TRANSFERRING]

    def get_completed_transfers(self, limit: int = 50) -> List[TransferInfo]:
        """Get recently completed transfers"""
        with self._lock:
            completed = [
                t for t in self._transfers.values()
                if t.status in (TransferStatus.COMPLETED, TransferStatus.DENIED, TransferStatus.CANCELLED, TransferStatus.FAILED)
            ]
            completed.sort(key=lambda t: (t.completed_at or 0), reverse=True)
            return completed[:limit]

    def get_received_file_path(self, transfer_id: str) -> Optional[str]:
        """Get the final file path for a completed download transfer"""
        transfer = self.get_transfer(transfer_id)
        if transfer and transfer.status == TransferStatus.COMPLETED and transfer.direction == "download":
            return transfer.filepath
        return None

    def _notify_change(self, transfer_id: str, transfer: TransferInfo):
        """Notify callbacks of transfer status change"""
        for callback in self._callbacks:
            try:
                callback(transfer_id, transfer)
            except Exception:
                pass

    def clear_old_transfers(self, max_age_days: int = 30):
        """Clear transfer records older than specified days"""
        cutoff = time.time() - (max_age_days * 86400)
        with self._lock:
            to_remove = [
                tid for tid, t in self._transfers.items()
                if t.completed_at and t.completed_at < cutoff
            ]
            for tid in to_remove:
                del self._transfers[tid]


# Global file transfer manager instance
_global_transfer_manager: Optional[FileTransferManager] = None


def get_transfer_manager(base_path: str = None) -> FileTransferManager:
    """Get global file transfer manager instance"""
    global _global_transfer_manager
    if _global_transfer_manager is None:
        _global_transfer_manager = FileTransferManager(base_path)
    return _global_transfer_manager