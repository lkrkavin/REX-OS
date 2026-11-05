#!/usr/bin/env python3
"""REX Omni: discover installed desktop apps and launch them with approval."""
import sys
try:
    from PyQt6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QListWidget,QPushButton,QMessageBox
    QT=True
except ImportError: QT=False
from services.desktop_control import DesktopControl

if QT:
    class OmniWindow(QWidget):
        def __init__(self):
            super().__init__();self.setWindowTitle("REX OMNI");self.resize(650,620)
            self.setStyleSheet("QWidget{background:#101522;color:#e8eef8;} QLineEdit,QListWidget{background:#192438;border:1px solid #34536d;border-radius:10px;padding:9px;color:#fff;} QPushButton{background:#126c82;color:white;border:0;border-radius:10px;padding:10px 18px;}")
            layout=QVBoxLayout(self);layout.addWidget(QLabel("◈  REX OMNI  ·  APPLICATION LIBRARY"))
            self.search=QLineEdit();self.search.setPlaceholderText("Search installed applications…");layout.addWidget(self.search)
            self.apps=QListWidget();layout.addWidget(self.apps)
            row=QHBoxLayout();refresh=QPushButton("Refresh");launch=QPushButton("Launch selected");row.addWidget(refresh);row.addWidget(launch);layout.addLayout(row)
            refresh.clicked.connect(self.refresh);launch.clicked.connect(self.launch_selected);self.search.textChanged.connect(self.filter)
            self.entries=[];self.refresh()
        def refresh(self):
            self.entries=DesktopControl().list_applications();self.filter(self.search.text())
        def filter(self,text):
            self.apps.clear()
            for item in self.entries:
                if text.casefold() in item["name"].casefold():self.apps.addItem(item["name"])
        def launch_selected(self):
            item=self.apps.currentItem()
            if not item:return
            entry=next((x for x in self.entries if x["name"]==item.text()),None)
            if not entry:return
            answer=QMessageBox.question(self,"Confirm launch",f"Allow REX to open {entry['name']}?")
            if answer!=QMessageBox.StandardButton.Yes:return
            result=DesktopControl(lambda *_:True).launch_application(entry["id"])
            QMessageBox.information(self,"REX OMNI",result.message)
def main():
    if not QT:print("REX OMNI requires PyQt6.");return 1
    app=QApplication(sys.argv);window=OmniWindow();window.show();return app.exec()
if __name__=="__main__":sys.exit(main())
