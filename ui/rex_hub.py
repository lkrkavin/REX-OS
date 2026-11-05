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
              "AI Settings":[sys.executable,"/opt/rex-os/ui/rex_ai_settings.py"],
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
            self.resize(900,58)
            self.setStyleSheet("""
                QWidget#surface{background:rgba(13,18,32,238);border:1px solid rgba(130,170,220,85);border-radius:21px;}
                QLabel{color:#eaf7ff;} QLabel#brand{color:#f2f7ff;font-size:18px;font-weight:850;letter-spacing:2px;}
                QLabel#muted{color:#9caec8;font-size:10px;letter-spacing:1px;}
                QPushButton{color:#eaf4ff;background:rgba(42,58,82,210);border:1px solid rgba(150,185,220,45);border-radius:15px;padding:9px 15px;font-weight:650;}
                QPushButton:hover{background:rgba(47,115,145,235);border-color:#78eaff;}
                QWidget#dock{background:rgba(13,18,32,242);border:1px solid rgba(130,170,220,95);border-radius:25px;}
                QPushButton[dock="true"]{font-size:13px;padding:13px 17px;border-radius:17px;}
            """)
            root=QVBoxLayout(self);root.setContentsMargins(0,0,0,0)
            surface=QFrame();surface.setObjectName("surface")
            row=QHBoxLayout(surface);row.setContentsMargins(15,5,15,5)
            brand=QLabel("REX  ◉");brand.setObjectName("brand");row.addWidget(brand)
            sub=QLabel("INTELLIGENCE  ·  CONNECTED");sub.setObjectName("muted");row.addWidget(sub);row.addStretch(1)
            self.status=QLabel("STARTING");self.status.setObjectName("muted");row.addWidget(self.status)
            root.addWidget(surface)
            self.dock=QWidget()
            self.dock.setWindowTitle("REX Floating Dock")
            self.dock.setObjectName("dock")
            self.dock.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint|Qt.WindowType.Tool)
            self.dock.setStyleSheet(self.styleSheet())
            dockrow=QHBoxLayout(self.dock);dockrow.setContentsMargins(12,8,12,8);dockrow.setSpacing(8)
            for name in ("✦  REX AI","◈  AI SETUP","▦  OMNI","⌁  CONNECT","◫  FILES","⌘  TERMINAL","⚙  SETTINGS"):
                button=QPushButton(name);button.setProperty("dock","true")
                button.clicked.connect(lambda checked=False,app=name:launch_fixed_app({"✦  REX AI":"Assistant","◈  AI SETUP":"AI Settings","▦  OMNI":"Apps","⌁  CONNECT":"Connect","◫  FILES":"Files","⌘  TERMINAL":"Terminal","⚙  SETTINGS":"Settings"}[app]))
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
                self.status.setText("REX • " + str(data["total"]) + " MODULES")
            else:self.status.setText("REX • DESKTOP READY")
        def showEvent(self,event):
            super().showEvent(event);self.dock.show()
        def closeEvent(self,event):
            self.dock.close();event.accept()

def main():
    if not QT_AVAILABLE:print("REX Hub requires PyQt6.");return 1
    app=QApplication(sys.argv);window=REXHub();window.show();return app.exec()
if __name__=="__main__":sys.exit(main())
