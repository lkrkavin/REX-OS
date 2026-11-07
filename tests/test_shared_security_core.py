import tempfile
import unittest
from pathlib import Path
from connect.security import Permission, PermissionLevel, SecurityManager

class SharedSecurityCoreTests(unittest.TestCase):
    def test_unknown_device_denied(self):
        self.assertFalse(SecurityManager().check_permission("unknown",Permission.SYSTEM_STATUS))
    def test_token_scope_expiry_and_revoke(self):
        m=SecurityManager(); m.grant_device_permissions("phone",PermissionLevel.READ_ONLY)
        t=m.create_session_token("phone",60); self.assertIsNotNone(t)
        self.assertTrue(m.check_permission("phone",Permission.SYSTEM_STATUS,t.token_id))
        self.assertFalse(m.check_permission("other",Permission.SYSTEM_STATUS,t.token_id))
        self.assertTrue(m.revoke_token(t.token_id)); self.assertFalse(m.check_permission("phone",Permission.SYSTEM_STATUS,t.token_id))
    def test_device_revocation_invalidates_sessions(self):
        m=SecurityManager(); m.grant_device_permissions("phone",PermissionLevel.READ_ONLY); t=m.create_session_token("phone")
        self.assertTrue(m.revoke_device_permissions("phone")); self.assertIsNone(m.create_session_token("phone"))
        self.assertFalse(m.check_permission("phone",Permission.SYSTEM_STATUS,t.token_id))
    def test_lifetime_is_bounded_and_invalid_values_rejected(self):
        m=SecurityManager(); m.grant_device_permissions("phone",PermissionLevel.READ_ONLY)
        self.assertIsNone(m.create_session_token("phone",0)); self.assertIsNone(m.create_session_token("phone",-1))
        t=m.create_session_token("phone",m.MAX_TOKEN_LIFETIME*10)
        self.assertLessEqual(t.expires_at-t.created_at,m.MAX_TOKEN_LIFETIME)
    def test_sensitive_action_requires_approval_and_unknown_action_denied(self):
        m=SecurityManager(); m.grant_device_permissions("local",PermissionLevel.CONTROL)
        self.assertFalse(m.authorize_action("local","launch_application","browser"))
        approved=SecurityManager(lambda _a,_t:True); approved.grant_device_permissions("local",PermissionLevel.CONTROL)
        self.assertTrue(approved.authorize_action("local","launch_application","browser"))
        self.assertFalse(approved.authorize_action("local","arbitrary_shell","id"))
    def test_audit_records_denials(self):
        m=SecurityManager(); self.assertFalse(m.authorize_action("x","unknown_action"))
        self.assertFalse(m.audit_events()[-1].allowed)
    def test_path_sanitizer_rejects_nul_bytes(self):
        manager = SecurityManager()
        with tempfile.TemporaryDirectory() as directory:
            self.assertIsNone(manager.sanitize_path(directory + "\x00bad", [directory]))

    def test_path_sanitizer_resolves_symlink_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/"root"; root.mkdir(); outside=Path(d)/"outside"; outside.mkdir()
            (root/"escape").symlink_to(outside,target_is_directory=True)
            m=SecurityManager()
            self.assertIsNotNone(m.sanitize_path(str(root/"ok"),[str(root)]))
            self.assertIsNone(m.sanitize_path(str(root/"escape"/"file"),[str(root)]))

if __name__=="__main__":unittest.main()
