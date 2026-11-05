#!/usr/bin/env python3
"""REX Assistant desktop chat window with a background AI worker."""

import sys
import asyncio
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextEdit, QLineEdit, QPushButton, QLabel, QFrame, QGridLayout,
        QComboBox
    )
    from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

try:
    from ais.ai_core import REXAICore
    from ais.conversation_manager import ConversationManager
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


if PYQT6_AVAILABLE:
    class AIWorker(QThread):
        """Own the asyncio loop and AI manager outside the Qt UI thread."""
        response_ready = pyqtSignal(str)
        status_ready = pyqtSignal(str, bool)

        def __init__(self):
            super().__init__()
            self.loop = None
            self.manager = None

        def run(self):
            if not AI_AVAILABLE:
                self.status_ready.emit("AI modules unavailable", False)
                return

            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                core = REXAICore()
                self.manager = ConversationManager(ai_core=core)
                available = self.loop.run_until_complete(self.manager.initialize())
                provider = core.current_provider.value if core.current_provider else "Offline"
                self.status_ready.emit(provider, bool(available))
                self.loop.run_forever()
            except Exception as exc:
                self.status_ready.emit(str(exc), False)
            finally:
                if self.manager:
                    try:
                        self.manager.shutdown()
                    except Exception:
                        pass
                if self.loop and not self.loop.is_closed():
                    self.loop.close()

        def send_message(self, message: str):
            if not self.loop or not self.manager or not self.loop.is_running():
                self.response_ready.emit(
                    "REX AI is not connected. Check that an AI provider is configured and running."
                )
                return

            future = asyncio.run_coroutine_threadsafe(
                self.manager.send_message(message), self.loop
            )

            def completed(task):
                try:
                    answer = task.result()
                    self.response_ready.emit(
                        answer or "No response received. Check your AI provider."
                    )
                except Exception as exc:
                    self.response_ready.emit(f"AI request failed: {exc}")

            future.add_done_callback(completed)

        def stop(self):
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)


    class AssistantWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("REX Assistant")
            self.resize(560, 620)
            self.setMinimumSize(380, 440)
            self.setStyleSheet("""
                QMainWindow, QWidget { background: #171923; color: #e5e7eb; }
                QTextEdit { background: #10131b; color: #e5e7eb;
                            border: 1px solid #3b4255; border-radius: 8px; padding: 8px; }
                QLineEdit { background: #242938; color: #ffffff;
                            border: 1px solid #00c2cb; border-radius: 8px; padding: 10px; }
                QPushButton { background: #263344; color: #ffffff;
                              border: 1px solid #00c2cb; border-radius: 8px; padding: 9px 16px; }
                QPushButton:hover { background: #35445b; }
                QComboBox { background: #242938; color: #ffffff; padding: 6px; }
            """)

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)

            self.status = QLabel("REX AI: Starting...")
            self.status.setStyleSheet(
                "background:#242938; color:#00c2cb; padding:10px; border-radius:8px;"
            )
            layout.addWidget(self.status)

            self.chat = QTextEdit()
            self.chat.setReadOnly(True)
            layout.addWidget(self.chat, 1)

            row = QHBoxLayout()
            self.input = QLineEdit()
            self.input.setPlaceholderText("Type a message for REX...")
            self.input.returnPressed.connect(self.send_message)
            row.addWidget(self.input, 1)
            self.send_button = QPushButton("Send")
            self.send_button.clicked.connect(self.send_message)
            row.addWidget(self.send_button)
            layout.addLayout(row)

            self.provider = QComboBox()
            self.provider.addItems(["Automatic provider selection", "Ollama", "OpenAI", "Anthropic", "Google"])
            self.provider.setToolTip("Provider selection is currently controlled by /etc/rex/ai_providers.json")
            layout.addWidget(self.provider)

            self.worker = AIWorker()
            self.worker.response_ready.connect(self.show_response)
            self.worker.status_ready.connect(self.show_status)
            self.worker.start()

            self.add_message("REX", "Hello! I'm REX. The chat is connecting to your configured AI provider.", False)

        def add_message(self, sender: str, message: str, user: bool):
            safe = (message.replace("&", "&amp;").replace("<", "&lt;")
                    .replace(">", "&gt;").replace("\n", "<br>"))
            color = "#26384a" if user else "#222638"
            self.chat.append(
                f'<div style="margin:8px;padding:10px;background:{color};'
                f'border-radius:8px;"><b style="color:#00c2cb">{sender}:</b><br>{safe}</div>'
            )

        def send_message(self):
            message = self.input.text().strip()
            if not message:
                return
            self.input.clear()
            self.add_message("You", message, True)
            self.send_button.setEnabled(False)
            self.worker.send_message(message)

        def show_response(self, response: str):
            self.add_message("REX", response, False)
            self.send_button.setEnabled(True)

        def show_status(self, provider: str, online: bool):
            state = "Online" if online else "Offline"
            color = "#51cf66" if online else "#ffb86c"
            self.status.setText(f"REX AI: {state} — {provider}")
            self.status.setStyleSheet(
                f"background:#242938;color:{color};padding:10px;border-radius:8px;"
            )

        def closeEvent(self, event):
            self.worker.stop()
            self.worker.wait(3000)
            event.accept()


def main():
    if not PYQT6_AVAILABLE:
        print("REX Assistant requires python3-pyqt6.")
        return 1
    app = QApplication(sys.argv)
    window = AssistantWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
