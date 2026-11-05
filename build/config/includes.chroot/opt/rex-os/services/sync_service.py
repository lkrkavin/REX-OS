#!/usr/bin/env python3
"""Local REX settings sync/export. Secrets and API credentials are deliberately excluded."""
import json,hashlib,os,tempfile
from pathlib import Path

class SyncService:
    VERSION=1
    ALLOWED={"ui_preferences.json","automation_rules.json","omni_favorites.json"}
    def __init__(self,base_dir=None):
        self.base=Path(base_dir or Path.home()/".config/rex")
    def export_bundle(self,destination):
        files={}
        for name in sorted(self.ALLOWED):
            path=self.base/name
            if path.is_file():
                try:files[name]=json.loads(path.read_text(encoding="utf-8"))
                except Exception:continue
        payload={"version":self.VERSION,"files":files}
        raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
        bundle={"payload":payload,"sha256":hashlib.sha256(raw).hexdigest()}
        dest=Path(destination);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(bundle,indent=2),encoding="utf-8")
        os.chmod(dest,0o600)
        return {"path":str(dest),"files":sorted(files),"sha256":bundle["sha256"]}
    def import_bundle(self,source):
        bundle=json.loads(Path(source).read_text(encoding="utf-8"))
        payload=bundle.get("payload",{})
        if payload.get("version")!=self.VERSION:raise ValueError("Unsupported sync bundle version")
        files=payload.get("files",{})
        if not isinstance(files,dict) or set(files)-self.ALLOWED:raise ValueError("Bundle contains unsupported files")
        raw=json.dumps(payload,sort_keys=True,separators=(",",":")).encode()
        if hashlib.sha256(raw).hexdigest()!=bundle.get("sha256"):raise ValueError("Sync bundle checksum mismatch")
        self.base.mkdir(parents=True,exist_ok=True)
        written=[]
        for name,data in files.items():
            target=self.base/name
            fd,tmp=tempfile.mkstemp(prefix=".rex-sync-",dir=str(self.base))
            try:
                with os.fdopen(fd,"w",encoding="utf-8") as handle:json.dump(data,handle,indent=2)
                os.chmod(tmp,0o600);os.replace(tmp,target);written.append(name)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
        return written
