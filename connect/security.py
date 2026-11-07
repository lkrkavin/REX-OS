#!/usr/bin/env python3
"""Shared, fail-closed REX Security Core for local and companion services."""
from __future__ import annotations
import os, secrets, threading, time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

class PermissionLevel(Enum):
    NONE=0; READ_ONLY=1; CONTROL=2; FULL_ACCESS=3; ADMIN=4

class Permission(Enum):
    REMOTE_MOUSE="remote_mouse"; REMOTE_KEYBOARD="remote_keyboard"; MEDIA_CONTROL="media_control"
    SCREEN_STREAMING="screen_streaming"; FILE_TRANSFER="file_transfer"; NOTIFICATIONS="notifications"
    SYSTEM_STATUS="system_status"; PROCESS_MONITOR="process_monitor"; APP_LAUNCH="app_launch"
    LOCK_SCREEN="lock_screen"; PAIRING="pairing"; DESKTOP_CONTROL="desktop_control"
    SETTINGS_WRITE="settings_write"; CLOUD_SYNC="cloud_sync"; APP_INSTALL="app_install"; APP_REMOVE="app_remove"

@dataclass(frozen=True)
class AccessToken:
    token_id: str
    device_id: str
    created_at: float
    expires_at: float
    permission_level: PermissionLevel
    permissions: FrozenSet[Permission]=field(default_factory=frozenset)
    is_revoked: bool=False
    def is_valid(self, now=None):
        now=time.time() if now is None else now
        return not self.is_revoked and self.created_at <= now < self.expires_at

@dataclass(frozen=True)
class AuditEvent:
    timestamp: float
    actor: str
    action: str
    target: str
    allowed: bool
    reason: str

@dataclass(frozen=True)
class ActionSpec:
    name: str
    permission: Permission
    requires_approval: bool=False
    max_target_length: int=256

