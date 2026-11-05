#!/usr/bin/env python3
"""
REX Robot Assistant UI Module
A draggable, Qt-based visual assistant for REX OS with AI integration

States:
- Idle: Robot at rest
- Listening: Microphone active, eyes pulsing cyan
- Thinking: Processing request
- Speaking: TTS active
- Executing: Action in progress
- Permission: Awaiting user approval
- Error: Something went wrong
- Offline: No AI connectivity
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QHBoxLayout, QTextEdit, QLineEdit
    from PyQt6.QtCore import Qt, QTimer, QPoint, QThread, pyqtSignal, QTime
    from PyQt6.QtGui import QPainter, QColor, QFont, QMouseEvent, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    # Fallback to tkinter
    try:
        import tkinter as tk
        from tkinter import ttk
        TK_AVAILABLE = True
    except ImportError:
        TK_AVAILABLE = False

# Import AI modules - PYTHONPATH=/opt/rex-os is set in systemd service
try:
    from ais.ai_core import REXAICore, ProviderType
    from ais.voice_assistant import VoiceAssistant, VoiceState, VoiceConfig
    from ais.conversation_manager import ConversationManager, ConversationMode
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class RobotState:
    """Visual states for the robot"""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    EXECUTING = "executing"
    PERMISSION = "permission"
    ERROR = "error"
    OFFLINE = "offline"


class REXRobot(QWidget):
    """A simple draggable robot indicator widget with AI integration"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("REX 🤖")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.StayOnTop
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(120, 120)
        self.dragging = False
        self.offset = QPoint()

        # Robot state
        self.state = RobotState.IDLE
        self.robot_color = QColor(0, 194, 203)  # Cyan

        # AI is initialized by the REX daemon / assistant worker, not from
        # the GUI constructor. Avoid scheduling asyncio tasks without a loop.
        self.ai_core: Optional[REXAICore] = None
        self.conversation: Optional[ConversationManager] = None

        # Timer for animation
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_angle = 0

        self._start_animation()

    def _init_ai(self):
        """Initialize AI Core integration"""
        if not AI_AVAILABLE:
            return

        try:
            self.ai_core = REXAICore()
            # Run async init in background
            asyncio.create_task(self._init_ai_async())
        except Exception:
            pass

    async def _init_ai_async(self):
        """Async AI initialization"""
        if self.ai_core:
            await self.ai_core.initialize()

    def _start_animation(self):
        """Start the robot animation"""
        self._animation_timer.start(50)

    def _update_animation(self):
        """Update animation frame"""
        self._animation_angle = (self._animation_angle + 2) % 360
        self.update()

    def set_state(self, state: str):
        """Set robot state"""
        self.state = state
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseDoubleClickEvent(self, event):
        """Open the full REX Assistant when the robot is double-clicked."""
        try:
            subprocess.Popen(
                [sys.executable, "/opt/rex-os/ui/rex_assistant.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:
            print(f"Unable to open REX Assistant: {exc}", file=sys.stderr)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = self.mapToGlobal(event.pos() - self.offset)
            self.move(new_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Robot body - dark graphite
        painter.setBrush(QColor(42, 45, 58))
        painter.setPen(QColor(74, 80, 112))
        painter.drawEllipse(10, 10, 100, 100)

        # Robot eyes - state dependent color
        if self.state == RobotState.LISTENING:
            eye_color = QColor(0, 255, 100)  # Green
        elif self.state == RobotState.THINKING:
            eye_color = QColor(255, 165, 0)  # Orange
        elif self.state == RobotState.SPEAKING:
            eye_color = QColor(0, 194, 203)  # Cyan
        elif self.state == RobotState.ERROR:
            eye_color = QColor(255, 0, 0)  # Red
        else:
            eye_color = self.robot_color

        painter.setBrush(eye_color)
        painter.drawEllipse(30, 35, 20, 20)
        painter.drawEllipse(70, 35, 20, 20)

        # Animated pupils when thinking
        if self.state == RobotState.THINKING:
            import math
            offset = 3 + math.sin(self._animation_angle * math.pi / 180) * 2
            pupil_x = 35 + offset
            pupil_y = 40
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(int(pupil_x), int(pupil_y), 6, 6)
            painter.drawEllipse(75 - offset, 40, 6, 6)
        else:
            # Static pupils
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(35, 40, 8, 8)
            painter.drawEllipse(67, 40, 8, 8)

        # Robot antenna
        painter.setPen(QColor(138, 43, 226))
        painter.drawLine(60, 10, 60, 0)
        painter.setBrush(QColor(138, 43, 226))
        painter.drawEllipse(55, 0, 10, 10)

        # Antenna light state indicator
        if self.state == RobotState.LISTENING:
            painter.setBrush(QColor(0, 255, 100))
        elif self.state == RobotState.THINKING:
            painter.setBrush(QColor(255, 165, 0))
        else:
            painter.setBrush(QColor(138, 43, 226))
        painter.drawEllipse(55, 0, 8, 8)


def main():
    """Main entry point"""
    if not PYQT6_AVAILABLE and not TK_AVAILABLE:
        print("Neither PyQt6 nor Tkinter available for UI")
        return

    if PYQT6_AVAILABLE:
        app = QApplication(sys.argv)
        robot = REXRobot()
        robot.show()
        sys.exit(app.exec())
    else:
        # Tkinter fallback
        root = tk.Tk()
        root.title("REX 🦾")
        root.geometry("120x120")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        label = tk.Label(root, text="🤖", font=("Arial", 24))
        label.pack(expand=True)
        root.mainloop()


if __name__ == "__main__":
    main()