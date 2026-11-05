#!/usr/bin/env python3
"""Dependency-light registry for the unified REX ecosystem."""
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass(frozen=True)
class ModuleInfo:
    module_id: str
    title: str
    description: str
    state: str
    entrypoint: Optional[str] = None

class REXEcosystem:
    def __init__(self):
        self._modules={}
        self._checks={}

    def register(self,module_id,title,description,health_check=None,entrypoint=None):
        if not module_id or not module_id.replace("_","").isalnum():
            raise ValueError("Invalid REX module identifier")
        self._checks[module_id]=health_check or (lambda:True)
        self._modules[module_id]=ModuleInfo(module_id,title,description,"registered",entrypoint)

    def status(self,module_id):
        item=self._modules[module_id]
        try: healthy=bool(self._checks[module_id]())
        except Exception: healthy=False
        return ModuleInfo(item.module_id,item.title,item.description,"online" if healthy else "offline",item.entrypoint)

    def modules(self):
        return [self.status(key) for key in sorted(self._modules)]

    def health(self):
        items=self.modules()
        return {"system":"online" if all(x.state=="online" for x in items) else "partial",
                "online":sum(x.state=="online" for x in items),"total":len(items),
                "modules":[x.__dict__ for x in items]}

def create_default_ecosystem():
    result=REXEcosystem()
    result.register("ai","REX AI","Assistant, providers, search and voice.")
    result.register("omni","REX Omni","Application discovery and management.")
    result.register("connect","REX Connect","Paired devices and secure connectivity.")
    result.register("automation","REX Automation","Permission-gated workflows.")
    result.register("control","REX Control","Guest desktop and window controls.")
    result.register("sync","REX Sync","Shared settings and synchronization.")
    return result
