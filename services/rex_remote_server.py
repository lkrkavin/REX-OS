#!/usr/bin/env python3
"""
REX REMOTE Server Agent

Runs on the laptop/desktop and provides:
- Secure outbound connection to phone
- Process monitoring
- System status reporting
- Basic remote control capabilities

This uses an authenticated outbound connection architecture so
the laptop never needs to expose a public port.
"""

import asyncio
import json
import os
import sys
import time
import base64
import hashlib
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading
import uuid

# Configuration
LOCALHOST = "127.0.0.1"
WS_PORT = 8765
HTTP_PORT = 8766
RELAY_HOST = os.environ.get("REX_RELAY_HOST")  # Required: set via environment
RELAY_PORT = int(os.environ.get("REX_RELAY_PORT", 443))

if not RELAY_HOST:
    import warnings
    warnings.warn("REX_RELAY_HOST not set. Relay mode will not work. Set via environment variable.")

# Try optional imports
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

try:
    import mss
    import numpy as np
    import cv2
    MSCC_AVAILABLE = True
except ImportError:
    MSCC_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False


class SystemStats:
    """Get system statistics using psutil"""

    @staticmethod
    def get_all() -> Dict[str, Any]:
        """Get complete system status"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1, percpu=False)

            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            battery = {"percent": 0, "power_plugged": False, "exists": False}
            try:
                b = psutil.sensors_battery()
                if b:
                    battery = {
                        "percent": b.percent,
                        "power_plugged": b.power_plugged,
                        "exists": True
                    }
            except:
                pass

            temps = None
            try:
                t = psutil.sensors_temperatures()
                if t and 'coretemp' in t:
                    temps = {"current": t['coretemp'][0].current, "max": t['coretemp'][0].max}
            except:
                pass

            net_io = psutil.net_io_counters()
            load = os.getloadavg() if hasattr(os, 'getloadavg') else (0, 0, 0)

            return {
                "cpu_percent": round(cpu_percent, 1),
                "cpu_count": os.cpu_count() or 1,
                "load_average": [round(l, 2) for l in load],
                "ram_total_gb": round(ram.total / 1024**3, 2),
                "ram_used_gb": round(ram.used / 1024**3, 2),
                "ram_percent": round(ram.percent, 1),
                "disk_total_gb": round(disk.total / 1024**3, 2),
                "disk_used_gb": round(disk.used / 1024**3, 2),
                "disk_percent": round(disk.percent, 1),
                "battery": battery,
                "temps": temps,
                "network_bytes_sent": net_io.bytes_sent,
                "network_bytes_recv": net_io.bytes_recv,
                "uptime_seconds": int(time.time() - psutil.boot_time())
            }
        except Exception as e:
            return {"error": str(e), "timestamp": datetime.now().isoformat()}


class ProcessMonitor:
    """Monitor running processes"""

    @staticmethod
    def get_top_processes(limit: int = 50) -> List[Dict[str, Any]]:
        """Get top processes by CPU usage"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status', 'create_time', 'cmdline']):
                try:
                    p = proc.info
                    runtime = time.time() - (p.get('create_time', time.time()) or time.time())
                    if runtime < 0:
                        runtime = 0

                    memory_mb = 0
                    if p.get('memory_info'):
                        memory_mb = p['memory_info'].rss / 1024 / 1024

                    cmdline = p.get('cmdline') or []
                    cmdline_str = ' '.join(cmdline[:3]) if cmdline else ''

                    processes.append({
                        "pid": p['pid'],
                        "name": p['name'],
                        "cmdline": cmdline_str,
                        "status": p['status'],
                        "cpu": round(p.get('cpu_percent', 0) or 0, 1),
                        "memory_mb": round(memory_mb, 1),
                        "runtime_sec": int(runtime),
                        "create_time": p.get('create_time')
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

            # Sort by CPU usage descending
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            return processes[:limit]
        except Exception as e:
            return [{"error": str(e), "timestamp": datetime.now().isoformat()}]

    @staticmethod
    def get_process_by_name(name: str) -> Optional[Dict[str, Any]]:
        """Find a process by name"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'status', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower()
                    if name.lower() in proc_name:
                        return {
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cpu": round(proc.info['cpu_percent'], 1),
                            "memory_mb": round((proc.info['memory_info'].rss / 1024 / 1024) if proc.info['memory_info'] else 0),
                            "status": proc.info['status'],
                            "cmdline": ' '.join(proc.info.get('cmdline') or [])
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except:
            pass
        return None

    @staticmethod
    def get_process_tree() -> List[Dict[str, Any]]:
        """Get process tree"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'ppid', 'name', 'status']):
                try:
                    processes.append({
                        "pid": proc.info['pid'],
                        "ppid": proc.info['ppid'],
                        "name": proc.info['name'],
                        "status": proc.info['status']
                    })
                except:
                    pass
            return processes
        except:
            return []

    @staticmethod
    def kill_process(pid: int) -> Dict[str, Any]:
        """Kill a process by PID"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            return {"success": True, "message": f"Process {pid} terminated"}
        except psutil.NoSuchProcess:
            return {"success": False, "error": "Process not found"}
        except psutil.AccessDenied:
            return {"success": False, "error": "Access denied"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ScreenCapture:
    """Handle screen capture operations"""

    def __init__(self):
        self.last_capture = None
        self.capture_count = 0

    def capture(self, quality: int = 75) -> Optional[str]:
        """Capture screen and return base64 JPEG"""
        if not MSCC_AVAILABLE:
            return None

        try:
            with mss.mss() as sct:
                # Use primary monitor
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                img = sct.grab(monitor)

                # Convert to numpy array
                pixels = np.array(img)

                # Remove alpha if present (RGBA -> RGB)
                if pixels.shape[2] == 4:
                    pixels = pixels[:, :, :3]

                # Encode as JPEG
                encode_param = [cv2.IMWRITE_JPEG_QUALITY, quality]
                _, buf = cv2.imencode('.jpg', pixels, encode_param)

                # Base64 encode for transmission
                self.last_capture = base64.b64encode(buf.tobytes()).decode('utf-8')
                self.capture_count += 1
                return self.last_capture

        except Exception as e:
            print(f"Screen capture error: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get capture statistics"""
        return {
            "capture_count": self.capture_count,
            "last_capture_time": datetime.now().isoformat() if self.last_capture else None,
            "available": MSCC_AVAILABLE
        }


class RexRemoteServer:
    """Main REX Remote server"""

    def __init__(self):
        self.connections: Dict[str, Dict] = {}
        self.running = True
        self.stats = SystemStats()
        self.monitor = ProcessMonitor()
        self.screen_capture = ScreenCapture()
        self.notifications: List[Dict] = []
        self.session_tokens: Dict[str, Dict] = {}
        self.relay_websocket = None

    def add_notification(self, title: str, message: str, level: str = "info"):
        """Add a notification"""
        notification = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "message": message,
            "level": level,
            "timestamp": datetime.now().isoformat()
        }
        self.notifications.insert(0, notification)
        self.notifications = self.notifications[:50]  # Keep last 50

    async def check_relay_connection(self) -> bool:
        """Check if relay server is available (for phone connectivity)"""
        if not AIOHTTP_AVAILABLE:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"wss://{RELAY_HOST}:{RELAY_PORT}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except:
            return False

    async def connect_to_relay(self, session_token: str) -> bool:
        """Connect to relay server for phone access"""
        if not AIOHTTP_AVAILABLE:
            return False

        try:
            self.relay_websocket = await websockets.connect(
                f"wss://{RELAY_HOST}:{RELAY_PORT}/client"
            )

            # Register with session token
            await self.relay_websocket.send(json.dumps({
                "type": "register",
                "session_token": session_token,
                "client_version": "1.0.0"
            }))

            return True
        except Exception as e:
            print(f"Relay connection failed: {e}")
            return False

    async def handle_message(self, websocket, message: str):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            msg_id = data.get("id", str(uuid.uuid4())[:8])

            if msg_type == "ping":
                await websocket.send(json.dumps({
                    "type": "pong",
                    "id": msg_id,
                    "timestamp": time.time()
                }))

            elif msg_type == "get_status":
                await websocket.send(json.dumps({
                    "type": "response",
                    "id": msg_id,
                    "data": self.stats.get_all()
                }))

            elif msg_type == "get_processes":
                await websocket.send(json.dumps({
                    "type": "response",
                    "id": msg_id,
                    "data": self.monitor.get_top_processes(50)
                }))

            elif msg_type == "get_process_tree":
                await websocket.send(json.dumps({
                    "type": "response",
                    "id": msg_id,
                    "data": self.monitor.get_process_tree()
                }))

            elif msg_type == "get_system_info":
                await websocket.send(json.dumps({
                    "type": "response",
                    "id": msg_id,
                    "data": {
                        "os": os.name,
                        "platform": sys.platform,
                        "python_version": sys.version,
                        "cpu_count": os.cpu_count(),
                        "hostname": os.uname().nodename if hasattr(os, 'uname') else "Unknown",
                        "python_executable": sys.executable
                    }
                }))

            elif msg_type == "capture_screen":
                quality = data.get("quality", 75)
                img_b64 = self.screen_capture.capture(quality)
                if img_b64:
                    await websocket.send(json.dumps({
                        "type": "screen_frame",
                        "id": msg_id,
                        "data": {"image": img_b64, "stats": self.screen_capture.get_stats()}
                    }))
                else:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "id": msg_id,
                        "message": "Screen capture unavailable"
                    }))

            elif msg_type == "execute_action":
                action_data = data.get("action", {})
                result = self.execute_action(action_data)
                await websocket.send(json.dumps({
                    "type": "action_result",
                    "id": msg_id,
                    "data": result
                }))

            elif msg_type == "notification":
                level = data.get("level", "info")
                self.add_notification(
                    data.get("title", "Notification"),
                    data.get("message", ""),
                    level
                )

            elif msg_type == "get_notifications":
                await websocket.send(json.dumps({
                    "type": "response",
                    "id": msg_id,
                    "data": self.notifications
                }))

            elif msg_type == "get_screen_stats":
                await websocket.send(json.dumps({
                    "type": "response",
                    "id": msg_id,
                    "data": self.screen_capture.get_stats()
                }))

            else:
                await websocket.send(json.dumps({
                    "type": "error",
                    "id": msg_id,
                    "message": f"Unknown message type: {msg_type}"
                }))

        except json.JSONDecodeError:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }))

    def execute_action(self, action: Dict) -> Dict:
        """Execute remote action"""
        action_type = action.get("type")

        try:
            if action_type == "mouse_click":
                if PYAUTOGUI_AVAILABLE:
                    button = action.get("button", "left")
                    x = action.get("x")
                    y = action.get("y")
                    if x is not None and y is not None:
                        pyautogui.click(x, y, button=button)
                    else:
                        pyautogui.click(button=button)
                    return {"success": True, "message": f"Clicked with {button} button"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "mouse_move":
                if PYAUTOGUI_AVAILABLE:
                    x = action.get("x", 0)
                    y = action.get("y", 0)
                    pyautogui.moveRel(x, y)
                    return {"success": True, "message": f"Moved mouse by ({x}, {y})"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "scroll":
                if PYAUTOGUI_AVAILABLE:
                    amount = action.get("amount", 1)
                    pyautogui.scroll(amount)
                    return {"success": True, "message": f"Scrolled by {amount}"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "mouse_down":
                if PYAUTOGUI_AVAILABLE:
                    button = action.get("button", "left")
                    x = action.get("x")
                    y = action.get("y")
                    if x is not None and y is not None:
                        pyautogui.mouseDown(x, y, button=button)
                    else:
                        pyautogui.mouseDown(button=button)
                    return {"success": True, "message": f"Mouse down: {button}"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "mouse_up":
                if PYAUTOGUI_AVAILABLE:
                    button = action.get("button", "left")
                    x = action.get("x")
                    y = action.get("y")
                    if x is not None and y is not None:
                        pyautogui.mouseUp(x, y, button=button)
                    else:
                        pyautogui.mouseUp(button=button)
                    return {"success": True, "message": f"Mouse up: {button}"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "keyboard_text":
                if PYAUTOGUI_AVAILABLE:
                    text = action.get("text", "")
                    if text:
                        pyautogui.write(text)
                        return {"success": True, "message": f"Typed: {text}"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "key_press":
                if PYAUTOGUI_AVAILABLE:
                    key = action.get("key")
                    if key:
                        pyautogui.press(key)
                        return {"success": True, "message": f"Pressed {key}"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "key_tap":
                if PYAUTOGUI_AVAILABLE:
                    key = action.get("key")
                    if key:
                        pyautogui.keyDown(key)
                        pyautogui.keyUp(key)
                        return {"success": True, "message": f"Tapped {key}"}
                return {"success": False, "error": "pyautogui not available"}

            elif action_type == "open_app":
                app = action.get("app", "")
                if not app:
                    return {"success": False, "error": "Application not specified"}

                # Validate app name - only allow alphanumeric, dash, underscore, dot
                import re
                if not re.match(r'^[a-zA-Z0-9._-]+$', app):
                    return {"success": False, "error": "Invalid application name"}

                try:
                    if sys.platform == "win32":
                        subprocess.run(["start", "", app], shell=True, check=True)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", app], check=True)
                    else:
                        subprocess.run(["xdg-open", app], check=True)
                    return {"success": True, "message": f"Opened: {app}"}
                except subprocess.CalledProcessError as e:
                    return {"success": False, "error": f"Failed to open app: {e}"}
                except FileNotFoundError:
                    return {"success": False, "error": "Command not found (xdg-open/open/start)"}

            elif action_type == "lock":
                if sys.platform == "win32":
                    os.system("rundll32.exe user32.dll,LockWorkStation")
                elif sys.platform == "darwin":
                    os.system("osascript -e 'tell application \"System Events\" to keystroke \"q\" using {command down, control down}'")
                else:
                    os.system("loginctl lock-sessions")
                return {"success": True, "message": "Computer locked"}

            elif action_type == "logout":
                return {"success": False, "message": "Log out requires user confirmation"}

            elif action_type == "screenshot":
                img = self.screen_capture.capture()
                if img:
                    return {"success": True, "image": img}
                return {"success": False, "error": "Capture failed"}

            elif action_type == "terminate_process":
                pid = action.get("pid")
                if pid:
                    return self.monitor.kill_process(pid)
                return {"success": False, "error": "PID not specified"}

            elif action_type == "get_process":
                name = action.get("name") or action.get("process")
                if name:
                    proc = self.monitor.get_process_by_name(name)
                    if proc:
                        return {"success": True, "data": proc}
                    return {"success": False, "error": f"Process '{name}' not found"}
                return {"success": False, "error": "Process name not specified"}

            else:
                return {"success": False, "error": f"Unknown action: {action_type}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def register_client(self, websocket, client_id: str = None) -> str:
        """Register a new WebSocket connection"""
        if not client_id:
            client_id = f"client_{uuid.uuid4().hex[:8]}"

        self.connections[client_id] = {
            "websocket": websocket,
            "connected_at": time.time(),
            "mode": "monitor",
            "last_activity": time.time()
        }

        # Send welcome
        await websocket.send(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "server_version": "1.0.0",
            "features": ["monitoring", "screen_capture", "process_control", "notifications"],
            "timestamp": time.time()
        }))

        return client_id

    async def unregister_client(self, client_id: str):
        """Unregister a WebSocket connection"""
        if client_id in self.connections:
            del self.connections[client_id]

    async def broadcast_status(self):
        """Broadcast status to all connected clients"""
        status = self.stats.get_all()
        processes = self.monitor.get_top_processes(20)
        screen_stats = self.screen_capture.get_stats()

        for client_id, conn in list(self.connections.items()):
            try:
                ws = conn["websocket"]
                if not ws:
                    continue

                await ws.send(json.dumps({
                    "type": "status_update",
                    "data": {
                        "system": status,
                        "processes": processes,
                        "screen": screen_stats,
                        "timestamp": time.time()
                    }
                }))
                conn["last_activity"] = time.time()
            except:
                await self.unregister_client(client_id)

    async def handle_websocket(self, websocket, path=None):
        """Handle WebSocket connection"""
        client_id = await self.register_client(websocket)
        print(f"Client {client_id} connected")

        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {client_id} disconnected")
        except Exception as e:
            print(f"Error handling client {client_id}: {e}")
        finally:
            await self.unregister_client(client_id)

    async def run_local(self):
        """Run the server on localhost"""
        print(f"Starting REX Remote server on {LOCALHOST}:{WS_PORT}")
        self.add_notification("Server Started", "REX Remote server is now running")

        if not WEBSOCKETS_AVAILABLE:
            print("ERROR: websockets library not available. Install with: pip install websockets")
            return

        async with websockets.serve(self.handle_websocket, LOCALHOST, WS_PORT):
            # Periodically broadcast status
            while self.running:
                await asyncio.sleep(5)
                await self.broadcast_status()

    async def run_relay(self):
        """Run server in relay mode for phone connectivity"""
        if not RELAY_HOST:
            print("REX_RELAY_HOST not configured, running in local mode")
            await self.run_local()
            return

        if not await self.check_relay_connection():
            print("Relay server not available, running in local mode")
            await self.run_local()
            return

        session_token = os.environ.get("REX_SESSION_TOKEN")
        if not session_token:
            print("REX_SESSION_TOKEN not set, running in local mode")
            await self.run_local()
            return

        print(f"Connecting to relay at {RELAY_HOST}:{RELAY_PORT}")
        if await self.connect_to_relay(session_token):
            print("Connected to relay, accepting phone connections")
        else:
            print("Failed to connect to relay, falling back to local mode")
            await self.run_local()


async def main():
    global server_instance
    server_instance = RexRemoteServer()

    try:
        # Check if running in relay mode
        relay_mode = os.environ.get("REX_RELAY_MODE", "false").lower() == "true"

        if relay_mode:
            await server_instance.run_relay()
        else:
            await server_instance.run_local()

    except KeyboardInterrupt:
        print("\nShutting down REX Remote server...")
        server_instance.running = False


if __name__ == "__main__":
    asyncio.run(main())