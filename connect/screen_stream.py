#!/usr/bin/env python3
"""
REX CONNECT - Screen Stream Manager

Handles screen sharing with user consent and efficient encoding.
Designed for 4GB RAM hardware constraints.
"""

import asyncio
import time
import base64
import io
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum


class StreamConfig:
    """Configuration for screen streaming"""
    def __init__(
        self,
        quality: int = 50,           # JPEG quality 1-100, default 50
        fps: int = 15,               # Frames per second, default 15
        max_resolution: tuple = (1280, 720),  # Max width, height
        target_bandwidth: int = 500,   # Target KB/s, default 500KB/s
        use_motion_detection: bool = True,  # Skip frames with no motion
    ):
        self.quality = quality
        self.fps = fps
        self.max_resolution = max_resolution
        self.target_bandwidth = target_bandwidth
        self.use_motion_detection = use_motion_detection


@dataclass
class StreamStatus:
    """Current streaming status"""
    active: bool
    start_time: Optional[float] = None
    frame_count: int = 0
    bytes_sent: int = 0
    fps_actual: float = 0.0
    current_quality: int = 50


@dataclass
class StreamInfo:
    """Information about an active stream"""
    stream_id: str
    device_id: str
    started_at: float
    config: StreamConfig
    status: StreamStatus = field(default_factory=lambda: StreamStatus(active=False))


class ScreenStreamer:
    """
    Manages screen streaming for connected devices.
    - User consent required before stream starts
    - Visible indicator while streaming
    - Efficient encoding for low-RAM hardware
    """

    def __init__(self, security_manager=None):
        from .security import get_security_manager
        self._security_manager = security_manager or get_security_manager()
        self._active_streams: Dict[str, StreamInfo] = {}
        self._callbacks: List[Callable[[str, bytes], None]] = []
        self._running = False
        self._stream_lock = asyncio.Lock()

    def register_frame_callback(self, callback: Callable[[str, bytes], None]):
        """Register callback for frame delivery"""
        self._callbacks.append(callback)

    async def start_stream(
        self,
        device_id: str,
        user_confirmed: bool = False,
        config: Optional[StreamConfig] = None
    ) -> bool:
        """
        Start screen streaming for a device.
        Must be called with explicit user confirmation.
        Returns True if stream started, False if denied (fail closed).
        """
        if not user_confirmed:
            # Fail closed: stream must not start without user consent
            return False

        # User consent is necessary but not sufficient: require a scoped grant too.
        from .security import Permission
        security = self._security_manager
        if security is None or not security.check_permission(device_id, Permission.SCREEN_STREAMING):
            return False

        try:
            import uuid
            stream_id = f"stream_{uuid.uuid4().hex[:8]}"

            stream_info = StreamInfo(
                stream_id=stream_id,
                device_id=device_id,
                started_at=time.time(),
                config=config or StreamConfig()
            )
            stream_info.status.active = True

            self._active_streams[stream_id] = stream_info
            return True

        except Exception:
            return False

    async def stop_stream(self, stream_id: str) -> bool:
        """Stop a streaming session"""
        async with self._stream_lock:
            if stream_id in self._active_streams:
                stream = self._active_streams[stream_id]
                stream.status.active = False
                del self._active_streams[stream_id]
                return True
            return False

    def is_streaming(self, device_id: str) -> bool:
        """Check if device is currently streaming"""
        for stream in self._active_streams.values():
            if stream.device_id == device_id and stream.status.active:
                return True
        return False

    async def send_frame(self, stream_id: str, frame_data: bytes) -> bool:
        """Send a frame to the active stream"""
        async with self._stream_lock:
            if stream_id not in self._active_streams:
                return False

            stream = self._active_streams[stream_id]
            if not stream.status.active:
                return False

            stream.status.frame_count += 1
            stream.status.bytes_sent += len(frame_data)

            # Call registered callbacks
            for callback in self._callbacks:
                try:
                    callback(stream_id, frame_data)
                except Exception:
                    pass

            return True

    def get_stream_status(self, stream_id: str) -> Optional[StreamStatus]:
        """Get status of a specific stream"""
        if stream_id in self._active_streams:
            return self._active_streams[stream_id].status
        return None

    def get_all_streams(self) -> List[StreamInfo]:
        """Get all active streams"""
        return list(self._active_streams.values())

    def get_streaming_devices(self) -> List[str]:
        """Get list of device IDs currently streaming"""
        return [s.device_id for s in self._active_streams.values() if s.status.active]

    async def stop_all_streams_for_device(self, device_id: str):
        """Stop all streams for a device"""
        to_stop = [
            sid for sid, s in self._active_streams.items()
            if s.device_id == device_id and s.status.active
        ]
        for sid in to_stop:
            await self.stop_stream(sid)

    def request_user_consent(
        self,
        device_id: str,
        callback: Callable[[str, bool], None]
    ):
        """
        Request user consent for streaming.
        Callback receives (device_id, consent_granted).
        Must be implemented by UI layer.
        """
        # This is a placeholder - UI implementation should show consent dialog
        # and call back with user's decision
        if callback:
            callback(device_id, False)  # Default: deny until user confirms


# Global stream manager instance
_global_stream_manager: Optional[ScreenStreamer] = None


def get_stream_manager() -> ScreenStreamer:
    """Get global stream manager instance"""
    global _global_stream_manager
    if _global_stream_manager is None:
        _global_stream_manager = ScreenStreamer()
    return _global_stream_manager