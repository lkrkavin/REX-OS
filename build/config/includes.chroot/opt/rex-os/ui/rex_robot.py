#!/usr/bin/env python3
"""
REX Robot Assistant UI Module
A draggable, Qt-based visual assistant for REX OS with AI integration
"""

import sys
import os
import asyncio
from pathlib import Path
from typing import Optional

# Ensure we can import from our modules
sys.path.insert(0, '/opt/rex-os')

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
    from PyQt6.QtCore import Qt, QTimer, QPoint
    from PyQt6.QtGui import QPainter, QColor, QMouseEvent
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    try:
        import tkinter as tk
        TK_AVAILABLE = True
    except ImportError:
        TK_AVAILABLE = False

try:
    from ai_core import REXAICore
    from ai_providers import ProviderType
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
        self.setWindowTitle("REX Robot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.StayOnTop |
            Qt.WindowType.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(120, 120)
        self.dragging = False
        self.offset = QPoint()
        self.state = RobotState.IDLE
        self.robot_color = QColor(0, 194, 203)
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_angle = 0
        self._start_animation()

    def _start_animation(self):
        self._animation_timer.start(50)

    def _update_animation(self):
        self._animation_angle = (self._animation_angle + 2) % 360
        self.update()

    def set_state(self, state: str):
        self.state = state
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.pos()

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

        painter.setBrush(QColor(42, 45, 58))
        painter.setPen(QColor(74, 80, 112))
        painter.drawEllipse(10, 10, 100, 100)

        if self.state == RobotState.LISTENING:
            eye_color = QColor(0, 255, 100)
        elif self.state == RobotState.THINKING:
            eye_color = QColor(255, 165, 0)
        elif self.state == RobotState.SPEAKING:
            eye_color = QColor(0, 194, 203)
        elif self.state == RobotState.ERROR:
            eye_color = QColor(255, 0, 0)
        else:
            eye_color = self.robot_color

        painter.setBrush(eye_color)
        painter.drawEllipse(30, 35, 20, 20)
        painter.drawEllipse(70, 35, 20, 20)

        if self.state == RobotState.THINKING:
            import math
            offset = 3 + math.sin(self._animation_angle * math.pi / 180) * 2
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(int(35 + offset), 40, 6, 6)
            painter.drawEllipse(int(67 - offset), 40, 6, 6)
        else:
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(35, 40, 8, 8)
            painter.drawEllipse(67, 40, 8, 8)

        painter.setPen(QColor(138, 43, 226))
        painter.drawLine(60, 10, 60, 0)
        painter.setBrush(QColor(138, 43, 226))
        painter.drawEllipse(55, 0, 10, 10)

        if self.state == RobotState.LISTENING:
            painter.setBrush(QColor(0, 255, 100))
        elif self.state == RobotState.THINKING:
            painter.setBrush(QColor(255, 165, 0))
        else:
            painter.setBrush(QColor(138, 43, 226))
        painter.drawEllipse(55, 0, 8, 8)

def main():
    if not PYQT6_AVAILABLE and not TK_AVAILABLE:
        print("Neither PyQt6 nor Tkinter available for UI")
        return

    if PYQT6_AVAILABLE:
        app = QApplication(sys.argv)
        robot = REXRobot()
        robot.show()
        sys.exit(app.exec())
    else:
        root = tk.Tk()
        root.title("REX Robot")
        root.geometry("120x120")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        label = tk.Label(root, text="🤖", font=("Arial", 24))
        label.pack(expand=True)
        root.mainloop()

if __name__ == "__main__":
    main()
