#!/usr/bin/env python3
"""REX desktop shell: compact top panel plus a separate floating application dock."""
import sys,subprocess
sys.path.insert(0, "/opt/rex-os")
try:
    from PyQt6.QtCore import Qt,QTimer
    from PyQt6.QtWidgets import QApplication,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QFrame
    QT_AVAILABLE=True
except ImportError: QT_AVAILABLE=False
try: from services.ecosystem import create_default_ecosystem
except ImportError: create_default_ecosystem=None

APP_COMMANDS={"Assistant":[sys.executable,"/opt/rex-os/ui/rex_assistant.py"],
              "Files":["dolphin"],"Terminal":["konsole"],"Settings":["systemsettings"],
              "Browser":["firefox-esr"],"Apps":[sys.executable,"/opt/rex-os/ui/rex_omni.py"],
              "Connect":[sys.executable,"/opt/rex-os/ui/rex_connect.py"]}

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
            self.setWindowTitle("REX Top Panel")
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self.resize(760,54)
            self.setStyleSheet("""
                QWidget#surface{background:rgba(13,20,36,242);border:1px solid #286078;border-radius:15px;}
                QLabel{color:#eaf7ff;} QLabel#brand{color:#67e8f9;font-size:17px;font-weight:800;}
                QLabel#muted{color:#9aacc5;font-size:10px;}
                QPushButton{color:#e8f6ff;background:#1b2b43;border:1px solid #2e506a;border-radius:10px;padding:7px 12px;font-weight:600;}
                QPushButton:hover{background:#14566b;border-color:#65d9eb;}
                QWidget#dock{background:rgba(15,23,41,245);border:1px solid #3a6380;border-radius:22px;}
                QPushButton[dock="true"]{font-size:13px;padding:12px 16px;border-radius:14px;}
            """)
            root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0)
            surface=QFrame();surface.setObjectName("surface")
            row=QHBoxLayout(surface);row.setContentsMargins(15,5,15,5)
            brand=QLabel("◈ REX");brand.setObjectName("brand");row.addWidget(brand)
            sub=QLabel("INTELLIGENCE OS");sub.setObjectName("muted");row.addWidget(sub);row.addStretch(1)
            self.status=QLabel("STARTING");self.status.setObjectName("muted");row.addWidget(self.status)
            root.addWidget(surface)
            self.dock=QWidget()
            self.dock.setWindowTitle("REX Floating Dock")
            self.dock.setObjectName("dock")
            self.dock.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
            self.dock.setStyleSheet(self.styleSheet())
            dockrow=QHBoxLayout(self.dock);dockrow.setContentsMargins(12,8,12,8);dockrow.setSpacing(8)
            for name in ("Assistant","Apps","Connect","Files","Browser","Terminal","Settings"):
                button=QPushButton(name);button.setProperty("dock","true")
                button.clicked.connect(lambda checked=False,app=name:launch_fixed_app(app))
                dockrow.addWidget(button)
            self.dock.adjustSize()
            self.position_windows()
            self.timer=QTimer(self);self.timer.timeout.connect(self.refresh);self.timer.start(5000);self.refresh()
        def position_windows(self):
            screen=QApplication.primaryScreen()
            if screen:
                area=screen.availableGeometry()
                self.move(area.x()+(area.width()-self.width())//2,area.y()+8)
                self.dock.move(area.x()+(area.width()-self.dock.width())//2,area.y()+area.height()-self.dock.height()-24)
        def refresh(self):
            if create_default_ecosystem:
                data=create_default_ecosystem().health()
                self.status.setText(f"REX • {data['online']}/{data['total']} MODULES")
            else:self.status.setText("REX • DESKTOP READY")
        def showEvent(self,event):
            super().showEvent(event);self.dock.show()
        def closeEvent(self,event):
            self.dock.close();event.accept()

def main():
    if not QT_AVAILABLE:print("REX Hub requires PyQt6.");return 1
    app=QApplication(sys.argv);window=REXHub();window.show();return app.exec()
if __name__=="__main__":sys.exit(main())
