#!/usr/bin/env python3
"""REX AI provider settings. API keys are stored in the desktop keyring only."""
import sys, json, os, urllib.request, urllib.error
from pathlib import Path
try:
    from PyQt6.QtWidgets import QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QPushButton,QMessageBox
    from PyQt6.QtCore import Qt
    QT=True
except ImportError: QT=False

MODELS=[
 "openai/gpt-4o-mini",
 "anthropic/claude-3.5-sonnet",
 "google/gemini-2.0-flash-001",
 "deepseek/deepseek-chat",
]
class SettingsWindow(QWidget if QT else object):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("REX AI · Provider Settings")
        self.resize(560,420)
        self.setStyleSheet("""
          QWidget{background:#0b1020;color:#edf4ff;font-size:13px}
          QLabel#title{font-size:24px;font-weight:800;color:#f4f7ff}
          QLabel#hint{color:#9aacc4}
          QLineEdit,QComboBox{background:#142039;color:#fff;border:1px solid #456b91;border-radius:13px;padding:12px}
          QPushButton{background:#6556c8;color:white;border:0;border-radius:14px;padding:12px 18px;font-weight:700}
          QPushButton:hover{background:#8272ef}
        """)
        layout=QVBoxLayout(self);layout.setContentsMargins(26,24,26,24);layout.setSpacing(14)
        title=QLabel("REX AI SETTINGS");title.setObjectName("title");layout.addWidget(title)
        hint=QLabel("Connect REX to OpenRouter. Your key is saved to the system keyring, never to Git or the REX config file.")
        hint.setObjectName("hint");hint.setWordWrap(True);layout.addWidget(hint)
        layout.addWidget(QLabel("OpenRouter API key"))
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.EchoMode.Password);self.key.setPlaceholderText("Paste the key supplied by the account holder");layout.addWidget(self.key)
        layout.addWidget(QLabel("Default model"))
        self.model=QComboBox();self.model.addItems(MODELS);layout.addWidget(self.model)
        layout.addStretch()
        row=QHBoxLayout();save=QPushButton("Save securely");test=QPushButton("Test connection");row.addWidget(save);row.addWidget(test);layout.addLayout(row)
        save.clicked.connect(self.save);test.clicked.connect(self.test)
        try:
            import keyring
            existing=keyring.get_password("rex-os","openrouter")
            if existing:self.key.setPlaceholderText("An API key is already stored (leave blank to keep it)")
        except Exception:pass
        cfg=Path.home()/".config/rex/ai.json"
        try:
            data=json.loads(cfg.read_text())
            idx=self.model.findText(data.get("openrouter_model",""))
            if idx>=0:self.model.setCurrentIndex(idx)
        except Exception:pass
    def save(self):
        try:
            import keyring
            if self.key.text().strip():
                keyring.set_password("rex-os","openrouter",self.key.text().strip())
            path=Path.home()/".config/rex/ai.json";path.parent.mkdir(parents=True,exist_ok=True)
            data={}
            if path.exists():
                try:data=json.loads(path.read_text())
                except Exception:pass
            data["openrouter_model"]=self.model.currentText()
            tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(data,indent=2));os.chmod(tmp,0o600);tmp.replace(path);os.chmod(path,0o600)
            self.key.clear()
            QMessageBox.information(self,"REX AI","Settings saved. Restart REX Assistant to apply the provider/model change.")
        except Exception as exc:
            QMessageBox.critical(self,"Secure storage unavailable",f"Could not save the API key to the desktop keyring. No plaintext fallback was used.\n\n{exc}")
    def test(self):
        key=self.key.text().strip()
        try:
            import keyring
            if not key:key=keyring.get_password("rex-os","openrouter") or ""
        except Exception as exc:
            QMessageBox.critical(self,"Keyring unavailable",f"Cannot read the saved API key securely.\\n\\n{exc}")
            return
        if not key:
            QMessageBox.warning(self,"API key required","Enter your OpenRouter API key, or save it first.")
            return
        request=urllib.request.Request(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization":"Bearer "+key,"User-Agent":"REX-OS/0.1.0"},
            method="GET"
        )
        try:
            with urllib.request.urlopen(request,timeout=12) as response:
                if response.status==200:
                    payload=json.loads(response.read().decode("utf-8"))
                    data=payload.get("data",{})
                    limit=data.get("limit")
                    usage=data.get("usage")
                    detail="OpenRouter accepted the API key."
                    if limit is not None:detail+=f"\\nKey limit: {limit}"
                    if usage is not None:detail+=f"\\nUsage: {usage}"
                    QMessageBox.information(self,"Connection successful",detail)
                else:
                    QMessageBox.warning(self,"Connection failed",f"OpenRouter returned HTTP {response.status}.")
        except urllib.error.HTTPError as exc:
            QMessageBox.critical(self,"Authentication failed",f"OpenRouter returned HTTP {exc.code}. Check the key and account permissions.")
        except Exception as exc:
            QMessageBox.critical(self,"Connection failed",f"Could not reach OpenRouter: {exc}")
def main():
    if not QT:print("REX AI Settings requires PyQt6.");return 1
    app=QApplication(sys.argv);w=SettingsWindow();w.show();return app.exec()
if __name__=="__main__":sys.exit(main())