class SecurityManager:
    """One authority for device grants, short-lived scoped sessions, approvals and audit."""
    DEFAULT_TOKEN_LIFETIME=3600
    MAX_TOKEN_LIFETIME=86400
    MAX_AUDIT_EVENTS=2000
    def __init__(self, approval_callback: Optional[Callable[[str,str],bool]]=None):
        self._lock=threading.RLock()
        self._tokens: Dict[str,AccessToken]={}
        self._device_permissions: Dict[str,FrozenSet[Permission]]={}
        self._device_levels: Dict[str,PermissionLevel]={}
        self._revoked_devices:Set[str]=set()
        self._approval_callback=approval_callback or (lambda _a,_t:False)
        self._audit:List[AuditEvent]=[]
        self._actions:Dict[str,ActionSpec]={}
        for spec in (
            ActionSpec("read_system_status",Permission.SYSTEM_STATUS),
            ActionSpec("read_processes",Permission.PROCESS_MONITOR),
            ActionSpec("launch_application",Permission.APP_LAUNCH,True),
            ActionSpec("desktop_input",Permission.DESKTOP_CONTROL,True),
            ActionSpec("screen_stream",Permission.SCREEN_STREAMING,True),
            ActionSpec("transfer_file",Permission.FILE_TRANSFER,True),
            ActionSpec("pair_device",Permission.PAIRING,True),
            ActionSpec("change_settings",Permission.SETTINGS_WRITE,True),
            ActionSpec("cloud_sync",Permission.CLOUD_SYNC,True),
            ActionSpec("install_app",Permission.APP_INSTALL,True),
            ActionSpec("remove_app",Permission.APP_REMOVE,True)):
            self._actions[spec.name]=spec

    def _defaults(self,level):
        read={Permission.SYSTEM_STATUS,Permission.NOTIFICATIONS,Permission.PROCESS_MONITOR}
        control=read|{Permission.REMOTE_MOUSE,Permission.REMOTE_KEYBOARD,Permission.MEDIA_CONTROL,Permission.APP_LAUNCH,Permission.LOCK_SCREEN,Permission.DESKTOP_CONTROL}
        full=control|{Permission.SCREEN_STREAMING,Permission.FILE_TRANSFER}
        return frozenset({PermissionLevel.NONE:set(),PermissionLevel.READ_ONLY:read,PermissionLevel.CONTROL:control,PermissionLevel.FULL_ACCESS:full,PermissionLevel.ADMIN:full|{Permission.PAIRING,Permission.SETTINGS_WRITE}}.get(level,set()))

    def register_action(self,spec):
        if not isinstance(spec,ActionSpec) or not spec.name or len(spec.name)>64:return False
        with self._lock:
            if spec.name in self._actions:return False
            self._actions[spec.name]=spec
            return True

    def grant_device_permissions(self,device_id,level,permissions=None):
        if not isinstance(device_id,str) or not device_id.strip() or len(device_id)>128 or not isinstance(level,PermissionLevel):return False
        try:
            granted=frozenset(permissions) if permissions is not None else self._defaults(level)
            if any(not isinstance(p,Permission) for p in granted):return False
        except (TypeError,ValueError):return False
        with self._lock:
            self._device_levels[device_id]=level; self._device_permissions[device_id]=granted; self._revoked_devices.discard(device_id)
        self._record(device_id,"grant_permissions",level.name,True,"explicit grant")
        return True

    def revoke_device_permissions(self,device_id):
        if not isinstance(device_id,str) or not device_id:return False
        with self._lock:
            self._device_levels[device_id]=PermissionLevel.NONE; self._device_permissions[device_id]=frozenset(); self._revoked_devices.add(device_id)
            for key,t in list(self._tokens.items()):
                if t.device_id==device_id:self._tokens[key]=AccessToken(t.token_id,t.device_id,t.created_at,t.expires_at,t.permission_level,t.permissions,True)
        self._record(device_id,"revoke_device",device_id,True,"device revoked")
        return True

    def create_session_token(self,device_id,lifetime=DEFAULT_TOKEN_LIFETIME):
        if not isinstance(device_id,str) or not device_id.strip():return None
        try:ttl=float(lifetime)
        except (TypeError,ValueError):return None
        if ttl<=0:return None
        ttl=min(ttl,self.MAX_TOKEN_LIFETIME)
        with self._lock:
            if device_id in self._revoked_devices or device_id not in self._device_permissions:return None
            now=time.time(); token=AccessToken(secrets.token_urlsafe(32),device_id,now,now+ttl,self._device_levels.get(device_id,PermissionLevel.NONE),self._device_permissions[device_id])
            self._tokens[token.token_id]=token
        self._record(device_id,"create_session","session",True,"token issued")
        return token

    def validate_token(self,token_id):
        if not isinstance(token_id,str) or not token_id:return None
        with self._lock:
            t=self._tokens.get(token_id)
            return t if t and t.is_valid() and t.device_id not in self._revoked_devices else None

    def revoke_token(self,token_id):
        with self._lock:
            t=self._tokens.get(token_id)
            if t is None:return False
            self._tokens[token_id]=AccessToken(t.token_id,t.device_id,t.created_at,t.expires_at,t.permission_level,t.permissions,True)
        self._record(t.device_id,"revoke_session",token_id[:8],True,"session revoked")
        return True

    def check_permission(self,device_id,permission,token_id=None):
        try:
            if not isinstance(device_id,str) or not device_id or not isinstance(permission,Permission):return False
            with self._lock:
                if device_id in self._revoked_devices:return False
                if token_id is not None:
                    t=self.validate_token(token_id)
                    return bool(t and t.device_id==device_id and permission in t.permissions)
                return permission in self._device_permissions.get(device_id,frozenset())
        except Exception:return False

    def authorize_action(self,actor,action,target="",token_id=None):
        if not isinstance(actor,str) or not actor or not isinstance(action,str):return False
        if not isinstance(target,str) or len(target)>256:
            self._record(str(actor)[:128],str(action)[:64],"invalid-target",False,"invalid target"); return False
        with self._lock:spec=self._actions.get(action)
        if spec is None:
            self._record(actor,action,target,False,"unknown action"); return False
        if not self.check_permission(actor,spec.permission,token_id):
            self._record(actor,action,target,False,"permission denied"); return False
        if spec.requires_approval:
            try:approved=bool(self._approval_callback(action,target))
            except Exception:approved=False
            if not approved:
                self._record(actor,action,target,False,"approval denied"); return False
        self._record(actor,action,target,True,"authorized"); return True

    def _record(self,actor,action,target,allowed,reason):
        event=AuditEvent(time.time(),str(actor)[:128],str(action)[:64],str(target)[:256],bool(allowed),str(reason)[:128])
        with self._lock:
            self._audit.append(event)
            if len(self._audit)>self.MAX_AUDIT_EVENTS:del self._audit[:-self.MAX_AUDIT_EVENTS]

    def audit_events(self,limit=100):
        if not isinstance(limit,int) or limit<1:return tuple()
        with self._lock:return tuple(self._audit[-min(limit,self.MAX_AUDIT_EVENTS):])

    def sanitize_path(self,path_str,allowed_roots=None):
        if not isinstance(path_str,str) or not path_str or "\x00" in path_str:return None
        try:
            candidate=Path(path_str).expanduser().resolve(strict=False)
            roots=[Path(x).expanduser().resolve(strict=False) for x in allowed_roots] if allowed_roots is not None else [Path.home().resolve(),(Path("/var/lib/rex/connect/transfers") if os.name!="nt" else Path("C:/rex/transfers")).resolve(strict=False)]
            for root in roots:
                try:candidate.relative_to(root); return str(candidate)
                except ValueError:continue
            return None
        except (OSError,RuntimeError,ValueError):return None

_global_security_manager=None
_global_lock=threading.Lock()
def get_security_manager():
    """Return the process-wide shared security authority."""
    global _global_security_manager
    with _global_lock:
        if _global_security_manager is None:_global_security_manager=SecurityManager()
        return _global_security_manager
