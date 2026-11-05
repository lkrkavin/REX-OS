#!/usr/bin/env python3
"""Event-driven REX automation rules. No shell commands or arbitrary code execution."""
import json,re,threading
from pathlib import Path
from dataclasses import dataclass,asdict
from typing import Dict,Any,Callable,List

_ALLOWED={"launch_app","show_notification","open_panel"}
@dataclass
class AutomationRule:
    rule_id:str
    trigger:str
    action:str
    arguments:Dict[str,Any]
    enabled:bool=True

class AutomationEngine:
    def __init__(self,path="/var/lib/rex/automation/rules.json"):
        self.path=Path(path);self._lock=threading.RLock();self._rules={}
        self.load()
    def load(self):
        try:
            data=json.loads(self.path.read_text(encoding="utf-8"))
            for raw in data.get("rules",[]):
                rule=AutomationRule(**raw)
                self._validate(rule);self._rules[rule.rule_id]=rule
        except FileNotFoundError:pass
        except Exception:self._rules={}
    def _validate(self,rule):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,48}",rule.rule_id):raise ValueError("Invalid rule ID")
        if not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}",rule.trigger):raise ValueError("Invalid trigger")
        if rule.action not in _ALLOWED:raise ValueError("Unsupported automation action")
        if len(json.dumps(rule.arguments))>2048:raise ValueError("Rule arguments too large")
    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"version":1,"rules":[asdict(x) for x in self._rules.values()]},indent=2),encoding="utf-8")
        tmp.replace(self.path)
    def add_rule(self,rule):
        self._validate(rule)
        with self._lock:self._rules[rule.rule_id]=rule;self._save()
        return rule
    def remove_rule(self,rule_id):
        with self._lock:
            if rule_id not in self._rules:return False
            del self._rules[rule_id];self._save();return True
    def list_rules(self):
        with self._lock:return [asdict(x) for x in self._rules.values()]
    def dispatch(self,trigger,executor,authorize):
        """Run matching enabled rules only after a per-action approval."""
        results=[]
        with self._lock:rules=list(self._rules.values())
        for rule in rules:
            if not rule.enabled or rule.trigger!=trigger:continue
            if not callable(authorize) or not authorize(rule):results.append({"rule_id":rule.rule_id,"success":False,"reason":"approval denied"});continue
            if not callable(executor):results.append({"rule_id":rule.rule_id,"success":False,"reason":"no executor"});continue
            try:results.append({"rule_id":rule.rule_id,"success":bool(executor(rule.action,dict(rule.arguments)))})
            except Exception as exc:results.append({"rule_id":rule.rule_id,"success":False,"reason":str(exc)})
        return results
