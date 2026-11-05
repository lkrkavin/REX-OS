#!/usr/bin/env python3
"""REX floating robot with local offline 'Hey Rex' activation."""

import sys
sys.path.insert(0, "/opt/rex-os")
sys.path.insert(0, "/opt/rex-os")
import subprocess

try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import Qt, QTimer, QPoint, QObject, pyqtSignal, QRectF
    from PyQt6.QtGui import QPainter, QColor, QPen, QRadialGradient, QConicalGradient
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
            self.resize(156, 156)
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
            import math
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            phase = math.radians(self._animation_angle)
            bob = math.sin(phase * 1.8) * 3.5
            cx, cy = 78.0, 78.0
            if self.state == RobotState.THINKING:
                accent = QColor("#a895ff")
            elif self.state == RobotState.LISTENING:
                accent = QColor("#62eaff")
            elif self.state in (RobotState.ERROR, RobotState.OFFLINE):
                accent = QColor("#ff788b")
            else:
                accent = QColor("#70e6d2")
            pulse = 0.5 + 0.5 * math.sin(phase * 2.2)
            # soft ambient aura and animated orbit
            aura = QRadialGradient(78, 78, 76)
            aura.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 68))
            aura.setColorAt(1, QColor(9, 14, 28, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(aura)
            p.drawEllipse(2, 2, 152, 152)
            p.save()
            p.translate(cx, cy)
            p.rotate(self._animation_angle * 0.65)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(QColor(accent.red(), accent.green(), accent.blue(), 115), 1.5))
            p.drawArc(-62, -62, 124, 124, 20 * 16, 105 * 16)
            p.drawArc(-62, -62, 124, 124, 205 * 16, 65 * 16)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawEllipse(53, -63, 5, 5)
            p.restore()
            # antenna
            p.setPen(QPen(accent, 2.5))
            p.drawLine(QPoint(78, int(35 + bob)), QPoint(78, int(22 + bob)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawEllipse(QPoint(78, int(19 + bob)), int(4 + pulse * 2), int(4 + pulse * 2))
            # side modules
            p.setBrush(QColor("#263651"))
            p.setPen(QPen(accent, 2))
            p.drawRoundedRect(QRectF(27, 59 + bob, 13, 29), 6, 6)
            p.drawRoundedRect(QRectF(116, 59 + bob, 13, 29), 6, 6)
            # ceramic shell
            shell = QRadialGradient(60, 45 + bob, 95)
            shell.setColorAt(0, QColor("#f4fbff"))
            shell.setColorAt(1, QColor("#a9c7df"))
            p.setBrush(shell)
            p.setPen(QPen(QColor("#8cecff"), 2))
            p.drawRoundedRect(QRectF(35, 34 + bob, 86, 76), 25, 25)
            # face glass
            p.setBrush(QColor("#101c33"))
            p.setPen(QPen(QColor("#547a9d"), 1.2))
            p.drawRoundedRect(QRectF(43, 45 + bob, 70, 52), 18, 18)
            # eyes react to state
            eye_y = 70 + bob
            eye_h = 3 if (self._animation_angle % 120) < 4 else (9 if self.state != RobotState.THINKING else 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawRoundedRect(QRectF(56, eye_y - eye_h / 2, 10, eye_h), 4, 4)
            p.drawRoundedRect(QRectF(90, eye_y - eye_h / 2, 10, eye_h), 4, 4)
            # expressive mouth
            p.setPen(QPen(accent, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if self.state == RobotState.LISTENING:
                p.drawEllipse(QRectF(74, 82 + bob, 8, 7))
            elif self.state == RobotState.THINKING:
                p.drawPoint(QPoint(78, int(86 + bob)))
            else:
                p.drawLine(QPoint(73, int(86 + bob)), QPoint(83, int(86 + bob)))
            # compact floating body
            p.setBrush(QColor("#293d5b"))
            p.setPen(QPen(accent, 1.8))
            p.drawRoundedRect(QRectF(51, 111 + bob, 54, 25), 10, 10)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(accent)
            p.drawEllipse(QPoint(78, int(123 + bob)), 4, 4)
            p.end()

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
