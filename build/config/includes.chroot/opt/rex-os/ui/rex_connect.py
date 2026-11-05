#!/usr/bin/env python3
"""REX Connect device dashboard; pairing and permissions remain explicit."""
import sys
try:
    from PyQt6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel,QListWidget,QPushButton,QMessageBox
    QT=True
except ImportError:QT=False
from connect.device_registry import get_device_registry

if QT:
    class ConnectWindow(QWidget):
        def __init__(self):
            super().__init__();self.setWindowTitle("REX CONNECT");self.resize(560,480)
            self.setStyleSheet("QWidget{background:#101522;color:#e8eef8;} QListWidget{background:#192438;border:1px solid #34536d;border-radius:10px;padding:8px;color:#fff;} QPushButton{background:#126c82;color:white;border:0;border-radius:10px;padding:10px 18px;}")
            layout=QVBoxLayout(self);layout.addWidget(QLabel("◈  REX CONNECT  ·  YOUR DEVICES"))
            self.devices=QListWidget();layout.addWidget(self.devices)
            refresh=QPushButton("Refresh devices");layout.addWidget(refresh);refresh.clicked.connect(self.refresh);self.refresh()
        def refresh(self):
            self.devices.clear()
            for device in get_device_registry().get_all_devices():
                self.devices.addItem(f"{device.name}  ·  {device.device_type.value}  ·  {device.connection_status.value}")
            if self.devices.count()==0:self.devices.addItem("No paired devices yet. Pairing requires confirmation on both devices.")
def main():
    if not QT:print("REX Connect requires PyQt6.");return 1
    app=QApplication(sys.argv);window=ConnectWindow();window.show();return app.exec()
if __name__=="__main__":sys.exit(main())
