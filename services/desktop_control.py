#!/usr/bin/env python3
"""REX guest-desktop control broker. Every modifying action requires approval."""
import configparser, shlex, shutil, subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

@dataclass
class ControlResult:
    success: bool
    action: str
    message: str
    pid: Optional[int] = None

class DesktopControl:
    def __init__(self, confirm: Optional[Callable[[str, str], bool]] = None):
        self.confirm = confirm or (lambda _action, _target: False)
        self.children = {}
        self.desktop_dirs = (Path("/usr/share/applications"), Path.home()/".local/share/applications")

    def _approved(self, action, target):
        try: return bool(self.confirm(action, target))
        except Exception: return False

    def list_applications(self):
        found = {}
        for directory in self.desktop_dirs:
            if not directory.is_dir(): continue
            for entry in directory.glob("*.desktop"):
                try:
                    parser=configparser.ConfigParser(interpolation=None)
                    parser.read(entry, encoding="utf-8")
                    section=parser["Desktop Entry"]
                    if section.get("Type","Application")!="Application" or section.get("NoDisplay","false").lower()=="true": continue
                    found[entry.name]={"id":entry.name,"name":section.get("Name",entry.stem),"icon":section.get("Icon","")}
                except (OSError, KeyError, configparser.Error): continue
        return sorted(found.values(), key=lambda item:item["name"].casefold())

    def launch_application(self, desktop_id):
        if not isinstance(desktop_id,str) or not desktop_id.endswith(".desktop") or "/" in desktop_id or "\\" in desktop_id or ".." in desktop_id:
            return ControlResult(False,"launch","Invalid desktop-entry ID.")
        entry=next((d/desktop_id for d in self.desktop_dirs if (d/desktop_id).is_file()),None)
        if entry is None: return ControlResult(False,"launch","Application was not found.")
        try:
            parser=configparser.ConfigParser(interpolation=None); parser.read(entry,encoding="utf-8")
            section=parser["Desktop Entry"]
            if section.get("Type","Application")!="Application" or section.get("Terminal","false").lower()=="true" or section.get("Hidden","false").lower()=="true":
                return ControlResult(False,"launch","This application entry is not supported.")
            raw=section.get("Exec","").strip()
            if any(token in raw for token in (";","&&","||","|","`","$(","\n","\r")):
                return ControlResult(False,"launch","Unsafe desktop command rejected.")
            args=[part for part in shlex.split(raw) if not (part.startswith("%") and len(part)==2)]
            args=[arg.replace("%%","%") for arg in args]
            if not args or not shutil.which(args[0]): return ControlResult(False,"launch","Application command unavailable.")
            target=section.get("Name",desktop_id)
            if not self._approved("launch",target): return ControlResult(False,"launch","Launch requires user approval.")
            process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,start_new_session=True)
            self.children[process.pid]=process
            return ControlResult(True,"launch",f"Started {target}.",process.pid)
        except (OSError,ValueError,configparser.Error) as exc:
            return ControlResult(False,"launch",f"Could not launch application: {exc}")

    def list_windows(self):
        tool=shutil.which("wmctrl")
        if not tool:return []
        try:
            result=subprocess.run([tool,"-l"],capture_output=True,text=True,timeout=3,check=False)
            rows=[]
            for line in result.stdout.splitlines():
                parts=line.split(None,3)
                if len(parts)==4: rows.append({"id":parts[0],"desktop":parts[1],"host":parts[2],"title":parts[3]})
            return rows if result.returncode==0 else []
        except (OSError,subprocess.TimeoutExpired): return []

    def focus_window(self, window_id):
        if not isinstance(window_id,str) or not window_id.startswith("0x"): return ControlResult(False,"focus_window","Invalid window identifier.")
        if not self._approved("focus_window",window_id): return ControlResult(False,"focus_window","Window focus requires approval.")
        tool=shutil.which("wmctrl")
        if not tool:return ControlResult(False,"focus_window","wmctrl is not installed.")
        try:
            result=subprocess.run([tool,"-ia",window_id],capture_output=True,timeout=3,check=False)
            return ControlResult(result.returncode==0,"focus_window","Window focused." if result.returncode==0 else "Window focus failed.")
        except (OSError,subprocess.TimeoutExpired) as exc:return ControlResult(False,"focus_window",str(exc))

    def terminate_managed_process(self,pid):
        process=self.children.get(pid)
        if process is None or process.poll() is not None:return ControlResult(False,"terminate","REX does not manage this process.")
        if not self._approved("terminate",str(pid)):return ControlResult(False,"terminate","Closing an application requires approval.")
        try:process.terminate();return ControlResult(True,"terminate","Close request sent.",pid)
        except OSError as exc:return ControlResult(False,"terminate",str(exc))
