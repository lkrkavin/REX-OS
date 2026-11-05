#!/usr/bin/env python3
"""REX floating robot with local offline 'Hey Rex' activation."""

import sys
sys.path.insert(0, "/opt/rex-os")
sys.path.insert(0, "/opt/rex-os")
import subprocess

try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import Qt, QTimer, QPoint, QObject, pyqtSignal
    from PyQt6.QtGui import QPainter, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

try:
    from ais.wake_word import LocalWakeWordListener
except ImportError:
    LocalWakeWordListener = None


class RobotState:
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    ERROR = "error"
    OFFLINE = "offline"


if PYQT6_AVAILABLE:
    class WakeBridge(QObject):
        activated = pyqtSignal(object)
        error = pyqtSignal(str)


    class REXRobot(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("REX")
            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool |
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.resize(120, 120)
            self.dragging = False
            self.offset = QPoint()
            self.state = RobotState.IDLE
            self.robot_color = QColor(0, 194, 203)
            self._animation_angle = 0
            self._animation_timer = QTimer(self)
            self._animation_timer.timeout.connect(self._update_animation)
            self._animation_timer.start(50)

            self._wake_bridge = WakeBridge(self)
            self._wake_bridge.activated.connect(self._on_wake_activation)
            self._wake_bridge.error.connect(self._on_wake_error)
            self._wake_listener = None
            if LocalWakeWordListener is not None:
                self._wake_listener = LocalWakeWordListener(
                    on_activation=lambda command: self._wake_bridge.activated.emit(command),
                    on_error=lambda message: self._wake_bridge.error.emit(message),
                    wake_word="hey rex",
                    language="en-US",
                )
                self._wake_listener.start()

        def _update_animation(self):
            self._animation_angle = (self._animation_angle + 2) % 360
            self.update()

        def set_state(self, state):
            self.state = state
            self.update()

        def _on_wake_error(self, message):
            print("[REX Wake Word] " + message, file=sys.stderr)
            self.set_state(RobotState.OFFLINE)

        def _on_wake_activation(self, command):
            self.set_state(RobotState.THINKING)
            self._launch_assistant(command=command, wake=True)
            self.set_state(RobotState.IDLE)

        def _launch_assistant(self, command=None, wake=False):
            args = [sys.executable, "/opt/rex-os/ui/rex_assistant.py"]
            if command:
                args.extend(["--voice-command", command])
            elif wake:
                args.append("--wake")
            try:
                subprocess.Popen(
                    args,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except Exception as exc:
                print("Unable to open REX Assistant: " + str(exc), file=sys.stderr)
                self.set_state(RobotState.ERROR)

        def mousePressEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.dragging = True
                self.offset = event.pos()

        def mouseDoubleClickEvent(self, event):
            self._launch_assistant()

        def mouseReleaseEvent(self, event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.dragging = False

        def mouseMoveEvent(self, event):
            if self.dragging:
                self.move(self.mapToGlobal(event.pos() - self.offset))

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(24, 31, 48, 238))
            painter.setPen(QColor(0, 194, 203))
            painter.drawEllipse(10, 10, 100, 100)

            if self.state == RobotState.THINKING:
                eye_color = QColor(255, 183, 77)
            elif self.state == RobotState.ERROR or self.state == RobotState.OFFLINE:
                eye_color = QColor(255, 107, 107)
            else:
                eye_color = QColor(73, 224, 235)
            painter.setBrush(eye_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(30, 35, 20, 20)
            painter.drawEllipse(70, 35, 20, 20)
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(36, 41, 8, 8)
            painter.drawEllipse(76, 41, 8, 8)
            painter.setPen(QColor(159, 111, 255))
            painter.drawLine(60, 10, 60, 0)
            painter.setBrush(QColor(159, 111, 255))
            painter.drawEllipse(55, 0, 10, 10)

        def closeEvent(self, event):
            if self._wake_listener:
                self._wake_listener.stop()
            event.accept()


def main():
    if not PYQT6_AVAILABLE:
        print("REX Robot requires python3-pyqt6.")
        return 1
    app = QApplication(sys.argv)
    robot = REXRobot()
    robot.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
