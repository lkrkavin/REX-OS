#!/usr/bin/env python3
"""REX AI desktop assistant with Google Search context and source links."""

import sys
sys.path.insert(0, "/opt/rex-os")
import asyncio
import html
import shutil
import subprocess
import threading
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTextBrowser, QLineEdit, QPushButton, QLabel, QCheckBox, QFrame, QMessageBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

try:
    from ais.ai_core import REXAICore
    from ais.conversation_manager import ConversationManager
    from ais.web_search import GoogleSearch, SearchUnavailable, format_search_context
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


try:
    from services.command_router import DesktopCommandRouter
except ImportError:
    DesktopCommandRouter = None


if PYQT6_AVAILABLE:
    class AIWorker(QThread):
        response_ready = pyqtSignal(str)
        status_ready = pyqtSignal(str, bool)
        search_ready = pyqtSignal(str)

        def __init__(self):
            super().__init__()
            self.loop = None
            self.manager = None
            self.searcher = GoogleSearch(timeout=8, max_results=5)

        def run(self):
            if not AI_AVAILABLE:
                self.status_ready.emit("REX AI modules unavailable", False)
                return
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                core = REXAICore()
                self.manager = ConversationManager(ai_core=core)
                self.loop.run_until_complete(self.manager.initialize())
                available = core.is_available
                provider = core.current_provider.value if core.current_provider else "No provider"
                self.status_ready.emit(provider, available)
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

        def send_message(self, message: str, use_google: bool = True):
            if not self.loop or not self.manager or not self.loop.is_running():
                self.response_ready.emit(
                    "REX AI is not ready yet. Check the provider status and try again."
                )
                return
            future = asyncio.run_coroutine_threadsafe(
                self._process_message(message, use_google), self.loop
            )
            def completed(task):
                try:
                    self.response_ready.emit(task.result() or "No response received.")
                except Exception as exc:
                    self.response_ready.emit("Request failed: " + str(exc))
            future.add_done_callback(completed)

        async def _process_message(self, message: str, use_google: bool) -> str:
            prompt = message
            if use_google:
                try:
                    results = await self.searcher.search_async(message)
                    self.search_ready.emit(self._format_results(results))
                    prompt += "\n\n" + format_search_context(message, results)
                except SearchUnavailable as exc:
                    self.search_ready.emit("Google Search unavailable: " + str(exc))
            return await self.manager.send_message(prompt)

        @staticmethod
        def _format_results(results):
            parts = ["<b>Google Search sources</b>"]
            for index, item in enumerate(results, 1):
                title = html.escape(item.title)
                url = html.escape(item.url, quote=True)
                snippet = html.escape(item.snippet)
                parts.append(
                    f'<div style="margin:7px 0;padding:8px;background:#202a3a;'
                    f'border-radius:9px;"><b>{index}. <a href="{url}">{title}</a></b>'
                    f'<br><span style="color:#aab6c8">{snippet}</span></div>'
                )
            return "".join(parts)

        def stop(self):
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(self.loop.stop)

    class VoiceCaptureWorker(QThread):
        recognized = pyqtSignal(str)
        failed = pyqtSignal(str)

        def run(self):
            try:
                import speech_recognition as sr
            except ImportError:
                self.failed.emit("Offline speech recognition is not installed.")
                return
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.listen(source, timeout=5.0, phrase_time_limit=8.0)
                try:
                    text = recognizer.recognize_sphinx(audio)
                except sr.UnknownValueError:
                    self.failed.emit("Speech not understood. Please try again.")
                    return
                except sr.RequestError as exc:
                    self.failed.emit("Offline speech engine error: " + str(exc))
                    return
                if text.strip():
                    self.recognized.emit(text.strip())
                else:
                    self.failed.emit("No speech was detected.")
            except sr.WaitTimeoutError:
                self.failed.emit("No speech heard. Press the microphone and try again.")
            except Exception as exc:
                self.failed.emit("Microphone unavailable: " + str(exc))


    class WakeWordWorker(QThread):
        activated = pyqtSignal(str)
        failed = pyqtSignal(str)

        def __init__(self, parent=None):
            super().__init__(parent)
            self._stop_event = threading.Event()
            self._listener = None

        def run(self):
            try:
                from ais.wake_word import LocalWakeWordListener
                self._listener = LocalWakeWordListener(
                    on_activation=lambda command: self.activated.emit(command or ""),
                    on_error=self.failed.emit,
                )
                if not self._listener.start():
                    self.failed.emit("Hey Rex is unavailable. Check microphone and offline speech packages.")
                    return
                while not self._stop_event.wait(0.2):
                    if not self._listener.running:
                        break
            except Exception as exc:
                self.failed.emit("Hey Rex listener error: " + str(exc))
            finally:
                if self._listener:
                    self._listener.stop()

        def stop(self):
            self._stop_event.set()
            if self._listener:
                self._listener.stop()


    class AssistantWindow(QMainWindow):
        def __init__(self, initial_command=None, wake_only=False):
            super().__init__()
            self.initial_command = initial_command
            self.wake_only = wake_only
            self.setWindowTitle("REX AI")
            self.resize(820, 780)
            self.setMinimumSize(560, 620)
            self.setWindowFlags(
                Qt.WindowType.Window |
                Qt.WindowType.WindowCloseButtonHint |
                Qt.WindowType.WindowMinimizeButtonHint |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.setStyleSheet("""
                QMainWindow, QWidget { background:#0b1020; color:#edf4ff; }
                QLabel#brand { color:#f5f8ff; font-size:27px; font-weight:800; letter-spacing:1px; }
                QLabel#subtitle { color:#9aaac4; font-size:10px; letter-spacing:2px; }
                QLabel#status { color:#8deaff; background:#111e33;
                                border:1px solid #263b55; border-radius:10px;
                                padding:8px 12px; }
                QTextBrowser { background:#0f192b; color:#e8eef8;
                               border:1px solid #263b58; border-radius:20px;
                               padding:12px; selection-background-color:#315a78; }
                QLineEdit { background:#142039; color:#ffffff;
                            border:1px solid #456b91; border-radius:18px;
                            padding:13px; font-size:14px; }
                QPushButton { background:#6556c8; color:#ffffff;
                              border:0; border-radius:17px;
                              padding:12px 20px; font-weight:700; }
                QPushButton:hover { background:#8272ef; }
                QPushButton:disabled { background:#394657; color:#9aa6b7; }
                QCheckBox { color:#b9c8dc; spacing:8px; padding:5px; }
                QFrame#header { background:#151f30; border:1px solid #263b55;
                                border-radius:15px; }
            """)

            central = QWidget()
            self.setCentralWidget(central)
            layout = QVBoxLayout(central)
            layout.setContentsMargins(18, 18, 18, 18)
            layout.setSpacing(12)

            header = QFrame()
            header.setObjectName("header")
            header_layout = QVBoxLayout(header)
            header_layout.setContentsMargins(16, 13, 16, 13)
            brand = QLabel("REX AI  ·  YOUR INTELLIGENT DESKTOP")
            brand.setObjectName("brand")
            subtitle = QLabel("A NEW KIND OF DESKTOP COMPANION")
            subtitle.setObjectName("subtitle")
            header_layout.addWidget(brand)
            header_layout.addWidget(subtitle)
            layout.addWidget(header)

            self.status = QLabel("REX AI: Connecting…")
            self.status.setObjectName("status")
            layout.addWidget(self.status)

            self.chat = QTextBrowser()
            self.chat.setOpenExternalLinks(True)
            self.chat.setPlaceholderText("Your conversation with REX will appear here.")
            layout.addWidget(self.chat, 1)

            controls = QHBoxLayout()
            self.google_toggle = QCheckBox("Search Google and use results in answers")
            self.google_toggle.setChecked(True)
            controls.addWidget(self.google_toggle)
            controls.addStretch(1)
            layout.addLayout(controls)

            row = QHBoxLayout()
            self.input = QLineEdit()
            self.input.setPlaceholderText("Ask REX anything…")
            self.input.returnPressed.connect(self.send_message)
            row.addWidget(self.input, 1)
            self.voice_button = QPushButton("🎙 Speak")
            self.voice_button.setToolTip("Record one offline voice command")
            self.voice_button.clicked.connect(self.start_voice_capture)
            row.addWidget(self.voice_button)
            self.send_button = QPushButton("Send  ➤")
            self.send_button.clicked.connect(self.send_message)
            row.addWidget(self.send_button)
            layout.addLayout(row)

            self.wake_toggle = QCheckBox("Enable Hey Rex hands-free listening (processed locally)")
            self.wake_toggle.setChecked(False)
            self.wake_toggle.setToolTip("When enabled, the microphone listens locally for Hey Rex. Audio is not uploaded or saved.")
            layout.addWidget(self.wake_toggle)
            self.wake_worker = None
            self.wake_toggle.toggled.connect(self.toggle_wake_word)

            self.speak_toggle = QCheckBox("Speak REX replies aloud")
            self.speak_toggle.setChecked(True)
            self.speak_toggle.setToolTip("Uses the installed local espeak-ng voice")
            layout.addWidget(self.speak_toggle)
            self.voice_worker = None

            self.command_router = DesktopCommandRouter() if DesktopCommandRouter else None
            self.worker = AIWorker()
            self.worker.response_ready.connect(self.show_response)
            self.worker.status_ready.connect(self.show_status)
            self.worker.search_ready.connect(self.show_search_results)
            self.worker.start()
            self.add_message("REX", "Hello! I'm REX. Ask me something, or let me search Google and bring sources into our conversation.", False)
            QTimer.singleShot(1200, self.process_initial_request)

        def add_message(self, sender, message, user):
            safe = html.escape(message).replace("\n", "<br>")
            bg = "#20344a" if user else "#192438"
            self.chat.append(
                f'<div style="margin:9px 0;padding:11px 13px;background:{bg};'
                f'border-radius:12px;"><b style="color:#62d8e5">{html.escape(sender)}</b>'
                f'<br><span>{safe}</span></div>'
            )

        def process_initial_request(self):
            if self.initial_command:
                self.input.setText(self.initial_command)
                self.send_message()
            elif self.wake_only:
                greeting = "I heard you. What can I do for you?"
                self.add_message("REX", greeting, False)
                self.speak_response(greeting)
                self.input.setFocus()

        def toggle_wake_word(self, enabled):
            if enabled:
                if self.wake_worker and self.wake_worker.isRunning():
                    return
                self.wake_worker = WakeWordWorker(self)
                self.wake_worker.activated.connect(self.on_wake_activation)
                self.wake_worker.failed.connect(self.on_voice_error)
                self.wake_worker.finished.connect(self.on_wake_finished)
                self.wake_worker.start()
                self.add_message("VOICE", "Hey Rex is listening locally. Say “Hey Rex” followed by a command.", False)
            elif self.wake_worker:
                self.wake_worker.stop()
                self.wake_worker.wait(5000)
                self.wake_worker = None
                self.add_message("VOICE", "Hey Rex listening is off.", False)

        def on_wake_activation(self, command):
            if command.strip():
                self.input.setText(command.strip())
                self.send_message()
            else:
                greeting = "I heard Hey Rex. What can I do for you?"
                self.add_message("REX", greeting, False)
                self.speak_response(greeting)

        def on_wake_finished(self):
            if self.wake_toggle.isChecked():
                self.wake_toggle.blockSignals(True)
                self.wake_toggle.setChecked(False)
                self.wake_toggle.blockSignals(False)
            self.wake_worker = None

        def start_voice_capture(self):
            if self.voice_worker and self.voice_worker.isRunning():
                return
            self.voice_button.setEnabled(False)
            self.voice_button.setText("Listening…")
            self.voice_worker = VoiceCaptureWorker(self)
            self.voice_worker.recognized.connect(self.on_voice_text)
            self.voice_worker.failed.connect(self.on_voice_error)
            self.voice_worker.finished.connect(self.on_voice_finished)
            self.voice_worker.start()

        def on_voice_text(self, text):
            self.input.setText(text)
            self.send_message()

        def on_voice_error(self, message):
            self.add_message("VOICE", message, False)

        def on_voice_finished(self):
            self.voice_button.setEnabled(True)
            self.voice_button.setText("🎙 Speak")
            self.voice_worker = None

        def speak_response(self, text):
            if not self.speak_toggle.isChecked():
                return
            tts = shutil.which("espeak-ng")
            if not tts:
                self.add_message("VOICE", "Local speech output is unavailable. Install espeak-ng.", False)
                return
            spoken = (text or "").strip()
            if not spoken:
                return
            try:
                subprocess.Popen(
                    [tts, "-s", "155", "--", spoken[:2500]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception as exc:
                self.add_message("VOICE", "Could not start speech output: " + str(exc), False)

        def send_message(self):
            message = self.input.text().strip()
            if not message:
                return
            self.input.clear()
            self.add_message("YOU", message, True)
            if self.command_router:
                result = self.command_router.execute(message, self.confirm_desktop_action)
                if result is not None:
                    self.add_message("REX", result, False)
                    self.speak_response(result)
                    return
            self.send_button.setEnabled(False)
            self.send_button.setText("Working…")
            self.worker.send_message(message, self.google_toggle.isChecked())

        def confirm_desktop_action(self, action, target):
            answer = QMessageBox.question(
                self, "Allow REX desktop action",
                f"Allow REX to {action}: {target}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            return answer == QMessageBox.StandardButton.Yes

        def show_search_results(self, markup):
            self.chat.append(markup)

        def show_response(self, response):
            self.add_message("REX", response, False)
            self.speak_response(response)
            self.send_button.setEnabled(True)
            self.send_button.setText("Send  ➤")

        def show_status(self, provider, online):
            state = "AI MODEL CONNECTED" if online else "AI MODEL NOT CONNECTED"
            color = "#79e2a8" if online else "#ffc078"
            self.status.setText(f"{state}  ·  {provider}")
            self.status.setStyleSheet(
                f"color:{color};background:#192438;border:1px solid #263b55;"
                "border-radius:10px;padding:8px 12px;"
            )

        def closeEvent(self, event):
            self.worker.stop()
            self.worker.wait(3000)
            if self.voice_worker and self.voice_worker.isRunning():
                self.voice_worker.wait(3000)
            if self.wake_worker and self.wake_worker.isRunning():
                self.wake_worker.stop()
                self.wake_worker.wait(5000)
            event.accept()


def main():
    if not PYQT6_AVAILABLE:
        print("REX Assistant requires python3-pyqt6.")
        return 1
    initial_command = None
    wake_only = "--wake" in sys.argv[1:]
    if "--voice-command" in sys.argv[1:]:
        index = sys.argv.index("--voice-command")
        if index + 1 < len(sys.argv):
            initial_command = sys.argv[index + 1]
    app = QApplication(sys.argv)
    window = AssistantWindow(initial_command=initial_command, wake_only=wake_only)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
