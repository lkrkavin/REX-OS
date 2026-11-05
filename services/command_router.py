#!/usr/bin/env python3
"""Deterministic, allowlisted natural-language desktop command router."""
import re
from services.desktop_control import DesktopControl

class DesktopCommandRouter:
    def __init__(self, control=None):
        self.control=control or DesktopControl()

    def execute(self, command, confirm=None):
        if not isinstance(command,str):return None
        text=command.strip()
        lower=text.casefold()
        control=self.control if confirm is None else DesktopControl(confirm)
        if lower in ("show windows","list windows","what windows are open"):
            windows=control.list_windows()
            return "No windows were found, or wmctrl is unavailable." if not windows else "\n".join(f"{w['title']} [{w['id']}]" for w in windows)
        if lower in ("list apps","show apps","what apps are installed"):
            apps=control.list_applications()
            return "\n".join(x["name"] for x in apps[:40]) if apps else "No desktop applications were found."
        match=re.fullmatch(r"(?:open|launch|start) (.+)",text,re.IGNORECASE)
        if match:
            requested=match.group(1).strip().casefold()
            apps=control.list_applications()
            exact=[x for x in apps if x["name"].casefold()==requested or x["id"].removesuffix(".desktop").casefold()==requested]
            candidates=exact or [x for x in apps if requested in x["name"].casefold()]
            if not candidates:return f"I couldn't find an installed app named {match.group(1)}."
            if len(candidates)>1:return "More than one app matches: "+", ".join(x["name"] for x in candidates[:8])+". Please use the exact app name."
            result=control.launch_application(candidates[0]["id"])
            return result.message
        match=re.fullmatch(r"(?:switch to|focus) (.+)",text,re.IGNORECASE)
        if match:
            requested=match.group(1).strip().casefold()
            windows=control.list_windows()
            matches=[w for w in windows if requested in w["title"].casefold()]
            if len(matches)!=1:return "I couldn't identify one unique open window with that title."
            return control.focus_window(matches[0]["id"]).message
        match=re.fullmatch(r"press (.+)",text,re.IGNORECASE)
        if match:return control.press_key(match.group(1).strip()).message
        match=re.fullmatch(r"type (.+)",text,re.IGNORECASE|re.DOTALL)
        if match:return control.type_text(match.group(1)).message
        if lower in ("click","left click"):return control.click_mouse(1).message
        if lower=="right click":return control.click_mouse(3).message
        match=re.fullmatch(r"move mouse to (\d{1,5})[, ]+(\d{1,5})",text,re.IGNORECASE)
        if match:return control.move_mouse(int(match.group(1)),int(match.group(2))).message
        return None
