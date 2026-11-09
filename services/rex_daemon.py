#!/usr/bin/env python3
"""
REX OS Daemon - Main system service
"""

import asyncio
import json
import os
import sys
import signal
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Add paths
sys.path.insert(0, '/opt/rex-os')

try:
    from ais.ai_core import REXAICore
    from ais.user_memory import UserMemory
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class REXDaemon:
    """Main REX OS daemon service"""

    def __init__(self):
        self.config_path = os.environ.get("REX_CONFIG_PATH", "/etc/rex")
        self.data_path = os.environ.get("REX_DATA_PATH", "/var/lib/rex")
        self.running = True
        self.ai_core: Optional[REXAICore] = None
        self.user_memory: Optional[UserMemory] = None
        self.config: Dict[str, Any] = {}

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration"""
        config_file = os.path.join(self.config_path, "rex-daemon.json")

        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {
            "log_level": "info",
            "ai_enabled": True,
            "memory_enabled": True,
            "device_check_interval": 30
        }

    async def initialize(self):
        """Initialize daemon services"""
        print("Initializing REX OS Daemon...")

        # Ensure directories exist
        os.makedirs(self.data_path, exist_ok=True)

        self.config = self._load_config()

        # Initialize AI Core if enabled
        if self.config.get("ai_enabled", True):
            if AI_AVAILABLE:
                self.ai_core = REXAICore()
                await self.ai_core.initialize()
                print("AI Core initialized")
            else:
                print("AI Core not available (missing dependencies)")

        # Initialize user memory
        if self.config.get("memory_enabled", True):
            if AI_AVAILABLE:
                self.user_memory = UserMemory(1)  # Default user
                print("User memory initialized")

        # Start background tasks
        asyncio.create_task(self._monitor_system())
        asyncio.create_task(self._check_devices())

        print("REX OS Daemon started successfully")

    async def _monitor_system(self):
        """Monitor system health"""
        while self.running:
            try:
                if PSUTIL_AVAILABLE:
                    cpu = psutil.cpu_percent(interval=5)
                    mem = psutil.virtual_memory().percent

                    if cpu > 90:
                        print(f"WARNING: High CPU usage: {cpu}%")
                    if mem > 85:
                        print(f"WARNING: High memory usage: {mem}%")

                await asyncio.sleep(10)

            except Exception as e:
                print(f"Monitor error: {e}")
                await asyncio.sleep(10)

    async def _check_devices(self):
        """Check connected devices"""
        while self.running:
            try:
                # Check for connected devices
                # This would integrate with device registry
                await asyncio.sleep(self.config.get("device_check_interval", 30))

            except Exception as e:
                print(f"Device check error: {e}")
                await asyncio.sleep(30)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"Received signal {signum}, shutting down...")
        self.running = False

    async def run(self):
        """Main daemon loop"""
        await self.initialize()

        while self.running:
            await asyncio.sleep(1)

        print("REX OS Daemon stopped")


async def main():
    """Main entry point"""
    daemon = REXDaemon()
    await daemon.run()


if __name__ == "__main__":
    asyncio.run(main())