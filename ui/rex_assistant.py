#!/usr/bin/env python3
"""
REX Assistant Window
Main AI assistant interface for REX OS.

Features:
- Chat interface with AI
- Push-to-talk button
- Provider status display
- Voice/mic controls
"""

import sys
import os
import asyncio
from typing import Optional
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QGridLayout,
        QComboBox, QSlider, QCheckBox, QMessageBox, QProgressBar
    )
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QObject
    from PyQt6.QtGui import QFont, QColor, QPalette
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

try:
    from ais.conversation_manager import ConversationManager, ConversationMode, AgentStatus
    from ais.voice_assistant import VoiceAssistant, VoiceState
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class AssistantWindow(QMainWindow):
    """Main assistant window for REX OS"""

    def __init__(self, conversation_manager: Optional[ConversationManager] = None):
        super().__init__()
        self.setWindowTitle("REX Assistant")
        self.resize(400, 500)
        self.setMinimumWidth(300)

        self._manager = conversation_manager
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )

        self._setup_ui()
        self._setup_connections()

        # Timer for updates
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(1000)

    def _setup_ui(self):
        """Create the user interface"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Status bar
        self._status_label = QLabel("Initializing REX Assistant...")
        self._status_label.setStyleSheet("background: #2a2d3a; color: #e0e0e0; padding: 8px;")
        main_layout.addWidget(self._status_label)

        # Chat display
        self._chat_display = QTextEdit()
        self._chat_display.setReadOnly(True)
        self._chat_display.setStyleSheet("""
            background: #1a1a1a;
            color: #e0e0e0;
            border: 1px solid #444;
        """)
        main_layout.addWidget(self._chat_display, 1)

        # Input area
        input_layout = QHBoxLayout()
        main_layout.addLayout(input_layout)

        self._input_field = QLineEdit()
        self._input_field.setPlaceholderText("Type a message...")
        input_layout.addWidget(self._input_field, 1)

        self._send_button = QPushButton("Send")
        self._send_button.clicked.connect(self._send_message)
        input_layout.addWidget(self._send_button)

        self._mic_button = QPushButton("🎙️")
        self._mic_button.clicked.connect(self._toggle_mic)
        self._mic_button.setCheckable(True)
        input_layout.addWidget(self._mic_button)

        # Options panel
        options_frame = QFrame()
        options_frame.setStyleSheet("background: #2a2d3a; border-radius: 8px; margin: 8px;")
        options_layout = QGridLayout(options_frame)

        # Provider selection
        options_layout.addWidget(QLabel("Provider:"), 0, 0)
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["Auto", "Ollama", "OpenAI", "Anthropic", "Google"])
        options_layout.addWidget(self._provider_combo, 0, 1)

        # Status indicators
        self._ai_status = QLabel("AI: Offline")
        self._ai_status.setStyleSheet("color: #ff6b6b;")
        options_layout.addWidget(self._ai_status, 0, 2)

        self._voice_status = QLabel("Voice: Ready")
        self._voice_status.setStyleSheet("color: #51cf66;")
        options_layout.addWidget(self._voice_status, 1, 0)

        # Mic mute checkbox
        self._mute_checkbox = QCheckBox("Mute Mic")
        self._mute_checkbox.toggled.connect(self._toggle_mute)
        options_layout.addWidget(self._mute_checkbox, 1, 1)

        main_layout.addWidget(options_frame)

        # Welcome message
        self._add_message("REX Assistant", "Hello! I'm REX, your AI assistant. How can I help you today?", "assistant")

    def _setup_connections(self):
        """Setup signal connections"""
        if self._manager:
            self._manager.set_on_response(self._on_response)
            self._manager.set_on_status_change(self._on_status_change)

    def _add_message(self, sender: str, text: str, role: str = "user"):
        """Add a message to the chat display"""
        from PyQt6.QtGui import QTextOption

        # Format message
        html = f"""
        <div style="margin: 8px 0; padding: 8px; border-radius: 8px;
                    background: {'#3a3f5a' if role == 'user' else '#2a2a3a'};
                    color: #e0e0e0;">
            <b style="color: #00c2cb;">{sender}:</b><br>
            {text}
        </div>
        """

        self._chat_display.append(html)
        self._chat_display.moveCursor(self._chat_display.verticalScrollBar().bottom())

    def _send_message(self):
        """Send message to AI"""
        text = self._input_field.text().strip()
        if not text:
            return

        self._add_message("You", text, "user")
        self._input_field.clear()

        # Simulate response for testing
        self._add_message("REX", "Processing your request...", "assistant")

    def _toggle_mic(self):
        """Toggle microphone state"""
        if self._manager:
            muted = self._manager.toggle_mute()
            if muted:
                self._mic_button.setText("🔇")
            else:
                self._mic_button.setText("🎙️")

    def _toggle_mute(self, checked: bool):
        """Handle mute checkbox"""
        pass  # Handled by mic button

    def _on_response(self, response: str):
        """Handle AI response"""
        self._add_message("REX", response, "assistant")

    def _on_status_change(self, status: AgentStatus):
        """Handle status change"""
        if status.ai_available:
            self._ai_status.setStyleSheet("color: #51cf66;")
            self._ai_status.setText(f"AI: {status.current_provider or 'Online'}")
        else:
            self._ai_status.setStyleSheet("color: #ff6b6b;")
            self._ai_status.setText("AI: Offline")

    def _update_status(self):
        """Update status indicators"""
        # This is called periodically
        pass

    def closeEvent(self, event):
        """Handle window close"""
        if self._manager:
            self._manager.shutdown()
        event.accept()


def create_assistant(conversation_manager: Optional[ConversationManager] = None) -> Optional[QMainWindow]:
    """Create and return the assistant window"""
    if not PYQT6_AVAILABLE:
        return None

    app = QApplication.instance() or QApplication(sys.argv)
    window = AssistantWindow(conversation_manager)
    window.show()
    return window


if __name__ == "__main__":
    create_assistant()
    QApplication.instance().exec()