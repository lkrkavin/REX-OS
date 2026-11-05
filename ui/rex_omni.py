#!/usr/bin/env python3
"""REX Omni application centre: installed apps, repository search and platform support."""
import sys, subprocess, re, shutil
sys.path.insert(0,"/opt/rex-os")
try:
 from PyQt6.QtWidgets import (QApplication,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,
  QListWidget,QListWidgetItem,QPushButton,QMessageBox,QTabWidget,QComboBox,QProgressBar)
 from PyQt6.QtCore import Qt
 QT=True
except ImportError: QT=False
try:
 from omni.platform_support import PlatformSupport
except ImportError: PlatformSupport=None

PKG_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_-]{0,179}$")
def run(args,timeout=180):
 try:
  return subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False)
 except Exception as exc:
  return None

if QT:
 class OmniWindow(QWidget):
  def __init__(self):
   super().__init__();self.setWindowTitle("REX OMNI · Universal App Centre");self.resize(900,700)
   self.setStyleSheet("""
    QWidget{background:#0b1020;color:#edf4ff;font-size:13px}
    QLabel#title{font-size:25px;font-weight:850;color:#f4f7ff;letter-spacing:1px}
    QLabel#muted{color:#9aacc4}
    QLineEdit,QListWidget,QComboBox{background:#142039;color:#fff;border:1px solid #354f70;border-radius:14px;padding:10px}
    QPushButton{background:#6556c8;color:white;border:0;border-radius:14px;padding:11px 17px;font-weight:700}
    QPushButton:hover{background:#8272ef}
    QTabWidget::pane{border:1px solid #293d5a;border-radius:15px}
    QTabBar::tab{background:#142039;color:#cbd8ec;padding:11px 18px;border-radius:10px;margin:4px}
    QTabBar::tab:selected{background:#6556c8;color:white}
   """)
   root=QVBoxLayout(self);title=QLabel("REX OMNI");title.setObjectName("title");root.addWidget(title)
   hint=QLabel("One place to discover, install and manage applications");hint.setObjectName("muted");root.addWidget(hint)
   self.tabs=QTabWidget();root.addWidget(self.tabs)
   self._build_store();self._build_installed();self._build_platforms()
  def _build_store(self):
   page=QWidget();layout=QVBoxLayout(page)
   row=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText("Search Debian packages or enter a Flatpak application ID…")
   self.method=QComboBox();self.method.addItems(["APT (Debian)","Flatpak (Flathub)"])
   search=QPushButton("Search");search.clicked.connect(self.search_apps)
   row.addWidget(self.search,1);row.addWidget(self.method);row.addWidget(search);layout.addLayout(row)
   self.results=QListWidget();layout.addWidget(self.results,1)
   actions=QHBoxLayout();install=QPushButton("Install selected");install.clicked.connect(self.install_selected)
   refresh=QPushButton("Refresh search");refresh.clicked.connect(self.search_apps)
   actions.addWidget(refresh);actions.addStretch();actions.addWidget(install);layout.addLayout(actions)
   self.tabs.addTab(page,"Discover")
  def _build_installed(self):
   page=QWidget();layout=QVBoxLayout(page)
   row=QHBoxLayout();refresh=QPushButton("Refresh installed apps");refresh.clicked.connect(self.refresh_installed)
   remove=QPushButton("Uninstall selected");remove.clicked.connect(self.uninstall_selected)
   updates=QPushButton("Check updates");updates.clicked.connect(self.check_updates)
   row.addWidget(refresh);row.addWidget(remove);row.addWidget(updates);layout.addLayout(row)
   self.installed=QListWidget();layout.addWidget(self.installed,1)
   self.tabs.addTab(page,"Installed & Updates");self.refresh_installed()
  def _build_platforms(self):
   page=QWidget();layout=QVBoxLayout(page)
   note=QLabel("REX Omni distinguishes native installs from compatibility layers and remote devices. It will not claim that every foreign-OS app runs locally.")
   note.setWordWrap(True);note.setObjectName("muted");layout.addWidget(note)
   self.platforms=QListWidget();layout.addWidget(self.platforms,1)
   btn=QPushButton("Detect available platforms");btn.clicked.connect(self.refresh_platforms);layout.addWidget(btn)
   self.tabs.addTab(page,"Platforms");self.refresh_platforms()
  def _message(self,title,text,error=False):
   (QMessageBox.critical if error else QMessageBox.information)(self,title,text)
  def search_apps(self):
   query=self.search.text().strip()
   if not query:self._message("Search","Enter an app name first.");return
   self.results.clear()
   if self.method.currentIndex()==0:
    res=run(["apt-cache","search","--names-only",query],30)
    if not res or res.returncode not in (0,):
     self._message("Search failed",res.stderr if res else "apt-cache unavailable",True);return
    for line in res.stdout.splitlines()[:60]:
     parts=line.split(" - ",1);pkg=parts[0].strip()
     if PKG.fullmatch(pkg):
      desc=parts[1] if len(parts)>1 else ""
      item=QListWidgetItem(pkg+"  —  "+desc);item.setData(Qt.ItemDataRole.UserRole,(pkg,"apt"));self.results.addItem(item)
   else:
    if not shutil.which("flatpak"):
     self._message("Flatpak unavailable","Flatpak is not installed on this system.");return
    res=run(["flatpak","search",query],45)
    if res:
     for line in res.stdout.splitlines()[1:]:
      cols=line.split("\t")
      if len(cols)>=2 and PKG.fullmatch(cols[0].strip()):
       fid=cols[0].strip();item=QListWidgetItem(fid+"  —  "+cols[1].strip());item.setData(Qt.ItemDataRole.UserRole,(fid,"flatpak"));self.results.addItem(item)
   if self.results.count()==0:self.results.addItem("No matching packages found.")
  def install_selected(self):
   item=self.results.currentItem()
   if not item:return
   package,method=item.data(Qt.ItemDataRole.UserRole) or (None,None)
   if not package:return
   label="APT package" if method=="apt" else "Flatpak application"
   answer=QMessageBox.question(self,"Confirm installation",f"Install {package} using {label}? This may download software and change your REX OS installation.")
   if answer!=QMessageBox.StandardButton.Yes:return
   if method=="apt":
    if not shutil.which("pkexec"):self._message("PolicyKit required","Install pkexec/policykit-1 before installing system packages.",True);return
    result=run(["pkexec","apt-get","install","-y",package],600)
   else:
    remote=run(["flatpak","remotes","--user","--columns=name"],15)
    if remote and "flathub" not in remote.stdout.split():
     confirm=QMessageBox.question(self,"Add Flathub","Add the official Flathub user repository?")
     if confirm!=QMessageBox.StandardButton.Yes:return
     add=run(["flatpak","remote-add","--user","--if-not-exists","flathub","https://dl.flathub.org/repo/flathub.flatpakrepo"],90)
     if not add or add.returncode!=0:self._message("Flathub setup failed",add.stderr if add else "Command failed",True);return
    result=run(["flatpak","install","--user","--assumeyes","flathub",package],600)
   if result and result.returncode==0:self._message("REX Omni",f"Installed {package}.");self.refresh_installed()
   else:self._message("Installation failed or cancelled",(result.stderr if result else "Command failed")[-2500:],True)
  def refresh_installed(self):
   self.installed.clear()
   res=run(["dpkg-query","-W","-f=${binary:Package}\t${Version}\n"],30)
   if res and res.returncode==0:
    for line in res.stdout.splitlines():
     parts=line.split("\t")
     if len(parts)==2 and PKG.fullmatch(parts[0]): 
      item=QListWidgetItem(parts[0]+"  ·  "+parts[1]+"  [APT]");item.setData(Qt.ItemDataRole.UserRole,(parts[0],"apt"));self.installed.addItem(item)
   if shutil.which("flatpak"):
    res=run(["flatpak","list","--user","--app","--columns=application,version"],30)
    if res:
     for line in res.stdout.splitlines():
      parts=line.split("\t")
      if parts and PKG.fullmatch(parts[0]):
       item=QListWidgetItem(parts[0]+"  ·  "+(parts[1] if len(parts)>1 else "")+"  [Flatpak]");item.setData(Qt.ItemDataRole.UserRole,(parts[0],"flatpak"));self.installed.addItem(item)
  def uninstall_selected(self):
   item=self.installed.currentItem()
   if not item:return
   package,method=item.data(Qt.ItemDataRole.UserRole)
   if QMessageBox.question(self,"Confirm removal",f"Uninstall {package}?")!=QMessageBox.StandardButton.Yes:return
   if method=="apt":
    if not shutil.which("pkexec"):self._message("PolicyKit required","pkexec is needed for system package removal.",True);return
    result=run(["pkexec","apt-get","remove","-y",package],600)
   else:result=run(["flatpak","uninstall","--user","--assumeyes",package],300)
   if result and result.returncode==0:self._message("REX Omni",f"Removed {package}.");self.refresh_installed()
   else:self._message("Removal failed or cancelled",(result.stderr if result else "Command failed")[-2000:],True)
  def check_updates(self):
   if not shutil.which("pkexec"):self._message("PolicyKit required","pkexec is needed to update system packages.",True);return
   if QMessageBox.question(self,"System updates","Refresh package lists and upgrade installed Debian packages?")!=QMessageBox.StandardButton.Yes:return
   result=run(["pkexec","sh","-c","apt-get update && apt-get upgrade -y"],1200)
   if result and result.returncode==0:self._message("Updates","System packages updated.");self.refresh_installed()
   else:self._message("Update failed or cancelled",(result.stderr if result else "Command failed")[-2500:],True)
  def refresh_platforms(self):
   self.platforms.clear()
   if PlatformSupport:
    for p in PlatformSupport().report():
     state="AVAILABLE" if p["available"] else "NOT DETECTED"
     self.platforms.addItem(f'{p["platform"]}  ·  {state}  ·  {p["detail"]}')
   else:
    for name,detail in [("Linux","Native applications"),("Windows","Wine/Bottles compatibility required"),("Android","Waydroid required"),("macOS","Connect to a separate Mac; macOS apps cannot run natively on Linux")]:
     self.platforms.addItem(name+"  ·  "+detail)
def main():
 if not QT:print("REX Omni requires PyQt6.");return 1
 app=QApplication(sys.argv);window=OmniWindow();window.show();return app.exec()
if __name__=="__main__":sys.exit(main())
