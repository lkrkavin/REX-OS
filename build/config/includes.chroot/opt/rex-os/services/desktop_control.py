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

    def _xdotool(self):
        return shutil.which("xdotool")

    def press_key(self, key):
        allowed={"ENTER","ESC","TAB","SPACE","CTRL+C","CTRL+V","CTRL+L","ALT+F4","CTRL+SHIFT+ESC"}
        if not isinstance(key,str) or key.upper() not in allowed:
            return ControlResult(False,"press_key","Key or shortcut is not in the safe allowlist.")
        if not self._approved("press_key",key.upper()):
            return ControlResult(False,"press_key","Keyboard input requires approval.")
        tool=self._xdotool()
        if not tool:return ControlResult(False,"press_key","xdotool is not installed.")
        try:
            result=subprocess.run([tool,"key",key.lower()],capture_output=True,timeout=3,check=False)
            return ControlResult(result.returncode==0,"press_key","Key sent." if result.returncode==0 else "Key action failed.")
        except (OSError,subprocess.TimeoutExpired) as exc:return ControlResult(False,"press_key",str(exc))

    def type_text(self, text):
        if not isinstance(text,str) or not text or len(text)>1000 or "\\x00" in text:
            return ControlResult(False,"type_text","Text must be between 1 and 1000 characters.")
        if not self._approved("type_text","text input"):
            return ControlResult(False,"type_text","Typing requires approval.")
        tool=self._xdotool()
        if not tool:return ControlResult(False,"type_text","xdotool is not installed.")
        try:
            result=subprocess.run([tool,"type","--clearmodifiers","--delay","1","--",text],capture_output=True,timeout=10,check=False)
            return ControlResult(result.returncode==0,"type_text","Text entered." if result.returncode==0 else "Text entry failed.")
        except (OSError,subprocess.TimeoutExpired) as exc:return ControlResult(False,"type_text",str(exc))

    def click_mouse(self, button=1):
        if button not in (1,2,3):return ControlResult(False,"click_mouse","Only primary, middle and secondary clicks are allowed.")
        if not self._approved("click_mouse",str(button)):
            return ControlResult(False,"click_mouse","Mouse click requires approval.")
        tool=self._xdotool()
        if not tool:return ControlResult(False,"click_mouse","xdotool is not installed.")
        try:
            result=subprocess.run([tool,"click",str(button)],capture_output=True,timeout=3,check=False)
            return ControlResult(result.returncode==0,"click_mouse","Click sent." if result.returncode==0 else "Click failed.")
        except (OSError,subprocess.TimeoutExpired) as exc:return ControlResult(False,"click_mouse",str(exc))

    def move_mouse(self, x, y):
        if not isinstance(x,int) or not isinstance(y,int) or not (0<=x<=10000 and 0<=y<=10000):
            return ControlResult(False,"move_mouse","Mouse coordinates are outside the accepted range.")
        if not self._approved("move_mouse",f"{x},{y}"):
            return ControlResult(False,"move_mouse","Mouse movement requires approval.")
        tool=self._xdotool()
        if not tool:return ControlResult(False,"move_mouse","xdotool is not installed.")
        try:
            result=subprocess.run([tool,"mousemove","--sync",str(x),str(y)],capture_output=True,timeout=3,check=False)
            return ControlResult(result.returncode==0,"move_mouse","Pointer moved." if result.returncode==0 else "Pointer movement failed.")
        except (OSError,subprocess.TimeoutExpired) as exc:return ControlResult(False,"move_mouse",str(exc))

    def terminate_managed_process(self,pid):
        process=self.children.get(pid)
        if process is None or process.poll() is not None:return ControlResult(False,"terminate","REX does not manage this process.")
        if not self._approved("terminate",str(pid)):return ControlResult(False,"terminate","Closing an application requires approval.")
        try:process.terminate();return ControlResult(True,"terminate","Close request sent.",pid)
        except OSError as exc:return ControlResult(False,"terminate",str(exc))
