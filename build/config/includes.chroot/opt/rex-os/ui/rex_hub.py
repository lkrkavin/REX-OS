#!/usr/bin/env python3
"""Unified lightweight REX top panel and application dock."""
import sys,subprocess
try:
    from PyQt6.QtCore import Qt,QTimer
    from PyQt6.QtWidgets import QApplication,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QFrame
    QT_AVAILABLE=True
except ImportError: QT_AVAILABLE=False
try: from services.ecosystem import create_default_ecosystem
except ImportError: create_default_ecosystem=None

APP_COMMANDS={"Assistant":[sys.executable,"/opt/rex-os/ui/rex_assistant.py"],
              "Files":["dolphin"],"Terminal":["konsole"],
              "Settings":["systemsettings"],"Browser":["firefox-esr"]}

def launch_fixed_app(name):
    command=APP_COMMANDS.get(name)
    if not command:return False
    try:
        subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True)
        return True
    except OSError:return False

if QT_AVAILABLE:
    class REXHub(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("REX Desktop")
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.resize(920,72)
            self.setStyleSheet("""
                QWidget#surface{background:rgba(13,20,36,238);border:1px solid #286078;border-radius:19px;}
                QLabel{color:#eaf7ff;} QLabel#brand{color:#67e8f9;font-size:18px;font-weight:800;}
                QLabel#muted{color:#9aacc5;font-size:10px;}
                QPushButton{color:#e8f6ff;background:#1b2b43;border:1px solid #2e506a;border-radius:12px;padding:9px 13px;font-weight:600;}
                QPushButton:hover{background:#14566b;border-color:#65d9eb;}
            """)
            root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0)
            surface=QFrame();surface.setObjectName("surface")
            row=QHBoxLayout(surface);row.setContentsMargins(18,9,18,9);row.setSpacing(9)
            brand=QLabel("◈  REX");brand.setObjectName("brand");row.addWidget(brand)
            sub=QLabel("YOUR DESKTOP");sub.setObjectName("muted");row.addWidget(sub);row.addStretch(1)
            for name in ("Assistant","Files","Browser","Terminal","Settings"):
                button=QPushButton(name)
                button.clicked.connect(lambda checked=False,app=name:launch_fixed_app(app))
                row.addWidget(button)
            self.status=QLabel("SYSTEM READY");self.status.setObjectName("muted");row.addWidget(self.status)
            root.addWidget(surface)
            screen=QApplication.primaryScreen()
            if screen:
                area=screen.availableGeometry()
                self.move(area.x()+(area.width()-self.width())//2,area.y()+12)
            self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(5000);self.refresh()
        def refresh(self):
            if create_default_ecosystem:
                data=create_default_ecosystem().health()
                self.status.setText(f"REX  •  {data['online']}/{data['total']} MODULES")
            else:self.status.setText("REX  •  DESKTOP READY")

def main():
    if not QT_AVAILABLE:print("REX Hub requires PyQt6.");return 1
    app=QApplication(sys.argv);window=REXHub();window.show();return app.exec()
if __name__=="__main__":sys.exit(main())
