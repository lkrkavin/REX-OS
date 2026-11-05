#!/usr/bin/env python3
"""REX mac-inspired desktop shell: translucent menu bar and floating app dock."""
import sys, subprocess
from datetime import datetime
sys.path.insert(0, "/opt/rex-os")
try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QFrame
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
try:
    from services.ecosystem import create_default_ecosystem
except ImportError:
    create_default_ecosystem = None

APP_COMMANDS = {
    "Assistant": [sys.executable, "/opt/rex-os/ui/rex_assistant.py"],
    "AI Settings": [sys.executable, "/opt/rex-os/ui/rex_ai_settings.py"],
    "Files": ["dolphin"], "Terminal": ["konsole"], "Settings": ["systemsettings"],
    "Browser": ["firefox-esr"], "Apps": [sys.executable, "/opt/rex-os/ui/rex_omni.py"],
    "Connect": [sys.executable, "/opt/rex-os/ui/rex_connect.py"],
}
def launch_fixed_app(name):
    command = APP_COMMANDS.get(name)
    if not command:
        return False
    try:
        subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
        return True
    except OSError:
        return False

if QT_AVAILABLE:
    class REXHub(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("REX Menu Bar")
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.resize(1040, 56)
            self.setStyleSheet("""
                QWidget#bar, QWidget#dock { background:rgba(15,20,35,235); border:1px solid rgba(148,177,220,90); }
                QWidget#bar { border-radius:19px; }
                QWidget#dock { border-radius:27px; }
                QLabel { color:#eaf2ff; }
                QLabel#brand { color:#ffffff; font-size:17px; font-weight:900; letter-spacing:2px; }
                QLabel#muted { color:#aabbd3; font-size:10px; letter-spacing:1px; }
                QLabel#clock { color:#edf4ff; font-size:12px; font-weight:650; }
                QToolButton { color:#eaf4ff; background:transparent; border:1px solid transparent;
                    border-radius:17px; padding:5px; font-size:11px; font-weight:650; }
                QToolButton:hover { background:rgba(80,112,160,100); border:1px solid rgba(130,220,255,150); }
            """)
            root = QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
            bar = QFrame(); bar.setObjectName("bar")
            row = QHBoxLayout(bar); row.setContentsMargins(18,5,18,5); row.setSpacing(14)
            brand = QLabel("REX"); brand.setObjectName("brand"); row.addWidget(brand)
            menu = QLabel("  Workspace     Applications     AI     Window     Help"); menu.setObjectName("muted"); row.addWidget(menu)
            row.addStretch(1)
            self.status = QLabel("INITIALISING"); self.status.setObjectName("muted"); row.addWidget(self.status)
            self.clock = QLabel(); self.clock.setObjectName("clock"); row.addWidget(self.clock)
            root.addWidget(bar)
            self.dock = QWidget(); self.dock.setObjectName("dock")
            self.dock.setWindowTitle("REX Floating Dock")
            self.dock.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
            self.dock.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.dock.setStyleSheet(self.styleSheet())
            dockrow = QHBoxLayout(self.dock); dockrow.setContentsMargins(13,8,13,8); dockrow.setSpacing(5)
            entries = [
                ("✦","REX AI","Assistant"), ("◈","AI SETUP","AI Settings"), ("▦","OMNI","Apps"),
                ("⌁","CONNECT","Connect"), ("◫","FILES","Files"), ("⌘","TERMINAL","Terminal"),
                ("◎","BROWSER","Browser"), ("⚙","SETTINGS","Settings")
            ]
            for glyph, label, target in entries:
                button = QToolButton(); button.setText(glyph + "\n" + label)
                button.setToolTip(target); button.setFixedSize(78,66)
                button.clicked.connect(lambda checked=False, app=target: launch_fixed_app(app))
                dockrow.addWidget(button)
            self.dock.adjustSize()
            self.position_windows()
            self.timer = QTimer(self); self.timer.timeout.connect(self.refresh); self.timer.start(1000)
            self.refresh()
        def position_windows(self):
            screen = QApplication.primaryScreen()
            if screen:
                area = screen.availableGeometry()
                self.move(area.x() + (area.width()-self.width())//2, area.y()+8)
                self.dock.move(area.x() + (area.width()-self.dock.width())//2,
                               area.y()+area.height()-self.dock.height()-18)
        def refresh(self):
            if create_default_ecosystem:
                report = create_default_ecosystem().health()
                self.status.setText("●  " + str(report.get("registered",0)) + " MODULES REGISTERED")
            else:
                self.status.setText("●  DESKTOP READY")
            self.clock.setText(datetime.now().astimezone().strftime("%a  %d %b   %I:%M %p"))
        def showEvent(self, event):
            super().showEvent(event); self.dock.show()
        def closeEvent(self, event):
            self.dock.close(); event.accept()

def main():
    if not QT_AVAILABLE:
        print("REX Hub requires PyQt6."); return 1
    app = QApplication(sys.argv); window = REXHub(); window.show(); return app.exec()
if __name__ == "__main__":
    sys.exit(main())
